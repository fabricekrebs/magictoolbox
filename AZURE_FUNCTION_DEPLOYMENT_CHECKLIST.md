# Azure Function Bicep Deployment Checklist

## Pre-Deployment Verification ✅

### 1. Bicep Files Updated
- [x] `infra/main.bicep` - Function App principal ID passed to RBAC
- [x] `infra/modules/function-app.bicep` - Managed Identity configured for storage
- [x] `infra/modules/rbac.bicep` - Function App permissions added
- [x] `infra/modules/postgresql.bicep` - Firewall rule for Azure services added
- [x] All Bicep files pass linting (no errors)

### 2. Function App Permissions Configured
- [x] **Storage Blob Data Contributor** role assigned via RBAC
- [x] **Key Vault Secrets User** role assigned via RBAC
- [x] PostgreSQL firewall allows Azure services
- [x] Managed Identity used for all authentication

### 3. Storage Configuration
- [x] `AzureWebJobsStorage__accountName` configured
- [x] `AzureWebJobsStorage__credential` set to `managedidentity`
- [x] Blob trigger will use Managed Identity

### 4. Database Configuration
- [x] `DB_HOST` environment variable configured
- [x] `DB_NAME` environment variable configured
- [x] `DB_USER` environment variable configured
- [x] `DB_PASSWORD` environment variable configured
- [x] Firewall rule allows Function App connection

## Deployment Steps

### Step 1: Deploy Infrastructure
```bash
cd infra
az deployment group create \
  --resource-group magictoolbox-demo-rg \
  --template-file main.bicep \
  --parameters @parameters.dev.json
```

**Expected Duration**: 10-15 minutes

**Verify**:
```bash
# Check deployment status
az deployment group show \
  --resource-group magictoolbox-demo-rg \
  --name <deployment-name> \
  --query properties.provisioningState
```

### Step 2: Wait for RBAC Propagation
**Duration**: 5-10 minutes (Azure RBAC propagation delay)

### Step 3: Deploy Function Code
```bash
cd function_app

# Deploy using Azure Functions Core Tools
func azure functionapp publish <function-app-name> --python
```

**Verify**:
```bash
# Check function deployment
az functionapp function list \
  --resource-group magictoolbox-demo-rg \
  --name <function-app-name> \
  --query "[].{Name:name, Status:properties.status}" -o table
```

### Step 4: Test Function App

#### Test 1: Health Endpoint
```bash
curl https://<function-app-name>.azurewebsites.net/api/health
```
Expected: `{"status": "healthy", "function": "pdf-to-docx-converter"}`

#### Test 2: Storage Access
```bash
# Upload test blob
az storage blob upload \
  --account-name <storage-account-name> \
  --container-name uploads \
  --name pdf/test-$(uuidgen).pdf \
  --file /path/to/test.pdf \
  --auth-mode login

# Monitor function logs
az functionapp log tail \
  --resource-group magictoolbox-demo-rg \
  --name <function-app-name>
```

#### Test 3: Database Connection
From Function App console (Kudu):
```bash
python -c "import psycopg2; conn = psycopg2.connect(host='<db-host>', dbname='magictoolbox', user='<user>', password='<pass>'); print('Connected!')"
```

### Step 5: Enable in Container App
```bash
az containerapp update \
  --resource-group magictoolbox-demo-rg \
  --name <container-app-name> \
  --set-env-vars "USE_AZURE_FUNCTIONS_PDF_CONVERSION=true"
```

### Step 6: End-to-End Test
```bash
# Upload PDF via Django API
curl -X POST https://<container-app-url>/api/v1/tools/pdf-docx-converter/convert/ \
  -F "file=@test.pdf" \
  -F "start_page=0"

# Check status
curl https://<container-app-url>/api/v1/tools/executions/<execution-id>/status/

# Download result
curl -O https://<container-app-url>/api/v1/tools/executions/<execution-id>/download/
```

