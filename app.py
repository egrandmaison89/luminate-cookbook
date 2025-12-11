#!/usr/bin/env python3
"""
Luminate Cookbook - Main Entry Point

A collection of tools for working with Luminate Online.
Navigate to different tools using the sidebar.

Run locally: streamlit run app.py
Deploy: Push to GitHub and connect to Streamlit Cloud
"""

import streamlit as st
import importlib.util
import os

# Page configuration
st.set_page_config(
    page_title="Luminate Cookbook",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp {
        max-width: 1400px;
        margin: 0 auto;
    }
    .tool-card {
        padding: 2em;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        margin: 1em 0;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
    }
    .tool-card:hover {
        border-color: #1f77b4;
        box-shadow: 0 4px 12px rgba(31, 119, 180, 0.15);
    }
    .tool-title {
        font-size: 1.5em;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5em;
    }
    .tool-description {
        color: #666;
        line-height: 1.6;
    }
    .welcome-header {
        text-align: center;
        padding: 2em 0;
    }
</style>
""", unsafe_allow_html=True)


def home_page():
    """Home page content."""
    # Header
    st.markdown('<div class="welcome-header">', unsafe_allow_html=True)
    st.title("📚 Luminate Cookbook")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; color: #666; margin-bottom: 3em;">
        <p style="font-size: 1.2em;">A collection of tools to help you work with Luminate Online</p>
        <p>Navigate to different tools using the sidebar menu →</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tools showcase
    st.markdown("## 🛠️ Available Tools")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="tool-card">
            <div class="tool-title">🏃 Email Banner Processor</div>
            <div class="tool-description">
                Transform photos into perfectly-sized email banners with intelligent face detection. 
                Automatically crops images to avoid cutting off heads, supports custom dimensions, 
                and generates Retina-ready versions.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="tool-card">
            <div class="tool-title">📤 Image Uploader</div>
            <div class="tool-description">
                Batch upload images directly to your Luminate Online Image Library. 
                Upload multiple images at once with real-time progress tracking. 
                Get URLs for all uploaded images instantly.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("""
        <div class="tool-card">
            <div class="tool-title">🔍 PageBuilder Decomposer</div>
            <div class="tool-description">
                Extract all nested PageBuilders from a Luminate Online PageBuilder. 
                Enter a URL or PageBuilder name and download all components as separate 
                HTML files in a ZIP archive. No login required.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick start
    st.markdown("---")
    st.markdown("## 🚀 Quick Start")
    st.markdown("""
    1. **Use the sidebar** to navigate to any tool
    2. **Email Banner Processor**: Upload images, adjust settings, download optimized banners
    3. **Image Uploader**: Enter credentials, select images, upload to Luminate Online
    4. **PageBuilder Decomposer**: Extract nested PageBuilders as separate HTML files
    
    All tools are ready to use - no configuration needed!
    """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 0.9em; padding: 2em 0;">
        <p><strong>Luminate Cookbook</strong> • Built with Streamlit</p>
        <p>More tools coming soon! 🎉</p>
    </div>
    """, unsafe_allow_html=True)


def load_and_run_page(file_path):
    """Load and execute a page module, suppressing its page_config."""
    # Save original set_page_config before importing
    import streamlit as st_module
    original_set_page_config = st_module.set_page_config
    
    # Create a no-op function to suppress page_config calls
    def noop_page_config(*args, **kwargs):
        pass
    
    # Replace set_page_config in the streamlit module BEFORE importing
    st_module.set_page_config = noop_page_config
    st.set_page_config = noop_page_config
    
    try:
        # Load the module
        spec = importlib.util.spec_from_file_location("page_module", file_path)
        if spec is None or spec.loader is None:
            st.error(f"Could not load page from {file_path}")
            return
        
        module = importlib.util.module_from_spec(spec)
        # Execute the module (this is where set_page_config would be called)
        # This will catch import errors from the module itself
        spec.loader.exec_module(module)
        
        # Run the main function
        if hasattr(module, 'main'):
            module.main()
        else:
            st.error(f"Page module {file_path} does not have a main() function")
    except ImportError as e:
        # Handle import errors specifically
        st.error(f"⚠️ Import error loading page: {str(e)}")
        st.info("This may be due to missing dependencies. Check deployment logs for details.")
    except SyntaxError as e:
        # Handle syntax errors
        st.error(f"⚠️ Syntax error in page module: {str(e)}")
    except Exception as e:
        # Handle all other errors
        st.error(f"Error loading page: {str(e)}")
        import traceback
        with st.expander("Technical details"):
            st.code(traceback.format_exc())
    finally:
        # Restore original set_page_config
        st_module.set_page_config = original_set_page_config
        st.set_page_config = original_set_page_config


def email_banner_page():
    """Email Banner Processor page."""
    file_path = os.path.join(os.path.dirname(__file__), "pages", "1_Email_Banner_Processor.py")
    load_and_run_page(file_path)


def image_uploader_page():
    """Image Uploader page."""
    file_path = os.path.join(os.path.dirname(__file__), "pages", "2_Image_Uploader.py")
    try:
        load_and_run_page(file_path)
    except ImportError as e:
        # Handle import errors gracefully (e.g., if luminate_uploader_lib fails to import)
        st.error("⚠️ Image Uploader is currently unavailable")
        st.markdown("""
        <div style="padding: 1em; background-color: #fff3cd; border-radius: 5px; border: 1px solid #ffc107; margin: 1em 0;">
        <strong>Browser automation is not available.</strong><br><br>
        The Image Uploader requires browser automation to upload images to Luminate Online.
        This feature may not be available in all deployment environments.<br><br>
        <strong>Possible solutions:</strong><br>
        • If you're using Streamlit Cloud, check deployment logs for dependency issues<br>
        • Contact support if this is a persistent issue<br>
        • Try using the tool locally where dependencies can be installed
        </div>
        """, unsafe_allow_html=True)
        st.info(f"Technical details: {str(e)}")
    except Exception as e:
        # Handle any other errors gracefully
        st.error("⚠️ An error occurred loading the Image Uploader")
        st.exception(e)


def pagebuilder_decomposer_page():
    """PageBuilder Decomposer page."""
    file_path = os.path.join(os.path.dirname(__file__), "pages", "3_PageBuilder_Decomposer.py")
    load_and_run_page(file_path)


# Create page objects using st.Page
home = st.Page(
    home_page,
    title="Home",
    icon="📚",
    default=True
)

email_banner = st.Page(
    email_banner_page,
    title="Email Banner Processor",
    icon="🏃"
)

image_uploader = st.Page(
    image_uploader_page,
    title="Image Uploader",
    icon="📤"
)

pagebuilder_decomposer = st.Page(
    pagebuilder_decomposer_page,
    title="PageBuilder Decomposer",
    icon="🔍"
)

# Set up navigation
pages = {
    "Luminate Cookbook": [home, email_banner, image_uploader, pagebuilder_decomposer]
}

# Run the selected page
selected_page = st.navigation(pages)
selected_page.run()