/**
 * MagicToolbox - Main JavaScript
 * 
 * This file contains common JavaScript functionality used across the application.
 */

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
  // Initialize tooltips
  initTooltips();
  
  // Initialize auto-dismiss alerts
  autoHideAlerts();
  
  // Add fade-in animation to main content
  addFadeInAnimation();
});

/**
 * Initialize Bootstrap tooltips
 */
function initTooltips() {
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function(tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
}

/**
 * Auto-hide alert messages after 5 seconds
 */
function autoHideAlerts() {
  const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
  alerts.forEach(function(alert) {
    setTimeout(function() {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });
}

/**
 * Add fade-in animation to main content
 */
function addFadeInAnimation() {
  const mainContent = document.querySelector('main');
  if (mainContent) {
    mainContent.classList.add('fade-in');
  }
}

/**
 * Utility function to format file size
 * @param {number} bytes - File size in bytes
 * @returns {string} - Formatted file size string
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Validate file before upload
 * @param {File} file - File object to validate
 * @param {Array} allowedTypes - Array of allowed MIME types
 * @param {number} maxSize - Maximum file size in bytes
 * @returns {Object} - Validation result with isValid and message properties
 */
function validateFile(file, allowedTypes, maxSize) {
  // Check file type
  if (allowedTypes && allowedTypes.length > 0) {
    const fileType = file.type;
    const fileExtension = file.name.split('.').pop().toLowerCase();
    
    const isTypeAllowed = allowedTypes.some(type => {
      if (type.includes('*')) {
        const baseType = type.split('/')[0];
        return fileType.startsWith(baseType);
      }
      return fileType === type || fileExtension === type;
    });
    
    if (!isTypeAllowed) {
      return {
        isValid: false,
        message: 'File type not allowed. Please select a valid file.'
      };
    }
  }
  
  // Check file size
  if (maxSize && file.size > maxSize) {
    return {
      isValid: false,
      message: `File size exceeds maximum allowed size of ${formatFileSize(maxSize)}.`
    };
  }
  
  return {
    isValid: true,
    message: 'File is valid.'
  };
}

/**
 * Show loading spinner on button
 * @param {HTMLElement} button - Button element
 * @param {string} text - Loading text (optional)
 */
function showButtonLoading(button, text = 'Processing...') {
  button.disabled = true;
  button.dataset.originalText = button.innerHTML;
  button.innerHTML = `
    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
    ${text}
  `;
}

/**
 * Hide loading spinner on button
 * @param {HTMLElement} button - Button element
 */
function hideButtonLoading(button) {
  button.disabled = false;
  if (button.dataset.originalText) {
    button.innerHTML = button.dataset.originalText;
    delete button.dataset.originalText;
  }
}

/**
 * Show notification toast
 * @param {string} message - Notification message
 * @param {string} type - Type of notification (success, error, warning, info)
 */
function showNotification(message, type = 'info') {
  const alertClass = type === 'error' ? 'danger' : type;
  const iconClass = {
    success: 'bi-check-circle-fill',
    error: 'bi-exclamation-triangle-fill',
    warning: 'bi-exclamation-circle-fill',
    info: 'bi-info-circle-fill'
  }[type] || 'bi-info-circle-fill';
  
  const alertHtml = `
    <div class="alert alert-${alertClass} alert-dismissible fade show" role="alert">
      <i class="bi ${iconClass} me-2"></i>
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;
  
  const container = document.querySelector('.container');
  if (container) {
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHtml;
    container.insertBefore(alertDiv.firstElementChild, container.firstChild);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
      const alert = container.querySelector('.alert');
      if (alert) {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
      }
    }, 5000);
  }
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise} - Promise that resolves when text is copied
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showNotification('Copied to clipboard!', 'success');
    return true;
  } catch (err) {
    showNotification('Failed to copy to clipboard.', 'error');
    return false;
  }
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Export functions for use in other scripts
window.MagicToolbox = {
  formatFileSize,
  validateFile,
  showButtonLoading,
  hideButtonLoading,
  showNotification,
  copyToClipboard,
  debounce
};
