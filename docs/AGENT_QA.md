# Agent QA: Verify Before “Done”

This project expects **thorough verification** of any change before it is considered complete. A change is not finished until the checks below have passed (or a documented reason is given, for example a known environment limitation).

---

## 1. Run automated tests

- Run the **relevant** test module(s), for example:
  ```bash
  cd /path/to/luminate-cookbook
  PYTHONPATH=. python3 -m unittest tests.test_email_beautifier -v
  ```
- If you touched multiple areas, run the full suite you can reasonably run:
  ```bash
  PYTHONPATH=. python3 -m pytest tests/ -q
  # or
  PYTHONPATH=. python3 -m unittest discover -s tests -v
  ```
- **Do not** report work as complete if tests were not run and failing tests were not fixed or explained.

---

## 2. If something fails: debug before continuing

1. **Read the failure** (traceback, assertion message, diff).
2. **Reproduce** in isolation (single test, minimal input).
3. **Fix the root cause**; avoid papering over with skips unless the skip is documented and justified.
4. **Re-run** the same tests until they pass.
5. Only then move on to documentation or the next feature.

Stating that a change “should work” without running tests is not sufficient.

---

## 3. Manual or smoke checks (when the change is user-facing or API)

- For web flows: start the app (`uvicorn app.main:app --reload --port 8000`) and exercise the **actual** page or `curl` the **actual** endpoint when feasible.
- For CLI-only changes: run the command with a representative input.
- If you cannot run (for example no network in CI), say what was run locally and what remains for the user to verify.

---

## 4. Update documentation in the same iteration

When you change behavior, APIs, dependencies, or file layout, update the docs **in the same change set** so the repo does not lie to the next human or agent.

- Feature behavior: that feature’s technical doc (e.g. `docs/EMAIL_BEAUTIFIER.md`).
- APIs and request bodies: `README.md` and/or `docs/ARCHITECTURE.md` as appropriate.
- Process for future agents: `docs/AI_AGENT_GUIDE.md` and this file when the workflow changes.
- Notable user-visible changes: `CHANGELOG.md` under `[Unreleased]` (or a dated section).

See also: [AI Agent Guide — Change Workflow](AI_AGENT_GUIDE.md).

---

## 5. Definition of “complete”

Work is **complete** when:

- Relevant tests pass (or failures are explicitly deferred with written justification).
- Docs and `CHANGELOG` reflect the change if it affects how the project is used or maintained.
- No known regressions are left unmentioned.

---

## Quick reference (Email Beautifier example)

```bash
PYTHONPATH=. python3 -m unittest tests.test_email_beautifier -v
# UI: http://localhost:8000/email-beautifier
```

For other tools, use the test modules under `tests/` and the feature docs in `docs/`.
