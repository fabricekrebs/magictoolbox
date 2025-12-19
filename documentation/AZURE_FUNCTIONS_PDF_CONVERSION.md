# Azure Functions Integration for PDF to DOCX Conversion

**Last Updated**: December 1, 2025  
**Status**: Implemented - Ready for Deployment

## 📋 Overview

This document describes the Azure Functions integration for asynchronous PDF to DOCX conversion in MagicToolbox. The implementation uses Azure Blob Storage triggers to automatically process PDFs uploaded by users, providing a scalable, serverless solution.

---

## 🏗️ Architecture

### **High-Level Flow**

```
User Upload → Django API → Azure Blob Storage → Azure Function → Conversion → Result Storage → User Download
     ↓            ↓              ↓                    ↓              ↓              ↓              ↓
  Web UI    Create Record  uploads/pdf/        Blob Trigger   PDF→DOCX    processed/docx/  Poll Status
                          {exec_id}.pdf                                    {exec_id}.docx    & Download
```

### **Components**

1. **Django Web App** (Container Apps)
   - Validates and uploads PDF to blob storage
   - Creates ToolExecution record with status "pending"
   - Provides status polling API
   - Serves download links for completed conversions

2. **Azure Blob Storage**
   - Container: `uploads/pdf/` - Input PDFs
   - Container: `processed/docx/` - Output DOCX files
   - Blob metadata carries conversion parameters

3. **Azure Function App**
   - Python 3.11 runtime on Linux
   - Consumption plan (serverless, pay-per-execution)
   - Blob trigger on `uploads/pdf/{name}`
   - Converts PDF using `pdf2docx` library
   - Updates ToolExecution status via PostgreSQL

4. **PostgreSQL Database**
   - Shared between Django and Azure Function
   - Stores ToolExecution records for tracking

---

## 🚀 Deployment Guide

### **Prerequisites**

- Azure CLI installed and authenticated
- Existing MagicToolbox infrastructure deployed
- Storage account with `uploads` and `processed` containers
- PostgreSQL database accessible from Azure Functions

### **Step 1: Deploy Function App Infrastructure**

The Function App is included in the main Bicep template. To deploy:

```bash
# Navigate to infrastructure directory
cd infra

# Deploy using existing parameters
az deployment group create \
  --resource-group magictoolbox-demo-rg \
  --template-file main.bicep \
  --parameters @parameters.dev.json
```

This creates:
- Function App with Consumption plan
- System-assigned Managed Identity
- RBAC role assignments (Storage Blob Data Contributor)
- Connection to PostgreSQL database
- Application Insights integration

**Outputs to note:**
```bash
# Get Function App name
FUNC_APP_NAME=$(az deployment group show \
  --resource-group magictoolbox-demo-rg \
  --name <deployment-name> \
  --query properties.outputs.functionAppName.value -o tsv)

echo "Function App: $FUNC_APP_NAME"
```

### **Step 2: Deploy Function Code**

#### **Option A: Using Azure Functions Core Tools (Recommended)**

```bash
# Install Azure Functions Core Tools (if not already installed)
npm install -g azure-functions-core-tools@4

# Navigate to function app directory
cd function_app

# Install Python dependencies locally (for validation)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Deploy to Azure
func azure functionapp publish $FUNC_APP_NAME --python
```

#### **Option B: Using Azure CLI with ZIP Deploy**

```bash
cd function_app

# Create deployment package
zip -r function_app.zip . -x "*.venv*" -x "*__pycache__*" -x "*.git*"

# Deploy package
az functionapp deployment source config-zip \
  --resource-group magictoolbox-demo-rg \
  --name $FUNC_APP_NAME \
  --src function_app.zip
```

#### **Option C: GitHub Actions (CI/CD)**

Add to `.github/workflows/deploy-function-app.yml`:

```yaml
name: Deploy Azure Function

on:
  push:
    branches: [main]
    paths:
      - 'function_app/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd function_app
          pip install -r requirements.txt --target=".python_packages/lib/site-packages"
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy Function App
        uses: Azure/functions-action@v1
        with:
          app-name: ${{ secrets.AZURE_FUNCTION_APP_NAME }}
          package: function_app
```

