# PLAN_reassigned_steps_endpoints_20260731

## Metadata

- Plan ID: `PLAN_reassigned_steps_endpoints_20260731`
- Status: `archived`
- Owner agent: `planning_session_claude`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/making_endpoint_for_getting_reasign_tasks.md`

## Goal and intent

- Goal: expose two read-only endpoints that let a logged-in worker see every task step
  that was reassigned into one of their currently-assigned working sections and is not
  yet finished — one paginated list endpoint returning the full step cards, and one
  lightweight count endpoint.
- Business/user intent: the worker app (`app_scope="worker"`) gains a dedicated
  "Reassigned to me" page. A
  worker who finished a task and later had new work pushed back onto it needs a single
  place that shows those steps, grouped by working section, without scanning each
  section list. The count endpoint feeds the navigation badge and must be cheap enough
  to poll.
- Non-goals:
  - No new write path. Acknowledging / marking-seen already exists
    (`POST /api/v1/task-step-acknowledgments/seen` and `/acknowledge`) and is untouched.
  - No change to how `TaskStepAcknowledgment` rows are created in `add_task_steps`.
  - No migration, no new column, no new table, no new realtime event.
  - No change to the existing `GET /api/v1/task-step-acknowledgments/pending` endpoint.
    It stays as-is for the acknowledgment modal flow; this plan adds a *different*
    surface with different filters and a different loading strategy.

## Scope

### In scope

1. New query service `list_reassigned_steps` — paginated list of the caller's reassigned,
   non-terminal steps, filtered by the caller's *current* working-section membership, with a
   free-text `q` search (D6).
2. New query service `count_reassigned_steps` — counts only, over the same filter set.
3. Extraction of the batch step-card payload builder currently inlined in
   `list_working_section_steps`, so both endpoints emit byte-identical step objects.
4. Two new routes on the existing `task_step_acknowledgments` router.
5. Integration tests for both new services, plus a characterization test that pins the
   existing `list_working_section_steps` payload before the extraction.
6. Frontend handoff document.

### Out of scope

- Every filter *except* `q`: `task_types`, `item_major_category`, `major_category`,
  `item_position`, `item_zone`, `record_step_state`, `readiness_statuses`,
  `upholstery_search`, `group_by_upholstery`. The reassigned page is an inbox, not a browse
  surface — those params exist on `list_working_section_steps` because that list can hold
  thousands of rows. **`q` is in scope** (operator decision, 2026-07-31) because finding one
  known article among a worker's reassignments is the one search a small list still needs.
  Note `upholstery_search` staying out means `q` covers article number and SKU only (D6).
- Sockets / push. Reassignment already fires its own notification from `add_task_steps`.

### Assumptions

- `TaskStepAcknowledgment` is the single source of truth for "this step was reassigned
  and this worker owes attention to it". Verified: `add_task_steps` writes one row per
  (reassigned step × active member of that step's working section), with the acting
  manager's own row pre-acknowledged.
- `TaskStepAcknowledgment.worker_id` is **every active member of the section**, not only
  `step.assigned_worker_id`. The model docstring says "the worker who owes the
  acknowledgment — step.assigned_worker_id at the moment of reassignment", but
  `add_task_steps.py:218-231` iterates `members_by_section`. The membership join in this
  plan is therefore *not* redundant with the ack row: it re-checks membership **as of
  read time**, so a worker moved out of a section stops seeing that section's
  reassignments. This is the behavior the intention asks for ("where the user has the
  working section assigned to that reassigned task step").
- Uniqueness guarantees make the core join 1:1, so no `DISTINCT` is needed:
  - `uix_task_step_ack_step_worker` — unique on (workspace_id, step_id, worker_id).
  - `uix_working_section_memberships_active` — unique on
    (workspace_id, working_section_id, user_id) where `removed_at IS NULL`.
- Offset pagination is the app-local convention (`07_queries_local.md` overrides the
  canonical cursor pagination). Existing services return
  `{limit, offset, has_more}` and fetch `limit + 1`.

## Clarifications required

None block implementation. Two decisions were made rather than deferred; both are
recorded under "Design decisions" with their rejected alternative, and both are cheap to
reverse if the frontend disagrees after reading the handoff:

- [x] Ordering — chronological (newest reassignment first) rather than grouped-by-section.
- [x] Acknowledged rows — included in the list, split out in the count.

## Acceptance criteria

1. `GET /api/v1/task-step-acknowledgments/reassigned-steps` returns only steps where
   **all** of the following hold: a live `TaskStepAcknowledgment` exists for
   (workspace, step, caller); the caller has an active `WorkingSectionMembership` for
   the step's working section; the step is live and its state is **not** in
   `TERMINAL_STEP_STATES` (`COMPLETED`, `SKIPPED`, `FAILED`, `CANCELLED`); the step's
   task is live; the working section is live.
2. Every item in `steps_pagination.items` has exactly the key set produced by
   `list_working_section_steps` items, plus one added key `acknowledgment`.
3. The response carries a top-level `working_sections` object keyed by working-section
   `client_id`, covering exactly the sections referenced by the page's steps, each
   serialized with `serialize_working_section_compact`.
4. `GET /api/v1/task-step-acknowledgments/reassigned-steps/count` returns
   `{"reassigned_steps_count": {"total": <int>, "unacknowledged": <int>}}` over the
   identical filter set, executing **one** SQL statement and loading no ORM entities.
5. `count.total` equals the number of items obtainable by paging the list endpoint to
   exhaustion **with no `q`**, for the same caller and workspace. With `q` present the list
   narrows and the count deliberately does not (D7).
5b. `q` matches case-insensitively and partially against the primary item's `article_number`
   and `sku`, is applied via `apply_string_filter`, and is length-validated at the router
   (`max_length=200`). A step whose task has no primary item is excluded by a non-empty `q`
   but **present** when `q` is absent. `55_query_filters_local.md`'s completion gate passes.
6. `list_working_section_steps` output is unchanged after the payload-builder extraction
   — proven by a characterization test written *before* the refactor.
7. Both endpoints are workspace-scoped and caller-scoped: a user never sees another
   user's obligations or another workspace's rows.
8. The list endpoint issues a bounded number of SQL statements independent of page size
   (no per-step query loop).
9. **Both responses match
   `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`
   field-for-field.** That handoff was written ahead of implementation and the frontend
   is building against it now, so it is the authoritative contract — where it and this
   plan disagree on a shape, **the handoff wins** and the discrepancy is an operator
   decision, not an implementer choice.

## Contracts and skills

### Read order

- `backend/architecture/<canonical>.md` (baseline)
- `backend/architecture/<canonical>_local.md` (app delta, where present)

Applied precedence: local extension overrides baseline for this app only.

### Contracts loaded

Core (always, per `task_system/backend_contract_goal_mapping_guide.md`):

- `backend/architecture/01_architecture.md`: layer boundaries (router → service → model).
- `backend/architecture/04_context.md`: `ServiceContext`, `ctx.workspace_id`, `ctx.user_id`,
  `ctx.query_params` — both services read the caller's identity from context, never from
  a request parameter.
- `backend/architecture/05_errors.md`: error taxonomy. These queries raise nothing by
  design (an empty result is a valid result, not a `NotFound`) — the contract is read to
  confirm that choice is legal.
- `backend/architecture/06_commands.md` + `06_commands_local.md`: read-only pass. Loaded
  to confirm no command/transaction/event obligation is triggered by a pure read.
- `backend/architecture/07_queries.md` + `07_queries_local.md`: **primary contract.**
  Query service signature, pagination envelope. Local overrides cursor pagination with
  offset — this plan follows the local rule.
- `backend/architecture/09_routers.md`: handler skeleton, `require_roles`, `run_service`,
  `build_ok` / `build_err`.
- `backend/architecture/21_naming_conventions.md`: service file/function naming, route
  path casing (kebab-case paths, snake_case payload keys).
- `backend/architecture/40_identity.md` + `40_identity_local.md`: `client_id` prefixes.
- `backend/architecture/41_user.md` + `41_user_local.md`: user serialization surface.
- `backend/architecture/42_event.md` + `42_event_local.md`: confirms no event is emitted.
- `backend/architecture/48_presence.md` + `48_presence_local.md`: confirms the reassigned
  page has no presence obligation.

### Added from guide

- `backend/architecture/46_serialization.md` + `46_serialization_local.md`: trigger —
  the deliverable is defined almost entirely by output shape, and shape parity with
  `list_working_section_steps` is acceptance criterion #2.
- `backend/architecture/24_multi_tenancy.md`: trigger — every clause in both new queries
  must be workspace-scoped; the joins reach five tables.
- `backend/architecture/25_soft_delete.md`: trigger — the filter set mixes three deletion
  idioms (`is_deleted` on ack/step/task/section, `removed_at` on membership,
  `deleted_at` on images). Getting these wrong is the most likely correctness bug here.
- `backend/architecture/22_performance.md`: trigger — "n+1". The neighbouring
  `list_pending_step_acknowledgments` loads its page with a per-step query loop; this
  plan must not copy that shape.
- `backend/architecture/15_testing.md` + `50_testing_strategy.md`: trigger —
  "deterministic testing", "fixture isolation", "n+1". Governs the integration tests and
  the pre-refactor characterization test.
- `backend/architecture/55_query_filters_local.md`: trigger — "search", "q param",
  "ilike", "partial match". **Mandatory read before implementing D6.** It is a local-only
  contract with a completion gate, and it *forbids* the inline-`.ilike` pattern the
  neighbouring `list_working_section_steps` uses — see D6 for how that is reconciled.

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination replaces cursor
  pagination. Delta used: `{items, limit, offset, has_more}` with a `limit + 1` fetch.
- `backend/architecture/06_commands_local.md`: `maybe_begin` / session-call safety.
  Delta used: **none** — no write, so no transaction wrapper.
- `backend/architecture/46_serialization_local.md`: app serializer inventory. Delta used:
  reuse `serialize_working_section_compact`, `serialize_step`, `serialize_task_light`,
  `serialize_item_worker_light`, `serialize_step_state_record_light`,
  `serialize_user_working_section_member`, `serialize_image` / `serialize_image_light`.

### Excluded contracts

- `03_models.md`, `30_migrations.md`: no schema change. Both endpoints read existing
  tables and existing indexes.
- `11_infra_events.md`, `13_sockets.md`, `56_realtime_layer.md`: no event or socket
  emission on a read.
- `16_background_jobs.md`, `12_infra_redis.md`, `51_worker_runtime.md`: no async work.
- *(none additional — `55_query_filters_local.md` was excluded in the first draft and is now
  required; see "Added from guide")*
- `47_notifications_local.md`: the reassignment notification already fires from
  `add_task_steps`; this plan adds none.

### Skill selection

- Primary skill: `skills/domains/content/add_query/SKILL.md`
  - Router trigger terms: `list`, `count`, `read`, `no write side effects`, `output shape`.
  - Task steps and acknowledgments are work-content records; the request is a pure
    list/count read with an explicitly specified output shape, which is exactly this
    skill's trigger condition.
- Secondary skill: `skills/domains/content/add_router_endpoint/SKILL.md`
  - Router trigger terms: `new endpoint`, `route`, `handler wiring`.
- Excluded alternatives:
  - `skills/domains/identity/add_query/SKILL.md` — the caller's identity is a *filter*
    here, not the entity being read.
  - `skills/domains/case/add_query/SKILL.md` — `cases_summary` is one embedded field
    inherited from the shared payload builder, not the subject of the query.
  - `skills/domains/image/add_query/SKILL.md` — `item_images` likewise comes from the
    shared builder unchanged.
  - `skills/domains/presence/add_presence_feature/SKILL.md` — no presence surface.
  - `skills/cross_cutting/ask_clarification_first/SKILL.md` — the intention document is
    unambiguous on filters and shape; the two open choices are decided in this plan.

### File read intent — pattern vs. relational

Apply the test before opening any file outside this plan's scope:

> "Am I reading this to understand **how to write** my new code — or to understand
> **what this existing code does**?"

**Permitted relational reads for this plan** (already surveyed during planning; re-read
only as needed):

- `app/beyo_manager/models/tables/tasks/task_step_acknowledgment.py` — exact columns and
  the two indexes the queries must hit.
- `app/beyo_manager/models/tables/working_sections/working_section_membership.py` —
  `removed_at` semantics and the active-membership partial unique index.
- `app/beyo_manager/services/queries/working_sections/list_working_section_steps.py` —
  the payload being extracted and matched. This is the reference implementation.
- `app/beyo_manager/services/queries/task_step_acknowledgments/list_pending_step_acknowledgments.py`
  — the existing acknowledgment serialization to reuse.
- `app/beyo_manager/domain/task_steps/constants.py` — `TERMINAL_STEP_STATES`.
- `app/beyo_manager/routers/api_v1/task_step_acknowledgments.py` — existing routes on the
  router being extended.

**Prohibited pattern reads** — the contract already defines these:

- Opening another query service to learn the query-service skeleton → `07_queries.md`.
- Opening another router to learn handler wiring → `09_routers.md`.
- Opening another serializer to learn output-shaping style → `46_serialization.md`.

## Design decisions

### D1 — Ordering: chronological, not section-grouped

`ORDER BY TaskStepAcknowledgment.created_at DESC, TaskStep.client_id DESC`.

Rationale: the page is an inbox. The newest reassignment is the one the worker has not
seen. The `client_id` tiebreak makes the order total, which offset pagination requires —
without it, two acks written in the same transaction (the common case: one manager
reassigns several steps at once, all sharing `now`) can shuffle between pages and cause
duplicated or skipped rows.

Rejected: `WorkingSection.order_list ASC, ...` — keeps a section's steps contiguous
across pages, which suits the container layout. Rejected because container grouping is a
client-side concern and the frontend already receives `order_list` inside the
`working_sections` map, so it can order containers itself. If the reassigned page turns
out to routinely exceed one page, revisit — this is a one-line change.

### D2 — Acknowledged rows are included in the list; the count splits them

The intention says "all TaskStepAcknowledgment instances for the currently logged-in
user … where the task step is not completed yet". It does not say *unacknowledged*.
`GET /pending` already covers the unacknowledged-only case for the acknowledgment modal.

So: the list returns every live ack row (acknowledged or not) and exposes
`first_seen_at` / `acknowledged_at` per item so the frontend can badge the unread ones.
The count returns both numbers in one statement, so a badge can show either without a
second round trip.

An optional `unacknowledged_only` boolean query param is added to the **list** endpoint
(default `false`) so the frontend can narrow client-side filtering into the query if the
page grows. It costs one extra `if` in the where-clause builder.

### D3 — `working_sections` is a map keyed by `client_id`, scoped to the page

```json
"working_sections": { "wsec_abc": { …compact… }, "wsec_def": { … } }
```

Keyed rather than a list because the frontend's only access pattern is
`working_sections[step.working_section_id]` while building containers — O(1), no
client-side index build. Scoped to the sections referenced by the current page, not to
every section the worker belongs to: a section with no reassigned step on this page has
no container to render.

### D4 — Upholstery-group fields are present but null

`list_working_section_steps` items carry `upholstery_group_key`,
`upholstery_group_image_url`, `upholstery_group_upholstery_id`, and
`upholstery_group_inventory` — populated only when `group_by_upholstery=true`. The
reassigned page has no grouping mode, so these are emitted as `null`. The keys are kept
so the frontend can reuse one TypeScript type for both surfaces (acceptance criterion #2).

Likewise `is_reassigned` is present and always `true` on this endpoint.

### D6 — `q` free-text search: same behaviour as the section list, contract-compliant shape

**What it searches.** Behavioural parity with `list_working_section_steps`: case-insensitive
partial match against the **primary item's** `article_number` and `sku`.

```python
_ALLOWED_STRING_COLUMNS = {
    "article_number": Item.article_number,
    "sku": Item.sku,
}
```

Not searched: upholstery `name` / `code`. On the section list those are gated behind
`upholstery_search=true`, which is out of scope here (see Scope), so `q` covers the two item
columns only.

**Shape: use `apply_string_filter`, not the neighbouring inline pattern.** This needs stating
because the two sources disagree:

- `55_query_filters_local.md` mandates
  `services/queries/utils/string_filter.py::apply_string_filter` and its completion gate
  declares a query **INCOMPLETE** if "inline `.ilike` calls appear in the query body instead".
- `list_working_section_steps.py:203-267` does exactly that — a hand-built
  `select(distinct(TaskStep.client_id))` subquery with `or_(...)` and `.ilike`.

The contract wins, per the pattern-authority rule: contracts define **how to write**,
implementation files show **what exists**. The operator asked for "the same principles as
`list_working_section_steps`" — that is a statement about *which columns are searchable*, which
this preserves exactly. It is not an instruction to copy a shape that predates (or diverges
from) the contract. **Do not "fix" `list_working_section_steps` to match** — that is a separate
change and would break the Step 1 characterization test.

**Why no subquery and no `DISTINCT` are needed here.** The section list needs them because its
`q` joins `TaskItem`/`Item` and it defends against fan-out. This query does not: the model
guarantees at most one active primary item per task —

```
uix_task_items_primary_active  UNIQUE (workspace_id, task_id)
                               WHERE role = 'primary' AND removed_at IS NULL
