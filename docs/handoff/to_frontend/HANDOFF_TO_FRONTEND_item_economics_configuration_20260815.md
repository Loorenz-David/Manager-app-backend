# HANDOFF_TO_FRONTEND_item_economics_configuration_20260815

**Stage 1 of 2.** This document is the settings half of item economics: the thirteen
endpoints a manager uses to configure the workshop's economics. **Nothing in the
operational handoff works until these have been called at least once** — every price
screen shows "no cost group set up" for every item on a workspace that has skipped this.

The operational half is
[`HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`](HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md).
This document is self-contained: you can build the configuration screens from it alone.

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_economics_configuration_20260815`
- Created at (UTC): `2026-08-15T00:00:00Z`
- Owner agent: `implementation-executor (phase 9)`
- Source plan: `backend/docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_9_docs_and_drift.md`
- Living docs: `backend/docs/domains/item_economics/`

---

## 1. What this configures, in one paragraph

A manager tells the system what the workshop costs to run and what share of an item's
expected sale price is reserved for other things. From those two facts the backend derives
**how many worker-minutes an item is allowed to consume** before it stops being
profitable. There are three configuration objects, and all three must exist before any
item can be evaluated:

1. a **production cost group** per major category (`wood`, `seat`) — a named pipeline of
   working sections;
2. an open **basis version** on each group — the monthly cost and paid capacity, from
   which the backend derives a cost per productive worker-minute;
3. an open **cost model version** for the workspace — the allocation terms subtracted from
   the expected sale price.

Build the settings page in that order. `GET /configuration-status` tells you exactly how
far a workspace has got.

---

## 2. Conventions

Base path: `/api/v1/item-economics/`. Every endpoint requires
`Authorization: Bearer <access_token>` and **every endpoint in this document is
ADMIN/MANAGER only** — a WORKER or SELLER token gets `403` from the route dependency
before any handler runs. Do not render entry points to these screens for those roles.

Envelope:

```json
{ "data": { }, "ok": true, "warnings": [] }
```

```json
{ "error": "IDENTITY: human sentence", "ok": false }
```

**Errors have no `code` field.** The machine-readable identity is the **leading token of
`error`, up to the first colon**. Branch on that token; treat the sentence after it as
display copy that may be reworded without notice.

```ts
const identity = body.error.split(":")[0];   // "ITEM_COST_GROUP_NAME_TAKEN"
```

Status codes you will see: `422` validation/admission refusals, `409` uniqueness and race
conflicts, `404` unknown id in this workspace, `403` wrong role.

**Money is integer minor units** (öre/cents) everywhere. **Decimals arrive as strings**
(`"160.00"`, `"20.000"`) — parse them as decimals, never as floats, and send them as
strings or numbers; both are accepted.

Lists use offset pagination: `?limit=<1..200, default 50>&offset=<≥0>`, and the response
carries a sibling `<key>_pagination` object with `has_more`, `limit`, `offset`.

---

## 3. `GET /configuration-status` — build the settings page from this

The one call the settings screen should make on mount. Nothing else tells you what is
missing.

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

- **`categories` is keyed by major category** and always carries both `wood` and `seat`.
  Readiness is per category: a workspace can price wood items and be unable to price seat
  items.
- `evaluable` is the per-category verdict. When it is false, `first_failure` names the
  first thing missing, using the same status vocabulary the operational handoff documents:
  `not_configured_no_cost_group` → `not_configured_ambiguous_cost_group` →
  `not_configured_no_basis_version` → `not_configured_no_cost_model_version`.
- `has_open_cost_model_version` is **workspace-wide**, not per category — one cost model
  serves both.

A category is fully set up when `evaluable` is `true` **and**
`has_open_cost_model_version` is `true`.

---

## 4. Cost groups (six endpoints)

A cost group is "the wood pipeline" or "the seat pipeline". It owns the working sections
whose time the basis version prices.

### 4.1 `POST /cost-groups`

```json
{ "name": "Wood workshop", "major_category": "wood" }
```

`major_category` is required and is one of `wood` | `seat`.

→ `200`

```json
{
  "production_cost_group": {
    "client_id": "pcg_01H…",
    "workspace_id": "ws_01H…",
    "name": "Wood workshop",
    "major_category": "wood",
    "created_at": "2026-08-15T10:00:00+00:00",
    "created_by_id": "usr_01H…",
    "updated_at": null,
    "updated_by_id": null
  }
}
```

**Errors:**

| Identity | HTTP | When |
|---|---|---|
| `ITEM_COST_GROUP_NAME_TAKEN` | `422` / `409` | another non-deleted group in the workspace already has this name |
| `ITEM_COST_GROUP_CATEGORY_TAKEN` | `422` / `409` | an active group already exists for this category — **only one per category** |

Both identities arrive at `422` when the backend catches the clash before writing and at
`409` when two writers raced. **The identity token is identical in both cases** — branch
on the token, not the status. The `422` message names the offending value; the `409`
message is the uniform conflict sentence.

### 4.2 `GET /cost-groups`

Query: `limit`, `offset`.

```json
{
  "production_cost_groups": [ { } ],
  "production_cost_groups_pagination": { "has_more": false, "limit": 50, "offset": 0 }
}
```

### 4.3 `PATCH /cost-groups/{client_id}`

```json
{ "name": "Wood workshop", "major_category": "wood" }
```

`name` is required; `major_category` is optional.

**A group's category cannot be changed once it has any basis version.** Flipping it would
silently reprice every item in both categories. Attempting it returns `422`
`ITEM_COST_GROUP_CATEGORY_IMMUTABLE`, with a message naming the group and its current
category. The correction path is delete-and-recreate, which the deletion guards below
protect.

In the UI: render the category selector as **read-only after creation**. Do not offer an
edit that the backend will always refuse.

Other errors: `ITEM_COST_GROUP_NAME_TAKEN`, `ITEM_COST_GROUP_CATEGORY_TAKEN` (both dual
path as above).

### 4.4 `DELETE /cost-groups/{client_id}`

Soft delete. Returns `{ "production_cost_group": { … } }`.

`422` `ITEM_COST_GROUP_IN_USE` when the group still has a non-deleted basis version or an
active section membership. **Remove those first** — the guard exists because deleting a
priced group would orphan its history.

### 4.5 `POST /cost-groups/{client_id}/sections`

```json
{ "working_section_id": "wsec_01H…" }
```

→ `{ "production_cost_group_section": { "client_id": "pcgs_…", "workspace_id": "ws_…", "production_cost_group_id": "pcg_…", "working_section_id": "wsec_…", "added_at": "…", "added_by_id": "usr_…", "removed_at": null, "removed_by_id": null } }`

`422` / `409` `ITEM_COST_SECTION_ALREADY_GROUPED` — **a working section belongs to at most
one active group.** When building the section picker, exclude sections already grouped
elsewhere, and handle the identity anyway for the concurrent case.

### 4.6 `DELETE /cost-groups/{client_id}/sections/{working_section_client_id}`

Note the path: the **section's** client id, not the membership row's.

Returns the membership row with `removed_at` / `removed_by_id` set. The row is never
deleted — the membership history is kept.

---

## 5. Basis versions (three endpoints)

A basis version answers "what does an hour of productive capacity in this group cost?".
It is **effective-dated and append-only**: you never edit one, you create the next.

### 5.1 `POST /cost-groups/{client_id}/basis-versions`

```json
{
  "effective_from": "2026-08-15",
  "fixed_monthly_cost_minor": 20000000,
  "currency": "swedish_krona",
  "monthly_paid_hours": "160.00",
  "planning_utilization_percent": "80.00"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `effective_from` | `date` (`YYYY-MM-DD`) | conditional — see below | may **not** be in the future |
| `fixed_monthly_cost_minor` | int minor units | yes | must be `> 0` |
| `currency` | enum | yes | `swedish_krona` \| `danish_krona` \| `euro` |
| `monthly_paid_hours` | decimal string | yes | `> 0` |
| `planning_utilization_percent` | decimal string | yes | `> 0` and `<= 100` |

**Do not send `cost_per_worker_minute_minor`.** It is derived by the backend and returned;
a client-supplied rate is never accepted anywhere in this domain.

→ `200`

```json
{
  "production_cost_basis_version": {
    "client_id": "pcbv_01H…",
    "workspace_id": "ws_01H…",
    "production_cost_group_id": "pcg_01H…",
    "effective_from": "2026-08-15",
    "effective_to": null,
    "fixed_monthly_cost_minor": 20000000,
    "currency": "swedish_krona",
    "monthly_paid_hours": "160.00",
    "planning_utilization_percent": "80.00",
    "cost_per_worker_minute_minor": "26.0417",
    "created_at": "2026-08-15T10:00:00+00:00",
    "created_by_id": "usr_01H…",
    "updated_at": null,
    "updated_by_id": null
  }
}
```

Creating a version **closes the group's previous open version** by setting its
`effective_to`. `effective_to: null` marks the open row — that is how you find "the current
basis" in a list response.

**Errors:**

| Identity | HTTP | When |
|---|---|---|
| `ITEM_COST_BASIS_VERSION_EFFECTIVE_FROM_FUTURE` | `422` | `effective_from` is after today |
| `ITEM_COST_BASIS_VERSION_EFFECTIVE_FROM_REQUIRED` | `422` | an open version exists and you omitted `effective_from` |
| `ITEM_COST_BASIS_VERSION_EFFECTIVE_FROM_NOT_AFTER_OPEN` | `422` | `effective_from` is not strictly after the open version's |
| `ITEM_COST_RATE_UNDERFLOW` | `422` | the derived rate rounds to zero — a tiny fixed cost over a huge capacity |
| `ITEM_COST_CONCURRENT_BASIS_VERSION` | `409` | another writer opened a version first |

The three `EFFECTIVE_FROM_*` identities are why the date field should be a date picker
bounded at today, pre-filled to today, and disabled-until-after the open version's
`effective_from` when one exists.

### 5.2 `GET /cost-groups/{client_id}/basis-versions`

Query: `limit`, `offset`.

```json
{
  "production_cost_basis_versions": [ { } ],
  "production_cost_basis_versions_pagination": { "has_more": false, "limit": 50, "offset": 0 }
}
```

This is the group's rate history. Render it as a timeline; the row with
`effective_to: null` is live.

### 5.3 `DELETE /basis-versions/{client_id}`

Note the path root: `/basis-versions/`, **not** under the group.

`422` `ITEM_COST_BASIS_VERSION_IN_USE` when any evaluation snapshot references it. Most
basis versions become undeletable as soon as an item is priced against them — that is
intended, and the UI should present deletion as an early-mistake correction, not a normal
action.

---

## 6. Cost model versions (three endpoints)

The cost model says what fraction of an item's expected sale price is reserved before the
production budget is calculated. **One open version per workspace**, shared by both
categories.

### 6.1 `POST /cost-model-versions`

A version is **replaced whole**. There is no endpoint to add, edit or remove a single term
— you post the complete term list every time, and the previous version closes.

```json
{
  "effective_from": "2026-08-15",
  "currency": "swedish_krona",
  "terms": [
    { "name": "VAT reserve", "calculation_type": "percentage_of_expected_sale_price", "percent_value": "20.000" },
    { "name": "Shipping",    "calculation_type": "fixed_amount", "fixed_amount_minor": 15000 },
    { "name": "Purchase",    "calculation_type": "item_purchase_cost" }
  ]
}
```

**Term shapes — the columns are exclusive, and sending the wrong pair is refused twice:**

| `calculation_type` | `percent_value` | `fixed_amount_minor` | Contributes |
|---|---|---|---|
| `percentage_of_expected_sale_price` | **required**, `0` – `999.999` | must be omitted/null | that percentage of the gross expected sale price |
| `fixed_amount` | must be omitted/null | **required**, `>= 0` | that amount verbatim |
| `item_purchase_cost` | must be omitted/null | must be omitted/null | the item's own purchase cost |

**At most one `item_purchase_cost` term per version.**

> ### Percentage terms are planning allocations, not tax
>
> This wording is binding on every surface you build.
>
> `percent_value` is applied to the **gross** expected sale price exactly as entered, with
> no conversion of any kind. It answers "how much of the expected selling price does
> management want to reserve for this category?" — **a percentage term must never be
> presented as computing the legally payable tax amount.**
>
> A term's name carries no calculation semantics: a term called "VAT reserve" at `15.00`
> on a 4,000 kr expected price reserves exactly 600 kr. It is not a VAT engine, and actual
> VAT treatment (including Swedish margin taxation, VMB) is outside this system entirely.
>
> Because the base is gross, a manager encoding a statutory 25 % VAT-on-net enters
> **20.00**. Put that translation in the field's help text — the base must be named
> explicitly at the point of entry, so it is done once by a human who understands it.
>
> Do not label these fields "tax", "VAT" or "moms" in your UI chrome. The manager may name
> an individual term whatever they like; the field label and any tooltip must not.

→ `200`

```json
{
  "cost_model_version": {
    "client_id": "cmv_01H…",
    "workspace_id": "ws_01H…",
    "effective_from": "2026-08-15",
    "effective_to": null,
    "currency": "swedish_krona",
    "created_at": "2026-08-15T10:00:00+00:00",
    "created_by_id": "usr_01H…",
    "updated_at": null,
    "updated_by_id": null,
    "terms": [
      {
        "client_id": "cmvt_01H…",
        "workspace_id": "ws_01H…",
        "cost_model_version_id": "cmv_01H…",
        "name": "VAT reserve",
        "calculation_type": "percentage_of_expected_sale_price",
        "percent_value": "20.000",
        "fixed_amount_minor": null,
        "created_at": "2026-08-15T10:00:00+00:00",
        "created_by_id": "usr_01H…",
        "updated_at": null,
        "updated_by_id": null
      }
    ]
  }
}
```

**Errors:**

| Identity | HTTP | When |
|---|---|---|
| `ITEM_COST_TERM_SHAPE_INVALID` | `422` | a term's columns do not match its `calculation_type` — the message names the type and the offending column |
| `ITEM_COST_TERM_NAME_TAKEN` | `422` / `409` | two terms in the version share a name |
| `ITEM_COST_PURCHASE_TERM_DUPLICATE` | `422` / `409` | more than one `item_purchase_cost` term |
| `ITEM_COST_MODEL_VERSION_EFFECTIVE_FROM_FUTURE` / `_REQUIRED` / `_NOT_AFTER_OPEN` | `422` | same date admission rules as basis versions |
| `ITEM_COST_CONCURRENT_MODEL_VERSION` | `409` | another writer opened a version first |

Validate term shapes client-side too — the editor should not let a user type a percentage
into a `fixed_amount` term at all.

### 6.2 `GET /cost-model-versions`

Query: `limit`, `offset`.

```json
{
  "cost_model_versions": [ { "…": "…", "terms": [ ] } ],
  "cost_model_versions_pagination": { "has_more": false, "limit": 50, "offset": 0 }
}
```

Each version carries its terms inline. The row with `effective_to: null` is live.

### 6.3 `DELETE /cost-model-versions/{client_id}`

`422` `ITEM_COST_MODEL_VERSION_IN_USE` when any evaluation references it — the same
history-preserving guard as basis versions.

---

## 7. Currency — the one cross-cutting trap

Three currencies must agree before any item can be evaluated: the **item's valuation**,
the selected group's **basis version**, and the workspace's **cost model version**. Any
mismatch produces the status `currency_mismatch` and **no evaluation at all**.

There is no conversion anywhere in the system, and none is planned. In practice this means
a workspace can only price items in its configuration's currency.

Consequences for the settings UI:

- Default the currency selector on both version forms to the currency already in use, and
  make changing it a deliberate act with a warning.
- When `GET /configuration-status` shows a category evaluable but items still report
  `currency_mismatch`, the mismatch is between the configuration and the item's price —
  surface which pair disagreed from the `ITEM_COST_CURRENCY_MISMATCH` message, which names
  both sides.

---

## 8. Suggested build order

1. **Settings landing** — call `GET /configuration-status`; show one card per category
   plus a workspace-level cost-model card. Each card is done / needs-attention with
   `first_failure` as the explanation.
2. **Cost group create + section membership** — creation with the category selector, then
   the section picker excluding already-grouped sections.
3. **Basis version form** — date bounded at today, all four numeric fields required, the
   derived rate shown read-only in the response, history rendered as a timeline.
4. **Cost model editor** — a repeating term row whose available fields switch on
   `calculation_type`, with the planning-allocation help text on `percent_value`. Load the
   current version's terms as the starting point for the next version; posting replaces.
5. Only then does the operational handoff's pricing screen have anything to show.

## Validation notes

- Backend validation run: full suite green at the phase-9 checkpoint; role gates,
  admission rules and both conflict paths are covered by integration tests.
- Suggested frontend validation: on a fresh workspace, walk steps 1–4 and confirm every
  category card flips to evaluable; then attempt each refusal deliberately (duplicate
  category, future `effective_from`, malformed term, delete an in-use version) and confirm
  your error handling reads the leading token rather than the sentence.

## Trace links

- Living docs: `backend/docs/domains/item_economics/` (`README.md`, `api.md`, `events.md`, `states.md`)
- Operational half: `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`
- Route table: `backend/app/beyo_manager/routers/README.md`
