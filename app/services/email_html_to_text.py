"""
Convert marketing / HTML emails to readable plain text for the beautifier pipeline.

Uses BeautifulSoup to strip noise and extract preheader text, then html2text for
structure-preserving conversion. Post-processes to remove table-artifact pipes,
convert image markdown to plain labels, and unwrap bold for a clean plain-text handoff.
"""

from __future__ import annotations

import re
from html import unescape
from typing import Optional, Tuple

import html2text
from bs4 import BeautifulSoup, Comment

# Phrases in hidden preview cells to ignore
_PREVIEW_PLACEHOLDER_TOKENS = frozenset(
    {"<!--preview text-->", "preview text here", "put-in-normail-email-tracking-here"}
)


def _unwrap_wrapped_html_fragment(html: str) -> str:
    """Ensure parser sees a document root; fragments are wrapped."""
    t = html.strip()
    if not t:
        return t
    if re.search(r"<\s*html\s", t, re.I):
        return t
    return f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body>{t}</body></html>"


def _strip_noise_tags(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["script", "style", "noscript", "title"]):
        tag.decompose()
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()
    for tag in soup.find_all(id="_eoa_div"):
        tag.decompose()
    for tag in soup.find_all(id="_eoa_img"):
        tag.decompose()
    for img in soup.find_all("img"):
        src = (img.get("src") or "").lower()
        w, h = str(img.get("width", "")), str(img.get("height", ""))
        if "eoapxl" in src or "eoa_img" in src:
            img.decompose()
            continue
        if w in ("0", "1") and h in ("0", "1"):
            if not (img.get("alt") or "").strip():
                img.decompose()
                continue
        if "gmailspacer" in src or "spacer.gif" in src:
            img.decompose()


def _td_style_suggests_preheader(td) -> bool:
    st = (td.get("style") or "") + " " + " ".join(td.get("class") or [])
    st = st.lower().replace(" ", "")
    if "display:none" in st or "max-height:0" in st:
        return True
    if "font-size:0" in st and "line-height:0" in st:
        return True
    if "mso-hide:all" in st:
        return True
    return False


def _extract_preheader(soup: BeautifulSoup) -> Tuple[Optional[str], bool]:
    """
    Pull inbox preview line from a hidden <td> (common in Luminate/Convio).
    Returns (text, found_hidden_cell). If we found a cell, it is decomposed
    to avoid duplicating the line in the main conversion.
    """
    for td in soup.find_all("td"):
        if not _td_style_suggests_preheader(td):
            continue
        text = " ".join(td.get_text(" ", strip=True).split())
        if not text:
            continue
        low = text.lower()
        if any(tok in low for tok in _PREVIEW_PLACEHOLDER_TOKENS):
            continue
        if "*/link:" in text or "unsubscribe" in low and "/*" in text:
            continue
        td.decompose()
        return text, True
    return None, False


def _postprocess_table_artifacts_and_pipes(text: str) -> str:
    """Remove html2text markdown table junk (pipes, separator rows) from email tables."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s in ("---", "|", "***"):
            continue
        if re.match(r"^[\-:| \t\u00a0]+$", s) and len(s) > 0:
            continue
        while True:
            t = line.lstrip()
            if t.startswith("|"):
                line = line[1:].lstrip(" \t")
            else:
                break
        line = re.sub(r"\s*\|\s*$", "", line)
        out.append(line.rstrip())
    text = "\n".join(out)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Two-column table leftovers: "Label: | Name"
    text = re.sub(r":\s*\|\s*", ": ", text)
    return text.strip()


def _image_markdown_to_plain(m: re.Match) -> str:
    alt = (m.group(1) or "").strip()
    url = m.group(2) or ""
    ulow = url.lower()
    if any(
        p in ulow
        for p in (
            "gmailspacer",
            "spacer.gif",
            "eoapxl",
            "1x1",
            "tracking",
            "pixel",
        )
    ):
        return ""
    if not alt:
        if any(p in ulow for p in ("banner", "evitebanner", "broadcast", "comms_")):
            return "[Banner image]"
        return "" if "pagebuilder" in ulow and "logo" not in ulow else f"[Image]({url})"
    if len(alt) < 200:
        return f"[Image: {alt}]"
    return f"[Image: {alt[:197]}...]"


def _postprocess_image_and_bold_markdown(text: str) -> str:
    # ![alt](url) from html2text
    text = re.sub(
        r"!\[([^\]]*)\]\((https?://[^)\s]+)\)",
        lambda m: _image_markdown_to_plain(m) or "\0DROP\0",
        text,
    )
    # Drop empty placeholders from removed images
    text = text.replace("\0DROP\0", "")
    # **bold** -> plain (readable without markdown)
    text = re.sub(r"\*\*([^*]+?)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+?)\*", r"\1", text)
    return text


def _collapse_blank_runs(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _normalize_protected_link_brackets(text: str) -> str:
    """
    html2text with protect_links emits [label](<https://url>); remove inner <> so
    downstream URL cleaning and markdown handling see [label](https://url).
    """
    text = re.sub(
        r"\[([^\]]+)\]\(<(https?://[^>]+)>\)",
        r"[\1](\2)",
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(<(mailto:[^>]+)>\)",
        r"[\1](\2)",
        text,
    )
    return text


def email_html_to_plain_text(html: str) -> str:
    """
    Convert an HTML email string to plain text suitable for :func:`beautify_email`.

    Strips styles/scripts, tracking pixels, preheader cells (injected at top if extracted),
    runs html2text, then polishes for human-readable plain text.
    """
    if not html or not html.strip():
        return ""
    raw = _unwrap_wrapped_html_fragment(html)
    soup = BeautifulSoup(raw, "html.parser")
    preheader, _ = _extract_preheader(soup)
    _strip_noise_tags(soup)

    h2t = html2text.HTML2Text()
    h2t.body_width = 0
    h2t.unicode_snob = True
    h2t.ignore_emphasis = False
    h2t.ignore_images = False
    h2t.images_to_alt = True
    h2t.default_image_alt = ""
    h2t.skip_internal_links = True
    h2t.ignore_links = False
    h2t.protect_links = True

    text = h2t.handle(str(soup))
    text = unescape(text)
    text = _normalize_protected_link_brackets(text)
    text = _postprocess_table_artifacts_and_pipes(text)
    text = _postprocess_image_and_bold_markdown(text)
    text = _collapse_blank_runs(text)
    if preheader:
        head = preheader.strip()
        tlow = (text or "").lower()[: min(len(head) + 20, 400)]
        if not head.lower() in tlow:
            text = f"{head}\n\n{text}" if text else head
    return text