## Post-Deployment Verification

### Check Function App Managed Identity
```bash
az functionapp show \
  --resource-group magictoolbox-demo-rg \
  --name <function-app-name> \
  --query "identity.{Type:type, PrincipalId:principalId}" -o table
```

Expected:
- Type: `SystemAssigned`
- PrincipalId: `<guid>`

### Check RBAC Assignments
```bash
PRINCIPAL_ID=$(az functionapp show \
  --resource-group magictoolbox-demo-rg \
  --name <function-app-name> \
  --query identity.principalId -o tsv)

az role assignment list \
  --assignee $PRINCIPAL_ID \
  --query "[].{Role:roleDefinitionName, Scope:scope}" -o table
```

Expected roles:
- Storage Blob Data Contributor (on storage account)
- Key Vault Secrets User (on key vault)

### Check PostgreSQL Firewall
```bash
az postgres flexible-server firewall-rule list \
  --resource-group magictoolbox-demo-rg \
  --name <postgres-server-name> \
  --query "[?name=='AllowAllAzureServicesAndResourcesWithinAzureIps'].{Name:name, Start:startIpAddress, End:endIpAddress}" -o table
```

Expected:
- Start: `0.0.0.0`
- End: `0.0.0.0`

### Check Application Insights
```bash
az functionapp show \
  --resource-group magictoolbox-demo-rg \
  --name <function-app-name> \
  --query "siteConfig.appSettings[?name=='APPLICATIONINSIGHTS_CONNECTION_STRING'].value" -o tsv
```

Should return Application Insights connection string.

## Monitoring

### View Function Metrics
```bash
az monitor metrics list \
  --resource /subscriptions/<sub-id>/resourceGroups/magictoolbox-demo-rg/providers/Microsoft.Web/sites/<function-app-name> \
  --metric FunctionExecutionCount \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --interval PT1M
```

### View Function Logs
```bash
az functionapp log tail \
  --resource-group magictoolbox-demo-rg \
  --name <function-app-name>
```

### Application Insights Queries
In Azure Portal -> Application Insights -> Logs:

```kusto
// Function execution duration
requests
| where cloud_RoleName contains "func-"
| summarize avg(duration), max(duration), min(duration) by bin(timestamp, 5m)

// Function errors
exceptions
| where cloud_RoleName contains "func-"
| project timestamp, operation_Name, outerMessage
| order by timestamp desc
```

## Troubleshooting

### Issue: Function can't access storage
**Fix**: Wait 5-10 minutes for RBAC propagation

### Issue: Function can't connect to database
**Fix**: Verify firewall rule and connection string

### Issue: Blob trigger not firing
**Fix**: Check Managed Identity configuration and RBAC

## Success Criteria

- [ ] Infrastructure deployed without errors
- [ ] Function App running and healthy
- [ ] RBAC permissions assigned correctly
- [ ] PostgreSQL firewall configured
- [ ] Function can read/write blobs
- [ ] Function can update database records
- [ ] Application Insights receiving telemetry
- [ ] End-to-end PDF conversion works
- [ ] Download URL accessible

## Rollback Plan

If deployment fails:

```bash
# Delete Function App
az functionapp delete \
  --resource-group magictoolbox-demo-rg \
  --name <function-app-name>

# Remove RBAC assignments
az role assignment delete \
  --assignee <principal-id> \
  --scope <storage-account-id>

# Remove firewall rule
az postgres flexible-server firewall-rule delete \
  --resource-group magictoolbox-demo-rg \
  --name <postgres-server-name> \
  --rule-name AllowAllAzureServicesAndResourcesWithinAzureIps
```

Then redeploy after fixing issues.

---

**Status**: ✅ Ready for Deployment  
**Documentation**: [AZURE_FUNCTION_BICEP_UPDATES.md](./documentation/AZURE_FUNCTION_BICEP_UPDATES.md)
