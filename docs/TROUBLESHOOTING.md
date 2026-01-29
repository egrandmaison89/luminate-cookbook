# Troubleshooting Guide - Luminate Cookbook

## ⚠️ Application Architecture Update

**Current Platform**: Google Cloud Run with FastAPI  
**Previous Platform**: Streamlit Cloud (deprecated)

This document covers troubleshooting for the current FastAPI implementation deployed on Google Cloud Run. Historical Streamlit issues are preserved at the bottom for reference.

---

## Common Issues (FastAPI on Cloud Run)

### 1. Browser Session Issues

#### Issue: "Session not found or expired"

**When it happens**: After entering credentials and trying to submit 2FA code.

**Root Causes**:
1. **Session timeout**: Default 10-minute expiration
2. **Cloud Run multi-instance routing**: Sessions are stored in memory, not shared across instances
3. **Manual cancellation**: User or another tab cancelled the session

**Solutions**:

**Short-term** (Single-instance mode):
```bash
# Force single instance to avoid routing issues
gcloud run services update luminate-cookbook \
    --max-instances 1 \
    --min-instances 1 \
    --region us-central1
```

**Long-term** (Multi-instance with session persistence):
1. Add Redis/Memorystore for session storage
2. Update `browser_manager.py` to serialize session state
3. Store browser session IDs with instance affinity headers

**Workaround**:
- Complete 2FA within 10 minutes
- Use same browser tab throughout the flow
- Don't refresh the page after starting upload

---

### 2. Playwright Browser Issues

#### Issue: "Browser launch failed" or "Chromium could not be found"

**Symptoms**:
- Image Uploader fails to initialize
- Logs show Playwright installation errors
- Container crashes during browser launch

**Root Causes**:
1. Docker build didn't complete system dependencies install
2. `PLAYWRIGHT_BROWSERS_PATH` incorrect
3. Insufficient memory (Chromium needs 200MB+)

**Solutions**:

**Verify Docker build**:
```bash
# Rebuild with verbose logging
docker build -t luminate-cookbook:test . --progress=plain

# Check Playwright installation
docker run --rm luminate-cookbook:test python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

**Check environment variables**:
```bash
gcloud run services describe luminate-cookbook \
    --region us-central1 \
    --format='value(spec.template.spec.containers[0].env)'
```

Should include: `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`

**Memory allocation**:
```bash
# Ensure at least 2Gi memory
gcloud run services update luminate-cookbook \
    --memory 2Gi \
    --region us-central1
```

---

### 3. Upload Verification Failures

#### Issue: "Upload completed but verification failed"

**Symptoms**:
- Files appear uploaded in Playwright
- But verification GET request returns 404
- Image not accessible at expected URL

**Root Causes**:
1. **Timing issue**: File not yet propagated to CDN (Luminate's infrastructure)
2. **Filename mismatch**: Luminate may rename files with special characters
3. **Permission issue**: File uploaded to wrong folder or not public

**Solutions**:

**Increase retry attempts** in `browser_manager.py`:
```python
# Current: 2 retries with 2s delay
# Change to: 5 retries with 3s delay
for _ in range(5):
    page.wait_for_timeout(3000)
    # ... verification logic
```

**Manual verification**:
1. Log into Luminate admin
2. Navigate to Image Library
3. Check if file exists but with different name
4. Try direct URL: `https://danafarber.jimmyfund.org/images/content/pagebuilder/FILENAME.jpg`

---

### 4. Face Detection Not Working

#### Issue: Banner processor crops off faces

**Symptoms**:
- Face count shows 0 when faces are clearly visible
- Crop region doesn't preserve faces
- Output images have heads cut off

**Root Causes**:
1. **Poor photo quality**: Low resolution or blurry faces
2. **Lighting issues**: Overexposed or underexposed faces
3. **Angle issues**: Profile shots or tilted heads
4. **OpenCV cascade limitations**: Haar Cascade only detects frontal faces

**Solutions**:

**Check input image**:
- Minimum recommended resolution: 1200px width
- Frontal face angles work best
- Good lighting and contrast

**Adjust detection parameters** in `banner_processor.py`:
```python
# More sensitive detection (more false positives)
faces = face_cascade.detectMultiScale(
    gray,
    scaleFactor=1.05,  # Lower = more sensitive (default 1.1)
    minNeighbors=3,    # Lower = more detections (default 5)
    minSize=(20, 20),  # Smaller minimum (default 30, 30)
)
```

