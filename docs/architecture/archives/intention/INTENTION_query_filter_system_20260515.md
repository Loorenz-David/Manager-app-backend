# INTENTION_query_filter_system_20260515

## Metadata

- Intention ID: `INTENTION_query_filter_system_20260515`
- Status: `achieved`
- Owner: `David`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T23:59:00Z`

## Goal

Establish a consistent, reusable query filter system for all list queries: free-text string search (`q`) applied via case-insensitive partial match across declared columns, scoped by an optional `string_filters` param, with a per-query date range filter naming convention.

## Why this matters

List queries across the codebase apply filters inconsistently — ad-hoc `.ilike` checks, different param names, and no shared utility. As new list endpoints are added (users, tasks, working sections), each author would independently reinvent the filter pattern. A local contract and shared utility function eliminates that drift, makes filter behavior discoverable, and gives agents a single authoritative reference.

## Success criteria

1. A `apply_string_filter` utility function exists at `backend/app/beyo_manager/services/queries/utils/string_filter.py` and is importable by any query module.
2. Any list query can add string search by calling `apply_string_filter(stmt, q, string_filters, allowed_columns)` — no inline `.ilike` calls.
3. ✅ **DONE** — Local contract file `backend/architecture/55_query_filters_local.md` documents the full convention: param names, utility signature, router pattern, joined table pattern, security and performance rules, and completion gate.
4. ✅ **DONE** — `backend_contract_goal_mapping_guide.md` trigger expansion map updated with search/filter keywords → contract 55.
5. `string_filters` is parsed as a comma-separated string (`"username,email"`) and silently ignores invalid column names.
6. Date range filter params follow the `{field}_before` / `{field}_after` naming convention (per-query implementation, no shared utility needed).
7. No credential or secret columns (`password`, hashes) can appear in `allowed_columns`.

## Scope boundary

- In scope:
  - `apply_string_filter` utility function (ILIKE partial match, column scoping)
  - `string_filters` comma-separated column name parsing
  - `{field}_before` / `{field}_after` date filter naming convention (contract documentation only — each query implements its own)
  - Local contract file `55_query_filters_local.md`
  - Mapping guide trigger expansion update

- Out of scope:
  - Full-text search (PostgreSQL `tsvector` / `tsquery`) — a separate concern if needed later
  - Shared date filter utility — each query implements its own date filter block
  - Retroactively refactoring existing list queries to use the utility (separate plan per domain)
  - Enum / status filters — covered per-query, no shared utility needed

- Non-goals:
  - Elasticsearch or external search integration
  - Faceted search or aggregation queries

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_query_filter_system_20260515` | `backend/docs/architecture/archives/implementation/PLAN_query_filter_system_20260515.md` | `completed` | **Utility function only** — contract and mapping guide are already done. See SC 3 and 4. |

## Progress notes

- `2026-05-15`: Intention created. Goal-intent alignment completed with David. All design decisions resolved: ILIKE via utility, comma-separated string_filters, date filters per-query convention, new contract at 55.
- `2026-05-15`: Implementation plan `PLAN_query_filter_system_20260515` created. Contract `55_query_filters_local.md` written and stable — includes primary table and joined table patterns, conditional join pattern, security rules, performance notes, completion gate. Mapping guide updated. SC 3 and SC 4 are complete.
- `2026-05-15`: Contract 55 finalised. `PLAN_query_filter_system_20260515` scope reduced to **utility function only** (2 new files). Copilot must not create a new plan — the existing plan at the path above is the single source of truth for this work.
- `2026-05-15`: `PLAN_query_filter_system_20260515` completed and archived. Utility files created at `services/queries/utils/__init__.py` and `services/queries/utils/string_filter.py`; validation checks passed (`OK`).

## Open questions

- None — all blocking decisions resolved during alignment.

## Lifecycle transition

- Current status: `achieved`
- Next status: `archived`
- Transition trigger: Intention archived after downstream domain plans adopt the utility where needed.
