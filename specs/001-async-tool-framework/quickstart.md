# Quickstart Guide: Adding New Tools

**Feature**: Async Tool Framework & Plugin System  
**Audience**: Developers adding new tools to MagicToolbox  
**Time to First Tool**: ~30 minutes

---

## Prerequisites

Before you begin, ensure you have:

- ✅ Python 3.11+ installed
- ✅ MagicToolbox repository cloned
- ✅ Virtual environment activated: `source .venv/bin/activate`
- ✅ Dependencies installed: `pip install -r requirements/development.txt`
- ✅ Azurite running (for async tools): `azurite-blob --location ./azurite --debug ./azurite-debug.log`
- ✅ PostgreSQL/SQLite database configured
- ✅ Familiarity with Django and Python type hints

---

## Quick Decision: Sync or Async?

Choose the right pattern for your tool:

### Use **Synchronous Processing** if:
- ✅ Processing completes in < 5 seconds
- ✅ No heavy computation (CPU-intensive)
- ✅ No file I/O or file size < 1MB
- ✅ Examples: Text encoding, hash generation, unit conversion, JSON formatting

### Use **Asynchronous Processing** if:
- ✅ Processing takes > 5 seconds
- ✅ File manipulation (conversion, rotation, compression)
- ✅ Large files (> 1MB) or video/image processing
- ✅ Examples: PDF conversion, video rotation, OCR, image format conversion

---

## Path 1: Adding a Synchronous Tool

**Example**: Base64 Encoder

### Step 1: Create Plugin File

Create `apps/tools/plugins/base64_encoder.py`:

```python
"""Base64 Encoder Tool - Encodes text or files to Base64 format"""
from typing import Any, Dict, Tuple, Optional
import base64
from django.core.exceptions import ValidationError
from apps.tools.base import BaseTool


class Base64Encoder(BaseTool):
    """Synchronous tool for Base64 encoding"""
    
    # Tool Metadata (required)
    name = "base64-encoder"
    display_name = "Base64 Encoder"
    description = "Encode text or files to Base64 format for safe data transmission"
    category = "TEXT"  # Options: DOCUMENT, IMAGE, VIDEO, GPS, TEXT, CONVERSION
    supported_formats = []  # Empty for text-based tools
    max_file_size = 10 * 1024 * 1024  # 10MB
    is_async = False  # Synchronous processing
    icon = "bi-code-square"  # Bootstrap icon class
    
    def validate(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input before processing.
        
        Args:
            input_data: Dictionary containing 'text' or 'file' key
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If input is invalid
        """
        if 'text' not in input_data and 'file' not in input_data:
            raise ValidationError("Either 'text' or 'file' must be provided")
        
        if 'text' in input_data:
            text = input_data['text']
            if not isinstance(text, str):
                raise ValidationError("Text must be a string")
            if len(text) == 0:
                raise ValidationError("Text cannot be empty")
            if len(text) > 100000:  # 100KB text limit
                raise ValidationError("Text exceeds maximum length (100,000 characters)")
        
        return True
    
    def process(self, input_data: Dict[str, Any]) -> Tuple[Any, Optional[str]]:
        """
        Process input and return result immediately.
        
        Args:
            input_data: Validated input data
            
        Returns:
            Tuple of (result_dict, None) for synchronous processing
        """
        if 'text' in input_data:
            # Encode text
            text_bytes = input_data['text'].encode('utf-8')
            encoded = base64.b64encode(text_bytes).decode('utf-8')
            
            result = {
                "encodedText": encoded,
                "originalLength": len(input_data['text']),
                "encodedLength": len(encoded)
            }
        else:
            # Encode file (simplified example)
            file_content = input_data['file'].read()
            encoded = base64.b64encode(file_content).decode('utf-8')
            
            result = {
                "encodedText": encoded,
                "fileName": input_data['file'].name,
                "fileSizeBytes": len(file_content)
            }
        
        # Return (result, None) for synchronous tools
        return result, None
```

### Step 2: Create Template (Optional - Can Use Generic)

Create `templates/tools/base64_encoder.html`:

