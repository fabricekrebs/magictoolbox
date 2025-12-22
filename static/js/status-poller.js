/**
 * StatusPoller - Polls execution status until completion
 * 
 * Usage:
 *   const poller = new StatusPoller(executionId);
 *   poller.start();
 */

class StatusPoller {
    constructor(executionId, options = {}) {
        this.executionId = executionId;
        this.options = {
            initialInterval: 2000,     // Start at 2 seconds
            maxInterval: 5000,         // Max 5 seconds
            backoffMultiplier: 1.2,    // Increase by 20% each time
            maxAttempts: 150,          // Stop after 150 attempts (5 minutes at 2s)
            onStatusUpdate: null,      // Callback(status, data)
            onComplete: null,          // Callback(data)
            onError: null,             // Callback(error)
            ...options
        };
        
        this.currentInterval = this.options.initialInterval;
        this.attempts = 0;
        this.timeoutId = null;
        this.isRunning = false;
    }
    
    /**
     * Start polling
     */
    start() {
        if (this.isRunning) {
            console.warn('StatusPoller already running');
            return;
        }
        
        this.isRunning = true;
        this.attempts = 0;
        console.log(`🚀 Starting status poller for execution: ${this.executionId}`);
        this.poll();
    }
    
    /**
     * Stop polling
     */
    stop() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
        this.isRunning = false;
        console.log('⏹️ Status poller stopped');
    }
    
    /**
     * Poll status once
     */
    async poll() {
        if (!this.isRunning) return;
        
        this.attempts++;
        
        // Check max attempts
        if (this.attempts > this.options.maxAttempts) {
            console.error('❌ Max polling attempts reached');
            this.stop();
            if (this.options.onError) {
                this.options.onError(new Error('Polling timeout - max attempts reached'));
            }
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/executions/${this.executionId}/status/`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const status = data.status;
            
            console.log(`📊 Status update (attempt ${this.attempts}): ${status}`);
            
            // Call status update callback
            if (this.options.onStatusUpdate) {
                this.options.onStatusUpdate(status, data);
            }
            
            // Check if terminal state
            if (status === 'completed') {
                console.log('✅ Execution completed');
                this.stop();
                if (this.options.onComplete) {
                    this.options.onComplete(data);
                }
                return;
            }
            
            if (status === 'failed') {
                console.error('❌ Execution failed:', data.error_message);
                this.stop();
                if (this.options.onError) {
                    this.options.onError(new Error(data.error_message || 'Execution failed'));
                }
                return;
            }
            
            // Continue polling for pending/processing
            this.scheduleNextPoll();
            
        } catch (error) {
            console.error('❌ Polling error:', error);
            
            // Retry on network errors
            if (this.attempts < this.options.maxAttempts) {
                this.scheduleNextPoll();
            } else {
                this.stop();
                if (this.options.onError) {
                    this.options.onError(error);
                }
            }
        }
    }
    
    /**
     * Schedule next poll with exponential backoff
     */
    scheduleNextPoll() {
        // Increase interval with backoff
        this.currentInterval = Math.min(
            this.currentInterval * this.options.backoffMultiplier,
            this.options.maxInterval
        );
        
        console.log(`⏱️ Next poll in ${Math.round(this.currentInterval)}ms`);
        
        this.timeoutId = setTimeout(() => {
            this.poll();
        }, this.currentInterval);
    }
    
    /**
     * Get current execution status (single request, no polling)
     */
    static async getStatus(executionId) {
        const response = await fetch(`/api/v1/executions/${executionId}/status/`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StatusPoller;
}
