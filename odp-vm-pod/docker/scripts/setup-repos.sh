#!/bin/bash
set -e

echo "Setting up ODP repositories..."

# These will be replaced with actual values via build args or environment variables
ODP_REPO_URL="${ODP_REPO_URL:-https://mirror.odp.acceldata.dev/ODP/centos/3.3.6.3-1/}"
AMBARI_REPO_URL="${AMBARI_REPO_URL:-https://mirror.odp.acceldata.dev/AMBARI/centos/2.7.6.0-1/}"

# Create Ambari repo file
cat > /etc/yum.repos.d/ambari.repo <<EOF
[ambari-2.7.6.0]
name=Ambari 2.7.6.0
baseurl=${AMBARI_REPO_URL}
gpgcheck=0
enabled=1
priority=1
EOF

# Create ODP repo file
cat > /etc/yum.repos.d/odp.repo <<EOF
[ODP-3.3.6.3-1]
name=ODP 3.3.6.3-1
baseurl=${ODP_REPO_URL}
gpgcheck=0
enabled=1
priority=1
EOF

echo "✓ Repositories configured"
echo "  Ambari: ${AMBARI_REPO_URL}"
echo "  ODP: ${ODP_REPO_URL}"

# Clean yum cache
dnf clean all
dnf makecache
