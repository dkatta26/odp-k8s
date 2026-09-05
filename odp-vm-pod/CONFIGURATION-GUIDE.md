# Configuration Guide: Building Custom Images and Sizing Clusters

## Overview

This guide explains how to configure:
1. **Docker Images** - OS, Java, Python, ODP versions
2. **Pod Resources** - Memory, CPU allocation
3. **Storage** - Persistent volume sizing

---

## Part 1: Building Custom Docker Images

### Available Configurations

We support a matrix of combinations:

| Config Name | OS | ODP Version | Java | Python |
|-------------|----|----|------|--------|
| `rhel9-odp3.3.6.3-jdk11` | RHEL 9 | 3.3.6.3-1 | OpenJDK 11 | 3.11 |
| `rhel9-odp3.3.6.3-jdk17` | RHEL 9 | 3.3.6.3-1 | OpenJDK 17 | 3.11 |
| `rhel9-odp3.3.6.3-zingjdk11` | RHEL 9 | 3.3.6.3-1 | Zing JDK 11 | 3.11 |
| `rhel8-odp3.2.2.0-jdk8` | RHEL 8 | 3.2.2.0-2 | OpenJDK 8 | 2 |
| `rhel8-odp3.2.2.0-jdk11` | RHEL 8 | 3.2.2.0-2 | OpenJDK 11 | 2 |
| `centos7-odp3.2.2.0-jdk8` | CentOS 7 | 3.2.2.0-2 | OpenJDK 8 | 2 |
| `ubuntu22-odp3.3.6.3-jdk11` | Ubuntu 22.04 | 3.3.6.3-1 | OpenJDK 11 | 3.11 |
| `ubuntu22-odp3.3.6.3-jdk17` | Ubuntu 22.04 | 3.3.6.3-1 | OpenJDK 17 | 3.11 |
| `ubuntu20-odp3.2.2.0-jdk8` | Ubuntu 20.04 | 3.2.2.0-2 | OpenJDK 8 | 2 |

### Quick Build

```bash
cd odp-vm-pod/docker

# List available configs
./build-images.sh

# Build specific configuration
./build-images.sh rhel9-odp3.3.6.3-jdk11

# Build and push to registry
PUSH=true ./build-images.sh rhel9-odp3.3.6.3-jdk11

# Build all configurations
./build-images.sh all
```

### Manual Build (Custom Configuration)

```bash
docker build \
  -f Dockerfile.template \
  --build-arg BASE_OS="rockylinux:9" \
  --build-arg OS_TYPE="rhel9" \
  --build-arg ODP_VERSION="3.3.6.3-1" \
  --build-arg AMBARI_VERSION="2.7.6.0-1" \
  --build-arg JAVA_VERSION="jdk11" \
  --build-arg PYTHON_VERSION="3.11" \
  --build-arg ODP_REPO_URL="https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --build-arg AMBARI_REPO_URL="https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  -t acceldata/odp-vm-node:custom-tag \
  .
```

### Build Arguments Reference

| Argument | Description | Examples |
|----------|-------------|----------|
| `BASE_OS` | Base container image | `rockylinux:9`, `ubuntu:22.04`, `centos:7` |
| `OS_TYPE` | OS type identifier | `rhel9`, `rhel8`, `centos7`, `ubuntu20`, `ubuntu22` |
| `ODP_VERSION` | ODP version to install | `3.3.6.3-1`, `3.2.2.0-2` |
| `AMBARI_VERSION` | Ambari version | `2.7.6.0-1` |
| `JAVA_VERSION` | Java variant | `jdk8`, `jdk11`, `jdk17`, `zingjdk8`, `zingjdk11`, `zingjdk17` |
| `PYTHON_VERSION` | Python version | `2`, `3.11`, `311` |
| `ODP_REPO_URL` | ODP repository URL | Full URL to ODP repo |
| `AMBARI_REPO_URL` | Ambari repository URL | Full URL to Ambari repo |
| `ZING_JDK_URL` | ZingJDK download URL | Only for ZingJDK builds |

---

## Part 2: Pod Resource Configuration

### Setting Memory and CPU

Edit `values.yaml` or create custom values file:

