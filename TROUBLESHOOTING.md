# Troubleshooting: Streamlit Cloud Access Error

## Error: "You do not have access to this app or it does not exist"

This error typically means Streamlit Cloud can't access your GitHub repository. Here's how to fix it:

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
