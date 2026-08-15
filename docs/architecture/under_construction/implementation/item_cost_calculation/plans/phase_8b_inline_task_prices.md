# Phase 8B — Inline item prices at task creation

```
plan: phase 8B
role: phase plan (coordinator-authored, round 18; the projection gates it)
date: 2026-08-15
state: IMPLEMENTED
```

## Goal

Ship §7B.6 (round 18, R18-1): the task-creation item block accepts the
valuation vocabulary (`expected_sale_price_minor`, `purchase_cost_minor`,
`currency` — mirroring `ItemValuationRequest`); on a NEWLY CREATED item with
any of the trio present, valuation version 1 is written through the
registered chain writer inside `create_task`'s transaction BEFORE the
§7B.5 auto-commit savepoint, so the task is priced in one call. On a
matched EXISTING item, inline prices REFUSE (conservative default — the
projection may card it). Legacy money keys stay rejected (`ITEM_MONEY_MOVED`
unchanged). **No new status, read surface, or schema.**

## Read first

1. Intention **§7B.6 (NEW, governing)**, §7B.5 as amended rounds 16,
   §11A.5 (R13-1 first-save-is-v1), §6A.9 (currency), §4.7A.
2. Master plan §6.4 (ITEM_MONEY_MOVED row — must keep biting), §6.5
   (`write_item_valuation_chain_in_session` in `_common.py`; the valuation
   audit events), §9 ALL rules — esp. expected-red (every named mutation
   names its red node id), deferral cap (zero deferrals — this phase is
   small), P-AB (if any helper gains a mode parameter, enumerate its
   gated effects), endpoint-boundary rule.
3. In-tree: `services/commands/tasks/requests/__init__.py`
   (`FindOrCreateItemInput` :25-50 with `reject_legacy_money`),
   `create_task.py` (the item-creation branch and the §7B.5 savepoint at
   :311-ff), `services/commands/item_economics/_common.py` (chain writer),
   `services/commands/item_economics/requests/__init__.py:116-121`
   (`ItemValuationRequest` — the vocabulary being mirrored).

## Dependencies

Phase 8 APPROVED (shipped). Phase 9 BLOCKED on this phase (the frontend
handoff documents the post-8B flow).

## Files expected to change

- `app/beyo_manager/services/commands/tasks/requests/__init__.py`
  (`FindOrCreateItemInput` += the trio; validation: currency required iff
  either amount present; ge=0; legacy rejection untouched)
- `app/beyo_manager/services/commands/tasks/create_task.py` (the valuation
  write on the item-creation branch, before the savepoint; the
  existing-item refusal)
- `routers/README.md` (task-creation body mirror row); tests
- NO migration; NO new files expected (the projection verifies)

## Implementation tasks (ordered)

1. Request vocabulary: the trio on `FindOrCreateItemInput`, mirrored
   semantics (`ge=0`; currency REQUIRED iff either amount present —
   pydantic 422, no domain identity; the §6.4 registry decides if one is
   needed).
2. The birth write: on the created-item path, when any trio field present →
   `write_item_valuation_chain_in_session(...)` (v1: no supersede, R13-1),
   `created_by_id = ctx.user_id`, the registered `item_valuation.created`
   audit event — all inside `maybe_begin`, BEFORE the auto-commit
   savepoint.
3. The existing-item refusal: matched item + any trio field → registered
   refusal identity (propose to the coordinator before use — the 4B N-c
   pattern), `ValidationError`, nothing written.
4. Router body mirror + README row.

## Acceptance criteria (the projection re-derives and hardens these)

**C1 — birth with prices:** create task with a new item + trio → exactly
one valuation row (v1: `superseded_at IS NULL`, `created_by_id` = creator,
figures/currency as sent); in an evaluable workspace the auto-commit fires
(committed evaluation exists, inputs from the valuation, no mirror — C5
row 4 discipline); in an unconfigured workspace the task is created, the
valuation EXISTS, and the skip line logs the resolver status. Named
mutation: delete the valuation write at its definition site → expected red
node named in the plan before implementation.

