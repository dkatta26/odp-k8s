# ODP on Kubernetes - Development Methodology & Architecture Plan

## Project Overview
Convert VM-based ODP (Open Data Platform) deployment to Kubernetes-native Helm charts with full support for Ambari, 37+ big data services, Kerberos, and SSL/TLS.

---

## Architecture Strategy

### **Phase 1: Research & Foundation (Weeks 1-2)**

#### 1.1 Technology Assessment
- **Research existing solutions:**
  - Apache Ambari on Kubernetes (if available)
  - Hadoop operator patterns (e.g., Stackable, Apache YuniKorn)
  - StatefulSet vs Operator pattern for stateful services
  - Service mesh considerations (Istio/Linkerd for mTLS)

- **Containerization strategy:**
  - Base images (CentOS, Ubuntu, RHEL UBI)
  - Multi-stage builds for size optimization
  - Init containers for configuration management
  - Sidecar patterns for log forwarding

- **Storage strategy:**
  - StorageClass selection (local-path, Rook-Ceph, cloud providers)
  - PersistentVolume sizing for HDFS DataNodes
  - StatefulSet volumeClaimTemplates
  - Backup/restore strategies

#### 1.2 Architecture Decisions

**Decision 1: Deployment Pattern**
- **Option A:** Operator-based (complex but powerful)
- **Option B:** Helm + StatefulSets (simpler, recommended start)
- **Recommendation:** Start with Helm, migrate to Operator if needed

**Decision 2: Ambari Strategy**
- **Option A:** Run Ambari in K8s (challenging - expects SSH access)
- **Option B:** Replace Ambari with K8s-native management
- **Option C:** Hybrid - Ambari for config, K8s for orchestration
- **Recommendation:** Option C initially, move to B long-term

**Decision 3: Networking**
- StatefulSet headless services for stable DNS
- NodePort/LoadBalancer for external access
- NetworkPolicy for security zones
- Consider CNI requirements (Calico, Cilium)

---

## Phase 2: Core Infrastructure (Weeks 3-4)

### 2.1 Helm Chart Structure
```
odp-helm/
├── charts/                    # Subcharts for each service
│   ├── hdfs/
│   ├── yarn/
│   ├── zookeeper/
│   ├── kafka/
│   └── ...
├── templates/
│   ├── _helpers.tpl          # Template helpers
│   ├── namespace.yaml
│   ├── service-account.yaml
│   ├── configmaps/           # Config templates
│   └── secrets/              # Credential management
├── values.yaml               # Default values
├── values-dev.yaml          # Dev overrides
├── values-prod.yaml         # Prod overrides
└── Chart.yaml
```

### 2.2 Base Components Priority
1. **ZooKeeper** (foundation for coordination)
2. **HDFS** (NameNode, DataNode, JournalNode for HA)
3. **YARN** (ResourceManager, NodeManager)
4. **Core Services** (Hive, HBase, Spark)

### 2.3 Configuration Management
- **ConfigMaps:** Non-sensitive configs (core-site.xml, hdfs-site.xml)
- **Secrets:** Passwords, keytabs, certificates
- **Init containers:** Template rendering, config validation
- **Environment-based:** Dev/staging/prod value files

---

## Phase 3: Service Containerization (Weeks 5-8)

### 3.1 Docker Image Strategy

**Base Image Creation:**
```dockerfile
# Example: HDFS NameNode
FROM registry.access.redhat.com/ubi9/ubi:latest

# Install Java
RUN yum install -y java-11-openjdk-devel && yum clean all

# Install Hadoop
ARG ODP_VERSION=3.3.x
COPY hadoop-${ODP_VERSION}.tar.gz /tmp/
RUN tar -xzf /tmp/hadoop-*.tar.gz -C /opt/ && \
    ln -s /opt/hadoop-* /opt/hadoop

# Configuration templates
COPY configs/ /etc/hadoop/templates/

# Entrypoint script
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["namenode"]
```

### 3.2 Service-Specific Considerations

**HDFS:**
- NameNode: StatefulSet with 2 replicas (HA)
- DataNode: DaemonSet or StatefulSet
- JournalNode: StatefulSet (3+ replicas)
- Persistent volumes for metadata and data

