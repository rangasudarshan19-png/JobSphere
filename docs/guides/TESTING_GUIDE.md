# Testing and Quality Assurance Guide

## Overview
This document describes the testing strategy, quality assurance processes, and best practices for the JobSphere application.

**Current Status:** 51/51 backend tests passing (32.8% code coverage, 30% threshold met)

---

## Test Architecture

### Test Levels
1. **Unit Tests** - Test individual functions/methods in isolation
2. **Integration Tests** - Test multiple components working together
3. **End-to-End Tests** - Test complete user workflows

### Test Structure
```
backend/python-service/tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── test_auth.py                   # Authentication tests (login, register, profile)
├── test_applications.py           # Application CRUD tests
├── test_analytics.py              # Analytics endpoint tests
├── test_email_service_simple.py   # Email service tests
└── test_integration_workflows.py  # Integration workflow tests

testing/
├── backend/
│   ├── conftest.py
│   ├── test_email_service.py
│   ├── test_notifications.py
│   └── test_schema.py
├── frontend/
│   ├── conftest.py
│   └── test_feature_gating.py
├── integration/
│   └── test_integration.py
├── E2E_FULL_TEST.py
├── E2E_TEST_VERIFICATION.py
├── run_all_tests.py
├── run_regression_tests.py
└── RUN_TESTS_QUICK_GUIDE.py
```

---

## Running Tests

### Prerequisites
```bash
cd backend/python-service
pip install -r requirements.txt
```

### Basic Commands

**Run all tests:**
```bash
cd backend/python-service
python -m pytest tests/ -v
```

**Run with verbose output and short tracebacks:**
```bash
pytest tests/ -v --tb=short
```

**Run specific test file:**
```bash
pytest tests/test_auth.py
```

**Run specific test class:**
```bash
pytest tests/test_auth.py::TestLogin
```

**Run specific test:**
```bash
pytest tests/test_auth.py::TestLogin::test_login_success
```

**Stop on first failure:**
```bash
pytest -x
```

**Show print statements:**
```bash
pytest -s
```

---

## Code Coverage

### Generate Coverage Report

**Terminal report:**
```bash
pytest --cov=app --cov-report=term-missing
```

**HTML report:**
```bash
pytest --cov=app --cov-report=html
# Open coverage_html/index.html in browser
```

### Coverage Targets
- **Overall**: 30%+ (currently 32.8%)
- **Critical paths** (auth, applications): 80%+
- **Models**: 100%
- **Services**: 25%+

### Current Coverage by Module (as of Feb 2026)

| Module | Coverage |
|--------|----------|
| Models (all) | 100% |
| Middleware | 83-100% |
| Utils | 73-92% |
| Routers/auth | 45% |
| Routers/applications | 83% |
| Routers/analytics | 59% |
| Routers/reviews | 45% |
| Services | 10-42% |

---

## Test Fixtures

### Available Fixtures (from conftest.py)

#### Database Fixtures
- `engine` - Test database engine (in-memory SQLite)
- `db_session` - Database session for tests

#### Client Fixture
- `client` - FastAPI TestClient with database override

#### User Fixtures
- `test_user` - Regular user (email: test@example.com)
- `admin_user` - Admin user (email: admin@example.com)
- `auth_headers` - Authentication headers for test_user
- `admin_auth_headers` - Authentication headers for admin_user

#### Data Fixtures
- `test_application` - Sample job application

#### Mock Fixtures
- `mock_email_service` - Prevents actual email sending

### Using Fixtures

```python
def test_example(client, auth_headers, test_application):
    response = client.get(
        f"/api/applications/{test_application.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
```

---

## Writing Tests

### Test Structure Template

