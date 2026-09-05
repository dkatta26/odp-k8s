# Getting Started: ODP on Kubernetes

## What We've Created

You now have a complete development methodology and starter code to convert your VM-based ODP deployment to Kubernetes. Here's what's included:

### 📋 Planning Documents
- **`ODP-K8S-MIGRATION-PLAN.md`** - Complete 12-week development plan with architecture decisions, risk mitigation, and success criteria
- **`GETTING-STARTED.md`** (this file) - Quick start guide
- **Task list** - 14 tracked tasks for development progress

### 🎯 Helm Chart Foundation
- **`odp-helm/`** - Production-ready Helm chart structure
  - `Chart.yaml` - Chart metadata
  - `values.yaml` - Comprehensive configuration (37+ components)
  - `templates/` - Kubernetes manifests
    - `_helpers.tpl` - Reusable template functions
    - `namespace.yaml` - Namespace creation
    - `zookeeper-statefulset.yaml` - Complete ZooKeeper implementation (HA-ready)
  - `README.md` - Full documentation with examples

### 🐳 Container Images
- **`docker/hdfs/`** - HDFS containerization example
  - `Dockerfile` - Multi-role HDFS image (NameNode/DataNode/JournalNode)
  - `entrypoint.sh` - Smart startup script with HA, Kerberos, auto-configuration

---

## Next Steps

### Week 1: Set Up Development Environment

```bash
# 1. Set up a local Kubernetes cluster
# Option A: Minikube (recommended for testing)
minikube start --cpus=4 --memory=8192 --disk-size=50g

# Option B: Kind (lightweight)
kind create cluster --name odp-dev

# 2. Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 3. Test the ZooKeeper deployment (already implemented!)
cd odp-helm
helm install test-zk . \
  --set hdfs.enabled=false \
  --set yarn.enabled=false \
  --namespace odp-test \
  --create-namespace

# 4. Verify ZooKeeper is running
kubectl get pods -n odp-test
kubectl logs test-zk-zookeeper-0 -n odp-test
```

### Week 2-3: Build HDFS Images

```bash
# 1. Build the HDFS container
cd docker/hdfs

# Create config templates directory
mkdir -p config-templates

# Copy HDFS configs from your Ansible playbooks
# Look in: ansible-hortonworks/playbooks/roles/*/templates/
cp /path/to/ansible/configs/* config-templates/

# Build the image
docker build -t your-registry/odp-hdfs:3.3.6.2-1 .

# Push to registry
docker push your-registry/odp-hdfs:3.3.6.2-1

# 2. Update values.yaml with your image
sed -i 's|imageRegistry:.*|imageRegistry: "your-registry"|g' ../odp-helm/values.yaml
```

### Week 3-4: Deploy HDFS

```bash
# 1. Create HDFS templates (follow ZooKeeper pattern)
cd odp-helm/templates

# Create these files (see migration plan for guidance):
# - hdfs-namenode-statefulset.yaml
# - hdfs-datanode-statefulset.yaml
# - hdfs-journalnode-statefulset.yaml
# - hdfs-configmap.yaml

# 2. Test HDFS deployment
helm upgrade test-zk . \
  --set hdfs.enabled=true \
  --namespace odp-test

# 3. Verify HDFS is working
kubectl exec -it test-zk-hdfs-namenode-0 -n odp-test -- bash
# Inside pod:
hdfs dfs -mkdir /test
hdfs dfs -ls /
```

---

## Development Workflow

### Daily Iteration Pattern

1. **Morning:** Pick next task from task list
   ```bash
   # See task list in your terminal or:
   cat task-list.txt
   ```

2. **Research Phase (1-2 hours)**
   - Study the component's Ansible role in your Jenkins pipeline
   - Document configuration files needed
   - Identify dependencies

3. **Implementation Phase (3-4 hours)**
   - Write Dockerfile
   - Create Helm templates
   - Update values.yaml

4. **Testing Phase (1-2 hours)**
   ```bash
   # Lint chart
   helm lint odp-helm/

   # Dry-run
   helm install test . --dry-run --debug

   # Deploy to test cluster
   helm upgrade --install test . -n test --create-namespace

   # Verify
   kubectl get all -n test
   ```

5. **Document & Commit**
   ```bash
   git add .
   git commit -m "feat: add [component] support"
   git push
   ```

---

## Component Priority Order

Based on dependencies, build in this order:

1. ✅ **ZooKeeper** (DONE - already in templates/)
2. **HDFS** (Start here)
   - JournalNode first (simpler)
   - NameNode
   - DataNode
   - Test: Create files, read/write
3. **YARN**
   - ResourceManager
   - NodeManager
   - Test: Run a MapReduce job
4. **Hive Metastore** (needs external DB)
5. **HBase**
6. **Spark**
7. **Kafka**
8. **Security Layer**
   - Kerberos KDC
   - cert-manager + SSL
9. **Remaining 30+ services**

---

## Key Architecture Decisions

