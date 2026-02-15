/**
 * JobSphere — Core JavaScript v2.0
 * Auth, Toast, Loading, Modal, Utils, SessionTimeout, Notifications
 */

const API_BASE = (() => {
    const h = window.location.hostname;
    if (!h || h === 'localhost' || h === '127.0.0.1') return 'http://127.0.0.1:8000';
    return window.location.origin;
})();

/* ═══════════════════════════════════
   AUTH
   ═══════════════════════════════════ */
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
        sessionStorage.removeItem('isAdmin');
    }
    static isAuthenticated() {
        return !!this.getToken();
    }
    static logout() {
        this.removeToken();
        Toast.show('Signed out successfully', 'info', 2000);
        setTimeout(() => { window.location.href = 'login.html'; }, 500);
    }
    static async requireAuth() {
        if (!this.isAuthenticated()) {
            Toast.show('Please login to continue', 'warning');
            setTimeout(() => { window.location.href = 'login.html'; }, 1200);
            return false;
        }
        return true;
    }
    static async fetchWithAuth(url, options = {}) {
        const token = this.getToken();
        const headers = { 'Content-Type': 'application/json', ...options.headers };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        try {
            const response = await fetch(url, { ...options, headers });
            if (response.status === 401) {
                this.removeToken();
                Toast.show('Session expired. Please login again.', 'error');
                setTimeout(() => { window.location.href = 'login.html'; }, 1500);
                throw new Error('Unauthorized');
            }
            return response;
        } catch (err) {
            if (err.message === 'Unauthorized') throw err;
            if (err.name === 'TypeError' && err.message.includes('fetch')) {
                Toast.show('Cannot reach the server. Is the backend running?', 'error');
            }
            throw err;
        }
    }
    static getUserInfo() {
        return {
            email: sessionStorage.getItem('userEmail') || '',
            name: sessionStorage.getItem('userName') || 'User'
        };
    }
    static getInitials() {
        const name = this.getUserInfo().name;
        return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2) || 'U';
    }
}

/* ═══════════════════════════════════
   TOAST — Enhanced with progress bar
   ═══════════════════════════════════ */
class Toast {
    static ICONS = {
        info: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
        success: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        warning: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        error: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
    };
    static MAX_TOASTS = 5;

    static show(message, type = 'info', duration = 4000) {
        const container = this._container();
        
        // Limit max visible toasts
        while (container.children.length >= this.MAX_TOASTS) {
            this._dismiss(container.firstElementChild);
        }

        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.setAttribute('role', 'alert');
        el.setAttribute('aria-live', 'assertive');
        el.style.setProperty('--toast-duration', `${duration}ms`);
        el.innerHTML = `
            <span class="toast-icon"></span>
            <span class="toast-message">${this.escape(message)}</span>
            <button class="toast-close" aria-label="Dismiss">&times;</button>
            <div class="toast-progress"></div>`;
        el.querySelector('.toast-close').addEventListener('click', () => this._dismiss(el));
        container.appendChild(el);
        requestAnimationFrame(() => el.classList.add('show'));
        el._timer = setTimeout(() => this._dismiss(el), duration);
    }

    static _dismiss(el) {
        if (!el || !el.parentNode) return;
        clearTimeout(el._timer);
        el.classList.remove('show');
        el.style.transform = 'translateX(110%)';
        setTimeout(() => { if (el.parentNode) el.remove(); }, 400);
    }

    static _container() {
        let c = document.getElementById('toast-container');
        if (!c) {
            c = document.createElement('div');
            c.id = 'toast-container';
            document.body.appendChild(c);
        }
        return c;
    }

    static escape(str) {
        if (!str) return '';
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }
    static escapeHtml(str) { return this.escape(str); }
}

/* ═══════════════════════════════════
   LOADING — Enhanced with dots animation
   ═══════════════════════════════════ */
class Loading {
    static show(message = 'Loading...') {
        if (document.getElementById('loading-overlay')) return;
        const el = document.createElement('div');
        el.id = 'loading-overlay';
        el.setAttribute('role', 'status');
        el.setAttribute('aria-live', 'polite');
        el.innerHTML = `
            <div class="loading-card">
                <div class="loading-spinner"></div>
                <div class="loading-content"><p>${Toast.escape(message)}</p></div>
                <div class="loading-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>`;
        document.body.appendChild(el);
        requestAnimationFrame(() => el.classList.add('show'));
    }
    static hide() {
        const el = document.getElementById('loading-overlay');
        if (el) { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }
    }
    static async wrap(asyncFn, message = 'Loading...') {
        this.show(message);
        try { return await asyncFn(); }
        finally { this.hide(); }
    }
}

