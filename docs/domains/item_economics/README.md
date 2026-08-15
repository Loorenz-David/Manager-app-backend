# Domain: Item Economics

## Responsibility

Owns the money side of an item's work: what a manager expects to sell it for, what the
workshop is allowed to spend producing it, and how much of that allowance the work has
actually consumed.

It does **not** own task steps, step time, or worker pay. It **reads** the step-time
rollups the task-steps domain maintains, and it never writes them.

---

## The one thing to understand first

The domain turns one price into one **time allowance**, through a fixed chain:

```
expected sale price          (entered by a manager, snapshotted at commit)
        ↓  subtract the configured allocation terms
production budget            (integer minor units)
        ↓  ÷ cost per productive worker-minute
allowed worker-minutes       (the aggregate economic constraint)
        ↓  compare against WORKING seconds already recorded on the task's steps
consumed / remaining / variance
```

Every link is computed in exactly one place — `domain/item_economics/calculator.py`. No
service does money, rate or minute arithmetic inline. A value that is not a calculator
output is not a derived economic value.

The chain runs against a **committed evaluation**, which is an immutable snapshot of
every input it used. Changing a cost model, a cost basis, or the item's price never
alters a committed evaluation; a new decision supersedes the old row and the old row
stays readable forever.

---

## The two cost numbers — they are different numbers on purpose

This is the single most common way to get this domain wrong.

`task_steps.total_cost_minor` (salary-priced, working **+ paused**, compensation's
remit) and `item_cost_results.consumed_cost_minor` (allowance-priced, working only)
answer different questions and differ for the same episode by construction.

Concretely:

| | `task_steps.total_cost_minor` | `item_cost_results.consumed_cost_minor` |
|---|---|---|
| Owned by | worker compensation | item economics |
| Priced with | the worker's salary rate | the workshop's cost per productive worker-minute |
| Counts | working **and paused** seconds | working seconds only |
| Question it answers | "what did this labour cost us in wages?" | "how much of this item's production budget has the work eaten?" |

They diverge because the paused seconds are real wage cost but are not production
capacity the budget bought. Reconciling them is not a task anyone should attempt:

- they never appear in the same serialized object;
- no item-economics payload carries a money field sourced from `TaskStep`;
- no step or task payload embeds an economics money field;
- they are never summed, differenced, compared or reconciled anywhere in code, and no
  query projects them into one column.

A structural test asserts the two payload families' money-key sets are disjoint. If you
find yourself adding one to the other's payload, that test is the thing telling you the
design does not want it.

---

## Percentage terms are planning allocations, never tax

A cost-model term with `calculation_type = percentage_of_expected_sale_price` applies its
`percent_value` to the **gross** expected sale price, exactly as entered — no conversion
of any kind.

**Presentation rule (binding on API field docs, the living-docs page, and every frontend
surface): a percentage term must never be presented as computing the legally payable tax
amount.** The domain answers "how much of the expected selling price does management want
to reserve for this economic category?", never "what tax amount must be declared for this
sale?".

A term's **name carries no calculation semantics**. A term named "VAT reserve" with
`percent_value = 15.00` on a 4,000 kr expected price reserves exactly 600 kr; it is not a
statutory VAT engine. Actual VAT treatment — including Swedish margin taxation (VMB) for
qualifying second-hand goods — is an accounting concern outside this domain.

Because the base is the gross price, a manager encoding a statutory 25 % VAT-on-net as a
reserve enters **20.00**. The base is named explicitly wherever the field is documented,
so that translation is done once, by the manager, at term setup.

---

## Unknown is never zero

An absent input produces a named refusal or `null` — never `0`. An item with no price is
not an item worth nothing; a task with no committed evaluation has no budget, not a
budget of zero.

The concrete rule: for every status except `ok` and `infeasible`, the status payload's
numeric fields are `null`. Never `0`, never omitted. `percent_consumed` is `null` for
`infeasible` too. The one carve-out is the valuation endpoint's `preview` key, where the
computable preview state (`not_evaluated`) carries fully computed
`production_budget_minor` and `allowed_worker_minutes` — see [api.md](api.md).

Consumption is the exception that proves the rule: a task with no steps consumes `0`, and
there `0` is a true statement about the work, not an inferred input.

---

## Vocabulary

**Worker-minutes.** The allowance is an aggregate quantity of worker-minutes. Worker count
and section count appear nowhere in the calculation. "Minutes per worker" is banned from
schema, API names, payload keys, docs and test names — it describes a different quantity
this domain does not compute.

**Episode.** One task is one economic episode for its PRIMARY item. An item returning on a
later task is a new episode with its own evaluation and its own result row; results never
merge across tasks.

**Committed vs projection.** A committed evaluation carries operational meaning. A
projection answers "what if" and is read by nothing — not worker surfaces, not analytics,
not the result. Promotion creates a new committed evaluation; it does not mutate the
projection.

---

## Entities

### `ProductionCostGroup` — a named pipeline of working sections

Prefix `pcg` · `production_cost_groups`

