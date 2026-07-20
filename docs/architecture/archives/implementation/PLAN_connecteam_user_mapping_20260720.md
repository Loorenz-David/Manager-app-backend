# PLAN_connecteam_user_mapping_20260720

## Metadata

- Plan ID: `PLAN_connecteam_user_mapping_20260720`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-20T16:00:00Z`
- Last updated at (UTC): `2026-07-20T20:00:00Z`
- Related issue/ticket: `n/a` (predecessors: `archives/implementation/PLAN_connecteam_clock_actions_20260720.md`, `under_construction/implementation/PLAN_connecteam_time_activity_webhook_foundation_20260720.md`)
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_connecteam_user_mapping_20260720.md` (see its **Strategy revision** note: CSV source supersedes the API sections)

## Goal and intent

- Goal: A one-time, manually-invoked backfill script that reads Connecteam users from an owner-provided CSV file (`backend/app/scripts/connecteam/connecteam_users.csv`; per-user `userId`, `firstName`, `lastName`), matches each user's constructed full name (`firstName + " " + lastName`, normalized) exactly against `users.username` (normalized), and stores `str(userId)` into `user_work_profiles.connecteam_user_id` — dry-run by default, single transaction on apply, conflicts never overwritten.
- Business/user intent: The phase-2 clock pipeline only acts for workers whose `connecteam_user_id` is set; today mapping is manual SQL. This script populates the mapping for the whole workforce in one controlled, reviewable operation, from a CSV the owner exports and reviews themselves.
- Non-goals: any Connecteam API calls (superseded strategy — no API key usage at all); creating users or work profiles; touching Connecteam data; importing time activities; webhook changes; email/phone/fuzzy/partial matching; recurring sync; any endpoint or frontend; archived Connecteam users (owner excludes them from the CSV).

## Scope

