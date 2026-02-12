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
    'mkt_tok', 'trk', 'trkid', 'icid', 'igshid', 'zanpid', 's_src',
    'aff', 'ref', 'ref_src', 'ref_cid', 'cmpid',  # affiliate/referral params
}

# Common CTA phrases (case-insensitive)
CTA_PHRASES = [
    'click here', 'learn more', 'get started', 'sign up', 'register now',
    'join now', 'subscribe', 'download', 'read more', 'view more',
    'shop now', 'buy now', 'order now', 'book now', 'reserve',
    'discover', 'explore', 'find out more', 'see more', 'get it now',
    'try it free', 'start free trial', 'claim offer', 'redeem',
    'rsvp', 'rsvp today', 'rsvp now', 'register', 'sign up now',
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
    
    # Pattern 3: Standalone URL preceded by CTA-like text on previous line(s)
    # Example: "RSVP Today\n\nhttps://example.com" or "Click here\nhttps://example.com"
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # Check if line is a standalone URL
        if re.match(r'^https?://[^\s]+$', line_stripped):
            # Check previous non-empty line(s) for CTA text
            prev_line = None
            for j in range(i - 1, -1, -1):
                candidate = lines[j].strip()
                if candidate:
                    prev_line = candidate
                    break
            if prev_line and any(phrase in prev_line.lower() for phrase in CTA_PHRASES):
                    # CTAs are short button-like phrases, not full sentences
                    # Skip if prev_line is too long (e.g. "The event will sell out, so RSVP promptly!")
                    if len(prev_line) <= 50:
                        # Replace from start of CTA line (j) to end of URL line (i)
                        start_pos = len('\n'.join(lines[:j])) if j > 0 else 0
                        end_pos = len('\n'.join(lines[:i + 1]))
                        # Make sure we haven't already captured this
                        overlap = any(
                            start_pos >= start and end_pos <= end
                            for _, _, start, end in ctas
                        )
                        if not overlap:
                            ctas.append((prev_line, line_stripped, start_pos, end_pos))
    
    return ctas


def format_cta(cta_text: str, url: str, visual_bounce: bool = True) -> str:
    """
    Format a CTA with arrow styling and optional visual bounce (blank lines).
    
    Example: >>> GET STARTED: https://example.com <<<
    With visual_bounce: blank line above and below for emphasis.
    """
    # Ensure CTA text is uppercase and clean
    cta_clean = cta_text.strip().upper()
    url_clean = url.strip()
    
    formatted = f">>> {cta_clean}: {url_clean} <<<"
    if visual_bounce:
        return f"\n\n{formatted}\n\n"
    return formatted


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


def strip_css_blocks(text: str) -> str:
    """
    Remove CSS blocks from text.
    
    Handles:
    - <style> tags
    - CSS rules (selector { properties })
    - @media queries
    - Email tracking CSS
    """
    # Remove everything up to and including closing style tag
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    lines = text.split('\n')
    
    # Remove CSS blocks at the START
    # Find first line that's definitely NOT CSS
    content_start = 0
    brace_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Update brace count
        brace_count += stripped.count('{') - stripped.count('}')
        
        # Skip empty lines
        if not stripped:
            continue
        
        # CSS patterns to match
        css_patterns = [
            r'^body\s*{',  # body {
            r'^@media',  # @media queries
            r'^#[\w-]+\s*{',  # #id {
            r'^\.[\w-]+\s*{',  # .class {
            r'^\*\s*{',  # * {
            r'^/\*',  # /* comment
            r'^\*/',  # */ comment end
            r'^\}',  # closing brace
            r'^[\w-]+:\s*[^{]+;',  # CSS property: value;
            r'!important',  # !important keyword
        ]
        
        # Check if line matches any CSS pattern OR we're inside braces
        is_css = any(re.search(pattern, stripped) for pattern in css_patterns) or brace_count > 0
        
        # If NOT CSS and braces are balanced or over-closed, we found content
        if not is_css and brace_count <= 0:
            content_start = i
            break
    
    # Apply the cut
    if content_start > 0:
        lines = lines[content_start:]
    
    # Remove CSS blocks at the END (work with the already-trimmed lines)
    # Work backwards to find last line of CSS
    content_end = len(lines)
    brace_count = 0
    
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        
        # Update brace count (reversed)
        brace_count += stripped.count('}') - stripped.count('{')
        
        # Skip empty lines
        if not stripped:
            continue
        
        # End CSS patterns
        end_css_patterns = [
            r'@media',
            r'prefers-color-scheme',
            r'display:\s*none',
            r'background-image:\s*url',
            r'content:\s*url',
            r'^#[\w_]+\s*{',  # #_eoa_img {
            r'^\.[\w_]+',  # .class
            r'^div\.',  # div.class
            r'^table\.',  # table.class
            r'^blockquote',  # blockquote
            r'^\}',  # closing brace
        ]
        
        # Check if line matches end CSS patterns OR we're inside braces
        is_end_css = any(re.search(pattern, stripped, re.IGNORECASE) for pattern in end_css_patterns) or brace_count > 0
        
        # If NOT CSS and braces are balanced, we found last content
        if not is_end_css and brace_count == 0:
            content_end = i + 1
            break
    
    # Apply the cut
    if content_end < len(lines):
        lines = lines[:content_end]
    
    return '\n'.join(lines)


def detect_preview_text(text: str) -> tuple[str, str]:
    """
    Detect and extract preview/callout text at the beginning.
    
    Preview text is usually the first line of actual content (non-URL)
    that appears before the main body.
    
    Returns:
        Tuple of (preview_text, remaining_text)
    """
    lines = text.strip().split('\n')
    preview_text = None
    content_start = 0
    
    # Look for the first substantial line of text (not a URL, not too short)
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines and URLs
        if not stripped or re.match(r'^https?://', stripped):
            continue
        
        # If it's a short, impactful line (typical preview text), mark it
        if len(stripped) < 100 and not stripped.startswith('Dear') and not stripped.startswith('Hi'):
            preview_text = stripped
            content_start = i + 1
            break
    
    if preview_text:
        remaining = '\n'.join(lines[content_start:])
        return preview_text, remaining
    
    return None, text


def join_broken_lines(text: str) -> str:
    """
    Join lines that are part of the same paragraph/sentence.
    
    Keeps intentional breaks (empty lines, ends of sentences, etc.)
    but joins lines that were broken mid-sentence due to HTML conversion.
    """
    lines = text.split('\n')
    result_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip()
        
        # If line is empty, keep it and move on
        if not line.strip():
            result_lines.append(line)
            i += 1
            continue
        
        # Check if this line should be joined with the next
        should_join = False
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            
            # Don't join if next line is empty
            if not next_line:
                result_lines.append(line)
                i += 1
                continue
            
            # Don't join if next line starts with URL
            if next_line.startswith('http://') or next_line.startswith('https://'):
                result_lines.append(line)
                i += 1
                continue
            
            # Don't join if current line ends with sentence-ending punctuation
            if line.rstrip().endswith(('.', '!', '?', ':', '>>>')):
                result_lines.append(line)
                i += 1
                continue
            
            # Don't join if next line looks like a header or CTA (all caps, short)
            if next_line.isupper() and len(next_line) < 50:
                result_lines.append(line)
                i += 1
                continue
            
            # Don't join if current or next line contains arrows (formatted CTA)
            if '>>>' in line or '<<<' in line or '>>>' in next_line or '<<<' in next_line:
                result_lines.append(line)
                i += 1
                continue
            
            # JOIN if next line starts with lowercase (continuation)
            if next_line[0].islower():
                should_join = True
            # JOIN if line ends with comma/semicolon (trailing continuation)
            elif line.rstrip().endswith((',', ';')):
                should_join = True
            # JOIN if line doesn't end with punctuation and next starts with uppercase but continues thought
            elif not line.rstrip().endswith(('.', '!', '?', ':', '-', '&')) and next_line[0].isupper():
                # This is a judgment call - join if the line seems incomplete
                # (less than 70 chars suggests it might be broken)
                if len(line) < 70:
                    should_join = True
        
        if should_join and i + 1 < len(lines):
            # Join with next line
            next_line = lines[i + 1].strip()
            joined = line + ' ' + next_line
            result_lines.append(joined)
            i += 2  # Skip next line since we joined it
        else:
            result_lines.append(line)
            i += 1
    
    return '\n'.join(result_lines)


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


def simplify_footer(text: str) -> str:
    """
    Simplify and clean up footer section.
    
    Footer is identified from the END of the document (last 25-30% of lines).
    Only treats content as footer when we find clear footer patterns:
    - 2+ consecutive social platform labels (Facebook, X, Instagram, etc.)
    - "X Logo" standalone in the last 15 lines
    
    Does NOT treat header logos or body text (e.g. "Dana-Farber Marathon Challenge")
    as footer - those appear early in the document.
    
    - Removes logo/image references from footer
    - Consolidates organization links
    - Formats unsubscribe/privacy policy inline
    - Removes social media/badge links
    """
    lines = text.split('\n')
    
    if len(lines) < 5:
        return text
    
    # Footer is typically in the last 25-30% of the document
    search_start = max(0, int(len(lines) * 0.70))
    search_region = list(enumerate(lines[search_start:], start=search_start))
    
    # Social platform labels (standalone, typical footer pattern)
    SOCIAL_LABELS = {'facebook', 'twitter', 'x', 'instagram', 'youtube', 'linkedin'}
    
    footer_start_idx = None
    
    # Strategy 1: Find 2+ consecutive social platform labels in the search region
    consecutive_social = 0
    for i, line in search_region:
        line_lower = line.lower().strip()
        if line_lower in SOCIAL_LABELS:
            consecutive_social += 1
            if consecutive_social >= 2:
                # Back up to include the first social label and any logo line before it
                footer_start_idx = max(search_start, i - consecutive_social - 2)
                break
        else:
            consecutive_social = 0
    
    # Strategy 2: Find "X Logo" pattern in last 15 lines only (footer logo)
    if footer_start_idx is None:
        last_15_start = max(0, len(lines) - 15)
        for i in range(last_15_start, len(lines)):
            line = lines[i].strip()
            # Standalone "Something Logo" (e.g. "Dana-Farber Logo", "DFMC Logo")
            if re.match(r'^[\w\-]+\s+Logo\s*$', line, re.IGNORECASE):
                footer_start_idx = i
                break
    
    # Strategy 3: Multiple consecutive URLs in last 30% (footer link block)
    if footer_start_idx is None:
        url_count = 0
        for i in range(len(lines) - 1, search_start - 1, -1):
            if lines[i].strip().startswith('http'):
                url_count += 1
                if url_count >= 3:
                    footer_start_idx = max(0, i - 2)
                    break
            else:
                url_count = 0
    
    # Conservative: if no clear footer pattern found, return original unchanged
    if footer_start_idx is None:
        return text
    
    # Process main content (before footer)
    main_content = lines[:footer_start_idx]
    footer_content = lines[footer_start_idx:]
    
    # Patterns to remove from footer
    remove_patterns = [
        r'.*logo.*',
        r'.*badge.*',
        r'^facebook$',
        r'^twitter$',
        r'^x$',
        r'^instagram$',
        r'^youtube$',
        r'^linkedin$',
    ]
    
    # Extract important URLs from footer
    org_urls = []
    unsubscribe_info = None
    privacy_info = None
    view_browser_url = None
    copyright_line = None
    address_line = None
    
    i = 0
    while i < len(footer_content):
        line = footer_content[i].strip()
        line_lower = line.lower()
        
        # Skip remove patterns
        if any(re.match(pattern, line_lower) for pattern in remove_patterns):
            i += 1
            continue
        
        # Skip social media URLs
        if re.search(r'(facebook\.com|twitter\.com|instagram\.com|youtube\.com|linkedin\.com)', line_lower):
            i += 1
            continue
        
        # Skip badge/rating URLs
        if 'usnews.com' in line_lower or 'charitynavigator.org' in line_lower:
            i += 1
            continue
        
        # Capture main org URLs
        if ('dana-farber.org' in line or 'jimmyfund.org' in line) and '/site/' not in line and '/privacy' not in line:
            org_urls.append(line)
            i += 1
            continue
        
        # Capture unsubscribe
        if '/site/CO' in line or ('unsubscribe' in line_lower and line.startswith('http')):
            unsubscribe_info = f'Unsubscribe ({line})'
            i += 1
            # Skip previous "Unsubscribe" label line if exists
            continue
        
        # Capture privacy policy
        if 'privacy-policy' in line or ('privacy' in line_lower and 'policy' in line_lower and line.startswith('http')):
            privacy_info = f'Privacy Policy ({line})'
            i += 1
            continue
        
        # Capture view in browser
        if 'MessageViewer' in line or ('view' in line_lower and 'browser' in line_lower and line.startswith('http')):
            view_browser_url = line
            i += 1
            continue
        
        # Capture copyright
        if line.startswith('©'):
            copyright_line = line
            i += 1
            continue
        
        # Capture address (usually has numbers and "MA" or similar)
        if re.search(r'\d{5}(-\d{4})?', line):  # ZIP code pattern
            address_line = line
            i += 1
            continue
        
        i += 1
    
    # Rebuild footer in simplified format
    simplified_footer = []
    
    # Add separator
    simplified_footer.append('')
    simplified_footer.append('═' * 70)
    simplified_footer.append('')
    
    # Add org URLs on one line
    if org_urls:
        simplified_footer.append(' | '.join(org_urls))
        simplified_footer.append('')
    
    # Add unsubscribe
    if unsubscribe_info:
        simplified_footer.append(unsubscribe_info)
        simplified_footer.append('')
    
    # Add privacy policy
    if privacy_info:
        simplified_footer.append(privacy_info)
        simplified_footer.append('')
    
    # Add copyright
    if copyright_line:
        simplified_footer.append(copyright_line)
        simplified_footer.append('')
    
    # Add address
    if address_line:
        simplified_footer.append(address_line)
    
    # Combine main content with simplified footer
    result = main_content + simplified_footer
    
    return '\n'.join(result)


def clean_footer_section(text: str) -> str:
    """
    Clean up footer sections (unsubscribe links, addresses, etc.).
    
    Adds visual separator before footer if detected.
    """
    # Apply footer simplification
    text = simplify_footer(text)
    
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
        'css_stripped': False,
        'preview_text_found': False,
    }
    
    # Strip CSS blocks first
    text = strip_css_blocks(raw_text)
    if len(text) < len(raw_text) * 0.9:  # If we removed more than 10%, we likely found CSS
        stats['css_stripped'] = True
    
    # Detect and extract preview text
    preview_text, text = detect_preview_text(text)
    if preview_text:
        stats['preview_text_found'] = True
    
    # Join broken lines (fix mid-sentence breaks)
    text = join_broken_lines(text)
    
    # Start with normalized whitespace
    text = normalize_whitespace(text)
    
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
    
    # Add preview text at the top if found
    if preview_text:
        preview_section = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{preview_text}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text = preview_section + text
    
    stats['lines_after'] = len(text.split('\n'))
    
    return text, stats
