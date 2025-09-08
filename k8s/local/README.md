# AI DevOps Local Kubernetes Deployment (Docker Desktop)

This directory contains Kubernetes manifests for deploying the AI DevOps Orchestration System locally using Docker Desktop Kubernetes.

## Prerequisites

- Docker Desktop with Kubernetes enabled
- kubectl configured to use docker-desktop context
- AI DevOps Docker images built locally

## Quick Start

```powershell
# Navigate to the local deployment directory
cd k8s/local

# Deploy using the script (if using bash/WSL)
bash deploy.sh

# Or deploy manually with kubectl
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-databases.yaml
kubectl apply -f 02-applications.yaml
kubectl apply -f 03-monitoring.yaml
```

## Manual Deployment (PowerShell)

```powershell
# Apply manifests in order
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-databases.yaml

# Wait for databases to be ready
Start-Sleep -Seconds 30

kubectl apply -f 02-applications.yaml
kubectl apply -f 03-monitoring.yaml

# Wait for all deployments
kubectl wait --for=condition=Available deployment --all -n ai-devops-local --timeout=300s
```

## Service Access

Once deployed, services are accessible via NodePort:

| Service | URL | Description |
|---------|-----|-------------|
| Controller | http://localhost:30000 | Main orchestration service |
| Azure DevOps Governance | http://localhost:30001 | Azure DevOps factory |
| GitHub Governance | http://localhost:30002 | GitHub factory |
| Database Governance | http://localhost:30003 | Database factory |
| Prometheus | http://localhost:30090 | Metrics collection |
| Grafana | http://localhost:30300 | Monitoring dashboard (admin/admin) |

## Health Check

```powershell
# Check controller health
Invoke-RestMethod -Uri http://localhost:30000/health

# Check all pod status
kubectl get pods -n ai-devops-local

# View service status
kubectl get services -n ai-devops-local
```

## Testing Beta-42 Mission

```powershell
# Test the autonomous tenant onboarding
Invoke-RestMethod -Uri http://localhost:30000/api/v1/tenants/beta-42/onboard -Method POST

# Check operation status
Invoke-RestMethod -Uri http://localhost:30000/api/v1/tenants/beta-42/status
```

## Port Forwarding (Alternative Access)

```powershell
# Controller service
kubectl port-forward service/controller-service 8000:8000 -n ai-devops-local

# Grafana
kubectl port-forward service/grafana-service 3000:3000 -n ai-devops-local

# Prometheus
kubectl port-forward service/prometheus-service 9090:9090 -n ai-devops-local
```

## Viewing Logs

```powershell
# View controller logs
kubectl logs -f deployment/controller-deployment -n ai-devops-local

# View all service logs
kubectl logs -l app=ai-devops -n ai-devops-local --tail=100

# View events
kubectl get events -n ai-devops-local --sort-by='.lastTimestamp'
```

## Scaling Services

```powershell
# Scale controller to 2 replicas
kubectl scale deployment controller-deployment --replicas=2 -n ai-devops-local

# Scale governance services
kubectl scale deployment azure-devops-governance-deployment --replicas=2 -n ai-devops-local
```

## Troubleshooting

### Common Issues

1. **Pods stuck in ImagePullBackOff**
   - Ensure Docker images are built locally
   - Check image names match exactly

2. **Services not responding**
   - Wait longer for startup (some services need 1-2 minutes)
   - Check logs: `kubectl logs -f deployment/<name> -n ai-devops-local`

3. **Database connection issues**
   - Ensure databases are running: `kubectl get pods -n ai-devops-local | grep database`
   - Check service discovery: `kubectl get services -n ai-devops-local`

### Debugging Commands

```powershell
# Describe pod for detailed info
kubectl describe pod <pod-name> -n ai-devops-local

# Check resource usage
kubectl top pods -n ai-devops-local

# Check endpoints
kubectl get endpoints -n ai-devops-local

# View configmaps and secrets
kubectl get configmaps,secrets -n ai-devops-local
```

## Cleanup

```powershell
# Delete entire deployment
kubectl delete namespace ai-devops-local

# Or delete specific resources
kubectl delete -f 03-monitoring.yaml
kubectl delete -f 02-applications.yaml
kubectl delete -f 01-databases.yaml
kubectl delete -f 00-namespace.yaml
```

## Configuration

### Environment Variables
- All services use local development configuration
- Database passwords are set to simple values for local testing
- Debug logging is enabled

### Storage
- Uses emptyDir volumes (data is ephemeral)
- For persistent data, modify manifests to use PersistentVolumes

### Networking
- NodePort services for easy access
- Internal service discovery via DNS
- No ingress controller required

## Performance Notes

- Resource requests/limits are set for local development
- Single replica deployments to minimize resource usage
- Monitoring stack included but lightweight

## Security Notes

- **Local development only** - not production ready
- Simple passwords and secrets
- No TLS/SSL encryption
- No network policies or RBAC restrictions

---

This local deployment is perfect for:
- Development and testing
- Demonstrating the Beta-42 mission
- Learning Kubernetes concepts
- Debugging service interactions

For production deployment, use the manifests in the `k8s/production` directory.
