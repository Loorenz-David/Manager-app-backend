# PLAN_quote_stripper_fallback_fix_20260706

## Metadata

- Plan ID: `PLAN_quote_stripper_fallback_fix_20260706`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-06T09:00:00Z`
- Last updated at (UTC): `2026-07-06T09:30:00Z`
- Related issue/ticket: `Post-implementation review of PLAN_strip_quoted_reply_history_20260706`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_quote_stripper_fallback_fix_20260706.md`

## Goal and intent

- Goal: Fix a reproduced correctness bug in the quote-stripping feature delivered by `PLAN_strip_quoted_reply_history_20260706` (archived at `backend/docs/architecture/archives/implementation/PLAN_strip_quoted_reply_history_20260706.md`, summarized at `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_strip_quoted_reply_history_20260706.md`). The regex-based fallback path — which activates whenever `email-reply-parser` isn't importable — fails to strip the quoted trailer on the exact real-world message that motivated the original plan, because its header regex requires "On ... wrote:" to sit on a single physical line, which real Gmail-generated quote headers do not when the sender name+email is long enough to wrap.
- Business/user intent: Verified by direct execution: this project's own checked-in `.venv` does not have `email-reply-parser` installed despite it being declared in `requirements.txt`, meaning the buggy fallback is the code path actually running today. Any inbound sync executed in this environment right now produces a `text_body_clean` that still contains the quoted trailer for line-wrapped headers — the exact defect the original plan was built to eliminate.
- Non-goals:
  - Do NOT remove the fallback path entirely. Graceful degradation has real value: if `email-reply-parser` is ever unavailable in some environment, inbound sync should still succeed with best-effort stripping rather than failing outright. The fallback should be fixed and made visible, not deleted.
  - Do NOT re-litigate the library choice — `email-reply-parser` remains the correct primary path (already verified correct in review) and is not being replaced.
  - Do NOT touch the Alembic migration head-merge from the original plan — independently verified structurally correct (single true head, no orphaned branches) and out of scope for this correction.
  - Do NOT backfill historical `email_messages.text_body_clean` rows — still deferred, as in the original plan.

## Scope

- In scope:
  1. Install `email-reply-parser==0.5.12` into the project's checked-in `.venv` now, closing the immediate operational gap in this environment.
  2. Fix `_strip_quoted_reply_fallback`'s quote-header detection in `quote_stripper.py` so it correctly identifies "On <date>, <name> <email> wrote:" headers that wrap across multiple physical lines (the reproduced bug), not just single-line headers.
  3. Add a one-time (per-process) warning log when the fallback path activates instead of the primary library, so this drift is never silent again.
  4. Add regression test coverage that (a) uses the exact real-world example from the bug report (long sender name/email causing line-wrap) and (b) explicitly exercises the fallback branch regardless of whether `email-reply-parser` happens to be installed in the test environment, so this specific regression cannot silently reappear.
- Out of scope:
  - Any change to `email_reply_parser`'s own behavior (it's already verified correct; only the fallback needs fixing).
  - CI/deployment pipeline changes to guarantee `requirements.txt` is always installed fresh — noted as a risk/mitigation below, not an implementation task here.
  - The Alembic migration merge and historical backfill (Non-goals).
- Assumptions:
  - The fallback's line-wrap bug is specifically in `_QUOTE_HEADER_PATTERNS`'s first pattern (`re.compile(r"(?im)^\s*On .+wrote:\s*$")`), which anchors both "On " and "wrote:" to the same line via `^...$` under `MULTILINE` — confirmed by direct execution reproducing the exact failure and by tracing the regex logic.
  - `>`-quoted-line detection (the second heuristic in `_find_quote_start`) already works correctly and is not implicated in this bug — the failure is specifically that the header-line regex fails to match first, causing the header lines to be left in front of the (correctly detected) quoted body.

## Clarifications required

None — the fix is a bounded regex/observability correction with a clear, already-reproduced test case to validate against.

## Acceptance criteria

