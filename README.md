# Luminate Cookbook

A production-ready suite of tools for Luminate Online administrators, built with FastAPI and deployed on Google Cloud Run. Designed to solve real operational challenges with enterprise-grade architecture.

## Features

### 📤 Image Uploader
Upload images to your Luminate Online Image Library with **full 2FA support**. Solves the critical threading issue that plagued browser-based solutions.

**Key Innovation**: Persistent server-side browser sessions survive HTTP request boundaries, enabling seamless 2FA workflows without session loss.

- ✅ Persistent Playwright browser sessions for 2FA
- ✅ Real-time progress tracking via HTMX polling
- ✅ Batch upload with verification
- ✅ Automatic retry and validation
- ✅ Human-like interaction patterns to avoid bot detection

### 🎨 Email Banner Processor
Transform photos into perfectly-sized email banners with **intelligent person detection** and **interactive crop preview**.

**Design Decision**: MediaPipe full-body detection ensures both people and gestures are captured. Interactive preview gives users control over automatic suggestions.

- ✅ MediaPipe Pose detection for full-body awareness (with OpenCV face detection fallback)
- ✅ Smart crop algorithm with configurable padding (0-30%)
- ✅ Interactive crop preview with Cropper.js for manual adjustments
- ✅ Two-workflow support: preview-adjust or auto-process
- ✅ Customizable dimensions and quality
- ✅ Retina-ready 2x versions for high-DPI displays
- ✅ ZIP download with all processed variants

> See [Banner Processor User Guide](docs/BANNER_PROCESSOR_USER_GUIDE.md) for detailed usage instructions.

### 🔍 PageBuilder Decomposer
Extract and analyze nested PageBuilder components from any Luminate Online page with full hierarchy visualization.

**Architecture**: No authentication required - pure HTTP parsing with recursive component discovery.

- ✅ No login required (public content only)
- ✅ Complete hierarchical structure visualization
- ✅ Recursive component extraction
- ✅ ZIP download with organized folder structure
- ✅ Optional exclusion of global stylesheets

### ✨ HTML → Plain Text Email Beautifier
Paste or upload the **HTML source** of a marketing email; get polished plain text with clean URLs and optional CTA emphasis.

**Use Case**: Built for Luminate/Convio-style HTML (tables, preheader, tracking links). Converts HTML to text, then beautifies: tracking strips, line joining, footer simplification, optional markdown links.

- ✅ **HTML in**: paste in the page or upload `.html` / `multipart` API
- ✅ Strips tracking parameters (utm_*, aff, s_src, s_subsrc, etc.)
- ✅ Intelligent CTA detection (RSVP, Donate, Give Now, Volunteer, etc.)
- ✅ Joins broken sentences (hyphenated words, time ranges)
- ✅ Footer detection with visual break; social links removed
- ✅ Preheader / preview extraction from hidden cells where present
- ✅ Line-break normalization

> See [Email Beautifier Technical](docs/EMAIL_BEAUTIFIER.md) for implementation details and iterative change workflow.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Jinja2 templates + HTMX
- **Browser Automation**: Playwright
- **Email beautifier (HTML)**: BeautifulSoup4, html2text
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

# After pulling new code, run the line above again so new packages
# (e.g. html2text, beautifulsoup4 for the Email Beautifier) are installed.

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

All endpoints return JSON except where noted. Interactive documentation available at `/docs` (Swagger UI).

### Image Uploader API

| Endpoint | Method | Description | Returns |
|----------|--------|-------------|---------|
| `/api/upload/start` | POST | Start upload session, attempts login | `{session_id, state, needs_2fa, message}` |
| `/api/upload/2fa/{session_id}` | POST | Submit 2FA code to existing session | `{success, state, message}` |
| `/api/upload/status/{session_id}` | GET | Poll for current status and progress | `{state, progress, results, message}` |
| `/api/upload/{session_id}` | DELETE | Cancel session and cleanup resources | `{success, message}` |

**HTMX Endpoints** (return HTML partials):
- `POST /upload/start` - Start upload, returns status HTML
- `POST /upload/2fa/{session_id}` - Submit 2FA, returns updated status HTML
- `GET /api/upload/status/{session_id}/partial` - Poll endpoint for HTMX

