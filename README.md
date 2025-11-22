# ODP Build Pipeline for Kubernetes

A well-structured Jenkins pipeline that orchestrates building ODP (Open Data Platform) components on Kubernetes with automatic dependency resolution. The pipeline is configuration-driven with all logic contained in the repository.

## Architecture

This project follows a clean separation of concerns:

- **Jenkinsfile**: Minimal pipeline that clones the repo and calls the orchestration script
- **Configuration**: YAML files define releases and components (no hardcoding)
- **Orchestration Logic**: Python scripts handle all build logic
- **Kubernetes Integration**: Job management and monitoring

## Directory Structure

```
odp-on-k8s/
├── Jenkinsfile                      # Minimal Jenkins pipeline
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
├── config/
│   ├── releases.yaml               # Release configurations (branch, image, namespace)
│   └── components.yaml             # Component definitions and dependencies
└── src/
    ├── main.py                     # Main entrypoint called by Jenkins
    ├── orchestrator.py             # Build orchestration and dependency management
    └── k8s_manager.py              # Kubernetes Job management
```

## Features

- **Configuration-Driven**: All metadata in YAML files (releases, components, dependencies)
- **Automatic Dependency Resolution**: Builds components in the correct order
- **Parallel Execution**: Independent components build simultaneously
- **Real-time Logging**: All output visible in Jenkins console
- **Dynamic Job Generation**: Creates Kubernetes Jobs based on configuration
- **Dry Run Mode**: Preview build plan without execution
- **Thread-Safe**: Handles parallel builds safely

## Prerequisites

1. **Kubernetes Cluster Access**
   - `kubectl` configured and accessible
   - `KUBECONFIG` environment variable set (default: `/odp-hz.yaml`)
   - **Required Permissions**:
     - Read access to the target namespace (e.g., `build-deploy`)
     - Create/read Jobs in the namespace
     - Read Secrets in the namespace
     - Read Pod logs in the namespace
   - **Note**: Cluster-level permissions (like listing nodes) are NOT required

2. **Kubernetes Resources**
   - Namespace (e.g., `build-deploy`)
   - Secret: `github-ssh-key` containing SSH keys for GitHub access

3. **Jenkins**
   - Python 3.6+ available on Jenkins agent
   - Pipeline plugin installed

4. **Python Dependencies**
   - PyYAML (installed automatically during pipeline run)

## Setup

### 1. Create GitHub SSH Secret

On your Kubernetes node:

```bash
kubectl create secret generic github-ssh-key \
  --from-file=id_rsa=/root/.ssh/id_rsa \
  --from-file=known_hosts=/root/.ssh/known_hosts \
  -n build-deploy
```

### 2. Configure Jenkins Pipeline

1. Create a new Jenkins Pipeline job
2. Configure Git repository URL
3. Set Jenkinsfile path: `Jenkinsfile`
4. Configure parameters (see below)

**Important: Running as Root User**

This pipeline needs to run with root user permissions to access the kubeconfig file and create Kubernetes Jobs. Configure your Jenkins agent to run as root:

**Option A: Configure Jenkins Node as root**
1. Go to Jenkins → Manage Jenkins → Manage Nodes
2. Select your node (or create a new one)
3. Configure the node to run as root user
4. Ensure the node has access to `/odp-hz.yaml` kubeconfig file

**Option B: Run Jenkins directly on the Kubernetes node**
1. SSH to your Kubernetes node (e.g., `odp04`) as root
2. Run Jenkins agent from there with root permissions
3. Ensure `KUBECONFIG=/odp-hz.yaml` is set in the environment

### 3. Add New Releases (Optional)

Edit `config/releases.yaml` to add new ODP releases:

**Note**: You don't need to specify `bigtop_branch` or `docker_image` in the config - these come from Jenkins parameters.

```yaml
releases:
  ODP-3.3.7.0-1:
    namespace: build-deploy
    github_repo: git@github.com:acceldata-io/odp-bigtop.git
    secret_name: github-ssh-key
    job_ttl_seconds: 6000
```

### 4. Add New Components (Optional)

Edit `config/components.yaml` to add new components:

```yaml
components:
  spark:
    name: spark
    description: "Apache Spark - Unified analytics engine"
    gradle_tasks:
      - spark-clean
      - spark-rpm
    dependencies:
      - hadoop
```

## Jenkins Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `REPO_URL` | (your repo) | Git repository URL for this orchestration repo |
| `REPO_BRANCH` | `main` | Git branch to checkout |
| `COMPONENTS_TO_BUILD` | (empty) | Comma-separated components (empty = build all) |
| `ODP_RELEASE` | `ODP-3.3.6.3-1` | ODP release version (used to lookup config) |
| `BIGTOP_BRANCH` | `rel/ODP-3.3.6.3-1` | ODP Bigtop branch to use for builds |
| `DOCKER_IMAGE` | `repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6` | Docker image for build environment |
| `KUBECONFIG_PATH` | `/odp-hz.yaml` | Path to kubeconfig file |

