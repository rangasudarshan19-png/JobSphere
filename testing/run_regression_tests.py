#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Local Regression Tests
Tests that don't require external dependencies
"""
import os
import sys
from pathlib import Path

# Set stdout encoding to UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"  {text}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")


def test_passed(name):
    """Print test passed"""
    print(f"  {Colors.GREEN}[PASS]{Colors.END} - {name}")


def test_failed(name, reason):
    """Print test failed"""
    print(f"  {Colors.RED}[FAIL]{Colors.END} - {name}")
    print(f"     Reason: {reason}\n")
    return False


def run_tests():
    """Run all local tests"""
    project_root = Path(__file__).parent.parent
    results = []
    
    print_header("JobSphere Regression Tests - Local Validation")
    print(f"Project Root: {project_root}\n")
    
    # TEST 1: Email templates removed
    print(f"{Colors.BOLD}TEST 1: Email Templates Cleanup{Colors.END}")
    templates_dir = project_root / "backend" / "python-service" / "templates" / "emails"
    
    active_templates = ["base_email.html", "otp_verification.html", "welcome.html"]
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
    
    test_ok = True
    for tmpl in active_templates:
        if (templates_dir / tmpl).exists():
            test_passed(f"Active template exists: {tmpl}")
        else:
            test_ok = test_failed(f"Active template {tmpl}", f"File not found at {templates_dir / tmpl}")
    
    for tmpl in removed_templates:
        if not (templates_dir / tmpl).exists():
            test_passed(f"Removed template deleted: {tmpl}")
        else:
            test_ok = test_failed(f"Template should be removed: {tmpl}", f"File still exists: {templates_dir / tmpl}")
    
    results.append(("Email Templates", test_ok))
    
    # TEST 2: Database schema cleaned
    print(f"\n{Colors.BOLD}TEST 2: Database Schema Cleanup{Colors.END}")
    schema_file = project_root / "database" / "schema.sql"
    
    with open(schema_file, 'r', encoding='utf-8', errors='ignore') as f:
        schema_content = f.read()
    
    test_ok = True
    
    # Check for kept tables
    kept_tables = ["users", "companies", "applications", "notifications", "notification_preferences",
                   "enhanced_resumes", "matched_jobs", "user_job_preferences"]
    
    for table in kept_tables:
        if f"CREATE TABLE {table}" in schema_content:
            test_passed(f"Kept table: {table}")
        else:
            test_ok = test_failed(f"Kept table {table}", f"Table not found in schema")
    
    # Check for removed tables
    removed_tables = ["interview_stages", "skills", "user_skills", "job_skills", 
                      "interview_questions", "resumes", "activity_log", "reminders"]
    
    for table in removed_tables:
        # Simple check - shouldn't have CREATE TABLE for these (except in comments)
        if f"CREATE TABLE {table}" not in schema_content:
            test_passed(f"Removed table: {table}")
        else:
            test_ok = test_failed(f"Removed table {table}", f"Found CREATE TABLE statement for {table}")
    
    # Check JobSphere branding
    if "JobSphere" in schema_content:
        test_passed("Schema branding: JobSphere")
    else:
        test_ok = test_failed("Schema branding", "JobSphere not found in schema")
    
    results.append(("Database Schema", test_ok))
    
    # TEST 3: Email service gating
    print(f"\n{Colors.BOLD}TEST 3: Email Service Gating{Colors.END}")
    email_service_file = project_root / "backend" / "python-service" / "app" / "services" / "email_service.py"
    
    with open(email_service_file, 'r', encoding='utf-8', errors='ignore') as f:
        email_content = f.read()
    
    test_ok = True
    
    # Check that disabled methods return False
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
        if f"def {method}" in email_content:
            # Extract method body
            method_idx = email_content.find(f"def {method}")
            method_end = email_content.find("\n    def ", method_idx + 1)
            if method_end == -1:
                method_end = len(email_content)
            
            method_body = email_content[method_idx:method_end]
            
            if "return False" in method_body and ("not yet implemented" in method_body.lower() or "disabled" in method_body.lower()):
                test_passed(f"Gated method: {method}")
            else:
                test_ok = test_failed(f"Method gating: {method}", "Does not return False or missing log message")
        else:
            test_ok = test_failed(f"Method exists: {method}", "Method definition not found")
    
    results.append(("Email Service Gating", test_ok))
    
    # TEST 4: UI feature gating
    print(f"\n{Colors.BOLD}TEST 4: Frontend Feature Gating{Colors.END}")
    test_ok = True
    
    # Check job matching
    job_matching_file = project_root / "frontend" / "job-matching.html"
    if job_matching_file.exists():
        with open(job_matching_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
        if "not yet implemented" in content or "feature not" in content:
            test_passed("Job matching: feature gating message present")
        else:
            test_ok = test_failed("Job matching gating", "Feature not implemented message not found")
    
    # Check cover letter
    cover_letter_file = project_root / "frontend" / "cover-letter.html"
    if cover_letter_file.exists():
        with open(cover_letter_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
        if "development" in content or "not yet" in content:
            test_passed("Cover letter: feature gating message present")
        else:
            test_ok = test_failed("Cover letter gating", "Development message not found")
    
    # Check dashboard no duplicates
    dashboard_file = project_root / "frontend" / "dashboard.html"
    if dashboard_file.exists():
        with open(dashboard_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        search_count = content.lower().count("search jobs")
        if search_count <= 2:  # Allow extension text in search
            test_passed("Dashboard: no duplicate job search elements")
        else:
            test_ok = test_failed("Dashboard duplicate check", f"Found {search_count} references to 'search jobs'")
    
    results.append(("Frontend Feature Gating", test_ok))
    
    # TEST 5: Notification service gating
    print(f"\n{Colors.BOLD}TEST 5: Notification Service Gating{Colors.END}")
    notification_file = project_root / "backend" / "python-service" / "app" / "services" / "notification_service.py"
    
    with open(notification_file, 'r', encoding='utf-8', errors='ignore') as f:
        notif_content = f.read()
    
    test_ok = True
    
    if "_send_status_change_email" in notif_content:
        # Check if it's gated
        method_idx = notif_content.find("def _send_status_change_email")
        method_end = notif_content.find("\n    def ", method_idx + 1)
        if method_end == -1:
            method_end = len(notif_content)
        
        method_body = notif_content[method_idx:method_end]
        
        if "return False" in method_body and ("not yet implemented" in method_body.lower()):
            test_passed("Status change notification: gated")
        else:
            test_ok = test_failed("Status change gating", "Method should return False with skip message")
    
    results.append(("Notification Service Gating", test_ok))
    
    # SUMMARY
    print_header("Test Summary")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = f"{Colors.GREEN}[PASS]{Colors.END}" if passed else f"{Colors.RED}[FAIL]{Colors.END}"
        print(f"  {status} - {test_name}")
    
    print(f"\n  {Colors.BOLD}Total: {passed_count}/{total_count} test suites passed{Colors.END}\n")
    
    if passed_count == total_count:
        print(f"{Colors.GREEN}{Colors.BOLD}All tests passed! Project is clean and working correctly.{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}WARNING: {total_count - passed_count} test suite(s) failed. See details above.{Colors.END}\n")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
