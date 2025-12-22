/**
 * HistoryManager - Manages execution history sidebar
 * 
 * Usage:
 *   const manager = new HistoryManager('pdf-docx-converter', {
 *       containerId: 'historyList',
 *       limit: 10
 *   });
 *   manager.load();
 */

class HistoryManager {
    constructor(toolName, options = {}) {
        this.toolName = toolName;
        this.options = {
            containerId: 'historyList',
            emptyId: 'historyEmpty',
            loadingId: 'historyLoading',
            limit: 10,
            autoRefresh: false,
            refreshInterval: 30000,  // 30 seconds
            onLoad: null,            // Callback(executions)
            onError: null,           // Callback(error)
            onDelete: null,          // Callback(executionId)
            ...options
        };
        
        this.refreshIntervalId = null;
        this.deleteModalInstance = null;
        this.pendingDeleteId = null;
    }
    
    /**
     * Load history from API
     */
    async load() {
        const container = document.getElementById(this.options.containerId);
        const empty = document.getElementById(this.options.emptyId);
        const loading = document.getElementById(this.options.loadingId);
        
        if (!container) {
            console.error('History container not found:', this.options.containerId);
            return;
        }
        
        // Show loading state
        if (loading) loading.style.display = 'block';
        if (empty) empty.style.display = 'none';
        if (container) container.style.display = 'none';
        
        try {
            const url = `/api/v1/executions/?tool_name=${encodeURIComponent(this.toolName)}&limit=${this.options.limit}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const executions = data.results || [];
            
            console.log(`📜 Loaded ${executions.length} history items for ${this.toolName}`);
            
            // Hide loading
            if (loading) loading.style.display = 'none';
            
            // Show empty state or render items
            if (executions.length === 0) {
                if (empty) empty.style.display = 'block';
            } else {
                this.render(executions);
                if (container) container.style.display = 'block';
            }
            
            // Call callback
            if (this.options.onLoad) {
                this.options.onLoad(executions);
            }
            
        } catch (error) {
            console.error('❌ Error loading history:', error);
            if (loading) loading.style.display = 'none';
            if (empty) {
                empty.innerHTML = '<p class="text-danger small">Failed to load history</p>';
                empty.style.display = 'block';
            }
            
            if (this.options.onError) {
                this.options.onError(error);
            }
        }
    }
    
    /**
     * Render history items
     */
    render(executions) {
        const container = document.getElementById(this.options.containerId);
        if (!container) return;
        
        container.innerHTML = executions.map(exec => this.renderItem(exec)).join('');
        
        // Attach event listeners
        this.attachEventListeners();
    }
    
    /**
     * Render single history item
     */
    renderItem(execution) {
        const statusBadge = this.getStatusBadge(execution.status);
        const timeAgo = this.formatTimeAgo(execution.created_at);
        const hasOutput = execution.status === 'completed';
        
        return `
            <div class="list-group-item list-group-item-action p-2" data-execution-id="${execution.id}">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <div class="flex-grow-1" style="min-width: 0;">
                        <p class="mb-0 small text-truncate" title="${this.escapeHtml(execution.input_filename)}">
                            <i class="bi bi-file-earmark"></i> ${this.escapeHtml(execution.input_filename)}
                        </p>
                        <p class="mb-0 text-muted" style="font-size: 0.75rem;">
                            ${timeAgo}
                        </p>
                    </div>
                    ${statusBadge}
                </div>
                <div class="d-flex gap-1">
                    ${hasOutput ? `
                        <a href="/api/v1/executions/${execution.id}/download/" 
                           class="btn btn-sm btn-outline-success flex-fill"
                           title="Download result"
                           download>
                            <i class="bi bi-download"></i>
                        </a>
                    ` : ''}
                    <button 
                        class="btn btn-sm btn-outline-danger ${hasOutput ? '' : 'flex-fill'} delete-btn"
                        data-execution-id="${execution.id}"
                        title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    /**
     * Get status badge HTML
     */
    getStatusBadge(status) {
        const badges = {
            completed: '<span class="badge bg-success ms-2">completed</span>',
            failed: '<span class="badge bg-danger ms-2">failed</span>',
            processing: '<span class="badge bg-primary ms-2">processing</span>',
            pending: '<span class="badge bg-secondary ms-2">pending</span>',
        };
        return badges[status] || '<span class="badge bg-secondary ms-2">unknown</span>';
    }
    
    /**
     * Format time ago
     */
    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const seconds = Math.floor((new Date() - date) / 1000);
        
        if (seconds < 60) return 'just now';
        
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        
        const days = Math.floor(hours / 24);
        if (days < 7) return `${days}d ago`;
        
        return date.toLocaleDateString();
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Attach event listeners to history items
     */
    attachEventListeners() {
        const deleteButtons = document.querySelectorAll('.delete-btn');
        deleteButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const executionId = btn.dataset.executionId;
                this.confirmDelete(executionId);
            });
        });
    }
    
    /**
     * Confirm delete with modal
     */
    confirmDelete(executionId) {
        this.pendingDeleteId = executionId;
        
        const modalEl = document.getElementById('deleteModal');
        if (!modalEl) {
            console.error('Delete modal not found');
            return;
        }
        
        if (!this.deleteModalInstance) {
            this.deleteModalInstance = new bootstrap.Modal(modalEl);
            
            // Attach confirm button listener once
            const confirmBtn = document.getElementById('confirmDeleteBtn');
            if (confirmBtn) {
                confirmBtn.addEventListener('click', () => {
                    this.delete(this.pendingDeleteId);
                });
            }
        }
        
        this.deleteModalInstance.show();
    }
    
    /**
     * Delete execution
     */
    async delete(executionId) {
        if (!executionId) return;
        
        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            const response = await fetch(`/api/v1/executions/${executionId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken || ''
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            console.log(`🗑️ Deleted execution: ${executionId}`);
            
            // Hide modal and reload
            if (this.deleteModalInstance) {
                this.deleteModalInstance.hide();
            }
            
            this.load();
            
            if (this.options.onDelete) {
                this.options.onDelete(executionId);
            }
            
        } catch (error) {
            console.error('❌ Delete failed:', error);
            alert('Failed to delete execution. Please try again.');
        }
    }
    
    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
        if (this.refreshIntervalId) {
            console.warn('Auto-refresh already running');
            return;
        }
        
        console.log(`🔄 Starting auto-refresh every ${this.options.refreshInterval}ms`);
        this.refreshIntervalId = setInterval(() => {
            this.load();
        }, this.options.refreshInterval);
    }
    
    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshIntervalId) {
            clearInterval(this.refreshIntervalId);
            this.refreshIntervalId = null;
            console.log('⏹️ Auto-refresh stopped');
        }
    }
    
    /**
     * Cleanup
     */
    destroy() {
        this.stopAutoRefresh();
        this.deleteModalInstance = null;
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HistoryManager;
}