**Note**: `BIGTOP_BRANCH` and `DOCKER_IMAGE` are provided as Jenkins parameters, not hardcoded in config files. This allows you to easily change them per build without modifying the repository.

## Usage

### Build All Components

Leave `COMPONENTS_TO_BUILD` empty:

```
REPO_URL: https://github.com/your-org/odp-on-k8s.git
REPO_BRANCH: main
COMPONENTS_TO_BUILD: (empty)
ODP_RELEASE: ODP-3.3.6.3-1
BIGTOP_BRANCH: rel/ODP-3.3.6.3-1
DOCKER_IMAGE: repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6
KUBECONFIG_PATH: /odp-hz.yaml
```

### Build Specific Components

Set `COMPONENTS_TO_BUILD`:

```
COMPONENTS_TO_BUILD: zookeeper,hadoop
BIGTOP_BRANCH: rel/ODP-3.3.6.3-1
DOCKER_IMAGE: repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6
```

### Use Different Branch or Image

Simply change the parameters in Jenkins:

```
BIGTOP_BRANCH: rel/ODP-3.3.7.0-1
DOCKER_IMAGE: repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:7
```

The pipeline automatically handles dependencies. For example, if you request only `hadoop`, it will also build `zookeeper` first.

### Command Line Usage (Direct)

You can also run the orchestration script directly:

```bash
# Build all components
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6

# Build specific components
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
  --components zookeeper,hadoop

# Dry run (show plan only)
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
  --dry-run

# Verbose output
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
  --verbose
```

## Components and Dependencies

Current components defined in `config/components.yaml`:

| Component | Dependencies | Gradle Tasks |
|-----------|--------------|--------------|
| **zookeeper** | None | `zookeeper-clean`, `zookeeper-rpm` |
| **hadoop** | zookeeper | `hadoop-clean`, `hadoop-rpm` |
| **hue** | None | `hue-clean`, `hue-rpm` |
| **kafka** | zookeeper | `kafka-clean`, `kafka-rpm` |

### Dependency Graph

```
zookeeper (no dependencies) ─┬─→ hadoop
                             └─→ kafka

hue (no dependencies)
```

### Build Order

1. **Stage 1 (parallel)**: `zookeeper`, `hue`
2. **Stage 2 (parallel)**: `hadoop`, `kafka` (after zookeeper completes)

## How It Works

### 1. Jenkins Checkout

Jenkinsfile clones the repository and checks out the specified branch.

### 2. Environment Validation

- Verifies Python 3 is available
- Checks kubectl access
- Installs Python dependencies
- Validates Kubernetes namespace and secret

### 3. Build Orchestration

The main Python script (`src/main.py`):

1. Loads configuration from YAML files
2. Validates the release exists
3. Parses components to build
4. Initializes Kubernetes manager
5. Creates build orchestrator
6. Calculates build order from dependencies
7. Executes builds in stages

### 4. Parallel Execution

Components with met dependencies build in parallel:

- `zookeeper` and `hue` start simultaneously (no dependencies)
- When `zookeeper` completes, `hadoop` and `kafka` start in parallel

### 5. Job Monitoring

Each build:

1. Generates Kubernetes Job YAML dynamically
2. Launches the Job
3. Monitors status every 30 seconds
4. Logs progress to Jenkins console
5. Marks as completed or failed

## Monitoring

### View Build Progress

All logs appear in Jenkins console output with clear stages and timestamps.

### Check Kubernetes Jobs

```bash
# List all jobs
kubectl get jobs -n build-deploy

# View job details
kubectl describe job zookeeper-build -n build-deploy

# View job logs
kubectl logs job/zookeeper-build -n build-deploy

# Stream logs
kubectl logs job/zookeeper-build -n build-deploy --follow
```

### Check Pods

```bash
kubectl get pods -n build-deploy
kubectl logs <pod-name> -n build-deploy
```

## Troubleshooting

### Permission Denied Error

**Symptom**: `Error from server (Forbidden): nodes is forbidden` or similar RBAC errors

**Solutions**:
1. You don't need cluster-level permissions. The pipeline only requires:
   - Access to your namespace (e.g., `build-deploy`)
   - Ability to create/read Jobs
   - Ability to read Secrets and Pod logs

2. Test your permissions:
   ```bash
   # Check namespace access (should work)
   kubectl get namespace build-deploy
   
   # Check if you can list jobs in your namespace (should work)
   kubectl get jobs -n build-deploy
   
   # Check if you can see secrets (should work)
   kubectl get secrets -n build-deploy
   ```

