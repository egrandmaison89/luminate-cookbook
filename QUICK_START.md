# Quick Start: Deploy Luminate Cookbook

## 🚀 Two Steps to Deploy

### Step 1: Commit and Push (Do this now)

```bash
git commit -m "Deploy unified Luminate Cookbook with multi-page navigation"
git push origin main
```

### Step 2: Redeploy on Streamlit Cloud (Then do this)

**Note:** Streamlit Cloud doesn't allow changing the main file directly. You need to delete and redeploy.

1. Go to https://share.streamlit.io
2. Click on your **emailbanners** app
3. Click **"Manage app"** → **"Delete app"** (your code is safe on GitHub!)
4. Click **"New app"**
5. Select repo: `egrandmaison89/luminate-email-banners`, branch: `main`
6. **Main file path:** Enter `app.py`
7. Click **"Deploy"**
8. Wait 2-5 minutes for deployment
9. Visit https://emailbanners.streamlit.app/ to verify

## ✅ What's Ready

All files are staged and ready:
- ✅ New unified app (`app.py`)
- ✅ Email Banner Processor page
- ✅ Image Uploader page
- ✅ All dependencies verified
- ✅ Documentation updated

## 📋 After Deployment

Test these pages:
1. **Home** - Should show "Luminate Cookbook" with navigation
2. **Email Banner Processor** - Should work as before
3. **Image Uploader** - New tool for batch uploads

## 🔄 Need to Rollback?

Change main file back to `streamlit_app.py` in Streamlit Cloud dashboard.

---

**See `STREAMLIT_CLOUD_UPDATE.md` for detailed instructions.**
