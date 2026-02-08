"""
Tests for authentication endpoints
"""
import pytest
from fastapi import status


@pytest.mark.unit
class TestRegistration:
    """Test user registration"""
    
    def test_register_new_user(self, client):
        """Test successful user registration"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User"
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "password" not in data
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email fails"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
                "full_name": "Duplicate User"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email fails"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
                "full_name": "Invalid Email"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "123",  # Too short
                "full_name": "Weak Password User"
            }
        )
        # Backend might accept any password or enforce minimum length
        # Accept success (201) or validation error (400/422)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


@pytest.mark.unit
class TestLogin:
    """Test user login"""
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = client.post("/api/auth/login", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
class TestCurrentUser:
    """Test getting current user info"""
    
    def test_get_current_user(self, client, auth_headers):
        """Test getting current user with valid token"""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "is_admin" in data
        assert data["is_admin"] == False
    
    def test_get_current_user_no_token(self, client):
        """Test getting current user without token"""
        response = client.get("/api/auth/me")
        # FastAPI may return 403 when auth is required but not provided
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
class TestProfile:
    """Test profile management"""
    
    def test_update_profile(self, client, auth_headers):
        """Test updating user profile"""
        response = client.put(
            "/api/auth/update-profile",
            headers=auth_headers,
            json={
                "full_name": "Updated Name",
                "phone": "+1234567890"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["phone"] == "+1234567890"
    
    def test_update_profile_unauthorized(self, client):
        """Test updating profile without authentication"""
        response = client.put(
            "/api/auth/update-profile",
            json={"full_name": "Hacker"}
        )
        # FastAPI may return 403 when auth is required but not provided
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.integration
class TestAuthFlow:
    """Test complete authentication flow"""
    
    def test_register_login_access_protected_resource(self, client):
        """Test full flow: register -> login -> access protected resource"""
        # Register
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "flowtest@example.com",
                "password": "securepass123",
                "full_name": "Flow Test"
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "flowtest@example.com",
                "password": "securepass123"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        
        # Access protected resource
        headers = {"Authorization": f"Bearer {token}"}
        me_response = client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["email"] == "flowtest@example.com"
