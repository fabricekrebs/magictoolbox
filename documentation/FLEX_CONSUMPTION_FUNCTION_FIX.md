# Azure Functions Not Appearing - Flex Consumption Plan Issue

## Problem Analysis

Azure Functions are not appearing in the portal for a Flex Consumption plan deployment.

## Root Cause

**Flex Consumption plans have a different architecture** than traditional Consumption or Premium plans:

### Key Differences:
1. **Configuration Location**: Runtime settings are in `functionAppConfig.runtime`, NOT in `siteConfig.appSettings`
2. **Deployment Model**: Uses blob storage deployment via `functionAppConfig.deployment`
3. **No Legacy Settings**: Doesn't use `FUNCTIONS_WORKER_RUNTIME` in app settings (redundant with `functionAppConfig.runtime`)

### The Conflict:
The original Bicep template had:
```bicep
functionAppConfig: {
  runtime: {
    name: 'python'
    version: '3.11'
  }
}
siteConfig: {
  appSettings: [
    {
      name: 'FUNCTIONS_WORKER_RUNTIME'  // ❌ Redundant/conflicting
      value: 'python'
    }
    {
      name: 'FUNCTIONS_EXTENSION_VERSION'  // ❌ Not needed for Flex
      value: '~4'
    }
  ]
}
```

This creates a **configuration conflict** where:
- Flex Consumption runtime is configured via `functionAppConfig.runtime`
- But legacy app settings are trying to override it
- Azure gets confused and doesn't load functions properly

## Solution Applied

**Removed redundant/conflicting settings** from `siteConfig.appSettings`:
- ❌ Removed `FUNCTIONS_WORKER_RUNTIME` (handled by `functionAppConfig.runtime.name`)
- ❌ Removed `FUNCTIONS_EXTENSION_VERSION` (Flex Consumption uses latest automatically)
- ❌ Removed `WEBSITE_RUN_FROM_PACKAGE='1'` (handled by `functionAppConfig.deployment`)

**Kept only application-specific settings**:
- ✅ Storage connection (identity-based)
- ✅ Application Insights
- ✅ Database configuration
- ✅ Custom app settings

## Correct Flex Consumption Configuration

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
        name: 'python'      // ✅ This sets the worker runtime
        version: '3.11'     // ✅ This sets the Python version
      }
    }
    siteConfig: {
      appSettings: [
        // ✅ Only application-specific settings here
        // ❌ NO FUNCTIONS_WORKER_RUNTIME
        // ❌ NO FUNCTIONS_EXTENSION_VERSION
        // ❌ NO WEBSITE_RUN_FROM_PACKAGE
      ]
    }
  }
}
```

## Deployment Requirements

For functions to appear after fixing the Bicep:

1. **Redeploy Infrastructure**:
   ```bash
   az deployment group create \
     --resource-group <rg-name> \
     --template-file infra/main.bicep \
     --parameters infra/main.parameters.json
   ```

2. **Deploy Function Code**:
   ```bash
   cd function_app
   func azure functionapp publish <function-app-name> --python
   ```

3. **Verify in Portal**:
   - Navigate to Function App → Functions
   - Should see all 9 functions appear within 2-3 minutes

## Additional Notes

### Why This Matters
- Flex Consumption is a **newer plan type** (GA in 2024)
- Has different deployment model than traditional plans
- Requires different Bicep configuration
- Mixing old and new approaches causes runtime to fail silently

### Common Symptoms
- ✅ Function App deploys successfully
- ✅ App Settings appear in portal
- ❌ But no functions are listed
- ❌ Runtime status shows "Unknown" or "Error"
- ❌ Logs show "Worker failed to start" or similar

### References
- [Flex Consumption Plan Overview](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-plan)
- [Flex Consumption Bicep Examples](https://learn.microsoft.com/en-us/azure/azure-functions/functions-infrastructure-as-code?tabs=bicep)
- [Python Worker Configuration](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)

## Date Fixed
December 15, 2025