```yaml
nodes:
  master:
    count: 1
    resources:
      requests:
        memory: "30Gi"  # Minimum guaranteed
        cpu: "6"        # Minimum guaranteed cores
      limits:
        memory: "32Gi"  # Maximum allowed
        cpu: "8"        # Maximum allowed cores
  
  worker:
    count: 3
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
      limits:
        memory: "32Gi"
        cpu: "8"
```

### Resource Units

**Memory:**
- `Mi` = Mebibytes (1024^2 bytes)
- `Gi` = Gibibytes (1024^3 bytes)
- Examples: `4Gi`, `8Gi`, `16Gi`, `30Gi`

**CPU:**
- `1` = 1 full CPU core
- `0.5` or `500m` = Half a core
- Examples: `2`, `4`, `6`, `8`

### Quality of Service (QoS) Classes

```yaml
# Guaranteed QoS - Best performance
requests:
  memory: "30Gi"
  cpu: "6"
limits:
  memory: "30Gi"  # Same as request
  cpu: "6"        # Same as request

# Burstable QoS - Can use more if available
requests:
  memory: "30Gi"
  cpu: "6"
limits:
  memory: "40Gi"  # Higher than request
  cpu: "8"        # Higher than request

# Best Effort - No guarantees (not recommended)
# Omit requests and limits
```

### Resource Examples by Use Case

**Minimal Dev (Testing):**
```yaml
resources:
  requests:
    memory: "4Gi"
    cpu: "2"
  limits:
    memory: "6Gi"
    cpu: "3"
```

**Standard Dev:**
```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "4"
  limits:
    memory: "12Gi"
    cpu: "6"
```

**Large Testing (Your Requirement):**
```yaml
resources:
  requests:
    memory: "30Gi"
    cpu: "6"
  limits:
    memory: "32Gi"
    cpu: "8"
```

**Production-like:**
```yaml
resources:
  requests:
    memory: "64Gi"
    cpu: "16"
  limits:
    memory: "64Gi"
    cpu: "16"
```

---

## Part 3: Storage Configuration

### Setting Storage Size

```yaml
nodes:
  master:
    storage:
      size: "100Gi"              # Size per master pod
      storageClass: "fast-ssd"   # Optional: specific storage class
  
  worker:
    storage:
      size: "500Gi"              # Size per worker pod
      storageClass: "fast-ssd"
```

### Storage Classes

Check available storage classes in your cluster:
```bash
kubectl get storageclass
```

Common types:
- `standard` - Default (usually network storage)
- `fast` / `fast-ssd` - SSD-backed storage
- `local-path` - Local node storage
- `rook-ceph-block` - Ceph storage

### Storage Sizing Guidelines

| Node Type | Data | Recommended Size |
|-----------|------|------------------|
| Master | NameNode metadata | 50-200Gi |
| Master (HA) | JournalNode | 100-300Gi |
| Worker | DataNode data | 500Gi - 2Ti |
| Edge | Client configs | 20-50Gi |

---

## Part 4: Complete Configuration Examples

### Example 1: Your Requirements (30GB RAM, 6 Cores)

**values-custom.yaml:**
```yaml
clusterName: "my-cluster"

image:
  repository: "acceldata/odp-vm-node"
  tag: "rhel9-odp3.3.6.3-jdk11"

nodes:
  master:
    count: 1
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
      limits:
        memory: "30Gi"
        cpu: "6"
    storage:
      size: "100Gi"
      storageClass: "fast-ssd"
  
  worker:
    count: 3
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
      limits:
        memory: "30Gi"
        cpu: "6"
    storage:
      size: "500Gi"
      storageClass: "fast-ssd"

components:
  hdfs: true
  yarn: true
  hive: true
  spark: true
  kafka: true
```

**Deploy:**
```bash
helm install my-cluster helm-chart/ \
  -f values-custom.yaml \
  --namespace user-divesh
```

### Example 2: Multiple Java Versions

Build images for each Java version:
```bash
./build-images.sh rhel9-odp3.3.6.3-jdk8
./build-images.sh rhel9-odp3.3.6.3-jdk11
./build-images.sh rhel9-odp3.3.6.3-jdk17
```

