# Async File Processing - Gold Standard

**Last Updated**: December 11, 2025  
**Status**: ✅ Production Ready

## 📋 Overview

This document defines the **gold standard architecture** for asynchronous file processing tools in MagicToolbox. All file manipulation tools (conversion, transformation, processing) **MUST** follow this pattern for consistency, maintainability, and scalability.

---

## 🏗️ Architecture Pattern

### **Flow Diagram**

```
┌─────────────┐
│   User      │
│  Uploads    │
│   File      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  Django Web App                                     │
│  ─────────────────────────────────────────────────  │
│  1. Validate file (type, size, parameters)          │
│  2. Create ToolExecution record (status: pending)   │
│  3. Upload to Azure Blob Storage                    │
│  4. Trigger Azure Function via HTTP POST            │
│  5. Return execution_id to client                   │
└───────────────────┬─────────────────────────────────┘
                    │
       ┌────────────┴─────────────┐
       │                          │
       ▼                          ▼
┌─────────────┐          ┌─────────────┐
│   Client    │          │   Azure     │
│   Polls     │◄─────────│  Function   │
│  /status/   │          │             │
└─────────────┘          └──────┬──────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
        ┌──────────────────┐    ┌──────────────────┐
        │   PostgreSQL     │    │  Blob Storage    │
        │   Database       │    │  (processed/)    │
        │   (status)       │    │                  │
        └──────────────────┘    └──────────────────┘
```

---

## 🎯 Mandatory Components

### 1. **Django Tool Plugin**

**Location**: `apps/tools/plugins/{tool_name}.py`

**Required Methods**:
```python
class MyAsyncTool(BaseTool):
    # Metadata
    name = "my-tool-name"
    display_name = "My Tool Display Name"
    description = "Tool description"
    category = "category"  # document, video, image, etc.
    version = "1.0.0"
    icon = "bootstrap-icon-name"
    
    # File constraints
    allowed_input_types = [".ext1", ".ext2"]
    max_file_size = 100 * 1024 * 1024  # bytes
    
    def validate(self, input_file, parameters) -> Tuple[bool, Optional[str]]:
        """Validate file and parameters. Return (is_valid, error_message)"""
        pass
    
    def process(self, input_file, parameters, execution_id=None) -> Tuple[str, None]:
        """
        Upload file to blob storage for async processing.
        Returns (execution_id, None) to signal async mode.
        """
        pass
    
    def _get_blob_service_client(self) -> BlobServiceClient:
        """Get blob client with Azurite support for local dev"""
        pass
```

**Key Requirements**:
- ✅ Return `(execution_id, None)` from `process()` to signal async
- ✅ Upload to standardized blob path: `{container}/{category}/{execution_id}{ext}`
- ✅ Include metadata: `execution_id`, `original_filename`, `tool_name`, parameters
- ✅ Trigger Azure Function via HTTP POST after upload
- ✅ Support both local (Azurite) and Azure (Managed Identity) auth

---

### 2. **Azure Function Handler**

**Location**: `function_app/function_app.py`

**Required Endpoint Pattern**:
```python
@app.route(route="{category}/{action}", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def process_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    Expected JSON payload:
    {
        "execution_id": "uuid",
        "blob_name": "uploads/{category}/{uuid}.ext",
        "parameter1": "value1",  # Tool-specific parameters
        "parameter2": "value2"
    }
    """
    execution_id = None
    temp_input = None
    temp_output = None
    
    try:
        # 1. Parse request and validate
        req_body = req.get_json()
        execution_id = req_body.get('execution_id')
        blob_name = req_body.get('blob_name')
        
        # 2. Update database: status = 'processing'
        update_database_status(execution_id, 'processing')
        
        # 3. Download input file from blob storage
        blob_service = get_blob_service_client()
        temp_input = download_blob(blob_service, blob_name)
        
        # 4. Process file (convert, transform, etc.)
        temp_output = process_file_logic(temp_input, parameters)
        
        # 5. Upload output to processed container
        output_blob_name = f"{category}/{execution_id}_output{ext}"
        upload_blob(blob_service, temp_output, "processed", output_blob_name)
        
        # 6. Update database: status = 'completed'
        update_database_completion(execution_id, output_blob_name, file_size)
        
        # 7. Cleanup temp files
        cleanup_temp_files(temp_input, temp_output)
        
        return func.HttpResponse(
            body=json.dumps({"status": "success", "execution_id": execution_id}),
            status_code=200
        )
        
    except Exception as e:
        # Update database: status = 'failed'
        update_database_failure(execution_id, str(e))
        cleanup_temp_files(temp_input, temp_output)
        
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(e)}),
            status_code=500
        )
```