3. If you still get permission errors, contact your cluster administrator to grant you:
   - `edit` or `admin` role in the `build-deploy` namespace

### Job Not Starting

**Symptom**: Pipeline validates successfully but job doesn't start

**Solutions**:
1. Verify namespace exists:
   ```bash
   kubectl get namespace build-deploy
   ```

2. Verify secret exists:
   ```bash
   kubectl get secret github-ssh-key -n build-deploy
   ```

3. Check KUBECONFIG:
   ```bash
   export KUBECONFIG=/odp-hz.yaml
   kubectl get nodes
   ```

### Build Fails

**Symptom**: Job starts but build fails

**Solutions**:
1. Check job logs in Jenkins console (automatically printed on failure)

2. View full logs:
   ```bash
   kubectl logs job/<component>-build -n build-deploy
   ```

3. Check pod status:
   ```bash
   kubectl get pods -n build-deploy
   kubectl describe pod <pod-name> -n build-deploy
   ```

4. Verify SSH key access:
   ```bash
   kubectl exec -it <pod-name> -n build-deploy -- ls -l /root/.ssh
   ```

### Configuration Error

**Symptom**: Release or component not found

**Solutions**:
1. Check `config/releases.yaml` for release name (case-sensitive)
2. Check `config/components.yaml` for component names
3. Verify YAML syntax is valid

### Dependency Issues

**Symptom**: "Circular dependency or missing dependency detected"

**Solutions**:
1. Review `config/components.yaml` for circular dependencies
2. Ensure all dependency components exist
3. Check dependency names match exactly (case-sensitive)

## Configuration Reference

### Release Configuration (`config/releases.yaml`)

```yaml
releases:
  <RELEASE_NAME>:
    namespace: <k8s-namespace>           # Kubernetes namespace
    github_repo: <git-url>               # GitHub repository URL
    secret_name: <secret-name>           # SSH key secret name
    job_ttl_seconds: <seconds>           # Job cleanup TTL
```

**Note**: `bigtop_branch` and `docker_image` are NOT in the config file. They are passed as Jenkins parameters (`BIGTOP_BRANCH` and `DOCKER_IMAGE`), allowing users to change them easily without modifying the repository.

### Component Configuration (`config/components.yaml`)

```yaml
components:
  <component-name>:
    name: <component-name>               # Component name
    description: <description>           # Human-readable description
    gradle_tasks:                        # Gradle tasks to run
      - <task1>
      - <task2>
    dependencies:                        # List of dependency components
      - <dependency1>
      - <dependency2>
```

## Advanced Usage

### Adding More Components

1. Edit `config/components.yaml`
2. Add component definition with dependencies
3. Commit and push changes
4. Run pipeline - new component is automatically available

### Adding More Releases

1. Edit `config/releases.yaml`
2. Add release configuration
3. Commit and push changes
4. Use new release in `ODP_RELEASE` parameter

### Custom Build Environment

Simply change the Jenkins parameter to use different Docker images:

```
DOCKER_IMAGE: custom-registry/build-env:latest
```

No code changes needed!

## Development

### Testing Configuration Changes

Use dry-run mode to test configuration changes:

```bash
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
  --dry-run
```

### Running Locally

You can run the orchestration locally (requires kubectl access):

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run build
python3 src/main.py \
  --release ODP-3.3.6.3-1 \
  --bigtop-branch rel/ODP-3.3.6.3-1 \
  --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
  --components zookeeper
```

### Extending Functionality

- **k8s_manager.py**: Add Kubernetes operations (e.g., persistent volumes)
- **orchestrator.py**: Modify build logic (e.g., retry mechanisms)
- **main.py**: Add command-line options

## Best Practices

1. **Version Control**: All configuration in Git for traceability
2. **Dry Run First**: Test configuration changes with `--dry-run`
3. **Incremental Builds**: Build single components during development
4. **Monitor Logs**: Watch Jenkins console for real-time progress
5. **Clean Up**: Jobs auto-delete after TTL (default: 6000 seconds)

## Security

- SSH keys stored in Kubernetes secrets (not in code)
- Secrets mounted read-only (mode 0400)
- KUBECONFIG path configurable
- No credentials in Jenkins pipeline or code

## Performance

- **Parallel Builds**: Independent components build simultaneously
- **Fast Feedback**: Status checks every 30 seconds
- **Efficient**: Only builds requested components
- **Scalable**: Kubernetes handles resource allocation

## Support

For issues or questions:

1. Check Jenkins console logs
2. Review Kubernetes job logs
3. Verify configuration files
4. Check this README for troubleshooting

## License

Internal project for ODP builds.

