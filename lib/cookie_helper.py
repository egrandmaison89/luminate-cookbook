#!/usr/bin/env python3
"""
Cookie Helper for Luminate Cookbook

Provides utilities for extracting and importing browser cookies to bypass 2FA.
When users are already logged into Luminate in their browser, they can export
their session cookies and use them with our uploader.
"""

import json
import base64
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse


# Luminate cookie domains
LUMINATE_DOMAINS = [
    "secure2.convio.net",
    ".convio.net",
    "convio.net",
]


def get_cookie_extraction_bookmarklet() -> str:
    """
    Returns JavaScript code for a bookmarklet that extracts Luminate cookies.
    
    The user can:
    1. Log into Luminate Online in their browser
    2. Run this bookmarklet on the Luminate admin page
    3. Copy the generated string
    4. Paste it into our app
    """
    # This JavaScript extracts cookies and displays them in a copyable format
    js_code = """
(function() {
    // Get all cookies for this domain
    var cookies = document.cookie.split(';').map(function(c) {
        var parts = c.trim().split('=');
        return {
            name: parts[0],
            value: parts.slice(1).join('='),
            domain: window.location.hostname,
            path: '/',
            secure: window.location.protocol === 'https:',
            httpOnly: false
        };
    });
    
    // Create export object
    var exportData = {
        cookies: cookies,
        url: window.location.href,
        timestamp: Date.now(),
        userAgent: navigator.userAgent
    };
    
    // Encode as base64
    var encoded = btoa(unescape(encodeURIComponent(JSON.stringify(exportData))));
    
    // Create modal to show the encoded string
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:999999;display:flex;align-items:center;justify-content:center;';
    
    var content = document.createElement('div');
    content.style.cssText = 'background:white;padding:20px;border-radius:8px;max-width:600px;width:90%;max-height:80vh;overflow:auto;';
    
    content.innerHTML = '<h2 style="margin:0 0 15px 0;color:#333;">Session Exported!</h2>' +
        '<p style="color:#666;margin-bottom:15px;">Copy this code and paste it into the Luminate Cookbook Image Uploader:</p>' +
        '<textarea id="lum-cookie-export" style="width:100%;height:150px;font-family:monospace;font-size:12px;padding:10px;border:1px solid #ccc;border-radius:4px;">' + encoded + '</textarea>' +
        '<div style="margin-top:15px;text-align:right;">' +
        '<button id="lum-copy-btn" style="background:#007bff;color:white;border:none;padding:10px 20px;border-radius:4px;cursor:pointer;margin-right:10px;">Copy to Clipboard</button>' +
        '<button id="lum-close-btn" style="background:#6c757d;color:white;border:none;padding:10px 20px;border-radius:4px;cursor:pointer;">Close</button>' +
        '</div>';
    
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // Select text
    var textarea = document.getElementById('lum-cookie-export');
    textarea.select();
    
    // Copy button
    document.getElementById('lum-copy-btn').onclick = function() {
        textarea.select();
        document.execCommand('copy');
        this.textContent = 'Copied!';
        this.style.background = '#28a745';
    };
    
    // Close button
    document.getElementById('lum-close-btn').onclick = function() {
        modal.remove();
    };
    
    // Close on backdrop click
    modal.onclick = function(e) {
        if (e.target === modal) modal.remove();
    };
})();
    """.strip()
    
    # Return as bookmarklet URL
    return f"javascript:{js_code}"


def get_browser_instructions() -> str:
    """
    Returns instructions for users on how to extract cookies manually.
    """
    return """
## How to Export Your Luminate Session

### Option 1: Use the Bookmarklet (Recommended)

1. **Create the bookmarklet:**
   - Right-click your browser's bookmarks bar
   - Select "Add bookmark" or "Add page"
   - Name it "Export Luminate Session"
   - In the URL field, paste the bookmarklet code (shown below)

2. **Use it:**
   - Log into Luminate Online as usual (complete 2FA if prompted)
   - Click the bookmarklet while on any Luminate admin page
   - Copy the code that appears
   - Paste it into the "Session Import" field in the Image Uploader

### Option 2: Manual Export (Chrome)

1. Log into Luminate Online
2. Open Developer Tools (F12 or Cmd+Option+I)
3. Go to Application tab → Cookies
4. Find cookies for `secure2.convio.net`
5. Copy the cookie values (especially JSESSIONID)

### Why This Works

When you log into Luminate in your browser, you complete any 2FA challenges.
By exporting your session cookies, our app can use your authenticated session
instead of trying to log in again (which would trigger 2FA from our server).

Your session typically lasts 24 hours, so you only need to do this once per day.
"""


