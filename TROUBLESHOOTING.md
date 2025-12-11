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