### **Step 3: Verify Deployment**

```bash
# Check deployment status
az functionapp show \
  --resource-group magictoolbox-demo-rg \
  --name $FUNC_APP_NAME \
  --query state -o tsv

# Test health endpoint
curl https://$FUNC_APP_NAME.azurewebsites.net/api/health

# Expected response:
# {"status": "healthy", "function": "pdf-to-docx-converter"}
```

### **Step 4: Enable Azure Functions in Django**

Update Container Apps environment variable:

```bash
# Get Container App name
CONTAINER_APP_NAME=$(az containerapp list \
  --resource-group magictoolbox-demo-rg \
  --query "[0].name" -o tsv)

# Set environment variable
az containerapp update \
  --resource-group magictoolbox-demo-rg \
  --name $CONTAINER_APP_NAME \
  --set-env-vars "USE_AZURE_FUNCTIONS_PDF_CONVERSION=true"

# Restart to apply changes
az containerapp revision restart \
  --resource-group magictoolbox-demo-rg \
  --name $CONTAINER_APP_NAME \
  --revision $(az containerapp revision list \
    --resource-group magictoolbox-demo-rg \
    --name $CONTAINER_APP_NAME \
    --query "[0].name" -o tsv)
```

---

## 🧪 Testing

### **Test 1: Manual Blob Upload**

```bash
# Upload test PDF directly to blob storage
az storage blob upload \
  --account-name $STORAGE_ACCOUNT_NAME \
  --container-name uploads \
  --name pdf/test-$(uuidgen).pdf \
  --file /path/to/test.pdf \
  --metadata execution_id=$(uuidgen) start_page=0 original_filename=test.pdf \
  --auth-mode login

# Monitor function execution
az functionapp log tail \
  --resource-group magictoolbox-demo-rg \
  --name $FUNC_APP_NAME
```

### **Test 2: Via Django API**

```bash
# Upload PDF via API
curl -X POST http://localhost:8000/api/v1/tools/pdf-docx-converter/convert/ \
  -F "file=@/path/to/test.pdf" \
  -F "start_page=0"

# Response:
# {
#   "executionId": "uuid",
#   "status": "pending",
#   "message": "File uploaded for processing...",
#   "statusUrl": "/api/v1/tools/executions/{uuid}/status/"
# }

# Check status
curl http://localhost:8000/api/v1/tools/executions/{uuid}/status/

# Response when processing:
# {
#   "executionId": "uuid",
#   "status": "processing",
#   "startedAt": "2025-12-01T10:00:00Z",
#   ...
# }

# Response when completed:
# {
#   "executionId": "uuid",
#   "status": "completed",
#   "completedAt": "2025-12-01T10:00:30Z",
#   "downloadUrl": "/api/v1/tools/executions/{uuid}/download/",
#   ...
# }

# Download result
curl -O http://localhost:8000/api/v1/tools/executions/{uuid}/download/
```

### **Test 3: Verify Database Updates**

```bash
# Connect to PostgreSQL
az postgres flexible-server execute \
  --name $POSTGRES_SERVER_NAME \
  --database-name magictoolbox \
  --admin-user $POSTGRES_ADMIN_USER \
  --admin-password $POSTGRES_ADMIN_PASSWORD \
  --querytext "SELECT id, status, created_at, started_at, completed_at FROM tools_toolexecution ORDER BY created_at DESC LIMIT 5;"
```

---

## 📊 Monitoring

### **Function App Metrics**

```bash
# View function execution metrics
az monitor metrics list \
  --resource $FUNC_APP_ID \
  --metric FunctionExecutionCount \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --interval PT1M

# View function errors
az monitor metrics list \
  --resource $FUNC_APP_ID \
  --metric FunctionExecutionUnits \
  --aggregation Total
```

### **Application Insights Queries**

Navigate to Application Insights in Azure Portal and run KQL queries:

```kusto
// Function execution duration
requests
| where cloud_RoleName == "function-app-name"
| where name contains "pdf_to_docx_converter"
| summarize avg(duration), max(duration), min(duration) by bin(timestamp, 5m)

// Function errors
exceptions
| where cloud_RoleName == "function-app-name"
| project timestamp, operation_Name, outerMessage, problemId
| order by timestamp desc

// Blob trigger performance
traces
| where message contains "Processing PDF"
| project timestamp, message
| order by timestamp desc
```

