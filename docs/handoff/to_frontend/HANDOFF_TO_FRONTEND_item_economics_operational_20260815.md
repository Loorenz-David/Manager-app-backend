# HANDOFF_TO_FRONTEND_item_economics_operational_20260815

**Stage 2 of 2.** This document is the day-to-day half of item economics: pricing an item,
committing a budget, exploring what-ifs, and reading how much of the allowance the work has
consumed. It also carries **the removals** — the keys that no longer exist and the ones
that now return `422`.

The settings half is
[`HANDOFF_TO_FRONTEND_item_economics_configuration_20260815.md`](HANDOFF_TO_FRONTEND_item_economics_configuration_20260815.md).
**Nothing here produces a number until that half has been done once**: on an unconfigured
workspace every screen below correctly reports "not configured" rather than a value. You
can build these screens from this document alone, but you cannot demo them without the
settings first.

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_economics_operational_20260815`
- Created at (UTC): `2026-08-15T00:00:00Z`
- Owner agent: `implementation-executor (phase 9)`
- Source plan: `backend/docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_9_docs_and_drift.md`
- Living docs: `backend/docs/domains/item_economics/`

---

## 1. Read this first — the removals

### 1.1 Item money keys are gone from every read

`item_value_minor`, `item_cost_minor` and `item_currency` **no longer exist on items**.
Nine read surfaces that used to emit them no longer carry any of the three:

| Serializer | Surfaces |
|---|---|
| `domain/items/serializers.py::_serialize_item_base` | items list, item detail, customer detail's `linked_items[]` |
| `domain/tasks/serializers.py::serialize_item` | tasks list, task detail, task coordination threads, upholstery order needs, pending seat tasks, upholstery orders |

If any component still reads one of those keys off an item, it is reading `undefined`
today. Search for all three names and remove the readers before you build anything new.

The item's price now lives on its **valuation** — see §3.

### 1.2 Sending a legacy money key is a hard `422`

The three keys are **still accepted by the request bodies** of item create / find-or-create
/ update and task create. That is deliberate: deleting them from the schemas would let a
client's price be silently discarded instead of refused.

Sending any of the three with a **non-null** value returns:

```json
{ "error": "ITEM_MONEY_MOVED: item money fields moved to the item-valuation endpoint", "ok": false }
```

→ `422`. That message is exact. Present-with-null and absent both pass and are ignored.

**The live risk:** production task creation currently omits all three (the body builder
`normalize-task-form-payload.ts` does not emit the amounts and serialises `item_currency`
as an absent key). The moment anyone mounts a currency input on the task form, task
creation `422`s as soon as a user picks a value. Remove the fields from the form models,
do not just hide them.

### 1.3 Worker and seller payloads carry no money at all

Money is visible to **ADMIN and MANAGER only**. WORKER *and* SELLER are both excluded — a
seller no longer sees the step cost number that used to appear on task detail.

Where a monetary key is withheld it is **absent from the object**, not `null`. Read key
presence, never value, to decide whether to render a cost:

```ts
if ("total_cost_minor" in step) { /* render */ }   // correct
if (step.total_cost_minor != null) { /* render */ } // also works, but only by accident
```

`total_cost_minor` on task steps is affected on these endpoints:

| Endpoint | WORKER | SELLER |
|---|---|---|
| `GET /api/v1/tasks/{task_id}` | absent | absent |
| `GET /api/v1/tasks/{task_id}/steps` | absent | absent |
| `GET /api/v1/working-sections/{id}/steps` | absent | — |
| `GET /api/v1/working-sections/steps/user-last-active` | absent | — |
| `GET /api/v1/task-step-acknowledgments/reassigned-steps` | absent | — |
| `GET /api/v1/task-step-acknowledgments/pending` | absent | — |
| `GET /api/v1/worker-stats/{user_id}/daily-steps` | n/a (ADMIN/MANAGER route) | — |
| `GET /api/v1/worker-stats/last-interacted-steps` | n/a (ADMIN/MANAGER route) | — |

`GET /working-sections/steps/user-last-active` is the worker's live step card
(`LastActiveStepCard.tsx`) — the most frequently fetched worker payload in the app. Smoke
that one first.

The same rule governs this domain's own budget-status endpoint, which serves two different
payloads by role — see §5.1.

### 1.4 Two cost numbers exist and they are not the same number

`task_steps.total_cost_minor` (salary-priced, working **+ paused**) and the item-economics
`consumed_cost_minor` (allowance-priced, working only) answer different questions and
differ for the same task by construction.

Never put them in the same view as if they were comparable, never subtract one from the
other, and never label either simply "cost". The backend guarantees they never appear in
the same object; the UI has to hold up its half.

---

## 2. Conventions

Base path: `/api/v1/item-economics/`, `Authorization: Bearer <access_token>` required.

Envelope: `{"data": …, "ok": true, "warnings": []}` / `{"error": "IDENTITY: sentence", "ok": false}`.

**Errors have no `code` field.** The identity is the leading token of `error` up to the
first colon; branch on that, treat the rest as display copy.

Money is **integer minor units**. Decimals arrive as **strings** (`"160.00"`); parse as
decimals, never floats.

Role gate: everything below is **ADMIN/MANAGER only except
`GET /tasks/{task_client_id}/budget-status`**, which admits ADMIN, MANAGER, WORKER and
SELLER.

---

## 3. Pricing an item

### 3.1 `PUT /items/{item_client_id}/valuation` — set the price

**Auth:** ADMIN, MANAGER

```json
{ "expected_sale_price_minor": 400000, "purchase_cost_minor": 120000, "currency": "swedish_krona" }
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `expected_sale_price_minor` | int minor units | conditional | `>= 0` |
| `purchase_cost_minor` | int minor units | conditional | `>= 0` |
| `currency` | enum | **yes** | `swedish_krona` \| `danish_krona` \| `euro` |

