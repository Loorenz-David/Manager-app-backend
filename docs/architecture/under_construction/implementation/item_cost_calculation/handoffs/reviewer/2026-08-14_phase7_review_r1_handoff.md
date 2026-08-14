---
plan: phase 7 (evaluations — commit/supersede, projections, auto-commit)
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-14
actor: reviewer (Claude Opus 5)
---

# Phase 7 review r1 handoff

**Verdict: CHANGES_REQUESTED** — 3 blocking, 5 should-fix, 8 notes (counted from
the ledger table below, not prose).

The commit procedure itself is, with one exception, correct: I re-derived §7B.1
step by step and then exercised every C1–C14 row by hand, and the *behaviour*
holds — admission, the resolver gate and all ten §6.4 translations, snapshot
immutability, the recompute decision, the mirror predicate's `None == None`
semantics, promotion's byte-stability, the savepoint, the log lines, the
TASK-linked history reaching the team flow, the read's four ordering pins, and
all three lock classes (task `FOR UPDATE`, valuation `FOR UPDATE`, both config
chains `FOR SHARE`) really do what the intention says.

Two things stop approval. One real defect: **creating a projection silently
rewrites the item's real price** (B1). And the phase's proof: roughly **8 of ~60
enumerated criterion rows have an arbiter** in the shipped suite (B2) — I had to
write the other ~50 myself to find out the implementation was right.

⚠ OWNER DECISIONS REQUIRED (0) — nothing here needs an owner answer. Every
finding has a determined correction in the intention or the plan.

---

## Findings ledger

| id | sev | title | authority |
|---|---|---|---|
| B1 | blocking | Projection creation advances the valuation chain | §7.3, §7B/§7B.1 s9, §7B.4, HC-2, C8 |
| B2 | blocking | ~52 of ~60 enumerated criterion rows have no arbiter | charter rule 2; P-V 2nd/3rd ext; P-I 6th ext |
| B3 | blocking | C8 byte-unchanged asserted from the same session | A3/C8 (explicit prohibition) |
| S1 | should-fix | C2's prescribed DB-conflict arbiter cannot raise the identity | A3/C2, P-S, P-T |
| S2 | should-fix | C11's named mutation is inert against the obvious observable | P-T, charter rule 11 |
| S3 | should-fix | C5 row 6's named mutation is inert unless the fixture omits the override | P-T, P-Q |
| S4 | should-fix | Tracker row's suite numbers are wrong (both figures) | P-L |
| S5 | should-fix | Promotion's cross-task guard keys on an input the router never sends | P-R, P-S |
| N1–N8 | note | see Notes | — |

### B1 (blocking) — creating a projection silently supersedes the item's current valuation

`commit_item_cost_evaluation.py:342-355` runs the §7B.4 mirror write **without
gating on `kind`**. `create_item_cost_projection.py:58-76` routes through the
same helper with `kind=PROJECTION`, so any projection carrying an overridden
`expected_sale_price_minor` / `purchase_cost_minor` advances the **valuation**
chain: the item's real current price is closed (`superseded_at` set) and
replaced by the speculative figure, attributed to the projecting user.

Authority: §7.3 (projections are speculative, freely soft-deletable, and never
reach operational reads — HC-2); §7B.4's mirror rule belongs to *the commit
transaction* (§7B.1 step 9); plan C8 requires projection creation to do exactly
two things — compute via the calculator and persist `kind = projection`.

Observed — probe `test_probe_projection_with_override_must_not_touch_the_valuation`:

```
AssertionError: projection advanced the valuation chain: 2 valuation rows,
current price now 2000
```

(fixture valuation 1000; projection created with `source: scratch`,
`expected_sale_price_minor: 2000`.)

The damage is **not reversible**: soft-deleting the projection does not restore
the price, and superseded valuation rows are never deletable (§7.5), so the
speculative figure is permanently part of the item's price history.

