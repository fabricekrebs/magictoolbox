# MagicToolbox Azure Deployment Guide

Complete guide for deploying MagicToolbox to Azure Container Apps with CI/CD via GitHub Actions.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Initial Setup](#initial-setup)
- [Local Development](#local-development)
- [Azure Infrastructure Deployment](#azure-infrastructure-deployment)
- [CI/CD Pipeline Setup](#cicd-pipeline-setup)
- [Application Deployment](#application-deployment)
- [Post-Deployment Configuration](#post-deployment-configuration)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

1. **Azure CLI** (v2.50+)
   ```bash
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   ```

2. **Azure Bicep** (included with Azure CLI 2.20+)
   ```bash
   az bicep install
   az bicep version
   ```

3. **Docker** (v20.10+)
   ```bash
   sudo apt-get update
   sudo apt-get install docker-ce docker-ce-cli containerd.io
   ```

4. **Git**
   ```bash
   sudo apt-get install git
   ```

### Azure Subscription

- Active Azure subscription with appropriate permissions
- Resource Group creation permissions
- Container Apps, PostgreSQL, Redis, Storage, and Key Vault creation permissions

### GitHub Repository

- GitHub repository with this codebase
- GitHub Actions enabled
- Branch protection rules (recommended for `main` branch)

---

## Architecture Overview

MagicToolbox deploys the following Azure resources:

```
┌─────────────────────────────────────────────────────────────┐
│                      Azure Resource Group                    │
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │ Container Apps   │──────│ Container        │            │
│  │ Environment      │      │ Registry (ACR)   │            │
│  └──────────────────┘      └──────────────────┘            │
│           │                                                  │
│           │                                                  │
│  ┌────────┴─────────┬──────────────┬──────────────┐        │
│  │                  │              │              │        │
│  ▼                  ▼              ▼              ▼        │
│  ┌──────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐    │
│  │PostgreSQL│  │  Redis  │  │ Storage │  │Key Vault │    │
│  │Flexible  │  │  Cache  │  │ Account │  │          │    │
│  └──────────┘  └─────────┘  └─────────┘  └──────────┘    │
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │ Log Analytics    │──────│ Application      │            │
│  │ Workspace        │      │ Insights         │            │
│  └──────────────────┘      └──────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Components

- **Azure Container Apps**: Hosts the Django application with auto-scaling, SSL termination at ingress
- **Azure Container Registry**: Stores Docker images
- **PostgreSQL Flexible Server**: Primary database (production-grade)
- **Azure Cache for Redis**: Session storage and caching
- **Azure Storage Account**: Blob storage for user uploads (private access only)
- **WhiteNoise**: Efficient static file serving from container with compression
- **Azure Key Vault**: Secure secrets management
- **Log Analytics + App Insights**: Monitoring and telemetry

### Important Configuration Notes

- **SSL/TLS**: Handled by Azure Container Apps ingress, not Django
- **Static Files**: Served via WhiteNoise from container (not Azure Blob Storage)
- **Media Files**: User uploads stored in Azure Blob Storage with private access
- **Health Checks**: Custom middleware handles internal Azure health probe IPs

---

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/magictoolbox.git
cd magictoolbox
```

### 2. Azure Login

```bash
az login
az account set --subscription "Your Subscription Name"
```

### 3. Create Resource Group

```bash
# Development environment
az group create \
  --name rg-westeurope-magictoolbox-dev-01 \
  --location westeurope

# Production environment
az group create \
  --name rg-westeurope-magictoolbox-prod-01 \
  --location westeurope
```

### 4. Generate Secrets

Generate secure secrets for your deployment:

```bash
# Django Secret Key (50 characters)
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# PostgreSQL Admin Password (16+ characters with mixed case, numbers, symbols)
openssl rand -base64 32
```

Store these securely - you'll need them for deployment.

---

## Local Development

### Option 1: Virtual Environment (Recommended for Development)

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/development.txt

# Start local services with Docker Compose
docker-compose up -d

# Create .env.development file
cat > .env.development <<EOF
DJANGO_SETTINGS_MODULE=magictoolbox.settings.development
SECRET_KEY=dev-secret-key-change-me
DEBUG=True
DATABASE_URL=postgresql://magictoolbox:magictoolbox_dev_password@localhost:5432/magictoolbox
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
EOF

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Visit http://localhost:8000

### Option 2: Full Docker Environment

```bash
# Build Docker image locally
docker build -t magictoolbox:dev .

# Start all services including the app
docker-compose -f docker-compose.yml up -d

# Run migrations inside container
docker exec magictoolbox-app python manage.py migrate

# Create superuser
docker exec -it magictoolbox-app python manage.py createsuperuser
```

---

## Azure Infrastructure Deployment

### 1. Update Parameter Files

Edit `infra/parameters.dev.json` and `infra/parameters.prod.json`:

```json
{
  "parameters": {
    "appName": {
      "value": "magictoolbox"
    },
    "location": {
      "value": "westeurope"
    },
    "postgresAdminUsername": {
      "value": "mtbadmin"
    }
  }
}
```

### 2. Validate Bicep Templates

```bash
# Validate templates
az bicep build --file ./infra/main.bicep

# Preview changes (What-If)
az deployment group what-if \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --template-file ./infra/main.bicep \
  --parameters ./infra/parameters.dev.json \
  --parameters \
    postgresAdminPassword="YOUR-POSTGRES-PASSWORD" \
    djangoSecretKey="YOUR-DJANGO-SECRET-KEY"
```

### 3. Deploy Infrastructure

```bash
# Deploy to Development
az deployment group create \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --template-file ./infra/main.bicep \
  --parameters ./infra/parameters.dev.json \
  --parameters \
    postgresAdminPassword="YOUR-POSTGRES-PASSWORD" \
    djangoSecretKey="YOUR-DJANGO-SECRET-KEY" \
  --name magictoolbox-dev-deployment

# Deploy to Production
az deployment group create \
  --resource-group rg-westeurope-magictoolbox-prod-01 \
  --template-file ./infra/main.bicep \
  --parameters ./infra/parameters.prod.json \
  --parameters \
    postgresAdminPassword="YOUR-POSTGRES-PASSWORD" \
    djangoSecretKey="YOUR-DJANGO-SECRET-KEY" \
  --name magictoolbox-prod-deployment
```

Deployment takes approximately 10-15 minutes.

### 4. Get Deployment Outputs

```bash
# Get important outputs
az deployment group show \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --name magictoolbox-dev-deployment \
  --query properties.outputs

# Store outputs
ACR_NAME=$(az deployment group show \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --name magictoolbox-dev-deployment \
  --query properties.outputs.acrLoginServer.value -o tsv)

APP_URL=$(az deployment group show \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --name magictoolbox-dev-deployment \
  --query properties.outputs.containerAppUrl.value -o tsv)

echo "ACR Login Server: $ACR_NAME"
echo "Application URL: $APP_URL"
```

---

## CI/CD Pipeline Setup

### 1. Create Azure Service Principal

Create a service principal for GitHub Actions:

```bash
az ad sp create-for-rbac \
  --name magictoolbox-github-actions \
  --role Contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/rg-westeurope-magictoolbox-dev-01 \
  --sdk-auth
```

Save the JSON output - you'll need it for GitHub secrets.

### 2. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secrets:

#### Azure Authentication
- `AZURE_CLIENT_ID`: From service principal JSON
- `AZURE_CLIENT_SECRET`: From service principal JSON (or use OIDC)
- `AZURE_TENANT_ID`: From service principal JSON
- `AZURE_SUBSCRIPTION_ID`: Your Azure subscription ID

#### Resource Names
- `AZURE_RESOURCE_GROUP`: `rg-westeurope-magictoolbox-dev-01` (or `rg-westeurope-magictoolbox-prod-01`)
- `ACR_NAME`: Your ACR name (without .azurecr.io)

#### Application Secrets
- `POSTGRES_ADMIN_PASSWORD`: PostgreSQL admin password
- `DJANGO_SECRET_KEY`: Django secret key

### 3. Configure GitHub Environments

Create two environments in GitHub:
- **dev**: For development deployments
- **prod**: For production deployments (add protection rules)

Settings → Environments → New environment

For production:
- ✅ Required reviewers (add yourself)
- ✅ Wait timer (optional: 5 minutes)
- ✅ Deployment branches: Only `main` branch

### 4. Test CI/CD Pipeline

```bash
# Push to trigger build
git add .
git commit -m "feat: setup Azure deployment"
git push origin develop

# This triggers: build-and-test.yml workflow
```

Check GitHub Actions tab for workflow status.

---

## Application Deployment

### Option 1: Automatic Deployment (Recommended)

Push to `main` branch triggers automatic deployment:

```bash
git checkout main
git merge develop
git push origin main

# This triggers:
# 1. build-and-push.yml - Builds Docker image
# 2. deploy-app.yml - Deploys to Container Apps
```

### Option 2: Manual Deployment via GitHub Actions

1. Go to GitHub repository → Actions
2. Select "Deploy to Container Apps" workflow
3. Click "Run workflow"
4. Select environment (dev/prod) and image tag
5. Click "Run workflow"

### Option 3: Manual Deployment via Azure CLI

```bash
# Build and push Docker image manually
ACR_NAME="your-acr-name"

az acr login --name $ACR_NAME

docker build -t ${ACR_NAME}.azurecr.io/magictoolbox:latest .
docker push ${ACR_NAME}.azurecr.io/magictoolbox:latest

# Update Container App
APP_NAME="your-container-app-name"

az containerapp update \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --image ${ACR_NAME}.azurecr.io/magictoolbox:latest

# Run migrations
az containerapp exec \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --command "python manage.py migrate --noinput"
```

---

## Post-Deployment Configuration

### 1. Verify Deployment

```bash
# Check Container App status
az containerapp show \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query properties.runningStatus

# Check revision health
az containerapp revision list \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "[].{Name:name, Active:properties.active, Health:properties.healthState, Traffic:properties.trafficWeight}" \
  --output table

# Test health endpoint
curl https://your-app-url.azurecontainerapps.io/health/

# Verify static files load correctly
curl -I https://your-app-url.azurecontainerapps.io/static/css/custom.css
# Should return HTTP 200 with server: gunicorn

curl -I https://your-app-url.azurecontainerapps.io/static/js/main.js
# Should return HTTP 200 with server: gunicorn

# Test homepage loads with all assets
curl -s https://your-app-url.azurecontainerapps.io/ | grep -i stylesheet

# View application logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --follow
```

### 2. Create Django Superuser

```bash
# Access container shell
az containerapp exec \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --command "/bin/bash"

# Inside container:
python manage.py createsuperuser
exit
```

### 3. Configure Custom Domain (Optional)

```bash
# Add custom domain
az containerapp hostname add \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --hostname yourdomain.com

# Bind SSL certificate
az containerapp ssl upload \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --hostname yourdomain.com \
  --certificate-file /path/to/certificate.pfx \
  --certificate-password "cert-password"
```

### 4. Update ALLOWED_HOSTS

Update environment variable in Container App:

```bash
az containerapp update \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --set-env-vars "ALLOWED_HOSTS=.azurecontainerapps.io,yourdomain.com"
```

---

## Monitoring and Maintenance

### Application Insights

Access telemetry in Azure Portal:
1. Navigate to your Application Insights resource
2. View:
   - Live Metrics
   - Failures
   - Performance
   - Logs (KQL queries)

### Log Analytics Queries

Example KQL queries:

```kusto
// Application errors
ContainerAppConsoleLogs_CL
| where Log_s contains "ERROR"
| project TimeGenerated, Log_s
| order by TimeGenerated desc
| take 100

// Request performance
AppRequests
| where TimeGenerated > ago(1h)
| summarize avg(DurationMs), percentile(DurationMs, 95) by bin(TimeGenerated, 5m)
| render timechart

// Failed requests
AppRequests
| where Success == false
| project TimeGenerated, Name, ResultCode, DurationMs
| order by TimeGenerated desc
```

### Container App Metrics

```bash
# View revision history
az containerapp revision list \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --output table

# View replica count
az containerapp show \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query properties.template.scale
```

### Database Maintenance

```bash
# PostgreSQL connection
PGHOST=$(az postgres flexible-server show \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --name your-postgres-server \
  --query fullyQualifiedDomainName -o tsv)

psql "host=$PGHOST port=5432 dbname=magictoolbox user=mtbadmin sslmode=require"

# Inside PostgreSQL:
-- Check database size
SELECT pg_size_pretty(pg_database_size('magictoolbox'));

-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Table sizes
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

---

## Troubleshooting

### Container App Won't Start

```bash
# Check logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --tail 100

# Check system logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --type system

# Restart container app
az containerapp update \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01
```

### Revision Shows "Unhealthy" Status

**Symptom**: Container App revision health state is "Unhealthy", health probes failing with 400 errors.

**Diagnosis**:
```bash
# Check revision health
az containerapp revision list \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "[].{Name:name, Health:properties.healthState, Traffic:properties.trafficWeight}" \
  --output table

# Check logs for health probe errors
az containerapp logs show \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --tail 100 | grep -i "health\|invalid"
```

**Solution**: Already implemented in the codebase:
- `apps/core/middleware.py` contains `HealthCheckMiddleware`
- Detects health probe requests from Azure internal IPs (100.100.0.0/16)
- Bypasses ALLOWED_HOSTS validation for `/health/`, `/readiness/`, `/liveness/` endpoints
- Ensures health checks succeed from internal Azure network

### Redirect Loop / Too Many Redirects

**Symptom**: Browser error "This page isn't working... redirected you too many times"

**Diagnosis**:
```bash
# Check if getting 301 redirects
curl -I https://your-app-url.azurecontainerapps.io/
```

**Solution**: Already configured in `magictoolbox/settings/production.py`:
```python
# Azure Container Apps handles SSL termination at ingress
SECURE_SSL_REDIRECT = False  # Don't redirect in Django
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Trust Azure proxy
```

If you encounter this issue:
1. Verify `SECURE_SSL_REDIRECT = False` in production settings
2. Check that `SECURE_PROXY_SSL_HEADER` is set correctly
3. Redeploy the application if settings were changed

### Static Files Not Loading (HTTP 409)

**Symptom**: Browser console shows errors loading CSS/JS files with "Public access is not permitted"

**Diagnosis**:
```bash
# Test static file loading
curl -I https://your-app-url.azurecontainerapps.io/static/css/custom.css

# Should return HTTP 200, not 409
```

**Solution**: Already implemented using WhiteNoise:
1. `requirements/production.txt` includes `whitenoise[brotli]>=6.6`
2. `magictoolbox/settings/base.py` has WhiteNoise middleware configured
3. `magictoolbox/settings/production.py` uses WhiteNoise for static files:
   ```python
   STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
   STATIC_URL = '/static/'
   ```
4. Static files collected during container startup via `scripts/startup.sh`

Benefits:
- Static files served efficiently from container
- Brotli compression for smaller file sizes
- Cache-busting hashes prevent stale content
- Azure Blob Storage kept private for user uploads only

### Database Connection Issues

```bash
# Test PostgreSQL connectivity from container
az containerapp exec \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --command "nc -zv postgres-host 5432"

# Check firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --name your-postgres-server
```

### Redis Connection Issues

```bash
# Test Redis connectivity
az containerapp exec \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --command "nc -zv redis-host 6380"

# Check Redis metrics
az redis show \
  --name your-redis-cache \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query provisioningState
```

### Image Pull Errors

```bash
# Verify ACR access
az acr login --name $ACR_NAME

# Check Container App managed identity
az containerapp identity show \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01

# Grant AcrPull role (if needed)
ACR_ID=$(az acr show --name $ACR_NAME --query id -o tsv)
IDENTITY_ID=$(az containerapp identity show \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query principalId -o tsv)

az role assignment create \
  --assignee $IDENTITY_ID \
  --role AcrPull \
  --scope $ACR_ID
```

### Application Performance Issues

```bash
# Scale up replicas
az containerapp update \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --min-replicas 2 \
  --max-replicas 10

# Increase resources
az containerapp update \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --cpu 1.0 \
  --memory 2Gi
```

### Rollback Deployment

```bash
# List revisions
az containerapp revision list \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --output table

# Activate previous revision
az containerapp revision activate \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --revision <revision-name>
```

---

## Cost Optimization

### Development Environment

- Use Burstable tier for PostgreSQL (`Standard_B1ms`)
- Use Basic tier for Redis (`C0`)
- Scale Container Apps to 0-1 replicas during off-hours
- Consider stopping resources when not in use:

```bash
# Stop Container App (scale to 0)
az containerapp update \
  --name $APP_NAME \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --min-replicas 0 \
  --max-replicas 0

# Stop PostgreSQL
az postgres flexible-server stop \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --name your-postgres-server
```

### Production Environment

- Use appropriate tiers based on load
- Enable auto-scaling for Container Apps
- Monitor Application Insights for optimization opportunities
- Use Azure Cost Management for tracking

---

## Security Best Practices

1. **Secrets Management**: Never commit secrets to Git
2. **Network Security**: Consider VNet integration for production
3. **Database Security**: Use Azure AD authentication when possible
4. **Key Vault**: Rotate secrets regularly
5. **Container Scanning**: Enable Defender for Containers
6. **HTTPS Only**: Enforce SSL/TLS for all connections
7. **RBAC**: Use least privilege access for service principals

---

## Additional Resources

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [Azure Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [GitHub Actions for Azure](https://github.com/Azure/actions)

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review Azure Container Apps logs
3. Check Application Insights telemetry
4. Open an issue in the GitHub repository

---

**Last Updated**: 2024
**Version**: 1.0.0
