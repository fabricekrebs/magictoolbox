# GitHub Secrets and Environments Setup Guide

This guide explains how to configure GitHub secrets and environments for the MagicToolbox CI/CD pipeline.

## Quick Setup (Automated)

The easiest way to set up all secrets and environments is using the automated script:

```bash
# Make the script executable (if not already)
chmod +x scripts/setup-github-secrets.sh

# Run the setup script
./scripts/setup-github-secrets.sh
```

The script will:
- ✅ Create GitHub environments (development, staging, production)
- ✅ Create Azure service principals for each environment
- ✅ Configure all required secrets
- ✅ Enable ACR admin access
- ✅ Validate Azure resources

## Manual Setup

If you prefer to set up secrets manually, follow these steps:

### Prerequisites

1. **GitHub CLI**: Install from https://cli.github.com/
2. **Azure CLI**: Install from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
3. **Repository Access**: Admin access to the GitHub repository
4. **Azure Access**: Contributor role on Azure subscription/resource groups

### Step 1: Create GitHub Environments

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Environments**
3. Create three environments:
   - `development`
   - `staging` (optional)
   - `production`

4. For **production** environment:
   - Click on the environment name
   - Enable **Required reviewers**
   - Add team members who should approve production deployments
   - Set **Wait timer** to 0 (or desired minutes)

### Step 2: Create Azure Service Principals

You need a service principal for each environment to allow GitHub Actions to deploy to Azure.

**Important**: Each service principal requires **TWO roles**:
1. **Contributor**: For deploying and managing Azure resources
2. **User Access Administrator**: For managing RBAC role assignments (required by the Bicep RBAC module)

#### For Development Environment:

```bash
# Set variables
SUBSCRIPTION_ID="fec3a155-e384-43cd-abc7-9c20391a3fd4"
SP_NAME_DEV="sp-magictoolbox-cicd-dev"

# Create service principal with Contributor role at subscription level
az ad sp create-for-rbac \
  --name "$SP_NAME_DEV" \
  --role Contributor \
  --scopes "/subscriptions/$SUBSCRIPTION_ID" \
  --sdk-auth

# Save the JSON output - you'll need it for GitHub secrets

# Get the service principal App ID
SP_APP_ID=$(az ad sp list --display-name "$SP_NAME_DEV" --query "[0].appId" -o tsv)

# Grant User Access Administrator role (required for RBAC module in Bicep)
az role assignment create \
  --assignee "$SP_APP_ID" \
  --role "User Access Administrator" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"

# Verify both roles are assigned
az role assignment list --assignee "$SP_APP_ID" --query "[].{Role:roleDefinitionName, Scope:scope}" -o table
```

#### For Staging Environment (optional):

```bash
SP_NAME_STAGING="sp-magictoolbox-cicd-staging"

# Create service principal with Contributor role at subscription level
az ad sp create-for-rbac \
  --name "$SP_NAME_STAGING" \
  --role Contributor \
  --scopes "/subscriptions/$SUBSCRIPTION_ID" \
  --sdk-auth

# Get the service principal App ID
SP_APP_ID=$(az ad sp list --display-name "$SP_NAME_STAGING" --query "[0].appId" -o tsv)

# Grant User Access Administrator role
az role assignment create \
  --assignee "$SP_APP_ID" \
  --role "User Access Administrator" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"
```

#### For Production Environment:

```bash
SP_NAME_PROD="sp-magictoolbox-cicd-prod"

# Create service principal with Contributor role at subscription level
az ad sp create-for-rbac \
  --name "$SP_NAME_PROD" \
  --role Contributor \
  --scopes "/subscriptions/$SUBSCRIPTION_ID" \
  --sdk-auth

# Get the service principal App ID
SP_APP_ID=$(az ad sp list --display-name "$SP_NAME_PROD" --query "[0].appId" -o tsv)

# Grant User Access Administrator role
az role assignment create \
  --assignee "$SP_APP_ID" \
  --role "User Access Administrator" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"
```

**Important**: Each command outputs JSON like this:
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "fec3a155-e384-43cd-abc7-9c20391a3fd4",
  "tenantId": "af2dd59c-81cf-4524-8d9e-6d8254d02438"
}
```

Save each JSON output - you'll use it in the next step.

### Step 3: Get Azure Container Registry Credentials

```bash
# Get ACR name
ACR_NAME=$(az acr list --resource-group rg-westeurope-magictoolbox-dev-01 --query "[0].name" -o tsv)

