# INTENTION — One-Time Connecteam User ID Mapping by Full Name (2026-07-20)

> Provided by the product owner on 2026-07-20. Phase 3 of the Connecteam integration
> (phase 1: webhook foundation; phase 2: clock actions — both archived/live).

> **STRATEGY REVISION (owner, 2026-07-20, later same day):** the user source is **no longer
> the Connecteam API**. The owner will export the users and place a **CSV file** at
> `backend/app/scripts/connecteam/` (filename chosen by the implementer:
> `connecteam_users.csv`). Sections 2, 3, 9 below (API contract, API key configuration,
> HTTP error handling) are superseded — no API call, no `CONNECTEAM_API_KEY` usage, no
> pagination. Everything else (matching rules, normalization, statuses, dry-run/apply,
> transaction semantics, reporting, CLI, out-of-scope list) remains authoritative. The
> CSV must provide, per user: the Connecteam `userId`, `firstName`, and `lastName`.

## 1. Objective

A one-time, manually-invoked backend script that reads the owner-provided active-user
CSV and maps each row to an existing ManagerBeyo user: construct
`<firstName> <lastName>`, compare against `users.username` (normalized, exact), resolve
the corresponding `UserWorkProfile`, and store `str(userId)` in
`user_work_profiles.connecteam_user_id`. The user data is already coordinated so that
normalized Connecteam full name == normalized `users.username`. Controlled backfill only —
must never run automatically or periodically; the script performs no Connecteam API calls.

## 2. Confirmed Connecteam API contract

`GET https://api.connecteam.com/users/v1/users` with query params
`limit` (1–500; use 500), `offset` (offset pagination), `order=asc`,
`userStatus=active`; headers `accept: application/json` and `X-API-KEY: <CONNECTEAM_API_KEY>`.
Response shape: `{ "requestId": str, "data": { "users": [ { "userId": int,
"firstName": str, "lastName": str, ... } ] }, "paging": { "offset": int, "total": int? } }`.
Users also carry `phoneNumber`, `userType`, `email`, `isArchived` — Connecteam has **no
native username field**; the external match value is deterministically constructed from
`firstName + " " + lastName`. Correctness must not depend on response ordering.

## 3. Environment configuration

`CONNECTEAM_API_KEY=` and `CONNECTEAM_API_BASE_URL=https://api.connecteam.com`, read
through the existing typed settings. Fail clearly when the key is missing at use time.
Never log the key, include it in exceptions, return it from results, or expose it to
frontend code. Do not reuse `CONNECTEAM_WEBHOOK_SECRET`. Security note: the key currently
in the shared `.env` has been exposed in conversation and should be **rotated** before use
beyond local testing.

## 4. Scope

In scope: typed API config; async Connecteam users client; full pagination; minimal
tolerant provider DTOs; full-name construction; normalization; exact matching against
`users.username`; `UserWorkProfile` resolution; dry-run (default) and apply modes;
conflict detection; single-transaction updates; structured report; unit/integration tests.

Out of scope: creating users or work profiles; updating Connecteam; importing historical
time activities; creating shift/timeline records; webhook processing; matching by
email/phone/fuzzy/nickname/partial name; recurring sync; public endpoint; frontend page;
archived users.

## 5. Normalization and matching rules

One deterministic function: NFKC normalize → strip → collapse internal whitespace →
`casefold()`. Applied to both the constructed external full name and `users.username`.
Match must be **exact after normalization** — no partial, reordered, first-only,
last-only, nickname, or Levenshtein matching; no accent removal unless the dataset
requires it. `users.username` is globally unique (`String(128), unique=True`) and is the
deterministic internal key. Store the Connecteam ID **as a string** on the work profile,
never on `users`.

## 6. Mapping statuses (each external user gets exactly one)

