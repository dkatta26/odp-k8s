"""
Build Orchestrator
Manages dependency resolution and parallel build execution for ODP components
"""

import logging
import time
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor, Future
import threading

logger = logging.getLogger(__name__)


class BuildOrchestrator:
    """Orchestrates component builds with dependency management"""
    
    def __init__(self, k8s_manager, components_config: Dict, release_config: Dict):
        """
        Initialize the Build Orchestrator
        
        Args:
            k8s_manager: KubernetesJobManager instance
            components_config: Component configurations
            release_config: Release configuration
        """
        self.k8s_manager = k8s_manager
        self.components_config = components_config
        self.release_config = release_config
        self.namespace = release_config['namespace']
        
        self.completed = set()  # Successfully completed components
        self.failed = set()  # Failed components
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
    
    def dependencies_met(self, component: str) -> bool:
        """
        Check if all dependencies for a component have been met
        
        Args:
            component: Component name
            
        Returns:
            True if all dependencies are completed, False otherwise
        """
        dependencies = self.get_dependencies(component)
        with self.lock:
            return all(dep in self.completed for dep in dependencies)
    
    def get_build_order(self, components: List[str]) -> List[List[str]]:
        """
        Calculate build order based on dependencies
        Returns a list of lists, where each inner list can be built in parallel
        
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
        
        logger.info("\nBuild order (by stage):")
        build_order = self.get_build_order(components)
        for i, stage in enumerate(build_order, 1):
            if len(stage) > 1:
                logger.info(f"  Stage {i} (parallel): {', '.join(stage)}")
            else:
                logger.info(f"  Stage {i}: {stage[0]}")
        
        logger.info("=" * 80)
    
    def build_component(self, component: str) -> bool:
        """
        Build a single component
        
        Args:
            component: Component name
            
        Returns:
            True if build succeeded, False otherwise
        """
        config = self.components_config[component]
        job_name = f"{component}-build"
        
        logger.info("=" * 80)
        logger.info(f"BUILDING: {component}")
        logger.info("=" * 80)
        logger.info(f"Description: {config.get('description', 'N/A')}")
        logger.info(f"Gradle tasks: {', '.join(config['gradle_tasks'])}")
        logger.info(f"Dependencies: {', '.join(self.get_dependencies(component)) or 'None'}")
        logger.info("=" * 80)
        
        # Launch the job
        if not self.k8s_manager.launch_job(component, config, self.release_config):
            logger.error(f"✗ Failed to launch job for {component}")
            with self.lock:
                self.failed.add(component)
            return False
        
        # Wait for completion with status updates
        success = self.k8s_manager.wait_for_job(
            job_name, 
            self.namespace,
            timeout=3600,  # 1 hour timeout per component
            check_interval=30
        )
        
        with self.lock:
            if success:
                self.completed.add(component)
                self.in_progress.discard(component)
                logger.info(f"✓ Successfully built {component}")
            else:
                self.failed.add(component)
                self.in_progress.discard(component)
                logger.error(f"✗ Failed to build {component}")
        
        return success
    
    def build_stage(self, stage: List[str]) -> bool:
        """
        Build all components in a stage (in parallel)
        
        Args:
            stage: List of component names to build in parallel
            
        Returns:
            True if all builds succeeded, False if any failed
        """
        if len(stage) == 1:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Starting build: {stage[0]}")
            logger.info(f"{'=' * 80}\n")
            return self.build_component(stage[0])
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Starting parallel builds: {', '.join(stage)}")
        logger.info(f"{'=' * 80}\n")
        
        with self.lock:
            self.in_progress.update(stage)
        
        # Build components in parallel
        with ThreadPoolExecutor(max_workers=len(stage)) as executor:
            futures = {executor.submit(self.build_component, comp): comp for comp in stage}
            results = {}
            
            for future in futures:
                component = futures[future]
                try:
                    results[component] = future.result()
                except Exception as e:
                    logger.error(f"Exception building {component}: {e}")
                    results[component] = False
                    with self.lock:
                        self.failed.add(component)
        
        # Check if all succeeded
        all_success = all(results.values())
        
        if all_success:
            logger.info(f"\n✓ All parallel builds completed: {', '.join(stage)}\n")
        else:
            failed_comps = [comp for comp, success in results.items() if not success]
            logger.error(f"\n✗ Some parallel builds failed: {', '.join(failed_comps)}\n")
        
        return all_success
    
    def build_all(self, components: List[str]) -> bool:
        """
        Build all specified components in the correct order
        
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
        
        # Build each stage
        for stage_num, stage in enumerate(build_order, 1):
            logger.info(f"\n{'#' * 80}")
            logger.info(f"# STAGE {stage_num} of {len(build_order)}")
            logger.info(f"{'#' * 80}\n")
            
            if not self.build_stage(stage):
                logger.error(f"\n✗ Stage {stage_num} failed. Aborting build.")
                return False
        
        # All stages completed
        logger.info("\n" + "=" * 80)
        logger.info("BUILD COMPLETE")
        logger.info("=" * 80)
        logger.info(f"✓ Successfully built: {', '.join(sorted(self.completed))}")
        if self.failed:
            logger.info(f"✗ Failed: {', '.join(sorted(self.failed))}")
        logger.info("=" * 80)
        
        return len(self.failed) == 0
    
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
                'in_progress': sorted(list(self.in_progress)),
                'total_completed': len(self.completed),
                'total_failed': len(self.failed),
                'success': len(self.failed) == 0
            }

