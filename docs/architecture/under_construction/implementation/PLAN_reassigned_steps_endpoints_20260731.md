# PLAN_reassigned_steps_endpoints_20260731

## Metadata

- Plan ID: `PLAN_reassigned_steps_endpoints_20260731`
- Status: `under_construction`
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
   non-terminal steps, filtered by the caller's *current* working-section membership.
2. New query service `count_reassigned_steps` — counts only, over the same filter set.
3. Extraction of the batch step-card payload builder currently inlined in
   `list_working_section_steps`, so both endpoints emit byte-identical step objects.
4. Two new routes on the existing `task_step_acknowledgments` router.
5. Integration tests for both new services, plus a characterization test that pins the
   existing `list_working_section_steps` payload before the extraction.
6. Frontend handoff document.

### Out of scope

- Filtering/searching (`q`, `task_types`, `item_major_category`, upholstery grouping…).
  The reassigned page is an inbox, not a browse surface. The query params exist on
  `list_working_section_steps` because that list can hold thousands of rows; a worker's
  pending reassignments are bounded by how many reassignments a manager made.
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
   exhaustion, for the same caller and workspace.
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
- `55_query_filters_local.md`: no `q` / date / ilike filtering in scope (see Out of scope).
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

1. Read `limit` (clamped to `_MAX_LIMIT`), `offset`, and `unacknowledged_only` from
   `ctx.query_params`, mirroring how `list_working_section_steps` coerces its params.
2. Select the page of ids and their ack rows in one statement:
   `select(TaskStepAcknowledgment.step_id, TaskStepAcknowledgment.client_id)` — or select
   the `TaskStepAcknowledgment` entity, which is simpler and the row count is bounded by
   `limit`. Apply Step 4's joins and clauses, order by D1, `.offset(offset).limit(limit + 1)`.
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

Take no `limit` / `offset`. A count endpoint that paginates is a bug waiting to happen.

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
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "unacknowledged_only": str(unacknowledged_only).lower(),
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

`test_count_reassigned_steps_integration.py`:

| Case | Expectation |
|---|---|
| Mixed set: 2 unacknowledged + 1 acknowledged, all visible | `{"total": 3, "unacknowledged": 2}` |
| Every exclusion case from the list table | not counted |
| Agreement | `count.total` equals the item count from paging the list to exhaustion with `limit=1` (acceptance criterion #5) |
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
| `pytest app/tests/ -q` | no new failures vs. the pre-change baseline; capture that baseline before starting, since the parallel work may already have failures unrelated to this plan |
| App boots and OpenAPI lists both routes under the `task-step-acknowledgments` tag | `/api/v1/task-step-acknowledgments/reassigned-steps` and `.../reassigned-steps/count` present |
| Manual: `GET .../reassigned-steps` as a worker with a seeded reassignment | 200; `steps_pagination.items[0].acknowledgment` populated; `working_sections` has the step's section |
| Manual: `GET .../reassigned-steps/count` for the same worker | `total` equals the item count from the list call |
| Manual: `GET /api/v1/working-sections/{id}/steps` before and after the change | responses byte-identical for the same fixture |
| Echo SQL (or `EXPLAIN` via query logging) on a 50-item page | statement count is constant, not ~50 × N |
| Handoff conformance: diff each documented field in the handoff §3.5/§4/§5/§6/§10 against a real response | every key, nullability, and enum value matches; evidence recorded in the Review log |
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

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `implementing_session_claude`
