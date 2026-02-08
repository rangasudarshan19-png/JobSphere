"""
Tests for application CRUD endpoints
"""
import pytest
from fastapi import status
from datetime import datetime, date


@pytest.mark.unit
class TestCreateApplication:
    """Test creating job applications"""
    
    def test_create_application_success(self, client, auth_headers):
        """Test successful application creation"""
        response = client.post(
            "/api/applications",
            headers=auth_headers,
            json={
                "company_name": "New Tech Corp",
                "job_title": "Senior Developer",
                "job_description": "Build awesome apps",
                "status": "Applied",
                "location": "San Francisco, CA",
                "job_type": "Full-time",
                "salary_range": "$120k-$150k",
                "applied_date": date.today().isoformat()
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["job_title"] == "Senior Developer"
        assert data["status"] == "Applied"
        assert "id" in data
        assert "company" in data
    
    def test_create_application_unauthorized(self, client):
        """Test creating application without authentication"""
        response = client.post(
            "/api/applications",
            json={"job_title": "Test Job"}
        )
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_create_application_with_existing_company(self, client, auth_headers, test_company):
        """Test creating application with existing company"""
        response = client.post(
            "/api/applications",
            headers=auth_headers,
            json={
                "company_id": test_company.id,
                "job_title": "DevOps Engineer",
                "status": "Applied",
                "applied_date": date.today().isoformat()
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["company"]["id"] == test_company.id
    
    def test_create_application_invalid_data(self, client, auth_headers):
        """Test creating application with invalid data"""
        response = client.post(
            "/api/applications",
            headers=auth_headers,
            json={"invalid_field": "value"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
class TestGetApplications:
    """Test retrieving applications"""
    
    def test_get_all_applications(self, client, auth_headers, test_application):
        """Test getting all user's applications"""
        response = client.get("/api/applications", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(app["id"] == test_application.id for app in data)
    
    def test_get_applications_empty(self, client, auth_headers):
        """Test getting applications when user has none"""
        response = client.get("/api/applications", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        # Depending on fixtures, might be empty or have test_application
        assert isinstance(response.json(), list)
    
    def test_get_application_by_id(self, client, auth_headers, test_application):
        """Test getting specific application"""
        response = client.get(
            f"/api/applications/{test_application.id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_application.id
        assert data["job_title"] == test_application.job_title
    
    def test_get_nonexistent_application(self, client, auth_headers):
        """Test getting application that doesn't exist"""
        response = client.get("/api/applications/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_applications_unauthorized(self, client):
        """Test getting applications without authentication"""
        response = client.get("/api/applications")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.unit
class TestUpdateApplication:
    """Test updating applications"""
    
    def test_update_application_status(self, client, auth_headers, test_application):
        """Test updating application status"""
        response = client.patch(
            f"/api/applications/{test_application.id}",
            headers=auth_headers,
            json={"status": "Interview"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "Interview"
    
    def test_update_application_full(self, client, auth_headers, test_application):
        """Test full application update"""
        response = client.put(
            f"/api/applications/{test_application.id}",
            headers=auth_headers,
            json={
                "company_id": test_application.company_id,
                "job_title": "Updated Title",
                "status": "Offer",
                "notes": "Great opportunity!",
                "applied_date": date.today().isoformat()
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job_title"] == "Updated Title"
        assert data["status"] == "Offer"
        assert data["notes"] == "Great opportunity!"
    
    def test_update_nonexistent_application(self, client, auth_headers):
        """Test updating application that doesn't exist"""
        response = client.patch(
            "/api/applications/99999",
            headers=auth_headers,
            json={"status": "Interview"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_other_users_application(self, client, admin_auth_headers, test_application):
        """Test updating another user's application (should fail)"""
        # This assumes proper authorization checks are in place
        response = client.patch(
            f"/api/applications/{test_application.id}",
            headers=admin_auth_headers,
            json={"status": "Rejected"}
        )
        # Should either be 404 (not found) or 403 (forbidden)
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]


@pytest.mark.unit
class TestDeleteApplication:
    """Test deleting applications"""
    
    def test_delete_application(self, client, auth_headers, test_application):
        """Test successful application deletion"""
        response = client.delete(
            f"/api/applications/{test_application.id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        get_response = client.get(
            f"/api/applications/{test_application.id}",
            headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_nonexistent_application(self, client, auth_headers):
        """Test deleting application that doesn't exist"""
        response = client.delete("/api/applications/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
class TestApplicationStats:
    """Test application statistics"""
    
    def test_get_stats_summary(self, client, auth_headers, test_application):
        """Test getting application stats summary"""
        response = client.get("/api/applications/stats/summary", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_applications" in data
        assert "by_status" in data
        assert isinstance(data["total_applications"], int)
        assert isinstance(data["by_status"], dict)


@pytest.mark.integration
class TestApplicationWorkflow:
    """Test complete application workflow"""
    
    def test_full_application_lifecycle(self, client, auth_headers):
        """Test: create -> read -> update -> delete"""
        # Create
        create_response = client.post(
            "/api/applications",
            headers=auth_headers,
            json={
                "company_name": "Lifecycle Corp",
                "job_title": "Test Engineer",
                "status": "Applied",
                "applied_date": date.today().isoformat()
            }
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        app_id = create_response.json()["id"]
        
        # Read
        read_response = client.get(f"/api/applications/{app_id}", headers=auth_headers)
        assert read_response.status_code == status.HTTP_200_OK
        assert read_response.json()["status"] == "Applied"
        
        # Update
        update_response = client.patch(
            f"/api/applications/{app_id}",
            headers=auth_headers,
            json={"status": "Interview"}
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["status"] == "Interview"
        
        # Delete
        delete_response = client.delete(f"/api/applications/{app_id}", headers=auth_headers)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        verify_response = client.get(f"/api/applications/{app_id}", headers=auth_headers)
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND
