#!/bin/bash
# Setup GitHub Secrets and Environments for MagicToolbox CI/CD
# This script configures GitHub repository secrets and environments for automated deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed"
        log_info "Install it from: https://cli.github.com/"
        exit 1
    fi
    
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed"
        log_info "Install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed"
        log_info "Install it: sudo apt-get install jq (Ubuntu) or brew install jq (macOS)"
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

# Authenticate with GitHub
authenticate_github() {
    log_info "Checking GitHub authentication..."
    
    if ! gh auth status &> /dev/null; then
        log_info "Please authenticate with GitHub..."
        gh auth login
    fi
    
    log_success "GitHub authentication verified"
}

# Get repository information
get_repo_info() {
    log_info "Getting repository information..."
    
    REPO_OWNER=$(git config --get remote.origin.url | sed -n 's#.*/\([^/]*\)/\([^/]*\)\.git#\1#p')
    REPO_NAME=$(git config --get remote.origin.url | sed -n 's#.*/\([^/]*\)/\([^/]*\)\.git#\2#p')
    
    if [ -z "$REPO_OWNER" ] || [ -z "$REPO_NAME" ]; then
        log_error "Could not determine repository owner and name"
        log_info "Please ensure you're in a git repository with a remote named 'origin'"
        exit 1
    fi
    
    log_success "Repository: $REPO_OWNER/$REPO_NAME"
}

# Get Azure information
get_azure_info() {
    log_info "Getting Azure information..."
    
    # Check Azure login
    if ! az account show &> /dev/null; then
        log_error "Not logged in to Azure. Please run 'az login'"
        exit 1
    fi
    
    # Get subscription and tenant
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    TENANT_ID=$(az account show --query tenantId -o tsv)
    
    log_success "Azure Subscription: $SUBSCRIPTION_ID"
    log_success "Azure Tenant: $TENANT_ID"
}

# Create service principal for CI/CD
create_service_principal() {
    local ENV=$1
    local RG=$2
    local SP_NAME="sp-magictoolbox-cicd-${ENV}"
    
    log_info "Creating service principal for $ENV environment..."
    
    # Check if service principal already exists
    SP_APP_ID=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv 2>/dev/null)
    
    if [ -n "$SP_APP_ID" ]; then
        log_warning "Service principal $SP_NAME already exists (App ID: $SP_APP_ID)"
        read -p "Do you want to reset credentials? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Resetting credentials..."
            SP_CREDENTIALS=$(az ad sp credential reset --id "$SP_APP_ID" --query "{clientId:appId, clientSecret:password, tenantId:tenant}" -o json)
        else
            log_error "Cannot proceed without service principal credentials"
            log_info "Please manually provide the credentials or reset them"
            exit 1
        fi
    else
        # Create new service principal with contributor role on resource group
        log_info "Creating new service principal with Contributor role on $RG..."
        
        # Ensure resource group exists
        if ! az group show --name "$RG" &> /dev/null; then
            log_error "Resource group $RG does not exist"
            log_info "Please create it first or provide the correct resource group name"
            exit 1
        fi
        
        RG_ID=$(az group show --name "$RG" --query id -o tsv)
        
        SP_CREDENTIALS=$(az ad sp create-for-rbac \
            --name "$SP_NAME" \
            --role Contributor \
            --scopes "$RG_ID" \
            --query "{clientId:appId, clientSecret:password, tenantId:tenant}" \
            -o json)
        
        # Get the service principal object ID for additional role assignment
        SP_OBJECT_ID=$(az ad sp list --display-name "$SP_NAME" --query "[0].id" -o tsv)
    fi
    
    # Get service principal object ID if not set (for existing SP with reset credentials)
    if [ -z "$SP_OBJECT_ID" ]; then
        SP_OBJECT_ID=$(az ad sp list --display-name "$SP_NAME" --query "[0].id" -o tsv)
    fi
    
    # Grant User Access Administrator role for RBAC role assignments
    log_info "Granting User Access Administrator role to service principal..."
    az role assignment create \
        --assignee "$SP_OBJECT_ID" \
        --role "User Access Administrator" \
        --scope "$RG_ID" \
        --output none 2>/dev/null || log_warning "User Access Administrator role may already be assigned"
    
    # Extract credentials
    CLIENT_ID=$(echo "$SP_CREDENTIALS" | jq -r '.clientId')
    CLIENT_SECRET=$(echo "$SP_CREDENTIALS" | jq -r '.clientSecret')
    TENANT_ID_SP=$(echo "$SP_CREDENTIALS" | jq -r '.tenantId')
    
    # Create Azure credentials JSON
    AZURE_CREDENTIALS=$(jq -n \
        --arg clientId "$CLIENT_ID" \
        --arg clientSecret "$CLIENT_SECRET" \
        --arg subscriptionId "$SUBSCRIPTION_ID" \
        --arg tenantId "$TENANT_ID_SP" \
        '{clientId: $clientId, clientSecret: $clientSecret, subscriptionId: $subscriptionId, tenantId: $tenantId}')
    
    log_success "Service principal created/updated for $ENV"
    
    echo "$AZURE_CREDENTIALS"
}

