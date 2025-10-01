#!/usr/bin/env python3
"""
Simple test script to verify the Appium Hub setup
"""

import sys
import os
import time
import subprocess
import requests

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def check_appium_installed():
    """Check if Appium is installed and accessible"""
    try:
        result = subprocess.run(
            ["appium", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Appium is installed: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Appium version check failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Appium version check timed out")
        return False
    except FileNotFoundError:
        print("❌ Appium not found. Please install with: npm install -g appium")
        return False
    except Exception as e:
        print(f"❌ Error checking Appium: {e}")
        return False


def test_hub_startup():
    """Test if the hub can start up properly"""
    try:
        from appium_hub.server_manager import AppiumServerManager

        print("🧪 Testing AppiumServerManager...")

        # Create a server manager instance
        manager = AppiumServerManager(port=4723, session_id="test_session")

        print("✅ AppiumServerManager created successfully")
        print(f"   - Port: {manager.port}")
        print(f"   - Session ID: {manager.session_id}")
        print(f"   - Log file: {manager.log_file}")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing server manager: {e}")
        return False


def test_basic_server_start():
    """Test starting and stopping a basic Appium server"""
    try:
        from appium_hub.server_manager import AppiumServerManager

        print("🧪 Testing Appium server start/stop...")

        manager = AppiumServerManager(port=4725, session_id="test_basic")

        print("   Starting server...")
        if manager.start(timeout=20):
            print("✅ Server started successfully")

            print("   Checking if server is alive...")
            if manager.is_alive():
                print("✅ Server is responding")
            else:
                print("⚠️  Server is not responding to health checks")

            print("   Stopping server...")
            if manager.stop():
                print("✅ Server stopped successfully")
            else:
                print("⚠️  Server stop may have failed")

            return True
        else:
            print("❌ Server failed to start")
            return False

    except Exception as e:
        print(f"❌ Error testing server start/stop: {e}")
        return False


def main():
    """Run all verification tests"""
    print("🔍 Verifying Appium Hub Setup\n")

    tests = [
        ("Appium Installation", check_appium_installed),
        ("Hub Components", test_hub_startup),
        ("Server Start/Stop", test_basic_server_start),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"📋 {test_name}:")
        try:
            result = test_func()
            results.append(result)
            print(f"   Result: {'✅ PASS' if result else '❌ FAIL'}\n")
        except Exception as e:
            print(f"   Result: ❌ ERROR - {e}\n")
            results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)

    print("=" * 50)
    print(f"📊 Summary: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Your Appium Hub setup looks good.")
        print("\nNext steps:")
        print("1. Start the hub: python start_hub.py")
        print("2. Run example tests: pytest tests/test_simple_example.py -v")
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        print("\nCommon solutions:")
        print("- Install Appium: npm install -g appium")
        print("- Install drivers: appium driver install uiautomator2")
        print("- Check that Appium is in your PATH")

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
