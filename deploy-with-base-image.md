# Deploy ODP Using Base OS Image (No Custom Image Build Required)

This approach uses standard OS images and installs ODP packages at runtime, eliminating the need to rebuild images for every ODP release.

## Advantages

✅ No custom image builds needed  
✅ Easy to change ODP versions (just update values.yaml)  
✅ Similar to your existing Ansible/Jenkins workflow  
✅ Works with any ODP version  
✅ Smaller base images  

## Quick Deploy

### Step 1: Install Storage Provisioner (if not already done)

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### Step 2: Deploy ODP Cluster

```bash
cd /Users/divesh/Documents/k8s_odp/Jenkins/odp-vm-pod

# Deploy using base image values
helm install prod-cluster helm-chart/ \
  -f helm-chart/values-base-image.yaml \
  --set odp.version="3.3.6.3-1" \
  --set odp.repositories.odp="https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --set odp.repositories.ambari="https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \
  --namespace odp \
  --create-namespace
```

### Step 3: Watch Installation Progress

```bash
# Watch pods starting up
kubectl get pods -n odp -w

# Watch init container installing ODP
kubectl logs -f prod-cluster-master-0 -c install-odp -n odp

# Once init completes, watch main container
kubectl logs -f prod-cluster-master-0 -n odp
```

## Deploy Different ODP Versions

To deploy a different ODP version (no image rebuild needed):

```bash
# ODP 3.2.2.0-2
helm install odp-322 helm-chart/ \
  -f helm-chart/values-base-image.yaml \
  --set odp.version="3.2.2.0-2" \
  --set odp.repositories.odp="https://mirror.odp.acceldata.dev/ODP/centos/3.2.2.0-2/" \
  --namespace odp-322 \
  --create-namespace

# ODP 3.3.6.3-1 (latest)
helm install odp-336 helm-chart/ \
  -f helm-chart/values-base-image.yaml \
  --set odp.version="3.3.6.3-1" \
  --set odp.repositories.odp="https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \
  --namespace odp-336 \
  --create-namespace
```

## Customization

### Change Java Version

```bash
helm install prod-cluster helm-chart/ \
  -f helm-chart/values-base-image.yaml \
  --set odp.java.version="17" \
  --set odp.java.package="java-17-openjdk java-17-openjdk-devel" \
  --namespace odp \
  --create-namespace
```

### Change Cluster Size

```bash
helm install prod-cluster helm-chart/ \
  -f helm-chart/values-base-image.yaml \
  --set nodes.master.count=2 \
  --set nodes.worker.count=5 \
  --namespace odp \
  --create-namespace
```

### Use Different Base OS

```bash
# Ubuntu
helm install prod-cluster helm-chart/ \
  -f helm-chart/values-base-image.yaml \
  --set image.repository="ubuntu" \
  --set image.tag="22.04" \
  --set odp.repositories.odp="https://mirror.odp.acceldata.dev/ODP/ubuntu/3.3.6.3-1/" \
  --namespace odp \
  --create-namespace

# Red Hat UBI
helm install prod-cluster helm-chart/ \
  -f helm-chart/values-base-image.yaml \
  --set image.repository="registry.access.redhat.com/ubi9/ubi" \
  --set image.tag="latest" \
  --namespace odp \
  --create-namespace
```

## Comparison: Image Build vs Runtime Install

| Approach | Build Time | Deploy Time | Version Changes | Image Size |
|----------|-----------|-------------|-----------------|------------|
| **Pre-built Image** | 15-20 min | 2-3 min | Rebuild image | 8-10 GB |
| **Runtime Install** | 0 min | 10-15 min | Update values | 200 MB |

## Verification

```bash
# Check pod status
kubectl get pods -n odp

# Check ODP version installed
kubectl exec prod-cluster-master-0 -n odp -- cat /opt/odp/.installed

# Check Ambari
kubectl exec prod-cluster-master-0 -n odp -- ambari-server --version

# Access Ambari UI
kubectl port-forward svc/prod-cluster-ambari 8080:8080 -n odp
# Open: http://localhost:8080
```

## Upgrade ODP Version

To upgrade an existing cluster to a new ODP version:

```bash
# Update the values
helm upgrade prod-cluster helm-chart/ \
  -f helm-chart/values-base-image.yaml \
  --set odp.version="3.3.6.4-1" \
  --set odp.repositories.odp="https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.4-1/" \
  --namespace odp

# Rolling restart will install new version
kubectl rollout restart statefulset/prod-cluster-master -n odp
kubectl rollout restart statefulset/prod-cluster-worker -n odp
```

## Troubleshooting

### Init container fails

```bash
# View init container logs
kubectl logs prod-cluster-master-0 -c install-odp -n odp

# Common issues:
# - Repository URL unreachable
# - Package conflicts
# - Insufficient disk space
```

### Main container fails to start

```bash
# Check main container logs
kubectl logs prod-cluster-master-0 -n odp

# Check events
kubectl describe pod prod-cluster-master-0 -n odp
```

### ODP services not starting

```bash
# Exec into pod
kubectl exec -it prod-cluster-master-0 -n odp -- /bin/bash

# Check services
systemctl status ambari-server
systemctl status ambari-agent

# Check logs
tail -f /var/log/ambari-server/ambari-server.log
```

## Next Steps

1. **Deploy** - Use the base image approach (no builds needed)
2. **Configure** - Customize ODP components via Ambari UI
3. **Scale** - Add more worker nodes as needed
4. **Upgrade** - Change ODP version in values, rollout restart

This approach gives you the flexibility of your current deployment method while leveraging Kubernetes benefits!
