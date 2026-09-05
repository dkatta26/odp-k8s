# ODP on Kubernetes - Complete User Guide

## Welcome! 👋

This guide will help you deploy your own ODP (Open Data Platform) cluster in Kubernetes in just a few steps.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (3 Steps)](#quick-start-3-steps)
3. [Detailed Walkthrough](#detailed-walkthrough)
4. [Common Scenarios](#common-scenarios)
5. [Accessing Your Cluster](#accessing-your-cluster)
6. [Managing Your Cluster](#managing-your-cluster)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Prerequisites

Before you start, make sure you have:

- ✅ Access to a Kubernetes cluster
- ✅ `kubectl` configured and working
- ✅ `helm` installed (version 3.x)
- ✅ A namespace assigned to you (usually `user-<yourname>`)
- ✅ The ODP Docker image built (ask your admin, or see [Build Guide](#building-images))

**Check your access:**
```bash
# Check kubectl works
kubectl get nodes

# Check helm works
helm version

# Check your namespace
kubectl get namespace user-$USER
```

---

## Quick Start (3 Steps)

### Step 1: Get the Template

```bash
# Clone or download the project
cd odp-vm-pod/

# Copy the template
cp my-cluster.yaml my-config.yaml
```

### Step 2: Edit Configuration

```bash
vim my-config.yaml
```

**Change these key settings:**
```yaml
# Line 6: Your cluster name
clusterName: "yourname-cluster"

# Line 14: Image tag (ask admin which to use)
tag: "rhel9-odp3.3.6.3-1-jdk11"

# Line 24: Number of master pods
count: 1

# Line 28-30: Resources per master pod
memory: "30Gi"  # RAM per pod
cpu: "6"        # CPU cores per pod

# Line 38: Number of worker pods
count: 4
```

### Step 3: Deploy!

```bash
helm install my-cluster helm-chart/ \
  -f my-config.yaml \
  --namespace user-$USER \
  --create-namespace
```

**Wait for pods to start (5-10 minutes):**
```bash
kubectl get pods -n user-$USER -w
```

**Access Ambari:**
```bash
kubectl port-forward my-cluster-master-0 8080:8080 -n user-$USER
```
Open browser: http://localhost:8080 (login: admin/admin)

---

## Detailed Walkthrough

### Understanding the Configuration File

The `my-cluster.yaml` file has 9 sections. Here's what each does:

#### Section 1: Cluster Identity
```yaml
clusterName: "my-odp-cluster"
```
- **What it is:** The name of your cluster
- **Change to:** Your preferred name (e.g., "john-dev", "team-prod")
- **Rules:** Lowercase, alphanumeric, hyphens only

#### Section 2: Image Configuration
```yaml
image:
  repository: "acceldata/odp-vm-node"
  tag: "rhel9-odp3.3.6.3-1-jdk11"
```
- **What it is:** Which ODP image to use
- **Common tags:**
  - `rhel9-odp3.3.6.3-1-jdk11` - RHEL 9 + JDK 11
  - `rhel9-odp3.3.6.3-1-jdk17` - RHEL 9 + JDK 17
  - `ubuntu22-odp3.3.6.3-1-jdk11` - Ubuntu 22 + JDK 11
- **Ask your admin** which tag to use

#### Section 3: Node Configuration
```yaml
nodes:
  master:
    count: 1                    # How many master pods
    resources:
      requests:
        memory: "30Gi"          # RAM per master pod
        cpu: "6"                # CPU cores per master pod
    storage:
      size: "100Gi"             # Disk space per master pod
  
  worker:
    count: 4                    # How many worker pods
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
    storage:
      size: "500Gi"             # Disk space per worker pod
```

**How to decide node counts:**
- **1 node:** Testing only (1 master, 0 workers)
- **3 nodes:** Small dev (1 master + 2 workers)
- **5 nodes:** Standard dev (1 master + 4 workers)
- **10 nodes:** Large cluster (1 master + 9 workers)
- **10 nodes HA:** Production (3 masters + 7 workers)

**Resource sizing guide:**
| Use Case | Memory/Pod | CPU/Pod | Typical Count |
|----------|-----------|---------|---------------|
| Quick test | 4-8Gi | 2-4 | 1-2 nodes |
| Development | 8-16Gi | 4-6 | 3-5 nodes |
| Testing | 30Gi | 6 | 5-10 nodes |
| Production | 64Gi+ | 16+ | 10+ nodes |

#### Section 4: ODP Repository (Reference Only)
```yaml
odpConfig:
  odpRepoUrl: "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/"
  ambariRepoUrl: "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/"
```
- **What it is:** Where ODP packages came from (for reference)
- **Do you need to change it?** Usually no (this is set during image build)

#### Section 5: Component Selection
```yaml
components:
  hdfs: true        # Hadoop file system
  yarn: true        # Resource manager
  hive: true        # SQL engine
  spark: true       # Processing engine
  kafka: true       # Messaging
  hbase: true       # NoSQL database
  # ... more components
```
- **What it is:** Which ODP services to enable
- **Defaults:** Core components (HDFS, YARN, Hive) are enabled
- **Change to:** Enable only what you need to save resources

#### Section 6: Security
```yaml
security:
  kerberos:
    enabled: false  # Enable Kerberos authentication
  tls:
    enabled: false  # Enable SSL/TLS encryption
```
- **What it is:** Security features
- **For dev/test:** Usually keep disabled
- **For production:** Ask admin to help enable

#### Section 7: Network Services
```yaml
services:
  ambari:
    enabled: true
    type: NodePort      # How to access Ambari
    nodePort: 30080     # Port number
```
- **Types:**
  - `ClusterIP` - Access only from inside Kubernetes
  - `NodePort` - Access via node IP + port (default)
  - `LoadBalancer` - Get external IP (if available)
- **Usually don't need to change**

#### Sections 8-9: Advanced (Skip for Now)
- Resource quotas
- Security contexts
- **Usually keep defaults**

---

## Common Scenarios

### Scenario 1: Small Dev Cluster (Quick Testing)

**Your needs:** 3 nodes, minimal resources, just test basic functionality

**Configuration:**
```yaml
clusterName: "test-cluster"

image:
  tag: "rhel9-odp3.3.6.3-1-jdk11"

nodes:
  master:
    count: 1
    resources:
      requests:
        memory: "8Gi"
        cpu: "4"
    storage:
      size: "50Gi"
  
  worker:
    count: 2
    resources:
      requests:
        memory: "8Gi"
        cpu: "4"
    storage:
      size: "100Gi"

components:
  hdfs: true
  yarn: true
  hive: true
  spark: true
  # Others: false
```

**Deploy:**
```bash
helm install test helm-chart/ -f my-config.yaml --namespace user-$USER --create-namespace
```

**Resources used:** 24GB RAM, 12 CPU cores

---

### Scenario 2: Standard Dev Cluster (Your Daily Work)

**Your needs:** 5 nodes, 30GB RAM, 6 cores per pod (your requirement!)

**Use ready-made example:**
```bash
helm install my-cluster helm-chart/ \
  -f examples/example-your-requirements.yaml \
  --namespace user-$USER \
  --create-namespace
```

**Or customize:**
```yaml
clusterName: "dev-cluster"

image:
  tag: "rhel9-odp3.3.6.3-1-jdk11"

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

components:
  hdfs: true
  yarn: true
  hive: true
  spark: true
  kafka: true
  hbase: true
```

**Resources used:** 150GB RAM, 30 CPU cores

---

### Scenario 3: Large Testing Cluster

**Your needs:** 10 nodes, test at scale

```yaml
clusterName: "large-test"

nodes:
  master:
    count: 1
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
  
  worker:
    count: 9
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
```

**Resources used:** 300GB RAM, 60 CPU cores

---

### Scenario 4: High Availability Cluster

**Your needs:** Production-ready with HA

```bash
# Use ready-made HA example
helm install ha-cluster helm-chart/ \
  -f examples/example-ha-cluster.yaml \
  --namespace user-$USER \
  --create-namespace
```

**This gives you:**
- 3 master pods (HA)
- 7 worker pods
- Total: 10 nodes

---

## Accessing Your Cluster

### 1. Check Deployment Status

```bash
# See all pods
kubectl get pods -n user-$USER

# Watch pods come up
kubectl get pods -n user-$USER -w

# Expected output (for 5-node cluster):
# my-cluster-master-0    1/1   Running
# my-cluster-worker-0    1/1   Running
# my-cluster-worker-1    1/1   Running
# my-cluster-worker-2    1/1   Running
# my-cluster-worker-3    1/1   Running
```

### 2. Access Ambari Web UI

**Method 1: Port Forward (Easiest)**
```bash
# Forward Ambari port to your laptop
kubectl port-forward my-cluster-master-0 8080:8080 -n user-$USER

# Open browser
http://localhost:8080

# Login
Username: admin
Password: admin
```

**Method 2: NodePort (If configured)**
```bash
# Get node IP
kubectl get nodes -o wide

# Get NodePort
kubectl get svc my-cluster-ambari -n user-$USER

# Access
http://<node-ip>:30080
```

### 3. SSH into Pods

```bash
# SSH into master pod
kubectl exec -it my-cluster-master-0 -n user-$USER -- bash

# Inside pod, you can use all ODP commands:
hdfs dfs -ls /
yarn node -list
beeline -u jdbc:hive2://localhost:10000
```

### 4. Access Other UIs

**HDFS NameNode:**
```bash
kubectl port-forward my-cluster-master-0 9870:9870 -n user-$USER
# Open: http://localhost:9870
```

**YARN ResourceManager:**
```bash
kubectl port-forward my-cluster-master-0 8088:8088 -n user-$USER
# Open: http://localhost:8088
```

**Spark History Server:**
```bash
kubectl port-forward my-cluster-master-0 18080:18080 -n user-$USER
# Open: http://localhost:18080
```

---

## Managing Your Cluster

### View Cluster Information

```bash
# List all resources
kubectl get all -n user-$USER

# Check resource usage
kubectl top pods -n user-$USER

# Check storage
kubectl get pvc -n user-$USER

# Check services
kubectl get svc -n user-$USER
```

### Scale Your Cluster

**Add more workers:**
```yaml
# Edit your config file
nodes:
  worker:
    count: 6  # Was 4, now 6
```

```bash
# Apply changes
helm upgrade my-cluster helm-chart/ \
  -f my-config.yaml \
  -n user-$USER
```

**Or scale directly:**
```bash
kubectl scale statefulset my-cluster-worker --replicas=6 -n user-$USER
```

### Update Configuration

```bash
# Edit your config
vim my-config.yaml

# Apply changes
helm upgrade my-cluster helm-chart/ \
  -f my-config.yaml \
  -n user-$USER

# Check status
kubectl rollout status statefulset my-cluster-master -n user-$USER
```

### Stop Your Cluster (Save Resources)

```bash
# Scale to 0 (stops all workers)
kubectl scale statefulset my-cluster-worker --replicas=0 -n user-$USER

# Or delete entirely (can redeploy later)
helm uninstall my-cluster -n user-$USER
```

### Restart Your Cluster

```bash
# If you stopped it:
kubectl scale statefulset my-cluster-worker --replicas=4 -n user-$USER

# If you deleted it:
helm install my-cluster helm-chart/ -f my-config.yaml -n user-$USER
```

### Delete Your Cluster

```bash
# Delete everything
helm uninstall my-cluster -n user-$USER

# Also delete persistent volumes (if you want to free storage)
kubectl delete pvc --all -n user-$USER

# Verify deletion
kubectl get all -n user-$USER
```

---

## Troubleshooting

### Pods Not Starting

**Check pod status:**
```bash
kubectl get pods -n user-$USER
kubectl describe pod my-cluster-master-0 -n user-$USER
```

**Common issues:**

**1. ImagePullBackOff**
```
Error: Failed to pull image
```
**Fix:** Image doesn't exist. Ask admin which image tag to use.

**2. Pending**
```
Status: Pending
Reason: Insufficient memory/cpu
```
**Fix:** Not enough resources in cluster. Reduce your requests:
```yaml
resources:
  requests:
    memory: "16Gi"  # Was 30Gi
    cpu: "4"        # Was 6
```

**3. CrashLoopBackOff**
```bash
# Check logs
kubectl logs my-cluster-master-0 -n user-$USER
kubectl logs my-cluster-master-0 -n user-$USER --previous
```
**Fix:** Usually a configuration issue. Contact admin.

### Can't Access Ambari

**Check if pod is ready:**
```bash
kubectl get pods -n user-$USER
# Should show: my-cluster-master-0    1/1   Running
```

**Check if port-forward is running:**
```bash
ps aux | grep port-forward
```

**Restart port-forward:**
```bash
# Kill existing
pkill -f "port-forward.*8080"

# Start new
kubectl port-forward my-cluster-master-0 8080:8080 -n user-$USER
```

**Check Ambari inside pod:**
```bash
kubectl exec my-cluster-master-0 -n user-$USER -- systemctl status ambari-server
```

### Services Not Working

**Inside master pod:**
```bash
kubectl exec -it my-cluster-master-0 -n user-$USER -- bash

# Check all services
systemctl list-units --type=service --state=running

# Check specific service
systemctl status ambari-server
systemctl status ambari-agent

# Restart if needed
systemctl restart ambari-server
```

### Out of Resources

**Check your quota:**
```bash
kubectl describe resourcequota -n user-$USER
```

**See actual usage:**
```bash
kubectl top pods -n user-$USER
```

**Fix:** Reduce resources or delete other clusters:
```bash
helm list -n user-$USER
helm uninstall old-cluster -n user-$USER
```

### Storage Issues

**Check PVCs:**
```bash
kubectl get pvc -n user-$USER
```

**If PVC is Pending:**
```
Status: Pending
Reason: Waiting for storage class
```
**Fix:** Ask admin about available storage classes:
```bash
kubectl get storageclass
```

---

## FAQ

### Q: Which image tag should I use?
**A:** Ask your admin. Common options:
- `rhel9-odp3.3.6.3-1-jdk11` - Most common
- `rhel9-odp3.3.6.3-1-jdk17` - If you need JDK 17

### Q: How many nodes should I create?
**A:** Depends on your use case:
- Testing: 1-3 nodes
- Development: 3-5 nodes
- Heavy testing: 5-10 nodes

### Q: How much resources per pod?
**A:** Start with:
- Development: 8Gi RAM, 4 CPU
- Testing: 30Gi RAM, 6 CPU
- Production: 64Gi+ RAM, 16+ CPU

### Q: Can I have multiple clusters?
**A:** Yes! Just use different names:
```bash
helm install cluster1 helm-chart/ -f config1.yaml -n user-$USER
helm install cluster2 helm-chart/ -f config2.yaml -n user-$USER
```

### Q: How do I save costs?
**A:**
1. Delete clusters when not in use
2. Use smaller resources
3. Scale workers to 0 when not needed
4. Enable only components you use

### Q: Can I share my cluster with teammates?
**A:** Yes, but they need access to your namespace. Ask admin to grant them access:
```bash
# They can then access:
kubectl port-forward my-cluster-master-0 8080:8080 -n user-you
```

### Q: How long does deployment take?
**A:** 5-10 minutes typically. Watch with:
```bash
kubectl get pods -n user-$USER -w
```

### Q: What if I need help?
**A:**
1. Check this guide
2. Check pod logs: `kubectl logs POD_NAME -n user-$USER`
3. Ask admin or post in your team channel

---

## Cheat Sheet

```bash
# Deploy cluster
helm install my-cluster helm-chart/ -f my-config.yaml --namespace user-$USER --create-namespace

# Check status
kubectl get pods -n user-$USER

# Access Ambari
kubectl port-forward my-cluster-master-0 8080:8080 -n user-$USER
# Open: http://localhost:8080

# SSH into pod
kubectl exec -it my-cluster-master-0 -n user-$USER -- bash

# Scale workers
kubectl scale statefulset my-cluster-worker --replicas=6 -n user-$USER

# Update cluster
helm upgrade my-cluster helm-chart/ -f my-config.yaml -n user-$USER

# Delete cluster
helm uninstall my-cluster -n user-$USER

# Check resource usage
kubectl top pods -n user-$USER

# Get logs
kubectl logs my-cluster-master-0 -n user-$USER
```

---

## Need More Help?

- **Documentation:** Check other .md files in this directory
- **Examples:** See `examples/` folder for ready-made configs
- **Admin:** Contact your Kubernetes admin
- **Team Channel:** Post in your team Slack/chat

---

**Happy clustering!** 🎉