**YARN:**
- ResourceManager: Deployment with 2 replicas (HA)
- NodeManager: DaemonSet (runs on all worker nodes)
- Timeline Server: Deployment

**ZooKeeper:**
- StatefulSet with 3/5 replicas
- Anti-affinity for pod distribution
- PodDisruptionBudget for availability

**Kafka:**
- StatefulSet with rack awareness
- Persistent storage for logs
- Cruise Control for rebalancing

### 3.3 Component Enablement Matrix
Create a values.yaml structure:
```yaml
components:
  hdfs:
    enabled: true
    namenode:
      replicas: 2
      resources:
        requests:
          memory: "2Gi"
          cpu: "1"
    datanode:
      replicas: 3
      storage: "100Gi"
  
  yarn:
    enabled: true
  
  spark:
    enabled: false
    version: "3.3.3"
  
  kafka:
    enabled: true
    replicas: 3
```

---

## Phase 4: Security Implementation (Weeks 9-10)

### 4.1 Kerberos in Kubernetes

**Architecture:**
1. **KDC (Key Distribution Center):**
   - Deploy MIT Kerberos in StatefulSet
   - Initialize realm on first boot
   - Backup KDC database to persistent volume

2. **Keytab Management:**
   - Init container generates service principals
   - Store keytabs in Kubernetes Secrets
   - Mount secrets as files in service pods

3. **Configuration:**
   ```yaml
   security:
     kerberos:
       enabled: true
       realm: "CLUSTER.LOCAL"
       kdc:
         replicas: 2
       principals:
         - "hdfs/namenode@CLUSTER.LOCAL"
         - "yarn/resourcemanager@CLUSTER.LOCAL"
   ```

**Implementation Steps:**
1. Create KDC StatefulSet
2. Init job to create realm and admin principal
3. Service init containers to:
   - Request principals from KDC
   - Generate keytabs
   - Configure krb5.conf
4. Apply Kerberos configs to core-site.xml

### 4.2 SSL/TLS Implementation

**Certificate Management:**
- **Option A:** cert-manager (recommended)
- **Option B:** Manual certificate injection

**Architecture:**
```yaml
security:
  tls:
    enabled: true
    certManager:
      enabled: true
      issuer: "letsencrypt-prod"
    
    # Or manual certificates
    certificates:
      ca: "base64-encoded-ca-cert"
      certs:
        namenode: "base64-encoded-cert"
        resourcemanager: "base64-encoded-cert"
```

**Service Configuration:**
- HTTPS endpoints for web UIs
- SSL for RPC communication (HDFS, YARN)
- Keystore/truststore generation via init containers
- Automatic certificate rotation handling

---

## Phase 5: Advanced Features (Weeks 11-12)

### 5.1 High Availability
- **HDFS HA:** Active/Standby NameNodes with automatic failover
- **YARN HA:** Multiple ResourceManagers with ZK coordination
- **HBase HA:** HMaster with backup
- **PodDisruptionBudgets** for all critical services

### 5.2 Monitoring & Observability
- **Metrics:** Prometheus exporters for each service
- **Logging:** Fluent Bit sidecar → Elasticsearch/Loki
- **Tracing:** OpenTelemetry integration
- **Dashboards:** Grafana templates for HDFS/YARN/Kafka

### 5.3 Scaling & Resource Management
- **HPA (Horizontal Pod Autoscaler):** For stateless services
- **VPA (Vertical Pod Autoscaler):** For resource optimization
- **Node affinity:** Separate control plane and data nodes
- **Taints/Tolerations:** Dedicated node pools

---

## Phase 6: Testing Strategy (Ongoing)

### 6.1 Unit Testing
- Helm template rendering tests (`helm template --debug`)
- YAML validation (kubeval, kubeconform)
- Policy validation (OPA, Kyverno)

