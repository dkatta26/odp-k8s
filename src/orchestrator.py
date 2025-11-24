"""
Build Orchestrator
Manages dependency resolution and parallel build execution for ODP components
"""

import logging
import time
import sys
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)


class BuildOrchestrator:
    """Orchestrates component builds with dependency management"""
    
    def __init__(self, k8s_manager, components_config: Dict, release_config: Dict, interactive: bool = True, stream_logs: bool = False):
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
        
        self.completed = set()  # Successfully completed components
        self.failed = set()  # Failed components
        self.skipped = set()  # Skipped components
        self.in_progress = set()  # Currently building components
        self.lock = threading.Lock()  # Thread safety for shared state
        self.component_stage_counter = 0  # Counter for component stages
        
    def get_all_components(self) -> List[str]:
        """Get list of all available components"""
        return list(self.components_config.keys())
    
    def validate_components(self, components: List[str]) -> List[str]:
        """
        Validate that requested components exist
        
        Args:
            components: List of component names
            
        Returns:
            List of valid component names
        """
        all_components = self.get_all_components()
        valid = []
        
        for component in components:
            if component in all_components:
                valid.append(component)
            else:
                logger.warning(f"Unknown component '{component}', skipping")
        
        return valid
    
    def get_dependencies(self, component: str) -> List[str]:
        """
        Get dependencies for a component
        
        Args:
            component: Component name
            
        Returns:
            List of dependency component names
        """
        return self.components_config[component].get('dependencies', [])
    
    def dependencies_met(self, component: str, components_to_build: List[str]) -> bool:
        """
        Check if all dependencies for a component have been met
        
        Args:
            component: Component name
            components_to_build: List of components that are part of this build
            
        Returns:
            True if all dependencies are completed or not in build list, False otherwise
        """
        dependencies = self.get_dependencies(component)
        with self.lock:
            for dep in dependencies:
                # Dependency must be completed if it's in the build list
                if dep in components_to_build and dep not in self.completed:
                    return False
            return True
    
    def get_build_order(self, components: List[str]) -> List[List[str]]:
        """
        Calculate build order based on dependencies
        Returns a list of stages, where each stage contains components that can be built in parallel
        
        Args:
            components: List of component names to build
            
        Returns:
            List of build stages, each stage is a list of components that can be built in parallel
        """
        remaining = set(components)
        completed = set()
        build_order = []
        
        while remaining:
            # Find components whose dependencies are all completed
            ready = [
                comp for comp in remaining
                if all(dep in completed or dep not in components 
                       for dep in self.get_dependencies(comp))
            ]
            
            if not ready:
                # Circular dependency or missing dependency
                logger.error(f"Cannot resolve dependencies for: {', '.join(remaining)}")
                logger.error(f"Completed: {', '.join(completed)}")
                for comp in remaining:
                    deps = self.get_dependencies(comp)
                    unmet = [d for d in deps if d not in completed and d in components]
                    if unmet:
                        logger.error(f"  {comp} depends on: {', '.join(unmet)}")
                raise ValueError("Circular dependency or missing dependency detected")
            
            # Sort components by name for consistent ordering
            ready.sort()
            build_order.append(ready)
            completed.update(ready)
            remaining -= set(ready)
        
        return build_order
    
    def print_build_plan(self, components: List[str]):
        """
        Print the build plan showing dependencies and build order
        
        Args:
            components: List of component names to build
        """
        logger.info("=" * 80)
        logger.info("BUILD PLAN")
        logger.info("=" * 80)
        
        logger.info("\nComponents to build:")
        for component in components:
            deps = self.get_dependencies(component)
            desc = self.components_config[component].get('description', '')
            if deps:
                logger.info(f"  • {component}: {desc}")
                logger.info(f"    Dependencies: {', '.join(deps)}")
            else:
                logger.info(f"  • {component}: {desc} (no dependencies)")
        
        logger.info("\nBuild strategy:")
        logger.info("  - Components will be built dynamically as dependencies are met")
        logger.info("  - Multiple components can build in parallel when dependencies allow")
        logger.info("  - Each component gets its own stage")
        logger.info("=" * 80)
    
    def prompt_user_action(self, component: str) -> str:
        """
        Prompt user to choose action on build failure
        
        Args:
            component: Component name that failed
            
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
    
    def print_component_stage_header(self, component: str, stage_label: str = None):
        """
        Print a clear stage header for a component
        
        Args:
            component: Component name
            stage_label: Optional stage label (e.g., "Stage 1 of 4")
        """
        with self.lock:
            self.component_stage_counter += 1
            stage_num = self.component_stage_counter
        
        config = self.components_config[component]
        deps = self.get_dependencies(component)
        
        logger.info("\n")
        logger.info("*" * 80)
        logger.info("*" * 80)
        if stage_label:
            logger.info(f"**  {stage_label}")
        logger.info(f"**  COMPONENT STAGE: {component.upper()}")
        logger.info("*" * 80)
        logger.info(f"**  Description: {config.get('description', 'N/A')}")
        logger.info(f"**  Gradle Tasks: {', '.join(config['gradle_tasks'])}")
        logger.info(f"**  Dependencies: {', '.join(deps) if deps else 'None'}")
        logger.info("*" * 80)
        logger.info("*" * 80)
        logger.info("")
    
    def build_component(self, component: str, stage_label: str = None) -> bool:
        """
        Build a single component with retry/skip functionality
        
        Args:
            component: Component name
            stage_label: Optional stage label for logging
            
        Returns:
            True if build succeeded, False otherwise
        """
        config = self.components_config[component]
        job_name = f"{component}-build"
        
        max_auto_retries = 0  # No auto retries, only manual
        attempt = 0
        
        while True:
            attempt += 1
            
            # Print component stage header
            if attempt == 1:
                self.print_component_stage_header(component, stage_label)
            else:
                logger.info(f"\n{'=' * 80}")
                logger.info(f"RETRY ATTEMPT {attempt} for {component}")
                logger.info(f"{'=' * 80}\n")
            
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
                    logger.info(f"\n{'*' * 80}")
                    logger.info(f"[{component}] END OF COMPONENT STAGE")
                    logger.info(f"{'*' * 80}\n")
                    return False
                else:  # abort
                    with self.lock:
                        self.failed.add(component)
                    raise KeyboardInterrupt("Build aborted by user")
            
            logger.info(f"[{component}] ✓ Job launched successfully")
            logger.info(f"[{component}] Waiting for build to complete...")
            logger.info("")
            
            # Stream logs if enabled
            if self.stream_logs:
                logger.info(f"[{component}] " + "=" * 70)
                logger.info(f"[{component}] BUILD LOGS (streaming)")
                logger.info(f"[{component}] " + "=" * 70)
                logger.info("")
            
            # Wait for completion with status updates
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
                
                if attempt <= max_auto_retries:
                    logger.warning(f"[{component}] Retrying after 5 seconds...")
                    time.sleep(5)
                    continue
                
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
    
    def build_component_wrapper(self, component: str, total_components: int) -> bool:
        """
        Wrapper around build_component that manages stage numbering
        
        Args:
            component: Component name
            total_components: Total number of components to build
            
        Returns:
            True if build succeeded, False otherwise
        """
        with self.lock:
            self.component_stage_counter += 1
            stage_num = self.component_stage_counter
        
        stage_label = f"Component {stage_num} of {total_components}"
        
        try:
            return self.build_component(component, stage_label)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"[{component}] ✗ Unexpected error: {e}", exc_info=True)
            with self.lock:
                self.failed.add(component)
                self.in_progress.discard(component)
            return False
    
    def build_all(self, components: List[str]) -> bool:
        """
        Build all specified components with dynamic dependency-based triggering
        Components start building as soon as their dependencies are met
        
        Args:
            components: List of component names to build
            
        Returns:
            True if at least one component succeeded and no hard failures, False otherwise
        """
        # Validate components
        valid_components = self.validate_components(components)
        if not valid_components:
            logger.error("No valid components to build")
            return False
        
        # Print build plan
        self.print_build_plan(valid_components)
        
        total_components = len(valid_components)
        remaining = set(valid_components)
        
        # Use ThreadPoolExecutor to manage parallel builds
        max_parallel = min(len(valid_components), 10)  # Max 10 parallel builds
        
        logger.info(f"\n{'=' * 80}")
        logger.info("STARTING DYNAMIC BUILD EXECUTION")
        logger.info(f"{'=' * 80}\n")
        
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {}  # Future -> component mapping
            
            try:
                while remaining or futures:
                    # Check which components are ready to build
                    ready_to_build = []
                    with self.lock:
                        for component in list(remaining):
                            # Skip if already in progress or dependencies not met
                            if component in self.in_progress:
                                continue
                            
                            if self.dependencies_met(component, valid_components):
                                # Check if dependencies failed
                                deps = self.get_dependencies(component)
                                failed_deps = [d for d in deps if d in valid_components and d in self.failed]
                                if failed_deps:
                                    logger.warning(f"⊗ Skipping {component}: dependencies failed: {', '.join(failed_deps)}")
                                    self.skipped.add(component)
                                    remaining.discard(component)
                                    continue
                                
                                ready_to_build.append(component)
                    
                    # Submit new builds for ready components
                    for component in ready_to_build:
                        with self.lock:
                            self.in_progress.add(component)
                        remaining.discard(component)
                        
                        logger.info(f"[{component}] Dependencies met, starting build...")
                        future = executor.submit(self.build_component_wrapper, component, total_components)
                        futures[future] = component
                    
                    # Check for completed builds
                    if futures:
                        # Wait for at least one build to complete
                        done_futures = []
                        for future in list(futures.keys()):
                            if future.done():
                                done_futures.append(future)
                        
                        if not done_futures and not ready_to_build:
                            # Wait a bit for something to complete
                            time.sleep(1)
                            continue
                        
                        for future in done_futures:
                            component = futures[future]
                            try:
                                success = future.result()
                                # Success/failure already recorded in build_component_wrapper
                            except KeyboardInterrupt:
                                logger.error("\n\nBuild aborted by user")
                                # Cancel remaining futures
                                for f in futures:
                                    f.cancel()
                                raise
                            except Exception as e:
                                logger.error(f"[{component}] ✗ Unexpected error: {e}", exc_info=True)
                                with self.lock:
                                    self.failed.add(component)
                                    self.in_progress.discard(component)
                            
                            del futures[future]
                    
                    # If nothing is ready and nothing is running, we're stuck
                    if not ready_to_build and not futures and remaining:
                        # Remaining components have unmet dependencies
                        with self.lock:
                            for component in remaining:
                                deps = self.get_dependencies(component)
                                unmet = [d for d in deps if d in valid_components and d not in self.completed]
                                if unmet:
                                    logger.warning(f"⊗ Skipping {component}: unmet dependencies: {', '.join(unmet)}")
                                    self.skipped.add(component)
                        break
                        
            except KeyboardInterrupt:
                logger.error("\n\nBuild aborted by user")
                return False
        
        # All builds attempted
        logger.info("\n" + "=" * 80)
        logger.info("BUILD COMPLETE")
        logger.info("=" * 80)
        if self.completed:
            logger.info(f"✓ Successfully built ({len(self.completed)}): {', '.join(sorted(self.completed))}")
        if self.skipped:
            logger.warning(f"⊗ Skipped ({len(self.skipped)}): {', '.join(sorted(self.skipped))}")
        if self.failed:
            logger.error(f"✗ Failed ({len(self.failed)}): {', '.join(sorted(self.failed))}")
        logger.info("=" * 80)
        
        # Success if at least one component was built and no hard failures
        return len(self.completed) > 0 and len(self.failed) == 0
    
    def get_build_summary(self) -> Dict:
        """
        Get a summary of the build status
        
        Returns:
            Dictionary with build summary
        """
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

