#!/bin/bash
# Complete build and deploy script for ODP on Kubernetes with containerd

set -e

# Configuration
CLUSTER_NODES=("demo.acceldata.com" "demo1.acceldata.com" "demo2.acceldata.com")
IMAGE_NAME="acceldata/odp-vm-node"
IMAGE_TAG="rhel9-odp3.3.6.3-jdk11"
ODP_REPO="https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/"
AMBARI_REPO="https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/"

echo "================================================"
echo "ODP Kubernetes Build & Deploy"
echo "================================================"

# Step 1: Build image locally
echo ""
echo "Step 1: Building Docker image..."
cd odp-vm-pod/docker/

./build-from-repo.sh \
  --odp-repo "$ODP_REPO" \
  --ambari-repo "$AMBARI_REPO" \
  --os rhel9 \
  --java jdk11 \
  --tag "$IMAGE_TAG"

echo "✓ Image built successfully"

# Step 2: Save and compress
echo ""
echo "Step 2: Saving and compressing image..."
cd ../..
docker save ${IMAGE_NAME}:${IMAGE_TAG} -o odp-image.tar
gzip -f odp-image.tar
echo "✓ Image saved: odp-image.tar.gz ($(du -h odp-image.tar.gz | cut -f1))"

# Step 3: Transfer to all nodes
echo ""
echo "Step 3: Transferring to cluster nodes..."
for node in "${CLUSTER_NODES[@]}"; do
  echo "  Transferring to $node..."
  scp -o StrictHostKeyChecking=no odp-image.tar.gz root@${node}:/tmp/ || echo "  Warning: Failed to transfer to $node"
done
echo "✓ Transfer complete"

# Step 4: Import into containerd on all nodes
echo ""
echo "Step 4: Importing into containerd on each node..."
for node in "${CLUSTER_NODES[@]}"; do
  echo "  Importing on $node..."
  ssh -o StrictHostKeyChecking=no root@${node} \
    "gunzip -c /tmp/odp-image.tar.gz | ctr -n k8s.io images import - && rm /tmp/odp-image.tar.gz" \
    || echo "  Warning: Failed to import on $node"
done
echo "✓ Import complete"

# Step 5: Verify images
echo ""
echo "Step 5: Verifying images on nodes..."
for node in "${CLUSTER_NODES[@]}"; do
  echo "  Checking $node..."
  ssh -o StrictHostKeyChecking=no root@${node} "crictl images | grep odp || echo '  Image not found'"
done

# Step 6: Restart pods
echo ""
echo "Step 6: Restarting ODP pods..."
kubectl delete pods -n odp --all 2>/dev/null || echo "  No pods to delete"

echo ""
echo "================================================"
echo "✓ Build and deploy complete!"
echo "================================================"
echo ""
echo "Watch pods starting:"
echo "  kubectl get pods -n odp -w"
echo ""
echo "Check pod status:"
echo "  kubectl get pods -n odp"
echo ""
echo "View logs:"
echo "  kubectl logs -f <pod-name> -n odp"
echo "================================================"

# Cleanup
rm -f odp-image.tar.gz
