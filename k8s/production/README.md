# AI DevOps Production Kubernetes Deployment

This directory contains production-ready Kubernetes manifests for the AI DevOps Orchestration System.

## Quick Start

```bash
# Deploy the entire system
chmod +x deploy.sh
./deploy.sh

# Or manually apply in order
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmaps.yaml
kubectl apply -f 02-secrets.yaml
kubectl apply -f 03-storage.yaml
kubectl apply -f 04-databases.yaml
kubectl apply -f 05-applications.yaml
kubectl apply -f 06-services.yaml
kubectl apply -f 07-monitoring.yaml
kubectl apply -f 08-ingress.yaml
kubectl apply -f 09-autoscaling.yaml
```

## Architecture Overview

### Components
- **Controller Service**: Main orchestration hub (3 replicas with HPA)
- **Governance Factories**: Azure DevOps, GitHub, Database (2 replicas each with HPA)
- **AI Provider Service**: AI/ML workload handling (2 replicas with HPA)
- **Databases**: PostgreSQL, MongoDB, Redis with persistent storage
- **Monitoring**: Prometheus + Grafana with custom dashboards
- **Load Balancing**: NGINX Ingress with SSL termination

### High Availability Features
- Multi-replica deployments with rolling updates
- Horizontal Pod Autoscaling (HPA) based on CPU/memory/custom metrics
- Pod Disruption Budgets (PDB) for zero-downtime updates
- Persistent storage with data retention
- Health checks and readiness probes
- Network policies for security

## File Structure

```
k8s/production/
├── 00-namespace.yaml       # Namespace, RBAC, Network Policies
├── 01-configmaps.yaml      # Application and database configurations
├── 02-secrets.yaml         # Sensitive data (passwords, keys, certs)
├── 03-storage.yaml         # Persistent Volumes and Claims
├── 04-databases.yaml       # PostgreSQL, MongoDB, Redis deployments
├── 05-applications.yaml    # AI DevOps service deployments
├── 06-services.yaml        # Service discovery and load balancing
├── 07-monitoring.yaml      # Prometheus, Grafana, alerting
├── 08-ingress.yaml         # External access and SSL termination
├── 09-autoscaling.yaml     # HPA, PDB, VPA configurations
├── deploy.sh               # Automated deployment script
└── README.md               # This file
```

## Prerequisites

### Cluster Requirements
- Kubernetes 1.24+
- Minimum 8 CPU cores, 16GB RAM
- 200GB+ persistent storage
- Ingress controller (NGINX recommended)
- StorageClass: `fast-ssd` for high-performance workloads

### Required Tools
- `kubectl` configured for your cluster
- Helm 3.x (for optional chart deployment)
- Docker images built and pushed to registry

## Security Configuration

### Secrets Management
**⚠️ IMPORTANT**: Update all default secrets before production deployment!

```bash
# Generate new secrets
kubectl create secret generic ai-devops-secret \
  --from-literal=JWT_SECRET_KEY="$(openssl rand -base64 32)" \
  --from-literal=ENCRYPTION_KEY="$(openssl rand -base64 32)" \
  -n ai-devops-system --dry-run=client -o yaml | kubectl apply -f -

# Generate database passwords
kubectl create secret generic postgres-secret \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -base64 24)" \
  -n ai-devops-system --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic mongodb-secret \
  --from-literal=MONGO_INITDB_ROOT_PASSWORD="$(openssl rand -base64 24)" \
  -n ai-devops-system --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic redis-secret \
  --from-literal=REDIS_PASSWORD="$(openssl rand -base64 24)" \
  -n ai-devops-system --dry-run=client -o yaml | kubectl apply -f -
```

### TLS Certificates
```bash
# For production, use real certificates
kubectl create secret tls ai-devops-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n ai-devops-system
```

### External Secrets (Optional)
Configure external secret management (Azure Key Vault, AWS Secrets Manager, etc.):
```bash
# Example for Azure Key Vault
kubectl create secret generic external-secrets-config \
  --from-literal=AZURE_TENANT_ID="your-tenant-id" \
  --from-literal=AZURE_CLIENT_ID="your-client-id" \
  --from-literal=AZURE_CLIENT_SECRET="your-client-secret" \
  -n ai-devops-system
```

## Storage Configuration

### StorageClass Setup
Create required StorageClasses if not available:

```yaml
# fast-ssd StorageClass (example for AWS EBS)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

### Storage Requirements
- PostgreSQL: 50GB (transactional data)
- MongoDB: 30GB (document storage)
- Redis: 10GB (cache data)
- Prometheus: 20GB (metrics data)
- Grafana: 5GB (dashboards, config)
- Backup: 100GB (automated backups)
- Logs: 50GB (centralized logging)

## Networking Configuration

### Domain Setup
Configure DNS for the following domains:
- `ai-devops.com` → Main application
- `api.ai-devops.com` → API gateway
- `admin.ai-devops.com` → Admin dashboard
- `monitoring.ai-devops.com` → Grafana/Prometheus
- `internal.ai-devops.com` → Internal services (restricted)

### Ingress Configuration
The system uses NGINX Ingress with:
- SSL/TLS termination
- Rate limiting (100 req/min)
- CORS configuration
- Security headers
- Load balancing with session affinity

### Network Policies
- Pod-to-pod communication within namespace
- Ingress controller access
- Database access restricted to application pods
- External egress for HTTPS/DNS only

## Monitoring and Alerting

### Prometheus Metrics
- Application metrics (HTTP requests, response times, errors)
- System metrics (CPU, memory, disk, network)
- Database metrics (connections, queries, performance)
- Custom business metrics (tenant operations, security events)

### Grafana Dashboards
- System Overview (service status, resource usage)
- Application Performance (request rates, response times)
- Database Performance (query performance, connections)
- Security Dashboard (failed authentications, suspicious activity)

### Alert Rules
- High CPU/Memory usage (>80%)
- Service downtime (>1 minute)
- High error rates (>10%)
- Database connectivity issues
- Disk space low (<10%)
- Pod restart loops

## Scaling Configuration

### Horizontal Pod Autoscaling (HPA)
- **Controller**: 3-10 replicas based on CPU/memory/RPS
- **Governance Services**: 2-8 replicas based on CPU/memory
- **AI Provider**: 2-12 replicas with custom AI metrics
- **Databases**: Single replica with vertical scaling

### Vertical Pod Autoscaling (VPA)
- Automatic resource recommendation for database workloads
- Memory and CPU optimization based on usage patterns

### Pod Disruption Budgets
- Ensures minimum availability during updates
- Controller: minimum 2 replicas available
- Governance services: minimum 1 replica available

## Backup and Recovery

### Automated Backups
- Database backups: Daily at 2 AM UTC
- Configuration backups: After each deployment
- Retention: 30 days for databases, 7 days for configs

### Disaster Recovery
```bash
# Backup entire namespace
kubectl get all,configmaps,secrets,pvc,ingress -n ai-devops-system -o yaml > backup.yaml

