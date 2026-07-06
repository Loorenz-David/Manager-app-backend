# PLAN_coordination_threads_q_search_20260706

## Metadata

- Plan ID: `PLAN_coordination_threads_q_search_20260706`
- Status: `archived`
- Owner agent: `claude-opus-4-8`
- Created at (UTC): `2026-07-06T00:00:00Z`
- Last updated at (UTC): `2026-07-06T10:37:27Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/email_implementation.txt` (INTENTION block, lines 25-50)

## Goal and intent

- Goal: Add a free-text `q` query param to `route_list_task_coordination_threads` /
  `list_task_coordination_threads` that mirrors the `q` search strategy already used by
  `list_tasks`, and additionally searches email subject and email content on the linked
  threads/messages.
- Business/user intent: Let the frontend filter the customer-coordination thread inbox by
  a single search box — matching on task/item/upholstery attributes **and** on email
  subject/body — the same way the task list already works.
- Non-goals:
  - **No schema change, no new model, no Alembic migration.** The GOAL text in the
    intention file ("run the migration for creating the email template model") is
    leftover copy from the prior email-templates plan; the email template model already
    exists (`HANDOFF_TO_FRONTEND_email_templates_20260704.md`). This search change reads
    only existing columns. Confirmed dropped with the requester.
  - No cursor pagination change (app is offset-based, unchanged here).
  - No `string_filters` column-scoping param in this iteration — a single `q` searches the
    full allowed column set (mirrors `list_tasks`, which also has no `string_filters`).

## Scope

- In scope:
  - Extract the `list_tasks` `q` subquery (Task/Item/ItemUpholstery `ILIKE` fan-out) into a
    shared, reusable helper so both services search identical task columns and cannot drift.
  - Refactor `list_tasks` to consume the shared helper (behavior-preserving).
  - Add `q` handling to `list_task_coordination_threads` that combines the shared task
    subquery with a new email subquery (thread subject/topic + message subject/body/sender).
  - Add the `q` router param (`max_length=200`) to `route_list_task_coordination_threads`
    and thread it through `query_params`.
  - Write a frontend handoff doc.
- Out of scope: any change to the response shape of `list_task_coordination_threads`
  (only the row set narrows when `q` is present), sockets, events, indexes.
- Assumptions:
  - `q` matches a thread if **either** its linked task matches the task/item/upholstery
    columns **or** its thread/messages match the email columns (logical OR).
  - Searching `EmailMessage.text_body_clean` (cleaned plaintext) is the intended "email
    content" target; `subject_normalized`/`topic` + `EmailMessage.subject` are the
    "email subject" targets. Sender (`from_address`, `from_name`) included as useful.

## Clarifications required

- [x] Search implementation strategy — resolved: **mirror `list_tasks` + shared helper**,
      and also search email subject + email content.
- [x] Migration for "email template model" — resolved: **drop it**, no migration.
- [ ] Confirm the exact email column set to search (proposed: `EmailThread.subject_normalized`,
      `EmailThread.topic`, `EmailMessage.subject`, `EmailMessage.text_body_clean`,
      `EmailMessage.body_preview`, `EmailMessage.from_address`, `EmailMessage.from_name`).
      Non-blocking — implement the proposed set unless told otherwise.

## Acceptance criteria

1. `GET /tasks/customer-coordination/threads?q=<term>` returns only coordination threads
   whose linked task matches the task/item/upholstery columns **or** whose thread/messages
   match the email columns; `q` absent/empty returns the current unfiltered result.
2. `q` matching on task/item/upholstery columns is byte-for-byte identical to `list_tasks`
   (both call the same shared helper).
3. `q` is validated with `max_length=200` at the router and passed through `query_params`.
4. Response shape (`coordination_threads`, `coordination_threads_pagination`) is unchanged;
   `has_more` still derives from `limit + 1`.
5. `list_tasks` output is unchanged after the refactor (existing behavior preserved).
6. A frontend handoff doc exists at the required path describing the new param. ✅

## Contracts and skills

### Read order (baseline → local delta)

- `../../../architecture/07_queries.md` (baseline) → `../../../architecture/07_queries_local.md`
  (offset pagination — already how both services work)
