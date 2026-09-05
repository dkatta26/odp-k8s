# ODP VM-Pod: Deploy ODP Clusters in Kubernetes

**Each pod = Complete virtual machine with ALL ODP services**  
**Each user = Separate namespace with their own cluster**

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Kubernetes Cluster                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌───────────────────────────────────────────────────────┐ │
│ │ Namespace: user-divesh                                 │ │
│ │                                                         │ │
│ │ ┌─────────────────────┐  ┌─────────────────────┐     │ │
│ │ │ Pod: master-0       │  │ Pod: worker-0       │     │ │
│ │ │ (Like a VM)         │  │ (Like a VM)         │     │ │
│ │ │                     │  │                     │     │ │
│ │ │ ├─ systemd (PID 1)  │  │ ├─ systemd (PID 1)  │     │ │
│ │ │ ├─ Ambari Server    │  │ ├─ Ambari Agent     │     │ │
│ │ │ ├─ HDFS NameNode    │  │ ├─ HDFS DataNode    │     │ │
│ │ │ ├─ YARN RM          │  │ ├─ YARN NM          │     │ │
│ │ │ ├─ ZooKeeper        │  │ ├─ HBase RS         │     │ │
│ │ │ ├─ Hive Server      │  │ ├─ Kafka Broker     │     │ │
│ │ │ └─ SSH Server       │  │ └─ SSH Server       │     │ │
│ │ └─────────────────────┘  └─────────────────────┘     │ │
│ │                                                         │ │
│ │ Resources: 32 CPU, 64GB RAM, 300GB Storage            │ │
│ └───────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐ │
│ │ Namespace: user-john                                   │ │
│ │ ┌─────────────────────┐  ┌─────────────────────┐     │ │
│ │ │ Pod: master-0       │  │ Pod: worker-0       │     │ │
│ │ │ (His own cluster)   │  │ (His own cluster)   │     │ │
│ │ └─────────────────────┘  └─────────────────────┘     │ │
│ └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### For Users: Deploy Your Own Cluster

```bash
# 1. Get your namespace name (assigned by admin)
NAMESPACE="user-${USER}"

# 2. Create your namespace
kubectl create namespace $NAMESPACE
kubectl config set-context --current --namespace=$NAMESPACE

# 3. Deploy your cluster (1 master, 2 workers)
helm install my-cluster helm-chart/ \
  --set clusterName="my-odp" \
  --set nodes.master.count=1 \
  --set nodes.worker.count=2 \
  --namespace $NAMESPACE

# 4. Wait for pods to be ready (takes 5-10 minutes)
kubectl get pods -w

# 5. Access Ambari Web UI
kubectl port-forward my-odp-master-0 8080:8080

# Open browser: http://localhost:8080
# Default credentials: admin/admin
```

### Quick Deploy Examples

**Minimal cluster (1 node for testing):**
```bash
helm install test helm-chart/ \
  --set clusterName="test-cluster" \
  --set nodes.master.count=1 \
  --set nodes.worker.count=0
```

**Small cluster (1 master + 2 workers):**
```bash
helm install small helm-chart/ \
  --set clusterName="small-cluster" \
  --set nodes.master.count=1 \
  --set nodes.worker.count=2
```

**Large cluster (3 masters + 5 workers for HA):**
```bash
helm install prod helm-chart/ \
  --set clusterName="prod-cluster" \
  --set nodes.master.count=3 \
  --set nodes.worker.count=5
```

## Building the Docker Image

### Prerequisites
- Docker installed
- Access to ODP mirrors
- Network access to `mirror.odp.acceldata.dev`

### Build Steps

```bash
cd docker/

# Build the image
docker build \
  --build-arg ODP_VERSION=3.3.6.3-1 \
  --build-arg AMBARI_VERSION=2.7.6.0-1 \
  -t acceldata/odp-vm-node:3.3.6.3-1 \
  .

# Test the image locally
docker run -d --privileged \
  --name test-odp \
  -p 8080:8080 \
  acceldata/odp-vm-node:3.3.6.3-1

# Check if services started
docker exec test-odp systemctl status ambari-server

# Push to registry
docker push acceldata/odp-vm-node:3.3.6.3-1
```

### Custom ODP Repository URLs

```bash
docker build \
  --build-arg ODP_REPO_URL="https://your-mirror.com/ODP/3.3.6.3-1/" \
  --build-arg AMBARI_REPO_URL="https://your-mirror.com/AMBARI/2.7.6.0-1/" \
  -t your-registry/odp-vm-node:custom \
  .
```

## Configuration

### Cluster Sizing

Edit `helm-chart/values.yaml`:

```yaml
nodes:
  master:
    count: 1  # Number of master pods
    resources:
      requests:
        memory: "8Gi"  # Adjust based on your needs
        cpu: "4"
    storage:
      size: "100Gi"  # HDFS NameNode metadata

  worker:
    count: 2  # Number of worker pods
    resources:
      requests:
        memory: "8Gi"
        cpu: "4"
    storage:
      size: "200Gi"  # HDFS DataNode storage
```

### Component Selection

```yaml
components:
  hdfs: true
  yarn: true
  hive: true
  hbase: true
  kafka: true
  spark: true
  # Enable/disable what you need
```

### External Access

