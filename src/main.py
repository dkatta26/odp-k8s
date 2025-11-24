#!/usr/bin/env python3
"""
Main entrypoint for ODP Build Pipeline
Called by Jenkins to orchestrate component builds on Kubernetes
"""

import argparse
import logging
import sys
import yaml
from pathlib import Path
from typing import List, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from k8s_manager import KubernetesJobManager
from orchestrator import BuildOrchestrator


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)8s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Suppress verbose loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('kubernetes').setLevel(logging.WARNING)


def load_yaml_config(config_file: Path) -> dict:
    """
    Load YAML configuration file
    
    Args:
        config_file: Path to YAML file
        
    Returns:
        Dictionary with configuration
    """
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def get_repo_root() -> Path:
    """Get the repository root directory"""
    # Assume this script is in src/, so parent is repo root
    return Path(__file__).parent.parent


def parse_components(components_str: str, available_components: List[str]) -> Optional[List[str]]:
    """
    Parse comma-separated component string
    
    Args:
        components_str: Comma-separated component names
        available_components: List of available component names
        
    Returns:
        List of component names, or None if empty (meaning build all)
    """
    if not components_str or not components_str.strip():
        return None
    
    requested = [c.strip().lower() for c in components_str.split(',') if c.strip()]
    
    # Validate components
    invalid = [c for c in requested if c not in available_components]
    if invalid:
        raise ValueError(f"Invalid components: {', '.join(invalid)}")
    
    return requested


