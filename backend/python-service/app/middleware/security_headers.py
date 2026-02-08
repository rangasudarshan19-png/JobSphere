"""
Security Headers Middleware for FastAPI
Adds comprehensive security headers to all HTTP responses
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Headers added:
    - Content-Security-Policy (CSP): Prevents XSS and injection attacks
    - Strict-Transport-Security (HSTS): Forces HTTPS connections
    - X-Frame-Options: Prevents clickjacking attacks
    - X-Content-Type-Options: Prevents MIME-sniffing attacks
    - X-XSS-Protection: Enables browser XSS filtering
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and add security headers to the response.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            Response with security headers added
        """
        response = await call_next(request)
        
        # Content Security Policy - Restrict resource loading
        # Allow same-origin by default, specific external sources for CDNs
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https: http:; "
            "connect-src 'self' https://generativelanguage.googleapis.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # HTTP Strict Transport Security - Force HTTPS for 1 year
        # includeSubDomains: Apply to all subdomains
        # preload: Allow inclusion in browser preload lists
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        
        # X-Frame-Options - Prevent clickjacking by disabling framing
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options - Prevent MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection - Enable browser's XSS filtering (legacy browsers)
        # mode=block: Block the page if XSS is detected
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy - Control referrer information sent
        # strict-origin-when-cross-origin: Send full URL for same-origin, origin only for cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy - Control browser features
        # Disable unnecessary browser features for security
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=()"
        )
        
        # X-Permitted-Cross-Domain-Policies - Restrict cross-domain policy files
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Cache-Control for sensitive pages (can be overridden by specific routes)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response
