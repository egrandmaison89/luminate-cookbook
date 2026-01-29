# Deployment Guide: Luminate Cookbook

Complete guide for deploying the Luminate Cookbook application to various platforms.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Streamlit Cloud Deployment](#streamlit-cloud-deployment)
3. [Google Cloud Run Deployment](#google-cloud-run-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Python 3.8+
- Git repository with your code
- GitHub account (for Streamlit Cloud)
- See platform-specific sections for additional requirements

### Files Required for Deployment

**FastAPI Application** (current architecture):
- `app/main.py` - FastAPI application entry point
- `app/config.py` - Configuration with Pydantic Settings
- `app/services/` - Core business logic
  - `browser_manager.py` - Persistent browser sessions for 2FA
  - `banner_processor.py` - Image processing with face detection
  - `email_beautifier.py` - Plain text email beautification
  - `pagebuilder_service.py` - PageBuilder decomposition wrapper
- `app/models/schemas.py` - Pydantic request/response models
- `app/templates/` - Jinja2 HTML templates
- `app/static/` - CSS and JavaScript assets
- `lib/` - Reusable libraries
  - `luminate_uploader_lib.py` - Core Luminate interaction
  - `pagebuilder_decomposer_lib.py` - PageBuilder parsing engine
- `requirements.txt` - Python dependencies
- `Dockerfile` - **Required** for Cloud Run (Playwright dependencies)
- `cloudbuild.yaml` - Cloud Build configuration (optional)
- `deploy-cloud-run.sh` - Deployment automation script

---

## ⚠️ Deployment Update

**This application has been migrated from Streamlit to FastAPI.** The sections below referencing Streamlit Cloud are outdated and kept for historical reference only.

**Current Deployment Platform**: Google Cloud Run (see below for instructions)

---

## ~~Streamlit Cloud Deployment~~ (Deprecated)

### Overview

**Note**: This section is outdated. The application no longer uses Streamlit. All functionality has been migrated to FastAPI with improved architecture.

~~Streamlit Cloud is the easiest deployment option for the Email Banner Processor and PageBuilder Decomposer. **Note:** Streamlit Cloud does NOT support Dockerfiles, so the Image Uploader may have limited functionality.~~

### Step 1: Prepare Your Repository

1. Ensure all files are committed to GitHub
2. Verify `requirements.txt` includes all dependencies
3. Set main file to `app.py`

### Step 2: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Click **"New app"**
4. Configure:
   - **Repository:** Select your GitHub repository
   - **Branch:** `main` (or your default branch)
   - **Main file path:** `app.py`
   - **App URL:** Leave empty (auto-generated) or enter a custom URL
5. Click **"Deploy"**

### Step 3: Monitor Deployment

- Watch deployment logs in the dashboard
- First deployment takes 2-5 minutes
- Check for any import errors or missing dependencies

### Step 4: Verify Deployment

Test all pages:
- ✅ Home page shows "Luminate Cookbook"
- ✅ Email Banner Processor works
- ✅ PageBuilder Decomposer works
- ⚠️ Image Uploader may show "Browser automation unavailable" (see below)

### Image Uploader on Streamlit Cloud

**Limitation:** Streamlit Cloud doesn't support Dockerfiles, so Playwright system libraries may not be available.

**Option 1: Try packages.txt**
- Create a `packages.txt` file with required system packages
- Streamlit Cloud will automatically use it
- May or may not work depending on package availability

**Option 2: Use Alternative Platform**
- Deploy to Google Cloud Run, Railway, or Fly.io for full Image Uploader functionality
- See [Google Cloud Run Deployment](#google-cloud-run-deployment) section

**Option 3: Use Locally**
- Image Uploader works perfectly when running locally
- Deploy other tools to Streamlit Cloud
- Use Image Uploader on your local machine

### Updating Streamlit Cloud Deployment

If you need to change the main file:

1. Go to https://share.streamlit.io
2. Find your app
3. Click **"Manage app"** → **"Settings"**
4. Update **Main file path** if needed
5. Click **"Save"** (auto-redeploys)

Or delete and recreate:
1. Click **"Manage app"** → **"Delete app"**
2. Create new app with updated configuration

### Rollback

If deployment has issues:
1. In Streamlit Cloud dashboard, change **Main file** back to previous version
2. Save - Streamlit will auto-redeploy
3. Investigate issues and redeploy when fixed

---

## Google Cloud Run Deployment (Current)

### Overview

**Primary deployment platform for this application.** Google Cloud Run provides:

- ✅ Full Docker support (all Playwright dependencies)
- ✅ Auto-scaling from 0 to N instances
- ✅ Generous free tier: 2 million requests/month
- ✅ All four tools fully functional
- ✅ Built-in load balancing and HTTPS
- ✅ Excellent performance for browser automation

**Why Cloud Run?**
1. **Playwright Requirements**: Needs full system dependencies that only Docker can provide
2. **Resource Control**: Can allocate exactly 2Gi memory + 2 CPU cores for Chromium
3. **Cost Efficiency**: Pay only for actual usage, auto-scales to zero
4. **Production Ready**: Proper monitoring, logging, and health checks

### Prerequisites

1. **Google Cloud Account**
   - Sign up at https://cloud.google.com (free tier available)
   - $300 free credit for new accounts

2. **Google Cloud SDK (gcloud)**
   - Install from: https://cloud.google.com/sdk/docs/install
   - Or use: `brew install google-cloud-sdk` (macOS)

3. **Docker** (optional - can use Cloud Build instead)

### Quick Deployment (5 Minutes)

#### Step 1: Login and Setup

```bash
# Login to Google Cloud
gcloud auth login

# Create project (or use existing)
gcloud projects create luminate-cookbook --name="Luminate Cookbook"
gcloud config set project luminate-cookbook

# Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
```

#### Step 2: Deploy

**Option A: No Local Docker (Recommended)**

```bash
# Make script executable
chmod +x deploy-cloud-run-no-docker.sh

# Deploy (uses Google Cloud Build - builds in the cloud)
./deploy-cloud-run-no-docker.sh $(gcloud config get-value project) us-central1
```

**Option B: With Local Docker**

```bash
# Make script executable
chmod +x deploy-cloud-run.sh

# Deploy (builds locally, then pushes)
./deploy-cloud-run.sh $(gcloud config get-value project) us-central1
```

#### Step 3: Get Your URL

The script will output your app URL, or run:

```bash
gcloud run services describe luminate-cookbook \
    --platform managed \
    --region us-central1 \
    --format 'value(status.url)'
```

### Detailed Deployment Steps

See `docs/GOOGLE_CLOUD_RUN.md` for complete step-by-step instructions.

### Updating Deployment

```bash
# No Docker version (recommended)
./deploy-cloud-run-no-docker.sh $(gcloud config get-value project) us-central1

# Or with Docker
./deploy-cloud-run.sh $(gcloud config get-value project) us-central1
```

---

## Docker Deployment

### Overview

The Dockerfile enables deployment to any Docker-supporting platform (Google Cloud Run, Railway, Fly.io, AWS, etc.).

### Important Note

**Streamlit Cloud does NOT support Dockerfiles.** Use Docker for:
- Google Cloud Run
- Railway.app
- Fly.io
- AWS Elastic Beanstalk
- Other Docker-supporting platforms

### Local Testing

#### Build the Docker Image

```bash
docker build -t luminate-cookbook:latest .
```

This will:
- Download Python 3.11 slim base image
- Install all system dependencies (~5-10 minutes first time)
- Install Python packages from requirements.txt
- Install Playwright Chromium browser
- Copy application files

#### Test Playwright

```bash
# Run the test script inside the container
docker run --rm luminate-cookbook:latest python tests/test_playwright.py
```

Expected output:
```
Testing Playwright installation...
✅ Playwright imported successfully
✅ Chromium browser launched successfully
✅ All Playwright tests passed!
```

#### Run Locally

```bash
docker run -p 8501:8501 luminate-cookbook:latest
```

Then open http://localhost:8501 in your browser.

### What the Dockerfile Does

1. **Base Image**: Uses `python:3.11-slim` (Debian-based)

2. **System Dependencies**: Installs all libraries Playwright needs:
   - Network/Security: libnspr4, libnss3
   - Accessibility: libatk-bridge2.0-0, libatk1.0-0
   - Graphics: libdrm2, libgbm1, libgtk-3-0
   - X11: libxcomposite1, libxdamage1, libxfixes3
   - Audio: libasound2
   - And many more...

3. **Python Dependencies**: Installs packages from `requirements.txt`

4. **Playwright Setup**:
   - `playwright install chromium` - Downloads Chromium browser
   - `playwright install-deps chromium` - Configures system dependencies

5. **Application**: Copies app files and runs Streamlit

### Deployment to Alternative Platforms

#### Railway.app

1. Connect GitHub repository
2. Railway auto-detects Dockerfile
3. Deploy automatically

#### Fly.io

1. Install flyctl
2. Initialize: `fly launch`
3. Deploy: `fly deploy`

#### AWS Elastic Beanstalk

1. Build and push Docker image
2. Configure Elastic Beanstalk for Docker
3. Deploy

---

## Troubleshooting

### Common Issues

#### Streamlit Cloud: "Unexpected error" on App URL

**Problem:** Custom URL field shows error, Deploy button grayed out.

**Solution:**
1. Clear the "App URL (optional)" field completely
2. Leave it empty - Streamlit will auto-generate a URL
3. Verify other fields are correct
4. Click "Deploy"

**Why:** Custom URLs must be unique and may have naming restrictions.

#### Streamlit Cloud: Import Errors

**Problem:** Pages fail to load with import errors.

**Solution:**
1. Check deployment logs for specific import errors
2. Verify `requirements.txt` includes all dependencies
3. Ensure file paths are correct (e.g., `lib/luminate_uploader_lib.py`)
4. Check that all files are committed to GitHub

#### Image Uploader: "Browser automation unavailable"

**Problem:** Image Uploader shows error message on Streamlit Cloud.

**Solution:**
- This is expected on Streamlit Cloud (no Dockerfile support)
- Options:
  1. Deploy to Google Cloud Run or another Docker-supporting platform
  2. Use Image Uploader locally
  3. Try `packages.txt` (may or may not work)

#### Google Cloud Run: Build Fails

**Problem:** Docker build fails during deployment.

**Solution:**
```bash
# Check build logs
gcloud builds list
gcloud builds log BUILD_ID

# Common issues:
# - Package names incorrect
# - Network timeout (retry)
# - Insufficient permissions (check IAM)
```

#### Google Cloud Run: Deployment Fails

**Problem:** Service fails to start.

**Solution:**
```bash
# Check service logs
gcloud run services logs read luminate-cookbook --region us-central1

# Common issues:
# - Missing environment variables
# - Port configuration (should be 8501)
# - Memory limits too low
```

#### Playwright: Browser Launch Fails

**Problem:** Playwright can't launch browser in container.

**Solution:**
1. Verify Dockerfile installed all system dependencies
2. Test locally: `docker run --rm luminate-cookbook:latest python tests/test_playwright.py`
3. Check build logs for missing packages
4. Ensure `playwright install chromium` ran successfully

### Build Timeout

**Problem:** Build times out during deployment.

**Solution:**
- First build takes longer (downloading browsers)
- Some platforms have build time limits
- Consider:
  - Using pre-built base images
  - Caching Docker layers
  - Splitting build into multiple steps

### Image Size Too Large

**Problem:** Docker image is very large.

**Solution:**
- Expected: ~1-2GB due to:
  - System libraries
  - Playwright Chromium browser (~300MB)
  - Python packages
- This is necessary for Playwright to work
- Consider multi-stage builds for optimization (advanced)

---

## Pre-Deployment Checklist

### ✅ Application Ready

All files are production-ready and tested:

**Core Application**:
- [x] `app/main.py` - FastAPI application with all routes
- [x] `app/config.py` - Environment-based configuration
- [x] `app/services/` - All four service modules
- [x] `app/models/schemas.py` - Pydantic models
- [x] `app/templates/` - All HTML templates
- [x] `lib/` - Reusable business logic libraries

**Deployment Files**:
- [x] `Dockerfile` - Multi-stage build with Playwright dependencies
- [x] `requirements.txt` - All Python dependencies pinned
- [x] `cloudbuild.yaml` - Cloud Build configuration
- [x] `deploy-cloud-run.sh` - Automated deployment script
- [x] `.dockerignore` - Optimized for faster builds

**Documentation**:
- [x] `README.md` - Complete architecture documentation
- [x] `docs/DEPLOYMENT.md` - This file
- [x] `docs/GOOGLE_CLOUD_RUN.md` - Detailed Cloud Run guide
- [x] `DEPLOY_NOW.md` - Quick start guide

### Dependencies (Production)

```txt
# Web Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
jinja2>=3.1.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Image Processing
Pillow>=10.0.0
opencv-python-headless>=4.8.0
numpy>=1.24.0

# Browser Automation
playwright>=1.40.0

# HTTP Client
requests>=2.28.0
httpx>=0.26.0

# Utilities
python-dotenv>=1.0.0
```

**Note**: Streamlit has been **removed** from dependencies.

### Post-Deployment Verification

After deployment, test all four tools systematically:

#### 1. Home Page
- ✅ Navigate to `https://your-app-url.run.app/`
- ✅ "Luminate Cookbook" title visible
- ✅ Four tool cards displayed with descriptions
- ✅ Navigation links functional
- ✅ Check `/docs` for interactive API documentation

#### 2. Image Uploader (Critical - Tests 2FA)
- ✅ Navigate to `/upload`
- ✅ Enter Luminate credentials
- ✅ Select 1-2 test images
- ✅ Click "Upload All Images"
- ✅ **If 2FA required**: 
  - Verify "Two-factor authentication required" message appears
  - Enter 6-digit code from authenticator app
  - Verify upload continues without session loss
- ✅ Check Luminate Image Library for uploaded files
- ✅ Verify image URLs are accessible

#### 3. Email Banner Processor
- ✅ Navigate to `/banner`
- ✅ Upload test photo with visible face(s)
- ✅ Verify face detection count displayed
- ✅ Adjust dimensions (e.g., 600x340)
- ✅ Enable retina version
- ✅ Click "Process Images"
- ✅ Download ZIP file
- ✅ Verify ZIP contains both standard and @2x versions
- ✅ Verify images are properly cropped with faces visible

#### 4. PageBuilder Decomposer
- ✅ Navigate to `/pagebuilder`
- ✅ Enter test PageBuilder URL or name
- ✅ Click "Analyze Structure" to preview hierarchy
- ✅ Verify component tree displays
- ✅ Click "Decompose & Download"
- ✅ Download ZIP file
- ✅ Verify ZIP contains HTML files with proper folder structure
- ✅ Verify nested PageBuilders are extracted

#### 5. Plain Text Email Beautifier
- ✅ Navigate to `/email-beautifier`
- ✅ Paste sample plain text email
- ✅ Enable all options (strip tracking, format CTAs, markdown links)
- ✅ Click "Beautify"
- ✅ Verify tracking parameters removed from URLs
- ✅ Verify CTAs formatted with >>> arrows <<<
- ✅ Verify footer cleaned and simplified
- ✅ Check stats display (URLs cleaned, CTAs formatted, etc.)

#### Health Check
- ✅ Navigate to `/health`
- ✅ Verify returns: `{"status": "healthy", "app": "Luminate Cookbook", "active_sessions": 0}`

#### Performance Verification
- ✅ Check Cloud Run metrics for cold start time (<30s)
- ✅ Verify memory usage stays under 2Gi
- ✅ Check logs for any errors or warnings
- ✅ Test concurrent access (multiple tabs/users)

---

## Next Steps After Deployment

1. Test all three tools thoroughly
2. Share the URL with your team
3. Monitor for any user-reported issues
4. Set up monitoring/alerting (optional)
5. Configure custom domain (optional)

---

## Support

If you encounter issues:

1. Check deployment logs
2. Review troubleshooting section above
3. Verify all files are committed to repository
4. Test locally first before deploying
5. Check platform-specific documentation

For detailed platform-specific guides:
- Google Cloud Run: See `docs/GOOGLE_CLOUD_RUN.md`
- Troubleshooting: See `docs/TROUBLESHOOTING.md`
