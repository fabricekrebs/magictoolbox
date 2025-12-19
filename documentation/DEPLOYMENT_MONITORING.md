# Deployment Monitoring Checklist

**Date**: December 4, 2025  
**Commit**: b1a4014  
**Branch**: develop  
**Status**: 🚀 Deployed and Monitoring

---

## 📦 What Was Deployed

### Code Changes:
1. **Azure Function App** (`function_app/function_app.py`)
   - Fixed blob trigger path
   - Improved metadata extraction
   - Fixed database output format
   - Enhanced HTTP endpoint

2. **Infrastructure** (Bicep files)
   - Updated Container Apps to include Function App URL
   - Added AZURE_ACCOUNT_NAME setting
   - Function App module already deployed

3. **Django Application**
   - Fixed HTTP trigger payload format
   - Added configuration settings
   - Ready for Azure Functions mode

---

## 🔍 Deployment Monitoring

### GitHub Actions Workflows

Check status at: https://github.com/fabricekrebs/magictoolbox/actions

#### 1. Deploy Azure Function App
**Triggered by**: `function_app/**` changes  
**Expected duration**: 3-5 minutes  

**Steps to Monitor**:
- [ ] Checkout code
- [ ] Set up Python 3.11
- [ ] Azure Login
- [ ] Get Function App name
- [ ] Create deployment package
- [ ] Temporarily enable storage public access
- [ ] Upload package to blob storage
- [ ] Set WEBSITE_RUN_FROM_PACKAGE
- [ ] Restore storage private access

**Success Indicators**:
- ✅ Deployment package uploaded
- ✅ Function App restarted with new code
- ✅ No errors in workflow log

**How to Verify**:
```bash
# Check Function App health
curl https://func-westeurope-magictoolbox-dev-01.azurewebsites.net/api/health/connectivity

# Check Function App logs
az functionapp log tail \
  --name func-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01
```

#### 2. Deploy Infrastructure (if triggered)
**Triggered by**: `infra/**` changes  
**Expected duration**: 10-15 minutes  

**Steps to Monitor**:
- [ ] Validate Bicep templates
- [ ] Deploy infrastructure changes
- [ ] Update Container App settings
- [ ] Verify resource group state

**Success Indicators**:
- ✅ Bicep validation passed
- ✅ Infrastructure deployment completed
- ✅ No errors in deployment log

**How to Verify**:
```bash
# Check deployment status
az deployment group list \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "[0].{Name:name, State:properties.provisioningState, Timestamp:properties.timestamp}" \
  -o table

# Check Container App environment variables
az containerapp show \
  --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "properties.template.containers[0].env[?name=='AZURE_FUNCTION_PDF_CONVERT_URL']"
```

---

## ✅ Post-Deployment Verification

### 1. Function App Health Check

```bash
# Check connectivity endpoint
curl https://func-westeurope-magictoolbox-dev-01.azurewebsites.net/api/health/connectivity | jq

# Expected response:
# {
#   "timestamp": "...",
#   "storage": { "accessible": true, ... },
#   "database": { "accessible": true, ... },
#   "overall_status": "healthy"
# }
```

### 2. Container App Settings

Verify these environment variables are set:
- [ ] `USE_AZURE_FUNCTIONS_PDF_CONVERSION=true`
- [ ] `AZURE_FUNCTION_PDF_CONVERT_URL=https://func-westeurope-magictoolbox-dev-01.azurewebsites.net/api/convert/pdf-to-docx`
- [ ] `AZURE_ACCOUNT_NAME=sawemagictoolboxdev01`

```bash
# Check all Azure Functions related settings
az containerapp show \
  --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "properties.template.containers[0].env[?contains(name, 'AZURE')]" \
  -o table
```

### 3. End-to-End PDF Conversion Test

```bash
# Get Container App URL
CONTAINER_APP_URL=$(az containerapp show \
  --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Container App URL: https://${CONTAINER_APP_URL}"

# Test upload (requires authentication)
# 1. Login to get JWT token
TOKEN=$(curl -X POST "https://${CONTAINER_APP_URL}/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"your-password"}' | jq -r '.access')

# 2. Upload a PDF
EXECUTION_ID=$(curl -X POST "https://${CONTAINER_APP_URL}/api/v1/tools/pdf-docx-converter/" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@sample.pdf" | jq -r '.executionId')

echo "Execution ID: ${EXECUTION_ID}"

# 3. Check status (repeat until completed)
curl "https://${CONTAINER_APP_URL}/api/v1/tools/executions/${EXECUTION_ID}/status/" \
  -H "Authorization: Bearer ${TOKEN}" | jq

# 4. Download when completed
curl "https://${CONTAINER_APP_URL}/api/v1/tools/executions/${EXECUTION_ID}/download/" \
  -H "Authorization: Bearer ${TOKEN}" \
  -o converted.docx
```

