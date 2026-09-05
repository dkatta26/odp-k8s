# Local Testing Guide with Kubeadm

## Overview

This guide shows how to test the ODP VM-Pod solution on a local Kubernetes cluster created with kubeadm.

---

## Table of Contents

1. [Setup Local Kubernetes Cluster](#setup-local-kubernetes-cluster)
2. [Install Prerequisites](#install-prerequisites)
3. [Build and Load Images](#build-and-load-images)
4. [Deploy Test Cluster](#deploy-test-cluster)
5. [Verify Deployment](#verify-deployment)
6. [Cleanup](#cleanup)
7. [Troubleshooting](#troubleshooting)

---

## Setup Local Kubernetes Cluster

### Option 1: Single-Node Cluster (Quickest)

**System Requirements:**
- 8GB+ RAM
- 4+ CPU cores
- 50GB+ disk space
- Ubuntu 20.04/22.04 or Rocky Linux 9

**Step 1: Install Container Runtime (containerd)**

```bash
# Install containerd
sudo apt-get update
sudo apt-get install -y containerd

# Configure containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml

# Enable SystemdCgroup
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# Restart containerd
sudo systemctl restart containerd
sudo systemctl enable containerd
```

**Step 2: Install kubeadm, kubelet, kubectl**

```bash
# Add Kubernetes repository
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Install
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

**Step 3: Initialize Kubernetes**

```bash
# Disable swap (required for Kubernetes)
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# Initialize cluster
sudo kubeadm init --pod-network-cidr=10.244.0.0/16

# Setup kubectl for your user
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Verify
kubectl get nodes
```

**Step 4: Remove Taint (Allow pods on control plane)**

```bash
# For single-node testing, allow pods on master
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

**Step 5: Install CNI (Network Plugin)**

```bash
# Install Flannel
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

# Wait for it to be ready
kubectl wait --for=condition=ready pod -l app=flannel -n kube-flannel --timeout=300s

# Verify node is Ready
kubectl get nodes
# Should show: Ready
```

**Step 6: Install Local Storage Provisioner**

```bash
# Install local-path-provisioner for dynamic PVs
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml

# Set as default storage class
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

# Verify
kubectl get storageclass
```

---

### Option 2: Multi-Node Cluster (More Realistic)

If you have multiple VMs or machines:

**On Master Node:**
```bash
# Initialize with your network
sudo kubeadm init --pod-network-cidr=10.244.0.0/16 --apiserver-advertise-address=<MASTER_IP>

# Save the join command shown at the end!
# It looks like:
# kubeadm join <MASTER_IP>:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>
```

**On Worker Nodes:**
```bash
# Run the join command from master output
sudo kubeadm join <MASTER_IP>:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>
```

**Back on Master:**
```bash
# Setup kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install CNI
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

# Verify all nodes are Ready
kubectl get nodes
```

---

## Install Prerequisites

### Install Helm

```bash
# Install Helm 3
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify
helm version
```

### Enable Privileged Pods (Required for systemd)

```bash
# Edit kube-apiserver manifest
sudo vim /etc/kubernetes/manifests/kube-apiserver.yaml

# Add this flag under spec.containers[0].command:
# - --allow-privileged=true

# Wait for API server to restart
kubectl get pods -n kube-system
```

Or create a PodSecurityPolicy:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: privileged
spec:
  privileged: true
  allowPrivilegeEscalation: true
  allowedCapabilities:
  - '*'
  volumes:
  - '*'
  hostNetwork: true
  hostPorts:
  - min: 0
    max: 65535
  hostIPC: true
  hostPID: true
  runAsUser:
    rule: 'RunAsAny'
  seLinux:
    rule: 'RunAsAny'
  supplementalGroups:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
EOF
```

---

## Build and Load Images

### Step 1: Build ODP Image Locally

```bash
cd odp-vm-pod/docker/

# Build image (takes 10-20 minutes)
./build-from-repo.sh \
  --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  --os rhel9 \
  --java jdk11

# Note the image tag: acceldata/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11
```

### Step 2: Make Image Available to Cluster

**If using containerd (default with kubeadm):**

```bash
# Image is already available (built on same machine)
# Verify
sudo ctr -n k8s.io images list | grep odp-vm-node
```

**If using multi-node cluster:**

Option A: Push to local registry
```bash
# On master, start local registry
docker run -d -p 5000:5000 --restart=always --name registry registry:2

# Tag and push
docker tag acceldata/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11 localhost:5000/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11
docker push localhost:5000/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11

# On worker nodes, configure insecure registry
sudo vim /etc/containerd/config.toml
# Add under [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
#   [plugins."io.containerd.grpc.v1.cri".registry.mirrors."localhost:5000"]
#     endpoint = ["http://<MASTER_IP>:5000"]

# Update your config to use:
image:
  repository: "localhost:5000/odp-vm-node"
  tag: "rhel9-odp3.3.6.3-1-jdk11"
```

Option B: Save and load on each node
```bash
# On build machine
docker save acceldata/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11 | gzip > odp-image.tar.gz

# Copy to worker nodes
scp odp-image.tar.gz worker1:/tmp/
scp odp-image.tar.gz worker2:/tmp/

# On each worker node
sudo ctr -n k8s.io images import /tmp/odp-image.tar.gz
```

---

## Deploy Test Cluster

### Create Test Configuration

```bash
cd odp-vm-pod/

# Create minimal test config
cat > test-local.yaml <<EOF
clusterName: "test-local"

image:
  repository: "acceldata/odp-vm-node"
  tag: "rhel9-odp3.3.6.3-1-jdk11"
  pullPolicy: IfNotPresent

nodes:
  master:
    count: 1
    resources:
      requests:
        memory: "4Gi"   # Reduced for local testing
        cpu: "2"        # Reduced for local testing
      limits:
        memory: "6Gi"
        cpu: "3"
    storage:
      size: "20Gi"      # Reduced for local testing
      storageClass: "local-path"

  worker:
    count: 1           # Just 1 worker for testing
    resources:
      requests:
        memory: "4Gi"
        cpu: "2"
      limits:
        memory: "6Gi"
        cpu: "3"
    storage:
      size: "30Gi"
      storageClass: "local-path"

components:
  hdfs: true
  yarn: true
  hive: true
  spark: false       # Disable to save resources
  kafka: false
  hbase: false

services:
  ambari:
    enabled: true
    type: NodePort
    nodePort: 30080

securityContext:
  privileged: true
  capabilities:
    add:
      - SYS_ADMIN
      - NET_ADMIN
EOF
```

### Deploy

```bash
# Create namespace
kubectl create namespace test-odp

# Deploy
helm install test-cluster helm-chart/ \
  -f test-local.yaml \
  --namespace test-odp

# Watch pods come up (takes 5-10 minutes)
kubectl get pods -n test-odp -w
```

---

## Verify Deployment

### Check Pod Status

```bash
# Should see pods running
kubectl get pods -n test-odp

# Expected output:
# test-local-master-0    1/1   Running
# test-local-worker-0    1/1   Running

# Check logs
kubectl logs test-local-master-0 -n test-odp

# Check events
kubectl get events -n test-odp --sort-by='.lastTimestamp'
```

### Access Ambari

**Method 1: Port Forward**
```bash
kubectl port-forward test-local-master-0 8080:8080 -n test-odp

# Open browser: http://localhost:8080
# Login: admin/admin
```

**Method 2: NodePort (if configured)**
```bash
# Get node IP
kubectl get nodes -o wide

# Access
http://<NODE_IP>:30080
```

### Test HDFS

```bash
# SSH into master pod
kubectl exec -it test-local-master-0 -n test-odp -- bash

# Inside pod, test HDFS
hdfs dfs -mkdir /test
hdfs dfs -put /etc/hosts /test/
hdfs dfs -ls /test/
hdfs dfs -cat /test/hosts

# Check HDFS status
hdfs dfsadmin -report
```

### Test YARN

```bash
# Inside master pod
yarn node -list

# Run a test job
yarn jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar pi 2 100
```

### Check Services

```bash
# Inside master pod
systemctl status ambari-server
systemctl status ambari-agent
systemctl list-units --type=service --state=running | grep -E 'hdfs|yarn|ambari'
```

---

## Resource Monitoring

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n test-odp

# Check storage
kubectl get pvc -n test-odp

# Check PV usage
df -h | grep local-path
```

---

## Cleanup

### Remove Test Cluster

```bash
# Delete Helm release
helm uninstall test-cluster -n test-odp

# Delete namespace
kubectl delete namespace test-odp

# Verify PVs are deleted
kubectl get pv
```

### Clean Up Images

```bash
# List images
sudo ctr -n k8s.io images list | grep odp

# Remove if needed
sudo ctr -n k8s.io images rm acceldata/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11
```

### Reset Kubernetes (Complete Wipe)

```bash
# Reset kubeadm
sudo kubeadm reset -f

# Clean up
sudo rm -rf /etc/cni/net.d
sudo rm -rf $HOME/.kube

# Stop kubelet
sudo systemctl stop kubelet
```

---

## Troubleshooting

### Pods Stuck in Pending

**Issue:** Pods don't schedule

**Check:**
```bash
kubectl describe pod test-local-master-0 -n test-odp
```

**Common causes:**

1. **Not enough resources**
   ```bash
   # Check available resources
   kubectl describe nodes
   
   # Fix: Reduce resources in test-local.yaml
   ```

2. **Taints on nodes**
   ```bash
   # Check taints
   kubectl describe nodes | grep Taint
   
   # Remove control-plane taint
   kubectl taint nodes --all node-role.kubernetes.io/control-plane-
   ```

3. **Storage issues**
   ```bash
   # Check PVCs
   kubectl get pvc -n test-odp
   
   # Check storage class
   kubectl get storageclass
   ```

---

### Pods in CrashLoopBackOff

**Check logs:**
```bash
kubectl logs test-local-master-0 -n test-odp
kubectl logs test-local-master-0 -n test-odp --previous
```

**Common issues:**

1. **Privileged mode not allowed**
   ```bash
   # Check pod security
   kubectl describe pod test-local-master-0 -n test-odp | grep -A5 "Security"
   
   # Fix: Enable privileged pods in kube-apiserver
   ```

2. **systemd issues**
   ```bash
   # Check if systemd is running
   kubectl exec test-local-master-0 -n test-odp -- systemctl status
   
   # Check cgroup mount
   kubectl exec test-local-master-0 -n test-odp -- ls -la /sys/fs/cgroup
   ```

---

### Can't Access Ambari

1. **Check if Ambari is running**
   ```bash
   kubectl exec test-local-master-0 -n test-odp -- systemctl status ambari-server
   ```

2. **Restart Ambari**
   ```bash
   kubectl exec test-local-master-0 -n test-odp -- systemctl restart ambari-server
   ```

3. **Check Ambari logs**
   ```bash
   kubectl exec test-local-master-0 -n test-odp -- tail -f /var/log/ambari-server/ambari-server.log
   ```

---

### Storage Full

**Check disk usage:**
```bash
# On Kubernetes node
df -h

# In pod
kubectl exec test-local-master-0 -n test-odp -- df -h
```

**Clean up:**
```bash
# Docker images
docker system prune -a

# Containerd images
sudo ctr -n k8s.io images prune

# Old logs
sudo journalctl --vacuum-time=2d
```

---

## Performance Tips

### For Single-Node Testing

1. **Reduce resources**
   ```yaml
   resources:
     requests:
       memory: "2Gi"  # Minimum
       cpu: "1"       # Minimum
   ```

2. **Disable components**
   ```yaml
   components:
     hdfs: true
     yarn: true
     hive: true
     # Everything else: false
   ```

3. **Smaller storage**
   ```yaml
   storage:
     size: "10Gi"     # Minimum for testing
   ```

### For Multi-Node Testing

1. **Use dedicated worker nodes**
   - Don't schedule workload pods on master

2. **Use local storage**
   - Faster than network storage

3. **Monitor resources**
   ```bash
   watch kubectl top nodes
   watch kubectl top pods -n test-odp
   ```

---

## Alternative: Test with Kind or Minikube

### Using Kind (Kubernetes in Docker)

```bash
# Install kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Create cluster with extra mounts
cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraMounts:
  - hostPath: /sys/fs/cgroup
    containerPath: /sys/fs/cgroup
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        feature-gates: "AllowPrivileged=true"
EOF

# Load image into kind
kind load docker-image acceldata/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11

# Deploy as normal
helm install test helm-chart/ -f test-local.yaml
```

### Using Minikube

```bash
# Start with more resources
minikube start --cpus=4 --memory=8192 --disk-size=50g

# Enable privileged
minikube ssh
sudo vi /etc/kubernetes/manifests/kube-apiserver.yaml
# Add: --allow-privileged=true

# Load image
minikube image load acceldata/odp-vm-node:rhel9-odp3.3.6.3-1-jdk11

# Deploy
helm install test helm-chart/ -f test-local.yaml
```

---

## Summary

**Complete Local Test Flow:**

```bash
# 1. Setup Kubernetes
kubeadm init --pod-network-cidr=10.244.0.0/16
kubectl apply -f flannel.yml
kubectl apply -f local-path-provisioner.yml

# 2. Build image
cd docker/
./build-from-repo.sh --odp-repo "..." --ambari-repo "..."

# 3. Deploy test cluster
cd ../
helm install test helm-chart/ -f test-local.yaml --namespace test-odp --create-namespace

# 4. Verify
kubectl get pods -n test-odp -w
kubectl port-forward test-local-master-0 8080:8080 -n test-odp

# 5. Test
kubectl exec -it test-local-master-0 -n test-odp -- hdfs dfs -ls /

# 6. Cleanup
helm uninstall test -n test-odp
```

**Minimum System Requirements for Testing:**
- 8GB RAM (16GB recommended)
- 4 CPU cores
- 50GB disk space
- Ubuntu 20.04+ or Rocky Linux 9

Good luck with testing! 🚀
