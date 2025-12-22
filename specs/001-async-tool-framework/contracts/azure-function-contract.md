# Azure Function Contract

**Feature**: Async Tool Framework & Plugin System  
**Version**: 1.0.0  
**Date**: 2025-12-21

## Overview

This document defines the contract between Django application and Azure Functions for asynchronous file processing. All async tools must trigger Azure Functions following this standard interface.

---

## Endpoint Pattern

### URL Structure

```
{AZURE_FUNCTION_BASE_URL}/{category}/{action}
```

**Examples**:
- `https://magictoolbox-functions.azurewebsites.net/document/convert`
- `https://magictoolbox-functions.azurewebsites.net/video/rotate`
- `https://magictoolbox-functions.azurewebsites.net/image/resize`
- `http://localhost:7071/pdf/convert` (local development)

**Path Parameters**:
- `{category}`: Tool category (document, video, image, gps, text)
- `{action}`: Processing action (convert, rotate, resize, analyze, etc.)

---

## Request Specification

### HTTP Method
`POST`

### Headers
```http
Content-Type: application/json
```

### Request Body Schema

```json
{
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "toolName": "pdf-docx-converter",
  "inputBlobPath": "uploads/document/550e8400-e29b-41d4-a716-446655440000.pdf",
  "outputContainer": "processed",
  "parameters": {
    "preserveLayout": true,
    "includeImages": true
  }
}
```

**Field Definitions**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `executionId` | UUID string | Yes | Unique execution identifier | `"550e8400-e29b-41d4-a716-446655440000"` |
| `toolName` | String | Yes | Tool name for logging/tracking | `"pdf-docx-converter"` |
| `inputBlobPath` | String | Yes | Full blob path to input file | `"uploads/document/{uuid}.pdf"` |
| `outputContainer` | String | Yes | Target container for output | `"processed"` (always) |
| `parameters` | Object | No | Tool-specific processing parameters | Varies by tool |

**Example Requests**:

**PDF to DOCX Conversion**:
```json
{
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "toolName": "pdf-docx-converter",
  "inputBlobPath": "uploads/document/550e8400-e29b-41d4-a716-446655440000.pdf",
  "outputContainer": "processed",
  "parameters": {
    "preserveLayout": true
  }
}
```

**Video Rotation**:
```json
{
  "executionId": "123e4567-e89b-12d3-a456-426614174000",
  "toolName": "video-rotation",
  "inputBlobPath": "uploads/video/123e4567-e89b-12d3-a456-426614174000.mp4",
  "outputContainer": "processed",
  "parameters": {
    "rotation": 90
  }
}
```

---

## Response Specification

### Success Response (200 OK)

```json
{
  "status": "success",
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "outputBlobPath": "processed/document/550e8400-e29b-41d4-a716-446655440000.docx",
  "processingTimeSeconds": 83.5,
  "metadata": {
    "inputSizeBytes": 2458624,
    "outputSizeBytes": 1834567,
    "pageCount": 15
  }
}
```

**Field Definitions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | String | Yes | Always `"success"` for 200 responses |
| `executionId` | UUID string | Yes | Echo of request execution ID |
| `outputBlobPath` | String | Yes | Full path to processed file in blob storage |
| `processingTimeSeconds` | Number | Yes | Total processing time |
| `metadata` | Object | No | Tool-specific output metadata |

### Error Response (400 Bad Request)

```json
{
  "status": "error",
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "error": "ValidationError",
  "message": "Input file is corrupted or not a valid PDF",
  "details": {
    "errorCode": "INVALID_PDF_FORMAT",
    "technicalDetails": "PyPDF2 raised PdfReadError: EOF marker not found"
  }
}
```

### Error Response (500 Internal Server Error)

```json
{
  "status": "error",
  "executionId": "550e8400-e29b-41d4-a716-446655440000",
  "error": "ProcessingError",
  "message": "An unexpected error occurred during processing",
  "details": {
    "errorCode": "INTERNAL_ERROR",
    "technicalDetails": "Exception: Out of memory during conversion"
  }
}
```

**Error Field Definitions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | String | Yes | Always `"error"` for error responses |
| `executionId` | UUID string | Yes | Echo of request execution ID |
| `error` | String | Yes | Error category (ValidationError, ProcessingError, TimeoutError) |
| `message` | String | Yes | User-friendly error message |
| `details` | Object | Yes | Technical error details for logging |

---

## Function Implementation Pattern

### Python Azure Function Template

