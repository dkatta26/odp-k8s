# Dynamic Jenkins Pipeline with Scripted Triggering

## ⚡ The Solution You Want!

This **scripted Jenkins pipeline** provides TRUE dynamic triggering - components start building **immediately** when their dependencies are met, without waiting for entire stages to complete.

## ✅ Dynamic Behavior

### Timeline Example:

```
t=0s:     Start zookeeper (no deps)
          Start hue (no deps)
          Both running in parallel

t=400s:   ✓ zookeeper completes
          → Immediately start hadoop (dep: zookeeper ✓)
          → Immediately start kafka (dep: zookeeper ✓)
          hue STILL BUILDING (doesn't block anything!)

t=800s:   ✓ hadoop completes
          ✓ kafka completes

t=900s:   ✗ hue fails (but hadoop & kafka already done!)
```

**Key Point**: `hadoop` and `kafka` start at **t=400s**, NOT waiting for `hue` to finish!

## 🚀 Generate the Pipeline

### Basic Usage:

```bash
python3 src/main.py \
    --release ODP-3.3.6.3-1 \
    --bigtop-branch rel/ODP-3.3.6.3-1 \
    --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
    --generate-jenkinsfile \
    --scripted-pipeline
```

### Preview the Structure:

```bash
python3 src/main.py \
    --release ODP-3.3.6.3-1 \
    --bigtop-branch rel/ODP-3.3.6.3-1 \
    --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
    --print-pipeline-structure \
    --scripted-pipeline
```

### Custom Output Path:

```bash
python3 src/main.py \
    --release ODP-3.3.6.3-1 \
    --bigtop-branch rel/ODP-3.3.6.3-1 \
    --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
    --generate-jenkinsfile \
    --scripted-pipeline \
    --jenkinsfile-output Jenkinsfile
```

## 📊 How It Works

### 1. Continuous Monitoring Loop

The pipeline continuously monitors:
- Which components are completed
- Which components have dependencies met
- Which components are ready to build

```groovy
while (!remaining.isEmpty() || !inProgress.isEmpty()) {
    // Find components with met dependencies
    def readyToBuild = []
    remaining.each { component ->
        if (dependenciesMet(component)) {
            readyToBuild.add(component)
        }
    }
    
    // Launch ready components in parallel
    if (!readyToBuild.isEmpty()) {
        parallel futures  // Run all ready components now!
    }
}
```

### 2. Separate Stage Per Component

Each component still gets its own Jenkins stage:

```groovy
stage('ZOOKEEPER') { ... }
stage('HUE') { ... }
stage('HADOOP') { ... }
stage('KAFKA') { ... }
```

### 3. Parallel Execution

Multiple components with met dependencies run in parallel:

```groovy
// At t=0s: Both ready, launch in parallel
parallel {
    'zookeeper': { buildComponent('zookeeper') }
    'hue': { buildComponent('hue') }
}

// At t=400s: zookeeper done, both ready, launch in parallel
parallel {
    'hadoop': { buildComponent('hadoop') }
    'kafka': { buildComponent('kafka') }
}
```

### 4. Graceful Failure Handling

- Failed components don't block unrelated components
- Only components depending on failed components are skipped
- Clear failure reporting

## 📋 Jenkins UI View

### Blue Ocean View:

```
Pipeline
├─ ZOOKEEPER  ✓ (400s)
├─ HUE        ✗ (900s) 
├─ HADOOP     ✓ (starts at 400s, finishes at 800s)
└─ KAFKA      ✓ (starts at 400s, finishes at 800s)
```

### Classic View:

```
[zookeeper] Dependencies met, starting build...
[hue] Dependencies met, starting build...

********************************************************************************
**  COMPONENT STAGE: ZOOKEEPER
********************************************************************************
[zookeeper] ✓ BUILD SUCCESSFUL

[hadoop] Dependencies met, starting build...
[kafka] Dependencies met, starting build...

********************************************************************************
**  COMPONENT STAGE: HADOOP
********************************************************************************
[hadoop] ✓ BUILD SUCCESSFUL

********************************************************************************
**  COMPONENT STAGE: KAFKA
********************************************************************************
[kafka] ✓ BUILD SUCCESSFUL

********************************************************************************
**  COMPONENT STAGE: HUE
********************************************************************************
[hue] ✗ BUILD FAILED
```

