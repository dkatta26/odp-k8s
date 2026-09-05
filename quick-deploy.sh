#!/bin/bash
# Quick deployment script for ODP on Kubernetes

set -e

CLUSTER_NAME="${1:-prod-cluster}"
NAMESPACE="${2:-odp}"
NODE_COUNT="${3:-3}"

echo "=========================================="
echo "ODP Kubernetes Deployment"
echo "=========================================="
echo "Cluster Name: $CLUSTER_NAME"
echo "Namespace: $NAMESPACE"
echo "Node Count: $NODE_COUNT"
echo "=========================================="

# Step 1: Check prerequisites
echo ""
echo "Step 1: Checking prerequisites..."
if ! kubectl cluster-info &> /dev/null; then
  echo "ERROR: Cannot connect to Kubernetes cluster"
  exit 1
fi
echo "✓ Kubernetes cluster accessible"

# Step 2: Install storage provisioner
echo ""
echo "Step 2: Setting up storage..."
if ! kubectl get storageclass local-path &> /dev/null; then
  echo "Installing local-path provisioner..."
  kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml
  kubectl wait --for=condition=ready pod -l app=local-path-provisioner -n local-path-storage --timeout=120s
  kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
else
  echo "✓ Storage provisioner already installed"
fi

# Step 3: Clean up any existing deployment
echo ""
echo "Step 3: Cleaning up any existing deployment..."
helm uninstall $CLUSTER_NAME -n $NAMESPACE 2>/dev/null || echo "No existing deployment"

# Step 4: Deploy ODP
echo ""
echo "Step 4: Deploying ODP cluster..."
cd "$(dirname "$0")/odp-vm-pod"

MASTERS=1
WORKERS=$((NODE_COUNT - 1))

echo "  Masters: $MASTERS"
echo "  Workers: $WORKERS"

helm install $CLUSTER_NAME helm-chart/ \
  -f helm-chart/values-base-image.yaml \
  --set clusterName="$CLUSTER_NAME" \
  --set nodes.master.count=$MASTERS \
  --set nodes.worker.count=$WORKERS \
  --namespace $NAMESPACE \
  --create-namespace

# Step 5: Watch deployment
echo ""
echo "=========================================="
echo "✓ Deployment started!"
echo "=========================================="
echo ""
echo "Monitoring deployment (this will take ~12-15 minutes)..."
echo "Press Ctrl+C to stop watching (deployment continues in background)"
echo ""

# Show initial status
sleep 5
kubectl get pods -n $NAMESPACE

echo ""
echo "Waiting for init containers to complete (~10 minutes)..."
echo "You can watch detailed logs with:"
echo "  kubectl logs -f $CLUSTER_NAME-master-0 -c install-odp -n $NAMESPACE"
echo ""

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l cluster=$CLUSTER_NAME -n $NAMESPACE --timeout=20m || {
  echo ""
  echo "Pods taking longer than expected. Check status with:"
  echo "  kubectl get pods -n $NAMESPACE"
  echo "  kubectl describe pod $CLUSTER_NAME-master-0 -n $NAMESPACE"
  exit 1
}

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Cluster Status:"
kubectl get pods -n $NAMESPACE
echo ""
kubectl get svc -n $NAMESPACE
echo ""
echo "To access Ambari UI:"
echo "  kubectl port-forward svc/$CLUSTER_NAME-ambari 8080:8080 -n $NAMESPACE"
echo "  Then open: http://localhost:8080"
echo ""
echo "To check ODP version:"
echo "  kubectl exec $CLUSTER_NAME-master-0 -n $NAMESPACE -- cat /opt/odp/.installed"
echo ""
echo "=========================================="
