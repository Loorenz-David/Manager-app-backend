# Intention: inline valuation versioning on task creation

```
status: SHAPED — 0 owner cards open (D17, D18, D-AUTH settled); round 2 corrects
        HC-1 to FOUR files after the implement-r1 blocker; next gate = implement r1b
role: intention (pipeline root artifact)
shaped_from: owner conversation of 2026-08-19
date: 2026-08-19
round: 2
```

---

## 1. Objective & hard constraints

Today, sending an inline price on task creation for an item that **already has a current
valuation** is rejected outright. That was correct while inline pricing was a first-time
convenience. The owner wants it to become an ordinary re-pricing act: **if the values
differ, write a new valuation version credited to the person creating the task; if they
are the same, do nothing.**

**Hard constraints:**

- **HC-1 — Authorized v1 change (owner, 2026-08-19).** This deliberately changes closed
  item-cost v1 behaviour and **retires a registered error identity**. Exactly FOUR files
  may change (corrected from three — see the round-2 note below):
  1. `app/beyo_manager/services/commands/tasks/create_task.py` — the guard at `:324-342`
     becomes the compare-and-version branch
  2. `app/tests/unit/docs/test_item_economics_handoff_accuracy.py` — remove
     `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` from the registered-identity set (`:97`)
  3. `app/tests/integration/services/commands/item_economics/test_phase8b_inline_task_prices.py`
     — the rejection test becomes the versioning tests
  4. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`
     — §9.1 rewritten and validation step 4 rewritten (see §3.1)

  **HC-1 correction, round 2 (coordinator, 2026-08-19, implement r1 blocker).** Round 1
  enumerated THREE files on a verification that was wrong: the grep behind it was run from
  `backend/app/`, so `backend/docs/` was never searched. The identity **is** published, in
  two live places — an example error response at `:682` and a validation step at `:725`,
  inside a titled subsection **§9.1 "The refusal — an existing item that already has a
  price"** whose whole body asserts the behaviour being retired. Removing the registry
  entry without touching the document turns
  `test_no_document_names_an_unregistered_error_identity[operational]` red, which is
  exactly what the implementer hit.

  **No new owner card is raised.** D-AUTH already authorized retiring the identity;
  removing it from the document that publishes it is entailed by that decision, not a
  separate one. Same precedent as `simple_production_budget_division`'s HC-1a extension
  (3 → 4 artifacts, same rationale, recorded for provenance). The implementer was correct
  to stop rather than exceed the perimeter — the constraint worked.

  **Verified 2026-08-19, repo-wide from `backend/`:** four live files, plus references in
  `item_cost_calculation`'s planning and archive documents, which are **provenance of a
  decision that was true when written and MUST NOT be rewritten**. `Application_contracts`
  carries no reference.
- **HC-2 — One valuation writer.** `write_item_valuation_chain_in_session`
  (`services/commands/item_economics/_common.py:117`) remains the only code that
  supersedes and creates a valuation. It already sets `superseded_at`,
  `superseded_by_id` and `created_by_id` correctly. **This phase adds a decision in
  front of it, never a second writer.**
- **HC-3 — No schema change.** No migration, no new column, no
  `CALCULATION_VERSION` bump. Behaviour only.
- **HC-4 — The trigger is unchanged.** The branch still fires only when
  `request.item` carries at least one of `expected_sale_price_minor` /
  `purchase_cost_minor` (`create_task.py:317-323`). A task created with no inline price
  touches no valuation, exactly as today.

## 2. Grounding (verified 2026-08-19, all paths read this session)

- **The guard being replaced:** `create_task.py:324-342` — loads the current valuation
  and raises `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` if one exists. Fires before commit,
  so the whole task creation rolls back today.
- **The writer:** `_common.py:117-169`. Takes the values verbatim; supersedes the current
  row; links `superseded_by_id`; credits `created_by_id`. **It does not merge** — a field
  passed as `None` is stored as `None`.
- **The existing valuation endpoint** (`set_item_valuation.py:71-80`) passes request
  values straight through, so it replaces wholesale too. That is tolerable there because
  it is a deliberate re-pricing act with its own request shape; it is **not** the model
  this phase follows (see D17).
- **Currency is already mandatory alongside a price:** the task request validator
  (`tasks/requests/__init__.py:56-61`) raises when a price is sent without
  `item.currency`. So the comparison always has a currency on both sides.
- **After the branch, `auto_commit_item_cost_evaluation_in_session` runs regardless**
  (`create_task.py:355-368`), inside a `try` that only logs on failure. So a new
  valuation produces a fresh evaluation and the production-time budget follows it; a
  no-op leaves the existing evaluation in place. A task can still be created with no
  evaluation at all — that surfaces as `not_evaluated`, unchanged.

## 3. Mechanism contract M1 — compare, inherit, version

When the trigger fires and the item **was not created by this request**:

1. **Load** the current valuation (`superseded_at IS NULL AND is_deleted = false`).
   If there is none → write the chain exactly as today. Done.
2. **Build the effective values** (D17 — inherit, never null by omission):
   - `expected_sale_price_minor` = the request's value if not `None`, else the current
     valuation's value
   - `purchase_cost_minor` = the request's value if not `None`, else the current
     valuation's value
   - `currency` = the request's `item.currency` (always present per HC-4/§2)
3. **Compare** the effective triple against the current valuation's
   `(expected_sale_price_minor, purchase_cost_minor, currency)`.
   - **Identical → no-op.** Write nothing: no new row, no supersede, no audit event.
     The current valuation keeps its id, its `created_by_id` and its `superseded_at IS
     NULL`.
   - **Different → write the chain** with the effective triple, `created_by_id =
     ctx.user_id` (the task creator, D-credit).
4. The error identity `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` becomes **unreachable and
   is removed** from the code and from the docs-accuracy registry.

**Comparison includes currency (D18).** 400 EUR is not 400 SEK; ignoring currency would
leave an item priced in the wrong one, and the budget's own currency-equality check
(`calculator.py:376-383`) would then fail downstream with a less traceable status.

### 3.1 The document edit, specified (not left to the implementer)

Deleting the two lines is **wrong**: it would leave the handoff silent about what now
happens when an inline price meets a priced item, and would strand §9.1's closing "rule in
one line", which asserts the retired behaviour.

**§9.1 (`:675-691`) is rewritten**, title included, to state the new behaviour: the trio
now re-prices the item; a field omitted from the request keeps its current value (D17); a
resulting price that differs from what is stored writes a new valuation version credited
to whoever created the task; an identical one writes nothing at all. It must also keep the
one fact that survives unchanged — an existing item with *no* current valuation still
accepts the trio and starts a chain — and state the deliberate divergence from
`PUT /items/{id}/valuation`, which continues to replace wholesale (§5).

**Validation step 4 (`:725-726`)** is rewritten from "confirm the … path leaves no task
behind" to two checks: re-price an already-priced item with a **different** price and
confirm a new valuation version appears; repeat with the **identical** price and confirm
no new version appears.

Nothing else in that document changes. §9.2's auto-commit table is unaffected — it
describes what happens once a valuation exists, which this phase does not alter.

## 4. Properties

- **P-INHERIT** — a field omitted from the request never changes value. After the write,
  the omitted field equals what it was before.
- **P-NOOP** — identical effective values produce **zero** new rows: the current
  valuation's `client_id` is unchanged and its `superseded_at` is still `NULL`. Counting
  valuation rows before and after gives the same number.
- **P-CREDIT** — a new version's `created_by_id` is the user creating the task.
- **P-CHAIN** — the superseded row gets `superseded_at` set and `superseded_by_id`
  pointing at the new row (the writer's existing behaviour, asserted through this path).
- **P-TRIGGER** — with no inline price in the request, no valuation row is touched at
  all, whatever the item's state.

## 5. Non-goals

Merging semantics for the dedicated valuation endpoint (it keeps replacing wholesale —
different surface, deliberate act). Any change to `auto_commit`. Any change to the
twelve-value status vocabulary. Backfilling or repairing existing valuation chains.

## 6. Testing expectations

Charter standing rules apply; **MVP calibration** applies — this is a fifteen-line
behaviour change with no arithmetic, so no mutation ledger beyond the enumerated named
mutations below. Each row is a distinct fixture.

| # | Row |
|---|---|
| C1 | Existing item, current valuation, **both** prices sent and **different** → new version; old row superseded and linked; `created_by_id` is the task creator (P-CREDIT, P-CHAIN) |
| C2 | Existing item, current valuation, **identical** values → **no-op**: row count unchanged, same `client_id`, `superseded_at` still `NULL` (P-NOOP). **Named mutation: drop the equality check → C2 goes red.** |
| C3 | **Partial request, inherit**: current 400/1200, request sends purchase 450 only → new version is 450/**1200** (P-INHERIT). **Named mutation: pass the request value straight through → C3 goes red** (would store `expected_sale_price_minor = None`). |
| C4 | **Partial request that is effectively identical**: current 400/1200, request sends purchase **400** only → inherited 1200 makes the triple identical → **no-op**. The row C2 and C3 cannot both cover. |
| C5 | **Currency-only change** (D18): same amounts, different `item.currency` → new version. **Named mutation: compare amounts only → C5 goes red.** |
| C6 | Existing item with **no** current valuation → first valuation written, as today |
| C7 | Item **created by this request** + prices → unchanged first-valuation behaviour |
| C8 | **No inline price at all** on an existing priced item → zero valuation rows touched (P-TRIGGER) |
| C9 | The identity `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` appears **nowhere** in the package, and the docs-accuracy suite is green |

## 7. Owner decisions

Both settled 2026-08-19, verbatim in `planning/owner_decisions.md`: **D17** (inherit the
omitted field) and **D18** (currency counts as a difference). The owner also authorized
the v1 change itself (HC-1).
