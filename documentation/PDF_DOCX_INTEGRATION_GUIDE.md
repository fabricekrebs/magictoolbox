# PDF to DOCX Conversion - Integration Guide

**Last Updated**: December 4, 2025  
**Status**: Fixed and Ready for Testing

## 📋 Overview

This guide explains how the PDF to DOCX conversion works with Azure Functions and provides testing instructions.

---

## 🏗️ Architecture

### **Complete Flow**

```
1. User uploads PDF via Django UI/API
   ↓
2. Django creates ToolExecution record (status: "pending")
   ↓
3. Django uploads PDF to Azure Blob Storage (uploads/pdf/{execution_id}.pdf)
   ↓
4. Azure Function is triggered (blob trigger OR HTTP fallback)
   ↓
5. Function updates status to "processing" in database
   ↓
6. Function converts PDF to DOCX using pdf2docx
   ↓
7. Function uploads DOCX to Azure Blob Storage (processed/docx/{execution_id}.docx)
   ↓
8. Function updates status to "completed" with output file path in database
   ↓
9. User polls status endpoint and downloads converted file
```

### **Key Components**

1. **Django Web App** (`apps/tools/plugins/pdf_docx_converter.py`)
   - Validates PDF upload
   - Creates ToolExecution record
   - Uploads to blob storage with metadata
   - Optionally triggers HTTP endpoint

2. **Azure Blob Storage**
   - Container: `uploads` - Subdirectory: `pdf/` - Input PDFs
   - Container: `processed` - Subdirectory: `docx/` - Output DOCX files

3. **Azure Function** (`function_app/function_app.py`)
   - Blob trigger on `uploads/{name}` (filters for `pdf/*.pdf`)
   - HTTP trigger at `/api/convert/pdf-to-docx` (fallback)
   - Converts using pdf2docx library
   - Updates PostgreSQL database directly

4. **PostgreSQL Database** (`tool_executions` table)
   - Shared between Django and Azure Function
   - Tracks status: pending → processing → completed/failed

---

## 🔧 Recent Fixes Applied

### 1. **Blob Trigger Path Fixed**
- **Issue**: Trigger was on `uploads/pdf/{name}` but uploads go to `uploads/pdf/`
- **Fix**: Changed to `uploads/{name}` with filter for `pdf/*.pdf` files
- **Location**: `function_app/function_app.py` line ~455

### 2. **Metadata Extraction Improved**
- **Issue**: execution_id was parsed from blob name, missing metadata
- **Fix**: Now reads from blob metadata first, falls back to blob name
- **Location**: `function_app/function_app.py` line ~480

### 3. **Database Output Path Format Fixed**
- **Issue**: Function saved `processed/{blob_name}` but Django expects just `{blob_name}`
- **Fix**: Now saves just `docx/{uuid}.docx` without container prefix
- **Location**: `function_app/function_app.py` line ~555

### 4. **HTTP Trigger Payload Fixed**
- **Issue**: Django sent `pdf/{uuid}.pdf` but HTTP endpoint expected `uploads/pdf/{uuid}.pdf`
- **Fix**: Django now sends full path `uploads/pdf/{uuid}.pdf`
- **Location**: `apps/tools/plugins/pdf_docx_converter.py` line ~210

### 5. **HTTP Endpoint Database Update Fixed**
- **Issue**: HTTP endpoint used wrong parameter name (`output_url` instead of `output_file`)
- **Fix**: Now uses correct parameters: `output_file`, `output_filename`, `output_size`
- **Location**: `function_app/function_app.py` line ~680

### 6. **Configuration Added**
- **New Setting**: `AZURE_FUNCTION_PDF_CONVERT_URL` in Django settings
- **Location**: `magictoolbox/settings/base.py` line ~267

---

## 🚀 Local Testing Setup

### **Prerequisites**

1. **Azurite** (Azure Storage Emulator)
   ```bash
   docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 \
     mcr.microsoft.com/azure-storage/azurite
   ```

2. **PostgreSQL Database**
   - Must be accessible from both Django and Azure Functions
   - Same database for both (shared `tool_executions` table)

3. **Azure Functions Core Tools**
   ```bash
   npm install -g azure-functions-core-tools@4
   ```

