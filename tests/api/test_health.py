"""
Tests for health check endpoint
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check_success(self):
        """Test health check returns 200 when healthy"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "scheduler" in data
    
    def test_health_check_accessible_without_auth(self):
        """Test health check doesn't require authentication"""
        response = client.get("/health")
        assert response.status_code == 200
        # Should not return 401