```

— so a `LEFT JOIN` on `(TaskItem.role == PRIMARY, removed_at IS NULL)` plus `Item` adds **at
most one row per step**, exactly like the ack and membership joins already do. The joins go
straight into the base statement, which is also what `apply_string_filter` requires ("any join
required by a column in `allowed_columns` must be present in the base statement **before**
`apply_string_filter` is called").

Use `isouter=True` for both. An inner join would silently drop every reassigned step whose task
has no primary item — a filter nobody asked for, and one that would apply even when `q` is
absent.

**`string_filters` is not exposed** (operator: "for now that endpoint will only have one query
param, the `q`"). Pass `"string_filters": None` in `query_params` anyway: `apply_string_filter`
reads `None` as "search every column in `allowed_columns`", which is the wanted behaviour, and
the contract's gate requires both keys present in the `ServiceContext` dict. Adding the param
later is then a router-only change.

**`q` does not apply to the count endpoint** — see D7.

### D7 — The count endpoint ignores `q`

`GET .../reassigned-steps/count` takes no parameters at all, including `q`. It answers "how many
reassignments do I have", which is a badge, not a search result. A count that silently narrowed
with a search term would make the badge disagree with itself depending on what the user last
typed.

Consequence for acceptance criterion #5: the list/count agreement guarantee holds **when `q` is
absent**. With `q` present the list is a subset and the count is deliberately not. This is
stated in the handoff so the frontend does not treat the difference as a bug.

### D5 — Shared payload builder, extracted rather than duplicated

`list_working_section_steps` builds its item payload inline across ~250 lines of batch
loading (steps, tasks, task items, items, upholsteries, requirements, images, users,
first-started timestamps, dependency sections, case summaries). Duplicating that into
the new query would guarantee drift; the intention explicitly requires the *same*
response object.

It is extracted verbatim into a shared helper, with the list-specific inputs
(`reassigned_step_ids`, the three upholstery-group maps) passed in as optional
arguments. This is a pure extraction: no behavior change, no reordering of statements,
no changed defaults.

Note that `step_record_payload.py` already sits in
`services/queries/working_sections/` and is already consumed cross-domain by
`list_pending_step_acknowledgments` — so placing the new helper beside it follows an
established precedent rather than inventing a location.

## Implementation plan

Execute in order. Each numbered step is one commit (see "Commit hygiene").

### Step 1 — Characterize the existing payload (test-first, no production change)

Create `app/tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py`.

Seed a workspace, user, working section, task, one primary task item with an item, and
one step. Call `list_working_section_steps` and assert on the **exact key set** of
`result["steps_pagination"]["items"][0]` and of the nested `last_state_record`, `task`,
and `item` objects. Assert the envelope keys of `steps_pagination`.

Cover both `group_by_upholstery=false` and `group_by_upholstery=true` so the extraction
cannot silently drop the group columns.

This test must pass **before** Step 2 and be unchanged **after** it. It is the proof for
acceptance criterion #6.

### Step 2 — Extract the batch payload builder (pure refactor)

Create `app/beyo_manager/services/queries/working_sections/steps_list_payload.py`:

```python
async def build_steps_list_payload(
    ctx: ServiceContext,
    *,
    page_ids: list[str],
    reassigned_step_ids: set[str] | None = None,
    group_key_by_step_id: dict[str, str | None] | None = None,
    group_image_by_step_id: dict[str, str | None] | None = None,
    group_uph_id_by_step_id: dict[str, str | None] | None = None,
) -> list[dict]:
    """Batch-build the step-card payloads for an already-paginated list of step ids.

    Returns one dict per resolvable id, in ``page_ids`` order. Ids whose step row is
    missing are skipped rather than yielding a null entry — callers paginate on ids, so
    a vanished step must not shift the list shape.
    """
