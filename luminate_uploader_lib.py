#!/usr/bin/env python3
"""
Luminate Online Upload Library

Reusable functions for uploading images to Luminate Online Image Library.
Can be used by both CLI scripts and web applications.
"""

import os
import time
import requests
import subprocess
import sys
import shutil

# Playwright imports are lazy-loaded to prevent app crashes if dependencies are missing
# Use _import_playwright() helper function to safely import Playwright when needed

# Luminate Online URLs
LOGIN_URL = "https://secure2.convio.net/dfci/admin/AdminLogin"
IMAGE_LIBRARY_URL = "https://secure2.convio.net/dfci/admin/ImageLibrary"
BASE_URL = "https://danafarber.jimmyfund.org/images/content/pagebuilder/"


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


def login(page, username, password):
    """Log into Luminate Online with provided credentials."""
    page.goto(LOGIN_URL)
    
    # Wait for the page to fully load
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)  # Extra wait for JS to initialize
    
    # Use role-based selectors which are more reliable
    username_input = page.get_by_role("textbox").first
    password_input = page.get_by_role("textbox").nth(1)
    
    username_input.fill(username)
    password_input.fill(password)
    
    # Submit the form by clicking the Log In button
    page.get_by_role("button", name="Log In").click()
    
    # Wait for navigation after login
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)


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


def upload_images_batch(username, password, image_paths, progress_callback=None):
    """Upload multiple images to Luminate Online.
    
    Args:
        username: Luminate username
        password: Luminate password
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
            
            context = browser.new_context()
            page = context.new_page()
            
            try:
                # Login
                if progress_callback:
                    progress_callback(0, len(image_paths), "Logging in...", "info")
                login(page, username, password)
                
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
