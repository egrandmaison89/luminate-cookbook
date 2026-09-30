# Legacy notes

## Streamlit era (retired)

The original Cookbook ran on Streamlit Cloud. Persistent Playwright sessions for Luminate 2FA could not work reliably under Streamlit’s request-scoped session model, so the app was rewritten as FastAPI (`app/main.py`).

- Old entrypoint preserved at: `archive/legacy_streamlit_app.py`
- Streamlit is **not** in `requirements.txt`
- Do not deploy to Streamlit Cloud

Historical Streamlit troubleshooting remains at the bottom of `docs/TROUBLESHOOTING.md` and in struck-through sections of `docs/DEPLOYMENT.md` for archaeology only.
