# PDF to DOCX Conversion Workflow with Azure Functions

This document describes the complete workflow for PDF to DOCX conversion using Azure Functions for asynchronous processing.

## Architecture Overview

```
User Upload (Django) → Blob Storage → Azure Function → Blob Storage → Database Update
                    ↓                                              ↑
                Database (Create Record)                Database (Update Record)
```

## Workflow Steps

### 1. User Initiates Conversion (Django)

**Location**: `apps/tools/plugins/pdf_docx_converter.py` - `_process_async()` method

**Process**:
1. Generate unique `execution_id` (UUID)
2. Upload PDF to blob storage at `uploads/pdf/{execution_id}.pdf`
3. Set blob metadata:
   - `execution_id`: UUID for tracking
   - `original_filename`: Original file name
   - `start_page`: First page to convert (optional)
   - `end_page`: Last page to convert (optional)
4. Trigger Azure Function via HTTP POST to `/api/pdf/convert`
5. Return `execution_id` to caller

**Logging**: Comprehensive logging with emoji indicators for easy troubleshooting:
- 📤 Upload start
- 🔧 Local Azurite vs 🔐 Azure Managed Identity
- ✅ Success indicators
- ❌ Error indicators
- 🚀 Function trigger

### 2. Create Database Record (Django)

**Location**: `apps/tools/views.py` - `ToolViewSet.convert_file()` method

**Process**:
1. After `process()` returns `execution_id`, create `ToolExecution` record
2. Set fields:
   - `id`: Same as `execution_id` for consistency
   - `user`: Authenticated user
   - `tool_name`: "pdf-docx-converter"
   - `input_filename`: Original filename
   - `input_size`: File size in bytes
   - `status`: "pending"
   - `azure_function_invoked`: `True`
   - `function_execution_id`: Same as `execution_id`
   - `input_blob_path`: `uploads/pdf/{execution_id}.pdf`
3. Return HTTP 202 Accepted with execution details

**API Response**:
```json
{
  "executionId": "uuid-string",
  "filename": "document.pdf",
  "status": "pending",
  "statusUrl": "/api/v1/executions/{execution_id}/status/",
  "message": "File uploaded for processing"
}
```

### 3. Azure Function Processing

**Location**: `function_app/function_app.py` - `convert_pdf_to_docx()` function

**HTTP Trigger**: `POST /api/pdf/convert`

**Expected Payload**:
```json
{
  "execution_id": "uuid-string",
  "blob_name": "uploads/pdf/{uuid}.pdf"
}
```

**Process**:

#### 3.1 Update Status to Processing
```sql
UPDATE tool_executions 
SET status = 'processing', started_at = NOW()
WHERE id = execution_id
```

#### 3.2 Download PDF from Blob Storage
- Container: `uploads`
- Blob: `pdf/{execution_id}.pdf`
- Retrieve metadata for conversion parameters

#### 3.3 Convert PDF to DOCX
- Use `pdf2docx` library
- Apply page range if specified in metadata
- Create temporary files for input/output
- Perform conversion

#### 3.4 Upload DOCX to Blob Storage
- Container: `processed`
- Blob: `docx/{execution_id}.docx`
- Set metadata:
  - `execution_id`
  - `original_filename`
  - `output_filename`
  - `converted_at`

#### 3.5 Update Database with Success
```sql
UPDATE tool_executions 
SET status = 'completed',
    completed_at = NOW(),
    duration_seconds = duration,
    output_filename = filename,
    output_size = size,
    output_blob_path = 'processed/docx/{execution_id}.docx'
WHERE id = execution_id
```

#### 3.6 Error Handling
If any step fails:
```sql
UPDATE tool_executions 
SET status = 'failed',
    error_message = error,
    completed_at = NOW()
WHERE id = execution_id
```

**Logging**: Extremely verbose logging with sections:
- `=` Major section dividers (100 chars)
- `-` Subsection dividers (100 chars)
- 🚀 Process start
- 📥 Request parsing
- 💾 Database operations
- 🔐 Authentication
- ⬇️ Downloads
- 🔄 Conversion
- ⬆️ Uploads
- 🧹 Cleanup
- ✅ Success
- ❌ Errors
- ⚠️ Warnings

