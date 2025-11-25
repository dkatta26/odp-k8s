"""
Scripted Jenkinsfile Generator
Generates Jenkins scripted pipeline with dynamic dependency-based triggering
"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class ScriptedJenkinsfileGenerator:
    """Generates Jenkins scripted pipeline with dynamic build triggering"""
    
    def __init__(self, components_config: Dict, release_config: Dict):
        """
        Initialize the Scripted Jenkinsfile Generator
        
        Args:
            components_config: Component configurations
            release_config: Release configuration
        """
        self.components_config = components_config
        self.release_config = release_config
    
    def get_dependencies(self, component: str) -> List[str]:
        """Get dependencies for a component"""
        return self.components_config[component].get('dependencies', [])
    
    def generate_scripted_jenkinsfile(self, components: List[str]) -> str:
        """
        Generate scripted Jenkinsfile with dynamic dependency triggering
        
        Args:
            components: List of components to build
            
        Returns:
            Complete scripted Jenkinsfile as string
        """
        
        # Build component info map for the script
        component_deps = {}
        for comp in components:
            deps = self.get_dependencies(comp)
            # Only include dependencies that are in the build list
            component_deps[comp] = [d for d in deps if d in components]
        
        jenkinsfile = f"""// Dynamic Build Pipeline with Dependency-Based Triggering
// Generated automatically - each component starts as soon as its dependencies complete

