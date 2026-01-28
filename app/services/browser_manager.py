"""
Browser Session Manager for Luminate Cookbook.

Manages Playwright browser sessions with proper lifecycle handling.
This is the key component that solves the 2FA threading issue by keeping
browser sessions alive as persistent server-side objects.
"""

import asyncio
import uuid
import time
import shutil
import random
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from app.config import settings
from app.models.schemas import SessionState, UploadResult


@dataclass
class BrowserSession:
    """Represents a browser session with all its state."""
    id: str
    username: str
    state: SessionState
    created_at: float
    files_to_upload: List[str]
    temp_dir: str
    
    # Playwright objects (set after creation)
    playwright: Any = None
    browser: Any = None
    context: Any = None
    page: Any = None
    
    # Progress tracking
    current_file_index: int = 0
    results: List[UploadResult] = field(default_factory=list)
    
    # Messages
    message: str = ""
    error: Optional[str] = None
    
    @property
    def needs_2fa(self) -> bool:
        return self.state == SessionState.AWAITING_2FA
    
    @property
    def progress(self) -> float:
        if not self.files_to_upload:
            return 0.0
        return self.current_file_index / len(self.files_to_upload)
    
    @property
    def time_remaining_seconds(self) -> int:
        elapsed = time.time() - self.created_at
        remaining = settings.session_timeout_seconds - elapsed
        return max(0, int(remaining))
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > settings.session_timeout_seconds


