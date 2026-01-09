#!/usr/bin/env python3
"""
Luminate Online Upload Library

Reusable functions for uploading images to Luminate Online Image Library.
Can be used by both CLI scripts and web applications.

Supports two authentication modes:
1. Username/password login (may trigger 2FA)
2. Cookie passthrough (uses user's existing browser session, bypasses 2FA)
"""

import os
import time
import random
import re
import requests
import subprocess
import sys
import shutil
import json
import hashlib

# Playwright imports are lazy-loaded to prevent app crashes if dependencies are missing
# Use _import_playwright() helper function to safely import Playwright when needed

# Luminate Online URLs
LOGIN_URL = "https://secure2.convio.net/dfci/admin/AdminLogin"
IMAGE_LIBRARY_URL = "https://secure2.convio.net/dfci/admin/ImageLibrary"
BASE_URL = "https://danafarber.jimmyfund.org/images/content/pagebuilder/"

# Authentication modes
AUTH_MODE_LOGIN = "login"  # Traditional username/password (may trigger 2FA)
AUTH_MODE_COOKIES = "cookies"  # Use pre-authenticated cookies (bypasses 2FA)


class TwoFactorAuthRequired(Exception):
    """Exception raised when 2FA is required during login."""
    def __init__(self, message, current_url=None, browser_state_path=None):
        super().__init__(message)
        self.current_url = current_url
        self.browser_state_path = browser_state_path


def is_streamlit_cloud():
    """Check if running on Streamlit Cloud."""
    return os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit-cloud" or \
           os.path.exists("/app") or \
           "streamlit" in os.environ.get("HOSTNAME", "").lower()


