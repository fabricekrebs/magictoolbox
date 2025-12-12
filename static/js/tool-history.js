/**
 * Shared History Management Module for Async File Processing Tools
 * 
 * Provides consistent history functionality across all async tools following
 * the gold standard pattern.
 */

// ============================================================================
// CONFIGURATION
// ============================================================================
const HISTORY_CONFIG = {
  pollInterval: 5000, // 5 seconds (user requirement)
  maxItems: 10,
  apiBase: '/api/v1'
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get CSRF token from the page
 */
function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

/**
 * Format timestamp as "time ago" string
 * @param {string} timestamp - ISO 8601 timestamp
 * @returns {string} Human-readable time ago (e.g., "2m ago", "1h ago")
 */
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

/**
 * Get status badge HTML
 * @param {string} status - Status: pending, processing, completed, failed
 * @returns {string} HTML for status badge
 */
function getStatusBadge(status) {
  const badges = {
    'pending': '<span class="badge bg-info"><i class="bi bi-clock me-1"></i>Pending</span>',
    'processing': '<span class="badge bg-primary"><i class="bi bi-arrow-repeat me-1"></i>Processing</span>',
    'completed': '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Completed</span>',
    'failed': '<span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>Failed</span>'
  };
  return badges[status] || badges['pending'];
}

/**
 * Truncate filename for display
 * @param {string} filename - Full filename
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated filename
 */
function truncateFilename(filename, maxLength = 30) {
  if (!filename || filename.length <= maxLength) return filename;
  const ext = filename.split('.').pop();
  const name = filename.substring(0, filename.lastIndexOf('.'));
  const truncated = name.substring(0, maxLength - ext.length - 4) + '...';
  return `${truncated}.${ext}`;
}

// ============================================================================
// HISTORY MANAGEMENT
// ============================================================================

/**
 * Load and display execution history (internal function)
 * @param {string} toolName - Tool name to filter by
 * @param {Object} elements - DOM element references
 * @param {HTMLElement} elements.container - Container for history items
 * @param {HTMLElement} elements.loading - Loading indicator element
 * @param {HTMLElement} elements.empty - Empty state element
 */
async function loadHistoryInternal(toolName, elements) {
  const { container, loading, empty } = elements;
  
  // Show loading state
  if (loading) loading.style.display = 'block';
  if (empty) empty.style.display = 'none';
  if (container) container.innerHTML = '';
  
  try {
    const response = await fetch(
      `${HISTORY_CONFIG.apiBase}/executions/?tool_name=${encodeURIComponent(toolName)}&limit=${HISTORY_CONFIG.maxItems}`
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Hide loading state
    if (loading) loading.style.display = 'none';
    
    if (data.results && data.results.length > 0) {
      renderHistoryItems(data.results, container);
    } else {
      if (empty) empty.style.display = 'block';
    }
    
  } catch (error) {
    console.error('Failed to load history:', error);
    if (loading) loading.style.display = 'none';
    if (container) {
      container.innerHTML = `
        <div class="alert alert-danger m-3">
          <i class="bi bi-exclamation-triangle me-2"></i>
          Failed to load history. Please try again.
        </div>
      `;
    }
  }
}

/**
 * Render history items in the container
 * @param {Array} items - Array of execution objects
 * @param {HTMLElement} container - Container element
 */
function renderHistoryItems(items, container) {
  if (!container) return;
  
  container.innerHTML = items.map(item => {
    const statusBadge = getStatusBadge(item.status);
    const timeAgo = formatTimeAgo(item.created_at);
    const canDownload = item.status === 'completed';
    
    return `
      <div class="border-bottom p-2 history-item" 
           data-id="${item.id}"
           data-input="${(item.input_filename || '').toLowerCase()}"
           data-output="${(item.output_filename || '').toLowerCase()}">
        <!-- Status, Time, and Action Buttons on same line -->
        <div class="d-flex justify-content-between align-items-center mb-2">
          <div class="d-flex align-items-center gap-2">
            ${statusBadge}
            <small class="text-muted">${timeAgo}</small>
          </div>
          <div class="btn-group" role="group">
            ${canDownload ? `
              <a href="${HISTORY_CONFIG.apiBase}/executions/${item.id}/download/" 
                 class="btn btn-sm btn-outline-success" 
                 download="${item.output_filename || 'file'}"
                 title="Download">
                <i class="bi bi-download"></i>
              </a>
            ` : `
              <button class="btn btn-sm btn-outline-secondary" disabled title="Not available">
                <i class="bi bi-download"></i>
              </button>
            `}
            <button class="btn btn-sm btn-outline-danger delete-history-btn" 
                    data-id="${item.id}"
                    data-filename="${item.input_filename || 'this item'}"
                    title="Delete">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
        
        <!-- Input Filename (inline) -->
        <div class="mb-1 small">
          <span class="text-muted">In:</span>
          <span class="text-truncate d-inline" style="max-width: 75%;" title="${item.input_filename || 'N/A'}">
            <i class="bi bi-file-earmark"></i>
            ${truncateFilename(item.input_filename, 25)}
          </span>
        </div>
        
        <!-- Output Filename (inline) -->
        ${item.output_filename ? `
          <div class="small">
            <span class="text-muted">Out:</span>
            <span class="text-truncate d-inline" style="max-width: 75%;" title="${item.output_filename}">
              <i class="bi bi-file-earmark-check"></i>
              ${truncateFilename(item.output_filename, 25)}
            </span>
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
  
  // Attach delete event listeners
  container.querySelectorAll('.delete-history-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const id = this.dataset.id;
      const filename = this.dataset.filename;
      showDeleteConfirmation(id, filename);
    });
  });
}

/**
 * Show delete confirmation modal
 * @param {string} executionId - Execution ID to delete
 * @param {string} filename - Filename for display
 */
function showDeleteConfirmation(executionId, filename) {
  const modalElement = document.getElementById('deleteHistoryModal');
  if (!modalElement) {
    console.error('Delete modal not found (expected ID: deleteHistoryModal)');
    return;
  }
  
  // Update modal content
  const modalBody = modalElement.querySelector('.modal-body');
  if (modalBody) {
    modalBody.innerHTML = `
      <p>Are you sure you want to delete this item from history?</p>
      <p class="mb-0"><strong>${filename}</strong></p>
      <small class="text-muted">This will also delete the associated files from storage.</small>
    `;
  }
  
  // Setup confirm button
  const confirmBtn = document.getElementById('confirmDeleteBtn');
  if (confirmBtn) {
    // Remove old event listeners by cloning
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    newConfirmBtn.addEventListener('click', async function() {
      const success = await deleteHistoryItem(executionId);
      const modal = bootstrap.Modal.getInstance(modalElement);
      if (modal) modal.hide();
      
      // Call callbacks
      if (success && window._historyDeleteSuccessCallback) {
        window._historyDeleteSuccessCallback();
      } else if (!success && window._historyDeleteErrorCallback) {
        window._historyDeleteErrorCallback('Failed to delete item');
      }
      
      // Refresh history
      if (success && window._currentHistoryToolName) {
        await loadHistory(window._currentHistoryToolName);
      }
    });
  }
  
  // Show modal
  const modal = new bootstrap.Modal(modalElement);
  modal.show();
}

/**
 * Delete a history item
 * @param {string} executionId - Execution ID to delete
 * @returns {Promise<boolean>} Success status
 */
async function deleteHistoryItem(executionId) {
  try {
    const response = await fetch(`${HISTORY_CONFIG.apiBase}/executions/${executionId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    });
    
    if (response.ok) {
      console.log(`✅ Deleted execution: ${executionId}`);
      
      // Trigger custom event for history refresh
      document.dispatchEvent(new CustomEvent('historyDeleted', { 
        detail: { executionId } 
      }));
      
      return true;
    } else {
      throw new Error(`Failed to delete: HTTP ${response.status}`);
    }
  } catch (error) {
    console.error('Delete failed:', error);
    alert('Failed to delete item. Please try again.');
    return false;
  }
}

// ============================================================================
// STATUS POLLING
// ============================================================================

/**
 * Poll execution status until completion
 * @param {string} executionId - Execution ID to check
 * @param {Function} onUpdate - Callback for status updates (status, data)
 * @param {Function} onComplete - Callback when completed (data)
 * @param {Function} onError - Callback on error (error, data)
 * @returns {Object} Control object with stop() method
 */
function pollExecutionStatus(executionId, onUpdate, onComplete, onError) {
  let intervalId = null;
  let stopped = false;
  
  const checkStatus = async () => {
    if (stopped) return;
    
    try {
      const response = await fetch(`${HISTORY_CONFIG.apiBase}/executions/${executionId}/status/`);
      const data = await response.json();
      
      if (onUpdate) onUpdate(data.status, data);
      
      if (data.status === 'completed') {
        stopPolling();
        if (onComplete) onComplete(data);
      } else if (data.status === 'failed') {
        stopPolling();
        if (onError) onError(data.error || 'Processing failed', data);
      }
    } catch (error) {
      console.error('Status check failed:', error);
      stopPolling();
      if (onError) onError(error.message, null);
    }
  };
  
  const stopPolling = () => {
    stopped = true;
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  };
  
  // Start polling immediately
  checkStatus();
  intervalId = setInterval(checkStatus, HISTORY_CONFIG.pollInterval);
  
  return { stop: stopPolling };
}

/**
 * Public wrapper for loadHistory that automatically finds DOM elements
 * @param {string} toolName - Tool name to filter by
 * @param {Object} options - Optional callbacks
 * @param {Function} options.onDeleteSuccess - Callback when item is deleted successfully
 * @param {Function} options.onDeleteError - Callback when deletion fails
 */
async function loadHistory(toolName, options = {}) {
  const elements = {
    container: document.getElementById('historyList'),
    loading: document.getElementById('historyLoading'),
    empty: document.getElementById('historyEmpty')
  };
  
  // Store current tool name for refresh after delete
  window._currentHistoryToolName = toolName;
  
  // Store callbacks for delete operations
  if (options.onDeleteSuccess) {
    window._historyDeleteSuccessCallback = options.onDeleteSuccess;
  }
  if (options.onDeleteError) {
    window._historyDeleteErrorCallback = options.onDeleteError;
  }
  
  await loadHistoryInternal(toolName, elements);
  
  // Initialize search filter after loading
  initializeSearchFilter();
}

/**
 * Initialize search filter for history items
 */
function initializeSearchFilter() {
  const searchInput = document.getElementById('historySearchInput');
  if (!searchInput) return;
  
  searchInput.addEventListener('input', function(e) {
    const searchTerm = e.target.value.toLowerCase().trim();
    const historyItems = document.querySelectorAll('.history-item');
    
    historyItems.forEach(item => {
      const inputFilename = item.getAttribute('data-input') || '';
      const outputFilename = item.getAttribute('data-output') || '';
      
      const matches = inputFilename.includes(searchTerm) || 
                     outputFilename.includes(searchTerm);
      
      item.style.display = matches ? '' : 'none';
    });
    
    // Show/hide empty state if all filtered out
    const visibleItems = document.querySelectorAll('.history-item:not([style*="display: none"])');
    const emptyState = document.getElementById('historyEmpty');
    const container = document.getElementById('historyList');
    
    if (visibleItems.length === 0 && container && container.children.length > 0) {
      if (emptyState) {
        emptyState.innerHTML = `
          <div class="text-center py-4">
            <i class="bi bi-search text-muted d-block mb-2" style="font-size: 2rem;"></i>
            <p class="text-muted mb-0">No results match "${e.target.value}"</p>
          </div>
        `;
        emptyState.style.display = 'block';
      }
    } else {
      if (emptyState) emptyState.style.display = 'none';
    }
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

// Export as global object for use in templates
window.ToolHistory = {
  loadHistory,
  renderHistoryItems,
  deleteHistoryItem,
  showDeleteConfirmation,
  pollExecutionStatus,
  formatTimeAgo,
  getStatusBadge,
  getCsrfToken
};
