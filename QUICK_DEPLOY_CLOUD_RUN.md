# Quick Deploy to Google Cloud Run

## Prerequisites Check

```bash
# Check if gcloud is installed
gcloud --version

# Docker is NOT required! We use Google Cloud Build instead
# If you have Docker, you can use deploy-cloud-run.sh
# If you don't have Docker, use deploy-cloud-run-no-docker.sh (recommended)
```

## 5-Minute Deployment

### Step 1: Login and Setup

```bash
# Login to Google Cloud
gcloud auth login

# Create project (or use existing)
gcloud projects create luminate-cookbook --name="Luminate Cookbook"
gcloud config set project luminate-cookbook

# Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
```

### Step 2: Deploy

**Option A: No Local Docker Required (Recommended for Dev Containers)**

```bash
# Make script executable
chmod +x deploy-cloud-run-no-docker.sh

# Deploy (uses Google Cloud Build - builds in the cloud)
./deploy-cloud-run-no-docker.sh $(gcloud config get-value project) us-central1
```

**Option B: With Local Docker (if you have Docker installed)**

```bash
# Make script executable
chmod +x deploy-cloud-run.sh

# Deploy (builds locally, then pushes)
./deploy-cloud-run.sh $(gcloud config get-value project) us-central1
```

### Step 3: Get Your URL

The script will output your app URL, or run:

```bash
gcloud run services describe luminate-cookbook \
    --platform managed \
    --region us-central1 \
    --format 'value(status.url)'
```

## That's It! 🎉

Your app is now live with:
- ✅ Email Banner Processor
- ✅ Image Uploader (full Playwright support!)
- ✅ PageBuilder Decomposer

## Update Later

```bash
# No Docker version (recommended)
./deploy-cloud-run-no-docker.sh $(gcloud config get-value project) us-central1

# Or with Docker (if you have it)
./deploy-cloud-run.sh $(gcloud config get-value project) us-central1
```

## Troubleshooting

**Build fails?**
```bash
gcloud builds list
gcloud builds log BUILD_ID
```

**Deployment fails?**
```bash
gcloud run services logs read luminate-cookbook --region us-central1
```

**Need help?**
See [GOOGLE_CLOUD_RUN_DEPLOYMENT.md](GOOGLE_CLOUD_RUN_DEPLOYMENT.md) for detailed guide.
