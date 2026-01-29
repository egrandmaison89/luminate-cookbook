"""
Application configuration settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App settings
    app_name: str = "Luminate Cookbook"
    debug: bool = False
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Browser session settings
    session_timeout_seconds: int = 600  # 10 minutes
    max_2fa_wait_seconds: int = 90  # 90 seconds for 2FA
    max_concurrent_sessions: int = 10
    
    # Upload settings
    max_upload_size_mb: int = 10
    allowed_extensions: set = {"jpg", "jpeg", "png", "gif"}
    
    # Luminate URLs
    luminate_login_url: str = "https://secure2.convio.net/dfci/admin/AdminLogin"
    luminate_image_library_url: str = "https://secure2.convio.net/dfci/admin/ImageLibrary"
    luminate_base_url: str = "https://danafarber.jimmyfund.org"
    luminate_image_base_url: str = "https://danafarber.jimmyfund.org/images/content/pagebuilder/"
    
    # Playwright settings
    playwright_headless: bool = True
    playwright_browsers_path: Optional[str] = os.environ.get(
        "PLAYWRIGHT_BROWSERS_PATH",
        os.path.expanduser("~/.cache/ms-playwright")
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars not defined in Settings


# Global settings instance
settings = Settings()