```python
import azure.functions as func
import logging
import json
import os
import tempfile
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

app = func.FunctionApp()

@app.route(route="{category}/{action}", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def process_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generic file processing handler for async tools.
    
    Route pattern: /{category}/{action}
    Example: /document/convert, /video/rotate
    """
    # Extract route parameters
    category = req.route_params.get('category')
    action = req.route_params.get('action')
    
    # Parse request body
    try:
        req_body = req.get_json()
        execution_id = req_body['executionId']
        tool_name = req_body['toolName']
        input_blob_path = req_body['inputBlobPath']
        output_container = req_body['outputContainer']
        parameters = req_body.get('parameters', {})
    except (ValueError, KeyError) as e:
        return func.HttpResponse(
            json.dumps({"status": "error", "error": "InvalidRequest", "message": str(e)}),
            status_code=400,
            mimetype="application/json"
        )
    
    logging.info(f"🚀 Starting {category}/{action} - Execution: {execution_id}")
    
    # Initialize blob client
    blob_service_client = get_blob_service_client()
    
    # Temporary file paths
    temp_input = None
    temp_output = None
    start_time = datetime.utcnow()
    
    try:
        # Step 1: Update database status to "processing"
        update_execution_status(execution_id, "processing")
        
        # Step 2: Download input file from blob storage
        logging.info(f"📥 Downloading input: {input_blob_path}")
        temp_input = download_blob(blob_service_client, input_blob_path)
        
        # Step 3: Process file (tool-specific logic)
        logging.info(f"⚙️ Processing with {tool_name}")
        temp_output = process_tool(category, action, temp_input, parameters)
        
        # Step 4: Upload result to processed container
        output_extension = get_output_extension(category, action)
        output_blob_path = f"{output_container}/{category}/{execution_id}{output_extension}"
        logging.info(f"📤 Uploading output: {output_blob_path}")
        upload_blob(blob_service_client, temp_output, output_blob_path)
        
        # Step 5: Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Step 6: Update database status to "completed"
        update_execution_status(
            execution_id, 
            "completed", 
            output_blob_path=output_blob_path,
            processing_time=processing_time
        )
        
        logging.info(f"✅ Completed in {processing_time:.2f}s - Execution: {execution_id}")
        
        # Step 7: Return success response
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "executionId": execution_id,
                "outputBlobPath": output_blob_path,
                "processingTimeSeconds": processing_time,
                "metadata": get_output_metadata(temp_output)
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except ValidationError as e:
        logging.error(f"❌ Validation error: {str(e)}")
        update_execution_status(execution_id, "failed", error_message=str(e))
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "executionId": execution_id,
                "error": "ValidationError",
                "message": str(e),
                "details": {"errorCode": e.code}
            }),
            status_code=400,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"❌ Processing error: {str(e)}", exc_info=True)
        update_execution_status(execution_id, "failed", error_message=str(e))
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "executionId": execution_id,
                "error": "ProcessingError",
                "message": "An unexpected error occurred during processing",
                "details": {"technicalDetails": str(e)}
            }),
            status_code=500,
            mimetype="application/json"
        )
        
    finally:
        # Step 8: Cleanup temporary files (ALWAYS)
        if temp_input and os.path.exists(temp_input):
            os.remove(temp_input)
            logging.info(f"🗑️ Cleaned up temp input: {temp_input}")
        if temp_output and os.path.exists(temp_output):
            os.remove(temp_output)
            logging.info(f"🗑️ Cleaned up temp output: {temp_output}")


def get_blob_service_client() -> BlobServiceClient:
    """Initialize blob client with connection string or Managed Identity"""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if connection_string:
        # Local development (Azurite)
        return BlobServiceClient.from_connection_string(connection_string)
    else:
        # Production (Managed Identity)
        account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        account_url = f"https://{account_name}.blob.core.windows.net"
        return BlobServiceClient(account_url, credential=DefaultAzureCredential())


def download_blob(client: BlobServiceClient, blob_path: str) -> str:
    """Download blob to temporary file, return temp file path"""
    container_name, blob_name = blob_path.split('/', 1)
    blob_client = client.get_blob_client(container=container_name, blob=blob_name)
    
    # Create temp file with appropriate extension
    _, ext = os.path.splitext(blob_name)
    fd, temp_path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    
    # Download blob content
    with open(temp_path, 'wb') as f:
        blob_data = blob_client.download_blob()
        blob_data.readinto(f)
    
    return temp_path


def upload_blob(client: BlobServiceClient, file_path: str, blob_path: str):
    """Upload file to blob storage"""
    container_name, blob_name = blob_path.split('/', 1)
    blob_client = client.get_blob_client(container=container_name, blob=blob_name)
    
    with open(file_path, 'rb') as f:
        blob_client.upload_blob(f, overwrite=True)


def update_execution_status(execution_id: str, status: str, **kwargs):
    """Update ToolExecution record in database via REST API"""
    database_api_url = os.getenv("DATABASE_API_URL")
    # Implementation: HTTP PATCH to Django API
    # PATCH {database_api_url}/api/v1/executions/{execution_id}/
    # Body: {"status": status, ...kwargs}
    pass


def process_tool(category: str, action: str, input_file: str, parameters: dict) -> str:
    """
    Tool-specific processing logic.
    Returns path to output file.
    """
    # Example: Route to specific processor based on category/action
    if category == "document" and action == "convert":
        return convert_pdf_to_docx(input_file, parameters)
    elif category == "video" and action == "rotate":
        return rotate_video(input_file, parameters)
    else:
        raise ValueError(f"Unknown tool: {category}/{action}")
```