At least one of the two amounts must be present. Both amounts null → `422`
`ITEM_COST_VALUATION_AMOUNT_REQUIRED`. A negative amount or a missing currency is a plain
schema `422` with no identity.

→ `200`

```json
{
  "item_valuation": {
    "client_id": "ival_01H…",
    "workspace_id": "ws_01H…",
    "item_id": "itm_01H…",
    "expected_sale_price_minor": 400000,
    "purchase_cost_minor": 120000,
    "currency": "swedish_krona",
    "superseded_at": null,
    "superseded_by_id": null,
    "created_at": "2026-08-15T10:00:00+00:00",
    "created_by_id": "usr_01H…"
  },
  "preview": {
    "status": "not_evaluated",
    "production_budget_minor": 200000,
    "allowed_worker_minutes": "160.00"
  }
}
```

**`preview` is a sibling key and must stay one in your UI too.** It is ephemeral: computed
on the fly, never stored, carrying no `client_id`. It says "if you committed right now,
here is what you would get". It creates nothing and supersedes nothing. **Never render a
preview figure in a place a decided figure appears** — that confusion is the exact reason
it has its own key.

`preview.status` carries the full status vocabulary (§6). Two numeric rules:

- status `not_evaluated` → `production_budget_minor` and `allowed_worker_minutes` are
  **fully computed**. This is the state you show the manager a real number in.
- **every other status** → both are `null`. Never `0`. Render the status, not a zero.

**There is no confirmation step.** The first save creates version 1 immediately; a later
save supersedes it. Build the form accordingly.

`409` `ITEM_COST_CONCURRENT_VALUATION` when two writers raced — refetch and retry.

### 3.2 `GET /items/{item_client_id}/valuations` — price history

**Auth:** ADMIN, MANAGER · unpaginated.

```json
{ "item_valuations": [ { } ] }
```

Newest first. Deleted rows are hidden. The row with `superseded_at: null` is the current
price; everything else is history and is **immutable**.