def _import_playwright():
    """Safely import Playwright modules.
    
    Returns:
        tuple: (sync_playwright, PlaywrightTimeout, PlaywrightError) or raises ImportError
        
    Raises:
        ImportError: If Playwright cannot be imported
        RuntimeError: If Playwright is installed but not functional
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout, Error as PlaywrightError
        return sync_playwright, PlaywrightTimeout, PlaywrightError
    except ImportError as e:
        raise ImportError(
            "Playwright is not installed. Please install it with: pip install playwright && python -m playwright install chromium"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Failed to import Playwright: {str(e)}. "
            "This may indicate a dependency issue. Please check your installation."
        ) from e


def get_storage_state_path(username):
    """Generate secure file path for storing browser state.
    
    Args:
        username: Username to generate path for
        
    Returns:
        str: Path to storage state file
    """
    # Create a hash of the username for the filename (for security)
    username_hash = hashlib.sha256(username.encode()).hexdigest()[:16]
    
    # Use temp directory for storage (works on both local and Cloud Run)
    temp_dir = os.environ.get('TMPDIR', '/tmp')
    if not os.path.exists(temp_dir):
        temp_dir = '/tmp'
    
    # Create a subdirectory for our session files
    session_dir = os.path.join(temp_dir, 'luminate_sessions')
    os.makedirs(session_dir, mode=0o700, exist_ok=True)
    
    return os.path.join(session_dir, f'luminate_session_{username_hash}.json')


def save_browser_state(context, username):
    """Save browser context state to a file.
    
    Args:
        context: Playwright browser context
        username: Username associated with this session
        
    Returns:
        str: Path to saved state file, or None if save failed
    """
    try:
        state_path = get_storage_state_path(username)
        context.storage_state(path=state_path)
        
        # Set secure permissions (user read/write only)
        os.chmod(state_path, 0o600)
        
        return state_path
    except Exception as e:
        # Log error but don't fail the operation
        print(f"Warning: Failed to save browser state: {str(e)}")
        return None


def load_browser_state(username):
    """Load saved browser state if it exists.
    
    Args:
        username: Username to load state for
        
    Returns:
        dict or None: Browser state dictionary if file exists and is valid, None otherwise
    """
    try:
        state_path = get_storage_state_path(username)
        
        if not os.path.exists(state_path):
            return None
        
        # Check file permissions (should be 600)
        file_stat = os.stat(state_path)
        if file_stat.st_mode & 0o077 != 0:
            # File has group/other permissions - consider it insecure, don't load
            print(f"Warning: Session file has insecure permissions, ignoring: {state_path}")
            return None
        
        # Load and validate JSON
        with open(state_path, 'r') as f:
            state = json.load(f)
        
        # Validate state structure
        if not isinstance(state, dict) or 'cookies' not in state:
            print(f"Warning: Invalid session state format, ignoring: {state_path}")
            return None
        
        return state_path  # Return path, Playwright can load from path directly
    except json.JSONDecodeError:
        print(f"Warning: Corrupted session state file, ignoring: {state_path}")
        return None
    except Exception as e:
        print(f"Warning: Failed to load browser state: {str(e)}")
        return None


def clear_browser_state(username):
    """Clear saved browser state for a username.
    
    Args:
        username: Username to clear state for
        
    Returns:
        bool: True if state was cleared, False otherwise
    """
    try:
        state_path = get_storage_state_path(username)
        if os.path.exists(state_path):
            os.remove(state_path)
            return True
        return False
    except Exception as e:
        print(f"Warning: Failed to clear browser state: {str(e)}")
        return False


def submit_2fa_code(page, two_factor_code):
    """Submit a 2FA code when already on the 2FA page.
    
    Args:
        page: Playwright page object (should already be on 2FA page)
        two_factor_code: 6-digit 2FA code to submit
        
    Returns:
        tuple: (success: bool, error: str or None)
    """
    try:
        # Wait a moment for the page to fully load
        page.wait_for_timeout(1000)
        
        # Try multiple strategies to find the 2FA input field
        code_input = None
        
        # Strategy 1: Look for inputs with maxlength="6" (6-digit codes)
        try:
            potential_input = page.locator('input[maxlength="6"], input[maxlength="6" i]').first
            if potential_input.count() > 0:
                code_input = potential_input
        except:
            pass
        
        # Strategy 2: Look for inputs with code-related attributes
        if not code_input:
            try:
                potential_input = page.locator('input[name*="code" i], input[id*="code" i], input[name*="verify" i], input[id*="verify" i], input[name*="2fa" i], input[id*="2fa" i], input[name*="otp" i], input[id*="otp" i]').first
                if potential_input.count() > 0:
                    code_input = potential_input
            except:
                pass
        
        # Strategy 3: Look for input type="tel" (often used for verification codes)
        if not code_input:
            try:
                tel_inputs = page.locator('input[type="tel"]')
                if tel_inputs.count() > 0:
                    code_input = tel_inputs.first
            except:
                pass
        
        # Strategy 4: Look for text inputs
        if not code_input:
            try:
                all_inputs = page.locator('input[type="text"]')
                if all_inputs.count() > 0:
                    code_input = all_inputs.first
            except:
                pass
        
        # Strategy 5: Use role-based selector for textbox
        if not code_input:
            try:
                code_input = page.get_by_role("textbox").first
            except:
                pass
        
        # Strategy 6: Look for input with pattern matching digits
        if not code_input:
            try:
                pattern_inputs = page.locator('input[pattern*="\\d"], input[pattern*="[0-9]"]')
                if pattern_inputs.count() > 0:
                    code_input = pattern_inputs.first
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
            
            # Try to find and click submit button
            submit_button = None
            try:
                # Try common submit button selectors
                submit_button = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Verify"), button:has-text("Continue")').first
                if submit_button.count() == 0:
                    # Try role-based
                    submit_button = page.get_by_role("button", name=re.compile("submit|verify|continue", re.I)).first
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
                'security code', 'enter code', 'verify your identity'
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


def login(page, username, password, wait_for_2fa=True, max_2fa_wait_time=300, two_factor_code=None):
    """Log into Luminate Online with provided credentials.
    
    Uses human-like behavior patterns and handles 2FA:
    - Simulates realistic typing speed
    - Adds random delays between actions
    - Detects 2FA prompts and can accept a 2FA code
    - Waits appropriately for page loads
    
    Args:
        page: Playwright page object
        username: Luminate username
        password: Luminate password
        wait_for_2fa: If True, wait for user to complete 2FA manually (deprecated, use two_factor_code instead)
        max_2fa_wait_time: Maximum seconds to wait for 2FA completion (default 5 minutes)
        two_factor_code: Optional 6-digit 2FA code to submit automatically
        
    Returns:
        tuple: (success: bool, needs_2fa: bool, error: str or None)
            - success: True if login successful
            - needs_2fa: True if 2FA is required but no code was provided
            - error: Error message if login failed, None otherwise
    """
    page.goto(LOGIN_URL)
    
    # Wait for the page to fully load
    page.wait_for_load_state("networkidle")
    # Add a small random delay to simulate human reading time
    page.wait_for_timeout(2000 + random.randint(0, 1000))
    
    # Use role-based selectors which are more reliable
    username_input = page.get_by_role("textbox").first
    password_input = page.get_by_role("textbox").nth(1)
    
    # Simulate human typing for username (not instant fill)
    username_input.click()
    page.wait_for_timeout(random.randint(100, 300))  # Brief pause before typing
    
    # Clear any existing content and type username character by character with human-like delays
    username_input.clear()
    for char in username:
        username_input.type(char, delay=random.randint(50, 150))
    
    # Small pause after typing username (human behavior)
    page.wait_for_timeout(random.randint(200, 500))
    
    # Move to password field
    password_input.click()
    page.wait_for_timeout(random.randint(100, 300))
    
    # Clear any existing content and type password character by character with human-like delays
    password_input.clear()
    for char in password:
        password_input.type(char, delay=random.randint(50, 150))
    
    # Brief pause before clicking submit (human behavior)
    page.wait_for_timeout(random.randint(300, 800))
    
    # Submit the form by clicking the Log In button
    page.get_by_role("button", name="Log In").click()
    
    # Wait for navigation after login
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    
    # Check if 2FA is required
    current_url = page.url
    page_content = page.content().lower()
    
    # Check for 2FA indicators in page content
    two_factor_indicators = [
        'two-factor',
        '2fa',
        'verification code',
        'authenticator',
        'security code',
        'enter code',
        'verify your identity',
        'verification',
        'enter the code',
        'six-digit',
        '6-digit',
        'text message',
        'sms code'
    ]
    
    has_2fa_prompt = any(indicator in page_content for indicator in two_factor_indicators)
    
    # Also check for 2FA-specific HTML elements
    # Look for input fields that might be for 2FA codes (6-digit codes)
    has_2fa_input = False
    try:
        # Check for input with maxlength="6" (common for 6-digit codes)
        code_inputs = page.locator('input[maxlength="6"], input[maxlength="6" i]')
        if code_inputs.count() > 0:
            has_2fa_input = True
        # Also check for inputs with pattern matching 6 digits
        pattern_inputs = page.locator('input[pattern*="6"], input[pattern*="\\d{6}"]')
        if pattern_inputs.count() > 0:
            has_2fa_input = True
        # Check for input with type="tel" (often used for verification codes)
        tel_inputs = page.locator('input[type="tel"]')
        if tel_inputs.count() > 0:
            has_2fa_input = True
    except:
        pass
    
    # Also check if we're still on login page (might indicate 2FA or error)
    still_on_login = 'AdminLogin' in current_url or 'login' in current_url.lower()
    
    # Check for error messages - if there's an error, it's not 2FA
    has_error = any(error_term in page_content for error_term in ['error', 'invalid', 'incorrect', 'failed'])
    
    if (has_2fa_prompt or has_2fa_input or (still_on_login and not has_error)):
        # 2FA is required
        if two_factor_code:
            # We have a code, try to submit it
            try:
                # Wait a moment for the page to fully load
                page.wait_for_timeout(1000)
                
                # Try multiple strategies to find the 2FA input field
                code_input = None
                
                # Strategy 1: Look for inputs with maxlength="6" (6-digit codes)
                try:
                    potential_input = page.locator('input[maxlength="6"], input[maxlength="6" i]').first
                    if potential_input.count() > 0:
                        code_input = potential_input
                except:
                    pass
                
                # Strategy 2: Look for inputs with code-related attributes
                if not code_input:
                    try:
                        potential_input = page.locator('input[name*="code" i], input[id*="code" i], input[name*="verify" i], input[id*="verify" i], input[name*="2fa" i], input[id*="2fa" i], input[name*="otp" i], input[id*="otp" i]').first
                        if potential_input.count() > 0:
                            code_input = potential_input
                    except:
                        pass
                
                # Strategy 3: Look for input type="tel" (often used for verification codes)
                if not code_input:
                    try:
                        tel_inputs = page.locator('input[type="tel"]')
                        if tel_inputs.count() > 0:
                            code_input = tel_inputs.first
                    except:
                        pass
                
                # Strategy 4: Look for text inputs (excluding username/password fields)
                if not code_input:
                    try:
                        # Get all text inputs, filter out username/password
                        all_inputs = page.locator('input[type="text"]')
                        input_count = all_inputs.count()
                        # Usually 2FA field is the first or only text input after login
                        if input_count > 0:
                            code_input = all_inputs.first
                    except:
                        pass
                
                # Strategy 5: Use role-based selector for textbox
                if not code_input:
                    try:
                        code_input = page.get_by_role("textbox").first
                    except:
                        pass
                
                # Strategy 6: Look for input with pattern matching digits
                if not code_input:
                    try:
                        pattern_inputs = page.locator('input[pattern*="\\d"], input[pattern*="[0-9]"]')
                        if pattern_inputs.count() > 0:
                            code_input = pattern_inputs.first
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
                    
                    # Try to find and click submit button
                    submit_button = None
                    try:
                        # Try common submit button selectors
                        submit_button = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Verify"), button:has-text("Continue")').first
                        if submit_button.count() == 0:
                            # Try role-based
                            submit_button = page.get_by_role("button", name=re.compile("submit|verify|continue", re.I)).first
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
                            return (True, False, None)
                        except:
                            # Might still be authenticating, check again
                            page.wait_for_timeout(2000)
                            current_url = page.url
                            if 'AdminLogin' not in current_url and 'login' not in current_url.lower():
                                try:
                                    page.wait_for_selector('text=Upload Image', timeout=5000)
                                    return (True, False, None)
                                except:
                                    pass
                    
                    # Check if 2FA prompt is still there (code might be invalid)
                    page_content = page.content().lower()
                    still_has_2fa = any(indicator in page_content for indicator in two_factor_indicators)
                    if still_has_2fa:
                        return (False, True, "Invalid 2FA code. Please try again.")
                    else:
                        # 2FA prompt gone, verify we're logged in
                        try:
                            page.goto(IMAGE_LIBRARY_URL, timeout=10000)
                            page.wait_for_load_state("networkidle")
                            page.wait_for_selector('text=Upload Image', timeout=5000)
                            return (True, False, None)
                        except:
                            return (False, True, "2FA code submitted but authentication verification failed.")
                else:
                    return (False, True, "Could not find 2FA input field on the page.")
                    
            except Exception as e:
                return (False, True, f"Error submitting 2FA code: {str(e)}")
        else:
            # No code provided, return needs_2fa=True
            return (False, True, None)
    
    # If wait_for_2fa is True and we're using the old behavior, wait manually
    if wait_for_2fa and not two_factor_code:
        # Old behavior: wait for manual completion
        start_time = time.time()
        while time.time() - start_time < max_2fa_wait_time:
            page.wait_for_timeout(2000)  # Wait 2 seconds between checks
            current_url = page.url
            page_content = page.content().lower()
            
            # Check if we've successfully logged in (navigated away from login/2FA pages)
            if 'AdminLogin' not in current_url and 'login' not in current_url.lower():
                # Check if we can see authenticated content
                try:
                    # Try navigating to image library to confirm login
                    page.goto(IMAGE_LIBRARY_URL, timeout=10000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_selector('text=Upload Image', timeout=5000)
                    # Successfully authenticated!
                    return (True, False, None)
                except:
                    # Not fully authenticated yet, continue waiting
                    pass
            
            # Check if 2FA prompt is still visible
            still_has_2fa = any(indicator in page_content for indicator in two_factor_indicators)
            if not still_has_2fa and 'AdminLogin' not in current_url:
                # 2FA prompt gone and not on login page - might be authenticated
                try:
                    page.goto(IMAGE_LIBRARY_URL, timeout=10000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_selector('text=Upload Image', timeout=5000)
                    return (True, False, None)
                except:
                    pass
        
        # Timeout waiting for 2FA
        return (False, True, "Timeout waiting for 2FA completion.")
    
    # Verify login was successful by checking if we can access protected content
    try:
        page.goto(IMAGE_LIBRARY_URL, timeout=10000)
        page.wait_for_load_state("networkidle")
        page.wait_for_selector('text=Upload Image', timeout=5000)
        return (True, False, None)
    except Exception as e:
        return (False, False, f"Login verification failed: {str(e)}")


def validate_session(page):
    """Validate if the current session is still active and authenticated.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if session is valid, False if expired or invalid
    """
    try:
        # Try to navigate to a protected page (Image Library)
        page.goto(IMAGE_LIBRARY_URL, timeout=15000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        # Check if we're redirected to login page
        current_url = page.url
        if 'AdminLogin' in current_url or 'login' in current_url.lower():
            return False
        
        # Check for 2FA prompts
        try:
            # Look for common 2FA indicators
            two_factor_indicators = [
                'two-factor',
                '2fa',
                'verification code',
                'authenticator',
                'security code'
            ]
            page_text = page.content().lower()
            for indicator in two_factor_indicators:
                if indicator in page_text:
                    # Might be a 2FA prompt, but could also be in page content
                    # Check if we can see the Upload Image button (means we're logged in)
                    try:
                        page.wait_for_selector('text=Upload Image', timeout=3000)
                        # If we can see Upload Image, we're logged in (2FA was just text on page)
                        break
                    except:
                        # Can't see Upload Image, might be 2FA prompt
                        return False
        except:
            pass
        
        # Check if we can see the Upload Image button (confirms we're logged in)
        try:
            page.wait_for_selector('text=Upload Image', timeout=5000)
            return True
        except:
            # Can't find Upload Image button, session might be invalid
            return False
    except Exception as e:
        # Any error during validation suggests session might be invalid
        print(f"Session validation error: {str(e)}")
        return False


def navigate_to_image_library(page):
    """Navigate to the Image Library."""
    page.goto(IMAGE_LIBRARY_URL)
    page.wait_for_load_state("networkidle")
    
    # Wait for the Upload Image button to be visible
    page.wait_for_selector('text=Upload Image', timeout=10000)


def verify_upload(url, max_retries=3, retry_delay=2):
    """Verify that an uploaded image URL is accessible and returns an image.
    
    Args:
        url: The URL to verify
        max_retries: Maximum number of retry attempts
        retry_delay: Seconds to wait between retries
        
    Returns:
        bool: True if URL is accessible and returns an image, False otherwise
    """
    
    for attempt in range(max_retries):
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            # Check if it's a successful response and content type is an image
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if content_type.startswith('image/'):
                    return True
            # If 404, might still be processing - retry
            if response.status_code == 404 and attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return False
        except requests.exceptions.RequestException:
            # Network error - retry if we have attempts left
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return False
        except:
            return False
    
    return False


def check_file_size(image_path, max_size_mb=10):
    """Check if file size is within limits.
    
    Args:
        image_path: Path to the image file
        max_size_mb: Maximum file size in MB (default 10MB)
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    file_size = os.path.getsize(image_path)
    file_size_mb = file_size / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        return (False, f"File too large: {file_size_mb:.1f}MB (max {max_size_mb}MB)")
    
    return (True, None)


