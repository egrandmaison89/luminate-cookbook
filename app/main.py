"""
Luminate Cookbook - FastAPI Application

Main entry point for the FastAPI application.
"""

import os
import uuid
import tempfile
import shutil
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio

from app.config import settings
from app.models.schemas import (
    UploadStartResponse,
    TwoFactorRequest,
    TwoFactorResponse,
    UploadStatusResponse,
    UploadResult,
    BannerProcessResponse,
    BannerSettings,
    BannerPreviewResponse,
    ManualCrop,
    PageBuilderRequest,
    PageBuilderResponse,
    SessionState,
    EmailBeautifierRequest,
    EmailBeautifierResponse,
)
from app.services.browser_manager import browser_manager


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup: Start background cleanup task
    cleanup_task = asyncio.create_task(browser_manager.cleanup_loop())
    print(f"🚀 {settings.app_name} started")
    
    yield
    
    # Shutdown: Cancel cleanup task and close all sessions
    cleanup_task.cancel()
    await browser_manager.shutdown()
    print(f"👋 {settings.app_name} shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A collection of tools for working with Luminate Online",
    version="2.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


# =============================================================================
# HTML Page Routes
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with tool overview."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": settings.app_name,
    })


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Image uploader page."""
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "title": "Image Uploader",
        "max_file_size_mb": settings.max_upload_size_mb,
    })


@app.get("/banner", response_class=HTMLResponse)
async def banner_page(request: Request):
    """Banner processor page."""
    return templates.TemplateResponse("banner.html", {
        "request": request,
        "title": "Email Banner Processor",
    })


@app.get("/pagebuilder", response_class=HTMLResponse)
async def pagebuilder_page(request: Request):
    """PageBuilder decomposer page."""
    return templates.TemplateResponse("pagebuilder.html", {
        "request": request,
        "title": "PageBuilder Decomposer",
    })


@app.get("/email-beautifier", response_class=HTMLResponse)
async def email_beautifier_page(request: Request):
    """Email beautifier page."""
    return templates.TemplateResponse("email_beautifier.html", {
        "request": request,
        "title": "Plain Text Email Beautify",
    })


# =============================================================================
# Upload API Routes
# =============================================================================

@app.post("/upload/start", response_class=HTMLResponse)
async def upload_start_html(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    Start upload session and return HTML partial for HTMX.
    This is the endpoint the form actually hits.
    """
    # Validate files
    if not files:
        return templates.TemplateResponse("partials/upload_error.html", {
            "request": request,
            "error": "No files provided",
        })
    
    # Validate file sizes and types
    temp_dir = tempfile.mkdtemp()
    saved_files = []
    
    try:
        for file in files:
            # Check extension
            ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
            if ext not in settings.allowed_extensions:
                return templates.TemplateResponse("partials/upload_error.html", {
                    "request": request,
                    "error": f"Invalid file type: {file.filename}. Allowed: {', '.join(settings.allowed_extensions)}",
                })
            
            # Save to temp directory
            file_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            
            # Check size
            size_mb = len(content) / (1024 * 1024)
            if size_mb > settings.max_upload_size_mb:
                return templates.TemplateResponse("partials/upload_error.html", {
                    "request": request,
                    "error": f"File too large: {file.filename} ({size_mb:.1f}MB). Max: {settings.max_upload_size_mb}MB",
                })
            
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(file_path)
        
        # Create browser session and start login
        session_id, state, needs_2fa, message, error = await browser_manager.create_session(
            username=username,
            password=password,
            files=saved_files,
            temp_dir=temp_dir,
        )
        
        # Get full status to render template
        status = await browser_manager.get_session_status(session_id)
        
        # Return HTML partial
        return templates.TemplateResponse("partials/upload_status.html", {
            "request": request,
            **status,
        })
        
    except Exception as e:
        # Clean up on unexpected error
        shutil.rmtree(temp_dir, ignore_errors=True)
        return templates.TemplateResponse("partials/upload_error.html", {
            "request": request,
            "error": str(e),
        })