### **Check Logs**

```bash
# Stream live logs
az functionapp log tail \
  --resource-group magictoolbox-demo-rg \
  --name $FUNC_APP_NAME

# Get recent logs
az functionapp log show \
  --resource-group magictoolbox-demo-rg \
  --name $FUNC_APP_NAME \
  --lines 100
```

---

## 🔧 Configuration

### **Environment Variables (Function App)**

Set via Azure Portal or CLI:

| Variable | Description | Example |
|----------|-------------|---------|
| `AzureWebJobsStorage` | Storage connection for Functions runtime | `DefaultEndpointsProtocol=https;...` |
| `FUNCTIONS_WORKER_RUNTIME` | Runtime language | `python` |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account for blob trigger | `magictoolboxdevst...` |
| `DB_HOST` | PostgreSQL hostname | `magictoolbox-dev-psql-...postgres.database.azure.com` |
| `DB_NAME` | Database name | `magictoolbox` |
| `DB_USER` | Database user | `admin_user` |
| `DB_PASSWORD` | Database password | `***` (secret) |
| `DB_PORT` | Database port | `5432` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights connection | `InstrumentationKey=...` |

### **Function App Settings**

In `host.json`:
- `functionTimeout`: `00:10:00` (10 minutes for large PDFs)
- `retry.maxRetryCount`: `3` (automatic retries on failure)
- `retry.strategy`: `exponentialBackoff`

---

## 🛠️ Troubleshooting

### **Issue: Function not triggered**

**Symptoms**: PDF uploaded but no processing happens

**Solutions**:
1. Check blob trigger is working:
   ```bash
   az functionapp function show \
     --resource-group magictoolbox-demo-rg \
     --name $FUNC_APP_NAME \
     --function-name pdf_to_docx_converter
   ```

2. Verify RBAC permissions:
   ```bash
   # Check Managed Identity has Storage Blob Data Contributor role
   az role assignment list \
     --scope /subscriptions/{sub-id}/resourceGroups/magictoolbox-demo-rg/providers/Microsoft.Storage/storageAccounts/{storage-name} \
     --assignee {function-app-principal-id}
   ```

3. Check Application Insights for errors

### **Issue: Database connection fails**

**Symptoms**: Function executes but status not updated

**Solutions**:
1. Test database connectivity:
   ```bash
   # From Function App console
   python -c "import psycopg2; conn = psycopg2.connect('host=... dbname=... user=... password=...')"
   ```

2. Verify firewall rules allow Function App IP
3. Check connection string in environment variables

### **Issue: Conversion fails**

**Symptoms**: Status changes to "failed" with error message

**Solutions**:
1. Check error in ToolExecution record
2. Review Application Insights exceptions
3. Verify PDF is not corrupted or password-protected
4. Check function timeout (increase if needed for large PDFs)

### **Issue: High costs**

**Symptoms**: Unexpected Azure Functions charges

**Solutions**:
1. Review execution metrics to identify excessive runs
2. Check for retry loops (blob trigger firing repeatedly)
3. Implement dead-letter queue for poison messages
4. Consider switching to Premium plan if execution count is consistently high

---

## 💰 Cost Analysis

### **Consumption Plan Pricing** (as of Dec 2025)

- **Execution**: $0.20 per million executions
- **Execution Time**: $0.000016 per GB-s
- **Free Grant**: 1 million executions + 400,000 GB-s per month

### **Estimated Costs**

**Development Environment** (100 PDFs/month):
- Executions: 100 × $0.20 / 1,000,000 = **$0.00** (within free tier)
- Compute: 100 × 30s × 1GB × $0.000016 = **$0.05**
- **Total: ~$0** (free tier covers usage)

**Production Environment** (1,000 PDFs/month):
- Executions: 1,000 × $0.20 / 1,000,000 = **$0.00** (within free tier)
- Compute: 1,000 × 30s × 1GB × $0.000016 = **$0.48**
- **Total: ~$0.50/month**