# Enable admin user (required for GitHub Actions)
az acr update --name $ACR_NAME --admin-enabled true

# Get credentials
az acr credential show --name $ACR_NAME
```

This will output:
```json
{
  "passwords": [
    {
      "name": "password",
      "value": "xxxxxxxxxxxxxxxxxxxxx"
    },
    {
      "name": "password2",
      "value": "xxxxxxxxxxxxxxxxxxxxx"
    }
  ],
  "username": "acrwemagictoolboxdev01"
}
```

### Step 4: Get Container App Names

```bash
# Development
az containerapp list --resource-group rg-westeurope-magictoolbox-dev-01 --query "[0].name" -o tsv

# Staging (if exists)
az containerapp list --resource-group rg-westeurope-magictoolbox-staging-01 --query "[0].name" -o tsv

# Production (if exists)
az containerapp list --resource-group rg-westeurope-magictoolbox-prod-01 --query "[0].name" -o tsv
```

### Step 5: Configure GitHub Repository Secrets

Go to **Settings** → **Secrets and variables** → **Actions** → **Repository secrets**

Add the following **repository-level secrets** (shared across all environments):

| Secret Name | Value | Example |
|-------------|-------|---------|------
| `ACR_LOGIN_SERVER` | ACR login server | `acrwemagictoolboxdev01.azurecr.io` |
| `ACR_USERNAME` | ACR username | `acrwemagictoolboxdev01` |
| `ACR_PASSWORD` | ACR password | From Step 3, `passwords[0].value` |
| `ACR_NAME` | ACR name | `acrwemagictoolboxdev01` |

### Step 6: Configure GitHub Environment Secrets

Go to **Settings** → **Environments** → Select environment → **Environment secrets**

#### Development Environment Secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|------
| `AZURE_CREDENTIALS_DEV` | Service principal JSON from Step 2 | Full JSON output |
| `RESOURCE_GROUP_DEV` | Resource group name | `rg-westeurope-magictoolbox-dev-01` |
| `CONTAINER_APP_NAME_DEV` | Container app name | `app-westeurope-magictoolbox-dev-01` |

#### Staging Environment Secrets (if applicable):

| Secret Name | Value | Example |
|-------------|-------|---------|------
| `AZURE_CREDENTIALS_STAGING` | Service principal JSON from Step 2 | Full JSON output |
| `RESOURCE_GROUP_STAGING` | Resource group name | `rg-westeurope-magictoolbox-staging-01` |
| `CONTAINER_APP_NAME_STAGING` | Container app name | `app-westeurope-magictoolbox-sta-01` |

#### Production Environment Secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|------
| `AZURE_CREDENTIALS_PROD` | Service principal JSON from Step 2 | Full JSON output |
| `RESOURCE_GROUP_PROD` | Resource group name | `rg-westeurope-magictoolbox-prod-01` |
| `CONTAINER_APP_NAME_PROD` | Container app name | `app-westeurope-magictoolbox-prod-01` |

## Current Azure Resources (Reference)

Based on your current deployment:

```yaml
Subscription ID: fec3a155-e384-43cd-abc7-9c20391a3fd4
Tenant ID: af2dd59c-81cf-4524-8d9e-6d8254d02438

Development Environment:
  Resource Group: rg-westeurope-magictoolbox-dev-01
  Container App: app-westeurope-magictoolbox-dev-01
  Container Apps Env: env-westeurope-magictoolbox-dev-01
  ACR Name: acrwemagictoolboxdev01
  ACR Login Server: acrwemagictoolboxdev01.azurecr.io
  Key Vault: kvwemagictoolboxdev01
  PostgreSQL: psql-westeurope-magictoolbox-dev-01
  Redis: red-westeurope-magictoolbox-dev-01
  Storage: sawemagictoolboxdev01
  App Insights: ai-westeurope-magictoolbox-dev-01
  Log Analytics: law-westeurope-magictoolbox-dev-01
  Location: westeurope
