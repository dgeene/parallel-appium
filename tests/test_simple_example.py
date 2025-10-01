"""
Simple example test demonstrating basic hub usage
"""
import pytest
import httpx
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options


@pytest.fixture(scope="session")
def hub_url():
    """Hub URL fixture"""
    return "http://localhost:4444"

@pytest.fixture(scope="session")
def udid(request):
    """Get the specific real phone we want to test on"""
    return request.config.getoption("--udid")


@pytest.fixture
def basic_android_caps(udid):
    """Basic Android capabilities for testing"""
    caps =  {
        "platformName": "Android",
        "appium:automationName": "UiAutomator2",
        "appium:udid": udid,
        "appium:deviceName": "Android Realdevice",
        "appium:appPackage": "com.android.settings",  # Using Settings app as it's always available
        "appium:appActivity": ".Settings",
        "appium:noReset": True,
        "appium:newCommandTimeout": 300
    }
    #opts = UiAutomator2Options()
    return caps #opts.load_capabilities(caps)


class TestBasicHub:
    """Basic hub functionality tests"""
    
    def test_hub_status(self, hub_url):
        """Test that hub is responding"""
        with httpx.Client() as client:
            response = client.get(hub_url, timeout=10.0)
            assert response.status_code == 200
            
            data = response.json()
            assert data["name"] == "Appium Gateway Hub"
            assert data["status"] == "running"
    
    def test_create_session_manual(self, hub_url, basic_android_caps):
        """Test creating a session manually through the hub API"""
        with httpx.Client(timeout=60.0) as client:
            # Create session
            response = client.post(
                f"{hub_url}/session",
                json={
                    "capabilities": basic_android_caps,
                    "device_name": "test_device"
                }
            )
            
            # Check if we can create a session (might fail if no device available)
            if response.status_code == 200:
                session_data = response.json()
                hub_session_id = session_data["hub_session_id"]
                
                # Get session info
                info_response = client.get(f"{hub_url}/session/{hub_session_id}/info")
                assert info_response.status_code == 200
                
                info_data = info_response.json()
                assert info_data["session_id"] == hub_session_id
                assert info_data["is_alive"] is True
                
                # Clean up
                delete_response = client.delete(f"{hub_url}/session/{hub_session_id}")
                assert delete_response.status_code == 200
            else:
                # Session creation failed - might be no devices available
                print(f"Session creation failed: {response.text}")
                assert response.status_code in [503, 500]


# Example of running tests in parallel:
"""
To run these tests in parallel using pytest-xdist:

1. Install dependencies:
   pip install pytest pytest-xdist

2. Run tests with multiple workers:
   pytest tests/ -n 4  # Run with 4 parallel workers
   
3. Run specific test with parallel execution:
   pytest tests/test_simple_example.py -n 2 -v

4. Run with custom markers:
   pytest tests/ -n 3 -m "not slow"

5. Generate HTML report:
   pip install pytest-html
   pytest tests/ -n 4 --html=report.html --self-contained-html

Environment variables for configuration:
export HUB_HOST=localhost
export HUB_PORT=4444
export MAX_SESSIONS=10
export APPIUM_PORT_START=4723
export APPIUM_PORT_END=4773
"""