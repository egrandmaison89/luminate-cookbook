# AI Agent Guide — Building on Progress

This document helps AI assistants (Cursor, Copilot, etc.) make changes that **build upon** existing work without breaking it. Read this before modifying code or docs.

**QA before “done”**: Run tests, fix failures, then update docs. Full checklist: [AGENT_QA.md](AGENT_QA.md).

---

## Document Trail — What to Read First

| Task | Read First | Then |
|------|------------|------|
| Email Beautifier changes | [EMAIL_BEAUTIFIER.md](EMAIL_BEAUTIFIER.md) | `app/services/email_beautifier.py` |
| Banner Processor changes | [BANNER_PROCESSOR_TECHNICAL.md](BANNER_PROCESSOR_TECHNICAL.md) | `app/services/banner_processor.py` |
| Architecture / new features | [ARCHITECTURE.md](ARCHITECTURE.md) | Relevant service + `app/main.py` |
| Deployment | [DEPLOYMENT.md](DEPLOYMENT.md), [GOOGLE_CLOUD_RUN.md](GOOGLE_CLOUD_RUN.md) | — |

---

## Before Making Any Change

1. **Read the relevant doc** — Each major feature has a technical doc with design decisions and pitfalls.
2. **Run existing tests** — `PYTHONPATH=. python3 -m unittest tests.test_<module> -v`
3. **Understand the pipeline** — Many tools have ordered steps; changing order or one step can break others.
4. **When done** — Re-run tests, then update documentation and changelog as in [Change Workflow](#change-workflow-preserve-progress). Do not announce completion without verification; if tests fail, debug and fix first ([AGENT_QA.md](AGENT_QA.md)).

---

## Change Workflow (Preserve Progress)

### 1. Add Tests Before or With Changes

- New behavior → add a test that asserts it.
- Bug fix → add a regression test so it doesn't recur.
- Tests live in `tests/`; fixtures in `tests/fixtures/`.

### 2. Modify One Concern at a Time

- Avoid bundling unrelated edits (e.g. footer + CTA + line joining in one change).
- Smaller, focused changes are easier to debug and revert if needed.

### 3. Run Tests After Each Change

```bash
PYTHONPATH=. python3 -m unittest tests.test_email_beautifier -v
```

### 4. Update Documentation (required for iterative changes)

- **Same iteration as the code change** — do not leave the repo with outdated API text, feature descriptions, or dependency lists.
- If you change behavior, constants, or add rules: update the feature technical doc and any affected sections in the root [README.md](../README.md).
- If you add a new module, route, or dependency: update [README.md](../README.md) (API table, project tree, or tech stack) and [docs/README.md](README.md) index if the doc set changes.
- New feature: add a section to its technical doc; link from docs index when appropriate.

### 5. Update CHANGELOG.md

- Add an entry under `[Unreleased]` or a new version.
- Brief description of what changed and why (for future sessions).

### 6. Thorough QA (mandatory)

Follow [AGENT_QA.md](AGENT_QA.md): run tests, smoke-test when relevant, and only then treat the work as complete. If something fails, debug and re-run before moving on.

---

## Email Beautifier — Lessons Learned

These issues were encountered and fixed. Avoid reintroducing them:

| Issue | Root Cause | Fix |
|-------|------------|-----|
| Most content removed | Footer detection triggered on "logo" or "dana-farber" in body | Footer only in bottom 50%; "X Logo" pattern in that region |
| "RSVP promptly!" formatted as CTA | Line before URL contained "rsvp" but was full sentence | Max 50 chars for general CTAs; 25 for strict (donate, volunteer) |
| "Donate" in body matched | Phrase match without length check | STRICT_CTA_PHRASES + STRICT_CTA_MAX_LEN |
| "pre-race", "In-Memory" broken | No hyphen-handling in join_broken_lines | Join when line ends with `-` |
| Time ranges split across lines | No time-pattern joining | Join when line ends with 4:00, p.m., a.m. |
| Footer not detected | "Dana-Farber Logo" was outside last 15 lines | Search bottom 50% for " Logo" pattern |

---

## Leaving a Trail for Future Conversations

When you make meaningful changes:

1. **Update the feature's technical doc** — Describe new logic, constants, and gotchas.
2. **Add a CHANGELOG entry** — Version, date, what changed.
3. **Add or update tests** — Tests are executable documentation.
4. **Add brief code comments** — For non-obvious logic (e.g. why 25 chars for strict CTAs).

Future AI sessions can grep for recent CHANGELOG entries, read the technical doc, and run tests to understand current state.

---

## Quick Reference

**Email Beautifier files**:
- Services: `app/services/email_html_to_text.py` (HTML → plain), `app/services/email_beautifier.py` (plain-text beautify + `beautify_email_from_html`)
- Tests: `tests/test_email_beautifier.py`
- Fixtures: `tests/fixtures/textemail.txt` (plain text for `beautify_email` tests)
- Docs: [docs/EMAIL_BEAUTIFIER.md](EMAIL_BEAUTIFIER.md), [docs/AGENT_QA.md](AGENT_QA.md)

**Run dev server**: `uvicorn app.main:app --reload --port 8000` (from project root)
**Email Beautifier UI**: http://localhost:8000/email-beautifier
