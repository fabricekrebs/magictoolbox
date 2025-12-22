# Production Environment Deployment to New Azure Subscription

**Created**: December 17, 2025  
**Purpose**: Guide for deploying MagicToolbox production environment to a different Azure subscription

## 📋 Overview

This guide walks you through deploying the production environment to a new Azure subscription while maintaining the existing development environment in the current subscription.

## 🎯 Prerequisites

### 1. Azure Subscription Access
- [ ] **New Azure Subscription ID** ready
- [ ] **Subscription Owner** or **Contributor + User Access Administrator** roles
- [ ] Sufficient quota for required resources (check [Azure Quotas](#azure-resource-quotas))

### 2. Local Tools Installed
```bash
# Azure CLI (version 2.50+)
az --version

# GitHub CLI (for secrets management)
gh --version

# OpenSSL (for generating secrets)
openssl version
```

### 3. Repository Access
- [ ] Admin access to GitHub repository
- [ ] Ability to create/modify GitHub secrets
- [ ] Ability to create GitHub environments

---

## 🚀 Step-by-Step Deployment Process

### Step 1: Azure Subscription Setup

#### 1.1 Login and Set Subscription
```bash
# Login to Azure
az login

# List available subscriptions
az account list --output table

# Set the NEW production subscription
PROD_SUBSCRIPTION_ID="<your-new-production-subscription-id>"
az account set --subscription $PROD_SUBSCRIPTION_ID

# Verify correct subscription is selected
az account show --query "{Name:name, ID:id, TenantID:tenantId}" --output table
```

#### 1.2 Create Resource Group
```bash
# Production resource group
PROD_RG="rg-magictoolbox-prod"
LOCATION="westeurope"  # or your preferred region

az group create \
  --name $PROD_RG \
  --location $LOCATION \
  --tags Environment=Production Application=MagicToolbox ManagedBy=Bicep
```

---

### Step 2: Generate Secure Secrets

```bash
# Generate Django secret key
DJANGO_SECRET_PROD=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
echo "Django Secret (save this): $DJANGO_SECRET_PROD"

# Generate PostgreSQL password (32 characters, alphanumeric + special chars)
POSTGRES_PASSWORD_PROD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "PostgreSQL Password (save this): $POSTGRES_PASSWORD_PROD"

# IMPORTANT: Save these values securely - you'll need them for GitHub secrets
```

---

### Step 3: Create Service Principal for GitHub Actions

The service principal needs **two roles** for successful deployments:
1. **Contributor**: Deploy and manage Azure resources
2. **User Access Administrator**: Manage RBAC role assignments (required by Bicep RBAC module)

```bash
# Set variables
SP_NAME_PROD="sp-magictoolbox-cicd-prod"

# Create service principal with Contributor role at subscription level
SP_JSON=$(az ad sp create-for-rbac \
  --name "$SP_NAME_PROD" \
  --role Contributor \
  --scopes "/subscriptions/$PROD_SUBSCRIPTION_ID" \
  --sdk-auth)

# IMPORTANT: Save this entire JSON output - needed for GitHub secret AZURE_CREDENTIALS_PROD
echo "$SP_JSON"

# Get the service principal App ID
SP_APP_ID=$(az ad sp list --display-name "$SP_NAME_PROD" --query "[0].appId" -o tsv)

# Grant User Access Administrator role (required for RBAC module in Bicep)
az role assignment create \
  --assignee "$SP_APP_ID" \
  --role "User Access Administrator" \
  --scope "/subscriptions/$PROD_SUBSCRIPTION_ID"

# Verify both roles are assigned
az role assignment list \
  --assignee "$SP_APP_ID" \
  --query "[].{Role:roleDefinitionName, Scope:scope}" \
  --output table
```

**Expected Output**:
```
Role                          Scope
----------------------------  --------------------------------------------------------
Contributor                   /subscriptions/<subscription-id>
User Access Administrator     /subscriptions/<subscription-id>
```

---

### Step 4: Configure GitHub Secrets and Environment

#### 4.1 Create Production Environment on GitHub

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Environments**
3. Click **New environment**
4. Name it: `Production`
5. Configure protection rules:
   - ✅ Enable **Required reviewers** (select team members)
   - ✅ Set **Wait timer** to 5 minutes (optional safety buffer)
   - ✅ Enable **Deployment branches** → Select `main` branch only

#### 4.2 Add GitHub Repository Secrets

Using GitHub CLI (easier):
```bash
# Navigate to repository root
cd /home/azureuser/magictoolbox

# Authenticate with GitHub
gh auth login

# Set production secrets
gh secret set AZURE_CREDENTIALS_PROD --body "$SP_JSON"
gh secret set RESOURCE_GROUP_PROD --body "$PROD_RG"
gh secret set POSTGRES_ADMIN_PASSWORD_PROD --body "$POSTGRES_PASSWORD_PROD"
gh secret set DJANGO_SECRET_KEY_PROD --body "$DJANGO_SECRET_PROD"
```

Or manually via GitHub UI:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add each secret:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AZURE_CREDENTIALS_PROD` | Full JSON output from service principal creation | Azure authentication for production |
| `RESOURCE_GROUP_PROD` | `rg-italynorth-magictoolbox-prod-01` | Production resource group name |
| `POSTGRES_ADMIN_PASSWORD_PROD` | Generated PostgreSQL password | PostgreSQL admin password |
| `DJANGO_SECRET_KEY_PROD` | Generated Django secret | Django SECRET_KEY |

#### 4.3 Verify ACR Secrets (from Dev)

The Container Registry secrets should already exist from dev setup. Verify:
```bash
gh secret list | grep ACR
```

Should show:
- `ACR_LOGIN_SERVER`
- `ACR_USERNAME`
- `ACR_PASSWORD`

If missing, check [GITHUB_SECRETS_SETUP.md](./GITHUB_SECRETS_SETUP.md#step-5-enable-acr-admin-access).

---

### Step 5: Update Infrastructure Parameters

#### 5.1 Review Production Parameters File

Check the production parameters file:

```bash
cat infra/parameters.prod.json
```

Expected content:
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environment": {
      "value": "prod"
    },
    "location": {
      "value": "westeurope"
    },
    "appName": {
      "value": "magictoolbox"
    },
    "postgresAdminUsername": {
      "value": "mtbadmin"
    }
  }
}
```

#### 5.2 Modify if Needed

If you want to use a different region or naming convention for production:

```bash
# Edit the file
code infra/parameters.prod.json

# Example: Change location to North Europe
# "location": { "value": "northeurope" }

# Commit changes
git add infra/parameters.prod.json
git commit -m "chore: update production parameters for new subscription"
git push origin develop
```

---

### Step 6: Deploy Infrastructure to Production

#### 6.1 Option A: Deploy via GitHub Actions (Recommended)

1. Go to **Actions** → **Deploy Infrastructure** workflow
2. Click **Run workflow**
3. Select:
   - Branch: `main` (or `develop` if testing first)
   - Environment: `prod`
   - Destroy: `false`
4. Click **Run workflow**
5. Monitor the deployment (takes ~15-20 minutes)

#### 6.2 Option B: Deploy Manually via Azure CLI

```bash
cd /home/azureuser/magictoolbox/infra

# Ensure you're on the correct subscription
az account set --subscription $PROD_SUBSCRIPTION_ID

# Validate Bicep template
az bicep build --file main.bicep

# What-If deployment (preview changes)
az deployment group what-if \
  --resource-group $PROD_RG \
  --template-file main.bicep \
  --parameters parameters.prod.json \
  --parameters \
    postgresAdminPassword="$POSTGRES_PASSWORD_PROD" \
    djangoSecretKey="$DJANGO_SECRET_PROD"

# REVIEW THE OUTPUT CAREFULLY!

# Deploy infrastructure
az deployment group create \
  --resource-group $PROD_RG \
  --template-file main.bicep \
  --parameters parameters.prod.json \
  --parameters \
    postgresAdminPassword="$POSTGRES_PASSWORD_PROD" \
    djangoSecretKey="$DJANGO_SECRET_PROD" \
    useKeyVaultReferences=false

# Wait for deployment to complete (~15-20 minutes)
# Monitor progress: Go to Azure Portal → Resource Groups → rg-italynorth-magictoolbox-prod-01 → Deployments
```

#### 6.3 Verify Infrastructure Deployment

```bash
# List all deployed resources
az resource list \
  --resource-group $PROD_RG \
  --output table

# Check Container Apps Environment
az containerapp env list \
  --resource-group $PROD_RG \
  --output table

# Check Storage Account containers
STORAGE_ACCOUNT=$(az storage account list --resource-group $PROD_RG --query "[0].name" -o tsv)
az storage container list \
  --account-name $STORAGE_ACCOUNT \
  --auth-mode login \
  --output table
```

**Expected Resources**:
- ✅ Virtual Network with 3 subnets
- ✅ Log Analytics Workspace + Application Insights
- ✅ Azure Container Registry (or reuse from dev)
- ✅ Azure Key Vault (with private endpoint)
- ✅ Azure Cache for Redis (with private endpoint)
- ✅ PostgreSQL Flexible Server (with private endpoint)
- ✅ Storage Account with FR-011 standardized containers:
  - `static` - Static web assets
  - `deployments` - Function App deployment packages
  - `uploads` - Input files (organized by category: uploads/pdf/, uploads/image/, uploads/video/, uploads/gpx/, uploads/ocr/)
  - `processed` - Output files (organized by category: processed/pdf/, processed/image/, etc.)
  - `temp` - Temporary files (auto-cleanup after 24h via lifecycle policy)
- ✅ Container Apps Environment
- ✅ Azure Function App (Flex Consumption)

---

### Step 7: Deploy Application Code

#### 7.1 Trigger Deployment via GitHub Actions

**Method 1: Merge to main branch**
```bash
# Ensure all changes are committed on develop
git checkout develop
git pull origin develop

# Create and merge PR to main
git checkout main
git pull origin main
git merge develop
git push origin main

# This will trigger the "Deploy to Azure Container Apps" workflow
```

**Method 2: Manual workflow dispatch**
1. Go to **Actions** → **Deploy to Azure Container Apps**
2. Click **Run workflow**
3. Select:
   - Branch: `main`
   - Environment: `prod`
4. Click **Run workflow**

#### 7.2 Monitor Deployment

```bash
# Watch GitHub Actions progress in browser
# Or use CLI:
gh run list --workflow="Deploy to Azure Container Apps" --limit 1

# View logs
gh run view --log
```

#### 7.3 Verify Application Deployment

```bash
# Get Container App URL
CONTAINER_APP_URL=$(az containerapp show \
  --name app-magictoolbox-prod \
  --resource-group $PROD_RG \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

echo "Production URL: https://$CONTAINER_APP_URL"

# Test health endpoint
curl -s "https://$CONTAINER_APP_URL/api/v1/health/" | python -m json.tool

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "cache": "connected",
#   "storage": "connected"
# }
```

---

### Step 8: Deploy Azure Functions

#### 8.1 Manual Deployment (First Time)

```bash
cd /home/azureuser/magictoolbox/function_app

# Get Function App name
FUNCTION_APP_NAME=$(az functionapp list \
  --resource-group $PROD_RG \
  --query "[0].name" \
  --output tsv)

# Deploy function code
func azure functionapp publish $FUNCTION_APP_NAME --python

# Wait for deployment to complete (~2-3 minutes)
```

#### 8.2 Verify Function Deployment

```bash
# Test health endpoint
FUNCTION_URL=$(az functionapp show \
  --name $FUNCTION_APP_NAME \
  --resource-group $PROD_RG \
  --query defaultHostName \
  --output tsv)

curl -s "https://$FUNCTION_URL/api/health?detailed=true" | python -m json.tool
```

---

### Step 9: Configure DNS and Custom Domain (Optional)

If you want a custom domain for production:

```bash
# Add custom domain to Container App
az containerapp hostname add \
  --name app-magictoolbox-prod \
  --resource-group $PROD_RG \
  --hostname magictoolbox.yourdomain.com

# Get verification ID
az containerapp hostname list \
  --name app-magictoolbox-prod \
  --resource-group $PROD_RG

# Add TXT record to your DNS provider
# Follow Azure Portal instructions for domain verification

# Bind SSL certificate (automatic with managed certificate)
az containerapp hostname bind \
  --name app-magictoolbox-prod \
  --resource-group $PROD_RG \
  --hostname magictoolbox.yourdomain.com \
  --environment $(az containerapp env list -g $PROD_RG --query "[0].name" -o tsv)
```

---

### Step 10: Database Migration and Initial Setup

#### 10.1 Run Django Migrations

Migrations should run automatically via the startup script, but you can verify:

```bash
# Connect to Container App and check logs
az containerapp logs show \
  --name app-magictoolbox-prod \
  --resource-group $PROD_RG \
  --follow

# Look for migration log entries:
# "Running migrations..."
# "✅ Migrations completed successfully"
```

#### 10.2 Create Superuser (Admin Account)

```bash
# Execute command in running container
az containerapp exec \
  --name app-magictoolbox-prod \
  --resource-group $PROD_RG \
  --command "/bin/bash"

# Inside container:
python manage.py createsuperuser
# Follow prompts to create admin user

# Exit container
exit
```

---

### Step 11: Configure Monitoring and Alerts

#### 11.1 Verify Application Insights

```bash
# Get Application Insights instrumentation key
APP_INSIGHTS_KEY=$(az monitor app-insights component show \
  --resource-group $PROD_RG \
  --query "[0].instrumentationKey" \
  --output tsv)

echo "Application Insights Key: $APP_INSIGHTS_KEY"

# View live metrics
# Go to Azure Portal → Application Insights → Live Metrics
```

#### 11.2 Set Up Alerts (Recommended)

```bash
# Create alert for high error rate
az monitor metrics alert create \
  --name "High Error Rate" \
  --resource-group $PROD_RG \
  --scopes "/subscriptions/$PROD_SUBSCRIPTION_ID/resourceGroups/$PROD_RG/providers/Microsoft.App/containerApps/app-magictoolbox-prod" \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m

# Create alert for database connection failures
# (Add more alerts as needed)
```

---

## 🔍 Verification Checklist

After deployment, verify the following:

### Infrastructure
- [ ] All Azure resources deployed successfully
- [ ] Virtual Network with correct subnets
- [ ] Private endpoints configured for all services
- [ ] Key Vault accessible and populated with secrets
- [ ] Storage containers created with correct naming

### Application
- [ ] Container App running and accessible
- [ ] Health endpoint returns 200 OK
- [ ] Database migrations completed
- [ ] Static files served correctly
- [ ] Admin panel accessible (`/admin/`)

### Azure Functions
- [ ] Function App deployed and running
- [ ] Health endpoint returns healthy status
- [ ] PDF conversion test successful
- [ ] Video rotation test successful

### Security
- [ ] No public access to PostgreSQL
- [ ] No public access to Redis
- [ ] No public access to Storage Account
- [ ] All secrets in Key Vault
- [ ] Managed Identity configured for all services
- [ ] HTTPS enforced

### Monitoring
- [ ] Application Insights receiving telemetry
- [ ] Log Analytics workspace configured
- [ ] Alerts configured for critical metrics

---

## 🔧 Troubleshooting

### Issue: Deployment Fails with "Insufficient Permissions"

**Solution**:
```bash
# Verify service principal has both required roles
az role assignment list --assignee $SP_APP_ID --output table

# Should show both:
# - Contributor
# - User Access Administrator

# If missing, add the role:
az role assignment create \
  --assignee "$SP_APP_ID" \
  --role "User Access Administrator" \
  --scope "/subscriptions/$PROD_SUBSCRIPTION_ID"
```

### Issue: Container App Won't Start

**Check logs**:
```bash
az containerapp logs show \
  --name app-magictoolbox-prod \
  --resource-group $PROD_RG \
  --follow
```

**Common causes**:
- Database connection failure (check Key Vault secrets)
- Migration errors (check PostgreSQL connectivity)
- Missing environment variables (check Container App configuration)

### Issue: Azure Function Not Responding

**Solution**:
```bash
# Restart Function App
az functionapp restart \
  --name $FUNCTION_APP_NAME \
  --resource-group $PROD_RG

# Check Application Insights for errors
# Go to Azure Portal → Function App → Logs
```

### Issue: DNS/Custom Domain Not Working

**Solution**:
1. Verify DNS records are propagated: `nslookup magictoolbox.yourdomain.com`
2. Check domain verification status in Azure Portal
3. Ensure SSL certificate is bound
4. Check Container App ingress configuration

---

## 📊 Azure Resource Quotas

Before deploying, ensure your subscription has sufficient quota for:

| Resource Type | Required | Check Command |
|--------------|----------|---------------|
| vCPUs (Container Apps) | 4-8 vCPUs | `az vm list-usage --location westeurope` |
| Public IP Addresses | 2-3 | `az network list-usages --location westeurope` |
| PostgreSQL Flexible Server | 1 instance | Check Azure Portal quota |
| Redis Cache | 1 instance | Check Azure Portal quota |
| Storage Account | 1 account | `az storage account list --query "length(@)"` |

---

## 🔄 Rollback Plan

If production deployment fails and needs rollback:

```bash
# 1. Scale down Container App to 0 replicas
az containerapp update \
  --name app-magictoolbox-prod \
  --resource-group $PROD_RG \
  --min-replicas 0 \
  --max-replicas 0

# 2. Delete specific deployment (if needed)
az deployment group delete \
  --resource-group $PROD_RG \
  --name <deployment-name>

# 3. Restore database from backup (if applicable)
# Contact Azure support or use automated backups

# 4. Redeploy previous working version
git checkout <previous-commit-sha>
# Trigger deployment workflow again
```

---

## 📚 Related Documentation

- [Azure Deployment README](./AZURE_DEPLOYMENT_README.md)
- [GitHub Secrets Setup](./GITHUB_SECRETS_SETUP.md)
- [Deployment Instructions](../DEPLOYMENT_INSTRUCTIONS.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
- [Private Endpoints Migration](./PRIVATE_ENDPOINTS_MIGRATION.md)

---

## 📝 Notes

- **Development** environment remains in the original subscription
- **Production** environment is deployed to the new subscription
- Both environments are independent and isolated
- Use separate service principals for each environment
- Always test changes in dev before deploying to prod
- Keep both subscriptions' credentials secure and separate

---

## ✅ Post-Deployment Tasks

After successful production deployment:

1. **Update Documentation**
   - [ ] Update README with production URL
   - [ ] Document any production-specific configurations
   - [ ] Add production contact information

2. **Configure Backup Strategy**
   - [ ] Enable automated PostgreSQL backups (default: enabled)
   - [ ] Configure blob storage lifecycle policies
   - [ ] Set up disaster recovery plan

3. **Performance Optimization**
   - [ ] Review and adjust Container App scaling rules
   - [ ] Configure CDN for static assets (optional)
   - [ ] Set up Redis cache policies

4. **Security Hardening**
   - [ ] Review all RBAC assignments
   - [ ] Enable Azure Defender for all services
   - [ ] Configure network security groups
   - [ ] Set up Azure Firewall (if needed)

5. **Monitoring & Maintenance**
   - [ ] Set up status page (e.g., Azure Status Page)
   - [ ] Configure automated alerts for on-call team
   - [ ] Schedule regular security reviews
   - [ ] Plan for monthly dependency updates

---

**Last Updated**: December 17, 2025  
**Maintainer**: MagicToolbox Team  
**Version**: 1.0