### 4. Status Checking (Django)

**Location**: `apps/api/v1/views.py` (or similar)

Users can check conversion status via:
```
GET /api/v1/executions/{execution_id}/status/
```

**Response**:
```json
{
  "executionId": "uuid-string",
  "status": "completed|processing|pending|failed",
  "inputFilename": "document.pdf",
  "outputFilename": "document.docx",
  "startedAt": "2025-12-07T10:00:00Z",
  "completedAt": "2025-12-07T10:01:30Z",
  "durationSeconds": 90.5,
  "errorMessage": null
}
```

## Database Schema

### ToolExecution Model Fields

**Original Fields**:
- `id` (UUID): Primary key
- `user`: Foreign key to User
- `tool_name`: "pdf-docx-converter"
- `status`: pending|processing|completed|failed
- `input_filename`, `output_filename`: File names
- `input_size`, `output_size`: File sizes in bytes
- `parameters`: JSON with conversion parameters
- `started_at`, `completed_at`: Timestamps
- `duration_seconds`: Processing duration
- `error_message`, `error_traceback`: Error details

**New Azure Functions Fields** (Migration: `0004_add_azure_function_tracking.py`):
- `azure_function_invoked` (Boolean): Whether Azure Function was triggered
- `function_execution_id` (String): Execution ID for tracking (indexed)
- `input_blob_path` (String): Path to input blob (`uploads/pdf/{uuid}.pdf`)
- `output_blob_path` (String): Path to output blob (`processed/docx/{uuid}.docx`)

## Configuration

### Django Settings

**File**: `magictoolbox/settings/base.py`

```python
# Enable Azure Functions for PDF conversion
USE_AZURE_FUNCTIONS_PDF_CONVERSION = config(
    "USE_AZURE_FUNCTIONS_PDF_CONVERSION", default=False, cast=bool
)

# Azure Function URL for PDF conversion
AZURE_FUNCTION_PDF_CONVERT_URL = config(
    "AZURE_FUNCTION_PDF_CONVERT_URL", 
    default="https://func-magictoolbox-{env}-{hash}.azurewebsites.net/api/pdf/convert"
)

# Azure Storage (for both local and production)
AZURE_STORAGE_CONNECTION_STRING = config("AZURE_STORAGE_CONNECTION_STRING", default="")
AZURE_STORAGE_ACCOUNT_NAME = config("AZURE_STORAGE_ACCOUNT_NAME", default="")
```

### Environment Variables

**Development** (`.env.development`):
```bash
USE_AZURE_FUNCTIONS_PDF_CONVERSION=true
AZURE_FUNCTION_PDF_CONVERT_URL=http://localhost:7071/api/pdf/convert
AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true  # Azurite
```

**Production** (Azure App Configuration / Key Vault):
```bash
USE_AZURE_FUNCTIONS_PDF_CONVERSION=true
AZURE_FUNCTION_PDF_CONVERT_URL=https://func-magictoolbox-prod-xyz.azurewebsites.net/api/pdf/convert
AZURE_STORAGE_ACCOUNT_NAME=stmagictoolboxprodxyz
# No connection string - use Managed Identity
```

### Azure Function Settings

