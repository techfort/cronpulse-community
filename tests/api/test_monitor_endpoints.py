"""
Integration tests for monitor endpoints
"""
import pytest


@pytest.fixture
def auth_headers(client):
    """Create a user and return authentication headers"""
    # Signup
    client.post(
        "/api/signup",
        data={
            "email": "test@example.com",
            "password": "strongpassword123"
        }
    )
    
    # Login
    response = client.post(
        "/api/login",
        data={
            "username": "test@example.com",
            "password": "strongpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestMonitorEndpoints:
    """Test monitor API endpoints"""
    
    def test_create_monitor_success(self, client, auth_headers):
        """Test creating a monitor successfully"""
        response = client.post(
            "/api/monitors",
            json={
                "name": "Test Job",
                "interval": 60.0,
                "email_recipient": "alerts@example.com"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Job"
        assert data["interval"] == 60.0
        assert data["email_recipient"] == "alerts@example.com"
    
    def test_create_monitor_no_auth(self, client):
        """Test creating monitor without authentication fails"""
        response = client.post(
            "/api/monitors",
            json={
                "name": "Test Job",
                "interval": 60.0,
                "email_recipient": "alerts@example.com"
            }
        )
        assert response.status_code == 401
    
    def test_create_monitor_invalid_interval(self, client, auth_headers):
        """Test creating monitor with invalid interval"""
        response = client.post(
            "/api/monitors",
            json={
                "name": "Test Job",
                "interval": -5.0,  # Negative interval
                "email_recipient": "alerts@example.com"
            },
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_create_monitor_no_alert_destination(self, client, auth_headers):
        """Test creating monitor without email or webhook"""
        response = client.post(
            "/api/monitors",
            json={
                "name": "Test Job",
                "interval": 60.0
            },
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_list_monitors(self, client, auth_headers):
        """Test listing monitors"""
        # Create a monitor
        client.post(
            "/api/monitors",
            json={
                "name": "Test Job",
                "interval": 60.0,
                "email_recipient": "alerts@example.com"
            },
            headers=auth_headers
        )
        
        # List monitors
        response = client.get("/api/monitors", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Job"
    
    def test_update_monitor(self, client, auth_headers):
        """Test updating a monitor"""
        # Create monitor
        create_response = client.post(
            "/api/monitors",
            json={
                "name": "Test Job",
                "interval": 60.0,
                "email_recipient": "alerts@example.com"
            },
            headers=auth_headers
        )
        monitor_id = create_response.json()["id"]
        
        # Update monitor
        response = client.put(
            f"/api/monitors/{monitor_id}",
            json={
                "name": "Updated Job",
                "interval": 120.0
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Job"
        assert data["interval"] == 120.0
    
    def test_delete_monitor(self, client, auth_headers):
        """Test deleting a monitor"""
        # Create monitor
        create_response = client.post(
            "/api/monitors",
            json={
                "name": "Test Job",
                "interval": 60.0,
                "email_recipient": "alerts@example.com"
            },
            headers=auth_headers
        )
        monitor_id = create_response.json()["id"]
        
        # Delete monitor
        response = client.delete(
            f"/api/monitors/{monitor_id}",
            headers=auth_headers
        )
        assert response.status_code == 204
        
        # Verify deletion
        list_response = client.get("/api/monitors", headers=auth_headers)
        assert len(list_response.json()) == 0
    
    def test_ping_monitor(self, client, auth_headers):
        """Test pinging a monitor"""
        # Create monitor
        create_response = client.post(
            "/api/monitors",
            json={
                "name": "Test Job",
                "interval": 60.0,
                "email_recipient": "alerts@example.com"
            },
            headers=auth_headers
        )
        monitor_id = create_response.json()["id"]
        
        # Ping monitor
        response = client.post(
            f"/api/ping/{monitor_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