1. With `email-reply-parser` NOT importable (simulating the fallback path, e.g. via monkeypatching `EmailReplyParser = None` in a test), `strip_quoted_reply(...)` on the exact real-world example from `emsg_01KWS4FFSTQR3MV74CAZVNXJJ1` (new content, followed by a two-line-wrapped "On Sun, Jul 5, 2026 at 2:34 PM Test Beyo Vintage <loorenz.david@gmail.com>\nwrote:", followed by `>`-quoted Swedish text) returns exactly the new content ("yes yes fast"), matching the original plan's Acceptance Criterion 1.
2. The existing fallback test (`test_strip_quoted_reply_removes_reply_history`) continues to pass, and a new test using the longer, line-wrapping sender identity is added alongside it — both must pass.
3. A single-line "On ... wrote:" header (the previously-only-tested case) continues to strip correctly — no regression on the case that already worked.
4. When the fallback path activates, exactly one warning-level log line is emitted per process (not once per message — avoid log spam on high-volume inbox syncs), clearly stating that `email-reply-parser` is unavailable and the regex fallback is in use.
5. `email-reply-parser==0.5.12` is installed and importable in this project's `.venv`, confirmed by `python -c "import email_reply_parser"` succeeding.
6. No change in behavior for the primary (library-based) path — it was already verified correct in review and must remain the preferred path whenever available.

## Contracts and skills

### Contracts loaded

- None beyond what the original plan already loaded — this is a narrow correctness fix within an already-reviewed contract boundary (`smtp_imap/quote_stripper.py`).

### Local extensions loaded

- None expected.

### File read intent — pattern vs. relational

Relational reads already performed and sufficient — do not re-read broadly:
- `services/infra/email_providers/smtp_imap/quote_stripper.py` — the file being corrected; bug confirmed to live in `_QUOTE_HEADER_PATTERNS[0]` and how `_find_quote_start` sequences the header-check before the `>`-quote-run check.
- `tests/emails/test_email_core.py` — existing test coverage; confirmed `test_strip_quoted_reply_removes_reply_history` uses a shortened sender identity that avoids triggering the line-wrap this bug depends on.
- `requirements.txt` — already correctly declares `email-reply-parser==0.5.12`; no change needed there, only to the local `.venv`'s installed state.

### Skill selection

- Primary skill: n/a (targeted regex/logging/test correction to an already-reviewed file).
- Router trigger terms: `quote stripping regression, fallback regex, line-wrapped header, silent dependency fallback`.
- Excluded alternatives: none — this is a direct bugfix with no architectural fork.

## Implementation plan

1. **Install the dependency now.** Run `pip install -r requirements.txt` (or targeted `pip install email-reply-parser==0.5.12`) in the project's `.venv` so the primary path is active in this environment immediately. This alone fixes today's live behavior; steps 2-4 fix the fallback so it's correct even when the primary path is genuinely unavailable elsewhere.
2. **Fix the header regex.** In `quote_stripper.py`, replace the single-line-anchored pattern with one that tolerates the header wrapping across a bounded number of lines — e.g. drop the `^...$` per-line anchoring for this pattern and instead search with something like `re.compile(r"On\b.{0,300}?wrote:", re.IGNORECASE | re.DOTALL)` (bounded `.` span to avoid runaway/greedy matches across an entire long email), used as a `search()` over the full text rather than a per-line match. Verify it still correctly finds the match's start position for truncation via `_find_quote_start`, and that it doesn't false-positive on legitimate message content that happens to contain "On" and "wrote" far apart (the bounded `{0,300}` window guards against this).
3. **Add a one-time fallback warning.** In `quote_stripper.py`, when `EmailReplyParser is None` and the fallback path is about to run for the first time in the process, emit `logger.warning(...)` once (e.g. guard with a module-level flag, mirroring the "log once" pattern rather than logging per-message) stating that `email-reply-parser` is not installed and quote stripping is using the regex fallback.
4. **Add regression tests to `tests/emails/test_email_core.py`:**
   - A new test using the exact real-world example (long sender name/email causing the "On ... wrote:" line wrap) asserting correct stripping via `strip_quoted_reply` with the fallback forced active (monkeypatch `quote_stripper.EmailReplyParser = None` for the duration of the test, restoring afterward).
   - Confirm the existing single-line-header fallback test and the library-based tests (`test_mime_parser_uses_clean_text_for_preview`, etc.) still pass unchanged.