---

## 📊 Monitoring Points

### Application Insights

Check for:
- Function execution logs
- Conversion duration metrics
- Error rates
- Database query performance

```kusto
// Function executions in last hour
traces
| where operation_Name == "PdfToDocxConverter"
| where timestamp > ago(1h)
| order by timestamp desc
| take 50

// Conversion failures
exceptions
| where operation_Name == "PdfToDocxConverter"
| where timestamp > ago(24h)
| summarize count() by problemId, outerMessage
```

### Database

Check ToolExecution records:

```sql
-- Recent conversions
SELECT id, status, input_filename, output_filename, created_at, completed_at
FROM tool_executions
WHERE tool_name = 'pdf-docx-converter'
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- Conversion success rate
SELECT 
  status,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM tool_executions
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND tool_name = 'pdf-docx-converter'
GROUP BY status;
```

### Azure Blob Storage

Check containers have files:

```bash
# List recent uploads
az storage blob list \
  --account-name sawemagictoolboxdev01 \
  --container-name uploads \
  --prefix "pdf/" \
  --query "[].{Name:name, Size:properties.contentLength, Created:properties.creationTime}" \
  --auth-mode login \
  -o table

# List recent processed files
az storage blob list \
  --account-name sawemagictoolboxdev01 \
  --container-name processed \
  --prefix "docx/" \
  --query "[].{Name:name, Size:properties.contentLength, Created:properties.creationTime}" \
  --auth-mode login \
  -o table
```

---

## 🚨 Troubleshooting

### Issue: Function App deployment failed

**Check**:
1. GitHub Actions logs for error details
2. Storage account accessibility during deployment
3. Function App logs: `az functionapp log tail`

**Common fixes**:
- Retry the workflow
- Manually enable storage public access temporarily
- Check if deployment blob exists

### Issue: Function not triggering on blob upload

**Check**:
1. Function App is running: `az functionapp show --query "state"`
2. Blob trigger binding is correct in deployed code
3. Storage connection is using Managed Identity
4. Containers `uploads` and `processed` exist

**Test**:
```bash
# Manually trigger via HTTP endpoint
curl -X POST "https://func-westeurope-magictoolbox-dev-01.azurewebsites.net/api/convert/pdf-to-docx" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_id": "test-uuid",
    "blob_name": "uploads/pdf/test.pdf"
  }'
```

### Issue: Database updates not happening

**Check**:
1. Function App has correct DB credentials
2. PostgreSQL firewall allows Azure services
3. Key Vault references are working
4. Database connection string format

**Test**:
```bash
# Check Function App settings
az functionapp config appsettings list \
  --name func-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "[?name=='DB_HOST' || name=='DB_NAME' || name=='DB_USER']"
```

### Issue: Download fails (404)

**Check**:
1. `output_file` format in database (should be `docx/{uuid}.docx`)
2. Blob exists in `processed` container
3. Django has correct `AZURE_ACCOUNT_NAME` setting

**Verify**:
```sql
-- Check output_file format
SELECT id, output_file, output_filename
FROM tool_executions
WHERE status = 'completed'
ORDER BY completed_at DESC
LIMIT 5;
```

---

## ✅ Success Criteria

Deployment is successful when:

- [x] GitHub Actions workflows complete without errors
- [ ] Function App health check returns `"overall_status": "healthy"`
- [ ] Container App has all required environment variables
- [ ] End-to-end PDF upload → conversion → download works
- [ ] No errors in Application Insights logs
- [ ] Database updates show `pending → processing → completed` flow
- [ ] Converted DOCX files appear in blob storage
- [ ] Download endpoint returns valid DOCX files

---

## 📝 Notes

- First deployment after code changes - monitor closely
- Blob trigger may have 1-2 minute delay (Consumption plan)
- HTTP fallback available if blob trigger issues persist
- All tests passed locally - production should work similarly

---

**Deployed by**: Automated GitHub Actions  
**Monitoring by**: Developer  
**Status**: 🟢 Monitoring in progress
