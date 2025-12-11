#!/usr/bin/env python3
"""
Image Uploader - Luminate Cookbook Tool

Batch upload images directly to your Luminate Online Image Library.

Supports two authentication modes:
1. Cookie Passthrough (Recommended): Use your existing browser session - NO 2FA needed!
2. Username/Password: Traditional login - may trigger 2FA
"""

import streamlit as st
import streamlit.components.v1 as components
import tempfile
import os
import json

# Lazy import to handle cases where luminate_uploader_lib might have issues
try:
    from lib.luminate_uploader_lib import (
        upload_images_batch, 
        upload_images_with_cookies,
        upload_images_auto,
        check_playwright_available,
        load_browser_state,
        clear_browser_state,
        get_storage_state_path
    )
    LIBRARY_AVAILABLE = True
except ImportError as e:
    LIBRARY_AVAILABLE = False
    IMPORT_ERROR = str(e)
except Exception as e:
    LIBRARY_AVAILABLE = False
    IMPORT_ERROR = f"Error importing library: {str(e)}"

# Try to import cookie helper
try:
    from lib.cookie_helper import (
        parse_cookie_export,
        parse_simple_cookie_paste,
        cookies_to_playwright_state,
        validate_luminate_cookies,
        get_cookie_extraction_bookmarklet,
        get_browser_instructions,
        create_simple_cookie_paste_instructions
    )
    COOKIE_HELPER_AVAILABLE = True
