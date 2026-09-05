#!/bin/bash
# Initialization script run on pod startup
# Configures the node based on its role and cluster configuration

set -e

echo "========================================"
echo "Initializing ODP Node"
echo "========================================"

# Get configuration from environment variables
NODE_TYPE="${NODE_TYPE:-master}"
CLUSTER_NAME="${CLUSTER_NAME:-odp-cluster}"
NODE_INDEX="${NODE_INDEX:-0}"
NAMESPACE="${NAMESPACE:-default}"

echo "Node Type: $NODE_TYPE"
echo "Cluster: $CLUSTER_NAME"
echo "Node Index: $NODE_INDEX"
echo "Namespace: $NAMESPACE"

# Set hostname
HOSTNAME="${CLUSTER_NAME}-${NODE_TYPE}-${NODE_INDEX}"
hostnamectl set-hostname $HOSTNAME
echo "✓ Hostname set to: $HOSTNAME"

# Configure Ambari Agent
if [ -f /etc/ambari-agent/conf/ambari-agent.ini ]; then
    # Point to Ambari Server (first master node)
    AMBARI_SERVER="${CLUSTER_NAME}-master-0.${CLUSTER_NAME}-headless.${NAMESPACE}.svc.cluster.local"

    sed -i "s/hostname=localhost/hostname=${AMBARI_SERVER}/g" /etc/ambari-agent/conf/ambari-agent.ini
    echo "✓ Ambari Agent configured to connect to: $AMBARI_SERVER"
fi

# Generate SSH keys if not present
if [ ! -f /root/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
    echo "✓ SSH keys generated"
fi

# Configure hosts file for cluster DNS
# This will be populated by Kubernetes DNS, but we add entries for clarity
cat >> /etc/hosts <<EOF

# ODP Cluster Nodes (added by init script)
# Kubernetes DNS will resolve these automatically
# ${CLUSTER_NAME}-master-0.${CLUSTER_NAME}-headless.${NAMESPACE}.svc.cluster.local
EOF

# Initialize HDFS NameNode (only on first master)
if [ "$NODE_TYPE" = "master" ] && [ "$NODE_INDEX" = "0" ]; then
    echo "Initializing as HDFS NameNode..."

    # Wait for systemd to be ready
    sleep 5

    # Format NameNode if not already formatted
    if [ ! -d "/hadoop/hdfs/namenode/current" ]; then
        echo "Formatting HDFS NameNode..."
        sudo -u hdfs hdfs namenode -format -force -nonInteractive || true
        echo "✓ NameNode formatted"
    fi
fi

# Configure services based on node type
case "$NODE_TYPE" in
    master)
        echo "Enabling master services..."
        systemctl enable ambari-server
        # HDFS NameNode, YARN RM will be managed by Ambari
        ;;
    worker)
        echo "Enabling worker services..."
        # HDFS DataNode, YARN NM will be managed by Ambari
        ;;
    edge)
        echo "Enabling edge services..."
        # Client-only node
        ;;
esac

echo "========================================"
echo "✓ ODP Node Initialization Complete"
echo "========================================"

# Keep the init script running so we can see logs
# systemd will take over from here