**Key Requirements**:
- ✅ Route naming: `/{category}/{action}` (e.g., `/pdf/convert`, `/video/rotate`)
- ✅ Always update database status: `pending` → `processing` → `completed`/`failed`
- ✅ Always cleanup temp files (in try/finally blocks)
- ✅ Comprehensive logging with emojis for easy scanning
- ✅ Timeout handling for long-running operations
- ✅ Proper error messages saved to database

---

### 3. **Database Model**

**Location**: `apps/tools/models.py`

**Required Fields**:
```python
class ToolExecution(UUIDModel, TimeStampedModel):
    # User & tool info
    user = ForeignKey(User)
    tool_name = CharField(max_length=100, db_index=True)
    
    # Status tracking
    status = CharField(choices=[pending, processing, completed, failed], db_index=True)
    
    # File info
    input_filename = CharField(max_length=255)
    output_filename = CharField(max_length=255, blank=True)
    input_size = BigIntegerField(default=0)
    output_size = BigIntegerField(default=0)
    
    # Blob storage paths
    input_blob_path = CharField(max_length=500, blank=True)
    output_blob_path = CharField(max_length=500, blank=True)
    
    # Timing
    started_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
    
    # Error handling
    error_message = TextField(blank=True)
    
    # Parameters
    parameters = JSONField(default=dict)
```

---

### 4. **Frontend Template**

**Location**: `templates/tools/{tool_name}.html`

**Required Sections**:

#### A. **File Upload Form**
```html
<div class="card shadow-sm">
  <div class="card-header bg-primary text-white">
    <h5><i class="bi bi-upload me-2"></i>Upload & Process</h5>
  </div>
  <div class="card-body">
    <form id="uploadForm" enctype="multipart/form-data">
      {% csrf_token %}
      <div class="mb-3">
        <label for="file" class="form-label">Select File</label>
        <input type="file" class="form-control" name="file" accept=".ext" required>
      </div>
      <!-- Tool-specific parameters -->
      <button type="submit" class="btn btn-primary btn-lg w-100">
        <i class="bi bi-arrow-repeat me-2"></i>Process File
      </button>
    </form>
  </div>
</div>
```

#### B. **Processing Status Section**
```html
<div id="statusSection" style="display: none;">
  <h5><i class="bi bi-hourglass-split me-2"></i>Processing Status</h5>
  <div class="card">
    <div class="card-body">
      <div id="statusList"></div>
      <div class="progress mt-3" style="height: 25px;">
        <div class="progress-bar progress-bar-striped progress-bar-animated" 
             id="progressBar" style="width: 0%">
          <span id="progressText">0%</span>
        </div>
      </div>
    </div>
  </div>
</div>
```

#### C. **History Section** (MANDATORY)
```html
<div class="card shadow-sm">
  <div class="card-header bg-info text-white">
    <div class="d-flex justify-content-between align-items-center">
      <h5><i class="bi bi-clock-history me-2"></i>Processing History</h5>
      <button class="btn btn-sm btn-light" id="refreshHistoryBtn">
        <i class="bi bi-arrow-clockwise"></i> Refresh
      </button>
    </div>
  </div>
  <div class="card-body">
    <div id="historyList">
      <div class="text-center text-muted">
        <i class="bi bi-hourglass-split fs-3"></i>
        <p>Loading history...</p>
      </div>
    </div>
  </div>
</div>
```

**Required JavaScript**:
```javascript
// Poll status every 2-3 seconds
async function checkStatus() {
  const response = await fetch(`/api/v1/executions/${executionId}/status/`);
  const data = await response.json();
  
  if (data.status === 'completed') {
    showDownloadButton(data.downloadUrl);
    stopPolling();
  } else if (data.status === 'failed') {
    showError(data.error);
    stopPolling();
  }
  // Continue polling for 'pending' or 'processing'
}

// Load history on page load
async function loadHistory() {
  const response = await fetch('/api/v1/executions/?tool_name={tool-name}&limit=10');
  const data = await response.json();
  renderHistoryList(data.results);
}
```

---

### 5. **API Endpoints**

**Required Endpoints**:

