# ODP Build Pipeline - Refactored Version

## Overview

This is a clean, refactored version of the ODP build pipeline that orchestrates component builds on Kubernetes. The refactoring focused on:

1. **Simplified Logic**: Cleaner orchestration logic without complex threading issues
2. **Better Error Handling**: Comprehensive error handling and validation
3. **Improved Logging**: Clear, structured logging throughout the pipeline
4. **Fixed Blocking Issues**: Resolved the hanging issue in dynamic build execution
5. **Maintainability**: More readable and maintainable code structure

## What Was Fixed

### Main Issue: Infinite Loop in Build Orchestration

**Problem**: The original code was stuck at "STARTING DYNAMIC BUILD EXECUTION" because:
- The while loop was checking for ready components but not properly handling the case where futures were still running
- The `time.sleep(1)` was too short and caused busy waiting
- The logic for detecting completed futures was inefficient

**Solution**:
- Simplified the main orchestration loop
- Properly check for completed futures using `future.done()`
- Added better waiting logic with `time.sleep(2)` only when needed
- Clear separation between ready checking, submission, and completion handling

### Additional Improvements

1. **Better Resource Management**:
   - Automatic cleanup of existing jobs before launching new ones
   - Proper error handling for kubectl commands
   - Resource limits added to Kubernetes jobs

2. **Enhanced Validation**:
   - Validate components before build
   - Check kubeconfig file exists
   - Verify namespace and secrets before starting

3. **Cleaner Code Structure**:
   - Removed unnecessary complexity
   - Better separation of concerns
   - More maintainable functions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Jenkinsfile                         │
│  (Jenkins Pipeline - Orchestrates the entire process)       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        main.py                              │
│  • Load configurations (releases.yaml, components.yaml)     │
│  • Parse command-line arguments                             │
│  • Validate environment                                     │
│  • Initialize K8s manager and orchestrator                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   orchestrator.py   │         │   k8s_manager.py    │
│                     │         │                     │
│ • Dependency        │◄────────┤ • Job creation      │
│   resolution        │         │ • Job monitoring    │
│ • Parallel builds   │         │ • Log retrieval     │
│ • Retry/skip logic  │         │ • kubectl wrapper   │
└─────────────────────┘         └─────────────────────┘
```

## Key Components

### 1. `src/main.py`
- Entry point for the pipeline
- Loads configuration files
- Validates environment
- Coordinates the build process

### 2. `src/orchestrator.py`
- **BuildOrchestrator**: Manages parallel builds with dependency resolution
- Tracks component status (completed, failed, skipped, in_progress)
- Handles retry/skip/abort logic
- Thread-safe state management

### 3. `src/k8s_manager.py`
- **KubernetesJobManager**: Manages Kubernetes jobs
- Creates and monitors build jobs
- Retrieves logs on failure
- Handles job cleanup

### 4. `Jenkinsfile`
- Jenkins declarative pipeline
- Agent: `dev-build-deploy-hz`
- Stages: Checkout → Setup → Validate → Build

## Configuration Files

### `config/releases.yaml`
Defines release-specific configurations:
```yaml
releases:
  ODP-3.3.6.3-1:
    namespace: build-deploy
    github_repo: git@github.com:acceldata-io/odp-bigtop.git
    secret_name: github-ssh-key
    job_ttl_seconds: 6000
```

### `config/components.yaml`
Defines component build configurations:
```yaml
components:
  zookeeper:
    name: zookeeper
    description: "Apache ZooKeeper - Distributed coordination service"
    gradle_tasks:
      - zookeeper-clean
      - zookeeper-rpm
    dependencies: []
  
  hadoop:
    name: hadoop
    description: "Apache Hadoop - Distributed storage and processing"
    gradle_tasks:
      - hadoop-clean
      - hadoop-rpm
    dependencies:
      - zookeeper
```

## Usage

### From Jenkins

1. **Configure Jenkins Job**:
   - Create a new Pipeline job
   - Point to your repository
   - Use the `Jenkinsfile` at the root

2. **Set Parameters**:
   - `ODP_RELEASE`: e.g., `ODP-3.3.6.3-1`
   - `BIGTOP_BRANCH`: e.g., `rel/ODP-3.3.6.3-1`
   - `DOCKER_IMAGE`: e.g., `repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6`
   - `COMPONENTS_TO_BUILD`: Leave empty for all, or specify: `zookeeper,hadoop`
   - `NON_INTERACTIVE`: `true` (recommended for Jenkins)

3. **Run the Pipeline**

### From Command Line

```bash
# Build all components
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
  --kubeconfig /odp-hz.yaml \
  --non-interactive

# Build specific components
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --components zookeeper,hadoop \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
  --kubeconfig /odp-hz.yaml

# Dry run (show plan without executing)
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
  --kubeconfig /odp-hz.yaml \
  --dry-run

# Verbose logging
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
  --kubeconfig /odp-hz.yaml \
  --verbose
