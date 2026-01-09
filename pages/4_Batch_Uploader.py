#!/usr/bin/env python3
"""
Batch Uploader - Luminate Cookbook Tool

Upload multiple images to Luminate Online with robust 2FA handling.
Browser sessions stay alive during 2FA waits for seamless user experience.
"""

import streamlit as st
import tempfile
import os
import time
import threading

# Lazy import to handle cases where batch_uploader_lib might have issues
try:
    from lib.batch_uploader_lib import (
        create_browser_session,
        cleanup_browser_session,
        login_with_persistent_browser,
        submit_2fa_code_robust,
        upload_with_persistent_browser
    )
    from lib.luminate_uploader_lib import (
        check_playwright_available,
        IMAGE_LIBRARY_URL,
        navigate_to_image_library
    )
    LIBRARY_AVAILABLE = True
except ImportError as e:
    LIBRARY_AVAILABLE = False
    IMPORT_ERROR = str(e)
except Exception as e:
    LIBRARY_AVAILABLE = False
    IMPORT_ERROR = f"Error importing library: {str(e)}"

# Page configuration
st.set_page_config(
    page_title="Batch Uploader",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp {
        max-width: 1000px;
        margin: 0 auto;
    }
    .success-box {
        padding: 1em;
        background-color: #d4edda;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin: 1em 0;
    }
    .error-box {
        padding: 1em;
        background-color: #f8d7da;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
        margin: 1em 0;
    }
    .info-box {
        padding: 1em;
        background-color: #0d6efd;
        color: white;
        border-radius: 5px;
        border: 1px solid #0a58ca;
        margin: 1em 0;
    }
    .warning-box {
        padding: 1em;
        background-color: #fff3cd;
        border-radius: 5px;
        border: 1px solid #ffc107;
        margin: 1em 0;
    }
    h1 {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for browser management
if 'batch_playwright' not in st.session_state:
    st.session_state.batch_playwright = None
if 'batch_browser' not in st.session_state:
    st.session_state.batch_browser = None
if 'batch_context' not in st.session_state:
    st.session_state.batch_context = None
if 'batch_page' not in st.session_state:
    st.session_state.batch_page = None
if 'batch_needs_2fa' not in st.session_state:
    st.session_state.batch_needs_2fa = False
if 'batch_pending_files' not in st.session_state:
    st.session_state.batch_pending_files = None
if 'batch_credentials' not in st.session_state:
    st.session_state.batch_credentials = None
if 'batch_upload_results' not in st.session_state:
    st.session_state.batch_upload_results = None
if 'batch_uploading' not in st.session_state:
    st.session_state.batch_uploading = False
if 'batch_2fa_error' not in st.session_state:
    st.session_state.batch_2fa_error = None
if 'batch_2fa_start_time' not in st.session_state:
    st.session_state.batch_2fa_start_time = None
if 'batch_temp_dir' not in st.session_state:
    st.session_state.batch_temp_dir = None


def cleanup_browser():
    """Clean up browser session from session state."""
    if st.session_state.batch_browser or st.session_state.batch_playwright:
        try:
            cleanup_browser_session(
                st.session_state.batch_playwright,
                st.session_state.batch_browser
            )
        except:
            pass
    st.session_state.batch_playwright = None
    st.session_state.batch_browser = None
    st.session_state.batch_context = None
    st.session_state.batch_page = None


def check_2fa_timeout():
    """Check if 2FA wait has exceeded timeout (10 minutes)."""
    if st.session_state.batch_2fa_start_time:
        elapsed = time.time() - st.session_state.batch_2fa_start_time
        if elapsed > 600:  # 10 minutes
            cleanup_browser()
            st.session_state.batch_needs_2fa = False
            st.session_state.batch_2fa_start_time = None
            st.session_state.batch_2fa_error = "2FA timeout: Browser session expired after 10 minutes. Please start a new upload."
            return True
    return False


def main():
    st.title("📦 Batch Uploader")
    st.markdown("---")
    
    # Check if the library is available
    if not LIBRARY_AVAILABLE:
        st.markdown("""
        <div class="error-box">
        <strong>⚠️ Batch Uploader Unavailable</strong><br><br>
        The Batch Uploader library could not be loaded. This may be due to missing dependencies or installation issues.
        </div>
        """, unsafe_allow_html=True)
        st.error(f"Import error: {IMPORT_ERROR}")
        st.info("Please check the deployment logs or contact support.")
        return
    
    # Check if Playwright is available
    try:
        playwright_available, playwright_error = check_playwright_available()
    except Exception as e:
        playwright_available = False
        playwright_error = f"Error checking Playwright availability: {str(e)}"
    
    if not playwright_available:
        st.markdown("""
        <div class="error-box">
        <strong>⚠️ Browser Automation Unavailable</strong><br><br>
        The Batch Uploader requires browser automation to upload images to Luminate Online.
        This feature is currently not available in this environment.
        </div>
        """, unsafe_allow_html=True)
        st.info(playwright_error or "Browser automation is not available.")
        return
    
    st.markdown("""
    <div class="info-box">
    <strong>Welcome to Batch Uploader!</strong> Upload multiple images to your Luminate Online Image Library.
    <br><br>
    <strong>🔐 2FA Support:</strong> If two-factor authentication is required, your browser session will stay open 
    while you enter your 6-digit code. No need to start over!
    </div>
    """, unsafe_allow_html=True)
    
    # Check for 2FA timeout
    if check_2fa_timeout():
        st.warning(st.session_state.batch_2fa_error)
    
    # Step 1: Credentials
    st.subheader("Step 1: Enter Your Luminate Credentials")
    
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input(
            "Username",
            value=st.session_state.get('batch_username', ''),
            help="Your Luminate Online username (email address)",
            key="batch_username_input"
        )
    with col2:
        password = st.text_input(
            "Password",
            type="password",
            value="",
            help="Your Luminate Online password",
            key="batch_password_input"
        )
    
    # 2FA Input Section (shown when 2FA is required)
    if st.session_state.batch_needs_2fa:
        st.markdown("---")
        st.markdown("""
        <div class="warning-box">
        <strong>🔐 Two-Factor Authentication Required</strong><br><br>
        Please enter the 6-digit verification code sent to your phone or authenticator app.
        Your browser session is waiting - enter the code below to continue.
        </div>
        """, unsafe_allow_html=True)
        
        # Show timeout warning if approaching limit
        if st.session_state.batch_2fa_start_time:
            elapsed = time.time() - st.session_state.batch_2fa_start_time
            remaining = 600 - elapsed  # 10 minutes total
            if remaining < 120:  # Less than 2 minutes left
                st.warning(f"⚠️ Browser session will expire in {int(remaining/60)} minutes. Please enter your code soon.")
        
        col_code, col_submit = st.columns([2, 1])
        with col_code:
            two_factor_input = st.text_input(
                "Enter 6-digit code",
                value="",
                max_chars=6,
                key="batch_2fa_input",
                help="Enter the 6-digit code from your text message or authenticator app"
            )
        with col_submit:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            submit_2fa = st.button("Submit Code", type="primary", use_container_width=True, key="batch_submit_2fa")
        
        # Show error if any
        if st.session_state.batch_2fa_error:
            st.error(st.session_state.batch_2fa_error)
        
        # Handle 2FA code submission
        if submit_2fa:
            # Validate code format
            if not two_factor_input or len(two_factor_input) != 6 or not two_factor_input.isdigit():
                st.session_state.batch_2fa_error = "Please enter a valid 6-digit code."
                st.rerun()
            else:
                # Clear error and attempt to submit code
                st.session_state.batch_2fa_error = None
                st.session_state.batch_uploading = True
                
                # Get the page from session state
                if st.session_state.batch_page:
                    try:
                        # Submit the 2FA code using the persistent browser
                        success, error = submit_2fa_code_robust(
                            st.session_state.batch_page,
                            two_factor_input
                        )
                        
                        if success:
                            # 2FA successful, continue with upload
                            st.session_state.batch_needs_2fa = False
                            st.session_state.batch_2fa_start_time = None
                            st.rerun()
                        else:
                            # 2FA failed
                            st.session_state.batch_2fa_error = error or "Invalid code. Please try again."
                            st.session_state.batch_uploading = False
                            st.rerun()
                    except Exception as e:
                        st.session_state.batch_2fa_error = f"Error submitting code: {str(e)}"
                        st.session_state.batch_uploading = False
                        st.rerun()
                else:
                    st.session_state.batch_2fa_error = "Browser session lost. Please start a new upload."
                    cleanup_browser()
                    st.session_state.batch_needs_2fa = False
                    st.session_state.batch_uploading = False
                    st.rerun()
    
    # Step 2: File Upload
    st.markdown("---")
    st.subheader("Step 2: Select Images to Upload")
    
    st.info("💡 **Tip:** Each file should be under 10MB. If you get an upload error, try compressing your images first.")
    
    uploaded_files = st.file_uploader(
        "Choose image files",
        type=['jpg', 'jpeg', 'png', 'gif'],
        accept_multiple_files=True,
        help="You can select multiple images at once. Supported formats: JPG, PNG, GIF. Maximum file size: 10MB per file.",
        key="batch_file_uploader"
    )
    
    if uploaded_files:
        # Validate file sizes
        invalid_files = []
        for file in uploaded_files:
            file_size_mb = file.size / (1024 * 1024)
            if file_size_mb > 10:
                invalid_files.append((file.name, file_size_mb))
        
        if invalid_files:
            st.error("⚠️ Some files are too large:")
            for filename, size_mb in invalid_files:
                st.error(f"  • {filename}: {size_mb:.1f}MB (max 10MB)")
            st.info("Please resize or compress these files before uploading.")
        else:
            st.success(f"✅ {len(uploaded_files)} image(s) selected")
            
            # Show file list
            with st.expander("View selected files"):
                for i, file in enumerate(uploaded_files, 1):
                    file_size_mb = file.size / (1024 * 1024)
                    st.text(f"{i}. {file.name} ({file_size_mb:.2f} MB)")
    
    # Step 3: Upload Button
    st.markdown("---")
    
    # Use pending files if available (for 2FA retry), otherwise use current uploaded files
    files_to_upload = st.session_state.batch_pending_files if st.session_state.batch_pending_files else uploaded_files
    
    has_credentials = username and password
    can_upload = playwright_available and has_credentials and files_to_upload and not st.session_state.batch_uploading and not st.session_state.batch_needs_2fa
    
    # Show status
    if not has_credentials:
        st.warning("⚠️ Please enter your username and password (Step 1)")
    elif not files_to_upload:
        st.info("📁 Select images to upload (Step 2)")
    elif st.session_state.batch_needs_2fa:
        st.info("🔐 Please enter your 2FA code above to continue")
    
    if st.button(
        "🚀 Upload All Images",
        type="primary",
        disabled=not can_upload,
        use_container_width=True,
        key="batch_upload_button"
    ):
        if not has_credentials:
            st.error("Please provide username and password")
            return
        
        if not files_to_upload:
            st.error("Please select at least one image to upload")
            return
        
        # Clear previous results
        st.session_state.batch_upload_results = None
        st.session_state.batch_2fa_error = None
        
        # Start upload process
        st.session_state.batch_uploading = True
        
        # Save uploaded files to temporary directory
        if 'batch_temp_dir' not in st.session_state or not st.session_state.batch_temp_dir:
            temp_dir = tempfile.mkdtemp()
            st.session_state.batch_temp_dir = temp_dir
        else:
            temp_dir = st.session_state.batch_temp_dir
        
        image_paths = []
        
        try:
            # Use pending file paths if available (for 2FA retry), otherwise save current uploaded files
            if st.session_state.batch_pending_files:
                image_paths = st.session_state.batch_pending_files
            else:
                # Save current uploaded files
                for uploaded_file in files_to_upload:
                    file_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    image_paths.append(file_path)
                # Store file paths for potential 2FA retry
                st.session_state.batch_pending_files = image_paths
            
            # Store credentials
            st.session_state.batch_credentials = {
                'username': username,
                'password': password
            }
            
            # Create progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.empty()
            
            # Progress callback function
            def progress_callback(current, total, filename, status):
                if status == "info":
                    status_text.info(f"🔄 {filename}")
                elif status == "uploading":
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.info(f"📤 Uploading {current}/{total}: {filename}")
                elif status == "success":
                    status_text.success(f"✅ Uploaded {current}/{total}: {filename}")
                elif status == "error":
                    status_text.warning(f"⚠️ Failed {current}/{total}: {filename}")
            
            # Create or reuse browser session
            if not st.session_state.batch_browser:
                status_text.info("🌐 Starting browser session...")
                playwright_instance, browser, context, page = create_browser_session()
                
                if not browser:
                    st.error("Failed to create browser session. Please try again.")
                    st.session_state.batch_uploading = False
                    return
                
                st.session_state.batch_playwright = playwright_instance
                st.session_state.batch_browser = browser
                st.session_state.batch_context = context
                st.session_state.batch_page = page
            else:
                page = st.session_state.batch_page
            
            # Attempt login
            status_text.info("🔄 Logging in to Luminate Online...")
            login_success, needs_2fa, login_error = login_with_persistent_browser(
                page,
                username,
                password
            )
            
            if needs_2fa:
                # 2FA required - keep browser alive and show input
                st.session_state.batch_needs_2fa = True
                st.session_state.batch_2fa_start_time = time.time()
                st.session_state.batch_uploading = False
                progress_bar.empty()
                status_text.empty()
                st.warning("🔐 Two-factor authentication is required. Please enter your 6-digit code above.")
                st.rerun()
            
            if not login_success:
                # Login failed
                cleanup_browser()
                st.session_state.batch_uploading = False
                error_msg = login_error or "Login failed. Please check your credentials and try again."
                st.error(f"❌ {error_msg}")
                return
            
            # Login successful, proceed with uploads
            status_text.info("✅ Logged in successfully! Starting uploads...")
            
            # Navigate to Image Library
            try:
                navigate_to_image_library(page)
            except:
                pass  # Might already be there
            
            # Upload images
            results = upload_with_persistent_browser(
                page,
                image_paths,
                progress_callback
            )
            
            # Store results
            st.session_state.batch_upload_results = results
            st.session_state.batch_uploading = False
            
            # Clean up browser and temp files
            cleanup_browser()
            
            # Clear 2FA state and pending files on successful upload
            st.session_state.batch_needs_2fa = False
            st.session_state.batch_2fa_start_time = None
            st.session_state.batch_pending_files = None
            st.session_state.batch_credentials = None
            
            # Clean up temp directory
            if st.session_state.batch_temp_dir:
                try:
                    import shutil
                    shutil.rmtree(st.session_state.batch_temp_dir, ignore_errors=True)
                except:
                    pass
                st.session_state.batch_temp_dir = None
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Show results
            if results:
                display_results(results)
            
        except Exception as e:
            st.session_state.batch_uploading = False
            cleanup_browser()
            st.error(f"❌ An error occurred: {str(e)}")
            st.info("Please check your credentials and try again.")
        finally:
            # Only clean up temporary files if upload completed successfully
            if not st.session_state.batch_needs_2fa and st.session_state.batch_pending_files:
                # Clean up temporary files
                for file_path in image_paths:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except:
                        pass
                # Clean up temp directory if we're done
                if st.session_state.batch_temp_dir:
                    try:
                        import shutil
                        if os.path.exists(st.session_state.batch_temp_dir):
                            shutil.rmtree(st.session_state.batch_temp_dir, ignore_errors=True)
                    except:
                        pass
                    st.session_state.batch_temp_dir = None
                    st.session_state.batch_pending_files = None
    
    # Display results only if we just completed an upload (not from cache)
    if st.session_state.batch_upload_results and not st.session_state.batch_uploading:
        st.markdown("---")
        st.subheader("📋 Upload Results")
        display_results(st.session_state.batch_upload_results)
        
        # Add a button to clear results
        if st.button("🔄 Start New Upload", use_container_width=True, key="batch_new_upload"):
            st.session_state.batch_upload_results = None
            cleanup_browser()
            st.rerun()
    
    # Cleanup on page unload (when user navigates away)
    # Note: This is best-effort since Streamlit doesn't have a reliable on_unload hook
    # The browser will be cleaned up when session expires or on next page load


def display_results(results):
    """Display upload results in a user-friendly format."""
    successful = results['successful']
    failed = results['failed']
    urls = results['urls']
    
    # Success summary
    if successful:
        st.markdown(f"""
        <div class="success-box">
        <strong>✅ Successfully uploaded {len(successful)} image(s)!</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # Display URLs
        st.subheader("📎 Uploaded Image URLs")
        st.markdown("Click the copy button to copy each URL:")
        
        for i, url in enumerate(urls, 1):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text_input(
                    f"URL {i}",
                    value=url,
                    key=f"batch_url_input_{i}",
                    disabled=True,
                    label_visibility="collapsed"
                )
            with col2:
                copy_key = f"batch_copy_btn_{i}"
                if st.button("📋 Copy", key=copy_key, use_container_width=True):
                    escaped_url = url.replace("'", "\\'")
                    st.markdown(f"""
                    <script>
                    navigator.clipboard.writeText('{escaped_url}').then(function() {{
                        var msg = document.createElement('div');
                        msg.textContent = '✓ Copied!';
                        msg.style.cssText = 'position:fixed;top:20px;right:20px;background:#28a745;color:white;padding:10px;border-radius:5px;z-index:9999;';
                        document.body.appendChild(msg);
                        setTimeout(function() {{ msg.remove(); }}, 2000);
                    }});
                    </script>
                    """, unsafe_allow_html=True)
                    st.rerun()
        
        # Download URLs as text file
        urls_text = "\n".join(urls)
        st.download_button(
            label="💾 Download All URLs as Text File",
            data=urls_text,
            file_name="uploaded_urls.txt",
            mime="text/plain",
            key="batch_download_urls"
        )
    
    # Failed uploads
    if failed:
        st.markdown(f"""
        <div class="error-box">
        <strong>⚠️ {len(failed)} upload(s) failed</strong>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("View failed uploads"):
            for filename, error in failed:
                st.error(f"**{filename}**: {error}")
    
    # Summary stats
    total = len(successful) + len(failed)
    if total > 0:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Images", total)
        col2.metric("Successful", len(successful), delta=f"{len(successful)/total*100:.0f}%")
        col3.metric("Failed", len(failed))


if __name__ == "__main__":
    main()