### Email Banner Processor API

| Endpoint | Method | Description | Returns |
|----------|--------|-------------|---------|
| `/api/banner/preview` | POST | Generate crop preview for single image | JSON with base64 image and crop coordinates |
| `/api/banner/process` | POST | Process images with person detection | ZIP file (application/zip) |

**Form Parameters**:
- `files`: List of image files (multipart/form-data)
- `width`: Target width in pixels (default: 600)
- `height`: Target height in pixels (default: 340)
- `quality`: JPEG quality 1-100 (default: 82)
- `crop_padding`: Padding around detected people 0.0-0.3 (default: 0.15)
- `include_retina`: Generate 2x version (default: true)
- `filename_prefix`: Optional prefix for output filenames
- `manual_crops`: Optional JSON string with manual crop coordinates per file

### PageBuilder Decomposer API

| Endpoint | Method | Description | Returns |
|----------|--------|-------------|---------|
| `/api/pagebuilder/analyze` | POST | Analyze structure without downloading | `{success, hierarchy, components, total_components}` |
| `/api/pagebuilder/decompose` | POST | Extract all nested PageBuilders | ZIP file (application/zip) |

**Request Body**:
```json
{
  "url_or_name": "reus_dm_event_2024",
  "base_url": "https://danafarber.jimmyfund.org",
  "ignore_global_stylesheet": true
}
```

### Email Beautifier API (HTML → plain text)

| Endpoint | Method | Description | Returns |
|----------|--------|-------------|---------|
| `/api/email-beautifier/process` | POST | Convert HTML email to beautified plain text | `{success, beautified_text, stats}` |

**Request** (choose one):

- **JSON** — `Content-Type: application/json`
```json
{
  "html": "<html><body>…</body></html>",
  "strip_tracking": true,
  "format_ctas": true,
  "markdown_links": true
}
```

- **Multipart** — `Content-Type: multipart/form-data` with field `file` = HTML file, and the same option fields as form keys (`strip_tracking`, `format_ctas`, `markdown_links` are typical boolean strings: `true` / `false`).

**Response stats** (non-exhaustive):
- `urls_cleaned`, `ctas_formatted`, `links_converted`, `lines_before`, `lines_after`
- `css_stripped`, `preview_text_found`, `source` (e.g. `"html"` when using `beautify_email_from_html`)

## Architecture

### Design Philosophy

This application was architected to solve specific operational challenges encountered with Luminate Online:

1. **2FA Threading Problem**: Streamlit's session state doesn't survive reruns, causing browser objects to be accessed from different threads
2. **Scalability**: Cloud Run provides auto-scaling without managing servers
3. **Modern UX**: HTMX enables dynamic updates without complex SPA frameworks
4. **Reliability**: Playwright with anti-detection ensures consistent automation success

### Tech Stack Rationale

| Technology | Why We Chose It |
|------------|-----------------|
| **FastAPI** | Async-first Python framework with excellent performance and automatic API docs. Necessary for proper async Playwright integration. |
| **Playwright** | Most reliable browser automation library with strong anti-detection. Chromium provides consistent rendering across environments. |
| **HTMX** | Enables dynamic UI updates without React/Vue complexity. Perfect for server-rendered apps with targeted interactivity. |
| **Jinja2** | Server-side templating keeps frontend simple while maintaining flexibility. |
| **Docker** | Ensures consistent Playwright system dependencies across development and production. |
| **Cloud Run** | Serverless container platform with generous free tier (2M requests/month). Auto-scales from 0 to N instances based on traffic. |

### 2FA Flow - The Critical Innovation

**The Problem**: Traditional session-based approaches fail because browser objects can't survive HTTP request boundaries. Streamlit's `st.session_state` is request-scoped and thread-local, causing browser access from wrong threads.

**Our Solution**: Server-side persistent browser sessions managed as singleton objects with UUID-based session IDs.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client (Browser)                            │
└─────────────────────────────────────────────────────────────────┘
         │
         │ POST /upload/start
         │ (credentials + files)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Server                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         BrowserSessionManager (Singleton)                │  │
