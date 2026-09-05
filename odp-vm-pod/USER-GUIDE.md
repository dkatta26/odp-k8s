# User Guide: Deploy Your Own ODP Cluster

## For Team Members

Each team member can create their own isolated ODP cluster in Kubernetes.

---

## Step 1: Get Your Namespace

Your admin has created a namespace for you:
```
Namespace: user-<your-name>
Example: user-divesh, user-john
```

---

## Step 2: Set Your Namespace

```bash
# Set your namespace as default
kubectl config set-context --current --namespace=user-<your-name>

# Verify
kubectl config view --minify | grep namespace:
```

---

## Step 3: Deploy Your Cluster

### Option A: Quick Deploy (1 master + 2 workers)

```bash
helm install my-cluster /path/to/helm-chart \
  --set clusterName="$(whoami)-cluster"
```

### Option B: Custom Configuration

Create `my-values.yaml`:
```yaml
clusterName: "divesh-test"

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
  kafka: true
  hbase: false  # Disable if not needed
```

Deploy:
```bash
helm install my-cluster /path/to/helm-chart -f my-values.yaml
```

---

## Step 4: Wait for Cluster to Start

```bash
# Watch pods come up (takes 5-10 minutes)
kubectl get pods -w

# Should see:
# my-cluster-master-0    1/1   Running
# my-cluster-worker-0    1/1   Running
# my-cluster-worker-1    1/1   Running
```

---

## Step 5: Access Ambari UI

```bash
# Forward Ambari port to your laptop
kubectl port-forward my-cluster-master-0 8080:8080
```

Open browser: **http://localhost:8080**

Login:
- Username: `admin`
- Password: `admin`

---

## Step 6: Use Your Cluster

### SSH into pods

```bash
# Master node
kubectl exec -it my-cluster-master-0 -- bash

# Worker node
kubectl exec -it my-cluster-worker-0 -- bash
```

### HDFS Operations

```bash
# Inside master pod
hdfs dfs -mkdir /user/$(whoami)
hdfs dfs -put /tmp/data.txt /user/$(whoami)/
hdfs dfs -ls /user/$(whoami)/
```

### Run Spark Job

```bash
# Inside master pod
spark-submit \
  --class org.apache.spark.examples.SparkPi \
  --master yarn \
  /usr/lib/spark3/examples/jars/spark-examples*.jar \
  10
```

### Hive Query

```bash
# Inside master pod
beeline -u jdbc:hive2://localhost:10000

# In beeline:
CREATE TABLE test (id INT, name STRING);
INSERT INTO test VALUES (1, 'hello'), (2, 'world');
SELECT * FROM test;
```

---

## Step 7: When Done, Clean Up

```bash
# Delete your cluster (keeps namespace)
helm uninstall my-cluster

# Verify deletion
kubectl get all

# Optional: Delete persistent volumes if you want to free storage
kubectl delete pvc --all
```

---

## Quick Reference

### Check Cluster Status

```bash
# List all resources
kubectl get all

# Check pod logs
kubectl logs my-cluster-master-0

# Check pod details
kubectl describe pod my-cluster-master-0

# Check services
kubectl get svc
```

### Resource Usage

```bash
# Check your namespace quota
kubectl describe resourcequota

# Check actual usage
kubectl top pods
```

### Access Services

| Service | Command | URL |
|---------|---------|-----|
| Ambari | `kubectl port-forward my-cluster-master-0 8080:8080` | http://localhost:8080 |
| HDFS NameNode | `kubectl port-forward my-cluster-master-0 9870:9870` | http://localhost:9870 |
| YARN RM | `kubectl port-forward my-cluster-master-0 8088:8088` | http://localhost:8088 |
| Spark History | `kubectl port-forward my-cluster-master-0 18080:18080` | http://localhost:18080 |

---

## Common Issues

### Pod stuck in "Pending"

**Cause:** Not enough resources in namespace

**Fix:** Reduce resource requests or ask admin to increase quota
```bash
kubectl describe resourcequota
```

### Pod stuck in "Init" or "CrashLoopBackOff"

**Cause:** Image pull issues or configuration errors

**Fix:**
```bash
kubectl describe pod my-cluster-master-0
kubectl logs my-cluster-master-0
```

### Ambari UI not accessible

**Cause:** Port-forward not running or Ambari not started

**Fix:**
```bash
# Check if port-forward is running
ps aux | grep kubectl | grep port-forward

# Check Ambari status inside pod
kubectl exec my-cluster-master-0 -- systemctl status ambari-server

# Restart Ambari if needed
kubectl exec my-cluster-master-0 -- systemctl restart ambari-server
```

### Worker nodes not showing in Ambari

**Cause:** Ambari Agent not connected

**Fix:**
```bash
# Check agent on worker
kubectl exec my-cluster-worker-0 -- systemctl status ambari-agent

# Check agent logs
kubectl exec my-cluster-worker-0 -- tail -f /var/log/ambari-agent/ambari-agent.log
```

---

## Getting Help

- Check documentation: `/path/to/README.md`
- Ask admin for quota increase
- Report issues to DevOps team
- Slack channel: #odp-kubernetes

---

## Best Practices

✅ **Name your cluster uniquely** - Use your name as prefix  
✅ **Clean up when done** - Free resources for others  
✅ **Monitor your quota** - Don't exceed namespace limits  
✅ **Start small** - Test with 1 worker before scaling  
✅ **Save your configs** - Keep custom values.yaml files  

---

## Example Workflow

```bash
# Morning: Deploy cluster
helm install dev-cluster helm-chart/

# Wait 5 minutes
kubectl get pods -w

# Work on your tasks
kubectl exec -it dev-cluster-master-0 -- bash
# ... do your work ...

# Evening: Clean up
helm uninstall dev-cluster

# Resources released for others
```

Happy clustering! 🚀
