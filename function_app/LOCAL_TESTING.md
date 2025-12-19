# Local Testing Guide for Azure Functions

## Quick Start

### Start Local Environment
```bash
cd function_app
./start_local_env.sh
```

This will start:
- **Azurite** (Azure Storage Emulator) on ports 10000 (Blob), 10001 (Queue), 10002 (Table)
- **Azure Functions** on port 7071

### Stop Local Environment
```bash
cd function_app
./stop_local_env.sh
```

## Monitor Logs

### Azurite Logs
```bash
tail -f /tmp/azurite.log
```

### Azure Functions Logs
```bash
tail -f /tmp/azure-functions.log
```

## Testing the PDF to DOCX Conversion

### 1. Set Up Environment Variable
```bash
export AZURE_STORAGE_CONNECTION_STRING='DefaultEndpointsProtocol=http;AccountName=devstorageaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstorageaccount1;'
```

### 2. Upload a Test PDF
```bash
# Upload with required metadata
az storage blob upload \
  --container-name uploads \
  --file /path/to/test.pdf \
  --name pdf/test-001.pdf \
  --metadata execution_id=test-001 original_filename=test.pdf \
  --overwrite
```

**Required Metadata:**
- `execution_id`: Unique identifier for the conversion job
- `original_filename`: Original name of the PDF file

**Optional Metadata:**
- `start_page`: First page to convert (default: 0)
- `end_page`: Last page to convert (default: all pages)

### 3. Watch Conversion
```bash
# Monitor function logs for conversion activity
tail -f /tmp/azure-functions.log | grep -E "(PDF to DOCX|Executing|Conversion)"
```

### 4. Verify Output
```bash
# List converted files
az storage blob list --container-name processed --output table

# Download converted DOCX
az storage blob download \
  --container-name processed \
  --name docx/test-001.docx \
  --file output.docx

# Check metadata
az storage blob metadata show \
  --container-name processed \
  --name docx/test-001.docx
```

## Architecture Details

### Local vs Azure Configuration

The function code automatically detects the environment:

- **Local Development**: Uses connection string from `AzureWebJobsStorage` if it contains `127.0.0.1`
- **Azure Deployment**: Uses Managed Identity with `DefaultAzureCredential`

This ensures the same code works in both environments without modification.

### Storage Containers

- `uploads`: PDF files to be converted (trigger pattern: `uploads/pdf/{name}`)
- `processed`: Converted DOCX files (output pattern: `processed/docx/{execution_id}.docx`)
- `azure-webjobs-secrets`: Function runtime secrets
- `azure-webjobs-hosts`: Host coordination and blob receipts

### Blob Trigger Behavior

- The function polls the `uploads` container every ~2 seconds
- When a new blob matching `uploads/pdf/{name}` is detected, the function triggers
- Blob receipts prevent duplicate processing
- If `execution_id` metadata is missing, the function logs an error and skips processing

## Troubleshooting

### Function Not Starting
```bash
# Check if ports are already in use
lsof -i :7071 -i :10000 -i :10001 -i :10002

# Force kill all processes
pkill -9 -f "func start"
pkill -9 -f "azure_functions_worker"
pkill -9 -f "azurite"

# Restart
./start_local_env.sh
```

### Conversion Not Triggering
1. Ensure the PDF was uploaded to `uploads/pdf/` path (not just `uploads/`)
2. Verify `execution_id` metadata is present: `az storage blob metadata show --container-name uploads --name pdf/yourfile.pdf`
3. Check function logs for "No execution_id in blob metadata" errors
4. Verify Azurite is running: `curl http://127.0.0.1:10000/devstorageaccount1?comp=list`

### Output Not Appearing
1. Check function logs for errors: `tail -100 /tmp/azure-functions.log | grep -i error`
2. Verify the processed container exists: `az storage container show --name processed`
3. Look for "Using connection string for local development" in logs to confirm local mode

### PDF Conversion Fails
- The `pdf2docx` library may struggle with complex PDFs (many pages, complex layouts, scanned images)
- Check function logs for conversion errors
- Try with a simple, text-based PDF first

## Integration with Django

When testing the full Django → Azure Functions workflow:

1. Start the local environment: `./start_local_env.sh`
2. Start Django dev server: `python manage.py runserver`
3. Use the Django API to upload a PDF with `use_azure_functions=True`
4. Django will upload to Azurite with proper metadata
5. Function will detect, convert, and store the DOCX
6. Django API can poll status and retrieve the result

## Production Deployment

When deploying to Azure:

1. The same function code works without modification
2. Environment variables in Azure:
   - `AZURE_STORAGE_ACCOUNT_NAME`: Name of the storage account
   - `AzureWebJobsStorage`: Connection string (automatically set by Azure)
   - `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL connection details
3. Managed Identity is automatically used for blob storage access
4. No Azurite needed - uses real Azure Blob Storage

## Health Check

Test if the function is running:
```bash
curl http://localhost:7071/api/health
```

Expected response:
```json
{"status": "healthy", "function": "pdf-to-docx-converter"}
```
