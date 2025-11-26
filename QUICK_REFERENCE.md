# Quick Reference: Key Vault & Application Insights

## ✅ What Was Implemented

### Key Vault Integration
- Secure secret storage with RBAC-based access
- Managed identity authentication (no passwords)
- Automatic secret retrieval with env var fallback
- Secrets: django-secret-key, postgres-password, redis-access-key, storage-account-key

### Application Insights
- Distributed request tracing with OpenCensus
- Exception logging with stack traces
- Performance metrics and custom events
- Environment-aware sampling (100% dev, 50% prod)

### DevOps Automation
- Comprehensive deployment script (`scripts/deploy-to-azure.sh`)
- GitHub Actions CI/CD pipeline (`.github/workflows/azure-deploy.yml`)
- RBAC role assignments in Bicep (`infra/modules/rbac.bicep`)

## 🚀 Quick Deploy

### Option 1: Manual Deployment Script
```bash
./scripts/deploy-to-azure.sh \
    --environment dev \
    --resource-group magictoolbox-dev-rg
```

### Option 2: GitHub Actions
1. Configure secrets in GitHub repository
2. Push to `develop` branch → deploys to dev
3. Push to `main` branch → deploys to staging → requires approval for prod

## 🔍 Verify Integration

### Check Key Vault Access
```bash
# View Container App logs
az containerapp logs show \
    --name <app-name> \
    --resource-group <rg> \
    --follow | grep -E "Key Vault|Retrieved"

# Should see: "Retrieved django-secret-key from Key Vault"
```

### Check Application Insights
```bash
# Query recent requests
az monitor app-insights query \
    --app <app-insights-name> \
    --analytics-query "requests | take 10"

# Query exceptions
az monitor app-insights query \
    --app <app-insights-name> \
    --analytics-query "exceptions | take 10"
```

### Check RBAC Assignments
```bash
# Get Container App managed identity
PRINCIPAL_ID=$(az containerapp show \
    --name <app-name> \
    --resource-group <rg> \
    --query "identity.principalId" -o tsv)

# List role assignments
az role assignment list \
    --assignee $PRINCIPAL_ID \
    --all
```

## 📋 Environment Variables

### Required in Container App
```bash
# Key Vault
KEY_VAULT_NAME=kvmagictoolboxgrrafk

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=<from-secret>

# Environment
ENVIRONMENT=dev|staging|prod

# Database
DB_HOST=<postgres-host>
DB_NAME=magictoolbox
DB_USER=<username>
DB_PASSWORD=<from-keyvault-or-secret>

# Redis
REDIS_HOST=<redis-hostname>
REDIS_URL=rediss://...

# Storage
AZURE_STORAGE_ACCOUNT_NAME=<storage-account>
```

## 🐛 Common Issues

### "Could not retrieve secret from Key Vault"
**Cause**: Missing RBAC permissions
**Fix**: 
```bash
# Verify RBAC role assignment exists
az role assignment list --scope <keyvault-id>
```

### "No telemetry in Application Insights"
**Cause**: Missing packages or wrong connection string
**Fix**:
```bash
# Check packages installed
az containerapp exec \
    --name <app-name> \
    --resource-group <rg> \
    --command "pip list | grep opencensus"

# Verify connection string set
az containerapp show \
    --name <app-name> \
    --resource-group <rg> \
    --query "properties.template.containers[0].env[?name=='APPLICATIONINSIGHTS_CONNECTION_STRING']"
```

### "Application using env vars instead of Key Vault"
**Status**: This is EXPECTED behavior (fallback)
**Note**: Application gracefully falls back to environment variables if Key Vault is unavailable

## 📊 Monitoring

### Application Insights Dashboards
- **Performance**: Azure Portal → Application Insights → Performance
- **Failures**: Azure Portal → Application Insights → Failures  
- **Logs**: Azure Portal → Application Insights → Logs

### Key Metrics to Monitor
- Request duration (p50, p95, p99)
- Exception rate
- Dependency call duration (DB, Redis, Storage)
- HTTP 5xx error rate

### Cost Tracking
- **Key Vault**: ~$5/month (minimal operations)
- **Application Insights**: ~$10-30/month (with 50% sampling)
- **Total Additional**: ~$15-35/month

## 📚 Documentation Files

- `AZURE_KEYVAULT_APPINSIGHTS.md` - Comprehensive guide (400+ lines)
- `DEVOPS_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `DEPLOYMENT.md` - Azure deployment guide
- `README.md` - Updated with Key Vault/App Insights info

## 🔧 Useful Commands

```bash
# Deploy infrastructure only
./scripts/deploy-to-azure.sh --environment dev --resource-group <rg> --skip-build

# Update Container App only
./scripts/deploy-to-azure.sh --environment dev --resource-group <rg> --skip-infra

# View Container App health
az containerapp show \
    --name <app-name> \
    --resource-group <rg> \
    --query "properties.runningStatus"

# List Container App revisions
az containerapp revision list \
    --name <app-name> \
    --resource-group <rg>

# Rollback to previous revision
az containerapp revision activate \
    --name <app-name> \
    --resource-group <rg> \
    --revision <previous-revision-name>

# View Key Vault secrets (admin only)
az keyvault secret list --vault-name <vault-name>

# Query Application Insights
az monitor app-insights query \
    --app <app-insights-name> \
    --analytics-query "requests | summarize count() by resultCode"
```

## ✨ Key Benefits

1. **Security**: No secrets in code, managed identity everywhere
2. **Observability**: Full visibility into app performance and errors
3. **Automation**: One-command deployment with validation
4. **Reliability**: Graceful fallback, auto-scaling, health checks
5. **Cost-Optimized**: Adaptive sampling, efficient caching
6. **DevOps Ready**: CI/CD pipeline, IaC, automated testing

## 🎯 Next Steps

1. **Configure GitHub Secrets** for CI/CD pipeline
2. **Deploy to dev environment** using deployment script
3. **Verify Key Vault and App Insights** integration
4. **Set up monitoring alerts** in Azure Portal
5. **Review cost** in Azure Cost Management

---

For detailed information, see:
- **AZURE_KEYVAULT_APPINSIGHTS.md** - Complete documentation
- **DEVOPS_IMPLEMENTATION_SUMMARY.md** - Implementation details
