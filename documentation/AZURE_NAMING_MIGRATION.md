# Azure Naming Convention Migration Summary

## Overview

All Azure resources in the MagicToolbox project have been updated to follow a new standardized naming convention that aligns with Azure best practices and improves resource organization, searchability, and governance.

## New Naming Convention Format

### Standard Pattern
```
{prefix}-{location}-{app}-{env}-{instance}
```

### For Resources with Constraints (no hyphens)
```
{prefix}{locationAbbr}{app}{env}{instance}
```

## Resource Naming Changes

### Development Environment (westeurope)

| Resource Type | Old Name | New Name |
|--------------|----------|----------|
| **Resource Group** | `magictoolbox-dev-rg` | `rg-westeurope-magictoolbox-dev-01` |
| **Container Apps Env** | `env-magictoolboxdevgrrafkow` | `env-westeurope-magictoolbox-dev-01` |
| **Container App** | `app-magictoolboxdevgrrafkow` | `app-westeurope-magictoolbox-dev-01` |
| **Container Registry** | `magictoolboxdevacrgrrafkow6cceq` | `acrwemagictoolboxdev01` |
| **Key Vault** | `kvmagictoolboxdevgrraf` | `kvwemagictoolboxdev01` |
| **Application Insights** | `magictoolbox-dev-ai-grrafkow` | `ai-westeurope-magictoolbox-dev-01` |
| **Log Analytics** | `magictoolbox-dev-logs-grrafkow` | `law-westeurope-magictoolbox-dev-01` |
| **Redis Cache** | `magictoolbox-dev-redis-grrafkow` | `red-westeurope-magictoolbox-dev-01` |
| **PostgreSQL** | `magictoolbox-dev-psql-grrafkow` | `psql-westeurope-magictoolbox-dev-01` |
| **Storage Account** | `magictoolboxdevstgrrafkow` | `sawemagictoolboxdev01` |

### Staging Environment (westeurope)

| Resource Type | Old Name | New Name |
|--------------|----------|----------|
| **Resource Group** | `magictoolbox-staging-rg` | `rg-westeurope-magictoolbox-staging-01` |
| **Container App** | `app-magictoolbox-staging` | `app-westeurope-magictoolbox-sta-01` |
| **Container Registry** | Shared with dev | `acrwemagictoolboxsta01` |

### Production Environment (westeurope)

| Resource Type | Old Name | New Name |
|--------------|----------|----------|
| **Resource Group** | `magictoolbox-prod-rg` | `rg-westeurope-magictoolbox-prod-01` |
| **Container App** | `app-magictoolbox-prod` | `app-westeurope-magictoolbox-prod-01` |
| **Container Registry** | N/A | `acrwemagictoolboxprod01` |

## Files Updated

### Infrastructure as Code (Bicep)
- ✅ `/infra/main.bicep` - Main orchestration template
- ✅ `/infra/modules/monitoring.bicep` - Log Analytics & App Insights
- ✅ `/infra/modules/acr.bicep` - Container Registry
- ✅ `/infra/modules/redis.bicep` - Redis Cache
- ✅ `/infra/modules/keyvault.bicep` - Key Vault
- ✅ `/infra/modules/postgresql.bicep` - PostgreSQL Database
- ✅ `/infra/modules/storage.bicep` - Storage Account
- ✅ `/infra/modules/container-apps.bicep` - Container Apps

### Documentation
- ✅ `AZURE_NAMING_CONVENTION.md` - **NEW** Complete naming standards document
- ✅ `GITHUB_SECRETS_QUICK_REFERENCE.md` - GitHub secrets with new resource names
- ✅ `GITHUB_SECRETS_SETUP.md` - Updated setup guide
- ✅ `DEPLOYMENT.md` - All deployment commands updated
- ✅ `AZURE_KEYVAULT_APPINSIGHTS.md` - Azure resource references
- ✅ `README.md` - Added reference to naming convention doc

### Scripts
- ✅ `/scripts/deploy-to-azure.sh` - Updated examples
- ✅ `/scripts/setup-github-secrets.sh` - Updated defaults

## Key Improvements

### 1. **Consistency**
- All resources follow the same hierarchical pattern
- Predictable naming makes automation easier

### 2. **Clarity**
- Resource type immediately visible (prefix)
- Location and environment clear at a glance
- No ambiguous abbreviated names

### 3. **Governance**
- Better cost tracking by location and environment
- Easier to enforce Azure policies
- Improved compliance auditing

