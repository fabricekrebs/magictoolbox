# Async File Processing - Gold Standard

**Last Updated**: December 23, 2025

**Last Updated**: December 12, 2025  
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
- ✅ Upload to standardized blob path: `{category}-uploads/{execution_id}{ext}`
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

### 4. **Frontend Template Structure** (MANDATORY)

**Location**: `templates/tools/{tool_name}.html`

**Layout Pattern**: Two-column layout with upload/status on the left and history sidebar on the right.

#### **Complete Template Structure**:

```html
{% extends 'base.html' %}
{% load static crispy_forms_tags %}

{% block title %}{{ tool.display_name }} - MagicToolbox{% endblock %}

{% block content %}
<div class="container-fluid py-5">
  <!-- Tool Header -->
  <div class="row mb-4">
    <div class="col-12">
      <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
          <li class="breadcrumb-item"><a href="{% url 'core:home' %}">Home</a></li>
          <li class="breadcrumb-item"><a href="{% url 'tools:tool_list' %}">Tools</a></li>
          <li class="breadcrumb-item active">{{ tool.display_name }}</li>
        </ol>
      </nav>
      <h1 class="display-5 fw-bold mb-2">
        <i class="bi bi-{icon} text-primary me-2"></i>
        {{ tool.display_name }}
      </h1>
      <p class="lead text-muted">{{ tool.description }}</p>
    </div>
  </div>

  <div class="row">
    <!-- LEFT COLUMN: Upload & Processing Status (8 columns) -->
    <div class="col-lg-8">
      
      <!-- A. File Upload Form (MANDATORY) -->
      <div class="card shadow-sm mb-4">
        <div class="card-header bg-primary text-white">
          <h5 class="mb-0">
            <i class="bi bi-upload me-2"></i>Upload & Process
          </h5>
        </div>
        <div class="card-body">
          <form id="uploadForm" enctype="multipart/form-data">
            {% csrf_token %}
            
            <!-- File Input -->
            <div class="mb-3">
              <label for="file" class="form-label">Select File</label>
              <input type="file" 
                     class="form-control" 
                     id="file" 
                     name="file" 
                     accept=".{extensions}" 
                     required>
              <div class="form-text">
                <i class="bi bi-info-circle me-1"></i>
                Supported formats: {formats}. Max size: {max_size}MB
              </div>
            </div>

            <!-- Tool-specific Parameters (if any) -->
            <!-- Example: rotation angle, quality settings, etc. -->
            
            <!-- Submit Button -->
            <div class="d-grid gap-2">
              <button type="submit" class="btn btn-primary btn-lg" id="submitBtn">
                <i class="bi bi-arrow-repeat me-2"></i>Process File
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- B. Processing Status Section (MANDATORY) -->
      <div id="statusSection" class="card shadow-sm mb-4" style="display: none;">
        <div class="card-header bg-info text-white">
          <h5 class="mb-0">
            <i class="bi bi-hourglass-split me-2"></i>Processing Status
          </h5>
        </div>
        <div class="card-body">
          <!-- Status Messages -->
          <div id="statusMessages" class="mb-3"></div>
          
          <!-- Progress Bar -->
          <div class="progress mb-3" style="height: 30px;">
            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                 id="progressBar" 
                 role="progressbar" 
                 style="width: 0%">
              <span id="progressText" class="fw-bold">Initializing...</span>
            </div>
          </div>
          
          <!-- Download Button (shown on completion) -->
          <div id="downloadSection" style="display: none;">
            <div class="alert alert-success">
              <i class="bi bi-check-circle-fill me-2"></i>
              Processing completed successfully!
            </div>
            <div class="d-grid gap-2">
              <a href="#" id="downloadBtn" class="btn btn-success btn-lg">
                <i class="bi bi-download me-2"></i>Download Result
              </a>
            </div>
          </div>
          
          <!-- Error Display -->
          <div id="errorSection" class="alert alert-danger" style="display: none;">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            <span id="errorMessage"></span>
          </div>
        </div>
      </div>

      <!-- C. Usage Instructions (Optional but recommended) -->
      <div class="card shadow-sm">
        <div class="card-header">
          <h5 class="mb-0">
            <i class="bi bi-info-circle me-2"></i>How to Use
          </h5>
        </div>
        <div class="card-body">
          <ol class="mb-0">
            <li>Select your file using the upload form</li>
            <li>Configure any tool-specific parameters (if applicable)</li>
            <li>Click "Process File" to start conversion</li>
            <li>Monitor the processing status in real-time</li>
            <li>Download the result when complete</li>
            <li>View your processing history in the sidebar →</li>
          </ol>
        </div>
      </div>
    </div>

    <!-- RIGHT COLUMN: Processing History Sidebar (4 columns) - MANDATORY -->
    <div class="col-lg-4">
      <div class="card shadow-sm sticky-top" style="top: 20px;">
        <div class="card-header bg-secondary text-white">
          <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0">
              <i class="bi bi-clock-history me-2"></i>History
            </h5>
            <button class="btn btn-sm btn-light" id="refreshHistoryBtn" title="Refresh">
              <i class="bi bi-arrow-clockwise"></i>
            </button>
          </div>
        </div>
        <div class="card-body p-0">
          <!-- History List -->
          <div id="historyList" style="max-height: 70vh; overflow-y: auto;">
            <!-- Loading State -->
            <div id="historyLoading" class="text-center p-4">
              <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
              </div>
              <p class="text-muted mt-2 mb-0">Loading history...</p>
            </div>
            
            <!-- Empty State -->
            <div id="historyEmpty" class="text-center p-4" style="display: none;">
              <i class="bi bi-inbox fs-1 text-muted"></i>
              <p class="text-muted mb-0">No processing history yet</p>
            </div>
            
            <!-- History Items (populated via JavaScript) -->
            <div id="historyItems"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Delete Confirmation Modal -->
<div class="modal fade" id="deleteModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Confirm Delete</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        Are you sure you want to delete this item from history?
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-danger" id="confirmDeleteBtn">Delete</button>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

---

#### **Required JavaScript Implementation**:

**Location**: Embedded in template or separate file `static/js/tools/{tool_name}.js`

```javascript
// ============================================================================
// GLOBAL STATE
// ============================================================================
let currentExecutionId = null;
let statusCheckInterval = null;
const POLL_INTERVAL = 2500; // 2.5 seconds

