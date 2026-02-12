# Plain Text Email Beautifier — Technical Documentation

**Purpose**: Transform ugly plain text emails (from HTML-to-text conversions by marketing platforms) into readable, well-formatted plain text with clean URLs, joined sentences, formatted CTAs, and a simplified footer.

**Primary Use Case**: Luminate Online / Convio marketing platform emails. Most emails are **fundraising-related** (events, donations, volunteering).

---

## How It Works

### Processing Pipeline (Order Matters)

The `beautify_email()` function in `app/services/email_beautifier.py` runs these steps in sequence:

```
1. strip_css_blocks()     - Remove CSS, @media, style rules
2. detect_preview_text()  - Extract header/preview (e.g. "DFMC Logo")
3. join_broken_lines()   - Fix mid-sentence line breaks
4. normalize_whitespace() - Collapse blanks, trim
5. detect_ctas()         - Find call-to-action phrases + URLs
6. format_cta()          - Replace CTAs with >>> CTA: url <<<
7. clean_url()           - Strip tracking params from remaining URLs
8. convert_links_to_markdown() - Optional markdown conversion
9. simplify_footer()     - Identify footer, add visual break, remove social links
10. Add preview banner at top
```

### Key Design Decisions

#### Footer Detection (Critical — Was Previously Broken)

**Problem**: Early implementation triggered on first occurrence of "logo" or "dana-farber" anywhere, treating body content like "Dana-Farber Marathon Challenge runners..." as footer start. This removed most of the email.

**Solution**: Footer is identified from the **bottom half** of the document only:
- **Strategy 1**: Find any line ending with `" Logo"` (e.g. "Dana-Farber Logo") in the bottom 50% of lines. Everything beneath that line is footer.
- **Strategy 2**: Find 2+ consecutive social platform labels (Facebook, X, Instagram, etc.).
- **Strategy 3**: Find 3+ consecutive URLs in last 30%.

**Footer output**: Main content + visual break (`═══`) + simplified footer (main org URL only; social links removed).

#### CTA Detection — Standalone vs Body Copy

**Problem**: Words like "donate" and "RSVP" appear in body copy ("Please donate to our cause", "The event will sell out, so RSVP promptly!"). Early logic wrongly formatted these as CTAs.

**Solution**:
- **General CTAs**: Line before URL must be ≤50 chars.
- **Strict CTAs** (`donate`, `donate now`, `give now`, `volunteer`): Line must be ≤25 chars to avoid matching full sentences.

CTAs are standalone phrases followed immediately by a link, not part of longer sentences.

#### Line Joining — HTML Conversion Artifacts

Marketing platforms often produce text with irregular line breaks:
- Hyphenated words split: "pre-" / "race", "In-" / "Memory"
- Time ranges split: "4:00" on one line, "4:45 p.m." on next
- Mid-phrase breaks: "runners, friends," / "and family"
- Phrase continuations: "start to" / "race weekend", "from 4:00" / "4:45 p.m."

**Join rules**:
- Next line starts with lowercase → join
- Line ends with hyphen → join (hyphenated word continuation)
- Line ends with comma/semicolon → join
- Line ends with " from", " to", " and", " or" → join
- Line ends with time (4:00, p.m., a.m.) → join
- Line <85 chars, doesn't end with punctuation, next starts uppercase → join

---

## Configuration Constants

Located at top of `app/services/email_beautifier.py`:

| Constant | Purpose |
|----------|---------|
| `TRACKING_PARAMS` | Query params to strip from URLs (utm_*, aff, s_src, fbclid, etc.) |
| `CTA_PHRASES` | Phrases that indicate a CTA (click here, donate, RSVP, etc.) |
| `STRICT_CTA_PHRASES` | Phrases that require short line (donate, volunteer, give now) |
| `STRICT_CTA_MAX_LEN` | Max 25 chars for strict CTA lines |

---

## Test Fixtures

- **Input**: `tests/fixtures/textemail.txt` — Sample from marketing platform (CSS + event email)
- **Expected output**: `tests/fixtures/textemail_expected.txt` — Regenerate with the beautifier
- **Tests**: `tests/test_email_beautifier.py` — Unit and integration tests

**Run tests**:
```bash
PYTHONPATH=. python3 -m unittest tests.test_email_beautifier -v
```

---

## Iterative Improvement Workflow

### Before Making Changes

1. **Read this document** and `app/services/email_beautifier.py`.
2. **Run existing tests** — ensure baseline passes.
3. **Identify the function** to modify (strip_css, join_broken_lines, simplify_footer, detect_ctas, etc.).

### Making Changes Safely

1. **Add a failing test first** (or use the sample fixture) that demonstrates the desired behavior.
2. **Modify one concern at a time** — e.g. only footer logic, only line joining.
3. **Run tests after each change** — `python3 -m unittest tests.test_email_beautifier -v`.
4. **Test with real sample** — paste `tests/fixtures/textemail.txt` into the UI at `/email-beautifier`.
5. **Update this doc** if you add new rules, constants, or change behavior.

### Pitfalls to Avoid

| Pitfall | Why It Fails |
|---------|--------------|
| Triggering footer on "logo" at top | "DFMC Logo" is header; footer logos are in bottom half |
| Matching body copy as CTA | "The event will sell out, so RSVP promptly!" is a sentence, not CTA |
| Over-joining lines | Don't join across paragraphs; respect empty lines |
| Removing main content | Footer simplification must only affect content *beneath* footer marker |
| Adding CTA phrase without length check | "donate" in "You can donate online at..." would be false positive |

### Adding New CTA Phrases

1. Add to `CTA_PHRASES` in `email_beautifier.py`.
2. If the phrase often appears in body copy (e.g. "volunteer", "register"), add to `STRICT_CTA_PHRASES` so it only matches when line ≤25 chars.
3. Add a test in `tests/test_email_beautifier.py` that verifies detection.
4. Test with sample that has the phrase in body copy to ensure no false positive.

### Adding New Tracking Params

Add to `TRACKING_PARAMS` set. Use lowercase. Common additions: `aff`, `ref`, `ref_src`, `cmpid`.

---

## API

- **Endpoint**: `POST /api/email-beautifier/process`
- **Request**: `{ raw_text, strip_tracking?, format_ctas?, markdown_links? }`
- **Response**: `{ success, beautified_text, stats, message }`
- **UI**: `/email-beautifier`

---

## Reference: Sample Input/Output

**Input** (abbreviated): CSS block + "DFMC Logo" + URLs + event details + "RSVP Today" + body + "Dana-Farber Logo" + social links.

**Output**: Preview banner, cleaned content with joined sentences, CTA formatted with visual bounce, footer with `═══` and org URL only.
