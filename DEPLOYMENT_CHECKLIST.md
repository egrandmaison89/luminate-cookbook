# Streamlit Cloud Docker Deployment Checklist

Quick reference for deploying with Docker support on Streamlit Cloud.

## Pre-Deployment Checklist

- [x] Dockerfile created in repository root
- [x] .dockerignore created to optimize build
- [x] All application files committed
- [x] requirements.txt is up to date
- [ ] Repository pushed to GitHub

## Deployment Steps

### 1. Commit and Push Files
```bash
git add Dockerfile .dockerignore test_playwright.py DOCKER_DEPLOYMENT.md
git commit -m "Add Dockerfile for Playwright support on Streamlit Cloud"
git push origin main
```

### 2. Configure Streamlit Cloud

**⚠️ IMPORTANT: Streamlit Cloud does NOT support Dockerfiles.**

**Option A: Try packages.txt (for Streamlit Cloud)**
1. Ensure `packages.txt` is in your repository
2. Streamlit Cloud will automatically detect and use it
3. No additional settings needed

**Option B: Deploy to Alternative Platform**
- Use Google Cloud Run, Railway, or Fly.io
- These platforms support Dockerfiles
- See [STREAMLIT_CLOUD_ALTERNATIVES.md](STREAMLIT_CLOUD_ALTERNATIVES.md)

### 3. Deploy

- Click **"Redeploy"** button, OR
- Push a new commit to trigger automatic redeploy

### 4. Monitor Build

- First build: ~10-15 minutes (downloading Playwright browsers)
- Subsequent builds: ~5-10 minutes
- Watch build logs for any errors

### 5. Verify Deployment

- [ ] App loads successfully
- [ ] Email Banner Processor works
- [ ] Image Uploader page loads (no "Browser automation unavailable" error)
- [ ] Can upload test image via Image Uploader
- [ ] PageBuilder Decomposer works

## Testing Playwright (Optional)

If you want to test Playwright in the container:

```bash
# Build image
docker build -t luminate-cookbook:test .

# Test Playwright
docker run --rm luminate-cookbook:test python test_playwright.py

# Run app locally
docker run -p 8501:8501 luminate-cookbook:test
```

## Troubleshooting

### Build Fails
- Check Streamlit Cloud build logs
- Verify Dockerfile syntax
- Ensure all package names are correct

### Image Uploader Still Shows Error
- Verify Dockerfile was used (check build logs)
- Check that Playwright browsers installed successfully
- Review deployment logs for system library errors

### Build Timeout
- First build takes longer (downloading browsers)
- Streamlit Cloud has time limits
- Consider using a pre-built base image (advanced)

## Success Indicators

✅ Build completes without errors
✅ App deploys successfully
✅ Image Uploader page shows upload form (not error message)
✅ Can successfully upload an image
✅ All other tools continue working

## Files to Commit

Make sure these files are in your repository:
- `Dockerfile` (required)
- `.dockerignore` (recommended)
- `app.py` (required)
- `requirements.txt` (required)
- All files in `pages/` directory (required)
- `luminate_uploader_lib.py` (required for Image Uploader)

## Next Steps After Deployment

1. Test all three tools:
   - Email Banner Processor
   - Image Uploader
   - PageBuilder Decomposer

2. Share the app URL with your team

3. Monitor for any issues in the first few days

4. Update documentation if needed