```django
{% extends "base.html" %}
{% load static %}
{% load crispy_forms_tags %}

{% block title %}{{ tool.display_name }} - MagicToolbox{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <!-- Main Content: 8 columns -->
        <div class="col-md-8">
            <h2><i class="{{ tool.icon }}"></i> {{ tool.display_name }}</h2>
            <p class="text-muted">{{ tool.description }}</p>
            
            <!-- Input Form -->
            <div class="card mb-4">
                <div class="card-header">
                    <h5>Encode Text</h5>
                </div>
                <div class="card-body">
                    <form id="encoderForm" method="post" action="{% url 'api-tool-base64-encoder' %}">
                        {% csrf_token %}
                        <div class="mb-3">
                            <label for="inputText" class="form-label">Text to Encode</label>
                            <textarea class="form-control" id="inputText" name="text" rows="5" 
                                      placeholder="Enter text to encode..." required></textarea>
                            <small class="form-text text-muted">Maximum 100,000 characters</small>
                        </div>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi-arrow-right-circle"></i> Encode
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Results Section -->
            <div id="resultSection" class="card d-none">
                <div class="card-header bg-success text-white">
                    <h5><i class="bi-check-circle"></i> Encoded Result</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label">Base64 Encoded Text</label>
                        <textarea class="form-control" id="encodedResult" rows="5" readonly></textarea>
                    </div>
                    <button class="btn btn-secondary" onclick="copyToClipboard()">
                        <i class="bi-clipboard"></i> Copy to Clipboard
                    </button>
                </div>
            </div>
        </div>
        
        <!-- Sidebar: 4 columns -->
        <div class="col-md-4">
            {% include 'tools/includes/instructions.html' with instructions="Enter text or upload a file to encode in Base64 format. Base64 encoding is commonly used for transmitting binary data over text-based protocols." %}
        </div>
    </div>
</div>

<script>
document.getElementById('encoderForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const response = await fetch(e.target.action, {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    
    if (response.ok) {
        // Display result
        document.getElementById('encodedResult').value = data.result.encodedText;
        document.getElementById('resultSection').classList.remove('d-none');
    } else {
        // Show error
        alert(data.error);
    }
});

function copyToClipboard() {
    const textarea = document.getElementById('encodedResult');
    textarea.select();
    document.execCommand('copy');
    alert('Copied to clipboard!');
}
</script>
{% endblock %}
```

### Step 3: Test Your Tool

```bash
# Run Django development server
python manage.py runserver

# Navigate to: http://localhost:8000/tools/base64-encoder/
```

**That's it!** Your synchronous tool is live. The framework automatically:
- ✅ Registered your tool in the registry
- ✅ Created URL routes (`/tools/base64-encoder/` and `/api/v1/tools/base64-encoder/process/`)
- ✅ Rendered your custom template (or generic if none provided)

---

## Path 2: Adding an Asynchronous Tool

**Example**: Video Rotation Tool

### Step 1: Create Django Plugin File

Create `apps/tools/plugins/video_rotation.py`:

```python
"""Video Rotation Tool - Rotates videos by specified degrees"""
from typing import Any, Dict, Tuple, Optional
import uuid
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from apps.tools.base import BaseTool
from apps.tools.models import ToolExecution
from apps.tools.services.blob_storage import BlobStorageClient
from apps.tools.services.async_task import AsyncTaskTrigger


class VideoRotation(BaseTool):
    """Asynchronous tool for video rotation"""
    
    # Tool Metadata
    name = "video-rotation"
    display_name = "Video Rotation"
    description = "Rotate videos by 90, 180, or 270 degrees clockwise"
    category = "VIDEO"
    supported_formats = [".mp4", ".avi", ".mov", ".mkv"]
    max_file_size = 500 * 1024 * 1024  # 500MB
    is_async = True  # Asynchronous processing
    icon = "bi-arrow-clockwise"
    
    def validate(self, input_data: Dict[str, Any]) -> bool:
        """Validate uploaded file and rotation parameter"""
        # Validate file
        if 'file' not in input_data:
            raise ValidationError("Video file is required")
        
        file: UploadedFile = input_data['file']
        
        # Check file extension
        file_ext = os.path.splitext(file.name)[1].lower()
        if file_ext not in self.supported_formats:
            raise ValidationError(
                f"Unsupported format. Allowed: {', '.join(self.supported_formats)}"
            )
        
        # Check file size
        if file.size > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            raise ValidationError(f"File size exceeds {max_mb:.0f}MB limit")
        
        # Validate rotation parameter
        if 'rotation' not in input_data:
            raise ValidationError("Rotation angle is required")
        
        rotation = input_data['rotation']
        if rotation not in [90, 180, 270, -90]:
            raise ValidationError("Rotation must be 90, 180, 270, or -90 degrees")
        
        return True
    
    def process(self, input_data: Dict[str, Any]) -> Tuple[str, None]:
        """
        Upload file and trigger Azure Function for async processing.
        
        Args:
            input_data: Validated input with 'file' and 'rotation'
            
        Returns:
            Tuple of (execution_id, None) for async processing
        """
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
        file: UploadedFile = input_data['file']
        rotation = int(input_data['rotation'])
        
        # Upload file to blob storage
        blob_client = BlobStorageClient()
        input_blob_path = blob_client.upload_file(
            container='uploads',
            blob_path=f"{self.category.lower()}/{execution_id}{os.path.splitext(file.name)[1]}",
            file_content=file
        )
        
        # Create execution record
        execution = ToolExecution.objects.create(
            execution_id=execution_id,
            tool_name=self.name,
            status=ToolExecution.Status.PENDING,
            input_file_name=file.name,
            input_blob_path=input_blob_path,
            parameters={"rotation": rotation},
            file_size_bytes=file.size
        )
        
        # Trigger Azure Function
        trigger = AsyncTaskTrigger()
        trigger.trigger_function(
            category=self.category.lower(),
            action="rotate",
            execution_id=execution_id,
            input_blob_path=input_blob_path,
            parameters={"rotation": rotation}
        )
        
        # Return (execution_id, None) for async tools
        return execution_id, None
```