### 6.2 Integration Testing
```bash
# Test script structure
#!/bin/bash
set -e

# Deploy cluster
helm install odp ./odp-helm --wait --timeout 30m

# Validate services
kubectl wait --for=condition=ready pod -l app=hdfs-namenode --timeout=300s

# Functional tests
kubectl exec -it hdfs-namenode-0 -- hdfs dfs -mkdir /test
kubectl exec -it hdfs-namenode-0 -- hdfs dfs -put /tmp/test.txt /test/

# Cleanup
helm uninstall odp
```

### 6.3 Test Environments
1. **Local:** Minikube/Kind for development
2. **Staging:** Small K8s cluster (3 nodes)
3. **Production:** Full cluster with HA

---

## Development Workflow

### Iteration Cycle (Per Component)
1. **Research** (1 day)
   - Study original Ansible role
   - Identify dependencies
   - Document configuration files

2. **Containerize** (2-3 days)
   - Create Dockerfile
   - Build and test image locally
   - Push to registry

3. **Create Helm Chart** (2 days)
   - StatefulSet/Deployment manifests
   - Service, ConfigMap, Secret definitions
   - values.yaml entries

4. **Test** (1 day)
   - Deploy to test cluster
   - Validate functionality
   - Document issues

5. **Security** (1 day)
   - Add Kerberos support
   - Configure SSL/TLS
   - Test authenticated access

6. **Integrate** (1 day)
   - Test with other components
   - Update dependencies
   - Documentation

---

## Milestones

### M1: Foundation (Week 4)
- ✅ Helm chart structure
- ✅ ZooKeeper deployed
- ✅ HDFS NameNode + DataNode working
- ✅ Basic HDFS operations functional

### M2: Core Services (Week 8)
- ✅ YARN operational
- ✅ Hive, HBase deployed
- ✅ Spark jobs can run
- ✅ Basic monitoring setup

### M3: Security (Week 10)
- ✅ Kerberos fully functional
- ✅ SSL/TLS on all services
- ✅ RBAC policies applied

### M4: Production Ready (Week 12)
- ✅ HA for all critical services
- ✅ Full monitoring & alerting
- ✅ Documentation complete
- ✅ CI/CD pipeline

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ambari doesn't work in K8s | High | Replace with K8s-native config management |
| Storage performance issues | High | Use local SSDs or high-IOPS storage classes |
| Networking complexity | Medium | Use CNI with proper network policies |
| Kerberos in containers | Medium | Well-documented init container pattern |
| Service interdependencies | Medium | Proper init containers and readiness probes |

---

## Success Criteria

### Functional
- [ ] All 37 components can be enabled/disabled via values.yaml
- [ ] HDFS can store and retrieve data
- [ ] YARN can schedule and run jobs
- [ ] Spark/Hive queries work correctly
- [ ] Kafka can produce/consume messages

### Security
- [ ] Kerberos authentication working
- [ ] SSL/TLS on all web UIs
- [ ] Encrypted RPC communication
- [ ] RBAC policies enforced

### Operations
- [ ] Cluster survives node failures
- [ ] Rolling updates without downtime
- [ ] Backup/restore procedures documented
- [ ] Monitoring shows all metrics

### Performance
- [ ] HDFS throughput comparable to VMs
- [ ] YARN scheduling latency acceptable
- [ ] No resource contention issues

---

## Tools & Technologies

### Development
- Docker / Podman
- Helm 3.x
- Kind / Minikube (local testing)
- VS Code with YAML extensions

### CI/CD
- GitHub Actions / GitLab CI
- Helm chart testing (chart-testing)
- Kubernetes cluster for integration tests

### Monitoring
- Prometheus + Grafana
- Elasticsearch + Kibana (logs)
- Jaeger (tracing)

---

## Next Steps

1. **Set up development environment**
2. **Start with ZooKeeper** (simplest, needed by others)
3. **Move to HDFS** (core storage)
4. **Iterate through remaining services**
5. **Add security layer**
6. **Production hardening**

---

## References

- [Hadoop on Kubernetes Best Practices](https://kubernetes.io/blog/2020/12/running-apache-hadoop-on-kubernetes/)
- [StatefulSet Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Helm Chart Development Guide](https://helm.sh/docs/chart_template_guide/)
- [Kerberos in Containers](https://web.mit.edu/kerberos/krb5-latest/doc/)
