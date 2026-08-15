# Item Economics API

Base path: `/api/v1/item-economics/`
Auth: all endpoints require `Authorization: Bearer <access_token>`.

Every response is wrapped: `{"data": {...}, "ok": true, "warnings": []}` on success,
`{"error": "...", "ok": false}` on failure. The shapes below are the contents of `data`.

**Role gates.** Every endpoint is ADMIN/MANAGER only, with exactly one exception:
`GET /tasks/{task_client_id}/budget-status`, which admits ADMIN, MANAGER, WORKER and
SELLER and serves two different payloads (see "The money audience").

**Error identities.** A domain error carries no `code` field. The identity is the leading
token of the message, in the shape `<IDENTITY>: <human sentence>`, and it travels in the
`error` key. Clients match on the leading token, never on the sentence.

| HTTP | Class | Meaning |
|---|---|---|
| 404 | `NotFound` | The named row does not exist in this workspace |
| 409 | `ConflictError` | A uniqueness or chain race lost at the database |
| 422 | `ValidationError` | Request or domain admission refused |

---

## The money audience

A payload may carry monetary fields **iff the requesting identity's role is ADMIN or
MANAGER**. WORKER *and* SELLER are both excluded.

The boundary is a declared field of the interface, failing closed:
`serialize_step(step, *, include_monetary: bool)` is keyword-only with **no default**, so
a new call site cannot inherit money by silence. `total_cost_minor` is **absent from the
dict** when the flag is false — absent, not `null`, because a null key still tells a
worker that a cost number exists.

Inside this domain the same discipline takes a stronger form: the worker-facing budget
status is a **separate query service whose serializer has no monetary keys at all**, not a
flag on the manager serializer.

### `total_cost_minor` exposure census — eight endpoints

`serialize_step` (`domain/tasks/serializers.py`) is reached from eight endpoints. This is
the complete list; the flag is derived from the request identity once inside each shared
payload builder, so every endpoint riding a builder inherits the redaction.

| # | Endpoint | Query service | Admitted roles | `total_cost_minor` |
|---|---|---|---|---|
| 1 | `GET /api/v1/tasks/{task_id}` | `queries/tasks/tasks.py` (`get_task`) | ADMIN, MANAGER, WORKER, SELLER | redacted for WORKER and SELLER |
| 2 | `GET /api/v1/tasks/{task_id}/steps` | `queries/tasks/list_task_steps.py` | ADMIN, MANAGER, WORKER, SELLER | redacted for WORKER and SELLER |
| 3 | `GET /api/v1/working-sections/{id}/steps` | `queries/working_sections/steps_list_payload.py` | ADMIN, MANAGER, WORKER | redacted for WORKER |
| 4 | `GET /api/v1/working-sections/steps/user-last-active` | `queries/working_sections/step_record_payload.py` | ADMIN, MANAGER, WORKER | redacted for WORKER |
| 5 | `GET /api/v1/worker-stats/{user_id}/daily-steps` | `queries/worker_stats/get_worker_daily_step_breakdown.py` | ADMIN, MANAGER | present |
| 6 | `GET /api/v1/task-step-acknowledgments/reassigned-steps` | `queries/task_step_acknowledgments/list_reassigned_steps.py` | ADMIN, MANAGER, WORKER | redacted for WORKER |
| 7 | `GET /api/v1/task-step-acknowledgments/pending` | `queries/task_step_acknowledgments/list_pending_step_acknowledgments.py` | ADMIN, MANAGER, WORKER | redacted for WORKER |
| 8 | `GET /api/v1/worker-stats/last-interacted-steps` | `queries/worker_stats/list_workers_last_interacted_step.py` | ADMIN, MANAGER | present |

Rows 5 and 8 keep money deliberately: their audience is already ADMIN/MANAGER, and they
are the rows that make a blanket redaction fail loudly instead of passing unnoticed.

---

## Item and task payloads carry no money

Items own no monetary columns. Nine read surfaces that used to emit
`item_value_minor` / `item_cost_minor` / `item_currency` no longer carry any of them:

