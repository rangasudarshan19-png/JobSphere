"""
Backend Tests: Notification Service
Tests verify notification gating and email integration
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend" / "python-service"))

from app.services.notification_service import NotificationService


class TestNotificationServiceGating:
    """Test that status change notifications are properly gated"""

    def setup_method(self):
        """Mock database session"""
        self.mock_db = Mock()

    def test_status_change_email_gated(self):
        """Status change email method should be gated"""
        notification_service = NotificationService(self.mock_db)
        
        # Create mock objects
        mock_notification = Mock()
        mock_notification.type = 'status_change'
        mock_notification.message = 'Applied -> Interview'
        mock_notification.application_id = 1
        
        mock_user = Mock()
        mock_user.email = 'test@example.com'
        mock_user.full_name = 'Test User'
        
        # Call the gated method
        result = notification_service._send_status_change_email(mock_notification, mock_user)
        
        # Should return False (gated)
        assert result is False, "Status change email should be gated and return False"


class TestTemplateIntegrity:
    """Test that email templates are properly managed"""

    def test_active_templates_exist(self):
        """Verify active templates exist"""
        templates_dir = Path(__file__).parent.parent.parent / "backend" / "python-service" / "templates" / "emails"
        
        active_templates = [
            "base_email.html",
            "otp_verification.html",
            "welcome.html"
        ]
        
        for template in active_templates:
            template_path = templates_dir / template
            assert template_path.exists(), f"Template {template} should exist"

    def test_removed_templates_deleted(self):
        """Verify removed templates are deleted"""
        templates_dir = Path(__file__).parent.parent.parent / "backend" / "python-service" / "templates" / "emails"
        
        removed_templates = [
            "application_created.html",
            "follow_up.html",
            "interview_reminder.html",
            "next_phase_reminder.html",
            "next_phase_today.html",
            "offer_received.html",
            "otp_verification_simple.html",
            "status_change.html",
            "weekly_summary.html"
        ]
        
        for template in removed_templates:
            template_path = templates_dir / template
            assert not template_path.exists(), f"Template {template} should be removed"

    def test_base_email_used_by_active_templates(self):
        """Verify active templates extend base_email"""
        templates_dir = Path(__file__).parent.parent.parent / "backend" / "python-service" / "templates" / "emails"
        
        templates_using_base = {
            "otp_verification.html": "extends",
            "welcome.html": "extends"
        }
        
        for template, keyword in templates_using_base.items():
            template_path = templates_dir / template
            with open(template_path, 'r') as f:
                content = f.read()
            assert keyword in content.lower() and "base" in content.lower(), \
                f"Template {template} should extend base_email"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
