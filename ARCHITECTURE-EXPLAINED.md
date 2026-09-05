# ODP on Kubernetes - Architecture Explained

## Table of Contents
1. [High-Level Architecture](#high-level-architecture)
2. [VM vs Kubernetes Comparison](#vm-vs-kubernetes-comparison)
3. [Pod Architecture](#pod-architecture)
4. [Storage Architecture](#storage-architecture)
5. [Network Architecture](#network-architecture)
6. [Runtime Installation Flow](#runtime-installation-flow)
7. [Component Distribution](#component-distribution)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                            │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Namespace: odp                                 │ │
│  │                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │ │
│  │  │  Master Pod-0   │  │  Worker Pod-0   │  │ Worker     │ │ │
│  │  │                 │  │                 │  │ Pod-1      │ │ │
│  │  │ • Ambari Server │  │ • Ambari Agent  │  │            │ │ │
│  │  │ • Ambari Agent  │  │ • HDFS DataNode │  │ • Ambari   │ │ │
│  │  │ • NameNode      │  │ • YARN NodeMgr  │  │   Agent    │ │ │
│  │  │ • ResourceMgr   │  │ • HBase Region  │  │ • HDFS     │ │ │
│  │  │ • HBase Master  │  │ • Kafka Broker  │  │   DataNode │ │ │
│  │  │ • ZooKeeper     │  │                 │  │ • YARN     │ │ │
│  │  │ • Hive Metastore│  │                 │  │   NodeMgr  │ │ │
│  │  └─────────────────┘  └─────────────────┘  └────────────┘ │ │
│  │         │                     │                    │        │ │
│  │         └─────────────────────┴────────────────────┘        │ │
│  │                    Kubernetes Network                        │ │
│  │                  (Service Discovery via DNS)                 │ │
│  │                                                             │ │
│  │  Storage Layer (PersistentVolumes)                         │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │ │
│  │  │ Data: 100G │  │ Data: 500G │  │ Data: 500G │          │ │
│  │  │ Logs: 50G  │  │ Logs: 100G │  │ Logs: 100G │          │ │
│  │  └────────────┘  └────────────┘  └────────────┘          │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

---

## VM vs Kubernetes Comparison

### Traditional VM-Based Deployment (Current)

```
┌─────────────────────────────────────────────────────────────┐
│                    Physical Infrastructure                   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   VM-1       │  │   VM-2       │  │   VM-3       │     │
│  │              │  │              │  │              │     │
│  │ RHEL/CentOS  │  │ RHEL/CentOS  │  │ RHEL/CentOS  │     │
│  │ ────────     │  │ ────────     │  │ ────────     │     │
│  │ Ansible      │  │ Ansible      │  │ Ansible      │     │
│  │ installs:    │  │ installs:    │  │ installs:    │     │
│  │ • Java       │  │ • Java       │  │ • Java       │     │
│  │ • ODP pkgs   │  │ • ODP pkgs   │  │ • ODP pkgs   │     │
│  │ • Ambari     │  │ • Ambari     │  │ • Ambari     │     │
│  │              │  │              │  │              │     │
│  │ Services:    │  │ Services:    │  │ Services:    │     │
│  │ • NameNode   │  │ • DataNode   │  │ • DataNode   │     │
│  │ • ResourceMgr│  │ • NodeMgr    │  │ • NodeMgr    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│        ↑                 ↑                 ↑               │
│        └─────────────────┴─────────────────┘               │
│              Static IPs / Hostnames                        │
└────────────────────────────────────────────────────────────┘

Problems:
❌ Slow provisioning (15-30 min per VM)
❌ Resource wastage (each VM reserves full resources)
❌ Manual scaling (provision new VMs)
❌ Static configuration (IPs, hostnames)
❌ No auto-recovery
```

### Kubernetes-Based Deployment (New)

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Pod-0      │  │   Pod-1      │  │   Pod-2      │     │
│  │              │  │              │  │              │     │
│  │ Base Image:  │  │ Base Image:  │  │ Base Image:  │     │
│  │ Rocky Linux  │  │ Rocky Linux  │  │ Rocky Linux  │     │
│  │ ────────     │  │ ────────     │  │ ────────     │     │
│  │ Init:        │  │ Init:        │  │ Init:        │     │
│  │ • Install    │  │ • Install    │  │ • Install    │     │
│  │   Java       │  │   Java       │  │   Java       │     │
│  │ • Install    │  │ • Install    │  │ • Install    │     │
│  │   ODP        │  │   ODP        │  │   ODP        │     │
│  │              │  │              │  │              │     │
│  │ Main:        │  │ Main:        │  │ Main:        │     │
│  │ • NameNode   │  │ • DataNode   │  │ • DataNode   │     │
│  │ • ResourceMgr│  │ • NodeMgr    │  │ • NodeMgr    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│        ↑                 ↑                 ↑               │
│        └─────────────────┴─────────────────┘               │
│         Dynamic DNS (pod-0.svc, pod-1.svc)                │
│         Automatic Service Discovery                        │
└────────────────────────────────────────────────────────────┘

Benefits:
✅ Fast provisioning (2-3 min per pod)
✅ Efficient resources (pack more workloads)
✅ Auto-scaling (kubectl scale)
✅ Dynamic configuration (DNS, service discovery)
✅ Self-healing (pod restarts automatically)
```

---

## Pod Architecture

### Pod Internal Structure

Each pod mimics a complete VM with all services:

```
┌───────────────────────────────────────────────────────────────┐
│                    Pod: prod-cluster-master-0                  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Init Container: install-odp                              │ │
│  │  (Runs once at pod startup)                              │ │
│  │                                                           │ │
│  │  1. Setup YUM repositories                               │ │
│  │     • ODP repo URL                                        │ │
│  │     • Ambari repo URL                                     │ │
│  │                                                           │ │
│  │  2. Install Java                                          │ │
│  │     yum install java-11-openjdk                          │ │
│  │                                                           │ │
│  │  3. Install ODP packages                                  │ │
│  │     yum install ambari-server hadoop hive hbase ...     │ │
│  │                                                           │ │
│  │  4. Create directories                                    │ │
│  │     /hadoop/hdfs, /var/log, etc.                        │ │
│  │                                                           │ │
│  │  5. Mark as installed                                     │ │
│  │     echo "3.3.6.3-1" > /opt/odp/.installed              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                            ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Main Container: odp-node                                 │ │
│  │  (Runs continuously)                                      │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  SystemD (PID 1)                                     │ │ │
│  │  │                                                      │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │ │ │
│  │  │  │ Ambari Server│  │ Ambari Agent │  │ SSH       │ │ │ │
│  │  │  │ Port: 8080   │  │              │  │ Port: 22  │ │ │ │
│  │  │  └──────────────┘  └──────────────┘  └───────────┘ │ │ │
│  │  │                                                      │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │ │ │
│  │  │  │ HDFS         │  │ YARN         │  │ ZooKeeper │ │ │ │
│  │  │  │ NameNode     │  │ ResourceMgr  │  │           │ │ │ │
│  │  │  │ Port: 9870   │  │ Port: 8088   │  │ Port: 2181│ │ │ │
│  │  │  └──────────────┘  └──────────────┘  └───────────┘ │ │ │
│  │  │                                                      │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │ │ │
│  │  │  │ Hive         │  │ HBase        │  │ Kafka     │ │ │ │
│  │  │  │ Metastore    │  │ Master       │  │ Broker    │ │ │ │
│  │  │  │ Port: 9083   │  │ Port: 16000  │  │ Port: 9092│ │ │ │
│  │  │  └──────────────┘  └──────────────┘  └───────────┘ │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Volume Mounts:                                                │
│  • /hadoop       → PVC (data-prod-cluster-master-0)           │
│  • /var/log      → PVC (logs-prod-cluster-master-0)           │
│  • /sys/fs/cgroup → HostPath (for systemd)                    │
└───────────────────────────────────────────────────────────────┘
```

### Why This Design?

**VM-in-Pod Approach:**
- Each pod = one complete "VM" with all services
- Uses systemd as init system (just like real VMs)
- All ODP services run as systemd units
- Matches your current VM deployment exactly

**Alternative Approaches (Not Used):**
❌ One service per pod (too many pods, complex networking)
❌ DaemonSets (loses flexibility in node placement)
❌ Separate containers per service (doesn't work with systemd)

---

## Storage Architecture

### Persistent Volume Claims (PVCs)

Each pod gets two persistent volumes:

```
Pod Lifecycle:
┌─────────────────────────────────────────────────────────────┐
│  Pod: master-0 (can be deleted, recreated)                  │
│     ↓ ↓                                                     │
│     │ └─────────────────┐                                   │
│     ↓                   ↓                                   │
│  ┌──────────────┐   ┌──────────────┐                       │
│  │ PVC: data    │   │ PVC: logs    │                       │
│  │ 100Gi        │   │ 50Gi         │                       │
│  └──────┬───────┘   └──────┬───────┘                       │
│         ↓                   ↓                               │
│  ┌──────────────┐   ┌──────────────┐                       │
│  │ PV: pv-001   │   │ PV: pv-002   │                       │
│  │ (survives)   │   │ (survives)   │                       │
│  └──────┬───────┘   └──────┬───────┘                       │
│         ↓                   ↓                               │
│  ┌──────────────────────────────────┐                      │
│  │  Physical Storage (Node Disk)     │                      │
│  │  /mnt/data/pv-001                │                      │
│  │  /mnt/data/pv-002                │                      │
│  └──────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘

Key Points:
✅ Data survives pod restarts/deletions
✅ Each pod gets its own volumes (not shared)
✅ Volumes bound to pod via StatefulSet
```

### Directory Mapping

```
Inside Pod:                         On Physical Disk:
─────────────                       ─────────────────

/hadoop/                     →      PVC: data-master-0 (100Gi)
├── hdfs/                            │
│   ├── namenode/                    └── Bound to: /mnt/data/pv-001/
│   └── datanode/                        ├── hdfs/namenode/
├── yarn/                                ├── hdfs/datanode/
│   ├── local/                           └── yarn/...
│   └── logs/

/var/log/                    →      PVC: logs-master-0 (50Gi)
├── hadoop/                          │
├── ambari-server/                   └── Bound to: /mnt/data/pv-002/
├── hive/                                ├── hadoop/
├── hbase/                               ├── ambari-server/
└── kafka/                               └── hive/...
```

---

## Network Architecture

### Service Discovery

Kubernetes provides automatic DNS:

```
┌────────────────────────────────────────────────────────────┐
│                  Kubernetes DNS                             │
│                                                             │
│  Pod Names (StatefulSet):                                  │
│  • prod-cluster-master-0.prod-cluster-headless.odp.svc     │
│  • prod-cluster-worker-0.prod-cluster-headless.odp.svc     │
│  • prod-cluster-worker-1.prod-cluster-headless.odp.svc     │
│                                                             │
│  Services:                                                  │
│  • prod-cluster-ambari.odp.svc     → Port 8080            │
│  • prod-cluster-hdfs.odp.svc       → Port 9870            │
│  • prod-cluster-yarn.odp.svc       → Port 8088            │
└────────────────────────────────────────────────────────────┘

How Components Find Each Other:

┌──────────────┐                    ┌──────────────┐
│ DataNode     │  "Where is         │ NameNode     │
│ (worker-0)   │   NameNode?"       │ (master-0)   │
│              │                    │              │
│  Queries DNS │ ───────────────→   │ Returns:     │
│              │                    │ master-0.    │
│              │                    │ svc:9870     │
│              │ ←───────────────   │              │
│  Connects to │                    │              │
│  master-0:9870                    │              │
└──────────────┘                    └──────────────┘

Benefits:
✅ No hardcoded IPs
✅ Automatic updates when pods move
✅ Load balancing via services
```

### Port Mapping

```
Service Type: ClusterIP (Internal)
┌────────────────────────────────────────┐
│ Internal Cluster Network               │
│                                        │
│ master-0:8080  → Ambari UI             │
│ master-0:9870  → HDFS NameNode Web     │
│ master-0:8088  → YARN ResourceMgr Web  │
│ master-0:8020  → HDFS RPC              │
│ master-0:2181  → ZooKeeper             │
└────────────────────────────────────────┘

Service Type: NodePort (External Access)
┌────────────────────────────────────────┐
│ External Network                       │
│                                        │
│ <any-node-ip>:30880 → Ambari UI        │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  Kubernetes forwards to:         │  │
│  │  master-0:8080 internally        │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

---

## Runtime Installation Flow

### Detailed Startup Sequence

```
Time: T0 (Pod Creation)
┌────────────────────────────────────────────────────────┐
│ 1. Kubernetes schedules pod on node demo1.acceldata.com│
│ 2. Pulls base image: rockylinux:9                     │
│ 3. Creates volumes (data, logs)                       │
└────────────────────────────────────────────────────────┘
                        ↓
Time: T+30s (Init Container Starts)
┌────────────────────────────────────────────────────────┐
│ Init Container: install-odp                            │
│                                                        │
│ Step 1: Check if already installed                    │
│   if [ -f /opt/odp/.installed ]; then exit 0; fi      │
│                                                        │
│ Step 2: Setup repositories                            │
│   cat > /etc/yum.repos.d/odp.repo <<EOF               │
│   [ODP]                                               │
│   baseurl=https://mirror.odp.acceldata.dev/...       │
│   EOF                                                 │
│                                                        │
│ Step 3: Install system packages                       │
│   yum install -y systemd openssh-server wget ...      │
│                                                        │
│ Step 4: Install Java                                  │
│   yum install -y java-11-openjdk                      │
│                                                        │
│ Step 5: Install ODP (10-12 minutes)                   │
│   yum install -y ambari-server ambari-agent \         │
│                  hadoop hadoop-hdfs hadoop-yarn \     │
│                  hive hbase zookeeper kafka spark2    │
│   (Downloads ~3-5 GB of packages)                     │
│                                                        │
│ Step 6: Create directories                            │
│   mkdir -p /hadoop/hdfs/{namenode,datanode}           │
│   mkdir -p /var/log/{hadoop,ambari-server,...}        │
│                                                        │
│ Step 7: Mark as installed                             │
│   echo "3.3.6.3-1" > /opt/odp/.installed             │
│   date >> /opt/odp/.installed                        │
│                                                        │
│ Exit code: 0 (Success)                                │
└────────────────────────────────────────────────────────┘
                        ↓
Time: T+12m (Main Container Starts)
┌────────────────────────────────────────────────────────┐
│ Main Container: odp-node                               │
│                                                        │
│ Command: /usr/sbin/init (systemd)                     │
│                                                        │
│ SystemD starts services:                              │
│   • sshd                                              │
│   • ambari-server                                     │
│   • ambari-agent                                      │
│                                                        │
│ Ambari manages ODP services:                          │
│   • HDFS NameNode                                     │
│   • YARN ResourceManager                              │
│   • HBase Master                                      │
│   • ZooKeeper Server                                  │
│   • Kafka Broker                                      │
│                                                        │
│ Pod Status: Running (1/1)                             │
└────────────────────────────────────────────────────────┘
                        ↓
Time: T+15m (Services Ready)
┌────────────────────────────────────────────────────────┐
│ All services started and healthy                       │
│ Cluster ready for use                                 │
└────────────────────────────────────────────────────────┘
```

### What Happens on Pod Restart?

```
Scenario: Pod crashes or node failure
┌────────────────────────────────────────────────────────┐
│ 1. Kubernetes detects pod failure                      │
│ 2. Schedules new pod (maybe different node)            │
│ 3. Attaches SAME volumes (data, logs)                  │
│                                                        │
│ 4. Init container runs:                               │
│    • Checks: /opt/odp/.installed exists?              │
│    • YES → Skips installation (instant)               │
│    • NO → Installs ODP (12 min)                       │
│                                                        │
│ 5. Main container starts                              │
│ 6. All data intact from previous run                  │
└────────────────────────────────────────────────────────┘

Benefits:
✅ First start: 12 min (install)
✅ Restarts: 2 min (skip install)
✅ Data preserved across restarts
```

---

## Component Distribution

### Master Pods (Control Plane)

```
Master-0:
├── Ambari Server      (Cluster management UI)
├── Ambari Agent       (Executes commands)
├── HDFS NameNode      (Metadata management)
├── HDFS JournalNode   (HA shared edits)
├── YARN ResourceMgr   (Resource scheduling)
├── HBase Master       (HBase coordination)
├── Hive Metastore     (Metadata for Hive)
├── ZooKeeper Server   (Coordination service)
└── PostgreSQL         (Ambari/Hive metadata DB)

Resources:
• CPU: 6 cores
• Memory: 30 GB
• Storage: 100 GB (data) + 50 GB (logs)
```

### Worker Pods (Data Plane)

```
Worker-0, Worker-1, Worker-N:
├── Ambari Agent       (Receives commands)
├── HDFS DataNode      (Stores data blocks)
├── YARN NodeManager   (Runs containers)
├── HBase RegionServer (Serves HBase regions)
├── Kafka Broker       (Message broker)
└── Spark Executors    (Runs Spark tasks)

Resources:
• CPU: 6 cores
• Memory: 30 GB
• Storage: 500 GB (data) + 100 GB (logs)
```

### Scaling Pattern

```
kubectl scale statefulset prod-cluster-worker --replicas=5

Before:                    After:
┌─────────┐               ┌─────────┐
│Master-0 │               │Master-0 │
└─────────┘               └─────────┘
    │                          │
    ├── Worker-0               ├── Worker-0
    ├── Worker-1               ├── Worker-1
                               ├── Worker-2  ← New
                               ├── Worker-3  ← New
                               └── Worker-4  ← New

Each new worker:
• Installs ODP automatically
• Registers with Ambari
• Starts serving data/compute
```

---

## Summary

### Key Architectural Decisions

1. **VM-in-Pod Model**
   - Each pod = complete VM equivalent
   - Run all services in one pod
   - Use systemd as init system

2. **Runtime Installation**
   - No custom images to maintain
   - Install ODP packages at startup
   - Easy to change versions

3. **Persistent Storage**
   - StatefulSet + PVCs for data
   - Survives pod restarts
   - Per-pod isolated storage

4. **Service Discovery**
   - Kubernetes DNS
   - No hardcoded IPs
   - Automatic updates

5. **Component Layout**
   - Masters: Control plane services
   - Workers: Data/compute services
   - Horizontal scaling of workers

### Deployment Timeline

```
┌─────────────────────────────────────────────────────┐
│ Deployment Phase          Duration    Cumulative    │
├─────────────────────────────────────────────────────┤
│ Create namespace           10s        10s           │
│ Create PVCs                30s        40s           │
│ Schedule pods              20s        1m            │
│ Pull base image            2m         3m            │
│ Init: Install ODP          10m        13m           │
│ Start main container       1m         14m           │
│ Services ready             1m         15m           │
├─────────────────────────────────────────────────────┤
│ Total: 15 minutes from helm install to ready        │
└─────────────────────────────────────────────────────┘
```

### This Architecture Gives You:

✅ **Flexibility** - Change ODP versions without rebuilding images  
✅ **Familiarity** - Same deployment flow as Ansible/VMs  
✅ **Scalability** - Scale workers with one command  
✅ **Reliability** - Automatic pod restart on failure  
✅ **Portability** - Run on any Kubernetes cluster  
✅ **Efficiency** - Better resource utilization than VMs  

---

## Next: Deploy This Architecture

See `deploy-with-base-image.md` for deployment commands!