**Correction:** gate the mirror block on
`kind is ItemCostEvaluationKindEnum.COMMITTED`. Promotion is unaffected — it
carries `kind=COMMITTED` and *should* mirror.

**Criterion to add — C5 row 7:** a projection with an override differing from
the current valuation writes **no** valuation row (assert the current valuation
row's `client_id` and figures are unchanged, and that exactly one valuation row
exists). Named mutation: removing the `kind is COMMITTED` guard at the
definition site in `commit_item_cost_evaluation.py` must redden exactly this row.

**Independent corroboration:** the phase-7 architecture-graph delta records
`writes_to → table-item-valuation` for `commit_item_cost_evaluation` and for
`promote_item_cost_projection`, and **not** for
`create_item_cost_projection` — the inferring pass modelled the intended
design; the code deviates from it.

### B2 (blocking) — the criteria have almost no arbiters

Shipped proof for phase 7: **4** integration tests
(`test_phase7_evaluations.py`) plus **21** router nodes. The amended C1–C14
enumerate roughly **60** rows. The row-coverage map is below; the short version
is that one monolithic integration test is standing in for C1, C2, C8, C10 and
C14 at once, and C3–C7, C9, C11 and C12 have essentially nothing.

Authority: charter rule 2 (enumerate, never sample); **P-V second extension** —
"a monolithic integration test cannot discharge an enumerated criterion — the
parametrize id IS the mapping evidence"; P-V third extension; P-I sixth
extension (N named mutations ⇒ N ledger rows).

**This is a proof gap, not a correctness gap.** I built the missing rows and ran
them: every one of them passes against the shipped implementation except B1's.
The two probe files are attached (see *Probe artifacts*) and are close to
drop-in — the fix cycle should adopt them rather than re-derive them, with
parametrize ids naming the authority rows per P-V's standing form.

### B3 (blocking) — C8's byte-unchanged check uses the same session

`test_phase7_evaluations.py:135-144` reads the projection row before and after
the promote through the same `db_session`, i.e. the same identity map. A3/C8 is
explicit: "read from a SECOND session before and after the promote, equal on
all columns **including `updated_at`** … a stale identity-map comparison does
not discharge this."

Compounding: the shipped `db_session` fixture (`tests/conftest.py:46-50`) rolls
back and never commits, so a second session cannot see the rows at all. The
criterion is unsatisfiable under that fixture and needs the committing harness
phase 4 already established (`database._session_factory()`,
`test_phase4_fix_coverage.py:508-582`).

I verified the underlying property by inspection: the promote path only *reads*
`source_evaluation`; no ORM attribute is assigned, so `onupdate` cannot fire.
The property holds — it just has no arbiter.

### S1 (should-fix) — C2's prescribed DB-conflict arbiter cannot produce the identity

A3/C2 directs the row to "drive the conflict from a second session doing a
direct `ItemCostEvaluation` INSERT … and assert the exact translated identity".
I built exactly that (`test_probe_c2_db_conflict_surfaces_the_translated_identity`)
and the identity never fires.

