# Luminate Cookbook

A collection of tools for working with Luminate Online, built with FastAPI.

## Features

### 📤 Image Uploader
Upload images to your Luminate Online Image Library with **full 2FA support**. Browser sessions stay alive during authentication - no more threading issues!

- Persistent browser sessions for 2FA
- Progress tracking during uploads
- Batch upload support
- Real-time status updates via HTMX

### 🏃 Email Banner Processor
Transform photos into perfectly-sized email banners with intelligent face detection.

- Automatic face detection to avoid cutting off heads
- Customizable dimensions and quality
- Retina-ready 2x versions
- ZIP download with all processed images

### 🔍 PageBuilder Decomposer
Extract all nested PageBuilders from a Luminate Online page.

- No login required
- Hierarchical structure visualization
- Download as ZIP with organized folder structure
- Option to exclude global stylesheet components

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Jinja2 templates + HTMX
- **Browser Automation**: Playwright
- **Deployment**: Docker / Google Cloud Run

## Local Development

### Prerequisites

- Python 3.9+
- Playwright browsers

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd luminate-cookbook

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium

# Run the app
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000` in your browser.

## Deployment

### Docker

```bash
# Build the image
docker build -t luminate-cookbook .

# Run the container
docker run -p 8000:8000 luminate-cookbook
```

### Google Cloud Run

```bash
# Deploy using the provided script
./deploy-cloud-run.sh YOUR_PROJECT_ID us-central1
```

Or set up automatic deployments via Cloud Build - see `cloudbuild.yaml`.

## API Endpoints

### Upload API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload/start` | POST | Start upload session, returns session_id |
| `/api/upload/2fa/{session_id}` | POST | Submit 2FA code |
| `/api/upload/status/{session_id}` | GET | Get upload status |
| `/api/upload/{session_id}` | DELETE | Cancel upload |

### Banner API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/banner/process` | POST | Process images, returns ZIP |

### PageBuilder API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/pagebuilder/analyze` | POST | Analyze structure (preview) |
| `/api/pagebuilder/decompose` | POST | Decompose and download ZIP |

## Architecture

### 2FA Flow

The key innovation is how 2FA is handled:

1. **Start Upload**: Creates a browser session, attempts login
2. **2FA Detected**: Browser stays open, session ID returned to client
3. **Submit Code**: Client submits 2FA code to same session
4. **Success**: Upload continues with authenticated browser

```
Client                    FastAPI                 BrowserSessionManager
  |                          |                           |
  |-- POST /upload/start --->|                           |
  |                          |-- create_session() ------>|
  |                          |                           |-- Create browser
  |                          |                           |-- Attempt login
  |                          |                           |-- Detect 2FA
  |                          |<-- session_id, needs_2fa -|
  |<-- {session_id, needs_2fa: true}                     |
  |                          |                           |
  |   (User enters 2FA code) |                           |
  |                          |                           |
  |-- POST /upload/2fa ----->|                           |
  |                          |-- submit_2fa() ---------->|
  |                          |                           |-- Submit code
  |                          |                           |-- Verify success
  |                          |                           |-- Start uploads
  |<-- {success: true} ------|<--------------------------|
```

Browser sessions are managed as persistent server-side objects, not stored in client session state. This eliminates the threading issues that occurred with Streamlit.

## Project Structure

```
luminate-cookbook/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── services/
│   │   ├── browser_manager.py   # Browser session management
│   │   ├── banner_processor.py  # Image processing
│   │   └── pagebuilder_service.py
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS assets
├── lib/                     # Shared libraries
├── Dockerfile
├── requirements.txt
└── README.md
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | Server port |
| `PLAYWRIGHT_BROWSERS_PATH` | (auto) | Playwright browser location |
| `DEBUG` | false | Enable debug mode |

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