- `../../../architecture/06_commands.md` → `06_commands_local.md` (n/a — this is a query, not a command; loaded only to confirm no write path is touched)
- `../../../architecture/09_routers.md` (router handler wiring for the new `q` param)
- `../../../architecture/46_serialization.md` → `46_serialization_local.md` (confirm no serializer change)
- `../../../architecture/55_query_filters_local.md` (local-only search contract)

Applied precedence: local extension overrides baseline for this app only.

### Contracts loaded

- `55_query_filters_local.md`: defines the app's `q` search convention and the
  `apply_string_filter` utility.
- `07_queries_local.md`: offset pagination + list-query completion gate (both services
  already comply; must stay compliant).
- `09_routers.md`: router param + `ServiceContext` wiring pattern.

### Contract deviation (recorded, deliberate)

Contract `55_query_filters_local.md` prescribes `apply_string_filter` applied to a **live**
`select()` and explicitly forbids applying it to a subquery. That utility cannot express the
**distinct-`task_id` fan-out across Task→TaskItem→Item→ItemUpholstery** that `list_tasks`
requires (joining those tables into the main statement would multiply thread rows and break
pagination). The requester explicitly chose to **mirror `list_tasks`'s subquery strategy**.
Therefore this plan uses the same `select(distinct(Task.client_id))...where(or_(...ilike...))`
subquery pattern as `list_tasks`, extracted into a shared helper, instead of
`apply_string_filter`. This is a conscious, documented deviation for the multi-table search
case; `55` remains authoritative for simple single-statement searches elsewhere.

### File read intent — pattern vs. relational (all reads already done are relational)

- `services/queries/tasks/tasks.py` — read to reuse the **existing** `q` subquery shape (what exists). ✔ legitimate
- `services/queries/tasks/list_task_coordination_threads.py` — read to see current statement/return shape. ✔ legitimate
- `models/tables/emails/email_thread.py`, `email_message.py` — read for exact searchable field names. ✔ legitimate
- `routers/api_v1/tasks.py` — read current handler wiring for both routes. ✔ legitimate

### Skill selection

- Primary skill: none required (single-file query refactor + router param + doc).
- Router trigger terms: `q param, search, string filter, ilike, partial match` → contract `55`.
- Excluded alternatives: migrations/model skills — excluded (no schema change).

## Implementation plan

1. **Create shared task-search helper** —
   `app/beyo_manager/services/queries/utils/task_search.py`:
   - Move the exact column list and subquery construction currently inlined in
     `list_tasks` (tasks.py:203-255) into a function, e.g.:
     ```python
     def build_task_q_subquery(workspace_id: str, q: str):
         q_like = f"%{q}%"
         return (
             select(distinct(Task.client_id))
             .select_from(Task)
             .join(TaskItem, and_(TaskItem.task_id == Task.client_id,
                                  TaskItem.workspace_id == workspace_id,
                                  TaskItem.removed_at.is_(None)), isouter=True)
             .join(Item, and_(Item.client_id == TaskItem.item_id,
                              Item.workspace_id == workspace_id,
                              Item.is_deleted.is_(False)), isouter=True)
             .join(ItemUpholstery, and_(ItemUpholstery.item_id == Item.client_id,
                                        ItemUpholstery.workspace_id == workspace_id,
                                        ItemUpholstery.is_deleted.is_(False)), isouter=True)
             .where(Task.workspace_id == workspace_id, or_(<the same 14 ilike columns>))
         )
     ```
   - Keep the OR column list identical to the current `list_tasks` list (title,
     additional_details cast, phone/email x2, article_number, sku, designer,
     item_position, item_category_snapshot, item_major_category_snapshot, upholstery
     name, upholstery code).

2. **Refactor `list_tasks`** (tasks.py) to call `build_task_q_subquery(ctx.workspace_id, q)`
   in place of the inlined block. No behavior change — the produced SQL must be equivalent.

3. **Add email-search subquery in `list_task_coordination_threads`** — build a subquery that
   returns matching `EmailThread.client_id`:
   ```python
   email_q_subq = (
       select(distinct(EmailThread.client_id))
       .join(EmailMessage, EmailMessage.thread_id == EmailThread.client_id, isouter=True)
       .where(
           EmailThread.workspace_id == ctx.workspace_id,
           or_(
               EmailThread.subject_normalized.ilike(q_like),
               EmailThread.topic.ilike(q_like),
               EmailMessage.subject.ilike(q_like),
               EmailMessage.text_body_clean.ilike(q_like),
               EmailMessage.body_preview.ilike(q_like),
               EmailMessage.from_address.ilike(q_like),
               EmailMessage.from_name.ilike(q_like),
           ),
       )
   )
   ```