// ============================================================================
// INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
  initializeUploadForm();
  loadHistory();
  setupEventListeners();
});

function setupEventListeners() {
  // Refresh history button
  document.getElementById('refreshHistoryBtn')?.addEventListener('click', () => {
    loadHistory();
  });
}

// ============================================================================
// UPLOAD & PROCESSING
// ============================================================================
function initializeUploadForm() {
  const form = document.getElementById('uploadForm');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(form);
    const submitBtn = document.getElementById('submitBtn');
    
    // Disable button during upload
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
    
    try {
      const response = await fetch('/api/v1/tools/{tool-name}/convert/', {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': getCsrfToken()
        }
      });
      
      const data = await response.json();
      
      if (response.ok) {
        currentExecutionId = data.executionId;
        showStatusSection();
        startStatusPolling();
        form.reset();
      } else {
        showError(data.error || 'Upload failed');
      }
    } catch (error) {
      showError('Network error. Please try again.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="bi bi-arrow-repeat me-2"></i>Process File';
    }
  });
}

// ============================================================================
// STATUS POLLING
// ============================================================================
function startStatusPolling() {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
  }
  
  // Check immediately
  checkStatus();
  
  // Then poll every 2.5 seconds
  statusCheckInterval = setInterval(checkStatus, POLL_INTERVAL);
}

async function checkStatus() {
  if (!currentExecutionId) return;
  
  try {
    const response = await fetch(`/api/v1/executions/${currentExecutionId}/status/`);
    const data = await response.json();
    
    updateProgressBar(data.status);
    
    if (data.status === 'completed') {
      showDownloadButton(data.downloadUrl, data.outputFilename);
      stopStatusPolling();
      loadHistory(); // Refresh history
    } else if (data.status === 'failed') {
      showError(data.error || 'Processing failed');
      stopStatusPolling();
      loadHistory(); // Refresh history
    }
  } catch (error) {
    console.error('Status check failed:', error);
  }
}

function stopStatusPolling() {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
    statusCheckInterval = null;
  }
}

function updateProgressBar(status) {
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  
  const statusMap = {
    'pending': { width: '25%', text: 'Pending...', class: 'bg-info' },
    'processing': { width: '50%', text: 'Processing...', class: 'bg-primary' },
    'completed': { width: '100%', text: 'Completed!', class: 'bg-success' },
    'failed': { width: '100%', text: 'Failed', class: 'bg-danger' }
  };
  
  const config = statusMap[status] || statusMap['pending'];
  progressBar.style.width = config.width;
  progressBar.className = `progress-bar progress-bar-striped ${config.class}`;
  if (status !== 'processing') {
    progressBar.classList.remove('progress-bar-animated');
  }
  progressText.textContent = config.text;
}

