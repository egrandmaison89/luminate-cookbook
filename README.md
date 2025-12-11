# Luminate Cookbook

A collection of tools to help you work with Luminate Online. All tools are accessible through a unified web interface.

## 🎯 Available Tools

### 🏃 Email Banner Processor
Transform photos into perfectly-sized email banners with intelligent face detection that avoids cropping heads.

### 📤 Image Uploader
Batch upload images directly to your Luminate Online Image Library with real-time progress tracking.

## 🚀 Quick Start

### Web App (Recommended for Teams)
A user-friendly web interface - no coding required!

**Try it locally:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open in your browser. Use the sidebar to navigate between tools.

**Deploy to share with your team:**
1. Push this folder to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set the main file to `app.py`
5. Share the URL with your team!

### Command Line Scripts (For Power Users)

**Process banners:**
```bash
# Install dependencies
pip install -r requirements.txt

# Put your images in the 'originals/' folder
# Then run:
python process_banners.py
```

Output will be saved to the `resized/` folder.

**Upload to Luminate:**
```bash
# Set up credentials in .env file
# Then run:
python upload_to_luminate.py
```

---

## 📐 Features

- **Smart Face Detection** - Automatically detects faces and crops intelligently to avoid cutting off heads
- **Customizable Dimensions** - Set your own width and height (default: 600×340px)
- **Filename Prefix** - Add a custom prefix to organize banners by program (e.g., "AGEM123_email_banner_600.jpg")
- **Retina Support** - Optionally generate 2x resolution images for high-DPI displays
- **Optimized File Sizes** - JPEG compression tuned for fast email loading
- **Batch Processing** - Process multiple images at once

---

## 📁 Project Structure

```
email_banners/
├── app.py                    # Main entry point (Luminate Cookbook)
├── pages/                    # Multi-page app structure
│   ├── 1_Email_Banner_Processor.py  # Email banner tool
│   └── 2_Image_Uploader.py           # Image uploader tool
├── luminate_uploader_lib.py  # Shared upload library
├── process_banners.py        # CLI banner processing script
├── upload_to_luminate.py     # CLI upload script
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── originals/                # Source images (for CLI)
└── resized/                  # Output images (from CLI)
```

## 🛠️ Adding New Tools

To add a new tool to the Luminate Cookbook:

1. Create a new file in the `pages/` directory
2. Name it with a number prefix (e.g., `3_Your_Tool.py`)
3. Add page configuration:
   ```python
   st.set_page_config(
       page_title="Your Tool",
       page_icon="🔧",
       layout="wide"
   )
   ```
4. Streamlit will automatically add it to the navigation!

---

## ⚙️ Configuration

### Web App Settings (sidebar)
- **Width**: 400-1000px (default: 600px)
- **Height**: 150-600px (default: 340px)
- **JPEG Quality**: 60-95 (default: 82)
- **Filename Prefix**: Optional prefix for output files
- **Retina versions**: On/Off

### CLI Script Settings (edit `process_banners.py`)
```python
TARGET_WIDTH = 600
TARGET_HEIGHT = 340
RETINA_WIDTH = 1200
RETINA_HEIGHT = 680
JPEG_QUALITY = 82
```

---

## 🚀 Deploying to Streamlit Cloud (Free)

### Standard Deployment (Email Banner Processor & PageBuilder Decomposer)

1. **Create a GitHub repository** and push this folder

2. **Go to** [share.streamlit.io](https://share.streamlit.io)

3. **Click "New app"** and select:
   - Your GitHub repo
   - Branch: `main`
   - Main file: `app.py`

4. **Click Deploy!**

5. **Share the URL** with your team (e.g., `https://your-app.streamlit.app`)

### Image Uploader on Streamlit Cloud

**⚠️ Important:** Streamlit Cloud doesn't support Dockerfiles. The Image Uploader requires Playwright system libraries.

**Option 1: Try packages.txt**
- A `packages.txt` file is included with required system packages
- Streamlit Cloud will automatically use it during deployment
- May work, but some packages might not be available

**Option 2: Deploy to Google Cloud Run** ⭐ (Recommended)
- Full Image Uploader functionality available
- Free tier: 2 million requests/month
- Easy deployment with included scripts
- See [GOOGLE_CLOUD_RUN_DEPLOYMENT.md](GOOGLE_CLOUD_RUN_DEPLOYMENT.md) for complete guide

**Option 3: Deploy to Other Platforms**
- Railway, Fly.io, or other Docker-supporting platforms
- See [STREAMLIT_CLOUD_ALTERNATIVES.md](STREAMLIT_CLOUD_ALTERNATIVES.md) for details

**Option 3: Use Locally**
- Image Uploader works perfectly when running locally
- Deploy other tools to Streamlit Cloud
- Use Image Uploader on your local machine

See [STREAMLIT_CLOUD_ALTERNATIVES.md](STREAMLIT_CLOUD_ALTERNATIVES.md) for all options.

Your teammates can now:
- Visit the URL from any device
- Navigate between tools using the sidebar
- Use the Email Banner Processor to create optimized banners
- Use the Image Uploader to batch upload to Luminate Online (requires Docker deployment)
- Use the PageBuilder Decomposer to extract nested PageBuilders
- Access all tools from a single unified interface

---

## 📋 Requirements

- Python 3.8+
- See `requirements.txt` for packages

---

## 🏃 About

Built by the Luminate team. The Luminate Cookbook provides a collection of tools to streamline your workflow with Luminate Online.

**Current Tools:**
- Email Banner Processor - Create optimized email banners with smart face detection
- Image Uploader - Batch upload images to Luminate Online Image Library

**More tools coming soon!** 🎉

