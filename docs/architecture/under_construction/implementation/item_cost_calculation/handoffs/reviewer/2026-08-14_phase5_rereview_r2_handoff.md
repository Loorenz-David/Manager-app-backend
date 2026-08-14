---
plan: phase 5 (valuation surface)
role: review
round: 2 (re-review, delta-scoped)
verdict: CHANGES_REQUESTED
date: 2026-08-14
actor: reviewer (Claude Opus 5)
---

# Phase 5 re-review r2 handoff

## Summary

**All four blocking findings and all five should-fix findings from r1 are closed,
and each was re-proven by me with a mutation that was green in r1 and reddens
now.** The production diff is exactly the two lines r1 verified — both files are
byte-identical to the ones my predecessor produced during correction
verification, so nothing extra rode along. The suite is clean, the race is clean,
the graph is untouched.

One thing keeps this from APPROVED. The new L15 structural guard — the row whose
*absence* was blocking B3 — catches the mutation it was named for and misses two
other shapes of the same defect. It builds the exact module set L15 describes and
then never asserts the property against it: adding a second, unmediated snapshot
read (in the same file, or in any other in-economics module) leaves 363/363
green. That is the one job a structural guard exists to do. The correction is
six lines; I executed it and it reddens all three shapes.

**Verdict: CHANGES_REQUESTED** — 0 blocking, **1 should-fix**, 7 notes.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

## Step 1 — perimeter

- `git show a0cebde --stat` = the **7 declared files**, exactly.
- `git status --porcelain` clean; `git diff a0cebde..HEAD -- app/` **empty**.
- Ruff clean on all five changed `app/` files.
- **Production diff is exactly two lines** (`git diff 8b4ac06..a0cebde -- app/beyo_manager/`):
  `delete_item_valuation.py` +1 (`ItemValuation.is_deleted.is_(False)`),
  `configuration.py` −1 (the redundant middle currency clause). Nothing else.