│  │                                                          │  │
│  │  sessions: Dict[UUID, BrowserSession]                    │  │
│  │    ├─ session_1: {                                       │  │
│  │    │    playwright: <Playwright>                         │  │
│  │    │    browser: <Browser> ← PERSISTENT OBJECT           │  │
│  │    │    page: <Page>       ← STAYS ALIVE                 │  │
│  │    │    state: AWAITING_2FA                              │  │
│  │    │  }                                                   │  │
│  │    └─ session_2: { ... }                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │
         │ returns: {session_id: "abc-123", needs_2fa: true}
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Client (Browser)                            │
│  [User receives 2FA code via authenticator app]                 │
└─────────────────────────────────────────────────────────────────┘
         │
         │ POST /upload/2fa/abc-123
         │ {code: "123456"}
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Server                                │
│                                                                 │
│  Look up session_id "abc-123" → Gets SAME browser object       │
│  Submit 2FA code to page that's STILL OPEN                     │
│  Verify authentication                                          │
│  Start uploads in background task                              │
└─────────────────────────────────────────────────────────────────┘
```

**Key Technical Details**:

1. **Thread Pool Execution**: Playwright is synchronous, so we run it in a thread pool via `loop.run_in_executor()`
2. **Session Lifecycle**: Sessions auto-expire after 10 minutes or on completion
3. **Background Cleanup**: Async task runs every 30 seconds to clean expired sessions
4. **Concurrent Limit**: Maximum 10 simultaneous browser sessions to prevent resource exhaustion

This architecture is what makes 2FA possible - the browser session persists across HTTP requests because it's stored in server memory, not serialized into client state.

## Project Structure

```
luminate-cookbook/
├── app/
│   ├── main.py                      # FastAPI app with all routes (546 lines)
│   ├── config.py                    # Pydantic settings with env var support
│   ├── services/
│   │   ├── browser_manager.py       # ⭐ Core 2FA solution (738 lines)
│   │   ├── banner_processor.py      # OpenCV face detection + image processing
│   │   ├── email_html_to_text.py    # HTML email → initial plain text
│   │   ├── email_beautifier.py     # Plain-text beautify + from-HTML entrypoint
│   │   └── pagebuilder_service.py   # PageBuilder decomposition wrapper
│   ├── models/
│   │   └── schemas.py               # Pydantic request/response models
│   ├── templates/                   # Jinja2 HTML templates
│   │   ├── base.html                # Base template with navigation
│   │   ├── index.html               # Home page with tool cards
│   │   ├── upload.html              # Image uploader interface
│   │   ├── banner.html              # Banner processor interface
│   │   ├── pagebuilder.html         # PageBuilder tool interface
│   │   ├── email_beautifier.html    # Email beautifier interface
│   │   └── partials/                # HTMX partial responses
│   │       ├── upload_status.html   # Dynamic upload status
│   │       └── upload_error.html    # Error display
│   └── static/
│       ├── css/styles.css           # Custom styling
│       └── js/app.js                # Client-side utilities
├── lib/                             # Reusable libraries from original Streamlit app
│   ├── luminate_uploader_lib.py     # Core Luminate interaction logic
│   ├── pagebuilder_decomposer_lib.py # PageBuilder parsing engine
│   ├── batch_uploader_lib.py        # Batch upload utilities
│   ├── cookie_helper.py             # Cookie management
│   └── session_storage.py           # Session persistence helpers
├── scripts/
│   ├── process_banners.py           # Standalone banner processing script
│   └── upload_to_luminate.py        # CLI upload tool
├── docs/
│   ├── EMAIL_BEAUTIFIER.md          # Email beautifier technical doc
│   ├── AI_AGENT_GUIDE.md            # Guide for AI agents (change workflow)
│   ├── DEPLOYMENT.md                # Full deployment guide
│   ├── GOOGLE_CLOUD_RUN.md          # Cloud Run specific docs
│   └── TROUBLESHOOTING.md           # Common issues and solutions
├── Dockerfile                       # Production-ready container with Playwright
├── cloudbuild.yaml                  # Google Cloud Build configuration
├── deploy-cloud-run.sh              # Automated deployment script
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

**Key Files Explained**:

