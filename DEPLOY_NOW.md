# Deploy to Google Cloud Run - Quick Guide

## 🚀 Production Deployment

Your FastAPI application is production-ready with full 2FA support, face detection, and all four tools tested. This guide will deploy to Google Cloud Run with auto-scaling and proper resource allocation for Playwright.

## Prerequisites

- Google Cloud SDK installed (`gcloud` command)
- Docker installed
- Google Cloud project created

## Deployment Steps

### Option 1: Quick Deploy (Recommended)

Open your terminal and run:

```bash
cd ~/Desktop/cursor_projects/luminate-cookbook
./deploy-cloud-run.sh YOUR_PROJECT_ID us-central1
```

Replace `YOUR_PROJECT_ID` with your actual Google Cloud project ID.

### Option 2: Manual Deploy

```bash
# 1. Set your project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 3. Build and submit to Cloud Build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/luminate-cookbook

# 4. Deploy to Cloud Run
gcloud run deploy luminate-cookbook \
  --image gcr.io/YOUR_PROJECT_ID/luminate-cookbook \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 600 \
  --max-instances 10 \
  --set-env-vars "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright"
```

## What Will Happen

1. **Docker Build** (~5-10 minutes)
   - Installs Python dependencies
   - Downloads Chromium browser (160MB)
   - Installs system dependencies for Playwright

2. **Deploy to Cloud Run** (~2-3 minutes)
   - Pushes image to Google Container Registry
   - Creates Cloud Run service
   - Returns public URL

3. **Access Your App**
   - You'll get a URL like: `https://luminate-cookbook-xxxxx-uc.a.run.app`
   - Open it in your browser
   - Test the 2FA flow with real credentials

## Expected Output

```
✅ Deployment complete!

Your app is available at:
https://luminate-cookbook-xxxxx-uc.a.run.app

To view logs:
  gcloud run services logs read luminate-cookbook --region us-central1
```

## Important Configuration

The deployment uses these settings optimized for browser automation:

- **Memory**: 2Gi (required for running Chromium)
- **CPU**: 2 cores (for browser performance)
- **Timeout**: 600s (10 minutes for uploads + 2FA wait time)
- **Port**: 8000 (FastAPI default)
- **Concurrency**: Up to 10 instances

## Testing After Deployment

Once deployed, test all four tools:

### 1. Image Uploader (with 2FA)
1. Navigate to: `https://your-app-url.run.app/upload`
2. Enter your Luminate credentials and select images
3. Click "Upload All Images"
4. **If 2FA is required**:
   - You'll see: "Two-factor authentication required"
   - Browser session stays alive waiting for your code
   - Enter your 6-digit 2FA code
   - Upload continues with the same authenticated session
5. Verify images appear in your Luminate Image Library

### 2. Email Banner Processor
1. Navigate to: `https://your-app-url.run.app/banner`
2. Upload one or more photos
3. Configure dimensions (default: 600x340 for email banners)
4. Click "Process Images"
5. Download ZIP with standard + retina versions

### 3. PageBuilder Decomposer
1. Navigate to: `https://your-app-url.run.app/pagebuilder`
2. Enter a PageBuilder URL or name (e.g., `reus_dm_event_2024`)
3. Click "Analyze Structure" to preview
4. Click "Decompose & Download" to get ZIP

### 4. Plain Text Email Beautifier
1. Navigate to: `https://your-app-url.run.app/email-beautifier`
2. Paste ugly plain text email
3. Configure options (strip tracking, format CTAs, etc.)
4. Click "Beautify"
5. Copy the cleaned, formatted output

## Troubleshooting

### View Logs
```bash
gcloud run services logs read luminate-cookbook --region us-central1 --limit 50
```

### Check Service Status
```bash
gcloud run services describe luminate-cookbook --region us-central1
```

### Update Deployment
Just run the same deploy command again, or:
```bash
./deploy-cloud-run.sh YOUR_PROJECT_ID us-central1
```

## Why FastAPI Instead of Streamlit?

This application was originally built with Streamlit but migrated to FastAPI to solve critical architectural limitations:

### The Threading Problem
**Streamlit Issue**: `st.session_state` is request-scoped and thread-local. When a page reruns (which Streamlit does frequently), it may execute in a different thread. Playwright browser objects cannot be accessed from a thread different than the one that created them, causing `RuntimeError: cannot switch to a different thread`.

**FastAPI Solution**: Browser sessions are managed as singleton server-side objects in `BrowserSessionManager`. They persist in memory across HTTP requests and are accessed via UUID session IDs. No thread-switching occurs.

### Architecture Comparison

| Aspect | Streamlit | FastAPI (Current) |
|--------|-----------|-------------------|
| **Session Persistence** | Request-scoped, thread-local | Server-side singleton, survives requests |
| **2FA Support** | ❌ Breaks on rerun | ✅ Fully functional |
| **Threading** | Multi-threaded reruns | Async single-thread with thread pool for sync code |
| **Resource Control** | Limited on Cloud | Explicit memory/CPU allocation |
| **API Access** | None | Full REST API + HTMX endpoints |
| **Deployment** | Streamlit Cloud (limited Playwright support) | Google Cloud Run (full Docker support) |
| **Scalability** | Single container | Auto-scaling 0→N instances |

### Additional Benefits
- ✅ **Automatic API documentation** via FastAPI `/docs` endpoint
- ✅ **Type safety** with Pydantic models
- ✅ **Better error handling** with proper HTTP status codes
- ✅ **Flexible frontend** - HTMX for dynamic updates without SPA complexity
- ✅ **Production-ready** monitoring and health checks

## Need Help?

If deployment fails, check:
1. Docker is running
2. gcloud is authenticated: `gcloud auth login`
3. Correct project is set: `gcloud config get-value project`
4. Required APIs are enabled (the script does this automatically)

## Cost Estimate

Cloud Run pricing (as of 2026):
- **Free tier**: 2 million requests/month
- **With 2Gi memory**: ~$0.05 per upload session (< 1 minute typically)
- **Your usage**: Likely stays in free tier for normal use

---

🎯 **Ready?** Run the deployment command from your terminal!
