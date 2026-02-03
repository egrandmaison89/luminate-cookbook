"""
Pydantic schemas for API request/response validation.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class SessionState(str, Enum):
    """Browser session states."""
    INITIALIZING = "initializing"
    LOGIN = "login"
    AWAITING_2FA = "awaiting_2fa"
    AUTHENTICATED = "authenticated"
    UPLOADING = "uploading"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


# Upload Schemas

class UploadStartRequest(BaseModel):
    """Request to start an upload session."""
    username: str = Field(..., description="Luminate Online username")
    password: str = Field(..., description="Luminate Online password")
    # Files are handled via form data, not JSON


class UploadStartResponse(BaseModel):
    """Response after starting an upload session."""
    session_id: str = Field(..., description="Unique session identifier")
    state: SessionState = Field(..., description="Current session state")
    needs_2fa: bool = Field(default=False, description="Whether 2FA is required")
    message: str = Field(default="", description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if any")


class TwoFactorRequest(BaseModel):
    """Request to submit 2FA code."""
    code: str = Field(..., min_length=6, max_length=6, description="6-digit 2FA code")


class TwoFactorResponse(BaseModel):
    """Response after submitting 2FA code."""
    success: bool = Field(..., description="Whether 2FA was successful")
    state: SessionState = Field(..., description="Current session state")
    message: str = Field(default="", description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if any")


class UploadResult(BaseModel):
    """Result for a single file upload."""
    filename: str = Field(..., description="Original filename")
    success: bool = Field(..., description="Whether upload succeeded")
    url: Optional[str] = Field(default=None, description="URL of uploaded image")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class UploadStatusResponse(BaseModel):
    """Response for upload status check."""
    session_id: str = Field(..., description="Session identifier")
    state: SessionState = Field(..., description="Current session state")
    needs_2fa: bool = Field(default=False, description="Whether 2FA is required")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Upload progress 0-1")
    current_file: Optional[str] = Field(default=None, description="Currently uploading file")
    total_files: int = Field(default=0, description="Total files to upload")
    completed_files: int = Field(default=0, description="Files uploaded so far")
    results: List[UploadResult] = Field(default_factory=list, description="Upload results")
    message: str = Field(default="", description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if any")
    time_remaining_seconds: Optional[int] = Field(default=None, description="Seconds until session expires")


# Banner Processor Schemas

class BannerSettings(BaseModel):
    """Settings for banner processing."""
    width: int = Field(default=600, ge=100, le=2000, description="Output width in pixels")
    height: int = Field(default=340, ge=100, le=1000, description="Output height in pixels")
    quality: int = Field(default=90, ge=1, le=100, description="JPEG quality (higher = better color preservation)")
    include_retina: bool = Field(default=True, description="Include 2x retina version")
    filename_prefix: str = Field(default="", description="Prefix for output filenames")
    crop_padding: float = Field(default=0.15, ge=0.0, le=0.3, description="Padding around detected subjects (0.0-0.3)")
    detection_mode: str = Field(default="auto", description="Detection mode: auto, face_only, manual")


class BannerProcessRequest(BaseModel):
    """Request to process banner images."""
    settings: BannerSettings = Field(default_factory=BannerSettings)
    # Files are handled via form data


class BannerResult(BaseModel):
    """Result for a single banner."""
    filename: str
    width: int
    height: int
    size_kb: float
    faces_detected: int
    people_detected: int = Field(default=0, description="Number of people detected")


class BannerProcessResponse(BaseModel):
    """Response after processing banners."""
    success: bool
    results: List[BannerResult] = Field(default_factory=list)
    total_files: int = 0
    message: str = ""
    error: Optional[str] = None


class CropBox(BaseModel):
    """Crop box coordinates."""
    x1: int = Field(..., description="Left coordinate")
    y1: int = Field(..., description="Top coordinate")
    x2: int = Field(..., description="Right coordinate")
    y2: int = Field(..., description="Bottom coordinate")
    width: int = Field(..., description="Crop width")
    height: int = Field(..., description="Crop height")


class ImageDimensions(BaseModel):
    """Image dimensions."""
    width: int
    height: int


class BannerPreviewResponse(BaseModel):
    """Response for banner crop preview."""
    success: bool = Field(..., description="Whether preview generation succeeded")
    image_base64: str = Field(default="", description="Base64 encoded image with data URI")
    crop_box: Optional[CropBox] = Field(default=None, description="Suggested crop coordinates")
    people_detected: int = Field(default=0, description="Number of people detected")
    faces_detected: int = Field(default=0, description="Number of faces detected")
    dimensions: Optional[ImageDimensions] = Field(default=None, description="Original image dimensions")
    target_dimensions: Optional[ImageDimensions] = Field(default=None, description="Target output dimensions")
    message: str = Field(default="", description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if any")


class ManualCrop(BaseModel):
    """Manual crop coordinates for a file."""
    filename: str = Field(..., description="Filename to apply crop to")
    x1: int = Field(..., ge=0, description="Left coordinate")
    y1: int = Field(..., ge=0, description="Top coordinate")
    x2: int = Field(..., gt=0, description="Right coordinate")
    y2: int = Field(..., gt=0, description="Bottom coordinate")


# PageBuilder Decomposer Schemas

class PageBuilderRequest(BaseModel):
    """Request to decompose a PageBuilder."""
    url_or_name: str = Field(..., description="PageBuilder URL or name")
    base_url: str = Field(default="https://danafarber.jimmyfund.org", description="Luminate base URL")
    ignore_global_stylesheet: bool = Field(default=True, description="Ignore reus_dm_global_stylesheet")


class PageBuilderComponent(BaseModel):
    """A single PageBuilder component."""
    name: str
    is_included: bool
    children: List[str] = Field(default_factory=list)


class PageBuilderResponse(BaseModel):
    """Response after decomposing PageBuilder."""
    success: bool
    pagename: str = ""
    total_components: int = 0
    included_components: int = 0
    excluded_components: int = 0
    hierarchy: Dict[str, List[str]] = Field(default_factory=dict)
    components: List[PageBuilderComponent] = Field(default_factory=list)
    message: str = ""
    error: Optional[str] = None


# Email Beautifier Schemas

class EmailBeautifierRequest(BaseModel):
    """Request to beautify plain text email."""
    raw_text: str = Field(..., description="Raw plain text email to beautify")
    strip_tracking: bool = Field(default=True, description="Strip tracking parameters from URLs")
    format_ctas: bool = Field(default=True, description="Format CTAs with arrow styling")
    markdown_links: bool = Field(default=True, description="Convert links to markdown format")


class EmailBeautifierResponse(BaseModel):
    """Response after beautifying email text."""
    success: bool = Field(..., description="Whether beautification succeeded")
    beautified_text: str = Field(default="", description="The beautified email text")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Statistics about changes made")
    message: str = Field(default="", description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if any")