def upload_image(page, image_path, verify=True):
    """Upload a single image to the Image Library.
    
    Args:
        page: Playwright page object
        image_path: Path to the image file to upload
        verify: Whether to verify the upload by checking the URL
        
    Returns:
        tuple: (success: bool, filename: str, error: str or None, url: str or None)
    """
    filename = os.path.basename(image_path)
    abs_path = os.path.abspath(image_path)
    
    # Check file size before attempting upload
    size_valid, size_error = check_file_size(abs_path, max_size_mb=10)
    if not size_valid:
        return (False, filename, size_error, None)
    
    try:
        # Click the Upload Image button to open the dialog
        page.get_by_role("link", name="Upload Image").click()
        
        # Wait for the dialog iframe to appear
        page.wait_for_timeout(1500)
        
        # The upload form is inside an iframe - we need to access it
        iframe_locator = page.frame_locator("iframe").last
        
        # Wait for the file input to be ready inside the iframe
        file_input = iframe_locator.locator('#imageFileUpload')
        file_input.wait_for(timeout=10000)
        
        # Check for error messages in the iframe before uploading (like duplicate filename)
        # This is a pre-check, but errors usually appear after upload attempt
        
        # Set the file on the file input
        file_input.set_input_files(abs_path)
        
        # Wait for the file to be selected
        page.wait_for_timeout(1000)
        
        # Click the Upload button inside the iframe
        upload_button = iframe_locator.locator('input[type="submit"][value="Upload"], button:has-text("Upload")')
        upload_button.click()
        
        # Wait for the upload to complete - wait for network activity to finish
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        # Check for error messages after upload attempt
        # Look for common error patterns in the iframe
        error_detected = False
        error_message = None
        
        try:
            # Check for various error indicators
            error_selectors = [
                'text=/error/i',
                'text=/too large/i',
                'text=/already exists/i',
                'text=/duplicate/i',
                'text=/file size/i',
                'text=/exceed/i',
                '.error',
                '[class*="error"]',
                '[id*="error"]'
            ]
            
            for selector in error_selectors:
                try:
                    error_elements = iframe_locator.locator(selector)
                    if error_elements.count() > 0:
                        # Get the error text
                        error_text = error_elements.first
                        if error_text.is_visible(timeout=1000):
                            error_message = error_text.inner_text(timeout=1000)
                            if error_message and len(error_message.strip()) > 0:
                                error_detected = True
                                break
                except:
                    continue
            
            # Also check the page itself for error messages
            if not error_detected:
                try:
                    page_error = page.locator('text=/error|too large|already exists|duplicate/i')
                    if page_error.count() > 0 and page_error.first.is_visible(timeout=1000):
                        error_message = page_error.first.inner_text(timeout=1000)
                        if error_message and len(error_message.strip()) > 0:
                            error_detected = True
                except:
                    pass
            
        except:
            pass  # Continue with upload verification
        
        if error_detected and error_message:
            # Close dialog if still open
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
            except:
                pass
            page.reload()
            page.wait_for_load_state("networkidle")
            page.wait_for_selector('text=Upload Image', timeout=10000)
            return (False, filename, f"Upload failed: {error_message.strip()}", None)
        
        # After upload, refresh the page to ensure clean state for next upload
        page.reload()
        page.wait_for_load_state("networkidle")
        
        # Wait for the Upload Image link to be visible again
        page.wait_for_selector('text=Upload Image', timeout=10000)
        
        # Generate URL and verify if requested
        url = generate_url(filename)
        if verify:
            # Wait a moment for the image to be processed on the server
            page.wait_for_timeout(3000)
            if not verify_upload(url, max_retries=3, retry_delay=2):
                return (False, filename, "Upload completed but image URL is not accessible. This may indicate: (1) file is still processing, (2) duplicate filename already exists, or (3) upload failed silently.", None)
        
        return (True, filename, None, url)
        
    except Exception as e:
        # Check if it's a Playwright timeout error
        error_str = str(e).lower()
        if "timeout" in error_str:
            return (False, filename, f"Timeout: {str(e)}", None)
        return (False, filename, str(e), None)


