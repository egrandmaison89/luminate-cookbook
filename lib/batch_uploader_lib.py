#!/usr/bin/env python3
"""
Batch Uploader Library - Persistent Browser Sessions

Provides functions for uploading images to Luminate Online with persistent
browser sessions that stay alive during 2FA waits. Designed for multi-user
Cloud Run deployments where each user session maintains its own browser instance.
"""

import os
import time
import random
import re
from typing import Optional, Dict, List, Tuple, Any

# Import from existing library
from lib.luminate_uploader_lib import (
    _import_playwright,
    ensure_playwright_browsers_installed,
    IMAGE_LIBRARY_URL,
    LOGIN_URL,
    upload_image,
    navigate_to_image_library,
    validate_session,
    TwoFactorAuthRequired
)


def submit_2fa_code_robust(page, two_factor_code):
    """Submit a 2FA code using the specific Luminate 2FA HTML structure.
    
    Based on the actual Luminate 2FA page structure:
    - Input field: input[name^="ADDITIONAL_AUTH"] (type="password")
    - Submit button: input[type="submit"][name="login"] or input[id="login"]
    - Form: form[name="lmainLogonForm"]
    
    Args:
        page: Playwright page object (should already be on 2FA page)
        two_factor_code: 6-digit 2FA code to submit
        
    Returns:
        tuple: (success: bool, error: str or None)
    """
    try:
        # Wait for Luminate 2FA form to be present before interacting
        try:
            page.wait_for_selector('input[name^="ADDITIONAL_AUTH"]', state='visible', timeout=5000)
        except:
            pass
        page.wait_for_timeout(1000)
        
        # Strategy 1: Look for ADDITIONAL_AUTH input (specific to Luminate 2FA)
        code_input = None
        try:
            # Try the specific Luminate 2FA input field
            potential_input = page.locator('input[name^="ADDITIONAL_AUTH"]')
            if potential_input.count() > 0:
                code_input = potential_input.first
        except:
            pass
        
        # Strategy 2: Look for password input (since Luminate uses type="password" for 2FA)
        if not code_input:
            try:
                # Find password inputs that aren't the main password field
                # The 2FA field is usually after the username/password fields
                password_inputs = page.locator('input[type="password"]')
                if password_inputs.count() > 1:
                    # Skip the first one (main password), use the second (2FA)
                    code_input = password_inputs.nth(1)
                elif password_inputs.count() == 1:
                    # Only one password field - check if we're on 2FA page
                    page_content = page.content().lower()
                    if 'security code' in page_content or 'additional' in page_content:
                        code_input = password_inputs.first
            except:
                pass
        
        # Strategy 3: Look for inputs with maxlength (6-digit codes)
        if not code_input:
            try:
                potential_input = page.locator('input[maxlength="6"], input[maxlength="99"]').first
                if potential_input.count() > 0:
                    code_input = potential_input
            except:
                pass
        
        # Strategy 4: Look for inputs with code-related attributes (fallback)
        if not code_input:
            try:
                potential_input = page.locator('input[name*="AUTH" i], input[id*="AUTH" i], input[name*="code" i], input[id*="code" i]').first
                if potential_input.count() > 0:
                    code_input = potential_input
            except:
                pass
        
        if code_input and code_input.count() > 0:
            # Found the input field, enter the code
            code_input.click()
            page.wait_for_timeout(200)
            code_input.clear()
            
            # Type the code character by character (human-like)
            for char in str(two_factor_code):
                code_input.type(char, delay=random.randint(50, 150))
            
            page.wait_for_timeout(500)
            
            # Find and click submit button
            submit_button = None
            try:
                # Strategy 1: Look for the specific Luminate submit button
                submit_button = page.locator('input[type="submit"][name="login"], input[id="login"]').first
                if submit_button.count() == 0:
                    # Strategy 2: Look for submit button in the form
                    submit_button = page.locator('form[name="lmainLogonForm"] input[type="submit"]').first
                if submit_button.count() == 0:
                    # Strategy 3: Generic submit button
                    submit_button = page.locator('input[type="submit"], button[type="submit"]').first
                if submit_button.count() == 0:
                    # Strategy 4: Role-based
                    submit_button = page.get_by_role("button", name=re.compile("log in|submit|verify", re.I)).first
            except:
                pass
            
            if submit_button and submit_button.count() > 0:
                submit_button.click()
            else:
                # Fallback: try pressing Enter
                code_input.press("Enter")
            
            # Wait for navigation
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            # Verify authentication was successful
            current_url = page.url
            if 'AdminLogin' not in current_url and 'login' not in current_url.lower():
                # Check if we can access protected content
                try:
                    page.goto(IMAGE_LIBRARY_URL, timeout=10000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_selector('text=Upload Image', timeout=5000)
                    return (True, None)
                except:
                    # Might still be authenticating, check again
                    page.wait_for_timeout(2000)
                    current_url = page.url
                    if 'AdminLogin' not in current_url and 'login' not in current_url.lower():
                        try:
                            page.wait_for_selector('text=Upload Image', timeout=5000)
                            return (True, None)
                        except:
                            pass
            
            # Check if 2FA prompt is still there (code might be invalid)
            page_content = page.content().lower()
            two_factor_indicators = [
                'two-factor', '2fa', 'verification code', 'authenticator',
                'security code', 'enter code', 'verify your identity', 'additional-auth'
            ]
            still_has_2fa = any(indicator in page_content for indicator in two_factor_indicators)
            if still_has_2fa:
                return (False, "Invalid 2FA code. Please try again.")
            else:
                # 2FA prompt gone, verify we're logged in
                try:
                    page.goto(IMAGE_LIBRARY_URL, timeout=10000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_selector('text=Upload Image', timeout=5000)
                    return (True, None)
                except:
                    return (False, "2FA code submitted but authentication verification failed.")
        else:
            return (False, "Could not find 2FA input field on the page.")
            
    except Exception as e:
        return (False, f"Error submitting 2FA code: {str(e)}")


def create_browser_session():
    """Create a new Playwright browser session.
    
    Returns:
        tuple: (playwright_instance, browser, context, page) or (None, None, None, None) if failed
    """
    try:
        sync_playwright, _, PlaywrightError = _import_playwright()
        
        # Ensure browsers are installed
        if not ensure_playwright_browsers_installed():
            return (None, None, None, None)
        
        playwright_instance = sync_playwright().start()
        browser = playwright_instance.chromium.launch(headless=True)
        
        # Context options with realistic browser fingerprint
        context_options = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'viewport': {'width': 1920, 'height': 1080},
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'color_scheme': 'light',
            'permissions': ['geolocation'],
            'extra_http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
        }
        
        context = browser.new_context(**context_options)
        page = context.new_page()
        
        # Inject JavaScript to hide automation indicators
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            window.chrome = {
                runtime: {}
            };
        """)
        
        return (playwright_instance, browser, context, page)
        
    except Exception as e:
        print(f"Error creating browser session: {str(e)}")
        return (None, None, None, None)


def cleanup_browser_session(playwright_instance=None, browser=None, context=None):
    """Safely close browser and clean up resources.
    
    Args:
        playwright_instance: Playwright instance (or None)
        browser: Playwright browser instance (or None)
        context: Optional browser context (will be closed with browser)
    """
    try:
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
    except Exception as e:
        print(f"Error cleaning up browser session: {str(e)}")


def login_with_persistent_browser(page, username, password, two_factor_code=None):
    """Log into Luminate Online with a persistent browser session.
    
    Args:
        page: Playwright page object (from persistent browser)
        username: Luminate username
        password: Luminate password
        two_factor_code: Optional 6-digit 2FA code if 2FA is required
        
    Returns:
        tuple: (success: bool, needs_2fa: bool, error: str or None)
    """
    page.goto(LOGIN_URL)
    
    # Wait for the page to fully load
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000 + random.randint(0, 1000))
    
    # Use role-based selectors
    username_input = page.get_by_role("textbox").first
    password_input = page.get_by_role("textbox").nth(1)
    
    # Simulate human typing
    username_input.click()
    page.wait_for_timeout(random.randint(100, 300))
    username_input.clear()
    for char in username:
        username_input.type(char, delay=random.randint(50, 150))
    
    page.wait_for_timeout(random.randint(200, 500))
    
    password_input.click()
    page.wait_for_timeout(random.randint(100, 300))
    password_input.clear()
    for char in password:
        password_input.type(char, delay=random.randint(50, 150))
    
    page.wait_for_timeout(random.randint(300, 800))
    
    # Submit the form
    page.get_by_role("button", name="Log In").click()
    
    # Wait for navigation (stay on current page - do NOT navigate away yet)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    
    # Check for 2FA and login errors on the CURRENT page before any navigation.
    # (Navigating to Image Library would leave the 2FA form and break detection.)
    current_url = page.url
    page_content = page.content().lower()
    
    two_factor_indicators = [
        'we sent a security code',  # Most specific - from actual 2FA page
        'security code:',  # Label from 2FA form
        'two-factor',
        '2fa',
        'verification code',
        'authenticator',
        'enter code',
        'verify your identity'
    ]
    
    has_2fa_prompt = any(indicator in page_content for indicator in two_factor_indicators)
    
    has_2fa_input = False
    try:
        auth_inputs = page.locator('input[name^="ADDITIONAL_AUTH"]')
        if auth_inputs.count() > 0 and auth_inputs.first.is_visible():
            has_2fa_input = True
    except:
        pass
    
    still_on_login = 'AdminLogin' in current_url or 'login' in current_url.lower()
    if still_on_login and not has_2fa_input:
        try:
            password_inputs = page.locator('input[type="password"]')
            if password_inputs.count() > 1:
                second_pwd = password_inputs.nth(1)
                if second_pwd.is_visible():
                    try:
                        input_name = second_pwd.get_attribute('name') or ''
                        if 'ADDITIONAL_AUTH' in input_name.upper() or 'AUTH' in input_name.upper():
                            has_2fa_input = True
                    except:
                        pass
        except:
            pass
    
    has_error = any(error_term in page_content for error_term in [
        'invalid username or password',
        'incorrect username or password',
        'login failed',
        'authentication failed',
        'invalid credentials'
    ])
    
    if has_2fa_input or (has_2fa_prompt and still_on_login):
        if two_factor_code:
            success, error = submit_2fa_code_robust(page, two_factor_code)
            if success:
                return (True, False, None)
            else:
                return (False, True, error or "2FA code submission failed")
        else:
            return (False, True, None)
    
    if has_error:
        return (False, False, "Login failed. Please check your credentials.")
    
    # No 2FA and no login error on current page - try to access Image Library to confirm success
    try:
        page.goto(IMAGE_LIBRARY_URL, timeout=10000)
        page.wait_for_load_state("networkidle")
        page.wait_for_selector('text=Upload Image', timeout=5000)
        return (True, False, None)
    except:
        pass
    
    # Image Library failed - re-check page (we may have been redirected to 2FA or login)
    current_url = page.url
    page_content = page.content().lower()
    has_2fa_prompt = any(indicator in page_content for indicator in two_factor_indicators)
    has_2fa_input = False
    try:
        auth_inputs = page.locator('input[name^="ADDITIONAL_AUTH"]')
        if auth_inputs.count() > 0 and auth_inputs.first.is_visible():
            has_2fa_input = True
    except:
        pass
    still_on_login = 'AdminLogin' in current_url or 'login' in current_url.lower()
    if still_on_login and not has_2fa_input:
        try:
            password_inputs = page.locator('input[type="password"]')
            if password_inputs.count() > 1:
                second_pwd = password_inputs.nth(1)
                if second_pwd.is_visible():
                    try:
                        input_name = second_pwd.get_attribute('name') or ''
                        if 'ADDITIONAL_AUTH' in input_name.upper() or 'AUTH' in input_name.upper():
                            has_2fa_input = True
                    except:
                        pass
        except:
            pass
    has_error = any(error_term in page_content for error_term in [
        'invalid username or password',
        'incorrect username or password',
        'login failed',
        'authentication failed',
        'invalid credentials'
    ])
    if has_2fa_input or (has_2fa_prompt and still_on_login):
        return (False, True, None)
    if has_error:
        return (False, False, "Login failed. Please check your credentials.")
    if still_on_login:
        page.wait_for_timeout(2000)
        try:
            page.goto(IMAGE_LIBRARY_URL, timeout=10000)
            page.wait_for_load_state("networkidle")
            page.wait_for_selector('text=Upload Image', timeout=5000)
            return (True, False, None)
        except:
            pass
    return (False, False, "Login verification failed. Unable to access Image Library.")


def upload_with_persistent_browser(
    page,
    image_paths: List[str],
    progress_callback=None
) -> Dict[str, Any]:
    """Upload images using a persistent browser session.
    
    Args:
        page: Playwright page object (should already be authenticated)
        image_paths: List of paths to image files
        progress_callback: Optional callback function(current, total, filename, status)
        
    Returns:
        dict: {
            'successful': list of filenames,
            'failed': list of (filename, error) tuples,
            'urls': list of URLs for successful uploads
        }
    """
    successful = []
    failed = []
    urls = []
    
    # Navigate to Image Library if not already there
    try:
        current_url = page.url
        if IMAGE_LIBRARY_URL not in current_url:
            navigate_to_image_library(page)
    except:
        navigate_to_image_library(page)
    
    # Upload each image
    for i, image_path in enumerate(image_paths, 1):
        filename = os.path.basename(image_path)
        
        if progress_callback:
            progress_callback(i, len(image_paths), filename, "uploading")
        
        success, uploaded_filename, error, url = upload_image(page, image_path, verify=True)
        
        if success and url:
            successful.append(uploaded_filename)
            urls.append(url)
            if progress_callback:
                progress_callback(i, len(image_paths), filename, "success")
        else:
            error_msg = error or "Upload verification failed"
            failed.append((filename, error_msg))
            if progress_callback:
                progress_callback(i, len(image_paths), filename, "error")
    
    return {
        'successful': successful,
        'failed': failed,
        'urls': urls
    }
