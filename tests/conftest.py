"""
Pytest configuration for parallel Appium testing
"""

import pytest
import os


def pytest_addoption(parser):
    parser.addoption(
        "--udid",
        action="store",
        default="26131JEGR16239",
        help="The UDID of the device to test on",
    )


def pytest_configure(config):
    """Configure pytest for parallel execution"""
    # Set worker ID for parallel execution
    worker_id = getattr(config, "workerinput", {}).get("workerid", "master")
    pytest.current_pytest_worker_id = worker_id

    # Add custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "android: marks tests for Android platform")
    config.addinivalue_line("markers", "ios: marks tests for iOS platform")


@pytest.fixture(scope="session")
def worker_id():
    """Get the current worker ID"""
    return getattr(pytest, "current_pytest_worker_id", "master")


@pytest.fixture(scope="session")
def hub_base_url():
    """Base URL for the Appium Hub"""
    return os.getenv("HUB_URL", "http://localhost:4444")


@pytest.fixture(scope="session")
def test_timeout():
    """Default timeout for tests"""
    return int(os.getenv("TEST_TIMEOUT", "60"))


@pytest.fixture
def unique_device_name(worker_id):
    """Generate a unique device name for this worker"""
    return f"device_{worker_id}_{os.getpid()}"
