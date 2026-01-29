"""
Email Beautifier Service

Transforms ugly plain text emails (from HTML conversions) into beautiful,
clean, well-formatted plain text with proper formatting, cleaned URLs,
and styled CTAs.
"""

import re
from typing import List, Tuple, Dict
from urllib.parse import urlparse, parse_qs, urlunparse


# Common tracking parameters to strip from URLs
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'utm_id', 'utm_source_platform', 'utm_creative_format', 'utm_marketing_tactic',
    'fbclid', 'gclid', 'msclkid', '_ga', 'mc_cid', 'mc_eid',
    'mkt_tok', 'trk', 'trkid', 'icid', 'igshid', 'zanpid',
}

# Common CTA phrases (case-insensitive)
CTA_PHRASES = [
    'click here', 'learn more', 'get started', 'sign up', 'register now',
    'join now', 'subscribe', 'download', 'read more', 'view more',
    'shop now', 'buy now', 'order now', 'book now', 'reserve',
    'discover', 'explore', 'find out more', 'see more', 'get it now',
    'try it free', 'start free trial', 'claim offer', 'redeem',
]


def clean_url(url: str, strip_tracking: bool = True) -> str:
    """
    Clean a URL by removing tracking parameters.
    
    Args:
        url: The URL to clean
        strip_tracking: Whether to strip tracking parameters
    
    Returns:
        Cleaned URL
    """
    if not strip_tracking:
        return url
    
    try:
        # Parse URL
        parsed = urlparse(url)
        
        # Parse query parameters
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        
        # Filter out tracking parameters
        cleaned_params = {
            key: value for key, value in query_params.items()
            if key.lower() not in TRACKING_PARAMS
        }
        
        # Rebuild query string
        if cleaned_params:
            query_string = '&'.join(
                f"{key}={value[0]}" if value else key
                for key, value in cleaned_params.items()
            )
        else:
            query_string = ''
        
        # Rebuild URL
        cleaned = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            query_string,
            parsed.fragment
        ))
        
        return cleaned
    except Exception:
        # If parsing fails, return original
        return url


def detect_ctas(text: str) -> List[Tuple[str, str, int, int]]:
    """
    Detect CTAs (call-to-action) in text.
    
    Returns list of (cta_text, url, start_pos, end_pos) tuples.
    """
    ctas = []
    
    # Pattern 1: All-caps text followed by URL on same or next line
    # Example: "CLICK HERE\nhttps://example.com"
    pattern1 = r'([A-Z][A-Z\s]{2,50}?)\s*[\n\r]*\s*(https?://[^\s]+)'
    for match in re.finditer(pattern1, text):
        cta_text = match.group(1).strip()
        url = match.group(2).strip()
        
        # Check if it's a known CTA phrase
        if any(phrase in cta_text.lower() for phrase in CTA_PHRASES):
            ctas.append((cta_text, url, match.start(), match.end()))
    
    # Pattern 2: CTA phrase followed by colon and URL
    # Example: "Click here: https://example.com"
    pattern2 = r'([A-Za-z\s]{3,50}?):\s*(https?://[^\s]+)'
    for match in re.finditer(pattern2, text):
        cta_text = match.group(1).strip()
        url = match.group(2).strip()
        
        if any(phrase in cta_text.lower() for phrase in CTA_PHRASES):
            # Make sure we haven't already captured this as pattern1
            overlap = any(
                match.start() >= start and match.end() <= end
                for _, _, start, end in ctas
            )
            if not overlap:
                ctas.append((cta_text, url, match.start(), match.end()))
    
    # Pattern 3: Standalone URL preceded by CTA-like text within 50 chars
    # Example: "Click the button below to get started\nhttps://example.com"
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # Check if line is a standalone URL
        if re.match(r'^https?://[^\s]+$', line_stripped):
            # Check previous line(s) for CTA text
            if i > 0:
                prev_line = lines[i-1].strip()
                if any(phrase in prev_line.lower() for phrase in CTA_PHRASES):
                    # Calculate position in original text
                    text_before = '\n'.join(lines[:i])
                    start_pos = len(text_before) + 1 if text_before else 0
                    end_pos = start_pos + len(line_stripped)
                    
                    # Make sure we haven't already captured this
                    overlap = any(
                        start_pos >= start and end_pos <= end
                        for _, _, start, end in ctas
                    )
                    if not overlap:
                        ctas.append((prev_line, line_stripped, start_pos, end_pos))
    
    return ctas


def format_cta(cta_text: str, url: str) -> str:
    """
    Format a CTA with arrow styling.
    
    Example: >>> GET STARTED: https://example.com <<<
    """
    # Ensure CTA text is uppercase and clean
    cta_clean = cta_text.strip().upper()
    url_clean = url.strip()
    
    return f">>> {cta_clean}: {url_clean} <<<"


