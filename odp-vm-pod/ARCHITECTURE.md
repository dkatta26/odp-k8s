# ODP VM-Pod Architecture

## Concept: Container as Virtual Machine

Traditional Kubernetes deploys **one service per pod** (microservices).  
This project deploys **ALL services in one pod** (monolithic, VM-like).

## Why This Approach?

### Use Case
- Development/testing environments
- Quick cluster provisioning (5 min vs 30 min)
- Self-service for team members
- Isolated per-user clusters
- Mirrors existing VM workflow (Ambari + all services)

### Trade-offs

**Advantages:**
- ✅ Faster deployment than VMs
- ✅ Familiar Ambari workflow
- ✅ Easy to understand (1 pod = 1 VM)
- ✅ Simple networking (all services localhost)
- ✅ Lower overhead than VMs

**Disadvantages:**
- ❌ Requires privileged mode (systemd)
- ❌ Not cloud-native (monolithic)
- ❌ Cannot scale individual services
- ❌ Higher resource usage per pod
- ❌ Limited by single-node storage

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────┐
│ Kubernetes Node                                           │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Pod: my-cluster-master-0 (acts like VM)            │ │
│  │                                                     │ │
│  │  Container:                                         │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │ systemd (PID 1)                            │  │ │
│  │  │ ├─ sshd                                    │  │ │
│  │  │ ├─ ambari-server                           │  │ │
│  │  │ ├─ ambari-agent                            │  │ │
│  │  │ ├─ hdfs-namenode                           │  │ │
│  │  │ ├─ yarn-resourcemanager                    │  │ │
│  │  │ ├─ zookeeper-server                        │  │ │
│  │  │ ├─ hiveserver2                             │  │ │
│  │  │ ├─ hbase-master                            │  │ │
│  │  │ └─ ... more services                       │  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  Volumes:                                           │ │
│  │  • /hadoop → PVC (100Gi)                           │ │
│  │  • /var/log → PVC (10Gi)                           │ │
│  │  • /sys/fs/cgroup → hostPath (for systemd)         │ │
│  └─────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Docker Image
- Base: Rocky Linux 9 with systemd
- Installed: All ODP packages (HDFS, YARN, Hive, HBase, etc.)
- Entrypoint: `/usr/sbin/init` (systemd becomes PID 1)
- Services: Managed via systemd units

### 2. Pod Configuration
- **Security:** `privileged: true` + `SYS_ADMIN` capability
- **Init:** Custom script sets hostname, configures Ambari
- **Storage:** PersistentVolumes for data + logs
- **Network:** Headless service for stable DNS

### 3. Service Discovery
StatefulSet provides stable DNS:
```
my-cluster-master-0.my-cluster-headless.namespace.svc.cluster.local
my-cluster-worker-0.my-cluster-headless.namespace.svc.cluster.local
```

Ambari agents connect to master using this DNS.

### 4. Process Management
systemd inside container manages all services:
```bash
systemctl start ambari-server
systemctl enable hdfs-namenode
systemctl status yarn-resourcemanager
```

## Comparison: VM-Pod vs Microservices

| Aspect | VM-Pod (This) | Microservices (Standard K8s) |
|--------|---------------|------------------------------|
| **Pods per cluster** | 3-5 (masters + workers) | 50+ (one per service) |
| **Deployment complexity** | Simple | Complex |
| **Resource efficiency** | Medium | High |
| **Scaling** | Scale entire VM | Scale individual services |
| **Debugging** | Easy (ssh + systemctl) | Complex (many pods) |
| **Production-ready** | No | Yes |
| **Learning curve** | Low (like VMs) | High (K8s native) |

## When to Use This Approach

### ✅ Good For:
- Development clusters
- Testing ODP versions
- Training environments
- Short-lived clusters
- Self-service for developers
- Proof-of-concept
- Replicating VM setup

### ❌ Not Good For:
- Production workloads
- Auto-scaling services
- Resource optimization
- Long-running clusters
- High availability (use microservices)

## Security Considerations

### Privileged Mode
- Required for systemd to function
- Grants elevated permissions to pod
- Isolated by namespace + RBAC
- Acceptable for dev/test, risky for prod

### Namespace Isolation
- Each user gets own namespace
- ResourceQuota limits resources
- NetworkPolicy can restrict traffic
- RBAC controls who can deploy

### Best Practices:
1. Dedicated K8s cluster for VM-pods (don't mix with prod)
2. Strong namespace RBAC
3. Resource quotas per user
4. Regular image updates
5. Audit privileged pod usage

## Future Improvements

1. **Remove systemd dependency** → Use supervisord (lighter)
2. **Multi-container pods** → One process per container
3. **Init containers** → Better separation of init vs runtime
4. **Operator pattern** → Custom controller for lifecycle
5. **Hybrid approach** → Critical services (HDFS) separate, others grouped

## Related Projects

- **KubeVirt**: Run actual VMs in Kubernetes
- **Kata Containers**: Lightweight VMs for containers
- **Weave Ignite**: VM in containers
- **Coder/Devpod**: Development environments in K8s

This approach is inspired by development workspace tools, adapted for big data clusters.
