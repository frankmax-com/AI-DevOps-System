# Deployment Script for AI DevOps Production Environment
#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="ai-devops-system"
KUBECTL_TIMEOUT="300s"
DEPLOYMENT_ORDER=(
    "00-namespace.yaml"
    "01-configmaps.yaml"
    "02-secrets.yaml"
    "03-storage.yaml"
    "04-databases.yaml"
    "05-applications.yaml"
    "06-services.yaml"
    "07-monitoring.yaml"
    "08-ingress.yaml"
    "09-autoscaling.yaml"
)

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if running as root (for some operations)
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. Some operations may require non-root user."
    fi
    
    # Check required files
    for file in "${DEPLOYMENT_ORDER[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required file $file not found"
            exit 1
        fi
    done
    
    log_success "Prerequisites check completed"
}

backup_existing_deployment() {
    log_info "Creating backup of existing deployment..."
    
    local backup_dir="backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup existing resources if they exist
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        kubectl get all,configmaps,secrets,pvc,ingress -n "$NAMESPACE" -o yaml > "$backup_dir/existing-resources.yaml" 2>/dev/null || true
        log_success "Backup created in $backup_dir"
    else
        log_info "No existing deployment found to backup"
    fi
}

apply_manifests() {
    log_info "Applying Kubernetes manifests..."
    
    for file in "${DEPLOYMENT_ORDER[@]}"; do
        log_info "Applying $file..."
        
        if kubectl apply -f "$file" --timeout="$KUBECTL_TIMEOUT"; then
            log_success "Successfully applied $file"
        else
            log_error "Failed to apply $file"
            return 1
        fi
        
        # Wait between critical components
        case "$file" in
            "00-namespace.yaml")
                log_info "Waiting for namespace to be ready..."
                kubectl wait --for=condition=Ready namespace/"$NAMESPACE" --timeout="$KUBECTL_TIMEOUT" || true
                sleep 5
                ;;
            "03-storage.yaml")
                log_info "Waiting for persistent volumes to be bound..."
                sleep 10
                ;;
            "04-databases.yaml")
                log_info "Waiting for databases to be ready..."
                sleep 30
                ;;
        esac
    done
}

wait_for_deployment() {
    log_info "Waiting for deployments to be ready..."
    
    local deployments=(
        "postgres-deployment"
        "mongodb-deployment" 
        "redis-deployment"
        "controller-deployment"
        "azure-devops-governance-deployment"
        "github-governance-deployment"
        "database-governance-deployment"
        "ai-provider-deployment"
        "prometheus-deployment"
        "grafana-deployment"
    )
    
    for deployment in "${deployments[@]}"; do
        log_info "Waiting for $deployment to be ready..."
        if kubectl wait --for=condition=Available deployment/"$deployment" -n "$NAMESPACE" --timeout="$KUBECTL_TIMEOUT"; then
            log_success "$deployment is ready"
        else
            log_warning "$deployment is not ready within timeout"
        fi
    done
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pod status
    log_info "Pod status:"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    # Check service status
    log_info "Service status:"
    kubectl get services -n "$NAMESPACE"
    
    # Check ingress status
    log_info "Ingress status:"
    kubectl get ingress -n "$NAMESPACE"
    
    # Check persistent volumes
    log_info "Persistent Volume status:"
    kubectl get pv,pvc -n "$NAMESPACE"
    
    # Check for failed pods
    local failed_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Failed -o name 2>/dev/null | wc -l)
    if [[ $failed_pods -gt 0 ]]; then
        log_warning "Found $failed_pods failed pods"
        kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Failed
    fi
    
    # Check for pending pods
    local pending_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Pending -o name 2>/dev/null | wc -l)
    if [[ $pending_pods -gt 0 ]]; then
        log_warning "Found $pending_pods pending pods"
        kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Pending
    fi
    
    # Health checks
    log_info "Running health checks..."
    
    # Check if controller service is responding
    if kubectl get service controller-service -n "$NAMESPACE" &> /dev/null; then
        log_info "Controller service found"
        # Port forward temporarily for health check
        kubectl port-forward service/controller-service 8080:8000 -n "$NAMESPACE" &
        local pf_pid=$!
        sleep 5
        
        if curl -f http://localhost:8080/health &> /dev/null; then
            log_success "Controller health check passed"
        else
            log_warning "Controller health check failed"
        fi
        
        kill $pf_pid 2>/dev/null || true
    fi
}