Deploy different clusters:
```bash
# Cluster with JDK 8
helm install cluster-jdk8 helm-chart/ \
  --set image.tag="rhel9-odp3.3.6.3-jdk8" \
  --set clusterName="jdk8-cluster"

# Cluster with JDK 11
helm install cluster-jdk11 helm-chart/ \
  --set image.tag="rhel9-odp3.3.6.3-jdk11" \
  --set clusterName="jdk11-cluster"
```

### Example 3: Different ODP Versions

```bash
# Build both versions
./build-images.sh rhel8-odp3.2.2.0-jdk8
./build-images.sh rhel9-odp3.3.6.3-jdk11

# Deploy ODP 3.2.2.0
helm install odp-3-2 helm-chart/ \
  --set image.tag="rhel8-odp3.2.2.0-jdk8" \
  --namespace odp-32

# Deploy ODP 3.3.6.3
helm install odp-3-3 helm-chart/ \
  --set image.tag="rhel9-odp3.3.6.3-jdk11" \
  --namespace odp-33
```

---

## Part 5: Multi-User Deployment

### Admin: Create User Namespaces with Quotas

**create-user-namespace.sh:**
```bash
#!/bin/bash
USER=$1
MEMORY_QUOTA="${2:-128Gi}"  # Default 128Gi total
CPU_QUOTA="${3:-64}"         # Default 64 cores total

kubectl create namespace user-${USER}

kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: user-quota
  namespace: user-${USER}
spec:
  hard:
    requests.cpu: "${CPU_QUOTA}"
    requests.memory: "${MEMORY_QUOTA}"
    requests.storage: "2Ti"
    persistentvolumeclaims: "20"
    pods: "20"
EOF

echo "✓ Created namespace user-${USER}"
echo "  CPU Quota: ${CPU_QUOTA}"
echo "  Memory Quota: ${MEMORY_QUOTA}"
```

Usage:
```bash
# Create namespace with default quotas
./create-user-namespace.sh divesh

# Create with custom quotas (256GB RAM, 128 cores)
./create-user-namespace.sh john 256Gi 128
```

### User: Deploy with Specific Configuration

Each user can deploy their cluster:

```bash
# User creates custom values
cat > my-cluster-values.yaml <<EOF
clusterName: "divesh-test"

image:
  repository: "acceldata/odp-vm-node"
  tag: "rhel9-odp3.3.6.3-jdk11"

nodes:
  master:
    count: 1
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
  worker:
    count: 2
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
EOF

# Deploy
helm install my-cluster helm-chart/ \
  -f my-cluster-values.yaml \
  --namespace user-divesh
```

---

## Part 6: Validation and Monitoring

### Check Resource Allocation

```bash
# See what's requested
kubectl describe nodes

# See actual usage
kubectl top nodes
kubectl top pods -n user-divesh

# Check namespace quota
kubectl describe resourcequota -n user-divesh
```

### Verify Image Version

```bash
# Check image being used
kubectl get pod my-cluster-master-0 -o jsonpath='{.spec.containers[0].image}'

# Exec into pod and check versions
kubectl exec -it my-cluster-master-0 -- bash

# Inside pod:
java -version
python --version
cat /etc/os-release
rpm -qa | grep odp
```

---

## Quick Reference

### Build Image Matrix

```bash
# See all configs
cd docker && ./build-images.sh

# Build specific config
./build-images.sh <config-name>

# Build all
./build-images.sh all
```

### Deploy with Resources

```bash
helm install CLUSTER helm-chart/ \
  --set image.tag="IMAGE_TAG" \
  --set nodes.master.resources.requests.memory="30Gi" \
  --set nodes.master.resources.requests.cpu="6" \
  --set nodes.worker.count=3
```

### Common Commands

```bash
# Check pod resources
kubectl describe pod POD_NAME

# Update resources (requires pod restart)
kubectl set resources statefulset CLUSTER-master \
  --requests=cpu=6,memory=30Gi \
  --limits=cpu=8,memory=32Gi

# Scale workers
helm upgrade CLUSTER helm-chart/ \
  --set nodes.worker.count=5 \
  --reuse-values
```

---

Need help with a specific configuration? Check `values-examples.yaml` for more examples!