**C2 — no prices ⇒ byte-old behaviour:** trio absent → no valuation row,
the phase-8 `item_unvalued` flow intact (regression rows = the shipped
phase-7/8 suites stay green; collection delta reconciled).

**C3 — legacy keys still die:** the three legacy names each still 422
`ITEM_MONEY_MOVED` (P-G retention rows — the new trio must NOT soften the
bridge); mixed payload (legacy + new) also 422.

**C4 — existing-item refusal:** matched existing item (with and without a
current valuation) + trio → the registered identity, no valuation written,
no task created (or task created without prices? — the projection pins
the atomicity: recommend REFUSE THE WHOLE REQUEST, nothing written).

**C5 — currency/validation rows:** amount without currency → 422; negative
amounts → 422; currency alone (no amounts) → pinned by the projection
(recommend: accepted-and-ignored OR 422 — decide one).

**C6 — router boundary:** the task-creation body model carries the trio at
the HTTP boundary (phase-6 D6 discipline: deleting them there silently
drops client money — survival row) and OpenAPI advertises them.

## Notes

- The §7B.5 savepoint discipline is untouched: the valuation write is NOT
  inside the savepoint (a valuation that persists while the auto-commit
  rolls back is CORRECT — the price is real even when pricing the task
  fails; state this so nobody "fixes" it) — the projection verifies this
  reading of §7B.6 or cards it.
- Archgraph: delta = the reads/writes this adds to `command-task-create`
  (writes_to table-item-valuation via the shared chain) — small additive
  batch; orient on `command-item-economics-set-item-valuation`,
  `table-item-valuation`.

## Review log

(append-only)

## Amendments (projection r0, 2026-08-15) — GOVERNING

Where this block contradicts the sections above, THIS BLOCK WINS. Routed
from `handoffs/reviewer/2026-08-15_phase8b_projection_r0_handoff.md`
(18 rows; owner card 1 → **R18-3, branch B**). Intention §7B.6 carries the
lettered corrections (a) trio shape and (b) branch B; §4.7A and §11A.5(c)
corrected upstream (L10); `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`
registered (§6.4, L11 adapted for B).

### B1 (L1) — the trio's shape (supersedes "mirroring exactly")

All three fields OPTIONAL; `ge=0` on both amounts; `currency` required
**iff** either amount is present. Deliberate divergence from
`ItemValuationRequest` (whose `currency` is unconditionally required),
recorded in §7B.6(a).

### B2 (L2, decided) — C5 replaced by five exact rows

