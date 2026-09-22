# Stock Report — API

Living document for the `stock_report` domain (`architecture/23_documentation.md`).
It is written **from the shipped routers and serializers**, never from the intention's
examples (master plan §9 rule 15), and `app/tests/unit/docs/test_stock_report_docs.py`
fails when it drifts from them.

Semantics live in `docs/architecture/under_construction/implementation/stock_report/planning/intention.md`.
The state machine and the cascade strategy live beside this file in `states.md`.

## 1. Routes

Thirteen routes in total, the three Scanner webhooks included. The `Roles` column is
the `require_roles([...])` list the router declares; `key` means the route is
authenticated by the `x-api-key` header instead (Scanner-facing, no JWT, no role).

| Method | Path | Roles | Service | Phase |
|---|---|---|---|---|
| `GET` | `/api/v1/stock-report/consistency` | `admin`, `manager` | `get_stock_report_consistency` | 3 |
| `POST` | `/api/v1/stock-report/repair` | `admin`, `manager` | `repair_stock_report` | 3 |
| `POST` | `/api/v1/stock-report/assignments` | `admin`, `manager`, `worker` | `create_stock_task_assignments` | 8 |
| `POST` | `/api/v1/stock-report/assignments/delete` | `admin`, `manager`, `worker` | `delete_stock_task_assignments` | 8 |
| `POST` | `/api/v1/stock-report/items/{client_id}/match-preview` | `admin`, `manager`, `worker` | `preview_stock_task_assignment_match` | 8A |
| `GET` | `/api/v1/stock-report/items` | `admin`, `manager`, `worker`, `seller` | `list_stock_report_items` | 12 |
| `PATCH` | `/api/v1/stock-report/items/{client_id}/priority` | `admin`, `manager`, `seller` | `set_stock_report_item_priority` | 12 |
| `PATCH` | `/api/v1/stock-report/items/{client_id}/priority-order` | `admin`, `manager`, `seller` | `set_stock_report_item_priority_order` | 12 |
| `DELETE` | `/api/v1/stock-report/items/{client_id}` | `admin`, `manager` | `delete_stock_report_item` | 13 |
| `GET` | `/api/v1/stock-report/items/{client_id}/assignments` | `admin`, `manager`, `worker`, `seller` | `list_stock_task_assignments` | 13 |
| `POST` | `/api/v1/location-tracker/webhooks/stock-demand` | `key` | `receive_stock_demand_webhook` | 7 |
| `POST` | `/api/v1/location-tracker/webhooks/items-processed` | `key` | `process_items_processed` | 9 |
| `POST` | `/api/v1/location-tracker/webhooks/stock-demand-deleted` | `key` | `process_stock_demand_deleted` | 13A |

The wire contract Scanner builds against is
`docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v2_20260919.md` (read-only; §4A covers
the delete webhook). The contract the frontend builds against is the current file
under the project's `handoffs/to_frontend/`.

## 2. Request bodies

| Route | Body |
|---|---|
| `GET …/consistency`, `POST …/repair` | none |
| `POST …/assignments` | `{"entries": [{"stock_report_item_id", "task_id", "item_id", "override_property_mismatch"?}]}`, `extra="forbid"` |
| `POST …/assignments/delete` | `{"client_ids": [...]}`, `extra="forbid"` |
| `POST …/match-preview` | `{"task_id"?, "article_number"?, "sku"?, "item_category_id", "properties", "quantity"}` — `item_category_id` is **required** (owner ruling, round 3: an Item cannot validly exist without a category, so the preview is never more permissive than creation) |
| `GET …/items` | none; optional `?priority=high,medium,low` query parameter |
| `PATCH …/priority` | `{"priority": "high"\|"medium"\|"low"\|null}` — the key is required and has no default |
| `PATCH …/priority-order` | `{"priority_order": <strict int>}` — the string `"2"` is refused, never coerced |
| `DELETE …/items/{client_id}` | **none**; `client_id` travels in the path |
| `GET …/items/{client_id}/assignments` | none |
| the three webhooks | raw bytes, read with `await request.body()`; the body is a JSON array and is parsed by the command, not by FastAPI |