**Fallback**: If face detection fails, manual crop is better than center crop
- Consider adding manual crop region selection in UI
- Or use center-weighted crop as fallback

---

### 5. Cloud Run Cold Start Delays

#### Issue: First request takes 30+ seconds

**Symptoms**:
- Initial page load very slow
- Subsequent requests fast
- Happens after 15 minutes of inactivity

**Root Causes**:
1. **Serverless architecture**: Container starts from scratch
2. **Playwright browser size**: 300MB Chromium download
3. **Python imports**: NumPy, OpenCV, etc. take time to load

**Solutions**:

**Keep instances warm** with Cloud Scheduler:
```bash
# Ping /health every 5 minutes
gcloud scheduler jobs create http keep-luminate-warm \
    --schedule="*/5 * * * *" \
    --uri="https://your-app-url.run.app/health" \
    --http-method=GET \
    --location=us-central1
```

**Set minimum instances** (costs ~$10/month):
```bash
gcloud run services update luminate-cookbook \
    --min-instances 1 \
    --region us-central1
```

**Optimize Docker image**:
- Use multi-stage builds (already done)
- Remove unused system packages
- Consider using distroless base images (advanced)

---

### 6. Memory Limit Exceeded

#### Issue: Container killed with "Memory limit exceeded"

**Symptoms**:
- Upload fails midway
- Logs show OOM (out of memory)
- Cloud Run metrics show memory spike

**Root Causes**:
1. **Too many concurrent sessions**: More than 10 browser instances
2. **Memory leak**: Browser not cleaned up properly
3. **Large images**: Processing many high-res images simultaneously

**Solutions**:

**Verify session limits**:
```bash
# Check active sessions
curl https://your-app-url.run.app/health
# Should show: "active_sessions": <10
```

**Increase memory**:
```bash
gcloud run services update luminate-cookbook \
    --memory 4Gi \
    --region us-central1
```

**Monitor cleanup**:
- Check logs for cleanup task running every 30 seconds
- Verify sessions expire after 10 minutes
- Ensure browser objects are being closed

---

## Deprecated Issues (Historical - Streamlit)

### ~~Error: "You do not have access to this app or it does not exist"~~

**Status**: Application no longer uses Streamlit Cloud

**Historical context**: This error occurred when Streamlit Cloud couldn't access GitHub repositories. The migration to FastAPI eliminated this entire class of deployment issues.

## Solution Steps

### Step 1: Verify Repository is Public
1. Go to https://github.com/egrandmaison89/luminate-cookbook
2. Check that the repository shows "Public" (not "Private")
3. If it's private, either:
   - Make it public: Settings → Scroll down → Change visibility → Make public
   - OR upgrade to Streamlit Cloud for Teams (paid) to use private repos

### Step 2: Reauthorize Streamlit's GitHub Access
1. Go to GitHub: https://github.com/settings/applications
2. Click "Authorized OAuth Apps" (left sidebar)
3. Find "Streamlit" in the list
4. Click on it
5. Click "Revoke" to remove old permissions
6. Go back to Streamlit Cloud: https://share.streamlit.io
7. Try to create/edit your app - it will prompt you to reauthorize GitHub
8. Grant Streamlit access to your repositories

### Step 3: Verify App Configuration
In Streamlit Cloud dashboard:
1. Make sure the repository is: `egrandmaison89/luminate-cookbook`
2. Branch: `main`
3. Main file: `app.py`

### Step 4: Delete and Recreate App (If Needed)
If the above doesn't work:
1. Delete the app in Streamlit Cloud
2. Create a new app
3. Select repository: `egrandmaison89/luminate-cookbook`
4. Branch: `main`
5. Main file path: `app.py`
6. Deploy

## Common Issues

**Repository name mismatch:**
- Your local repo might be `luminate-email-banners`
- But Streamlit is looking for `luminate-cookbook`
- Make sure Streamlit Cloud is pointing to the correct repository name

**GitHub account mismatch:**
- Ensure you're signed into Streamlit Cloud with the same GitHub account (`egrandmaison89`)
- Check that the repository owner matches your GitHub username

**OAuth permissions:**
- Streamlit needs permission to read your repositories
- Revoking and reauthorizing usually fixes this