def convert_links_to_markdown(text: str, ctas: List[Tuple[str, str, int, int]]) -> str:
    """
    Convert regular links (non-CTA) to markdown format.
    
    Handles patterns like:
    - "Check out https://example.com for more info"
    - "Visit our website: https://example.com"
    """
    # Find all formatted CTA positions (>>> ... <<<) to skip them
    cta_pattern = r'>>>[^<]+<<<'
    cta_positions = []
    for match in re.finditer(cta_pattern, text):
        cta_positions.append((match.start(), match.end()))
    
    # Pattern: Text followed by URL, where URL is not part of a CTA
    # We'll look for standalone URLs and try to extract preceding context
    
    # First, find all URLs in text
    url_pattern = r'https?://[^\s)>\]]+(?:[^\s.,;!?)])?'
    
    result = text
    replacements = []
    
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        url_start = match.start()
        url_end = match.end()
        
        # Skip if this URL is within a formatted CTA
        is_in_cta = any(start <= url_start < end for start, end in cta_positions)
        if is_in_cta:
            continue
        
        # Look for preceding text that might be the link text
        # Check if there's a pattern like "text: url" or "text - url"
        context_start = max(0, url_start - 100)
        context = text[context_start:url_start]
        
        # Look for link text pattern (text followed by : or -)
        link_text_match = re.search(r'([^.!?\n]{3,50}?)(?::\s*|-\s*)$', context)
        
        if link_text_match:
            link_text = link_text_match.group(1).strip()
            # Create markdown link
            markdown = f"[{link_text}]({url})"
            # Store replacement (original text + url -> markdown)
            original_start = context_start + link_text_match.start()
            replacements.append((original_start, url_end, markdown))
        else:
            # Just convert standalone URL to markdown with URL as text
            # But only if it's not at the start of a line (which might be intentional)
            if url_start > 0 and text[url_start-1] not in '\n\r':
                # Get domain as link text
                domain = re.search(r'https?://([^/]+)', url)
                if domain:
                    domain_text = domain.group(1).replace('www.', '')
                    markdown = f"[{domain_text}]({url})"
                    replacements.append((url_start, url_end, markdown))
    
    # Apply replacements in reverse order to maintain positions
    for start, end, markdown in reversed(replacements):
        result = result[:start] + markdown + result[end:]
    
    return result


def normalize_whitespace(text: str) -> str:
    """
    Normalize excessive whitespace and line breaks.
    
    - Removes trailing whitespace from lines
    - Collapses multiple blank lines to maximum 2
    - Removes leading/trailing whitespace from entire text
    """
    # Split into lines
    lines = text.split('\n')
    
    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in lines]
    
    # Collapse multiple blank lines
    result_lines = []
    blank_count = 0
    
    for line in lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:
                result_lines.append(line)
        else:
            blank_count = 0
            result_lines.append(line)
    
    # Join and strip
    result = '\n'.join(result_lines).strip()
    
    return result


def clean_footer_section(text: str) -> str:
    """
    Clean up footer sections (unsubscribe links, addresses, etc.).
    
    Adds visual separator before footer if detected.
    """
    # Common footer indicators
    footer_indicators = [
        'unsubscribe', 'opt out', 'manage preferences', 'manage subscription',
        'update your email preferences', 'you received this email',
        'you are receiving this', 'view in browser', 'view online',
        'privacy policy', 'terms of service', 'copyright',
    ]
    
    # Find first footer indicator
    lines = text.split('\n')
    footer_start = None
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(indicator in line_lower for indicator in footer_indicators):
            footer_start = i
            break
    
    # If footer found, add separator
    if footer_start is not None and footer_start > 0:
        # Insert separator line
        lines.insert(footer_start, '')
        lines.insert(footer_start, '─' * 50)
        lines.insert(footer_start, '')
        text = '\n'.join(lines)
    
    return text


def beautify_email(
    raw_text: str,
    strip_tracking: bool = True,
    format_ctas: bool = True,
    markdown_links: bool = True
) -> Tuple[str, Dict]:
    """
    Main function to beautify email text.
    
    Args:
        raw_text: The ugly plain text email
        strip_tracking: Whether to strip tracking parameters from URLs
        format_ctas: Whether to format CTAs with arrows
        markdown_links: Whether to convert links to markdown
    
    Returns:
        Tuple of (beautified_text, stats_dict)
    """
    stats = {
        'urls_cleaned': 0,
        'ctas_formatted': 0,
        'links_converted': 0,
        'lines_before': len(raw_text.split('\n')),
        'lines_after': 0,
    }
    
    # Start with normalized whitespace
    text = normalize_whitespace(raw_text)
    
    # Detect CTAs first
    ctas = []
    if format_ctas:
        ctas = detect_ctas(text)
        stats['ctas_formatted'] = len(ctas)
    
    # Clean URLs in CTAs and format them
    if format_ctas and ctas:
        # Process CTAs in reverse order to maintain positions
        for cta_text, url, start, end in reversed(ctas):
            clean_url_str = clean_url(url, strip_tracking)
            if clean_url_str != url:
                stats['urls_cleaned'] += 1
            
            formatted_cta = format_cta(cta_text, clean_url_str)
            text = text[:start] + formatted_cta + text[end:]
    
    # Clean remaining URLs (non-CTA)
    if strip_tracking:
        def replace_url(match):
            url = match.group(0)
            cleaned = clean_url(url, strip_tracking)
            if cleaned != url:
                stats['urls_cleaned'] += 1
            return cleaned
        
        # Only clean URLs that are not already processed as CTAs
        text = re.sub(r'https?://[^\s)>\]]+', replace_url, text)
    
    # Convert links to markdown (if not CTAs)
    if markdown_links:
        original_text = text
        text = convert_links_to_markdown(text, ctas)
        # Count how many links were converted (approximate)
        stats['links_converted'] = text.count('[') - original_text.count('[')
    
    # Clean footer section
    text = clean_footer_section(text)
    
    # Final whitespace normalization
    text = normalize_whitespace(text)
    
    stats['lines_after'] = len(text.split('\n'))
    
    return text, stats
