# Azure Container Apps Deployment - Setup Complete! 🎉

**Last Updated:** December 2, 2025  
**Status:** ✅ Fully operational with VNet integration, private endpoints, and Azure Functions

This document provides a quick overview of the Azure deployment files created for MagicToolbox.

## 📁 Files Created

### Docker Configuration
- ✅ **Dockerfile** - Multi-stage build with Python 3.11, optimized for production
- ✅ **.dockerignore** - Excludes unnecessary files from Docker context
- ✅ **scripts/startup.sh** - Database checks, migrations, and Gunicorn startup
- ✅ **docker-compose.yml** - Local development with PostgreSQL, Redis, and MinIO

### Infrastructure as Code (Bicep)
- ✅ **infra/main.bicep** - Main orchestration template
- ✅ **infra/modules/monitoring.bicep** - Log Analytics + Application Insights
- ✅ **infra/modules/acr.bicep** - Azure Container Registry
- ✅ **infra/modules/keyvault.bicep** - Azure Key Vault for secrets (private endpoint only)
- ✅ **infra/modules/storage.bicep** - Azure Blob Storage (uploads, processed, static)
- ✅ **infra/modules/redis.bicep** - Azure Cache for Redis
- ✅ **infra/modules/postgresql.bicep** - PostgreSQL Flexible Server (database: `magictoolbox`)
- ✅ **infra/modules/network.bicep** - Virtual Network with subnets for Container Apps, Private Endpoints, and Function Apps
- ✅ **infra/modules/container-apps.bicep** - Container Apps Environment + App with VNet integration
- ✅ **infra/modules/function-app.bicep** - Azure Function App (FlexConsumption) for PDF to DOCX conversion
- ✅ **infra/modules/private-endpoints.bicep** - Private endpoints for ACR, PostgreSQL, Redis, Storage, and Key Vault
- ✅ **infra/modules/rbac.bicep** - Role assignments for managed identities (Storage, ACR, Key Vault access)
- ✅ **infra/parameters.dev.json** - Development environment parameters
- ✅ **infra/parameters.prod.json** - Production environment parameters

### CI/CD (GitHub Actions)
- ✅ **.github/workflows/build-and-test.yml** - Lint, test, security scan
- ✅ **.github/workflows/deploy-infrastructure.yml** - Deploy Bicep templates
- ✅ **.github/workflows/build-and-push.yml** - Build Docker image, push to ACR
- ✅ **.github/workflows/deploy-app.yml** - Deploy to Container Apps

### Configuration
- ✅ **.env.production.template** - Production environment variables template
- ✅ **magictoolbox/settings/production.py** - Updated for Azure services

### Documentation
- ✅ **DEPLOYMENT.md** - Complete deployment guide with troubleshooting

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login
```

### 2. Create Resource Groups
```bash
az group create --name magictoolbox-dev-rg --location westeurope
az group create --name magictoolbox-prod-rg --location westeurope
```

### 3. Deploy Infrastructure
```bash
# Generate secrets first
DJANGO_SECRET=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Deploy to Dev
az deployment group create \
  --resource-group magictoolbox-dev-rg \
  --template-file ./infra/main.bicep \
  --parameters ./infra/parameters.dev.json \
  --parameters \
    postgresAdminPassword="$POSTGRES_PASSWORD" \
    djangoSecretKey="$DJANGO_SECRET"
```

### 4. Setup GitHub Actions
Configure GitHub secrets (Settings → Secrets → Actions):
- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`, `ACR_NAME`
- `POSTGRES_ADMIN_PASSWORD`, `DJANGO_SECRET_KEY`

### 5. Deploy Application
```bash
# Push to main branch triggers automatic deployment
git push origin main

# Or manually via GitHub Actions:
# Actions → Deploy to Container Apps → Run workflow
```

## 📊 Architecture

```
Azure Resource Group
├── Virtual Network (10.0.0.0/16)
│   ├── snet-container-apps (10.0.0.0/23) - For Container Apps
│   ├── snet-private-endpoints (10.0.2.0/24) - For Private Endpoints
│   └── snet-function-apps (10.0.3.0/24) - For Function App VNet integration
├── Container Apps Environment (VNet integrated)
│   └── Django App (auto-scaling with managed identity)
├── Azure Function App (FlexConsumption, VNet integrated)
│   └── PDF to DOCX Converter (HTTP trigger)
├── Azure Container Registry (private endpoint)
├── PostgreSQL Flexible Server (private endpoint, database: magictoolbox)
├── Azure Cache for Redis (private endpoint)
├── Storage Account (private endpoint, keyless access)
│   ├── uploads container (PDF inputs)
│   ├── processed container (DOCX outputs)
│   ├── deploymentpackage container (Function App deployments)
│   └── static container (Django static files)
├── Key Vault (private endpoint only, RBAC for secrets)
├── Log Analytics Workspace
└── Application Insights

Network Flow:
- Container App → Private Endpoints → ACR, PostgreSQL, Redis, Storage, Key Vault
- Function App → VNet → Private Endpoints → PostgreSQL, Storage, Key Vault
- External → HTTPS → Container App Ingress
- External → HTTPS (with function key) → Function App HTTP trigger
```