function showStatusSection() {
  document.getElementById('statusSection').style.display = 'block';
  document.getElementById('downloadSection').style.display = 'none';
  document.getElementById('errorSection').style.display = 'none';
  updateProgressBar('pending');
}

function showDownloadButton(url, filename) {
  const downloadSection = document.getElementById('downloadSection');
  const downloadBtn = document.getElementById('downloadBtn');
  
  downloadBtn.href = url;
  downloadBtn.download = filename || 'result';
  downloadSection.style.display = 'block';
}

function showError(message) {
  const errorSection = document.getElementById('errorSection');
  const errorMessage = document.getElementById('errorMessage');
  
  errorMessage.textContent = message;
  errorSection.style.display = 'block';
}

// ============================================================================
// HISTORY MANAGEMENT (MANDATORY)
// ============================================================================
async function loadHistory() {
  const historyLoading = document.getElementById('historyLoading');
  const historyEmpty = document.getElementById('historyEmpty');
  const historyItems = document.getElementById('historyItems');
  
  historyLoading.style.display = 'block';
  historyEmpty.style.display = 'none';
  historyItems.innerHTML = '';
  
  try {
    const response = await fetch('/api/v1/executions/?tool_name={tool-name}&limit=10');
    const data = await response.json();
    
    historyLoading.style.display = 'none';
    
    if (data.results && data.results.length > 0) {
      renderHistoryItems(data.results);
    } else {
      historyEmpty.style.display = 'block';
    }
  } catch (error) {
    console.error('Failed to load history:', error);
    historyLoading.style.display = 'none';
    historyItems.innerHTML = `
      <div class="alert alert-danger m-3">
        Failed to load history. Please try again.
      </div>
    `;
  }
}

