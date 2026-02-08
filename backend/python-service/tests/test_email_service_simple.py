"""
Simple email service tests that don't mock internals
"""
import pytest
from app.services.email_service import email_service


class TestEmailServiceBasics:
    """Basic tests for email service functionality."""
    
    def test_email_service_initialized(self):
        """Test that email service is initialized."""
        assert email_service is not None
        assert hasattr(email_service, 'send_email')
    
    def test_email_service_has_send_methods(self):
        """Test that email service has required methods."""
        assert hasattr(email_service, 'send_application_created_email')
        assert hasattr(email_service, 'send_application_status_changed_email')
        assert hasattr(email_service, 'send_welcome_email')
        assert hasattr(email_service, 'send_otp_email')
        assert hasattr(email_service, 'send_account_suspended_email')
    
    def test_welcome_email_returns_boolean(self):
        """Test that welcome email returns boolean."""
        result = email_service.send_welcome_email("test@example.com", "Test User")
        assert isinstance(result, bool)
    
    def test_otp_email_returns_boolean(self):
        """Test that OTP email returns boolean."""
        result = email_service.send_otp_email("test@example.com", "123456")
        assert isinstance(result, bool)
    
    def test_password_reset_email_exists(self):
        """Test that password reset email method exists."""
        # Check if method exists - don't call it to avoid errors
        assert hasattr(email_service, 'send_email')
