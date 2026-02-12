# Luminate Cookbook - Architecture Documentation

**Version**: 2.0 (FastAPI)  
**Last Updated**: January 29, 2026  
**Status**: Production

---

## Executive Summary

Luminate Cookbook is a production-grade web application providing four specialized tools for Luminate Online administrators. The application was architected to solve a critical browser automation challenge: enabling two-factor authentication in a serverless environment.

**The Core Innovation**: Persistent server-side browser sessions that survive HTTP request boundaries, enabling seamless 2FA workflows that were impossible with traditional session-based architectures.

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Layer                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Browser (Users)                                              │  │
│  │  - HTML/CSS/JavaScript                                        │  │
│  │  - HTMX for dynamic updates                                   │  │
│  │  - Form submissions                                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Google Cloud Run (Serverless)                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (Python 3.11)                           │  │
│  │  ├─ HTTP Routes (Jinja2 templates)                           │  │
│  │  ├─ API Routes (JSON responses)                              │  │
│  │  ├─ HTMX Partial Routes (HTML fragments)                     │  │
│  │  └─ Health Check Endpoint                                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                               │                                      │
│                               ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Business Logic Layer                                         │  │
│  │  ├─ BrowserSessionManager (singleton)                        │  │
│  │  │   └─ Persistent Playwright sessions                       │  │
│  │  ├─ BannerProcessor (OpenCV face detection)                  │  │
│  │  ├─ EmailBeautifier (regex text processing)                  │  │
│  │  └─ PageBuilderService (HTML parsing)                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                               │                                      │
│                               ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Infrastructure Layer                                         │  │
│  │  ├─ Playwright Chromium (browser automation)                 │  │
│  │  ├─ OpenCV (computer vision)                                 │  │
│  │  ├─ Pillow (image processing)                                │  │
│  │  └─ Requests (HTTP client)                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Luminate Online (External)                        │
│  - Admin login (with 2FA)                                           │
│  - Image Library upload                                             │
│  - PageBuilder content (public)                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions & Rationale

### 1. FastAPI vs. Streamlit

**Decision**: Migrate from Streamlit to FastAPI  
**Date**: January 2026  
**Owner**: Architecture Team

**Context**:
Original application built with Streamlit encountered a critical bug: `RuntimeError: cannot switch to a different thread` when attempting 2FA workflows. Streamlit's session state is request-scoped and thread-local, causing browser objects to be accessed from different threads during page reruns.

**Analysis**:

| Framework | Session Model | Threading | 2FA Support | Deployment |
|-----------|---------------|-----------|-------------|------------|
| Streamlit | Request-scoped, thread-local | Multi-threaded reruns | ❌ Breaks | Streamlit Cloud (limited) |
| FastAPI | Server-side, persistent | Async single-thread + thread pool | ✅ Works | Docker (full control) |

**Decision Rationale**:
1. **Technical Necessity**: 2FA is a hard requirement; Streamlit's architecture makes it impossible
2. **Production Readiness**: FastAPI is designed for production APIs with proper async support
3. **Flexibility**: Full control over session lifecycle and state management
4. **Performance**: Async-first design handles concurrent requests better
5. **Developer Experience**: Automatic API documentation, better error handling