```

Move, **without editing the logic**, lines 304–592 of the current
`list_working_section_steps.py` — everything from the `steps_result` load through the
`items_payload` assembly loop. Preserve exactly:

- the `if not page_ids: return []` early exit;
- the `select(TaskStep).options(selectinload(TaskStep.latest_state_record).selectinload(StepStateRecord.pause_reason))` load;
- `load_upholstery_group_inventories` for the page's group upholstery ids;
- the `try/except Exception: case_summary_by_task = {}` swallow around the case-summary
  query — it is deliberate defensive behavior, not a bug to fix in a refactor commit;
- the first-image-rich / rest-light image treatment, including the
  `first_image.pop("image_annotations", None)`;
- the `dep_ws_map` dependency-working-section ordering
  (`order_list ASC NULLS LAST, client_id ASC`);
- the `step_map.get(step_id)` / `continue` skip for missing steps;
- key order in the assembled dict.

Then reduce `list_working_section_steps` to: id selection + filters + ordering +
pagination (unchanged), followed by

```python
items_payload = await build_steps_list_payload(
    ctx,
    page_ids=page_ids,
    reassigned_step_ids=reassigned_step_ids,
    group_key_by_step_id=group_key_by_step_id,
    group_image_by_step_id=group_image_by_step_id,
    group_uph_id_by_step_id=group_uph_id_by_step_id,
)
```

Delete now-unused imports from `list_working_section_steps.py`. Keep the existing
early-return-on-empty-page branch there (it returns the envelope with `items: []`).

Run the Step 1 test. It must pass with zero edits.

### Step 3 — Shared acknowledgment serializer

`list_pending_step_acknowledgments._serialize_acknowledgment` is module-private and now
needed by two services. Promote it to
`app/beyo_manager/domain/task_steps/serializers.py` (the file exists and currently holds
`serialize_task_step_compact`) as:

```python
def serialize_task_step_acknowledgment(
    ack: TaskStepAcknowledgment,
    *,
    worker: User | None = None,
    created_by: User | None = None,
) -> dict:
```

Body identical to the current private function. Update
`list_pending_step_acknowledgments` to import it and delete the local copy — a
same-shape swap, so `/pending` responses are unchanged.

### Step 4 — Shared filter builder for the two new queries

Create `app/beyo_manager/services/queries/task_step_acknowledgments/_reassigned_steps_filters.py`:

```python
def reassigned_steps_where_clauses(ctx: ServiceContext, *, unacknowledged_only: bool = False) -> list:
    """The single definition of 'a reassigned step this caller should see'.

    Shared by the list and the count so the badge can never disagree with the page.
    """
```

Returning the clause list:

```python
TaskStepAcknowledgment.workspace_id == ctx.workspace_id,
TaskStepAcknowledgment.worker_id == ctx.user_id,
TaskStepAcknowledgment.is_deleted.is_(False),
TaskStep.state.notin_(TERMINAL_STEP_STATES),
```

plus `TaskStepAcknowledgment.acknowledged_at.is_(None)` when `unacknowledged_only`.

And a companion that applies the four joins, so both queries build the same FROM:

```python
def reassigned_steps_select_from(stmt, ctx: ServiceContext):
    """Join ack → step → task → membership → section, all live and workspace-scoped."""
```

Joins:

| Join | Condition |
|---|---|
| `TaskStep` | `client_id == ack.step_id`, `workspace_id == ctx.workspace_id`, `is_deleted is False` |
| `Task` | `client_id == TaskStep.task_id`, `workspace_id == ctx.workspace_id`, `is_deleted is False` |
| `WorkingSectionMembership` | `working_section_id == TaskStep.working_section_id`, `user_id == ctx.user_id`, `workspace_id == ctx.workspace_id`, `removed_at is None` |
| `WorkingSection` | `client_id == TaskStep.working_section_id`, `workspace_id == ctx.workspace_id`, `is_deleted is False` |

All four are INNER joins — each is a required condition, so an outer join plus a null
check would be strictly worse. Note the three distinct soft-delete idioms
(`is_deleted`, `removed_at`, and `deleted_at` further down in the image load); do not
normalize them.

Acceptance criterion #5 (count agrees with list) holds **because** both callers use this
module. Do not inline either helper into one of the two services.

### Step 5 — `list_reassigned_steps`

Create `app/beyo_manager/services/queries/task_step_acknowledgments/list_reassigned_steps.py`.

```python
_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50