setup_monitoring() {
    log_info "Setting up monitoring access..."
    
    # Get Grafana service info
    local grafana_nodeport=$(kubectl get service grafana-service -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
    local prometheus_nodeport=$(kubectl get service prometheus-service -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
    
    if [[ -n "$grafana_nodeport" ]]; then
        log_success "Grafana will be available at: http://<node-ip>:$grafana_nodeport"
    fi
    
    if [[ -n "$prometheus_nodeport" ]]; then
        log_success "Prometheus will be available at: http://<node-ip>:$prometheus_nodeport"
    fi
    
    # Check ingress
    local ingress_ip=$(kubectl get ingress ai-devops-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [[ -n "$ingress_ip" ]]; then
        log_success "AI DevOps system will be available at: https://$ingress_ip"
    else
        log_info "Ingress IP not yet assigned. Check with: kubectl get ingress -n $NAMESPACE"
    fi
}

print_access_info() {
    log_info "=== AI DevOps System Access Information ==="
    
    echo ""
    echo "Namespace: $NAMESPACE"
    echo ""
    echo "Services:"
    kubectl get services -n "$NAMESPACE" --no-headers | while read line; do
        echo "  - $line"
    done
    
    echo ""
    echo "Ingress:"
    kubectl get ingress -n "$NAMESPACE" --no-headers | while read line; do
        echo "  - $line"
    done
    
    echo ""
    echo "Useful Commands:"
    echo "  - View all resources: kubectl get all -n $NAMESPACE"
    echo "  - View logs: kubectl logs -f deployment/<deployment-name> -n $NAMESPACE"
    echo "  - Port forward controller: kubectl port-forward service/controller-service 8000:8000 -n $NAMESPACE"
    echo "  - Port forward Grafana: kubectl port-forward service/grafana-service 3000:3000 -n $NAMESPACE"
    echo "  - Port forward Prometheus: kubectl port-forward service/prometheus-service 9090:9090 -n $NAMESPACE"
    echo ""
    echo "Default Credentials:"
    echo "  - Grafana: admin / (check ai-devops-secret)"
    echo "  - Database passwords are stored in respective secrets"
    echo ""
}

cleanup_on_error() {
    log_error "Deployment failed. Cleaning up..."
    
    # Optional: rollback or cleanup
    read -p "Do you want to delete the failed deployment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace "$NAMESPACE" --timeout="$KUBECTL_TIMEOUT" || true
        log_info "Cleanup completed"
    fi
}

main() {
    echo "=================================="
    echo "AI DevOps Production Deployment"
    echo "=================================="
    echo ""
    
    # Check if we're in the right directory
    if [[ ! -f "00-namespace.yaml" ]]; then
        log_error "Please run this script from the k8s/production directory"
        exit 1
    fi
    
    # Confirmation
    read -p "This will deploy AI DevOps to production. Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
    
    # Execute deployment steps
    check_prerequisites || exit 1
    backup_existing_deployment || exit 1
    
    if apply_manifests; then
        wait_for_deployment
        verify_deployment
        setup_monitoring
        print_access_info
        log_success "AI DevOps production deployment completed successfully!"
    else
        cleanup_on_error
        exit 1
    fi
}

# Handle script interruption
trap 'log_error "Script interrupted"; cleanup_on_error; exit 1' INT TERM

# Run main function
main "$@"
