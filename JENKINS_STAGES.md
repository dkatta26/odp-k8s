# Jenkins Pipeline with Separate Component Stages

## Overview

The build system now generates Jenkins declarative pipelines with **separate stages for each component**, while respecting dependency order. Components with no dependencies on each other run in parallel within dependency stages.

## Features

✅ **Separate Jenkins Stage per Component** - Each component gets its own named stage  
✅ **Automatic Dependency Resolution** - Components grouped by dependency level  
✅ **Parallel Execution** - Independent components run in parallel  
✅ **Clear Logging** - Each component stage clearly marked in Jenkins UI  
✅ **No Hardcoding** - Pipeline generated dynamically from components.yaml  

## Usage

### 1. Generate Jenkinsfile

Generate a Jenkinsfile with all components:

```bash
python3 src/main.py \
    --release ODP-3.3.6.3-1 \
    --bigtop-branch rel/ODP-3.3.6.3-1 \
    --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
    --generate-jenkinsfile \
    --jenkinsfile-output Jenkinsfile
```

Generate Jenkinsfile for specific components:

```bash
python3 src/main.py \
    --release ODP-3.3.6.3-1 \
    --components zookeeper,hadoop,kafka \
    --bigtop-branch rel/ODP-3.3.6.3-1 \
    --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
    --generate-jenkinsfile
```

### 2. View Pipeline Structure

Print the pipeline structure without generating the file:

```bash
python3 src/main.py \
    --release ODP-3.3.6.3-1 \
    --bigtop-branch rel/ODP-3.3.6.3-1 \
    --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
    --print-pipeline-structure
```

Output:
```
================================================================================
JENKINS PIPELINE STRUCTURE
================================================================================

🧱 DEPENDENCY-STAGE-1
  └─ Parallel Stages:
      ├─ stage('hue') (no deps)
      ├─ stage('zookeeper') (no deps)

🧱 DEPENDENCY-STAGE-2
  └─ Parallel Stages:
      ├─ stage('hadoop') (deps: zookeeper)
      ├─ stage('kafka') (deps: zookeeper)
================================================================================
```

### 3. Use in Jenkins

1. Generate the Jenkinsfile:
   ```bash
   python3 src/main.py --release ODP-3.3.6.3-1 \
       --bigtop-branch rel/ODP-3.3.6.3-1 \
       --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
       --generate-jenkinsfile --jenkinsfile-output Jenkinsfile
   ```

2. Review and customize:
   - Update agent label if needed
   - Update kubeconfig credential ID
   - Adjust environment variables

3. Commit to your repository

4. Configure Jenkins pipeline job to use the Jenkinsfile

## Generated Pipeline Structure

### Example with 4 Components

**Components:**
- `zookeeper` (no deps)
- `hue` (no deps)
- `hadoop` (depends on: zookeeper)
- `kafka` (depends on: zookeeper)

**Generated Structure:**

```groovy
pipeline {
    agent {
        label 'k8s-build-agent'
    }
    
    stages {
        stage('🧱 DEPENDENCY-STAGE-1') {
            parallel {
                stage('hue') {
                    steps {
                        script {
                            echo '**  COMPONENT STAGE: HUE'
                            sh 'python3 src/main.py --components hue ...'
                        }
                    }
                }
                stage('zookeeper') {
                    steps {
                        script {
                            echo '**  COMPONENT STAGE: ZOOKEEPER'
                            sh 'python3 src/main.py --components zookeeper ...'
                        }
                    }
                }
            }
        }
        
        stage('🧱 DEPENDENCY-STAGE-2') {
            parallel {
                stage('hadoop') {
                    steps {
                        script {
                            echo '**  COMPONENT STAGE: HADOOP'
                            sh 'python3 src/main.py --components hadoop ...'
                        }
                    }
                }
                stage('kafka') {
                    steps {
                        script {
                            echo '**  COMPONENT STAGE: KAFKA'
                            sh 'python3 src/main.py --components kafka ...'
                        }
                    }
                }
            }
        }
    }
}
```

## Jenkins UI View

In the Jenkins Blue Ocean interface, you'll see:

```
🧱 DEPENDENCY-STAGE-1 (parallel)
  ├─ hue
  └─ zookeeper

🧱 DEPENDENCY-STAGE-2 (parallel)
  ├─ hadoop
  └─ kafka
```

Each component gets its own **clickable stage** with separate logs!

## How It Works

### 1. Dependency Stages (Not Component Stages)

The **DEPENDENCY-STAGE-X** groups components that can run in parallel because they:
- Have the same dependency depth
- Don't depend on each other

### 2. Separate Component Stages

Within each dependency stage, **each component gets its own Jenkins stage**:
- Shows up separately in Jenkins UI
- Has its own logs
- Can be restarted independently
- Clear success/failure status

### 3. Parallel Execution

Jenkins automatically:
- Runs all components in a dependency stage in parallel
- Waits for all components in a stage to complete before moving to next stage
- Shows parallel execution in the UI

### 4. Benefits

✅ **Faster builds** - Parallel execution within dependency stages  
✅ **Clear visibility** - Each component visible in Jenkins UI  
✅ **Easy debugging** - Click on failed component to see its logs  
✅ **Flexible** - Add/remove components without changing Jenkinsfile  
✅ **Dynamic** - Generated from components.yaml configuration  

## Customization

### Edit Generator Settings

Edit `src/jenkinsfile_generator.py` to customize:
- Agent labels
- Credential IDs
- Environment variables
- Stage naming conventions
- Additional build steps

### Add More Components

Simply update `config/components.yaml`:

```yaml
components:
  my-new-component:
    name: my-new-component
    description: "My New Component"
    gradle_tasks:
      - my-new-component-clean
      - my-new-component-rpm
    dependencies:
      - zookeeper
```

Regenerate Jenkinsfile and the new component will be automatically included!

## Troubleshooting

### Component Not Building

Check dependencies in `config/components.yaml`:
```yaml
hadoop:
  dependencies:
    - zookeeper  # Make sure this component exists
```

### Wrong Build Order

The generator uses dependency-based topological sorting. If the order seems wrong:
1. Check component dependencies
2. Run with `--print-pipeline-structure` to verify
3. Components with no dependencies always build first

### Parallel Stages Not Working

Verify in Jenkinsfile:
- `parallel { }` block is present for stages with multiple components
- Each component is wrapped in its own `stage() { }` block

## See Also

- `Jenkinsfile.example` - Example generated Jenkinsfile
- `config/components.yaml` - Component configuration
- `src/jenkinsfile_generator.py` - Generator implementation