```

## Secrets Summary

### Repository Secrets (4 total)
These are shared across all environments:

1. **ACR_LOGIN_SERVER**: `acrwemagictoolboxdev01.azurecr.io`
2. **ACR_USERNAME**: `acrwemagictoolboxdev01`
3. **ACR_PASSWORD**: *(from ACR credentials)*
4. **ACR_NAME**: `acrwemagictoolboxdev01`

### Environment Secrets (3 per environment)

**Development:**
1. **AZURE_CREDENTIALS_DEV**: Service principal JSON
2. **RESOURCE_GROUP_DEV**: `rg-westeurope-magictoolbox-dev-01`
3. **CONTAINER_APP_NAME_DEV**: `app-westeurope-magictoolbox-dev-01`

**Staging (optional):**
1. **AZURE_CREDENTIALS_STAGING**: Service principal JSON
2. **RESOURCE_GROUP_STAGING**: `rg-westeurope-magictoolbox-staging-01`
3. **CONTAINER_APP_NAME_STAGING**: `app-westeurope-magictoolbox-sta-01`

**Production:**
1. **AZURE_CREDENTIALS_PROD**: Service principal JSON
2. **RESOURCE_GROUP_PROD**: `rg-westeurope-magictoolbox-prod-01`
3. **CONTAINER_APP_NAME_PROD**: `app-westeurope-magictoolbox-prod-01`

## Using GitHub CLI

If you prefer using the GitHub CLI (`gh`):

### Set Repository Secret:
```bash
gh secret set ACR_LOGIN_SERVER --body "acrwemagictoolboxdev01.azurecr.io"
gh secret set ACR_USERNAME --body "acrwemagictoolboxdev01"
gh secret set ACR_PASSWORD --body "<your-password>"
gh secret set ACR_NAME --body "acrwemagictoolboxdev01"
```

### Set Environment Secret:
```bash
# Development
gh secret set AZURE_CREDENTIALS_DEV --env development --body '<service-principal-json>'
gh secret set RESOURCE_GROUP_DEV --env development --body "magictoolbox-dev-rg"
gh secret set CONTAINER_APP_NAME_DEV --env development --body "app-magictoolboxdevgrrafkow"

# Production
gh secret set AZURE_CREDENTIALS_PROD --env production --body '<service-principal-json>'
gh secret set RESOURCE_GROUP_PROD --env production --body "rg-westeurope-magictoolbox-prod-01"
gh secret set CONTAINER_APP_NAME_PROD --env production --body "app-magictoolbox-prod"
```

## Verification

After setting up all secrets:

1. **View all secrets**:
   ```bash
   gh secret list
   ```

2. **Check environments**:
   - Go to **Settings** → **Environments**
   - Verify all three environments are created
   - Verify production has required reviewers configured

3. **Test the pipeline**:
   ```bash
   # Push to develop branch (triggers dev deployment)
   git checkout develop
   git push origin develop
   
   # Push to main branch (triggers staging and prod deployment)
   git checkout main
   git push origin main
   ```

4. **Monitor workflow**:
   - Go to **Actions** tab in GitHub
   - Watch the workflow execution
   - Production deployment will require approval

## Troubleshooting

### "Service principal not found"
- Verify the service principal was created: `az ad sp list --display-name sp-magictoolbox-cicd-dev`
- Recreate if necessary using commands from Step 2

### "Access denied to ACR"
- Ensure admin user is enabled: `az acr update --name <acr-name> --admin-enabled true`
- Verify credentials are correct: `az acr credential show --name <acr-name>`

### "Container app not found"
- Verify the container app exists: `az containerapp list --resource-group <rg-name>`
- Ensure the correct resource group is specified

### "GitHub Actions failing to deploy"
- Check the workflow logs in GitHub Actions tab
- Verify all secrets are set correctly
- Ensure service principals have Contributor role on resource groups

## Security Best Practices

1. **Rotate Secrets Regularly**: Update service principal credentials every 90 days
2. **Limit Scope**: Service principals should only have access to specific resource groups
3. **Use Environment Protection**: Require approvals for production deployments
4. **Audit Access**: Review who has access to secrets in GitHub settings
5. **Enable Branch Protection**: Protect main and develop branches
6. **Secret Scanning**: Enable GitHub secret scanning in repository settings

## E2E Testing Secrets

The End-to-End testing workflow (`.github/workflows/e2e-tests.yml`) requires additional secrets for Azure Storage and Functions access.

### Required E2E Secrets (Per Environment)

Add these to each environment (`dev`, `test`, `prod`):

1. **`AZURE_STORAGE_ACCOUNT_NAME`**
   - Storage account name (e.g., `sawemagictoolboxdev01`)
   - Find with: `az storage account list --resource-group <rg-name> --query "[0].name" -o tsv`

2. **`AZURE_STORAGE_CONNECTION_STRING`**
   - Full connection string for storage account
   - Get with:
     ```bash
     az storage account show-connection-string \
       --name <storage-account-name> \
       --resource-group <rg-name> \
       --query connectionString -o tsv
     ```

3. **`AZURE_FUNCTIONS_URL`**
   - Azure Functions app URL (e.g., `https://func-westeurope-magictoolbox-dev-01.azurewebsites.net`)
   - Get with:
     ```bash
     az functionapp show \
       --resource-group <rg-name> \
       --name <function-app-name> \
       --query defaultHostName -o tsv
     ```

