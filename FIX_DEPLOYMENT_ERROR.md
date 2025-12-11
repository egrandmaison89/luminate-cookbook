# Fix: Streamlit Cloud "Unexpected error" on App URL

## Problem
The "App URL (optional)" field is showing an "Unexpected error" and the Deploy button is grayed out.

## Solution: Leave App URL Empty

The custom URL `ericscookbook` might be taken or causing validation issues. Here's how to fix it:

### Step 1: Clear the App URL Field
1. **Delete the text** in the "App URL (optional)" field
2. **Leave it completely empty**
3. Streamlit will auto-generate a URL for you (like `luminate-cookbook-xxxxx.streamlit.app`)

### Step 2: Verify Other Fields
Make sure these are correct:
- **Repository:** `egrandmaison89/luminate-cookbook`
- **Branch:** `main`
- **Main file path:** `app.py`
- **App URL:** (leave empty)

### Step 3: Deploy
1. The "Deploy" button should now be clickable
2. Click "Deploy"
3. Wait for deployment to complete

### Step 4: Get Your App URL
After deployment:
1. Streamlit will assign an auto-generated URL
2. You can find it in your app dashboard
3. The URL will be something like: `https://luminate-cookbook-xxxxx.streamlit.app`

## Why This Happens

Custom URLs in Streamlit Cloud:
- Must be unique across all Streamlit apps
- May have naming restrictions
- Can cause errors if already taken or invalid format

**Best Practice:** Let Streamlit auto-generate the URL, then you can share that URL with your team. The auto-generated URLs work perfectly fine!

## Alternative: Try Different Custom URL

If you really want a custom URL, try:
- `erics-luminate-cookbook`
- `luminate-cookbook-tools`
- `eric-cookbook`
- Or any other unique name

But for now, **leave it empty** to get the app deployed quickly!
