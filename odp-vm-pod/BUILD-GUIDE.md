# Building ODP Images from Repository URLs

## Overview

ODP images are **NOT pre-built**. You must build them locally by downloading ODP packages from Acceldata's public repositories during the Docker build process.

## Quick Start

### Step 1: Build Image from ODP Repository

```bash
cd odp-vm-pod/docker/

# Build from ODP 3.3.6.3-1 repository
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/"

# Result: Image tagged as acceldata/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11
```

### Step 2: Deploy Using Built Image

```bash
cd ../

./deploy-odp.sh \
  -n 3 \
  -c my-cluster \
  -i rhel9-odp3.3.6.3-1-jdk11
```

---

## Repository URLs

### Public Acceldata Repositories

**ODP 3.3.6.3-1 (Latest):**
```bash
ODP_REPO="https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/"
AMBARI_REPO="https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/"
```

**ODP 3.2.2.0-2:**
```bash
ODP_REPO="https://mirror.odp.acceldata.dev/ODP/centos/3.2.2.0-2/"
AMBARI_REPO="https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/"
```

**Ubuntu Repositories:**
```bash
ODP_REPO="https://mirror.odp.acceldata.dev/ODP/ubuntu/3.3.6.3-1/"
AMBARI_REPO="https://mirror.odp.acceldata.dev/AMBARI/ubuntu/2.7.6.0-1/"
```

---

## Build Examples

### Example 1: Build RHEL 9 + ODP 3.3.6.3 + JDK 11

```bash
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  --os rhel9 \
  --java jdk11
```

### Example 2: Build with JDK 17

```bash
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  --os rhel9 \
  --java jdk17
```

### Example 3: Build Ubuntu Image

```bash
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/ubuntu/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/ubuntu/2.7.6.0-1/" \
  --os ubuntu22 \
  --java jdk11
```

### Example 4: Build from Custom Repository

```bash
./build-from-repo.sh \
  --odp-repo "http://your-internal-mirror.com/ODP/custom/" \
  --ambari-repo "http://your-internal-mirror.com/AMBARI/custom/" \
  --os rhel9 \
  --java jdk11 \
  --tag "custom-dev-build"
```

### Example 5: Build with Mpacks

```bash
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  --mpacks "https://mirror.odp.acceldata.dev/v2/odp/python3/jdk11/3.3.6.2-1/mpacks/" \
  --os rhel9 \
  --java jdk11
```

### Example 6: Build and Push to Registry

```bash
# Set your registry
export REGISTRY="your-registry.io/your-org"

./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  --registry "$REGISTRY" \
  --push
```

---

## Build Parameters Reference

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--odp-repo` | ODP repository URL (required) | `https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/` |
| `--ambari-repo` | Ambari repository URL (required) | `https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/` |
| `--os` | OS type | `rhel9`, `rhel8`, `centos7`, `ubuntu22`, `ubuntu20` |
| `--java` | Java version | `jdk8`, `jdk11`, `jdk17`, `zingjdk11`, `zingjdk17` |
| `--python` | Python version | `2`, `3.11`, `311` |
| `--tag` | Custom image tag | `my-custom-tag` |
| `--registry` | Docker registry | `your-registry.io/your-org` |
| `--push` | Push after build | (flag, no value) |
| `--odp-utils` | ODP utils URL | `https://...` |
| `--mpacks` | Ambari mpacks URL | `https://...` |

---

## Build Matrix (Common Configurations)

### RHEL 9 Based

```bash
# ODP 3.3.6.3 + JDK 11
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  --os rhel9 --java jdk11

# ODP 3.3.6.3 + JDK 17
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  --os rhel9 --java jdk17
```

### RHEL 8 Based

```bash
# ODP 3.2.2.0 + JDK 8
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.2.2.0-2/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  --os rhel8 --java jdk8 --python 2
```

### Ubuntu 22 Based

```bash
# ODP 3.3.6.3 + JDK 11
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/ubuntu/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/ubuntu/2.7.6.0-1/" \
  --os ubuntu22 --java jdk11
```

---

## Testing Built Images

### Local Test

```bash
# Run container
docker run -d --privileged \
  --name test-odp \
  -p 8080:8080 \
  acceldata/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11

# Check services
docker exec test-odp systemctl status ambari-server

# Check versions
docker exec test-odp java -version
docker exec test-odp python --version
docker exec test-odp rpm -qa | grep odp

# Cleanup
docker stop test-odp
docker rm test-odp
```

### Kubernetes Test

```bash
# Deploy test cluster
./deploy-odp.sh \
  -n 1 \
  -c test \
  -i rhel9-odp3.3.6.3-1-jdk11 \
  --namespace test

# Check deployment
kubectl get pods -n test

# Access Ambari
kubectl port-forward test-master-0 8080:8080 -n test
```

---

## Automation: Build Multiple Images

Create a build script for your common configurations:

```bash
#!/bin/bash
# build-all-images.sh

REPOS=(
  "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/"
  "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/"
)

# Build JDK 11
./build-from-repo.sh \
  --odp-repo "${REPOS[0]}" \
  --ambari-repo "${REPOS[1]}" \
  --os rhel9 --java jdk11

# Build JDK 17
./build-from-repo.sh \
  --odp-repo "${REPOS[0]}" \
  --ambari-repo "${REPOS[1]}" \
  --os rhel9 --java jdk17

# Build Ubuntu
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/ubuntu/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/ubuntu/2.7.6.0-1/" \
  --os ubuntu22 --java jdk11
```

---

## Troubleshooting

### Build fails with "cannot download packages"

**Cause:** Repository URL is incorrect or inaccessible

**Fix:**
```bash
# Test repository access
curl -I https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/

# Check URL has trailing slash
# ✓ Correct: https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/
# ✗ Wrong:   https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1
```

### Build fails with "Java not found"

**Cause:** Invalid Java version for OS/ODP combination

**Fix:**
```bash
# Check compatibility:
# ODP 3.2.x → JDK 8 or 11
# ODP 3.3.x → JDK 11 or 17
```

### Image size too large

**Solution:** Use multi-stage build or clean up in same layer:
```dockerfile
RUN yum install -y package && yum clean all
```

---

## CI/CD Integration

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('Build ODP Image') {
            steps {
                sh '''
                    cd odp-vm-pod/docker/
                    ./build-from-repo.sh \
                      --odp-repo "${ODP_REPO_URL}" \
                      --ambari-repo "${AMBARI_REPO_URL}" \
                      --os rhel9 \
                      --java jdk11 \
                      --push
                '''
            }
        }
    }
}
```

### GitLab CI

```yaml
build-image:
  script:
    - cd odp-vm-pod/docker/
    - ./build-from-repo.sh \
        --odp-repo "$ODP_REPO_URL" \
        --ambari-repo "$AMBARI_REPO_URL" \
        --push
```

---

## Summary

**Key Points:**
1. ✅ Images are built locally from repository URLs
2. ✅ Repository URLs point to Acceldata's public mirrors
3. ✅ Build time downloads ODP packages
4. ✅ One build script for all configurations
5. ✅ Easy to customize for your repositories

**Workflow:**
1. Build image → 2. Push to registry → 3. Deploy cluster

```bash
# Build
./build-from-repo.sh --odp-repo "..." --ambari-repo "..."

# Deploy
./deploy-odp.sh -n 3 -c my-cluster -i <tag>
```