| Serializer | Surfaces |
|---|---|
| `domain/items/serializers.py::_serialize_item_base` | items list, item detail, customer detail's `linked_items[]` |
| `domain/tasks/serializers.py::serialize_item` | tasks list, task detail, task coordination threads, upholstery order needs, pending seat tasks, upholstery orders |

The three keys are still **accepted** by the item and task creation/update request
bodies, and sending any of them with a non-null value is refused:

```json
{ "error": "ITEM_MONEY_MOVED: item money fields moved to the item-valuation endpoint", "ok": false }
```

→ `422`. Present-with-null and absent both pass and are ignored. The one surface that can
change an existing item's price is `PUT /api/v1/item-economics/items/{item_client_id}/valuation`.

Because those columns are gone from `items`, the general rule for a destructive schema
change applies to anything of this shape: **deploy the code first, change the schema
second**, so no process is ever serving a model that names a column the database no longer
has. The operational procedure lives in `docs/deploy/`.

---

## Configuration

### `GET /configuration-status`

Whether the workspace can evaluate anything yet, per major category. Drives onboarding.

**Auth:** `ADMIN`, `MANAGER`

**Response:**

```json
{
  "categories": {
    "wood": {
      "group_count": 1,
      "has_cost_group": true,
      "has_open_basis_version": true,
      "evaluable": true,
      "first_failure": null
    },
    "seat": {
      "group_count": 0,
      "has_cost_group": false,
      "has_open_basis_version": false,
      "evaluable": false,
      "first_failure": "not_configured_no_cost_group"
    }
  },
  "has_open_cost_model_version": true
}
```

`first_failure` is `null` when `evaluable` is true, and otherwise the first failing
status value from the ordered configuration precedence — see [states.md](states.md).

---

### `POST /cost-groups`

**Auth:** `ADMIN`, `MANAGER`

**Request:** `{ "name": "Wood workshop", "major_category": "wood" }`

**Response:** `{ "production_cost_group": { … } }`

Group fields: `client_id`, `workspace_id`, `name`, `major_category`, `created_at`,
`created_by_id`, `updated_at`, `updated_by_id`.

**Errors:** `ITEM_COST_GROUP_NAME_TAKEN` (422 on the pre-check, 409 on the database
conflict), `ITEM_COST_GROUP_CATEGORY_TAKEN` (same dual path — one active group per
category; the pre-check message names the category).

---

### `GET /cost-groups`

**Auth:** `ADMIN`, `MANAGER` · **Query:** `limit` (1–200, default 50), `offset` (≥ 0)

**Response:**

```json
{
  "production_cost_groups": [ { } ],
  "production_cost_groups_pagination": { "has_more": false, "limit": 50, "offset": 0 }
}
```

---

### `PATCH /cost-groups/{client_id}`

**Auth:** `ADMIN`, `MANAGER`

**Request:** `{ "name": "Wood workshop", "major_category": "wood" }` — `major_category`
is optional and may only repeat the current value once any basis version exists.

**Response:** `{ "production_cost_group": { … } }`

**Errors:** `ITEM_COST_GROUP_CATEGORY_IMMUTABLE` (422 — the message names the group and
its current category), `ITEM_COST_GROUP_NAME_TAKEN`, `ITEM_COST_GROUP_CATEGORY_TAKEN`.

---

### `DELETE /cost-groups/{client_id}`

**Auth:** `ADMIN`, `MANAGER` · **Response:** `{ "production_cost_group": { … } }`

**Errors:** `ITEM_COST_GROUP_IN_USE` (422) when a non-deleted basis version or an active
section membership exists.

---

### `POST /cost-groups/{client_id}/sections`

**Auth:** `ADMIN`, `MANAGER` · **Request:** `{ "working_section_id": "wsec_…" }`

**Response:** `{ "production_cost_group_section": { … } }` with `client_id`,
`workspace_id`, `production_cost_group_id`, `working_section_id`, `added_at`,
`added_by_id`, `removed_at`, `removed_by_id`.

**Errors:** `ITEM_COST_SECTION_ALREADY_GROUPED` (422 on the pre-check, 409 on the
database conflict) — a working section belongs to at most one active group.

---

### `DELETE /cost-groups/{client_id}/sections/{working_section_client_id}`