def generate_url(filename):
    """Generate the URL for an uploaded image."""
    return BASE_URL + filename


def check_playwright_available():
    """Check if Playwright is available and can be used.
    
    This function safely checks if Playwright can be imported without
    actually initializing it or accessing system libraries. Used by the UI 
    to show appropriate status messages. The actual browser check happens
    when upload is attempted.
    
    Returns:
        tuple: (available: bool, error_message: str or None)
        - available: True if Playwright can be imported, False otherwise
        - error_message: None if available, otherwise a user-friendly error message
    """
    try:
        # Just check if Playwright can be imported - don't try to initialize it
        # Initialization might access system libraries that aren't available
        # The actual browser check will happen when upload is attempted
        _import_playwright()
        
        # If import succeeds, assume it's available
        # We'll catch actual browser/system dependency errors when trying to use it
        return (True, None)
        
    except ImportError as e:
        return (False, "Playwright is not installed. Browser automation is not available.")
    except RuntimeError as e:
        return (False, f"Playwright setup error: {str(e)}")
    except Exception as e:
        return (False, f"Unexpected error checking Playwright: {str(e)}")


def ensure_playwright_browsers_installed(progress_callback=None):
    """Check if Playwright browsers are installed, and install them if missing.
    Also ensures system dependencies are installed.
    
    Args:
        progress_callback: Optional callback function for progress updates
    
    Returns:
        bool: True if browsers are available, False if installation failed
        
    Raises:
        ImportError: If Playwright cannot be imported
        RuntimeError: If system dependencies are missing
    """
    # Lazy import Playwright
    try:
        sync_playwright, _, _ = _import_playwright()
    except (ImportError, RuntimeError) as e:
        raise RuntimeError(f"Cannot use browser automation: {str(e)}") from e
    
    try:
        # Try to launch a browser to check if it's installed and working
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception as e:
        error_str = str(e).lower()
        error_message = str(e)
        
        # Check if it's a missing system library error (like libnspr4.so)
        missing_lib_indicators = [
            "cannot open shared object file",
            "libnspr4.so",
            "shared libraries",
            "no such file or directory"
        ]
        is_missing_lib = any(indicator in error_message.lower() for indicator in missing_lib_indicators)
        
        # Check if it's a browser installation error
        is_browser_missing = "executable doesn't exist" in error_str or "browsers" in error_str
        
        if is_missing_lib or is_browser_missing:
            try:
                # First, try to install system dependencies (required for Chromium to run)
                if is_missing_lib or progress_callback:
                    if progress_callback:
                        progress_callback(0, 0, "Installing Playwright system dependencies...", "info")
                    try:
                        # Install system dependencies for Chromium
                        subprocess.run(
                            [sys.executable, "-m", "playwright", "install-deps", "chromium"],
                            check=True,
                            capture_output=True,
                            timeout=300  # 5 minute timeout
                        )
                    except subprocess.CalledProcessError as deps_error:
                        # System dependencies installation might fail in restricted environments
                        # (like Streamlit Cloud), but we'll continue to try installing browsers
                        if progress_callback:
                            progress_callback(0, 0, "System dependencies installation skipped (may not be available in this environment)...", "info")
                    except subprocess.TimeoutExpired:
                        if progress_callback:
                            progress_callback(0, 0, "System dependencies installation timed out, continuing...", "info")
                
                # Then install browser binaries
                if progress_callback:
                    progress_callback(0, 0, "Installing Playwright browsers...", "info")
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True,
                    capture_output=True,
                    timeout=300  # 5 minute timeout
                )
                
                # Try launching again after installation
                try:
                    sync_playwright, _, _ = _import_playwright()
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        browser.close()
                    return True
                except Exception as retry_error:
                    # If it still fails after installation, it's likely a system dependency issue
                    retry_error_str = str(retry_error).lower()
                    if is_missing_lib or any(indicator in retry_error_str for indicator in missing_lib_indicators):
                        # Provide environment-specific guidance
                        if is_streamlit_cloud():
                            error_msg = (
                                f"Browser installed but missing system dependencies (likely libnspr4.so or similar). "
                                f"This is a known issue with Playwright on Streamlit Cloud. "
                                f"Error: {str(retry_error)}\n\n"
                                f"Possible solutions:\n"
                                f"1. Contact Streamlit Cloud support to ensure system dependencies are available\n"
                                f"2. Check Streamlit Cloud deployment logs for system library errors\n"
                                f"3. Consider using a custom Docker image with required dependencies"
                            )
                        else:
                            error_msg = (
                                f"Browser installed but missing system dependencies. "
                                f"Please install required system libraries. "
                                f"Error: {str(retry_error)}\n\n"
                                f"For Linux/Docker, install system dependencies:\n"
                                f"  python -m playwright install-deps chromium\n\n"
                                f"Or manually install: libnspr4 libnss3 libatk-bridge2.0-0 libatk1.0-0 "
                                f"libatspi2.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 "
                                f"libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libxss1 libasound2"
                            )
                        raise RuntimeError(error_msg)
                    raise
                    
            except subprocess.TimeoutExpired:
                return False
            except RuntimeError:
                # Re-raise RuntimeError (our custom error for missing system deps)
                raise
            except Exception:
                return False
        else:
            # Re-raise if it's a different error
            raise