### 3.3 `DELETE /items/{item_client_id}/valuation` — remove the current price

**Auth:** ADMIN, MANAGER

Deletes the **current** valuation only — the escape hatch for a mistyped price. Superseded
rows are true history and cannot be deleted: attempting it returns `422`
`ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE`.

```json
{ "preview": { "status": "item_unvalued", "production_budget_minor": null, "allowed_worker_minutes": null } }
```

Note the response is **status-only** — no `item_valuation` key. The status is re-resolved
from scratch, so a never-priced item and a just-deleted-price item show the **same**
status: `item_unvalued` in a configured workspace, the missing-setup reason in an
unconfigured one.

---

## 4. Committing and exploring

### 4.1 `POST /tasks/{task_client_id}/evaluations/commit`

Freezes the economic decision for this task. **This is the act that produces a budget.**

**Auth:** ADMIN, MANAGER

```json
{ "expected_sale_price_minor": 400000, "purchase_cost_minor": 120000, "label": "after re-pricing" }
```

Every field is optional. The amounts are **overrides**; omit them to use the item's current
valuation. **No currency is ever accepted here** — the evaluation's currency is the
valuation's, full stop. `label` is free text, max 255 chars, stored verbatim.

When an override differs from the current valuation, the backend **also advances the
valuation chain**, so the item's price and the committed figures can never disagree. If
your screen shows both, refetch the valuation after a commit with overrides.

→ `200` `{ "evaluation": { … } }`

```json
{
  "client_id": "ice_01H…",
  "workspace_id": "ws_01H…",
  "task_id": "tsk_01H…",
  "item_id": "itm_01H…",
  "kind": "committed",
  "label": "after re-pricing",
  "task_type_snapshot": "return",
  "return_source_snapshot": "after_purchase",
  "expected_sale_price_minor": 400000,
  "purchase_cost_minor": 120000,
  "currency": "swedish_krona",
  "cost_model_version_id": "cmv_01H…",
  "production_cost_group_id": "pcg_01H…",
  "production_cost_basis_version_id": "pcbv_01H…",
  "monthly_paid_hours_snapshot": "160.00",
  "planning_utilization_percent_snapshot": "80.00",
  "fixed_monthly_cost_minor_snapshot": 20000000,
  "cost_per_worker_minute_minor_snapshot": "26.0417",
  "production_budget_minor": 200000,
  "allowed_worker_minutes": "160.00",
  "calculation_version": 1,
  "committed_at": "2026-08-15T10:00:00+00:00",
  "superseded_at": null,
  "superseded_by_id": null,
  "promoted_from_id": null,
  "created_at": "2026-08-15T10:00:00+00:00",
  "created_by_id": "usr_01H…",
  "terms": [
    {
      "client_id": "icet_01H…",
      "workspace_id": "ws_01H…",
      "evaluation_id": "ice_01H…",
      "name": "VAT reserve",
      "calculation_type": "percentage_of_expected_sale_price",
      "percent_value": "20.000",
      "fixed_amount_minor": null,
      "amount_minor": 80000,
      "created_at": "2026-08-15T10:00:00+00:00"
    }
  ],
  "error": null
}
```

The `*_snapshot` fields and `terms` are what make a committed evaluation explain itself
years later — render them as the "how this number was reached" drill-down. `error` is the
integrity marker (§4.3).

**Errors.** Every refusal is the status vocabulary translated into an identity, and
**nothing is written when one fires**:

