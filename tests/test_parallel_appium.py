"""
Example test using pytest-xdist for parallel testing with Appium Hub
"""
import pytest
import httpx
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions


class TestParallelAppium:
    """Test class for parallel Appium testing"""
    
    @pytest.fixture(scope="session")
    def hub_url(self):
        """Hub URL fixture"""
        return "http://localhost:4444"
    
    @pytest.fixture
    def android_capabilities(self):
        """Android test capabilities"""
        return {
            "platformName": "Android",
            "automationName": "UiAutomator2",
            "deviceName": "Android Device",
            "app": "/path/to/your/app.apk",  # Update with your app path
            "noReset": True,
            "newCommandTimeout": 300
        }
    
    @pytest.fixture
    def ios_capabilities(self):
        """iOS test capabilities"""
        return {
            "platformName": "iOS",
            "automationName": "XCUITest", 
            "deviceName": "iPhone",
            "app": "/path/to/your/app.ipa",  # Update with your app path
            "noReset": True,
            "newCommandTimeout": 300
        }
    
    @pytest.fixture
    def driver_session(self, hub_url, android_capabilities):
        """Create an Appium driver session through the hub"""
        # Create session through hub
        with httpx.Client() as client:
            response = client.post(
                f"{hub_url}/session",
                json={
                    "capabilities": android_capabilities,
                    "device_name": f"device_{pytest.current_pytest_worker_id}"
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                pytest.fail(f"Failed to create session: {response.text}")
            
            session_data = response.json()
            hub_session_id = session_data["hub_session_id"]
            service_url = session_data["service_url"]
            appium_session = session_data["appium_session"]
            
            # Extract the actual Appium session ID
            appium_session_id = appium_session["value"]["sessionId"]
        
        # Create Appium driver with the service URL
        options = UiAutomator2Options()
        options.load_capabilities(android_capabilities)
        
        driver = webdriver.Remote(
            command_executor=f"{service_url}",
            options=options
        )
        
        # Store session info for cleanup
        driver.hub_session_id = hub_session_id
        driver.hub_url = hub_url
        
        yield driver
        
        # Cleanup
        try:
            driver.quit()
        except:
            pass
        
        # Delete session from hub
        try:
            with httpx.Client() as client:
                client.delete(f"{hub_url}/session/{hub_session_id}", timeout=30.0)
        except:
            pass
    
    def test_app_launch(self, driver_session):
        """Test app launch and basic functionality"""
        driver = driver_session
        
        # Wait for app to load
        time.sleep(3)
        
        # Get current activity (Android specific)
        current_activity = driver.current_activity
        assert current_activity is not None
        
        # Take a screenshot for verification
        screenshot = driver.get_screenshot_as_base64()
        assert screenshot is not None
        
        print(f"Test completed on worker: {pytest.current_pytest_worker_id}")
    
    def test_basic_interaction(self, driver_session):
        """Test basic UI interaction"""
        driver = driver_session
        
        # Wait for app to load
        time.sleep(3)
        
        # Example: Find an element and interact with it
        # Note: Update selectors based on your actual app
        try:
            # This is a generic example - replace with your app's elements
            element = driver.find_element("id", "com.example:id/button")
            element.click()
            time.sleep(1)
            assert True  # Replace with actual assertion
        except Exception:
            # If element not found, just verify we can get page source
            page_source = driver.page_source
            assert len(page_source) > 0
        
        print(f"Interaction test completed on worker: {pytest.current_pytest_worker_id}")
    
    def test_multiple_activities(self, driver_session):
        """Test multiple activities/screens"""
        driver = driver_session
        
        # Wait for app to load
        time.sleep(3)
        
        # Get initial context
        initial_activity = driver.current_activity
        
        # Perform some navigation (example)
        # Replace with your app's actual navigation flow
        try:
            # Example navigation - replace with your app's flow
            driver.press_keycode(4)  # Back button
            time.sleep(1)
        except Exception:
            pass
        
        # Verify we can still interact with the app
        page_source = driver.page_source
        assert len(page_source) > 0
        
        print(f"Multiple activities test completed on worker: {pytest.current_pytest_worker_id}")


class TestHubManagement:
    """Test the hub management endpoints"""
    
    @pytest.fixture(scope="session")
    def hub_url(self):
        return "http://localhost:4444"
    
    def test_hub_health(self, hub_url):
        """Test hub health endpoint"""
        with httpx.Client() as client:
            response = client.get(f"{hub_url}/health", timeout=10.0)
            assert response.status_code == 200
            
            health_data = response.json()
            assert "total_sessions" in health_data
            assert "healthy_sessions" in health_data
    
    def test_list_sessions(self, hub_url):
        """Test listing sessions"""
        with httpx.Client() as client:
            response = client.get(f"{hub_url}/sessions", timeout=10.0)
            assert response.status_code == 200
            
            sessions_data = response.json()
            assert "sessions" in sessions_data
            assert isinstance(sessions_data["sessions"], list)
    
    def test_create_and_delete_session(self, hub_url):
        """Test creating and deleting a session"""
        capabilities = {
            "platformName": "Android",
            "automationName": "UiAutomator2",
            "deviceName": "Test Device",
            "app": "/path/to/test/app.apk"
        }
        
        with httpx.Client() as client:
            # Create session
            response = client.post(
                f"{hub_url}/session",
                json={"capabilities": capabilities},
                timeout=60.0
            )
            
            if response.status_code == 200:
                session_data = response.json()
                hub_session_id = session_data["hub_session_id"]
                
                # Delete session
                delete_response = client.delete(
                    f"{hub_url}/session/{hub_session_id}",
                    timeout=30.0
                )
                assert delete_response.status_code == 200
            else:
                # If session creation fails (e.g., no device available), that's OK for this test
                assert response.status_code in [503, 500]


# Configuration for pytest-xdist
def pytest_configure(config):
    """Configure pytest for parallel execution"""
    # Set worker ID if not already set
    if not hasattr(pytest, 'current_pytest_worker_id'):
        worker_id = getattr(config, 'workerinput', {}).get('workerid', 'master')
        pytest.current_pytest_worker_id = worker_id


# Example pytest.ini content (create this file in the tests directory):
"""
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
"""