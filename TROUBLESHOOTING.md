# Troubleshooting Guide

## ⚠️ Note: Application Migrated to FastAPI

This application has been migrated from Streamlit to FastAPI. Streamlit Cloud troubleshooting sections below are kept for historical reference only.

Current deployment platform: **Google Cloud Run**

---

## Current Issues (FastAPI on Cloud Run)

### Issue: 2FA Session Not Found

**Symptom**: After entering credentials, you get "Session not found or expired" when submitting 2FA code.

**Cause**: Session expired (10-minute timeout) or multiple Cloud Run instances causing session routing issues.

**Solution**:
1. Check if more than 10 minutes passed between login and 2FA submission
2. If using multiple tabs, ensure you're in the same tab that initiated the session
3. For Cloud Run multi-instance: Session IDs are instance-local. We need to add session persistence (Redis/Memorystore) for multi-instance deployments
4. Temporary workaround: Set `--max-instances 1` in Cloud Run to force single instance

```bash
gcloud run services update luminate-cookbook \
    --max-instances 1 \
    --region us-central1
```

### Issue: "Memory limit exceeded" in Cloud Run Logs

**Symptom**: Cloud Run kills the container during uploads.

**Cause**: Multiple concurrent browser sessions exceeding 2Gi memory allocation.

**Solution**:
1. Verify `MAX_CONCURRENT_SESSIONS=10` in configuration
2. Increase memory allocation if needed:
```bash
gcloud run services update luminate-cookbook \
    --memory 4Gi \
    --region us-central1
```
3. Check active sessions via `/health` endpoint

### Issue: Slow Cold Starts (30+ seconds)

**Symptom**: First request after idle period takes a long time.

**Cause**: Cloud Run starting container + Playwright initializing.

**Solution**:
1. This is expected for serverless - Playwright browser download is large
2. Keep instance warm with scheduled Cloud Scheduler ping:
```bash
# Create Cloud Scheduler job to ping every 5 minutes
gcloud scheduler jobs create http keep-warm \
    --schedule="*/5 * * * *" \
    --uri="https://your-app-url.run.app/health" \
    --http-method=GET
```
3. Or set `--min-instances 1` (costs ~$10/month but eliminates cold starts)

### Issue: Browser Automation Fails with "Target closed"

**Symptom**: Upload starts but fails with Playwright error about closed targets.

**Cause**: Page navigation or timeout issues with Luminate's admin interface.

**Solution**:
1. Check if Luminate Online UI has changed (inspect page in browser)
2. Review logs: `gcloud run services logs read luminate-cookbook --limit 100`
3. Increase timeouts in `browser_manager.py` if Luminate is slow
4. Test manually with `PLAYWRIGHT_HEADLESS=false` locally to see what's happening

---

## Deprecated Issues (Streamlit - Historical)

### ~~Error: "You do not have access to this app or it does not exist"~~ 

**Status**: No longer applicable - app no longer uses Streamlit Cloud

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