**High Volume** (10,000 PDFs/month):
- Executions: 10,000 × $0.20 / 1,000,000 = **$0.00** (within free tier)
- Compute: 10,000 × 30s × 1GB × $0.000016 = **$4.80**
- **Total: ~$5/month**

---

## 🔄 Switching Between Sync and Async

### **Enable Async Processing (Azure Functions)**

```bash
az containerapp update \
  --resource-group magictoolbox-demo-rg \
  --name $CONTAINER_APP_NAME \
  --set-env-vars "USE_AZURE_FUNCTIONS_PDF_CONVERSION=true"
```

### **Disable Async Processing (Synchronous)**

```bash
az containerapp update \
  --resource-group magictoolbox-demo-rg \
  --name $CONTAINER_APP_NAME \
  --set-env-vars "USE_AZURE_FUNCTIONS_PDF_CONVERSION=false"
```

**Note**: Synchronous mode processes PDFs immediately in the Django process. This is simpler but:
- Blocks HTTP requests (timeout risk for large files)
- Uses Container App CPU/memory
- No automatic retries
- Less scalable

---

## 📚 API Reference

### **POST /api/v1/tools/pdf-docx-converter/convert/**

Convert PDF to DOCX (async mode).

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/tools/pdf-docx-converter/convert/ \
  -F "file=@document.pdf" \
  -F "start_page=0" \
  -F "end_page=10"
```

**Response (202 Accepted):**
```json
{
  "executionId": "uuid",
  "status": "pending",
  "message": "File uploaded for processing. Use the executionId to check status.",
  "statusUrl": "/api/v1/tools/executions/uuid/status/"
}
```

### **GET /api/v1/tools/executions/{id}/status/**

Check conversion status.

**Response:**
```json
{
  "executionId": "uuid",
  "status": "completed",
  "createdAt": "2025-12-01T10:00:00Z",
  "startedAt": "2025-12-01T10:00:05Z",
  "completedAt": "2025-12-01T10:00:30Z",
  "durationSeconds": 25.0,
  "inputFilename": "document.pdf",
  "outputFilename": "document.docx",
  "outputSize": 524288,
  "downloadUrl": "/api/v1/tools/executions/uuid/download/",
  "error": null
}
```

### **GET /api/v1/tools/executions/{id}/download/**

Download converted DOCX file.

**Response:** Binary file download

---

## 🎯 Best Practices

1. **Blob Lifecycle Management**: Set up lifecycle policies to auto-delete old files:
   ```bash
   az storage account management-policy create \
     --account-name $STORAGE_ACCOUNT_NAME \
     --policy @lifecycle-policy.json
   ```

2. **Dead-Letter Queue**: Handle poison messages (PDFs that repeatedly fail)

3. **Monitoring**: Set up alerts for function failures

4. **Rate Limiting**: Implement per-user upload limits in Django

5. **Security**: Use Managed Identity everywhere (no connection strings in code)

6. **Testing**: Test with various PDF types (text, scanned, forms, encrypted)

---

## 📖 Related Documentation

- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Azure Blob Storage Triggers](https://docs.microsoft.com/azure/azure-functions/functions-bindings-storage-blob-trigger)
- [pdf2docx Library](https://github.com/dothinking/pdf2docx)
- [MagicToolbox Deployment Guide](./AZURE_DEPLOYMENT_README.md)

---

## ✅ Deployment Checklist

- [ ] Deploy Function App infrastructure via Bicep
- [ ] Deploy Function code to Azure
- [ ] Verify RBAC permissions (Storage Blob Data Contributor)
- [ ] Test health endpoint
- [ ] Enable `USE_AZURE_FUNCTIONS_PDF_CONVERSION=true` in Container App
- [ ] Test PDF upload via API
- [ ] Verify status polling works
- [ ] Test download endpoint
- [ ] Check Application Insights for telemetry
- [ ] Set up monitoring alerts
- [ ] Configure blob lifecycle policies
- [ ] Document for team

---

**Deployment Status**: ✅ Code complete, ready for Azure deployment  
**Next Steps**: Deploy infrastructure and test in development environment