#### Upload & Process
```
POST /api/v1/tools/{tool-name}/convert/
Content-Type: multipart/form-data

Response:
{
  "executionId": "uuid",
  "status": "pending",
  "message": "File uploaded successfully"
}
```

#### Check Status
```
GET /api/v1/executions/{execution_id}/status/

Response:
{
  "executionId": "uuid",
  "status": "completed",  // pending, processing, completed, failed
  "downloadUrl": "/api/v1/executions/{id}/download/",
  "outputFilename": "output.ext",
  "error": null  // or error message if failed
}
```

#### Download File
```
GET /api/v1/executions/{execution_id}/download/

Response: Binary file stream with proper Content-Disposition header
```

#### History
```
GET /api/v1/executions/?tool_name={tool-name}&limit=10

Response:
{
  "results": [
    {
      "id": "uuid",
      "status": "completed",
      "inputFilename": "input.ext",
      "outputFilename": "output.ext",
      "createdAt": "2025-12-11T10:00:00Z",
      "downloadUrl": "/api/v1/executions/{id}/download/"
    }
  ]
}
```

---

## 🔧 Configuration Standards

### **Django Settings**

**Location**: `magictoolbox/settings/base.py`

```python
# Azure Functions Configuration
USE_AZURE_FUNCTIONS_{TOOL}_PROCESSING = config(
    "USE_AZURE_FUNCTIONS_{TOOL}_PROCESSING", 
    default=False, 
    cast=bool
)

AZURE_FUNCTION_{TOOL}_{ACTION}_URL = config(
    "AZURE_FUNCTION_{TOOL}_{ACTION}_URL",
    default=""
)

# Azure Storage Configuration
AZURE_STORAGE_CONNECTION_STRING = config("AZURE_STORAGE_CONNECTION_STRING", default="")
AZURE_STORAGE_ACCOUNT_NAME = config("AZURE_STORAGE_ACCOUNT_NAME", default="")
```

**Naming Convention**:
- Settings: `AZURE_FUNCTION_{TOOL}_{ACTION}_URL` (e.g., `AZURE_FUNCTION_PDF_CONVERT_URL`)
- Env vars: Same as setting names

---

### **Blob Storage Containers**

**Standard Container Names**:
```
uploads          # Input files organized by category
├── pdf/
├── video/
├── image/
└── document/

processed        # Output files organized by category
├── pdf/
├── video/
├── image/
└── document/

temp             # Temporary files (auto-cleanup after 24h)
```

**Blob Naming Convention**:
```
Input:  uploads/{category}/{execution_id}{original_ext}
Output: processed/{category}/{execution_id}{output_ext}

Examples:
  uploads/pdf/550e8400-e29b-41d4-a716-446655440000.pdf
  processed/pdf/550e8400-e29b-41d4-a716-446655440000.docx
  uploads/video/660e8400-e29b-41d4-a716-446655440000.mp4
  processed/video/660e8400-e29b-41d4-a716-446655440000.mp4
```

---

### **Function App Environment Variables**

**Required Variables**:
```bash
# Database connection (PostgreSQL)
DB_HOST=your-db-server.postgres.database.azure.com
DB_NAME=magictoolbox
DB_USER=admin_user
DB_PASSWORD=<secret>
DB_PORT=5432
DB_SSLMODE=require

# Azure Storage (Managed Identity in production)
AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount
# OR for local dev:
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;...
```

### **Django Environment Variables**

**Required Variables**:
```bash
# Single Azure Function base URL (shared by all tools)
AZURE_FUNCTION_BASE_URL=https://func-magictoolbox-prod-xyz.azurewebsites.net/api

# Optional: Enable/disable processing per tool
USE_AZURE_FUNCTIONS_PDF_CONVERSION=true

# Azure Storage (same as Function App)
AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount
# OR for local dev:
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;...
```

---

## 🧪 Testing Requirements

### **Unit Tests**

Test each component independently:

```python
def test_tool_validation():
    """Test file type and size validation"""
    pass

def test_tool_blob_upload():
    """Test blob upload with mocked BlobServiceClient"""
    pass

def test_function_processing():
    """Test Azure Function logic with mocked blob storage"""
    pass

def test_database_updates():
    """Test status transitions: pending → processing → completed"""
    pass
```

### **Integration Tests**

Test end-to-end with local Azurite:

