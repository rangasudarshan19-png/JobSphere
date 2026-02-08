# Testing and Quality Assurance Guide

## Overview
This document describes the testing strategy, quality assurance processes, and best practices for the Job Tracker application.

---

## Test Architecture

### Test Levels
1. **Unit Tests** - Test individual functions/methods in isolation
2. **Integration Tests** - Test multiple components working together
3. **End-to-End Tests** - Test complete user workflows

### Test Structure
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py             # Authentication tests
├── test_applications.py     # Application CRUD tests
├── test_analytics.py        # Analytics tests
└── README.md                # Testing documentation
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
pytest
```

**Run with verbose output:**
```bash
pytest -v
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

**Run by markers:**
```bash
pytest -m unit           # Only unit tests
pytest -m integration    # Only integration tests
pytest -m "not slow"     # Skip slow tests
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
# Open htmlcov/index.html in browser
```

**Combined:**
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Coverage Targets
- **Overall**: 80%+
- **Critical paths** (auth, applications): 90%+
- **Services**: 75%+
- **Utilities**: 85%+

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
- `test_company` - Sample company
- `test_application` - Sample job application

#### Mock Fixtures
- `mock_email_service` - Prevents actual email sending
- `mock_ai_service` - Prevents actual AI API calls

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

@pytest.mark.unit
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

1. **Test Naming**
   - Use descriptive names: `test_login_with_invalid_password`
   - Follow pattern: `test_<action>_<condition>_<expected_result>`

2. **Arrange-Act-Assert Pattern**
   ```python
   # Arrange - Setup test data
   user_data = {"email": "test@example.com", "password": "pass"}
   
   # Act - Perform action
   response = client.post("/api/auth/login", json=user_data)
   
   # Assert - Verify results
   assert response.status_code == 200
   ```

3. **Test One Thing**
   - Each test should verify one specific behavior
   - Keep tests focused and simple

4. **Independent Tests**
   - Tests should not depend on each other
   - Use fixtures for test data setup

5. **Clear Assertions**
   ```python
   # Good
   assert response.status_code == status.HTTP_200_OK
   assert data["email"] == "test@example.com"
   
   # Avoid
   assert response  # Unclear what's being tested
   ```

---

## Test Markers

### Built-in Markers
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow running tests

### Using Markers
```python
@pytest.mark.unit
def test_fast_operation():
    pass

@pytest.mark.slow
@pytest.mark.integration
def test_complex_workflow():
    pass
```

---

## Mocking External Services

### Email Service
```python
# Automatically mocked in conftest.py
def test_with_email(client, auth_headers):
    # Email won't actually send
    response = client.post("/api/applications", ...)
    # Test passes without SMTP configuration
```

### AI Service
```python
# Mock AI responses
def test_ai_feature(monkeypatch):
    def mock_generate(*args, **kwargs):
        return "Mock AI response"
    
    monkeypatch.setattr("app.services.ai_service.generate", mock_generate)
```

### External APIs
```python
@pytest.fixture
def mock_job_api(monkeypatch):
    def mock_search(*args, **kwargs):
        return {"jobs": [{"title": "Test Job"}]}
    
    monkeypatch.setattr("app.services.job_search.search", mock_search)
    return mock_search
```

---

## Testing Checklist

### For New Features
- [ ] Unit tests for core logic
- [ ] Integration tests for API endpoints
- [ ] Test success cases
- [ ] Test error cases
- [ ] Test edge cases
- [ ] Test authentication/authorization
- [ ] Update documentation

### Before Committing
- [ ] All tests pass locally
- [ ] No failing tests ignored
- [ ] Coverage meets minimum threshold
- [ ] No new linting errors
- [ ] Documentation updated

### For Bug Fixes
- [ ] Write test that reproduces the bug
- [ ] Fix the bug
- [ ] Verify test now passes
- [ ] Add regression test

---

## Continuous Integration

### GitHub Actions (Future)
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Performance Testing

### Load Testing (Future Enhancement)
```python
# Using locust or similar
from locust import HttpUser, task

class JobTrackerUser(HttpUser):
    @task
    def get_applications(self):
        self.client.get("/api/applications",
                       headers={"Authorization": f"Bearer {self.token}"})
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
# View logs during test
pytest --log-cli-level=DEBUG
```

---

## Test Data Management

### Database State
- Tests use in-memory SQLite
- Database is recreated for each test
- No need to clean up between tests

### Fixture Data
```python
# Define reusable test data
@pytest.fixture
def sample_application_data():
    return {
        "job_title": "Software Engineer",
        "company_name": "Test Corp",
        "status": "Applied"
    }
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
    create_response = client.post("/api/items", 
                                  json={"name": "Test"},
                                  headers=auth_headers)
    item_id = create_response.json()["id"]
    
    # Read
    read_response = client.get(f"/api/items/{item_id}", 
                               headers=auth_headers)
    assert read_response.json()["name"] == "Test"
    
    # Update
    update_response = client.put(f"/api/items/{item_id}",
                                 json={"name": "Updated"},
                                 headers=auth_headers)
    assert update_response.json()["name"] == "Updated"
    
    # Delete
    delete_response = client.delete(f"/api/items/{item_id}",
                                    headers=auth_headers)
    assert delete_response.status_code == 200
```

### Testing Error Handling
```python
def test_handles_invalid_input(client, auth_headers):
    response = client.post("/api/items",
                          json={"invalid": "data"},
                          headers=auth_headers)
    assert response.status_code == 422
    assert "error" in response.json()

def test_handles_not_found(client, auth_headers):
    response = client.get("/api/items/99999", headers=auth_headers)
    assert response.status_code == 404
```

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Last Updated**: November 18, 2025
**Maintained By**: Development Team