### 1. StatefulSet vs DaemonSet
- **StatefulSet:** Services needing stable identity (HDFS NameNode, ZooKeeper)
- **DaemonSet:** Services running on every node (HDFS DataNode, YARN NodeManager)

### 2. Configuration Management
- **ConfigMaps:** Store XML configs (core-site.xml, hdfs-site.xml)
- **Secrets:** Store passwords, keytabs, certificates
- **Init Containers:** Render templates, wait for dependencies

### 3. High Availability Pattern
```yaml
# Always use this pattern for HA services
replicas: 2
affinity:
  podAntiAffinity:  # Spread pods across nodes
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: your-service
        topologyKey: kubernetes.io/hostname
```

### 4. Readiness Probes
All services need proper readiness checks:
```yaml
readinessProbe:
  exec:
    command:
    - /bin/bash
    - -c
    - 'curl -f http://localhost:9870 || exit 1'
  initialDelaySeconds: 30
  periodSeconds: 10
```

---

## Testing Strategy

### Unit Tests (Before Deployment)
```bash
# Validate YAML syntax
helm template odp-helm/ | kubectl apply --dry-run=client -f -

# Check for security issues
helm template odp-helm/ | kubesec scan -

# Policy validation (if using OPA/Kyverno)
helm template odp-helm/ | conftest test -
```

### Integration Tests (After Deployment)
```bash
# HDFS tests
kubectl exec -it hdfs-namenode-0 -- hdfs dfs -mkdir /test
kubectl exec -it hdfs-namenode-0 -- hdfs dfs -put /tmp/data.txt /test/
kubectl exec -it hdfs-namenode-0 -- hdfs dfs -cat /test/data.txt

# YARN tests
kubectl exec -it yarn-resourcemanager-0 -- yarn jar \
  /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar \
  pi 2 100

# Failover tests
kubectl delete pod hdfs-namenode-0  # Should auto-recover
```

---

## Common Pitfalls to Avoid

### ❌ Don't Do This
1. **Hardcode IPs/hostnames** - Use Kubernetes DNS
2. **Run as root** - Use dedicated service accounts
3. **Skip resource limits** - Pods will OOM
4. **Ignore storage classes** - PVs won't bind
5. **Deploy all 37 services at once** - Iterate incrementally

### ✅ Do This
1. **Use headless services** for StatefulSets
2. **Set PodDisruptionBudgets** for HA services
3. **Add proper labels** for monitoring
4. **Version your images** with git commit SHAs
5. **Test locally first** with Minikube/Kind

---

## Resources & References

### Kubernetes Documentation
- [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Init Containers](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/)

### Helm Documentation
- [Chart Development Guide](https://helm.sh/docs/chart_template_guide/)
- [Best Practices](https://helm.sh/docs/chart_best_practices/)

### Existing Solutions to Study
- [Stackable Data Platform](https://github.com/stackabletech/stackable-data-platform) - Operators for Hadoop ecosystem
- [Apache YuniKorn](https://yunikorn.apache.org/) - Kubernetes scheduler for big data
- [Pravega Operator](https://github.com/pravega/pravega-operator) - Good StatefulSet patterns

### Your Codebase References
- Original Ansible playbooks: `ansible-hortonworks/playbooks/`
- Configuration templates: `ansible-hortonworks/playbooks/roles/*/templates/`
- Jenkins pipeline: `Jenkinsfile` (for understanding deployment flow)

---

## Questions? Issues?

### Debugging Checklist
```bash
# 1. Check pod status
kubectl get pods -n odp

# 2. Check pod events
kubectl describe pod <pod-name> -n odp

# 3. Check logs
kubectl logs <pod-name> -n odp
kubectl logs <pod-name> -n odp --previous  # If crashed

# 4. Check persistent volumes
kubectl get pv,pvc -n odp

# 5. Check service DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup hdfs-namenode.odp.svc.cluster.local
```

### Get Help
- Review the Migration Plan: `ODP-K8S-MIGRATION-PLAN.md`
- Check Helm chart README: `odp-helm/README.md`
- Look at working examples: `odp-helm/templates/zookeeper-statefulset.yaml`

---

## Success Milestones

Track your progress:

- [ ] Week 1: ZooKeeper running, can create/read znodes
- [ ] Week 4: HDFS operational, can store/retrieve files
- [ ] Week 6: YARN running jobs successfully
- [ ] Week 8: Hive queries working
- [ ] Week 10: Kerberos + SSL fully working
- [ ] Week 12: All 37 components deployable, monitoring active

---

## What Success Looks Like

```bash
# Final goal - one command deploys everything:
helm install prod-cluster odp/odp \
  --namespace production \
  --create-namespace \
  -f values-prod.yaml \
  --timeout 30m

# Result:
# ✅ 150+ pods running across 37 services
# ✅ Kerberos authentication working
# ✅ SSL/TLS on all connections
# ✅ High availability for critical services
# ✅ Monitoring dashboards showing metrics
# ✅ Can run Spark/Hive/Kafka workloads

# Total migration time: 8-12 weeks
# Maintenance: Kubernetes-native operations
# Scale: Add nodes, not VMs
```

Good luck! 🚀