| Field | Type | Description |
|---|---|---|
| `client_id` | prefixed ULID | Primary key and stable public identifier |
| `workspace_id` | prefixed ULID | Owning workspace |
| `name` | string | Unique per workspace among non-deleted rows |
| `major_category` | `ItemMajorCategoryEnum` | `wood` or `seat`; **one active group per (workspace, category)** |

The category is what selects the group for an item — see "Business rules". It cannot be
changed once any basis version exists.

### `ProductionCostGroupSection` — group membership of a working section

Prefix `pcgs` · `production_cost_group_sections`

A working section belongs to at most one active group. Membership is added and removed by
setting `removed_at`, never by deleting the row.

### `ProductionCostBasisVersion` — one effective-dated version of a group's cost basis

Prefix `pcbv` · `production_cost_basis_versions`

| Field | Type | Description |
|---|---|---|
| `effective_from` / `effective_to` | date, nullable | Half-open window; `effective_to IS NULL` is the open row |
| `fixed_monthly_cost_minor` | integer minor units | The group's monthly production cost |
| `currency` | `ItemCurrencyEnum` | |
| `monthly_paid_hours` | `Decimal` | |
| `planning_utilization_percent` | `Decimal` | Share of paid hours that is productive capacity |
| `cost_per_worker_minute_minor` | `Decimal` | **Derived and persisted** — never accepted from a request |

One open basis version per group. Creating a new one closes the predecessor.

### `CostModelVersion` + `CostModelTerm` — the workspace's allocation assumptions

Prefixes `cmv` / `cmvt` · `cost_model_versions`, `cost_model_terms`

One open model version per workspace. A version is replaced whole; terms are never edited
in place. Term types:

| `calculation_type` | Carries | Amount |
|---|---|---|
| `percentage_of_expected_sale_price` | `percent_value` | percentage of the gross expected sale price |
| `fixed_amount` | `fixed_amount_minor` | copied verbatim, no arithmetic |
| `item_purchase_cost` | neither | the evaluation's `purchase_cost_minor` |

At most one `item_purchase_cost` term per version. Any other combination of
NULL/NOT NULL is rejected at term creation *and* again by the calculator before use.

### `ItemValuation` — the item's current price/cost record

Prefix `ival` · `item_valuations`

| Field | Type | Description |
|---|---|---|
| `expected_sale_price_minor` | integer minor units, nullable | |
| `purchase_cost_minor` | integer minor units, nullable | |
| `currency` | `ItemCurrencyEnum` | Not null |
| `superseded_at` / `superseded_by_id` | | Set when a newer valuation replaces this one |

Immutable price history: a change writes a **new** row and supersedes the old one. At most
one current (non-superseded, non-deleted) valuation per item. At least one of the two
amounts must be present.

Superseded rows are never deletable. Deleting the *current* row is the escape hatch for a
mistaken entry, and deleted rows are hidden from the history read.

### `ItemCostEvaluation` — one economic decision (or scenario) for one episode

Prefix `ice` · `item_cost_evaluations`

Carries `kind` (`committed` | `projection`), the price inputs, the full configuration
snapshot (`fixed_monthly_cost_minor_snapshot`, `monthly_paid_hours_snapshot`,
`planning_utilization_percent_snapshot`, `cost_per_worker_minute_minor_snapshot`), the
derived `production_budget_minor` and `allowed_worker_minutes`, the provenance ids, and
`calculation_version`.

At most one current committed evaluation per task. Committed rows are never deletable;
projections are.

### `ItemCostEvaluationTerm` — snapshot of one term line as applied

Prefix `icet` · `item_cost_evaluation_terms`

The term's name, type, `percent_value` / `fixed_amount_minor` as they were, and the
resulting `amount_minor`. The budget sums these rows, never the live term rows.

### `ItemCostResult` — the episode's actuals

Prefix `icr` · `item_cost_results`

One row per task (`unique (task_id)` is the idempotency key). Carries
`actual_worker_seconds`, `actual_worker_minutes`, `consumed_cost_minor`,
`variance_worker_minutes`, `variance_cost_minor`, the `task_state_snapshot` and
`task_closed_at` the row was computed at, `calculation_version` and `computed_at`.

The row is **recomputed and SET at every episode boundary**, not written once. See
[states.md](states.md).

---

## Business rules

- **A group is selected by the item's major category.** The item's denormalized
  `item_major_category_snapshot` resolves to `wood` or `seat`; the workspace's active
  group for that category is the one used. An unresolvable category is
  `item_missing_major_category` — a refusal, not a fallback.
- **The evaluation's currency is the valuation's currency.** There is no other source: no
  request carries one, no workspace default exists, and no fallback is permitted. The
  valuation, basis version and model version currencies must be equal; any inequality is
  `currency_mismatch` and no evaluation is produced. No conversion happens anywhere — no
  rate source exists in this system.
- **Nothing is written before the calculator succeeds.** Every commit-path refusal is a
  translation from the resolved status to a named error identity, checked before any row
  is written.