### Step 2: Create Azure Function Handler

Create `function_app/video/rotate.py`:

```python
"""Azure Function: Video Rotation"""
import azure.functions as func
import logging
import json
import os
import tempfile
import subprocess
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential


def rotate_video(input_file: str, output_file: str, rotation: int):
    """
    Rotate video using ffmpeg.
    
    Args:
        input_file: Path to input video
        output_file: Path to save rotated video
        rotation: Rotation angle (90, 180, 270, -90)
    """
    # Map rotation to ffmpeg transpose filter
    transpose_map = {
        90: "transpose=1",     # 90 degrees clockwise
        180: "transpose=1,transpose=1",  # 180 degrees
        270: "transpose=2",    # 90 degrees counter-clockwise
        -90: "transpose=2"     # Same as 270
    }
    
    filter_str = transpose_map.get(rotation)
    if not filter_str:
        raise ValueError(f"Invalid rotation: {rotation}")
    
    # Run ffmpeg
    command = [
        "ffmpeg",
        "-i", input_file,
        "-vf", filter_str,
        "-c:a", "copy",  # Copy audio without re-encoding
        "-y",  # Overwrite output
        output_file
    ]
    
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")


def process_video_rotation(req: func.HttpRequest) -> func.HttpResponse:
    """Handler for /video/rotate endpoint"""
    
    # Parse request
    try:
        req_body = req.get_json()
        execution_id = req_body['executionId']
        input_blob_path = req_body['inputBlobPath']
        parameters = req_body.get('parameters', {})
        rotation = parameters.get('rotation', 90)
    except (ValueError, KeyError) as e:
        return func.HttpResponse(
            json.dumps({"status": "error", "error": "InvalidRequest", "message": str(e)}),
            status_code=400
        )
    
    logging.info(f"🚀 Starting video rotation - Execution: {execution_id}, Rotation: {rotation}°")
    
    # Initialize blob client
    blob_client = get_blob_service_client()
    
    temp_input = None
    temp_output = None
    start_time = datetime.utcnow()
    
    try:
        # Update status to processing
        update_execution_status(execution_id, "processing")
        
        # Download input video
        logging.info(f"📥 Downloading: {input_blob_path}")
        temp_input = download_blob(blob_client, input_blob_path)
        
        # Create output temp file
        _, ext = os.path.splitext(temp_input)
        temp_output = tempfile.mktemp(suffix=ext)
        
        # Rotate video
        logging.info(f"⚙️ Rotating video by {rotation}°")
        rotate_video(temp_input, temp_output, rotation)
        
        # Upload result
        output_blob_path = f"processed/video/{execution_id}{ext}"
        logging.info(f"📤 Uploading: {output_blob_path}")
        upload_blob(blob_client, temp_output, output_blob_path)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Update status to completed
        update_execution_status(
            execution_id,
            "completed",
            output_blob_path=output_blob_path,
            processing_time=processing_time
        )
        
        logging.info(f"✅ Completed in {processing_time:.2f}s")
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "executionId": execution_id,
                "outputBlobPath": output_blob_path,
                "processingTimeSeconds": processing_time
            }),
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"❌ Error: {str(e)}", exc_info=True)
        update_execution_status(execution_id, "failed", error_message=str(e))
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "executionId": execution_id,
                "error": "ProcessingError",
                "message": str(e)
            }),
            status_code=500
        )
        
    finally:
        # Cleanup temp files
        if temp_input and os.path.exists(temp_input):
            os.remove(temp_input)
        if temp_output and os.path.exists(temp_output):
            os.remove(temp_output)


# Register function in function_app.py
# @app.route(route="video/rotate", methods=["POST"])
# def video_rotate_handler(req: func.HttpRequest):
#     return process_video_rotation(req)
```

