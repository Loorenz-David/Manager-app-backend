---
plan: phase 5 (valuation surface)
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-13
actor: reviewer (Claude Opus 5)
session_date: 2026-08-14 (path/frontmatter date kept as the prompt's for coordinator lookup)
---

# Phase 5 review r1 handoff

## Summary

The valuation **surface** is right. The chain order, the race arbitration, the
persisted-rate preview, the audit events, the role gates and the request-layer
identity all re-derive correctly and every one of them has a live arbiter that I
executed myself. The **evidence** does not hold, and one behavioural defect got
through the gap: after a manager deletes a price and then sets a new one, that
new price can never be deleted again — the delete command's current-row
predicate is missing `is_deleted = false`, and no shipped test builds the
delete-then-reset state that would have caught it. That state is exactly the
fixture the routed amendments L13 and C4's last row asked for.

Four blocking findings, five should-fix, seven notes. Three of the four blockers
are governing amendments (L4, L15, L16) that were routed into the plan and not
implemented; the fourth is the delete defect they would have caught.

**Verdict: CHANGES_REQUESTED.**

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Every finding is a defect or an evidence gap the
coordinator routes; the two semantic questions this phase raised were already
answered in round 13 (R13-1, R13-2).

## Coordinator consumption findings — outcomes

### P5-A (arithmetic) — RESOLVED, the handoff is wrong

Measured by me, full `PYTHONPATH=. pytest -m 'not e2e'` at `8b4ac06`/`HEAD`
(tree identical, `git diff 8b4ac06..HEAD -- app/` empty):

**1950 passed / 23 failed / 1 deselected** in 69.53 s; collection
`1973/1974 tests collected (1 deselected)`.

The 23-failure set is **byte-identical** to the phase-1 baseline (diffed against
the enumerated list at `plans/phase_1_worker_money_redaction.md:198-220` —
zero-line diff). Phase 5 therefore adds **+23** selected tests over the 1927
baseline, all passing.

The handoff's "1951 passed, 23 failed" is off by one and omits the deselected
count; its "phase 5 added 24 collected tests relative to the recorded 1927
baseline" is the source of the error. **Discrepancy class: derived-not-read.**
1927 + 24 = 1951, i.e. the passed count was computed from an assumed +24
collection rather than read off a run. It is not a different tree state: the
tree is byte-identical and the number is not reproducible.

### P5-B (ledger under-declaration) — RESOLVED, and it hid three blockers

Of the ~ten mutations the governing amendments name, the ledger declared three.
I ran all of them. **Four of the owed seven do not bite**, and three of those
four are blocking findings (B2 is a missing enumeration rather than a single
mutation). Full results in the probe declaration below.

| Owed probe | Result |
|---|---|
| L1 — force the wrapper to diverge from `resolve_economics_selection` | **RED** (12 nodes) ✔ |
| L2(i) — permute `EconomicsStatusEnum` declaration order | **345/345 green** ✔ (structural independence holds) |
| L2(ii) — permute `ITEM_READINESS_PRECEDENCE` | 3 of 4 adjacent pairs red; **pair 2 green** → **S1** |
| L15 — inline a snapshot read in the preview | **345/345 green** → **B3** (the row does not exist) |
| L16 — drop one side of one currency comparison | **all three drops green** → **B4** |
| L7 — identity as exact leading token | **RED** under the naive impl ✔ (assertion is `^`-anchored) |
| L9 — remove an `audit(...)` call | **RED**, both events ✔ |

---

## Findings

### B1 (blocking) — a deleted-then-reset item's current valuation can never be deleted again

**Where.** `app/beyo_manager/services/commands/item_economics/delete_item_valuation.py:27-33`.

The item-scoped branch selects
`workspace_id = … AND item_id = … AND superseded_at IS NULL` and **omits
`is_deleted = false`**. INV-V1's predicate is both clauses — the index
`uix_item_valuations_current` is
`WHERE superseded_at IS NULL AND is_deleted = false`
(`models/tables/item_economics/item_valuation.py:39`), the command's own S1 close
statement uses both clauses (`set_item_valuation.py:132-134`), and routed
amendment L13 pins "exactly one current" to that predicate.

After a delete-then-reset the item legitimately holds **two** rows with
`superseded_at IS NULL` — the soft-deleted one and the live one. `session.scalar()`
returns whichever the planner yields first (no ordering, no filter); when that is
the deleted row, line 32's `valuation.is_deleted` guard converts it into
`NotFound`.

**Executed.** Reviewer probe `test_probe_delete_after_reset_targets_the_live_row`
(disposable, removed): set → delete → set → delete raises
`beyo_manager.errors.not_found.NotFound: Item valuation not found.` while a live
current row exists. A companion probe confirms the state independently:
`superseded_at IS NULL rows = 2; INV-V1 current rows = 1`.

**Reachable in production** through the shipped surface: `PUT
/items/{id}/valuation` → `DELETE /items/{id}/valuation` → `PUT` → `DELETE`.

**Verified correction (executed).** Add `ItemValuation.is_deleted.is_(False)` to
the item-scoped branch. With that one line the probe passes and the focused
selector is 346 passed / 0 failed (345 + the probe), zero regressions.
Mutant sha256 `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1`
→ restored `23cfe90f65bf7b4c1ba536bbf86304e22ba65ccf3cafffac792d2b71ed75e365`.

**Authority.** Intention §4.7A (INV-V1), §7.5 ("the current row is
soft-deletable"); plan amendment L13.

**Companion gap:** C4's last row ("re-set after delete starts a fresh current
row") is the test that would have caught this and was not built — see **S3**.

### B2 (blocking) — C5's 12-value preview enumeration was not built (L4 unimplemented)

Routed amendment L4 (GOVERNING) rewrote C5 as an enumeration over §11A.4's twelve
values, "one row per value with an exact outcome or a recorded reachability
judgment, parametrize ids naming the authority row
(`status-row-7-missing-purchase-cost`), each fixture sole-predicate".

What shipped: **three** preview statuses — `not_evaluated`,
`item_missing_expected_price`, `item_unvalued` — asserted inside a single
monolithic integration test (`test_valuation_surface.py:36-151`) with no
parametrize ids and no per-row fixtures.

Missing preview rows: `item_missing_major_category` (which the plan's own N-d
note mandates and which the projection re-measured as live for **53 of 471**
items), `not_configured_no_cost_group`, `not_configured_no_basis_version`,
`not_configured_no_cost_model_version`, `item_missing_purchase_cost`,
`currency_mismatch`. Missing recorded judgments: `ok` / `infeasible`
(task-scoped, out of the item-scoped preview) and
`not_configured_ambiguous_cost_group` (INV-G3-unreachable).

Also absent from **every** preview row: C5's own "asserts `item_cost_evaluations`
count unchanged (creates nothing)". Zero references to `ItemCostEvaluation` exist
anywhere in phase 5's tests.

**Executed.** I built two of the missing rows as disposable probes
(`item_missing_major_category` via a NULL snapshot, `not_configured_no_cost_group`
via an unconfigured workspace) and both **pass** — and a third probe confirms
`item_cost_evaluations` is unchanged across a set. The production code is right;
the evidence is simply not there. The 4B classifier rows cover the *classifier*,
not the preview surface.

**Authority.** Plan amendments L4/L6, §11A.4, §9 P-V and its r3 extension,
charter rule 2.

### B3 (blocking) — the L15 structural row does not exist

Routed amendment L15 (GOVERNING): "no module under `domain/item_economics/` or
`services/**/item_economics/` reads `item_major_category_snapshot` except through
`resolve_major_category` — the test names its inspected source; named mutation:
inlining a snapshot read in the preview must redden it." Master §6.5 was amended
to say the row "ships in PHASE 5 with the first production caller".

**Executed (M4).** I inlined the classification in
`set_item_valuation._load_preview_inputs`, bypassing `resolve_major_category`
entirely: **345/345 green**. A tree-wide grep confirms no test inspects any
module source for that column; the only `resolve_major_category` tests are 4B's
four value assertions (`test_phase4b_category_classifier.py:69-73`), which the
inlining leaves untouched.

**Verified correction.** P-J/P-X shape: a test that names the sources it inspects
(`inspect.getsource` over every module under the two package roots) and asserts
`item_major_category_snapshot` appears only inside
`configuration.py:resolve_major_category`, carrying M4 as its named mutation.

### B4 (blocking) — the three-way currency equality has no per-clause arbiter, and the row ids misname their pairs

**Where.** `configuration.py:154-164`;
`tests/unit/domain/item_economics/test_configuration.py` parametrized rows
`[valuation-basis] / [valuation-model] / [basis-model]`.

**Executed (M5 ×3).** Deleting **any one** of the three comparison clauses leaves
**345/345 green**. Every row carries two sufficient causes, so no clause has an
arbiter — §6A.9 step 3's "enumerated as three criterion rows … not one sampled
row" is met nominally only.

**Root cause, and why it cannot be fixed by picking better fixtures.** Equality is
transitive: no assignment can break exactly one pair, so
`a≠b or a≠c or b≠c ≡ a≠b or b≠c` — the middle clause is provably redundant and can
never have an arbiter on a status-only surface. The ids are also wrong:
`[valuation-basis]` = (EUR, SEK, SEK) breaks valuation≠basis **and**
valuation≠model; `[valuation-model]` = (SEK, EUR, SEK) has valuation **equal to**
model.

**Verified correction (executed).** Reduce the disjunction to the two independent
clauses (`valuation ≠ basis` OR `basis ≠ model`). With the three *existing*
fixtures unchanged: all 7 unit rows stay green under the 2-clause form; dropping
clause 1 reddens **exactly** `[valuation-basis]`; dropping clause 2 reddens
**exactly** `[basis-model]`. Then rename the ids to the pair each fixture holds
equal.

**Authority.** §6A.9 step 3, plan amendment L16, §9 P-O, charter rule 2's
sole-predicate companion.

### S1 (should-fix) — one adjacent pair of `ITEM_READINESS_PRECEDENCE` has no arbiter

**Executed (M3.0–M3.3).** Swapping each adjacent pair of the registered sequence:

| Pair | Result |
|---|---|
| 0 `item_unvalued` ↔ `item_missing_expected_price` | RED (via the `[0] is ITEM_UNVALUED` structural assert; behaviourally unarbitrable — the two predicates are mutually exclusive) |
| 1 `item_missing_expected_price` ↔ `item_missing_purchase_cost` | RED ✔ |
| **2 `item_missing_purchase_cost` ↔ `currency_mismatch`** | **345/345 GREEN** |
| 3 `currency_mismatch` ↔ `not_evaluated` | RED ✔ |

Consequence: an item whose model carries an `item_purchase_cost` term, whose
`purchase_cost_minor` is NULL **and** whose currency disagrees would report
`currency_mismatch` — the wrong repair instruction — with nothing to catch it.

**Verified correction (executed).** A fixture with purchase-cost term present,
`purchase_cost_minor` NULL, expected price set, valuation currency ≠ basis =
model currency, expecting `item_missing_purchase_cost`: it passes today and
reddens **exactly** under the M3.2 swap.

**Authority.** §11A.4 rows 7/8, plan amendment L2, charter rule 2.

### S2 (should-fix) — C6 is essentially unbuilt; history ordering has no arbiter

**Executed (M8, M8b).** Dropping `.order_by(...)` entirely, and reversing it to
ASC, each leave **345/345 green**. The only history assertion
(`test_valuation_surface.py:136`) compares a **one-element** list, so ordering is
unobservable.

C6 requires three things, none of which exists: "after three supersessions,
history returns all rows in order", "with exactly one current", "byte-identical
re-read". L13's total order (`created_at DESC, client_id DESC`) and the INV-V1
"exactly one current" predicate — whose prover L13 names as the delete-then-reset
fixture — are both unpinned.

Verified good alongside it: **M9** (dropping the `is_deleted` filter) reddens, so
R13-2's hidden-deleted-rows pin does have its arbiter.

### S3 (should-fix) — C4's "re-set after delete starts a fresh current row" row is absent

The criterion's last clause has no test. It is the same fixture S2 needs and the
one that would have caught **B1**. Recommend the fix cycle build it once and use
it for C4, C6 and L13's predicate proof together.

### S4 (should-fix) — C2's race criterion cannot count, and neither path is distinguished

`test_valuation_surface.py:265-272` asserts `remaining is not None` on a
`scalar()` of one column. §7A.2's criterion (a) is "**exactly one** row satisfies
the open predicate afterwards" — dropping the unique index would leave two
current rows and this assertion still passes.

The second block (`current_sessions`, `:242-263`) installs no gate and asserts no
observable distinguishing the pre-existing-current path from the first-valuation
path. L11 names path (i)'s observable explicitly ("loser blocks on the row lock,
rowcount 0 after winner commits") — P-T requires naming the observable that
flips, not only the outcome.

Verified good: both blocks do produce exactly one winner and one
`ITEM_COST_CONCURRENT_VALUATION`; **M13** proves the *identity* is asserted, not
just the class (phase-4 S1's lesson landed); all waits are bounded (0.5 s / 1.0 s
— P-T extension satisfied); teardown is in `finally` and scopes nine tables
(superset of the required five). I ran the subset **twice** with all ten
economics/actor tables flat.

**Correction.** `select(func.count())` over INV-V1's predicate `== 1` in both
blocks, and an asserted observable for path (i).

### S5 (should-fix) — C3's request-layer enumeration is missing three of its rows

Shipped at the request layer: both-null → identity, negative-expected,
negative-purchase. Missing: **missing currency** (C3 row 7's request half —
`ValidationError` naming `currency`), and the three accept rows
**expected-only / cost-only / both**. L10 scoped C3 to the request layer plus the
identity; it did not remove the accept rows. L10's "cite the phase-2 DB-CHECK
rows by node id" also appears nowhere in the test file.

---

## Notes

**N1 — L12's *named* mutation is inert; only raw re-division bites.**
**Executed (M10):** replacing the persisted-rate read with
`calculate_cost_per_worker_minute(fixed, hours, util)` — the mutation L12 names
verbatim — leaves **345/345 green**, because the calculator quantizes to exactly
the persisted `13.0208`. **Executed (M10b):** dividing by the raw un-quantized
rate reddens `test_valuation_chain_preview_delete_and_history`. Hand-verified:
raw `13.02083333…` → `76800.00`; persisted `13.0208` → `76800.20`. So the pin's
*intent* is protected but the plan's named mutation is not.
**Verified correction:** set the fixture's persisted `cost_per_worker_minute_minor`
to `13.0000` (≠ the calculator's `13.0208` for the same inputs) and expect
`76923.08` (hand-computed) — then both mutation forms redden. The ledger row
"Preview consumes persisted rate" should also state which form it ran (P-I second
extension).

**N2 — DELETE's `item_unvalued` is hardcoded, not resolved** (`delete_item_valuation.py:43`).
§11A.5(d) pins that word, so this matches the letter. But §11A.4 says the
vocabulary is "used identically by the budget status query, the valuation
endpoint's preview, and the auto-path log line", and configuration failures
precede `item_unvalued` in the order — so for an item in an unconfigured
workspace, phase 8's status query will say `not_configured_no_cost_group` where
DELETE says `item_unvalued`. → **phase 8** consistency check.

**N3 — R13-1 envelope exactness is per-key, not per-envelope.** `first["preview"]
== {…}` is exact-dict ✔ (and therefore proves the preview carries no
`client_id`). Nothing asserts the response has exactly `{item_valuation,
preview}`, and the serialized valuation is only touched via
`["client_id"].startswith("ival_")`. P-Y wants the shape restated per row.

**N4 — dev-DB residue predating the checkpoint (purge item, not a teardown defect).**
`item_valuations = 2`, `production_cost_groups / basis_versions /
cost_model_versions / cost_model_terms = 1` each, all owned by workspace
`ws_765225a015d5…` named `Wood 765225a015d5…` — the race test's fixture shape —
created **2026-08-13 20:48:23 UTC**, ~5 min before the checkpoint (22:53:41
+0200). Not a teardown hole: I ran the race subset twice and every count stayed
flat, and cleanup is in `finally`. Same shape as phase-4 r3 N3 (interrupted run).
→ closeout purge.

**N5 — `serialize_item_valuation` exposes `workspace_id`, `item_id`,
`created_by_id`, `superseded_by_id`.** Consistent with the phase-4 serializers,
so not a new divergence — recorded because this is the domain's first
*item-scoped* money payload and phase 9's docs pass should confirm the field list
is intended.

**N6 — the graph delta under-declares the set command's read boundary.**
`set_item_valuation` reads `items`, `production_cost_groups`,
`production_cost_basis_versions`, `cost_model_versions` and `cost_model_terms` to
compute the preview; the recorded delta carries only `writes_to
table-item-valuation`. Five `reads_from` edges are missing. No claim is wrong —
the read surface is simply invisible.

**N7 — one node went stale and the handoff does not declare it.** See the
anchor-spans table.

**N8 — L21 confirmed benign in the shipped code.** `calculate_term_amounts`
receives live `CostModelTerm` rows lacking the `TermSnapshot` Protocol's
`amount_minor`; only `calculation_type` / `percent_value` / `fixed_amount_minor`
are read. Runtime-safe as the projection predicted; correctly not "fixed".

---

## Verified correct (settled ground for the re-review)

- **Perimeter exact.** `git show 8b4ac06 --stat` = the 16 declared files;
  `git status --porcelain` clean; `git diff 8b4ac06..HEAD -- app/` empty.
  All three declared restored sha256s are byte-identical to the tree.
- **Ruff** clean on all 12 changed `app/` files.
- **Chain order (C1).** M12 — moving the INSERT before the close reddens both
  integration rows; M11 — dropping the S3 back-link reddens. Close-before-insert
  per §7A.1 verified by reading the emitted SQL.
- **Race identity (C2).** M13 — removing `uix_item_valuations_current` from
  `INDEX_IDENTITIES` reddens both the unit table row and the real two-session
  race. Both race blocks yield exactly one winner + one exact
  `ITEM_COST_CONCURRENT_VALUATION`. Subset run twice, ten tables flat.
- **L1 (selection/status can never disagree).** M1 — an independent
  re-derivation in the wrapper reddens **12** nodes across the 4B classifier
  enumeration and the phase-4 C8 status rows. The delegation is genuine.
- **L2(i) structural independence.** M2 — fully reversing `EconomicsStatusEnum`'s
  declaration order leaves 345/345 green.
- **L7 leading token.** M6 — the naive pydantic-side implementation yields
  `': Value error, ITEM_COST_VALUATION_AMOUNT_REQUIRED: …'` (reproducing the
  projection's finding exactly) and reddens the row; the assertion is
  `match=r"^ITEM_COST_VALUATION_AMOUNT_REQUIRED:"`, i.e. `startswith`, not a
  substring.
- **L9 audit.** M7a/M7b — removing either `audit(...)` call reddens; both
  registered strings are asserted as an exact ordered list.
- **P-R role gates.** M14 — dropping MANAGER from the three new routes reddens
  **exactly** the three MANAGER rows, zero collateral. Three routes, ADMIN/MANAGER,
  matching §6.5; router README rows present; L20's rename applied
  (`…every_item_economics_route…`).
- **R13-2 history filter.** M9 reddens.
- **L12's arithmetic.** `76800.20` vs `76800.00` re-derived by hand from the
  calculator; M10b reddens.
- **L5 option (a).** Superseded-row refusal proven by direct command call with the
  registered identity, `match=r"^ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE:"`.
- **L6.** DELETE returns the status-only `{"preview": …}` envelope per §11A.5(d).
- **L18.** No self-FK teardown special-casing; the single-statement chain delete
  works, as the projection proved.
- **Regression.** The 4B/phase-4 suites are untouched and green; `resolve_economics_configuration`'s
  results are unchanged (M2 + the 12-node M1 blast radius both confirm the
  reimplementation is behaviour-identical).
- **Suite** 1950/23/1, failure set byte-identical to the phase-1 baseline.
  **DB at head** `5caae620088c`.

## Architecture graph — verification and anchor-spans service (read-only)

State: revision `b5e6fe094caee2191414a297bb1ab63507ebda8ee4ee54c26cc612a5d940fc94`,
**153 nodes / 195 edges** (= 148 + 5, 188 + 7 — the declared delta is exact),
**12 pending**, 0 diagnostics, **1 stale node**. I made no decisions and no
mutations.

**All 12 claims verified TRUE against the code.** The phase-4 lesson is honoured:
both `writes_to` edges anchor in the command files, not a blanket router span.

| # | Item | Declared | Verdict | Final span |
|---|---|---|---|---|
| 1 | node `command-…-set-item-valuation` | `set_item_valuation.py:102-165` | IMPRECISE — 3 lines short, cuts mid-dict | **102–168** |
| 2 | node `command-…-delete-item-valuation` | `delete_item_valuation.py:17-43` | EXACT | 17–43 |
| 3 | node `endpoint-…-put-valuation` | `item_economics.py:229-241` | EXACT | 229–241 |
| 4 | node `endpoint-…-get-valuations` | `item_economics.py:244-256` | EXACT | 244–256 |
| 5 | node `endpoint-…-delete-valuation` | `item_economics.py:258-269` | EXACT | 258–269 |
| 6 | edge set `--writes_to-->` table | `set_item_valuation.py:128-159` | EXACT (S1 → S2 → S3) | 128–159 |
| 7 | edge delete `--writes_to-->` table | `delete_item_valuation.py:31-42` | WIDE — 31 is a SELECT, 42 writes `audit_logs` | **38–41** |
| 8 | edge get-valuations `--reads_from-->` table | `get_item_valuation_history.py:23-33` | WIDE by 2 — 32–33 is the return | **23–31** |
| 9 | edge get-valuations `--returns-->` table | `get_item_valuation_history.py:32-33` | EXACT | 32–33 |
| 10 | edge put-valuation `--returns-->` table | `item_economics.py:229-241` | EXACT | 229–241 |
| 11 | edge put-valuation `--accepts-->` command | `item_economics.py:229-241` | EXACT | 229–241 |
| 12 | edge delete-valuation `--accepts-->` command | `item_economics.py:258-269` | EXACT | 258–269 |

**Stale node (N7), undeclared by the handoff.** `domain-item-economics` carries a
source link to `configuration.py:44-82`, symbol `resolve_economics_configuration`
— the span 4B's fix-r1 N5 ride-along re-anchored. L1's rework moved that function;
it is now **64–77** (a 14-line delegating wrapper). Recommended re-link: symbol
**`resolve_economics_selection`, span 80–126** — the §7C.2 resolution authority
after L1. Same shape as phase-4 N2.

## Mutation-probe declaration

Every probe was applied in the main worktree, run against the focused selector,
then reverted with `git checkout --`. Restored sha256s are copy-pasted from the
probe harness output and equal the pre-probe baselines; the working tree is clean
and `git diff 8b4ac06..HEAD -- app/` is empty, so zero probe residue exists.

Focused selector (345 tests, ~9 s):
`tests/unit/domain/item_economics tests/unit/services/commands/item_economics tests/unit/routers/api_v1/test_item_economics_router.py tests/integration/services/commands/item_economics tests/integration/models/item_economics`

| Probe | File | Mutant sha256 | Restored sha256 | Observed red set (full) |
|---|---|---|---|---|
| M1 L1 wrapper diverges | `configuration.py` | `b3330a3599f13c084c92e2036b64e4eaaa97d75dcebb4065473132d354daf2bf` | `14dfea80ae0d7ac48f34765de5214556093effc71565701c8d764a434b65916a` | 12: `test_configuration_classifier_uses_explicit_failure_order_and_same_basis_identity_for_gap`; `test_classifier_value_rows_have_one_first_failure[V2…,V3…,V4…,V4b…,V5…]`; `test_classifier_adjacent_pair_rows_choose_the_earlier_failure[P3…,P4…,P5…]`; `test_c8_status_query_enumerates_each_first_failure_and_success`; `test_status_has_exact_per_category_shape_and_scopes_basis_to_each_group`; `test_status_shared_model_failure_is_repeated_in_each_category_block` |
| M2 L2(i) enum order reversed | `enums.py` | `cdc758e4015a8a743a2b5ea1881d104bbb8f17712e1cd3416b821cb166882eba` | `9490d6195acb0fe58a39c985c7ce175c1e02c19ba0ac1d4897884b08f50376bd` | **none — 345 passed** (expected) |
| M3.0 precedence swap 0↔1 | `configuration.py` | `46f88d0fabc94101fc3bd87d6b5faaf0e42b8befbef33d5e86896b26be307248` | `14dfea80…916a` | `test_item_readiness_uses_registered_order_and_requires_a_purchase_term` |
| M3.1 swap 1↔2 | `configuration.py` | `04b7dd209172e7f552420c90bf202ba925a9da18fa0d569b4c4b329cf28d076a` | `14dfea80…916a` | `test_item_readiness_uses_registered_order_and_requires_a_purchase_term` |
| **M3.2 swap 2↔3** | `configuration.py` | `39a100693b3d8631f67ac56b465ef78d6ef44f52adfac1bf10e0d55d7317d2bd` | `14dfea80…916a` | **none — 345 passed → S1** |
| M3.3 swap 3↔4 | `configuration.py` | `7aa389584c85842f0690f3eff7ca00044d90b83d90d19012bc4df0114258fc16` | `14dfea80…916a` | `test_item_readiness_rejects_each_currency_mismatch_pair[valuation-basis, valuation-model, basis-model]` |
| **M4 L15 inline snapshot read** | `set_item_valuation.py` | `df1f79b3a23081cf21cc785f6660999fdc3648d786fd074167bcb074cbfb7c88` | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | **none — 345 passed → B3** |
| **M5.a drop `val≠basis`** | `configuration.py` | `51475f92ae6a4f4b69513552549c808c0f6557591b3bd904ad4f8bc564c52d88` | `14dfea80…916a` | **none → B4** |
| **M5.b drop `val≠model`** | `configuration.py` | `75087586aae405c57117f6417720743102fbc4003336ce2e6e25689800d68bde` | `14dfea80…916a` | **none → B4** |
| **M5.c drop `basis≠model`** | `configuration.py` | `1e3d723438e6ea43700a4f3f908e180ac5871c35727d84fbaec51842109c8ba8` | `14dfea80…916a` | **none → B4** |
| M6 L7 rule inside pydantic | `requests/__init__.py` | `898b885287953eaf7d0650c4de97fc056f46da97d9016f29c6831340467814ff` | `5da4c3646170e9b72f99027e59eaa61e6cdfbe361f6e45731ee14917a11da132` | `test_valuation_request_requires_at_least_one_amount_after_pydantic_parse` |
| M7a remove `.created` audit | `set_item_valuation.py` | `f8bc46fc9397e03c64b4e6153df21b87dd5135f10c38e3b16dd276d9130f89ee` | `05587c2b…5bda8` | `test_valuation_chain_preview_delete_and_history` |
| M7b remove `.deleted` audit | `delete_item_valuation.py` | `0a41e0f31241235d6f159c8ce431c35402349222c3aec62ea328f39cc71ff88f` | `23cfe90f65bf7b4c1ba536bbf86304e22ba65ccf3cafffac792d2b71ed75e365` | `test_valuation_chain_preview_delete_and_history` |
| **M8 drop history `order_by`** | `get_item_valuation_history.py` | `8847d378bfb0cae10b324b0e0365125cd78f13311b7e64f72217722c3db87ef2` | `6f586d0f4d086abf5a5c035fe4ca07c99ee1d34723b12b871efb2f717cd4e16c` | **none → S2** |
| **M8b reverse ordering to ASC** | `get_item_valuation_history.py` | `f663c2536dcc446baf777a6208d1ac413e185e80f91982c57b8c770428f98f48` | `6f586d0f…16d4` | **none → S2** |
| M9 drop history `is_deleted` | `get_item_valuation_history.py` | `ce760b82e31bd56748d8dfddd348df22f8cd9f9fba5af1ce75a16ec658b22bb2` | `6f586d0f…16d4` | `test_valuation_chain_preview_delete_and_history` |
| **M10 L12's named mutation** | `set_item_valuation.py` | `64480dcefdd323644fcfd62fbd020fec154bbb8d72350e5a996e23c30fb805de` | `05587c2b…5bda8` | **none → N1** |
| M10b raw re-division | `set_item_valuation.py` | `8191d1f82e0002b083bd0ab051826acbb5e3032e8c8ea511cf3137c268ea1f22` | `05587c2b…5bda8` | `test_valuation_chain_preview_delete_and_history` |
| M11 drop S3 back-link | `set_item_valuation.py` | `aa77f1f0e45069dfe1150be5a6357e494bfc19de1c9f2c326d196eaea89feb9d` | `05587c2b…5bda8` | `test_valuation_chain_preview_delete_and_history` |
| M12 insert-before-close | `set_item_valuation.py` | `d2e9fcc33cfc422d53139cc439162786ef45c284bf5fa12147443f461de781a6` | `05587c2b…5bda8` | `test_valuation_chain_preview_delete_and_history`; `test_valuation_race_first_and_current_paths_use_two_sessions` |
| M13 drop index identity | `_common.py` | `64bb3b3970f56d9d7c41c43846b681bcb919f5f043de277ec6b0dd6ee9467263` | `a0d86df18b567b18d260c2e247b2ed7de301c1775e2b84cc7e7e3b2b61dfd7af` | `test_integrity_translation_preserves_each_registered_index_identity[uix_item_valuations_current-…]`; `test_valuation_race_first_and_current_paths_use_two_sessions` |
| M14 drop MANAGER (3 routes) | `api_v1/item_economics.py` | `eaacba60e7a497a184b082b4fba7a2cc6cc72a35435759c917d68a95c6c6d2dd` | `1144384ab6e14b9f5ee6b8f234fba1534a79b885fb9381f7bbbf9bedfc61f8ca` | `test_every_item_economics_route_retains_admin_and_manager_access[put-valuation-manager, get-valuations-manager, delete-valuation-manager]` |

**Correction-verification runs** (applied, measured, reverted — not findings):

| Check | Mutant sha256 | Result |
|---|---|---|
| B1 fix: `is_deleted.is_(False)` added to the delete predicate | `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1` | probe passes; focused selector 346 passed / 0 failed |
| B4 fix: 2-clause currency form | — | 7/7 unit rows green; dropping clause 1 reds **only** `[valuation-basis]`; dropping clause 2 reds **only** `[basis-model]` |
| S1 fix: purchase-cost + currency-mismatch fixture | — | passes today; reds **exactly** under M3.2 |

## Full write perimeter

- **Documents written:** this handoff; the Review log entry appended to
  `plans/phase_5_valuation_surface.md`; the phase-5 tracker row in
  `master_plan.md`. Nothing else.
- **Code / tests:** **zero net changes.** All probe edits were reverted via
  `git checkout --`; `git status --porcelain` is clean and
  `git diff 8b4ac06..HEAD -- app/` is empty.
- **Disposable test files created and removed:**
  `app/tests/integration/services/commands/item_economics/test_zz_reviewer_probe_phase5.py`
  and `…/test_zz_b1probe.py` — both deleted; neither is in the tree.
- **Database:** the configured dev DB, left at head `5caae620088c`. Row counts
  after my session are identical to before it (`item_valuations=2`,
  `audit_logs=112`, `workspaces=6468`, `item_cost_evaluations=0`) — the two
  valuation rows are the implementer's pre-checkpoint residue (N4), not mine.
  No disposable database was needed (no DDL in this phase).
- **Scratchpad (outside the repo):** the probe harness and suite logs under
  `…/scratchpad/`.
- **Architecture graph:** **READ-ONLY, zero delta.** `archgraph_status`,
  `list_pending_reviews`, twelve `get_review_item` calls, one `get_node`. No
  decision was made or recorded.

## Lessons for the plans

1. **An amendment that names a test row must be checked as *shipped*, not as
   *routed*.** Three of four blockers are governing amendments (L4, L15, L16)
   that reached the plan and never reached the tree. The implementer prompt
   restated them; the ledger declared three mutations out of ten, and the seven
   undeclared ones are exactly where the gaps are. Extends **P-I**: a prompt
   carrying N named mutations gets N ledger rows, and a missing row is itself the
   finding.
2. **An equality assertion cannot be enumerated pairwise.** L16 transplanted
   §6A.9's three-row error-path criterion onto a status-only surface where no
   fixture can isolate one pair and one clause is provably redundant. New rule
   candidate: when a criterion enumerates the ways a **transitive** relation can
   fail, it enumerates the *states* (which pair holds), not the *clauses*, and
   the implementation carries only the independent clauses.
3. **A named mutation must be checked against the implementation it will meet.**
   L12 named `calculate_cost_per_worker_minute(...)` as the mutation, but that
   function quantizes to exactly the persisted value, so the mutation is inert by
   construction. The pin needs a fixture where persisted ≠ derived. Extends
   **P-Q**.
4. **A monolithic integration test cannot discharge an enumerated criterion.**
   C5's twelve values, C6's three clauses and C4's four rows were all folded into
   one test node, which is how "the assertion exists" and "the assertion can fail"
   drifted apart. Extends **P-V**: the parametrize id *is* the mapping evidence.

## Carry-forward dispositions

| Item | Destination |
|---|---|
| N2 (DELETE's hardcoded `item_unvalued` vs §11A.4's order) | phase 8 status query |
| N4 (dev-DB residue `ws_765225a0…`) | closeout purge |
| N5 (valuation payload field list) | phase 9 docs pass |
| N6 (five missing `reads_from` edges) | coordinator's post-approval graph pass |
| N7 (stale `domain-item-economics` anchor) | coordinator's post-approval graph pass |
| N8 (L21 Protocol shape) | closed — verified benign, no action |