class BrowserSessionManager:
    """
    Manages browser sessions for Luminate uploads.
    
    Key features:
    - Sessions persist in memory, surviving HTTP request boundaries
    - Each session owns its Playwright browser instance
    - 2FA can be submitted to an existing session
    - Automatic cleanup of expired sessions
    """
    
    def __init__(self):
        self._sessions: Dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()
    
    @property
    def active_session_count(self) -> int:
        return len(self._sessions)
    
    async def create_session(
        self,
        username: str,
        password: str,
        files: List[str],
        temp_dir: str,
    ) -> Tuple[str, SessionState, bool, str, Optional[str]]:
        """
        Create a new browser session and attempt login.
        
        Returns:
            Tuple of (session_id, state, needs_2fa, message, error)
        """
        session_id = str(uuid.uuid4())
        
        # Create session object
        session = BrowserSession(
            id=session_id,
            username=username,
            state=SessionState.INITIALIZING,
            created_at=time.time(),
            files_to_upload=files,
            temp_dir=temp_dir,
            message="Initializing browser session...",
        )
        
        async with self._lock:
            # Check max sessions
            if len(self._sessions) >= settings.max_concurrent_sessions:
                return (
                    session_id,
                    SessionState.ERROR,
                    False,
                    "",
                    "Maximum concurrent sessions reached. Please try again later.",
                )
            self._sessions[session_id] = session
        
        # Initialize browser in a thread pool (Playwright is sync)
        try:
            await self._initialize_browser(session)
            session.state = SessionState.LOGIN
            session.message = "Logging in to Luminate Online..."
            
            # Attempt login
            needs_2fa, error = await self._perform_login(session, username, password)
            
            if error:
                session.state = SessionState.ERROR
                session.error = error
                return (session_id, session.state, False, "", error)
            
            if needs_2fa:
                session.state = SessionState.AWAITING_2FA
                session.message = "Two-factor authentication required. Please enter your 6-digit code."
                return (session_id, session.state, True, session.message, None)
            
            # Login successful, start uploads
            session.state = SessionState.AUTHENTICATED
            session.message = "Login successful! Starting uploads..."
            
            # Start upload process in background
            asyncio.create_task(self._perform_uploads(session))
            
            return (session_id, session.state, False, session.message, None)
            
        except Exception as e:
            session.state = SessionState.ERROR
            session.error = str(e)
            await self._cleanup_session(session)
            return (session_id, session.state, False, "", str(e))
    
    async def submit_2fa(
        self,
        session_id: str,
        code: str,
    ) -> Tuple[bool, SessionState, str, Optional[str]]:
        """
        Submit 2FA code to an existing session.
        
        The browser session is still open and waiting on the 2FA page.
        We submit the code to the same browser instance.
        """
        session = self._sessions.get(session_id)
        
        if not session:
            return (False, SessionState.ERROR, "", "Session not found or expired")
        
        if session.state != SessionState.AWAITING_2FA:
            return (False, session.state, "", f"Session not awaiting 2FA (state: {session.state})")
        
        try:
            # Submit 2FA code using the existing page
            success, error = await self._submit_2fa_code(session, code)
            
            if not success:
                return (False, SessionState.AWAITING_2FA, "", error or "Invalid 2FA code")
            
            # 2FA successful, start uploads
            session.state = SessionState.AUTHENTICATED
            session.message = "Authentication successful! Starting uploads..."
            
            # Start upload process in background
            asyncio.create_task(self._perform_uploads(session))
            
            return (True, session.state, session.message, None)
            
        except Exception as e:
            session.state = SessionState.ERROR
            session.error = str(e)
            return (False, session.state, "", str(e))
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a session."""
        session = self._sessions.get(session_id)
        
        if not session:
            return None
        
        return {
            "session_id": session.id,
            "state": session.state,
            "needs_2fa": session.needs_2fa,
            "progress": session.progress,
            "current_file": (
                session.files_to_upload[session.current_file_index]
                if session.current_file_index < len(session.files_to_upload)
                else None
            ),
            "total_files": len(session.files_to_upload),
            "completed_files": session.current_file_index,
            "results": session.results,
            "message": session.message,
            "error": session.error,
            "time_remaining_seconds": session.time_remaining_seconds,
        }
    
    async def cancel_session(self, session_id: str) -> bool:
        """Cancel and cleanup a session."""
        session = self._sessions.get(session_id)
        
        if not session:
            return False
        
        session.state = SessionState.CANCELLED
        await self._cleanup_session(session)
        
        async with self._lock:
            self._sessions.pop(session_id, None)
        
        return True
    
    async def cleanup_loop(self):
        """Background task to cleanup expired sessions."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cleanup loop: {e}")
    
    async def shutdown(self):
        """Shutdown all sessions on app shutdown."""
        async with self._lock:
            for session in list(self._sessions.values()):
                await self._cleanup_session(session)
            self._sessions.clear()
    
    # =========================================================================
    # Private Methods - Playwright Operations
    # =========================================================================
    
    async def _initialize_browser(self, session: BrowserSession):
        """Initialize Playwright browser for a session."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_initialize_browser, session)
    
    def _sync_initialize_browser(self, session: BrowserSession):
        """Synchronous browser initialization (runs in thread pool)."""
        from playwright.sync_api import sync_playwright
        
        session.playwright = sync_playwright().start()
        session.browser = session.playwright.chromium.launch(
            headless=settings.playwright_headless
        )
        
        # Create context with realistic browser fingerprint
        session.context = session.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            color_scheme='light',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
        )
        
        session.page = session.context.new_page()
        
        # Inject anti-detection script
        session.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)
    
    async def _perform_login(
        self,
        session: BrowserSession,
        username: str,
        password: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Perform login to Luminate Online.
        
        Returns:
            Tuple of (needs_2fa, error)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_perform_login,
            session,
            username,
            password,
        )
    
    def _sync_perform_login(
        self,
        session: BrowserSession,
        username: str,
        password: str,
    ) -> Tuple[bool, Optional[str]]:
        """Synchronous login (runs in thread pool)."""
        page = session.page
        
        try:
            # Navigate to login page
            page.goto(settings.luminate_login_url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000 + random.randint(0, 1000))
            
            # Find and fill login fields
            username_input = page.get_by_role("textbox").first
            password_input = page.get_by_role("textbox").nth(1)
            
            # Type username with human-like delays
            username_input.click()
            page.wait_for_timeout(random.randint(100, 300))
            username_input.clear()
            for char in username:
                username_input.type(char, delay=random.randint(50, 150))
            
            page.wait_for_timeout(random.randint(200, 500))
            
            # Type password
            password_input.click()
            page.wait_for_timeout(random.randint(100, 300))
            password_input.clear()
            for char in password:
                password_input.type(char, delay=random.randint(50, 150))
            
            page.wait_for_timeout(random.randint(300, 800))
            
            # Submit login
            page.get_by_role("button", name="Log In").click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            # Check for 2FA
            current_url = page.url
            page_content = page.content().lower()
            
            # 2FA indicators
            two_factor_indicators = [
                'we sent a security code',
                'security code:',
                'two-factor',
                '2fa',
                'verification code',
                'authenticator',
                'enter code',
                'verify your identity'
            ]
            
            has_2fa_prompt = any(indicator in page_content for indicator in two_factor_indicators)
            
            # Check for 2FA input field
            has_2fa_input = False
            try:
                auth_inputs = page.locator('input[name^="ADDITIONAL_AUTH"]')
                if auth_inputs.count() > 0 and auth_inputs.first.is_visible():
                    has_2fa_input = True
            except:
                pass
            
            # Check for password inputs (2FA often uses a second password field)
            still_on_login = 'AdminLogin' in current_url or 'login' in current_url.lower()
            if still_on_login and not has_2fa_input:
                try:
                    password_inputs = page.locator('input[type="password"]')
                    if password_inputs.count() > 1:
                        second_pwd = password_inputs.nth(1)
                        if second_pwd.is_visible():
                            input_name = second_pwd.get_attribute('name') or ''
                            if 'ADDITIONAL_AUTH' in input_name.upper() or 'AUTH' in input_name.upper():
                                has_2fa_input = True
                except:
                    pass
            
            # Check for login errors
            error_indicators = [
                'invalid username or password',
                'incorrect username or password',
                'login failed',
                'authentication failed',
                'invalid credentials'
            ]
            has_error = any(error_term in page_content for error_term in error_indicators)
            
            if has_error:
                return (False, "Login failed. Please check your credentials.")
            
            if has_2fa_input or (has_2fa_prompt and still_on_login):
                return (True, None)  # 2FA required
            
            # Try to verify login by accessing Image Library
            try:
                page.goto(settings.luminate_image_library_url, timeout=10000)
                page.wait_for_load_state("networkidle")
                page.wait_for_selector('text=Upload Image', timeout=5000)
                return (False, None)  # Login successful
            except:
                pass
            
            # Re-check for 2FA after navigation attempt
            current_url = page.url
            page_content = page.content().lower()
            has_2fa_prompt = any(indicator in page_content for indicator in two_factor_indicators)
            
            if has_2fa_prompt or 'AdminLogin' in current_url:
                return (True, None)
            
            return (False, "Login verification failed. Unable to access Image Library.")
            
        except Exception as e:
            return (False, f"Login error: {str(e)}")
    
    async def _submit_2fa_code(
        self,
        session: BrowserSession,
        code: str,
    ) -> Tuple[bool, Optional[str]]:
        """Submit 2FA code to the existing browser session."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_submit_2fa_code,
            session,
            code,
        )
    
    def _sync_submit_2fa_code(
        self,
        session: BrowserSession,
        code: str,
    ) -> Tuple[bool, Optional[str]]:
        """Synchronous 2FA submission (runs in thread pool)."""
        page = session.page
        
        try:
            # Wait for 2FA form
            try:
                page.wait_for_selector('input[name^="ADDITIONAL_AUTH"]', state='visible', timeout=5000)
            except:
                pass
            page.wait_for_timeout(1000)
            
            # Find 2FA input field
            code_input = None
            
            # Strategy 1: Look for ADDITIONAL_AUTH input
            try:
                potential_input = page.locator('input[name^="ADDITIONAL_AUTH"]')
                if potential_input.count() > 0:
                    code_input = potential_input.first
            except:
                pass
            
            # Strategy 2: Look for password input (Luminate uses type="password" for 2FA)
            if not code_input:
                try:
                    password_inputs = page.locator('input[type="password"]')
                    if password_inputs.count() > 1:
                        code_input = password_inputs.nth(1)
                    elif password_inputs.count() == 1:
                        page_content = page.content().lower()
                        if 'security code' in page_content or 'additional' in page_content:
                            code_input = password_inputs.first
                except:
                    pass
            
            # Strategy 3: Look for inputs with maxlength
            if not code_input:
                try:
                    potential_input = page.locator('input[maxlength="6"], input[maxlength="99"]').first
                    if potential_input.count() > 0:
                        code_input = potential_input
                except:
                    pass
            
            if not code_input or code_input.count() == 0:
                return (False, "Could not find 2FA input field")
            
            # Enter the code
            code_input.click()
            page.wait_for_timeout(200)
            code_input.clear()
            
            for char in str(code):
                code_input.type(char, delay=random.randint(50, 150))
            
            page.wait_for_timeout(500)
            
            # Find and click submit button
            submit_button = None
            try:
                submit_button = page.locator('input[type="submit"][name="login"], input[id="login"]').first
                if submit_button.count() == 0:
                    submit_button = page.locator('form[name="lmainLogonForm"] input[type="submit"]').first
                if submit_button.count() == 0:
                    submit_button = page.locator('input[type="submit"], button[type="submit"]').first
                if submit_button.count() == 0:
                    submit_button = page.get_by_role("button", name=re.compile("log in|submit|verify", re.I)).first
            except:
                pass
            
            if submit_button and submit_button.count() > 0:
                submit_button.click()
            else:
                code_input.press("Enter")
            
            # Wait for navigation
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            # Verify authentication
            current_url = page.url
            if 'AdminLogin' not in current_url and 'login' not in current_url.lower():
                try:
                    page.goto(settings.luminate_image_library_url, timeout=10000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_selector('text=Upload Image', timeout=5000)
                    return (True, None)
                except:
                    page.wait_for_timeout(2000)
                    current_url = page.url
                    if 'AdminLogin' not in current_url and 'login' not in current_url.lower():
                        try:
                            page.wait_for_selector('text=Upload Image', timeout=5000)
                            return (True, None)
                        except:
                            pass
            
            # Check if 2FA prompt is still there
            page_content = page.content().lower()
            two_factor_indicators = [
                'two-factor', '2fa', 'verification code', 'authenticator',
                'security code', 'enter code', 'verify your identity', 'additional-auth'
            ]
            still_has_2fa = any(indicator in page_content for indicator in two_factor_indicators)
            
            if still_has_2fa:
                return (False, "Invalid 2FA code. Please try again.")
            
            # Try one more time to access Image Library
            try:
                page.goto(settings.luminate_image_library_url, timeout=10000)
                page.wait_for_load_state("networkidle")
                page.wait_for_selector('text=Upload Image', timeout=5000)
                return (True, None)
            except:
                return (False, "2FA submitted but authentication verification failed.")
            
        except Exception as e:
            return (False, f"Error submitting 2FA code: {str(e)}")
    
    async def _perform_uploads(self, session: BrowserSession):
        """Upload all files for a session."""
        session.state = SessionState.UPLOADING
        session.message = "Starting uploads..."
        
        loop = asyncio.get_event_loop()
        
        try:
            for i, file_path in enumerate(session.files_to_upload):
                session.current_file_index = i
                filename = file_path.split("/")[-1]
                session.message = f"Uploading {filename}... ({i+1}/{len(session.files_to_upload)})"
                
                # Upload single file
                success, url, error = await loop.run_in_executor(
                    None,
                    self._sync_upload_file,
                    session,
                    file_path,
                )
                
                session.results.append(UploadResult(
                    filename=filename,
                    success=success,
                    url=url,
                    error=error,
                ))
            
            session.current_file_index = len(session.files_to_upload)
            session.state = SessionState.DONE
            
            successful = sum(1 for r in session.results if r.success)
            session.message = f"Upload complete! {successful}/{len(session.results)} files uploaded successfully."
            
        except Exception as e:
            session.state = SessionState.ERROR
            session.error = str(e)
        
        finally:
            # Cleanup browser but keep session for results
            await self._cleanup_browser(session)
    
    def _sync_upload_file(
        self,
        session: BrowserSession,
        file_path: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Upload a single file (runs in thread pool)."""
        page = session.page
        filename = file_path.split("/")[-1]
        
        try:
            # Navigate to Image Library if needed
            current_url = page.url
            if settings.luminate_image_library_url not in current_url:
                page.goto(settings.luminate_image_library_url)
                page.wait_for_load_state("networkidle")
                page.wait_for_selector('text=Upload Image', timeout=10000)
            
            # Click Upload Image button
            page.get_by_role("link", name="Upload Image").click()
            page.wait_for_timeout(1500)
            
            # Find iframe and file input
            iframe_locator = page.frame_locator("iframe").last
            file_input = iframe_locator.locator('#imageFileUpload')
            file_input.wait_for(timeout=10000)
            
            # Set file
            file_input.set_input_files(file_path)
            page.wait_for_timeout(1000)
            
            # Click upload button
            upload_button = iframe_locator.locator('input[type="submit"][value="Upload"], button:has-text("Upload")')
            upload_button.click()
            
            # Wait for upload
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            # Refresh page for next upload
            page.reload()
            page.wait_for_load_state("networkidle")
            page.wait_for_selector('text=Upload Image', timeout=10000)
            
            # Generate URL
            url = settings.luminate_image_base_url + filename
            
            # Verify upload
            import requests
            try:
                response = requests.head(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    if content_type.startswith('image/'):
                        return (True, url, None)
            except:
                pass
            
            # Try a few more times
            for _ in range(2):
                page.wait_for_timeout(2000)
                try:
                    response = requests.head(url, timeout=10, allow_redirects=True)
                    if response.status_code == 200:
                        return (True, url, None)
                except:
                    pass
            
            return (False, None, "Upload completed but verification failed")
            
        except Exception as e:
            return (False, None, str(e))
    
    async def _cleanup_browser(self, session: BrowserSession):
        """Close browser without removing session (for results access)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_cleanup_browser, session)
    
    def _sync_cleanup_browser(self, session: BrowserSession):
        """Synchronous browser cleanup."""
        try:
            if session.browser:
                session.browser.close()
                session.browser = None
            if session.playwright:
                session.playwright.stop()
                session.playwright = None
        except:
            pass
    
    async def _cleanup_session(self, session: BrowserSession):
        """Full session cleanup including browser and temp files."""
        await self._cleanup_browser(session)
        
        # Clean up temp directory
        if session.temp_dir:
            try:
                shutil.rmtree(session.temp_dir, ignore_errors=True)
            except:
                pass
    
    async def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        async with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired or session.state in (SessionState.DONE, SessionState.ERROR, SessionState.CANCELLED)
            ]
            
            for sid in expired:
                session = self._sessions.pop(sid, None)
                if session:
                    await self._cleanup_session(session)


# Global browser manager instance
browser_manager = BrowserSessionManager()
