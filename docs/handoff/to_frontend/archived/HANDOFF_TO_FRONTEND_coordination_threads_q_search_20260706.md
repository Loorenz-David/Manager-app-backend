# HANDOFF_TO_FRONTEND_coordination_threads_q_search_20260706

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_coordination_threads_q_search_20260706`
- Created at (UTC): `2026-07-06T10:37:27Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_coordination_threads_q_search_20260706.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_coordination_threads_q_search_20260706.md`

## Backend delivery context

- What backend implemented:
  - Added optional free-text `q` filtering to `GET /api/v1/tasks/customer-coordination/threads`.
  - The new search matches against the same task/item/upholstery fields already used by `GET /api/v1/tasks`.
  - The same `q` also matches coordination-thread email data: thread subject/topic plus message subject, cleaned body, preview, sender address, and sender name.
- API or contract changes:
  - `GET /api/v1/tasks/customer-coordination/threads` now accepts `q`.
- Feature flags/toggles: none.

## Frontend action required

1. Wire the customer-coordination inbox search box to the `q` query param on `GET /api/v1/tasks/customer-coordination/threads`.
2. Keep existing filters (`coordination_states`, `task_states`, `task_types`, `limit`, `offset`) unchanged; `q` composes with them via AND.
3. Treat empty or omitted `q` as no search filter.

## Interface details

- Endpoint: `GET /api/v1/tasks/customer-coordination/threads`
- New query param:

| Param | Type | Required | Notes |
|---|---|---|---|
| `q` | `string \| null` | No | Case-insensitive partial match, validated with `max_length=200`. |

- Search coverage:
  - Task side: task title, additional details, primary/secondary phone, primary/secondary email, item article number, SKU, designer, item position, item category snapshots, upholstery name, upholstery code.
  - Email side: thread `subject_normalized`, thread `topic`, message `subject`, `text_body_clean`, `body_preview`, `from_address`, `from_name`.
- Matching behavior:
  - A thread is included when either its linked task matches the shared task search helper or its thread/messages match the email search fields.
  - Existing non-search filters still apply first.
- Response shape:
  - Unchanged. The endpoint still returns `coordination_threads` and `coordination_threads_pagination`.
- Error cases:
  - Standard FastAPI validation failure if `q` exceeds 200 characters.

## Validation notes

- Backend validation run:
  - `python3 -m compileall -q app/beyo_manager/services/queries/utils/task_search.py app/beyo_manager/services/queries/tasks/tasks.py app/beyo_manager/services/queries/tasks/list_task_coordination_threads.py app/beyo_manager/routers/api_v1/tasks.py`
- Suggested frontend validation:
  - Search by a known task title and confirm the same thread appears as before.
  - Search by a word only present in an email subject/body and confirm the thread is returned.
  - Clear the search box and confirm the unfiltered inbox behavior remains unchanged.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_coordination_threads_q_search_20260706.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_coordination_threads_q_search_20260706.md`
- Related debug plan (optional): `—`
