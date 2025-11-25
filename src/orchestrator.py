"""
Build Orchestrator
Manages dependency resolution and parallel build execution for ODP components
"""

import logging
import time
import sys
from typing import Dict, List, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import threading

logger = logging.getLogger(__name__)


class BuildOrchestrator:
    """Orchestrates component builds with dependency management"""
    
    def __init__(self, k8s_manager, components_config: Dict, release_config: Dict, 
                 interactive: bool = True, stream_logs: bool = False):
        """
        Initialize the Build Orchestrator
        
        Args:
            k8s_manager: KubernetesJobManager instance
            components_config: Component configurations
            release_config: Release configuration
            interactive: Whether to prompt user for retry/skip on failures
            stream_logs: Whether to stream logs in real-time during builds
        """
        self.k8s_manager = k8s_manager
        self.components_config = components_config
        self.release_config = release_config
        self.namespace = release_config['namespace']
        self.interactive = interactive
        self.stream_logs = stream_logs
        
        # Build status tracking
        self.completed = set()  # Successfully completed components
        self.failed = set()  # Failed components
        self.skipped = set()  # Skipped components
        self.in_progress = set()  # Currently building components
        self.lock = threading.RLock()  # Thread safety for shared state (RLock allows re-entrance)
        
    def get_dependencies(self, component: str) -> List[str]:
        """Get dependencies for a component"""
        return self.components_config[component].get('dependencies', [])
    
    def dependencies_met(self, component: str, components_to_build: List[str]) -> bool:
        """
        Check if all dependencies for a component have been met
        
        Args:
            component: Component name
            components_to_build: List of components that are part of this build
            
        Returns:
            True if all dependencies are completed or not in build list
        """
        dependencies = self.get_dependencies(component)
        with self.lock:
            for dep in dependencies:
                # Dependency must be completed if it's in the build list
                if dep in components_to_build and dep not in self.completed:
                    return False
            return True
    
    def has_failed_dependencies(self, component: str, components_to_build: List[str]) -> bool:
        """Check if component has any failed dependencies"""
        dependencies = self.get_dependencies(component)
        with self.lock:
            for dep in dependencies:
                if dep in components_to_build and (dep in self.failed or dep in self.skipped):
                    return True
            return False
    
    def print_build_plan(self, components: List[str]):
        """Print the build plan showing dependencies and build order"""
        logger.info("=" * 80)
        logger.info("BUILD PLAN")
        logger.info("=" * 80)
        
        logger.info("\nComponents to build:")
        for component in sorted(components):
            deps = self.get_dependencies(component)
            desc = self.components_config[component].get('description', '')
            if deps:
                logger.info(f"  • {component}: {desc}")
                logger.info(f"    Dependencies: {', '.join(deps)}")
            else:
                logger.info(f"  • {component}: {desc} (no dependencies)")
        
        logger.info("\nBuild strategy:")
        logger.info("  - Components will be built as dependencies are met")
        logger.info("  - Multiple components can build in parallel when dependencies allow")
        logger.info("  - Each component builds in its own Kubernetes job")
        logger.info("=" * 80)
    
    def prompt_user_action(self, component: str) -> str:
        """
        Prompt user to choose action on build failure
        
        Returns:
            Action: 'retry', 'skip', or 'abort'
        """
        if not self.interactive:
            return 'skip'
        
        while True:
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"Build failed for component: {component}")
            logger.info("=" * 80)
            logger.info("Choose an action:")
            logger.info("  [r] Retry - Retry building this component")
            logger.info("  [s] Skip  - Skip this component and continue with others")
            logger.info("  [a] Abort - Abort the entire build pipeline")
            logger.info("=" * 80)
            
            try:
                choice = input("Enter your choice (r/s/a): ").strip().lower()
                if choice in ['r', 'retry']:
                    return 'retry'
                elif choice in ['s', 'skip']:
                    return 'skip'
                elif choice in ['a', 'abort']:
                    return 'abort'
                else:
                    logger.warning(f"Invalid choice: {choice}. Please enter 'r', 's', or 'a'.")
            except (EOFError, KeyboardInterrupt):
                logger.info("\nReceived interrupt, aborting build...")
                return 'abort'
    
    def build_component(self, component: str, total_components: int, component_num: int) -> bool:
        """
        Build a single component with retry/skip functionality
        
        Args:
            component: Component name
            total_components: Total number of components being built
            component_num: Current component number (for display)
            
        Returns:
            True if build succeeded, False otherwise
        """
        config = self.components_config[component]
        job_name = f"{component}-build"
        
        attempt = 0
        
        while True:
            attempt += 1
            
            # Print component header
            logger.info("\n")
            logger.info("*" * 80)
            logger.info("*" * 80)
            logger.info(f"**  COMPONENT: {component.upper()} ({component_num}/{total_components})")
            if attempt > 1:
                logger.info(f"**  ATTEMPT: {attempt}")
            logger.info("*" * 80)
            logger.info(f"**  Description: {config.get('description', 'N/A')}")
            logger.info(f"**  Gradle Tasks: {', '.join(config['gradle_tasks'])}")
            deps = self.get_dependencies(component)
            logger.info(f"**  Dependencies: {', '.join(deps) if deps else 'None'}")
            logger.info("*" * 80)
            logger.info("*" * 80)
            logger.info("")
            
            logger.info(f"[{component}] Launching Kubernetes job: {job_name}")
            logger.info(f"[{component}] Namespace: {self.namespace}")
            logger.info(f"[{component}] Docker Image: {self.release_config['docker_image']}")
            logger.info(f"[{component}] Bigtop Branch: {self.release_config['bigtop_branch']}")
            logger.info("")
            
            # Launch the job
            if not self.k8s_manager.launch_job(component, config, self.release_config):
                logger.error(f"[{component}] ✗ Failed to launch job")
                
                action = self.prompt_user_action(component)
                if action == 'retry':
                    logger.info(f"[{component}] Retrying build...")
                    continue
                elif action == 'skip':
                    with self.lock:
                        self.skipped.add(component)
                    logger.warning(f"[{component}] ⊗ Skipped")
                    return False
                else:  # abort
                    with self.lock:
                        self.failed.add(component)
                    raise KeyboardInterrupt("Build aborted by user")
            
            logger.info(f"[{component}] ✓ Job launched successfully")
            logger.info(f"[{component}] Waiting for build to complete...")
            logger.info("")
            
            # Wait for completion
            success = self.k8s_manager.wait_for_job(
                job_name, 
                self.namespace,
                timeout=3600,  # 1 hour timeout per component
                check_interval=30,
                component_prefix=f"[{component}]",
                stream_logs=self.stream_logs
            )
            
            if success:
                with self.lock:
                    self.completed.add(component)
                    self.in_progress.discard(component)
                logger.info("")
                logger.info(f"[{component}] ✓ BUILD SUCCESSFUL")
                logger.info(f"\n{'*' * 80}")
                logger.info(f"[{component}] END OF COMPONENT STAGE - SUCCESS")
                logger.info(f"{'*' * 80}\n")
                return True
            else:
                # Build failed
                logger.info("")
                logger.info(f"[{component}] ✗ BUILD FAILED")
                
                # Prompt user for action
                action = self.prompt_user_action(component)
                if action == 'retry':
                    logger.info(f"[{component}] Retrying build...")
                    continue
                elif action == 'skip':
                    with self.lock:
                        self.skipped.add(component)
                        self.in_progress.discard(component)
                    logger.warning(f"[{component}] ⊗ Skipped by user")
                    logger.info(f"\n{'*' * 80}")
                    logger.info(f"[{component}] END OF COMPONENT STAGE - SKIPPED")
                    logger.info(f"{'*' * 80}\n")
                    return False
                else:  # abort
                    with self.lock:
                        self.failed.add(component)
                        self.in_progress.discard(component)
                    logger.error(f"[{component}] ✗ Failed")
                    logger.info(f"\n{'*' * 80}")
                    logger.info(f"[{component}] END OF COMPONENT STAGE - FAILED")
                    logger.info(f"{'*' * 80}\n")
                    raise KeyboardInterrupt("Build aborted by user")
    
    def build_all(self, components: List[str]) -> bool:
        """
        Build all specified components with dynamic dependency-based triggering
        
        Args:
            components: List of component names to build
            
        Returns:
            True if at least one component succeeded and no hard failures
        """
        # Validate components
        valid_components = [c for c in components if c in self.components_config]
        if not valid_components:
            logger.error("No valid components to build")
            return False
        
        # Print build plan
        self.print_build_plan(valid_components)
        
        total_components = len(valid_components)
        remaining = set(valid_components)
        component_counter = 0
        
        # Use ThreadPoolExecutor for parallel builds
        max_parallel = min(total_components, 5)  # Max 5 parallel builds
        
        logger.info(f"\n{'=' * 80}")
        logger.info("STARTING DYNAMIC BUILD EXECUTION")
        logger.info(f"Max parallel builds: {max_parallel}")
        logger.info(f"Initial remaining: {remaining}")
        logger.info(f"{'=' * 80}\n")
        
        try:
            with ThreadPoolExecutor(max_workers=max_parallel) as executor:
                futures = {}  # Future -> component mapping
                
                logger.info("Entered main build loop...")
                
                while remaining or futures:
                    logger.info(f"Status check: {len(remaining)} remaining, {len(futures)} building, {len(self.completed)} completed")
                    logger.info(f"Remaining components: {remaining}")
                    logger.info(f"In progress: {self.in_progress}")
                    
                    # Find components ready to build
                    ready = []
                    with self.lock:
                        for component in list(remaining):
                            logger.debug(f"Checking {component}...")
                            
                            # Skip if already building
                            if component in self.in_progress:
                                logger.debug(f"  {component} already in progress, skipping")
                                continue
                            
                            # Check for failed dependencies
                            if self.has_failed_dependencies(component, valid_components):
                                deps = self.get_dependencies(component)
                                failed_deps = [d for d in deps if d in valid_components and 
                                             (d in self.failed or d in self.skipped)]
                                logger.warning(f"⊗ Skipping {component}: dependencies failed: {', '.join(failed_deps)}")
                                self.skipped.add(component)
                                remaining.discard(component)
                                continue
                            
                            # Check if dependencies met
                            deps_met = self.dependencies_met(component, valid_components)
                            logger.debug(f"  {component} dependencies met: {deps_met}")
                            if deps_met:
                                ready.append(component)
                    
                    # Submit new builds
                    logger.info(f"Found {len(ready)} components ready to build: {ready}")
                    
                    for component in ready:
                        with self.lock:
                            self.in_progress.add(component)
                            component_counter += 1
                        remaining.discard(component)
                        
                        logger.info(f"[{component}] Dependencies met, scheduling build...")
                        try:
                            future = executor.submit(self.build_component, component, total_components, component_counter)
                            futures[future] = component
                            logger.info(f"[{component}] Build submitted successfully")
                        except Exception as e:
                            logger.error(f"[{component}] Failed to submit build: {e}", exc_info=True)
                            with self.lock:
                                self.failed.add(component)
                                self.in_progress.discard(component)
                    
                    # Wait for at least one to complete
                    if futures:
                        # Check for completed futures
                        done_futures = [f for f in futures if f.done()]
                        
                        if not done_futures:
                            # No futures done yet, wait a bit
                            if not ready:
                                # Only wait if we didn't just submit new ones
                                time.sleep(2)
                            continue
                        
                        # Process completed futures
                        for future in done_futures:
                            component = futures[future]
                            try:
                                success = future.result()
                                # Status already updated in build_component
                            except KeyboardInterrupt:
                                logger.error("\n\nBuild aborted by user")
                                # Cancel remaining futures
                                for f in futures:
                                    if not f.done():
                                        f.cancel()
                                return False
                            except Exception as e:
                                logger.error(f"[{component}] ✗ Unexpected error: {e}", exc_info=True)
                                with self.lock:
                                    self.failed.add(component)
                                    self.in_progress.discard(component)
                            
                            # Remove from futures
                            del futures[future]
                    
                    # Check if we're stuck (nothing ready, nothing running, but have remaining)
                    if not ready and not futures and remaining:
                        with self.lock:
                            logger.error("\n" + "=" * 80)
                            logger.error("BUILD STUCK - Cannot proceed")
                            logger.error("=" * 80)
                            logger.error(f"Remaining components: {', '.join(remaining)}")
                            for component in remaining:
                                deps = self.get_dependencies(component)
                                unmet = [d for d in deps if d in valid_components and d not in self.completed]
                                if unmet:
                                    logger.error(f"  {component} waiting for: {', '.join(unmet)}")
                                self.skipped.add(component)
                        break
                    
                    # Safety sleep to prevent busy-waiting
                    if not ready and not futures:
                        logger.debug("No ready components and no active builds, waiting...")
                        time.sleep(2)
                    
        except KeyboardInterrupt:
            logger.error("\n\nBuild aborted by user")
            return False
        except Exception as e:
            logger.error(f"\n\nUnexpected error in build orchestration: {e}", exc_info=True)
            return False
        
        # Print final results
        logger.info("\n" + "=" * 80)
        logger.info("BUILD EXECUTION COMPLETE")
        logger.info("=" * 80)
        
        with self.lock:
            if self.completed:
                logger.info(f"✓ Completed ({len(self.completed)}): {', '.join(sorted(self.completed))}")
            if self.skipped:
                logger.warning(f"⊗ Skipped ({len(self.skipped)}): {', '.join(sorted(self.skipped))}")
            if self.failed:
                logger.error(f"✗ Failed ({len(self.failed)}): {', '.join(sorted(self.failed))}")
        
        logger.info("=" * 80)
        
        # Success if at least one component was built and no hard failures
        return len(self.completed) > 0 and len(self.failed) == 0
    
    def get_build_summary(self) -> Dict:
        """Get a summary of the build status"""
        with self.lock:
            return {
                'completed': sorted(list(self.completed)),
                'failed': sorted(list(self.failed)),
                'skipped': sorted(list(self.skipped)),
                'in_progress': sorted(list(self.in_progress)),
                'total_completed': len(self.completed),
                'total_failed': len(self.failed),
                'total_skipped': len(self.skipped),
                'success': len(self.failed) == 0 and len(self.completed) > 0
            }
