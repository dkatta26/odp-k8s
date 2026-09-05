# ODP "VM-as-Pod" Image
# All ODP services run inside one container using systemd
# Acts like a traditional VM but containerized

FROM rockylinux:9

LABEL maintainer="Acceldata <support@acceldata.io>" \
      description="ODP Complete Node - All services in one container" \
      version="3.3.6.3-1"

# Install systemd and basic tools
RUN dnf install -y \
    systemd \
    systemd-sysv \
    initscripts \
    java-11-openjdk-devel \
    python3 \
    python3-pip \
    openssh-server \
    openssh-clients \
    wget \
    curl \
    tar \
    gzip \
    net-tools \
    iproute \
    bind-utils \
    nc \
    vim \
    sudo \
    cronie \
    rsync \
    && dnf clean all

# Remove unnecessary systemd services that won't work in containers
RUN (cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
    rm -f /lib/systemd/system/multi-user.target.wants/*;\
    rm -f /etc/systemd/system/*.wants/*;\
    rm -f /lib/systemd/system/local-fs.target.wants/*; \
    rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
    rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
    rm -f /lib/systemd/system/basic.target.wants/*;\
    rm -f /lib/systemd/system/anaconda.target.wants/*;

# Set environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk \
    PATH=$PATH:/usr/lib/jvm/java-11-openjdk/bin

# ODP Version
ARG ODP_VERSION=3.3.6.3-1
ARG AMBARI_VERSION=2.7.6.0-1

# Copy ODP repository configuration script
COPY scripts/setup-repos.sh /tmp/setup-repos.sh
RUN chmod +x /tmp/setup-repos.sh

# Install ODP and Ambari packages
# This script will be populated based on your mirror URLs
RUN /tmp/setup-repos.sh && \
    dnf install -y \
    ambari-server \
    ambari-agent \
    hadoop \
    hadoop-hdfs \
    hadoop-yarn \
    hadoop-mapreduce \
    hive \
    hive-metastore \
    hive-server2 \
    hbase \
    zookeeper \
    kafka \
    spark3 \
    && dnf clean all

# Create ODP directories
RUN mkdir -p \
    /hadoop/hdfs/namenode \
    /hadoop/hdfs/datanode \
    /hadoop/yarn/local \
    /hadoop/yarn/logs \
    /var/log/hadoop \
    /var/log/ambari-server \
    /var/log/ambari-agent \
    /var/log/hive \
    /var/log/hbase \
    /var/log/zookeeper \
    /var/log/kafka \
    && chmod -R 755 /hadoop /var/log

# Copy systemd service files for ODP components
COPY systemd-services/*.service /etc/systemd/system/

# Enable services (they'll start via systemd when pod starts)
RUN systemctl enable sshd && \
    systemctl enable ambari-server && \
    systemctl enable ambari-agent

# Copy initialization script
COPY scripts/init-odp-node.sh /usr/local/bin/init-odp-node.sh
RUN chmod +x /usr/local/bin/init-odp-node.sh

# Copy Ambari blueprints and configurations
COPY configs/ /opt/odp-configs/

# Expose common ports
# Ambari: 8080
# HDFS NameNode: 9870, 8020
# HDFS DataNode: 9864, 9866
# YARN RM: 8088, 8030, 8031, 8032, 8033
# YARN NM: 8042
# Hive: 10000, 10002
# HBase: 16000, 16010, 16020, 16030
# ZooKeeper: 2181, 2888, 3888
# Kafka: 9092
# SSH: 22
EXPOSE 22 8080 8020 9870 9864 9866 8088 8042 10000 16000 16010 2181 9092

# Volume for persistent data
VOLUME ["/hadoop", "/var/log", "/etc/hadoop", "/etc/hive", "/etc/hbase"]

# systemd requires privileged mode and /run/systemd/system
STOPSIGNAL SIGRTMIN+3

# Start systemd as PID 1
CMD ["/usr/sbin/init"]