`proposed` (exact match, profile has no ID) · `updated` (apply-mode write performed) ·
`already_mapped_same_id` (idempotent, no write) · `existing_different_connecteam_id`
(never overwrite) · `external_user_unmatched` (no user created) · `work_profile_not_found`
(no profile created) · `work_profile_ambiguous` (never pick arbitrarily) ·
`duplicate_external_full_name` (two active Connecteam users collide — map neither) ·
`connecteam_id_already_assigned` (ID already on another profile — no update) ·
`invalid_external_name` (unusable name — skip).

## 7. Dry-run / apply contract

Dry-run is the **default** and performs the complete fetch, matching, and conflict
detection with zero writes/commits, printing a full summary + per-user detail table.
Apply requires an explicit mutually-exclusive flag, repeats the full fetch/validation
(never trusts a previous report), applies only exact conflict-free mappings, and
**aborts before commit when identity conflicts exist** (duplicate external names,
differing existing IDs, ID assigned elsewhere, ambiguous profiles). Unmatched users
report without blocking. All writes in **one transaction** (flush before commit; full
rollback on unexpected error; uniqueness violations surface inside the transaction).
A rerun reports `already_mapped_same_id`. Workspace scoping: inspect the actual
`UserWorkProfile` model — if profiles are workspace-scoped, support/require
`--workspace-id`; never arbitrarily select among multiple eligible profiles.

## 8. CLI, reporting, logging

Args: dry-run (default) / apply (mutually exclusive), optional workspace-id, limit
(default 500), optional JSON `--output`. Exit codes: 0 success · 1 configuration/HTTP/
parsing/DB error · 2 identity conflicts prevented apply. Structured result model
(row + report dataclasses) independent of terminal formatting. Lifecycle log events:
mapping_started, page_requested/received, fetch_completed, mapping_proposed,
already_mapped, unmatched, mapping_conflict, mapping_committed, mapping_failed — never
logging the API key, header values, or DB credentials.

## 9. HTTP error handling

Typed provider exceptions: configuration, authentication (401), access (403), invalid
request (422), rate-limit (429), temporary (5xx), response/contract (bad JSON/schema),
pagination (no progress). Bounded retries (max 3; ~1s/3s/10s) only for 429/502/503/504/
timeouts; never for 401/403/422/schema errors. Guard against infinite pagination loops;
verify the semantics of `paging.offset` against one real response before finalizing.

## 10. Manual verification sequence

(1) One direct curl with `limit=10` to confirm `userId`/`firstName`/`lastName` presence;
(2) full dry-run and human review of every proposed mapping; (3) apply; (4) SQL
verification joining `users` ↔ `user_work_profiles` on stored Connecteam IDs.

## 11. Acceptance criteria (summary)

Authenticates via `X-API-KEY`; calls `GET /users/v1/users` with active filter; paginates
fully; constructs and normalizes the full-name match; exact matches only; resolves the
work profile; stores the ID as string; dry-run default; explicit apply; idempotent
reruns; conflicting IDs never overwritten; duplicates/ambiguity rejected; one
transaction; credentials never logged; creates no users/profiles/shifts/records; tests
cover retrieval, pagination, matching, dry-run, apply, conflicts, rollback.

## Linked implementation plans

| Implementation plan | Status | Summary |
|---|---|---|
| `backend/docs/architecture/archives/implementation/PLAN_connecteam_user_mapping_20260720.md` | archived | CSV-based mapping implemented; owner-run live review remains pending. |

## Progress notes

- 2026-07-20: The canonical CSV gate was resolved by the owner: UTF-8, comma-delimited,
  headers `userId,firstName,lastName`, 15 rows. The implementation uses this CSV only;
  the superseded API sections remain historical context and are not executed.
- 2026-07-20: Mapping implementation completed with dry-run default, exact normalized
  matching, conflict-aborting apply, single-transaction writes, idempotent reruns, and
  JSON reporting. No handoff is required.
- 2026-07-20: Owner-driven sequence (dry-run review → execute → SQL verification) was
  not simulated. The full Connecteam suite has an unrelated pre-existing phase-2 parity
  failure that reproduces in isolation; phase-1/2 lifecycle state remains untouched.
