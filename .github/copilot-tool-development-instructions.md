---
description: Comprehensive guide for developing new tools in MagicToolbox
applyTo: 'apps/tools/plugins/**'
---

# Tool Development Guide

This guide provides standardized guidelines for creating new tools in MagicToolbox. All tools should follow these patterns to ensure consistency, maintainability, and a uniform user experience.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Tool Plugin (Python)](#backend-tool-plugin-python)
3. [Frontend Template (Django + Bootstrap)](#frontend-template-django--bootstrap)
4. [JavaScript Logic](#javascript-logic)
5. [Bulk Processing Support](#bulk-processing-support)
6. [Testing Requirements](#testing-requirements)
7. [Checklist for New Tools](#checklist-for-new-tools)

---

## Architecture Overview

Every tool in MagicToolbox consists of three main components:

1. **Backend Plugin** (`apps/tools/plugins/your_tool.py`) - Python class inheriting from `BaseTool`
2. **Frontend Template** (`templates/tools/your_tool.html`) - Django template with Bootstrap UI
3. **JavaScript Logic** (embedded in template) - Handles file upload, progress tracking, and result display

**Data Flow:**
```
User Upload → Frontend (JS) → API Endpoint → Backend Plugin → Processed File → Download
```

---

## Backend Tool Plugin (Python)

### File Location
```
backend/apps/tools/plugins/your_tool_name.py
```

### Class Structure

```python
"""
Brief description of what the tool does.

Detailed explanation of supported operations, formats, etc.
"""
from typing import Any, Dict, Optional, Tuple
from django.core.files.uploadedfile import UploadedFile
from apps.tools.base import BaseTool
from apps.core.exceptions import ToolValidationError, ToolExecutionError
from pathlib import Path
import tempfile
import os

# Import tool-specific libraries
# Example: from PIL import Image


class YourToolName(BaseTool):
    """
    Short description of tool functionality.
    
    Supports: List key features/formats
    """
    
    # ==================== METADATA (Required) ====================
    name = "your-tool-name"  # Kebab-case, used in URLs
    display_name = "Your Tool Name"  # Human-readable name
    description = "Brief description for tool listing"
    category = "image|file|document|data"  # Choose appropriate category
    version = "1.0.0"  # Semantic versioning
    icon = "bootstrap-icon-name"  # Bootstrap icon (without 'bi-' prefix)
    
    # ==================== FILE CONSTRAINTS (Required) ====================
    allowed_input_types = ['.ext1', '.ext2', '.ext3']  # Lowercase with dots
    max_file_size = 50 * 1024 * 1024  # 50MB default (adjust as needed)
    
    # ==================== TOOL-SPECIFIC CONSTANTS ====================
    # Define supported formats, options, etc.
    SUPPORTED_FORMATS = {
        'format1': {'name': 'Format 1', 'description': 'Description'},
        'format2': {'name': 'Format 2', 'description': 'Description'},
    }
    
    def validate(
        self,
        input_file: UploadedFile,
        parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input file and parameters before processing.
        
        Args:
            input_file: Uploaded file to validate
            parameters: Dictionary of conversion parameters
            
        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, "error message") if invalid
            
        Required parameters:
            - output_format: Target format (example)
            
        Optional parameters:
            - quality: Quality setting (example)
            - width/height: Resize dimensions (example)
        """
        # 1. Check required dependencies
        # if REQUIRED_LIBRARY is None:
        #     return False, "Library XYZ not installed"
        
        # 2. Validate file type using helper
        if not self.validate_file_type(input_file.name):
            return False, f"Unsupported file type. Allowed: {', '.join(self.allowed_input_types)}"
        
        # 3. Validate file size using helper
        if not self.validate_file_size(input_file):
            return False, f"File exceeds maximum size of {self.max_file_size / (1024*1024):.1f}MB"
        
        # 4. Validate required parameters
        output_format = parameters.get('output_format', '').lower()
        if not output_format:
            return False, "Missing required parameter: output_format"
        
        if output_format not in self.SUPPORTED_FORMATS:
            return False, f"Unsupported format: {output_format}"
        
        # 5. Validate optional parameters with proper type checking
        # Example for integer parameter:
        quality = parameters.get('quality')
        if quality is not None:
            try:
                quality = int(quality)
                if not 1 <= quality <= 100:
                    return False, "Quality must be between 1 and 100"
            except (ValueError, TypeError):
                return False, "Quality must be an integer"
        
        return True, None
    
    def process(
        self,
        input_file: UploadedFile,
        parameters: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Process the uploaded file and return converted file.
        
        Args:
            input_file: Uploaded file to process
            parameters: Validated conversion parameters
            
        Returns:
            Tuple of (output_file_path, output_filename)
            - output_file_path: Absolute path to temp file
            - output_filename: Name for download (with extension)
            
        Raises:
            ToolExecutionError: If processing fails
        """
        # Extract parameters
        output_format = parameters['output_format'].lower()
        optional_param = parameters.get('optional_param', default_value)
        
        temp_input = None
        temp_output = None
        
        try:
            # Step 1: Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(input_file.name).suffix) as tmp_in:
                for chunk in input_file.chunks():
                    tmp_in.write(chunk)
                temp_input = tmp_in.name
            
            # Step 2: Process the file (tool-specific logic)
            # Example: Open, convert, modify, etc.
            # ... your processing logic here ...
            
            # Step 3: Generate output filename
            # ALWAYS use original filename with new extension
            output_filename = f"{Path(input_file.name).stem}.{output_format}"
            
            # Step 4: Save processed file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{output_format}') as tmp_out:
                temp_output = tmp_out.name
                # Write processed data
                # ... save output ...
            
            # Step 5: Log success with file size
            output_size = os.path.getsize(temp_output)
            self.logger.info(
                f"Successfully converted {input_file.name} to {output_format}: "
                f"{output_size / 1024:.1f} KB"
            )
            
            # Step 6: Cleanup input temp file immediately
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            
            return temp_output, output_filename
            
        except Exception as e:
            self.logger.error(f"Processing failed: {e}", exc_info=True)
            
            # Cleanup on error
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.unlink(temp_output)
            
            raise ToolExecutionError(f"Processing failed: {str(e)}")
    
    def cleanup(self, *file_paths: str) -> None:
        """
        Cleanup temporary files after download.
        
        This is called automatically by the framework after the file
        is sent to the user. Only cleanup OUTPUT files here.
        
        Args:
            *file_paths: Paths to temporary files to delete
        """
        for path in file_paths:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    self.logger.debug(f"Cleaned up temp file: {path}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup {path}: {e}")
```

### Key Backend Principles

1. **Always use original filename with new extension** - Don't create custom naming logic
2. **Clean up input files immediately** - Delete temp input files in `process()` after reading
3. **Clean up output files in cleanup()** - Framework calls this after download
4. **Use tempfile.NamedTemporaryFile with delete=False** - Manual cleanup control
5. **Log success with file sizes** - Help debugging and monitoring
6. **Proper error handling** - Cleanup on errors, use ToolExecutionError
7. **Type hints** - Always include type annotations
8. **Docstrings** - Document parameters, return values, and exceptions

---

## Frontend Template (Django + Bootstrap)

### File Location
```
backend/templates/tools/your_tool_name.html
```

### Template Structure

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}{{ tool.display_name }} - MagicToolbox{% endblock %}

{% block content %}
<div class="container py-4">
  <!-- ==================== BREADCRUMB & HEADER ==================== -->
  <div class="row mb-4">
    <div class="col">
      <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
          <li class="breadcrumb-item"><a href="{% url 'core:home' %}">Home</a></li>
          <li class="breadcrumb-item"><a href="{% url 'tools:tool_list' %}">Tools</a></li>
          <li class="breadcrumb-item active" aria-current="page">{{ tool.display_name }}</li>
        </ol>
      </nav>
      
      <h1 class="display-4 mb-3">
        <i class="bi bi-{{ tool.icon }} text-primary me-3"></i>
        {{ tool.display_name }}
      </h1>
      <p class="lead text-muted">{{ tool.description }}</p>
    </div>
  </div>

  <div class="row">
    <!-- ==================== MAIN CONTENT (LEFT COLUMN) ==================== -->
    <div class="col-lg-8">
      <div class="card shadow-sm mb-4">
        <div class="card-header bg-primary text-white">
          <h5 class="mb-0">
            <i class="bi bi-upload me-2"></i>Upload & Convert
          </h5>
        </div>
        <div class="card-body">
          <!-- ==================== FORM ==================== -->
          <form id="toolForm" enctype="multipart/form-data">
            {% csrf_token %}
            
            <!-- File Input (MUST support multiple files) -->
            <div class="mb-3">
              <label for="inputFile" class="form-label">
                Select File(s)
                <span class="badge bg-success">Bulk supported!</span>
              </label>
              <input 
                type="file" 
                class="form-control" 
                id="inputFile" 
                name="files[]" 
                accept=".ext1,.ext2"
                multiple 
                required>
              <div class="form-text">
                <i class="bi bi-info-circle me-1"></i>
                Select one or multiple files (max 50MB per file).
              </div>
              <div id="fileList" class="mt-2"></div>
            </div>

            <!-- Output Format Selection (Required for most tools) -->
            <div class="mb-3">
              <label for="outputFormat" class="form-label">Output Format</label>
              <select class="form-select" id="outputFormat" name="output_format" required>
                <option value="">Choose format...</option>
                <option value="format1">Format 1 - Description</option>
                <option value="format2">Format 2 - Description</option>
              </select>
            </div>

            <!-- Optional Parameters (if applicable) -->
            <div class="mb-3">
              <label for="optionalParam" class="form-label">
                Optional Setting <span class="text-muted small">(Optional)</span>
              </label>
              <input type="range" class="form-range" id="optionalParam" name="optional_param" min="1" max="100" value="85">
            </div>
            
            <!-- Submit Button -->
            <div class="d-grid gap-2">
              <button type="submit" class="btn btn-primary btn-lg" id="convertBtn">
                <i class="bi bi-arrow-repeat me-2"></i>Convert File(s)
              </button>
            </div>
          </form>

          <!-- ==================== PROGRESS SECTION ==================== -->
          <div id="progressSection" class="mt-4" style="display: none;">
            <div class="progress" style="height: 30px;">
              <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                   role="progressbar" 
                   id="progressBar"
                   style="width: 0%">
                <span id="progressText">0%</span>
              </div>
            </div>
            <p class="text-center text-muted mt-2" id="progressMessage">Converting your file...</p>
          </div>

          <!-- ==================== SINGLE FILE RESULT ==================== -->
          <div id="resultSection" class="mt-4" style="display: none;">
            <div class="alert alert-success" role="alert">
              <h5 class="alert-heading">
                <i class="bi bi-check-circle me-2"></i>Conversion Successful!
              </h5>
              <p class="mb-0">Your file has been converted successfully.</p>
            </div>

            <!-- File Information Card -->
            <div class="card mb-3">
              <div class="card-header">
                <h6 class="mb-0">Conversion Details</h6>
              </div>
              <div class="card-body">
                <div class="row">
                  <div class="col-md-6">
                    <h6 class="text-muted mb-2">Original File</h6>
                    <p class="mb-1" id="originalFileName"></p>
                    <small class="text-muted" id="originalFileInfo"></small>
                  </div>
                  <div class="col-md-6">
                    <h6 class="text-muted mb-2">Converted File</h6>
                    <p class="mb-1" id="convertedFileName"></p>
                    <small class="text-muted" id="convertedFileInfo"></small>
                  </div>
                </div>
              </div>
            </div>

            <!-- Download Button -->
            <div class="d-grid gap-2">
              <a href="#" id="downloadBtn" class="btn btn-success btn-lg" download>
                <i class="bi bi-download me-2"></i>Download Converted File
              </a>
              <button type="button" class="btn btn-outline-primary" onclick="location.reload()">
                <i class="bi bi-arrow-clockwise me-2"></i>Convert Another File
              </button>
            </div>
          </div>

          <!-- ==================== BULK RESULT SECTION ==================== -->
          <div id="bulkResultSection" class="mt-4" style="display: none;">
            <div class="alert alert-success" role="alert">
              <h5 class="alert-heading">
                <i class="bi bi-check-circle me-2"></i>Bulk Conversion Complete!
              </h5>
              <p class="mb-0">Successfully converted <span id="successCount">0</span> file(s).</p>
            </div>

            <!-- Results Table -->
            <div class="card mb-3">
              <div class="card-header">
                <h6 class="mb-0">Conversion Results</h6>
              </div>
              <div class="card-body">
                <div class="table-responsive">
                  <table class="table table-sm">
                    <thead>
                      <tr>
                        <th>Original File</th>
                        <th>Status</th>
                        <th>Converted File</th>
                        <th>Size</th>
                      </tr>
                    </thead>
                    <tbody id="bulkResultsTable"></tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Download ZIP Button -->
            <div class="d-grid gap-2">
              <a href="#" id="downloadZipBtn" class="btn btn-success btn-lg" download>
                <i class="bi bi-file-earmark-zip me-2"></i>Download All as ZIP
              </a>
              <button type="button" class="btn btn-outline-primary" onclick="location.reload()">
                <i class="bi bi-arrow-clockwise me-2"></i>Convert More Files
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== SIDEBAR (RIGHT COLUMN) ==================== -->
    <div class="col-lg-4">
      <!-- Supported Formats Card -->
      <div class="card shadow-sm mb-3">
        <div class="card-header bg-light">
          <h6 class="mb-0">
            <i class="bi bi-info-circle me-2"></i>Supported Formats
          </h6>
        </div>
        <div class="card-body">
          <div class="mb-3">
            <h6 class="text-primary">Format 1</h6>
            <p class="small text-muted mb-0">Description of format 1</p>
          </div>
          <div>
            <h6 class="text-primary">Format 2</h6>
            <p class="small text-muted mb-0">Description of format 2</p>
          </div>
        </div>
      </div>

      <!-- Features Card -->
      <div class="card shadow-sm mb-3">
        <div class="card-header bg-light">
          <h6 class="mb-0">
            <i class="bi bi-star me-2"></i>Features
          </h6>
        </div>
        <div class="card-body">
          <ul class="list-unstyled mb-0">
            <li><i class="bi bi-check-circle text-success me-2"></i>Bulk upload support</li>
            <li><i class="bi bi-check-circle text-success me-2"></i>Feature 2</li>
            <li><i class="bi bi-check-circle text-success me-2"></i>Feature 3</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
// JavaScript code goes here (see JavaScript Logic section)
</script>
{% endblock %}
```

### Key Frontend Principles

1. **Always support multiple files** - Use `multiple` attribute and `name="files[]"`
2. **Consistent layout** - 8/4 column split (main content / sidebar)
3. **Bootstrap components** - Use cards, badges, alerts, buttons consistently
4. **Two result sections** - Single file result + bulk result with table
5. **Progress tracking** - Animated progress bar with percentage
6. **Breadcrumb navigation** - Always include breadcrumbs
7. **Icon usage** - Bootstrap icons for visual consistency
8. **Responsive design** - Mobile-first with Bootstrap grid

---

## JavaScript Logic

### Standard Structure

```javascript
{% block extra_js %}
<script>
// ==================== FILE LIST DISPLAY ====================
const fileInput = document.getElementById('inputFile');
const fileListDiv = document.getElementById('fileList');

fileInput.addEventListener('change', function() {
  const files = Array.from(fileInput.files);
  if (files.length === 0) {
    fileListDiv.innerHTML = '';
    return;
  }

  let html = '<div class="list-group">';
  let totalSize = 0;
  
  files.forEach((file, index) => {
    const fileExt = file.name.split('.').pop().toLowerCase();
    totalSize += file.size;
    
    html += `
      <div class="list-group-item">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <i class="bi bi-file-earmark me-2 text-primary"></i>
            <strong>${file.name}</strong>
          </div>
          <small class="text-muted">${MagicToolbox.formatFileSize(file.size)}</small>
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  
  if (files.length > 1) {
    html += `
      <div class="alert alert-info mt-2 mb-0">
        <i class="bi bi-info-circle me-1"></i>
        <strong>${files.length} files selected</strong> (Total: ${MagicToolbox.formatFileSize(totalSize)})
      </div>
    `;
  }
  
  fileListDiv.innerHTML = html;
});

// ==================== FORM SUBMISSION ====================
document.getElementById('toolForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const files = Array.from(fileInput.files);
  if (files.length === 0) {
    MagicToolbox.showNotification('Please select at least one file', 'error');
    return;
  }

  const convertBtn = document.getElementById('convertBtn');
  const progressSection = document.getElementById('progressSection');
  const resultSection = document.getElementById('resultSection');
  const bulkResultSection = document.getElementById('bulkResultSection');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const progressMessage = document.getElementById('progressMessage');
  
  // Show progress
  convertBtn.disabled = true;
  progressSection.style.display = 'block';
  resultSection.style.display = 'none';
  bulkResultSection.style.display = 'none';
  
  // Determine mode
  const isBulk = files.length > 1;
  progressMessage.textContent = isBulk 
    ? `Converting ${files.length} files...` 
    : 'Converting your file...';
  
  try {
    if (isBulk) {
      await handleBulkConversion(files, progressBar, progressText);
    } else {
      await handleSingleConversion(files[0], progressBar, progressText, this);
    }
  } catch (error) {
    console.error('Conversion error:', error);
    MagicToolbox.showNotification(error.message || 'Conversion failed', 'error');
    progressSection.style.display = 'none';
  } finally {
    convertBtn.disabled = false;
  }
});

// ==================== SINGLE FILE CONVERSION ====================
async function handleSingleConversion(file, progressBar, progressText, form) {
  const progressSection = document.getElementById('progressSection');
  const resultSection = document.getElementById('resultSection');
  
  // Animate progress
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += 15;
    progressBar.style.width = Math.min(progress, 90) + '%';
    progressText.textContent = Math.min(progress, 90) + '%';
    if (progress >= 90) clearInterval(progressInterval);
  }, 150);
  
  // Prepare form data
  const formData = new FormData(form);
  formData.delete('files[]');
  formData.append('file', file);
  
  try {
    const response = await fetch('/api/v1/tools/YOUR-TOOL-SLUG/convert/', {
      method: 'POST',
      body: formData,
      headers: {
        'X-CSRFToken': '{{ csrf_token }}'
      }
    });
    
    clearInterval(progressInterval);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `Server error: ${response.status}`);
    }
    
    // Complete progress
    progressBar.style.width = '100%';
    progressText.textContent = '100%';
    
    // Get converted file
    const blob = await response.blob();
    const convertedFileUrl = URL.createObjectURL(blob);
    
    // Extract filename from Content-Disposition
    const contentDisposition = response.headers.get('Content-Disposition');
    let convertedFilename = file.name;
    if (contentDisposition) {
      const matches = /filename="([^"]+)"/.exec(contentDisposition);
      if (matches) convertedFilename = matches[1];
    }
    
    // Update UI
    document.getElementById('originalFileName').textContent = file.name;
    document.getElementById('originalFileInfo').textContent = 
      `${file.name.split('.').pop().toUpperCase()} | ${MagicToolbox.formatFileSize(file.size)}`;
    
    document.getElementById('convertedFileName').textContent = convertedFilename;
    document.getElementById('convertedFileInfo').textContent = 
      `${convertedFilename.split('.').pop().toUpperCase()} | ${MagicToolbox.formatFileSize(blob.size)}`;
    
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.href = convertedFileUrl;
    downloadBtn.download = convertedFilename;
    
    // Show results
    setTimeout(() => {
      progressSection.style.display = 'none';
      resultSection.style.display = 'block';
      MagicToolbox.showNotification('Conversion successful!', 'success');
    }, 500);
  } catch (error) {
    throw error;
  }
}

// ==================== BULK CONVERSION ====================
async function handleBulkConversion(files, progressBar, progressText) {
  const progressSection = document.getElementById('progressSection');
  const bulkResultSection = document.getElementById('bulkResultSection');
  const outputFormat = document.getElementById('outputFormat').value;
  
  const results = [];
  const convertedBlobs = [];
  let successCount = 0;
  
  // Process each file sequentially
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const percent = Math.round(((i + 1) / files.length) * 100);
    
    progressBar.style.width = percent + '%';
    progressText.textContent = `${percent}% (${i + 1}/${files.length})`;
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('output_format', outputFormat);
      // Add other parameters as needed
      
      const response = await fetch('/api/v1/tools/YOUR-TOOL-SLUG/convert/', {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': '{{ csrf_token }}'
        }
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = file.name;
        if (contentDisposition) {
          const matches = /filename="([^"]+)"/.exec(contentDisposition);
          if (matches) filename = matches[1];
        }
        
        convertedBlobs.push({ blob, filename });
        results.push({
          originalName: file.name,
          convertedName: filename,
          size: blob.size,
          status: 'success'
        });
        successCount++;
      } else {
        results.push({
          originalName: file.name,
          status: 'error',
          error: 'Conversion failed'
        });
      }
    } catch (error) {
      results.push({
        originalName: file.name,
        status: 'error',
        error: error.message
      });
    }
  }
  
  // Display results table
  const tableBody = document.getElementById('bulkResultsTable');
  if (!tableBody) {
    throw new Error('Results table not found');
  }
  
  tableBody.innerHTML = '';
  results.forEach(result => {
    const row = document.createElement('tr');
    if (result.status === 'success') {
      row.innerHTML = `
        <td>${result.originalName}</td>
        <td><span class="badge bg-success">Success</span></td>
        <td>${result.convertedName}</td>
        <td>${MagicToolbox.formatFileSize(result.size)}</td>
      `;
    } else {
      row.innerHTML = `
        <td>${result.originalName}</td>
        <td><span class="badge bg-danger">Failed</span></td>
        <td colspan="2"><small class="text-danger">${result.error}</small></td>
      `;
    }
    tableBody.appendChild(row);
  });
  
  document.getElementById('successCount').textContent = successCount;
  
  // Create ZIP file
  if (successCount > 0) {
    const JSZip = window.JSZip;
    if (JSZip) {
      const zip = new JSZip();
      convertedBlobs.forEach(({ blob, filename }) => {
        zip.file(filename, blob);
      });
      
      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const zipUrl = URL.createObjectURL(zipBlob);
      
      const downloadZipBtn = document.getElementById('downloadZipBtn');
      if (downloadZipBtn) {
        downloadZipBtn.href = zipUrl;
        downloadZipBtn.download = 'converted_files.zip';
      }
    }
  }
  
  // Show results
  setTimeout(() => {
    progressSection.style.display = 'none';
    bulkResultSection.style.display = 'block';
    MagicToolbox.showNotification(
      `Converted ${successCount} of ${files.length} files`, 
      successCount > 0 ? 'success' : 'error'
    );
  }, 500);
}
</script>
{% endblock %}
```

### Key JavaScript Principles

1. **Always handle both single and bulk modes** - Check `files.length`
2. **Sequential processing** - Process files one by one, update progress
3. **Proper error handling** - Try/catch with user-friendly messages
4. **Progress feedback** - Show percentage and file count (X/Y)
5. **Use MagicToolbox utilities** - `formatFileSize()`, `showNotification()`
6. **ZIP creation** - Use JSZip library (included in base.html)
7. **Proper cleanup** - Revoke blob URLs when done
8. **CSRF protection** - Always include CSRF token

---

## Bulk Processing Support

### Backend Considerations

The backend `process()` method **does not need special bulk logic**. The frontend JavaScript:
1. Sends files **one at a time** to the API
2. Collects all responses
3. Creates a ZIP file on the client side

**Backend always receives a single file** via `file` parameter, never multiple.

### Frontend Bulk Implementation Checklist

- [ ] File input has `multiple` attribute
- [ ] File input name is `files[]`
- [ ] File list displays all selected files
- [ ] Form submission detects `isBulk` mode (files.length > 1)
- [ ] Bulk handler processes files sequentially
- [ ] Progress shows "X% (n/total)" format
- [ ] Results table shows success/failure for each file
- [ ] ZIP file created with JSZip
- [ ] Download button provides ZIP file
- [ ] Success count displayed

---

## Testing Requirements

### Backend Tests (pytest)

Create `backend/tests/test_your_tool.py`:

```python
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.tools.registry import tool_registry

@pytest.fixture
def tool_instance():
    return tool_registry.get_tool_instance('your-tool-slug')

@pytest.fixture
def sample_file():
    # Create sample file data
    content = b'sample file content'
    return SimpleUploadedFile('test.ext', content, content_type='application/octet-stream')

def test_tool_registration(tool_instance):
    """Test tool is properly registered."""
    assert tool_instance is not None
    assert tool_instance.name == 'your-tool-slug'

def test_validation_success(tool_instance, sample_file):
    """Test validation with valid inputs."""
    parameters = {'output_format': 'target_format'}
    is_valid, error = tool_instance.validate(sample_file, parameters)
    assert is_valid
    assert error is None

def test_validation_missing_parameter(tool_instance, sample_file):
    """Test validation fails with missing parameter."""
    parameters = {}
    is_valid, error = tool_instance.validate(sample_file, parameters)
    assert not is_valid
    assert 'output_format' in error

def test_validation_invalid_format(tool_instance, sample_file):
    """Test validation fails with invalid format."""
    parameters = {'output_format': 'invalid'}
    is_valid, error = tool_instance.validate(sample_file, parameters)
    assert not is_valid

def test_process_success(tool_instance, sample_file):
    """Test file processing succeeds."""
    parameters = {'output_format': 'target_format'}
    output_path, output_filename = tool_instance.process(sample_file, parameters)
    
    assert os.path.exists(output_path)
    assert output_filename.endswith('.target_format')
    
    # Cleanup
    tool_instance.cleanup(output_path)
```

### Minimum Coverage

- Tool registration
- Validation (success and failure cases)
- Processing (at least one format)
- Error handling
- File cleanup

---

## Checklist for New Tools

### Backend Plugin

- [ ] Inherits from `BaseTool`
- [ ] Has all required metadata (name, display_name, description, category, version, icon)
- [ ] Defines `allowed_input_types` and `max_file_size`
- [ ] Implements `validate()` with proper parameter checking
- [ ] Implements `process()` that returns (output_path, output_filename)
- [ ] Uses original filename with new extension for output
- [ ] Cleans up input temp file in `process()` after reading
- [ ] Implements `cleanup()` for output file cleanup
- [ ] Has proper error handling with ToolExecutionError
- [ ] Logs success with file sizes
- [ ] Has type hints on all methods
- [ ] Has comprehensive docstrings

### Frontend Template

- [ ] Extends `base.html`
- [ ] Has breadcrumb navigation
- [ ] Has tool header with icon and description
- [ ] Uses 8/4 column layout (main/sidebar)
- [ ] File input supports multiple files (`multiple` attribute)
- [ ] File input name is `files[]`
- [ ] Includes file list display area
- [ ] Has progress section with animated progress bar
- [ ] Has single file result section
- [ ] Has bulk result section with table
- [ ] Has sidebar with supported formats
- [ ] Has sidebar with features list
- [ ] Includes CSRF token in form

### JavaScript

- [ ] Displays selected files with sizes
- [ ] Shows total size for multiple files
- [ ] Handles form submission
- [ ] Detects single vs bulk mode
- [ ] Implements `handleSingleConversion()`
- [ ] Implements `handleBulkConversion()`
- [ ] Shows progress for each file in bulk mode
- [ ] Creates results table for bulk mode
- [ ] Creates ZIP file with JSZip
- [ ] Uses MagicToolbox utilities
- [ ] Has proper error handling
- [ ] Includes CSRF token in fetch requests
- [ ] Cleans up blob URLs

### Testing

- [ ] Has pytest test file
- [ ] Tests tool registration
- [ ] Tests validation success
- [ ] Tests validation failures
- [ ] Tests processing success
- [ ] Tests error handling
- [ ] Has minimum 80% code coverage

### Documentation

- [ ] Tool has clear description in plugin docstring
- [ ] README updated with new tool
- [ ] API endpoint documented (if custom)

---

## Common Patterns

### File Extension Handling

```python
# Always use original filename with new extension
output_filename = f"{Path(input_file.name).stem}.{output_format}"
```

### Temporary File Management

```python
# Input file - delete immediately after reading
with tempfile.NamedTemporaryFile(delete=False, suffix=input_ext) as tmp_in:
    # Save uploaded file
    temp_input = tmp_in.name

# ... read and process ...

# Delete input immediately
if temp_input and os.path.exists(temp_input):
    os.unlink(temp_input)

# Output file - delete in cleanup() after download
with tempfile.NamedTemporaryFile(delete=False, suffix=output_ext) as tmp_out:
    # Save processed file
    temp_output = tmp_out.name

return temp_output, output_filename
```

### Parameter Validation Pattern

```python
# 1. Check required parameters exist
param = parameters.get('param_name')
if not param:
    return False, "Missing required parameter: param_name"

# 2. Validate value against allowed values
if param not in ALLOWED_VALUES:
    return False, f"Invalid value: {param}"

# 3. For optional numeric parameters
optional_num = parameters.get('optional_num')
if optional_num is not None:
    try:
        optional_num = int(optional_num)
        if not 1 <= optional_num <= 100:
            return False, "Value must be between 1 and 100"
    except (ValueError, TypeError):
        return False, "Value must be an integer"
```

### Progress Bar Pattern (Frontend)

```javascript
// Single file: Animated progress
let progress = 0;
const interval = setInterval(() => {
  progress += 15;
  progressBar.style.width = Math.min(progress, 90) + '%';
  progressText.textContent = Math.min(progress, 90) + '%';
  if (progress >= 90) clearInterval(interval);
}, 150);

// Bulk: Per-file progress
const percent = Math.round(((i + 1) / files.length) * 100);
progressBar.style.width = percent + '%';
progressText.textContent = `${percent}% (${i + 1}/${files.length})`;
```

---

## API Endpoint Pattern

Tools automatically get the following API endpoint:

```
POST /api/v1/tools/{tool-slug}/convert/
```

**Request:**
- `file`: Single uploaded file
- Additional form parameters as defined in tool's `validate()`

**Response:**
- Success: File download with `Content-Disposition` header
- Error: JSON with `{"error": "message"}`

**No custom API views needed** - the framework handles this automatically via `apps/tools/views.py`.

---

## Common Mistakes to Avoid

1. ❌ Creating custom naming logic - Always use original filename + new extension
2. ❌ Not cleaning up input temp files - Delete immediately after reading
3. ❌ Implementing bulk logic in backend - Frontend handles bulk, backend gets single files
4. ❌ Not supporting multiple file selection - Always include `multiple` attribute
5. ❌ Missing error handling - Always try/catch with user-friendly messages
6. ❌ Not logging successes - Always log with file sizes
7. ❌ Forgetting CSRF token - Always include in fetch headers
8. ❌ Not using MagicToolbox utilities - Use `formatFileSize()`, `showNotification()`
9. ❌ Hardcoding tool slug in JavaScript - Replace `YOUR-TOOL-SLUG` with actual slug
10. ❌ Missing type hints or docstrings - Always document your code

---

## Questions?

If you encounter scenarios not covered by this guide, refer to:
- `apps/tools/plugins/image_format_converter.py` - Full-featured example
- `apps/tools/plugins/gpx_kml_converter.py` - Bidirectional conversion example
- `templates/tools/image_format_converter.html` - Complete frontend example
- `templates/tools/gpx_kml_converter.html` - Simplified frontend example

For architecture questions, see:
- `.github/copilot-instructions.md` - Overall project guidelines
- `apps/tools/base.py` - BaseTool abstract class
- `apps/tools/views.py` - Tool API endpoints
- `apps/tools/registry.py` - Tool registration system