### Step 3: Create Frontend Template

Create `templates/tools/video_rotation.html`:

```django
{% extends "base.html" %}
{% load static %}

{% block title %}{{ tool.display_name }} - MagicToolbox{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <!-- Main Content -->
        <div class="col-md-8">
            <h2><i class="{{ tool.icon }}"></i> {{ tool.display_name }}</h2>
            <p class="text-muted">{{ tool.description }}</p>
            
            <!-- Upload Form -->
            <div class="card mb-4">
                <div class="card-header"><h5>Upload Video</h5></div>
                <div class="card-body">
                    <form id="uploadForm">
                        {% csrf_token %}
                        <div class="mb-3">
                            <label for="videoFile" class="form-label">Select Video</label>
                            <input type="file" class="form-control" id="videoFile" 
                                   accept="{{ tool.supported_formats|join:',' }}" required>
                            <small class="form-text text-muted">
                                Max size: {{ tool.max_file_size|filesizeformat }}
                            </small>
                        </div>
                        <div class="mb-3">
                            <label for="rotation" class="form-label">Rotation Angle</label>
                            <select class="form-select" id="rotation" required>
                                <option value="90">90° Clockwise</option>
                                <option value="180">180° (Upside Down)</option>
                                <option value="270">270° Clockwise (90° Counter-clockwise)</option>
                            </select>
                        </div>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi-upload"></i> Upload & Rotate
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Status Section (shown after upload) -->
            <div id="statusSection" class="card d-none mb-4">
                <div class="card-header"><h5>Processing Status</h5></div>
                <div class="card-body">
                    <div class="progress mb-3">
                        <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" 
                             style="width: 0%"></div>
                    </div>
                    <p id="statusText">Uploading...</p>
                    <p><small>Elapsed: <span id="elapsedTime">0s</span></small></p>
                </div>
            </div>
            
            <!-- Download Section -->
            <div id="downloadSection" class="card d-none">
                <div class="card-header bg-success text-white">
                    <h5><i class="bi-check-circle"></i> Rotation Complete!</h5>
                </div>
                <div class="card-body">
                    <a id="downloadBtn" class="btn btn-success" href="#" download>
                        <i class="bi-download"></i> Download Rotated Video
                    </a>
                </div>
            </div>
        </div>
        
        <!-- History Sidebar -->
        <div class="col-md-4">
            {% include 'tools/includes/history_sidebar.html' %}
        </div>
    </div>
</div>

<script>
let statusPoller = null;
let startTime = null;

document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Show status section
    document.getElementById('statusSection').classList.remove('d-none');
    document.getElementById('downloadSection').classList.add('d-none');
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', document.getElementById('videoFile').files[0]);
    formData.append('rotation', document.getElementById('rotation').value);
    
    // Upload and trigger processing
    const response = await fetch('/api/v1/tools/video-rotation/process/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': '{{ csrf_token }}'
        }
    });
    
    const data = await response.json();
    
    if (response.ok) {
        // Start status polling
        startTime = Date.now();
        pollStatus(data.executionId);
    } else {
        alert('Error: ' + data.error);
    }
});

async function pollStatus(executionId) {
    const response = await fetch(`/api/v1/executions/${executionId}/status/`);
    const data = await response.json();
    
    // Update UI
    document.getElementById('statusText').textContent = 
        data.status.charAt(0).toUpperCase() + data.status.slice(1);
    document.getElementById('elapsedTime').textContent = 
        Math.floor((Date.now() - startTime) / 1000) + 's';
    
    if (data.status === 'processing') {
        document.getElementById('progressBar').style.width = '50%';
    }
    
    if (data.status === 'completed') {
        // Show download button
        document.getElementById('progressBar').style.width = '100%';
        document.getElementById('downloadBtn').href = data.downloadUrl;
        document.getElementById('downloadSection').classList.remove('d-none');
        document.getElementById('statusSection').classList.add('d-none');
        
        // Refresh history
        loadHistory();
    } else if (data.status === 'failed') {
        alert('Processing failed: ' + data.error);
    } else {
        // Continue polling
        setTimeout(() => pollStatus(executionId), 2000);
    }
}

async function loadHistory() {
    const response = await fetch('/api/v1/executions/?toolName=video-rotation&limit=10');
    const data = await response.json();
    // Update history sidebar...
}
</script>
{% endblock %}
```