def parse_cookie_export(encoded_string: str) -> Optional[Dict[str, Any]]:
    """
    Parse an exported cookie string from the bookmarklet.
    
    Args:
        encoded_string: Base64-encoded cookie export from bookmarklet
        
    Returns:
        dict with cookies and metadata, or None if invalid
    """
    try:
        # Decode base64
        decoded = base64.b64decode(encoded_string.strip())
        data = json.loads(decoded.decode('utf-8'))
        
        # Validate structure
        if 'cookies' not in data or not isinstance(data['cookies'], list):
            return None
        
        # Check timestamp (reject if too old - more than 48 hours)
        if 'timestamp' in data:
            age_hours = (time.time() * 1000 - data['timestamp']) / (1000 * 3600)
            if age_hours > 48:
                return None
        
        return data
    except Exception as e:
        print(f"Failed to parse cookie export: {e}")
        return None


def cookies_to_playwright_state(cookie_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert exported cookies to Playwright storage state format.
    
    Args:
        cookie_data: Parsed cookie export from parse_cookie_export()
        
    Returns:
        dict: Playwright-compatible storage state
    """
    cookies = cookie_data.get('cookies', [])
    
    # Convert to Playwright format
    playwright_cookies = []
    for cookie in cookies:
        pc = {
            'name': cookie.get('name', ''),
            'value': cookie.get('value', ''),
            'domain': cookie.get('domain', 'secure2.convio.net'),
            'path': cookie.get('path', '/'),
            'secure': cookie.get('secure', True),
            'httpOnly': cookie.get('httpOnly', False),
            'sameSite': cookie.get('sameSite', 'Lax'),
        }
        
        # Add expiry if not present (set to 24 hours from now)
        if 'expires' not in cookie:
            pc['expires'] = time.time() + 86400
        else:
            pc['expires'] = cookie['expires']
        
        playwright_cookies.append(pc)
    
    return {
        'cookies': playwright_cookies,
        'origins': []
    }


def validate_luminate_cookies(cookies: List[Dict]) -> bool:
    """
    Check if cookies contain valid Luminate session cookies.
    
    Args:
        cookies: List of cookie dictionaries
        
    Returns:
        bool: True if cookies appear to contain a valid Luminate session
    """
    # Look for session-related cookies
    session_indicators = ['JSESSIONID', 'convio', 'session', 'auth', 'sso']
    
    cookie_names = [c.get('name', '').lower() for c in cookies]
    
    for indicator in session_indicators:
        if any(indicator.lower() in name for name in cookie_names):
            return True
    
    return len(cookies) > 0  # Accept if there are any cookies


def create_simple_cookie_paste_instructions() -> str:
    """
    Return simple instructions for pasting cookies from browser dev tools.
    """
    return """
### Quick Cookie Paste (Chrome/Edge)

1. Log into Luminate Online in your browser
2. Press **F12** to open Developer Tools
3. Go to **Application** tab → **Cookies** → **secure2.convio.net**
4. Find the cookie named **JSESSIONID** 
5. Double-click its **Value** and copy it
6. Paste below in this format: `JSESSIONID=your_value_here`

You can also copy multiple cookies, one per line:
```
JSESSIONID=ABC123...
other_cookie=value...
```
"""


def parse_simple_cookie_paste(text: str) -> Optional[List[Dict]]:
    """
    Parse simple cookie=value format that users can copy from dev tools.
    
    Args:
        text: Cookie text in "name=value" format (one per line)
        
    Returns:
        List of cookie dicts or None if invalid
    """
    cookies = []
    
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if '=' in line:
            parts = line.split('=', 1)
            name = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ''
            
            if name:
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': 'secure2.convio.net',
                    'path': '/',
                    'secure': True,
                    'httpOnly': False,
                    'sameSite': 'Lax',
                    'expires': time.time() + 86400
                })
    
    return cookies if cookies else None
