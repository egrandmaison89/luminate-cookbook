# Cookbook untangle — summary (Sep 30, 2026)

## What changed (local branch `chore/local-untangle`, not pushed)

- **Local start:** `./start-local.sh` — uses `./venv/bin/python3 -m uvicorn` so moved-folder shebangs don’t break.
- **Docs:** `docs/LOCAL.md`, `docs/HOSTING_OPTIONS.md`, `docs/LEGACY.md`; README + docs index + DEPLOYMENT banner + CHANGELOG updated.
- **Legacy:** `app.py` (Streamlit) → `archive/legacy_streamlit_app.py`.

## How to run

```bash
cd ~/Desktop/AI/cursor_projects/luminate-cookbook
./start-local.sh
```

Open http://127.0.0.1:8000 (server may already be running from earlier today).

## Remaining knots (not rewritten)

- Dual `venv` / `.venv` — use `./venv` only; recreate if needed (see LOCAL.md).
- `lib/` still holds Streamlit-era helpers consumed by FastAPI services — works, but the boundary is messy.
- Root clutter: `originals/`, `resized/`, logs (gitignored) — leave alone.
- Tests still thin (mostly Email Beautifier); no CI test workflow yet (Cursor usage was maxed).
- Claude Code CLI on this Mac needs `claude` + `/login` before it can drive further refactors.

## Hosting recommendation

1. **Daily:** local (done).  
2. **Public later:** Fly.io or Railway with existing Dockerfile (2 GiB), or Cloud Run when GCP billing is back.  
3. Details: `docs/HOSTING_OPTIONS.md`.

No deploy, no push, no `.env` changes.