node('k8s-build-agent') {{
    
    // Environment setup
    withCredentials([file(credentialsId: 'odp-hz-kubeconfig', variable: 'KUBECONFIG')]) {{
        
        // Component status tracking
        def completed = [] as Set
        def failed = [] as Set
        def skipped = [] as Set
        def inProgress = [] as Set
        def remaining = {repr(components)} as Set
        
        // Component dependencies map
        def componentDeps = {repr(component_deps)}
        
        // Lock for thread-safe updates
        def statusLock = new Object()
        
        // Function to check if component's dependencies are met
        def dependenciesMet = {{ component ->
            def deps = componentDeps[component]
            if (deps == null || deps.isEmpty()) {{
                return true
            }}
            synchronized(statusLock) {{
                return deps.every {{ dep -> completed.contains(dep) }}
            }}
        }}
        
        // Function to check if component has failed dependencies
        def hasFailedDependencies = {{ component ->
            def deps = componentDeps[component]
            if (deps == null || deps.isEmpty()) {{
                return false
            }}
            synchronized(statusLock) {{
                return deps.any {{ dep -> failed.contains(dep) }}
            }}
        }}
        
        // Function to build a single component
        def buildComponent = {{ component ->
            def stageName = component.toUpperCase()
            
            stage(stageName) {{
                try {{
                    echo '********************************************************************************'
                    echo "**  COMPONENT STAGE: ${{stageName}}"
                    echo '********************************************************************************'
                    
                    def componentConfig = {repr(self.get_component_configs(components))}[component]
                    echo "**  Description: ${{componentConfig.description}}"
                    echo "**  Build Command: ${{componentConfig.build_command}}"
                    
                    def deps = componentDeps[component]
                    if (deps && !deps.isEmpty()) {{
                        echo "**  Dependencies: ${{deps.join(', ')}}"
                    }} else {{
                        echo "**  Dependencies: None"
                    }}
                    
                    echo '********************************************************************************'
                    echo ''
                    
                    // Execute the build
                    sh \"\"\"
                        python3 src/main.py \\
                            --release {self.release_config.get('release_name', 'RELEASE')} \\
                            --components ${{component}} \\
                            --bigtop-branch {self.release_config['bigtop_branch']} \\
                            --docker-image {self.release_config['docker_image']} \\
                            --kubeconfig ${{KUBECONFIG}} \\
                            --non-interactive
                    \"\"\"
                    
                    // Mark as completed
                    synchronized(statusLock) {{
                        completed.add(component)
                        inProgress.remove(component)
                    }}
                    
                    echo ''
                    echo "[${{component}}] ✓ BUILD SUCCESSFUL"
                    echo '********************************************************************************'
                    echo "[${{component}}] END OF COMPONENT STAGE - SUCCESS"
                    echo '********************************************************************************'
                    echo ''
                    
                }} catch (Exception e) {{
                    // Mark as failed
                    synchronized(statusLock) {{
                        failed.add(component)
                        inProgress.remove(component)
                    }}
                    
                    echo ''
                    echo "[${{component}}] ✗ BUILD FAILED: ${{e.message}}"
                    echo '********************************************************************************'
                    echo "[${{component}}] END OF COMPONENT STAGE - FAILED"
                    echo '********************************************************************************'
                    echo ''
                    
                    // Don't throw - let other components continue
                }}
            }}
        }}
        
        // Main build loop - dynamic triggering
        echo '=' * 80
        echo 'STARTING DYNAMIC BUILD EXECUTION'
        echo '=' * 80
        echo ''
        
        def futures = [:]
        
        while (!remaining.isEmpty() || !inProgress.isEmpty()) {{
            
            // Find components ready to build
            def readyToBuild = []
            synchronized(statusLock) {{
                remaining.each {{ component ->
                    if (!inProgress.contains(component)) {{
                        if (hasFailedDependencies(component)) {{
                            def deps = componentDeps[component]
                            def failedDeps = deps.findAll {{ failed.contains(it) }}
                            echo "⊗ Skipping ${{component}}: dependencies failed: ${{failedDeps.join(', ')}}"
                            skipped.add(component)
                            remaining.remove(component)
                        }} else if (dependenciesMet(component)) {{
                            readyToBuild.add(component)
                        }}
                    }}
                }}
            }}
            
            // Launch builds for ready components
            if (!readyToBuild.isEmpty()) {{
                readyToBuild.each {{ component ->
                    synchronized(statusLock) {{
                        inProgress.add(component)
                        remaining.remove(component)
                    }}
                    
                    echo "[${{component}}] Dependencies met, starting build..."
                    
                    // Launch build in parallel
                    def comp = component  // Capture variable for closure
                    futures[comp] = {{
                        buildComponent(comp)
                    }}
                }}
                
                // Execute all ready builds in parallel
                if (!futures.isEmpty()) {{
                    parallel futures
                    futures = [:]
                }}
            }}
            
            // Check if we're stuck (remaining components but none ready)
            if (readyToBuild.isEmpty() && !remaining.isEmpty() && inProgress.isEmpty()) {{
                synchronized(statusLock) {{
                    remaining.each {{ component ->
                        def deps = componentDeps[component]
                        def unmet = deps.findAll {{ !completed.contains(it) }}
                        echo "⊗ Skipping ${{component}}: unmet dependencies: ${{unmet.join(', ')}}"
                        skipped.add(component)
                    }}
                    remaining.clear()
                }}
                break
            }}
            
            // Small delay to prevent tight loop if nothing is ready yet
            if (readyToBuild.isEmpty() && !inProgress.isEmpty()) {{
                sleep(time: 1, unit: 'SECONDS')
            }}
        }}
        
        // Final summary
        echo ''
        echo '=' * 80
        echo 'BUILD COMPLETE'
        echo '=' * 80
        
        if (!completed.isEmpty()) {{
            echo "✓ Successfully built (${{completed.size()}}): ${{completed.join(', ')}}"
        }}
        if (!skipped.isEmpty()) {{
            echo "⊗ Skipped (${{skipped.size()}}): ${{skipped.join(', ')}}"
        }}
        if (!failed.isEmpty()) {{
            echo "✗ Failed (${{failed.size()}}): ${{failed.join(', ')}}"
        }}
        echo '=' * 80
        
        // Fail the build if any component failed
        if (!failed.isEmpty()) {{
            error("Build failed: ${{failed.join(', ')}}")
        }}
    }}
}}
"""
        
        return jenkinsfile
    
    def get_component_configs(self, components: List[str]) -> Dict:
        """
        Get simplified component configs for embedding in Jenkinsfile
        
        Args:
            components: List of components
            
        Returns:
            Dictionary of component configs
        """
        configs = {}
        for comp in components:
            config = self.components_config[comp]
            configs[comp] = {
                'description': config.get('description', 'N/A'),
                'build_command': config.get('build_command', '')
            }
        return configs
    
    def print_pipeline_info(self, components: List[str]):
        """
        Print information about the generated pipeline
        
        Args:
            components: List of components to build
        """
        logger.info("=" * 80)
        logger.info("SCRIPTED PIPELINE STRUCTURE")
        logger.info("=" * 80)
        logger.info("\nThis pipeline will:")
        logger.info("  ✓ Monitor dependencies dynamically")
        logger.info("  ✓ Start components immediately when dependencies are met")
        logger.info("  ✓ Run independent components in parallel")
        logger.info("  ✓ Continue building even if some components fail")
        logger.info("\nComponents to build:")
        
        for comp in sorted(components):
            deps = self.get_dependencies(comp)
            dep_str = f" (depends on: {', '.join(deps)})" if deps else " (no dependencies)"
            logger.info(f"  • {comp}{dep_str}")
        
        logger.info("\nDynamic behavior example:")
        logger.info("  t=0s:   Start zookeeper, hue (no dependencies)")
        logger.info("  t=400s: zookeeper completes")
        logger.info("          → Immediately start hadoop, kafka (deps met)")
        logger.info("          → hue still building in parallel")
        logger.info("  t=800s: hadoop, kafka complete")
        logger.info("  t=900s: hue completes (or fails without blocking others)")
        logger.info("=" * 80)

