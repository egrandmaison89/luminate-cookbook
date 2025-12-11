#!/usr/bin/env python3
"""
Quick test script to verify Playwright is working correctly.
Run this inside the Docker container to verify the setup.
"""

import sys

def test_playwright():
    """Test that Playwright can be imported and launch a browser."""
    print("Testing Playwright installation...")
    
    # Test 1: Import Playwright
    try:
        from playwright.sync_api import sync_playwright
        print("✅ Playwright imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Playwright: {e}")
        return False
    
    # Test 2: Launch browser
    try:
        print("Attempting to launch Chromium browser...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            print("✅ Chromium browser launched successfully")
            browser.close()
            print("✅ Browser closed successfully")
    except Exception as e:
        print(f"❌ Failed to launch browser: {e}")
        return False
    
    print("\n✅ All Playwright tests passed!")
    return True

if __name__ == "__main__":
    success = test_playwright()
    sys.exit(0 if success else 1)
