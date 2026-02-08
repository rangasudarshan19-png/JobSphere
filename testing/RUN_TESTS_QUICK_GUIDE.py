#!/usr/bin/env python3
"""
Quick Test Command Guide
Copy and paste these commands to run tests
"""

COMMANDS = {
    "Run All Tests (No Dependencies)": """
python testing/run_regression_tests.py
""",

    "Run Backend Tests": """
pytest testing/backend/ -v
""",

    "Run Email Service Tests": """
pytest testing/backend/test_email_service.py -v
""",

    "Run Database Schema Tests": """
pytest testing/backend/test_schema.py -v
""",

    "Run Notification Tests": """
pytest testing/backend/test_notifications.py -v
""",

    "Run Integration Tests": """
pytest testing/integration/ -v
""",

    "Run With Coverage Report": """
pytest testing/backend/ --cov=backend/python-service/app/services --cov-report=html
""",

    "Install Test Dependencies": """
pip install pytest pytest-asyncio httpx fastapi sqlalchemy
""",
}

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  JobSphere Testing - Quick Command Reference")
    print("="*70 + "\n")
    
    for i, (title, cmd) in enumerate(COMMANDS.items(), 1):
        print(f"{i}. {title}")
        print(f"   {cmd.strip()}\n")
    
    print("="*70)
    print("\nFor full documentation, see: testing/README.md")
    print("For test results, see: testing/TEST_REPORT.md")
    print("="*70 + "\n")