### **Configuration**

#### **Django Configuration** (`.env` file)

```bash
# Enable Azure Functions mode
USE_AZURE_FUNCTIONS_PDF_CONVERSION=True

# Optional: HTTP trigger fallback URL (for local testing)
AZURE_FUNCTION_PDF_CONVERT_URL=http://localhost:7071/api/convert/pdf-to-docx

# Local Azurite connection
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstorageaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstorageaccount1;

# Database (must be shared with Azure Function)
DB_HOST=localhost
DB_NAME=magictoolbox
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
```

#### **Azure Function Configuration** (`function_app/local.settings.json`)

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "DefaultEndpointsProtocol=http;AccountName=devstorageaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstorageaccount1;QueueEndpoint=http://127.0.0.1:10001/devstorageaccount1;TableEndpoint=http://127.0.0.1:10002/devstorageaccount1;",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "DB_HOST": "localhost",
    "DB_NAME": "magictoolbox",
    "DB_USER": "postgres",
    "DB_PASSWORD": "postgres",
    "DB_PORT": "5432"
  },
  "Host": {
    "LocalHttpPort": 7071,
    "CORS": "*"
  }
}
```

### **Create Storage Containers**

Using Azure Storage Explorer or az cli:

```bash
# Install Azure Storage Explorer or use az cli
# Create containers in Azurite
az storage container create --name uploads --connection-string "DefaultEndpointsProtocol=http;AccountName=devstorageaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstorageaccount1;"

az storage container create --name processed --connection-string "DefaultEndpointsProtocol=http;AccountName=devstorageaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstorageaccount1;"
```

Or use the startup scripts in `function_app/`:
```bash
cd function_app
./start_local_env.sh
```

---

## 🧪 Testing Steps

### **1. Start All Services**

**Terminal 1: Azurite**
```bash
docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 \
  mcr.microsoft.com/azure-storage/azurite
```

**Terminal 2: PostgreSQL**
```bash
# Ensure PostgreSQL is running
psql -h localhost -U postgres -d magictoolbox
# Verify tool_executions table exists
\dt tool_executions
```

**Terminal 3: Django**
```bash
source .venv/bin/activate
python manage.py runserver
```

**Terminal 4: Azure Functions**
```bash
cd function_app
source .venv/bin/activate  # or activate the function's venv
func start
```

### **2. Test Upload via API**

```bash
# Create a test user and get auth token first
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'

# Save the token
TOKEN="your-jwt-token-here"

# Upload a PDF for conversion
curl -X POST http://localhost:8000/api/v1/tools/pdf-docx-converter/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.pdf"

# Response will include execution_id
# Example: {"executionId": "550e8400-e29b-41d4-a716-446655440000", "status": "pending", ...}
EXECUTION_ID="550e8400-e29b-41d4-a716-446655440000"
```

### **3. Monitor Azure Function Logs**

Watch Terminal 4 for:
```
🎉 BLOB TRIGGER FIRED - PDF TO DOCX CONVERSION!
📄 Blob name: pdf/550e8400-e29b-41d4-a716-446655440000.pdf
🆔 Execution ID from metadata: 550e8400-e29b-41d4-a716-446655440000
⏳ Step 1: Updating database status to 'processing'...
✅ Database updated successfully
📖 Step 2: Reading PDF content...
🔄 Step 3: Converting PDF to DOCX...
✅ Conversion completed
☁️ Step 4: Uploading DOCX to blob storage...
✅ Uploaded to: processed/docx/550e8400-e29b-41d4-a716-446655440000.docx
✅ Step 5: Updating database status to 'completed'...
🎉 CONVERSION COMPLETED SUCCESSFULLY!
```

### **4. Check Status**

```bash
# Poll status endpoint
curl http://localhost:8000/api/v1/tools/executions/$EXECUTION_ID/status/ \
  -H "Authorization: Bearer $TOKEN"

# Response when completed:
# {
#   "executionId": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "completed",
#   "outputFilename": "sample.docx",
#   "downloadUrl": "/api/v1/tools/executions/550e8400-e29b-41d4-a716-446655440000/download/"
# }
```

### **5. Download Result**

```bash
# Download converted DOCX
curl http://localhost:8000/api/v1/tools/executions/$EXECUTION_ID/download/ \
  -H "Authorization: Bearer $TOKEN" \
  -o converted.docx
