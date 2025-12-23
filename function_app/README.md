# Azure Function App - PDF to DOCX Converter

This directory contains the Azure Function implementation for asynchronous PDF to DOCX conversion.

## 📁 Structure

```
function_app/
├── function_app.py           # Main function code (blob trigger + HTTP endpoint)
├── requirements.txt          # Python dependencies
├── host.json                # Function App configuration
├── .funcignore              # Files to exclude from deployment
└── local.settings.json.example  # Local development settings template
```

## 🚀 Quick Start

### Local Development

1. **Install Azure Functions Core Tools**:
   ```bash
   npm install -g azure-functions-core-tools@4
   ```

2. **Create local settings**:
   ```bash
   cp local.settings.json.example local.settings.json
   # Edit local.settings.json with your values
   ```

3. **Install Python dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run locally with Azurite (Storage Emulator)**:
   ```bash
   # Install Azurite
   npm install -g azurite
   
   # Start Azurite in a separate terminal
   azurite --silent --location ./azurite --debug ./azurite/debug.log
   
   # Start Function App
   func start
   ```

5. **Test locally**:
   ```bash
   # Test health endpoint
   curl http://localhost:7071/api/health
   
   # Upload test PDF to emulated storage
   az storage blob upload \
     --connection-string "UseDevelopmentStorage=true" \
     --container-name uploads \
     --name pdf/test.pdf \
     --file /path/to/test.pdf \
     --metadata execution_id=$(uuidgen) start_page=0 original_filename=test.pdf
   ```

### Deploy to Azure

1. **Using Azure Functions Core Tools**:
   ```bash
   func azure functionapp publish <your-function-app-name> --python
   ```

2. **Using Azure CLI**:
   ```bash
   cd function_app
   zip -r ../function_app.zip . -x "*.venv*" -x "*__pycache__*"
   
   az functionapp deployment source config-zip \
     --resource-group magictoolbox-demo-rg \
     --name <your-function-app-name> \
     --src ../function_app.zip
   ```

## 🔧 Configuration

### Environment Variables (Required in Azure)

Configure these in Azure Portal → Function App → Configuration:

| Variable | Description | Example |
|----------|-------------|---------|
| `AzureWebJobsStorage` | Storage for Functions runtime | Connection string |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | `magictoolboxdevst...` |
| `DB_HOST` | PostgreSQL hostname | `server.postgres.database.azure.com` |
| `DB_NAME` | Database name | `magictoolbox` |
| `DB_USER` | Database user | `admin_user` |
| `DB_PASSWORD` | Database password | `***` |
| `DB_PORT` | Database port | `5432` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights | `InstrumentationKey=...` |

### Function Configuration (host.json)

- **Timeout**: 10 minutes (suitable for large PDFs)
- **Retry Policy**: Exponential backoff, max 3 retries
- **Concurrency**: Auto-scales based on queue depth

## 📝 Function Details

### Blob Trigger: `pdf_to_docx_converter`

**Trigger Path**: `pdf-uploads/{name}`

**Input**: PDF file with metadata:
- `execution_id`: UUID for tracking
- `start_page`: First page to convert (optional)
- `end_page`: Last page to convert (optional)
- `original_filename`: Original PDF filename

**Process**:
1. Read PDF from blob storage
2. Update ToolExecution status to "processing"
3. Convert PDF to DOCX using pdf2docx
4. Upload DOCX to `pdf-processed/`
5. Update ToolExecution status to "completed"
6. On error: Update status to "failed" with error details

**Output**: DOCX file in `pdf-processed/{execution_id}.docx`

### HTTP Trigger: `http_trigger_test`

**Endpoint**: `GET /api/health`

**Purpose**: Health check for monitoring

**Response**:
```json
{
  "status": "healthy",
  "function": "pdf-to-docx-converter"
}
```

## 🧪 Testing

