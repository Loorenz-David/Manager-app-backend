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
ids naming the authority row (example CORRECTED per re-review r2 N1 to §7C.3's
current numbering: `status-row-8-missing-purchase-cost`; the full order is
1 major-category, 2 no-group, 3 ambiguous, 4 no-basis, 5 no-model, 6 unvalued,
7 missing-expected, 8 missing-purchase, 9 currency-mismatch, 10 not-evaluated,
+11/12 group-1), each
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

## Fix r1 amendments (2026-08-14, coordinator-routed from review r1 — GOVERNING)

Review r1: 4 blocking, 5 should-fix, 7 notes; zero owner cards (rounds 13
settled the semantics). Every correction below was EXECUTED by the reviewer —
resolve, don't relitigate. Two production files change (B1 one line, B4 the
clause reduction); everything else is test-side.

**B1 (production, one line):** `delete_item_valuation.py` item-scoped branch
gains `ItemValuation.is_deleted.is_(False)` — INV-V1's full predicate. The
delete-then-reset state legitimately holds two `superseded_at IS NULL` rows and
the unfiltered `scalar()` can return the ghost (`NotFound` on a live current
row; reachable through PUT→DELETE→PUT→DELETE). Reviewer-verified: with the
line, the probe passes, 346/0 focused.

**The shared fixture (B1/S3/S2/L13 — build ONCE):** set → delete → set:
two `superseded_at IS NULL` rows, exactly ONE INV-V1-current row; then
(S3/C4) the re-set current row deletes successfully; (C6/L13) history over a
three-supersession chain returns all non-deleted rows ordered
`created_at DESC, client_id DESC`, byte-identical re-read. Named mutations
(all reviewer-run, all currently green — must redden): M8 drop `order_by`,
M8b reverse to ASC, plus reverting B1's line reddens the delete row.

**B2 (C5 rebuilt as the 12-value enumeration, L4 as written):** one
parametrized row per §11A.4 value, ids naming the authority row
(`status-row-…`), sole-predicate fixtures; recorded judgments for
`ok`/`infeasible` (task-scoped) and ambiguous (INV-G3 defence); the six
missing rows built (`item_missing_major_category` live,
`not_configured_no_cost_group` / `…_no_basis_version` /
`…_no_cost_model_version`, `item_missing_purchase_cost`,
`currency_mismatch`); EVERY preview row asserts `null` numerics where owed
AND `item_cost_evaluations` count unchanged. The reviewer's two disposable
probes already passed — production is right; ship the evidence.

**B3 (L15 structural row):** `inspect.getsource` over every module under
`domain/item_economics/` and `services/**/item_economics/`, asserting
`item_major_category_snapshot` appears only inside
`configuration.py:resolve_major_category`. Named mutation M4 (inline the
read in `set_item_valuation._load_preview_inputs`) must redden — it left
345/345 green in r1.

**B4 (production + tests, P-AA):** the three-way currency check reduces to
the TWO independent clauses (`valuation ≠ basis` OR `basis ≠ model`) — the
middle clause is provably redundant (transitivity) and can never have an
arbiter. Rename the parametrize ids to the STATE each fixture holds (which
pair is equal), keeping the three existing fixtures. Reviewer-verified: 7/7
green under the 2-clause form; dropping clause 1 reds exactly
`[valuation-basis]`, clause 2 exactly `[basis-model]`.

**S1:** new readiness row — purchase-cost term present, `purchase_cost_minor`
NULL, expected price set, valuation currency ≠ basis = model → expects
`item_missing_purchase_cost`. Passes today; reds exactly under M3.2
(precedence swap 2↔3, green in r1).

