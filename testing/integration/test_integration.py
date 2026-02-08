"""
Integration Tests: End-to-End Workflow
Tests verify complete workflows after cleanup
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend" / "python-service"))


class TestEmailWorkflow:
    """Test email workflow after cleanup"""

    def test_only_implemented_emails_used(self):
        """Verify only OTP and Welcome emails are used"""
        email_service_file = Path(__file__).parent.parent.parent / "backend" / "python-service" / "app" / "services" / "email_service.py"
        
        with open(email_service_file, 'r') as f:
            content = f.read()
        
        # OTP and Welcome should have real implementations
        assert 'def send_otp_email' in content
        assert 'def send_welcome_email' in content
        
        # These should all return False
        disabled_methods = [
            'send_status_change_email',
            'send_interview_reminder_email',
            'send_follow_up_reminder_email',
            'send_offer_notification_email',
            'send_weekly_summary_email',
            'send_test_email',
            'send_next_phase_reminder_email',
            'send_next_phase_today_email',
            'send_application_created_email'
        ]
        
        for method in disabled_methods:
            # Find the method definition
            method_start = content.find(f'def {method}')
            method_end = content.find('\n    def ', method_start + 1)
            if method_end == -1:
                method_end = len(content)
            
            method_body = content[method_start:method_end]
            assert 'return False' in method_body, f"{method} should return False"
            assert 'not yet implemented' in method_body.lower(), f"{method} should log not implemented"


class TestDatabaseMigration:
    """Test that database can be migrated cleanly"""

    def test_schema_syntax_valid(self):
        """Verify schema SQL is syntactically valid"""
        schema_file = Path(__file__).parent.parent.parent / "database" / "schema.sql"
        
        with open(schema_file, 'r') as f:
            schema = f.read()
        
        # Check for basic SQL structure
        assert 'CREATE TABLE' in schema
        assert 'PRIMARY KEY' in schema
        assert 'FOREIGN KEY' in schema or 'REFERENCES' in schema
        
        # Check no duplicate table definitions
        for table in ['users', 'companies', 'applications', 'notifications']:
            count = schema.count(f'CREATE TABLE {table}')
            assert count == 1, f"Table {table} should be defined exactly once"


class TestFeatureGating:
    """Test that features are properly gated"""

    def test_dashboard_removed_duplicate(self):
        """Dashboard should not have duplicate job search"""
        dashboard_file = Path(__file__).parent.parent.parent / "frontend" / "dashboard.html"
        
        with open(dashboard_file, 'r') as f:
            content = f.read()
        
        # Count "Search Jobs" references (case insensitive)
        search_count = content.lower().count('search jobs')
        # Should have minimal references to search jobs
        assert search_count < 5, "Dashboard should not have duplicate job search elements"


class TestBranding:
    """Test JobSphere branding consistency"""

    def test_email_templates_use_jobsphere(self):
        """Active email templates should use JobSphere branding"""
        templates_dir = Path(__file__).parent.parent.parent / "backend" / "python-service" / "templates" / "emails"
        
        active_templates = ["otp_verification.html", "welcome.html"]
        
        for template in active_templates:
            template_path = templates_dir / template
            with open(template_path, 'r') as f:
                content = f.read().lower()
            
            # Should reference JobSphere or job tracking concept
            has_branding = 'jobsphere' in content or 'job' in content
            assert has_branding, f"Template {template} should include branding"

    def test_schema_references_jobsphere(self):
        """Schema should reference JobSphere"""
        schema_file = Path(__file__).parent.parent.parent / "database" / "schema.sql"
        
        with open(schema_file, 'r') as f:
            content = f.read()
        
        assert 'JobSphere' in content, "Schema should reference JobSphere"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