@app.post("/api/upload/start", response_model=UploadStartResponse)
async def upload_start(
    username: str = Form(...),
    password: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    Start an upload session.
    
    Creates a browser session, attempts login, and returns session_id.
    If 2FA is required, the session stays open waiting for the code.
    """
    # Validate files
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate file sizes and types
    temp_dir = tempfile.mkdtemp()
    saved_files = []
    
    try:
        for file in files:
            # Check extension
            ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
            if ext not in settings.allowed_extensions:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid file type: {file.filename}. Allowed: {settings.allowed_extensions}"
                )
            
            # Save to temp directory
            file_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            
            # Check size
            size_mb = len(content) / (1024 * 1024)
            if size_mb > settings.max_upload_size_mb:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large: {file.filename} ({size_mb:.1f}MB). Max: {settings.max_upload_size_mb}MB"
                )
            
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(file_path)
        
        # Create browser session and start login
        session_id, state, needs_2fa, message, error = await browser_manager.create_session(
            username=username,
            password=password,
            files=saved_files,
            temp_dir=temp_dir,
        )
        
        return UploadStartResponse(
            session_id=session_id,
            state=state,
            needs_2fa=needs_2fa,
            message=message,
            error=error,
        )
        
    except HTTPException:
        # Clean up on validation error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception as e:
        # Clean up on unexpected error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/2fa/{session_id}", response_class=HTMLResponse)
async def upload_2fa_html(
    request: Request,
    session_id: str,
    code: str = Form(...),
):
    """
    Submit 2FA code and return HTML partial for HTMX.
    """
    success, state, message, error = await browser_manager.submit_2fa(
        session_id=session_id,
        code=code,
    )
    
    # Get full status to render template
    status = await browser_manager.get_session_status(session_id)
    
    if status is None:
        return templates.TemplateResponse("partials/upload_error.html", {
            "request": request,
            "error": "Session not found or expired",
        })
    
    # Return HTML partial with updated status
    return templates.TemplateResponse("partials/upload_status.html", {
        "request": request,
        **status,
    })


@app.post("/api/upload/2fa/{session_id}", response_model=TwoFactorResponse)
async def upload_2fa(session_id: str, request: TwoFactorRequest):
    """
    Submit 2FA code for an existing session.
    
    The browser session is kept alive and the code is submitted
    to the same browser instance that initiated the login.
    """
    success, state, message, error = await browser_manager.submit_2fa(
        session_id=session_id,
        code=request.code,
    )
    
    return TwoFactorResponse(
        success=success,
        state=state,
        message=message,
        error=error,
    )


@app.get("/api/upload/status/{session_id}", response_model=UploadStatusResponse)
async def upload_status(session_id: str):
    """
    Get the current status of an upload session.
    
    Used for polling to check progress, 2FA status, and results.
    """
    status = await browser_manager.get_session_status(session_id)
    
    if status is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    return UploadStatusResponse(**status)


@app.delete("/api/upload/{session_id}")
async def upload_cancel(session_id: str):
    """
    Cancel and cleanup an upload session.
    """
    success = await browser_manager.cancel_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True, "message": "Session cancelled"}


# HTMX partial responses for upload status
@app.get("/api/upload/status/{session_id}/partial", response_class=HTMLResponse)
async def upload_status_partial(request: Request, session_id: str):
    """
    Return HTML partial for upload status (used by HTMX polling).
    """
    status = await browser_manager.get_session_status(session_id)
    
    if status is None:
        return templates.TemplateResponse("partials/upload_error.html", {
            "request": request,
            "error": "Session not found or expired",
        })
    
    return templates.TemplateResponse("partials/upload_status.html", {
        "request": request,
        **status,
    })


# =============================================================================
# Banner Processor API Routes
# =============================================================================

@app.post("/api/banner/preview")
async def banner_preview(
    file: UploadFile = File(...),
    width: int = Form(600),
    height: int = Form(340),
    quality: int = Form(82),
    crop_padding: float = Form(0.15),
):
    """
    Generate a crop preview for a single image.
    Returns the image with suggested crop coordinates.
    """
    from app.services.banner_processor import generate_crop_preview
    
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    settings_obj = BannerSettings(
        width=width,
        height=height,
        quality=quality,
        crop_padding=crop_padding,
    )
    
    try:
        content = await file.read()
        preview_data = generate_crop_preview(content, settings_obj)
        
        return BannerPreviewResponse(
            success=True,
            **preview_data,
            message="Preview generated successfully"
        )
    except Exception as e:
        return BannerPreviewResponse(
            success=False,
            error=str(e),
            message="Failed to generate preview"
        )


@app.post("/api/banner/process")
async def banner_process(
    files: List[UploadFile] = File(...),
    width: int = Form(600),
    height: int = Form(340),
    quality: int = Form(82),
    include_retina: bool = Form(True),
    filename_prefix: str = Form(""),
    crop_padding: float = Form(0.15),
    manual_crops: Optional[str] = Form(None),
):
    """
    Process uploaded images into email banners.
    Returns a ZIP file with processed images.
    
    Args:
        manual_crops: Optional JSON string mapping filename to crop coords
                     e.g., '{"image.jpg": {"x1": 0, "y1": 100, "x2": 600, "y2": 440}}'
    """
    from app.services.banner_processor import process_banners
    import json
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    settings_obj = BannerSettings(
        width=width,
        height=height,
        quality=quality,
        include_retina=include_retina,
        filename_prefix=filename_prefix,
        crop_padding=crop_padding,
    )
    
    # Parse manual crops if provided
    manual_crops_dict = None
    if manual_crops:
        try:
            manual_crops_dict = json.loads(manual_crops)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid manual_crops JSON")
    
    # Read file contents
    file_data = []
    for file in files:
        content = await file.read()
        file_data.append((file.filename, content))
    
    # Process banners
    try:
        zip_bytes, results = await process_banners(file_data, settings_obj, manual_crops_dict)
        
        # Return ZIP file
        zip_filename = f"{filename_prefix}_email_banners.zip" if filename_prefix else "email_banners.zip"
        
        return StreamingResponse(
            iter([zip_bytes]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PageBuilder Decomposer API Routes
# =============================================================================

@app.post("/api/pagebuilder/decompose")
async def pagebuilder_decompose(request: PageBuilderRequest):
    """
    Decompose a PageBuilder into its components.
    Returns a ZIP file with all nested PageBuilders.
    """
    from app.services.pagebuilder_service import decompose_pagebuilder
    
    try:
        zip_bytes, response_data = await decompose_pagebuilder(
            url_or_name=request.url_or_name,
            base_url=request.base_url,
            ignore_global_stylesheet=request.ignore_global_stylesheet,
        )
        
        if zip_bytes is None:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": response_data.get("error", "Unknown error")}
            )
        
        # Return ZIP file
        pagename = response_data.get("pagename", "pagebuilder")
        zip_filename = f"{pagename}_decomposed.zip"
        
        return StreamingResponse(
            iter([zip_bytes]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pagebuilder/analyze", response_model=PageBuilderResponse)
async def pagebuilder_analyze(request: PageBuilderRequest):
    """
    Analyze a PageBuilder structure without downloading.
    Returns hierarchy information for preview.
    """
    from app.services.pagebuilder_service import analyze_pagebuilder
    
    try:
        result = await analyze_pagebuilder(
            url_or_name=request.url_or_name,
            base_url=request.base_url,
            ignore_global_stylesheet=request.ignore_global_stylesheet,
        )
        return PageBuilderResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Email Beautifier API Routes
# =============================================================================

@app.post("/api/email-beautifier/process", response_model=EmailBeautifierResponse)
async def email_beautifier_process(request: EmailBeautifierRequest):
    """
    Beautify plain text email.
    
    Takes ugly plain text (from HTML email conversion) and returns
    beautifully formatted plain text with cleaned URLs and styled CTAs.
    """
    from app.services.email_beautifier import beautify_email
    
    try:
        if not request.raw_text or not request.raw_text.strip():
            return EmailBeautifierResponse(
                success=False,
                error="No text provided",
                message="Please enter some text to beautify"
            )
        
        beautified_text, stats = beautify_email(
            raw_text=request.raw_text,
            strip_tracking=request.strip_tracking,
            format_ctas=request.format_ctas,
            markdown_links=request.markdown_links,
        )
        
        return EmailBeautifierResponse(
            success=True,
            beautified_text=beautified_text,
            stats=stats,
            message="Email beautified successfully"
        )
    except Exception as e:
        return EmailBeautifierResponse(
            success=False,
            error=str(e),
            message="An error occurred while beautifying the email"
        )


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "active_sessions": browser_manager.active_session_count,
    }


# =============================================================================
# Run with uvicorn (for local development)
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