### Step 4: Test Locally

```bash
# Terminal 1: Start Azurite (blob storage emulator)
azurite-blob --location ./azurite

# Terminal 2: Start Django
python manage.py runserver

# Terminal 3: Start Azure Functions locally
cd function_app
func start

# Navigate to: http://localhost:8000/tools/video-rotation/
```

---

## Common Patterns & Best Practices

### 1. Tool Naming Convention
- **URL name**: `kebab-case` (e.g., `pdf-docx-converter`)
- **Class name**: `PascalCase` (e.g., `PdfDocxConverter`)
- **File name**: `snake_case` (e.g., `pdf_docx_converter.py`)

### 2. Error Handling
```python
from django.core.exceptions import ValidationError

def validate(self, input_data):
    try:
        # Validation logic
        if something_wrong:
            raise ValidationError("User-friendly error message")
    except SomeException as e:
        # Convert library exceptions to ValidationError
        raise ValidationError(f"Invalid input: {str(e)}")
```

### 3. Logging
```python
import logging

logger = logging.getLogger(__name__)

def process(self, input_data):
    logger.info(f"🚀 Starting {self.name} processing")
    try:
        # Process
        logger.info(f"✅ Completed successfully")
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        raise
```

### 4. Testing Your Tool
```python
# tests/unit/tools/test_my_tool.py
import pytest
from apps.tools.plugins.my_tool import MyTool
from django.core.exceptions import ValidationError

def test_validate_valid_input():
    tool = MyTool()
    assert tool.validate({"text": "valid"}) is True

def test_validate_empty_input():
    tool = MyTool()
    with pytest.raises(ValidationError):
        tool.validate({"text": ""})

@pytest.mark.django_db
def test_async_tool_creates_execution():
    tool = MyAsyncTool()
    execution_id, _ = tool.process({"file": mock_file})
    assert ToolExecution.objects.filter(execution_id=execution_id).exists()
```

---

## Troubleshooting

### Tool Not Appearing in Registry
**Problem**: Tool doesn't show up in `/api/v1/tools/`

**Solution**:
1. Check tool inherits from `BaseTool`
2. Verify file is in `apps/tools/plugins/` directory
3. Restart Django server (tool discovery happens at startup)
4. Check logs for registration errors

### Async Processing Stuck on "Pending"
**Problem**: Status never changes from "pending"

**Solution**:
1. Verify Azure Functions is running (`func start` in `function_app/`)
2. Check `AZURE_FUNCTION_BASE_URL` environment variable
3. Verify function endpoint matches: `{base_url}/{category}/{action}`
4. Check Azure Function logs for errors

### File Upload Fails
**Problem**: "File size exceeds limit" or "Unsupported format"

**Solution**:
1. Check `max_file_size` attribute in tool class
2. Verify file extension in `supported_formats` list
3. Check Azurite is running for local development
4. Verify blob storage connection string in `.env.development`

---

## Next Steps

1. ✅ Created your first tool
2. ⏭️ Add comprehensive tests (unit + integration)
3. ⏭️ Update documentation in `documentation/` folder
4. ⏭️ Submit PR following conventional commits format
5. ⏭️ Deploy to staging for E2E testing

---

## Reference Documentation

- **Feature Spec**: [spec.md](./spec.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contract**: [contracts/api-spec.yaml](./contracts/api-spec.yaml)
- **Azure Function Contract**: [contracts/azure-function-contract.md](./contracts/azure-function-contract.md)
- **Constitution**: [.specify/memory/constitution.md](../../.specify/memory/constitution.md)
- **Gold Standard**: [documentation/ASYNC_FILE_PROCESSING_GOLD_STANDARD.md](../../documentation/ASYNC_FILE_PROCESSING_GOLD_STANDARD.md)

---

## Support

**Questions?** Check existing tool implementations:
- Sync: `apps/tools/plugins/base64_encoder.py`
- Async: `apps/tools/plugins/pdf_docx_converter.py`, `apps/tools/plugins/video_rotation.py`

**Need help?** Open an issue or ask in team chat.