```python
@pytest.mark.integration
def test_complete_workflow():
    """Test upload → process → download with Azurite"""
    # 1. Upload file
    # 2. Verify blob created
    # 3. Trigger function
    # 4. Wait for completion
    # 5. Download result
    # 6. Verify output
    pass
```

### **E2E Tests**

Test in staging environment with real Azure resources.

---

## 📊 Monitoring & Observability

### **Required Logging**

**Django**:
```python
self.logger.info(f"📤 Uploading {tool_name} file: {filename}")
self.logger.info(f"✅ File uploaded successfully: {blob_name}")
self.logger.error(f"❌ Upload failed: {error}")
```

**Azure Function**:
```python
logger.info("=" * 100)
logger.info(f"🚀 {TOOL} PROCESSING STARTED")
logger.info(f"   Execution ID: {execution_id}")
logger.info("=" * 100)

logger.info(f"📥 Downloading from blob storage")
logger.info(f"🔄 Processing file")
logger.info(f"📤 Uploading result")
logger.info(f"✅ Processing completed successfully")
```

### **Application Insights**

Track these metrics:
- Upload success/failure rate
- Processing time distribution
- File size distribution
- Error rates by tool
- Queue depth (pending jobs)

---

## 🚀 Deployment Standards

### **Bicep Infrastructure**

**Location**: `infra/modules/function_app.bicep`

**Required Resources**:
```bicep
// Function App (Flex Consumption)
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        {
          name: 'AZURE_STORAGE_ACCOUNT_NAME'
          value: storageAccountName
        }
        {
          name: 'DB_HOST'
          value: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/db-host/)'
        }
        // ... other settings from Key Vault
      ]
    }
  }
  
  identity: {
    type: 'SystemAssigned'  // Enable Managed Identity
  }
}

// Storage containers
resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for container in ['uploads', 'processed', 'temp']: {
  name: container
  properties: {
    publicAccess: 'None'
  }
}]
```

### **CI/CD Pipeline**

**GitHub Actions Workflow**:
```yaml
name: Deploy Function App

on:
  push:
    branches: [main]
    paths:
      - 'function_app/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd function_app
          pip install -r requirements.txt
      
      - name: Deploy to Azure
        uses: Azure/functions-action@v1
        with:
          app-name: ${{ secrets.FUNCTION_APP_NAME }}
          package: function_app
```

---

## ✅ Compliance Checklist

Before creating a new async tool, ensure:

- [ ] Tool class inherits from `BaseTool`
- [ ] `process()` returns `(execution_id, None)`
- [ ] File uploaded to standardized blob path
- [ ] Azure Function endpoint follows naming convention
- [ ] Database status properly updated at each stage
- [ ] Frontend has upload, status, and history sections
- [ ] API endpoints for status, download, and history
- [ ] Comprehensive error handling and logging
- [ ] Unit and integration tests added
- [ ] Bicep infrastructure updated
- [ ] Environment variables documented
- [ ] CI/CD pipeline configured

---

## 📚 Reference Implementation

**PDF to DOCX Converter** is the reference implementation.

**Files**:
- Plugin: `apps/tools/plugins/pdf_docx_converter.py`
- Function: `function_app/function_app.py` → `@app.route("pdf/convert")`
- Template: `templates/tools/pdf_docx_converter.html`
- Tests: `tests/test_pdf_docx_*.py`
- Infrastructure: `infra/modules/function_app.bicep`

**Video Rotation** follows the same pattern with tool-specific processing logic.

---

## 🎓 Best Practices

1. **Always use UUIDs for execution IDs** - Prevents collisions
2. **Always clean up temp files** - Use try/finally blocks
3. **Always timeout long operations** - Prevent zombie processes
4. **Always log with emojis** - Makes logs scannable
5. **Always test with Azurite locally** - Catch issues early
6. **Always use Managed Identity in production** - No secrets in code
7. **Always show history** - Users need to see past executions
8. **Always poll, never webhook** - Simpler, more reliable for client-side
9. **Always validate before upload** - Save blob storage costs
10. **Always document parameters** - Help future developers

---

## 🔄 Migration Guide

To migrate an existing synchronous tool to this async pattern:

1. Update `process()` method to upload to blob storage
2. Create Azure Function handler
3. Update frontend to poll status
4. Add history section to template
5. Update tests for async behavior
6. Deploy infrastructure changes
7. Update documentation

---

**End of Gold Standard Document**
