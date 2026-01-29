"""
End-to-end tests using Testcontainers with the published Docker image
"""
import pytest
import httpx
import time
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="module")
def test_network():
    """Create a Docker network for inter-container communication"""
    network = Network()
    with network:
        yield network


@pytest.fixture(scope="module")
def postgres_container(test_network):
    """Start a PostgreSQL container for the application"""
    with PostgresContainer("postgres:15").with_network(test_network).with_network_aliases("postgres") as postgres:
        yield postgres


@pytest.fixture(scope="module")
def app_container(postgres_container, test_network):
    """
    Start the cronpulse application container using the published Docker image
    """
    # Build internal database URL using network alias
    db_url = "postgresql://test:test@postgres:5432/test"
    
    # Create and configure the application container
    container = DockerContainer("cronpulse/cronpulse-community:latest")
    container.with_env("DATABASE_URL", db_url)
    container.with_env("JWT_SECRET", "test-secret-for-e2e-testing")
    container.with_env("ADMIN_EMAIL", "admin@test.com")
    container.with_env("ADMIN_PASSWORD", "TestPass123!")
    container.with_env("SKIP_SCHEDULER", "true")  # Skip scheduler for controlled testing
    container.with_exposed_ports(8000)
    container.with_network(test_network)
    
    with container:
        # Wait for application to be ready
        port = container.get_exposed_port(8000)
        base_url = f"http://localhost:{port}"
        
        # Give container more time to initialize
        print(f"Waiting for container to start on {base_url}")
        time.sleep(5)  # Initial wait for container startup
        
        # Wait for health check with better error handling
        max_retries = 60
        last_error = None
        for i in range(max_retries):
            try:
                response = httpx.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    print(f"Container ready after {i+1} attempts")
                    break
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ReadError) as e:
                last_error = str(e)
                if i == max_retries - 1:
                    # Print container logs for debugging
                    logs = container.get_logs()
                    stdout_log = logs[0].decode() if isinstance(logs, tuple) and len(logs) > 0 else str(logs)
                    stderr_log = logs[1].decode() if isinstance(logs, tuple) and len(logs) > 1 else ""
                    print(f"\n=== STDOUT ===\n{stdout_log}")
                    if stderr_log:
                        print(f"\n=== STDERR ===\n{stderr_log}")
                    raise Exception(f"Application failed to start after {max_retries} attempts. Last error: {last_error}")
                if i % 10 == 0 and i > 0:
                    print(f"Still waiting... attempt {i}/{max_retries}")
                time.sleep(2)
        
        yield base_url