**Auth:** `ADMIN`, `MANAGER` · **Response:** `{ "production_cost_group_section": { … } }`
with `removed_at` / `removed_by_id` set. The row is never deleted.

---

### `POST /cost-groups/{client_id}/basis-versions`

**Auth:** `ADMIN`, `MANAGER`

**Request:**

```json
{
  "effective_from": "2026-08-15",
  "fixed_monthly_cost_minor": 200000,
  "currency": "swedish_krona",
  "monthly_paid_hours": "160.00",
  "planning_utilization_percent": "80.00"
}
```

`effective_from` is optional and may not be in the future. `cost_per_worker_minute_minor`
is **derived, never accepted**.

**Response:** `{ "production_cost_basis_version": { … } }` with `client_id`,
`workspace_id`, `production_cost_group_id`, `effective_from`, `effective_to`,
`fixed_monthly_cost_minor`, `currency`, `monthly_paid_hours`,
`planning_utilization_percent`, `cost_per_worker_minute_minor`, `created_at`,
`created_by_id`, `updated_at`, `updated_by_id`. Decimals serialize as strings.

Creating a version closes the group's open predecessor.

**Errors:** `ITEM_COST_BASIS_VERSION_EFFECTIVE_FROM_FUTURE`,
`ITEM_COST_BASIS_VERSION_EFFECTIVE_FROM_REQUIRED`,
`ITEM_COST_BASIS_VERSION_EFFECTIVE_FROM_NOT_AFTER_OPEN` (all 422),
`ITEM_COST_RATE_UNDERFLOW` (422 — the quantized rate would be zero),
`ITEM_COST_CONCURRENT_BASIS_VERSION` (409 — two writers raced for the open row).

---

### `GET /cost-groups/{client_id}/basis-versions`

**Auth:** `ADMIN`, `MANAGER` · **Query:** `limit`, `offset`

**Response:** `{ "production_cost_basis_versions": [ … ], "production_cost_basis_versions_pagination": { "has_more", "limit", "offset" } }`

---

### `DELETE /basis-versions/{client_id}`

**Auth:** `ADMIN`, `MANAGER` · **Response:** `{ "production_cost_basis_version": { … } }`

**Errors:** `ITEM_COST_BASIS_VERSION_IN_USE` (422) when any evaluation references it.

---

### `POST /cost-model-versions`

**Auth:** `ADMIN`, `MANAGER`

**Request** — a version is replaced whole; terms are never edited in place:

```json
{
  "effective_from": "2026-08-15",
  "currency": "swedish_krona",
  "terms": [
    { "name": "VAT reserve", "calculation_type": "percentage_of_expected_sale_price", "percent_value": "20.000" },
    { "name": "Shipping",    "calculation_type": "fixed_amount",                       "fixed_amount_minor": 15000 },
    { "name": "Purchase",    "calculation_type": "item_purchase_cost" }
  ]
}
```

`percent_value` is a **planning allocation percentage applied to the gross expected sale
price — never the legally payable tax amount**. For a statutory 25 % VAT-on-net, enter
`20.00` against the gross base.

**Response:** `{ "cost_model_version": { … , "terms": [ … ] } }`. Version fields:
`client_id`, `workspace_id`, `effective_from`, `effective_to`, `currency`, `created_at`,
`created_by_id`, `updated_at`, `updated_by_id`, `terms`. Term fields: `client_id`,
`workspace_id`, `cost_model_version_id`, `name`, `calculation_type`, `percent_value`,
`fixed_amount_minor`, `created_at`, `created_by_id`, `updated_at`, `updated_by_id`.

**Errors:** `ITEM_COST_TERM_SHAPE_INVALID` (422 — the message names the
`calculation_type` and the offending column), `ITEM_COST_TERM_NAME_TAKEN`,
`ITEM_COST_PURCHASE_TERM_DUPLICATE` (at most one `item_purchase_cost` term),
`ITEM_COST_MODEL_VERSION_EFFECTIVE_FROM_FUTURE` / `_REQUIRED` / `_NOT_AFTER_OPEN`,
`ITEM_COST_CONCURRENT_MODEL_VERSION` (409).

---

