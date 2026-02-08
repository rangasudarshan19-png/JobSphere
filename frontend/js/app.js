/**
 * JobSphere - Core JavaScript Utilities
 */

// API Configuration
const API_BASE = 'http://127.0.0.1:8000';

// Authentication Helper
class Auth {
    static getToken() {
        return sessionStorage.getItem('access_token') || sessionStorage.getItem('token');
    }

    static setToken(token) {
        sessionStorage.setItem('access_token', token);
    }

    static removeToken() {
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('userEmail');
        sessionStorage.removeItem('userName');
    }

    static isAuthenticated() {
        return !!this.getToken();
    }

    static async requireAuth(redirectUrl = '/login.html') {
        if (!this.isAuthenticated()) {
            Toast.show('Please login to continue', 'warning');
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 1500);
            return false;
        }
        return true;
    }

    static async fetchWithAuth(url, options = {}) {
        const token = this.getToken();
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, { ...options, headers });
            
            if (response.status === 401) {
                this.removeToken();
                Toast.show('Session expired. Please login again.', 'error');
                setTimeout(() => window.location.href = '/login.html', 1500);
                throw new Error('Unauthorized');
            }

            return response;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    static getUserInfo() {
        return {
            email: sessionStorage.getItem('userEmail') || 'user@example.com',
            name: sessionStorage.getItem('userName') || 'User'
        };
    }
}

// Toast Notifications
class Toast {
    static show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;

        const container = this.getContainer();
        container.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    static getContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }
}

// Loading Overlay
class Loading {
    static show(message = 'Loading...') {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-card">
                <div class="loading-spinner"></div>
                <div class="loading-content">
                    <p>${message}</p>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        setTimeout(() => overlay.classList.add('show'), 10);
    }

    static hide() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(() => overlay.remove(), 300);
        }
    }
}

// Modal Dialog
class Modal {
    static show(title, content, buttons = []) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        
        const buttonsHtml = buttons.map(btn => 
            `<button class="btn ${btn.class || 'btn-primary'}" onclick="${btn.onclick}">${btn.text}</button>`
        ).join('');

        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                <div class="modal-footer">
                    ${buttonsHtml}
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
    }

    static hide() {
        const modal = document.querySelector('.modal-overlay');
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        }
    }
}

// Utility Functions
const Utils = {
    formatDate(date) {
        return new Date(date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    formatDateTime(date) {
        return new Date(date).toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    truncate(str, length = 100) {
        return str.length > length ? str.substring(0, length) + '...' : str;
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            Toast.show('Copied to clipboard!', 'success');
        }).catch(() => {
            Toast.show('Failed to copy', 'error');
        });
    }
};

// Session Timeout Manager - 10 minutes idle time
class SessionTimeout {
    static IDLE_TIME = 10 * 60 * 1000; // 10 minutes in milliseconds
    static idleTimer = null;
    static warningTimer = null;
    static isWarningShown = false;

    static init() {
        if (!Auth.isAuthenticated()) {
            return; // Don't initialize if user is not logged in
        }

        // Set up activity listeners
        const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
        events.forEach(event => {
            document.addEventListener(event, () => this.resetTimer(), true);
        });

        // Start the idle timer
        this.resetTimer();
        
        console.log(`✅ Session timeout initialized: ${this.IDLE_TIME / 60000} minutes idle time`);
    }

    static resetTimer() {
        // Clear existing timers
        clearTimeout(this.idleTimer);
        clearTimeout(this.warningTimer);
        this.isWarningShown = false;

        // Check if user is still authenticated
        if (!Auth.isAuthenticated()) {
            return;
        }

        // Show warning at 9 minutes
        this.warningTimer = setTimeout(() => {
            if (!this.isWarningShown) {
                this.isWarningShown = true;
                Toast.show('⏰ Your session will expire in 1 minute due to inactivity', 'warning');
            }
        }, (this.IDLE_TIME - 60000)); // 9 minutes

        // Logout at 10 minutes
        this.idleTimer = setTimeout(() => {
            this.logout();
        }, this.IDLE_TIME);
    }

    static logout() {
        Auth.removeToken();
        localStorage.clear();
        Toast.show('🔒 Session expired due to inactivity. Please log in again.', 'warning');
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 2000);
    }

    static destroy() {
        clearTimeout(this.idleTimer);
        clearTimeout(this.warningTimer);
    }
}

// Auto-initialize session timeout on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        SessionTimeout.init();
    });
} else {
    SessionTimeout.init();
}

// Export for use in modules
if (typeof window !== 'undefined') {
    window.Auth = Auth;
    window.Toast = Toast;
    window.Loading = Loading;
    window.Modal = Modal;
    window.Utils = Utils;
    window.SessionTimeout = SessionTimeout;
    window.API_BASE = API_BASE;
}