**File**: `function_app/local.settings.json` (local development)

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_STORAGE_ACCOUNT_NAME": "devstoreaccount1",
    "DB_HOST": "localhost",
    "DB_NAME": "magictoolbox",
    "DB_USER": "postgres",
    "DB_PASSWORD": "your-password",
    "DB_PORT": "5432",
    "DB_SSLMODE": "disable"
  }
}
```

**Production** (Azure Portal or CLI):
- `AZURE_STORAGE_ACCOUNT_NAME`: Storage account name
- `DB_HOST`: PostgreSQL server hostname
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password (from Key Vault)
- Enable **Managed Identity** for storage and database access

## Blob Storage Containers

### Required Containers

1. **`uploads`**: Input files uploaded by users
   - Path pattern: `pdf/{execution_id}.pdf`
   - Access: Django (write), Azure Function (read)
   - Retention: Delete after successful conversion or 7 days

2. **`processed`**: Converted output files
   - Path pattern: `docx/{execution_id}.docx`
   - Access: Azure Function (write), Django (read), Users (read via signed URL)
   - Retention: 30 days or user-triggered deletion

## Error Handling

### Django Upload Errors

**Possible Issues**:
- Blob storage connection failure
- File size exceeds limit
- Invalid file format
- HTTP trigger failed

**Recovery**:
- Return error to user immediately
- No database record created
- No blob uploaded

### Azure Function Errors

**Possible Issues**:
- Blob not found
- PDF corruption
- Conversion failure (pdf2docx errors)
- Database update failure
- Upload failure

**Recovery**:
- Log detailed error information
- Update database with `status='failed'` and `error_message`
- Temporary files cleaned up automatically
- User can retry or contact support

## Monitoring and Troubleshooting

### Django Logs

Check Django application logs for:
- 📤 PDF upload process
- 🚀 Azure Function trigger
- ✅ Success confirmations
- ❌ Upload or trigger errors

### Azure Function Logs

Access via Azure Portal → Function App → Log stream or Application Insights

Look for:
- `=====` Section headers (100 chars)
- 🚀 Conversion start
- 💾 Database updates
- ⬇️ Download progress
- 🔄 Conversion progress
- ⬆️ Upload progress
- ✅ Success indicators
- ❌ Error details with full tracebacks

### Database Queries

**Check status of conversions**:
```sql
SELECT id, status, input_filename, started_at, completed_at, error_message
FROM tool_executions
WHERE tool_name = 'pdf-docx-converter'
ORDER BY created_at DESC
LIMIT 10;
```

**Find stuck conversions** (processing for >10 minutes):
```sql
SELECT id, status, input_filename, started_at
FROM tool_executions
WHERE tool_name = 'pdf-docx-converter'
  AND status = 'processing'
  AND started_at < NOW() - INTERVAL '10 minutes';
```

**Azure Functions tracking**:
```sql
SELECT id, status, azure_function_invoked, function_execution_id, 
       input_blob_path, output_blob_path
FROM tool_executions
WHERE azure_function_invoked = true
ORDER BY created_at DESC
LIMIT 10;
```

## Testing

### Local Testing

1. **Start Azurite** (local blob storage emulator):
   ```bash
   docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 \
     mcr.microsoft.com/azure-storage/azurite
   ```

2. **Start Django**:
   ```bash
   source .venv/bin/activate
   python manage.py runserver
   ```

3. **Start Azure Function**:
   ```bash
   cd function_app
   func start
   ```

4. **Upload a PDF**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/tools/pdf-docx-converter/convert/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@test.pdf"
   ```

5. **Check logs**:
   - Django console for upload logs
   - Function console for conversion logs
   - Database for status updates

### Production Testing

1. Deploy both Django and Azure Function
2. Verify environment variables are set
3. Test with small PDF first
4. Monitor Application Insights for errors
5. Check blob storage for uploaded/converted files
6. Verify database records updated correctly

## Performance Considerations

- **Cold Start**: First Function invocation may take 5-10 seconds
- **Conversion Time**: Depends on PDF size and complexity (typically 2-30 seconds per page)
- **Blob Storage**: Use appropriate access tiers (Hot for recent, Cool for archive)
- **Database**: Indexes on `status`, `function_execution_id`, and `user` for fast queries
- **Cleanup**: Implement scheduled job to delete old blobs and completed records

## Security

- **Authentication**: All endpoints require authentication
- **Managed Identity**: No storage keys in code or config (production)
- **Database**: SSL required, credentials in Key Vault
- **Blob Access**: Use SAS tokens for user downloads (not direct URLs)
- **Function Auth**: Consider adding function key authentication for production

## Future Enhancements

1. **Webhooks**: Notify users when conversion completes
2. **Batch Processing**: Parallel processing of multiple PDFs
3. **Progress Updates**: Real-time progress via WebSocket
4. **Retry Logic**: Automatic retry on transient failures
5. **Cost Optimization**: Archive old blobs to Cool or Archive tier
6. **Advanced Options**: OCR for scanned PDFs, custom formatting

---

**Last Updated**: 2025-12-07  
**Related Documentation**:
- `AZURE_DEPLOYMENT_README.md`
- `PDF_DOCX_INTEGRATION_GUIDE.md`
- `DEPLOYMENT_MONITORING.md`