```

---

## 🔍 Troubleshooting

### **Issue: Blob trigger not firing**

**Symptoms**: PDF uploads but no function execution

**Checks**:
1. Verify Azure Function is running (`func start` output should show "PdfToDocxConverter" loaded)
2. Check blob storage connection string matches in both Django and Function
3. Verify containers exist (`uploads` and `processed`)
4. Check function logs for any startup errors

**Workaround**: Use HTTP trigger fallback
```bash
# Set in Django .env
AZURE_FUNCTION_PDF_CONVERT_URL=http://localhost:7071/api/convert/pdf-to-docx
```

### **Issue: Database not updating**

**Symptoms**: Function runs but ToolExecution status stays "pending"

**Checks**:
1. Verify database credentials match in `local.settings.json`
2. Check PostgreSQL is accessible from function: `psql -h localhost -U postgres -d magictoolbox`
3. Verify `tool_executions` table exists and has proper schema
4. Check function logs for database connection errors

**Debug SQL**:
```sql
-- Check execution records
SELECT id, status, input_filename, output_filename, created_at, completed_at 
FROM tool_executions 
ORDER BY created_at DESC LIMIT 10;

-- Check specific execution
SELECT * FROM tool_executions WHERE id = '550e8400-e29b-41d4-a716-446655440000';
```

### **Issue: Conversion fails**

**Symptoms**: Status changes to "failed" with error message

**Checks**:
1. Verify pdf2docx is installed in function environment: `pip list | grep pdf2docx`
2. Check input PDF is valid (try opening it)
3. Look at error_message in database: `SELECT error_message FROM tool_executions WHERE id = '...'`
4. Check function logs for detailed traceback

### **Issue: Download fails (404)**

**Symptoms**: Status is "completed" but download returns 404

**Checks**:
1. Verify blob exists in storage:
   ```bash
   az storage blob list --container-name processed --connection-string "..."
   ```
2. Check `output_file` value in database (should be `docx/{uuid}.docx`)
3. Verify Django blob client is using correct container name (`processed`)

**Manual check**:
```python
# Django shell
from azure.storage.blob import BlobServiceClient
conn_str = "..."  # Your connection string
blob_service = BlobServiceClient.from_connection_string(conn_str)
blob_client = blob_service.get_blob_client("processed", "docx/{uuid}.docx")
exists = blob_client.exists()
print(f"Blob exists: {exists}")
```

### **Issue: Wrong output_file format in database**

**Symptoms**: Download fails because path is wrong

**Expected**: `output_file` should be `docx/{uuid}.docx` (no container prefix)

**Fix**: This was fixed in the recent updates. If still seeing `processed/docx/{uuid}.docx`, update Azure Function code and redeploy.

---

## 📊 Monitoring in Production

### **Application Insights Queries**

```kusto
// Function executions
traces
| where operation_Name == "PdfToDocxConverter"
| where timestamp > ago(1h)
| project timestamp, message
| order by timestamp desc

// Failed conversions
exceptions
| where operation_Name == "PdfToDocxConverter"
| where timestamp > ago(24h)
| project timestamp, problemId, outerMessage

// Conversion duration
customMetrics
| where name == "conversion_time_seconds"
| summarize avg(value), max(value), min(value) by bin(timestamp, 5m)
```

### **Database Monitoring**

```sql
-- Conversion success rate (last 24 hours)
SELECT 
  status,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM tool_executions
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND tool_name = 'pdf-docx-converter'
GROUP BY status;

-- Average conversion time
SELECT 
  AVG(duration_seconds) as avg_duration,
  MAX(duration_seconds) as max_duration,
  MIN(duration_seconds) as min_duration
FROM tool_executions
WHERE status = 'completed'
  AND created_at > NOW() - INTERVAL '24 hours'
  AND tool_name = 'pdf-docx-converter';

-- Stuck conversions (processing > 10 minutes)
SELECT id, input_filename, status, created_at, started_at
FROM tool_executions
WHERE status = 'processing'
  AND started_at < NOW() - INTERVAL '10 minutes'
  AND tool_name = 'pdf-docx-converter';