### `GET /cost-model-versions`

**Auth:** `ADMIN`, `MANAGER` · **Query:** `limit`, `offset`

**Response:** `{ "cost_model_versions": [ … ], "cost_model_versions_pagination": { "has_more", "limit", "offset" } }` — each version carries its `terms`.

---

### `DELETE /cost-model-versions/{client_id}`

**Auth:** `ADMIN`, `MANAGER` · **Response:** `{ "cost_model_version": { … } }`

**Errors:** `ITEM_COST_MODEL_VERSION_IN_USE` (422) when any evaluation references it.

---

## Valuation

### `PUT /items/{item_client_id}/valuation`

Sets the item's current price/cost and returns an economic preview under its own key.

**Auth:** `ADMIN`, `MANAGER`

**Request:**

```json
{ "expected_sale_price_minor": 400000, "purchase_cost_minor": 120000, "currency": "swedish_krona" }
```

Both amounts are optional individually and must be `≥ 0`; at least one must be present.
`currency` is required.

**Response:**

```json
{
  "item_valuation": {
    "client_id": "ival_…",
    "workspace_id": "ws_…",
    "item_id": "itm_…",
    "expected_sale_price_minor": 400000,
    "purchase_cost_minor": 120000,
    "currency": "swedish_krona",
    "superseded_at": null,
    "superseded_by_id": null,
    "created_at": "2026-08-15T10:00:00+00:00",
    "created_by_id": "usr_…"
  },
  "preview": {
    "status": "not_evaluated",
    "production_budget_minor": 200000,
    "allowed_worker_minutes": "160.00"
  }
}
```

**The preview lives under its own key and is never merged with committed figures.** It is
ephemeral: computed by the same calculator, never persisted, carrying no `client_id`. It
creates nothing and supersedes nothing.

Numerics inside `preview`: the computable state `not_evaluated` carries the fully
computed `production_budget_minor` and `allowed_worker_minutes`. Every other status
carries `null` for both — never `0`.

Saving a price for the first time creates version 1. There is no confirmation step
anywhere in the flow. A later save supersedes.

**Errors:** `ITEM_COST_VALUATION_AMOUNT_REQUIRED` (422 — both amounts null),
`ITEM_COST_CONCURRENT_VALUATION` (409). Negative amounts and a missing currency are
request-schema rejections (422) with no domain identity.

---

### `GET /items/{item_client_id}/valuations`

**Auth:** `ADMIN`, `MANAGER` · Unpaginated.

**Response:** `{ "item_valuations": [ … ] }` — newest first, non-deleted rows only.

---

### `DELETE /items/{item_client_id}/valuation`

Deletes the **current** valuation only. Superseded rows are immutable history.

**Auth:** `ADMIN`, `MANAGER`

**Response:** `{ "preview": { "status": "item_unvalued", "production_budget_minor": null, "allowed_worker_minutes": null } }`

The status is re-resolved through the same ordering as everywhere else, so a never-priced
item and a deleted-price item read the same: in an unconfigured workspace both report the
missing-setup reason, in a configured workspace both report `item_unvalued`.

**Errors:** `ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE` (422).

---

## Evaluations

### `POST /tasks/{task_client_id}/evaluations/commit`

Freezes the economic decision for this episode. Supersedes the previous committed row.

**Auth:** `ADMIN`, `MANAGER`

**Request** — all fields optional:

```json
{ "expected_sale_price_minor": 400000, "purchase_cost_minor": 120000, "label": "after re-pricing" }
```

The amounts are overrides; omitting them uses the item's current valuation. **No currency
is ever accepted** — the evaluation's currency is the valuation's. When an override
differs from the current valuation, the valuation chain is advanced too, so the item's
price and the committed figures cannot disagree.

**Response:** `{ "evaluation": { … } }`