4. **`APP_URL`**
   - Deployed application URL (without https://)
   - Get with:
     ```bash
     az containerapp show \
       --resource-group <rg-name> \
       --name <app-name> \
       --query properties.configuration.ingress.fqdn -o tsv
     ```

5. **`DJANGO_SECRET_KEY`**
   - Django secret key for the application
   - Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

6. **`AZURE_RESOURCE_GROUP`**
   - Resource group name (e.g., `rg-westeurope-magictoolbox-dev-01`)

### Service Principal Permissions for E2E Tests

The service principal needs these additional roles for E2E testing:

```bash
SP_OBJECT_ID=$(az ad sp list --display-name "magictoolbox-github-actions-dev" --query "[0].id" -o tsv)
SUBSCRIPTION_ID="<your-subscription-id>"
RESOURCE_GROUP="rg-westeurope-magictoolbox-dev-01"
STORAGE_ACCOUNT="sawemagictoolboxdev01"

# Storage Blob Data Contributor (read/write blobs during tests)
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

# Storage Account Contributor (manage network rules during tests)
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Account Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"
```

### Quick Setup Script for E2E Secrets

```bash
#!/bin/bash
# Script to add E2E testing secrets to GitHub environment

GITHUB_REPO="fabricekrebs/magictoolbox"
ENVIRONMENT="dev"  # or test, prod
RESOURCE_GROUP="rg-westeurope-magictoolbox-dev-01"
STORAGE_ACCOUNT="sawemagictoolboxdev01"
FUNCTION_APP="func-westeurope-magictoolbox-dev-01"
CONTAINER_APP="ca-westeurope-magictoolbox-dev-01"

# Get values from Azure
STORAGE_CONNECTION=$(az storage account show-connection-string \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query connectionString -o tsv)

FUNCTIONS_URL=$(az functionapp show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP" \
  --query defaultHostName -o tsv)

APP_URL=$(az containerapp show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$CONTAINER_APP" \
  --query properties.configuration.ingress.fqdn -o tsv)

DJANGO_SECRET=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# Add to GitHub environment
gh secret set AZURE_STORAGE_ACCOUNT_NAME --body "$STORAGE_ACCOUNT" --env "$ENVIRONMENT" --repo "$GITHUB_REPO"
gh secret set AZURE_STORAGE_CONNECTION_STRING --body "$STORAGE_CONNECTION" --env "$ENVIRONMENT" --repo "$GITHUB_REPO"
gh secret set AZURE_FUNCTIONS_URL --body "https://$FUNCTIONS_URL" --env "$ENVIRONMENT" --repo "$GITHUB_REPO"
gh secret set APP_URL --body "$APP_URL" --env "$ENVIRONMENT" --repo "$GITHUB_REPO"
gh secret set DJANGO_SECRET_KEY --body "$DJANGO_SECRET" --env "$ENVIRONMENT" --repo "$GITHUB_REPO"
gh secret set AZURE_RESOURCE_GROUP --body "$RESOURCE_GROUP" --env "$ENVIRONMENT" --repo "$GITHUB_REPO"

echo "✅ E2E testing secrets added to $ENVIRONMENT environment"
```

## Additional Resources

- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Azure Service Principals](https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli)
- [GitHub Actions for Azure](https://github.com/Azure/actions)
- [E2E Testing Guide](./E2E_TESTING_GUIDE.md) - Comprehensive guide for end-to-end testing

## Support

If you encounter issues:
1. Review workflow logs: `https://github.com/<owner>/<repo>/actions`
2. Check secret configuration: Repository Settings → Secrets and variables → Actions
3. Verify Azure resources: `az resource list --resource-group <rg-name>`
4. Test Azure CLI authentication: `az account show`
5. Test GitHub CLI authentication: `gh auth status`
6. For E2E test issues: See [E2E Testing Guide](./E2E_TESTING_GUIDE.md)
