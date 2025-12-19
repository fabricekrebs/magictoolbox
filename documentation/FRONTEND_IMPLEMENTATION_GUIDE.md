# Frontend Implementation Guide
## Gold Standard History Sidebar Integration

**Last Updated**: December 12, 2025  
**Status**: In Progress

---

## Overview

This guide provides step-by-step instructions for updating existing async tool templates to include the mandatory history sidebar following the gold standard pattern.

---

## ✅ Completed Infrastructure

### 1. **Shared JavaScript Module**
**File**: `static/js/tool-history.js`

**Available Functions**:
```javascript
// Global object: window.ToolHistory

// Load and display history
Tool History.loadHistory(toolName, {
  container: HTMLElement,     // Where to render history items
  loading: HTMLElement,       // Loading indicator
  empty: HTMLElement          // Empty state message
});

// Delete a history item
ToolHistory.deleteHistoryItem(executionId);

// Show delete confirmation modal
ToolHistory.showDeleteConfirmation(executionId, filename);

// Poll execution status
ToolHistory.pollExecutionStatus(executionId, onUpdate, onComplete, onError);

// Utility functions
ToolHistory.formatTimeAgo(timestamp);
ToolHistory.getStatusBadge(status);
ToolHistory.getCsrfToken();
```

### 2. **Shared CSS**
**File**: `static/css/tool-history.css`

**Features**:
- Responsive two-column layout
- Sticky sidebar on desktop (>= 992px)
- Mobile-friendly (history below upload)
- Custom scrollbar styling
- Hover effects and animations
- Color-coded status badges

### 3. **API DELETE Endpoint**
**Endpoint**: `DELETE /api/v1/executions/{id}/`

**Features**:
- Deletes execution record from database
- Removes associated blobs from storage (input & output)
- Returns 204 No Content on success
- Supports both Azurite and Azure Managed Identity

---

## 🔧 Template Update Steps

### Step 1: Add Required Includes

At the top of your template, add the CSS and JS:

```django
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/tool-history.css' %}">
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/tool-history.js' %}"></script>
<script>
  // Your tool-specific JavaScript here
</script>
{% endblock %}
```

### Step 2: Update Container Class

Change from fixed container to fluid:

```django
<!-- Before -->
<div class="container py-5">

<!-- After -->
<div class="container-fluid py-5">
```

### Step 3: Restructure Layout

Add the two-column layout with history sidebar:

```django
<div class="row">
  <!-- LEFT COLUMN: Upload & Processing (8 columns) -->
  <div class="col-lg-8">
    <!-- Your existing upload form and status sections -->
  </div>

  <!-- RIGHT COLUMN: History Sidebar (4 columns) -->
  <div class="col-lg-4 history-sidebar-col">
    <div class="card shadow-sm sticky-sidebar">
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
        <div class="history-sidebar">
          <!-- Loading State -->
          <div id="historyLoading" class="history-loading">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted mt-2 mb-0">Loading history...</p>
          </div>
          
          <!-- Empty State -->
          <div id="historyEmpty" class="history-empty" style="display: none;">
            <i class="bi bi-inbox fs-1 text-muted"></i>
            <p class="text-muted mb-0">No history yet</p>
          </div>
          
          <!-- History Items -->
          <div id="historyItems"></div>
        </div>
      </div>
    </div>
  </div>
</div>
```

### Step 4: Add Delete Modal

Before closing `{% endblock %}`, add the modal:

```django
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
```

### Step 5: Initialize History in JavaScript

In your `{% block extra_js %}` section:

```javascript
document.addEventListener('DOMContentLoaded', function() {
  // Initialize history
  loadToolHistory();
  
  // Refresh button
  document.getElementById('refreshHistoryBtn').addEventListener('click', loadToolHistory);
  
  // Listen for history deletion events
  document.addEventListener('historyDeleted', function() {
    loadToolHistory();
  });
});

function loadToolHistory() {
  const toolName = 'your-tool-name';  // e.g., 'pdf-docx-converter'
  
  ToolHistory.loadHistory(toolName, {
    container: document.getElementById('historyItems'),
    loading: document.getElementById('historyLoading'),
    empty: document.getElementById('historyEmpty')
  });
}

// After successful upload completion, refresh history
function onUploadComplete(data) {
  // ... your existing code ...
  
  // Refresh history
  loadToolHistory();
}
```

### Step 6: Update Status Polling

Use the shared polling function:

```javascript
// After file upload
const pollControl = ToolHistory.pollExecutionStatus(
  executionId,
  // onUpdate callback
  (status, data) => {
    updateProgressBar(status);
  },
  // onComplete callback
  (data) => {
    showDownloadButton(data.downloadUrl, data.outputFilename);
    loadToolHistory();  // Refresh history
  },
  // onError callback
  (error, data) => {
    showError(error);
  }
);

// To stop polling manually:
// pollControl.stop();
```

---

## 📋 Complete Example

See `documentation/ASYNC_FILE_PROCESSING_GOLD_STANDARD.md` for a complete template example with all sections.

---

## 🧪 Testing Checklist

After implementing the history sidebar:

- [ ] History sidebar appears on the right (desktop)
- [ ] History moves below upload form on mobile
- [ ] Loading spinner shows while fetching
- [ ] Empty state displays when no history
- [ ] Last 10 items displayed
- [ ] Status badges are color-coded correctly
- [ ] "Time ago" displays properly (e.g., "2m ago")
- [ ] Download button works for completed items
- [ ] Delete button shows confirmation modal
- [ ] Delete removes item from list and storage
- [ ] Manual refresh button works
- [ ] History auto-refreshes after new upload
- [ ] Responsive design works on mobile
- [ ] Scrollbar appears when >10 items

---

## 🔄 Migration Checklist

For each async tool:

### PDF to DOCX Converter
- [ ] Add CSS/JS includes
- [ ] Update container to fluid
- [ ] Add history sidebar (right column)
- [ ] Add delete modal
- [ ] Initialize history in JS
- [ ] Auto-refresh after conversion
- [ ] Test all features

### Video Rotation
- [ ] Add CSS/JS includes
- [ ] Move existing history to right sidebar
- [ ] Update styling to match gold standard
- [ ] Add delete functionality
- [ ] Add delete modal
- [ ] Update to show last 10 items
- [ ] Add "time ago" display
- [ ] Test all features

### Future Tools
- [ ] Follow gold standard from the start
- [ ] Copy template structure from reference
- [ ] Reuse shared JS/CSS modules
- [ ] Implement all mandatory features

---

## 🎯 Next Steps

1. **Update PDF Converter Template**
   - Most visible tool
   - Complex multi-file support
   - Reference implementation

2. **Update Video Rotation Template**
   - Already has basic history
   - Needs restructuring to sidebar
   - Add delete functionality

3. **Document Template Pattern**
   - Create boilerplate template
   - Easy copy-paste for new tools
   - Maintain consistency

4. **Update Tests**
   - E2E tests for history features
   - Test delete functionality
   - Test responsive design

---

## 📚 Reference Files

- **Gold Standard**: `documentation/ASYNC_FILE_PROCESSING_GOLD_STANDARD.md`
- **Copilot Instructions**: `.github/copilot-instructions.md`
- **Shared JS**: `static/js/tool-history.js`
- **Shared CSS**: `static/css/tool-history.css`
- **API Views**: `apps/tools/views.py` (ToolExecutionViewSet)

---

**Note**: The shared JavaScript module handles all complex logic (AJAX calls, rendering, time formatting, status badges). Your tool-specific code only needs to call the appropriate functions with the correct parameters.