Evaluation fields: `client_id`, `workspace_id`, `task_id`, `item_id`, `kind`, `label`,
`task_type_snapshot`, `return_source_snapshot`, `expected_sale_price_minor`,
`purchase_cost_minor`, `currency`, `cost_model_version_id`, `production_cost_group_id`,
`production_cost_basis_version_id`, `monthly_paid_hours_snapshot`,
`planning_utilization_percent_snapshot`, `fixed_monthly_cost_minor_snapshot`,
`cost_per_worker_minute_minor_snapshot`, `production_budget_minor`,
`allowed_worker_minutes`, `calculation_version`, `committed_at`, `superseded_at`,
`superseded_by_id`, `promoted_from_id`, `created_at`, `created_by_id`, `terms`, `error`.

Term fields: `client_id`, `workspace_id`, `evaluation_id`, `name`, `calculation_type`,
`percent_value`, `fixed_amount_minor`, `amount_minor`, `created_at`.

**Errors** — every refusal is a translation of the resolved status, and nothing is
written before the calculator succeeds:

| Condition | Identity |
|---|---|
| Task has no active PRIMARY item | `ITEM_COST_NO_PRIMARY_ITEM` |
| Task is in a terminal state | `ITEM_COST_TASK_TERMINAL` |
| Item's major category unresolvable | `ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY` |
| No active group for the category | `ITEM_COST_NO_COST_GROUP` |
| More than one active group | `ITEM_COST_AMBIGUOUS_COST_GROUP` (message names the count and the ids) |
| No applicable basis version | `ITEM_COST_NO_BASIS_VERSION` |
| No applicable cost-model version | `ITEM_COST_NO_COST_MODEL_VERSION` |
| Item has no current valuation | `ITEM_COST_ITEM_UNVALUED` |
| Valuation carries no expected price | `ITEM_COST_EXPECTED_PRICE_REQUIRED` |
| Model has a purchase term, valuation has no purchase cost | `ITEM_COST_PURCHASE_COST_REQUIRED` |
| Valuation / basis / model currencies disagree | `ITEM_COST_CURRENCY_MISMATCH` (names both sides and which pair failed) |
| A concurrent commit won the current-row index | `ITEM_COST_CONCURRENT_COMMIT` (409) |

All 422 unless marked otherwise.

**Side effects:** a TASK history entry (`item_cost_evaluation`), an
`item_cost_evaluation.committed` audit row, and — after the transaction commits — the
`item_economics:evaluation-committed` workspace event (see [events.md](events.md)).

---

### `GET /tasks/{task_client_id}/evaluations`

The task's committed chain and its projections, in separate keys — committed and
speculative figures never merge into one list.

**Auth:** `ADMIN`, `MANAGER` · Unpaginated (both sets are bounded per task).

**Response:**

```json
{ "evaluations": [ { } ], "projections": [ { } ] }
```

- `evaluations` — the committed chain, ordered `committed_at DESC, client_id DESC`, so
  the current row is first.
- `projections` — ordered `created_at DESC, client_id DESC`.
- Each row carries its `terms`, ordered `created_at ASC, client_id ASC`.

Each returned evaluation is re-derived from its own snapshot. A mismatch is logged as an
integrity-check failure and the row still renders, carrying the marker in its `error`
key, so the payload stays homogeneous.

---

### `POST /tasks/{task_client_id}/projections`

A what-if. Creates nothing operational and is read by nothing operational.

**Auth:** `ADMIN`, `MANAGER`

**Request:**

```json
{
  "source": "committed",
  "source_projection_id": null,
  "expected_sale_price_minor": 450000,
  "purchase_cost_minor": null,
  "label": "if we ask 4500"
}
```

`source` is `"committed" | "projection" | "scratch"` (default `"scratch"`).
`source_projection_id` is required exactly when `source == "projection"`.

**Response:** `{ "evaluation": { … } }` with `kind = "projection"` and `committed_at` null.

**Errors:** the same status translations as the commit path, plus `422` on a missing or
foreign `source_projection_id`.

---

### `DELETE /projections/{client_id}`

**Auth:** `ADMIN`, `MANAGER` · **Response:** `{ "evaluation": { … } }`

Projections are deletable. **Committed evaluations are not** — there is no delete path for
them anywhere in the API.

---

### `POST /projections/{client_id}/promote`

Turns a scenario into the decision. Creates a **new committed evaluation** carrying
`promoted_from_id`; the projection itself is not mutated.

**Auth:** `ADMIN`, `MANAGER` · No request body.

