# PDF Batch Conversion with Azure Functions

This document describes the multiple PDF upload and conversion feature using Azure Functions integration.

## Overview

The PDF to DOCX converter now supports uploading multiple PDF files simultaneously with real-time status tracking for each file. All conversions are processed asynchronously using Azure Functions for optimal performance.

## Features

### Multiple File Upload
- Select one or more PDF files at once
- Visual file list showing selected files with sizes
- Individual file validation before upload

### Real-Time Status Tracking
- Live progress indicators for each file
- Status updates: Pending → Processing → Completed/Failed
- Overall progress bar showing completion percentage
- Automatic status polling every 2 seconds

### Batch Download
- Download individual converted files
- "Download All" button for batch downloads
- Files named based on original PDF names

## Architecture

### Frontend (Django Template)
**File**: `templates/tools/pdf_docx_converter.html`

Key Components:
- Multiple file input: `<input type="file" multiple>`
- File list display showing selected PDFs
- Dynamic status cards for each conversion
- Overall progress tracking
- JavaScript polling mechanism

### Backend API
**File**: `apps/tools/views.py`

Key Endpoints:
1. **Upload & Process**
   - `POST /api/v1/tools/pdf-docx-converter/convert/`
   - Accepts multiple files via `files[]` parameter
   - Returns execution IDs for tracking

2. **Batch Status Check**
   - `POST /api/v1/tools/executions/batch-status/`
   - Accepts list of execution IDs
   - Returns current status for all files

3. **Download Result**
   - `GET /api/v1/tools/executions/{execution_id}/download/`
   - Downloads converted DOCX file

### Tool Plugin
**File**: `apps/tools/plugins/pdf_docx_converter.py`

Features:
- `process_multiple()` method for batch processing
- Azure Functions-only mode (no synchronous processing)
- Unique execution ID generation for each file
- Blob storage upload with metadata

### Azure Function
**File**: `function_app/function_app.py`

Processing:
- Blob trigger on `uploads/pdf/{name}` pattern
- PDF to DOCX conversion using pdf2docx
- Output to `processed/docx/{execution_id}.docx`
- Status updates in PostgreSQL database

## User Workflow

### 1. Upload Files
```
User selects multiple PDFs → Files displayed in list → Click "Convert to DOCX"
```

### 2. Processing
```
Files uploaded to Azure Blob Storage
  → Azure Function triggered for each file
  → Conversion starts automatically
  → Status updated in database
```

### 3. Status Monitoring
```
Frontend polls batch-status endpoint every 2 seconds
  → Status cards update in real-time
  → Progress bars show conversion progress
  → Overall progress calculated
```

### 4. Download Results
```
Completed files show download button
  → Click individual download links
  → Or use "Download All" button
  → Files saved with original names + .docx extension
```

## API Request/Response Examples

### Upload Multiple Files
**Request:**
```http
POST /api/v1/tools/pdf-docx-converter/convert/
Content-Type: multipart/form-data

files[]: file1.pdf
files[]: file2.pdf
files[]: file3.pdf
start_page: (optional)
end_page: (optional)
```

**Response:**
```json
{
  "message": "3 files uploaded for processing",
  "executions": [
    {
      "executionId": "uuid-1",
      "filename": "file1.pdf",
      "status": "pending"
    },
    {
      "executionId": "uuid-2",
      "filename": "file2.pdf",
      "status": "pending"
    },
    {
      "executionId": "uuid-3",
      "filename": "file3.pdf",
      "status": "pending"
    }
  ],
  "batchStatusUrl": "/api/v1/tools/executions/batch-status/"
}
```

### Check Batch Status
**Request:**
```http
POST /api/v1/tools/executions/batch-status/
Content-Type: application/json

{
  "executionIds": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**Response:**
```json
{
  "executions": [
    {
      "executionId": "uuid-1",
      "status": "completed",
      "filename": "file1.pdf",
      "outputFilename": "file1.docx",
      "downloadUrl": "/api/v1/tools/executions/uuid-1/download/",
      "createdAt": "2025-12-01T20:00:00Z",
      "completedAt": "2025-12-01T20:00:25Z",
      "error": null
    },
    {
      "executionId": "uuid-2",
      "status": "processing",
      "filename": "file2.pdf",
      "outputFilename": null,
      "createdAt": "2025-12-01T20:00:00Z",
      "completedAt": null,
      "error": null
    },
    {
      "executionId": "uuid-3",
      "status": "failed",
      "filename": "file3.pdf",
      "outputFilename": null,
      "createdAt": "2025-12-01T20:00:00Z",
      "completedAt": "2025-12-01T20:00:30Z",
      "error": "PDF file is corrupted or password-protected"
    }
  ]
}
```

## Database Schema

### ToolExecution Model
```python
{
  "id": "uuid",  # Execution ID
  "tool_name": "pdf-docx-converter",
  "status": "pending|processing|completed|failed",
  "input_filename": "original.pdf",
  "output_filename": "converted.docx",
  "input_size": 1024000,
  "output_size": 2048000,
  "parameters": {"start_page": 0, "end_page": null},
  "created_at": "2025-12-01T20:00:00Z",
  "started_at": "2025-12-01T20:00:05Z",
  "completed_at": "2025-12-01T20:00:25Z",
  "duration_seconds": 20.0,
  "error_message": null,
  "user": null  # Optional, nullable for public access
}
```

## Status Polling Strategy

### Efficient Polling
- **Interval**: 2 seconds
- **Batch Requests**: Single API call for all execution IDs
- **Auto-Stop**: Polling stops when all files completed or failed
- **Error Handling**: Failed requests logged but don't stop polling

### UI Updates
```javascript
// Poll every 2 seconds
setInterval(checkBatchStatus, 2000);