# Restore from backup
kubectl apply -f backup.yaml
```

## Access Information

### Service Access
```bash
# Port forwarding for local access
kubectl port-forward service/controller-service 8000:8000 -n ai-devops-system
kubectl port-forward service/grafana-service 3000:3000 -n ai-devops-system
kubectl port-forward service/prometheus-service 9090:9090 -n ai-devops-system

# External access via ingress
curl https://ai-devops.com/health
curl https://api.ai-devops.com/api/v1/status
curl https://monitoring.ai-devops.com/grafana/
```

### NodePort Access (Development)
If LoadBalancer is not available, NodePort services are configured:
- Controller: `<node-ip>:30000`
- Azure Governance: `<node-ip>:30001`
- GitHub Governance: `<node-ip>:30002`
- Database Governance: `<node-ip>:30003`
- AI Provider: `<node-ip>:30004`
- Prometheus: `<node-ip>:30090`
- Grafana: `<node-ip>:30300`

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending**
   ```bash
   kubectl describe pod <pod-name> -n ai-devops-system
   # Check resource requests vs cluster capacity
   ```

2. **PVC not binding**
   ```bash
   kubectl get pv,pvc -n ai-devops-system
   # Ensure StorageClass exists and provisioner is working
   ```

3. **Database connection issues**
   ```bash
   kubectl logs deployment/controller-deployment -n ai-devops-system
   # Check database service names and credentials
   ```

4. **Ingress not working**
   ```bash
   kubectl describe ingress ai-devops-ingress -n ai-devops-system
   # Verify ingress controller and DNS configuration
   ```

### Log Analysis
```bash
# View application logs
kubectl logs -f deployment/controller-deployment -n ai-devops-system

# View all pod logs
kubectl logs -l app=ai-devops -n ai-devops-system --tail=100

# Check events
kubectl get events -n ai-devops-system --sort-by='.lastTimestamp'
```

### Performance Monitoring
```bash
# Check resource usage
kubectl top pods -n ai-devops-system
kubectl top nodes

# Check HPA status
kubectl get hpa -n ai-devops-system

# Check service endpoints
kubectl get endpoints -n ai-devops-system
```

## Maintenance

### Rolling Updates
```bash
# Update application image
kubectl set image deployment/controller-deployment controller=ai-devops/controller:v1.1.0 -n ai-devops-system

# Check rollout status
kubectl rollout status deployment/controller-deployment -n ai-devops-system

# Rollback if needed
kubectl rollout undo deployment/controller-deployment -n ai-devops-system
```

### Scaling Operations
```bash
# Manual scaling
kubectl scale deployment controller-deployment --replicas=5 -n ai-devops-system

# Update HPA configuration
kubectl patch hpa controller-hpa -p '{"spec":{"maxReplicas":15}}' -n ai-devops-system
```

### Certificate Renewal
```bash
# Update TLS certificate
kubectl create secret tls ai-devops-tls \
  --cert=new-tls.crt \
  --key=new-tls.key \
  -n ai-devops-system \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Security Best Practices

1. **Regular Security Updates**
   - Keep base images updated
   - Monitor for CVEs in dependencies
   - Update Kubernetes cluster regularly

2. **Access Control**
   - Use RBAC for service accounts
   - Implement network policies
   - Regular audit of permissions

3. **Secret Management**
   - Rotate secrets regularly
   - Use external secret management
   - Never commit secrets to version control

4. **Monitoring and Auditing**
   - Enable audit logging
   - Monitor for suspicious activities
   - Set up security alerts

## Performance Optimization

1. **Resource Allocation**
   - Right-size pod requests/limits
   - Use VPA for optimization recommendations
   - Monitor resource utilization

2. **Database Optimization**
   - Tune database configurations
   - Implement connection pooling
   - Regular performance analysis

3. **Caching Strategy**
   - Optimize Redis configuration
   - Implement application-level caching
   - Use CDN for static content

4. **Network Optimization**
   - Use service mesh for advanced networking
   - Implement circuit breakers
   - Optimize ingress configuration

## Support and Documentation

For additional support:
- Review application logs for detailed error information
- Check Prometheus metrics for performance insights
- Use Grafana dashboards for system visualization
- Consult the main project documentation in the repository root

---

**Note**: This production configuration assumes a managed Kubernetes cluster with appropriate networking, storage, and security configurations. Adjust resource requirements and scaling parameters based on your specific workload and cluster capacity.
