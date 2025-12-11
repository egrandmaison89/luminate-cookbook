#!/usr/bin/env python3
"""
Luminate Online Image Uploader - Streamlit Web App

A user-friendly web interface for batch uploading images to Luminate Online Image Library.

Run locally: streamlit run luminate_uploader.py
Deploy: Push to GitHub and connect to Streamlit Cloud
"""

import streamlit as st
import streamlit.components.v1 as components
import tempfile
import os
import json
from luminate_uploader_lib import upload_images_batch

# Page configuration
st.set_page_config(
    page_title="Luminate Image Uploader",
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


def create_copy_component(url, component_id):
    """Create a custom HTML component for copying URLs to clipboard.
    
    Args:
        url: The URL to copy
        component_id: Unique ID for this component
        
    Returns:
        HTML component that handles clipboard copy
    """
    # Escape the URL for JavaScript
    escaped_url = url.replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')
    
    html = f"""
    <div id="copy-container-{component_id}" style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <input 
            type="text" 
            id="url-input-{component_id}" 
            value="{escaped_url}" 
            readonly 
            style="flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 14px; background-color: #f8f9fa;"
            onclick="this.select();"
        />
        <button 
            id="copy-btn-{component_id}"
            style="padding: 8px 16px; background-color: #0d6efd; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; white-space: nowrap;"
        >
            📋 Copy
        </button>
    </div>
    <div id="copy-feedback-{component_id}" style="display: none; color: #28a745; font-size: 12px; margin-top: -4px; margin-bottom: 8px;">
        ✓ Copied to clipboard!
    </div>
    <script>
        (function() {{
            const componentId = '{component_id}';
            const text = '{escaped_url}';
            const input = document.getElementById('url-input-' + componentId);
            const button = document.getElementById('copy-btn-' + componentId);
            const feedback = document.getElementById('copy-feedback-' + componentId);
            
            function showSuccess() {{
                feedback.style.display = 'block';
                setTimeout(function() {{
                    feedback.style.display = 'none';
                }}, 2000);
            }}
            
            function copyToClipboard() {{
                // Try modern clipboard API first
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(text).then(function() {{
                        showSuccess();
                    }}).catch(function(err) {{
                        // Fallback to execCommand
                        fallbackCopy();
                    }});
                }} else {{
                    // Fallback for older browsers
                    fallbackCopy();
                }}
            }}
            
            function fallbackCopy() {{
                input.select();
                input.setSelectionRange(0, 99999);
                try {{
                    document.execCommand('copy');
                    showSuccess();
                }} catch (err) {{
                    alert('Failed to copy. Please select the text and copy manually (Ctrl+C or Cmd+C).');
                }}
            }}
            
            // Attach event listener to button
            button.addEventListener('click', copyToClipboard);
            
            // Also allow clicking the input to select and copy
            input.addEventListener('click', function() {{
                this.select();
                fallbackCopy();
            }});
        }})();
    </script>
    """
    
    return components.html(html, height=70)


def main():
    st.title("📤 Luminate Image Uploader")
    st.markdown("---")
    
    st.markdown("""
    <div class="info-box">
    <strong>Welcome!</strong> Upload multiple images to your Luminate Online Image Library in just a few clicks.
    Your credentials are only used for this session and are never stored.
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
            help="Your Luminate Online password"
        )
    
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
    
    # Validate inputs
    can_upload = username and password and uploaded_files and not st.session_state.uploading
    
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
        st.markdown("Click the copy button or click the URL field to copy:")
        
        for i, url in enumerate(urls, 1):
            # Use the custom copy component
            create_copy_component(url, f"url_{i}")
        
        # Download URLs as text file
        urls_text = "\n".join(urls)
        st.download_button(
            label="💾 Download All URLs as Text File",
            data=urls_text,
            file_name="uploaded_urls.txt",
            mime="text/plain",
            key="download_urls_button"
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