// Update UI with latest status
updateStatusDisplay();

// Stop when complete
if (allCompleted || allFailed) {
  stopStatusPolling();
  showResults();
}
```

## Configuration

### Environment Variables
```bash
# Azure Storage (Local Development)
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;..."

# Azure Storage (Production)
AZURE_ACCOUNT_NAME="storageaccountname"
USE_MANAGED_IDENTITY=true

# Database
DATABASE_URL="postgresql://..."

# Processing Mode (Always Azure Functions for PDF)
USE_AZURE_FUNCTIONS_PDF_CONVERSION=true  # Not needed, always true
```

### Settings
```python
# settings/development.py or settings/production.py

# Azure Storage
AZURE_ACCOUNT_NAME = env("AZURE_ACCOUNT_NAME")

# Tool Configuration
TOOL_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB per PDF
TOOL_ALLOWED_EXTENSIONS = [".pdf"]

# Status Polling
STATUS_POLL_INTERVAL = 2000  # milliseconds (frontend)
```

## Performance Considerations

### Scalability
- **Parallel Processing**: Each file processed independently
- **Azure Functions**: Auto-scaling based on load
- **Blob Storage**: Handles concurrent uploads
- **Database**: Indexed queries for fast status checks

### Optimization
- **Batch Status API**: Single request for multiple files
- **Client-Side Polling**: Stops automatically when complete
- **Efficient Queries**: Database indexed on execution ID and status

### Limits
- **File Size**: 100MB per PDF
- **Concurrent Uploads**: Limited by browser (typically 6-8)
- **Processing Time**: 10-minute timeout per file
- **Blob Storage**: No practical limit on number of files

## Error Handling

### Upload Errors
- **Validation Failed**: File type or size rejected
- **Upload Failed**: Network error, retry recommended
- **Storage Full**: Unlikely with Azure Blob Storage

### Processing Errors
- **Conversion Failed**: PDF corrupted or unsupported format
- **Timeout**: File too large or complex (>10 minutes)
- **Azure Function Error**: Logged and returned to client

### Display Errors
- **Failed Status**: Red badge with error message
- **Partial Success**: Some files completed, others failed
- **Network Error**: Polling continues automatically

## Testing Workflow

### Local Testing
1. Start services:
   ```bash
   cd function_app
   ./start_local_env.sh
   ```

2. Start Django:
   ```bash
   cd ..
   python manage.py runserver 8001
   ```

3. Open browser: `http://localhost:8001/tools/pdf-docx-converter/`

4. Upload test PDFs and monitor status

### Monitoring
```bash
# Azure Functions logs
tail -f /tmp/azure-functions.log

# Azurite logs
tail -f /tmp/azurite.log

# Django logs
tail -f logs/django.log
```

### Test Cases
1. **Single File**: Upload one PDF, verify conversion
2. **Multiple Files**: Upload 3-5 PDFs, verify all convert
3. **Mixed Sizes**: Upload small and large PDFs
4. **Error Handling**: Upload invalid file, verify error shown
5. **Download All**: Verify batch download works

## Production Deployment

### Azure Resources Required
- Azure Container Apps (Django app)
- Azure Functions (PDF conversion)
- Azure Storage Account (uploads + processed)
- Azure Database for PostgreSQL (status tracking)
- Azure Cache for Redis (optional, for sessions)

### Deployment Steps
1. Deploy infrastructure with Bicep templates
2. Configure Managed Identity for storage access
3. Deploy Django container
4. Deploy Azure Function
5. Test end-to-end workflow

### Monitoring
- Application Insights for telemetry
- Azure Monitor for resource health
- Custom metrics for conversion success rate

## Future Enhancements

### Potential Improvements
- **Progress Percentage**: Real-time conversion progress (0-100%)
- **ZIP Download**: Package all converted files into ZIP
- **Queue Management**: Show queue position for pending files
- **Cancellation**: Allow users to cancel pending conversions
- **History**: Show past conversion jobs
- **Notifications**: Email/webhook when batch complete

### Advanced Features
- **OCR Support**: Handle scanned PDFs with text recognition
- **Batch Editing**: Apply different parameters to different files
- **Scheduled Conversions**: Queue conversions for later processing
- **API Integration**: Programmatic access for automation

---

**Last Updated**: December 1, 2025
**Version**: 1.0.0