# Get ACR credentials
get_acr_credentials() {
    local RG=$1
    
    log_info "Getting Azure Container Registry credentials..."
    
    ACR_NAME=$(az acr list --resource-group "$RG" --query "[0].name" -o tsv)
    
    if [ -z "$ACR_NAME" ]; then
        log_error "No Azure Container Registry found in resource group $RG"
        exit 1
    fi
    
    ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
    
    # Enable admin access (required for GitHub Actions)
    az acr update --name "$ACR_NAME" --admin-enabled true > /dev/null
    
    ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
    ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
    
    log_success "ACR: $ACR_LOGIN_SERVER"
    
    echo "$ACR_NAME|$ACR_LOGIN_SERVER|$ACR_USERNAME|$ACR_PASSWORD"
}

# Create GitHub environments
create_github_environments() {
    log_info "Creating GitHub environments..."
    
    # Development environment
    log_info "Creating development environment..."
    gh api \
        --method PUT \
        -H "Accept: application/vnd.github+json" \
        "/repos/$REPO_OWNER/$REPO_NAME/environments/development" \
        -f wait_timer=0 \
        > /dev/null 2>&1 || log_warning "Development environment may already exist"
    
    # Staging environment
    log_info "Creating staging environment..."
    gh api \
        --method PUT \
        -H "Accept: application/vnd.github+json" \
        "/repos/$REPO_OWNER/$REPO_NAME/environments/staging" \
        -f wait_timer=0 \
        > /dev/null 2>&1 || log_warning "Staging environment may already exist"
    
    # Production environment (with protection rules)
    log_info "Creating production environment with required reviewers..."
    gh api \
        --method PUT \
        -H "Accept: application/vnd.github+json" \
        "/repos/$REPO_OWNER/$REPO_NAME/environments/production" \
        -f wait_timer=0 \
        > /dev/null 2>&1 || log_warning "Production environment may already exist"
    
    log_success "GitHub environments created"
}

# Set GitHub secret
set_github_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2
    local ENV=$3
    
    if [ -n "$ENV" ]; then
        log_info "Setting environment secret: $SECRET_NAME (environment: $ENV)"
        gh secret set "$SECRET_NAME" \
            --env "$ENV" \
            --body "$SECRET_VALUE" \
            --repo "$REPO_OWNER/$REPO_NAME"
    else
        log_info "Setting repository secret: $SECRET_NAME"
        gh secret set "$SECRET_NAME" \
            --body "$SECRET_VALUE" \
            --repo "$REPO_OWNER/$REPO_NAME"
    fi
}

