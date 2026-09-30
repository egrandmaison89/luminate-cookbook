# Local use (FastAPI)

This is the supported way to run Luminate Cookbook day-to-day.

## One-command start

```bash
cd ~/Desktop/AI/cursor_projects/luminate-cookbook
./start-local.sh
```

Open **http://127.0.0.1:8000**

| Tool | URL |
|------|-----|
| Home | http://127.0.0.1:8000/ |
| Image Uploader (2FA) | http://127.0.0.1:8000/upload |
| Banner Processor | http://127.0.0.1:8000/banner |
| PageBuilder Decomposer | http://127.0.0.1:8000/pagebuilder |
| Email Beautifier | http://127.0.0.1:8000/email-beautifier |
| API docs (Swagger) | http://127.0.0.1:8000/docs |
| Health | http://127.0.0.1:8000/health |

Stop with **Ctrl+C**.

## First-time / broken venv

If `./start-local.sh` says there is no usable `./venv`, or imports fail after moving the project folder:

```bash
cd ~/Desktop/AI/cursor_projects/luminate-cookbook
rm -rf venv .venv
/usr/bin/python3 -m venv venv
./venv/bin/python3 -m pip install -U pip
./venv/bin/python3 -m pip install -r requirements.txt
./venv/bin/python3 -m playwright install chromium
./start-local.sh
```

Always start with `./venv/bin/python3 -m uvicorn …` (or `./start-local.sh`). Do **not** rely on `venv/bin/uvicorn` after moving the repo — shebangs can still point at an old path.

## Credentials

Optional `.env` in the project root (never commit):

- `LUMINATE_USERNAME` / `LUMINATE_PASSWORD` — used by the Image Uploader against Luminate Online

Other tools (banner, pagebuilder, email beautifier) do not need those for basic use.

## What not to run

- Do **not** `streamlit run app.py` — Streamlit was removed from the stack. The old entrypoint lives at `archive/legacy_streamlit_app.py` for history only.
- Prefer **one** venv: `./venv`. Ignore or delete `./.venv` if present.

## Quick smoke

With the server running:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health
```

Expect `200`.
