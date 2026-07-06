# SUMMARY_PLAN_quote_stripper_fallback_fix_20260706

## Metadata

- Summary ID: `SUMMARY_PLAN_quote_stripper_fallback_fix_20260706`
- Status: `summarized`
- Owner agent: `claude`
- Created at (UTC): `2026-07-06T09:30:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_quote_stripper_fallback_fix_20260706.md`
- Related debug plan (optional): `—`

## What was implemented

- Installed the already-declared `email-reply-parser==0.5.12` dependency into the project's `.venv`, closing the gap where the primary quote-stripping library was declared in `requirements.txt` but not actually importable in this environment.
- Fixed the regex fallback's quote-header detection in `quote_stripper.py`: replaced the single-line-anchored `^\s*On .+wrote:\s*$` pattern (which failed whenever a mail client wrapped the "On <date>, <name> <email> wrote:" header across two physical lines) with a bounded, non-anchored, `DOTALL` pattern (`On\b.{0,300}?wrote:`) that tolerates the wrap while still bounding the match to avoid runaway/false-positive spans.
- Added a one-time-per-process warning log (guarded by a module-level flag) that fires when the fallback path activates instead of the primary library, so this degraded state can no longer go unnoticed.
- Added two regression tests to `tests/emails/test_email_core.py`: one that forces the fallback branch via monkeypatching `EmailReplyParser = None` and replays the exact real-world line-wrapped example from the original bug report; one that asserts the fallback warning logs exactly once across repeated calls, not once per message.

## Files changed

- `backend/app/beyo_manager/services/infra/email_providers/smtp_imap/quote_stripper.py`: fixed the header regex, added the logger and one-time fallback warning.
- `backend/tests/emails/test_email_core.py`: added the two regression tests and the corresponding `quote_stripper` module import.
- `backend/app/.venv`: installed `email-reply-parser==0.5.12` (already declared in `requirements.txt`; no dependency-manifest change needed).

## Contract adherence

- Followed the plan's explicit Non-goal boundaries: the fallback path was fixed, not removed (preserves resilience if the library is ever genuinely unavailable); the library choice from the original plan was not re-litigated; the Alembic migration head-merge and historical backfill from the prior plan were untouched.
- `backend/skills/_shared/plan_lifecycle_contract.md`: plan progressed `under_construction` → `approved` → `implemented` → `summarized` → `archived` in the required order, with validation evidence attached before summarization.

## Validation evidence

- Direct reproduction: the exact real-world text from `emsg_01KWS4FFSTQR3MV74CAZVNXJJ1` (long sender name/email causing the header to wrap across two lines) now strips to `"yes yes fast"` both with `email-reply-parser` installed and with it forced absent (monkeypatched to `None`) — confirmed by direct script execution before writing the permanent tests.
- `./.venv/bin/python -m pytest ../tests/emails/test_email_core.py -v`: passed (`11 passed`, up from the prior 9 — the two new regression tests included).
- `./.venv/bin/python -m ruff check beyo_manager/services/infra/email_providers/smtp_imap/quote_stripper.py ../tests/emails/test_email_core.py`: passed, no findings.
- `python3 -m py_compile beyo_manager/services/infra/email_providers/smtp_imap/quote_stripper.py ../tests/emails/test_email_core.py`: passed.
- `pip freeze | grep email-reply-parser` / `python -c "import email_reply_parser"`: confirmed installed and importable in the project `.venv`.
- Manually confirmed the one-time warning log fires exactly once across two consecutive fallback-path calls in the same process (verified via ad hoc script before encoding it as a permanent `caplog`-based test).

## Known gaps or deferred items

- The root cause of why the dependency went uninstalled in the first place — this project's checked-in `.venv` drifting out of sync with `requirements.txt` — is a process/tooling concern, not a code defect, and was explicitly out of scope for this plan. No CI/pre-commit safeguard was added to prevent recurrence; flagged in the plan's Risks section as a candidate for a future, separate initiative.
- `email_reply_parser` itself emits a `DeprecationWarning` (`'count' is passed as positional argument`) internally during parsing, observed in the test run. This is upstream library behavior, not introduced by this change, and was not addressed here.
- No live inbound-sync end-to-end run was performed against a real IMAP connection in this pass; validation was via direct unit-level execution and the test suite, consistent with how the original plan was validated.

## Handoff notes

- No frontend or API contract changes — this was a backend-internal correctness fix to a feature not yet consumed by the frontend (per the original plan's handoff notes).
- If `email-reply-parser` is ever removed or fails to install in another environment (e.g. CI, production), the fallback is now correct on the previously-broken case and will additionally emit a clear, greppable warning log (`"quote_stripper | email_reply_parser not installed — using regex fallback for quote stripping"`) the first time it activates per process — worth adding to any log-monitoring alert rules if drift-detection is desired later.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_quote_stripper_fallback_fix_20260706.md`