### Unit Tests (Local)

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run tests
pytest test_function_app.py
```

### Integration Tests (Azure)

```bash
# Upload test PDF via Django API
curl -X POST https://your-app.azurewebsites.net/api/v1/tools/pdf-docx-converter/convert/ \
  -F "file=@test.pdf"

# Get execution ID from response, then check status
curl https://your-app.azurewebsites.net/api/v1/tools/executions/{id}/status/

# Monitor function logs
az functionapp log tail \
  --resource-group magictoolbox-demo-rg \
  --name your-function-app-name
```

## 📊 Monitoring

### View Logs

```bash
# Live stream
func azure functionapp logstream <function-app-name>

# Or using Azure CLI
az functionapp log tail \
  --resource-group magictoolbox-demo-rg \
  --name <function-app-name>
```

### Application Insights

Navigate to Azure Portal → Function App → Application Insights:
- **Failures**: Track conversion errors
- **Performance**: Monitor execution duration
- **Live Metrics**: Real-time monitoring

Example KQL query:
```kusto
requests
| where name contains "pdf_to_docx_converter"
| summarize 
    count=count(),
    avg_duration=avg(duration),
    max_duration=max(duration)
  by bin(timestamp, 5m)
| render timechart
```

## 🔍 Troubleshooting

### Function Not Triggering

1. **Check blob trigger connection**:
   ```bash
   az functionapp config appsettings list \
     --resource-group magictoolbox-demo-rg \
     --name <function-app-name> \
     --query "[?name=='AzureWebJobsStorage'].value" -o tsv
   ```

2. **Verify RBAC permissions**: Function's Managed Identity needs "Storage Blob Data Contributor" role

3. **Check blob path**: Ensure PDFs are uploaded to `pdf-uploads/` (tool-specific container)

### Database Connection Errors

1. **Test connectivity**:
   ```python
   import psycopg2
   conn = psycopg2.connect(
       host="server.postgres.database.azure.com",
       database="magictoolbox",
       user="admin_user",
       password="***",
       port=5432,
       sslmode="require"
   )
   ```

2. **Check firewall**: Ensure Function App IP is allowed in PostgreSQL firewall rules

3. **Verify connection string**: Double-check environment variables

### Conversion Failures

1. **Check PDF validity**: Test with simple PDF first
2. **Review error logs**: Check Application Insights for detailed errors
3. **Increase timeout**: Large PDFs may need more than 10 minutes
4. **Memory issues**: Consider upgrading to Premium plan for larger files

## 📚 Dependencies

Key libraries:
- `azure-functions`: Azure Functions runtime
- `azure-identity`: Managed Identity authentication
- `azure-storage-blob`: Blob storage operations
- `psycopg2-binary`: PostgreSQL connectivity
- `pdf2docx`: PDF to DOCX conversion
- `PyMuPDF`: PDF parsing

See `requirements.txt` for full list with versions.

## 🔐 Security

- **Managed Identity**: No connection strings in code
- **SSL/TLS**: All connections encrypted
- **Secrets**: Stored in Azure Key Vault (optional)
- **RBAC**: Least privilege access model
- **Network**: Can be deployed in VNet for private networking

## 💡 Tips

1. **Cold Start**: First execution after idle period may take longer (~30s)
2. **Scaling**: Consumption plan auto-scales, but consider Premium plan for consistent workload
3. **Retries**: Automatic retry on transient failures (network issues, etc.)
4. **Monitoring**: Enable Application Insights for detailed telemetry
5. **Cost**: Within free tier for development (<1 million executions/month)

## 📖 Learn More

- [Azure Functions Python Developer Guide](https://docs.microsoft.com/azure/azure-functions/functions-reference-python)
- [Blob Storage Triggers](https://docs.microsoft.com/azure/azure-functions/functions-bindings-storage-blob-trigger)
- [Best Practices](https://docs.microsoft.com/azure/azure-functions/functions-best-practices)
- [pdf2docx Documentation](https://github.com/dothinking/pdf2docx)

---

**Status**: ✅ Ready for deployment  
**Last Updated**: December 1, 2025
