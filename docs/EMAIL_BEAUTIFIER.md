# Email Beautifier (HTML → Plain Text) — Technical Documentation

**Purpose**: Take the **HTML source** of a marketing email (Luminate / Convio style), convert it to readable plain text, then apply cleanup: tracking-free URLs, joined lines, optional CTA emphasis, simplified footer, optional markdown links.

**Primary use case**: Fundraising and event email. The UI accepts **pasted HTML** or an **uploaded `.html` file**.

**Core code**:

- `app/services/email_html_to_text.py` — HTML parsing (BeautifulSoup), html2text conversion, preheader extraction, removal of tracking pixels / noise, normalization of html2text “protected” links (`[label](<https://…>)` → `[label](https://…)`).
- `app/services/email_beautifier.py` — `beautify_email()` (plain-text pipeline) and `beautify_email_from_html()` (HTML path: `email_html_to_plain_text` → `beautify_email`).

---

## End-to-end pipeline (HTML input)

```
1. email_html_to_plain_text()
   - Optional document wrapper for fragments
   - Extract preheader from hidden <td> (display:none / mso-hide / font-size:0), remove cell to avoid duplication
   - Remove script, style, noscript, comments; EOA tracking div/img; tiny/tracking images
   - html2text (body_width=0, protect_links) → normalize [label](<url>) brackets
   - Strip table markdown junk (pipes, ---), ": |" column artifacts; image markdown → [Image: alt] / banner short labels; unwrap **bold**
   - Prepend preheader if missing from body text

2. beautify_email() on the resulting plain text
   - strip_css_blocks()        (leftover CSS if any)
   - detect_preview_text()
   - join_broken_lines()
   - normalize_whitespace()
   - detect_ctas() / format_cta()
   - clean_url() on URLs (tracking param strip)
   - convert_links_to_markdown() — skips URLs already inside existing [text](url) markdown
   - simplify_footer() + preview banner
```

---

## Plain-text–only path

`beautify_email(raw_text=...)` is still used for **tests and fixtures** (`tests/fixtures/textemail.txt`) that are already plain text. Production UI and API expect **HTML**.

---

## Key design decisions (unchanged from plain-text era)

#### Footer detection

Footer is determined from the **bottom half** of the document. Primary marker: a line ending with `" Logo"`. See previous sections in git history for full strategies.

#### CTA detection

Standalone phrases (≤50 chars; ≤25 for strict donate/volunteer/give) near URLs, not long sentences. See `STRICT_CTA_*` in code.

#### Line joining

Fixes mid-sentence breaks common after HTML→text (hyphens, times, comma continuations, etc.).

#### Markdown link conversion

`convert_links_to_markdown` must **not** wrap URLs that already sit immediately after `](` (markdown link syntax), and HTML conversion normalizes `(<https` wrappers so `clean_url` does not break links.

---

## Configuration constants

| Location | Notes |
|----------|--------|
| `TRACKING_PARAMS` in `email_beautifier.py` | utm_*, s_src, s_subsrc, aff, ref, fbclid, etc. |
| `CTA_PHRASES`, `STRICT_CTA_*` | CTA detection |

---

## Test fixtures and tests

| Item | Role |
|------|------|
| `tests/fixtures/textemail.txt` | Legacy plain-text sample; exercises `beautify_email` directly |
| `tests/test_email_beautifier.py` | Unit + integration tests including `beautify_email_from_html` |

**Run tests**:

```bash
PYTHONPATH=. python3 -m unittest tests.test_email_beautifier -v
```

**Manual check**: `uvicorn app.main:app --reload --port 8000` → `/email-beautifier` (paste HTML or upload file).

---

## API

- **Endpoint**: `POST /api/email-beautifier/process`
- **Content types**:
  - `application/json` — body includes `html` (string) and optional `strip_tracking`, `format_ctas`, `markdown_links` (booleans).
  - `multipart/form-data` — field `file` = `.html` file, same option fields as form fields.
- **Response**: `{ success, beautified_text, stats, message, error? }`
- **Stats** may include: `urls_cleaned`, `ctas_formatted`, `links_converted`, `lines_before`, `lines_after`, `css_stripped`, `preview_text_found`, `source: "html"`

**JSON example**:

```json
{
  "html": "<html><body>…</body></html>",
  "strip_tracking": true,
  "format_ctas": true,
  "markdown_links": true
}
```

- **UI**: `/email-beautifier`

---

## Iterative improvement workflow

1. Read this doc and the two service files above.
2. Run `PYTHONPATH=. python3 -m unittest tests.test_email_beautifier -v` (must pass before merge).
3. If changing HTML conversion, add or extend a test with a small HTML snippet.
4. Update **this doc** and `README.md` / `CHANGELOG.md` when behavior or API changes.
5. See [AGENT_QA.md](AGENT_QA.md) and [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md) for full QA and documentation expectations.

---

## Pitfalls

| Pitfall | Mitigation |
|---------|------------|
| html2text `[label](<https://...>)` breaks URL regex passes | `_normalize_protected_link_brackets` in `email_html_to_text.py` |
| `convert_links_to_markdown` double-wrapping | Skip URL matches where `](` immediately precedes the URL |
| Multi-column table layout | May duplicate or reorder lines; table-to-text is inherently lossy |
| Hiding preheader in HTML | Extracted in BS pass; if ESP uses another pattern, extend `_extract_preheader` |
