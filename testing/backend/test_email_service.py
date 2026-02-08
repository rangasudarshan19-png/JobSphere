"""
Backend Tests: Email Service
Tests verify email gating and functionality after cleanup
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend" / "python-service"))

from app.services.email_service import EmailService


class TestEmailServiceGating:
    """Test that non-implemented emails are properly gated"""

    def setup_method(self):
        """Initialize email service"""
        self.email_service = EmailService()

    def test_status_change_email_disabled(self):
        """Status change email should return False (not implemented)"""
        result = self.email_service.send_status_change_email(
            to_email="test@example.com",
            user_name="Test User",
            company="Test Corp",
            position="Software Engineer",
            old_status="Applied",
            new_status="Interview",
            application_id=1
        )
        assert result is False, "Status change email should be disabled"

    def test_interview_reminder_email_disabled(self):
        """Interview reminder should return False"""
        result = self.email_service.send_interview_reminder_email(
            to_email="test@example.com",
            user_name="Test User",
            company="Test Corp",
            position="Software Engineer",
            interview_date="2025-01-10",
            interview_time="10:00 AM"
        )
        assert result is False, "Interview reminder should be disabled"

    def test_follow_up_reminder_email_disabled(self):
        """Follow-up reminder should return False"""
        result = self.email_service.send_follow_up_reminder_email(
            to_email="test@example.com",
            user_name="Test User",
            company="Test Corp",
            position="Software Engineer",
            days_since_application=7,
            application_id=1
        )
        assert result is False, "Follow-up reminder should be disabled"

    def test_offer_notification_email_disabled(self):
        """Offer notification should return False"""
        result = self.email_service.send_offer_notification_email(
            to_email="test@example.com",
            user_name="Test User",
            company="Test Corp",
            position="Software Engineer"
        )
        assert result is False, "Offer notification should be disabled"

    def test_weekly_summary_email_disabled(self):
        """Weekly summary should return False"""
        result = self.email_service.send_weekly_summary_email(
            to_email="test@example.com",
            user_name="Test User",
            stats={"applications_sent": 5}
        )
        assert result is False, "Weekly summary should be disabled"

    def test_next_phase_reminder_email_disabled(self):
        """Next phase 24h reminder should return False"""
        result = self.email_service.send_next_phase_reminder_email(
            to_email="test@example.com",
            user_name="Test User",
            company="Test Corp",
            position="Software Engineer",
            phase_type="Technical Interview",
            phase_date="2025-01-10",
            phase_time="10:00 AM"
        )
        assert result is False, "Next phase reminder should be disabled"

    def test_next_phase_today_email_disabled(self):
        """Next phase day-of reminder should return False"""
        result = self.email_service.send_next_phase_today_email(
            to_email="test@example.com",
            user_name="Test User",
            company="Test Corp",
            position="Software Engineer",
            phase_type="Technical Interview",
            phase_time="10:00 AM"
        )
        assert result is False, "Next phase day-of should be disabled"

    def test_application_created_email_disabled(self):
        """Application created email should return False"""
        result = self.email_service.send_application_created_email(
            to_email="test@example.com",
            user_name="Test User",
            company="Test Corp",
            position="Software Engineer"
        )
        assert result is False, "Application created email should be disabled"

    def test_test_email_disabled(self):
        """Test email should return False"""
        result = self.email_service.send_test_email(
            to_email="test@example.com",
            user_name="Test User"
        )
        assert result is False, "Test email should be disabled"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