function renderHistoryItems(items) {
  const historyItems = document.getElementById('historyItems');
  
  historyItems.innerHTML = items.map(item => {
    const statusBadge = getStatusBadge(item.status);
    const timeAgo = formatTimeAgo(item.createdAt);
    const canDownload = item.status === 'completed';
    
    return `
      <div class="border-bottom p-3 history-item" data-id="${item.id}">
        <!-- Status & Time -->
        <div class="d-flex justify-content-between align-items-start mb-2">
          ${statusBadge}
          <small class="text-muted">${timeAgo}</small>
        </div>
        
        <!-- Filename -->
        <div class="mb-2">
          <small class="text-muted d-block">Input:</small>
          <div class="text-truncate" title="${item.inputFilename}">
            <i class="bi bi-file-earmark me-1"></i>
            <strong>${item.inputFilename}</strong>
          </div>
        </div>
        
        ${item.outputFilename ? `
          <div class="mb-2">
            <small class="text-muted d-block">Output:</small>
            <div class="text-truncate" title="${item.outputFilename}">
              <i class="bi bi-file-earmark-check me-1"></i>
              ${item.outputFilename}
            </div>
          </div>
        ` : ''}
        
        <!-- Action Buttons -->
        <div class="btn-group w-100 mt-2" role="group">
          ${canDownload ? `
            <a href="${item.downloadUrl}" 
               class="btn btn-sm btn-outline-success" 
               download="${item.outputFilename}"
               title="Download">
              <i class="bi bi-download"></i>
            </a>
          ` : `
            <button class="btn btn-sm btn-outline-secondary" disabled>
              <i class="bi bi-download"></i>
            </button>
          `}
          <button class="btn btn-sm btn-outline-danger" 
                  onclick="deleteHistoryItem('${item.id}')"
                  title="Delete">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function getStatusBadge(status) {
  const badges = {
    'pending': '<span class="badge bg-info"><i class="bi bi-clock me-1"></i>Pending</span>',
    'processing': '<span class="badge bg-primary"><i class="bi bi-arrow-repeat me-1"></i>Processing</span>',
    'completed': '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Completed</span>',
    'failed': '<span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>Failed</span>'
  };
  return badges[status] || badges['pending'];
}

function formatTimeAgo(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return date.toLocaleDateString();
}

async function deleteHistoryItem(executionId) {
  const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
  modal.show();
  
  document.getElementById('confirmDeleteBtn').onclick = async () => {
    try {
      const response = await fetch(`/api/v1/executions/${executionId}/`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': getCsrfToken()
        }
      });
      
      if (response.ok) {
        modal.hide();
        loadHistory(); // Refresh history
      } else {
        alert('Failed to delete item');
      }
    } catch (error) {
      alert('Network error. Please try again.');
    }
  };
}

// ============================================================================
// UTILITIES
// ============================================================================
function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}
```

---

#### **CSS Styling Requirements**:

```css
/* History sidebar styling */
.history-item {
  transition: background-color 0.2s;
}

.history-item:hover {
  background-color: #f8f9fa;
}

/* Sticky sidebar on desktop */
@media (min-width: 992px) {
  .sticky-top {
    position: sticky;
    top: 20px;
    z-index: 1020;
  }
}

/* Mobile responsive adjustments */
@media (max-width: 991px) {
  .col-lg-8, .col-lg-4 {
    padding-left: 15px;
    padding-right: 15px;
  }
  
  /* Stack history below upload on mobile */
  .row > .col-lg-4 {
    order: 2;
    margin-top: 2rem;
  }
}
```

---

### 5. **API Endpoints** (MANDATORY)

**All Required Endpoints**:

#### A. Upload & Convert File
```
POST /api/v1/tools/{tool-name}/convert/
Content-Type: multipart/form-data

Request Body:
- file: (binary)
- parameter1: value (if applicable)
- parameter2: value (if applicable)

Response (201 Created):
{
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "File uploaded successfully"
}

Response (400 Bad Request):
{
  "error": "Invalid file type",
  "details": "Only .pdf files are allowed"
}
```

#### B. Check Processing Status
```
GET /api/v1/executions/{execution_id}/status/

Response (200 OK):
{
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",  // pending | processing | completed | failed
  "inputFilename": "document.pdf",
  "outputFilename": "document.docx",
  "downloadUrl": "/api/v1/executions/550e8400-e29b-41d4-a716-446655440000/download/",
  "createdAt": "2025-12-11T10:00:00Z",
  "completedAt": "2025-12-11T10:02:30Z",
  "error": null
}

Response (404 Not Found):
{
  "error": "Execution not found"
}
```

#### C. Download Processed File
```
GET /api/v1/executions/{execution_id}/download/

Response (200 OK):
- Content-Type: application/octet-stream (or specific MIME type)
- Content-Disposition: attachment; filename="output.ext"
- Binary file stream

Response (404 Not Found):
{
  "error": "File not found or not ready"
}

Response (410 Gone):
{
  "error": "File expired or deleted"
}
```

#### D. Get History (with pagination)
```
GET /api/v1/executions/?tool_name={tool-name}&limit=10&offset=0

Query Parameters:
- tool_name: Filter by specific tool (required)
- limit: Number of items per page (default: 10, max: 50)
- offset: Pagination offset (default: 0)
- status: Filter by status (optional: pending, processing, completed, failed)

Response (200 OK):
{
  "count": 42,
  "next": "/api/v1/executions/?tool_name=pdf-converter&limit=10&offset=10",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "inputFilename": "document.pdf",
      "outputFilename": "document.docx",
      "inputSize": 1048576,
      "outputSize": 524288,
      "createdAt": "2025-12-11T10:00:00Z",
      "completedAt": "2025-12-11T10:02:30Z",
      "downloadUrl": "/api/v1/executions/550e8400-e29b-41d4-a716-446655440000/download/",
      "parameters": {
        "start_page": 0,
        "end_page": 10
      }
    }
  ]
}
```

#### E. Delete History Item (MANDATORY)
```
DELETE /api/v1/executions/{execution_id}/

Response (204 No Content):
(Empty body - successful deletion)

Response (404 Not Found):
{
  "error": "Execution not found"
}

Response (403 Forbidden):
{
  "error": "You don't have permission to delete this item"
}

Note: This should also delete associated blob files from storage
```

#### F. Bulk Delete (Optional but recommended)
```
POST /api/v1/executions/bulk-delete/
Content-Type: application/json

Request Body:
{
  "execution_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ]
}

Response (200 OK):
{
  "deleted": 2,
  "failed": 0,
  "errors": []
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

**Standard Container Names** (Tool-Specific Pattern):
```
{tool}-uploads      # Input files for specific tool
├── pdf-uploads/
├── video-uploads/
├── image-uploads/
├── gpx-uploads/
└── ocr-uploads/

{tool}-processed    # Output files from specific tool
├── pdf-processed/
├── video-processed/
├── image-processed/
├── gpx-processed/
└── ocr-processed/

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

// Storage containers (tool-specific pattern)
var toolCategories = ['pdf', 'video', 'image', 'gpx', 'ocr']
resource uploadContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for category in toolCategories: {
  name: '${category}-uploads'
  properties: {
    publicAccess: 'None'
  }
}]
resource processedContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for category in toolCategories: {
  name: '${category}-processed'
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

Before creating a new async tool, ensure all requirements are met:

### **Backend Requirements**
- [ ] Tool class inherits from `BaseTool` in `apps/tools/plugins/{tool_name}.py`
- [ ] `process()` returns `(execution_id, None)` to signal async processing
- [ ] File uploaded to standardized blob path: `uploads/{category}/{execution_id}{ext}`
- [ ] Azure Function endpoint follows naming: `/{category}/{action}` (e.g., `/pdf/convert`)
- [ ] Database `ToolExecution` record created with status tracking
- [ ] Status transitions: `pending` → `processing` → `completed`/`failed`
- [ ] Comprehensive logging with emojis (🚀, ✅, ❌, ⚠️, 📝, 🔐)
- [ ] Error handling in try/except with proper cleanup
- [ ] Support both Azurite (local) and Azure (Managed Identity) authentication

### **Frontend Requirements (MANDATORY)**
- [ ] **Two-column layout**: Upload/status on left (8 cols), history on right (4 cols)
- [ ] **Upload section**: File input, validation, parameters, submit button
- [ ] **Status section**: Progress bar, real-time status updates, download button
- [ ] **History sidebar**: Right-aligned, sticky on desktop, shows last 10 items
- [ ] **History features**: Download, re-download, and delete actions for each item
- [ ] **Status polling**: Every 2-3 seconds until completion or failure
- [ ] **Responsive design**: History moves below upload on mobile
- [ ] **Loading states**: Spinners for upload, status check, and history loading
- [ ] **Empty states**: User-friendly message when history is empty
- [ ] **Error handling**: Display errors prominently with retry options
- [ ] **Time display**: Human-readable time ago (e.g., "2m ago", "1h ago")
- [ ] **Status badges**: Color-coded badges (pending=blue, processing=primary, completed=green, failed=red)
- [ ] **Delete confirmation**: Modal dialog before deleting history items
- [ ] **Auto-refresh history**: After upload completion or item deletion

### **API Requirements**
- [ ] `POST /api/v1/tools/{tool-name}/convert/` - Upload & convert
- [ ] `GET /api/v1/executions/{id}/status/` - Check status
- [ ] `GET /api/v1/executions/{id}/download/` - Download result
- [ ] `GET /api/v1/executions/?tool_name={name}&limit=10` - Get history with pagination
- [ ] `DELETE /api/v1/executions/{id}/` - Delete history item (with blob cleanup)
- [ ] Proper HTTP status codes (200, 201, 400, 404, 410, etc.)
- [ ] JSON responses follow camelCase convention
- [ ] CORS headers configured for API endpoints

### **Azure Function Requirements**
- [ ] Function route matches Django expectation: `/{category}/{action}`
- [ ] Database status updates: `processing` on start, `completed`/`failed` on finish
- [ ] Download from `{category}-uploads` container, process, upload to `{category}-processed` container
- [ ] Temp file cleanup in try/finally blocks
- [ ] Timeout handling (max 5 minutes for HTTP-triggered functions)
- [ ] Comprehensive logging for debugging
- [ ] Support both connection string (local) and Managed Identity (Azure)

### **Infrastructure & Deployment**
- [ ] Bicep templates updated with new function endpoint
- [ ] Environment variables added to `.env.example`
- [ ] `AZURE_FUNCTION_BASE_URL` configured in Django Container App
- [ ] Blob storage containers configured: `{tool}-uploads`, `{tool}-processed` (tool-specific)
- [ ] GitHub Actions workflow updated (if needed)
- [ ] Database migrations created and applied

### **Testing & Documentation**
- [ ] Unit tests for tool plugin logic
- [ ] Integration tests with mocked Azure services
- [ ] E2E tests with real Azure resources (staging)
- [ ] Test coverage ≥ 80% for new code
- [ ] Tool added to `.github/copilot-instructions.md` if special notes needed
- [ ] README or tool-specific documentation created

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
