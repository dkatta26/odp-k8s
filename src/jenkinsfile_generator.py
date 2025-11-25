"""
Jenkinsfile Generator
Generates Jenkins declarative pipeline with separate stages for each component
"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class JenkinsfileGenerator:
    """Generates Jenkins declarative pipeline dynamically"""
    
    def __init__(self, components_config: Dict, release_config: Dict):
        """
        Initialize the Jenkinsfile Generator
        
        Args:
            components_config: Component configurations
            release_config: Release configuration
        """
        self.components_config = components_config
        self.release_config = release_config
    
    def get_dependencies(self, component: str) -> List[str]:
        """Get dependencies for a component"""
        return self.components_config[component].get('dependencies', [])
    
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
    
    def generate_component_stage(self, component: str, indent: int = 12) -> str:
        """
        Generate Jenkins stage definition for a single component
        
        Args:
            component: Component name
            indent: Indentation level (spaces)
            
        Returns:
            Jenkins stage definition as string
        """
        config = self.components_config[component]
        build_command = config.get('build_command', '')
        
        ind = ' ' * indent
        
        stage_def = f"{ind}stage('{component}') {{\n"
        stage_def += f"{ind}    steps {{\n"
        stage_def += f"{ind}        script {{\n"
        
        # Add component build details
        stage_def += f"{ind}            echo '{'*' * 80}'\n"
        stage_def += f"{ind}            echo '**  COMPONENT STAGE: {component.upper()}'\n"
        stage_def += f"{ind}            echo '{'*' * 80}'\n"
        stage_def += f"{ind}            echo '**  Description: {config.get('description', 'N/A')}'\n"
        stage_def += f"{ind}            echo '**  Build Command: {build_command}'\n"
        
        deps = self.get_dependencies(component)
        if deps:
            stage_def += f"{ind}            echo '**  Dependencies: {', '.join(deps)}'\n"
        else:
            stage_def += f"{ind}            echo '**  Dependencies: None'\n"
        
        stage_def += f"{ind}            echo '{'*' * 80}'\n"
        stage_def += f"{ind}            echo ''\n"
        
        # Execute the Python build command
        stage_def += f"{ind}            sh '''\n"
        stage_def += f"{ind}                python3 src/main.py \\\n"
        stage_def += f"{ind}                    --release {self.release_config.get('release_name', 'RELEASE')} \\\n"
        stage_def += f"{ind}                    --components {component} \\\n"
        stage_def += f"{ind}                    --bigtop-branch {self.release_config['bigtop_branch']} \\\n"
        stage_def += f"{ind}                    --docker-image {self.release_config['docker_image']} \\\n"
        stage_def += f"{ind}                    --kubeconfig ${{KUBECONFIG}} \\\n"
        stage_def += f"{ind}                    --non-interactive\n"
        stage_def += f"{ind}            '''\n"
        
        stage_def += f"{ind}        }}\n"
        stage_def += f"{ind}    }}\n"
        stage_def += f"{ind}}}\n"
        
        return stage_def
    
    def generate_parallel_stage(self, stage_num: int, components: List[str]) -> str:
        """
        Generate a parallel stage containing multiple component stages
        
        Args:
            stage_num: Stage number
            components: List of components to build in parallel
            
        Returns:
            Jenkins parallel stage definition as string
        """
        stage_def = f"        stage('🧱 DEPENDENCY-STAGE-{stage_num}') {{\n"
        
        if len(components) > 1:
            stage_def += f"            parallel {{\n"
            
            for component in components:
                stage_def += self.generate_component_stage(component, indent=16)
            
            stage_def += f"            }}\n"
        else:
            # Single component, no parallel needed
            stage_def += f"            steps {{\n"
            stage_def += f"                script {{\n"
            component = components[0]
            config = self.components_config[component]
            build_command = config.get('build_command', '')
            
            stage_def += f"                    echo '{'*' * 80}'\n"
            stage_def += f"                    echo '**  COMPONENT STAGE: {component.upper()}'\n"
            stage_def += f"                    echo '{'*' * 80}'\n"
            stage_def += f"                    echo '**  Description: {config.get('description', 'N/A')}'\n"
            stage_def += f"                    echo '**  Build Command: {build_command}'\n"
            
            deps = self.get_dependencies(component)
            if deps:
                stage_def += f"                    echo '**  Dependencies: {', '.join(deps)}'\n"
            else:
                stage_def += f"                    echo '**  Dependencies: None'\n"
            
            stage_def += f"                    echo '{'*' * 80}'\n"
            stage_def += f"                    echo ''\n"
            
            stage_def += f"                    sh '''\n"
            stage_def += f"                        python3 src/main.py \\\n"
            stage_def += f"                            --release {self.release_config.get('release_name', 'RELEASE')} \\\n"
            stage_def += f"                            --components {component} \\\n"
            stage_def += f"                            --bigtop-branch {self.release_config['bigtop_branch']} \\\n"
            stage_def += f"                            --docker-image {self.release_config['docker_image']} \\\n"
            stage_def += f"                            --kubeconfig ${{KUBECONFIG}} \\\n"
            stage_def += f"                            --non-interactive\n"
            stage_def += f"                    '''\n"
            stage_def += f"                }}\n"
            stage_def += f"            }}\n"
        
        stage_def += f"        }}\n"
        
        return stage_def
    
    def generate_jenkinsfile(self, components: List[str], 
                            agent_label: str = "any",
                            kubeconfig_credential: str = "odp-hz-kubeconfig") -> str:
        """
        Generate complete Jenkinsfile with all stages
        
        Args:
            components: List of components to build
            agent_label: Jenkins agent label
            kubeconfig_credential: Jenkins credential ID for kubeconfig
            
        Returns:
            Complete Jenkinsfile as string
        """
        # Get build order
        build_order = self.get_build_order(components)
        
        jenkinsfile = f"""pipeline {{
    agent {{
        label '{agent_label}'
    }}
    
    environment {{
        KUBECONFIG = credentials('{kubeconfig_credential}')
        RELEASE = '{self.release_config.get('release_name', 'RELEASE')}'
        BIGTOP_BRANCH = '{self.release_config['bigtop_branch']}'
        DOCKER_IMAGE = '{self.release_config['docker_image']}'
    }}
    
    stages {{
"""
        
        # Generate stages
        for stage_num, stage_components in enumerate(build_order, 1):
            jenkinsfile += self.generate_parallel_stage(stage_num, stage_components)
            jenkinsfile += "\n"
        
        jenkinsfile += """    }
    
    post {
        always {
            script {
                echo '=' * 80
                echo 'BUILD PIPELINE COMPLETED'
                echo '=' * 80
            }
        }
        success {
            script {
                echo '✓ All components built successfully'
            }
        }
        failure {
            script {
                echo '✗ Some components failed to build'
            }
        }
    }
}
"""
        
        return jenkinsfile
    
    def print_build_structure(self, components: List[str]):
        """
        Print the build structure that will be generated
        
        Args:
            components: List of components to build
        """
        build_order = self.get_build_order(components)
        
        logger.info("=" * 80)
        logger.info("JENKINS PIPELINE STRUCTURE")
        logger.info("=" * 80)
        
        for stage_num, stage_components in enumerate(build_order, 1):
            logger.info(f"\n🧱 DEPENDENCY-STAGE-{stage_num}")
            if len(stage_components) > 1:
                logger.info(f"  └─ Parallel Stages:")
                for comp in stage_components:
                    deps = self.get_dependencies(comp)
                    dep_str = f" (deps: {', '.join(deps)})" if deps else " (no deps)"
                    logger.info(f"      ├─ stage('{comp}'){dep_str}")
            else:
                comp = stage_components[0]
                deps = self.get_dependencies(comp)
                dep_str = f" (deps: {', '.join(deps)})" if deps else " (no deps)"
                logger.info(f"  └─ stage('{comp}'){dep_str}")
        
        logger.info("\n" + "=" * 80)

