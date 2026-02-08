"""
Tests for analytics endpoints
"""
import pytest
from fastapi import status


@pytest.mark.unit
class TestAnalyticsOverview:
    """Test analytics overview endpoint"""
    
    def test_get_overview(self, client, auth_headers, test_application):
        """Test getting analytics overview"""
        response = client.get("/api/analytics/overview", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_applications" in data
        assert "status_breakdown" in data
        assert "recent_activity" in data
        assert isinstance(data["total_applications"], int)
    
    def test_get_overview_unauthorized(self, client):
        """Test getting overview without authentication"""
        response = client.get("/api/analytics/overview")
        # FastAPI returns 403 Forbidden when no credentials provided
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.unit
class TestAnalyticsTimeline:
    """Test analytics timeline endpoint"""
    
    def test_get_timeline(self, client, auth_headers):
        """Test getting timeline data"""
        response = client.get("/api/analytics/timeline", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Timeline returns dict with 'timeline' key containing list
        assert isinstance(data, dict)
        assert "timeline" in data
        assert isinstance(data["timeline"], list)


@pytest.mark.unit
class TestStatusDistribution:
    """Test status distribution endpoint"""
    
    def test_get_status_distribution(self, client, auth_headers, test_application):
        """Test getting status distribution"""
        response = client.get("/api/analytics/status-distribution", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, (list, dict))