| Identity | HTTP | Meaning to show the user |
|---|---|---|
| `ITEM_COST_NO_PRIMARY_ITEM` | `422` | this task has no primary item to price |
| `ITEM_COST_TASK_TERMINAL` | `422` | the task is finished; economics cannot be committed now |
| `ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY` | `422` | the item has no wood/seat category |
| `ITEM_COST_NO_COST_GROUP` | `422` | → settings: no cost group for that category |
| `ITEM_COST_AMBIGUOUS_COST_GROUP` | `422` | → settings: more than one active group (message names them) |
| `ITEM_COST_NO_BASIS_VERSION` | `422` | → settings: the group has no applicable cost basis |
| `ITEM_COST_NO_COST_MODEL_VERSION` | `422` | → settings: no applicable cost model |
| `ITEM_COST_ITEM_UNVALUED` | `422` | → price the item first |
| `ITEM_COST_EXPECTED_PRICE_REQUIRED` | `422` | the valuation has no expected sale price |
| `ITEM_COST_PURCHASE_COST_REQUIRED` | `422` | the cost model has a purchase term but the item has no purchase cost |
| `ITEM_COST_CURRENCY_MISMATCH` | `422` | the item's, basis's and model's currencies disagree (message names both sides and which pair failed) |
| `ITEM_COST_CONCURRENT_COMMIT` | `409` | someone else committed first — refetch |

The five `NO_*` / `AMBIGUOUS_*` identities should route the manager to the settings screen,
not show a generic error.

A commit also broadcasts the socket event `item_economics:evaluation-committed` — §7.

### 4.2 `POST /tasks/{task_client_id}/projections` — what-if

**Auth:** ADMIN, MANAGER

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
`source_projection_id` is required **exactly when** `source == "projection"`.

- `committed` — start from the task's current committed evaluation's inputs.
- `projection` — start from another projection's inputs.
- `scratch` — start from the item's live valuation and current configuration.

Returns the same object shape with `kind: "projection"` and `committed_at: null`. Same
error identities as the commit path.

**A projection is read by nothing operational** — not the budget status, not the worker
view, not the final result. It exists to be looked at and then promoted or thrown away.

### 4.3 `GET /tasks/{task_client_id}/evaluations` — the history screen

**Auth:** ADMIN, MANAGER · unpaginated (both sets are bounded per task).

```json
{ "evaluations": [ { } ], "projections": [ { } ] }
```

**Two keys, never merged.** Committed and speculative figures do not belong in one list,
and the API will not give you one.

- `evaluations` — the committed chain, current row first (`committed_at DESC`). Rows after
  the first carry `superseded_at` and `superseded_by_id`: that is the decision history.
- `projections` — newest first.
- Every row carries its `terms` in a stable order.

**The `error` key.** Each returned evaluation is re-derived from its own snapshot on read.
If a row's stored figures do not reproduce, `error` is non-null and the backend has logged
an integrity-check failure — **the row still renders**. Show a discreet warning badge if
you want to surface it; do not blank the row and do not call it "corrupt data".

### 4.4 `DELETE /projections/{client_id}`

**Auth:** ADMIN, MANAGER · returns the deleted projection.

**Committed evaluations are never deletable.** There is no endpoint for it. The only way to
change a decision is to commit a new one, which supersedes.

### 4.5 `POST /projections/{client_id}/promote`

**Auth:** ADMIN, MANAGER · no request body.

Turns a scenario into the decision: creates a **new committed evaluation** carrying
`promoted_from_id`, supersedes the previous committed row, and emits the same event as a
plain commit. **The projection itself is not consumed or mutated** — it stays in the
`projections` list.

Returns `{ "evaluation": { … } }` with `kind: "committed"`.

---

## 5. Reading the numbers

### 5.1 `GET /tasks/{task_client_id}/budget-status` — the budget screen

**Auth:** ADMIN, MANAGER, WORKER, SELLER — **the one endpoint everyone may call, and it
returns two different shapes.** The role is read from the token; there is no parameter.