def upload_images_batch(username, password, image_paths, progress_callback=None, two_factor_code=None):
    """Upload multiple images to Luminate Online.
    
    Args:
        username: Luminate username
        password: Luminate password
        image_paths: List of paths to image files
        progress_callback: Optional callback function(current, total, filename, status)
        two_factor_code: Optional 6-digit 2FA code if 2FA is required
        
    Returns:
        dict: {
            'successful': list of filenames,
            'failed': list of (filename, error) tuples,
            'urls': list of URLs for successful uploads
        }
        
    Raises:
        TwoFactorAuthRequired: If 2FA is required but no code was provided
    """
    successful = []
    failed = []
    urls = []
    
    # Ensure Playwright browsers are installed before attempting to use them
    try:
        if not ensure_playwright_browsers_installed(progress_callback):
            error_msg = (
                "Playwright browsers are not installed. "
                "Please run: python -m playwright install chromium"
            )
            # Mark all images as failed with this error
            for image_path in image_paths:
                filename = os.path.basename(image_path)
                failed.append((filename, error_msg))
            return {
                'successful': successful,
                'failed': failed,
                'urls': urls
            }
    except RuntimeError as e:
        # RuntimeError from ensure_playwright_browsers_installed for missing system deps
        error_msg = str(e)
        # Provide helpful guidance for Streamlit Cloud users
        if "system dependencies" in error_msg.lower() or "libnspr4" in error_msg.lower():
            error_msg += (
                "\n\nThis error typically occurs when system libraries are missing. "
                "If you're using Streamlit Cloud, please contact support or check the deployment logs. "
                "The app may need to be configured with additional system dependencies."
            )
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            failed.append((filename, error_msg))
        return {
            'successful': successful,
            'failed': failed,
            'urls': urls
        }
    except Exception as e:
        # If ensure_playwright_browsers_installed raises an unexpected error
        error_msg = f"Playwright setup error: {str(e)}"
        # Check if it's a system library error
        if "libnspr4" in error_msg.lower() or "shared object file" in error_msg.lower():
            error_msg += (
                "\n\nMissing system library detected. This may require system-level dependencies "
                "to be installed in the deployment environment."
            )
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            failed.append((filename, error_msg))
        return {
            'successful': successful,
            'failed': failed,
            'urls': urls
        }
    
    # Lazy import Playwright
    try:
        sync_playwright, _, PlaywrightError = _import_playwright()
    except (ImportError, RuntimeError) as e:
        error_msg = f"Cannot use browser automation: {str(e)}"
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            failed.append((filename, error_msg))
        return {
            'successful': successful,
            'failed': failed,
            'urls': urls
        }
    
    try:
        with sync_playwright() as p:
            # Launch browser in headless mode (better for web apps)
            try:
                browser = p.chromium.launch(headless=True)
            except PlaywrightError as e:
                error_str = str(e)
                error_lower = error_str.lower()
                
                # Check for missing system library errors
                missing_lib_indicators = [
                    "cannot open shared object file",
                    "libnspr4.so",
                    "shared libraries",
                    "no such file or directory"
                ]
                is_missing_lib = any(indicator in error_lower for indicator in missing_lib_indicators)
                
                if is_missing_lib:
                    if is_streamlit_cloud():
                        raise RuntimeError(
                            f"Missing system library detected (likely libnspr4.so or similar). "
                            f"This is a known issue with Playwright on Streamlit Cloud. "
                            f"Error: {error_str}\n\n"
                            f"The app will show a helpful error message instead of crashing. "
                            f"Browser automation is not available on Streamlit Cloud due to system dependency limitations."
                        )
                    else:
                        raise RuntimeError(
                            f"Missing system library detected. "
                            f"Error: {error_str}\n\n"
                            f"Please install system dependencies:\n"
                            f"  python -m playwright install-deps chromium\n\n"
                            f"Or manually install required packages. See TROUBLESHOOTING.md for details."
                        )
                elif "executable doesn't exist" in error_lower or "browsers" in error_lower:
                    # Provide helpful error message
                    raise RuntimeError(
                        "Playwright browser executable not found. "
                        "Please run: python -m playwright install chromium\n"
                        f"Original error: {error_str}"
                    )
                else:
                    raise
            
            # Check if we have a saved 2FA state (from previous 2FA attempt)
            # This happens when user is retrying with a 2FA code
            temp_2fa_state_path = get_storage_state_path(username).replace('.json', '_2fa.json')
            has_2fa_state = os.path.exists(temp_2fa_state_path) if two_factor_code else False
            
            # Try to load saved browser state first (normal session, not 2FA)
            saved_state_path = load_browser_state(username)
            session_valid = False
            needs_login = True
            
            # Base context options
            context_options = {
                # Use a realistic user agent (Chrome on Windows)
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                # Set realistic viewport size (common desktop resolution)
                'viewport': {'width': 1920, 'height': 1080},
                # Set locale and timezone (US-based defaults)
                'locale': 'en-US',
                'timezone_id': 'America/New_York',
                # Set color scheme preference
                'color_scheme': 'light',
                # Grant common permissions to appear more like a real browser
                'permissions': ['geolocation'],
                # Set extra HTTP headers that real browsers send
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
            
            # If we have a saved 2FA state, use it (this means we're retrying with a code)
            if has_2fa_state:
                context_options['storage_state'] = temp_2fa_state_path
                if progress_callback:
                    progress_callback(0, len(image_paths), "Restoring 2FA session...", "info")
            # Otherwise, if we have a saved state, try to use it
            elif saved_state_path:
                context_options['storage_state'] = saved_state_path
                if progress_callback:
                    progress_callback(0, len(image_paths), "Loading saved session...", "info")
            
            # Create browser context with saved state (if available)
            context = browser.new_context(**context_options)
            
            page = context.new_page()
            
            # Inject JavaScript to hide automation indicators
            # This helps avoid detection by anti-bot systems
            page.add_init_script("""
                // Override webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override plugins to appear more realistic
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Chrome runtime override
                window.chrome = {
                    runtime: {}
                };
            """)
            
            try:
                # If we have a saved state, validate it first
                if saved_state_path:
                    if progress_callback:
                        progress_callback(0, len(image_paths), "Validating saved session...", "info")
                    session_valid = validate_session(page)
                    
                    if session_valid:
                        # Session is valid, skip login
                        needs_login = False
                        if progress_callback:
                            progress_callback(0, len(image_paths), "Using saved session (no login needed)...", "info")
                        # Navigate to Image Library
                        navigate_to_image_library(page)
                    else:
                        # Session expired, clear it and login
                        if progress_callback:
                            progress_callback(0, len(image_paths), "Saved session expired, logging in...", "info")
                        clear_browser_state(username)
                        needs_login = True
                
                # Login if needed
                if needs_login:
                    # If we have a 2FA state, we're retrying with a code
                    if has_2fa_state and two_factor_code:
                        if progress_callback:
                            progress_callback(0, len(image_paths), "Restoring 2FA session...", "info")
                        # Navigate to login URL - the saved state contains cookies that should
                        # keep us authenticated to the 2FA page
                        page.goto(LOGIN_URL, timeout=30000)
                        page.wait_for_load_state("networkidle")
                        page.wait_for_timeout(2000)
                        
                        # Check if we're on the 2FA page
                        page_content = page.content().lower()
                        two_factor_indicators = [
                            'two-factor', '2fa', 'verification code', 'authenticator',
                            'security code', 'enter code', 'verify your identity'
                        ]
                        is_on_2fa_page = any(indicator in page_content for indicator in two_factor_indicators)
                        
                        if is_on_2fa_page:
                            # We're on the 2FA page, submit the code directly
                            if progress_callback:
                                progress_callback(0, len(image_paths), "Submitting 2FA code...", "info")
                            login_success, login_error = submit_2fa_code(page, two_factor_code)
                            needs_2fa = False if login_success else True
                            if not login_success and not login_error:
                                login_error = "2FA code submission failed"
                        else:
                            # Not on 2FA page, try normal login (might have been redirected)
                            if progress_callback:
                                progress_callback(0, len(image_paths), "Logging in to Luminate Online...", "info")
                            login_success, needs_2fa, login_error = login(page, username, password, wait_for_2fa=False, two_factor_code=two_factor_code)
                    else:
                        if progress_callback:
                            progress_callback(0, len(image_paths), "Logging in to Luminate Online...", "info")
                        
                        login_success, needs_2fa, login_error = login(page, username, password, wait_for_2fa=False, two_factor_code=two_factor_code)
                    
                    if needs_2fa:
                        # 2FA is required - save browser state before raising exception
                        # This preserves the session so we can continue after user enters code
                        current_url = page.url
                        
                        # Save browser state to a temporary file for 2FA retry
                        # Use a special 2FA state file that will be loaded on retry
                        temp_2fa_state_path = get_storage_state_path(username).replace('.json', '_2fa.json')
                        try:
                            context.storage_state(path=temp_2fa_state_path)
                            os.chmod(temp_2fa_state_path, 0o600)
                        except Exception as e:
                            # If we can't save state, still raise exception but without state
                            temp_2fa_state_path = None
                        
                        # Raise exception with context information
                        raise TwoFactorAuthRequired(
                            "Two-factor authentication is required. Please enter your 6-digit code.",
                            current_url=current_url,
                            browser_state_path=temp_2fa_state_path
                        )
                    
                    if not login_success:
                        # Login failed
                        error_msg = login_error or "Login failed. Please check your credentials and try again."
                        for image_path in image_paths:
                            filename = os.path.basename(image_path)
                            failed.append((filename, error_msg))
                        return {
                            'successful': successful,
                            'failed': failed,
                            'urls': urls
                        }
                    
                    # Save browser state after successful login
                    if progress_callback:
                        progress_callback(0, len(image_paths), "Saving session for future use...", "info")
                    save_browser_state(context, username)
                    
                    # Clean up 2FA state file if it exists (login successful)
                    if has_2fa_state and os.path.exists(temp_2fa_state_path):
                        try:
                            os.remove(temp_2fa_state_path)
                        except:
                            pass
                    
                    # Navigate to Image Library
                    if progress_callback:
                        progress_callback(0, len(image_paths), "Navigating to Image Library...", "info")
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
            
            except TwoFactorAuthRequired:
                # Re-raise 2FA exception so it can be handled by the caller
                # Don't mark images as failed - we'll retry after user enters code
                raise
            except Exception as e:
                # If login or navigation fails, mark all as failed
                for image_path in image_paths:
                    filename = os.path.basename(image_path)
                    failed.append((filename, f"Initialization error: {str(e)}"))
            finally:
                # Safely close browser if it was created
                try:
                    if 'browser' in locals() and browser:
                        browser.close()
                except:
                    pass  # Browser may not have been created or already closed
    
    except RuntimeError as e:
        # Catch our custom RuntimeError for missing browsers
        error_msg = str(e)
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            failed.append((filename, error_msg))
    except Exception as e:
        # Catch any other unexpected errors during browser launch
        error_msg = f"Browser launch error: {str(e)}"
        error_lower = str(e).lower()
        
        # Check for system library errors
        missing_lib_indicators = [
            "cannot open shared object file",
            "libnspr4.so",
            "shared libraries",
            "no such file or directory"
        ]
        is_missing_lib = any(indicator in error_lower for indicator in missing_lib_indicators)
        
        if is_missing_lib:
            if is_streamlit_cloud():
                error_msg += (
                    "\n\nMissing system library detected. This is a known issue with Playwright on Streamlit Cloud. "
                    "The app handles this gracefully and will show a helpful error message. "
                    "Browser automation is not available on Streamlit Cloud due to system dependency limitations."
                )
            else:
                error_msg += (
                    "\n\nMissing system library detected. Please install system dependencies:\n"
                    "  python -m playwright install-deps chromium\n\n"
                    "Or see TROUBLESHOOTING.md for manual installation instructions."
                )
        elif "executable doesn't exist" in error_lower:
            error_msg += "\nPlease run: python -m playwright install chromium"
        
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            failed.append((filename, error_msg))
    
    return {
        'successful': successful,
        'failed': failed,
        'urls': urls
    }


def upload_images_with_cookies(cookies, image_paths, progress_callback=None):
    """
    Upload images using pre-authenticated cookies (bypasses 2FA).
    
    This is the recommended approach when users have an existing Luminate session
    in their browser. They can export their session cookies and use them here,
    avoiding the need to log in again (which would trigger 2FA from the server).
    
    Args:
        cookies: List of cookie dicts or Playwright storage state dict
                 Each cookie should have: name, value, domain, path
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
    
    # Ensure Playwright browsers are installed
    try:
        if not ensure_playwright_browsers_installed(progress_callback):
            error_msg = "Playwright browsers are not installed."
            for image_path in image_paths:
                filename = os.path.basename(image_path)
                failed.append((filename, error_msg))
            return {'successful': successful, 'failed': failed, 'urls': urls}
    except Exception as e:
        error_msg = f"Playwright setup error: {str(e)}"
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            failed.append((filename, error_msg))
        return {'successful': successful, 'failed': failed, 'urls': urls}
    
    # Import Playwright
    try:
        sync_playwright, _, PlaywrightError = _import_playwright()
    except (ImportError, RuntimeError) as e:
        error_msg = f"Cannot use browser automation: {str(e)}"
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            failed.append((filename, error_msg))
        return {'successful': successful, 'failed': failed, 'urls': urls}
    
    # Normalize cookies to Playwright storage state format
    if isinstance(cookies, list):
        storage_state = {'cookies': cookies, 'origins': []}
    elif isinstance(cookies, dict) and 'cookies' in cookies:
        storage_state = cookies
    else:
        error_msg = "Invalid cookie format"
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            failed.append((filename, error_msg))
        return {'successful': successful, 'failed': failed, 'urls': urls}
    
    try:
        with sync_playwright() as p:
            if progress_callback:
                progress_callback(0, len(image_paths), "Starting browser...", "info")
            
            browser = p.chromium.launch(headless=True)
            
            # Context options with realistic browser fingerprint
            context_options = {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'viewport': {'width': 1920, 'height': 1080},
                'locale': 'en-US',
                'timezone_id': 'America/New_York',
                'color_scheme': 'light',
                'extra_http_headers': {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                }
            }
            
            # Create context with cookies
            context = browser.new_context(**context_options, storage_state=storage_state)
            page = context.new_page()
            
            # Inject anti-detection script
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                window.chrome = { runtime: {} };
            """)
            
            try:
                # Navigate directly to Image Library (cookies should authenticate us)
                if progress_callback:
                    progress_callback(0, len(image_paths), "Verifying session...", "info")
                
                page.goto(IMAGE_LIBRARY_URL, timeout=30000)
                page.wait_for_load_state("networkidle")
                
                # Check if we're authenticated
                current_url = page.url
                if 'AdminLogin' in current_url or 'login' in current_url.lower():
                    # Cookies didn't work - session might be expired
                    error_msg = (
                        "Session cookies are invalid or expired. "
                        "Please log into Luminate in your browser again and export fresh cookies."
                    )
                    for image_path in image_paths:
                        filename = os.path.basename(image_path)
                        failed.append((filename, error_msg))
                    return {'successful': successful, 'failed': failed, 'urls': urls}
                
                # Check for 2FA prompt (shouldn't happen with valid cookies, but just in case)
                page_content = page.content().lower()
                two_factor_indicators = ['two-factor', '2fa', 'verification code', 'authenticator']
                if any(indicator in page_content for indicator in two_factor_indicators):
                    error_msg = (
                        "2FA is still being requested. Your session cookies may not include the 2FA completion. "
                        "Please complete 2FA in your browser and export cookies again."
                    )
                    for image_path in image_paths:
                        filename = os.path.basename(image_path)
                        failed.append((filename, error_msg))
                    return {'successful': successful, 'failed': failed, 'urls': urls}
                
                # Verify we can see the Upload button
                try:
                    page.wait_for_selector('text=Upload Image', timeout=10000)
                except:
                    error_msg = "Could not access Image Library. Session may be invalid."
                    for image_path in image_paths:
                        filename = os.path.basename(image_path)
                        failed.append((filename, error_msg))
                    return {'successful': successful, 'failed': failed, 'urls': urls}
                
                if progress_callback:
                    progress_callback(0, len(image_paths), "Session valid! Starting uploads...", "info")
                
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
                
            finally:
                browser.close()
                
    except Exception as e:
        error_msg = f"Upload error: {str(e)}"
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            if not any(f[0] == filename for f in failed):  # Avoid duplicates
                failed.append((filename, error_msg))
    
    return {
        'successful': successful,
        'failed': failed,
        'urls': urls
    }