except ImportError:
    COOKIE_HELPER_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Image Uploader",
    page_icon="📤",
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
    h1 {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'upload_results' not in st.session_state:
    st.session_state.upload_results = None
if 'uploading' not in st.session_state:
    st.session_state.uploading = False


def main():
    st.title("📤 Image Uploader")
    st.markdown("---")
    
    # Check if the library is available
    if not LIBRARY_AVAILABLE:
        st.markdown("""
        <div class="error-box">
        <strong>⚠️ Image Uploader Unavailable</strong><br><br>
        The Image Uploader library could not be loaded. This may be due to missing dependencies or installation issues.
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
        # Show error message if browser automation is not available
        st.markdown("""
        <div class="error-box">
        <strong>⚠️ Browser Automation Unavailable</strong><br><br>
        The Image Uploader requires browser automation to upload images to Luminate Online.
        This feature is currently not available in this environment.
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### What does this mean?")
        st.info(playwright_error or "Browser automation is not available.")
        
        st.markdown("### What can you do?")
        st.markdown("""
        - **If you're using Streamlit Cloud**: This may be a temporary issue. Try refreshing the page or contact support.
        - **If you're running locally**: Make sure Playwright and its dependencies are installed.
        - **Alternative**: You can upload images directly through the Luminate Online web interface.
        """)
        
        # Don't show the upload form if Playwright is not available
        return
    
    st.markdown("""
    <div class="info-box">
    <strong>Welcome!</strong> Upload multiple images to your Luminate Online Image Library in just a few clicks.
    <br><br>
    <strong>🔑 Tip:</strong> Import your browser cookies to bypass 2FA! If cookies expire, 
    we'll fall back to username/password login.
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for cookies
    if 'imported_cookies' not in st.session_state:
        st.session_state.imported_cookies = None
    
    # Step 1: Credentials (always needed as fallback)
    st.subheader("Step 1: Enter Your Luminate Credentials")
    
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input(
            "Username",
            value=st.session_state.get('username', ''),
            help="Your Luminate Online username (email address)"
        )
    with col2:
        password = st.text_input(
            "Password",
            type="password",
            value="",
            help="Your Luminate Online password"
        )
    
    # Check for saved session
    has_saved_session = False
    if username and LIBRARY_AVAILABLE:
        try:
            saved_state = load_browser_state(username)
            has_saved_session = saved_state is not None
        except:
            has_saved_session = False
    
    # Show session status
    if username and has_saved_session:
        col_clear1, col_clear2 = st.columns([3, 1])
        with col_clear1:
            st.success("✅ Saved server session found for this account.")
        with col_clear2:
            if st.button("🗑️ Clear", key="clear_session", help="Clear saved session"):
                try:
                    if clear_browser_state(username):
                        st.success("Session cleared!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Step 2: Cookie Import (optional but recommended)
    st.markdown("---")
    st.subheader("Step 2: Import Browser Cookies (Recommended)")
    
    st.info("""
    🍪 **Bypass 2FA!** If you're already logged into Luminate in your browser, 
    import your session cookies to skip the login/2FA step entirely.
    """)
    
    with st.expander("📋 How to get your cookies", expanded=False):
        st.markdown("""
        **Chrome/Edge Users:**
        1. **Log into Luminate Online** in your browser (complete 2FA if prompted)
        2. Open the Luminate admin page (e.g., Image Library)
        3. Press **F12** to open Developer Tools
        4. Go to **Application** tab → **Cookies** → **secure2.convio.net**
        5. Find **JSESSIONID** and copy its value
        6. Paste below in format: `JSESSIONID=your_value`
        
        **Tip:** You can copy multiple cookies, one per line.
        """)
    
    # Cookie input
    cookie_input = st.text_area(
        "Paste your cookies here (optional)",
        height=80,
        placeholder="JSESSIONID=ABC123DEF456...",
        help="Paste cookies in name=value format, one per line. Leave empty to use username/password only."
    )
    
    # Parse cookies if provided
    cookies = None
    if cookie_input and cookie_input.strip():
        if COOKIE_HELPER_AVAILABLE:
            # Try base64 encoded format first (from bookmarklet)
            parsed = parse_cookie_export(cookie_input.strip())
            if parsed:
                cookies = cookies_to_playwright_state(parsed)
                st.success(f"✅ Imported {len(parsed.get('cookies', []))} cookies from bookmarklet export")
            else:
                # Try simple name=value format
                simple_cookies = parse_simple_cookie_paste(cookie_input)
                if simple_cookies:
                    cookies = {'cookies': simple_cookies, 'origins': []}
                    st.success(f"✅ Parsed {len(simple_cookies)} cookies - will try these first!")
                else:
                    st.error("❌ Could not parse cookies. Please check the format.")
        else:
            # Basic parsing without helper
            lines = cookie_input.strip().split('\n')
            simple_cookies = []
            for line in lines:
                if '=' in line:
                    parts = line.strip().split('=', 1)
                    simple_cookies.append({
                        'name': parts[0].strip(),
                        'value': parts[1].strip() if len(parts) > 1 else '',
                        'domain': 'secure2.convio.net',
                        'path': '/',
                        'secure': True,
                        'httpOnly': False,
                    })
            if simple_cookies:
                cookies = {'cookies': simple_cookies, 'origins': []}
                st.success(f"✅ Parsed {len(simple_cookies)} cookies - will try these first!")
            else:
                st.error("❌ Could not parse cookies. Use format: name=value")
    
    # Store cookies in session state
    st.session_state.imported_cookies = cookies
    
    # Show auth strategy
    if cookies:
        st.caption("🔄 **Auth strategy:** Try cookies first → Fall back to username/password if cookies fail")
    elif username and password:
        st.caption("🔄 **Auth strategy:** Username/password login (may trigger 2FA)")
    
    # Show advanced bookmarklet option
    if COOKIE_HELPER_AVAILABLE:
        with st.expander("🔧 Advanced: Use Bookmarklet for Complete Cookie Export"):
            st.markdown("""
            For a more complete cookie export, you can use our bookmarklet:
            
            1. Create a new bookmark in your browser
            2. Name it "Export Luminate Session"
            3. Paste this code as the URL:
            """)
            
            bookmarklet = get_cookie_extraction_bookmarklet()
            st.code(bookmarklet, language="javascript")
            
            st.markdown("""
            4. Go to any Luminate admin page while logged in
            5. Click the bookmarklet
            6. Copy the generated code and paste it above
            """)
    
    # Step 3: File Upload
    st.markdown("---")
    st.subheader("Step 3: Select Images to Upload")
    
    uploaded_files = st.file_uploader(
        "Choose image files",
        type=['jpg', 'jpeg', 'png', 'gif'],
        accept_multiple_files=True,
        help="You can select multiple images at once. Supported formats: JPG, PNG, GIF"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} image(s) selected")
        
        # Show file list
        with st.expander("View selected files"):
            for i, file in enumerate(uploaded_files, 1):
                st.text(f"{i}. {file.name} ({file.size / 1024:.1f} KB)")
    
    # Step 4: Upload Button
    st.markdown("---")
    
    # Validate inputs - need either cookies OR username/password
    has_cookies = st.session_state.imported_cookies is not None
    has_credentials = username and password
    has_valid_auth = has_cookies or has_credentials
    can_upload = playwright_available and has_valid_auth and uploaded_files and not st.session_state.uploading
    
    # Show auth status
    if not has_valid_auth:
        st.warning("⚠️ Please provide authentication: either import cookies (Step 2) or enter username/password (Step 1)")
    elif not uploaded_files:
        st.info("📁 Select images to upload (Step 3)")
    
    if st.button(
        "🚀 Upload All Images",
        type="primary",
        disabled=not can_upload,
        use_container_width=True
    ):
        if not has_valid_auth:
            st.error("Please provide authentication (cookies or username/password)")
            return
        
        if not uploaded_files:
            st.error("Please select at least one image to upload")
            return
        
        # Clear previous results to prevent caching
        st.session_state.upload_results = None
        
        # Store username in session state (if provided)
        if username:
            st.session_state.username = username
        
        # Start upload process
        st.session_state.uploading = True
        
        # Save uploaded files to temporary directory
        temp_dir = tempfile.mkdtemp()
        image_paths = []
        
        try:
            for uploaded_file in uploaded_files:
                # Save file to temp directory
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                image_paths.append(file_path)
            
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
            
            results = None
            
            # Try cookies first if available
            if has_cookies:
                status_text.info("🍪 Trying browser session cookies (no login needed)...")
                results = upload_images_with_cookies(
                    st.session_state.imported_cookies, 
                    image_paths, 
                    progress_callback
                )
                
                # Check if cookie auth failed (all uploads failed with session errors)
                cookie_failed = False
                if results['failed'] and not results['successful']:
                    # Check if failures are session-related
                    session_error_keywords = ['session', 'expired', 'invalid', 'login', 'cookie', 'authentication']
                    for _, error in results['failed']:
                        if any(keyword in error.lower() for keyword in session_error_keywords):
                            cookie_failed = True
                            break
                
                # Fall back to username/password if cookies failed and we have credentials
                if cookie_failed and has_credentials:
                    status_text.warning("🍪 Cookies expired or invalid. Falling back to username/password...")
                    results = upload_images_batch(username, password, image_paths, progress_callback)
            
            # Use username/password if no cookies provided
            elif has_credentials:
                status_text.info("🔄 Logging in to Luminate Online...")
                results = upload_images_batch(username, password, image_paths, progress_callback)
            
            # Store results
            st.session_state.upload_results = results
            st.session_state.uploading = False
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Show results
            if results:
                display_results(results)
            
        except Exception as e:
            st.session_state.uploading = False
            st.error(f"❌ An error occurred: {str(e)}")
            st.info("Please check your cookies/credentials and try again. If cookies aren't working, try refreshing them from your browser.")
        finally:
            # Clean up temporary files
            for file_path in image_paths:
                try:
                    os.remove(file_path)
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass
    
    # Display results only if we just completed an upload (not from cache)
    if st.session_state.upload_results and not st.session_state.uploading:
        st.markdown("---")
        st.subheader("📋 Upload Results")
        display_results(st.session_state.upload_results)
        
        # Add a button to clear results
        if st.button("🔄 Start New Upload", use_container_width=True):
            st.session_state.upload_results = None
            st.rerun()


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
                # Use text_input - users can select and copy manually, or use the button
                st.text_input(
                    f"URL {i}",
                    value=url,
                    key=f"url_input_{i}",
                    disabled=True,
                    label_visibility="collapsed"
                )
            with col2:
                # Create a copy button using Streamlit's button with JavaScript injection
                copy_key = f"copy_btn_{i}"
                if st.button("📋 Copy", key=copy_key, use_container_width=True):
                    # When button is clicked, inject JavaScript to copy to clipboard
                    # Escape single quotes for JavaScript
                    escaped_url = url.replace("'", "\\'")
                    st.markdown(f"""
                    <script>
                    navigator.clipboard.writeText('{escaped_url}').then(function() {{
                        // Show success message
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
            mime="text/plain"
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
