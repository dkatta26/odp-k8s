#!/bin/bash
# ODP Cluster Deployment Script
# Simplifies deployment with node count, resource specs, and version selection

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Defaults
REGISTRY="acceldata"
IMAGE_TAG="rhel9-odp3.3.6.3-jdk11"
MEMORY="30Gi"
CPU="6"
STORAGE_MASTER="100Gi"
STORAGE_WORKER="500Gi"
NAMESPACE=""

usage() {
    cat << EOF
${BLUE}ODP Cluster Deployment Script${NC}

Usage: $0 [OPTIONS]

${GREEN}Required:${NC}
  -n, --nodes COUNT          Total number of nodes (1-20+)
  -c, --cluster NAME         Cluster name

${GREEN}Optional:${NC}
  -m, --memory SIZE          Memory per pod (default: 30Gi)
  --cpu CORES               CPU cores per pod (default: 6)
  -i, --image TAG           Docker image tag (default: rhel9-odp3.3.6.3-jdk11)
  --namespace NS            Kubernetes namespace (default: user-\$USER)
  --ha                      Enable HA mode (multiple masters)
  --storage-master SIZE     Master storage (default: 100Gi)
  --storage-worker SIZE     Worker storage (default: 500Gi)
  --dry-run                 Show what would be deployed without deploying

${GREEN}Image Tags:${NC}
  rhel9-odp3.3.6.3-jdk11    (RHEL 9 + ODP 3.3.6.3 + JDK 11)
  rhel9-odp3.3.6.3-jdk17    (RHEL 9 + ODP 3.3.6.3 + JDK 17)
  rhel8-odp3.2.2.0-jdk8     (RHEL 8 + ODP 3.2.2.0 + JDK 8)
  ubuntu22-odp3.3.6.3-jdk11 (Ubuntu 22 + ODP 3.3.6.3 + JDK 11)

${GREEN}Examples:${NC}
  # 3 node cluster with defaults
  $0 -n 3 -c my-cluster

  # 5 node cluster with 30GB RAM, 6 cores
  $0 -n 5 -c prod -m 30Gi --cpu 6

  # 10 node HA cluster with JDK 17
  $0 -n 10 -c ha-cluster --ha -i rhel9-odp3.3.6.3-jdk17

  # Minimal 1 node test cluster
  $0 -n 1 -c test -m 8Gi --cpu 4

EOF
    exit 1
}

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Parse arguments
NODE_COUNT=""
CLUSTER_NAME=""
HA_MODE=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--nodes)
            NODE_COUNT="$2"
            shift 2
            ;;
        -c|--cluster)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        -m|--memory)
            MEMORY="$2"
            shift 2
            ;;
        --cpu)
            CPU="$2"
            shift 2
            ;;
        -i|--image)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --ha)
            HA_MODE=true
            shift
            ;;
        --storage-master)
            STORAGE_MASTER="$2"
            shift 2
            ;;
        --storage-worker)
            STORAGE_WORKER="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Validate required parameters
if [ -z "$NODE_COUNT" ]; then
    error "Node count is required. Use -n or --nodes"
fi

if [ -z "$CLUSTER_NAME" ]; then
    error "Cluster name is required. Use -c or --cluster"
fi

# Validate node count
if ! [[ "$NODE_COUNT" =~ ^[0-9]+$ ]] || [ "$NODE_COUNT" -lt 1 ]; then
    error "Node count must be a positive integer"
fi

# Set default namespace
if [ -z "$NAMESPACE" ]; then
    NAMESPACE="user-${USER}"
fi

# Calculate master and worker counts
if [ "$NODE_COUNT" -eq 1 ]; then
    MASTER_COUNT=1
    WORKER_COUNT=0
elif [ "$HA_MODE" = true ]; then
    if [ "$NODE_COUNT" -le 3 ]; then
        MASTER_COUNT=2
        WORKER_COUNT=$((NODE_COUNT - 2))
    elif [ "$NODE_COUNT" -le 6 ]; then
        MASTER_COUNT=2
        WORKER_COUNT=$((NODE_COUNT - 2))
    else
        MASTER_COUNT=3
        WORKER_COUNT=$((NODE_COUNT - 3))
    fi
else
    MASTER_COUNT=1
    WORKER_COUNT=$((NODE_COUNT - 1))
fi

# Ensure worker count is not negative
if [ "$WORKER_COUNT" -lt 0 ]; then
    WORKER_COUNT=0
fi

# Display deployment plan
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           ODP CLUSTER DEPLOYMENT PLAN                 ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Cluster Name:    $CLUSTER_NAME"
echo "Namespace:       $NAMESPACE"
echo "Total Nodes:     $NODE_COUNT"
echo "  Masters:       $MASTER_COUNT"
echo "  Workers:       $WORKER_COUNT"
echo "HA Mode:         $HA_MODE"
echo ""
echo "Image:           $REGISTRY/odp-vm-node:$IMAGE_TAG"
echo "Resources/Pod:   $MEMORY RAM, $CPU CPU"
echo "Storage:"
echo "  Master:        $STORAGE_MASTER"
echo "  Worker:        $STORAGE_WORKER"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    warn "Dry-run mode: No actual deployment will occur"
    echo ""
    echo "Helm command that would be executed:"
    echo ""
fi

# Build helm command
HELM_CMD="helm install $CLUSTER_NAME helm-chart/"
HELM_CMD="$HELM_CMD --set clusterName=\"$CLUSTER_NAME\""
HELM_CMD="$HELM_CMD --set image.repository=\"$REGISTRY/odp-vm-node\""
HELM_CMD="$HELM_CMD --set image.tag=\"$IMAGE_TAG\""
HELM_CMD="$HELM_CMD --set nodes.master.count=$MASTER_COUNT"
HELM_CMD="$HELM_CMD --set nodes.master.resources.requests.memory=\"$MEMORY\""
HELM_CMD="$HELM_CMD --set nodes.master.resources.requests.cpu=\"$CPU\""
HELM_CMD="$HELM_CMD --set nodes.master.storage.size=\"$STORAGE_MASTER\""
HELM_CMD="$HELM_CMD --set nodes.worker.count=$WORKER_COUNT"
HELM_CMD="$HELM_CMD --set nodes.worker.resources.requests.memory=\"$MEMORY\""
HELM_CMD="$HELM_CMD --set nodes.worker.resources.requests.cpu=\"$CPU\""
HELM_CMD="$HELM_CMD --set nodes.worker.storage.size=\"$STORAGE_WORKER\""
HELM_CMD="$HELM_CMD --namespace $NAMESPACE"
HELM_CMD="$HELM_CMD --create-namespace"

if [ "$DRY_RUN" = true ]; then
    echo "$HELM_CMD"
    echo ""
    exit 0
fi

# Confirm deployment
read -p "Proceed with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Deploy
log "Creating namespace if it doesn't exist..."
kubectl create namespace "$NAMESPACE" 2>/dev/null || true

log "Deploying cluster..."
eval "$HELM_CMD"

if [ $? -eq 0 ]; then
    log "✓ Deployment initiated successfully!"
    echo ""
    echo "Monitor deployment:"
    echo "  kubectl get pods -n $NAMESPACE -w"
    echo ""
    echo "Access Ambari (once pods are ready):"
    echo "  kubectl port-forward $CLUSTER_NAME-master-0 8080:8080 -n $NAMESPACE"
    echo "  Open: http://localhost:8080 (admin/admin)"
    echo ""
else
    error "Deployment failed!"
fi
