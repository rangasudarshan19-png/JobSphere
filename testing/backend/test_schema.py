"""
Backend Tests: Database Schema
Tests verify schema cleanup and table structure
"""
import pytest
import sys
from pathlib import Path
import sqlite3

# Test database connection and schema
def test_database_schema_clean():
    """Verify cleaned schema only has expected tables"""
    schema_file = Path(__file__).parent.parent.parent / "database" / "schema.sql"
    
    assert schema_file.exists(), "Schema file should exist"
    
    with open(schema_file, 'r') as f:
        schema_content = f.read()
    
    # Tables that should exist
    expected_tables = [
        "users",
        "companies",
        "applications",
        "notifications",
        "notification_preferences",
        "enhanced_resumes",
        "matched_jobs",
        "user_job_preferences"
    ]
    
    for table in expected_tables:
        assert f'CREATE TABLE {table}' in schema_content, f"Table {table} should exist in schema"
    
    # Tables that should NOT exist
    removed_tables = [
        "interview_stages",
        "skills",
        "user_skills",
        "job_skills",
        "interview_questions",
        "resumes",
        "activity_log",
        "reminders"
    ]
    
    for table in removed_tables:
        # Check CREATE TABLE statements (not in comments)
        lines = schema_content.split('\n')
        found = False
        for line in lines:
            if not line.strip().startswith('--') and f'CREATE TABLE {table}' in line:
                found = True
                break
        assert not found, f"Table {table} should be removed from schema"


def test_database_indexes_created():
    """Verify that indexes are created for performance"""
    schema_file = Path(__file__).parent.parent.parent / "database" / "schema.sql"
    
    with open(schema_file, 'r') as f:
        schema_content = f.read()
    
    expected_indexes = [
        "idx_applications_user",
        "idx_applications_status",
        "idx_applications_applied_date",
        "idx_notifications_user",
        "idx_notifications_application",
        "idx_enhanced_resumes_user",
        "idx_matched_jobs_user"
    ]
    
    for index in expected_indexes:
        assert f'CREATE INDEX {index}' in schema_content, f"Index {index} should be created"


def test_branding_updated_in_schema():
    """Verify schema references JobSphere branding"""
    schema_file = Path(__file__).parent.parent.parent / "database" / "schema.sql"
    
    with open(schema_file, 'r') as f:
        content = f.read()
    
    assert 'JobSphere' in content, "Schema should reference JobSphere"
    assert 'job application tracking' in content.lower(), "Schema should describe purpose"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
