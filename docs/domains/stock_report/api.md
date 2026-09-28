# Stock Report — API

Living document for the `stock_report` domain (`architecture/23_documentation.md`).
It is written **from the shipped routers and serializers**, never from the intention's
examples (master plan §9 rule 15), and `app/tests/unit/docs/test_stock_report_docs.py`
fails when it drifts from them.

Semantics live in `docs/architecture/under_construction/implementation/stock_report/planning/intention.md`
and, for the snapshot layer added 2026-09-26, in the current frontend handoff.
The state machine and the cascade strategy live beside this file in `states.md`.

## 1. Routes

Twenty-eight routes in total, the three Scanner webhooks included (nineteen at the
snapshot layer; draft versions, 2026-09-28, added the four versioned row edits, the
single-version read, the draft count, the draft delete, activation and the refresh of
the active version — the PATCH-version route follows). The `Roles` column is
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
| `GET` | `/api/v1/stock-report/snapshots/versions/draft-count` | `admin`, `manager`, `worker`, `seller` | `count_stock_report_draft_versions` | drafts (G-3) |
| `GET` | `/api/v1/stock-report/snapshots/versions/{client_id}` | `admin`, `manager`, `worker`, `seller` | `get_stock_report_snapshot_version` | drafts |
| `POST` | `/api/v1/stock-report/snapshots/versions` | `admin`, `manager` | `create_stock_report_snapshot_version` | snapshots |
| `DELETE` | `/api/v1/stock-report/snapshots/versions/{client_id}` | `admin`, `manager` | `delete_stock_report_snapshot_version` | drafts |
| `POST` | `/api/v1/stock-report/snapshots/versions/{client_id}/apply-priorities` | `admin`, `manager` | `apply_stock_report_snapshot_version_priorities` | snapshots |
| `POST` | `/api/v1/stock-report/snapshots/versions/{client_id}/activate` | `admin`, `manager` | `activate_stock_report_snapshot_version` | drafts |
| `POST` | `/api/v1/stock-report/snapshots/versions/{client_id}/refresh-requested` | `admin`, `manager` | `refresh_stock_report_snapshot_version_requested` | drafts |
| `PATCH` | `/api/v1/stock-report/snapshots/versions/{version_id}/items/{client_id}/priority` | `admin`, `manager`, `seller` | `set_stock_report_item_priority` | drafts |
| `PATCH` | `/api/v1/stock-report/snapshots/versions/{version_id}/items/{client_id}/priority-order` | `admin`, `manager`, `seller` | `set_stock_report_item_priority_order` | drafts |
| `PATCH` | `/api/v1/stock-report/snapshots/versions/{version_id}/items/{client_id}/missing-quantity` | `admin`, `manager`, `worker` | `set_stock_report_item_snapshot_missing_quantity` | drafts |
| `PATCH` | `/api/v1/stock-report/snapshots/versions/{version_id}/items/{client_id}/requested-quantity` | `admin`, `manager`, `seller` | `set_stock_report_item_snapshot_requested_quantity` | drafts |
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
| `GET …/snapshots/versions` | no body; `?limit=` (default **20** — owner ruling, the one departure from `07_queries_local`'s 50; max 200), `?offset=`, `?priority=` (as on `GET /items`; selects what `progress` sums) and `?state=` — a comma list of `draft`, `active`, `closed` (tokens trimmed, empties ignored, repeats folded; omitted → every state; any other token, `all` included → 422 `STOCK_REPORT_UNKNOWN_VERSION_STATE`) |
| `GET …/snapshots/versions/active` | `?priority=` only, as on `GET /items` |
| `GET …/snapshots/versions/draft-count` | none |
| `GET …/snapshots/versions/{client_id}` | no body; `?priority=` as on the list |
| `POST …/snapshots/versions` | **optional**, `extra="forbid"`: `{"draft": false, "title": null, "scheduled_activation_at": null, "scheduled_activation_keeps_active_missing": false}`. No body → a new active version of every live row. `title` is trimmed then capped at 200 (longer → 422; blank → `null`). `draft: true` → a draft (live rows, nothing frozen). A schedule (a `scheduled_activation_at`, or the flag `true`) with `draft: false` → 422 `STOCK_REPORT_VERSION_NOT_DRAFT` (the documented default body is a plain active create); `scheduled_activation_at` must carry an offset (naive → 422) and lie after now (else 422 `STOCK_REPORT_SCHEDULE_IN_THE_PAST`); it is stored in UTC |
| `DELETE …/snapshots/versions/{client_id}` | **none**; drafts only (422 `STOCK_REPORT_VERSION_NOT_DRAFT` otherwise) |
| `POST …/snapshots/versions/{client_id}/apply-priorities` | **optional** `{"target_version_id": null}` — `null` or absent is the active version, a draft's id is that draft; the source version's id travels in the path |
| `POST …/snapshots/versions/{client_id}/activate` | **optional**, `extra="forbid"`: `{"keep_active_missing": false}` — drafts only (422 `STOCK_REPORT_VERSION_NOT_DRAFT` otherwise). Closes the active version, freezes each row's live `quantity_requested` into the draft's snapshots (manual overrides kept) and settles `quantity_missing`: a typed value stays, the rest carry the closing board's value (`true`) or start at 0 (`false`), then clamped to the live ceiling. No body and `{}` are both the default; an unknown key → 422 |
| `POST …/snapshots/versions/{client_id}/refresh-requested` | **optional**, `extra="forbid"`: `{"keep_manual_requested": true}` — the active version only (422 `STOCK_REPORT_VERSION_NOT_ACTIVE` for a draft or a closed version). Re-freezes the Scanner value from the live rows, adds rows created since, clamps missing; `false` clears the manual overrides with one `quantity_requested_override` record each |
| `PATCH …/snapshots/versions/{version_id}/items/{client_id}/priority` and `…/priority-order` | the board twins' bodies, against the row's snapshot **in that version** (draft or active; closed → 422 `STOCK_REPORT_VERSION_IS_CLOSED`; absent/foreign version → 404; a row without a snapshot there → 404) |
| `PATCH …/snapshots/versions/{version_id}/items/{client_id}/missing-quantity` | `{"quantity_missing": <strict int ≥ 0> \| null}` — a number types a draft's own value, `null` clears it so the row borrows the active version's again; `null` on the active version → 422 `STOCK_REPORT_VERSION_NOT_DRAFT` |
| `PATCH …/snapshots/versions/{version_id}/items/{client_id}/requested-quantity` | `{"quantity_requested": <strict int ≥ 0> \| null}`, required — a number sets the snapshot's manual value (typing the value Scanner shows **pins** it), `null` reverts to Scanner's; on the active version the change clamps the snapshot's missing and writes a `quantity_requested_override` history record |
| `GET …/snapshots/missing-summary` | none |
| `GET …/items` | no body; `?limit=` (default **20** by owner ruling, min 1, max 200) and `?offset=` (`07_queries_local`, paginated since 2026-09-26); optional `?priority=high,medium,low`, `?include_zero_requested=true`, repeated `?item_major_categories=seat` / `?item_major_categories=wood`, repeated `?item_category_ids=<id>`, `?live_stock=true`, `?missing_only=true`. All supplied filters combine. By default the read is of the **active snapshots**: a row without one is absent, "zero requested" means `snapshot.quantity_requested − snapshot.quantity_missing <= 0` (hidden unless `include_zero_requested=true`, and never applied under `missing_only=true`, which returns every snapshot with `quantity_missing > 0`, fully missing ones included), and `priority` filters the snapshot's: omitted means unprioritised snapshots only, a list means only those priorities, and `priority=all` (alone, never combined) means every active snapshot, prioritised first in board order then unprioritised by `created_at, client_id`. `live_stock=true` reads every live row with its snapshot attached or `null`; `priority` and `missing_only` are refused on it |
| `PATCH …/missing-quantity` | `{"quantity_missing": <strict int>}` — the string `"2"` is refused, never coerced; an absolute value, not a delta |
| `PATCH …/priority` | `{"priority": "high"\|"medium"\|"low"\|null}` — the key is required and has no default |
| `PATCH …/priority-order` | `{"priority_order": <strict int>}` — the string `"2"` is refused, never coerced |
| `DELETE …/items/{client_id}` | **none**; `client_id` travels in the path |
| `GET …/items/{client_id}/assignments` | no body; optional `?include_resolved=true` query parameter. Exact `resolved` assignments are hidden by default |
| the three webhooks | raw bytes, read with `await request.body()`; the body is a JSON array and is parsed by the command, not by FastAPI |

The three item-scoped `PATCH` routes take the **row's** `client_id` in the path and act
on the row's **active snapshot** (2026-09-26); since 2026-09-28 they are the shortcut
form of the versioned routes above — the same command, the active version resolved
under the command's first lock, "no active version" and "no snapshot in it" both
answered with 422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT`. `GET …/items` also takes
`?version_id=` (that version's rows in any state; absent/foreign → 404; with
`live_stock=true` → 422 `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT`).

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
| `GET …/snapshots/versions` | `{"stock_report_snapshot_versions": [<version + "filtered_snapshot_count" + "progress">], "stock_report_snapshot_versions_pagination": {"has_more", "limit", "offset"}}` |
| `GET …/snapshots/versions/active` | `{"stock_report_snapshot_version": <version + "filtered_snapshot_count" + "progress">}`, or `{"stock_report_snapshot_version": null}` (200) when no version has been created yet |
| `GET …/snapshots/versions/draft-count` | `{"draft_count": <int>}` |
| `GET …/snapshots/versions/{client_id}` | `{"stock_report_snapshot_version": <version + "filtered_snapshot_count" + "progress">}`, any state; 404 absent/foreign |
| `POST …/snapshots/versions` | `{"stock_report_snapshot_version": <version>}` |
| `DELETE …/snapshots/versions/{client_id}` | `{"client_id": ...}` |
| `POST …/snapshots/versions/{client_id}/apply-priorities` | `{"changed": <int>, "stock_report_items": [<row>]}` — the rows whose snapshot moved, each with the **target** version's snapshot |
| `POST …/snapshots/versions/{client_id}/activate` | `{"stock_report_snapshot_version": <version>}` — column-only, as create; `progress` stays on the reads |
| `POST …/snapshots/versions/{client_id}/refresh-requested` | `{"stock_report_snapshot_version": <version>, "changed": <int>, "added": <int>}` — `changed` counts snapshots whose **effective** requested changed, `added` the rows that joined |
| the four versioned item `PATCH` routes | `{"stock_report_item": <row>}`, the row's snapshot being **that version's** |
| `GET …/snapshots/missing-summary` | `{"quantity_missing_total": <int>, "items_with_missing": <int>}` over the active snapshots |

**The `progress` object** (2026-09-26 addendum; `services/queries/stock_report/_version_progress.py`,
shape from `domain/stock_report/snapshot_rules.py::fold_version_progress`). Attached to a
version by the two version reads, never by the serializer. Computed over the version's
snapshots **selected by the `priority` query parameter** — the same parser and meaning as
`GET /items` (`_priority_filter.py`): omitted → null priority, `all` → every snapshot,
a list → those groups — whose row is not deleted, in one aggregate statement for a whole
page:

```jsonc
{
  "items_total": 3, "items_completed": 1,
  "quantity_requested": 21, "quantity_missing": 2, "quantity_target": 19,
  "quantity_in_queue": 3, "quantity_in_progress": 1, "quantity_awaiting": 9,
  "quantity_resolved": 4, "quantity_completed": 9,
  "by_priority": { "high": { /* the same ten keys */ }, "medium": { /* … */ }, "low": { /* … */ }, "unset": { /* null priority */ } }
}
```

- `quantity_target = Σ max(0, quantity_requested − quantity_missing)` — what the version
  set out to do.
- `quantity_awaiting` is the **wire** awaiting: the live (or frozen) awaiting **plus
  `quantity_resolved`**, so it never drops because Scanner processed a shelf.
- `quantity_completed = Σ min(target_i, awaiting_i)` per item (an over-assigned row cannot
  cover another's shortfall); `items_completed` counts items with `awaiting_i >= target_i`.
- The four `by_priority` keys are always present, zeros included, and the totals are
  their sum; no ratio is sent — `quantity_completed / quantity_target` is the bar.
  `snapshot_count` on the version is its size at creation and ignores the filter;
  **`filtered_snapshot_count`** (beside it, computed by the same statement) is that count
  under the filter — deleted rows included, so it equals `snapshot_count` under
  `priority=all` and exceeds `progress.items_total` by the rows deleted mid-version.
| `GET …/items` | `{"stock_report_items": [<row>], "stock_report_items_pagination": {"has_more", "limit", "offset"}}` — filters narrow first, then the page is cut from the ordered set |
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
`snapshot_version_state_mismatch`, `draft_membership_mismatch`, `goal_total`,
`task_flag`. The ordering and snapshot kinds name a **snapshot** id in `client_id`;
`draft_membership_mismatch` names the **version** (a draft lacking a snapshot for a
live row, `stored: null` / `expected: <row id>`, or holding one for a deleted row,
`stored: <row id>` / `expected: null`, field `stock_report_item_id`).
(`priority_order_nullness` was retired with the move: the snapshot table's pairing
check makes a half-null position unstorable; `snapshot_version_closed_mismatch`
became the one-directional `snapshot_version_state_mismatch` with drafts.)

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
| `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER` | 422 | a `priority` query token that is not `high`, `medium`, `low` or `all`, or `all` combined with another token |
| `STOCK_REPORT_ROW_HAS_NO_PRIORITY` | 422 | the row's active snapshot has no priority, so it has no group to be ordered within |
| `STOCK_REPORT_TARGET_OUT_OF_RANGE` | 422 | the requested `priority_order` is outside `1..n` for that group |
| `STOCK_REPORT_NO_ACTIVE_SNAPSHOT` | 422 | the row exists but has no active snapshot (created since the last version), so it has no position and no missing quantity to set |
| `STOCK_REPORT_MISSING_EXCEEDS_CEILING` | 422 | `quantity_missing` is negative or above what the snapshot's frozen `quantity_requested` still leaves uncovered by the row's live counters |
| `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT` | 422 | `priority` or `missing_only` combined with `live_stock=true` |
| `STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE` | 422 | apply-priorities named the active version as its source with the target omitted (the v6 case) |
| `STOCK_REPORT_SOURCE_IS_TARGET` | 422 | apply-priorities named the same version as source and target (every other case) |
| `STOCK_REPORT_TARGET_VERSION_IS_CLOSED` | 422 | apply-priorities named a closed version as its target |
| `STOCK_REPORT_VERSION_IS_CLOSED` | 422 | a versioned row edit named a closed version |
| `STOCK_REPORT_VERSION_NOT_DRAFT` | 422 | a draft-only action on an activated version: activate, delete, a schedule key with `draft: false`, `null` missing on the active version |
| `STOCK_REPORT_VERSION_NOT_ACTIVE` | 422 | refresh-requested named a draft or a closed version; only the active version is refreshed |
| `STOCK_REPORT_SCHEDULE_IN_THE_PAST` | 422 | `scheduled_activation_at` at or before now |
| `STOCK_REPORT_UNKNOWN_VERSION_STATE` | 422 | a `state` query token that is not `draft`, `active` or `closed` |

A row absent, soft-deleted or in another workspace is one answer on every item-scoped
route: **404 `Stock report item not found.`** — never an empty list (on a versioned
route a live row with no snapshot in that version is the same 404). An absent or
foreign version on any route that names one is **404 `Stock report snapshot version
not found.`**

The webhooks' malformed-body messages start `Malformed request: ` and name every
offending entry by its zero-based index; Scanner does not parse them.

## 5. Events

The twelve event names (the ratified six, the snapshot layer's three, and the draft
versions' `stock_report_snapshot_version:deleted`, `:activated` and `:refreshed`) and
their payloads are in `states.md` §4 and in the frontend
handoff; the guard asserts both directions against every `event_name=` site under
`bm/services/commands/stock_report/` plus master plan §6.7 and the snapshot layer's
three names.