def upload_images_auto(
    image_paths, 
    username=None, 
    password=None, 
    cookies=None,
    progress_callback=None
):
    """
    Unified upload function that automatically chooses the best authentication method.
    
    Priority:
    1. If cookies provided and valid -> use cookie-based auth (no 2FA)
    2. If username/password provided -> use login-based auth (may trigger 2FA)
    
    Args:
        image_paths: List of paths to image files
        username: Optional Luminate username
        password: Optional Luminate password  
        cookies: Optional pre-authenticated cookies (recommended to avoid 2FA)
        progress_callback: Optional callback function(current, total, filename, status)
        
    Returns:
        dict: {
            'successful': list of filenames,
            'failed': list of (filename, error) tuples,
            'urls': list of URLs for successful uploads,
            'auth_method': 'cookies' or 'login'
        }
    """
    # Try cookies first (preferred - no 2FA)
    if cookies:
        if progress_callback:
            progress_callback(0, len(image_paths), "Using session cookies (no login needed)...", "info")
        
        result = upload_images_with_cookies(cookies, image_paths, progress_callback)
        result['auth_method'] = 'cookies'
        return result
    
    # Fall back to login
    if username and password:
        if progress_callback:
            progress_callback(0, len(image_paths), "Logging in (may require 2FA)...", "info")
        
        result = upload_images_batch(username, password, image_paths, progress_callback)
        result['auth_method'] = 'login'
        return result
    
    # No auth provided
    error_msg = "No authentication provided. Please provide either cookies or username/password."
    return {
        'successful': [],
        'failed': [(os.path.basename(p), error_msg) for p in image_paths],
        'urls': [],
        'auth_method': None
    }
