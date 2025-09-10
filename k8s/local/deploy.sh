#!/bin/bash

# AI DevOps Local Kubernetes Deployment Script
# For use with Docker Desktop Kubernetes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="ai-devops-local"
KUBECTL_TIMEOUT="300s"

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
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        log_info "Make sure Docker Desktop Kubernetes is enabled"
        exit 1
    fi
    
    # Check context
    local context=$(kubectl config current-context)
    if [[ "$context" != "docker-desktop" ]]; then
        log_warning "Current context is $context, expected docker-desktop"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Prerequisites check completed"
}

check_images() {
    log_info "Checking Docker images..."
    
    local required_images=(
        "controller-service:latest"
        "azure-devops-governance-factory-azure-devops-governance-factory:latest"
        "github-governance-factory:latest"
        "database-governance-factory:latest"
        "postgres:15-alpine"
        "mongo:7"
        "redis:7-alpine"
        "prom/prometheus:latest"
        "grafana/grafana:latest"
    )
    
    local missing_images=()
    
    for image in "${required_images[@]}"; do
        if ! docker image inspect "$image" &> /dev/null; then
            missing_images+=("$image")
        fi
    done
    
    if [[ ${#missing_images[@]} -gt 0 ]]; then
        log_error "Missing Docker images:"
        for image in "${missing_images[@]}"; do
            echo "  - $image"
        done
        log_info "Please build the missing images or pull them from a registry"
        exit 1
    fi
    
    log_success "All required Docker images are available"
}

deploy_manifests() {
    log_info "Deploying Kubernetes manifests..."
    
    local manifests=(
        "00-namespace.yaml"
        "01-databases.yaml"
        "02-applications.yaml"
        "03-monitoring.yaml"
    )
    
    for manifest in "${manifests[@]}"; do
        if [[ ! -f "$manifest" ]]; then
            log_error "Manifest file $manifest not found"
            exit 1
        fi
        
        log_info "Applying $manifest..."
        if kubectl apply -f "$manifest"; then
            log_success "Successfully applied $manifest"
        else
            log_error "Failed to apply $manifest"
            exit 1
        fi
        
        # Wait between critical components
        case "$manifest" in
            "00-namespace.yaml")
                sleep 5
                ;;
            "01-databases.yaml")
                log_info "Waiting for databases to be ready..."
                sleep 20
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
    
    echo ""
    log_info "Pod status:"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo ""
    log_info "Service status:"
    kubectl get services -n "$NAMESPACE"
    
    # Health checks
    log_info "Running health checks..."
    
    # Wait a bit for services to be fully ready
    sleep 10
    
    # Check controller health
    if kubectl get service controller-service -n "$NAMESPACE" &> /dev/null; then
        local node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
        log_info "Checking controller health at http://$node_ip:30000/health"
        
        # Use kubectl port-forward for health check
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

print_access_info() {
    log_info "=== AI DevOps Local Deployment Access Information ==="
    
    local node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "localhost")
    
    echo ""
    echo "🌐 Service Access URLs:"
    echo "  Controller:              http://$node_ip:30000"
    echo "  Azure DevOps Governance: http://$node_ip:30001"
    echo "  GitHub Governance:       http://$node_ip:30002"
    echo "  Database Governance:     http://$node_ip:30003"
    echo "  Prometheus:              http://$node_ip:30090"
    echo "  Grafana:                 http://$node_ip:30300 (admin/admin)"
    echo ""
    
    echo "🔧 Port Forward Commands (alternative access):"
    echo "  kubectl port-forward service/controller-service 8000:8000 -n $NAMESPACE"
    echo "  kubectl port-forward service/prometheus-service 9090:9090 -n $NAMESPACE"
    echo "  kubectl port-forward service/grafana-service 3000:3000 -n $NAMESPACE"
    echo ""
    
    echo "🚀 Useful Commands:"
    echo "  View all resources:  kubectl get all -n $NAMESPACE"
    echo "  View logs:          kubectl logs -f deployment/<name> -n $NAMESPACE"
    echo "  Scale deployment:   kubectl scale deployment <name> --replicas=2 -n $NAMESPACE"
    echo "  Delete deployment:  kubectl delete namespace $NAMESPACE"
    echo ""
    
    echo "📊 Health Check:"
    echo "  curl http://$node_ip:30000/health"
    echo ""
}

cleanup_on_error() {
    log_error "Deployment failed."
    
    read -p "Do you want to delete the failed deployment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace "$NAMESPACE" --timeout="$KUBECTL_TIMEOUT" || true
        log_info "Cleanup completed"
    fi
}

main() {
    echo "=================================="
    echo "AI DevOps Local K8s Deployment"
    echo "=================================="
    echo ""
    
    # Check if we're in the right directory
    if [[ ! -f "00-namespace.yaml" ]]; then
        log_error "Please run this script from the k8s/local directory"
        exit 1
    fi
    
    # Execute deployment steps
    check_prerequisites || exit 1
    check_images || exit 1
    
    if deploy_manifests; then
        wait_for_deployment
        verify_deployment
        print_access_info
        log_success "AI DevOps local deployment completed successfully!"
        echo ""
        log_info "You can now access the services using the URLs above."
        log_info "To test the Beta-42 mission, use: http://$node_ip:30000/api/v1/tenants/beta-42/onboard"
    else
        cleanup_on_error
        exit 1
    fi
}

# Handle script interruption
trap 'log_error "Script interrupted"; cleanup_on_error; exit 1' INT TERM

# Run main function
main "$@"
