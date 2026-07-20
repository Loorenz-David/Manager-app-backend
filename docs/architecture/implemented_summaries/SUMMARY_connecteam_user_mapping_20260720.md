# Implementation Summary — Connecteam CSV user-ID mapping

Plan: [`PLAN_connecteam_user_mapping_20260720`](../archives/implementation/PLAN_connecteam_user_mapping_20260720.md)

Lifecycle: `approved` → `implemented` → `summarized` → `archived`

Implemented:

- Tolerant UTF-8/BOM comma-or-semicolon CSV reader with canonical `userId`,
  `firstName`, and `lastName` extraction, typed file/format/row errors, duplicate-row
  handling, and no provider-column leakage.
- Exact NFKC/strip/whitespace-collapse/casefold matching and full-name construction.
- One workspace-aware `users` ↔ `user_work_profiles` candidate query, normalized-name
  collision handling, ten mapping statuses, and structured frozen report models.
- Dry-run-default mapping command and one-time Typer CLI with `--execute`/`--apply`,
  `--file`, `--workspace-id`, `--output`, exit codes 0/1/2, conflict abort before writes,
  one transaction, rollback behavior, string ID storage, and idempotent reruns.
- Canonical CSV README, name-redacted fixture, and Connecteam mapping tests.

Constraints honored:

- No API client or `CONNECTEAM_API_KEY` read was added.
- No users, profiles, shifts, records, settings, schema, webhook, clock, scheduler, or
  phase-1/2 lifecycle files were changed.
- No handoff artifact was required.

Validation:

- New mapping tests: 22 passed.
- Canonical CSV parse: 15 rows.
- Targeted Ruff: passed.
- CLI help: passed.
- Missing-file CLI path: exit 1 before DB initialization.
- Full `tests/connecteam`: 39 passed; one untouched phase-2 parity test failed and also
  fails in isolation with the same existing clock-action mismatch. This is recorded as
  an out-of-scope follow-up; no phase-1/2 fix was attempted.
- Owner-driven live dry-run/apply/SQL verification: intentionally deferred; not simulated.
