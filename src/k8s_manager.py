"""
Kubernetes Job Manager
Handles creation, monitoring, and management of Kubernetes Jobs for ODP builds
"""

import subprocess
import time
import yaml
from typing import Dict, List, Optional
import logging
import os

logger = logging.getLogger(__name__)


class KubernetesJobManager:
    """Manages Kubernetes Jobs for component builds"""
    
    def __init__(self, kubeconfig: str):
        """
        Initialize the Kubernetes Job Manager
        
        Args:
            kubeconfig: Path to kubeconfig file
        """
        self.kubeconfig = kubeconfig
        self.jobs = {}  # Track launched jobs: {component: job_name}
        
        # Verify kubeconfig exists
        if not os.path.exists(kubeconfig):
            logger.warning(f"Kubeconfig file not found: {kubeconfig}")
        
    def _run_kubectl(self, args: List[str], capture_output: bool = True, check: bool = False) -> subprocess.CompletedProcess:
        """
        Run kubectl command
        
        Args:
            args: kubectl command arguments
            capture_output: Whether to capture output
            check: Whether to raise exception on non-zero return code
            
        Returns:
            CompletedProcess object
        """
        cmd = ['kubectl', f'--kubeconfig={self.kubeconfig}'] + args
        logger.debug(f"Running: {' '.join(cmd)}")
        
        try:
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            else:
                result = subprocess.run(cmd, text=True, check=check)
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"kubectl command failed: {e}")
            raise
        except FileNotFoundError:
            logger.error("kubectl command not found. Please ensure kubectl is installed and in PATH.")
            raise
    
    def verify_namespace(self, namespace: str) -> bool:
        """
        Verify that the namespace exists
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            True if namespace exists, False otherwise
        """
        logger.info(f"Verifying namespace: {namespace}")
        try:
            result = self._run_kubectl(['get', 'namespace', namespace])
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error verifying namespace: {e}")
            return False
    
    def verify_secret(self, secret_name: str, namespace: str) -> bool:
        """
        Verify that the secret exists
        
        Args:
            secret_name: Secret name
            namespace: Kubernetes namespace
            
        Returns:
            True if secret exists, False otherwise
        """
        logger.info(f"Verifying secret: {secret_name} in namespace: {namespace}")
        try:
            result = self._run_kubectl(['get', 'secret', secret_name, '-n', namespace])
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error verifying secret: {e}")
            return False
    
    def delete_existing_job(self, job_name: str, namespace: str) -> bool:
        """
        Delete an existing job if it exists (for cleanup/retry)
        
        Args:
            job_name: Job name
            namespace: Kubernetes namespace
            
        Returns:
            True if deleted or doesn't exist, False on error
        """
        try:
            # Check if job exists
            result = self._run_kubectl(['get', 'job', job_name, '-n', namespace])
            if result.returncode == 0:
                logger.info(f"Deleting existing job: {job_name}")
                result = self._run_kubectl(['delete', 'job', job_name, '-n', namespace, '--ignore-not-found=true'])
                if result.returncode == 0:
                    logger.info(f"✓ Deleted existing job: {job_name}")
                    time.sleep(2)  # Give K8s time to clean up
                    return True
                else:
                    logger.warning(f"Failed to delete job {job_name}: {result.stderr}")
                    return False
            return True
        except Exception as e:
            logger.warning(f"Error checking/deleting job: {e}")
            return True  # Continue anyway
    
    def generate_job_yaml(self, component: str, config: Dict, release_config: Dict) -> str:
        """
        Generate Kubernetes Job YAML for a component
        
        Args:
            component: Component name
            config: Component configuration
            release_config: Release configuration
            
        Returns:
            YAML string for the Job
        """
        gradle_tasks = config['gradle_tasks']
        job_name = f"{component}-build"
        
        # Build the gradle command string
        gradle_commands = []
        for task in gradle_tasks:
            gradle_commands.append(f'./gradlew {task} --info')
        
        gradle_command_str = '\n'.join(gradle_commands)
        
        # Generate bash script for the container
        bash_script = f"""set -euo pipefail

echo "============================================"
echo "Starting build for component: {component}"
echo "============================================"
echo "Bigtop Branch: {release_config['bigtop_branch']}"
echo "Docker Image: {release_config['docker_image']}"
echo "Gradle Tasks: {', '.join(gradle_tasks)}"
echo "============================================"

echo ""
echo "[INFO] Setting up SSH for git clones"
ls -lh /root/.ssh/

echo ""
echo "[INFO] Cloning odp-bigtop repository"
echo "[INFO] Branch: {release_config['bigtop_branch']}"
git clone -b {release_config['bigtop_branch']} {release_config['github_repo']} || {{
    echo "[ERROR] Failed to clone repository"
    exit 1
}}

cd odp-bigtop

echo ""
echo "[INFO] Starting Gradle build for {component}"
echo "============================================"
{gradle_command_str}

echo ""
echo "============================================"
echo "[SUCCESS] Build complete for {component}"
echo "============================================"
"""
        
        job_spec = {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'name': job_name,
                'namespace': release_config['namespace'],
                'labels': {
                    'component': component,
                    'release': release_config.get('release_name', 'unknown'),
                    'app': 'odp-build'
                }
            },
            'spec': {
                'ttlSecondsAfterFinished': release_config.get('job_ttl_seconds', 3600),
                'backoffLimit': 0,  # Don't retry on failure
                'template': {
                    'metadata': {
                        'labels': {
                            'component': component,
                            'app': 'odp-build'
                        }
                    },
                    'spec': {
                        'restartPolicy': 'Never',
                        'volumes': [
                            {
                                'name': 'ssh-keys',
                                'secret': {
                                    'secretName': release_config['secret_name'],
                                    'defaultMode': 0o400
                                }
                            }
                        ],
                        'containers': [
                            {
                                'name': f"{component}-build",
                                'image': release_config['docker_image'],
                                'volumeMounts': [
                                    {
                                        'name': 'ssh-keys',
                                        'mountPath': '/root/.ssh',
                                        'readOnly': True
                                    }
                                ],
                                'command': ['/bin/bash', '-c'],
                                'args': [bash_script],
                                'resources': {
                                    'requests': {
                                        'memory': '2Gi',
                                        'cpu': '1'
                                    },
                                    'limits': {
                                        'memory': '8Gi',
                                        'cpu': '4'
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        return yaml.dump(job_spec, default_flow_style=False)
    
    def launch_job(self, component: str, config: Dict, release_config: Dict) -> bool:
        """
        Launch a Kubernetes Job for a component
        
        Args:
            component: Component name
            config: Component configuration
            release_config: Release configuration
            
        Returns:
            True if job launched successfully, False otherwise
        """
        job_name = f"{component}-build"
        namespace = release_config['namespace']
        
        logger.debug(f"Preparing to launch job: {job_name}")
        
        # Delete existing job if present
        if not self.delete_existing_job(job_name, namespace):
            logger.warning(f"Could not clean up existing job, but continuing anyway...")
        
        # Generate YAML
        try:
            yaml_content = self.generate_job_yaml(component, config, release_config)
        except Exception as e:
            logger.error(f"Failed to generate job YAML: {e}")
            return False
        
        # Write to temporary file
        yaml_file = f"/tmp/{job_name}.yaml"
        try:
            with open(yaml_file, 'w') as f:
                f.write(yaml_content)
            logger.debug(f"Job YAML written to: {yaml_file}")
        except Exception as e:
            logger.error(f"Failed to write job YAML file: {e}")
            return False
        
        # Apply the job
        try:
            result = self._run_kubectl(['apply', '-f', yaml_file])
            
            if result.returncode == 0:
                self.jobs[component] = job_name
                logger.debug(f"✓ Job {job_name} created successfully")
                return True
            else:
                logger.error(f"✗ Failed to create job {job_name}")
                if result.stderr:
                    logger.error(f"  Error: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Exception while launching job: {e}")
            return False
        finally:
            # Clean up temp file
            try:
                os.remove(yaml_file)
            except:
                pass
    
    def get_job_status(self, job_name: str, namespace: str) -> Dict:
        """
        Get the status of a Kubernetes Job
        
        Args:
            job_name: Job name
            namespace: Kubernetes namespace
            
        Returns:
            Dictionary with status information
        """
        try:
            # Check if job exists
            result = self._run_kubectl(['get', 'job', job_name, '-n', namespace])
            if result.returncode != 0:
                return {
                    'exists': False,
                    'completed': False,
                    'failed': False,
                    'active': False
                }
            
            # Get completion status
            result = self._run_kubectl([
                'get', 'job', job_name, '-n', namespace,
                '-o', 'jsonpath={.status.conditions[?(@.type=="Complete")].status}'
            ])
            completed = result.stdout.strip() == 'True'
            
            # Get failed status
            result = self._run_kubectl([
                'get', 'job', job_name, '-n', namespace,
                '-o', 'jsonpath={.status.conditions[?(@.type=="Failed")].status}'
            ])
            failed = result.stdout.strip() == 'True'
            
            # Job is active if it exists and is neither completed nor failed
            active = not completed and not failed
            
            return {
                'exists': True,
                'completed': completed,
                'failed': failed,
                'active': active
            }
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {
                'exists': False,
                'completed': False,
                'failed': False,
                'active': False
            }
    
    def get_job_logs(self, job_name: str, namespace: str, tail: Optional[int] = None) -> str:
        """
        Get logs from a Kubernetes Job
        
        Args:
            job_name: Job name
            namespace: Kubernetes namespace
            tail: Number of lines to tail (optional)
            
        Returns:
            Log output as string
        """
        try:
            args = ['logs', f'job/{job_name}', '-n', namespace]
            if tail:
                args.extend(['--tail', str(tail)])
            
            result = self._run_kubectl(args)
            return result.stdout if result.returncode == 0 else ""
        except Exception as e:
            logger.error(f"Error getting job logs: {e}")
            return ""
    
    def wait_for_job(self, job_name: str, namespace: str, 
                     timeout: int = 3600, check_interval: int = 30,
                     component_prefix: str = "", stream_logs: bool = False) -> bool:
        """
        Wait for a job to complete
        
        Args:
            job_name: Job name
            namespace: Kubernetes namespace
            timeout: Maximum time to wait in seconds
            check_interval: Interval between status checks in seconds
            component_prefix: Prefix for log messages
            stream_logs: Whether to stream logs in real-time (not implemented yet)
            
        Returns:
            True if job completed successfully, False if failed or timeout
        """
        logger.info(f"{component_prefix} Waiting for job to complete...")
        start_time = time.time()
        last_status_log = 0
        
        while True:
            elapsed = int(time.time() - start_time)
            
            # Check timeout
            if elapsed >= timeout:
                logger.error(f"{component_prefix} ✗ Timeout after {timeout}s")
                # Print last logs
                logs = self.get_job_logs(job_name, namespace, tail=50)
                if logs:
                    logger.error(f"{component_prefix} Last 50 lines of logs:")
                    for line in logs.split('\n'):
                        if line.strip():
                            logger.error(f"{component_prefix}   {line}")
                return False
            
            # Get job status
            status = self.get_job_status(job_name, namespace)
            
            if not status['exists']:
                logger.error(f"{component_prefix} ✗ Job not found: {job_name}")
                return False
            
            if status['completed']:
                logger.info(f"{component_prefix} ✓ Job completed successfully")
                return True
            
            if status['failed']:
                logger.error(f"{component_prefix} ✗ Job failed")
                # Print last 100 lines of logs
                logs = self.get_job_logs(job_name, namespace, tail=100)
                if logs:
                    logger.error(f"{component_prefix} Last 100 lines of logs:")
                    for line in logs.split('\n'):
                        if line.strip():
                            logger.error(f"{component_prefix}   {line}")
                return False
            
            # Log status update every minute
            if elapsed - last_status_log >= 60:
                logger.info(f"{component_prefix}   [{elapsed}s / {timeout}s] Job still running...")
                last_status_log = elapsed
            
            # Wait before checking again
            time.sleep(check_interval)
    
    def delete_job(self, job_name: str, namespace: str) -> bool:
        """
        Delete a Kubernetes Job
        
        Args:
            job_name: Job name
            namespace: Kubernetes namespace
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.info(f"Deleting job: {job_name}")
            result = self._run_kubectl(['delete', 'job', job_name, '-n', namespace, '--ignore-not-found=true'])
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error deleting job: {e}")
            return False
    
    def cleanup_jobs(self, namespace: str) -> bool:
        """
        Clean up all managed jobs
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            True if all jobs deleted successfully
        """
        if not self.jobs:
            logger.info("No jobs to clean up")
            return True
        
        logger.info(f"Cleaning up {len(self.jobs)} jobs...")
        success = True
        for component, job_name in self.jobs.items():
            if not self.delete_job(job_name, namespace):
                logger.warning(f"Failed to delete job: {job_name}")
                success = False
        
        if success:
            logger.info("✓ All jobs cleaned up successfully")
        
        return success
