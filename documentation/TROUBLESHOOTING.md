# Azure Functions Troubleshooting Guide

## Overview
Common issues and solutions for Azure Functions deployment and configuration in MagicToolbox.

---

## Issue 1: Functions Not Appearing in Azure Portal (Traditional Plans)

### Symptoms
- Function App deployed successfully
- No functions listed in Azure Portal
- HTTP endpoints return 404

### Root Cause
Missing critical application settings in Bicep infrastructure configuration.

### Required Settings
1. `FUNCTIONS_WORKER_RUNTIME` - Specifies runtime language (python)
2. `FUNCTIONS_EXTENSION_VERSION` - Runtime version (~4)
3. `WEBSITE_RUN_FROM_PACKAGE` - Enables package deployment (1)

### Solution
Update Bicep template to include required app settings:

```bicep
siteConfig: {
  appSettings: [
    {
      name: 'FUNCTIONS_WORKER_RUNTIME'
      value: 'python'
    }
    {
      name: 'FUNCTIONS_EXTENSION_VERSION'
      value: '~4'
    }
    {
      name: 'WEBSITE_RUN_FROM_PACKAGE'
      value: '1'
    }
    // ... other settings
  ]
}
```

### Manual Fix (Temporary)
1. Azure Portal → Function App → Configuration
2. Add missing Application Settings
3. Save and restart
4. Wait 2-3 minutes for initialization

---

## Issue 2: Functions Not Appearing (Flex Consumption Plan)

### Symptoms
- Function App deployed successfully
- App settings look correct
- No functions listed in portal
- Runtime status shows "Unknown" or "Error"

### Root Cause
Flex Consumption plans use **different configuration architecture**:
- Runtime configured via `functionAppConfig.runtime` (not app settings)
- Deployment via `functionAppConfig.deployment` (not `WEBSITE_RUN_FROM_PACKAGE`)
- Legacy app settings create conflicts

### Configuration Conflicts to Avoid
❌ **Don't** use these in `siteConfig.appSettings` for Flex plans:
- `FUNCTIONS_WORKER_RUNTIME` (redundant with `functionAppConfig.runtime.name`)
- `FUNCTIONS_EXTENSION_VERSION` (Flex uses latest automatically)
- `WEBSITE_RUN_FROM_PACKAGE` (redundant with `functionAppConfig.deployment`)

### Correct Configuration
```bicep
resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  properties: {
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: 'https://${storageAccountName}.blob.core.windows.net/deployments'
          authentication: {
            type: 'SystemAssignedIdentity'
          }
        }
      }
      runtime: {
        name: 'python'
        version: '3.11'
      }
    }
    siteConfig: {
      appSettings: [
        // Only app-specific settings, NOT runtime settings
      ]
    }
  }
}
```

### Deployment Steps
1. Fix Bicep template
2. Redeploy infrastructure: `az deployment group create ...`
3. Deploy function code: `func azure functionapp publish <name> --python`
4. Verify in portal (wait 2-3 minutes)

---

## Issue 3: Blob Storage Connection Failures

### Symptoms
- Functions fail to read/write blobs
- "Unauthorized" or "Connection string not found" errors

### Solutions

**For Local Development:**
```bash
# Use connection string to Azurite
AZURE_STORAGE_CONNECTION_STRING="UseDevelopmentStorage=true"
```

**For Azure (Managed Identity):**
```python
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

blob_service_client = BlobServiceClient(
    account_url=f"https://{account_name}.blob.core.windows.net",
    credential=DefaultAzureCredential()
)
```

**Required Role Assignment:**
```bash
az role assignment create \
  --assignee <managed-identity-principal-id> \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg-name>/providers/Microsoft.Storage/storageAccounts/<storage-name>
```

---

## Issue 4: Database Connection Failures

### Symptoms
- Django can't connect to PostgreSQL
- "Connection refused" or "SSL required" errors

### Required Settings
```python
# .env.development or environment variables
DATABASE_URL=postgresql://username:password@hostname:5432/dbname?sslmode=require
```