- **browser_manager.py**: The heart of the 2FA solution. Manages persistent Playwright browser sessions with lifecycle management, cleanup, and thread-safe operations.
- **banner_processor.py**: Image processing with MediaPipe pose detection for full-body awareness, OpenCV face detection fallback, and smart crop algorithms.
- **email_html_to_text.py** / **email_beautifier.py**: HTML-to-text (BeautifulSoup, html2text) plus regex/URL/CTA/footer pipeline for plain-text output.
- **main.py**: FastAPI application with both JSON API endpoints and HTMX HTML partial endpoints for dynamic UI updates.
- **Dockerfile**: Multi-stage build that installs all Playwright system dependencies (Chromium requires ~30 system packages).

## Configuration

Environment variables (loaded via Pydantic Settings):

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | Server port for uvicorn |
| `DEBUG` | false | Enable debug mode (auto-reload, verbose logs) |
| `PLAYWRIGHT_BROWSERS_PATH` | `/ms-playwright` (Docker)<br>`~/.cache/ms-playwright` (local) | Playwright browser installation directory |
| `PLAYWRIGHT_HEADLESS` | true | Run browsers in headless mode (set false for debugging) |
| `SESSION_TIMEOUT_SECONDS` | 600 | Browser session expiration (10 minutes) |
| `MAX_2FA_WAIT_SECONDS` | 90 | Time limit for 2FA code submission |
| `MAX_CONCURRENT_SESSIONS` | 10 | Maximum simultaneous browser sessions |
| `MAX_UPLOAD_SIZE_MB` | 10 | Maximum file size for uploads |

**Cloud Run Specific**:
- `PORT` is set automatically by Cloud Run (typically 8080)
- `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` is required for Cloud Run
- Memory: **2Gi minimum** (Chromium requires substantial memory)
- CPU: **2 cores recommended** (improves browser performance)
- Timeout: **600 seconds** (allows time for 2FA and uploads)

**Why These Defaults**:
- **10-minute session timeout**: Balances user convenience (time to find authenticator app) with memory efficiency
- **10 concurrent sessions**: Prevents resource exhaustion while serving multiple users
- **2Gi memory**: Chromium with multiple tabs requires 200-400MB per session; 2Gi provides comfortable headroom

## Advanced Topics

### Browser Automation Strategy

**Challenge**: Luminate Online's admin interface requires careful automation to avoid bot detection.

**Our Approach**:

1. **Realistic Browser Fingerprint**
   ```python
   session.context = session.browser.new_context(
       user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
       viewport={'width': 1920, 'height': 1080},
       locale='en-US',
       timezone_id='America/New_York',
   )
   ```

2. **Anti-Detection Scripts**
   - Override `navigator.webdriver` property
   - Inject realistic plugin array
   - Add Chrome runtime object
   - Prevents headless browser detection

3. **Human-Like Behavior**
   ```python
   # Random delays between keystrokes (50-150ms)
   for char in username:
       username_input.type(char, delay=random.randint(50, 150))
   
   # Random pauses between actions (200-800ms)
   page.wait_for_timeout(random.randint(200, 500))
   ```

4. **Robust 2FA Detection**
   - Multiple detection strategies (content analysis, input field detection, URL patterns)
   - Handles various 2FA implementations
   - Graceful fallback if detection ambiguous

5. **Error Recovery**
   - Retry logic for network failures
   - Verification after each upload
   - Automatic cleanup on errors
   - Detailed logging for debugging

**Why This Matters**: Simple Playwright scripts often get blocked. Our implementation mimics real user behavior, ensuring reliable automation even as Luminate's anti-bot measures evolve.

---

### Performance Considerations

**Trade-offs we made**:

| Decision | Benefit | Cost | Rationale |
|----------|---------|------|-----------|
| **Server-side sessions** | 2FA support | Memory usage (200MB/session) | 2FA is critical, memory is cheap |
| **Synchronous Playwright** | API compatibility | Thread pool overhead | Playwright's sync API is more stable |
| **Face detection (Haar Cascade)** | Fast, no ML dependencies | Less accurate than ML models | Speed > perfection for batch processing |
| **HTMX over SPA** | Simple, no build step | Less rich interactions | Good enough UX, faster development |
| **Explicit cleanup** | Prevents memory leaks | More complex code | Production reliability > code simplicity |

