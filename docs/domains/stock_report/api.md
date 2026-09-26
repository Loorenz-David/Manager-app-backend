# Stock Report — API

Living document for the `stock_report` domain (`architecture/23_documentation.md`).
It is written **from the shipped routers and serializers**, never from the intention's
examples (master plan §9 rule 15), and `app/tests/unit/docs/test_stock_report_docs.py`
fails when it drifts from them.

Semantics live in `docs/architecture/under_construction/implementation/stock_report/planning/intention.md`
and, for the snapshot layer added 2026-09-26, in the current frontend handoff.
The state machine and the cascade strategy live beside this file in `states.md`.

## 1. Routes

Nineteen routes in total, the three Scanner webhooks included. The `Roles` column is
the `require_roles([...])` list the router declares; `key` means the route is
authenticated by the `x-api-key` header instead (Scanner-facing, no JWT, no role).

| Method | Path | Roles | Service | Phase |
|---|---|---|---|---|
| `GET` | `/api/v1/stock-report/consistency` | `admin`, `manager` | `get_stock_report_consistency` | 3 |
| `POST` | `/api/v1/stock-report/repair` | `admin`, `manager` | `repair_stock_report` | 3 |
| `POST` | `/api/v1/stock-report/assignments` | `admin`, `manager`, `worker` | `create_stock_task_assignments` | 8 |
| `POST` | `/api/v1/stock-report/assignments/delete` | `admin`, `manager`, `worker` | `delete_stock_task_assignments` | 8 |
| `POST` | `/api/v1/stock-report/items/{client_id}/match-preview` | `admin`, `manager`, `worker` | `preview_stock_task_assignment_match` | 8A |
| `GET` | `/api/v1/stock-report/snapshots/versions` | `admin`, `manager`, `worker`, `seller` | `list_stock_report_snapshot_versions` | snapshots |
| `GET` | `/api/v1/stock-report/snapshots/versions/active` | `admin`, `manager`, `worker`, `seller` | `get_stock_report_active_snapshot_version` | snapshots (progress) |
| `POST` | `/api/v1/stock-report/snapshots/versions` | `admin`, `manager` | `create_stock_report_snapshot_version` | snapshots |
| `POST` | `/api/v1/stock-report/snapshots/versions/{client_id}/apply-priorities` | `admin`, `manager` | `apply_stock_report_snapshot_version_priorities` | snapshots |
| `GET` | `/api/v1/stock-report/snapshots/missing-summary` | `admin`, `manager`, `worker`, `seller` | `get_stock_report_missing_summary` | snapshots |
| `GET` | `/api/v1/stock-report/items` | `admin`, `manager`, `worker`, `seller` | `list_stock_report_items` | 12 |
| `PATCH` | `/api/v1/stock-report/items/{client_id}/missing-quantity` | `admin`, `manager`, `worker` | `set_stock_report_item_snapshot_missing_quantity` | snapshots |
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
| `GET …/snapshots/versions` | no body; `?limit=` (default **20** — owner ruling, the one departure from `07_queries_local`'s 50; max 200) and `?offset=` |
| `GET …/snapshots/versions/active` | none |
| `POST …/snapshots/versions` | **none** — every live row is snapshotted, there is nothing to choose |
| `POST …/snapshots/versions/{client_id}/apply-priorities` | **none**; the source version's id travels in the path |
| `GET …/snapshots/missing-summary` | none |
| `GET …/items` | no body; optional `?priority=high,medium,low`, `?include_zero_requested=true`, repeated `?item_major_categories=seat` / `?item_major_categories=wood`, repeated `?item_category_ids=<id>`, `?live_stock=true`, `?missing_only=true`. All supplied filters combine. By default the read is of the **active snapshots**: a row without one is absent, "zero requested" means `snapshot.quantity_requested − snapshot.quantity_missing <= 0`, and `priority` filters the snapshot's. `live_stock=true` reads every live row with its snapshot attached or `null`; `priority` and `missing_only` are refused on it |
| `PATCH …/missing-quantity` | `{"quantity_missing": <strict int>}` — the string `"2"` is refused, never coerced; an absolute value, not a delta |
| `PATCH …/priority` | `{"priority": "high"\|"medium"\|"low"\|null}` — the key is required and has no default |
| `PATCH …/priority-order` | `{"priority_order": <strict int>}` — the string `"2"` is refused, never coerced |
| `DELETE …/items/{client_id}` | **none**; `client_id` travels in the path |
| `GET …/items/{client_id}/assignments` | no body; optional `?include_resolved=true` query parameter. Exact `resolved` assignments are hidden by default |
| the three webhooks | raw bytes, read with `await request.body()`; the body is a JSON array and is parsed by the command, not by FastAPI |

The three item-scoped `PATCH` routes take the **row's** `client_id` in the path and act
on the row's **active snapshot** (2026-09-26).

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
| `GET …/snapshots/versions` | `{"stock_report_snapshot_versions": [<version + "progress">], "stock_report_snapshot_versions_pagination": {"has_more", "limit", "offset"}}` |
| `GET …/snapshots/versions/active` | `{"stock_report_snapshot_version": <version + "progress">}`, or `{"stock_report_snapshot_version": null}` (200) when no version has been created yet |
| `POST …/snapshots/versions` | `{"stock_report_snapshot_version": <version>}` |
| `POST …/snapshots/versions/{client_id}/apply-priorities` | `{"changed": <int>, "stock_report_items": [<row>]}` — the rows whose snapshot moved |
| `GET …/snapshots/missing-summary` | `{"quantity_missing_total": <int>, "items_with_missing": <int>}` over the active snapshots |

**The `progress` object** (2026-09-26 addendum; `services/queries/stock_report/_version_progress.py`,
shape from `domain/stock_report/snapshot_rules.py::fold_version_progress`). Attached to a
version by the two version reads, never by the serializer. Computed over the version's
snapshots **whose `priority` is set** and whose row is not deleted, in one aggregate
statement for a whole page:

```jsonc
{
  "items_total": 3, "items_completed": 1,
  "quantity_requested": 21, "quantity_missing": 2, "quantity_target": 19,
  "quantity_in_queue": 3, "quantity_in_progress": 1, "quantity_awaiting": 9,
  "quantity_resolved": 4, "quantity_completed": 9,
  "by_priority": { "high": { /* the same ten keys */ }, "medium": { /* … */ }, "low": { /* … */ } }
}
```

- `quantity_target = Σ max(0, quantity_requested − quantity_missing)` — what the version
  set out to do.
- `quantity_awaiting` is the **wire** awaiting: the live (or frozen) awaiting **plus
  `quantity_resolved`**, so it never drops because Scanner processed a shelf.
- `quantity_completed = Σ min(target_i, awaiting_i)` per item (an over-assigned row cannot
  cover another's shortfall); `items_completed` counts items with `awaiting_i >= target_i`.
- The three `by_priority` keys are always present, zeros included; no ratio is sent —
  `quantity_completed / quantity_target` is the bar.
| `GET …/items` | `{"stock_report_items": [<row>]}` — unpaginated by ratified decision |
| the three item `PATCH` routes | `{"stock_report_item": <row>}` |
| `DELETE …/items/{client_id}` | `{"client_id": ...}` |
| `GET …/items/{client_id}/assignments` | `{"stock_task_assignments": [<assignment>]}` |
| `…/webhooks/stock-demand` | `{"results": [{"itemCategory", "properties", "outcome"}]}`, `outcome` ∈ `applied`, `category_not_found` |
| `…/webhooks/items-processed` | `{"results": [{"article_number", "outcome", "reason"}]}`, `outcome` ∈ `resolved`, `ignored` |
| `…/webhooks/stock-demand-deleted` | `{"results": [{"itemCategory", "properties", "outcome"}]}`, `outcome` ∈ `deleted`, `not_found`, `category_not_found` |

`<row>` is `serialize_stock_report_item` and embeds `"snapshot": <snapshot> | null`
(`serialize_stock_report_item_snapshot`); `<version>` is
`serialize_stock_report_snapshot_version`; `<assignment>` is
`serialize_stock_task_assignment` (which embeds `serialize_item_compact` and
`serialize_task_compact`). The field-by-field shapes with nullability are in the
current frontend handoff, and the docs guard compares that table against the shipped
serializers.

Divergence `kind` is one of `counter_in_queue`, `counter_in_progress`,
`counter_awaiting`, `signature`, `order_density`, `missing_over_ceiling`,
`snapshot_version_closed_mismatch`, `goal_total`, `task_flag`. The ordering and
snapshot kinds name a **snapshot** id in `client_id`. (`priority_order_nullness` was
retired with the move: the snapshot table's pairing check makes a half-null position
unstorable.)

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
| `STOCK_REPORT_ROW_HAS_NO_PRIORITY` | 422 | the row's active snapshot has no priority, so it has no group to be ordered within |
| `STOCK_REPORT_TARGET_OUT_OF_RANGE` | 422 | the requested `priority_order` is outside `1..n` for that group |
| `STOCK_REPORT_NO_ACTIVE_SNAPSHOT` | 422 | the row exists but has no active snapshot (created since the last version), so it has no position and no missing quantity to set |
| `STOCK_REPORT_MISSING_EXCEEDS_CEILING` | 422 | `quantity_missing` is negative or above what the snapshot's frozen `quantity_requested` still leaves uncovered by the row's live counters |
| `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT` | 422 | `priority` or `missing_only` combined with `live_stock=true` |
| `STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE` | 422 | apply-priorities named the active version as its source |

A row absent, soft-deleted or in another workspace is one answer on every item-scoped
route: **404 `Stock report item not found.`** — never an empty list. An absent or
foreign version on apply-priorities is **404 `Stock report snapshot version not found.`**

The webhooks' malformed-body messages start `Malformed request: ` and name every
offending entry by its zero-based index; Scanner does not parse them.

## 5. Events

The nine event names and their payloads are in `states.md` §4 and in the frontend
handoff; the guard asserts both directions against every `event_name=` site under
`bm/services/commands/stock_report/` plus master plan §6.7 and the snapshot layer's
three names.