### 4. **Searchability**
- Easy to filter in Azure Portal
- Simple to script resource discovery
- Quick identification in logs

### 5. **Scalability**
- Instance numbers support multiple deployments
- Can deploy same app to multiple regions
- Supports blue-green deployments

### 6. **Compliance**
- Adheres to Azure naming rules
- Respects length constraints
- Follows Microsoft best practices

## Location Abbreviations

For resources with strict length limits (e.g., Storage Account = 24 chars, Key Vault = 24 chars, ACR = 50 chars):

| Location | Abbreviation |
|----------|--------------|
| `westeurope` | `we` |
| `northeurope` | `ne` |
| `eastus` | `eu` |
| `eastus2` | `eu2` |

## Breaking Changes

⚠️ **Important**: This is a breaking change for existing deployments.

### Migration Options

**Option 1: Fresh Deployment (Recommended for Dev/Test)**
1. Delete existing resource group
2. Deploy with new naming convention
3. Restore data if needed

**Option 2: Side-by-Side Migration**
1. Deploy new resources with new names
2. Migrate data from old to new
3. Update application configuration
4. Switch traffic to new resources
5. Decommission old resources

**Option 3: Gradual Migration (Production)**
1. Create new resource group with new name
2. Deploy resources one by one with new naming
3. Configure data replication where possible
4. Test thoroughly in staging first
5. Execute cutover during maintenance window

## GitHub Secrets Update Required

After deploying with new naming convention, update these GitHub secrets:

### Repository Secrets
- `ACR_LOGIN_SERVER` → `acrwemagictoolboxdev01.azurecr.io`
- `ACR_USERNAME` → `acrwemagictoolboxdev01`
- `ACR_NAME` → `acrwemagictoolboxdev01`

### Environment Secrets (Development)
- `RESOURCE_GROUP_DEV` → `rg-westeurope-magictoolbox-dev-01`
- `CONTAINER_APP_NAME_DEV` → `app-westeurope-magictoolbox-dev-01`

### Environment Secrets (Production)
- `RESOURCE_GROUP_PROD` → `rg-westeurope-magictoolbox-prod-01`
- `CONTAINER_APP_NAME_PROD` → `app-westeurope-magictoolbox-prod-01`

Run the automated script:
```bash
./scripts/setup-github-secrets.sh
```

## Service Principal Naming

Service principals also follow the new convention:

```
sp-{app}-cicd-{env}
```

Examples:
- `sp-magictoolbox-cicd-dev`
- `sp-magictoolbox-cicd-staging`
- `sp-magictoolbox-cicd-prod`

## Validation Steps

After migration, verify:

1. **Bicep Deployment**
   ```bash
   az deployment group create \
     --resource-group rg-westeurope-magictoolbox-dev-01 \
     --template-file infra/main.bicep \
     --parameters infra/parameters.dev.json
   ```

2. **Resource Existence**
   ```bash
   az resource list --resource-group rg-westeurope-magictoolbox-dev-01 --output table
   ```

3. **Container App Access**
   ```bash
   az containerapp show \
     --name app-westeurope-magictoolbox-dev-01 \
     --resource-group rg-westeurope-magictoolbox-dev-01 \
     --query properties.configuration.ingress.fqdn
   ```

4. **ACR Authentication**
   ```bash
   az acr login --name acrwemagictoolboxdev01
   ```

## Next Steps

1. Review the comprehensive naming standards in [AZURE_NAMING_CONVENTION.md](AZURE_NAMING_CONVENTION.md)
2. Plan migration strategy (fresh vs gradual)
3. Update GitHub secrets using [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)
4. Deploy to dev environment first for validation
5. Test thoroughly before production migration
6. Update any external integrations or documentation

## Reference Documentation

- **[AZURE_NAMING_CONVENTION.md](AZURE_NAMING_CONVENTION.md)** - Complete naming standards
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Full deployment guide
- **[GITHUB_SECRETS_QUICK_REFERENCE.md](GITHUB_SECRETS_QUICK_REFERENCE.md)** - Secrets checklist
- **[AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md)** - Quick start guide

## Questions or Issues?

If you encounter any issues during migration:
1. Check [AZURE_CONTAINER_APPS_TROUBLESHOOTING.md](AZURE_CONTAINER_APPS_TROUBLESHOOTING.md)
2. Review Bicep templates for correct variable usage
3. Verify all GitHub secrets are updated
4. Check Azure Portal for resource creation status

---

**Migration Date**: November 27, 2025  
**Version**: 1.0  
**Status**: ✅ Complete - Ready for deployment
