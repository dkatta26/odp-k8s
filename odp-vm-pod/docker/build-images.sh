#!/bin/bash
# Build ODP VM-Pod images for different configurations
# Usage: ./build-images.sh [config-name] or ./build-images.sh all

set -e

REGISTRY="${REGISTRY:-acceldata}"
PUSH="${PUSH:-false}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Build configuration matrix
declare -A CONFIGS

# RHEL 9 configurations
CONFIGS["rhel9-odp3.3.6.3-jdk11"]="rockylinux:9|rhel9|3.3.6.3-1|2.7.6.0-1|jdk11|3.11"
CONFIGS["rhel9-odp3.3.6.3-jdk17"]="rockylinux:9|rhel9|3.3.6.3-1|2.7.6.0-1|jdk17|3.11"
CONFIGS["rhel9-odp3.3.6.3-zingjdk11"]="rockylinux:9|rhel9|3.3.6.3-1|2.7.6.0-1|zingjdk11|3.11|https://mirror.odp.acceldata.dev/scripts/azul_zing/zing26.01.0.0-11-jdk11.0.29.0.101-linux_x64.tar.gz"

# RHEL 8 configurations
CONFIGS["rhel8-odp3.2.2.0-jdk8"]="rockylinux:8|rhel8|3.2.2.0-2|2.7.6.0-1|jdk8|2"
CONFIGS["rhel8-odp3.2.2.0-jdk11"]="rockylinux:8|rhel8|3.2.2.0-2|2.7.6.0-1|jdk11|2"

# CentOS 7 configurations
CONFIGS["centos7-odp3.2.2.0-jdk8"]="centos:7|centos7|3.2.2.0-2|2.7.6.0-1|jdk8|2"

# Ubuntu 22 configurations
CONFIGS["ubuntu22-odp3.3.6.3-jdk11"]="ubuntu:22.04|ubuntu22|3.3.6.3-1|2.7.6.0-1|jdk11|3.11"
CONFIGS["ubuntu22-odp3.3.6.3-jdk17"]="ubuntu:22.04|ubuntu22|3.3.6.3-1|2.7.6.0-1|jdk17|3.11"

# Ubuntu 20 configurations
CONFIGS["ubuntu20-odp3.2.2.0-jdk8"]="ubuntu:20.04|ubuntu20|3.2.2.0-2|2.7.6.0-1|jdk8|2"

build_image() {
    local config_name=$1
    local config_value=$2

    IFS='|' read -r base_os os_type odp_ver ambari_ver java_ver python_ver zing_url <<< "$config_value"

    log "Building: ${config_name}"
    log "  Base OS: ${base_os}"
    log "  ODP: ${odp_ver}, Java: ${java_ver}, Python: ${python_ver}"

    local image_tag="${REGISTRY}/odp-vm-node:${config_name}"

    docker build \
        -f Dockerfile.template \
        --build-arg BASE_OS="${base_os}" \
        --build-arg OS_TYPE="${os_type}" \
        --build-arg ODP_VERSION="${odp_ver}" \
        --build-arg AMBARI_VERSION="${ambari_ver}" \
        --build-arg JAVA_VERSION="${java_ver}" \
        --build-arg PYTHON_VERSION="${python_ver}" \
        ${zing_url:+--build-arg ZING_JDK_URL="${zing_url}"} \
        -t "${image_tag}" \
        .

    if [ $? -eq 0 ]; then
        log "✓ Built: ${image_tag}"

        if [ "$PUSH" = "true" ]; then
            log "Pushing: ${image_tag}"
            docker push "${image_tag}"
            log "✓ Pushed: ${image_tag}"
        fi
    else
        error "✗ Failed to build: ${config_name}"
        return 1
    fi
}

list_configs() {
    echo ""
    echo "Available image configurations:"
    echo "================================"
    for config in "${!CONFIGS[@]}"; do
        IFS='|' read -r base_os os_type odp_ver ambari_ver java_ver python_ver zing_url <<< "${CONFIGS[$config]}"
        printf "%-40s | ODP %-12s | Java %-10s | OS: %s\n" "$config" "$odp_ver" "$java_ver" "$os_type"
    done
    echo ""
    echo "Usage:"
    echo "  Build one:  ./build-images.sh rhel9-odp3.3.6.3-jdk11"
    echo "  Build all:  ./build-images.sh all"
    echo "  With push:  PUSH=true ./build-images.sh rhel9-odp3.3.6.3-jdk11"
    echo ""
}

# Main script
if [ $# -eq 0 ]; then
    list_configs
    exit 0
fi

CONFIG_NAME=$1

if [ "$CONFIG_NAME" = "all" ]; then
    log "Building ALL configurations..."
    for config in "${!CONFIGS[@]}"; do
        build_image "$config" "${CONFIGS[$config]}"
        echo ""
    done
    log "✓ All builds complete!"
elif [ -n "${CONFIGS[$CONFIG_NAME]}" ]; then
    build_image "$CONFIG_NAME" "${CONFIGS[$CONFIG_NAME]}"
else
    error "Unknown configuration: $CONFIG_NAME"
    list_configs
    exit 1
fi