- **Both final production hashes reproduce r1's own correction-verification files
  byte-identically** —
  `delete_item_valuation.py` = `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1`
  (r1's B1 fix), `configuration.py` =
  `75087586aae405c57117f6417720743102fbc4003336ce2e6e25689800d68bde`
  (r1's M5.b probe = the 2-clause reduction). The fix shipped the verified
  corrections and only those.
- All five declared final file hashes in the fix handoff match the tree.

**Suite (re-run by me, clean tree): 1968 passed / 23 failed / 1 deselected** in
71.55 s; collection `1991/1992 (1 deselected)`. Failure set **byte-identical** to
the phase-1 baseline (zero-line diff against the enumerated list). Matches the
implementer's declaration exactly. DB at head `5caae620088c`.

**Self-reported measurement error (mine, corrected):** my first suite run
reported 24 failures. I had launched it in the background and then started
mutation probes; the run executed the L15 test while my M4a mutant was applied.
That run is void. The 1968/23/1 above is a foreground re-run on a
hash-verified-clean tree with nothing else touching it. Recorded because a
reviewer's own numbers must be reconstructible.

**Focused selector: 363 passed** (r1: 345; +18, matching the coordinator's
arithmetic).

---

## Step 2 — delta probes

### R2-P1 (B1) — CLOSED

Delete-then-reset-then-delete now runs end-to-end inside
`test_valuation_chain_preview_delete_and_history:298-330`: the reset row is
asserted present, `superseded_at IS NULL` rows == **2**, exactly **1** of them
not deleted, the second DELETE succeeds, and the INV-V1 count goes to 0. The
three-supersession block then asserts the count back at 1.

**B1-revert mutation:** mutant sha256
`23cfe90f65bf7b4c1ba536bbf86304e22ba65ccf3cafffac792d2b71ed75e365` — byte-identical
to the *old unfixed file*, exactly as the prompt predicted — reddens
`test_valuation_chain_preview_delete_and_history` (1 failed / 362 passed). In r1
this state had no test at all.

### R2-P2 (B2, P-V) — CLOSED, with a numbering note

`--collect-only` shows **12 ids**, mapping one-for-one onto §11A.4-as-amended-by-§7C.3's
twelve values: no duplicates, no omissions. Nine execute; three record
reachability judgments (`task_ok` / `task_infeasible` — "task-scoped; not
reachable by the item-scoped preview"; `not_configured_ambiguous_cost_group` —
"INV-G3 makes this unreachable through the database"), which is the shape L4
asked for.

Sole-predicate sampled on five rows, not three, by reading `_preview_fixture`'s
case sets:

| Row | Fixture state | Sole cause? |
|---|---|---|
| `no-basis-version` | group ✔, basis ✘, model ✔ | yes |
| `no-cost-model-version` | group ✔, basis ✔, model ✘ | yes |
| `currency-mismatch` | all present, payload EUR vs SEK/SEK, no purchase term | yes |
| `missing-purchase-cost` | purchase term added, all currencies SEK | yes |
| `not-evaluated` | all present, no terms; budget 100 → `7.68` (hand-checked: 100/13.0208 → Q3) | yes |

Every executed row asserts `item_cost_evaluations` count unchanged
(workspace-scoped, before/after) and `null` numerics where owed;
`not_evaluated` asserts the exact three-key dict. **M4a** (r1's own inline-classification
mutation, mutant `df1f79b3a23081cf21cc785f6660999fdc3648d786fd074167bcb074cbfb7c88`
— identical to r1's) reddens the new structural row where r1 saw 345 green.

### R2-P3 (B4 / S1) — CLOSED

All three declared mutant hashes reproduce byte-identically, and each reddens
exactly its own row:

| Mutation | Mutant sha256 | Red set |
|---|---|---|
| drop `valuation ≠ basis` | `ee22880184daa7b86ffc367b02fcc1563261cb61f5d9bf1869ecd1544790a957` | `…currency_mismatch_pair[basis-model]` **+** C5 `status-row-8-currency-mismatch` |
| drop `basis ≠ model` | `796ad66ee15e530ac57751ea87c9e5de2c9bd15d2ee43fb74427c2de57f0716b` | `…currency_mismatch_pair[valuation-basis]` |
| precedence swap 2↔3 | `bf241b9d507a70a250224ee5b71558ca216bdf128cab055b25d3ee17247548cf` | `test_item_readiness_purchase_cost_precedes_currency_mismatch` |

Both clauses now have sole-cause arbiters where r1 found none, and the drop of
`val ≠ basis` picks up a second arbiter at the integration layer. The reduction
did **not** weaken the three fixtures: all three states still return
`CURRENCY_MISMATCH` at baseline (363 green), and each drop reddens exactly one of
them. The id renaming reads as "the pair held **equal**" — confirmed against the
fixtures: (EUR,SEK,SEK)→`basis-model`, (SEK,EUR,SEK)→`valuation-model`,
(SEK,SEK,EUR)→`valuation-basis`. See note N3 on that convention.

### R2-P4 (S2 / S3 / L13) — CLOSED

Both r1-green ordering mutations now bite:

| Mutation | Mutant sha256 | Red set |
|---|---|---|
| drop `order_by` entirely | `8847d378bfb0cae10b324b0e0365125cd78f13311b7e64f72217722c3db87ef2` | `test_valuation_chain_preview_delete_and_history` |
| reverse to ASC | `f663c2536dcc446baf777a6208d1ac413e185e80f91982c57b8c770428f98f48` | `test_valuation_chain_preview_delete_and_history` |

The shared delete-then-reset fixture now carries C4's re-set row, four fresh
supersessions, the byte-identical re-read (`history == history_reread`), the
ordered id list against an independently-ordered expectation, and the INV-V1
current-count assertion (`== 1`). The expectation is a separate query with its
own hardcoded DESC, so the direction is genuinely pinned, not tautological.

Residual: the `client_id DESC` tie-breaker alone has no arbiter — see note N2.

### R2-P5 (S4 / S5) — CLOSED

- Race path (i) now asserts its **blocking observable**:
  `assert sorted(current_close_rowcounts) == [0, 1]` — winner's S1 closes one row,
  loser's closes none after the winner commits. That is exactly the observable
  L11/P-T named.
- Both blocks now count INV-V1's predicate: `remaining == 1` via
  `select(func.count(...))`, replacing r1's `is not None`.
- C3 gained the missing-currency reject row and three accept rows
  (`expected-only` / `cost-only` / `both`), plus a phase-2 citation comment.
- **Race subset run twice**, then the whole valuation file twice: all ten
  economics/actor tables **flat** across every run
  (`item_valuations=2, audit_logs=112, items=478, users=5950, workspaces=6816,
  prod_cost_groups=1, basis_versions=1, model_versions=1, model_terms=1,
  evaluations=0`). Rule 11½ holds. Residue scope named: the five valuation-chain
  tables plus the four configuration tables and `item_cost_evaluations`.

### R2-P6 (N1) — CLOSED

The chain fixture's persisted rate is now `13.0000` while the same basis inputs
derive `13.0208`, so persisted ≠ derived and both mutation forms bite:

| Mutation | Mutant sha256 | r1 | now |
|---|---|---|---|
| M10 — L12's **named** calculator recompute | `64480dcefdd323644fcfd62fbd020fec154bbb8d72350e5a996e23c30fb805de` | **green** | **red** |
| M10b — raw un-quantized re-division | `8191d1f82e0002b083bd0ab051826acbb5e3032e8c8ea511cf3137c268ea1f22` | red | red |

Hand-checked: 1 000 000 / `13.0000` → `76923.0769…` → Q3 `76923.08`, the asserted
value. The C5 `not_evaluated` row keeps `13.0208`/`7.68`, so both arithmetic
families stay live.

---

## Findings

### S1 (should-fix) — the L15 structural guard asserts a weaker property than the one it constructs

**Where.** `app/tests/unit/domain/item_economics/test_configuration.py`,
`test_item_major_category_snapshot_is_read_only_by_the_registered_resolver`.

The test correctly builds `module_sources` over exactly L15's two roots
(`domain/item_economics/*.py` and `services/**/item_economics/*.py` — 24 modules,
verified). It then never asserts the guard against that set. The only use of
`module_sources` is
`any(path == set_path and "item_major_category_snapshot" in source …)`, which
asserts the string **is** present in one file — the opposite of the guard.
Everything else is a string match on `set_item_valuation.py` alone.

**Executed — two shapes of the defect L15 exists to prevent survive:**

| Probe | Mutation | Mutant sha256 | Result |
|---|---|---|---|
| M4a | replace the resolver call with an inline chain (r1's / L15's named mutation) | `df1f79b3a23081cf21cc785f6660999fdc3648d786fd074167bcb074cbfb7c88` | **red** ✔ |
| **M4b** | keep the resolver call, add a second unmediated snapshot read in the same module | `e1ca06250fc7d8924e6e2d935bda00b9a03ece4bafdfee117afd013b88d3c6c0` | **363 green** |
| **M4c** | add a snapshot-classifying helper to `delete_item_valuation.py` (in scope) | `88c9f5aa59adca10e948fdc2c29acb12b77dce7eb491b615e73ff853d5f628ae` | **363 green** |

The literal amendment ("the test names its inspected source; inlining a snapshot
read in the preview must redden it") is met by M4a. The property the amendment
states — *no in-scope module reads the column except through the resolver* — is
not tested, and a structural guard's only job is to catch the reader added later.
This is P-J's exact hazard: a static proxy that reads adjacent constants survives
the defect it names.

**Verified correction (executed).** Use `module_sources` for what it was built
for — every in-scope occurrence must be a resolver argument:

```python
unmediated = {}
for path, source in module_sources:
    extra = (source.count("item_major_category_snapshot")
             - source.count("resolve_major_category(item.item_major_category_snapshot)"))
    if extra:
        unmediated[path.name] = extra
assert unmediated == {}, unmediated
```

With this in place the file is **9 passed** at baseline and **M4a, M4b and M4c
each redden it**. (Today the set has exactly one in-scope reader —
`set_item_valuation.py`, 1 occurrence, 1 mediated — so the assertion is
satisfiable as written.) The three `set_source` string asserts can stay or go;
the `ItemMajorCategoryEnum(` absence check is the one that does not generalise
(M4a's `ItemMajorCategoryEnum.WOOD` form contains no `ItemMajorCategoryEnum(`).

**Authority.** Plan amendment L15; master §6.5; §9 P-J / P-X; charter rule 2.

---

## Notes

**N1 — C5's row numbers map to no authority (P-V extension).** Coverage is
complete and correct *by value*; the numeric labels are a hybrid of two schemes.
`status-row-7-missing-purchase-cost` and `-row-8-currency-mismatch` follow
§11A.4's own pre-round-12 group-2 numbering (1–9); `-row-10-not-evaluated`
follows the post-§7C.3 numbering (1–10, `item_missing_major_category` inserted
first); `-row-1-item-unvalued`, `-row-2-missing-expected-price`,
`-row-3-missing-major-category`, `-row-4-no-cost-group`, `-row-5-no-basis-version`,
`-row-6-no-cost-model-version`, `-row-9-ambiguous` follow neither. Under
§7C.3 the correct numbering is 1 major-category, 2 no-group, 3 ambiguous,
4 no-basis, 5 no-model, 6 unvalued, 7 missing-expected, 8 missing-purchase,
9 currency-mismatch, 10 not-evaluated (+ 11/12 for group 1). **The plan seeded
this**: L4's own example id is `status-row-7-missing-purchase-cost`, which is
pre-round-12. P-V's whole payoff is that verifying the mapping costs one
`--collect-only`; wrong numbers cost a full re-audit (I did one). → next touch,
and correct L4's example.

**N2 — the `created_at DESC, client_id DESC` tie-breaker has no arbiter.**
Executed: dropping `client_id DESC` only (mutant
`a3248bbbec3df078aa6bd4e5c231f39b20a2631811bbb52d1947d422d6785866`) leaves
**363 green** — no fixture produces a `created_at` tie, because each
`set_item_valuation` call stamps its own `datetime.now()`. L13 pinned the total
order precisely because `created_at` is Python-side and *can* tie. Not reachable
by today's code, so not filed as a defect — but **phase 6's legacy money
migration will bulk-create valuation rows**, plausibly sharing one timestamp,
which is exactly when the clause becomes load-bearing. Verified correction: build
two rows with an explicit identical `created_at` and assert the `client_id DESC`
order. → **phase 6** forward note.

**N3 — the currency ids name the pair held EQUAL, while the clause each row
arbitrates is the other one.** `[basis-model]` is the row that proves
`valuation ≠ basis`, and `[valuation-basis]` proves `basis ≠ model`. This is what
r1's own correction wording asked for ("rename the ids to the pair each fixture
holds equal"), so it is not a finding — but the inversion is a live misreading
trap: deleting `val ≠ basis` and seeing `[basis-model]` go red reads like the
wrong thing broke. One comment above the parametrize naming which clause each row
arbitrates closes it. → next touch.

**N4 — two mutations shipped under one name (M4).** The fix ledger's M4 row
declares mutant `e818fa2b…` with red set "C5 missing-expected, missing-purchase,
currency-mismatch, not-evaluated, no-basis, no-model; chain" — a *behavioural*
blast radius that does not include the structural row. L15's and r1's M4 (mutant
`df1f79b3…`, behaviour-preserving) reddens **only** the structural row. Both are
legitimate probes; recording them under one label hid that the structural row's
coverage was never exercised by the ledger's own run. P-I second extension: the
declaration cites observed node ids from the run that produced it — it should
also pin *which* mutant produced them when a name is reused.

**N5 — race path (ii) still has no rowcount observable.** Path (i) now asserts
`[0, 1]`. Path (ii) (first valuation, both S1s necessarily rowcount 0) is
guaranteed by the `asyncio.Event` gate proving both are past S1 before either
inserts, so the added value is small. Recorded for completeness, not owed.

**N6 — the phase-2 citation is prose, not a node id.** L10 asked C3 to "cite the
phase-2 rows by node id"; the shipped citation is a comment naming
`node:table-item-valuation` and the six cases in words. The projection named the
actual test (`test_item_valuation_amount_and_currency_boundaries`, ids
`negative-sale / negative-purchase / both-null / null-currency / price-only /
cost-only`). Discharged in spirit; the pytest node id would make it navigable.
→ next touch.

**N7 — r1's carry-forwards are unchanged and still owed:** N2 (DELETE's
hardcoded `item_unvalued` vs §11A.4's order) → phase 8; N4 (dev-DB residue
`ws_765225a0…`, still present at `item_valuations=2` and confirmed *not* growing
across my runs) → closeout purge; N5 (valuation payload field list) → phase 9;
N6 (five missing `reads_from` edges) and N7 (stale `domain-item-economics`
anchor) → coordinator's post-approval graph pass.

---

## Step 3 — architecture graph (read-only)

**Zero delta this cycle, as expected.** `archgraph_status`: revision
`b5e6fe094caee2191414a297bb1ab63507ebda8ee4ee54c26cc612a5d940fc94`,
**153 nodes / 195 edges**, **12 pending**, 0 diagnostics, 1 stale node —
identical to the state r1 recorded. I made no decisions and no mutations.

**Anchor spans after the fix.** Only `delete_item_valuation.py` (+1 line, 43→44)
and `configuration.py` (−1 line, 171→169) moved. The configuration deletion is at
line ~160, *below* every anchored symbol, so no configuration span shifted. Two
spans in `delete_item_valuation.py` moved by +1:

| Item | r1 final span | r2 final span | Note |
|---|---|---|---|
| node `command-…-delete-item-valuation` | 17–43 | **17–44** | `return` moved to 44 |
| edge delete `--writes_to-->` table | 38–41 | **39–42** | write site `is_deleted = True` (39) → `flush()` (42); 43 is the audit write (different table), 44 the return |

**Unchanged and still final** (files untouched this cycle): node
`command-…-set-item-valuation` **102–168**; node endpoints **229–241 / 244–256 /
258–269**; edge set `--writes_to-->` **128–159**; edge get-valuations
`--reads_from-->` **23–31**; edge `--returns-->` **32–33**; the three router-anchored
edges **229–241 / 229–241 / 258–269**.

**Stale node (N7), still undeclared.** `domain-item-economics`'s source link
targets `configuration.py:44-82`, symbol `resolve_economics_configuration`.
Re-verified after the fix: that function is **64–77** and
`resolve_economics_selection` is **80–126** — both unmoved by this cycle.
Recommended re-link unchanged: symbol `resolve_economics_selection`, span
**80–126**.

---

## Mutation-probe declaration

Every probe applied in the main worktree, run against the focused selector
(363 tests, ~10 s), then reverted with `git checkout --`. Restored hashes are
copy-pasted from the harness output; the tree is clean and
`git diff a0cebde..HEAD -- app/` is empty, so zero probe residue exists.

Focused selector:
`tests/unit/domain/item_economics tests/unit/services/commands/item_economics tests/unit/routers/api_v1/test_item_economics_router.py tests/integration/services/commands/item_economics tests/integration/models/item_economics`

| Probe | File | Mutant sha256 | Restored sha256 | r1 | Observed red set (full) |
|---|---|---|---|---|---|
| R2-P1 B1-revert | `delete_item_valuation.py` | `23cfe90f65bf7b4c1ba536bbf86304e22ba65ccf3cafffac792d2b71ed75e365` | `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1` | n/a | `test_valuation_chain_preview_delete_and_history` |
| M4a L15 named | `set_item_valuation.py` | `df1f79b3a23081cf21cc785f6660999fdc3648d786fd074167bcb074cbfb7c88` | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | green | `test_item_major_category_snapshot_is_read_only_by_the_registered_resolver` |
| **M4b second reader, same module** | `set_item_valuation.py` | `e1ca06250fc7d8924e6e2d935bda00b9a03ece4bafdfee117afd013b88d3c6c0` | `05587c2b…5bda8` | — | **none — 363 passed → S1** |
| **M4c reader in another in-scope module** | `delete_item_valuation.py` | `88c9f5aa59adca10e948fdc2c29acb12b77dce7eb491b615e73ff853d5f628ae` | `ab9aebbe…3fc1` | — | **none — 363 passed → S1** |
| R2-P3a drop `val≠basis` | `configuration.py` | `ee22880184daa7b86ffc367b02fcc1563261cb61f5d9bf1869ecd1544790a957` | `75087586aae405c57117f6417720743102fbc4003336ce2e6e25689800d68bde` | green | `…currency_mismatch_pair[basis-model]`; `…enumeration…[status-row-8-currency-mismatch]` |
| R2-P3b drop `basis≠model` | `configuration.py` | `796ad66ee15e530ac57751ea87c9e5de2c9bd15d2ee43fb74427c2de57f0716b` | `75087586…8bde` | green | `…currency_mismatch_pair[valuation-basis]` |
| R2-P3c precedence swap 2↔3 | `configuration.py` | `bf241b9d507a70a250224ee5b71558ca216bdf128cab055b25d3ee17247548cf` | `75087586…8bde` | green | `test_item_readiness_purchase_cost_precedes_currency_mismatch` |
| R2-P4a drop `order_by` | `get_item_valuation_history.py` | `8847d378bfb0cae10b324b0e0365125cd78f13311b7e64f72217722c3db87ef2` | `6f586d0f4d086abf5a5c035fe4ca07c99ee1d34723b12b871efb2f717cd4e16c` | green | `test_valuation_chain_preview_delete_and_history` |
| R2-P4b reverse to ASC | `get_item_valuation_history.py` | `f663c2536dcc446baf777a6208d1ac413e185e80f91982c57b8c770428f98f48` | `6f586d0f…16d4` | green | `test_valuation_chain_preview_delete_and_history` |
| **R2-P4c drop `client_id DESC` only** | `get_item_valuation_history.py` | `a3248bbbec3df078aa6bd4e5c231f39b20a2631811bbb52d1947d422d6785866` | `6f586d0f…16d4` | — | **none — 363 passed → N2** |
| R2-P6a M10 named recompute | `set_item_valuation.py` | `64480dcefdd323644fcfd62fbd020fec154bbb8d72350e5a996e23c30fb805de` | `05587c2b…5bda8` | **green** | `test_valuation_chain_preview_delete_and_history` |
| R2-P6b M10b raw re-division | `set_item_valuation.py` | `8191d1f82e0002b083bd0ab051826acbb5e3032e8c8ea511cf3137c268ea1f22` | `05587c2b…5bda8` | red | `test_valuation_chain_preview_delete_and_history` |

**Correction-verification runs** (applied to the *test* file, measured, reverted —
not findings): the S1 correction leaves `test_configuration.py` at **9 passed**
and reddens M4a, M4b and M4c individually. Test file restored to
`9ad0b6eafbbbe2579ae8d5b4f174e5a5d73d087badb0a4b753ec7d1aada27483`.

## Full write perimeter

- **Documents written:** this handoff; the Review log entry appended to
  `plans/phase_5_valuation_surface.md`; the phase-5 tracker row in
  `master_plan.md`. Nothing else.
- **Code / tests:** **zero net changes.** Every probe reverted via
  `git checkout --`; `git status --porcelain` clean;
  `git diff a0cebde..HEAD -- app/` empty; all five declared final hashes match.
- **Disposable test files:** none created this round (r1's two were already
  removed and are absent from the tree).
- **Database:** configured dev DB, left at head `5caae620088c`. Economics tables
  unchanged by my session (`item_valuations=2`, `evaluations=0`, config tables 1
  each — r1's N4 pre-checkpoint residue, flat across four test runs). `items`,
  `users` and `workspaces` grew from my two full-suite runs — the known
  non-economics per-run residue recorded in §10.
- **Scratchpad (outside the repo):** probe harness and suite logs.
- **Architecture graph:** **READ-ONLY, zero delta.** One `archgraph_status` call.
  No decision recorded; the 12 pending items are not mine to adjudicate.

## Lessons for the plans

1. **A structural guard is graded on the reader added *later*, not the call
   replaced *now*.** The shipped L15 row catches "someone deleted the resolver
   call" — which the behavioural rows largely catch anyway — and misses "someone
   added a second reader", which is the only failure mode a structural row exists
   for. Candidate P-J extension: when a criterion states a property over a
   **module set**, the assertion quantifies over that set; a test that constructs
   the set and then asserts about one member has not discharged it.
2. **Row numbers in parametrize ids must cite a numbering scheme that still
   exists.** L4's own example (`status-row-7-…`) was pre-round-12, and the
   implementation blended it with the post-§7C.3 order. P-V's payoff — verify the
   mapping with one `--collect-only` — is lost the moment the numbers are a
   hybrid. Plans should quote the authority's *current* numbering when they give
   an id example.
3. **A reused mutation name needs a mutant hash beside each red set.** Two
   different M4 mutants shipped under one label, and the ledger's red set belonged
   to the one that did *not* exercise the row under review. Extends P-I's second
   extension.
4. **A reviewer's background suite run must not overlap its own probes.** My
   first run reported a 24th failure that was my own mutant. Recorded as process,
   not as a finding: suite runs are foreground, or probes wait.

## Carry-forward dispositions

| Item | Destination |
|---|---|
| S1 (L15 guard scope) | **fix cycle r2** — correction verified above |
| N1 (C5 row numbering + L4's example) | next touch + plan correction |
| N2 (`client_id DESC` tie-breaker) | **phase 6** (bulk valuation creation) |
| N3 (currency id inversion comment) | next touch |
| N4 (M4 label reuse) | coordinator — ledger convention |
| N6 (phase-2 node-id citation) | next touch |
| r1 N2 (DELETE `item_unvalued` vs §11A.4 order) | phase 8 |
| r1 N4 (dev-DB residue) | closeout purge |
| r1 N5 (payload field list) | phase 9 |
| r1 N6/N7 (graph read edges, stale anchor) | coordinator post-approval graph pass |