C5.1 expected+no-currency → 422 `item.currency`; C5.2 purchase+no-currency
→ 422; C5.3 **currency alone → 200, task created, ZERO rows in
`item_valuations` for the item (sole-predicate: zero, not "no current"),
status `item_unvalued`**; C5.4/C5.5 negative amounts → 422 `ge=0`. A
zero-amount price with currency is VALID (not a C5 row; optional C1 row —
implementer's call, declared either way).

### B3 (L3) — C1 replaced by six enumerated rows

The five reachable trio shapes (expected+purchase+currency with
purchase-term model → commits; expected+currency, no purchase term →
commits; expected+currency WITH purchase-term model →
`item_missing_purchase_cost` skip; purchase+currency →
`item_missing_expected_price` skip; full trio with mismatched currency →
`currency_mismatch` skip) + the unconfigured-workspace row. EVERY row: the
valuation row EXISTS (the phase's shared claim); skip rows assert the
verbatim `item_economics.auto_commit_skipped | … status=<value>` literal;
no status disjunctions; parametrize ids name these rows; rows 2 vs 3
differ ONLY in the model's terms (state it per P-M). Named mutation
(unchanged from the base plan): delete the valuation write at its
definition site → expected red = the C1 row-1 node id, stated in the
implementer's ledger BEFORE the run.

### B4 (L4 + R18-3) — C4 rebuilt on the owning harness, branch-B rows

- Harness: the fixture COMMITS before calling `create_task` so
  `maybe_begin` OWNS the transaction (precedent
  `test_phase7_evaluations.py:167`); `try/finally` teardown (rule 11½).
- Row 1 (refusal): matched item WITH a current valuation + trio →
  `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`, NO task row, NO TaskItem, NO
  valuation change, and **the matched item byte-unchanged** — send a
  different `designer` alongside the prices and assert the stored value is
  the ORIGINAL (find_or_create mutates the item before the refusal can be
  decided; the rollback must cover it).
- Row 2 (branch-B accept): matched item with NO current valuation + trio →
  task created, valuation written (v1 if never-valued; NEXT version if
  deleted/superseded-only — two sub-rows, the second asserting the chain
  grew rather than resurrected), auto-commit per the B3 rows.
- Named mutation: invert the current-valuation predicate at the refusal's
  definition site → row 1 and row 2 both redden (state both expected ids).

### B5 (L5) — C3 replaced by three exact rows + the validator-order pin

`reject_legacy_money` stays FIRST in definition order. (a) legacy + valid
trio → `ITEM_MONEY_MOVED`; (b) legacy + amount-without-currency →
`ITEM_MONEY_MOVED` (the order pin makes this deterministic); (c) legacy +
negative amount → pydantic's `ge=0` field error ALWAYS wins (field
constraints precede after-validators) — documented as accepted precedence,
not bridge failure. Named mutations, expected-red ids stated: (i) move the
currency-iff-amount validator ABOVE `reject_legacy_money` → row (b)
reddens; (ii) delete `reject_legacy_money` from `FindOrCreateItemInput` →
the three shipped `create-task-nested-item-present-nonnull` retention
nodes redden (`test_phase6_api_bridge.py:33-60` — extend that
parametrization, never duplicate).

### B6 (L6) — C6's two harnesses named; the OpenAPI clause DROPPED

(i) Field-presence introspection (`model_fields`, precedent
`test_item_economics_router.py:225-231`) on `_TaskItemInputBody`
(`routers/api_v1/tasks.py:95-114`, `extra="ignore"` — the silent-discard
hazard); (ii) endpoint survival (precedent
`test_phase6_api_bridge.py:105-133`): the trio survives
`PUT /api/v1/tasks` (:329-342, `exclude_unset=True`) to the domain
validator — the endpoint-boundary rule's row. The "OpenAPI advertises
them" clause is DELETED (no in-tree precedent; P-R). Named mutation:
delete the three fields from `_TaskItemInputBody` (definition site) → the
survival row reddens (expected id stated).

### B7 (L7) — the insertion point, pinned

ONE write site serving both item paths: after the TaskItem flush
(`create_task.py:306`) and before the savepoint (`try` at :308,
`begin_nested()` at :309), each branch setting a local newness/current-
valuation flag (`create_item_in_session` path :195-227 always creates;
`find_or_create_item` path :228-296 returns `was_created` :238). The
refusal check runs at the same site (it needs the resolved item).

### B8 (L8/L9) — the two stability sentences

(i) A failed birth write refuses the WHOLE request — safe by construction
(the item is new in this transaction, so no concurrent
`uix_item_valuations_current` holder exists; the CHECK is prevented at the
request boundary by B2) — stated so nobody wraps it in a savepoint. (ii)
The §7B.5 interaction rows hold by construction (projection L9, verified
against shipped code): pre-check sees the flushed valuation; savepoint
rollback leaves it; the auto path cannot mirror (inputs ARE the
valuation's). The C1 no-mirror assertion carries its P-J-5th-ext
non-vacuity companion: one explicit-commit row where an override DOES
mirror.

### B9 (L12/L13/L14/L17) — reality pins

- Archgraph: there is NO `create_task` node — 8B's delta is a **NEW node**
  (`command-task-create`) + edges (writes_to table-item-valuation via the
  chain; reads/writes it already had are recorded at the node's birth with
  accurate spans), one additive batch at checkpoint; never a delta to a
  node that doesn't exist.
- Citations: `FindOrCreateItemInput` class at :27; savepoint try/:308,
  begin_nested :309, block ends :324; §10A.3's cite is :37-39; the §6.5
  "inline chain writer" note is historical (extracted in phase 7,
  `_common.py:117-169`).
- README: the route section is **`PUT /api/v1/tasks`** (:2627). 8B adds
  its three `item.*` rows there and NOTHING else — the table's
  pre-existing drift (missing item_zone/can_have_upholstery/notes/steps/
  shopify_preorder rows; six phantom item_issues fields) routes to phase
  9's R18-2 deliverable. NO regeneration attempt (no generator exists
  in-tree despite the banner).
- Phase-6 structural guard: `test_phase6_api_bridge.py:87-97` asserts the
  legacy tokens appear nowhere in `create_task.py` — never name a local
  `item_currency`.

### B10 (L15/L16/L18) — routed to R18-2 (phase 9), no 8B logic

`quantity` does not participate in economics (a valuation is per-item;
1000 stays 1000 at quantity 5) — a handoff sentence, no code. Multi-item
is moot (the payload carries ONE item, always PRIMARY). The create
response carries no priced-or-not signal — the handoff documents the
two-call flow (create → GET budget-status). All three added to the
phase-9 R18-2 scope block.

## Review log

(append-only)

- **2026-08-15 — projection r0 (Claude): AMENDMENTS_REQUIRED** — 18 rows
  (5 H, 6 M, 7 L), 1 owner card. Handoff:
  `handoffs/reviewer/2026-08-15_phase8b_projection_r0_handoff.md`. Standouts:
  the "exact mirror" gloss was false against shipped code (PUT's currency
  is unconditionally required); C1's "auto-commit fires" was false for 3
  of 5 reachable shapes; C4's atomicity needed the maybe_begin OWNER
  harness + the item-byte-unchanged row (find_or_create mutates before
  the refusal); the mixed-payload row had a definition-order coin flip;
  currency-alone decided accepted-and-ignored (a currency-only row is
  impossible at the DB and 422 reproduces §10A.3's hazard). L9 verified
  the savepoint interaction by construction. Coordinator routed all 18
  same day: owner card → R18-3 (branch B); §7B.6 lettered (a)/(b);
  §4.7A + §11A.5(c) corrected; `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`
  registered; this GOVERNING block B1–B10. Gate holds (non-empty ledger —
  no self-retirement); implementer prompt
  `prompts/implementer/2026-08-15_phase8b_implement_r1.md`.

- **2026-08-15 — implementer r1 (Codex): IMPLEMENTED** — shipped the
  optional inline valuation trio and currency-iff-amount validation, the
  pre-savepoint valuation-chain birth write, current-valuation refusal for
  matched items, router boundary fields, and the three task-route README
  rows. Added the 21-node phase harness (C1–C6, C3 validator order, C4
  owning teardown, and B8 explicit-commit companion) and expanded the
  existing bridge parametrization by 24 retained-key nodes. Focused phase
  plus retention scope: **66 passed**. Full non-E2E foreground: **2183
  passed / 23 established failures / 1 deselected**, 2207 collected; the
  sorted failure IDs match the established 23-item baseline. Ruff clean;
  database at `c1d2e3f4a5b6` head; no migration. The complete mutation
  ledger, per-row expected reds, mutant/restored hashes, graph revision,
  and write perimeter are recorded in the implementer handoff.

- **2026-08-15 — review r1 (Claude): CHANGES_REQUESTED** — 2 should-fix, 3
  notes, zero blocking. Handoff:
  `handoffs/reviewer/2026-08-15_phase8b_review_r1_handoff.md`. The mechanism
  is CORRECT on every branch re-derived, including the two shapes no test
  reaches; both findings are test-integrity, not behaviour.

  - **S1 (should-fix, B4 second sub-row missing) — the `superseded_at IS
    NULL` conjunct of the refusal predicate is uncovered.** Deleting
    `ItemValuation.superseded_at.is_(None)` from `create_task.py:331` leaves
    the whole 66-node focused scope GREEN (reviewer mutation M6). B4 required
    TWO branch-B sub-rows ("deleted **or superseded**-only"); only the
    deleted-only row (C4 row 3) shipped, and it exercises the `is_deleted`
    conjunct alone (M7 reddens it — that conjunct IS covered). The state is
    reachable through three shipped commands — `set_item_valuation` ×2 then
    `delete_item_valuation` leaves v1 superseded + v2 deleted and NO current
    valuation — and §7B.6(b) requires ACCEPT-and-grow there. A reviewer probe
    built exactly that state: shipped code accepts and writes v3 (PASS);
    under M6 it raises `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` (FAIL). The
    R15-1-adjacent hazard the prompt named is real and currently unguarded.
    Correction: add the missing sub-row to C4 (seed through the production
    commands, not hand-built rows — charter rule 3), and name M6 as its
    expected-red mutation.
  - **S2 (should-fix, charter rule 11½) — C4 rows 2 and 3 leak committed rows
    on their own failure path.** Both call
    `_cleanup_committed_workspace(db_session, workspace.client_id,
    user.client_id)` from `finally`; when the body raises, the owning
    `maybe_begin` has already rolled back and EXPIRED those ORM instances, so
    evaluating `workspace.client_id` triggers a lazy reload that raises before
    a single DELETE is issued. Reproduced deterministically under M2: the
    named C4 rows redden and every seeded workspace survives (8 leaked across
    this review's probes, removed by hand). C4 row 1 is immune — it captures
    `workspace_id` / `user_id` into locals BEFORE the `try`. Correction: give
    rows 2 and 3 row 1's shape (capture the ids first); the helper itself is
    fine.
  - **N1 (note)** — the implementer handoff states the inverted-predicate
    mutant's four `phase8b` workspaces "were removed by the owning test
    teardown helper after the probe". Not reproducible: the teardown raises
    before deleting (S2). The rows were evidently removed some other way. 4B
    review L5 stands — a state claim needs a state assertion behind it.
  - **N2 (note, graph — READ-ONLY, human-adjudicated)** — the pending
    `command-task-create` node's anchors are partly inaccurate. Node evidence
    `create_task.py:69-580` starts three lines above the function (`:69` is
    the module-level `logger =`; `async def create_task` is `:72`). Edge
    `writes_to table-task` cites `:105-139`, which EXCLUDES the
    `ctx.session.add(task)` / `flush()` at `:182-183` that the edge's own
    summary asserts (`task = Task(` is `:113`). The two edges recording 8B's
    NEW behaviour are exact (`table-item-valuation` `:317-353`,
    `table-task-item` `:307-315`). Corrected spans for the human's
    post-approval pass: node `:72-580`; `writes_to table-task` `:113-183`.
  - **N3 (note, ledger discipline)** — mutant M1's declared "1 failure" is the
    named node only; re-run over the focused scope the same deletion reddens
    9 nodes. Four of five declared mutant hashes reproduced BYTE-IDENTICALLY
    from their descriptions (M2 `f0776418…`, M3 `f4670bde…`, M4 `dbfe1548…`,
    M5 `aafc1f53…`); M1's did not, because "delete the write at its
    definition site" does not pin the deletion boundary. Ledgers should state
    the run scope behind "observed red" and pin deletion boundaries by line.

  **Verified correct (settled — cheap for the re-review):** all seven final
  hashes recomputed byte-identical and `git status` clean; suite re-run in
  foreground 2183/23/1, 2207 collected, sorted failure IDs byte-identical to
  the phase-1 list (zero regressions); +45 reconciled exactly by
  `--collect-only` (phase file 21; bridge 21→45 = +24); focused 66 passed;
  ruff clean on all five touched Python files; DB at `c1d2e3f4a5b6` head;
  zero `phase8b` residue by state query after restoration. All five declared
  mutations re-run and every named expected-red node observed red. §7B.5/B8(ii)
  verified LIVE, not only by construction: a reviewer probe that writes an
  evaluation inside the savepoint then raises leaves the task created, the
  evaluation gone and the inline valuation intact (4200, `superseded_at IS
  NULL`). Effect set matches the PUT path exactly (chain write + one
  `item_valuation.created` audit; no history record, no workspace event, no
  preview persisted). Refusal identity, message shape and §6.4 registry entry
  match. Bridge unsoftened: legacy tokens absent from `create_task.py`, the
  phase-6 structural guard green, C3 rows 1–3 exact incl. the documented
  `ge=0`-beats-bridge precedence. C5.3's sole-predicate form is non-vacuous
  (adding `currency is not None` to `inline_price_requested` reddens it).
  `get_db` yields an untransacted session, so `maybe_begin` OWNS in
  production — B4's owning harness is production-faithful and C4 row 1's
  `designer` assertion tests production's rollback. README carries exactly the
  three `item.*` rows under `PUT /api/v1/tasks`. Graph read-only, zero delta,
  174/260 rev `53fdbc78…`, 5 pending HELD.

  **Residual coverage observation (no action):** every inline-price row routes
  through `find_or_create_item`; the `create_item_in_session` branch (no
  article_number, no sku) is never exercised with the trio. B7 deliberately
  made the write site shared and post-branch, so both paths converge — noted,
  not a finding.

## Amendments (fix r2, routed from review r1, 2026-08-15) — GOVERNING

Routed from `handoffs/reviewer/2026-08-15_phase8b_review_r1_handoff.md`
(0 blocking / 2 should-fix / 3 notes, 0 owner cards — both should-fixes
TEST-SIDE, local to `test_phase8b_inline_task_prices.py`).

### F1 (S1) — C4 row 4: the superseded-only sub-row B4 required

Seed the state through PRODUCTION COMMANDS (charter rule 3, the reviewer's
probe is the recipe): `set_item_valuation` (v1) → `set_item_valuation`
(v2 supersedes v1) → `delete_item_valuation` (v2). Assert the pre-state
has NO current valuation (v1 superseded-not-deleted; v2 deleted-not-
superseded), then `create_task` with the trio ACCEPTS and the chain GREW
to three rows with the new row current (§7B.6(b)). **Expected-red
mutation M6:** delete `ItemValuation.superseded_at.is_(None)` at
`create_task.py:331` (definition site, that line exactly) → this row
reddens. (Reviewer-verified: shipped code passes the probe; M6 flips it to
the refusal — the conjunct is correct and was merely unguarded.)

### F2 (S2) — C4 rows 2/3 adopt row 1's capture-locals shape

Capture `workspace.client_id` / `user.client_id` (and any other instance
attribute the assertions or cleanup need) into PLAIN LOCALS before the
`try` — the rollback on the failure path expires the ORM instances and
the `finally` currently raises inside attribute loading before a single
DELETE runs (reviewer-reproduced under M2: residue grew 2→8 workspaces;
hand-cleaned). `_cleanup_committed_workspace` itself is correct.
Verification: after the fix, run row 2 once under the M2 mutant and
assert-by-state-query ZERO `phase8b` residue after the red (the 11½
second-failure-mode check, done once and recorded).

### F3 (N1/N3) — ledger discipline (record-side, ride-along)

The fix handoff's ledger: deletion mutations pinned by LINE RANGE
(P-I 10th ext — M1's unpinned boundary was the one non-reproducing hash);
"observed red" states its SCOPE (M1's true focused-scope blast radius is
9 nodes); any environment/state claim carries a state query, never an
inference from what the harness should have done (N1, 4B L5).

### F4 (N2) — held for the post-approval pass (no fix-cycle action)

Corrected spans for the 5 pending graph items, recorded for the
coordinator: node `command-task-create` → `:72-580` (def line, not the
logger); `writes_to table-task` → `:113-183` (the add/flush the summary
asserts); `reads_from table-item` acceptable-loose (`:236-248` is the
precise core); the two 8B-behaviour edges exact as recorded. The phase-7
`item_valuations` residue row (`ival_01M012JEV…`) routes to the existing
rule-11½ maintenance record — NOT this phase's.

## Review log addendum

- **2026-08-15 — review r1 CONSUMED by the coordinator.** Perimeter exact
  (2 docs + handoff; app/+archgraph byte-identical to `513856d`).
  Production verified correct on every branch incl. two no-test-reaches
  shapes; the §7B.5 survival property now has a LIVE observation; effect
  set diffed against the PUT path (exact); M2–M5 byte-reproduced, M1
  boundary unpinned (P-I 10th ext born); reviewer mutations M6–M9 mapped
  the predicate's conjunct coverage precisely. §9 += per-alternative
  rule, rule-11½ capture-locals mode, P-I 10th ext, birth-anchor rule.
  Fix r2 = F1+F2 (+F3 record discipline), test-side only; prompt
  `prompts/implementer/2026-08-15_phase8b_fix_r2.md`.
