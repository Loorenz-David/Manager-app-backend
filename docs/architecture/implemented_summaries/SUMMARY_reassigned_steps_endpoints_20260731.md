# SUMMARY_reassigned_steps_endpoints_20260731

## Metadata

- Summary ID: `SUMMARY_reassigned_steps_endpoints_20260731`
- Status: `implemented`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-08-01T00:00:00Z`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_reassigned_steps_endpoints_20260731.md`
- Intention: `backend/docs/architecture/under_construction/intention/making_endpoint_for_getting_reasign_tasks.md`
- Review: round 1 `NEEDS_CHANGES` (2 blocking, 1 medium) → round 2 **`APPROVED`** (2 low, non-blocking)

## What was implemented

Two read-only endpoints backing a "Reassigned to me" page in the worker app. No migration, no new
table or column — both read existing tables and existing indexes.

- **`GET /api/v1/task-step-acknowledgments/reassigned-steps`** — paginated list of the caller's
  reassigned, unfinished steps, with a free-text `q` search and a page-scoped `working_sections`
  map for building per-section containers.
- **`GET /api/v1/task-step-acknowledgments/reassigned-steps/count`** — `{total, unacknowledged}`
  in one statement, for the navigation badge.
- **A shared batch payload builder**, extracted from `list_working_section_steps` so both surfaces
  emit an identical step object. This was the delivery's actual risk: ~290 lines moved out of the
  worker app's main section-list screen, which had zero test coverage beforehand.

Visibility rules: a step appears only when a live acknowledgment exists for (workspace, step,
caller), the caller holds an **active** membership for the step's working section **as of read
time**, the step is non-terminal, and step / task / section are all live. The membership join is
load-bearing rather than redundant — `add_task_steps` fans acknowledgments out to every *section
member*, so a worker moved out of a section must stop seeing its reassignments.

## Files changed

- `app/beyo_manager/services/queries/working_sections/steps_list_payload.py`: **new.** The batch
  step-card builder, moved verbatim from `list_working_section_steps`.
- `app/beyo_manager/services/queries/working_sections/list_working_section_steps.py`: reduced to id
  selection, filters, ordering and pagination, then a six-line builder call. Its early-empty
  envelope stays in the caller.
- `app/beyo_manager/services/queries/task_step_acknowledgments/_reassigned_steps_filters.py`:
  **new.** The single definition of "a reassigned step this caller should see" — shared by both
  services so the badge can never disagree with the page.
- `app/beyo_manager/services/queries/task_step_acknowledgments/list_reassigned_steps.py`: **new.**
- `app/beyo_manager/services/queries/task_step_acknowledgments/count_reassigned_steps.py`: **new.**
  One statement, `FILTER (WHERE …)` aggregate, no ORM entities loaded.
- `app/beyo_manager/domain/task_steps/serializers.py`: gained
  `serialize_task_step_acknowledgment`, promoted from a private helper.
- `app/beyo_manager/services/queries/task_step_acknowledgments/list_pending_step_acknowledgments.py`:
  imports the promoted serializer; `/pending` responses unchanged.
- `app/beyo_manager/routers/api_v1/task_step_acknowledgments.py`: two routes, roles
  `[ADMIN, MANAGER, WORKER]`, both scoped to the calling user.
- `app/tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py`:
  **new.** Written *before* the extraction; unedited after it.
- `app/tests/integration/services/queries/task_step_acknowledgments/test_reassigned_steps_integration.py`:
  **new.** Exclusion matrix, `q` cases, list/count Agreement, pagination stability, query budget.

Commits (12): `a747939` · `1204916` · `241eee5` · `444fffa` · `1ad796c` · `dccdb7a` · `082b226` ·
`b29bdbe` · `4ea8b26` · `213cac7` · plus operator doc commits `9ce1105`, `f512eb1`, `9edb6e5`.

## Contract adherence

- **`07_queries_local.md`** — offset pagination (`{items, limit, offset, has_more}`) with a
  `limit + 1` fetch, per the local override of canonical cursor pagination.
- **`55_query_filters_local.md`** — `q` uses `apply_string_filter` with a module-level
  `allowed_columns` of item `article_number` / `sku`; router enforces `max_length=200`. All seven
  Completion-gate boxes verified clear by the round-2 reviewer. Note this contract **conflicts with
  the neighbouring `list_working_section_steps`**, which uses an inline `.ilike` subquery predating
  it; the contract won (D6) and the neighbour was deliberately left alone.
