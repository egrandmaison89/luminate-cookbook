# Changelog

All notable changes to Luminate Cookbook are documented in this file.

## [2.2.0] - 2026-02-12

### Improved - Plain Text Email Beautifier

**Content Preservation (Critical Fixes)**
- **Footer detection rewritten**: Footer now identified from bottom 50% of document. Primary trigger: line ending with " Logo" (e.g. "Dana-Farber Logo"). Fixes bug where body content was wrongly treated as footer and removed.
- **Visual break before footer**: Adds `═══` separator; removes social media links; keeps main org URL.

**Line Joining Enhancements**
- Join hyphenated words split across lines ("pre-" + "race", "In-" + "Memory")
- Join time ranges ("4:00" + "4:45 p.m.")
- Join phrase continuations ("from", "to", "and", "or" at line end)
- Relaxed incomplete-line threshold (70→85 chars)

**CTA Detection Improvements**
- Added fundraising CTAs: Donate, Donate Now, Give Now, Volunteer, Register
- **Strict CTA matching**: Phrases like "donate" and "volunteer" require ≤25 char line to avoid matching body copy ("You can donate to our cause")
- Pattern 3: Check previous non-empty line (skip blank lines) for CTA
- Max 50 chars for general CTAs to avoid "The event will sell out, so RSVP promptly!"

**Tracking Params**
- Added: aff, ref, ref_src, ref_cid, cmpid (affiliate/referral)

**CTA Visual Bounce**
- Blank lines before and after formatted CTAs (`>>> CTA: url <<<`)

**Documentation**
- Created `docs/EMAIL_BEAUTIFIER.md` — technical doc, pipeline, pitfalls, iterative workflow
- Created `docs/AI_AGENT_GUIDE.md` — guide for AI agents to build on progress without breaking
- Updated `docs/ARCHITECTURE.md` — accurate Email Beautifier section
- Updated `docs/README.md`, `DOCUMENTATION_SUMMARY.md` — links to new docs

**Testing**
- Added `tests/test_email_beautifier.py` (10 tests)
- Added `tests/fixtures/textemail.txt`, `textemail_expected.txt`
- Run: `PYTHONPATH=. python3 -m unittest tests.test_email_beautifier -v`

---

## [2.1.0] - 2026-01-30

### Added - Banner Processor Enhancement

**Intelligent Person Detection**
- MediaPipe Pose detection for full-body awareness (detects up to 5 people)
- Three-tier fallback system: MediaPipe → OpenCV face detection → Center crop
- Configurable crop padding (0-30%) around detected subjects

**Interactive Crop Preview**
- Two-workflow support: Preview & Adjust OR Auto-Process
- Cropper.js integration for drag-and-resize crop adjustments
- Real-time detection feedback (shows people/faces detected)
- Progress tracking for multiple images
- Manual crop override capability

**New API Endpoints**
- `POST /api/banner/preview` - Generate crop preview with detection info
- Enhanced `POST /api/banner/process` - Accepts manual crop coordinates

**UI Improvements**
- Crop padding slider with real-time preview
- Two-button interface: "Preview & Adjust Crops" | "Process All Images"
- Interactive modal with crop adjustment controls
- Success toast notifications

### Technical Changes
- Added `mediapipe>=0.10.9` dependency
- Enhanced `BannerSettings` schema with `crop_padding` and `detection_mode`
- New schemas: `BannerPreviewResponse`, `CropBox`, `ManualCrop`
- Updated `banner_processor.py` with person detection and smart crop algorithms
- Integrated Cropper.js v1.6.1 via CDN

### Documentation
- Created `docs/BANNER_PROCESSOR_TECHNICAL.md` - Technical implementation details
- Updated `docs/BANNER_PROCESSOR_USER_GUIDE.md` - User-friendly instructions
- Updated `README.md` - Banner processor feature highlights
- Consolidated documentation (removed temporary files)

### Testing
- Browser testing: All features verified working (10/10 tests passed)
- Performance: Preview workflow ~5-7s, Auto workflow ~2-3s
- Verified graceful fallback when MediaPipe GPU unavailable

---

## [2.0.0] - 2025-12-XX

### Major Rewrite - Streamlit to FastAPI Migration

**Why**: Streamlit's threading model made persistent browser sessions for 2FA impossible. FastAPI enables proper async browser session management.

### Added

**Image Uploader with 2FA Support**
- Server-side persistent browser sessions using Playwright
- Background browser session manager with automatic cleanup
- Real-time progress tracking via HTMX polling
- Session lifecycle management (10-minute timeout)
- Support for batch uploads with verification

**Email Banner Processor**
- OpenCV-powered face detection using Haar Cascades
- Smart crop region calculation to preserve faces
- Customizable dimensions and quality settings
- Retina-ready 2x versions for high-DPI displays
- ZIP download with processed variants

**PageBuilder Decomposer**
- Recursive component extraction from Luminate pages
- Hierarchical structure visualization
- No authentication required (public content)
- ZIP download with organized folder structure

**Plain Text Email Beautifier**
- URL tracking parameter stripping
- Intelligent CTA detection and formatting
- Markdown link conversion
- CSS block removal
- Line-break normalization

**Infrastructure**
- FastAPI backend with async support
- Jinja2 templates with HTMX for dynamic UI
- Docker containerization with Playwright dependencies
- Google Cloud Run deployment support
- Automated deployment via Cloud Build

### Changed
- Complete rewrite from Streamlit to FastAPI
- Browser automation now uses server-side sessions
- UI uses server-rendered templates instead of Streamlit widgets
- Deployment target changed from Streamlit Cloud to Google Cloud Run

### Technical Architecture
- Singleton browser session manager
- Thread pool execution for sync Playwright API
- Background cleanup task for expired sessions
- Concurrent session limiting (max 10)
- Graceful error handling and retry logic

---

## [1.x.x] - 2024-2025

### Streamlit Version (Deprecated)

Initial implementation using Streamlit Cloud. Had critical threading issues with 2FA that couldn't be resolved within Streamlit's architecture.

**Key limitations that led to rewrite**:
- Browser objects accessed from different threads
- Session state doesn't survive reruns
- No persistent browser sessions
- 2FA workflows impossible to implement reliably

---

## Future Roadmap

### Planned Features
- Batch preview for banner processor (grid view)
- Keyboard shortcuts for crop adjustment
- Session persistence across Cloud Run instances (Redis)
- WebSocket support for real-time progress
- ML-based face detection (TensorFlow/PyTorch)
- Authentication layer (Cloud IAP or Firebase Auth)
- Rate limiting and audit logging

### Under Consideration
- Background upload queue (Cloud Tasks)
- Email template generator
- A/B testing tools for email campaigns
- Analytics dashboard for upload history
