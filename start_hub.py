#!/usr/bin/env python3
"""
Startup script for Appium Hub
"""
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from appium_hub.main import main

if __name__ == "__main__":
    main()