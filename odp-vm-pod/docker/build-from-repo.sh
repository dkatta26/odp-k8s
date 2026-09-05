#!/bin/bash
# Build ODP VM-Pod images from repository URLs
# Downloads ODP packages from public repositories during build

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Defaults
REGISTRY="${REGISTRY:-acceldata}"
PUSH="${PUSH:-false}"
BASE_OS="rockylinux:9"
OS_TYPE="rhel9"
JAVA_VERSION="jdk11"
PYTHON_VERSION="3.11"
IMAGE_TAG=""

usage() {
    cat << EOF
${BLUE}Build ODP VM-Pod Images from Repository URLs${NC}

Usage: $0 [OPTIONS]

${GREEN}Required:${NC}
  --odp-repo URL           ODP repository URL
  --ambari-repo URL        Ambari repository URL

${GREEN}Optional:${NC}
  --os OS_TYPE            OS type (rhel9, rhel8, centos7, ubuntu22, ubuntu20)
                          Default: rhel9
  --java VERSION          Java version (jdk8, jdk11, jdk17, zingjdk11, etc.)
                          Default: jdk11
  --python VERSION        Python version (2, 3.11, 311)
                          Default: 3.11
  --tag TAG              Custom image tag (auto-generated if not provided)
  --registry REGISTRY     Docker registry (default: acceldata)
  --push                  Push image to registry after build
  --odp-utils URL         ODP utils repository URL (optional)
  --mpacks URL            Ambari mpacks URL (optional)
  --zing-url URL          ZingJDK download URL (for zingjdk builds)

${GREEN}Examples:${NC}

  # Build from ODP 3.3.6.3-1 repository
  $0 \\
    --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \\
    --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \\
    --os rhel9 --java jdk11

  # Build from custom repository
  $0 \\
    --odp-repo "http://your-mirror.com/ODP/custom/" \\
    --ambari-repo "http://your-mirror.com/AMBARI/custom/" \\
    --tag "custom-build"

  # Build Ubuntu image
  $0 \\
    --odp-repo "https://mirror.odp.acceldata.dev/ODP/ubuntu/3.3.6.3-1/" \\
    --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/ubuntu/2.7.6.0-1/" \\
    --os ubuntu22 --java jdk11

  # Build and push to registry
  $0 \\
    --odp-repo "https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/" \\
    --ambari-repo "https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/" \\
    --push

EOF
    exit 1
}

# Parse arguments
ODP_REPO_URL=""
AMBARI_REPO_URL=""
ODP_UTILS_URL=""
MPACKS_URL=""
ZING_URL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --odp-repo)
            ODP_REPO_URL="$2"
            shift 2
            ;;
        --ambari-repo)
            AMBARI_REPO_URL="$2"
            shift 2
            ;;
        --odp-utils)
            ODP_UTILS_URL="$2"
            shift 2
            ;;
        --mpacks)
            MPACKS_URL="$2"
            shift 2
            ;;
        --os)
            OS_TYPE="$2"
            shift 2
            ;;
        --java)
            JAVA_VERSION="$2"
            shift 2
            ;;
        --python)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --zing-url)
            ZING_URL="$2"
            shift 2
            ;;
        --push)
            PUSH="true"
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
if [ -z "$ODP_REPO_URL" ]; then
    error "ODP repository URL is required. Use --odp-repo"
fi

if [ -z "$AMBARI_REPO_URL" ]; then
    error "Ambari repository URL is required. Use --ambari-repo"
fi

# Set base OS image based on OS type
case "$OS_TYPE" in
    rhel9)
        BASE_OS="rockylinux:9"
        ;;
    rhel8)
        BASE_OS="rockylinux:8"
        ;;
    centos7)
        BASE_OS="centos:7"
        ;;
    ubuntu22)
        BASE_OS="ubuntu:22.04"
        PYTHON_VERSION="3.11"
        ;;
    ubuntu20)
        BASE_OS="ubuntu:20.04"
        ;;
    *)
        error "Unknown OS type: $OS_TYPE. Use: rhel9, rhel8, centos7, ubuntu22, ubuntu20"
        ;;
esac

# Auto-generate image tag if not provided
if [ -z "$IMAGE_TAG" ]; then
    # Extract ODP version from URL
    ODP_VERSION=$(echo "$ODP_REPO_URL" | grep -oP '(\d+\.){2,}\d+-\d+' | head -1 || echo "custom")
    IMAGE_TAG="${OS_TYPE}-odp${ODP_VERSION}-${JAVA_VERSION}"
fi

FULL_IMAGE="${REGISTRY}/odp-vm-node:${IMAGE_TAG}"

# Display build plan
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           ODP IMAGE BUILD PLAN                        ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Image Tag:         $FULL_IMAGE"
echo "Base OS:           $BASE_OS ($OS_TYPE)"
echo "Java:              $JAVA_VERSION"
echo "Python:            $PYTHON_VERSION"
echo ""
echo "Repositories:"
echo "  ODP:             $ODP_REPO_URL"
echo "  Ambari:          $AMBARI_REPO_URL"
[ -n "$ODP_UTILS_URL" ] && echo "  ODP Utils:       $ODP_UTILS_URL"
[ -n "$MPACKS_URL" ] && echo "  Mpacks:          $MPACKS_URL"
[ -n "$ZING_URL" ] && echo "  ZingJDK:         $ZING_URL"
echo ""
echo "Push to registry:  $PUSH"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Confirm build
read -p "Proceed with build? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Build cancelled."
    exit 0
fi

log "Starting build..."

# Build command
BUILD_ARGS=(
    --build-arg BASE_OS="$BASE_OS"
    --build-arg OS_TYPE="$OS_TYPE"
    --build-arg JAVA_VERSION="$JAVA_VERSION"
    --build-arg PYTHON_VERSION="$PYTHON_VERSION"
    --build-arg ODP_REPO_URL="$ODP_REPO_URL"
    --build-arg AMBARI_REPO_URL="$AMBARI_REPO_URL"
)

[ -n "$ODP_UTILS_URL" ] && BUILD_ARGS+=(--build-arg ODP_UTILS_URL="$ODP_UTILS_URL")
[ -n "$MPACKS_URL" ] && BUILD_ARGS+=(--build-arg MPACKS_URL="$MPACKS_URL")
[ -n "$ZING_URL" ] && BUILD_ARGS+=(--build-arg ZING_JDK_URL="$ZING_URL")

docker build \
    -f Dockerfile.template \
    "${BUILD_ARGS[@]}" \
    -t "$FULL_IMAGE" \
    .

if [ $? -eq 0 ]; then
    log "✓ Image built successfully: $FULL_IMAGE"

    # Test the image
    log "Testing image..."
    docker run --rm "$FULL_IMAGE" java -version || warn "Could not verify Java in image"

    if [ "$PUSH" = "true" ]; then
        log "Pushing image to registry..."
        docker push "$FULL_IMAGE"
        if [ $? -eq 0 ]; then
            log "✓ Image pushed: $FULL_IMAGE"
        else
            error "Failed to push image"
        fi
    fi

    echo ""
    echo -e "${GREEN}✓ Build complete!${NC}"
    echo ""
    echo "Image: $FULL_IMAGE"
    echo ""
    echo "Deploy with:"
    echo "  helm install my-cluster helm-chart/ \\"
    echo "    --set image.repository=\"$REGISTRY/odp-vm-node\" \\"
    echo "    --set image.tag=\"$IMAGE_TAG\""
    echo ""
else
    error "Build failed!"
fi
