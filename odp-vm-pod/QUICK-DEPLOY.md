# Quick Deploy Guide - Node Count Selection

Deploy ODP clusters with **any number of nodes** - just like your Jenkins pipeline!

---

## TL;DR - One Command Deploy

```bash
# Choose your node count (1-10+ nodes)
NODE_COUNT=3

helm install my-cluster helm-chart/ \
  --set clusterName="test-$NODE_COUNT" \
  --set nodes.master.count=1 \
  --set nodes.worker.count=$((NODE_COUNT - 1)) \
  --namespace my-namespace
```

---

## Node Count Options (Matching Jenkins Pipeline)

### Option 1: Command Line (Quick)

```bash
# 1 Node (all-in-one)
helm install cluster helm-chart/ \
  --set nodes.master.count=1 \
  --set nodes.worker.count=0

# 2 Nodes (1 master + 1 worker)
helm install cluster helm-chart/ \
  --set nodes.master.count=1 \
  --set nodes.worker.count=1

# 3 Nodes (1 master + 2 workers)
helm install cluster helm-chart/ \
  --set nodes.master.count=1 \
  --set nodes.worker.count=2

# 3 Nodes HA (2 masters + 1 worker)
helm install cluster helm-chart/ \
  --set nodes.master.count=2 \
  --set nodes.worker.count=1

# 4 Nodes (1 master + 3 workers)
helm install cluster helm-chart/ \
  --set nodes.master.count=1 \
  --set nodes.worker.count=3

# 4 Nodes HA (2 masters + 2 workers)
helm install cluster helm-chart/ \
  --set nodes.master.count=2 \
  --set nodes.worker.count=2

# 5 Nodes (1 master + 4 workers)
helm install cluster helm-chart/ \
  --set nodes.master.count=1 \
  --set nodes.worker.count=4

# 10 Nodes (1 master + 9 workers)
helm install cluster helm-chart/ \
  --set nodes.master.count=1 \
  --set nodes.worker.count=9

# 10 Nodes HA (3 masters + 7 workers)
helm install cluster helm-chart/ \
  --set nodes.master.count=3 \
  --set nodes.worker.count=7
```

### Option 2: Use Predefined Values Files

```bash
# We provide ready-made configurations
cd helm-chart/

# 1 node
helm install cluster . -f values-node-counts.yaml --set-string topology=topology-1-node

# 3 nodes
helm install cluster . -f values-node-counts.yaml --set-string topology=topology-3-nodes

# 3 nodes HA
helm install cluster . -f values-node-counts.yaml --set-string topology=topology-3-nodes-ha

# 10 nodes
helm install cluster . -f values-node-counts.yaml --set-string topology=topology-10-nodes
```

### Option 3: Create Custom Values File

```bash
# Create your-cluster.yaml
cat > my-cluster.yaml <<EOF
clusterName: "my-odp"

image:
  repository: "acceldata/odp-vm-node"
  tag: "rhel9-odp3.3.6.3-jdk11"

nodes:
  master:
    count: 2  # Number of master pods
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
    storage:
      size: "100Gi"
  
  worker:
    count: 5  # Number of worker pods
    resources:
      requests:
        memory: "30Gi"
        cpu: "6"
    storage:
      size: "500Gi"
EOF

# Deploy
helm install my-cluster helm-chart/ -f my-cluster.yaml
```

---

## Complete Examples with All Parameters

### Small Dev Cluster (3 nodes, 8GB RAM)

```bash
helm install dev-cluster helm-chart/ \
  --set clusterName="dev-small" \
  --set image.tag="rhel9-odp3.3.6.3-jdk11" \
  --set nodes.master.count=1 \
  --set nodes.master.resources.requests.memory="8Gi" \
  --set nodes.master.resources.requests.cpu="4" \
  --set nodes.worker.count=2 \
  --set nodes.worker.resources.requests.memory="8Gi" \
  --set nodes.worker.resources.requests.cpu="4" \
  --namespace dev
```

### Your Requirement (4 nodes, 30GB RAM, 6 cores)

```bash
helm install prod-cluster helm-chart/ \
  --set clusterName="prod-4node" \
  --set image.tag="rhel9-odp3.3.6.3-jdk11" \
  --set nodes.master.count=1 \
  --set nodes.master.resources.requests.memory="30Gi" \
  --set nodes.master.resources.requests.cpu="6" \
  --set nodes.worker.count=3 \
  --set nodes.worker.resources.requests.memory="30Gi" \
  --set nodes.worker.resources.requests.cpu="6" \
  --namespace prod
```

### Large HA Cluster (10 nodes, 3 masters)