- **`24_multi_tenancy.md` / `25_soft_delete.md`** — every join carries `workspace_id` explicitly;
  the three distinct deletion idioms (`is_deleted`, `removed_at`, `deleted_at`) each used per table.
- **`22_performance.md`** — constant statement count, deliberately *not* copying the per-step
  loading loop in the neighbouring `list_pending_step_acknowledgments`.
- **`46_serialization_local.md`** — reuses existing serializers; the item shape is
  `list_working_section_steps`'s exactly, plus `acknowledgment`.

## Validation evidence

Round-2 review probed from the repo at `28711b7`, in the main tree, temporary files removed:

- **Extraction is a move, not a rewrite.** `diff` of `1204916^`'s `list_working_section_steps.py`
  lines 304–592 against `steps_list_payload.py:54-342` is **empty** — 289 lines byte-identical. The
  reviewer additionally loaded the pre-extraction file as a second module and ran both
  implementations against one fixture: identical JSON *and* identical key order, both
  parametrizations.
- **The characterization test discriminates** — deleting `group_image_by_step_id=` from the call
  site fails `…key_sets_are_stable[True]`. It has one commit (`a747939`) and was untouched by the
  extraction.
- **The Agreement test is a real paging loop** — inlining `acknowledged_at.is_(None)` into the list
  alone breaks it (2 failed / 13 passed).
- **Pagination is stable** — three acknowledgments sharing a `created_at`, paged at `limit=1`: no
  duplicate, no skip, exact `client_id DESC` order.
- **Query budget** — 13 statements for a 1-item page, 13 for a 50-item page.
- **Contract conformance** — item key set compared mechanically against handoff §5.1 (symmetric
  difference empty both ways); `422` confirmed through a `TestClient` for `limit=201`, `offset=-1`,
  and a 201-character `q`.
- **Scoping** — membership re-checked at read time; all four terminal states excluded individually;
  `ENDED_SHIFT` still visible; an admin caller sees only their own obligations on both endpoints.
- **Suite** (main tree, `backend/app`, default plugins): **26 failed / 1424 passed / 0 errors**,
  identical 26-node failure set across two runs, **zero** acknowledgment- or reassigned-related
  nodes. The +26 passed against the 26/1398 baseline is this feature's tests.
- `ruff check` clean on all feature-touched files. No migration in any feature commit.

## Known gaps or deferred items

- **`ENDED_SHIFT` removal is not part of this work.** Documented in handoff §6.1 as a build-ahead
  contract for a successor set —
  `INTENTION_ended_shift_step_state_collapse_20260731`. The frontend is instructed to parse the
  value but not branch on it.
- **Ordering is chronological, not section-grouped** (D1). A section's steps can span pages; the
  frontend merges into existing containers. Reversible one-liner if it proves awkward at scale.
- **`list_pending_step_acknowledgments` still loads its page per-step** (~12 statements per row).
  Explicitly out of scope; a known follow-up.
- **`limit=0` returns `422`** (`ge=1`), a case handoff §10's error table doesn't list. It narrows
  rather than widens, so no contract edit was needed — noted for a future handoff revision.
- **Three measurement traps were diagnosed during this work** and recorded in the
  `system_transition_reasons` master plan's "Validation baseline": a baseline worktree lacks both
  `app/.env*` **and** `app/.venv`, and `-p no:logging` kills `caplog` and manufactures ~19 phantom
  errors. Two separate sessions produced invalid baselines here (334/995/38 and 372/1042/38); both
  carry the same non-zero-error tell.

## Handoff notes

- To frontend: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`

Written **ahead of implementation** and treated as the authoritative contract — the backend
implemented to match it field-for-field. Two rounds of review found six wrong id prefixes in it
(`tstp_`→`tsp_`, `task_`→`tsk_`, `item_`→`itm_`, `icat_`→`itc_`, `iuph_`→`iup_`, `imev_`→`iev_`),
all operator-corrected; no implementer or reviewer edited the document or its liveness table.

**Operator action outstanding:** flip the two ⏳ liveness rows for the reassigned-steps endpoints
to ✅ and notify the frontend. The `ended_shift` row stays ⏳ — that is the successor set.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/reassigned_steps_endpoints/`