## Still Not Working?

1. Check Streamlit Cloud status: https://status.streamlit.io/
2. Check GitHub repository settings for any restrictions
3. Try accessing the repository directly: https://github.com/egrandmaison89/luminate-cookbook
4. Verify `app.py` exists in the root of the `main` branch

---

# Troubleshooting: Playwright Browser Launch Error

## Error: "libnspr4.so: cannot open shared object file" or "Browser launch error"

This error occurs when Playwright's Chromium browser is missing required system libraries. This is common in containerized environments like Streamlit Cloud.

### Symptoms
- Error message: `error while loading shared libraries: libnspr4.so: cannot open shared object file`
- Browser fails to launch when using the Image Uploader tool
- Error appears in Streamlit Cloud logs

### Solutions

#### For Streamlit Cloud Deployment

Streamlit Cloud should have system dependencies available, but if you encounter this error:

1. **Check Deployment Logs**
   - Go to Streamlit Cloud dashboard
   - Check the deployment logs for any system library errors
   - Look for messages about missing dependencies

2. **Contact Streamlit Cloud Support**
   - This may indicate that the base image is missing required libraries
   - Streamlit Cloud support can help ensure system dependencies are available
   - Note: The app handles missing Playwright gracefully - it will show an error message instead of crashing

3. **Verify Playwright Installation**
   - The app automatically installs Playwright browsers on first use
   - Check logs to ensure `playwright install chromium` completed successfully
   - If installation failed, you'll see a different error message

#### For Local/Docker Deployment

If running locally or in Docker:

1. **Install System Dependencies**
   ```bash
   # On Debian/Ubuntu, install required packages:
   sudo apt update
   sudo apt install -y \
     libnspr4 \
     libnss3 \
     libatk-bridge2.0-0 \
     libatk1.0-0 \
     libatspi2.0-0 \
     libcups2 \
     libdbus-1-3 \
     libdrm2 \
     libgbm1 \
     libgtk-3-0 \
     libxkbcommon0 \
     libxcomposite1 \
     libxdamage1 \
     libxfixes3 \
     libxrandr2 \
     libxss1 \
     libasound2
   
   # Or install Playwright's system dependencies (recommended):
   python -m playwright install-deps chromium
   ```

2. **Verify Installation**
   ```bash
   python -m playwright install chromium
   python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(); print('OK')"
   ```

3. **Dockerfile Example**
   If using a custom Dockerfile, add:
   ```dockerfile
   RUN apt-get update && apt-get install -y \
       libnspr4 libnss3 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
       libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libxkbcommon0 \
       libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libxss1 libasound2 \
       && rm -rf /var/lib/apt/lists/*
   RUN pip install -r requirements.txt
   RUN python -m playwright install chromium
   RUN python -m playwright install-deps chromium
   ```

### What the App Does Automatically

The app tries to:
1. Detect if browsers are installed
2. Install Playwright browsers if missing
3. Install system dependencies (may fail in restricted environments like Streamlit Cloud)
4. Provide helpful error messages with next steps

### Required System Libraries

The following libraries are needed for Playwright Chromium to work locally or in Docker:
- `libnspr4` - Netscape Portable Runtime
- `libnss3` - Network Security Services
- `libatk-bridge2.0-0`, `libatk1.0-0`, `libatspi2.0-0` - Accessibility toolkit
- `libcups2` - Printing support
- `libdbus-1-3` - Inter-process communication
- `libdrm2`, `libgbm1` - Graphics drivers
- `libgtk-3-0` - GTK+ library
- `libxkbcommon0` - Keyboard handling
- `libxcomposite1`, `libxdamage1`, `libxfixes3`, `libxrandr2`, `libxss1` - X11 extensions
- `libasound2` - Audio support

**Note for Streamlit Cloud**: These packages are not needed. The app handles missing Playwright gracefully and will show a helpful error message if browser automation is unavailable.

### Still Having Issues?

1. Check the full error message in Streamlit Cloud logs
2. Verify `playwright>=1.40.0` is in `requirements.txt`
3. Try redeploying the app (sometimes fixes dependency issues)
4. For Streamlit Cloud: The app will show a clear error message if Playwright isn't available - this is expected and the app will still work for other tools
5. For local deployments: Install the system packages listed above or use `python -m playwright install-deps chromium`