---

## Database Status Updates

Azure Functions must update the Django database via REST API endpoint:

### Update Status Endpoint

**URL**: `{DATABASE_API_URL}/api/internal/executions/{execution_id}/status/`  
**Method**: `PATCH`  
**Authentication**: Function Key (shared secret)

**Request Body**:
```json
{
  "status": "processing",
  "outputBlobPath": null,
  "errorMessage": null,
  "processingTimeSeconds": null
}
```

**Valid Status Transitions**:
- `pending` → `processing` (when function starts)
- `processing` → `completed` (on success)
- `processing` → `failed` (on error)

---

## Error Handling Requirements

1. **Always update database status** even on failure
2. **Always cleanup temp files** in `finally` block
3. **Log execution_id** in all log messages for traceability
4. **Return user-friendly messages** in error responses (no stack traces)
5. **Include technical details** in `details` field for debugging
6. **Set appropriate HTTP status codes**:
   - 200: Success
   - 400: Validation error (bad input)
   - 500: Processing error (system failure)
   - 504: Timeout (function execution exceeded limit)

---

## Timeout Configuration

Azure Functions must be configured with appropriate timeouts per category:

| Category | Default Timeout | Max Timeout | Rationale |
|----------|----------------|-------------|-----------|
| TEXT | 1 minute | 2 minutes | Fast text processing |
| IMAGE | 5 minutes | 10 minutes | Image format conversion |
| DOCUMENT | 5 minutes | 15 minutes | PDF conversion, OCR |
| VIDEO | 15 minutes | 30 minutes | Video encoding |
| GPS | 2 minutes | 5 minutes | GPX file parsing |

**Configuration** (host.json):
```json
{
  "version": "2.0",
  "functionTimeout": "00:15:00",
  "extensions": {
    "http": {
      "routePrefix": ""
    }
  }
}
```

---

## Authentication

### Local Development
- **Auth Level**: `ANONYMOUS`
- No authentication required for local testing

### Production
- **Auth Level**: `FUNCTION`
- Requires function key in `x-functions-key` header
- Django application stores function key in Azure Key Vault
- Key is passed in trigger request:

```python
headers = {
    "Content-Type": "application/json",
    "x-functions-key": settings.AZURE_FUNCTION_KEY
}
```

---

## Testing Contract Compliance

### Unit Tests (Azure Function side)
```python
def test_successful_processing():
    request_body = {
        "executionId": "550e8400-e29b-41d4-a716-446655440000",
        "toolName": "pdf-docx-converter",
        "inputBlobPath": "uploads/document/test.pdf",
        "outputContainer": "processed",
        "parameters": {"preserveLayout": True}
    }
    response = process_file(create_mock_request(request_body))
    assert response.status_code == 200
    data = json.loads(response.get_body())
    assert data["status"] == "success"
    assert "outputBlobPath" in data
```

### Integration Tests (Django side)
```python
def test_azure_function_trigger():
    # Upload file and create execution
    execution = create_test_execution()
    
    # Trigger Azure Function
    trigger_azure_function(execution.execution_id)
    
    # Wait for completion
    time.sleep(30)
    
    # Verify status updated
    execution.refresh_from_db()
    assert execution.status == "completed"
    assert execution.output_blob_path is not None
```

---

## Summary

**Key Contract Points**:
1. ✅ Standard URL pattern: `{base_url}/{category}/{action}`
2. ✅ Consistent request schema with `executionId`, `inputBlobPath`, `parameters`
3. ✅ Success response includes `outputBlobPath` and `processingTimeSeconds`
4. ✅ Error responses include `error`, `message`, and `details`
5. ✅ Database status updates via REST API
6. ✅ Mandatory temp file cleanup in `finally` block
7. ✅ Comprehensive logging with execution ID
8. ✅ Category-appropriate timeouts
9. ✅ Function key authentication in production

**Next Steps**:
- ✅ API contracts complete
- ⏭️ Generate quickstart guide for developers