```bash
helm install ha-cluster helm-chart/ \
  --set clusterName="ha-10node" \
  --set image.tag="rhel9-odp3.3.6.3-jdk17" \
  --set nodes.master.count=3 \
  --set nodes.master.resources.requests.memory="30Gi" \
  --set nodes.master.resources.requests.cpu="6" \
  --set nodes.worker.count=7 \
  --set nodes.worker.resources.requests.memory="30Gi" \
  --set nodes.worker.resources.requests.cpu="6" \
  --namespace ha-prod
```

---

## Dynamic Node Count (Scripted)

Create a helper script:

```bash
#!/bin/bash
# deploy-odp.sh - Deploy ODP cluster with any node count

NODE_COUNT=$1
CLUSTER_NAME=${2:-"cluster-$NODE_COUNT"}
NAMESPACE=${3:-"default"}

if [ -z "$NODE_COUNT" ]; then
  echo "Usage: $0 <node-count> [cluster-name] [namespace]"
  echo "Example: $0 5 my-cluster my-namespace"
  exit 1
fi

# Calculate master and worker counts
if [ "$NODE_COUNT" -eq 1 ]; then
  MASTERS=1
  WORKERS=0
elif [ "$NODE_COUNT" -le 4 ]; then
  MASTERS=1
  WORKERS=$((NODE_COUNT - 1))
else
  # For larger clusters, use 2 masters for HA
  MASTERS=2
  WORKERS=$((NODE_COUNT - 2))
fi

echo "Deploying $NODE_COUNT node cluster:"
echo "  Masters: $MASTERS"
echo "  Workers: $WORKERS"
echo "  Namespace: $NAMESPACE"

helm install "$CLUSTER_NAME" helm-chart/ \
  --set clusterName="$CLUSTER_NAME" \
  --set nodes.master.count=$MASTERS \
  --set nodes.worker.count=$WORKERS \
  --namespace "$NAMESPACE" \
  --create-namespace

echo "✓ Cluster deployed!"
kubectl get pods -n "$NAMESPACE"
```

Usage:
```bash
chmod +x deploy-odp.sh

# Deploy 5 node cluster
./deploy-odp.sh 5 my-cluster my-namespace

# Deploy 10 node cluster
./deploy-odp.sh 10 large-cluster test-ns
```

---

## Scaling Existing Clusters

Change node count after deployment:

```bash
# Scale up workers from 3 to 5
helm upgrade my-cluster helm-chart/ \
  --set nodes.worker.count=5 \
  --reuse-values

# Scale down workers from 5 to 3
helm upgrade my-cluster helm-chart/ \
  --set nodes.worker.count=3 \
  --reuse-values

# Or use kubectl directly
kubectl scale statefulset my-cluster-worker --replicas=5
```

---

## Node Count Reference Table

| Node Count | Typical Setup | Use Case |
|------------|---------------|----------|
| 1 | 1 master (all-in-one) | Quick testing, demos |
| 2 | 1 master + 1 worker | Minimal dev environment |
| 3 | 1 master + 2 workers | Standard dev cluster |
| 3 HA | 2 masters + 1 worker | HA testing |
| 4 | 1 master + 3 workers | Small production |
| 4 HA | 2 masters + 2 workers | HA small production |
| 5 | 1 master + 4 workers | Medium cluster |
| 6-9 | 1 master + 5-8 workers | Large cluster |
| 10 | 1 master + 9 workers | Very large cluster |
| 10 HA | 3 masters + 7 workers | HA large production |
| Custom | Any combination | Your specific needs |

---

## Verification

After deployment, check your pods:

```bash
# List all pods
kubectl get pods

# Should see:
# my-cluster-master-0     1/1   Running
# my-cluster-master-1     1/1   Running  (if HA)
# my-cluster-worker-0     1/1   Running
# my-cluster-worker-1     1/1   Running
# ... (based on your worker count)

# Check total node count
kubectl get pods | grep -c Running

# Check resources
kubectl top pods
```

---

## Comparison: Jenkins Pipeline vs Kubernetes

Your current Jenkins pipeline NODE_COUNT parameter vs new deployment:

| Jenkins | Kubernetes Equivalent |
|---------|----------------------|
| `NODE_COUNT=1` | `--set nodes.master.count=1 --set nodes.worker.count=0` |
| `NODE_COUNT=3` | `--set nodes.master.count=1 --set nodes.worker.count=2` |
| `NODE_COUNT=3_HA` | `--set nodes.master.count=2 --set nodes.worker.count=1` |
| `NODE_COUNT=10` | `--set nodes.master.count=1 --set nodes.worker.count=9` |

---

## Tips

✅ **Start small** - Test with 1-3 nodes first  
✅ **Scale gradually** - Add workers as needed  
✅ **Use HA** - 2+ masters for production  
✅ **Monitor resources** - Check if nodes fit in your K8s cluster  
✅ **Name uniquely** - Different clusters need different names  

---

Need help? Check the full **CONFIGURATION-GUIDE.md** for advanced options!