**Response:** `{ "evaluation": { … } }` with `kind = "committed"`.

Promotion runs the same commit procedure as `POST /evaluations/commit`, so it supersedes
the previous committed row, records the same history and audit entries, and emits the same
workspace event.

---

## Status and read models

### `GET /tasks/{task_client_id}/budget-status`

The live picture: the committed snapshot's figures, consumption recomputed at read time,
and the stored result row when one exists.

**Auth:** `ADMIN`, `MANAGER`, `WORKER`, `SELLER` — **two payloads, selected by role.**

**Manager response (ADMIN, MANAGER):**

```json
{
  "status": "ok",
  "item_binding": "bound",
  "actual_worker_seconds": 7200,
  "actual_worker_minutes": "120.00",
  "remaining_worker_minutes": "40.00",
  "percent_consumed": "75.00",
  "variance_worker_minutes": "40.00",
  "result": {
    "actual_worker_seconds": 7200,
    "actual_worker_minutes": "120.00",
    "consumed_cost_minor": 150000,
    "variance_worker_minutes": "40.00",
    "variance_cost_minor": 50000,
    "task_state_snapshot": "ready",
    "task_closed_at": null,
    "calculation_version": 1,
    "computed_at": "2026-08-15T10:00:00+00:00"
  },
  "production_budget_minor": 200000,
  "allowed_worker_minutes": "160.00",
  "consumed_cost_minor": 150000,
  "variance_cost_minor": 50000,
  "evaluation_id": "ice_…",
  "item_id": "itm_…"
}
```

**Worker/seller response (WORKER, SELLER)** — a different query service and a serializer
with no monetary keys at all:

```json
{
  "status": "ok",
  "item_binding": "bound",
  "actual_worker_seconds": 7200,
  "actual_worker_minutes": "120.00",
  "remaining_worker_minutes": "40.00",
  "percent_consumed": "75.00",
  "variance_worker_minutes": "40.00",
  "allowed_worker_minutes": "160.00",
  "result": {
    "actual_worker_minutes": "120.00",
    "variance_worker_minutes": "40.00",
    "percent_consumed": "75.00",
    "task_state_snapshot": "ready",
    "computed_at": "2026-08-15T10:00:00+00:00"
  }
}
```

`production_budget_minor`, `consumed_cost_minor`, `variance_cost_minor`, `evaluation_id`
and `item_id` are **absent** — not null — from the worker payload, as are the result's
`actual_worker_seconds`, `consumed_cost_minor`, `variance_cost_minor`, `task_closed_at`
and `calculation_version`.

`item_binding` is `"bound"`, `"detached"` (the task has no active PRIMARY item) or
`"mismatched"` (the committed evaluation names a different item than the task's current
PRIMARY).

`result` is `null` until the analytics handler has written the row. It is present from the
first READY entry onward, days before a manual resolution, and `task_state_snapshot` is
what tells you which boundary it was computed at — see [states.md](states.md).

For every status other than `ok` and `infeasible`, every numeric field above is `null`.

---

### `GET /items/{item_client_id}/economics`

Lifetime economics for one item: one entry per episode, plus totals. Read model only —
results are never merged across tasks.

**Auth:** `ADMIN`, `MANAGER` · **Query:** `limit` (1–200, default 50), `offset` (≥ 0)

**Response:**

```json
{
  "episodes": [
    {
      "task_id": "tsk_…",
      "task_type_snapshot": "return",
      "return_source_snapshot": "after_purchase",
      "evaluation": { },
      "result": { }
    }
  ],
  "totals": {
    "actual_worker_seconds": 7200,
    "actual_worker_minutes": "120.00",
    "consumed_cost_minor": 150000,
    "variance_worker_minutes": "40.00",
    "variance_cost_minor": 50000
  },
  "episodes_pagination": { "has_more": false, "limit": 50, "offset": 0 }
}
```

Episodes are the item's **current committed** evaluations, newest first. `result` is
Each episode's `evaluation` carries `terms: []` on this read — fetch
`GET /tasks/{task_client_id}/evaluations` for the term breakdown.
`null` for an episode whose result row has not been written. Totals sum only the episodes
that have one.