class TestE2EDockerWorkflow:
    """End-to-end tests with the Docker container"""
    
    def test_complete_monitor_workflow(self, app_container):
        """
        Complete workflow: create user, login, create monitor, ping it, delete it
        """
        base_url = app_container
        
        # Step 1: Create a user account
        signup_response = httpx.post(
            f"{base_url}/api/signup",
            data={
                "email": "testuser@example.com",
                "password": "SecurePass123!",
            },
            timeout=10
        )
        assert signup_response.status_code == 200, f"Signup failed: {signup_response.text}"
        
        # Step 2: Login to get access token
        login_response = httpx.post(
            f"{base_url}/api/login",
            data={
                "username": "testuser@example.com",
                "password": "SecurePass123!"
            },
            timeout=10
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token_data = login_response.json()
        access_token = token_data["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 3: Create a monitor
        create_monitor_response = httpx.post(
            f"{base_url}/api/monitors",
            json={
                "name": "E2E Test Monitor",
                "interval": 5,  # 5 minutes
                "email_recipient": "alerts@example.com"
            },
            headers=headers,
            timeout=10
        )
        assert create_monitor_response.status_code == 200, f"Create monitor failed: {create_monitor_response.text}"
        monitor_data = create_monitor_response.json()
        monitor_id = monitor_data["id"]
        
        # Construct ping URL from monitor ID
        ping_url = f"{base_url}/api/ping/{monitor_id}"
        
        # Verify monitor was created
        assert monitor_data["name"] == "E2E Test Monitor"
        assert monitor_data["interval"] == 5
        
        # Step 4: Ping the monitor (requires authentication in this version)
        ping_response = httpx.get(ping_url, headers=headers, timeout=10)
        assert ping_response.status_code == 200, f"Ping failed: {ping_response.text}"
        ping_result = ping_response.json()
        assert ping_result["status"] == "success"
        assert "monitor_id" in ping_result
        
        # Step 5: Verify monitor shows the ping (get monitor details)
        get_monitor_response = httpx.get(
            f"{base_url}/api/monitors/{monitor_id}",
            headers=headers,
            timeout=10
        )
        assert get_monitor_response.status_code == 200
        updated_monitor = get_monitor_response.json()
        assert updated_monitor["last_ping_at"] is not None, "Monitor should have last_ping_at set"
        
        # Step 6: List all monitors
        list_response = httpx.get(
            f"{base_url}/api/monitors",
            headers=headers,
            timeout=10
        )
        assert list_response.status_code == 200
        monitors_list = list_response.json()
        assert len(monitors_list) == 1
        assert monitors_list[0]["id"] == monitor_id
        
        # Step 7: Delete the monitor
        delete_response = httpx.delete(
            f"{base_url}/api/monitors/{monitor_id}",
            headers=headers,
            timeout=10
        )
        assert delete_response.status_code == 204, f"Delete failed: {delete_response.text}"
        
        # Step 8: Verify monitor is deleted
        verify_delete_response = httpx.get(
            f"{base_url}/api/monitors/{monitor_id}",
            headers=headers,
            timeout=10
        )
        assert verify_delete_response.status_code == 404, "Monitor should be deleted"
        
        # Step 9: Verify list is empty
        final_list_response = httpx.get(
            f"{base_url}/api/monitors",
            headers=headers,
            timeout=10
        )
        assert final_list_response.status_code == 200
        final_monitors = final_list_response.json()
        assert len(final_monitors) == 0, "All monitors should be deleted"
    
    
    def test_ping_with_auth(self, app_container):
        """
        Test that ping endpoint works with authentication
        """
        base_url = app_container
        
        # Create user and monitor first
        signup_response = httpx.post(
            f"{base_url}/api/signup",
            data={
                "email": "pingtest@example.com",
                "password": "SecurePass123!",
            },
            timeout=10
        )
        assert signup_response.status_code == 200
        
        login_response = httpx.post(
            f"{base_url}/api/login",
            data={
                "username": "pingtest@example.com",
                "password": "SecurePass123!"
            },
            timeout=10
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        create_monitor_response = httpx.post(
            f"{base_url}/api/monitors",
            json={
                "name": "Public Ping Test",
                "interval": 10,  # 10 minutes
                "email_recipient": "ping@example.com"
            },
            headers=headers,
            timeout=10
        )
        assert create_monitor_response.status_code == 200
        monitor_data = create_monitor_response.json()
        ping_url = f"{base_url}/api/ping/{monitor_data['id']}"
        
        # Ping with authentication
        ping_response = httpx.get(ping_url, headers=headers, timeout=10)
        assert ping_response.status_code == 200
        assert ping_response.json()["status"] == "success"
    
    
    def test_api_key_workflow(self, app_container):
        """
        Test creating and using API keys
        """
        base_url = app_container
        
        # Setup: Create user and login
        httpx.post(
            f"{base_url}/api/signup",
            data={
                "email": "apikey@example.com",
                "password": "SecurePass123!",
            },
            timeout=10
        )
        
        login_response = httpx.post(
            f"{base_url}/api/login",
            data={
                "username": "apikey@example.com",
                "password": "SecurePass123!"
            },
            timeout=10
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Create an API key
        create_key_response = httpx.post(
            f"{base_url}/api/api-keys",
            data={"name": "Test API Key"},
            headers=headers,
            timeout=10
        )
        assert create_key_response.status_code == 200
        api_key_data = create_key_response.json()
        api_key = api_key_data["key"]
        
        # Use API key to create a monitor
        api_headers = {"X-API-Key": api_key}
        create_monitor_response = httpx.post(
            f"{base_url}/api/monitors",
            json={
                "name": "API Key Monitor",
                "interval": 60,  # 1 hour
                "webhook_url": "https://example.com/hook"
            },
            headers=api_headers,
            timeout=10
        )
        assert create_monitor_response.status_code == 200
        
        # List monitors with API key
        list_response = httpx.get(
            f"{base_url}/api/monitors",
            headers=api_headers,
            timeout=10
        )
        assert list_response.status_code == 200
        monitors = list_response.json()
        assert len(monitors) == 1
        assert monitors[0]["name"] == "API Key Monitor"
    
    
    def test_invalid_authentication(self, app_container):
        """
        Test that invalid authentication is rejected
        """
        base_url = app_container
        
        # Try to create monitor without auth
        response = httpx.post(
            f"{base_url}/api/monitors",
            json={
                "name": "Unauthorized Monitor",
                "interval": 5,
                "email_recipient": "test@example.com"
            },
            timeout=10
        )
        assert response.status_code == 401
        
        # Try with invalid API key
        invalid_headers = {"X-API-Key": "invalid-key-12345"}
        response = httpx.get(
            f"{base_url}/api/monitors",
            headers=invalid_headers,
            timeout=10
        )
        assert response.status_code == 401
        
        # Try with invalid JWT token
        invalid_jwt_headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = httpx.get(
            f"{base_url}/api/monitors",
            headers=invalid_jwt_headers,
            timeout=10
        )
        assert response.status_code == 401
