#!/bin/bash
# DeepTech Radar - Staging Deployment Script
# This script deploys the complete DeepTech Radar stack to the staging environment

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="deeptech-staging"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}/../deploy/k8s/staging"

# Functions
echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    echo_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        echo_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        echo_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Check required environment variables
    if [ -z "${DATABASE_URL}" ]; then
        echo_error "DATABASE_URL environment variable is not set."
        echo_error "Please set it with: export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/deeptech_staging'"
        exit 1
    fi
    
    if [ -z "${OPENAI_API_KEY}" ]; then
        echo_error "OPENAI_API_KEY environment variable is not set."
        echo_error "Please set it with: export OPENAI_API_KEY='sk-...'"
        exit 1
    fi
    
    if [ -z "${GITHUB_TOKEN}" ]; then
        echo_error "GITHUB_TOKEN environment variable is not set."
        echo_error "Please set it with: export GITHUB_TOKEN='ghp_...'"
        exit 1
    fi
    
    echo_info "Prerequisites check passed ✓"
}

create_namespace() {
    echo_info "Creating namespace: ${NAMESPACE}..."
    kubectl apply -f "${K8S_DIR}/namespace.yaml"
    echo_info "Namespace created ✓"
}

create_secrets() {
    echo_info "Creating secrets..."
    
    # Create secrets from environment variables
    kubectl create secret generic deeptech-secrets \
        --from-literal=database-url="${DATABASE_URL}" \
        --from-literal=openai-api-key="${OPENAI_API_KEY}" \
        --from-literal=github-token="${GITHUB_TOKEN}" \
        --namespace="${NAMESPACE}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    echo_info "Secrets created ✓"
}

create_configmap() {
    echo_info "Creating ConfigMap..."
    kubectl apply -f "${K8S_DIR}/configmap.yaml"
    echo_info "ConfigMap created ✓"
}

deploy_api() {
    echo_info "Deploying API service..."
    
    # Apply deployment
    kubectl apply -f "${K8S_DIR}/api-deployment.yaml"
    
    # Apply service
    kubectl apply -f "${K8S_DIR}/api-service.yaml"
    
    # Apply ingress
    kubectl apply -f "${K8S_DIR}/api-ingress.yaml"
    
    echo_info "API service deployed ✓"
}

deploy_cronjobs() {
    echo_info "Deploying CronJobs..."
    kubectl apply -f "${K8S_DIR}/cronjobs.yaml"
    echo_info "CronJobs deployed ✓"
}

wait_for_deployment() {
    echo_info "Waiting for API deployment to be ready..."
    
    if kubectl wait --for=condition=available --timeout=300s deployment/deeptech-api -n "${NAMESPACE}"; then
        echo_info "API deployment is ready ✓"
    else
        echo_error "API deployment failed to become ready within timeout"
        echo_error "Check pod status with: kubectl get pods -n ${NAMESPACE}"
        echo_error "Check pod logs with: kubectl logs -n ${NAMESPACE} -l app=deeptech-api"
        exit 1
    fi
}

show_status() {
    echo_info "Deployment Status:"
    echo ""
    echo "Pods:"
    kubectl get pods -n "${NAMESPACE}"
    echo ""
    echo "Services:"
    kubectl get svc -n "${NAMESPACE}"
    echo ""
    echo "Ingress:"
    kubectl get ingress -n "${NAMESPACE}"
    echo ""
    echo "CronJobs:"
    kubectl get cronjobs -n "${NAMESPACE}"
}

main() {
    echo_info "Starting DeepTech Radar staging deployment..."
    echo ""
    
    check_prerequisites
    echo ""
    
    create_namespace
    echo ""
    
    create_secrets
    echo ""
    
    create_configmap
    echo ""
    
    deploy_api
    echo ""
    
    deploy_cronjobs
    echo ""
    
    wait_for_deployment
    echo ""
    
    show_status
    echo ""
    
    echo_info "🎉 Staging deployment complete!"
    echo ""
    echo_info "Next steps:"
    echo "  1. Verify health: kubectl port-forward -n ${NAMESPACE} svc/deeptech-api 8000:8000"
    echo "  2. Then check: curl http://localhost:8000/health"
    echo "  3. Run validation: python scripts/validate_staging.py"
    echo "  4. Check metrics: curl http://localhost:8000/metrics"
    echo "  5. Manually trigger a worker: kubectl create job --from=cronjob/arxiv-hourly arxiv-manual-1 -n ${NAMESPACE}"
}

# Run main function
main
