# Public hosting options (Playwright + FastAPI)

Cookbook is heavier than a typical web app: Chromium via Playwright for the Image Uploader, MediaPipe/OpenCV for banners, and multi‑minute sessions for 2FA. That drives cost and cold-start behavior.

## Recommended defaults

| Need | Recommendation | Why |
|------|----------------|-----|
| **Occasional use (you only)** | Keep **local** (`./start-local.sh`) | Zero hosting bill; uploader + 2FA most reliable on your Mac |
| **Share on demand / demo** | **Cloud Run scale-to-zero** (when billing allows) or **Fly.io** with auto-stop | Pay mostly when used; expect cold starts (especially Playwright) |
| **Always available for a small team** | Cloud Run with **min instances = 1** (or Fly always-on) | Avoids 20–60s cold starts; costs money every month |

Free tiers often die under Playwright memory: plan for **~2 GiB RAM** per instance.

## Option notes

### Local only (current best for Eric)
- Pros: free, full Playwright, `.env` stays on disk, no admin IT block.
- Cons: only while your Mac is on; not a public URL.

### Google Cloud Run (existing Dockerfile + scripts)
- Pros: already wired (`Dockerfile`, `cloudbuild.yaml`, deploy scripts); scales to zero.
- Cons: free credits/quota ran out before; min-instances cost if you want snappy uploader; cold start pulls a fat image.
- Fit: best when DFCI GCP billing is available again.

### Fly.io / Railway / Render
- Pros: simple public URL; Docker-friendly.
- Cons: free tiers are tight on RAM/CPU; Playwright may need paid plan; still cold starts if scaled to zero.
- Fit: personal public demo of banner/pagebuilder/email tools; uploader may be flaky on cheap tiers.

### Streamlit Cloud
- **Do not use.** App is FastAPI; Streamlit Cloud is obsolete for this project.

## Suggested path forward

1. Daily work: **local** (done).
2. When you need a public link: try **Fly.io** or **Railway** with the existing Dockerfile, 2 GiB memory, and document the URL in this file.
3. If work GCP billing returns: redeploy Cloud Run with scale-to-zero for demos, min=1 only if the team complains about cold starts.

No deploy was performed as part of the local untangle.
