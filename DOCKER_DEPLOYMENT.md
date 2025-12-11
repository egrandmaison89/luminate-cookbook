# Docker Deployment Guide

**⚠️ IMPORTANT: Streamlit Community Cloud does NOT support Dockerfiles.**

This Dockerfile is for deploying to alternative platforms that support Docker (Google Cloud Run, Railway, Fly.io, etc.).

For Streamlit Cloud, see [STREAMLIT_CLOUD_ALTERNATIVES.md](STREAMLIT_CLOUD_ALTERNATIVES.md) for options.

## Overview

The Dockerfile solves the Playwright system library issue by:
- Installing all required system libraries (libnspr4, libnss3, libatk-bridge2.0-0, etc.)
- Installing Playwright browsers (Chromium)
- Installing Playwright system dependencies
- Setting up the Streamlit app environment

## Files Created

- **Dockerfile**: Custom Docker image configuration
- **.dockerignore**: Excludes unnecessary files from Docker build
- **test_playwright.py**: Script to verify Playwright works in the container

## Local Testing (Optional)

Before deploying to Streamlit Cloud, you can test the Docker image locally:

### 1. Build the Docker Image

```bash
docker build -t luminate-cookbook:latest .
```

This will:
- Download the Python 3.11 slim base image
- Install all system dependencies (~5-10 minutes first time)
- Install Python packages from requirements.txt
- Install Playwright Chromium browser
- Copy your application files

### 2. Test Playwright in the Container

```bash
# Run the test script inside the container
docker run --rm luminate-cookbook:latest python test_playwright.py
```

Expected output:
```
Testing Playwright installation...
✅ Playwright imported successfully
Attempting to launch Chromium browser...
✅ Chromium browser launched successfully
✅ Browser closed successfully

✅ All Playwright tests passed!
```

### 3. Run the Streamlit App Locally

```bash
docker run -p 8501:8501 luminate-cookbook:latest
```

Then open http://localhost:8501 in your browser.

### 4. Test the Image Uploader

1. Navigate to the Image Uploader page
2. Enter your Luminate credentials
3. Upload a test image
4. Verify it works without the "Browser automation unavailable" error

## Deployment to Alternative Platforms

Since Streamlit Cloud doesn't support Dockerfiles, deploy to one of these platforms:

### Google Cloud Run (Recommended)

1. **Install Google Cloud SDK**
2. **Build and push image:**
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/luminate-cookbook
   ```
3. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy luminate-cookbook \
     --image gcr.io/YOUR_PROJECT_ID/luminate-cookbook \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### Railway.app

1. **Connect GitHub repository**
2. **Railway auto-detects Dockerfile**
3. **Deploy automatically**

### Fly.io

1. **Install flyctl**
2. **Initialize:**
   ```bash
   fly launch
   ```
3. **Deploy:**
   ```bash
   fly deploy
   ```

See [STREAMLIT_CLOUD_ALTERNATIVES.md](STREAMLIT_CLOUD_ALTERNATIVES.md) for detailed instructions.

## Troubleshooting

### Build Fails with "Package not found"

- Check that all package names in the Dockerfile are correct
- Some package names may differ between Debian versions
- The Dockerfile uses `python:3.11-slim` (Debian-based)

### Playwright Still Not Working

1. Check Streamlit Cloud build logs for errors
2. Verify the Dockerfile was used (check build logs)
3. Run the test script in the container:
   ```bash
   docker run --rm luminate-cookbook:latest python test_playwright.py
   ```

### Image Size Too Large

The Docker image will be larger (~1-2GB) due to:
- System libraries
- Playwright Chromium browser (~300MB)
- Python packages

This is expected and necessary for Playwright to work.

### Build Timeout

If the build times out:
- First build takes longer (downloading browsers)
- Streamlit Cloud has build time limits
- Consider using a pre-built image or caching

## What the Dockerfile Does

1. **Base Image**: Uses `python:3.11-slim` (Debian-based, smaller than full Python image)

2. **System Dependencies**: Installs all libraries Playwright needs:
   - Network/Security: libnspr4, libnss3
   - Accessibility: libatk-bridge2.0-0, libatk1.0-0, libatspi2.0-0
   - Graphics: libdrm2, libgbm1, libgtk-3-0
   - X11: libxcomposite1, libxdamage1, libxfixes3, etc.
   - Audio: libasound2
   - And many more...

3. **Python Dependencies**: Installs packages from `requirements.txt`

4. **Playwright Setup**:
   - `playwright install chromium` - Downloads Chromium browser
   - `playwright install-deps chromium` - Configures system dependencies

5. **Application**: Copies app files and runs Streamlit

## Environment Variables

The Dockerfile sets:
- `PYTHONUNBUFFERED=1` - Ensures Python output is not buffered
- `DEBIAN_FRONTEND=noninteractive` - Prevents interactive prompts during apt install
- `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` - Sets Playwright browser location

## Health Check

The Dockerfile includes a health check that verifies Streamlit is running:
- Checks every 30 seconds
- 10 second timeout
- 5 second start period (allows app to start)
- 3 retries before marking unhealthy

## Next Steps

After successful deployment:
1. ✅ Image Uploader should work
2. ✅ Email Banner Processor continues to work
3. ✅ PageBuilder Decomposer continues to work
4. ✅ All tools available to users

## Support

If you encounter issues:
1. Check Streamlit Cloud deployment logs
2. Review Docker build logs
3. Test locally with Docker first
4. Verify all files are committed to repository