## 3. Response bodies

Success is always `{"data": <payload>, "ok": true, "warnings": []}`. Domain errors are
`{"error": <message>, "ok": false}` with the error's own HTTP status. The two
structured assignment errors add `code` and `details` and are rendered explicitly in
the router.

| Route | `data` |
|---|---|
| `GET …/consistency` | `{"workspace_id", "checked_at", "divergences": [{"kind", "client_id", "field", "stored", "expected"}]}` |
| `POST …/repair` | `{"repaired": [...], "not_repaired": [...]}` — the same five-key divergence shape |
| `POST …/assignments` | `{"stock_task_assignments": [<assignment>]}` |
| `POST …/assignments/delete` | `{"deleted_client_ids": [...]}` |
| `POST …/match-preview` | `{"can_proceed", "override_required", "refusal_reason", "property_failures", "matched_item_client_id", "values_source", "checks"}` |
| `GET …/items` | `{"stock_report_items": [<row>]}` — unpaginated by ratified decision |
| both `PATCH` routes | `{"stock_report_item": <row>}` |
| `DELETE …/items/{client_id}` | `{"client_id": ...}` |
| `GET …/items/{client_id}/assignments` | `{"stock_task_assignments": [<assignment>]}` |
| `…/webhooks/stock-demand` | `{"results": [{"itemCategory", "properties", "outcome"}]}`, `outcome` ∈ `applied`, `category_not_found` |
| `…/webhooks/items-processed` | `{"results": [{"article_number", "outcome", "reason"}]}`, `outcome` ∈ `resolved`, `ignored` |
| `…/webhooks/stock-demand-deleted` | `{"results": [{"itemCategory", "properties", "outcome"}]}`, `outcome` ∈ `deleted`, `not_found`, `category_not_found` |

`<row>` is `serialize_stock_report_item`, `<assignment>` is
`serialize_stock_task_assignment` (which embeds `serialize_item_compact` and
`serialize_task_compact`). The field-by-field shapes with nullability are in the
current frontend handoff, and the docs guard compares that table against the shipped
serializers.

## 4. Errors

| Class | HTTP | Raised by |
|---|---|---|
| `LocationTrackerWebhookAuthError` | 401 | all three webhooks — a missing or wrong `x-api-key`, an unset key or workspace setting, or a configured workspace that does not exist. The body is identical for every cause; the cause is logged, never returned |
| `StockDemandDeadlineExceeded` | 503 | the demand and the delete webhooks, when the MC-9 time budget is exhausted immediately before commit. Nothing is committed |
| `StockAssignmentRefused` | 422 | `POST …/assignments` — `code: "stock_assignment_refused"`, `details: [{"index", "reason"}]` over a closed eleven-value reason vocabulary. The whole batch is refused |
| `StockAssignmentPropertyMismatch` | 409 | `POST …/assignments` — `code: "stock_assignment_property_mismatch"`, `details` carrying the per-entry `failures`. Recoverable: resend with `override_property_mismatch: true` |

Registered message identities (leading-token form, `05_errors_local`):

| Identity | HTTP | Meaning |
|---|---|---|
| `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER` | 422 | a `priority` query token that is not `high`, `medium` or `low` |
| `STOCK_REPORT_ROW_HAS_NO_PRIORITY` | 422 | the row has no priority, so it has no group to be ordered within |
| `STOCK_REPORT_TARGET_OUT_OF_RANGE` | 422 | the requested `priority_order` is outside `1..n` for that group |

A row absent, soft-deleted or in another workspace is one answer on every item-scoped
route: **404 `Stock report item not found.`** — never an empty list.

The webhooks' malformed-body messages start `Malformed request: ` and name every
offending entry by its zero-based index; Scanner does not parse them.

## 5. Events

The six event names and their payloads are in `states.md` §4 and in the frontend
handoff; the guard asserts both directions against every `event_name=` site under
`bm/services/commands/stock_report/` plus master plan §6.7.