4. **Combine both in the main statement** of `list_task_coordination_threads`, after the
   existing state/type filters and before `order_by`:
   ```python
   q = ctx.query_params.get("q")
   if q:
       q_like = f"%{q}%"
       task_q_subq = build_task_q_subquery(ctx.workspace_id, q)
       stmt = stmt.where(
           or_(
               Task.client_id.in_(task_q_subq),
               EmailThread.client_id.in_(email_q_subq),
           )
       )
   ```
   (`Task` and `EmailThread` are already in the base `select`/joins, so the OR is safe and
   does not fan out the main row set — filtering is via `IN (subquery)`.)

5. **Router** (`routers/api_v1/tasks.py`, `route_list_task_coordination_threads`,
   lines 461-485): add `q: str | None = Query(None, max_length=200)` and add
   `"q": q` to the `query_params` dict.

6. **No `__init__.py` export changes** unless the helper module needs one — add `task_search`
   import path only where consumed (both query modules import the function directly).

7. **Frontend handoff doc** — create
   `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_coordination_threads_q_search_20260706.md`
   from `TEMPLATE_HANDOFF_TO_FRONTEND.md`, documenting:
   - Endpoint: `GET /tasks/customer-coordination/threads`
   - New optional param `q` (string, max 200), case-insensitive partial match.
   - What `q` searches: task fields (title, details, phone/email, item article/sku/designer/
     position/category, upholstery name/code) **and** email fields (thread subject/topic,
     message subject, cleaned body, preview, sender address/name).
   - Behavior: combined with existing filters (`coordination_states`, `task_states`,
     `task_types`) via AND; `q` absent → no filtering.
   - Response shape unchanged (`coordination_threads[]`, `coordination_threads_pagination`).
   - No frontend action required beyond wiring the search box to `?q=`.

## Risks and mitigations

- Risk: Refactor of `list_tasks` subtly changes its SQL/results.
  Mitigation: Extract verbatim (same columns, same joins, same `distinct`); diff the emitted
  SQL or run the existing task-list test/manual query before and after.
- Risk: `ILIKE` on `EmailMessage.text_body` variants is a sequential scan → slow on large
  mailboxes.
  Mitigation: Search `text_body_clean`/`body_preview` (bounded/clean) rather than raw
  `html_body`; note in handoff + contract `55` performance section that a `pg_trgm` GIN index
  can be added later if needed. No index added in this plan.
- Risk: OR of two `IN (subquery)` clauses over-broadens or mis-scopes results.
  Mitigation: Both subqueries are workspace-scoped; the main statement already constrains
  workspace/entity_type, so the OR only narrows within the already-scoped thread set.
- Risk: Email subquery joins deleted/irrelevant messages.
  Mitigation: EmailMessage has no soft-delete column in the searched set; thread scoping via
  `thread_id` + workspace is sufficient. Confirm during implementation.

## Validation plan

- `ruff`/import check on the new `utils/task_search.py` and both edited modules: no errors.
- Manual/HTTP check `GET /tasks?q=<known task title>`: result set identical to pre-refactor.
- Manual/HTTP check `GET /tasks/customer-coordination/threads?q=<known task title>`: returns
  the matching thread.
- Manual/HTTP check `GET /tasks/customer-coordination/threads?q=<word only in an email body/subject>`:
  returns the thread even when the task fields don't match.
- Check `q` absent → same output as today; `q` empty string → no filtering.
- Confirm `coordination_threads_pagination.has_more` still correct with `limit + 1`.

## Review log

- `2026-07-06` requester: chose "mirror list_tasks + shared helper" and confirmed `q` must
  also search email subject + email content; confirmed dropping the migration/email-template
  model step as leftover text.
- `2026-07-06` implementation: shared task `q` helper added, coordination-thread `q` search
  implemented, router updated, frontend handoff written, summary written, archive record
  written, plan archived.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
