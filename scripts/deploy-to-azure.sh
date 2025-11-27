#!/bin/bash
# Deploy MagicToolbox to Azure Container Apps
# This script follows Azure DevOps best practices for infrastructure deployment

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check if required tools are installed
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it from https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

# Parse command line arguments
usage() {
    cat << EOF
Usage: $0 --environment <env> --resource-group <rg> [options]

Required arguments:
    --environment ENV       Environment: dev, staging, or prod
    --resource-group RG     Azure resource group name

Optional arguments:
    --location LOCATION     Azure region (default: westeurope)
    --app-name NAME         Application name (default: magictoolbox)
    --skip-build           Skip Docker image build
    --skip-infra           Skip infrastructure deployment
    --help                 Show this help message

Examples:
    # Deploy to dev environment
    $0 --environment dev --resource-group rg-westeurope-magictoolbox-dev-01

    # Deploy to production with custom location
    $0 --environment prod --resource-group rg-westeurope-magictoolbox-prod-01 --location eastus2

    # Only deploy application (skip infrastructure)
    $0 --environment staging --resource-group rg-westeurope-magictoolbox-staging-01 --skip-infra
EOF
    exit 1
}

# Parse arguments
ENVIRONMENT=""
RESOURCE_GROUP=""
LOCATION="westeurope"
APP_NAME="magictoolbox"
SKIP_BUILD=false
SKIP_INFRA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --app-name)
            APP_NAME="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-infra)
            SKIP_INFRA=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [[ -z "$ENVIRONMENT" || -z "$RESOURCE_GROUP" ]]; then
    log_error "Missing required arguments"
    usage
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    log_error "Invalid environment. Must be: dev, staging, or prod"
    exit 1
fi

log_info "Deployment Configuration:"
log_info "  Environment: $ENVIRONMENT"
log_info "  Resource Group: $RESOURCE_GROUP"
log_info "  Location: $LOCATION"
log_info "  App Name: $APP_NAME"

# Check Azure login
log_info "Checking Azure authentication..."
if ! az account show &> /dev/null; then
    log_error "Not logged in to Azure. Please run 'az login'"
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
log_success "Logged in to Azure subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"

# Create resource group if it doesn't exist
log_info "Ensuring resource group exists..."
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    log_info "Creating resource group: $RESOURCE_GROUP"
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --tags Environment="$ENVIRONMENT" Application="MagicToolbox" ManagedBy="Bicep"
    log_success "Resource group created"
else
    log_success "Resource group already exists"
fi

# Deploy infrastructure
if [[ "$SKIP_INFRA" == false ]]; then
    log_info "Deploying Azure infrastructure with Bicep..."
    
    PARAMS_FILE="infra/parameters.${ENVIRONMENT}.json"
    if [[ ! -f "$PARAMS_FILE" ]]; then
        log_error "Parameters file not found: $PARAMS_FILE"
        exit 1
    fi
    
    # Generate secrets if not provided in parameters file
    DJANGO_SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    POSTGRES_PASSWORD=$(openssl rand -base64 32)
    
    # Deploy with Bicep
    DEPLOYMENT_NAME="magictoolbox-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
    
    log_info "Starting infrastructure deployment: $DEPLOYMENT_NAME"
    DEPLOYMENT_OUTPUT=$(az deployment group create \
        --name "$DEPLOYMENT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --template-file infra/main.bicep \
        --parameters "$PARAMS_FILE" \
        --parameters environment="$ENVIRONMENT" \
        --parameters appName="$APP_NAME" \
        --parameters location="$LOCATION" \
        --parameters djangoSecretKey="$DJANGO_SECRET_KEY" \
        --parameters postgresAdminPassword="$POSTGRES_PASSWORD" \
        --output json)
    
    if [[ $? -eq 0 ]]; then
        log_success "Infrastructure deployed successfully"
        
        # Extract outputs
        ACR_LOGIN_SERVER=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.acrLoginServer.value')
        CONTAINER_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.containerAppName.value')
        CONTAINER_APP_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.containerAppUrl.value')
        
        log_info "Deployment outputs:"
        log_info "  ACR: $ACR_LOGIN_SERVER"
        log_info "  Container App: $CONTAINER_APP_NAME"
        log_info "  URL: $CONTAINER_APP_URL"
    else
        log_error "Infrastructure deployment failed"
        exit 1
    fi
else
    log_warning "Skipping infrastructure deployment"
    
    # Get existing ACR and Container App
    ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
    ACR_LOGIN_SERVER=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].loginServer" -o tsv)
    CONTAINER_APP_NAME=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
    
    if [[ -z "$ACR_NAME" || -z "$CONTAINER_APP_NAME" ]]; then
        log_error "Could not find existing ACR or Container App in resource group"
        exit 1
    fi
fi

# Build and push Docker image
if [[ "$SKIP_BUILD" == false ]]; then
    log_info "Building Docker image..."
    
    IMAGE_TAG="$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')"
    IMAGE_NAME="$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG"
    IMAGE_LATEST="$ACR_LOGIN_SERVER/$APP_NAME:latest"
    
    docker build -t "$IMAGE_NAME" -t "$IMAGE_LATEST" .
    
    if [[ $? -eq 0 ]]; then
        log_success "Docker image built successfully"
    else
        log_error "Docker build failed"
        exit 1
    fi
    
    log_info "Logging in to Azure Container Registry..."
    az acr login --name "$ACR_NAME"
    
    log_info "Pushing image to ACR..."
    docker push "$IMAGE_NAME"
    docker push "$IMAGE_LATEST"
    
    if [[ $? -eq 0 ]]; then
        log_success "Image pushed to ACR successfully"
    else
        log_error "Failed to push image to ACR"
        exit 1
    fi
else
    log_warning "Skipping Docker build"
    IMAGE_TAG="latest"
fi

# Update Container App with new image
log_info "Updating Container App with new revision..."

az containerapp update \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$ACR_LOGIN_SERVER/$APP_NAME:latest" \
    --output none

if [[ $? -eq 0 ]]; then
    log_success "Container App updated successfully"
else
    log_error "Failed to update Container App"
    exit 1
fi

# Wait for revision to be ready
log_info "Waiting for new revision to become healthy..."
TIMEOUT=300  # 5 minutes
ELAPSED=0
INTERVAL=10

while [[ $ELAPSED -lt $TIMEOUT ]]; do
    HEALTH_STATE=$(az containerapp revision list \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].properties.healthState" -o tsv)
    
    if [[ "$HEALTH_STATE" == "Healthy" ]]; then
        log_success "New revision is healthy"
        break
    fi
    
    log_info "Current health state: $HEALTH_STATE (waiting ${ELAPSED}s/${TIMEOUT}s)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [[ $ELAPSED -ge $TIMEOUT ]]; then
    log_error "Timeout waiting for revision to become healthy"
    log_info "Check Container App logs for details:"
    log_info "  az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
    exit 1
fi

# Run database migrations
log_info "Running database migrations..."
az containerapp exec \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --command "python manage.py migrate --noinput" || log_warning "Migration command may have failed"

# Collect static files
log_info "Collecting static files..."
az containerapp exec \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --command "python manage.py collectstatic --noinput" || log_warning "Collectstatic command may have failed"

# Get final URL
CONTAINER_APP_URL=$(az containerapp show \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

log_success "Deployment completed successfully!"
log_info "Application URL: https://$CONTAINER_APP_URL"
log_info ""
log_info "Useful commands:"
log_info "  View logs: az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
log_info "  View revisions: az containerapp revision list --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP"
log_info "  Scale app: az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 1 --max-replicas 5"