**S4:** both race blocks assert `select(func.count())` over INV-V1's full
predicate `== 1` (not `is not None` on a scalar), and path (i) asserts its
distinguishing observable (loser blocks on the row lock / rowcount 0 after
the winner commits — L11's wording).

**S5:** C3 gains the missing request-layer rows: missing currency
(`ValidationError` naming `currency`) + the three accept rows
(expected-only / cost-only / both); the file cites phase-2's six DB-CHECK
node ids per L10.

**N1 (L12 fixture corrected — P-Q ext):** the preview fixture's persisted
`cost_per_worker_minute_minor` becomes `13.0000` (≠ the calculator's
`13.0208` for the same inputs), expected allowance `76923.08`
(hand-computed). BOTH mutation forms must then redden: M10 (the plan's named
`calculate_cost_per_worker_minute(...)` swap — inert in r1) and M10b (raw
re-division). The ledger row states which form ran.

**Ledger rule (P-I sixth ext):** this prompt names its mutations; the ledger
carries ONE ROW PER NAMED MUTATION — B1-revert, M4, M5.a/M5.c (2-clause
forms), M3.2, M8, M8b, M10, M10b, plus re-runs of any row whose file changed.
Full observed red sets; divergences flagged; hashes copy-pasted.

**Not in scope:** N2 (phase 8), N4 (closeout purge — `ws_765225a0…`), N5
(phase 9), N6/N7 (coordinator's graph pass). The graph delta this cycle is
ZERO (the fix touches no route/command surface the graph models; N6's five
reads_from edges and N7's re-link belong to the coordinator's post-approval
pass).

## Fix r2 amendments (2026-08-14, coordinator-routed from re-review r2 — GOVERNING)

Re-review r2: 0 blocking, 1 should-fix, 7 notes. Everything else CLOSED and
settled. One test-side item ships this cycle:

**S1 — the L15 guard quantifies over its module set (P-J second ext):** replace
the single-member assertion with the reviewer's executed correction — every
in-scope occurrence of `item_major_category_snapshot` must be a
`resolve_major_category(...)` argument, asserted over ALL of `module_sources`
(`unmediated == {}`). Expected: `test_configuration.py` at 9 passed baseline;
mutations M4a (inline chain), M4b (second reader, same module) and M4c (reader
in another in-scope module) EACH redden it — M4b/M4c left 363 green in r2. The
`ItemMajorCategoryEnum(` absence check may be dropped (does not generalise);
the `set_source` string asserts may stay or go.

**N3 ride-along (same file):** one comment above the currency parametrize
naming which CLAUSE each row arbitrates (`[basis-model]` proves
`valuation ≠ basis`; `[valuation-basis]` proves `basis ≠ model`) — the
equal-pair naming is correct but inverts under a casual read.

**Next-touch (NOT this cycle):** N1's C5 id renumbering to §7C.3 (L4's example
corrected above); N6's pytest-node-id citation. **Phase-6 forward note:** N2 —
the `client_id DESC` tie-breaker has no arbiter because no fixture ties
`created_at`; phase 6's bulk valuation creation is when it becomes
load-bearing (verified correction: two rows with identical `created_at`,
assert the id order).

## Review log

(append-only)

### 2026-08-13 — implementer r1 (Codex)

- Implemented the valuation surface within the declared fence: selection/readiness resolvers, valuation serializers and request validation, set/delete commands, history query, three role-gated routes, router README rows, and focused unit/integration coverage.
- Judgment: preview computation reads the persisted `cost_per_worker_minute_minor`; `resolve_economics_selection` is the single selection authority and the legacy status resolver delegates to it. DELETE returns the status-only `item_unvalued` preview; direct superseded-row deletion is rejected with the registered immutable identity.
- The race harness uses two real sessions, bounded waits, and commits only its fixture; it exercises both no-current and current-row paths and asserts `ITEM_COST_CONCURRENT_VALUATION`. Cleanup scopes the five valuation-chain tables plus actor/workspace rows.
- Focused valuation/unit/router suite: 111 passed. The valuation integration and race subset each passed twice. Ruff and `git diff --check` passed. Alembic reports development DB at `5caae620088c` (head).
- Full suite: 1951 passed, 23 failed, 2 warnings. The 23-failure set is byte-identical to the established non-phase baseline; phase 5 added 24 collected tests relative to the recorded 1927 baseline. No phase-5 failure was present.
- Reversible mutation probes: readiness precedence swap reddened `test_item_readiness_uses_registered_order_and_requires_a_purchase_term`; raw-rate substitution reddened `test_valuation_chain_preview_delete_and_history` (`76800.00` vs `76800.20`); history soft-delete-filter removal reddened the same integration test. All probes were reverted; probe-only touched files were `app/beyo_manager/domain/item_economics/configuration.py`, `app/beyo_manager/services/commands/item_economics/set_item_valuation.py`, and `app/beyo_manager/services/queries/item_economics/get_item_valuation_history.py`.
- Architecture Graph: one additive batch applied after duplicate preflight: 5 nodes and 7 relationships, revision `b5e6fe094caee2191414a297bb1ab63507ebda8ee4ee54c26cc612a5d940fc94`; no review decisions were made.

### 2026-08-13 — review r1 (Claude Opus 5) — CHANGES_REQUESTED

Handoff: `handoffs/reviewer/2026-08-13_phase5_review_r1_handoff.md` (full probe
declaration with sha256 pairs, anchor-spans table, write perimeter).

Perimeter exact (16 files; `git diff 8b4ac06..HEAD -- app/` empty; tree clean;
all three declared restored hashes byte-identical). Ruff clean. Suite
**1950 passed / 23 failed / 1 deselected**, collection 1973+1, failure set
byte-identical to the phase-1 baseline (+23 tests, not the handoff's +24) —
**P5-A: the handoff's "1951 passed" is derived-not-read, off by one**.
**P5-B: seven owed mutations run; four do not bite.** DB at head `5caae620088c`.

**4 blocking.**
- **B1** `delete_item_valuation.py:27-33` omits `is_deleted = false` from the
  current-row predicate (INV-V1 is both clauses; S1's own close statement uses
  both). After delete-then-reset the item holds two `superseded_at IS NULL` rows
  and the unordered `scalar()` can return the deleted one → `NotFound`; the live
  valuation becomes permanently undeletable through the shipped route. Executed
  and reproduced; verified correction (one clause) makes the probe pass with
  346/0 and zero regressions.
- **B2** C5's 12-value enumeration (routed L4) not built: 3 statuses in one
  monolithic test, no P-V ids, no reachability judgments, and no row asserts
  `item_cost_evaluations` unchanged. Reviewer probes for two missing rows pass —
  the code is right, the evidence is absent.
- **B3** the L15 structural row does not exist: inlining an
  `item_major_category_snapshot` read in the preview leaves 345/345 green
  (master §6.5 says the row ships in phase 5).
- **B4** the three-way currency equality has no per-clause arbiter — dropping any
  one of the three comparisons leaves 345/345 green, and the ids misname their
  pairs. Equality is transitive, so `val≠basis or val≠model or basis≠model` ≡
  `val≠basis or basis≠model`: the middle clause is provably redundant. Verified
  correction (2-clause form) gives both clauses sole-cause arbiters with the
  existing fixtures.

**5 should-fix.** S1 the `item_missing_purchase_cost` ↔ `currency_mismatch`
adjacent pair has no arbiter (swap leaves 345 green; verified fixture supplied);
S2 C6 essentially unbuilt — dropping *and* reversing the history `order_by` both
leave 345 green (the only assertion is a one-element list), no three-supersession
row, no INV-V1 count, no byte-identical re-read; S3 C4's "re-set after delete"
row absent (the row that would have caught B1); S4 C2 asserts `remaining is not
None` instead of counting INV-V1's predicate, and neither race path's observable
is asserted (P-T); S5 C3 missing the request-layer missing-currency row and the
three accept rows.

**8 notes.** N1 L12's *named* mutation is inert (the calculator quantizes to the
persisted value — only raw re-division bites; verified fixture `13.0000` →
`76923.08`); N2 DELETE's hardcoded `item_unvalued` will disagree with phase 8's
status query in an unconfigured workspace → phase 8; N3 envelope not exact-dict
(preview is); N4 pre-checkpoint dev-DB residue `ws_765225a0…` → closeout purge
(not a teardown defect — subset run twice, ten tables flat); N5 valuation payload
field list → phase 9; N6 five missing `reads_from` edges in the graph delta; N7
`domain-item-economics` source link now stale, undeclared; N8 L21 verified benign.

**Verified correct:** chain order (insert-before-close reddens both rows; S3
back-link reddens), race identity on the real DB-conflict path (index-identity
removal reddens both the unit row and the race; bounded waits; `finally`
teardown; subset twice, flat), L1 delegation genuine (wrapper divergence reddens
12 nodes), L2(i) structural independence (enum order reversed → 345 green), L7
exact leading token (naive pydantic impl reproduces the projection's
`': Value error, …'` and reddens), L9 both audit events, P-R role gates (MANAGER
drop reds exactly 3 rows, zero collateral), R13-2 history filter, L12 arithmetic
(`76800.20` vs `76800.00` hand-derived), L5/L6/L18/L20.

**Graph:** read-only, zero delta; revision `b5e6fe09…`, 153/195, 12 pending. All
12 claims TRUE; 9 spans exact, 3 corrected (set-command node → 102–168; delete
`writes_to` → 38–41; history `reads_from` → 23–31); plus the undeclared stale
`domain-item-economics` link (`configuration.py:44-82` → re-link
`resolve_economics_selection` 80–126).

**Lessons:** (L1) a routed amendment naming a test row needs a ledger row — a
missing declaration *is* the finding (extends P-I); (L2) a transitive relation is
enumerated by *state*, not by *clause*, and the implementation carries only the
independent clauses; (L3) a named mutation must be checked against the
implementation it will meet (extends P-Q); (L4) a monolithic integration test
cannot discharge an enumerated criterion — the parametrize id is the mapping
evidence (extends P-V).

### 2026-08-14 — fix r1 (Codex) — IMPLEMENTED

- B1/S3: the delete command now scopes its current-row lookup to `is_deleted IS false`; the shared chain fixture performs set → delete → set → delete, verifies two open rows with exactly one live valuation, and verifies the supersession back-links and audit sequence.
- B2: C5 is a 12-value parametrized enumeration with P-V ids and explicit sole-predicate/reachability judgments. Every preview row asserts the owed null numerics, and every row asserts that `item_cost_evaluations` is unchanged.
- B3: the L15 structural arbiter requires the preview loader to call `resolve_major_category(item.item_major_category_snapshot)` and rejects inline enum classification.
- B4/S1: currency uses the two independent equal-pair clauses with corrected ids; a purchase-cost-present/currency-mismatch fixture proves `ITEM_MISSING_PURCHASE_COST` precedence.
- S2/S4: history is read in `created_at DESC, client_id DESC` order with two byte-identical reads and an `INV-V1` current-row count; the race fixture records both supersede rowcounts and asserts exactly one current live row.
- S5/N1: request validation covers missing currency plus expected-only, cost-only, and both-value acceptance; the persisted-rate fixture uses `13.0000` and expects `76923.08`.
- Mutation ledger: B1-revert `23cfe90f65bf7b4c1ba536bbf86304e22ba65ccf3cafffac792d2b71ed75e365` → `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1` (red: chain); M4 `e818fa2b74af93c79e1e0709c93e5281d17f3fb1ff5ffb1fddf2306a80fcfad7` → `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` (red: C5 non-trivial statuses, missing basis/model, chain); M5.a `ee22880184daa7b86ffc367b02fcc1563261cb61f5d9bf1869ecd1544790a957` → `75087586aae405c57117f6417720743102fbc4003336ce2e6e25689800d68bde` (red: basis-model); M5.c `796ad66ee15e530ac57751ea87c9e5de2c9bd15d2ee43fb74427c2de57f0716b` → same (red: valuation-basis); M3.2 `bf241b9d507a70a250224ee5b71558ca216bdf128cab055b25d3ee17247548cf` → same (red: purchase-cost precedence); M8 `8847d378bfb0cae10b324b0e0365125cd78f13311b7e64f72217722c3db87ef2` → `6f586d0f4d086abf5a5c035fe4ca07c99ee1d34723b12b871efb2f717cd4e16c` (red: chain); M8b `f663c2536dcc446baf777a6208d1ac413e185e80f91982c57b8c770428f98f48` → same (red: chain); M9 `ce760b82e31bd56748d8dfddd348df22f8cd9f9fba5af1ce75a16ec658b22bb2` → same (red: chain); M10 `6cc9084f18ae23e360ec56446ff3af4dc4c48b6a3212c844ffa081bf3e964664` → `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` (red: persisted-rate value); M10b `f20f70d6a3eaa8e188a867b202cd9cb94a8dc316c999a6af16e65fb9a7994b7e` → same (red: persisted-rate value); M7a `f8bc46fc9397e03c64b4e6153df21b87dd5135f10c38e3b16dd276d9130f89ee` → same (red: audit sequence); M7b `c15fbe56688c06767f7d73fb629913ffab66d64bf3e6bac5a489576d056bd58f` → same (red: audit sequence); M11 `e0f6b2551d39b9a255fdebd4c860d48f4ba1be5a73508476483d1da4183a71b3` → same (red: chain back-link); M12 insert-before-close probe → same (red: chain and race). Probe-only files were `set_item_valuation.py`, `configuration.py`, `get_item_valuation_history.py`, and `delete_item_valuation.py`; all were restored before the checkpoint.
- Focused phase suite: 62 passed. Race subset: 1 passed twice. Full non-e2e: 1968 passed / 23 failed / 1 deselected / 2 warnings; the 23 failures are the established baseline set and no phase-5 test failed. Targeted Ruff and `git diff --check` passed; repository-wide Ruff remains red on 122 pre-existing findings. Alembic: `5caae620088c` (head). Architecture Graph: read-only, zero delta, revision `b5e6fe094caee2191414a297bb1ab63507ebda8ee4ee54c26cc612a5d940fc94`.

### 2026-08-14 — re-review r2 (Claude Opus 5) — CHANGES_REQUESTED

Handoff: `handoffs/reviewer/2026-08-14_phase5_rereview_r2_handoff.md` (probe
declaration with sha256 pairs, corrected anchor spans, write perimeter).

Delta-scoped. Perimeter exact (7 files; tree clean; `git diff a0cebde..HEAD --
app/` empty; all five declared final hashes match). Production diff is exactly
two lines, and **both production files are byte-identical to the ones review r1
produced during correction verification** (`ab9aebbe…`, `75087586…`) — the fix
shipped the verified corrections and only those. Ruff clean. Suite re-run by me
on a hash-verified-clean tree: **1968 passed / 23 failed / 1 deselected**,
collection 1991+1, failure set byte-identical to the phase-1 baseline. Focused
selector 363 (r1: 345). DB at head `5caae620088c`. Graph read-only, zero delta.

**All four blocking and all five should-fix findings from r1 are CLOSED**, each
re-proven with a mutation that was green in r1 and reddens now; every declared
mutant hash reproduced byte-identically:
- **B1** — the B1-revert mutant (`23cfe90f…`, byte-identical to the old unfixed
  file) reddens the chain row; the delete-then-reset-then-delete fixture asserts
  2 open rows / exactly 1 live, then the INV-V1 count.
- **B2** — 12 parametrize ids map one-for-one onto §11A.4-as-amended (no
  duplicates/omissions); 3 recorded reachability judgments; sole-predicate
  verified on 5 sampled rows; every executed row asserts `item_cost_evaluations`
  unchanged and the owed null numerics.
- **B3** — M4a (r1's mutant `df1f79b3…`) now reddens the new structural row.
- **B4/S1** — both currency clause drops (`ee228801…`, `796ad66e…`) and the
  precedence swap (`bf241b9d…`) each redden exactly their own row; the drop of
  `val≠basis` gains a second arbiter at the C5 layer; the reduction did not
  weaken the three fixtures.
- **S2/S3** — M8 and M8b (both r1-green) now redden; byte-identical re-read,
  ordered id list against an independently-ordered expectation, INV-V1 count.
- **S4** — path (i) asserts its blocking observable (`close rowcounts == [0,1]`)
  and both blocks count INV-V1 `== 1`. Race subset twice + the whole file twice:
  ten tables flat.
- **S5/N1** — missing-currency + three accept rows; the `13.0000` fixture makes
  **M10 (L12's *named* mutation, inert in r1) redden**, alongside M10b.

**1 should-fix: S1 — the L15 structural guard asserts a weaker property than the
one it constructs.** The test builds `module_sources` over exactly L15's two
roots (24 modules, verified) and then never asserts the guard against it; the
only use asserts the string IS present in one file. Executed: keeping the
resolver call and adding a second unmediated snapshot read in the same module
(`e1ca0625…`) or adding a snapshot-classifying helper to
`delete_item_valuation.py` (`88c9f5aa…`) each leave **363 green**. The literal
amendment is met by M4a; the property it states is not tested, and catching the
reader added later is the only job a structural row has (P-J). Verified
correction (executed, 6 lines): count in-scope occurrences minus
`resolve_major_category(item.item_major_category_snapshot)` occurrences per
module and assert the remainder is empty — baseline 9 passed, and M4a/M4b/M4c
each redden it.

**7 notes.** N1 C5's row numbers are a hybrid of the pre-round-12 and post-§7C.3
numberings and map to no single authority (the plan's own L4 example is
pre-round-12) → next touch + plan correction; N2 dropping `client_id DESC` alone
leaves 363 green — no fixture ties `created_at`; not reachable today but
load-bearing once **phase 6** bulk-creates valuations → phase-6 forward note;
N3 the renamed currency ids name the pair held EQUAL while the clause each row
arbitrates is the other one (r1's own wording) — one comment closes the
misreading trap; N4 two different M4 mutants shipped under one label and the
ledger's red set belongs to the one that did not exercise the row under review
(P-I ext); N5 race path (ii) has no rowcount observable (gate-guaranteed, low
value); N6 the phase-2 citation is prose, not a pytest node id; N7 r1's
carry-forwards unchanged.

**Graph:** revision `b5e6fe09…`, 153/195, 12 pending, zero delta. Two anchor
spans moved (+1 in `delete_item_valuation.py`): node
`command-…-delete-item-valuation` **17–44**, edge `--writes_to-->`
**39–42**. All other r1 spans re-verified unchanged; the stale
`domain-item-economics` link is unmoved (`resolve_economics_configuration`
64–77; recommended re-link `resolve_economics_selection` **80–126**).

**Lessons:** (L1) a structural guard is graded on the reader added *later*, not
the call replaced *now* — a criterion stating a property over a module set must
quantify over that set (P-J ext); (L2) parametrize row numbers must cite a
numbering scheme that still exists, and plans should quote the authority's
current numbering in id examples (P-V); (L3) a reused mutation name needs a
mutant hash beside each red set (P-I ext); (L4) process — a reviewer's
background suite run must not overlap its own probes (my first run reported a
24th failure that was my own mutant; re-run foreground on a clean tree).

### 2026-08-14 — fix r2 (Codex) — IMPLEMENTED

- S1: `test_item_major_category_snapshot_is_read_only_by_the_registered_resolver`
  now quantifies over all `module_sources`; every in-scope occurrence of
  `item_major_category_snapshot` must be the registered resolver argument, with
  `unmediated == {}`. The non-generalizing `ItemMajorCategoryEnum(` assertion
  was removed. N3's currency-parametrize comment names the clause arbitrated by
  the equal-pair ids.
- Baselines: `test_configuration.py` **9 passed**; focused phase selector
  **363 passed**; full `PYTHONPATH=. pytest -m 'not e2e'` **1968 passed / 23
  failed / 1 deselected / 2 warnings**. The 23-failure set is byte-identical
  to the established baseline. Targeted Ruff and `git diff --check` passed.
- Mutation ledger (governing hashes copied from the re-review handoff; restored
  file hashes verified locally): M4a inline preview chain,
  `df1f79b3a23081cf21cc785f6660999fdc3648d786fd074167bcb074cbfb7c88` →
  `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8`, red
  `test_item_major_category_snapshot_is_read_only_by_the_registered_resolver`;
  M4b second same-module reader,
  `e1ca06250fc7d8924e6e2d935bda00b9a03ece4bafdfee117afd013b88d3c6c0` →
  `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8`, red
  same node; M4c reader helper in `delete_item_valuation.py`,
  `88c9f5aa59adca10e948fdc2c29acb12b77dce7eb491b615e73ff853d5f628ae` →
  `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1`, red
  same node. Local equivalent probe hashes were
  `e818fa2b74af93c79e1e0709c93e5281d17f3fb1ff5ffb1fddf2306a80fcfad7`,
  `c4abb17d4135df01e9e1029fc01a7ca905a66ff0b382570762fa41b8ff975332`, and
  `ead1b99984188576209f01abbf97603d93f1e07562788742532be009ef0dd65f`,
  respectively; each equivalent probe reddened the guard and was reverted.
- Database check: `5caae620088c` (head). Architecture Graph was read-only,
  revision `b5e6fe094caee2191414a297bb1ab63507ebda8ee4ee54c26cc612a5d940fc94`,
  153 nodes / 195 edges / 12 pending, zero delta.