/* ═══════════════════════════════════
   MODAL — Enhanced with focus trap
   ═══════════════════════════════════ */
class Modal {
    static show(title, content, buttons = []) {
        this.hide();

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-label', title);

        const btnsHtml = buttons.map((btn, i) =>
            `<button class="btn ${btn.class || 'btn-primary'}" data-modal-btn="${i}">${Toast.escape(btn.text || btn.label || 'OK')}</button>`
        ).join('');

        overlay.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${Toast.escape(title)}</h3>
                    <button class="modal-close" aria-label="Close">&times;</button>
                </div>
                <div class="modal-body">${content}</div>
                ${btnsHtml ? `<div class="modal-footer">${btnsHtml}</div>` : ''}
            </div>`;

        overlay.querySelector('.modal-close').addEventListener('click', () => Modal.hide());
        overlay.addEventListener('click', e => { if (e.target === overlay) Modal.hide(); });
        document.addEventListener('keydown', Modal._escHandler);

        buttons.forEach((btn, i) => {
            const el = overlay.querySelector(`[data-modal-btn="${i}"]`);
            if (el && btn.handler) el.addEventListener('click', btn.handler);
        });

        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';
        requestAnimationFrame(() => overlay.classList.add('show'));
        
        // Focus first button or close button
        const firstFocusable = overlay.querySelector('button');
        if (firstFocusable) setTimeout(() => firstFocusable.focus(), 100);
    }

    static hide() {
        document.removeEventListener('keydown', Modal._escHandler);
        const m = document.querySelector('.modal-overlay');
        if (m) { 
            m.classList.remove('show'); 
            document.body.style.overflow = '';
            setTimeout(() => m.remove(), 250); 
        }
    }

    static confirm(title, message) {
        return new Promise(resolve => {
            Modal.show(title, `<p>${Toast.escape(message)}</p>`, [
                { text: 'Cancel', class: 'btn-ghost', handler: () => { Modal.hide(); resolve(false); } },
                { text: 'Confirm', class: 'btn-primary', handler: () => { Modal.hide(); resolve(true); } }
            ]);
        });
    }

    static _escHandler = (e) => { if (e.key === 'Escape') Modal.hide(); };
}

/* ═══════════════════════════════════
   NOTIFICATION CARDS — Inline UI feedback
   ═══════════════════════════════════ */
class NotificationCard {
    static show(container, type, title, message, dismissable = true) {
        const iconMap = {
            info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
            warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
            error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
            success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
        };
        const card = document.createElement('div');
        card.className = `${type}-card fade-in`;
        card.innerHTML = `
            <div class="${type}-card-icon">${iconMap[type] || 'ℹ️'}</div>
            <div class="${type}-card-content">
                <h4>${Toast.escape(title)}</h4>
                <p>${Toast.escape(message)}</p>
            </div>
            ${dismissable ? `<button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:1.25rem;padding:4px;margin-left:auto;align-self:flex-start;border-radius:4px;transition:all 0.15s" onmouseover="this.style.color='var(--text-primary)'" onmouseout="this.style.color='var(--text-muted)'">&times;</button>` : ''}
        `;
        const target = typeof container === 'string' ? document.querySelector(container) : container;
        if (target) target.prepend(card);
        return card;
    }

    static info(container, title, message, dismissable = true) { return this.show(container, 'info', title, message, dismissable); }
    static warning(container, title, message, dismissable = true) { return this.show(container, 'warning', title, message, dismissable); }
    static error(container, title, message, dismissable = true) { return this.show(container, 'error', title, message, dismissable); }
    static success(container, title, message, dismissable = true) { return this.show(container, 'success', title, message, dismissable); }
}

/* ═══════════════════════════════════
   UTILS
   ═══════════════════════════════════ */
const Utils = {
    formatDate(date) {
        if (!date) return '—';
        return new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    },
    formatDateTime(date) {
        if (!date) return '—';
        return new Date(date).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    },
    timeAgo(date) {
        const s = Math.floor((Date.now() - new Date(date)) / 1000);
        if (s < 60) return 'just now';
        if (s < 3600) return `${Math.floor(s/60)}m ago`;
        if (s < 86400) return `${Math.floor(s/3600)}h ago`;
        if (s < 604800) return `${Math.floor(s/86400)}d ago`;
        return Utils.formatDate(date);
    },
    truncate(str, len = 100) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '…' : str;
    },
    debounce(fn, wait = 300) {
        let t;
        return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
    },
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            Toast.show('Copied to clipboard!', 'success', 2000);
        } catch {
            Toast.show('Failed to copy', 'error');
        }
    },
    slugify(str) {
        return str.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    },
    // Animate a number counting up
    animateCounter(element, target, duration = 800) {
        const start = parseInt(element.textContent) || 0;
        const startTime = performance.now();
        const update = (now) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            element.textContent = Math.round(start + (target - start) * eased);
            if (progress < 1) requestAnimationFrame(update);
        };
        requestAnimationFrame(update);
    },
    // Validate email properly
    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    },
    // Sanitize HTML to prevent XSS
    sanitizeHTML(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }
};

/* ═══════════════════════════════════
   SESSION TIMEOUT (10 min)
   ═══════════════════════════════════ */
class SessionTimeout {
    static IDLE_MS = 10 * 60 * 1000;
    static _idle = null;
    static _warn = null;

    static init() {
        if (!Auth.isAuthenticated()) return;
        const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
        events.forEach(evt =>
            document.addEventListener(evt, () => this.reset(), { passive: true, capture: true })
        );
        this.reset();
    }
    static reset() {
        clearTimeout(this._idle);
        clearTimeout(this._warn);
        if (!Auth.isAuthenticated()) return;
        this._warn = setTimeout(() => {
            Toast.show('Your session will expire in 1 minute. Move your mouse to stay signed in.', 'warning', 6000);
        }, this.IDLE_MS - 60000);
        this._idle = setTimeout(() => {
            Auth.removeToken();
            Toast.show('Session expired due to inactivity.', 'warning');
            setTimeout(() => { window.location.href = 'login.html'; }, 1500);
        }, this.IDLE_MS);
    }
    static destroy() {
        clearTimeout(this._idle);
        clearTimeout(this._warn);
    }
}

/* ═══════════════════════════════════
   CONNECTION STATUS MONITOR
   ═══════════════════════════════════ */
class ConnectionMonitor {
    static _isOnline = navigator.onLine;
    static _indicator = null;

    static init() {
        window.addEventListener('online', () => this._update(true));
        window.addEventListener('offline', () => this._update(false));
    }

    static _update(online) {
        this._isOnline = online;
        if (!online) {
            Toast.show('You are offline. Some features may be unavailable.', 'warning', 6000);
        } else {
            Toast.show('Connection restored.', 'success', 2000);
        }
    }

    static get isOnline() { return this._isOnline; }
}

/* ═══════════════════════════════════
   NAVBAR SCROLL EFFECT
   ═══════════════════════════════════ */
function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    const onScroll = () => {
        navbar.classList.toggle('scrolled', window.scrollY > 20);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
}

/* ═══════════════════════════════════
   PAGE VISIBILITY — Pause animations when hidden
   ═══════════════════════════════════ */
function initVisibilityHandler() {
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            document.body.classList.add('tab-hidden');
        } else {
            document.body.classList.remove('tab-hidden');
        }
    });
}

/* ═══════════════════════════════════
   SCROLL ANIMATIONS — IntersectionObserver
   ═══════════════════════════════════ */
function initScrollAnimations() {
    const observer = new IntersectionObserver(entries => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.style.animationPlayState = 'running';
                observer.unobserve(e.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.fade-in, .fade-in-up, .fade-in-left, .fade-in-right, .slide-up').forEach(el => {
        el.style.animationPlayState = 'paused';
        observer.observe(el);
    });
}

/* ═══════════════════════════════════
   INIT
   ═══════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    SessionTimeout.init();
    ConnectionMonitor.init();
    initNavbarScroll();
    initVisibilityHandler();
    initScrollAnimations();
    
    // Add page transition class
    document.body.classList.add('page-transition');
});

/* ═══════════════════════════════════
   EXPORTS
   ═══════════════════════════════════ */
if (typeof window !== 'undefined') {
    window.Auth = Auth;
    window.Toast = Toast;
    window.Loading = Loading;
    window.Modal = Modal;
    window.NotificationCard = NotificationCard;
    window.Utils = Utils;
    window.SessionTimeout = SessionTimeout;
    window.ConnectionMonitor = ConnectionMonitor;
    window.API_BASE = API_BASE;
}
