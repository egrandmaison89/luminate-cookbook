# Luminate Cookbook

A collection of tools to help you work with Luminate Online. All tools are accessible through a unified web interface.

## 🎯 Available Tools

### 🏃 Email Banner Processor
Transform photos into perfectly-sized email banners with intelligent face detection that avoids cropping heads.

### 📤 Image Uploader
Batch upload images directly to your Luminate Online Image Library with real-time progress tracking.

### 🔍 PageBuilder Decomposer
Extract all nested PageBuilders from a Luminate Online PageBuilder. Enter a URL or PageBuilder name and download all components as separate HTML files in a ZIP archive.

## 🚀 Quick Start

### Local development (no Docker)

Run the app on your machine without Docker or a dev container:

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: only needed for Image Uploader / Batch Uploader (Playwright)
python3 -m playwright install chromium

# Run the app
python3 -m streamlit run app.py
```

Open **http://localhost:8501** in your browser. Use the sidebar to navigate between tools.

### Deploy to Google Cloud Run

This app is deployed to **Google Cloud Run** (not Streamlit Cloud). No local Docker required—builds run in the cloud:

```bash
./deploy-cloud-run-no-docker.sh $(gcloud config get-value project) us-central1
```

See [docs/GOOGLE_CLOUD_RUN.md](docs/GOOGLE_CLOUD_RUN.md) for prerequisites and details.

### Command Line Scripts (For Power Users)

**Process banners:**
```bash
# Install dependencies
pip install -r requirements.txt

# Put your images in the 'originals/' folder
# Then run:
python scripts/process_banners.py
```

Output will be saved to the `resized/` folder.

**Upload to Luminate:**
```bash
# Set up credentials in .env file
# Then run:
python scripts/upload_to_luminate.py
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
luminate-cookbook/
├── app.py                    # Main entry point (Luminate Cookbook)
├── pages/                    # Multi-page app structure
│   ├── 1_Email_Banner_Processor.py  # Email banner tool
│   ├── 2_Image_Uploader.py          # Image uploader tool
│   └── 3_PageBuilder_Decomposer.py  # PageBuilder decomposer tool
├── lib/                      # Shared libraries
│   ├── luminate_uploader_lib.py      # Image upload library
│   └── pagebuilder_decomposer_lib.py # PageBuilder decomposer library
├── scripts/                  # CLI scripts
│   ├── process_banners.py    # CLI banner processing script
│   └── upload_to_luminate.py # CLI upload script
├── tests/                    # Test scripts
│   └── test_playwright.py   # Playwright test script
├── docs/                     # Documentation
│   ├── DEPLOYMENT.md        # Comprehensive deployment guide
│   ├── GOOGLE_CLOUD_RUN.md  # Google Cloud Run specific guide
│   └── TROUBLESHOOTING.md   # Troubleshooting guide
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker configuration (for deployments)
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

### CLI Script Settings (edit `scripts/process_banners.py`)
```python
TARGET_WIDTH = 600
TARGET_HEIGHT = 340
RETINA_WIDTH = 1200
RETINA_HEIGHT = 680
JPEG_QUALITY = 82
```

---

## 🚀 Deployment

Deployment is to **Google Cloud Run** only. Use the no-Docker script (builds in Google Cloud Build):

```bash
./deploy-cloud-run-no-docker.sh YOUR_PROJECT_ID us-central1
```

See [docs/GOOGLE_CLOUD_RUN.md](docs/GOOGLE_CLOUD_RUN.md) for setup and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for more detail.

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
- PageBuilder Decomposer - Extract nested PageBuilders as separate HTML files

**More tools coming soon!** 🎉

