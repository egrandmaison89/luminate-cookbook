# Google Cloud Run Deployment Guide

Complete guide for deploying Luminate Cookbook to Google Cloud Run with full Playwright support.

## Prerequisites

1. **Google Cloud Account**
   - Sign up at https://cloud.google.com (free tier available)
   - $300 free credit for new accounts

2. **Google Cloud SDK (gcloud)**
   - Install from: https://cloud.google.com/sdk/docs/install
   - Or use: `brew install google-cloud-sdk` (macOS)

3. **Docker**
   - Install from: https://docs.docker.com/get-docker/

4. **GitHub Repository**
   - Your code should be in a GitHub repository

## Quick Start (Automated)

### Step 1: Install Prerequisites

```bash
# Install Google Cloud SDK
# macOS:
brew install google-cloud-sdk

# Linux:
curl https://sdk.cloud.google.com | bash

# Windows:
# Download installer from https://cloud.google.com/sdk/docs/install
```

### Step 2: Authenticate

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create luminate-cookbook --name="Luminate Cookbook"

# Set the project
gcloud config set project luminate-cookbook

# Note your Project ID (you'll need it)
gcloud config get-value project
```

### Step 3: Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### Step 4: Deploy

```bash
# Make the script executable
chmod +x deploy-cloud-run.sh

# Run deployment (replace PROJECT_ID with your actual project ID)
./deploy-cloud-run.sh YOUR_PROJECT_ID us-central1
```

The script will:
- Build the Docker image
- Push to Google Container Registry
- Deploy to Cloud Run
- Give you the app URL

## Manual Deployment Steps

If you prefer to deploy manually:

### Step 1: Build and Push Docker Image

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Build the image
docker build -t gcr.io/$PROJECT_ID/luminate-cookbook:latest .

# Configure Docker to use gcloud as credential helper
gcloud auth configure-docker

# Push the image
docker push gcr.io/$PROJECT_ID/luminate-cookbook:latest
```

### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy luminate-cookbook \
    --image gcr.io/$PROJECT_ID/luminate-cookbook:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8501 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright"
```

### Step 3: Get Your App URL

```bash
gcloud run services describe luminate-cookbook \
    --platform managed \
    --region us-central1 \
    --format 'value(status.url)'
```

## Continuous Deployment with GitHub

Set up automatic deployments when you push to GitHub:

### Step 1: Connect GitHub Repository

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **Cloud Build** → **Triggers**
3. Click **Create Trigger**
4. Connect your GitHub repository
5. Select branch: `main`
6. Configuration: **Cloud Build configuration file**
7. Location: `cloudbuild.yaml`

### Step 2: Push to GitHub

Every push to `main` will automatically:
- Build the Docker image
- Deploy to Cloud Run
- Update your app

## Configuration Options

### Memory and CPU

The deployment uses:
- **Memory**: 2Gi (required for Playwright)
- **CPU**: 2 (recommended for Playwright)
- **Timeout**: 300 seconds (5 minutes)

To change these:

```bash
gcloud run services update luminate-cookbook \
    --memory 4Gi \
    --cpu 4 \
    --region us-central1
```

### Custom Domain

1. Go to Cloud Run service
2. Click **Manage Custom Domains**
3. Add your domain
4. Follow DNS setup instructions

### Environment Variables

Add environment variables:

```bash
gcloud run services update luminate-cookbook \
    --set-env-vars "KEY1=value1,KEY2=value2" \
    --region us-central1
```

## Monitoring and Logs

### View Logs

```bash
# Real-time logs
gcloud run services logs tail luminate-cookbook --region us-central1

# Recent logs
gcloud run services logs read luminate-cookbook --region us-central1
```

### View in Console

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Click on `luminate-cookbook`
3. View logs, metrics, and revisions

## Cost Estimation

### Free Tier
- **2 million requests/month** - FREE
- **400,000 GB-seconds** - FREE
- **200,000 GHz-seconds** - FREE

### After Free Tier
- **Requests**: $0.40 per million
- **CPU**: $0.00002400 per GB-second
- **Memory**: $0.00000250 per GB-second

**Estimated monthly cost for moderate use**: $0-5/month

## Troubleshooting

### Build Fails

```bash
# Check build logs
gcloud builds list
gcloud builds log BUILD_ID
```

### Deployment Fails

```bash
# Check service logs
gcloud run services logs read luminate-cookbook --region us-central1

# Check service status
gcloud run services describe luminate-cookbook --region us-central1
```

### Playwright Not Working

1. Check logs for system library errors
2. Verify memory is at least 2Gi
3. Check that Dockerfile was used (not packages.txt)

### Image Too Large

The Docker image is ~1-2GB due to:
- System libraries
- Playwright Chromium (~300MB)
- Python packages

This is normal and necessary.

## Updating the Deployment

### Option 1: Use the Script

```bash
./deploy-cloud-run.sh YOUR_PROJECT_ID us-central1
```

### Option 2: Manual Update

```bash
# Rebuild and push
docker build -t gcr.io/$PROJECT_ID/luminate-cookbook:latest .
docker push gcr.io/$PROJECT_ID/luminate-cookbook:latest

# Update service
gcloud run services update luminate-cookbook \
    --image gcr.io/$PROJECT_ID/luminate-cookbook:latest \
    --region us-central1
```

### Option 3: Automatic (with GitHub trigger)

Just push to GitHub - it will auto-deploy!

## Security

### Authentication (Optional)

To require authentication:

```bash
gcloud run services update luminate-cookbook \
    --no-allow-unauthenticated \
    --region us-central1
```

### Secrets Management

Store sensitive data in Secret Manager:

```bash
# Create secret
echo -n "your-secret-value" | gcloud secrets create my-secret --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding my-secret \
    --member="serviceAccount:SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

# Use in Cloud Run
gcloud run services update luminate-cookbook \
    --update-secrets="SECRET_NAME=my-secret:latest" \
    --region us-central1
```

## Next Steps

1. ✅ Deploy to Cloud Run
2. ✅ Test all three tools:
   - Email Banner Processor
   - Image Uploader (should work now!)
   - PageBuilder Decomposer
3. ✅ Set up custom domain (optional)
4. ✅ Configure monitoring alerts (optional)
5. ✅ Share the URL with your team!

## Support

- **Google Cloud Run Docs**: https://cloud.google.com/run/docs
- **Cloud Build Docs**: https://cloud.google.com/build/docs
- **Billing**: https://console.cloud.google.com/billing

## Summary

✅ **Free tier available** - 2 million requests/month  
✅ **Full Playwright support** - Image Uploader works!  
✅ **Auto-scaling** - Handles traffic automatically  
✅ **Easy updates** - Just push to GitHub  
✅ **Low cost** - $0-5/month for moderate use  

Your app is now live with full functionality! 🎉