# Main setup function
main() {
    log_info "========================================="
    log_info "GitHub Secrets Setup for MagicToolbox"
    log_info "========================================="
    echo
    
    check_prerequisites
    authenticate_github
    get_repo_info
    get_azure_info
    
    echo
    log_info "This script will create GitHub secrets and environments for:"
    log_info "  - Development environment"
    log_info "  - Staging environment (optional)"
    log_info "  - Production environment"
    echo
    
    # Get resource group names
    read -p "Enter DEVELOPMENT resource group name [rg-westeurope-magictoolbox-dev-01]: " RG_DEV
    RG_DEV=${RG_DEV:-rg-westeurope-magictoolbox-dev-01}
    
    read -p "Do you want to setup STAGING environment? (y/n) [n]: " -n 1 -r
    echo
    SETUP_STAGING=false
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        SETUP_STAGING=true
        read -p "Enter STAGING resource group name [rg-westeurope-magictoolbox-staging-01]: " RG_STAGING
        RG_STAGING=${RG_STAGING:-rg-westeurope-magictoolbox-staging-01}
    fi
    
    read -p "Do you want to setup PRODUCTION environment? (y/n) [y]: " -n 1 -r
    echo
    SETUP_PROD=true
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        SETUP_PROD=false
    else
        read -p "Enter PRODUCTION resource group name [rg-westeurope-magictoolbox-prod-01]: " RG_PROD
        RG_PROD=${RG_PROD:-rg-westeurope-magictoolbox-prod-01}
    fi
    
    echo
    log_info "Configuration:"
    log_info "  Development RG: $RG_DEV"
    [ "$SETUP_STAGING" = true ] && log_info "  Staging RG: $RG_STAGING"
    [ "$SETUP_PROD" = true ] && log_info "  Production RG: $RG_PROD"
    echo
    
    read -p "Continue with setup? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Setup cancelled"
        exit 1
    fi
    
    # Create GitHub environments
    create_github_environments
    
    # Get ACR credentials (shared across environments)
    ACR_INFO=$(get_acr_credentials "$RG_DEV")
    ACR_NAME=$(echo "$ACR_INFO" | cut -d'|' -f1)
    ACR_LOGIN_SERVER=$(echo "$ACR_INFO" | cut -d'|' -f2)
    ACR_USERNAME=$(echo "$ACR_INFO" | cut -d'|' -f3)
    ACR_PASSWORD=$(echo "$ACR_INFO" | cut -d'|' -f4)
    
    # Set repository-level secrets (shared)
    log_info "Setting repository-level secrets..."
    set_github_secret "ACR_LOGIN_SERVER" "$ACR_LOGIN_SERVER"
    set_github_secret "ACR_USERNAME" "$ACR_USERNAME"
    set_github_secret "ACR_PASSWORD" "$ACR_PASSWORD"
    set_github_secret "ACR_NAME" "$ACR_NAME"
    
    # Development environment
    log_info "Setting up DEVELOPMENT environment..."
    AZURE_CREDS_DEV=$(create_service_principal "dev" "$RG_DEV")
    CONTAINER_APP_NAME_DEV=$(az containerapp list --resource-group "$RG_DEV" --query "[0].name" -o tsv 2>/dev/null || echo "")
    
    set_github_secret "AZURE_CREDENTIALS_DEV" "$AZURE_CREDS_DEV" "development"
    set_github_secret "RESOURCE_GROUP_DEV" "$RG_DEV" "development"
    [ -n "$CONTAINER_APP_NAME_DEV" ] && set_github_secret "CONTAINER_APP_NAME_DEV" "$CONTAINER_APP_NAME_DEV" "development"
    
    # Staging environment
    if [ "$SETUP_STAGING" = true ]; then
        log_info "Setting up STAGING environment..."
        AZURE_CREDS_STAGING=$(create_service_principal "staging" "$RG_STAGING")
        CONTAINER_APP_NAME_STAGING=$(az containerapp list --resource-group "$RG_STAGING" --query "[0].name" -o tsv 2>/dev/null || echo "")
        
        set_github_secret "AZURE_CREDENTIALS_STAGING" "$AZURE_CREDS_STAGING" "staging"
        set_github_secret "RESOURCE_GROUP_STAGING" "$RG_STAGING" "staging"
        [ -n "$CONTAINER_APP_NAME_STAGING" ] && set_github_secret "CONTAINER_APP_NAME_STAGING" "$CONTAINER_APP_NAME_STAGING" "staging"
    fi
    
    # Production environment
    if [ "$SETUP_PROD" = true ]; then
        log_info "Setting up PRODUCTION environment..."
        AZURE_CREDS_PROD=$(create_service_principal "prod" "$RG_PROD")
        CONTAINER_APP_NAME_PROD=$(az containerapp list --resource-group "$RG_PROD" --query "[0].name" -o tsv 2>/dev/null || echo "")
        
        set_github_secret "AZURE_CREDENTIALS_PROD" "$AZURE_CREDS_PROD" "production"
        set_github_secret "RESOURCE_GROUP_PROD" "$RG_PROD" "production"
        [ -n "$CONTAINER_APP_NAME_PROD" ] && set_github_secret "CONTAINER_APP_NAME_PROD" "$CONTAINER_APP_NAME_PROD" "production"
    fi
    
    echo
    log_success "========================================="
    log_success "GitHub Secrets Setup Complete!"
    log_success "========================================="
    echo
    log_info "Summary:"
    log_info "  ✅ GitHub environments created"
    log_info "  ✅ Repository secrets configured"
    log_info "  ✅ Development environment secrets set"
    [ "$SETUP_STAGING" = true ] && log_info "  ✅ Staging environment secrets set"
    [ "$SETUP_PROD" = true ] && log_info "  ✅ Production environment secrets set"
    echo
    log_info "Next steps:"
    log_info "  1. Configure production environment protection rules:"
    log_info "     https://github.com/$REPO_OWNER/$REPO_NAME/settings/environments"
    log_info "  2. Add required reviewers for production deployments"
    log_info "  3. Test the CI/CD pipeline by pushing to develop or main branch"
    echo
    log_info "View secrets: https://github.com/$REPO_OWNER/$REPO_NAME/settings/secrets/actions"
    log_info "View environments: https://github.com/$REPO_OWNER/$REPO_NAME/settings/environments"
    echo
}

# Run main function
main