**Bottlenecks and Optimizations**:

1. **Bottleneck**: Browser startup (~2-3 seconds)
   - **Optimization**: Session reuse across uploads within same session
   - **Impact**: Single startup for batch uploads

2. **Bottleneck**: Image processing (1-2 seconds per image)
   - **Optimization**: Could parallelize with asyncio, but chose not to
   - **Rationale**: Face detection is CPU-bound; parallelization doesn't help with 2 cores

3. **Bottleneck**: Network I/O to Luminate (variable)
   - **Optimization**: Retry logic and verification
   - **Impact**: Reliability > speed

4. **Bottleneck**: Cold starts on Cloud Run (~20-30 seconds)
   - **Optimization**: Keep-alive via Cloud Scheduler or min-instances
   - **Cost**: $0/month (Scheduler free tier) or $10/month (min-instances)

---

### Security Considerations

**What we protect**:
- ✅ User credentials: Never logged, stored only in memory during session
- ✅ Browser sessions: Isolated per user, automatic timeout
- ✅ Uploaded files: Stored in temp directory, cleaned up after upload
- ✅ 2FA codes: Never logged or persisted

**What we don't protect** (by design):
- ⚠️ No authentication on the app itself (anyone can access)
- ⚠️ No rate limiting (Cloud Run provides DDoS protection but not application-level)
- ⚠️ No audit logging (would require database)

**Recommendations for production**:
1. Add authentication layer (Cloud Identity-Aware Proxy or Firebase Auth)
2. Implement rate limiting (Redis + middleware)
3. Add audit logging (Cloud Logging structured logs)
4. Use Secret Manager for Luminate URLs if they're sensitive

---

### Future Enhancements

**Considered but not implemented** (yet):

1. **Session Persistence Across Instances**
   - Requires: Redis/Memorystore
   - Benefit: Multi-instance Cloud Run scaling
   - Cost: $5-10/month + added complexity

2. **Better Face Detection (ML-based)**
   - Requires: TensorFlow/PyTorch + models
   - Benefit: More accurate face detection
   - Cost: Larger Docker image, slower processing

3. **Real-Time Progress Updates (WebSockets)**
   - Requires: WebSocket support
   - Benefit: Better UX than HTMX polling
   - Cost: Connection management complexity

4. **Batch Upload Queue (Background Workers)**
   - Requires: Cloud Tasks or Pub/Sub
   - Benefit: Handle large batches asynchronously
   - Cost: More infrastructure

5. **Email Beautifier Advanced Features**
   - Intelligent paragraph detection
   - Smart quote formatting
   - HTML preview alongside plain text
   - Cost: More regex complexity

---

## License

MIT

## Documentation

- **[User Guides](docs/)** - End-user instructions for each tool
  - [Banner Processor User Guide](docs/BANNER_PROCESSOR_USER_GUIDE.md)
- **[Technical Docs](docs/)** - Implementation details
  - [Architecture](docs/ARCHITECTURE.md)
  - [Banner Processor Technical](docs/BANNER_PROCESSOR_TECHNICAL.md)
  - [Email Beautifier Technical](docs/EMAIL_BEAUTIFIER.md) - Pipeline, design decisions, iterative workflow
  - [Deployment Guide](docs/DEPLOYMENT.md)
  - [Google Cloud Run Setup](docs/GOOGLE_CLOUD_RUN.md)
  - [Troubleshooting](docs/TROUBLESHOOTING.md)
- **[AI Agent Guide](docs/AI_AGENT_GUIDE.md)** - For AI assistants: how to make changes without breaking progress
- **[Changelog](CHANGELOG.md)** - Version history and updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with `uvicorn app.main:app --reload`
5. Ensure Docker builds successfully
6. Submit a pull request with clear description

**Development Workflow**:
```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

# Run locally
uvicorn app.main:app --reload --port 8000

# Test
python tests/test_playwright.py

# Build Docker
docker build -t luminate-cookbook:local .
docker run -p 8000:8000 luminate-cookbook:local
```
