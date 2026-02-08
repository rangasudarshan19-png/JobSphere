/**
 * Debounce utility for preventing duplicate/spam clicks
 */

class Debouncer {
    constructor(delay = 2000) {
        this.delay = delay;
        this.pendingRequests = new Map();
    }

    /**
     * Execute function only once within the delay period
     * @param {string} key - Unique identifier for this operation
     * @param {function} fn - Function to execute
     * @param {boolean} showLoading - Show loading indicator
     * @returns {Promise} - Result of function execution
     */
    async execute(key, fn, showLoading = true) {
        // If already pending, reject
        if (this.pendingRequests.has(key)) {
            Toast.show('Operation already in progress. Please wait...', 'warning');
            return Promise.reject('Pending');
        }

        // Mark as pending
        this.pendingRequests.set(key, true);

        if (showLoading) {
            Loading.show('Processing...');
        }

        try {
            // Execute the function
            const result = await fn();

            // Wait for delay before allowing next request
            await new Promise(resolve => setTimeout(resolve, this.delay));

            return result;
        } catch (error) {
            throw error;
        } finally {
            // Clear pending state
            this.pendingRequests.delete(key);
            if (showLoading) {
                Loading.hide();
            }
        }
    }

    /**
     * Disable button temporarily during operation
     * @param {string} buttonId - ID of button to disable
     * @param {function} fn - Async function to execute
     * @param {number} cooldown - Cooldown period in ms
     */
    async executeWithButton(buttonId, fn, cooldown = 3000) {
        const button = document.getElementById(buttonId);
        if (!button) return;

        // Prevent double-click
        if (button.disabled) return;

        const originalText = button.innerText;
        const originalClass = button.className;

        try {
            // Disable button
            button.disabled = true;
            button.style.opacity = '0.6';
            button.style.cursor = 'not-allowed';
            button.innerText = '⏳ Processing...';

            // Execute function
            const result = await fn();

            // Show success
            button.innerText = '✅ Done!';
            button.style.backgroundColor = '#4ade80';

            // Reset after delay
            setTimeout(() => {
                button.disabled = false;
                button.innerText = originalText;
                button.className = originalClass;
                button.style.opacity = '1';
                button.style.cursor = 'pointer';
                button.style.backgroundColor = '';
            }, cooldown);

            return result;
        } catch (error) {
            // Show error
            button.innerText = '❌ Error!';
            button.style.backgroundColor = '#ef4444';

            // Reset after delay
            setTimeout(() => {
                button.disabled = false;
                button.innerText = originalText;
                button.className = originalClass;
                button.style.opacity = '1';
                button.style.cursor = 'pointer';
                button.style.backgroundColor = '';
            }, 3000);

            throw error;
        }
    }

    /**
     * Clear all pending requests (useful for cleanup)
     */
    clearAll() {
        this.pendingRequests.clear();
    }
}

// Global debouncer instance
const debouncer = new Debouncer(2000);