def print_header():
    """Print pipeline header"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("ODP BUILD PIPELINE")
    logger.info("=" * 80)


def print_config(args, components_to_build: List[str]):
    """Print configuration summary"""
    logger = logging.getLogger(__name__)
    logger.info(f"Release: {args.release}")
    logger.info(f"Bigtop Branch: {args.bigtop_branch}")
    logger.info(f"Docker Image: {args.docker_image}")
    logger.info(f"Components: {', '.join(components_to_build)}")
    logger.info(f"Kubeconfig: {args.kubeconfig}")
    logger.info(f"Dry Run: {args.dry_run}")
    logger.info(f"Interactive Mode: {not args.non_interactive}")
    logger.info("=" * 80)


def verify_environment(k8s_manager: KubernetesJobManager, release_config: Dict) -> bool:
    """
    Verify Kubernetes environment is ready
    
    Args:
        k8s_manager: KubernetesJobManager instance
        release_config: Release configuration
        
    Returns:
        True if environment is ready, False otherwise
    """
    logger = logging.getLogger(__name__)
    logger.info("\n" + "=" * 80)
    logger.info("VERIFYING KUBERNETES ENVIRONMENT")
    logger.info("=" * 80)
    
    # Verify namespace
    if not k8s_manager.verify_namespace(release_config['namespace']):
        logger.error(f"✗ Namespace '{release_config['namespace']}' does not exist")
        logger.error(f"\nCreate the namespace using:")
        logger.error(f"  kubectl create namespace {release_config['namespace']}")
        return False
    logger.info(f"✓ Namespace '{release_config['namespace']}' exists")
    
    # Verify secret
    if not k8s_manager.verify_secret(release_config['secret_name'], release_config['namespace']):
        logger.error(f"✗ Secret '{release_config['secret_name']}' does not exist")
        logger.error(f"\nCreate the secret using:")
        logger.error(f"  kubectl create secret generic {release_config['secret_name']} \\")
        logger.error(f"    --from-file=id_rsa=$HOME/.ssh/id_rsa \\")
        logger.error(f"    --from-file=known_hosts=$HOME/.ssh/known_hosts \\")
        logger.error(f"    -n {release_config['namespace']}")
        return False
    logger.info(f"✓ Secret '{release_config['secret_name']}' exists")
    
    logger.info("=" * 80)
    return True


def main():
    """Main entrypoint"""
    parser = argparse.ArgumentParser(
        description='ODP Build Pipeline - Orchestrates component builds on Kubernetes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build all components for a release
  python3 main.py --release ODP-3.3.6.3-1 \\
    --bigtop-branch rel/ODP-3.3.6.3-1 \\
    --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6
  
  # Build specific components
  python3 main.py --release ODP-3.3.6.3-1 \\
    --components zookeeper,hadoop \\
    --bigtop-branch rel/ODP-3.3.6.3-1 \\
    --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6
"""
    )
    
    # Required arguments
    parser.add_argument(
        '--release',
        required=True,
        help='ODP release version (e.g., ODP-3.3.6.3-1)'
    )
    
    parser.add_argument(
        '--bigtop-branch',
        required=True,
        help='ODP Bigtop branch to use for builds (e.g., rel/ODP-3.3.6.3-1)'
    )
    
    parser.add_argument(
        '--docker-image',
        required=True,
        help='Docker image to use for build environment'
    )
    
    # Optional arguments
    parser.add_argument(
        '--components',
        default='',
        help='Comma-separated list of components to build (leave empty for all)'
    )
    
    parser.add_argument(
        '--kubeconfig',
        default='/odp-hz.yaml',
        help='Path to kubeconfig file (default: /odp-hz.yaml)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show build plan without executing'
    )
    
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Non-interactive mode: skip failed builds automatically'
    )
    
    parser.add_argument(
        '--stream-logs',
        action='store_true',
        help='Stream build logs in real-time (may interleave in parallel builds)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Print header
        print_header()
        
        # Get repository root and configuration directory
        repo_root = get_repo_root()
        config_dir = repo_root / 'config'
        
        logger.info(f"Repository root: {repo_root}")
        logger.info(f"Configuration directory: {config_dir}")
        logger.info("")
        
        # Load configurations
        logger.info("Loading configurations...")
        
        releases_config_file = config_dir / 'releases.yaml'
        components_config_file = config_dir / 'components.yaml'
        
        if not releases_config_file.exists():
            logger.error(f"Releases config not found: {releases_config_file}")
            return 1
        
        if not components_config_file.exists():
            logger.error(f"Components config not found: {components_config_file}")
            return 1
        
        releases_config = load_yaml_config(releases_config_file)
        components_config = load_yaml_config(components_config_file)
        
        logger.info(f"✓ Loaded releases configuration")
        logger.info(f"✓ Loaded components configuration")
        logger.info("")
        
        # Get release configuration
        if args.release not in releases_config['releases']:
            logger.error(f"Release '{args.release}' not found in configuration")
            logger.error(f"Available releases: {', '.join(releases_config['releases'].keys())}")
            return 1
        
        release_config = releases_config['releases'][args.release].copy()
        
        # Override with command-line parameters
        release_config['bigtop_branch'] = args.bigtop_branch
        release_config['docker_image'] = args.docker_image
        release_config['release_name'] = args.release
        
        logger.info(f"Release Configuration:")
        logger.info(f"  Name: {args.release}")
        logger.info(f"  Branch: {release_config['bigtop_branch']}")
        logger.info(f"  Docker Image: {release_config['docker_image']}")
        logger.info(f"  Namespace: {release_config['namespace']}")
        logger.info(f"  GitHub Repo: {release_config['github_repo']}")
        logger.info("")
        
        # Parse components to build
        available_components = list(components_config['components'].keys())
        components_to_build = parse_components(args.components, available_components)
        
        if components_to_build is None:
            # Build all components
            components_to_build = available_components
            logger.info(f"Building ALL components: {', '.join(components_to_build)}")
        else:
            logger.info(f"Building SELECTED components: {', '.join(components_to_build)}")
        
        logger.info("")
        
        # Print final configuration
        print_config(args, components_to_build)
        
        # Initialize Kubernetes manager
        logger.info("\nInitializing Kubernetes manager...")
        k8s_manager = KubernetesJobManager(args.kubeconfig)
        logger.info("✓ Kubernetes manager initialized")
        
        # Verify environment
        if not verify_environment(k8s_manager, release_config):
            logger.error("\n✗ Environment verification failed")
            return 1
        
        # Initialize orchestrator
        logger.info("\nInitializing build orchestrator...")
        orchestrator = BuildOrchestrator(
            k8s_manager,
            components_config['components'],
            release_config,
            interactive=not args.non_interactive,
            stream_logs=args.stream_logs
        )
        logger.info("✓ Build orchestrator initialized")
        logger.info("")
        
        # Dry run - just show the plan
        if args.dry_run:
            logger.info("=" * 80)
            logger.info("DRY RUN MODE - Build plan only")
            logger.info("=" * 80)
            orchestrator.print_build_plan(components_to_build)
            logger.info("\nDry run complete. No builds were executed.")
            return 0
        
        # Execute builds
        logger.info("Starting build execution...")
        logger.info("")
        
        success = orchestrator.build_all(components_to_build)
        
        # Print final summary
        summary = orchestrator.get_build_summary()
        logger.info("\n" + "=" * 80)
        logger.info("FINAL BUILD SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Components: {len(components_to_build)}")
        logger.info(f"Completed: {summary['total_completed']}")
        logger.info(f"Skipped: {summary['total_skipped']}")
        logger.info(f"Failed: {summary['total_failed']}")
        logger.info("")
        
        if summary['completed']:
            logger.info(f"✓ Completed: {', '.join(summary['completed'])}")
        if summary['skipped']:
            logger.warning(f"⊗ Skipped: {', '.join(summary['skipped'])}")
        if summary['failed']:
            logger.error(f"✗ Failed: {', '.join(summary['failed'])}")
        
        logger.info("=" * 80)
        
        if success:
            logger.info("\n✓ BUILD PIPELINE COMPLETED SUCCESSFULLY")
            return 0
        else:
            logger.error("\n✗ BUILD PIPELINE FAILED")
            return 1
            
    except FileNotFoundError as e:
        logger.error(f"\n✗ Configuration error: {e}")
        return 1
    except ValueError as e:
        logger.error(f"\n✗ Validation error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.error(f"\n\n✗ Build interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