**Manager shape (ADMIN, MANAGER):**

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
  "evaluation_id": "ice_01H…",
  "item_id": "itm_01H…"
}
```

**Worker/seller shape (WORKER, SELLER)** — a different service with a serializer that has
no monetary keys at all:

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

Absent for worker/seller — **absent, not null**: `production_budget_minor`,
`consumed_cost_minor`, `variance_cost_minor`, `evaluation_id`, `item_id`, and inside
`result`: `actual_worker_seconds`, `consumed_cost_minor`, `variance_cost_minor`,
`task_closed_at`, `calculation_version`.

The worker view is a **time budget**: minutes and a percentage. That is the whole contract
— do not synthesise a money figure from it.

**`item_binding`:**

| Value | Meaning |
|---|---|
| `bound` | normal — the evaluation is for the task's current primary item |
| `detached` | the task has no active primary item |
| `mismatched` | the committed evaluation names a **different** item than the task's current primary — the item on the task changed after the economics were decided. Say so; the figures still describe the item they were committed for. |

**`result` is `null`** until the backend has computed the episode's actuals. It is not a
"final" marker: it appears from the first time the task reaches READY, days before anyone
resolves it, and is recomputed at every later boundary. `task_state_snapshot` tells you
which boundary the numbers describe — `working`/`ready` means still converging;
`resolved`/`failed`/`cancelled` with `task_closed_at` set means final.

**Numerics:** for every status other than `ok` and `infeasible`, every numeric above is
`null`. Render the status sentence, never a zero.

### 5.2 `GET /items/{item_client_id}/economics` — lifetime

> Each episode's `evaluation` carries `terms: []` on this read — do NOT build
> the §4.1 drill-down from it; fetch `GET /tasks/{task_client_id}/evaluations`
> for the term breakdown.

**Auth:** ADMIN, MANAGER · query `limit` (1–200, default 50), `offset` (≥ 0)

```json
{
  "episodes": [
    {
      "task_id": "tsk_01H…",
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

One entry per **episode** — an item returning on a later task is a new episode with its own
evaluation and result. Results never merge across tasks. `result` is `null` for an episode
that has none, and `totals` sums only the episodes that have one, so the totals can lag the
episode list. Say "across N completed episodes", not "lifetime total".

---

## 6. The status vocabulary — twelve values

Used identically by the valuation preview, the budget status and the configuration status.
It is a **branch, not a flat list**, and building your UI as a flat switch will produce the
wrong copy.

**Branch A — this task has a committed evaluation.** The configuration is irrelevant; the
snapshot stands on its own.

| Value | When | What to show |
|---|---|---|
| `infeasible` | the allowance is zero or negative | the budget does not buy any work; `percent_consumed` is `null` |
| `ok` | otherwise | the normal budget screen |

**Branch B — no committed evaluation.** The reason, in precedence order; the first match
wins, and it is the one you show:

| # | Value | What to show |
|---|---|---|
| 1 | `item_missing_major_category` | the item has no wood/seat category — fix the item |
| 2 | `not_configured_no_cost_group` | → settings: no cost group for that category |
| 3 | `not_configured_ambiguous_cost_group` | → settings: more than one active group (should be unreachable; if you see it, tell the backend team) |
| 4 | `not_configured_no_basis_version` | → settings: the group has no cost basis |
| 5 | `not_configured_no_cost_model_version` | → settings: no cost model |
| 6 | `item_unvalued` | → price this item |
| 7 | `item_missing_expected_price` | the valuation has no expected sale price |
| 8 | `item_missing_purchase_cost` | the cost model needs a purchase cost and the item has none |
| 9 | `currency_mismatch` | the item's price and the configuration are in different currencies; nothing can be calculated |
| 10 | `not_evaluated` | **everything is ready — nobody has committed yet.** This is the "Commit budget" call to action, not an error. |

Rows 2–5 are settings problems, rows 1 and 6–9 are data problems on this item, and row 10
is the happy pre-commit state. Copy them differently.

**`not_evaluated` is the one status in branch B that carries real numbers**, and only
inside the valuation endpoint's `preview` key. Everywhere else, and for every other branch-B
status, the numerics are `null`.

---

## 7. The socket event

`item_economics:evaluation-committed`, broadcast to the workspace room after the commit
transaction succeeds. Emitted by the explicit commit, by promotion, and by the automatic
commit at task creation. **Projections never emit.**

```json
{ "client_id": "tsk_01H…", "evaluation_id": "ice_01H…" }
```

`client_id` is the **task's** id, matching the `task:state-changed` shape. The event
carries no figures — treat it as "refetch this task's budget status".

---

## 8. Flow narratives

### 8.1 Pricing an item

The manager opens an item, types an expected sale price and a purchase cost, picks the
currency, saves. One `PUT` and it is version 1 — no confirmation dialog exists on the
backend, so do not invent one. The response's `preview` immediately shows the budget and
allowance the item *would* get. If `preview.status` is anything other than `not_evaluated`,
show the status and no numbers.

Changing the price later is the same call. The old row becomes history, visible under
`GET /valuations`. Deleting the current price is allowed; deleting a superseded one is not.

### 8.2 Committing a budget

From the task screen, the manager sees `status: "not_evaluated"` on the budget status and a
"Commit budget" action. `POST /evaluations/commit` with an empty body uses the item's
current price. The response is the frozen decision: budget, allowance, and every input it
used.

Committing again later supersedes — the previous decision stays readable in
`GET /evaluations`. There is no edit and no delete.

If the commit refuses, the identity tells you where to send the manager: a `NOT_CONFIGURED_*`
family member goes to settings, `ITEM_COST_ITEM_UNVALUED` goes to the price form.

### 8.3 What-if projections and promotion

The manager wants to know what happens at a higher asking price. `POST /projections` with
`source: "committed"` and an overridden `expected_sale_price_minor` returns a full
evaluation object that is **not** a decision — it shows up under `projections`, never under
`evaluations`, and no worker screen and no result will ever see it.

Two or three of these can sit side by side. When one wins, `POST /projections/{id}/promote`
commits it: a new committed row appears carrying `promoted_from_id`, the old committed row
is superseded, and the projection stays where it was.

Label projections. `label` is free text and is the only thing distinguishing three rows of
similar numbers in the list.

### 8.4 Quantity does not participate

A valuation is **per item**, not per unit. An item with `quantity: 5` priced at
`expected_sale_price_minor: 100000` has an expected sale price of 100000 — the backend does
not multiply, and neither should any label you write. Do not show "1000 × 5" anywhere near
these figures.

### 8.5 Creating a task, then finding out whether it got priced

Task creation can carry the price inline (§9), and when everything lines up it also commits
the evaluation automatically. **But the create-task response carries no priced-or-not
signal** — there is no field on it that says whether an evaluation was committed, and the
automatic commit is best-effort: it is skipped silently whenever the item is not ready.

So the flow is **two calls**:

1. `PUT /api/v1/tasks` — create the task (optionally with the inline price).
2. `GET /api/v1/item-economics/tasks/{task_client_id}/budget-status` — read what actually
   happened.

Step 2's `status` is the answer: `ok` or `infeasible` means an evaluation exists; anything
else is branch B and names what is missing. Do not infer success from the create response.

### 8.6 The team task-flow history entry

Committing an evaluation writes a task history record, so the commit appears in the task's
activity feed like any other change. Its field name is `item_cost_evaluation` and its
from/to values carry the four headline figures — `expected_sale_price_minor`,
`purchase_cost_minor`, `production_budget_minor`, `allowed_worker_minutes` — so the feed
can render "budget changed from X to Y" without a second fetch. The `from` side is `null`
for the first commit on a task.

### 8.7 The budget screen from READY

The budget screen is live from the moment work starts, but the **`result` block** appears
the first time the task reaches READY — which is the machine-detectable completion of the
work, days before someone manually resolves the task.

That matters for labelling. A result whose `task_state_snapshot` is `ready` is **not**
final: a reopened task, a straggling step closed the next morning, or a later resolution
will all recompute it. Label it by its boundary:

- `task_state_snapshot` ∈ `working` | `ready` → "so far" / "in progress"
- `task_state_snapshot` ∈ `resolved` | `failed` | `cancelled`, `task_closed_at` set → "final"

`computed_at` is when the row was last recomputed and changes on every boundary — do not
show it as "completed at".

---

## 9. Inline pricing at task creation

`PUT /api/v1/tasks` accepts the valuation trio inside its `item` block:

```json
{
  "task_type": "return",
  "item": {
    "article_number": "302.445.11",
    "expected_sale_price_minor": 400000,
    "purchase_cost_minor": 120000,
    "currency": "swedish_krona"
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `item.expected_sale_price_minor` | int minor units, `>= 0` | optional |
| `item.purchase_cost_minor` | int minor units, `>= 0` | optional |
| `item.currency` | enum | **required as soon as either amount is present** |

Sending an amount without `item.currency` is a `422`:
`"item.currency is required when an inline item price is provided"`.

These are **not** the legacy keys. `item.item_value_minor` / `item.item_cost_minor` /
`item.item_currency` still exist on the body and are still rejected (§1.2); the trio above
is the replacement.

### 9.1 Inline re-pricing — an existing item that already has a price

Task creation resolves the item first (by `client_id`, or `article_number` / `sku`). If it
matches an **existing** item with a current valuation, sending the trio now re-prices that
item. An amount supplied in the request replaces the stored amount; a field omitted from
the request keeps its current value.

If the resulting amounts or currency differ from the current valuation, task creation
writes a new valuation version credited to whoever created the task. If the effective
amounts and currency are identical, it writes nothing at all — no new valuation row, no
supersession and no valuation audit event.

An existing item with *no* current valuation (never priced, or its price deleted) still
accepts the trio and starts a valuation chain; it does not resurrect a deleted row. This
inline convenience deliberately differs from `PUT /items/{id}/valuation`, which continues
to replace values wholesale rather than inheriting an omitted amount.

### 9.2 What the automatic commit does with it

When the item ends up with a valuation and the workspace is configured, task creation also
commits the evaluation for you — best effort, inside its own savepoint, so a failure never
fails the task. Six outcomes, all silent from the response's point of view:

| Inline trio | Cost model | Outcome |
|---|---|---|
| expected + purchase + currency | has an `item_purchase_cost` term | **commits** |
| expected + currency | no purchase term | **commits** |
| expected + currency | **has** a purchase term | skipped — `item_missing_purchase_cost` |
| purchase + currency (no expected) | any | skipped — `item_missing_expected_price` |
| full trio, currency ≠ configuration | any | skipped — `currency_mismatch` |
| any | workspace not configured | skipped — the relevant `not_configured_*` reason |

A skip writes the valuation and no evaluation. This is exactly why §8.5's second call
exists: the create response looks identical in all six cases.

---

## Validation notes

- Backend validation run: full suite green at the phase-9 checkpoint. Role gates, the money
  redaction on all eight step endpoints, the `ITEM_MONEY_MOVED` bridge, inline-pricing
  versioning and the six auto-commit outcomes each have integration coverage.
- Suggested frontend validation:
  1. grep the app for `item_value_minor`, `item_cost_minor`, `item_currency` — every hit is
     either a form field to delete or a reader of a key that no longer exists;
  2. load the worker step card and task detail under a WORKER token and confirm no cost is
     rendered and nothing throws on the absent key; repeat under SELLER;
  3. create a task with the inline trio on a brand-new article number, then call
     budget-status and confirm `status: "ok"`;
  4. against an already-priced item, send a **different** price and confirm a new valuation
     version appears; repeat with the **identical** price and confirm no new version appears;
  5. walk the ten branch-B statuses by dismantling the configuration one piece at a time
     and confirm each renders its own copy, with no numbers.

## Trace links

- Living docs: `backend/docs/domains/item_economics/` (`README.md`, `api.md`, `events.md`, `states.md`)
- Configuration half: `HANDOFF_TO_FRONTEND_item_economics_configuration_20260815.md`
- Route table: `backend/app/beyo_manager/routers/README.md`