### Firewall Rules
For Azure VM access:
```bash
# Allow VM subnet
az postgres flexible-server firewall-rule create \
  --resource-group <rg-name> \
  --name <server-name> \
  --rule-name allow-vm-subnet \
  --start-ip-address <vm-ip> \
  --end-ip-address <vm-ip>
```

For local development:
```bash
# Temporarily allow your IP
az postgres flexible-server firewall-rule create \
  --resource-group <rg-name> \
  --name <server-name> \
  --rule-name allow-my-ip \
  --start-ip-address <your-ip> \
  --end-ip-address <your-ip>
```

---

## Issue 5: Function App Deployment Hangs

### Symptoms
- `func azure functionapp publish` hangs indefinitely
- Deployment shows "Deploying..." for 10+ minutes

### Common Causes
1. Large dependencies in `requirements.txt`
2. Network timeout to Azure
3. Remote build taking too long

### Solutions

**Option 1: Local Build (Faster)**
```bash
cd function_app
pip install --target=".python_packages/lib/site-packages" -r requirements.txt
func azure functionapp publish <name> --no-build
```

**Option 2: Optimize Requirements**
```txt
# Remove unnecessary packages
# Pin versions for reproducibility
azure-functions==1.20.0
azure-storage-blob==12.19.0
python-docx==1.1.0
# ... minimal set only
```

**Option 3: Use GitHub Actions**
See [.github/workflows/azure-function-deploy.yml] for automated deployment.

---

## Issue 6: CORS Errors in Frontend

### Symptoms
- API calls fail with "CORS policy" errors
- Requests blocked by browser

### Solution
Add CORS configuration in Bicep:

```bicep
resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  properties: {
    siteConfig: {
      cors: {
        allowedOrigins: [
          'https://your-app.azurewebsites.net'
          'http://localhost:8000'  // For local dev
        ]
        supportCredentials: true
      }
    }
  }
}
```

---

## Issue 7: High Cold Start Times

### Symptoms
- First request takes 30+ seconds
- Subsequent requests are fast

### Solutions

**1. Use Application Insights for Monitoring:**
```bicep
{
  name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
  value: applicationInsights.properties.InstrumentationKey
}
```

**2. Enable "Always On" (Premium/Dedicated plans only):**
```bicep
siteConfig: {
  alwaysOn: true
}
```

**3. Optimize Code:**
- Import heavy libraries inside functions (not globally)
- Use connection pooling
- Minimize cold start dependencies

---

## Diagnostic Commands

### Check Function App Status
```bash
az functionapp show \
  --name <function-app-name> \
  --resource-group <rg-name> \
  --query "state"
```

### View Function App Logs
```bash
az functionapp log tail \
  --name <function-app-name> \
  --resource-group <rg-name>
```

### Test Function Endpoint
```bash
curl -X POST https://<function-app-name>.azurewebsites.net/api/health
```

### List All Functions
```bash
az functionapp function list \
  --name <function-app-name> \
  --resource-group <rg-name> \
  --output table
```

---

## Best Practices

✅ **Always** test locally first with `func start`  
✅ **Use** managed identity for Azure service connections  
✅ **Pin** dependency versions in `requirements.txt`  
✅ **Monitor** with Application Insights  
✅ **Validate** Bicep templates before deployment  
✅ **Keep** function code lightweight and modular  

❌ **Don't** mix Flex and Traditional plan configurations  
❌ **Don't** commit secrets to `local.settings.json`  
❌ **Don't** use overly broad CORS origins in production  

---

## Related Documentation
- [ASYNC_FILE_PROCESSING_GOLD_STANDARD.md](ASYNC_FILE_PROCESSING_GOLD_STANDARD.md) - Async tool development
- [AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md) - Infrastructure setup
- [E2E_API_TESTING_COMPLETE.md](E2E_API_TESTING_COMPLETE.md) - Testing guide

---

**Last Updated:** December 16, 2025
