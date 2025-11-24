"""
Build Orchestrator
Manages dependency resolution and sequential build execution for ODP components
"""

import logging
import time
import sys
from typing import Dict, List, Set
import threading

logger = logging.getLogger(__name__)


class BuildOrchestrator:
    """Orchestrates component builds with dependency management"""
    
    def __init__(self, k8s_manager, components_config: Dict, release_config: Dict, interactive: bool = True):
        """
        Initialize the Build Orchestrator
        
        Args:
            k8s_manager: KubernetesJobManager instance
            components_config: Component configurations
            release_config: Release configuration
            interactive: Whether to prompt user for retry/skip on failures
        """
        self.k8s_manager = k8s_manager
        self.components_config = components_config
        self.release_config = release_config
        self.namespace = release_config['namespace']
        self.interactive = interactive
        
        self.completed = set()  # Successfully completed components
        self.failed = set()  # Failed components
        self.skipped = set()  # Skipped components
        self.in_progress = set()  # Currently building components
        self.lock = threading.Lock()  # Thread safety for shared state
        
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
    
    def get_build_order(self, components: List[str]) -> List[str]:
        """
        Calculate build order based on dependencies
        Returns a list where each component is built sequentially
        
        Args:
            components: List of component names to build
            
        Returns:
            List of components in build order
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
            build_order.extend(ready)
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
        
        logger.info("\nBuild order (sequential):")
        build_order = self.get_build_order(components)
        for i, component in enumerate(build_order, 1):
            logger.info(f"  Stage {i}: {component}")
        
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
    
    def build_component(self, component: str) -> bool:
        """
        Build a single component with retry/skip functionality
        
        Args:
            component: Component name
            
        Returns:
            True if build succeeded, False otherwise
        """
        config = self.components_config[component]
        job_name = f"{component}-build"
        
        max_auto_retries = 0  # No auto retries, only manual
        attempt = 0
        
        while True:
            attempt += 1
            attempt_suffix = f" (Attempt {attempt})" if attempt > 1 else ""
            
            logger.info("=" * 80)
            logger.info(f"BUILDING: {component}{attempt_suffix}")
            logger.info("=" * 80)
            logger.info(f"Description: {config.get('description', 'N/A')}")
            logger.info(f"Gradle tasks: {', '.join(config['gradle_tasks'])}")
            logger.info(f"Dependencies: {', '.join(self.get_dependencies(component)) or 'None'}")
            logger.info("=" * 80)
            
            # Launch the job
            if not self.k8s_manager.launch_job(component, config, self.release_config):
                logger.error(f"✗ Failed to launch job for {component}")
                
                action = self.prompt_user_action(component)
                if action == 'retry':
                    logger.info(f"Retrying build for {component}...")
                    continue
                elif action == 'skip':
                    with self.lock:
                        self.skipped.add(component)
                    logger.warning(f"⊗ Skipped {component}")
                    return False
                else:  # abort
                    with self.lock:
                        self.failed.add(component)
                    raise KeyboardInterrupt("Build aborted by user")
            
            # Wait for completion with status updates
            success = self.k8s_manager.wait_for_job(
                job_name, 
                self.namespace,
                timeout=3600,  # 1 hour timeout per component
                check_interval=30
            )
            
            if success:
                with self.lock:
                    self.completed.add(component)
                    self.in_progress.discard(component)
                logger.info(f"✓ Successfully built {component}")
                return True
            else:
                # Build failed
                if attempt <= max_auto_retries:
                    logger.warning(f"Build failed for {component}, retrying...")
                    time.sleep(5)  # Brief pause before retry
                    continue
                
                # Prompt user for action
                action = self.prompt_user_action(component)
                if action == 'retry':
                    logger.info(f"Retrying build for {component}...")
                    continue
                elif action == 'skip':
                    with self.lock:
                        self.skipped.add(component)
                        self.in_progress.discard(component)
                    logger.warning(f"⊗ Skipped {component}")
                    return False
                else:  # abort
                    with self.lock:
                        self.failed.add(component)
                        self.in_progress.discard(component)
                    logger.error(f"✗ Failed to build {component}")
                    raise KeyboardInterrupt("Build aborted by user")
    
    def build_all(self, components: List[str]) -> bool:
        """
        Build all specified components in the correct order, sequentially
        Components with unmet dependencies will be skipped automatically
        
        Args:
            components: List of component names to build
            
        Returns:
            True if all builds succeeded, False if any failed
        """
        # Validate components
        valid_components = self.validate_components(components)
        if not valid_components:
            logger.error("No valid components to build")
            return False
        
        # Print build plan
        self.print_build_plan(valid_components)
        
        # Get build order
        try:
            build_order = self.get_build_order(valid_components)
        except ValueError as e:
            logger.error(f"Error calculating build order: {e}")
            return False
        
        # Build each component sequentially
        total_components = len(build_order)
        
        for stage_num, component in enumerate(build_order, 1):
            logger.info(f"\n{'#' * 80}")
            logger.info(f"# STAGE {stage_num} of {total_components}: {component}")
            logger.info(f"{'#' * 80}\n")
            
            # Check if dependencies are met
            if not self.dependencies_met(component, valid_components):
                unmet_deps = [dep for dep in self.get_dependencies(component) 
                             if dep in valid_components and dep not in self.completed]
                logger.warning(f"⊗ Skipping {component}: unmet dependencies: {', '.join(unmet_deps)}")
                with self.lock:
                    self.skipped.add(component)
                continue
            
            # Build the component
            try:
                with self.lock:
                    self.in_progress.add(component)
                
                success = self.build_component(component)
                
                if not success:
                    # Component was skipped or failed, but we continue with remaining components
                    logger.info(f"\nContinuing with remaining components despite {component} failure/skip...")
                    
            except KeyboardInterrupt:
                logger.error("\n\nBuild aborted by user")
                return False
            except Exception as e:
                logger.error(f"\n✗ Unexpected error building {component}: {e}", exc_info=True)
                with self.lock:
                    self.failed.add(component)
                    self.in_progress.discard(component)
                return False
        
        # All stages attempted
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

