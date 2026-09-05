# Simple Deployment Guide: One YAML File, One Command

## Overview

**No complex scripts needed!** Just edit one YAML file and deploy.

---

## Quick Start (3 Steps)

### Step 1: Build Docker Image (One Time)

```bash
cd odp-vm-pod/docker/

./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/"

# Note the image tag: rhel9-odp3.3.6.3-1-jdk11
```

### Step 2: Edit Configuration File

```bash
cd ../
cp my-cluster.yaml my-production.yaml
vim my-production.yaml
```

**Edit these sections:**
```yaml
clusterName: "my-odp"         # ← Your cluster name

image:
  tag: "rhel9-odp3.3.6.3-1-jdk11"  # ← Image you built

nodes:
  master:
    count: 1                   # ← Number of masters
    resources:
      requests:
        memory: "30Gi"         # ← Memory per pod
        cpu: "6"               # ← CPU per pod

  worker:
    count: 4                   # ← Number of workers
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
```

### Step 3: Deploy!

```bash
helm install my-cluster helm-chart/ \
  -f my-production.yaml \
  --namespace my-namespace \
  --create-namespace
```

**That's it!** ✅

---

## Using Example Configurations

We provide ready-made examples:

### Small Dev Cluster
```bash
helm install dev helm-chart/ \
  -f examples/example-small-dev.yaml \
  --namespace dev --create-namespace
```

### Your Requirements (5 nodes, 30GB, 6 cores)
```bash
helm install prod helm-chart/ \
  -f examples/example-your-requirements.yaml \
  --namespace prod --create-namespace
```

### HA Cluster (10 nodes)
```bash
helm install ha helm-chart/ \
  -f examples/example-ha-cluster.yaml \
  --namespace prod --create-namespace
```

---

## Configuration File Structure

The YAML file has 9 sections:

```yaml
# 1. CLUSTER IDENTITY
clusterName: "my-cluster"

# 2. IMAGE CONFIGURATION
image:
  tag: "rhel9-odp3.3.6.3-1-jdk11"

# 3. NODE CONFIGURATION
nodes:
  master:
    count: 1
    resources: ...
  worker:
    count: 2
    resources: ...

# 4. ODP REPOSITORY (for reference)
odpConfig:
  odpRepoUrl: "https://..."
  ambariRepoUrl: "https://..."

# 5. COMPONENT SELECTION
components:
  hdfs: true
  yarn: true
  hive: true
  ...

# 6. SECURITY
security:
  kerberos:
    enabled: false
  tls:
    enabled: false

# 7. NETWORK SERVICES
services:
  ambari:
    type: NodePort
    ...

# 8. RESOURCE QUOTAS
resourceQuota:
  enabled: false

# 9. ADVANCED SETTINGS
securityContext: ...
```

---

## Common Configurations

### Minimal Testing (1 node)

```yaml
clusterName: "test"
image:
  tag: "rhel9-odp3.3.6.3-1-jdk11"
nodes:
  master:
    count: 1
    resources:
      requests:
        memory: "8Gi"
        cpu: "4"
  worker:
    count: 0  # No workers
```

### Standard Dev (3 nodes)

```yaml
clusterName: "dev"
nodes:
  master:
    count: 1
    resources:
      requests:
        memory: "8Gi"
        cpu: "4"
  worker:
    count: 2
```

### Your Requirements (5 nodes, 30GB, 6 cores)

```yaml
clusterName: "prod"
nodes:
  master:
    count: 1
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
  worker:
    count: 4
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
```

### Large HA (10 nodes)

```yaml
clusterName: "prod-ha"
nodes:
  master:
    count: 3  # HA
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
  worker:
    count: 7
```

---

## Complete Workflow

### For First Time

```bash
# 1. Build image
cd docker/
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/"

# 2. Copy template
cd ../
cp my-cluster.yaml my-config.yaml

# 3. Edit configuration
vim my-config.yaml
# Edit: clusterName, image.tag, nodes counts, resources

# 4. Deploy
helm install my-cluster helm-chart/ \
  -f my-config.yaml \
  --namespace my-ns \
  --create-namespace

# 5. Wait for pods
kubectl get pods -n my-ns -w

# 6. Access Ambari
kubectl port-forward my-cluster-master-0 8080:8080 -n my-ns
# Open: http://localhost:8080
```

### For Subsequent Deployments

```bash
# Just edit YAML and redeploy
vim my-config.yaml  # Change what you need

helm install cluster2 helm-chart/ \
  -f my-config.yaml \
  --namespace another-ns \
  --create-namespace
```

---

## Updating Clusters

### Change Configuration

```bash
# Edit your YAML
vim my-config.yaml
# Change: node counts, resources, components, etc.

# Upgrade
helm upgrade my-cluster helm-chart/ \
  -f my-config.yaml \
  --namespace my-ns
```

### Scale Workers

```yaml
# In my-config.yaml, change:
nodes:
  worker:
    count: 5  # Was 2, now 5
```

```bash
helm upgrade my-cluster helm-chart/ \
  -f my-config.yaml \
  --namespace my-ns
```

---

## Multi-User Setup

### Admin: Provide Template

```bash
# Give users the template
cp my-cluster.yaml user-template.yaml

# Users edit their copy
# Each user gets unique name and namespace
```

### User Workflow

```bash
# 1. Copy template
cp user-template.yaml john-cluster.yaml

# 2. Edit for your needs
vim john-cluster.yaml
# Set: clusterName: "john-cluster"
# Set: your resource requirements

# 3. Deploy in your namespace
helm install john-cluster helm-chart/ \
  -f john-cluster.yaml \
  --namespace user-john \
  --create-namespace

# 4. Use cluster
kubectl get pods -n user-john
kubectl port-forward john-cluster-master-0 8080:8080 -n user-john

# 5. Cleanup when done
helm uninstall john-cluster --namespace user-john
```

---

## Validation

### Before Deploying

```bash
# Validate YAML syntax
helm template my-cluster helm-chart/ -f my-config.yaml > /dev/null

# See what will be created
helm template my-cluster helm-chart/ -f my-config.yaml | less

# Dry-run
helm install my-cluster helm-chart/ \
  -f my-config.yaml \
  --namespace my-ns \
  --dry-run --debug
```

### After Deploying

```bash
# Check pods
kubectl get pods -n my-ns

# Check services
kubectl get svc -n my-ns

# Check PVCs
kubectl get pvc -n my-ns

# Check resource usage
kubectl top pods -n my-ns
```

---

## Troubleshooting

### Config File Issues

```bash
# Validate YAML
yamllint my-config.yaml

# Check Helm values
helm show values helm-chart/

# Compare with your file
diff <(helm show values helm-chart/) my-config.yaml
```

### Deployment Issues

```bash
# Check Helm release
helm list -n my-ns

# Check release details
helm get all my-cluster -n my-ns

# Check values used
helm get values my-cluster -n my-ns
```

---

## Tips

✅ **Keep your YAML files** - They're your cluster definitions  
✅ **Version control** - Put them in git  
✅ **Name clearly** - Use descriptive cluster names  
✅ **Start small** - Test with 1-3 nodes first  
✅ **Document** - Add comments in YAML for your team  

---

## Summary

**Old Way:**
```bash
./deploy-odp.sh -n 5 -c cluster -m 30Gi --cpu 6 --image tag ...
# Many parameters, easy to forget
```

**New Way:**
```bash
# Edit once, deploy many times
vim my-cluster.yaml
helm install my-cluster helm-chart/ -f my-cluster.yaml --namespace my-ns --create-namespace
```

**Much simpler!** 🎉