- **Snapshots are written only from calculator outputs.** `cost_per_worker_minute_minor_snapshot`
  is *recomputed* from the three snapshot inputs, never copied from the basis version —
  that is what makes a stored evaluation re-derivable from itself.
- **A committed evaluation is re-derivable from its own rows.** Given only an evaluation
  row and its term rows — dereferencing no foreign key, reading no live configuration —
  the rate snapshot, every term amount, the budget and the allowance reproduce exactly.
  Reads run that re-derivation and log an integrity-check failure on mismatch; the read
  still renders.
- **`calculation_version` is the contract's identity.** Stored rows are never recomputed.
  A re-derivation whose version differs from the current one skips the comparison rather
  than failing it.
- **Consumption is WORKING seconds only**, summed over the task's non-deleted steps,
  always read from the step rollups and never recomputed from step state records. Paused
  and ended-shift time do not count. Deleting a step removes its time from the episode,
  which is the only way an episode's consumption can decrease.
- **`variance_cost_minor` and `variance_worker_minutes × rate` are two independent
  quantities** and may differ by a few minor units. This is correct and deliberately
  unreconciled.
- **Money is visible to ADMIN and MANAGER only.** WORKER and SELLER see minutes and
  percentages. This is a separate query service with a serializer that has no monetary
  keys at all, not a flag on the manager serializer — see
  [api.md](api.md).
- **Only the PRIMARY item carries economics.** RELATED items on a task carry none.

---

## Relationships to other domains

| Domain | Relationship |
|---|---|
| Tasks & steps | A task is the economic episode. This domain reads the task's state, its PRIMARY item binding and its steps' `total_working_seconds`; it writes nothing there except a task history entry when an evaluation is committed. |
| Items | The item is what gets priced. Item CRUD carries no money fields; prices live on `item_valuations` and change only through this domain's valuation endpoint. |
| Working sections | Sections are grouped into a production cost group, which is what the group's cost basis prices. |
| Analytics | The result row is written by the analytics worker's `process_item_cost_result` handler, riding the existing outbox → `queue:analytics` pipeline. |
| Worker compensation | Deliberately decoupled. Salary figures are not read and the production cost basis is configured independently. See "The two cost numbers". |
| Audit & history | Configuration and evaluation writes record audit events; a commit also records a TASK history entry. |

---

## Files in this domain

| Layer | Location | Responsibility |
|---|---|---|
| Router | `routers/api_v1/item_economics.py` | All 23 endpoints, role gates, request bodies |
| Domain | `domain/item_economics/calculator.py` | The whole calculation contract — the only place money/rate/minute arithmetic happens |
| Domain | `domain/item_economics/configuration.py` | Category → group → basis → model selection, and the item-readiness precedence |
| Domain | `domain/item_economics/enums.py` | Term calculation types, evaluation kind, `EconomicsStatusEnum` |
| Domain | `domain/item_economics/serializers.py` | Payload shapes, including the money-free worker variants |
| Commands | `services/commands/item_economics/` | Cost groups, sections, basis versions, model versions, valuations, evaluations, projections, promotion |
| Commands | `services/commands/item_economics/_common.py` | The valuation-chain writer and the preview-input loader — shared, never duplicated |
| Queries | `services/queries/item_economics/` | Configuration status, listings, valuation history, budget status (manager and worker services), evaluations, lifetime economics |
| Worker | `services/tasks/analytics/process_item_cost_result.py` | Recompute-and-SET of the result row |
| Models | `models/tables/item_economics/` | The nine tables |

---

## Known gaps in this domain

Real, current, and deliberately unfixed.

- **The result row is not produced for an unstarted episode.** A replayed or
  operator-re-emitted event for a task in `PENDING`, `ASSIGNED` or `STALLED` logs and
  returns, writing nothing. That is intentional — see [states.md](states.md) — but it
  means "no result row" is ambiguous between "no committed evaluation" and "the episode
  never started".
- **The workspace can only evaluate items priced in its groups' basis currency.** An item
  in another currency gets `currency_mismatch` and no evaluation, forever, until either
  the item or the configuration changes. There is no conversion and no plan for one.
- **Section-level allocation does not exist.** The allowance is one aggregate number for
  the whole episode; nothing apportions it across the sections that will do the work.
- **Ambiguous group selection is structurally unreachable** under the one-active-group-per-category
  index, and is retained only as the classifier's total-order defence. If you ever see
  `not_configured_ambiguous_cost_group` in production, the index is gone.

---

## Keeping this document true

**This is a living document. It describes what the system does now, not how it came to.**

Any change that alters the *logic* of this domain must update the affected file in this
folder **in the same change** — not afterwards, and not in a separate document. That
includes adding or changing a status value, an entity, an invariant, a calculation rule,
an endpoint, a request or response shape, who may see money, or moving a file listed in
the table above.

Changes that do **not** require an update: behaviour-preserving refactors, performance
work, and test-only changes.

Do not add implementation history, migration steps, or rationale for past decisions here.
Those belong elsewhere. This file answers *what is true* and *where to look*.