- In scope:
  - CSV reader for `scripts/connecteam/connecteam_users.csv` with tolerant header mapping, typed parse errors, and row-level validation.
  - Provider row DTO in `domain/connecteam/`; shared name-normalization helper; candidate query service; mapping command; report dataclasses; status enum.
  - Typer script in `scripts/backfill/` (repo's one-time-script convention), dry-run default, `--file` override, JSON output option, exit-code contract.
  - Structured lifecycle logging; tests (CSV parsing, normalization, query, mapping, dry-run, apply/rollback, CLI).
- Out of scope: everything in intention §4 "Out of scope"; the superseded API client/settings/pagination/retry work; migrations (column exists since phase 1); changes to webhook/clock code paths.
- Assumptions:
  - Phase-1 column, index, and `(workspace_id, connecteam_user_id)` unique constraint exist on `user_work_profiles`.
  - `users.username` is globally unique (`user.py:25`) and the dataset is coordinated: normalized Connecteam full name == normalized username. Observed reality: seeded usernames are **single first names** (`seed_workers.py` `_WORKER_NAMES`), so the CSV's `lastName` may be empty — the construction rule tolerates it.
  - The owner places and reviews the CSV before running the script; the CSV contains only active workers they intend to map.
  - The repo is not under git today; if that changes, the CSV (personal data) must not be committed — the plan adds a `README` note beside it.

## Clarifications required

- [ ] **Exact CSV shape is unverified until the owner places the file.** — Blocks finalizing the header mapping only. Canonical expected header row is `userId,firstName,lastName` (extra columns ignored), but Connecteam exports may differ (`User ID`, `First name`, delimiter `;`, BOM, quoted fields). Step 1 inspects the real file once present, records the observed headers/delimiter/encoding in this plan's Review log, and pins the header-normalization table accordingly. The reader is designed tolerant up front (case/space/underscore-insensitive header matching, BOM stripping, comma/semicolon sniffing), so this gate confirms rather than redesigns — same pattern as the phase-1 signature discovery.
- [ ] **Empty `lastName` handling.** — Needs owner awareness rather than redesign: seeded usernames are single tokens ("Andrii", "Roman", …). The full name is constructed as `" ".join(part for part in (first_name.strip(), last_name.strip()) if part)`; `invalid_external_name` applies only when the result is empty. If the CSV carries surnames that ManagerBeyo usernames lack, those users land in `external_user_unmatched` in the dry run — the mandatory dry-run review is where the owner confirms coordination before apply.
- [x] **RESOLVED 2026-07-20: canonical CSV now present.** Original finding (codex): the placed file was a Connecteam UI export (BOM, `;`-delimited, `First name`/`Last name`/`Kiosk code`/… headers, no `userId`); correctly refused to infer IDs. Resolution: at the owner's direction, a **one-time manual API fetch** (outside the script — the CSV strategy stands; the script performs no API calls) regenerated `scripts/connecteam/connecteam_users.csv` in canonical `userId,firstName,lastName` form: 15 data rows, UTF-8, comma-delimited, every row has a `userId` and at least one name part. The UI export is preserved as `connecteam_users_ui_export_backup.csv` (also personal data — same never-commit rule).

## Acceptance criteria

1. The script reads `backend/app/scripts/connecteam/connecteam_users.csv` by default (`--file <path>` overrides), extracts `userId`/`firstName`/`lastName` per row via tolerant header mapping, and the mapping outcome is identical regardless of row order.
2. A missing file, unreadable file, unrecognizable headers, or a row with a missing/non-integer `userId` fails with a typed, human-readable error (exit 1) that names the file, the row number where applicable, and the expected canonical headers — before any DB write.
3. Matching is exact-after-normalization only (NFKC → strip → collapse whitespace → casefold), applied identically to both sides; no partial/reordered/fuzzy behavior exists anywhere.
4. Every CSV user receives exactly one status from: `proposed`, `updated`, `already_mapped_same_id`, `existing_different_connecteam_id`, `external_user_unmatched`, `work_profile_not_found`, `work_profile_ambiguous`, `duplicate_external_full_name`, `connecteam_id_already_assigned`, `invalid_external_name` — plus duplicate `userId` rows within the CSV are collapsed/reported, never double-applied.
5. Dry-run is the default, performs the complete parse + match + conflict detection, prints summary and per-user detail, and performs zero writes and zero commits (asserted by test).
6. Apply requires the explicit write flag (mutually exclusive with dry-run), re-runs the full parse/validation (never trusts a previous report), writes only conflict-free `proposed` mappings, and **aborts with exit code 2 before any write when identity conflicts exist** (`duplicate_external_full_name`, `existing_different_connecteam_id`, `connecteam_id_already_assigned`, `work_profile_ambiguous`); `external_user_unmatched` / `work_profile_not_found` report without blocking.
7. All writes occur in one transaction (`async with session.begin()`, flush before commit); a DB failure or uniqueness violation rolls back the entire write set and reports clearly (exit 1).
8. A rerun after successful apply reports every written profile as `already_mapped_same_id` with zero writes (idempotence, pinned by test).
9. The Connecteam ID is stored as `str(userId)` on `user_work_profiles.connecteam_user_id` only — the `users` table is never written; no users, profiles, shifts, or clock records are created (asserted by test).
10. Workspace scoping follows the actual model: candidates join `users` ↔ `user_work_profiles`; optional `--workspace-id` filters profiles; a matched user with multiple eligible profiles and no workspace filter → `work_profile_ambiguous`, never an arbitrary pick.
11. Exit codes: 0 success (including clean dry-run), 1 configuration/file/parsing/DB error, 2 conflicts prevented apply; `--output <path>` writes the full report as valid JSON; CSV cell values are output-escaped as plain data (no key material exists in this flow; usernames/names are the only sensitive values and appear only in the report the owner requested).
12. Tests cover: CSV parsing matrix (canonical headers, variant headers, BOM, semicolon delimiter, missing columns, bad `userId`, empty file, duplicate rows), normalization matrix, candidate query (join, workspace filter, existing IDs, multi-profile user), all ten statuses, dry-run zero-write, apply transaction + rollback + rerun idempotence, CLI flag exclusivity, `--file` override, and exit codes 0/1/2.
13. No existing file outside the additive touch-list (enum module, `__init__` exports) is modified; webhook/clock behavior is untouched (phase-1/2 suites still pass). No settings changes: `CONNECTEAM_API_KEY` is not read anywhere.

## Contracts and skills

### Contracts loaded

Selected contracts (core, always included):
- `backend/architecture/01_architecture.md`: layer placement — parsing in a provider adapter, orchestration in a command, reads in a query, thin script.
- `backend/architecture/04_context.md`: command invocation shape (script-invoked; direct session per backfill precedent).
- `backend/architecture/05_errors.md`: typed error taxonomy for file/parse errors.
- `backend/architecture/06_commands.md`: command structure and transaction ownership.
- `backend/architecture/07_queries.md`: candidate query service shape.
- `backend/architecture/09_routers.md`: core-mandated (no router work — confirms none).
- `backend/architecture/21_naming_conventions.md`: file, enum, and status naming.
- `backend/architecture/40_identity.md`: `client_id` usage in report rows.
- `backend/architecture/41_user.md`: `users.username` uniqueness and work-profile ownership.
- `backend/architecture/42_event.md`: core-mandated (no domain events emitted by a backfill).
- `backend/architecture/48_presence.md`: core-mandated (confirms non-interference with shift state).

Added from guide (triggers + deliberate additions):
- `backend/architecture/19_integrations.md`: provider-boundary discipline — CSV is the provider payload; its column names must not leak past the adapter.
- `backend/architecture/27_cli_scripts.md`: script entry-point conventions (dry-run/execute, typer, session bootstrap).
- `backend/architecture/53_operational_cli.md`: operational command conventions (report formatting, exit codes).
- `backend/architecture/17_logging.md` + `49_observability_runtime.md`: trigger "structured logs" — lifecycle events, no PII beyond the requested report.
- `backend/architecture/15_testing.md`: test layout; tmp-file fixtures.
- `backend/architecture/22_performance.md`: one candidate query + in-memory index instead of per-user queries.

Excluded contracts:
- `30_migrations.md` / `03_models.md`: no schema change (phase-1 column reused).
- `16_background_jobs.md` / `12_infra_redis.md` / `51_worker_runtime.md`: no queue/worker involvement — synchronous manual script.
- `57_shopify_integration.md`: was loaded for the HTTP-client precedent; no external client exists in the CSV strategy.
- `13_sockets.md`, `34_file_storage.md`, `52_replayability.md`: untouched domains.

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: transaction utility rules (the apply transaction).
- `backend/architecture/07_queries_local.md`: query conventions for the candidate loader.
- `backend/architecture/40_identity_local.md`, `41_user_local.md`, `42_event_local.md`, `48_presence_local.md`: app deltas for touched/adjacent domains.

Applied precedence: canonical first, local second; local wins for this app.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted (relational reads — performed while authoring this plan; may be repeated):
- `models/tables/users/user.py` (`username` unique, `client_id`), `user_work_profile.py` (workspace scoping, phase-1 constraint names).
- `scripts/backfill/backfill_averaged_time.py` — the backfill script skeleton actually in use (typer app, dry-run default, `--execute`, `init_db`/`get_db_session`/`close_db`).
- `services/commands/bootstrap/phases/seed_workers.py` — actual username shapes for test fixtures.
- `domain/connecteam/` — phase-1/2 modules being extended (enums, existing DTO conventions).
- The real `scripts/connecteam/connecteam_users.csv` once the owner places it (step-1 gate).

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md` (lifecycle processing); contract set assembled via `backend/skills/cross_cutting/planning_contract_selection/SKILL.md`.
- Router trigger terms: `cli, script, backfill, integration, structured logs`
- Excluded alternatives: `backend/skills/domains/identity/SKILL.md` — reads user identity but defines no new identity behavior; this phase only reads `users.username`.

## Implementation plan

Design constants:
- CSV location: `backend/app/scripts/connecteam/connecteam_users.csv` (owner-provided; `--file` overrides). A `scripts/connecteam/README.md` documents the canonical format and states the file holds personal data and must never be committed if the project is placed under version control.
- Canonical CSV format: header row `userId,firstName,lastName` (UTF-8; extra columns ignored). Header matching is tolerant: case-insensitive, spaces/underscores stripped (`user id` / `User_ID` / `USERID` all → `userId`); BOM stripped; delimiter sniffed between `,` and `;`.
- Script: `backend/app/scripts/backfill/map_connecteam_user_ids.py` (repo one-time-script home); write flag `--execute` with `--apply` alias; `--dry-run` explicit no-op default, mutually exclusive with the write flag.
- Name normalization: NFKC → strip → collapse internal whitespace → casefold; full name = join of non-empty stripped parts.
- New enum `ConnecteamUserMappingStatusEnum` (10 statuses) in `domain/connecteam/enums.py` (additive).
- Log events (adapted from intention §23 minus the HTTP ones): `connecteam_user_mapping_started`, `connecteam_users_csv_loaded`, `connecteam_user_mapping_proposed`, `connecteam_user_already_mapped`, `connecteam_user_unmatched`, `connecteam_user_mapping_conflict`, `connecteam_user_mapping_committed`, `connecteam_user_mapping_failed` — via `log_event(...)`, phase-1 rule applied: never pass `event_type=` as a kwarg.

Steps:

1. **CSV shape confirmation gate** — once the owner places the file: inspect headers/delimiter/encoding, record findings in the Review log, pin the header-normalization table, and copy a 2–3-row **name-redacted** sample into `tests/connecteam/fixtures/users_sample.csv`. If the file is absent when implementation starts, build against the canonical format (the reader's tolerance covers the likely variants) and leave the Review-log entry to be completed when the file lands — do not bloc­k the rest of the build on it.
2. **Errors** — `errors/validation.py` is not touched; add a small provider-parse error in the adapter module itself (`ConnecteamCsvError(DomainError)` with `http_status = 400`, plus `ConnecteamCsvFormatError` / `ConnecteamCsvRowError` subclasses carrying file path and row number). No shared-file changes.
3. **Row DTO + reader (provider adapter)** — new `domain/connecteam/user_csv_rows.py`: frozen `ConnecteamCsvUser(user_id: int, first_name: str, last_name: str, row_number: int)` and `read_connecteam_users_csv(path: Path) -> list[ConnecteamCsvUser]` implementing: existence/readability check → BOM handling (`utf-8-sig`) → delimiter sniff (`,`/`;`) → tolerant header mapping → per-row extraction with `int(userId)` validation (`ConnecteamCsvRowError` names the row) → duplicate-`userId` collapse (identical rows deduped; contradictory rows → both reported for the conflict path). Pure file→DTO function; no DB, no normalization decisions beyond header mapping. Column names do not leak past this module.
4. **Normalization helper** — new `domain/connecteam/normalize_username.py`: `normalize_username(value: str) -> str` exactly per intention §13, plus `build_external_full_name(first: str, last: str) -> str | None` (join non-empty stripped parts; `None` → `invalid_external_name`). Pure functions, no I/O.
5. **Candidate query** — new `services/queries/users/get_connecteam_mapping_candidates.py`: one query joining `User` ↔ `UserWorkProfile` (`UserWorkProfile.user_id == User.client_id`), optional `workspace_id` filter, returning frozen `InternalConnecteamMappingCandidate(user_id, username, user_work_profile_id, workspace_id, connecteam_user_id)` rows. One query total; the command builds `internal_by_username` keyed by normalized username; a normalized-username collision inside the index (e.g. "Anna" vs "anna") marks affected externals as conflicts rather than picking one.
6. **Report model** — new `domain/connecteam/user_mapping_report.py`: frozen dataclasses `ConnecteamUserMappingRow` and `ConnecteamUserMappingReport` per intention §21 (`source_file: str` and `workspace_id: str | None` included; `identity_conflicts_present: bool` convenience flag for the exit-code decision). Independent of terminal formatting.
7. **Mapping command** — new `services/commands/connecteam/map_connecteam_user_ids.py`: `async def map_connecteam_user_ids(session, *, csv_users: list[ConnecteamCsvUser], apply: bool, workspace_id: str | None) -> ConnecteamUserMappingReport`.
   Pipeline: build/normalize external names → detect `duplicate_external_full_name` (two CSV users colliding post-normalization: both excluded) and `invalid_external_name` → load candidates (step 5) + index → classify every CSV user into exactly one status per intention §17, including `connecteam_id_already_assigned` (proposed ID already present on a different profile row — checked against both DB state and earlier proposals in the same run) → if `apply`: when any identity conflict exists (`duplicate_external_full_name`, `existing_different_connecteam_id`, `connecteam_id_already_assigned`, `work_profile_ambiguous`) **return the report without writing** (script maps this to exit 2); otherwise write all `proposed` rows inside `async with session.begin()` (load profiles by id, set `connecteam_user_id = str(user_id)`, flush; statuses become `updated`). Unmatched/not-found never block. `IntegrityError` propagates after rollback with a clear message (exit 1). Reruns classify written rows as `already_mapped_same_id`.
8. **Script entry point** — new `scripts/backfill/map_connecteam_user_ids.py` (typer app mirroring `backfill_averaged_time.py`): flags `--dry-run/--execute` (+ `--apply` alias), `--file` (default `scripts/connecteam/connecteam_users.csv`), `--workspace-id`, `--output <path>`. Thin: read CSV (step 3) → `init_db()` → session → command (step 7) → format summary + aligned detail table (per intention §18) → optional JSON dump → `close_db()` → exit code (0 / 1 on file, parse, or DB exceptions / 2 when apply blocked by conflicts). Docstring states it is one-time, manual, dry-run by default; nothing registers it with cron/schedulers.
9. **Data-folder README** — new `scripts/connecteam/README.md`: canonical CSV format, one example row, the "personal data — never commit" note, and the run sequence (dry-run → review → `--execute` → verification SQL from intention §10).
10. **Tests** — extend `backend/app/tests/connecteam/` (the suite's actual home): `test_user_csv_reader.py` (canonical + variant headers, BOM, semicolon, missing column, non-int userId with row number in the error, empty file, duplicate rows collapse/report, extra columns ignored), `test_normalize_username.py` (match/no-match matrix incl. single-name usernames, unicode NFKC, collapsed spaces; reordered/partial names rejected), `test_mapping_candidates_query.py` (join, workspace filter, existing IDs, multi-profile user), `test_map_user_ids_command.py` (all ten statuses; dry-run zero-write; apply single-transaction; conflict-abort writes nothing; rollback on forced IntegrityError; rerun idempotence; ID stored as string; `users` table never written), `test_map_user_ids_cli.py` (flag exclusivity, dry-run default, `--file` override, missing-file error, JSON output validity, exit codes 0/1/2). Phase-1/2 suites must still pass untouched.

## Risks and mitigations

- Risk: The real CSV export's headers/delimiter/encoding differ from the canonical format and rows silently mis-parse.
  Mitigation: Tolerant header mapping + delimiter sniffing + explicit `ConnecteamCsvFormatError` listing found-vs-expected headers; step-1 gate pins the real shape; unmatched headers fail loudly, never guess-map.
- Risk: A stale or hand-edited CSV maps a wrong ID to a worker (garbage in).
  Mitigation: Dry-run-by-default with full per-row report and mandatory owner review; conflicts with existing IDs are never overwritten; the phase-1 unique constraint rejects duplicate assignments inside a workspace at the DB level.
- Risk: Normalized-name collisions inside ManagerBeyo (two usernames normalizing identically).
  Mitigation: Index-build collision detection classifies affected externals as conflicts (blocks apply), surfaced in dry-run.
- Risk: The coordinated-data assumption fails (CSV has surnames, usernames don't).
  Mitigation: Clarification 2 + dry-run review; unmatched rows are informational, never destructive.
- Risk: Same user mapped in two workspaces (two profiles) gets an arbitrary profile written.
  Mitigation: Multi-candidate detection → `work_profile_ambiguous` (blocks apply); `--workspace-id` is the explicit narrowing mechanism.
- Risk: The CSV (personal data) ends up in version control later.
  Mitigation: README warning beside the file; if the project gains a git repo, `scripts/connecteam/*.csv` belongs in `.gitignore` (noted in the README).
- Risk: The script gets wired into automation later by mistake.
  Mitigation: Lives in `scripts/backfill/` beside other one-time scripts, requires an explicit write flag, docstring + plan forbid scheduling; no Procfile/cron/scheduler registration exists.

## Validation plan

- `cd backend/app && .venv/bin/python -m pytest tests/connecteam -q`: full suite (phases 1–3) passes.
- `.venv/bin/ruff check beyo_manager scripts`: no new violations.
- `.venv/bin/python -m scripts.backfill.map_connecteam_user_ids --help`: shows dry-run default, `--file`, and one-time warning.
- Missing-file check: run dry-run without the CSV present → clear `ConnecteamCsvError` naming the expected path, exit 1, no DB session opened.
- Live sequence (owner-driven): (1) owner places `scripts/connecteam/connecteam_users.csv`; (2) `--dry-run` — review every row; (3) `--execute`; (4) verification SQL joining `users` ↔ `user_work_profiles` on `connecteam_user_id IS NOT NULL` (intention §10); (5) rerun `--dry-run` — everything `already_mapped_same_id`.
- End-to-end proof: after apply, a Connecteam clock-in from any newly-mapped worker drives the phase-2 pipeline (`connecteam_worker_resolved` → shift record) without manual SQL mapping.

## Review log

- `2026-07-20` `owner (David)`: API-key rotation will be performed manually by the owner (retained from the API-strategy draft; the key is now unused by this plan — rotation remains advisable since the value was exposed, but is independent of this implementation).
- `2026-07-20` `claude (plan author)`: Initial draft (API-based).
- `2026-07-20` `owner (David)`: **Strategy revision — no API call.** Users will be supplied as a CSV placed at `backend/app/scripts/connecteam/` (filename delegated: `connecteam_users.csv`). Plan rewritten: API client/settings/pagination/retry work removed; CSV reader adapter added; matching, statuses, dry-run/apply, transaction, report, and CLI contracts unchanged.
- `2026-07-20` `claude (plan author)`: Clarification 1 re-scoped from `paging.offset` semantics to CSV shape confirmation (step-1 gate, non-blocking for the build). Clarification 2 (single-name usernames) unchanged, resolves at dry-run review.
- `2026-07-20` `codex`: Step-1 inspection found the present CSV is UTF-8 with BOM and semicolon-delimited, but lacks the required `userId` header; its non-canonical fields were not mapped by inference. Implementation is paused pending owner clarification, per the clarification-first rule.

- `2026-07-20` `owner (David)`: CSV-strategy plan confirmed ready; status moved to `approved`. Both clarifications remain as in-flow gates for the implementer.

- `2026-07-20` `claude (plan author)`: CSV blocker resolved — canonical `connecteam_users.csv` written from a one-time manual API fetch (owner-approved; script strategy unchanged). Observations recorded for posterity: the live user object carries `userId` (int), `firstName`, `lastName`, `kioskCode`, `isArchived`, etc.; `paging.offset` in the response equals the **next** offset (returned `offset: 15` after 15 of `total: 15` users) — confirming the accumulated-count advance rule; Cloudflare blocks non-browser HTTP clients (Python urllib → 403 error 1010) while curl succeeds, which is irrelevant to this plan since the script never calls the API. Step-1 CSV gate is now satisfied against the canonical file: UTF-8, comma-delimited, headers `userId,firstName,lastName`, 15 rows. Codex may resume at lifecycle step 6.
- `2026-07-20` `codex`: Implemented the CSV adapter, exact NFKC name normalization, candidate query, ten-status report, conflict-safe mapping command, dry-run/default CLI with `--execute`/`--apply`, JSON output, README, and Connecteam mapping tests. No API client, API-key read, schema/settings change, webhook/clock change, or automation registration was added.
- `2026-07-20` `codex`: Validation: 22 new mapping tests pass; canonical CSV parses as 15 rows; targeted Ruff passes; CLI help passes; missing-file path exits 1 before DB initialization. Full `tests/connecteam` reached 39 passed, but the untouched phase-2 parity test also fails alone with the same existing clock-action mismatch; no phase-1/2 lifecycle state was changed. Owner-driven dry-run/apply/SQL verification was intentionally not simulated.

## Lifecycle transition

- Current state: `archived`
- Next state: none for this implementation plan; the linked intention remains active pending owner-run mapping review and unrelated phase-2 baseline follow-up.
- Transition owner: `codex`
