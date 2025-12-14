# Azure Functions Not Appearing - Root Cause & Fix

## Issue Description
Azure Functions were not appearing in the Azure Portal despite having a properly structured `function_app.py` file with 9 decorated functions.

## Root Cause
The **Bicep infrastructure configuration** was missing critical application settings required for Azure Functions to work:

### Missing Settings
1. **`FUNCTIONS_WORKER_RUNTIME`** - Tells Azure the runtime language (Python)
2. **`FUNCTIONS_EXTENSION_VERSION`** - Specifies the Functions runtime version (~4)
3. **`WEBSITE_RUN_FROM_PACKAGE`** - Enables running from deployment package (improves cold start)

Without these settings, Azure Functions runtime cannot:
- Discover function decorators (`@app.route`)
- Load the Python worker
- Execute HTTP triggers
- Display functions in the portal

## Verification of Python Code
✅ The `function_app.py` file is **correct** and has no issues:
- No syntax errors
- Proper function decorators (`@app.route`)
- Correct use of `func.FunctionApp()`
- 9 functions registered:
  - `health` (GET)
  - `pdf/convert` (POST)
  - `storage/list-blobs` (GET)
  - `video/rotate` (POST)
  - `image/convert` (POST)
  - `image/ocr` (POST)
  - `gpx/convert` (POST)
  - `gpx/speed` (POST)
  - `gpx/merge` (POST)

## Solution Applied
Updated `/home/krfa/git-repo/magictoolbox/infra/modules/function-app.bicep` to include the required application settings:

```bicep
siteConfig: {
  appSettings: [
    // ===== CRITICAL: Azure Functions Runtime Configuration =====
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
    // ... rest of settings
  ]
}
```

## Deployment Steps
1. **Redeploy Infrastructure** (to update app settings):
   ```bash
   az deployment group create \
     --resource-group <your-resource-group> \
     --template-file infra/main.bicep \
     --parameters infra/main.parameters.json
   ```

2. **Deploy Function Code** (using GitHub Actions or manual):
   ```bash
   cd function_app
   func azure functionapp publish <function-app-name> --python
   ```

3. **Verify Functions Appear**:
   - Navigate to Azure Portal → Function App → Functions
   - Should see all 9 functions listed
   - Test health endpoint: `https://<function-app-name>.azurewebsites.net/api/health`

## Manual Verification (If Infrastructure Not Redeployed Yet)
If you need to verify immediately without redeploying infrastructure:

1. Go to Azure Portal → Function App → Configuration
2. Add these Application Settings manually:
   - `FUNCTIONS_WORKER_RUNTIME` = `python`
   - `FUNCTIONS_EXTENSION_VERSION` = `~4`
   - `WEBSITE_RUN_FROM_PACKAGE` = `1`
3. Save and restart the Function App
4. Wait 2-3 minutes for the runtime to initialize
5. Check Functions blade in portal

## Common Pitfalls
❌ **Don't forget these settings** when creating new Function Apps
❌ **Don't mix** Flex Consumption plan with wrong runtime settings
✅ **Always include** runtime configuration in Bicep/ARM templates
✅ **Test locally first** using Azure Functions Core Tools (`func start`)

## Related Documentation
- [Azure Functions Python Developer Guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Azure Functions App Settings Reference](https://learn.microsoft.com/en-us/azure/azure-functions/functions-app-settings)
- [Function App Bicep Template](../infra/modules/function-app.bicep)

## Date Fixed
December 14, 2025