```

## Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--release` | Yes | - | ODP release version |
| `--bigtop-branch` | Yes | - | ODP Bigtop branch |
| `--docker-image` | Yes | - | Docker image for builds |
| `--components` | No | (all) | Comma-separated components |
| `--kubeconfig` | No | `/odp-hz.yaml` | Path to kubeconfig |
| `--dry-run` | No | False | Show plan without executing |
| `--non-interactive` | No | False | Skip prompts, auto-skip failures |
| `--verbose` | No | False | Enable verbose logging |
| `--stream-logs` | No | False | Stream build logs in real-time |

## Prerequisites

### 1. Kubernetes Cluster Setup

```bash
# Create namespace
kubectl create namespace build-deploy

# Create SSH secret for GitHub access
kubectl create secret generic github-ssh-key \
  --from-file=id_rsa=$HOME/.ssh/id_rsa \
  --from-file=known_hosts=$HOME/.ssh/known_hosts \
  -n build-deploy
```

### 2. Jenkins Agent Setup

The Jenkins agent with label `dev-build-deploy-hz` must have:
- Python 3.6+
- kubectl installed and configured
- Kubeconfig file at the specified path (default: `/odp-hz.yaml`)
- Network access to Kubernetes API

### 3. Python Dependencies

```bash
pip3 install -r requirements.txt
```

Required packages:
- `pyyaml`: For YAML configuration parsing

## Build Flow

1. **Initialization**:
   - Load release and component configurations
   - Validate Kubernetes environment (namespace, secret)
   - Parse component list

2. **Build Plan**:
   - Analyze dependencies
   - Determine build order
   - Display build plan

3. **Dynamic Execution**:
   - Start components with no dependencies
   - As each component completes, start dependent components
   - Support parallel builds (up to 5 concurrent)

4. **Monitoring**:
   - Create Kubernetes Job for each component
   - Monitor job status (30-second check interval)
   - Retrieve logs on failure
   - Handle retries/skips

5. **Summary**:
   - Display final build summary
   - Report completed, skipped, and failed components

## Build States

- **Pending**: Not yet started, waiting for dependencies
- **In Progress**: Currently building
- **Completed**: Successfully built
- **Skipped**: Skipped due to failed dependencies or user choice
- **Failed**: Build failed

## Error Handling

### Interactive Mode (Default)
When a build fails, you'll be prompted:
- **[r] Retry**: Retry the failed component
- **[s] Skip**: Skip and continue with others
- **[a] Abort**: Abort the entire pipeline

### Non-Interactive Mode (`--non-interactive`)
- Automatically skips failed builds
- Recommended for Jenkins/CI environments
- No user prompts

## Parallel Builds

- Maximum 5 components build in parallel
- Components start as soon as dependencies are met
- Thread-safe status tracking
- Clean job isolation (each component in separate K8s job)

## Logging

### Log Levels
- **INFO**: General progress and status updates
- **WARNING**: Non-critical issues (e.g., skipped components)
- **ERROR**: Failures and errors

### Log Format
```
YYYY-MM-DD HH:MM:SS [LEVEL] Message
```

### Component-Specific Logs
Each component's logs are prefixed:
```
[component-name] Message
```

## Troubleshooting

### Issue: "Namespace does not exist"
```bash
kubectl create namespace build-deploy
```

### Issue: "Secret does not exist"
```bash
kubectl create secret generic github-ssh-key \
  --from-file=id_rsa=$HOME/.ssh/id_rsa \
  --from-file=known_hosts=$HOME/.ssh/known_hosts \
  -n build-deploy
```

### Issue: "Job launch failed"
- Check Kubernetes cluster connectivity
- Verify kubeconfig is valid
- Check Docker image is accessible
- Ensure proper RBAC permissions

### Issue: "Build stuck"
The refactored version fixes the original hanging issue. If you still experience issues:
1. Check component dependencies are correct
2. Verify all dependencies completed successfully
3. Enable `--verbose` for detailed logs

### Issue: "Git clone failed"
- Verify SSH keys in the secret are correct
- Check GitHub repository access
- Ensure `known_hosts` includes github.com

## Differences from Original Code

| Aspect | Original | Refactored |
|--------|----------|------------|
| Threading | Complex with potential deadlocks | Simplified with proper future handling |
| Error handling | Limited | Comprehensive try-catch blocks |
| Logging | Mixed quality | Structured and consistent |
| Code size | ~530 lines (orchestrator) | ~360 lines (orchestrator) |
| Maintainability | Low | High |
| Agent label | Configurable | Fixed: `dev-build-deploy-hz` |

## Performance

- **Parallel Builds**: Up to 5 components simultaneously
- **Status Checks**: Every 30 seconds
- **Job Timeout**: 3600 seconds (1 hour) per component
- **Job TTL**: 6000 seconds after completion (configurable)

## Future Enhancements

1. **Real-time Log Streaming**: Currently logs are shown on failure
2. **Build Artifacts**: Archive built RPMs
3. **Notifications**: Slack/email notifications on build status
4. **Metrics**: Build duration tracking and reporting
5. **Web UI**: Dashboard for build monitoring

## Contributing

When making changes:
1. Maintain thread safety in orchestrator
2. Add comprehensive error handling
3. Update this documentation
4. Test with both interactive and non-interactive modes
5. Verify parallel builds work correctly

## License

Internal use only - Acceldata

## Support

For issues or questions, contact the ODP Build team.

