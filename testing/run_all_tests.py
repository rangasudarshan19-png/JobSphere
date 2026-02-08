#!/usr/bin/env python3
"""
Comprehensive Test Runner
Runs all tests and generates report
"""
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def run_command(cmd, description):
    """Run command and return result"""
    print(f"▶ {description}")
    print(f"  Command: {cmd}")
    print("-" * 70)
    
    result = subprocess.run(cmd, shell=True, capture_output=False)
    return result.returncode == 0


def main():
    """Run all test suites"""
    project_root = Path(__file__).parent.parent
    testing_dir = project_root / "testing"
    backend_dir = project_root / "backend" / "python-service"
    
    os.chdir(project_root)
    
    print_header("JobSphere Comprehensive Test Suite")
    print(f"Project Root: {project_root}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Test 1: Backend Email Service Tests
    print_header("TEST 1: Email Service (Gating Verification)")
    results['email_service'] = run_command(
        f"{sys.executable} -m pytest {testing_dir}/backend/test_email_service.py -v --tb=short",
        "Testing email service gating..."
    )
    
    # Test 2: Database Schema Tests
    print_header("TEST 2: Database Schema (Cleanup Verification)")
    results['schema'] = run_command(
        f"{sys.executable} -m pytest {testing_dir}/backend/test_schema.py -v --tb=short",
        "Testing database schema cleanup..."
    )
    
    # Test 3: Notification Service Tests
    print_header("TEST 3: Notification Service (Integration)")
    results['notifications'] = run_command(
        f"{sys.executable} -m pytest {testing_dir}/backend/test_notifications.py -v --tb=short",
        "Testing notification service..."
    )
    
    # Test 4: Integration Tests
    print_header("TEST 4: Integration Tests (End-to-End)")
    results['integration'] = run_command(
        f"{sys.executable} -m pytest {testing_dir}/integration/test_integration.py -v --tb=short",
        "Testing integration workflows..."
    )
    
    # Print Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_status in results.items():
        status = "✅ PASS" if passed_status else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Project is clean and working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test suite(s) failed. See details above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
