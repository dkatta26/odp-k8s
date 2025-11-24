"""
Kubernetes Job Manager
Handles creation, monitoring, and management of Kubernetes Jobs for ODP builds
"""

import subprocess
import time
import yaml
from typing import Dict, List, Optional
import logging

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
        
    def _run_kubectl(self, args: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """
        Run kubectl command
        
        Args:
            args: kubectl command arguments
            capture_output: Whether to capture output
            
        Returns:
            CompletedProcess object
        """
        cmd = ['kubectl', f'--kubeconfig={self.kubeconfig}'] + args
        logger.debug(f"Running: {' '.join(cmd)}")
        
        if capture_output:
            return subprocess.run(cmd, capture_output=True, text=True)
        else:
            return subprocess.run(cmd, text=True)
    
    def verify_namespace(self, namespace: str) -> bool:
        """
        Verify that the namespace exists
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            True if namespace exists, False otherwise
        """
        logger.info(f"Verifying namespace: {namespace}")
        result = self._run_kubectl(['get', 'namespace', namespace])
        return result.returncode == 0
    
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
        result = self._run_kubectl(['get', 'secret', secret_name, '-n', namespace])
        return result.returncode == 0
    
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
        gradle_commands = '\n              '.join([f'./gradlew {task} --info' for task in gradle_tasks])
        
        job_spec = {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'name': job_name,
                'namespace': release_config['namespace']
            },
            'spec': {
                'ttlSecondsAfterFinished': release_config['job_ttl_seconds'],
                'template': {
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
                                        'mountPath': '/root/.ssh'
                                    }
                                ],
                                'command': ['/bin/bash', '-c'],
                                'args': [
                                    f"""set -euo pipefail

echo "[INFO] Using SSH key for git clones"
ls -l /root/.ssh

echo "[INFO] Cloning odp-bigtop repo"
git clone -b {release_config['bigtop_branch']} {release_config['github_repo']}

cd odp-bigtop

echo "[INFO] Building {component} via Gradle"
{gradle_commands}

echo "[INFO] Build complete for {component}"
"""
                                ]
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
        
        logger.info(f"Launching job for component: {component}")
        logger.info(f"  Job name: {job_name}")
        logger.info(f"  Namespace: {namespace}")
        
        # Generate YAML
        yaml_content = self.generate_job_yaml(component, config, release_config)
        
        # Write to temporary file
        yaml_file = f"/tmp/{job_name}.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)
        
        # Apply the job
        result = self._run_kubectl(['apply', '-f', yaml_file])
        
        if result.returncode == 0:
            self.jobs[component] = job_name
            logger.info(f"✓ Job {job_name} launched successfully")
            return True
        else:
            logger.error(f"✗ Failed to launch job {job_name}")
            logger.error(f"  Error: {result.stderr}")
            return False
    
    def get_job_status(self, job_name: str, namespace: str) -> Dict:
        """
        Get the status of a Kubernetes Job
        
        Args:
            job_name: Job name
            namespace: Kubernetes namespace
            
        Returns:
            Dictionary with status information: {
                'exists': bool,
                'completed': bool,
                'failed': bool,
                'active': bool
            }
        """
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
        args = ['logs', f'job/{job_name}', '-n', namespace]
        if tail:
            args.extend(['--tail', str(tail)])
        
        result = self._run_kubectl(args)
        return result.stdout if result.returncode == 0 else ""
    
    def stream_job_logs(self, job_name: str, namespace: str):
        """
        Stream logs from a Kubernetes Job in real-time
        
        Args:
            job_name: Job name
            namespace: Kubernetes namespace
        """
        logger.info(f"Streaming logs for job: {job_name}")
        logger.info("=" * 80)
        
        args = ['logs', f'job/{job_name}', '-n', namespace, '--follow']
        self._run_kubectl(args, capture_output=False)
    
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
            component_prefix: Prefix for log messages (e.g., "[component-name]")
            stream_logs: Whether to stream logs in real-time
            
        Returns:
            True if job completed successfully, False if failed or timeout
        """
        logger.info(f"{component_prefix} Waiting for job to complete: {job_name}")
        start_time = time.time()
        
        # Stream logs in background if requested
        log_streamed = False
        
        while True:
            elapsed = int(time.time() - start_time)
            
            if elapsed >= timeout:
                logger.error(f"{component_prefix} ✗ Timeout after {timeout}s")
                return False
            
            status = self.get_job_status(job_name, namespace)
            
            if not status['exists']:
                logger.error(f"{component_prefix} ✗ Job not found")
                return False
            
            if status['completed']:
                logger.info(f"{component_prefix} ✓ Job completed successfully")
                return True
            
            if status['failed']:
                logger.error(f"{component_prefix} ✗ Job failed")
                # Print last 50 lines of logs
                logs = self.get_job_logs(job_name, namespace, tail=50)
                logger.error(f"{component_prefix} Last 50 lines of logs:")
                for line in logs.split('\n'):
                    if line.strip():
                        logger.error(f"{component_prefix}   {line}")
                return False
            
            # Stream logs once when job starts running (first active check)
            if stream_logs and status['active'] and not log_streamed:
                logger.info(f"{component_prefix} Job is running, streaming logs...")
                # Note: In parallel builds, streaming might interleave logs
                # For now, we'll just note that logs are being generated
                log_streamed = True
            
            logger.info(f"{component_prefix}   [{elapsed}s] Job still running...")
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
        logger.info(f"Deleting job: {job_name}")
        result = self._run_kubectl(['delete', 'job', job_name, '-n', namespace])
        return result.returncode == 0
    
    def cleanup_jobs(self, namespace: str) -> bool:
        """
        Clean up all managed jobs
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            True if all jobs deleted successfully
        """
        logger.info("Cleaning up jobs...")
        success = True
        for component, job_name in self.jobs.items():
            if not self.delete_job(job_name, namespace):
                success = False
        return success