```yaml
services:
  ambari:
    type: LoadBalancer  # or NodePort, or ClusterIP
    port: 8080
```

## Usage

### Accessing Pods

```bash
# SSH into master pod
kubectl exec -it my-odp-master-0 -- /bin/bash

# SSH into worker pod
kubectl exec -it my-odp-worker-0 -- /bin/bash
```

### Checking Services

```bash
# Inside a pod
systemctl status ambari-server
systemctl status ambari-agent

# Check HDFS
sudo -u hdfs hdfs dfsadmin -report

# Check YARN
sudo -u yarn yarn node -list
```

### Using Ambari

1. **Port-forward to access UI:**
   ```bash
   kubectl port-forward my-odp-master-0 8080:8080
   ```

2. **Open browser:** http://localhost:8080

3. **Login:** admin/admin

4. **Configure cluster via Ambari blueprints** (automatic during init)

### Running Jobs

```bash
# Inside master pod
# HDFS operations
hdfs dfs -mkdir /data
hdfs dfs -put file.txt /data/

# Run a MapReduce job
hadoop jar /usr/lib/hadoop-mapreduce/hadoop-mapreduce-examples.jar \
  pi 10 100

# Run Hive query
beeline -u jdbc:hive2://localhost:10000 -n hive
> CREATE TABLE test (id INT, name STRING);
> INSERT INTO test VALUES (1, 'hello');
> SELECT * FROM test;
```

## Multi-User Setup

### For Administrators

Create namespaces with resource quotas for each user:

```bash
# Create script: create-user-namespace.sh
#!/bin/bash
USER=$1

kubectl create namespace user-${USER}

# Apply resource quota
kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: user-quota
  namespace: user-${USER}
spec:
  hard:
    requests.cpu: "32"
    requests.memory: "64Gi"
    requests.storage: "500Gi"
    persistentvolumeclaims: "20"
    pods: "20"
EOF

# Grant user access
kubectl create rolebinding ${USER}-admin \
  --clusterrole=admin \
  --user=${USER}@your-domain.com \
  --namespace=user-${USER}

echo "✓ Namespace user-${USER} created with quotas"
```

Usage:
```bash
./create-user-namespace.sh divesh
./create-user-namespace.sh john
./create-user-namespace.sh alice
```

### For Users

```bash
# Set your default namespace
kubectl config set-context --current --namespace=user-${USER}

# Deploy your cluster
helm install my-cluster helm-chart/

# List your resources
kubectl get all

# Delete your cluster
helm uninstall my-cluster
```

## Comparison with Traditional Deployment

| Feature | VM Deployment | VM-Pod Deployment |
|---------|---------------|-------------------|
| Deployment time | 30-60 minutes | 5-10 minutes |
| Resource isolation | Hypervisor | Kubernetes namespace |
| Scaling | Manual VM provisioning | `kubectl scale` |
| Monitoring | Custom tools | Kubernetes native |
| Cost | Full VM overhead | Container efficiency |
| User isolation | Separate VMs | Separate namespaces |
| Cleanup | Delete VMs | `helm uninstall` |

## Advantages

✅ **Familiar workflow** - Still uses Ambari, same as VM deployment  
✅ **Fast provisioning** - 5-10 min vs 30-60 min for VMs  
✅ **Easy cleanup** - `helm uninstall` removes everything  
✅ **Resource efficiency** - Containers vs full VMs  
✅ **Self-service** - Users deploy their own clusters  
✅ **Isolation** - Each namespace is isolated  
✅ **Cost-effective** - Better resource utilization  

## Troubleshooting

### Pod not starting

```bash
# Check events
kubectl describe pod my-odp-master-0

# Check logs
kubectl logs my-odp-master-0

# Common issue: Privileged mode not allowed
# Fix: Configure PSP or ask admin to enable privileged pods
```

### Services not starting

```bash
# Exec into pod
kubectl exec -it my-odp-master-0 -- bash

# Check systemd status
systemctl status

# Check specific service
systemctl status ambari-server
journalctl -u ambari-server -f

# Restart service
systemctl restart ambari-server
```

### Storage issues

```bash
# Check PVCs
kubectl get pvc

# Check if PVCs are bound
kubectl describe pvc data-my-odp-master-0

# If pending, check storage class
kubectl get storageclass
```

### Ambari Agent not connecting

```bash
# Inside worker pod
cat /etc/ambari-agent/conf/ambari-agent.ini

# Should point to: my-odp-master-0.my-odp-headless.namespace.svc.cluster.local

# Test DNS
nslookup my-odp-master-0.my-odp-headless

# Restart agent
systemctl restart ambari-agent
```

## Limitations

⚠️ **Requires privileged mode** - systemd needs SYS_ADMIN capability  
⚠️ **Storage performance** - Network storage slower than local SSD  
⚠️ **Not for production** - VM-pods are development/testing clusters  
⚠️ **Resource overhead** - systemd + multiple services per pod  

For production, consider the microservices approach (separate services).

## Next Steps

- Integrate with existing Jenkins build pipeline
- Add automated blueprint deployment
- Implement backup/restore for HDFS
- Add monitoring dashboards
- Create CI/CD for image builds

## Support

- Helm chart issues: Check `helm-chart/` directory
- Docker image issues: Check `docker/` directory
- General questions: Contact DevOps team
