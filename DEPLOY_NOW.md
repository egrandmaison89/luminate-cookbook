# Deploy to Google Cloud Run - Quick Guide

## 🚀 Ready to Deploy!

Your FastAPI migration is complete and tested locally. Now let's deploy to production to test the 2FA flow.

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

## Testing 2FA in Production

Once deployed:

1. Navigate to: `https://your-app-url.run.app/upload`
2. Enter your Luminate credentials
3. Select an image to upload
4. Click "Upload All Images"
5. **If 2FA is required**:
   - You'll see: "Two-factor authentication required"
   - Browser session stays alive waiting for your code
   - Enter your 6-digit 2FA code
   - Upload continues with the same authenticated session

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

## What's Different from Streamlit?

✅ **No threading issues** - Browser sessions persist server-side
✅ **Proper 2FA handling** - Same browser continues after code entry
✅ **Better resource control** - Explicit memory/CPU allocation
✅ **Modern stack** - FastAPI + HTMX for dynamic updates
✅ **API endpoints** - Can be integrated with other services

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