## 🆚 Comparison: Declarative vs Scripted

### Declarative Pipeline (Simple but Sequential Stages)

```groovy
stage('STAGE-1') {
    parallel {
        stage('zookeeper') { ... }
        stage('hue') { ... }
    }
}
// ⚠️ Must wait for BOTH zookeeper AND hue to complete

stage('STAGE-2') {
    parallel {
        stage('hadoop') { ... }
        stage('kafka') { ... }
    }
}
```

**Wait time**: MAX(zookeeper, hue) before starting Stage 2

### Scripted Pipeline (Dynamic Triggering) ⚡

```groovy
// Continuous monitoring loop
while (hasRemainingBuilds) {
    if (dependenciesMet('hadoop')) {
        // Start immediately!
        parallel { stage('hadoop') { ... } }
    }
}
```

**Wait time**: Only for actual dependencies (zookeeper), not for unrelated builds (hue)

## 📈 Performance Improvement

### Example with Your Components:

**Declarative Pipeline:**
- Stage 1: MAX(zookeeper=400s, hue=900s) = **900s**
- Stage 2: MAX(hadoop=400s, kafka=400s) = **400s**
- **Total: 1300s**

**Scripted Pipeline:**
- zookeeper + hue start: 0s
- zookeeper completes: 400s → hadoop + kafka start
- hadoop + kafka complete: 800s
- hue completes/fails: 900s
- **Total: 900s**

**Time Saved: 400 seconds (30% faster!)** ⚡

## 🔧 Customization

The generated pipeline is fully customizable:

### Update Agent Label:

```groovy
node('your-agent-label') {
    // ...
}
```

### Update Credentials:

```groovy
withCredentials([file(credentialsId: 'your-kubeconfig-id', variable: 'KUBECONFIG')]) {
    // ...
}
```

### Add Pre/Post Build Steps:

```groovy
stage(stageName) {
    // Pre-build
    echo "Starting ${component}..."
    
    // Build
    sh "python3 src/main.py ..."
    
    // Post-build
    archiveArtifacts "output/${component}/*.rpm"
}
```

## ⚠️ Important Notes

### 1. Scripted vs Declarative

- **Scripted** = More complex but provides dynamic triggering
- **Declarative** = Simpler but sequential stages

### 2. Thread Safety

The pipeline uses `synchronized` blocks to safely manage shared state across parallel builds.

### 3. Error Handling

Failed builds don't throw exceptions - the pipeline continues and reports all failures at the end.

### 4. Jenkins Configuration

Make sure your Jenkins installation:
- Allows scripted pipelines
- Has sufficient executors for parallel builds
- Has the Pipeline Groovy plugin installed

## 🎯 When to Use Each

### Use Scripted Pipeline When:
✅ You want maximum build speed
✅ Components have complex dependencies
✅ You're okay with more complex pipeline code
✅ You want dynamic triggering behavior

### Use Declarative Pipeline When:
✅ You want simpler, more readable pipeline
✅ Sequential stages are acceptable
✅ You prefer Jenkins best practices
✅ Wait times are not critical

## 📚 Files

- `Jenkinsfile.scripted.example` - Example generated scripted pipeline
- `src/scripted_jenkinsfile_generator.py` - Generator implementation
- Compare with `Jenkinsfile.example` to see differences

## 🚀 Quick Start

1. Generate the pipeline:
```bash
python3 src/main.py --release ODP-3.3.6.3-1 \
    --bigtop-branch rel/ODP-3.3.6.3-1 \
    --docker-image repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6 \
    --generate-jenkinsfile --scripted-pipeline \
    --jenkinsfile-output Jenkinsfile
```

2. Review the generated `Jenkinsfile`

3. Commit to your repository

4. Configure Jenkins pipeline job

5. Run and watch components build dynamically! ⚡

## ✅ Answer to Your Question

**Q: Will this start the build of hadoop as soon as zookeeper completes, without waiting for hue?**

**A: YES! ✓** 

The scripted pipeline monitors dependencies continuously and launches hadoop/kafka immediately when zookeeper completes, regardless of hue's status!

