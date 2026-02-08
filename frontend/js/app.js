/**
 * JobSphere — Core JavaScript
 * Auth, Toast, Loading, Modal, Utils, Session
 */

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : window.location.origin;

/* ── Auth ── */
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
        const response = await fetch(url, { ...options, headers });
        if (response.status === 401) {
            this.removeToken();
            Toast.show('Session expired. Please login again.', 'error');
            setTimeout(() => { window.location.href = 'login.html'; }, 1200);
            throw new Error('Unauthorized');
        }
        return response;
    }
    static getUserInfo() {
        return {
            email: sessionStorage.getItem('userEmail') || '',
            name: sessionStorage.getItem('userName') || 'User'
        };
    }
}

/* ── Toast ── */
class Toast {
    static show(message, type = 'info', duration = 3500) {
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.setAttribute('role', 'alert');
        el.innerHTML = `
            <span class="toast-message">${this.escapeHtml(message)}</span>
            <button class="toast-close" aria-label="Dismiss">&times;</button>`;
        el.querySelector('.toast-close').addEventListener('click', () => el.remove());
        this.getContainer().appendChild(el);
        requestAnimationFrame(() => el.classList.add('show'));
        setTimeout(() => {
            el.classList.remove('show');
            setTimeout(() => el.remove(), 350);
        }, duration);
    }
    static getContainer() {
        let c = document.getElementById('toast-container');
        if (!c) { c = document.createElement('div'); c.id = 'toast-container'; document.body.appendChild(c); }
        return c;
    }
    static escapeHtml(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }
}

/* ── Loading ── */
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
                <div class="loading-content"><p>${this.escapeHtml(message)}</p></div>
            </div>`;
        document.body.appendChild(el);
        requestAnimationFrame(() => el.classList.add('show'));
    }
    static hide() {
        const el = document.getElementById('loading-overlay');
        if (el) { el.classList.remove('show'); setTimeout(() => el.remove(), 250); }
    }
    static escapeHtml(str) {
        const d = document.createElement('div'); d.textContent = str; return d.innerHTML;
    }
}

/* ── Modal ── */
class Modal {
    static show(title, content, buttons = []) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');

        const btnsHtml = buttons.map(btn =>
            `<button class="btn ${btn.class || 'btn-primary'}" data-action="${btn.action || ''}">${Toast.escapeHtml(btn.text)}</button>`
        ).join('');

        overlay.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${Toast.escapeHtml(title)}</h3>
                    <button class="modal-close" aria-label="Close">&times;</button>
                </div>
                <div class="modal-body">${content}</div>
                ${btnsHtml ? `<div class="modal-footer">${btnsHtml}</div>` : ''}
            </div>`;

        overlay.querySelector('.modal-close').addEventListener('click', () => Modal.hide());
        overlay.addEventListener('click', e => { if (e.target === overlay) Modal.hide(); });
        buttons.forEach((btn, i) => {
            if (btn.handler) {
                overlay.querySelectorAll('.modal-footer .btn')[i]?.addEventListener('click', btn.handler);
            }
        });

        document.body.appendChild(overlay);
        requestAnimationFrame(() => overlay.classList.add('show'));
    }
    static hide() {
        const m = document.querySelector('.modal-overlay');
        if (m) { m.classList.remove('show'); setTimeout(() => m.remove(), 250); }
    }
}

/* ── Utils ── */
const Utils = {
    formatDate(date) {
        return new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    },
    formatDateTime(date) {
        return new Date(date).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    },
    truncate(str, len = 100) {
        return str.length > len ? str.substring(0, len) + '...' : str;
    },
    debounce(fn, wait) {
        let t;
        return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
    },
    async copyToClipboard(text) {
        try { await navigator.clipboard.writeText(text); Toast.show('Copied to clipboard!', 'success'); }
        catch { Toast.show('Failed to copy', 'error'); }
    }
};

/* ── Session Timeout (10 min) ── */
class SessionTimeout {
    static IDLE_MS = 10 * 60 * 1000;
    static _idle = null;
    static _warn = null;

    static init() {
        if (!Auth.isAuthenticated()) return;
        ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(evt =>
            document.addEventListener(evt, () => this.reset(), { passive: true, capture: true })
        );
        this.reset();
    }
    static reset() {
        clearTimeout(this._idle);
        clearTimeout(this._warn);
        if (!Auth.isAuthenticated()) return;
        this._warn = setTimeout(() => Toast.show('Session expires in 1 minute', 'warning'), this.IDLE_MS - 60000);
        this._idle = setTimeout(() => this.logout(), this.IDLE_MS);
    }
    static logout() {
        Auth.removeToken();
        Toast.show('Session expired. Please log in again.', 'warning');
        setTimeout(() => { window.location.href = 'login.html'; }, 1500);
    }
    static destroy() { clearTimeout(this._idle); clearTimeout(this._warn); }
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => SessionTimeout.init());

/* ── Exports ── */
if (typeof window !== 'undefined') {
    window.Auth = Auth;
    window.Toast = Toast;
    window.Loading = Loading;
    window.Modal = Modal;
    window.Utils = Utils;
    window.SessionTimeout = SessionTimeout;
    window.API_BASE = API_BASE;
}
