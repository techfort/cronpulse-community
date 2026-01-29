"""
End-to-end tests using Testcontainers with the published Docker image
"""
import pytest
import httpx
import time
import uuid
from datetime import datetime, timezone
from passlib.context import CryptContext
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.postgres import PostgresContainer
import psycopg2


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
        
        # Return both URL and container for log access
        yield {"url": base_url, "container": container}


@pytest.fixture(scope="function")
def api_key_fixture(postgres_container):
    """
    Create a user and API key directly in the database for testing.
    Returns tuple of (email, password, api_key)
    """
    # Connect to the database
    conn = psycopg2.connect(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        user="test",
        password="test",
        database="test"
    )
    cursor = conn.cursor()
    
    try:
        # Create password hash
        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        email = "apitest@example.com"
        password = "TestPass123!"
        password_hash = pwd_context.hash(password)
        
        # Insert user with all required fields and defaults
        cursor.execute(
            """INSERT INTO users (email, hashed_password, is_admin) 
               VALUES (%s, %s, %s) RETURNING id""",
            (email, password_hash, False)
        )
        user_id = cursor.fetchone()[0]
        
        # Create API key
        api_key = str(uuid.uuid4())
        key_hash = pwd_context.hash(api_key)
        
        cursor.execute(
            "INSERT INTO api_keys (user_id, api_key, key_hash, name, created_at) VALUES (%s, %s, %s, %s, %s)",
            (user_id, api_key, key_hash, "Test API Key", datetime.now(timezone.utc))
        )
        
        conn.commit()
        
        yield (email, password, api_key)
        
    finally:
        # Cleanup - delete monitors first due to foreign key constraint
        cursor.execute("DELETE FROM monitors WHERE user_id IN (SELECT id FROM users WHERE email = %s)", (email,))
        cursor.execute("DELETE FROM api_keys WHERE user_id IN (SELECT id FROM users WHERE email = %s)", (email,))
        cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        cursor.close()
        conn.close()


class TestE2EDockerWorkflow:
    """End-to-end tests with the Docker container"""
    
    def test_complete_monitor_workflow(self, app_container):
        """
        Complete workflow: create user, login, create monitor, ping it, delete it
        """
        base_url = app_container["url"]
        
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
        
        # Step 5: List all monitors and verify ping was recorded
        list_response = httpx.get(
            f"{base_url}/api/monitors",
            headers=headers,
            timeout=10
        )
        assert list_response.status_code == 200
        monitors_list = list_response.json()
        assert len(monitors_list) == 1
        assert monitors_list[0]["id"] == monitor_id
        assert monitors_list[0]["last_ping"] is not None, "Monitor should have last_ping set after ping"
        
        # Step 6: Delete the monitor
        delete_response = httpx.delete(
            f"{base_url}/api/monitors/{monitor_id}",
            headers=headers,
            timeout=10
        )
        assert delete_response.status_code == 204, f"Delete failed: {delete_response.text}"
        
        # Step 7: Verify list is empty
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
        base_url = app_container["url"]
        
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
    
    
    def test_api_key_workflow(self, app_container, api_key_fixture):
        """
        Test creating and using API keys
        """
        base_url = app_container["url"]
        container = app_container["container"]
        email, password, api_key = api_key_fixture
        
        # First, test listing monitors with API key (simpler operation)
        api_headers = {"X-API-Key": api_key}
        list_response = httpx.get(
            f"{base_url}/api/monitors",
            headers=api_headers,
            timeout=10
        )
        print(f"List monitors status: {list_response.status_code}")
        if list_response.status_code != 200:
            print(f"List error: {list_response.text}")
        assert list_response.status_code == 200
        
        # Use API key to create a monitor
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
        if create_monitor_response.status_code != 200:
            print(f"\n=== ERROR CREATING MONITOR ===")
            print(f"Status: {create_monitor_response.status_code}")
            print(f"Response: {create_monitor_response.text}")
            
            # Get container logs to see the actual error
            print(f"\n=== CONTAINER LOGS (last 100 lines) ===")
            logs = container.get_logs()
            if isinstance(logs, tuple) and len(logs) >= 2:
                stdout_log = logs[0].decode() if logs[0] else ""
                stderr_log = logs[1].decode() if logs[1] else ""
                log_str = stdout_log + "\n" + stderr_log
            else:
                log_str = logs[0].decode() if isinstance(logs, tuple) else str(logs)
            log_lines = log_str.split('\n')
            print('\n'.join(log_lines[-100:]))
            print(f"\n=== END LOGS ===")
        assert create_monitor_response.status_code == 200
        
        # List monitors again to verify
        list_response2 = httpx.get(
            f"{base_url}/api/monitors",
            headers=api_headers,
            timeout=10
        )
        assert list_response2.status_code == 200
        monitors = list_response2.json()
        assert len(monitors) == 1
        assert monitors[0]["name"] == "API Key Monitor"
    
    
    def test_invalid_authentication(self, app_container):
        """
        Test that invalid authentication is rejected
        """
        base_url = app_container["url"]
        
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