Mechanism: the direct INSERT takes an FK **`KEY SHARE`** lock on the `tasks`
row. That conflicts with the commit's step-1 `FOR UPDATE`, so the commit blocks
*before* its S1 — observed, bounded at 0.4 s. When the intruder commits and the
commit proceeds, S1 now sees the intruder and supersedes it normally. Final
state: two rows, exactly one current (the command's), intruder superseded, **no
error**.

So the recorded P-S judgment ("the DB path is UNREACHABLE from every phase-7
surface") is **correct and now empirically confirmed** — but it is stronger than
recorded: the path is unreachable from the prescribed *test* shape too. Delete
the fixture direction; discharge `ITEM_COST_CONCURRENT_COMMIT` with the recorded
note plus the `INDEX_IDENTITIES` registration (both present).

### S2 (should-fix) — C11's named mutation is inert against the obvious observable

C11 says "deleting `.with_for_update()` at the definition site must redden it".
It does not, for the natural counterparty. With mutant
`7f55ae58…98df` applied, an observable whose counterparty holds
`SELECT … FROM tasks … FOR UPDATE` stayed **green**, because the evaluation
INSERT's own FK `KEY SHARE` lock still conflicts with the counterparty. A
"two concurrent commits both succeed" observable also stayed green.

The mutation bites only when the counterparty holds **`FOR NO KEY UPDATE`** —
which `FOR UPDATE` excludes and FK `KEY SHARE` does not. Then the mutant fails
with `DID NOT RAISE TimeoutError`.

Authority: **P-T** — a lock criterion names *which counterparty acquires which
lock*, because FK `KEY SHARE` is a counterparty PostgreSQL supplies for free.
C11 must name the counterparty's lock mode. The working observable is in the
attached probe.

### S3 (should-fix) — C5 row 6's named mutation is inert unless the fixture omits the override

Deleting `.with_for_update()` from the step-4 valuation read (mutant
`9201108b…211c`) left my first C5r6 observable **green**: the commit's own
mirror `UPDATE` on that same row re-acquires a conflicting lock and masks the
deletion. It reddened only after the blocking commit was changed to carry **no
override** (hence no mirror write).

C5 row 6 must pin the fixture: the commit used to prove the step-4 lock carries
no price override. (The semantic half of the row — the manager's figures winning
under both orderings — additionally needs a seam in the commit to pause between
step 4 and step 9; without one, only the lock observable is buildable.)

### S4 (should-fix) — three documents, three number sets

My numbers, read off my own foreground runs:

| set | mine |
|---|---|
| phase-7 focused surface (router 88 + phase-7 integration 4) | **92 passed** |
| the four `create_task` integration files | **29 passed** |
| `test_create_task_sku_template_integration.py` alone | **5 passed** |
| phase-5 focused valuation suite (P7-8) | **54 passed** |
| full non-E2E | **2037 passed / 23 failed / 1 deselected** |

Failure set **byte-identical** to the phase-1 list: sorted diff over 23 entries,
zero differences. Suite delta reconciles exactly: 2060 − 2035 = **+25** = 21
router nodes (5 `_ROUTES` rows × 4 role-gate nodes + 1 completeness arbiter) + 4
integration.

- The **handoff** is correct (2037/23/1; its 97 = 92 + the 5-test SKU file).
- The **plan Review log's 92** is correct for its stated scope.
- The **tracker row is wrong on both figures** ("focused 94", "full 2034/23/1").
  Master plan §4 row 7 needs correcting (P-L).

### S5 (should-fix) — promotion's cross-task guard keys on an input the router never sends

`promote_item_cost_projection.py:32-34` reads
`ctx.incoming_data.get("task_client_id")`, but
`route_promote_item_cost_projection` (`item_economics.py:348-354`) sends only
`{"client_id": …}`. The URL is projection-keyed and the command promotes onto
`projection.task_id`, so C8's "promote a projection belonging to ANOTHER task →
`NotFound`" row cannot be reached through the real surface — only by
hand-feeding the service a key the HTTP boundary cannot produce (P-R).

Either delete the dead branch and discharge the row with a recorded note (P-S,
as for the ambiguous-group row), or restate the row as the reachable equivalent
(cross-workspace, already covered by the workspace filter).

### Notes

- **N1** — `CreateItemCostProjectionRequest.validate_source_projection_id`
  (`requests/__init__.py`) is a no-op validator returning its input unchanged;
  the real check lives in `parse_create_item_cost_projection_request`. Dead
  scaffolding (charter rule 4).
- **N2** — `auto_commit_item_cost_evaluation_in_session`'s docstring says "never
  raises", but it contains no handler; the savepoint and `except` are in
  `create_task.py`. Behaviour correct, docstring misleading.
- **N3** — The no-PRIMARY-item auto-path skip logs the literal token
  `"no_primary_item"`, which is not an `EconomicsStatusEnum` value. C9's tenth
  row asks for "the status token"; the vocabulary has no member for this state.
  Register one or pin the literal in the criterion.
- **N4** — C10's seam: the test monkeypatches
  `…tasks.create_task.event_bus.dispatch`, but `event_bus` is a shared **module
  object**, so the patch is global rather than per-module. It works (the auto
  path is the only dispatcher of that event) but cannot discriminate which
  module dispatched — which is the property A3/C10 asked the seam to prove.
- **N5** — Graph vocabulary: `list_task_evaluations` is registered as a
  `command` node although it lives under `services/queries/` and the graph
  carries a `projection` node type (9 members). Human adjudication only —
  I changed nothing.
- **N6** — `_load_preview_inputs` (auto-path pre-check, unlocked) and
  `_load_live_inputs` (commit, `FOR SHARE`) are two loaders over the same
  configuration. They agree today (same predicate, same resolver, same
  `today_utc()`); a future divergence would surface as a silent auto-commit
  skip, never an error. Worth a structural pin in phase 8 or 9.
- **N7** — The P-Z property row
  (`test_phase7_extracted_valuation_chain_preserves_set_supersede_delete_invariants`)
  asserts `superseded_by_id is not None` but never that it points at the correct
  successor. Verified correct by probe; the row itself is weak.
- **N8** — Double blank line inside the function at `create_task.py:308-309`
  (cosmetic; ruff passes).

---

## Row-coverage map (C1–C14 as AMENDED — A3/A4 win)

`—` = no arbiter in the shipped suite. Ids are observed
(`--collect-only`), not predicted.

| row | arbiter |
|---|---|
| C1 immutability (supersede valuation + both chains, rederive bit-for-bit) | **—** |
| C1 row 1b (persisted ≠ derived rate → snapshot = DERIVED) | `test_phase7_commit_projection_promotion_and_read` (l.122); **mutation M5 reddens it** |
| C2 second commit succeeds / one current / back-linked | **—** |
| C2 DB conflict path | **—** (and unbuildable as specified — S1) |
| C3 nine admission rows | 1 of 9 (`PENDING`, implicit in the monolith) |
| C4 no active PRIMARY | **—** |
| C4 `evaluation.item_id == P.item_id` | **—** |
| C5 rows 1–5 (mirror fires / no-fire / `None==None` / auto path / concurrent valuation) | **—** |
| C5 row 6 (committed mid-flight) | **—** (deferred; run by me — S3) |
| C5 row 7 (projection must not mirror) | **does not exist** — B1 |
| C6 five §7C.2 rows | **—** |
| C7 seven input rows | **—** |
| C8 promotion byte-unchanged | monolith l.135-144, **same session** — B3 |
| C8 three refusal rows + delete-never-touches-committed | **—** |
| C9 success row | `test_phase7_create_task_auto_commits_and_dispatches_after_task_transaction` |
| C9 TEN §11A.4 pre-check rows + `auto_commit_skipped` line | **—** |
| C9 savepoint mutation fixture | `test_phase7_auto_commit_overflow_rolls_back_savepoint_and_keeps_task`; **M7 reddens** |
| C10 event dispatched after tx | monolith / auto-path test (seam caveat N4) |
| C10 history record in `get_task_flow_records`, audit rows, nothing-on-failure | **—** |
| C11 task lock | **—** (deferred; run by me — S2) |
| C12 two chains × two orderings | **—** (row 1 run by me; row 2 = phase-4 `test_c6_serial_delete_guard_rechecks_all_evaluation_references`) |
| C13 five routes, both role gates, completeness arbiter | `test_every_item_economics_route_rejects_worker_and_seller[post-commit\|get-evaluations\|post-projections\|delete-ice_1\|post-promote-worker\|-seller]`, same for `…retains_admin_and_manager_access[…-admin\|-manager]`, `test_router_route_pairs_match_the_authoritative_route_table`; **M6 reddens** |
| C14 envelope + marker row | monolith l.146-166 |
| C14 three ordering pins + equal-`created_at` tie-break | **—** |

---

## Mutation ledger

Baseline hashes (= checkpoint `a7f421f` blobs):

- `commit_item_cost_evaluation.py` = `7711fd63a08ad6b59588c99a54f05f72b73ccc2ae31f778ea3daa2ae42ff3a37`
- `create_task.py` = `f1daef7f3e40456eeefa3cd6d6a3518c4f1abffc0eb44710de8e2d1b4205e4c8`
- `item_economics.py` (router) = `87fcb318050bb089e3e8a5f101e2c47a7def0f68ed85da17d016d4ae544840ae`

| # | row | site | mutant hash | observed red set (node ids) |
|---|---|---|---|---|
| M1 | C11 task lock | delete `.with_for_update()`, `_load_task_and_primary` (definition site) | `7f55ae58ae7f38ed97b82512a3eb17f521c002dfaf57c2a21896972a5bc698df` | `test_probe_c11_second_commit_blocked_while_task_locked` (**only** with a `FOR NO KEY UPDATE` counterparty — S2) + blast radius `test_probe_c2_db_conflict_surfaces_the_translated_identity`. Did **not** redden `test_probe_c11b_two_concurrent_commits_both_succeed_via_the_task_lock`. |
| M2 | C5 row 6 valuation lock | delete `.with_for_update()`, `_load_current_valuation` (definition site) | `9201108bb7f2f96ba42657da37428211615fd3040754a9988e487adebedf211c` | `test_probe_c5r6_commit_blocked_while_valuation_locked` (**only** with a no-override commit — S3) |
| M3 | C12 BASIS chain | delete `read=True`, basis resolution | `2095fc05595ae8007c61b169e235005f8250c64ebc3a2666602d12717ff56bc4` | `test_probe_c12_row1_delete_first_commit_blocks_then_refuses[basis]` — **row 1 only**, `[model]` stayed green |
| M4 | C12 MODEL chain | delete `read=True`, model resolution | `750d1fc8b56695049387f0c372d839c2750fe6633b8bd23a5def3c5b486d0835` | `test_probe_c12_row1_delete_first_commit_blocks_then_refuses[model]` — **row 1 only**, `[basis]` stayed green |
| M5 | C1 row 1b | `cost_per_worker_minute_minor_snapshot=rate` → `getattr(basis, "cost_per_worker_minute_minor", rate)` | `6f58123e25d9c8e158237f6d357a37ade16d8699d6a3522bc2d48f545e4c3202` | `test_phase7_commit_projection_promotion_and_read`, `test_probe_c1_snapshot_immutability_after_superseding_everything` |
| M6 | C13 arbiter (re-run) | extra `GET /phase7-route-mutation` route | `28dc95698b1aa226b2102d129242842a36baf3e70c7e1d160c5d29ab3d903c9a` | `test_router_route_pairs_match_the_authoritative_route_table` |
| M7 | C9 savepoint (re-run) | `async with ctx.session.begin_nested():` → `if True:` (definition site) | `e190976f2cc3b3935c100efda1c88fb9f7beb7f163aacd8c222e001ea546ad56` | `test_phase7_auto_commit_overflow_rolls_back_savepoint_and_keeps_task` (SAWarning "state changed on a non-active transaction") |

**M6/M7 hash note (P-I seventh extension):** my M6 mutant hash differs from the
implementer's declared `ce5d6486…8116` and my M7 from `51588d73…0589` because
the inserted mutant text differs; same defect class, different mutant. The
implementer's declared pairs were not re-derivable byte-for-byte, only
re-confirmed behaviourally.

**Reversion proven.** After every mutation the file was restored and re-hashed
to its baseline value above; final state:
`git diff --stat -- app/beyo_manager/` is **empty**, i.e. every production file
is byte-identical to the `a7f421f` blob.

C12 row 2 (commit resolves first, delete second → `..._IN_USE`) was **not**
mutated: per A4/C12 it is covered by the free FK `KEY SHARE` and is already
arbitrated serially by phase 4's
`test_c6_serial_delete_guard_rechecks_all_evaluation_references`.

---

## Write perimeter and probe declaration

**Documents written this session (the entire perimeter):**

- `docs/.../plans/phase_7_evaluations.md` — Review log entry appended; header
  `state:` → `CHANGES_REQUESTED`
- `docs/.../master_plan.md` — §4 tracker row 7 only
- `docs/.../handoffs/reviewer/2026-08-14_phase7_review_r1_handoff.md` — this file

**No production or test file in the repository was left modified.**

**Probe artifacts (created, run, and REMOVED from the tree):**

- `app/tests/integration/services/commands/item_economics/test_reviewer_r1_probe.py`
  — 31 nodes covering C1, C2, C3 (all nine), C4, C5 rows 1–4 + the B1 row, C6/C7
  (ten parametrized refusal rows), C8, C9's skipped line, C10, C14's ordering
  pins. Non-committing (`db_session`).
- `app/tests/integration/services/commands/item_economics/test_reviewer_r1_concurrency_probe.py`
  — 6 nodes: C11 (+ the two-concurrent-commits variant), C5 row 6, C12 row 1
  × both chains, C2's DB path. Committing harness with per-test `try/finally`
  teardown; every wait bounded at 0.4 s (P-T r2-L3).

Both files were moved out of the repository at close and preserved at
`…/scratchpad/probes/` for the fix cycle to adopt. **The fix cycle should adopt
them rather than re-derive them** (B2).

**Database side effects — restored exactly as found.** All seven economics
tables were 0 rows before my session and are **0 rows after** (verified
post-run). The concurrency probes commit; their teardown deletes evaluations,
terms, valuations, config rows, task/item/task_item, audit logs, history records
and links, then the user and workspace. `workspaces` moved 7859 → 8091 = **+232
over two full non-E2E runs = ~116/run**, exactly the known non-economics class
(§10; phase-4 r3 N11) — **residue scope: the nine tables named above; no
economics residue**. Configured DB left at head `be9dfe42a035`; no migration was
added or run.

**Architecture Graph — READ-ONLY, zero delta.** Status at exit: valid, **166
nodes / 239 edges**, 0 stale, **52 pending**, revision
`0a71061554fa2123d7e2fba7ff853c328fb1405676194dd0d2cc7f067938266c` — exactly as
declared. 50 pending items carry the phase-7 timestamp, 2 are the pre-existing
pair. **Nothing was adjudicated, promoted, rejected or edited.**

Spot-check of 5 sampled items — all anchors accurate and all claims true
(phase-4's P4-6 lesson is respected: edges carry write-site evidence, not
blanket router anchors):

1. `create_item_cost_projection --writes_to--> table-item-cost-evaluation` —
   anchor `create_item_cost_projection.py:23-82` ✓
2. `commit_item_cost_evaluation --writes_to--> table-item-valuation` — anchor
   `_commit_item_cost_evaluation_in_session:203-355`; the mirror write is at
   342-355, inside the span ✓
3. `list_task_evaluations` (node) — anchor
   `list_task_evaluations.py:34-89` ✓; type `command` questioned in N5
4. `POST …/projections/{client_id}/promote` (node) — anchor
   `item_economics.py:348-354`; decorator at 348, file ends at 354 ✓
5. `promote_item_cost_projection --writes_to--> table-item-valuation` — anchor
   `promote_item_cost_projection.py:22-50` ✓ (promotion mirroring is correct)

The "conflicting-canonical-relationship" contradictions the tool reports on the
multi-target `writes_to` edges are a tool artifact (it treats a second
`writes_to` from one source as canonical competition), not a modelling error.

**No anchor corrections are needed; no spans service is required.**

---

## Lessons for the plans (coordinator folds upstream)

1. **L1 — a lock criterion owes its counterparty's lock MODE, not just its
   identity.** P-T already says "name which counterparty acquires which lock";
   phase 7 shows the sharper form: name the *mode*, because FK `KEY SHARE` is
   acquired for free by any INSERT referencing the row and it masks a deleted
   `FOR UPDATE` from every naively-worded counterparty. Both C11 and C5 row 6
   shipped named mutations that are inert against the obvious observable
   (S2/S3). Proposed standing rule: **P-T third extension** — for a row lock on
   a table that other statements in the same transaction also reference, the
   criterion names a counterparty mode the *mutation* changes the answer for,
   and the plan states which competing lock would otherwise mask it.

2. **L2 — a criterion may not prescribe a fixture whose mechanism has not been
   checked against PostgreSQL's lock matrix.** A3/C2 prescribed a direct
   second-session INSERT to raise `ITEM_COST_CONCURRENT_COMMIT`; that INSERT's
   own FK lock makes the identity unraisable (S1). Extends P-Q's "check a named
   mutation against the implementation it will MEET" to *fixtures*: check a
   prescribed fixture against the engine semantics it will meet.

3. **L3 — a second-session criterion owes its harness.** A3/C8 demanded a second
   session; the shipped `db_session` fixture never commits, so the criterion was
   unsatisfiable as written and shipped satisfied by the very identity-map
   comparison it forbids (B3). P-R's form ("name the harness in the plan, the
   way §10 names the DB recipe") should extend to cross-session criteria —
   naming `database._session_factory()` + the committing-teardown recipe.

4. **L4 — a shared helper that performs a side effect needs its scope in the
   signature, not in its callers' heads.** B1 is one `if` away from correct, and
   it happened because `_commit_item_cost_evaluation_in_session` grew a
   `kind` parameter that gates the chain advance, the history record, the audit
   event and the pending event — but not the mirror. When a helper is
   parameterised by kind, the plan enumerates **which** effects that parameter
   gates, one line per effect; anything unlisted is a finding.

5. **L5 — deferral is legitimate, but a deferred mutation is deferred WORK, not
   deferred RISK.** The implementer's deferral was honest and correctly
   declared. But three of the five deferred rows turned out to need their
   criterion rewritten before they could bite (S1/S2/S3) — the deferral hid a
   *plan* defect, not just an unrun test. Where a phase defers its concurrency
   pass, the reviewer's prompt should require the criterion itself be re-derived,
   which this one did (P7-1) and which is why they were found.

6. **L6 — the tracker is evidence and gets verified like any other claim**
   (P-I eighth extension applied to the tracker). Row 7 carried numbers that
   matched neither the handoff nor reality (S4); the coordinator's consumption
   verified the file hashes but not the tracker's own figures.

## Carry-forward dispositions

Not applicable — this is a CHANGES_REQUESTED verdict; every note above returns
with the fix cycle. N5 (graph node type) is the exception: it is a human
adjudication, routed to the post-approval graph pass already held for phase 7.
N6 is routed to **phase 8** (its status query consumes the same resolver).

## What the fix cycle must do

1. **B1** — gate the mirror on `kind is COMMITTED`; add C5 row 7 with its named
   mutation; run it.
2. **B2** — adopt the attached probes as real test rows, with parametrize ids
   naming the authority row each discharges (P-V standing form), and
   mutation-test each added row per P-I (per row, not per test).
3. **B3** — rebuild C8's byte-unchanged check on a committing two-session
   harness.
4. **S1/S2/S3** — the coordinator amends C2, C11 and C5 row 6 in the plan
   *before* the fix prompt is compiled; the working observables are in the
   concurrency probe.
5. **S4** — correct master plan §4 row 7.
6. **S5** — decide between deleting the dead branch and restating the row.
7. **N1–N4, N7, N8** — cheap; fold into the same cycle.