**Trade-offs Accepted**:
- ❌ More complex codebase (546 lines main.py vs ~200 lines Streamlit)
- ❌ Manual template management (Jinja2 vs Streamlit's declarative UI)
- ✅ Complete control over session lifecycle
- ✅ Proper async/await for I/O operations
- ✅ Production-grade deployment

**Alternatives Considered**:
- **Flask**: Considered but rejected (no async support, less modern)
- **Django**: Too heavy for our needs (ORM, admin, migrations unnecessary)
- **Streamlit with workarounds**: Attempted Redis session storage, but Playwright objects not serializable

**Outcome**: Migration successful, 2FA works reliably, all four tools operational

---

### 2. Persistent Browser Sessions

**Decision**: Implement server-side browser session manager as singleton  
**Component**: `BrowserSessionManager` (738 lines)

**Architecture**:

```python
class BrowserSessionManager:
    """
    Singleton managing browser sessions across HTTP requests.
    
    Key innovation: Sessions persist in memory, not in client state.
    """
    
    def __init__(self):
        self._sessions: Dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()
    
    # Sessions identified by UUID, accessible across requests
    async def create_session(self, username, password, files, temp_dir):
        session_id = str(uuid.uuid4())
        session = BrowserSession(
            id=session_id,
            playwright=sync_playwright().start(),
            browser=playwright.chromium.launch(),
            # ... more initialization
        )
        self._sessions[session_id] = session  # ← Persists in memory
        return session_id
    
    async def submit_2fa(self, session_id, code):
        session = self._sessions.get(session_id)  # ← Same browser instance!
        # Submit code to page that's still open
        return await self._submit_2fa_code(session, code)
```

**Why This Works**:
1. **Memory Persistence**: Dict stored in module-level singleton, survives across requests
2. **UUID Identification**: Client receives session_id, uses it to reference same browser
3. **Thread Safety**: asyncio.Lock prevents race conditions
4. **Lifecycle Management**: Automatic cleanup after 10 minutes or completion

**Alternative Approaches Rejected**:

1. **Redis/Memorystore Session Storage**
   - ❌ Playwright browser objects not serializable
   - ❌ Would need to recreate browser on each request (defeats purpose)
   - ✅ Could work for session metadata with sticky sessions

2. **Sticky Sessions via Load Balancer**
   - ❌ Cloud Run doesn't guarantee session affinity
   - ❌ Still need shared state for multi-instance deployments
   - ⚠️ Forced to single-instance deployment currently

3. **WebSockets for Long-Lived Connection**
   - ❌ Overly complex for our needs
   - ❌ Doesn't solve persistence problem (browser still server-side)
   - ✅ Could improve UX for real-time progress

**Current Limitation**: Single-instance deployment required (sessions not shared across instances)

**Future Enhancement**: Add Redis for session metadata + instance affinity headers

---

### 3. HTMX for Dynamic UI

**Decision**: Use HTMX for dynamic updates instead of React/Vue SPA  
**Rationale**: Simple, server-rendered architecture

**Benefits**:
- ✅ No build step required
- ✅ Progressive enhancement (works without JS)
- ✅ Minimal JavaScript code
- ✅ Server-side rendering (better SEO, simpler debugging)
- ✅ Instant page loads (no SPA bundle download)

**Trade-offs**:
- ❌ Less rich interactions than full SPA
- ❌ Requires HTML partials design pattern
- ✅ Good enough for our admin tool use case

**Implementation Example**:

```html
<!-- Button triggers HTMX request -->
<form hx-post="/upload/start" 
      hx-target="#status-container"
      hx-swap="innerHTML">
    <!-- Form fields -->
</form>

<!-- Status container updated by HTMX -->
<div id="status-container">
    <!-- Replaced by server-rendered HTML partial -->
</div>

<!-- Polling for progress -->
<div hx-get="/api/upload/status/{session_id}/partial"
     hx-trigger="every 2s"
     hx-swap="innerHTML">
    <!-- Auto-updates every 2 seconds -->
</div>
```

**Why Not a Full SPA?**:
- Admin tool, not public-facing app
- Users value reliability > fancy UI
- Faster development iteration
- Easier to maintain (one technology stack)

---

### 4. OpenCV Haar Cascade for Face Detection

**Decision**: Use Haar Cascade instead of ML-based detection  
**Component**: `banner_processor.py`

**Trade-off Analysis**:

| Approach | Accuracy | Speed | Dependencies | Complexity |
|----------|----------|-------|--------------|------------|
| **Haar Cascade (chosen)** | ~85% | 50-100ms | OpenCV only | Low |
| MTCNN | ~95% | 500-1000ms | TensorFlow | Medium |
| YOLO | ~98% | 200-500ms | PyTorch | High |
| MediaPipe | ~90% | 100-300ms | MediaPipe | Medium |

**Decision Rationale**:
1. **Speed**: Email banner processing is batch operation - faster = better UX
2. **Dependencies**: OpenCV already required for image operations
3. **Accuracy**: 85% good enough (users can retry if crop poor)
4. **Docker Size**: ML models add 500MB+ to image
5. **Resource Usage**: No GPU needed

**Acceptable Failure Modes**:
- Profile shots: Falls back to center crop (acceptable)
- Poor lighting: May miss faces (user can adjust brightness)
- Multiple faces: Algorithm preserves all detected faces
- False positives: Better than false negatives (won't cut off heads)

**Future Enhancement**: Add option for ML-based detection via API flag

---

### 5. Cloud Run Deployment

**Decision**: Deploy to Google Cloud Run instead of VMs or Kubernetes  
**Rationale**: Serverless simplicity with full Docker support

**Comparison**:

| Platform | Cost | Scalability | Complexity | Docker | Startup Time |
|----------|------|-------------|------------|--------|--------------|
| **Cloud Run** (chosen) | $0-5/mo | Auto 0→N | Low | ✅ Full | ~20-30s |
| GCE VM | $20-50/mo | Manual | Medium | ✅ Full | Always on |
| GKE | $75+/mo | Auto | High | ✅ Full | ~5-10s |
| App Engine | $20+/mo | Auto | Low | ⚠️ Limited | ~10-20s |
| Streamlit Cloud | $0 | Auto | Very Low | ❌ None | ~30s |

**Decision Factors**:
1. **Cost**: Free tier covers typical usage (2M requests/month)
2. **Docker Support**: Playwright needs full system dependencies
3. **Scalability**: Auto-scales based on traffic (important for bursty admin usage)
4. **Simplicity**: No cluster management like Kubernetes
5. **HTTPS**: Automatic SSL certificates

**Configuration Choices**:

```yaml
resources:
  limits:
    memory: 2Gi          # Minimum for Chromium (200-400MB per session)
    cpu: 2               # Faster page loads, better concurrency
  
execution:
  timeout: 600s          # 10 minutes for 2FA workflow
  maxInstances: 10       # Cost control + prevents overload
  minInstances: 0        # Scale to zero when idle (cost efficiency)

container:
  port: 8000
  env:
    - PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
```

**Why These Values**:
- **2Gi memory**: Buffer for 10 concurrent sessions (10 × 200MB) + overhead
- **2 CPU**: Diminishing returns beyond 2 cores for our workload
- **600s timeout**: Allows users time to find authenticator app
- **maxInstances=10**: Prevents runaway costs while serving multiple teams

**Cold Start Optimization**:
- Docker image: ~1.2GB (acceptable for cold start)
- Startup time: ~20-30 seconds (Playwright browser download is large)
- Mitigation: Cloud Scheduler keep-alive pings every 5 minutes (free tier)

---

### 6. Security Posture

**Decision**: Minimal authentication, focus on credential protection  
**Rationale**: Internal admin tool, not public-facing

**What We Secure**:

1. **Credentials**:
   - ✅ Never logged
   - ✅ Stored only in memory during session
   - ✅ Cleared on session cleanup
   - ✅ Transmitted over HTTPS only

2. **Browser Sessions**:
   - ✅ UUID-based (unguessable)
   - ✅ Automatic 10-minute timeout
   - ✅ Isolated per user
   - ✅ Explicit cleanup on error

3. **Uploaded Files**:
   - ✅ Temp directory with unique paths
   - ✅ Automatic cleanup after upload
   - ✅ Not persisted to disk

4. **2FA Codes**:
   - ✅ Never logged
   - ✅ Transmitted securely
   - ✅ Single-use (verified then discarded)

**What We Don't Secure** (by design):

1. **App Access**:
   - ⚠️ No authentication required to access app
   - ⚠️ Anyone with URL can use tools
   - ⚠️ Rationale: Internal network, trusted users

2. **Rate Limiting**:
   - ⚠️ No application-level rate limits
   - ⚠️ Cloud Run provides DDoS protection
   - ⚠️ Could add if abuse detected

3. **Audit Logging**:
   - ⚠️ No permanent audit trail
   - ⚠️ Cloud Run logs retained 30 days
   - ⚠️ Would require database for permanent storage

**Threat Model**:

| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| Credential theft | Low | High | HTTPS, memory-only storage |
| Session hijacking | Low | Medium | UUID sessions, timeouts |
| DDoS | Medium | Medium | Cloud Run auto-scaling, rate limiting |
| Malicious uploads | Low | Low | Sandboxed processing |
| Data exfiltration | Low | Medium | No persistent storage |

**Production Recommendations**:
1. Add Cloud Identity-Aware Proxy (IAP) for auth
2. Implement rate limiting with Redis
3. Add structured audit logging to BigQuery
4. Use Secret Manager for sensitive config

---

## Component Deep Dive

### BrowserSessionManager

**Purpose**: Manage lifecycle of Playwright browser sessions with 2FA support

**Key Methods**:

```python
async def create_session(username, password, files, temp_dir) -> Tuple:
    """
    Create browser session and attempt login.
    
    Returns: (session_id, state, needs_2fa, message, error)
    
    If needs_2fa=True, browser stays open waiting for code.
    """

async def submit_2fa(session_id, code) -> Tuple:
    """
    Submit 2FA code to existing session.
    
    Returns: (success, state, message, error)
    
    Uses same browser instance that initiated login.
    """

async def get_session_status(session_id) -> Optional[Dict]:
    """Poll session for current state, progress, results."""

async def cancel_session(session_id) -> bool:
    """Cancel and cleanup session resources."""

async def cleanup_loop():
    """Background task to cleanup expired sessions every 30s."""
```

**Session Lifecycle**:

```
INITIALIZING → LOGIN → AWAITING_2FA → AUTHENTICATED → UPLOADING → DONE
                ↓                          ↓
              ERROR ←―――――――――――――――――――――┘
```

**Anti-Detection Techniques**:

1. **Realistic Browser Fingerprint**:
   ```python
   context = browser.new_context(
       user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
       viewport={'width': 1920, 'height': 1080},
       locale='en-US',
       timezone_id='America/New_York',
   )
   ```

2. **JavaScript Injection**:
   ```javascript
   Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
   window.chrome = { runtime: {} };
   ```

3. **Human-Like Typing**:
   ```python
   for char in username:
       input.type(char, delay=random.randint(50, 150))  # 50-150ms per keystroke
   page.wait_for_timeout(random.randint(200, 500))      # 200-500ms between actions
   ```

**Resource Management**:
- Memory: ~200-400MB per session
- Timeout: 10 minutes (configurable)
- Max concurrent: 10 sessions (configurable)
- Cleanup: Automatic on timeout, error, or completion

---

### BannerProcessor

**Purpose**: Convert photos to email banners with intelligent face-aware cropping

**Algorithm**:

```
1. Load image (PIL)
2. Detect faces (OpenCV Haar Cascade)
3. Calculate safe crop region:
   - If faces detected: Preserve all faces with 50% head padding
   - If no faces: Center crop
4. Crop image to target aspect ratio
5. Resize to target dimensions (Lanczos resampling)
6. If retina enabled: Generate 2x version
7. Save as JPEG with quality setting
8. Package in ZIP file
```

**Face Detection Parameters**:
- `scaleFactor=1.1`: Balance between speed and accuracy
- `minNeighbors=5`: Reduces false positives
- `minSize=(30, 30)`: Ignore tiny face detections

**Crop Region Calculation**:
```python
def calculate_safe_crop_region(img_width, img_height, faces, target_aspect):
    if faces:
        # Find top-most face (with 50% padding above)
        min_face_y = min(face.y - face.height * 0.5 for face in faces)
        # Find bottom-most face
        max_face_bottom = max(face.y + face.height for face in faces)
        # Center crop region around face area
        crop_top = center_vertically(min_face_y, max_face_bottom, target_height)
    else:
        # Fallback to center crop
        crop_top = (img_height - target_height) / 2
    
    return (0, crop_top, img_width, crop_top + target_height)
```

**Output Specifications**:
- Standard: 600×340px @ 82% JPEG quality (~50-100KB)
- Retina: 1200×680px @ 82% JPEG quality (~150-300KB)
- Format: JPEG (best size/quality for email)
- Color space: RGB (sRGB for web)

---

### EmailBeautifier

**Purpose**: Transform ugly HTML-to-plaintext emails (from marketing platforms like Luminate) into readable plain text. Primary use case: fundraising emails.

**Full documentation**: See [docs/EMAIL_BEAUTIFIER.md](EMAIL_BEAUTIFIER.md) for implementation details, pitfalls, and iterative change workflow.

**Processing Pipeline**:

```
1. Strip CSS blocks (styles, @media queries)
2. Detect and extract preview text (header)
3. Join broken lines (hyphenated words, time ranges, mid-sentence breaks)
4. Detect CTAs (standalone phrases followed by URL)
5. Format CTAs with >>> arrows <<< and visual bounce
6. Clean tracking parameters from URLs (utm_*, aff, s_src, etc.)
7. Convert remaining links to markdown (optional)
8. Simplify footer (identify from "X Logo" in bottom half; add visual break; remove social links)
9. Normalize whitespace
10. Add preview banner at top
```

**Footer detection**: Footer starts at "X Logo" (e.g. "Dana-Farber Logo") in the **bottom 50%** of the document. Social links removed; main org URL preserved. Fallbacks: 2+ consecutive social labels, or 3+ consecutive URLs.

**CTA detection**: Standalone phrases (≤50 chars; ≤25 for donate/volunteer/give now) followed by URL. Avoids body copy like "The event will sell out, so RSVP promptly!"

**URL cleaning**: Strips utm_*, aff, ref, s_src, fbclid, gclid, mc_cid, mc_eid, etc.

---

### PageBuilderService

**Purpose**: Extract nested PageBuilder components from Luminate pages

**Delegation Pattern**:
This is a thin wrapper around `lib/pagebuilder_decomposer_lib.py`, which contains the core parsing logic:

```python
async def decompose_pagebuilder(url_or_name, base_url, ignore_global_stylesheet):
    workflow = HierarchicalLuminateWorkflow(base_url=base_url)
    
    # Extract pagename from URL or use directly
    pagename = workflow.extract_pagename_from_url(url_or_name)
    
    # Recursively decompose
    files, inclusion_status, hierarchy = workflow.decompose_pagebuilder(
        pagename,
        ignore_pagebuilders=["reus_dm_global_stylesheet"] if ignore_global_stylesheet else []
    )
    
    # Package as ZIP
    return create_zip(files), metadata
```

**Parsing Strategy**:
1. Fetch root PageBuilder HTML
2. Parse for `<pb:pagebuilder>` tags
3. Recursively fetch nested PageBuilders
4. Build hierarchy tree
5. Generate file structure (folders for nested components)

**Output Structure**:
```
root_pagebuilder.html
└── components/
    ├── nested_component1.html
    ├── nested_component2.html
    └── deeply_nested/
        └── component3.html
```

---

## Deployment Architecture

### Docker Build Strategy

**Multi-Stage Build** (not currently used, but recommended):

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y build-essential
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
# Copy wheels from builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

# Install Playwright system dependencies
RUN apt-get update && apt-get install -y [...]
RUN python -m playwright install chromium
```

**Current Build** (single-stage):
- Base: `python:3.11-slim`
- System packages: 30+ libraries for Chromium
- Python packages: `pip install -r requirements.txt`
- Playwright: `playwright install chromium`
- Total size: ~1.2GB
- Build time: ~5-8 minutes

### Cloud Run Configuration

**Current Settings**:
```yaml
Service: luminate-cookbook
Region: us-central1

Container:
  Image: gcr.io/PROJECT_ID/luminate-cookbook:latest
  Port: 8000
  
Resources:
  Memory: 2Gi
  CPU: 2
  
Scaling:
  minInstances: 0       # Scale to zero when idle
  maxInstances: 10      # Cost control
  
Execution:
  Timeout: 600s         # 10 minutes for 2FA
  Concurrency: 80       # Default Cloud Run setting
  
Environment:
  PLAYWRIGHT_BROWSERS_PATH: /ms-playwright
  PORT: 8000
```

**Cost Analysis** (as of January 2026):

| Resource | Price | Usage | Monthly Cost |
|----------|-------|-------|--------------|
| Requests | $0.40/million | ~50K | $0.02 |
| CPU | $0.00002400/GB-sec | ~10K GB-sec | $0.24 |
| Memory | $0.00000250/GB-sec | ~80K GB-sec | $0.20 |
| **Total** | | | **~$0.50/month** |

**Free Tier**: 2M requests/month covers typical usage

---

## Performance Characteristics

### Benchmarks

**Cold Start** (container startup):
- Docker pull: ~5-10 seconds
- Python import: ~2-3 seconds
- Playwright browser: ~5-10 seconds
- **Total**: ~20-30 seconds

**Warm Requests**:
- Health check (`/health`): <10ms
- Page render (`/upload`): ~50-100ms
- API call (no browser): ~100-200ms

**Browser Operations**:
- Session creation: ~2-3 seconds
- Login attempt: ~5-8 seconds
- 2FA submission: ~3-5 seconds
- Single image upload: ~5-10 seconds

**Image Processing**:
- Face detection: ~50-100ms per image
- Resize + crop: ~100-200ms per image
- Retina generation: +100ms
- **Total**: ~300-500ms per image

### Bottlenecks

1. **Cold starts** (20-30s)
   - Mitigation: Cloud Scheduler keep-alive OR min-instances=1

2. **Luminate network I/O** (variable, 2-10s per upload)
   - Mitigation: Retry logic, verification

3. **Browser automation** (sequential, not parallelizable per session)
   - Mitigation: Multiple concurrent sessions supported

4. **Face detection** (CPU-bound, 50-100ms per image)
   - Acceptable: Fast enough for batch processing

---

## Monitoring & Observability

### Metrics Available

**Cloud Run Metrics**:
- Request count, latency (p50, p95, p99)
- Instance count (active, idle)
- CPU utilization (%)
- Memory utilization (%)
- Container startup time
- Error rate (5xx responses)

**Custom Metrics** (via `/health`):
```json
{
  "status": "healthy",
  "app": "Luminate Cookbook",
  "active_sessions": 3
}
```

**Logs**:
- Structured logs via Cloud Logging
- Request logs (automatic)
- Application logs (print statements)
- Error traces (automatic)

### Alerting Recommendations

**Critical Alerts**:
1. Error rate >5% (application failure)
2. Memory usage >90% (risk of OOM)
3. Active sessions >8 (approaching limit)

**Warning Alerts**:
1. P95 latency >30s (performance degradation)
2. Cold start >45s (infrastructure issue)
3. Request rate >100/minute (unusual traffic)

---

## Security Model

### Threat Surface

**External Attack Vectors**:
1. ✅ **DDoS**: Mitigated by Cloud Run auto-scaling
2. ✅ **Credential interception**: HTTPS required
3. ⚠️ **Session hijacking**: UUID-based, timeout protection
4. ⚠️ **Malicious file uploads**: Sandboxed processing, no execution

**Internal Risk Factors**:
1. ⚠️ **No authentication**: Anyone with URL can use
2. ⚠️ **Session state in memory**: Lost on instance restart
3. ⚠️ **No audit trail**: Can't track who uploaded what
4. ✅ **Credential exposure**: Never logged or persisted

### Compliance Considerations

**Data Handling**:
- Credentials: In-memory only, cleared on cleanup
- Uploaded files: Temporary, deleted after processing
- Browser sessions: Isolated, automatic timeout
- Logs: No sensitive data logged

**Recommendations for Regulated Environments**:
1. Add authentication (Cloud IAP, OAuth)
2. Implement audit logging (BigQuery, Cloud Logging)
3. Add session encryption (if persisting to Redis)
4. Enable VPC connector (private network access)
5. Add data retention policies

---

## Future Roadmap

### Short-Term Improvements

1. **Multi-Instance Session Persistence** (High Priority)
   - Problem: Sessions lost when request routes to different instance
   - Solution: Redis/Memorystore for session metadata + sticky sessions
   - Effort: 2-3 days
   - Impact: Enables scaling beyond single instance

2. **WebSocket Progress Updates** (Medium Priority)
   - Problem: HTMX polling is inefficient
   - Solution: WebSocket endpoint for real-time updates
   - Effort: 1-2 days
   - Impact: Better UX, reduced request count

3. **Improved Face Detection** (Low Priority)
   - Problem: Haar Cascade misses some faces
   - Solution: Add ML-based detection (MediaPipe or MTCNN)
   - Effort: 2-3 days
   - Impact: Higher accuracy, slower processing

### Long-Term Enhancements

1. **Queue-Based Upload Processing**
   - Use Cloud Tasks for asynchronous batch uploads
   - Decouple upload from HTTP request lifecycle
   - Better for large batches (100+ images)

2. **Advanced Email Beautifier**
   - AI-powered paragraph detection
   - Smart quote formatting
   - HTML preview generation

3. **PageBuilder Visual Editor**
   - WYSIWYG editing of PageBuilder components
   - Live preview of changes
   - Version control and diffing

4. **Admin Dashboard**
   - Usage statistics
   - Active session monitoring
   - Error tracking

---

## Appendix

### Glossary

- **2FA**: Two-Factor Authentication
- **Cold Start**: Time to start a container from scratch
- **HTMX**: Library for AJAX without writing JavaScript
- **Playwright**: Browser automation library
- **Session Persistence**: Keeping session state across requests
- **Sticky Sessions**: Routing requests to same instance

### References

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Playwright Documentation: https://playwright.dev/
- Google Cloud Run: https://cloud.google.com/run/docs
- HTMX: https://htmx.org/

### Change Log

- **2026-01-29**: Initial FastAPI architecture
- **2026-01-29**: Added Email Beautifier tool
- **2026-01-29**: Documentation update with architecture decisions

---

**End of Architecture Documentation**