5. **Verify end-to-end.** Re-run the exact reproduction from the review (the literal `emsg_01KWS4FFSTQR3MV74CAZVNXJJ1` text) through `strip_quoted_reply` with the library present and with it forced absent — both must now yield `"yes yes fast"`.

## Risks and mitigations

- Risk: The bounded `.{0,300}?` window in the new regex could still miss a header that wraps across an unusually long multi-line "On ... wrote:" (e.g. many CC'd names).
  Mitigation: 300 characters comfortably covers realistic single-sender headers (name + email rarely exceeds ~100 characters); the raw `text_body` remains the untouched fallback of last resort regardless, so even a missed match degrades to "no stripping" rather than data loss.
- Risk: Making the regex `DOTALL`/non-anchored could make it match inside the quoted body itself (double-processing) in unusual message structures.
  Mitigation: `_find_quote_start` only needs the match's start offset, and `text[:quote_start]` truncation is inherently safe even if the match extends further than expected — the truncation point is what matters, not the match's end.
- Risk: The "log once per process" pattern for the fallback warning could still mean it's easy to miss in high-noise logs.
  Mitigation: Out of scope to build deeper observability (e.g. a metrics counter or alert) in this pass; a clear, greppable warning message is the minimum bar for this correction. Revisit if this recurs.
- Risk: This project's checked-in `.venv` drifting out of sync with `requirements.txt` again in the future (the root cause of why this bug went live undetected).
  Mitigation: Not fixed by this plan (process/tooling concern, not code) — flagged here for awareness; consider a CI step or pre-commit check that diffs installed packages against `requirements.txt` as a separate, future initiative.

## Validation plan

- Static: `ruff check services/infra/email_providers/smtp_imap/quote_stripper.py tests/emails/test_email_core.py` + type check.
- Direct reproduction: run the exact bug-report text through `strip_quoted_reply` twice — once with `email_reply_parser` importable, once with it monkeypatched to `None` — and confirm both yield `"yes yes fast"`.
- Full test suite: `pytest tests/emails/test_email_core.py` — all existing tests plus the new fallback-specific regression test must pass.
- Dependency check: `python -c "import email_reply_parser"` succeeds in the project `.venv` with no error.
- Log check: trigger the fallback path (library absent) twice in the same process and confirm the warning log line appears exactly once, not twice.

## Review log

- `2026-07-06` `claude`: Drafted after a post-implementation review of `PLAN_strip_quoted_reply_history_20260706` reproduced, by direct execution, that the regex fallback (the explicitly rejected approach from that plan's Decisions log) is the code path actually active in this project's `.venv`, and that it fails to strip the quoted trailer on the exact real-world example the original plan was built around. Verified the primary library path is correct once installed, and that the existing test suite's fallback test avoids the line-wrap case that triggers the bug due to using a shortened sender identity.
- `2026-07-06` `david`: Approved for direct implementation by claude (no handoff to codex — scope was small and already fully diagnosed).
- `2026-07-06` `claude`: Implemented all four in-scope items. Installed `email-reply-parser==0.5.12` into the project `.venv`; fixed `_QUOTE_HEADER_PATTERNS`'s header regex to tolerate line-wrapped "On ... wrote:" headers (bounded, non-anchored, `DOTALL` pattern replacing the single-line `^...$` anchor); added a one-time-per-process warning log guarded by a module-level flag when the fallback path activates; added two regression tests to `tests/emails/test_email_core.py` — one forcing the fallback branch via monkeypatching `EmailReplyParser = None` and replaying the exact real-world line-wrapped example, one asserting the warning logs exactly once across repeated fallback calls. Verified via direct execution that both the library path and the fixed fallback path now return `"yes yes fast"` for the original bug report text. Full test suite (11 tests, up from 9), `ruff check`, and `py_compile` all pass.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `claude`
