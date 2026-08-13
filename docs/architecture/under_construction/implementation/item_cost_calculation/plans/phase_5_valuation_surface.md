# Phase 5 — Valuation surface

```
plan: phase 5
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Ship the specialized item-valuation surface (card 2 / R1-3): the superseding
valuation command with its chain and race, validation, history read, guarded
deletes, and the ephemeral economic preview (§11A.5). **NOT in this phase:** the
§10.2 legacy migration (phase 6), the §7.2 mirror rule (phase 7 — it is part of the
commit transaction), any evaluation or result row.

## Read first

1. `master_plan.md` §§5, 6 (registry: routes, identities), 9 (P-B), 10.
2. Intention §4.7A (table, INV-V1/V2), §7.5 (valuation deletion rules), §7A.1–7A.2
   (the valuation chain has all three steps S1/S2/S3), §11 ("Set item valuation"),
   §11A.4–§11A.5 (status vocabulary, preview), §6A.9 (currency), R-9.
3. Contracts: `06_commands`+local, `07_queries`+local, `09_routers`,
   `28_roles_permissions`, `46_serialization`+local (+ core).

## Dependencies

Phase 4 APPROVED (preview needs the calculator + the §7A.5 classifier + config
loading).

## Files expected to change

- `app/beyo_manager/services/commands/item_economics/set_item_valuation.py`,
  `delete_item_valuation.py` + additions to `requests/__init__.py`
- `app/beyo_manager/services/queries/item_economics/get_item_valuation_history.py`
- `app/beyo_manager/domain/item_economics/serializers.py` (valuation + preview
  serialization; started here, extended in later phases)
- `routers/api_v1/item_economics.py` (valuation routes per registry §6.5);
  `routers/README.md` mirror rows
- tests

## Implementation tasks (ordered)

1. `set_item_valuation` (ADMIN/MANAGER): validates per §4.7A (≥1 amount —
   `ITEM_COST_VALUATION_AMOUNT_REQUIRED`; non-negative amounts and required currency
   at the request layer), then writes through the valuation chain **S1→S2→S3**
   (§7A.1) in one transaction; `IntegrityError` from INV-V1 surfaces as
   `ConflictError ITEM_COST_CONCURRENT_VALUATION` (§7A.2 — never caught/retried).
2. Response embeds the **preview** (§11A.5): a pure computation from the posted
   valuation + current configuration via the §7A.5 classifier and the calculator —
   `EconomicsStatusEnum` + budget/allowed when computable, `null` numerics
   otherwise (P-B). The preview has no `client_id`, persists nothing, supersedes
   nothing, and **creates no evaluation row**.
3. `delete_item_valuation`: the **current** row only, soft delete → item returns to
   "unvalued"; a superseded row is never deletable
   (`ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE`, §7.5).
4. `get_item_valuation_history`: full chain, newest first; rows are immutable
   after creation (INV-V2) — no update surface exists anywhere.
5. Routes + role gates per registry §6.5.

## Acceptance criteria

**C1 — chain order (intention test 17, valuation row):** setting a second valuation
for an already-valued item succeeds; afterwards exactly one row satisfies INV-V1's
predicate and the superseded row carries `superseded_at` + `superseded_by_id` of the
new row. (This row fails outright under insert-before-close — its reason to exist.)

**C2 — INV-V1 race (intention test 12):** two sessions past S1 both attempt S2 →
exactly one current row afterwards + loser's exact
`ITEM_COST_CONCURRENT_VALUATION`; the DB conflict path, not the pre-check.

**C3 — validation (intention test 11), request layer AND DB CHECK (both paths per
row):** expected-only OK; cost-only OK; both OK; neither →
`ITEM_COST_VALUATION_AMOUNT_REQUIRED`; negative expected → 422 and CHECK violation;
negative cost → 422 and CHECK violation; missing currency → 422 and NOT NULL
violation.

**C4 — immutability & deletion (§7.5):** superseded row delete →
`ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE`; current row delete → item unvalued
(history retained; subsequent status reads `item_unvalued`); re-set after delete
starts a fresh current row.

**C5 — preview rows (§11A.5, each fixture sole-predicate; numeric fields `null`
for every non-computable status — P-B):**
- unconfigured workspace (no group) → `not_configured_no_cost_group`, nulls;
- configured + valuation with expected price → `not_evaluated` with exact
  budget/allowed preview values (calculator-derived);
- configured + cost-only valuation → `item_missing_expected_price`, nulls;
- valuation currency ≠ basis currency → `currency_mismatch`, nulls;
- model carries an `item_purchase_cost` term + valuation without purchase cost →
  `item_missing_purchase_cost`, nulls.
Every preview row also asserts `item_cost_evaluations` count unchanged (creates
nothing) and that the valuation row itself WAS written (the command's own effect).

**C6 — history:** after three supersessions, history returns all rows in order with
exactly one current; byte-identical re-read (no mutation on read).

## Notes

- The valuation is the ONLY source of an evaluation's currency (§6A.9 step 2) —
  the preview must never invent a fallback.
- An item with no current valuation is **unvalued** — an explicit state, never
  zero (R-9); the preview payload for it is status-only.
- Teardown discipline (rule 11½) for committed fixtures.
- Archgraph: delta = the valuation command/endpoint nodes; orient on
  `table-task-item` + phase-2 table nodes.

- **Forward item (phase-4 projection, N7 consumption half):** the valuation
  preview divides a budget by the rate — a criterion must prove it consumes the
  PERSISTED `cost_per_worker_minute_minor` (quantized, 4 dp), never a raw
  re-division from the basis inputs (fixture from the Q2-tie family where the
  two differ).

- **Live-data note (4B projection N-d):** the dev DB holds 37 items with NULL
  `item_major_category_snapshot` (225 wood / 193 seat) — `item_missing_major_category`
  is a LIVE preview outcome, not a defence row; the preview's criteria include it
  with P-B null-numerics.

- **Forward items (phase-4 re-reviews, same test files this phase touches):**
  when this phase edits the item-economics request/status tests, close in
  passing: (r2 N4) assert the persisted 4-dp **scale** (`Decimal.__eq__` treats
  `5.4` == `5.40` — compare `str()` or `as_tuple().exponent`); (r2 N5)
  parametrize C8's six looped fixtures into named rows (P-G(b)/P-I naming);
  (r3 N8) the three accept-boundary rows are ONE fixture with three names —
  give each row a payload that moves only its own field off the shared base;
  (r3 N9) drop the duplicated `percent=1000` reject row
  (`test_term_request_rejects_each_excluded_numeric_boundary[percent-over-max]`
  duplicates `…_out_of_range_numeric_field[percent-over-numeric-bound]`).

## Round-0 projection amendments (2026-08-13, coordinator-routed — GOVERNING where they conflict with the text above)

The r0 projection ledger (16 rows, handoff
`2026-08-13_phase5_projection_r0_handoff.md`) is fully routed. Owner cards
answered: **R13-1** (preview numerics under a dedicated key; first save =
version 1, no confirmation) and **R13-2** (deleted rows hidden from history) —
see intention §11A.5(a)–(d) and `planning/owner_decisions.md`.

**L1 — the selection resolver (task 2 rework):** build the registered
`resolve_economics_selection(...) -> EconomicsSelection` (frozen dataclass:
`status, selected_group, basis_version, cost_model_version`) in
`domain/item_economics/configuration.py`, and REIMPLEMENT
`resolve_economics_configuration` as `resolve_economics_selection(...).status`
(they can never disagree; named mutation: making the two diverge on the
selected group must redden). The preview consumes the selection, never
re-derives it. The loader (groups, basis versions, model versions AND the
selected model's non-deleted terms) lives in the command, not the pure module.

**L2 — the item-status resolver:** registered `ITEM_READINESS_PRECEDENCE`
(explicit ordered sequence `ITEM_UNVALUED → ITEM_MISSING_EXPECTED_PRICE →
ITEM_MISSING_PURCHASE_COST → CURRENCY_MISMATCH → NOT_EVALUATED`) + resolver
`resolve_item_economics_status(...)` in `configuration.py`, consumed by the
preview (phase 8 reuses it). `item_missing_purchase_cost` fires ONLY when the
selected model version carries an `item_purchase_cost` term (§11A.4 row 7).
Carry 4B's B6-shaped structural probe both ways: permuting
`EconomicsStatusEnum` declaration order changes nothing; permuting the
SEQUENCE reddens.

**L3 — preview numerics (R13-1, supersedes C5's preamble narrowing):** the
response envelope is `{"item_valuation": …, "preview": …}`. Inside `preview`,
`not_evaluated` (the computable state) carries computed
`production_budget_minor` + `allowed_worker_minutes`; every other status
carries `null` numerics (P-B as refined). The preview never merges with
committed figures.

**L4 — C5 rewritten as the 12-value enumeration (P-V):** one row per §11A.4
value with an exact outcome or a recorded reachability judgment, parametrize
ids naming the authority row (`status-row-7-missing-purchase-cost`), each
fixture sole-predicate. Judgments to record, not test: `ok`/`infeasible` are
task-scoped group-1 values (out of the item-scoped preview — state it);
`not_configured_ambiguous_cost_group` is INV-G3-unreachable via the DB (pure
defence, covered by 4B's V3). `item_unvalued` gets its row through the DELETE
response (L6). `item_missing_major_category` gets a live row (53 of 471 items
today — N-d re-measured).

**L5 — C4 row 1 resolved as option (a), P-S:** the surface stays item-scoped
(exactly the three §6.5 routes — no new route);
`ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE` is proven by calling the command
directly with a superseded row's client_id, and the reachability judgment is
recorded in the criterion.

**L6 — DELETE returns the status-only preview (§11A.5(d)):** task 3 declares
it; C4's "subsequent status reads `item_unvalued`" is arbitrated by the DELETE
response itself.

**L7 — the ≥1-amount rule raises OUTSIDE pydantic:** in the parser function
after `_parse` (or the command), so
`ITEM_COST_VALUATION_AMOUNT_REQUIRED` is the exact LEADING token (the shipped
`_parse` prefixes pydantic messages with the field name — verified). C3
asserts `startswith`. Negative amounts / missing currency stay pydantic-side
(no identity).

**L8 — Files list corrected:** ADD `domain/item_economics/configuration.py`
(L1/L2), `services/commands/item_economics/_common.py` (INDEX_IDENTITIES +=
`"uix_item_valuations_current": "ITEM_COST_CONCURRENT_VALUATION"`),
`tests/unit/routers/api_v1/test_item_economics_router.py` (the P-R harness
gains 3 routes), master_plan §6.4/§6.5 (already applied by the coordinator).
All paths carry the `app/beyo_manager/` prefix.

**L9 — audit criterion:** `item_valuation.created` / `item_valuation.deleted`
are now REGISTERED (§6.4). New criterion in phase-4 C11's shape: each command
writes exactly one registered event, exact strings, retention mutation named.

**L10 — C3 scoped to the request layer:** the DB-CHECK half shipped in phase 2
(`test_item_valuation_amount_and_currency_boundaries`, six ids — cite them);
phase 5 builds only the request-layer rows + the L7 identity row.

**L11 — C2 harness named (P-T):** the phase-4 gate transplants —
two sessions from `database._session_factory()`, the command's `audit` call
monkeypatched into an `asyncio.Event` gate, ALL waits bounded
(`asyncio.wait_for(..., timeout=0.3)`), FK-ordered teardown
(`item_valuations → audit_logs → items → users → workspaces`; no self-FK
special-casing — L18 probe), "exactly one current row afterwards" count.
**Both race paths enumerated:** (i) pre-existing current valuation (loser
blocks on the row lock, rowcount 0 after winner commits, S2 conflicts);
(ii) FIRST valuation (both S1s rowcount 0 without blocking; the INDEX alone
arbitrates). If the command has no post-S3 `audit` call, the plan's seam
declaration must name what is used instead.

**L12 — the persisted-rate pin becomes a criterion (P-Q):** fixture
`fixed=100000, hours=160.00, util=80.00` → persisted Q2 rate `13.0208`
(raw `13.020833…`), budget `1_000_000` → allowance from persisted rate
**76800.20** vs re-divided **76800.00**. Named mutation: replace the
persisted-rate read with `calculate_cost_per_worker_minute(fixed, hours,
util)` — must redden exactly this row.

**L13 — history pinned (R13-2):** rows WHERE `is_deleted = false`, ordered
`created_at DESC, client_id DESC` (total order, charter rule 5); "exactly one
current" = INV-V1's predicate (`superseded_at IS NULL AND is_deleted =
false`); the delete-then-reset fixture (which has TWO `superseded_at IS NULL`
rows) is the row that proves the predicate.

**L14 — prose corrections:** the dependency gate is **4B APPROVED** (closed
`377d0b9`); "§7A.5 classifier" reads "§7C.2 selection + §7A.5 rows 3–6 per
selected group"; Read-first gains intention §7C, master §6.3/§6.4, §9 P-A…P-Z.

**L15 — the snapshot-reader structural row ships HERE (P-J/P-X):** no module
under `domain/item_economics/` or `services/**/item_economics/` reads
`item_major_category_snapshot` except through `resolve_major_category` — the
test names its inspected source; named mutation: inlining a snapshot read in
the preview must redden it. (§6.5's stale "4B guards this" corrected.)

**L16 — three currency rows (§6A.9):** valuation≠basis, valuation≠model,
basis≠model — each fixture varies only its pair; message assertions name each
side individually (P-O).

**Notes carried:** L17 N-d re-measured (53 NULL / 225 wood / 193 seat of 471;
zero non-vocabulary, zero deleted); L18 no self-FK teardown special-casing
(probe: single-statement DELETE of a linked chain succeeds); L19 forward-note
N5 says FIVE looped C8 fixtures, not six; L20 rename the router-harness lists
to `…every_item_economics_route…` (or add a second list) when adding
`put-valuation`/`get-valuations`/`delete-valuation`; L21 `TermSnapshot`'s
`amount_minor` Protocol field is absent on live `CostModelTerm` rows —
runtime-safe (only type/percent/fixed are read); do NOT "fix" it; L22 phase-2's
`both-null` row has no named constraint arbiter — next touch of that file may
add `match="ck_item_valuations_amount_present"`.

**Delegations (granted):** envelope key names fixed above (L23's first item is
now pinned by R13-1); preview computed inside or outside the command's
transaction — implementer's choice, stated in the handoff; S1 optionally
preceded by a SELECT of the current row; unknown item client_id → `NotFound`
per phase-4 `_common.get_group` precedent.

## Review log

(append-only)
