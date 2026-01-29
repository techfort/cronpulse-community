"""
Integration tests for authentication endpoints
"""
import pytest


class TestAuthEndpoints:
    """Test authentication API endpoints"""
    
    def test_signup_success(self, client):
        """Test successful user signup"""
        response = client.post(
            "/api/signup",
            data={
                "email": "test@example.com",
                "password": "strongpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
    
    def test_signup_weak_password(self, client):
        """Test signup with weak password"""
        response = client.post(
            "/api/signup",
            data={
                "email": "test@example.com",
                "password": "weak"
            }
        )
        assert response.status_code == 400  # UserService returns 400 for weak password
    
    def test_signup_invalid_email(self, client):
        """Test signup with invalid email"""
        response = client.post(
            "/api/signup",
            data={
                "email": "not-an-email",
                "password": "strongpassword123"
            }
        )
        assert response.status_code == 400  # UserService returns 400 for invalid email
    
    def test_signup_duplicate_email(self, client):
        """Test signup with duplicate email"""
        # First signup
        client.post(
            "/api/signup",
            data={
                "email": "test@example.com",
                "password": "strongpassword123"
            }
        )
        
        # Duplicate signup
        response = client.post(
            "/api/signup",
            data={
                "email": "test@example.com",
                "password": "anotherpassword123"
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_login_success(self, client):
        """Test successful login"""
        # Create user first
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
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client):
        """Test login with wrong password"""
        # Create user
        client.post(
            "/api/signup",
            data={
                "email": "test@example.com",
                "password": "strongpassword123"
            }
        )
        
        # Wrong password
        response = client.post(
            "/api/login",
            data={
                "username": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 400
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/api/login",
            data={
                "username": "nobody@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 400