## 🔧 Local Development

```bash
# Start local services
docker-compose up -d

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements/development.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

## 📝 Environment Variables

Key environment variables (see `.env.production.template` for full list):

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection | `rediss://:pass@host:6380/0` |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account | `magictoolboxdevst123` |
| `ALLOWED_HOSTS` | Allowed hostnames | `.azurecontainerapps.io` |

## 🔍 Monitoring

Access telemetry in Azure Portal:
- **Application Insights**: Request metrics, failures, performance
- **Log Analytics**: Custom KQL queries, container logs
- **Container Apps**: Revision history, replica count, metrics

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### Issue 1: Unhealthy Container App Revisions
**Symptom**: Health probes return 400 "Invalid HTTP_HOST header"

**Cause**: Azure Container Apps health probes use internal IP addresses (100.100.0.0/16) that don't match ALLOWED_HOSTS.

**Solution**: Already implemented via `HealthCheckMiddleware` in `apps/core/middleware.py`:
- Detects internal Azure IPs from health check requests
- Bypasses ALLOWED_HOSTS validation for health endpoints
- Ensures health probes succeed from internal network

#### Issue 2: Redirect Loop (Too Many Redirects)
**Symptom**: Browser shows "redirected you too many times" error

**Cause**: Django's `SECURE_SSL_REDIRECT=True` conflicts with Azure Container Apps SSL termination at ingress.

**Solution**: Already configured in `magictoolbox/settings/production.py`:
```python
SECURE_SSL_REDIRECT = False  # Azure handles SSL at ingress
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

#### Issue 3: Static Files Not Loading (HTTP 409)
**Symptom**: CSS/JS files fail with "Public access is not permitted on this storage account"

**Cause**: Static files configured to load from Azure Blob Storage with public access disabled.

**Solution**: Already implemented using WhiteNoise:
- Static files served from container via WhiteNoise middleware
- Azure Blob Storage used only for media uploads (private)
- Provides compression, caching, and cache-busting
- See `requirements/production.txt` and `magictoolbox/settings/production.py`

### View Logs
```bash
az containerapp logs show \
  --name <app-name> \
  --resource-group magictoolbox-dev-rg \
  --follow
```

### Restart App
```bash
az containerapp update \
  --name <app-name> \
  --resource-group magictoolbox-dev-rg
```

### Check Health
```bash
curl https://<app-url>.azurecontainerapps.io/health/
```

## 📖 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[README.md](README.md)** - Application README
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Development guidelines

## 🔐 Security

- All secrets stored in Azure Key Vault
- Managed Identity for service-to-service auth
- HTTPS enforced for all connections via Azure Container Apps ingress
- SSL termination handled at Azure ingress level (not in Django)
- Custom HealthCheckMiddleware for secure internal health probes
- WhiteNoise serves static files efficiently from container
- Azure Blob Storage with private access for user uploads
- Network isolation available via VNet integration
- Container scanning via Azure Defender

## 💰 Cost Estimates

### Development Environment (~$50-100/month)
- Container Apps: ~$20
- PostgreSQL Burstable: ~$15
- Redis Basic: ~$15
- Storage + Other: ~$10

### Production Environment (~$200-500/month)
- Container Apps: ~$100-200
- PostgreSQL General Purpose: ~$80
- Redis Standard: ~$30
- Storage + Other: ~$20
- (Costs vary with usage and scaling)

## 📞 Support

For detailed instructions and troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md)

## ✅ Checklist

Before deploying to production:
- [ ] Generate secure secrets
- [ ] Configure GitHub secrets
- [ ] Update parameter files with correct values
- [ ] Configure custom domain (optional)
- [ ] Setup branch protection rules
- [ ] Enable Azure Defender for Containers
- [ ] Configure backup retention policies
- [ ] Setup alerting in Application Insights
- [ ] Test disaster recovery procedures

---

**Ready to deploy?** Follow the [DEPLOYMENT.md](DEPLOYMENT.md) guide for step-by-step instructions.
