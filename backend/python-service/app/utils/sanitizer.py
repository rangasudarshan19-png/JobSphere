"""
Input Sanitization Utilities
Provides functions to sanitize user input and prevent XSS, SQL injection, and other attacks
"""
import re
import html
from typing import Optional, Union, List
from bleach import clean
from bleach.css_sanitizer import CSSSanitizer


class InputSanitizer:
    """
    Comprehensive input sanitization utility class.
    
    Provides multiple sanitization methods for different types of input:
    - HTML content sanitization
    - Plain text sanitization
    - SQL injection prevention helpers
    - Email validation and sanitization
    - URL sanitization
    """
    
    # Allowed HTML tags for rich text (e.g., job descriptions, notes)
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'a', 'span', 'div', 'blockquote', 'code', 'pre'
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'target'],
        'span': ['class'],
        'div': ['class'],
        'code': ['class']
    }
    
    # Allowed URL protocols
    ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']
    
    @staticmethod
    def sanitize_html(text: str, strip_all: bool = False) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.
        
        Args:
            text: Raw HTML string to sanitize
            strip_all: If True, strip all HTML tags completely
            
        Returns:
            Sanitized HTML string safe for display
            
        Example:
            >>> InputSanitizer.sanitize_html('<script>alert("xss")</script><p>Safe</p>')
            '<p>Safe</p>'
        """
        if not text:
            return ""
        
        if strip_all:
            # Remove all HTML tags
            return clean(text, tags=[], strip=True)
        
        # Allow specific safe HTML tags with CSS sanitization
        css_sanitizer = CSSSanitizer(allowed_css_properties=['color', 'background-color', 'font-weight'])
        
        sanitized = clean(
            text,
            tags=InputSanitizer.ALLOWED_TAGS,
            attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
            protocols=InputSanitizer.ALLOWED_PROTOCOLS,
            strip=True,
            css_sanitizer=css_sanitizer
        )
        
        return sanitized
    
    @staticmethod
    def sanitize_plain_text(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize plain text input by encoding HTML entities.
        
        Args:
            text: Raw text string to sanitize
            max_length: Optional maximum length to truncate
            
        Returns:
            Sanitized plain text with HTML entities encoded
            
        Example:
            >>> InputSanitizer.sanitize_plain_text('<script>alert()</script>')
            '&lt;script&gt;alert()&lt;/script&gt;'
        """
        if not text:
            return ""
        
        # Encode HTML entities
        sanitized = html.escape(str(text))
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        # Truncate if needed
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """
        Sanitize and normalize email addresses.
        
        Args:
            email: Raw email string
            
        Returns:
            Normalized lowercase email address
            
        Raises:
            ValueError: If email format is invalid
            
        Example:
            >>> InputSanitizer.sanitize_email('  User@Example.COM  ')
            'user@example.com'
        """
        if not email:
            raise ValueError("Email cannot be empty")
        
        # Remove whitespace and convert to lowercase
        email = email.strip().lower()
        
        # Basic email format validation
        email_regex = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
        if not re.match(email_regex, email):
            raise ValueError("Invalid email format")
        
        # Remove any remaining HTML entities
        email = html.unescape(email)
        
        return email
    
    @staticmethod
    def sanitize_url(url: str, allowed_schemes: Optional[List[str]] = None) -> str:
        """
        Sanitize URL to prevent javascript: and other malicious schemes.
        
        Args:
            url: Raw URL string
            allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
            
        Returns:
            Sanitized URL
            
        Raises:
            ValueError: If URL scheme is not allowed
            
        Example:
            >>> InputSanitizer.sanitize_url('javascript:alert(1)')
            ValueError: URL scheme not allowed
        """
        if not url:
            return ""
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        url = url.strip()
        
        # Check for allowed schemes
        if ':' in url:
            scheme = url.split(':', 1)[0].lower()
            if scheme not in allowed_schemes:
                raise ValueError(f"URL scheme '{scheme}' not allowed")
        
        # Remove any HTML encoding
        url = html.unescape(url)
        
        # Remove javascript: and data: URLs
        dangerous_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'file:',
            r'about:'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                raise ValueError("Malicious URL detected")
        
        return url
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal and command injection.
        
        Args:
            filename: Raw filename string
            
        Returns:
            Safe filename
            
        Example:
            >>> InputSanitizer.sanitize_filename('../../etc/passwd')
            'etc_passwd'
        """
        if not filename:
            return ""
        
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Keep only alphanumeric, dots, hyphens, underscores
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        return filename
    
    @staticmethod
    def sanitize_phone(phone: str) -> str:
        """
        Sanitize phone number input.
        
        Args:
            phone: Raw phone number string
            
        Returns:
            Sanitized phone number with only digits, spaces, hyphens, parentheses, and +
            
        Example:
            >>> InputSanitizer.sanitize_phone('+1 (555) 123-4567<script>')
            '+1 (555) 123-4567'
        """
        if not phone:
            return ""
        
        # Keep only valid phone characters
        phone = re.sub(r'[^\d\s\-\(\)\+]', '', phone)
        
        # Normalize whitespace
        phone = ' '.join(phone.split())
        
        return phone
    
    @staticmethod
    def sanitize_json_string(text: str) -> str:
        """
        Sanitize text intended for JSON encoding.
        
        Args:
            text: Raw text string
            
        Returns:
            Sanitized text safe for JSON
        """
        if not text:
            return ""
        
        # Remove control characters except newline and tab
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        return text
    
    @staticmethod
    def remove_sql_comments(text: str) -> str:
        """
        Remove SQL comment patterns from text (additional protection layer).
        Note: Always use parameterized queries as primary SQL injection protection.
        
        Args:
            text: Text that might contain SQL comments
            
        Returns:
            Text with SQL comment patterns removed
        """
        if not text:
            return ""
        
        # Remove SQL single-line comments
        text = re.sub(r'--.*$', '', text, flags=re.MULTILINE)
        
        # Remove SQL multi-line comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        
        return text.strip()
    
    @staticmethod
    def sanitize_search_query(query: str, max_length: int = 200) -> str:
        """
        Sanitize search query input.
        
        Args:
            query: Raw search query
            max_length: Maximum query length
            
        Returns:
            Sanitized search query
        """
        if not query:
            return ""
        
        # Remove HTML tags
        query = InputSanitizer.sanitize_html(query, strip_all=True)
        
        # Remove SQL comment patterns
        query = InputSanitizer.remove_sql_comments(query)
        
        # Normalize whitespace
        query = ' '.join(query.split())
        
        # Truncate
        if len(query) > max_length:
            query = query[:max_length]
        
        return query


# Convenience functions for common use cases
def sanitize(text: str, type: str = "plain", **kwargs) -> str:
    """
    Convenience function for sanitization.
    
    Args:
        text: Text to sanitize
        type: Type of sanitization ('plain', 'html', 'email', 'url', 'filename', 'phone', 'search')
        **kwargs: Additional arguments passed to specific sanitizer
        
    Returns:
        Sanitized text
        
    Example:
        >>> sanitize('<b>Hello</b>', type='plain')
        '&lt;b&gt;Hello&lt;/b&gt;'
    """
    sanitizer = InputSanitizer()
    
    if type == "plain":
        return sanitizer.sanitize_plain_text(text, **kwargs)
    elif type == "html":
        return sanitizer.sanitize_html(text, **kwargs)
    elif type == "email":
        return sanitizer.sanitize_email(text)
    elif type == "url":
        return sanitizer.sanitize_url(text, **kwargs)
    elif type == "filename":
        return sanitizer.sanitize_filename(text)
    elif type == "phone":
        return sanitizer.sanitize_phone(text)
    elif type == "search":
        return sanitizer.sanitize_search_query(text, **kwargs)
    else:
        # Default to plain text
        return sanitizer.sanitize_plain_text(text)