async def list_reassigned_steps(ctx: ServiceContext) -> dict:
```

Module-level constant, per `55_query_filters_local.md` ("`allowed_columns` is defined **per
query** as a module-level constant"):

```python
_ALLOWED_STRING_COLUMNS = {
    "article_number": Item.article_number,
    "sku": Item.sku,
}
```

1. Read `limit` (clamped to `_MAX_LIMIT`), `offset`, `unacknowledged_only`, `q`, and
   `string_filters` from `ctx.query_params`, mirroring how `list_working_section_steps`
   coerces its params.
2. Select the page of ids and their ack rows in one statement:
   `select(TaskStepAcknowledgment.step_id, TaskStepAcknowledgment.client_id)` — or select
   the `TaskStepAcknowledgment` entity, which is simpler and the row count is bounded by
   `limit`. Apply Step 4's joins and clauses, order by D1, `.offset(offset).limit(limit + 1)`.

   **Before** applying the ordering and pagination, add the two search joins (D6) — always,
   not only when `q` is set, so the statement shape does not vary:

   ```python
   stmt = (
       stmt
       .join(
           TaskItem,
           and_(
               TaskItem.task_id == TaskStep.task_id,
               TaskItem.workspace_id == ctx.workspace_id,
               TaskItem.role == TaskItemRoleEnum.PRIMARY,
               TaskItem.removed_at.is_(None),
           ),
           isouter=True,
       )
       .join(
           Item,
           and_(
               Item.client_id == TaskItem.item_id,
               Item.workspace_id == ctx.workspace_id,
               Item.is_deleted.is_(False),
           ),
           isouter=True,
       )
   )
   stmt = apply_string_filter(stmt, q, string_filters, _ALLOWED_STRING_COLUMNS)
   ```

   `apply_string_filter` returns the statement unchanged when `q` is falsy, so the no-search
   path costs only the two left joins — bounded to one row per step by
   `uix_task_items_primary_active` (D6).
3. `has_more = len(rows) > limit`; `page = rows[:limit]`; `page_ids = [a.step_id for a in page]`.
4. Early return on empty page with `{"steps_pagination": {"items": [], "limit":…,
   "offset":…, "has_more": has_more}, "working_sections": {}}`.
5. Batch-load the users referenced by the page's ack rows (`worker_id`, `created_by_id`)
   in one `select(User).where(User.client_id.in_(...))`.
6. `items = await build_steps_list_payload(ctx, page_ids=page_ids, reassigned_step_ids=set(page_ids))`
   — every step on this page is by definition reassigned, so `is_reassigned` is `true`
   throughout. Pass no group maps (D4).
7. Attach `payload["acknowledgment"] = serialize_task_step_acknowledgment(ack, worker=…,
   created_by=…)` by joining `items` back to `page` on `step_id`. Build an
   `ack_by_step_id` dict first — `build_steps_list_payload` may return fewer items than
   `page_ids` if a step vanished mid-request, so do not zip positionally.
8. Load the page's working sections: collect `{item["working_section_id"] for item in items}`,
   one `select(WorkingSection)` filtered to live + workspace, serialize each with
   `serialize_working_section_compact`, key by `client_id`.
9. Return:

```python
{
    "steps_pagination": {"items": items, "limit": limit, "offset": offset, "has_more": has_more},
    "working_sections": working_sections_by_id,
}
```

Statement budget: 1 (ids) + 1 (users) + ~11 (shared builder) + 1 (sections) — constant
in page size. This is the point of Step 2; do not fall back to a per-step loop.

### Step 6 — `count_reassigned_steps`

Create `app/beyo_manager/services/queries/task_step_acknowledgments/count_reassigned_steps.py`.

```python
async def count_reassigned_steps(ctx: ServiceContext) -> dict:
```

One statement, no entities loaded, no pagination:

```python
select(
    func.count().label("total"),
    func.count().filter(TaskStepAcknowledgment.acknowledged_at.is_(None)).label("unacknowledged"),
)
```

with Step 4's joins and clauses (`unacknowledged_only=False`). Return:

```python
{"reassigned_steps_count": {"total": row.total or 0, "unacknowledged": row.unacknowledged or 0}}
```

`func.count().filter(...)` renders as a Postgres `FILTER (WHERE …)` aggregate, so both
numbers come from one scan. `count(*)` over an empty result set returns `0`, not `NULL`,
but keep the `or 0` guard so the contract holds regardless of dialect.

Take no `limit` / `offset` — a count endpoint that paginates is a bug waiting to happen — and
no `q` either (D7). Do not add the `TaskItem` / `Item` search joins here: with no `q` to apply
they would be pure cost on the endpoint whose whole purpose is being cheap.

### Step 7 — Routes

Edit `app/beyo_manager/routers/api_v1/task_step_acknowledgments.py`. Both routes are
literal paths on a router with no path parameters, so registration order is irrelevant
and no `/{...}` route can shadow them.

```python
@router.get("/reassigned-steps")
async def list_reassigned_steps_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    unacknowledged_only: bool = Query(False),
    q: str | None = Query(None, max_length=200),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "unacknowledged_only": str(unacknowledged_only).lower(),
            "q": q,
            # Not exposed as a route param yet (D6). Passed explicitly because
            # 55_query_filters_local.md's completion gate requires both keys in the
            # ServiceContext dict, and None means "search every allowed column".
            "string_filters": None,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_reassigned_steps, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/reassigned-steps/count")