```

---

## 🚀 Production Deployment

### **Environment Variables**

**Django** (Azure Container App):
```bash
USE_AZURE_FUNCTIONS_PDF_CONVERSION=True
AZURE_ACCOUNT_NAME=sawemagictoolboxdev01
AZURE_FUNCTION_PDF_CONVERT_URL=https://func-westeurope-magictoolbox-dev-01.azurewebsites.net/api/convert/pdf-to-docx
# Database connection (Azure PostgreSQL)
DB_HOST=psql-westeurope-magictoolbox-dev-01.postgres.database.azure.com
DB_NAME=magictoolbox
DB_USER=magictoolbox
# DB_PASSWORD comes from Key Vault
```

**Azure Function** (Function App):
```bash
# AzureWebJobsStorage uses Managed Identity
AzureWebJobsStorage__blobServiceUri=https://sawemagictoolboxdev01.blob.core.windows.net
# Database connection (same as Django)
DB_HOST=psql-westeurope-magictoolbox-dev-01.postgres.database.azure.com
DB_NAME=magictoolbox
DB_USER=magictoolbox
# DB_PASSWORD comes from Key Vault or App Settings
```

### **Deployment Steps**

1. **Deploy Infrastructure** (if not already done)
   ```bash
   cd infra
   az deployment group create \
     --resource-group magictoolbox-demo-rg \
     --template-file main.bicep \
     --parameters @parameters.dev.json
   ```

2. **Deploy Function Code**
   ```bash
   cd function_app
   func azure functionapp publish func-westeurope-magictoolbox-dev-01
   ```

3. **Verify Function Deployment**
   ```bash
   # Test health check
   curl https://func-westeurope-magictoolbox-dev-01.azurewebsites.net/api/health/connectivity
   ```

4. **Update Django Configuration**
   - Set environment variables in Container App
   - Restart container to apply changes

5. **Test End-to-End**
   - Upload a PDF via production UI
   - Monitor Application Insights for function execution
   - Verify download works

---

## 📝 Summary of Changes

### Files Modified:

1. **`function_app/function_app.py`**
   - Fixed blob trigger path: `uploads/pdf/{name}` → `uploads/{name}`
   - Added filter for PDF files only
   - Improved metadata extraction (reads from blob metadata first)
   - Fixed database output_file format (removed container prefix)
   - Fixed HTTP endpoint database update parameters

2. **`apps/tools/plugins/pdf_docx_converter.py`**
   - Fixed HTTP trigger blob_name format (now sends full path)

3. **`magictoolbox/settings/base.py`**
   - Added `AZURE_FUNCTION_PDF_CONVERT_URL` setting

4. **`magictoolbox/settings/development.py`**
   - Added comments about Azure Functions configuration

5. **`.env.example`**
   - Added Azure Functions configuration examples

### Database Schema (No Changes Required):

The `tool_executions` table already has the correct schema:
- `output_file`: FileField - stores blob path without container
- `output_filename`: CharField - display name for download
- `output_size`: BigIntegerField - file size in bytes

---

## ✅ Verification Checklist

Before considering this complete:

- [ ] Azurite is running
- [ ] PostgreSQL is accessible
- [ ] Containers `uploads` and `processed` exist in storage
- [ ] Django is configured with correct settings
- [ ] Azure Function is configured with correct settings
- [ ] Upload triggers function (check logs)
- [ ] Database status changes: pending → processing → completed
- [ ] Blob appears in `processed/docx/` container
- [ ] Status endpoint returns correct information
- [ ] Download endpoint returns DOCX file
- [ ] Test with actual PDF (not just dummy bytes)

---

## 🔗 Related Documentation

- [AZURE_FUNCTIONS_PDF_CONVERSION.md](./AZURE_FUNCTIONS_PDF_CONVERSION.md) - Original design document
- [AZURE_DEPLOYMENT_README.md](./AZURE_DEPLOYMENT_README.md) - Infrastructure deployment
- [LOCAL_TESTING.md](../function_app/LOCAL_TESTING.md) - Function local testing guide

---

**Questions or Issues?**
Check the troubleshooting section above or review Application Insights logs in production.
