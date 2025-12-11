#!/usr/bin/env python3
"""
Image Uploader - Luminate Cookbook Tool

Batch upload images directly to your Luminate Online Image Library.
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
    <strong>Session Management:</strong> After your first login (including 2FA), your session will be saved automatically. 
    Future uploads will use the saved session, avoiding 2FA prompts. Your credentials are only used for authentication 
    and are never stored permanently.
    </div>
    """, unsafe_allow_html=True)
    
    # Step 1: Login Credentials
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
            help="Your Luminate Online password (only needed if no saved session exists)"
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
    if username:
        if has_saved_session:
            st.success("✅ Saved session found! You can upload without logging in again (no 2FA needed).")
            col_clear1, col_clear2 = st.columns([3, 1])
            with col_clear1:
                st.caption("If you want to use a different account or refresh your session, clear it below.")
            with col_clear2:
                if st.button("🗑️ Clear Session", key="clear_session", help="Clear saved session for this username"):
                    try:
                        if clear_browser_state(username):
                            st.success("Session cleared!")
                            st.rerun()
                        else:
                            st.warning("No session found to clear.")
                    except Exception as e:
                        st.error(f"Error clearing session: {str(e)}")
        else:
            st.info("ℹ️ No saved session found. You'll need to log in on first use (2FA may be required).")
            st.caption("After successful login, your session will be saved automatically for future uploads.")
    
    # Step 2: File Upload
    st.markdown("---")
    st.subheader("Step 2: Select Images to Upload")
    
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
    
    # Step 3: Upload Button
    st.markdown("---")
    
    # Validate inputs (only allow upload if Playwright is available)
    can_upload = playwright_available and username and password and uploaded_files and not st.session_state.uploading
    
    if st.button(
        "🚀 Upload All Images",
        type="primary",
        disabled=not can_upload,
        use_container_width=True
    ):
        if not username or not password:
            st.error("Please enter your username and password")
            return
        
        if not uploaded_files:
            st.error("Please select at least one image to upload")
            return
        
        # Clear previous results to prevent caching
        st.session_state.upload_results = None
        
        # Store username in session state (password is not stored)
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
            
            # Upload images
            status_text.info("🔄 Logging in to Luminate Online...")
            results = upload_images_batch(username, password, image_paths, progress_callback)
            
            # Store results
            st.session_state.upload_results = results
            st.session_state.uploading = False
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Show results
            display_results(results)
            
        except Exception as e:
            st.session_state.uploading = False
            st.error(f"❌ An error occurred: {str(e)}")
            st.info("Please check your credentials and try again.")
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