async def count_reassigned_steps_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={}, query_params={}, identity=claims, session=session)
    outcome = await run_service(count_reassigned_steps, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

Roles match the sibling `/pending` route: `[ADMIN, MANAGER, WORKER]`. The services scope
to `ctx.user_id` regardless of role — an admin calling this sees *their own*
obligations, which is correct: this is a personal inbox, not an admin view.

The router is already registered at `/api/v1/task-step-acknowledgments`
(`routers/api_v1/__init__.py:101-105`). No `__init__.py` change is needed.

Note the boolean coercion: `list_working_section_steps` passes booleans through
`query_params` as `"true"` / `"false"` strings, and the service re-parses with
`str(...).lower() == "true"`. Follow the same convention for `unacknowledged_only` so
the two query services read params identically.

### Step 8 — Integration tests

Create `app/tests/integration/services/queries/task_step_acknowledgments/` (with
`__init__.py` if sibling test packages carry one) containing:

`test_list_reassigned_steps_integration.py`:

| Case | Expectation |
|---|---|
| Happy path: live ack + active membership + `PENDING` step | step present; `acknowledgment` populated; `is_reassigned is True` |
| Membership `removed_at` set | excluded |
| No membership row at all | excluded |
| Step state `COMPLETED` / `SKIPPED` / `FAILED` / `CANCELLED` (parametrized over `TERMINAL_STEP_STATES`) | excluded |
| Ack `is_deleted=True` | excluded |
| Step `is_deleted=True` | excluded |
| Task `is_deleted=True` | excluded |
| Working section `is_deleted=True` | excluded |
| Ack belongs to a different `worker_id` | excluded |
| Ack belongs to a different `workspace_id` | excluded |
| Already-acknowledged ack | **included**, with `acknowledgment.acknowledged_at` non-null (D2) |
| `unacknowledged_only=true` | acknowledged row excluded |
| 3 acks, `limit=2` | 2 items, `has_more is True`; `offset=2` returns the third, `has_more is False`; no id appears on both pages |
| Steps in two sections | `working_sections` has exactly those two keys, each with `name` / `order_list` / `image` / `allows_batch_working` / `allows_shopify_product_modifications` |
| Empty result | `items == []`, `working_sections == {}`, `has_more is False` |
| Payload parity | item key set equals the key set asserted in the Step 1 characterization test, plus `acknowledgment` |
| Ordering | two acks with distinct `created_at` → newer first |
| `q` matches `article_number` exactly | that step only |
| `q` matches a **substring**, mixed case (`"302.4"`, `"sofa"` vs `SOFA-3S`) | matched — proves ILIKE `%…%`, not equality or case-sensitive |
| `q` matches `sku` but not `article_number` | matched — proves the OR across both columns |
| `q` matches nothing | `items == []`, `working_sections == {}`, `has_more is False` |
| step whose task has **no primary item**, with `q` set | excluded |
| the same step, `q` absent | **present** — proves the left joins don't filter |
| `q` set to an upholstery name/code | **not** matched (upholstery search is out of scope, D6) |
| `q` + pagination together | `has_more` reflects the filtered set, not the unfiltered one |
| `q` does not widen the visible set | a step matching `q` but failing membership/terminal/workspace checks stays excluded |

`test_count_reassigned_steps_integration.py`:

| Case | Expectation |
|---|---|
| Mixed set: 2 unacknowledged + 1 acknowledged, all visible | `{"total": 3, "unacknowledged": 2}` |
| Every exclusion case from the list table | not counted |
| Agreement | `count.total` equals the item count from paging the list to exhaustion with `limit=1` **and no `q`** (acceptance criterion #5) |
| `q` is ignored here | the count is identical whether or not the caller has a matching search term; `q` is not a route param on this endpoint (D7) |
| Nothing visible | `{"total": 0, "unacknowledged": 0}` |

Follow the seeding style in
`app/tests/integration/services/queries/working_sections/test_get_user_last_active_step_record_integration.py`:
`uuid4().hex[:8]` suffixes for isolation, a local `_ctx(db_session, workspace_id=…, user_id=…)`
helper, `db_session.flush()` between inserts. `app/tests/factories/` is empty — seed
inline.

Write the "Agreement" case as a real loop over the list endpoint, not a hardcoded
number. It is the only test that would catch the list and the count drifting apart if
someone later inlines a filter (the failure mode Step 4 exists to prevent).

### Step 9 — Handoff conformance (the handoff already exists)

**The handoff was written ahead of implementation and the frontend is building against it
in parallel.** It lives at
`backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`
and is the **authoritative API contract** for this delivery — it outranks any shape
detail in this plan if the two ever disagree.

Do **not** write a second handoff. This step's deliverable is *conformance evidence*, not
a new document:

1. Verify the implemented responses match the handoff **field-for-field**: every key,
   every nullability, every enum value, the `working_sections` map shape, the envelope,
   and the error table in §10.
2. Record the verification in this plan's Review log.
3. Flip the liveness table at the top of the handoff from ⏳ to ✅ **only if the operator
   asks** — following the ruling recorded in the `declared_worker_states` plans, the
   liveness row is operator-owned and an implementer must never flip it.
4. If the implementation cannot match some documented shape, **stop and raise it** — that
   is an operator decision, and the handoff gets edited first. Do not silently deviate;
   the frontend has already built against the documented shape.

The "Handoff requirements" section below records what the handoff had to contain and is
retained as the checklist for step 1 above.

### Step 10 — Summary

Create `backend/docs/architecture/implemented_summaries/SUMMARY_reassigned_steps_endpoints_20260731.md`
from `TEMPLATE_SUMMARY.md`, and move this plan to its archived location per
`skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.

## Handoff requirements

> **Already satisfied.** The handoff was authored ahead of implementation (2026-07-31) at
> `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`.
> This list is retained as the **conformance checklist for Step 9** — verify the built
> endpoints against each item. Do not author a new document.

The handoff is self-sufficient — a frontend engineer can write the TypeScript types
without opening the backend. It contains:

1. **Both endpoint URLs**, verbs, auth requirement (bearer JWT, roles `ADMIN`,
   `MANAGER`, `WORKER`), and the note that both are scoped to the calling user.
2. **Query parameters**: `limit` (default 50, max 200), `offset` (default 0, min 0),
   `unacknowledged_only` (default `false`) for the list; none for the count.
3. **The response envelope**, showing that every endpoint response is wrapped by
   `build_ok` / `build_err` (document the actual wrapper shape — read
   `app/beyo_manager/routers/http/response.py`, do not assume it).
4. **A fully expanded example response** for the list endpoint with one item, every key
   present, realistic values, and `null`s shown explicitly where D4 applies.
5. **A field-by-field table** for each object, with type and nullability, covering:
   - the step level: all 22 keys from `serialize_step`, plus `updated_at`, `created_by`,
     `updated_by`, `last_state_record`, `task`, `item`, `item_images`, `cases_summary`,
     `dependency_working_sections`, `is_reassigned`, the four `upholstery_group_*` keys,
     and `acknowledgment`;
   - `acknowledgment`: `client_id`, `step_id`, `task_id`, `reason`, `worker`,
     `created_by`, `first_seen_at`, `acknowledged_at`, `created_at`;
   - `last_state_record` (`serialize_step_state_record_light`): `state`, `pause_reason`,
     `description`, `entered_at`, `exited_at`, `last_action_by`, `first_started_at`;
   - `task` (`serialize_task_light`): `client_id`, `task_type`, `priority`, `state`,
     `return_source`, `item_location`, `ready_by_at`, `scheduled_start_at`,
     `scheduled_end_at`, `return_method`, `assortment`;
   - `item` (`serialize_item_worker_light`): `client_id`, `article_number`, `sku`,
     `state`, `item_category_id`, `quantity`, `item_position`, `item_zone`,
     `upholstery_requirement[]`;
   - `item_images`: first element is the rich `serialize_image` shape minus
     `image_annotations`; subsequent elements are `serialize_image_light`. Call this
     asymmetry out explicitly — it is easy to miss and will break a naive shared type.
   - user objects (`serialize_user_working_section_member`): `client_id`, `username`,
     `profile_picture`;
   - `working_sections[<id>]` (`serialize_working_section_compact`): `client_id`, `name`,
     `image`, `order_list`, `allows_batch_working`,
     `allows_shopify_product_modifications`;
   - `dependency_working_sections[]`: `{working_section, prerequisite_step_state}`.
6. **Enum value lists** for `state` (step), `readiness_status`, `task.state`,
   `task_type`, `priority` — read from `domain/task_steps/enums.py` and
   `domain/tasks/enums.py` and enumerate the literal string values.
7. **The explicit statement that the item shape is identical to
   `GET /api/v1/working-sections/{id}/steps` items plus `acknowledgment`**, so the
   frontend can reuse its existing step-card type by extension rather than redefining it.
8. **Container-building guidance**: group `items` by `step.working_section_id`, look the
   section up in `working_sections`, order containers by `order_list` (nulls last, then
   `name`). Items arrive newest-reassignment-first (D1), so a section's steps may span
   pages — say so.
9. **Timestamp format**: all timestamps are ISO 8601 strings from `.isoformat()`, or
   `null`. Stored as timezone-aware UTC.
10. **Error cases**: 401 on missing/invalid token, 403 on an out-of-role caller. Note
    that neither endpoint 404s — no visible reassignments is an empty success response,
    not an error.
11. **Semantics the frontend needs to get right**:
    - a step leaves the list the moment it reaches a terminal state, without any
      acknowledgment action;
    - a step leaves the list if the worker is removed from the section;
    - `acknowledged_at != null` means the worker already confirmed it; the row still
      appears (D2);
    - acknowledging is done through the existing
      `POST /api/v1/task-step-acknowledgments/acknowledge` with `{step_ids: [...]}`,
      which this plan does not change — link it.
12. **Which existing socket events should trigger a refetch.** This plan adds no event;
    the frontend must drive both the page and the badge off events that already exist.
    Document this table and its gap:

    | The list/count changes because… | Existing event | Kind |
    |---|---|---|
    | a new reassignment lands | `task:step-acknowledgment-created` (`{task_id, step_ids}`) | targeted, per-worker |
    | a step is removed, destroying the obligation | `task:step-acknowledgment-removed` | targeted, per-worker |
    | the worker completes/skips/fails/cancels a reassigned step | `task:step-state-changed` | **workspace broadcast** |
    | the worker is removed from a working section | none acknowledgment-specific | — |
    | the worker acknowledges | none — the client made the call | — |

    Call the gap out explicitly: **only the count going *up* has a targeted event.** The
    two shrink paths are covered either by a workspace-wide broadcast the client must
    filter, or not at all. Recommend the frontend refetch the count on
    `task:step-acknowledgment-created`, `task:step-acknowledgment-removed`, and
    `task:step-state-changed`, and treat the membership-change case as a cold-start
    concern (refetch on app foreground / page mount) rather than a live one.

    The `task:step-acknowledgment-*` events were built for the existing `/pending`
    modal flow ("refetch its pending-acknowledgments query", per the source comments) —
    they happen to fit this page, but the reassigned page is a second consumer they were
    not designed for. If the badge proves laggy in practice, adding a targeted event on
    terminal transition is the follow-up; it is deliberately **out of scope here** and
    must not be smuggled into this plan's commits.

## Risks and mitigations

- **Risk:** The Step 2 extraction silently alters `list_working_section_steps` output.
  This is the highest-impact risk in the plan — that endpoint drives the worker app's
  main section-list screen and currently has no test coverage.
  **Mitigation:** Step 1 writes the characterization test first and Step 2 must leave it
  untouched. The extraction is a move, not a rewrite: no logic edits, no statement
  reordering, no "while I'm here" cleanups. Keep Steps 1 and 2 as separate commits so
  the refactor can be reverted alone.

- **Risk:** The list and the count drift apart, so the badge shows a number the page
  cannot produce.
  **Mitigation:** Step 4's shared filter module is the single definition, and the
  "Agreement" test in Step 8 fails if anyone inlines a clause.

- **Risk:** Silent cross-tenant or cross-user leakage through one un-scoped join. Five
  tables are joined and three different soft-delete idioms are in play.
  **Mitigation:** every join condition in Step 4 carries `workspace_id` explicitly, the
  clause list carries `worker_id == ctx.user_id`, and Step 8 tests both the
  different-worker and different-workspace exclusions.

- **Risk:** Copying the per-step loading loop from the neighbouring
  `list_pending_step_acknowledgments` (which calls `load_step_with_latest_record` +
  `build_step_record_payload` once per row) into the new list, producing ~12 queries per
  step.
  **Mitigation:** Step 5 mandates `build_steps_list_payload`; acceptance criterion #8
  states the constant-statement requirement. Do not "improve" `/pending` in this plan —
  that is a separate, out-of-scope change.

- **Risk:** Unstable pagination. Acks created in one manager action share `created_at`
  to the microsecond, so ordering on `created_at` alone lets rows swap between pages.
  **Mitigation:** the `TaskStep.client_id DESC` tiebreak in D1, and the
  no-id-on-both-pages assertion in Step 8.

- **Risk:** Query performance as the ack table grows.
  **Mitigation:** none needed now, and no new index is added. The partial index
  `ix_task_step_ack_pending_by_worker (workspace_id, worker_id) WHERE acknowledged_at IS
  NULL AND is_deleted = false` covers the `unacknowledged_only` path; the general path
  is served by the `worker_id` index plus the `workspace_id` index. If the count
  endpoint is polled aggressively and shows up in slow queries, the follow-up is a
  partial index on `(workspace_id, worker_id) WHERE is_deleted = false` — deliberately
  deferred rather than added speculatively.

- **Risk:** Commit collision with the `system_transition_reasons` work running in
  parallel.
  **Mitigation:** see "Commit hygiene" — the file sets are disjoint, and the one shared
  concept (`StepStateRecord` serialization) is consumed through
  `serialize_step_state_record_light`, which this plan does not modify.

## Commit hygiene (parallel-work constraint)

The `system_transition_reasons` implementation is in flight in this repo. Its working
set is:

```
app/beyo_manager/domain/users/serializers.py
app/beyo_manager/domain/transitions/                      (new)
app/beyo_manager/models/tables/tasks/step_state_record.py
app/beyo_manager/models/tables/users/user_shift_state_record.py
app/beyo_manager/services/queries/worker_stats/…
app/migrations/versions/a7d21f4c8b03_add_transition_reason_columns.py
app/tests/unit/domain/transitions/                        (new)
app/tests/integration/services/queries/worker_stats/…
docs/architecture/**/system_transition_reasons/**
```

This plan's working set is disjoint:

```
app/beyo_manager/domain/task_steps/serializers.py                              (edit)
app/beyo_manager/services/queries/working_sections/steps_list_payload.py       (new)
app/beyo_manager/services/queries/working_sections/list_working_section_steps.py (edit)
app/beyo_manager/services/queries/task_step_acknowledgments/_reassigned_steps_filters.py (new)
app/beyo_manager/services/queries/task_step_acknowledgments/list_reassigned_steps.py     (new)
app/beyo_manager/services/queries/task_step_acknowledgments/count_reassigned_steps.py    (new)
app/beyo_manager/services/queries/task_step_acknowledgments/list_pending_step_acknowledgments.py (edit, Step 3 only)
app/beyo_manager/routers/api_v1/task_step_acknowledgments.py                   (edit)
app/tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py (new)
app/tests/integration/services/queries/task_step_acknowledgments/**            (new)
docs/architecture/implemented_summaries/SUMMARY_reassigned_steps_endpoints_20260731.md (new)
docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md
    ^ ALREADY WRITTEN — read-only for the implementer, except an operator-authorized
      liveness-table flip. Do not rewrite it to match the code; make the code match it.
```

Rules for the implementing session:

- **Do not** run `git add -A` or `git commit -a`. Stage the specific paths listed above,
  per commit.
- **Do not** touch `domain/users/serializers.py`. `serialize_user_working_section_member`
  is imported and used as-is; if the parallel work changes its output, both endpoints
  inherit the change, which is correct.
- **Do not** touch `models/tables/tasks/step_state_record.py`. This plan reads
  `latest_state_record` through the existing relationship and serializes it through the
  existing `serialize_step_state_record_light`.
- **No migration.** If a migration file appears in the diff, something is wrong — both
  endpoints are pure reads over existing tables and indexes.
- One commit per implementation step, in order, each independently revertible:

  1. `test(working-sections): characterize list_working_section_steps item payload`
  2. `refactor(queries): extract batch step-list payload builder`
  3. `refactor(task-steps): promote acknowledgment serializer to domain`
  4. `feat(task-step-acknowledgments): add shared reassigned-steps filters`
  5. `feat(task-step-acknowledgments): add list_reassigned_steps query`
  6. `feat(task-step-acknowledgments): add count_reassigned_steps query`
  7. `feat(routers): expose reassigned-steps list and count endpoints`
  8. `test(task-step-acknowledgments): integration tests for reassigned steps`
  9. `docs: summary for reassigned-steps endpoints`
     (the handoff already exists and is committed — Step 9 adds conformance evidence to
     this plan's Review log, not a new handoff document)

- Commits 1–2 are the risky pair. Run the full working-sections test module after commit
  2 before proceeding.

## Validation plan

| Check | Expected result |
|---|---|
| `pytest app/tests/integration/services/queries/working_sections/ -q` (after Step 2) | all pass, characterization test included, no edits to it |
| `pytest app/tests/integration/services/queries/task_step_acknowledgments/ -q` | all pass |
| `pytest -q` **run from `backend/app/`** | no new failure nodes vs. the pre-change baseline. Capture the baseline before starting — the parallel feature set lands commits in this tree and its failures are not yours (T8). **Measured 2026-07-31 at `d70f7d8`: 26 failed / 1398 passed / 0 errors.** A figure in the hundreds, or any non-zero *error* count, means a broken environment — a baseline worktree lacks both `app/.env*` **and** `app/.venv`, and reproducing a bad number twice does not make it valid. Simplest avoidance: measure in the main tree at the base commit rather than in a worktree. |
| App boots and OpenAPI lists both routes under the `task-step-acknowledgments` tag | `/api/v1/task-step-acknowledgments/reassigned-steps` and `.../reassigned-steps/count` present |
| Manual: `GET .../reassigned-steps` as a worker with a seeded reassignment | 200; `steps_pagination.items[0].acknowledgment` populated; `working_sections` has the step's section |
| Manual: `GET .../reassigned-steps/count` for the same worker | `total` equals the item count from the list call |
| Manual: `GET /api/v1/working-sections/{id}/steps` before and after the change | responses byte-identical for the same fixture |
| Echo SQL (or `EXPLAIN` via query logging) on a 50-item page | statement count is constant, not ~50 × N |
| Handoff conformance: diff each documented field in the handoff §3.1/§3.5/§3.6/§4/§5/§6/§10 against a real response | every key, nullability, and enum value matches; `q` behaves as §3.5 documents; evidence recorded in the Review log |
| Walk `55_query_filters_local.md`'s "Completion gate" checklist against `list_reassigned_steps` | all seven boxes clear: `apply_string_filter` used, no inline `.ilike`, no secret columns, router `max_length=200`, `string_filters` not parsed inline, both keys in `query_params`, joins present before the call |
| `GET .../reassigned-steps?q=<201 chars>` | `422` from the router, not a database round-trip |
| `git log --stat` for the 9 commits | no file outside this plan's working set appears; the handoff file is **not** modified |

## Review log

- `2026-07-31` `planning_session_claude`: plan authored from
  `INTENTION making_endpoint_for_getting_reasign_tasks.md`. Surveyed
  `task_step_acknowledgment.py`, `add_task_steps.py`, `list_working_section_steps.py`,
  `list_pending_step_acknowledgments.py`, `working_section_membership.py`,
  `step_record_payload.py`, and the `task_step_acknowledgments` router. Recorded the
  discrepancy between the `TaskStepAcknowledgment.worker_id` docstring and the actual
  fan-out in `add_task_steps` — it is the reason the membership join is load-bearing
  rather than redundant.
- `2026-07-31` `operator (David)`: **`q` added to the list endpoint** — the one filter the
  inbox still needs. Recorded as D6/D7; `55_query_filters_local.md` moved from excluded to
  required; acceptance criteria 5/5b, the test tables and the validation plan updated. The
  contract-vs-`list_working_section_steps` conflict on inline `.ilike` is resolved in D6 in
  favour of the contract, with the neighbouring file explicitly left alone.
- `2026-07-31` `operator (David)`: the frontend handoff now also documents the **removal of
  the `ended_shift` task-step state** (`INTENTION_ended_shift_step_state_collapse_20260731`,
  sequenced as a successor set). **That is a handoff-only change — no deliverable in this plan
  touches it**, and no commit here may implement any part of it. The handoff marks it as not
  yet live and tells the frontend to tolerate `ended_shift` until it lands.

- `2026-07-31` `implementer`: **Step 1 complete.** Characterization test added, passing (6 passed
  in the working-sections module). Stopped before Step 2 so the extraction could be handed to a
  bounded pass.
- `2026-07-31` `reviewer`: Step 1 **accepted** with one gap closed in review — the test asserted
  the `upholstery_group_*` keys but not their *values*, and with no upholstery seeded the two
  parametrized runs were indistinguishable (all-null in both). An extraction that accepted the
  three group maps and never read them would have passed. Fixed by seeding an `Upholstery` +
  `ItemUpholstery` on the primary item and asserting the values per mode.

  **The reported baseline of 334 failed / 995 passed / 38 errors was rejected as invalid.** The
  baseline worktrees carried `app/.env*` but no `app/.venv`; the tree actually measures 26 failed
  / 1398 passed / 0 errors. Recorded in the Validation plan above and in the
  `system_transition_reasons` master plan's "Validation baseline" so the next session inherits the
  correction rather than the number.

- `2026-07-31` `reviewer (adversarial pass, Steps 2–5)`: **NEEDS_CHANGES.** The extraction — the
  one high-risk item — is clean and verified. The delivery is not: it stops mid-Step-5.

  **What was verified as correct** (do not re-litigate these):

  - **Step 2 is a move, not a rewrite.** `sed -n '304,592p'` of the pre-commit
    `list_working_section_steps.py` versus `steps_list_payload.py:54-342` is **byte-identical**
    (`diff` empty). All five listed hazards survive verbatim: the `try/except Exception:
    case_summary_by_task = {}` swallow (`steps_list_payload.py:122-123`), the first-image-rich
    treatment including `first_image.pop("image_annotations", None)` (`:207-213`), the
    `step_map.get(step_id)` / `continue` skip (`:301-303`), dependency ordering
    `order_list ASC NULLS LAST, client_id ASC` (`:279-282`), and key order (`:320-341`). The
    caller's remaining diff is import pruning plus the six-line builder call
    (`list_working_section_steps.py:284-291`); the early-empty envelope
    `{"steps_pagination": {"items": [], …}}` stays in the caller (`:294-302` pre-move, retained).
  - **The characterization test is untouched by Step 2** — commit `1204916` has a two-file stat
    and neither is the test — **and it discriminates.** Probed: dropping
    `group_image_by_step_id` from the builder call site fails
    `test_list_working_section_steps_payload_key_sets_are_stable[True]`. Restored after.
  - **Visibility and scoping are correct**, proven by a throwaway probe module (14 cases, all
    passing, deleted after the run): ack + active membership + non-terminal → visible;
    membership `removed_at` set afterwards → **invisible** (membership is re-checked at read
    time, `_reassigned_steps_filters.py:50-58`); each of the four `TERMINAL_STEP_STATES`
    excluded individually; `ENDED_SHIFT` still visible; another worker's and another
    workspace's acks both invisible. All four joins carry `workspace_id`, and the three
    soft-delete idioms are each used on the right table (`is_deleted` on step/task/section,
    `removed_at` on membership).
  - **Pagination is stable.** Three acks seeded with an identical `created_at`, paged at
    `limit=1`: no id repeated, none skipped. The `TaskStep.client_id DESC` tiebreak
    (`list_reassigned_steps.py:62-65`) is doing the work.
  - **`q` behaves as the handoff documents.** `apply_string_filter` used, no inline `.ilike`,
    joins added unconditionally and before the call (`list_reassigned_steps.py:39-61`),
    `isouter=True` on both. Probed: a task with no primary item is **returned** with no `q` and
    **dropped** by any non-empty `q`; partial and mixed-case matches hit; an upholstery name
    does **not** match. `uix_task_items_primary_active` still exists
    (`models/tables/tasks/task_item.py:53`), so the absence of `DISTINCT` remains sound.
  - **Payload parity.** The item key set is exactly the characterization test's 38 keys plus
    `acknowledgment` — matches handoff §5.1 field-for-field. `is_reassigned` is `true`
    throughout, the four `upholstery_group_*` keys are present and `null` (D4).
    `working_sections` is an object keyed by `client_id` covering exactly the page's sections;
    an empty page returns `working_sections: {}` with the full envelope.
  - **Performance.** A SQLAlchemy `before_cursor_execute` listener measures **14 statements for
    a 1-item page and 14 for a 10-item page** — constant, not per-step. The per-step
    `load_step_with_latest_record` loop was **not** copied, and
    `list_pending_step_acknowledgments` was **not** "improved" (its loop at `:71-81` is intact;
    only the serializer import changed).
  - `ruff check` is clean on every touched file. **No migration** belongs to this change — the
    untracked `app/migrations/versions/97b60e06d42a_backfill_other_task_priority_transition_.py`
    is `system_transition_reasons` phase 3 (T5), correctly attributed elsewhere.
  - **Suite: no new failure nodes.** Measured in the main tree: **26 failed / 1409 passed / 0
    errors**, against the recorded baseline of 26 failed / 1398 passed / 0 errors. Same failure
    count; no failing node is in this plan's working set. Spot-checked
    `test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task` — it
    fails on a pre-existing `ix_roles_name` fixture-isolation collision, not on this change.
    (Method note for the next session: `-p no:logging` disables the `caplog` fixture and
    manufactures ~19 phantom *errors*. That is a measurement artefact — do not record it.)

  **Findings.**

  1. **BLOCKING — the delivery stops mid-Step-5; Steps 5–10 are not delivered.** Only commits
     1–4 of the planned 9 exist (`a747939`, `1204916`, `241eee5`, `444fffa`). Missing entirely:
     `count_reassigned_steps.py`, both routes on
     `routers/api_v1/task_step_acknowledgments.py`, and
     `tests/integration/services/queries/task_step_acknowledgments/` (the directory does not
     exist). `services/queries/task_step_acknowledgments/list_reassigned_steps.py` is written
     and correct but **untracked** — no commit 5.
     Unmet: acceptance criteria **4** (count endpoint), **5** (list/count agreement — there is
     no count to agree with), **5b** and `55_query_filters_local.md`'s completion gate boxes 3
     and 6 (`q` length validation and both keys in `query_params` are router-layer, and the
     router does not exist), **7** as far as roles are concerned, **8**'s route exposure, and
     **9** (no endpoint is reachable, so no conformance evidence is possible). The two
     invariants the plan is built around — Agreement and the `q`-absent count equality — are
     **untestable in the current tree**. Severity: blocking.
  2. **BLOCKING (scope) — Step 3 landed in the wrong file, and in one the parallel feature is
     actively editing.** `241eee5` put `serialize_task_step_acknowledgment` in
     `app/beyo_manager/domain/tasks/serializers.py:181-196`. The plan's Step 3 and its working
     set both name `app/beyo_manager/domain/task_steps/serializers.py` — which exists, holds
     `serialize_task_step_compact`, and was left untouched. `domain/tasks/serializers.py` is
     outside the declared working set, and `867b8fb` (`system_transition_reasons`) added
     `serialize_step_pause_reason` to that same file at the **immediately adjacent** line
     (`:198`). This is precisely the collision "Commit hygiene" exists to prevent. Behaviour is
     unaffected — the promoted body is identical to the former
     `_serialize_acknowledgment` apart from a dropped comment and two parameters gaining
     `= None` defaults — so this is a hygiene and merge-risk finding, not a correctness one.
     Fix by moving the function to `domain/task_steps/serializers.py` and updating the two
     importers (`list_pending_step_acknowledgments.py:3`, `list_reassigned_steps.py:4`).
  3. **MEDIUM (contract, proposal only — the handoff was not modified) — §5.1 documents two
     wrong `client_id` prefixes.** It states the step id prefix is `tstp_` and the task id
     prefix is `task_`. The models say `tsp` (`models/tables/tasks/task_step.py:43`) and `tsk`
     (`models/tables/tasks/task.py:35`). The wrong values also appear in the §3.6 example
     payload (`"client_id": "tstp_9f3a1c"`, `"step_id": "tstp_9f3a1c"`) and the §9 request
     snippets. `tsa_` (§5.2) and `wsec_` (§5.9) are correct. §5.10 already tells the frontend
     never to prefix-match, so the blast radius is fixtures and mocks rather than logic — but
     the frontend is building against this document now. **Operator decision:** the handoff
     gets corrected first, then anything else. No liveness row was flipped and no byte of the
     handoff was changed by this review.
  4. **LOW (process) — the handoff is untracked.** The plan states it "already exists and is
     committed"; `git log` on
     `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`
     returns nothing — it is a `??` file. Nothing in git protects the contract the plan says is
     authoritative. Commit it before Step 9's conformance pass.
  5. **LOW (forward-looking, Step 7) — the planned router snippet has no lower bound on
     `limit`.** `limit: int = Query(50, le=200)` admits a negative value, which reaches
     `list_reassigned_steps.py:32` and becomes a negative SQL `LIMIT`. Add `ge=1`. Handoff §10
     lists `422` for `limit > 200` and `offset < 0` but is silent on `limit < 0`; `ge=1` makes
     the router match the documented spirit without a handoff edit.
  6. **LOW (pre-existing idiom, not introduced here) — the user batch-load is not
     workspace-scoped.** `list_reassigned_steps.py:81` selects users by `client_id.in_(…)`
     only. Not a leak: the ids come from acks already scoped to `ctx.workspace_id`. It mirrors
     `steps_list_payload.py:228` and `list_pending_step_acknowledgments.py:66`, so leave it
     alone in this plan — noted so a future reviewer does not read it as new.

  **Also:** the Review log above stops at "Step 1 complete … Stopped before Step 2", but Steps
  2, 3 and 4 have since been committed and were never recorded. Whoever resumes should log them
  rather than re-plan them.

  Verdict: **NEEDS_CHANGES.** Steps 1–4 are sound and should not be redone — resume at Step 5
  (commit the existing `list_reassigned_steps.py`), then Steps 6–10, and fix finding 2 before
  the parallel feature touches `domain/tasks/serializers.py` again.

- `2026-07-31` `implementer (review-fix pass)`: **findings closed; stop for re-review.**

  1. Finding 1 is closed. The previously untracked list query is committed as `dccdb7a`; the
     shared count query as `082b226`; both routes as `b29bdbe`; and service-level integration
     coverage as `4ea8b26`, with count-query budget evidence added in `213cac7`. The focused
     reassigned-step suite passes: **15 passed**. It covers list/count agreement by paging the
     real list to exhaustion, stable ordering and no duplicate page ids, every terminal state,
     every required soft-delete/membership/worker/workspace exclusion, acknowledged-row and
     `unacknowledged_only` semantics, empty results, payload/section-map shape, `q` narrowing,
     and list/count statement budgets. The list remains constant in page size; the count executes
     exactly one statement.
  2. Finding 2 is closed by `1ad796c`: `serialize_task_step_acknowledgment` was relocated to
     `domain/task_steps/serializers.py`, both consumers import it there, and the parallel
     transition-reason serializer surface in `domain/tasks/serializers.py` was left clear of this
     feature.
  3. Finding 3 is acknowledged as **operator-resolved**. The handoff prefixes were corrected by
     the operator; this implementation did not edit the operator-owned handoff or its liveness
     table.

  **Step 9 evidence:** both reassigned-step paths are present in router OpenAPI, and an isolated
  request with a 201-character `q` returns `422` before service execution. The `55_query_filters`
  completion gate is clear: the list uses `apply_string_filter`; its module-level allowed columns
  are only item article number and SKU; the router enforces `max_length=200`; it passes both `q`
  and `string_filters` without inline parsing; there are no date parameters; and both required
  outer joins precede filtering. Integration assertions establish handoff-compatible item parity
  (the working-section item key set plus `acknowledgment`), null upholstery-group fields,
  acknowledgment fields, and the page-scoped compact `working_sections` map. `ruff check` passes
  all feature-touched source and test files. No migration was added and the handoff remains
  unmodified.

  **Suite comparison:** the recorded valid baseline is **26 failed / 1398 passed / 0 errors**.
  The current default-plugin run from `backend/app` is **372 failed / 1042 passed / 38 errors**;
  it is therefore an invalid node-set comparison, not evidence of a feature regression. Failures
  span unrelated Connecteam, Shopify, worker-stats, auth, router, and analytics suites, while the
  reassigned-step directory passes in isolation immediately afterwards (**15 passed**). No claim
  of a clean full-suite comparison is made; this requires environment/parallel-work resolution in
  the independent re-review.

- `2026-07-31` `operator session`: **The deferred suite comparison is resolved — the feature is
  clean.** The implementer's 372/1042/38 carries the documented broken-environment signature (the
  identical **38-error** count as the rejected round-1 baseline; see the transition-reasons master
  plan's "Validation baseline"), so it was re-measured in the main tree at `f512eb1`, from
  `backend/app`, default plugins:

  - Run 1: **26 failed / 1424 passed / 0 errors** — the +26 passed vs the 26/1398 baseline is the
    feature's new tests.
  - Run 2: the identical 26-node failure set (compared as node sets, not counts).
  - **Zero acknowledgment- or reassigned-related nodes** among the 26; all are the pre-existing
    baseline set.

  The re-review can treat the full-suite criterion as met and should verify against these figures,
  not re-open the 372 number.

- `2026-07-31` `reviewer (adversarial pass, round 2 — full checklist re-run)`: **APPROVED.** Round-1
  findings 1 and 2 are closed, and every checklist item was re-verified from the repo rather than
  from the round-1 log. All probes were run in the main tree at `28711b7` against `app/.venv`; every
  temporary file was deleted and `git status` on `app/` is clean.

  **Round-1 closure.**

  - **Finding 1 (blocking) — closed.** `dccdb7a` (list query), `082b226` (count query), `b29bdbe`
    (both routes), `4ea8b26` (integration tests), `213cac7` (count statement budget). Steps 5–9 are
    delivered; the whole feature suite passes: `tests/integration/services/queries/
    task_step_acknowledgments/` **15 passed**, characterization module **2 passed**.
  - **Finding 2 (blocking, scope) — closed.** `1ad796c` moved
    `serialize_task_step_acknowledgment` to `domain/task_steps/serializers.py:26-43` and repointed
    `list_pending_step_acknowledgments.py:3`; `list_reassigned_steps.py:4` already imported it there.
    `git diff a747939^ HEAD -- app/beyo_manager/domain/tasks/serializers.py` is **empty** — the
    241eee5 excursion is fully reverted, so the parallel feature's `serialize_step_pause_reason`
    surface is untouched. `domain/users/serializers.py` never appears in the range.
  - **Finding 5 — applied.** `limit: int = Query(50, ge=1, le=200)`
    (`routers/api_v1/task_step_acknowledgments.py:38`).
  - **Finding 6** — unchanged by design (pre-existing idiom, `list_reassigned_steps.py:81`).

  **Extraction (highest risk) — re-verified independently, not taken on trust.**

  - `diff <(git show 1204916^:…/list_working_section_steps.py | sed -n '304,592p')
    <(sed -n '54,342p' steps_list_payload.py)` → **empty; 289 lines byte-identical.** The commit's
    entire added-line set in the caller is **11 lines**: the pruned `sqlalchemy` import line, the
    two-line `build_steps_list_payload` import, and the six-line call — no edited logic anywhere.
    All five listed hazards are inside that identical block (`steps_list_payload.py:122-123`,
    `:207-213`, `:301-303`, `:279-282`, `:320-341`). Early-empty envelope stays in the caller
    (`list_working_section_steps.py:275-282`), the builder's bare `[]` is not returned.
  - **Response parity probed, not inferred.** Loaded `1204916^`'s file as a second module and ran
    both implementations against the same fixture in one session, both parametrizations:
    `json.dumps(before) == json.dumps(after)` and identical key *order* — 2 passed.
  - **Characterization test byte-identical to its pre-Step-2 state:** `git log` on it returns the
    single commit `a747939`; `1204916` has a two-file stat that excludes it.
  - **It discriminates:** deleting `group_image_by_step_id=` from the call site fails
    `…key_sets_are_stable[True]`; restored, tree clean.
  - `ruff check` clean on all touched source and test files.

  **Visibility, scoping, invariants — probed.** A throwaway module (5 cases, all passing, deleted)
  plus the committed suite establish: membership re-checked at read time (`removed_at` set after the
  ack → invisible); each of the four terminal states excluded individually; `ENDED_SHIFT` visible
  with all four `upholstery_group_*` null; another worker's and another workspace's acks invisible;
  an **admin**-role caller sees only their own obligations on **both** endpoints. All four joins in
  `_reassigned_steps_filters.py:31-67` carry `workspace_id`, each table using its own soft-delete
  idiom (`is_deleted` on step/task/section, `removed_at` on membership, `is_deleted` on the ack).
  Both `uix_working_section_memberships_active` and `uix_task_step_ack_step_worker` are partial/full
  unique indexes, so neither join can fan out.

  - **Agreement discriminates.** Temporarily inlining
    `.where(TaskStepAcknowledgment.acknowledged_at.is_(None))` into the list only made
    `…list_and_count_agree_and_include_acknowledged_rows` and
    `…enforces_workspace_and_unacknowledged_filter` fail (2 failed / 13 passed). The test is a real
    paging loop to exhaustion, not a hardcoded number. Restored.
  - **Pagination is stable.** Three acks seeded with an identical `created_at`, paged at `limit=1`:
    no id repeated, none skipped, and the emitted order equals `sorted(ids, reverse=True)` — the
    `TaskStep.client_id DESC` tiebreak (`list_reassigned_steps.py:62-65`) is what makes it total.

  **`q` — contract 55 completion gate, all seven boxes clear.** `apply_string_filter` used
  (`list_reassigned_steps.py:61`), no inline `.ilike`; allowed columns are `Item.article_number` /
  `Item.sku` only; router `max_length=200`; `string_filters` passed through unparsed; no date params;
  both `q` and `string_filters` present in `query_params`; both joins precede the call and are
  **unconditional** with `isouter=True` (`:39-58`). Probed: a task with no primary item is returned
  with no `q` and dropped by any non-empty `q`; an upholstery `name`/`code` seeded on the primary
  item does **not** match while its SKU does — upholstery search stays out of scope; `q` never
  widens (a terminal-state step and a step in a section the caller has no membership for both stay
  invisible under a matching `q`). `uix_task_items_primary_active`
  (`models/tables/tasks/task_item.py:53`) still exists, so the absence of `DISTINCT` remains sound.
  `list_working_section_steps` was **not** converted — its inline `.ilike` calls survive at
  `:219-220` and `:235-236` (D6). The count endpoint has **zero** OpenAPI parameters and no search
  joins (D7).

  **Contract conformance — mechanically compared, handoff treated as authoritative.** Parsed the
  handoff §5.1 table and the characterization test's `_STEP_KEYS`: **39 vs 38 + `acknowledgment`,
  symmetric difference empty in both directions.** `working_sections` is an object keyed by
  `client_id` covering exactly the page's sections; an empty page returns `working_sections: {}`
  with the full envelope. `is_reassigned` is `true` on every item (`reassigned_step_ids=set(page_ids)`).
  Count returns both keys as `0`, never `null`, from **one** statement selecting only
  `func.count()` / `func.count().filter(...)` — no ORM entities. Router validation exercised through
  a `TestClient` with auth and DB overridden: `limit=201` → **422**, `offset=-1` → **422**,
  `q` at 201 chars → **422**, `q` at exactly 200 chars and `limit=50` → pass validation and reach the
  service. Neither service contains a `raise`, so no `404` is reachable on either path. **The handoff
  is unmodified** (single commit `9ce1105`, no working-tree diff) and no liveness row was flipped.

  **Performance.** SQLAlchemy `before_cursor_execute` listener, main tree: **13 statements for a
  1-item page and 13 for a 50-item page** — constant, verified at the checklist's stated page size,
  not extrapolated from 10. The per-step `load_step_with_latest_record` / `build_step_record_payload`
  loop was **not** copied, and `list_pending_step_acknowledgments.py:71-81` is intact — its only
  change across the whole range is the serializer import.

  **Scope and commit hygiene.** Twelve commits belong to this feature: the planned nine, plus the two
  round-1 remediation commits (`1ad796c`, `213cac7`) and one extra docs entry. Per-commit
  `--name-only` shows each touches only its own declared paths; commits 1 and 2 have disjoint file
  sets and are separably revertible. **No migration:** no feature commit touches
  `app/migrations/`; `97b60e06d42a_…` belongs to `2f96915` (`system_transition_reasons`) and
  `env.py` to `3698a70`. No `transition_reason` string appears anywhere in this feature's source, and
  no `docs/domains/` file was edited.

  **Suite.** Taken from the operator entry above per the round-2 instruction, not re-measured:
  **26 failed / 1424 passed / 0 errors** at `f512eb1`, identical 26-node failure set across two runs,
  zero acknowledgment- or reassigned-related nodes among them, against the valid 26/1398/0 baseline.

  **Findings (both non-blocking).**

  1. **LOW (contract documentation, proposal only — the handoff was not modified) — round-1 finding
     3 is only half-closed.** `HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md:371` still
     reads ``| `task_id` | string | no | prefix `task_` |``. The model prefix is `tsk`
     (`models/tables/tasks/task.py:35`), and the handoff's own §3.6 example (`"task_id": "tsk_44b1de"`)
     and §5.4 already use `tsk_`. The step prefix was corrected (`tstp_` → `tsp_` everywhere);
     this one row was missed. The round-2 implementer entry records finding 3 as "operator-resolved",
     which is accurate for the step prefix but not for the task prefix. Blast radius is frontend
     fixtures and mocks, not logic. **Proposal for the operator; this review changed no byte of the
     handoff.**
  2. **LOW (process) — Step 10 is outstanding.**
     `docs/architecture/implemented_summaries/SUMMARY_reassigned_steps_endpoints_20260731.md` does
     not exist, and it is named in both the plan's working set and planned commit 9. This is the
     lifecycle-transition deliverable and reasonably follows approval rather than preceding it —
     recorded so the transition owner does not lose it.

  **Also noted, no action:** `Query(50, ge=1, le=200)` makes `limit=0` a `422`, a case handoff §10's
  table does not list (it names `limit > 200`, `offset < 0`, non-integer). It narrows rather than
  widens what the endpoint accepts and matches §10's spirit, so it needs no handoff edit — but if
  the operator wants §10 exhaustive, that row is the one to add.

  Verdict: **APPROVED.** Acceptance criteria 1–9 and 5b are met and independently verified. Neither
  finding blocks the transition; finding 1 is an operator decision on an operator-owned file.

## Lifecycle transition

- Current state: `archived`
- Next state: — (terminal)
- Transition owner: `operator (David)`
- Outcome: round 2 **APPROVED** 2026-08-01. Summary:
  `backend/docs/architecture/implemented_summaries/SUMMARY_reassigned_steps_endpoints_20260731.md`
