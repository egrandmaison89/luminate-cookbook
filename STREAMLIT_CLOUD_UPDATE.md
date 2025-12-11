# Streamlit Cloud Update Instructions

## Quick Reference

**Current App URL:** https://emailbanners.streamlit.app/  
**Current Main File:** `streamlit_app.py`  
**New Main File:** `app.py`

## Action Required: Update Streamlit Cloud Dashboard

### Step-by-Step Instructions

1. **Go to Streamlit Cloud**
   - Visit: https://share.streamlit.io
   - Sign in with your GitHub account

2. **Find Your App**
   - Look for the app named **emailbanners**
   - Or navigate directly to: https://share.streamlit.io (then find your app)

3. **Delete the Existing App**
   - Click on the **emailbanners** app to open it
   - Look for **"Manage app"** button (usually in lower-right corner or ⋮ menu)
   - Click **"Manage app"** → **"Delete app"**
   - Confirm deletion (don't worry - your code is safe on GitHub!)

4. **Redeploy with New Main File**
   - Click **"New app"** button (top right or main dashboard)
   - Select your repository: `egrandmaison89/luminate-email-banners`
   - Select **Branch**: `main`
   - **Important:** In **"Main file path"** field, enter: `app.py`
   - Click **"Deploy"**
   - Streamlit Cloud will automatically:
     - Pull the latest code from GitHub
     - Install dependencies from requirements.txt
     - Install Playwright browsers (if needed)
     - Deploy the new unified app

6. **Monitor Deployment**
   - Watch the deployment logs
   - Wait for "Your app is live!" message
   - First deployment may take 2-5 minutes

7. **Test the App**
   - Visit: https://emailbanners.streamlit.app/
   - Verify:
     - Home page shows "Luminate Cookbook"
     - Navigation menu appears in sidebar
     - All three pages (Home, Email Banner Processor, Image Uploader) work

## What Changed

- **Before:** Single-page app (`streamlit_app.py`) - Email Banner Processor only
- **After:** Multi-page app (`app.py`) - Unified Cookbook with:
  - Home page with navigation
  - Email Banner Processor (same functionality)
  - Image Uploader (new tool)

## Rollback (If Needed)

If something goes wrong:
1. Delete the current app deployment
2. Create a new app and set **Main file path** to `streamlit_app.py`
3. Deploy - old app will be restored
4. Investigate issues and try again

## Files Ready for Deployment

All required files are staged and ready to commit:
- ✅ `app.py` (main entry point)
- ✅ `pages/1_Email_Banner_Processor.py`
- ✅ `pages/2_Image_Uploader.py`
- ✅ `luminate_uploader_lib.py`
- ✅ `requirements.txt` (updated)
- ✅ `README.md` (updated)

**Next Step:** Commit and push to GitHub, then update Streamlit Cloud dashboard.