```python
import pytest
from fastapi import status

class TestFeatureName:
    """Test description"""
    
    def test_success_case(self, client, auth_headers):
        """Test successful operation"""
        # Arrange
        data = {"field": "value"}
        
        # Act
        response = client.post("/api/endpoint", 
                               json=data, 
                               headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["field"] == "value"
    
    def test_error_case(self, client):
        """Test error handling"""
        response = client.post("/api/endpoint", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

### Best Practices

1. **Test Naming** - Use descriptive names: `test_login_with_invalid_password`
2. **Arrange-Act-Assert** - Setup → Action → Verification pattern
3. **Test One Thing** - Each test verifies one specific behavior
4. **Independent Tests** - Tests should not depend on each other
5. **Clear Assertions** - Be explicit about what's being verified

---

## Test Categories

### Authentication Tests (test_auth.py)
- Login with valid/invalid credentials
- Registration with validation
- Token generation and validation
- Profile retrieval and update
- Password change

### Application Tests (test_applications.py)
- CRUD operations (create, read, update, delete)
- Status filtering and search
- Application listing and pagination

### Analytics Tests (test_analytics.py)
- Statistics aggregation
- Status breakdown
- Trend data

### Email Service Tests (test_email_service_simple.py)
- Template rendering
- Notification sending
- Service configuration

### Integration Workflow Tests (test_integration_workflows.py)
- Multi-service end-to-end flows
- Application lifecycle
- Data consistency

---

## Test Credentials

**User Account:**
```
Email: rangasudarshan19@gmail.com
Password: Sudarshan@1
```

**Admin Account:**
```
Email: admin@jobtracker.com
Password: admin123
```

---

## Debugging Failed Tests

### View Detailed Output
```bash
pytest -vv --tb=long
```

### Debug with PDB
```bash
pytest --pdb  # Drop into debugger on failure
```

### Print Debugging
```bash
pytest -s  # Show print statements
```

### Check Logs
```bash
pytest --log-cli-level=DEBUG
```

---

## Common Testing Patterns

### Testing Authentication
```python
def test_protected_endpoint_requires_auth(client):
    response = client.get("/api/protected")
    assert response.status_code == 401

def test_protected_endpoint_with_auth(client, auth_headers):
    response = client.get("/api/protected", headers=auth_headers)
    assert response.status_code == 200
```

### Testing CRUD Operations
```python
def test_crud_lifecycle(client, auth_headers):
    # Create
    create_resp = client.post("/api/items", json={"name": "Test"}, headers=auth_headers)
    item_id = create_resp.json()["id"]
    
    # Read
    read_resp = client.get(f"/api/items/{item_id}", headers=auth_headers)
    assert read_resp.json()["name"] == "Test"
    
    # Update
    update_resp = client.put(f"/api/items/{item_id}", json={"name": "Updated"}, headers=auth_headers)
    assert update_resp.json()["name"] == "Updated"
    
    # Delete
    delete_resp = client.delete(f"/api/items/{item_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
```

### Testing Reviews API
```python
def test_review_lifecycle(client, auth_headers):
    # Create review
    review_data = {"rating": 5, "title": "Great App", "content": "JobSphere is excellent for job tracking!"}
    resp = client.post("/api/reviews", json=review_data, headers=auth_headers)
    assert resp.status_code == 201
    review_id = resp.json()["review"]["id"]
    
    # Get my review
    mine = client.get("/api/reviews/mine", headers=auth_headers)
    assert mine.json()["review"]["rating"] == 5
    
    # Public listing
    all_reviews = client.get("/api/reviews")
    assert all_reviews.json()["total_reviews"] >= 1
    
    # Update
    update = client.put(f"/api/reviews/{review_id}", json={"rating": 4}, headers=auth_headers)
    assert update.json()["review"]["rating"] == 4
    
    # Duplicate prevention
    dup = client.post("/api/reviews", json=review_data, headers=auth_headers)
    assert dup.status_code == 409
    
    # Delete
    delete = client.delete(f"/api/reviews/{review_id}", headers=auth_headers)
    assert delete.status_code == 200
```

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Last Updated**: February 16, 2026  
**Maintained By**: Development Team
