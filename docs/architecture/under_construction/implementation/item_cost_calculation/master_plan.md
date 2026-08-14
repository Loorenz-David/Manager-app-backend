# Master plan — item_cost_calculation

```
plan: master
role: planner artifact (coordination hub)
round: 1
date: 2026-08-11
status: ACTIVE
authority: planning/intention.md (round 4) is the semantic authority; this file owns
           the shared skeleton (naming registry, contract resolution, environment
           topology, sequencing, tracker). Semantic changes amend the intention;
           skeleton changes amend this file; a phase plan is NEVER patched into
           divergence with either.
```

## 1. Goal

Build the **item-economics domain**: expected sale price minus configured allocation
terms → production budget → aggregate worker-minute allowance, frozen as immutable
committed evaluations per task episode, with what-if projections, live consumption
from the existing step-time rollups, and a replay-safe result refreshed at every
episode boundary (READY entries, reopens, terminal transitions — intention §8B,
round 6; "final" = terminal-computed).
Full semantics: `planning/intention.md` — this plan never restates them. The
mechanism contracts live in intention §4A, §6A, §7A, §7B, §8A, **§8B**, §10A, §11A
(lettered sections govern the numbered ones they amend). Round-4 owner decisions are
settled:
**§8A.5 branch A (re-emit) only — branch B is rejected and no phase builds it**
(guard widened to READY ∪ terminal, round 6);
**§6A.4 gross-base planning-allocation semantics with the binding presentation rule**
(a percentage term is never presented as computing legally payable tax).

## 2. Sources of truth

| Content | Artifact |
|---|---|
| Product semantics, invariants, mechanism contracts | `planning/intention.md` (round 4) |
| Evidence census, verified code facts | `planning/research_context.md` (record — never edited) |
| Owner decisions | `planning/owner_decisions.md` (CLOSED) |
| Gate report, inventory table (34 rows), D-1…D-4 | `handoffs/mechanism_inventory/2026-08-11_mechanism-inventory_r1_handoff.md` |
| Shared skeleton: naming registry, contract resolution, environment topology, tracker | this file |
| Phase-local goal/tasks/criteria + Review log | `plans/phase_<n>_<slug>.md` |
| Session framing | `prompts/<role>/`, generated just-in-time by the coordinator |
| External-source evidence | none — §12 of the intention is satisfied vacuously |

**Fold-back rule:** a semantic gap found mid-phase routes to the coordinator as a
decision card or intention amendment (lettered section, never a renumber); a skeleton
gap amends this file. Nothing is silently patched into a phase plan.

## 3. Roles & session workflow

Per the pipeline charter (`/Users/davidloorenz/agent-skills/pipeline-charter.md`) and skills. State machine:
`NOT_STARTED → PROJECTED → PROMPT_READY → IMPLEMENTING → IMPLEMENTED → REVIEWING →
CHANGES_REQUESTED (→ IMPLEMENTING) → APPROVED`. A phase starts implementation only
when the previous phase is APPROVED. Every implementation and every fix cycle is
committed at `IMPLEMENTED` (`CHECKPOINT (not approved):` prefix, standing owner
authorization). First review = full checklist; re-review = delta-scoped with verified
perimeter. Agents update only their own tracker row; findings go to the phase plan's
Review log (append-only).

**Projection gate (round 0):** mandatory for every phase flagged ⚑ in the tracker
(the phase touches mechanisms ranked S1/S2 in the gate handoff's inventory table);
waivable only for unflagged phases with a recorded one-line justification.
Self-retiring per charter (two consecutive empty ledgers).

**Per-session obligations (every implementer/reviewer session):**
1. Re-emit the §5 contract resolution before coding (implementers).
2. Archgraph: `archgraph_status` + orient on the phase's named nodes at start; record
   the phase's architectural delta at close in ONE batched `archgraph_apply_changes`
   (accurate evidence spans; a delta of zero items is stated, not skipped). Sessions
   never adjudicate pending reviews — the per-phase delta items are handled by the
   §8 standing flow (reviewer verifies, coordinator confirms after approval).
   *(State 2026-08-12 after the phase-2 closeout confirmation: 125 nodes /
   161 edges, revision `10d94f14…`, **0 pending** — the phase-2 delta was
   confirmed 14-promote + 1-edit-then-promote under the §8 standing flow; audit
   records `…12-54-15…9f9769.yml`, `…12-54-37…9bff2f.yml`.)*
3. Tests, tracker row, Review log, checkpoint commit per charter.

## 4. Progress tracker

⚑ = projection gate MANDATORY (silent-failure mechanisms touched; inventory rows cited).

| # | Phase | Plan file | Gate | State | Date | Actor | Note |
|---|---|---|---|---|---|---|---|
| 1 | Worker money redaction | `plans/phase_1_worker_money_redaction.md` | ⚑ (row 33) | **APPROVED** | 2026-08-12 | reviewer (Claude); Codex (fix r2); reviewer r2 (Claude) | review r1: leak closed correctly on all 8 endpoints, 8/8 mutations bite, zero regressions (P-R1 settled: 23 pre-existing failures, identical sets at `545e504` and `4416570`); 2 should-fix — 5 ADMIN criteria rows untested (S1), recorded baseline wrong (S2) — + 6 notes. Coordinator: findings routed (N1/N2→phase 9, baseline→§10, lessons→§9 P-G/P-H), fix-r2 prompt authored; reviewer handoff was deposited late (after the coordinator's sweep) — consumed, authoritative. Fix r2: S1 ADMIN rows added and asserted `== 4321`; S2 baseline correction and full 23-item list recorded; focused 39 passed, full run 1605 passed / 23 failed / 1 deselected. Coordinator: fix handoff consumed, perimeter exact vs `ed99e7e`, arithmetic reconciled (1624→1629 = the 5 rows); re-review r2 prompt authored (probes: reshaped worker assertions, baseline list match, new-row liveness). **Review r2: APPROVED** — perimeter exact (six files, zero production-code change), S1+S2 resolved, criteria now 26/26 (24/24 cells), rows 19/22 survived the reshaping and run twice, all four probes bite per-parameter plus an ADMIN-drop probe reddening exactly 9 ADMIN ids with zero collateral, baseline list set-identical to r1's, suite 1605/23/1 with the failure set byte-identical to baseline, archgraph zero delta. Open notes carried forward: N1/N2→phase 9, N7 (test naming)→next touch |
| 2 | Schema, models & migration | `plans/phase_2_schema_models.md` | ⚑ (rows 1,3,8,11,12,15 — DDL side) | **APPROVED** | 2026-08-12 | coordinator; Codex; reviewer r1 (Claude); Codex (fix r2); reviewer r2 (Claude); Codex (fix r3); reviewer r3 (Claude) | projection r0 AMENDMENTS_REQUIRED (16-row ledger, 4 blocking: name truncation, open name list, unfalsifiable C5, no disposable-DB harness) — fully routed: §6.2 closed CHECK list + named FKs, §6.1 citation fix, §10 disposable recipe, intention round 7 (icet columns), plan tasks/criteria rewritten (C1a/b, C2 per-clause, C3 12-row table, C5 migration-site, C6); implementer r1: nine models/migration and focused suite 23 passed; full suite 1628 passed / 23 known failures / 1 deselected; enum ownership mutations pass; C2 predicate mutations outstanding for review. Coordinator: handoff consumed — effective checkpoint is `8b3f9f7` (500dfbd was amended; one-line handoff diff); graph state committed (`ab2b71c`: owner backlog adjudication 243→15 pending + the phase-2 delta); §10 gained the migration-chain-stall caveat; review r1 prompt authored (probes P2-1 C2 mutations … P2-6 graph delta per-item). **Review r1: CHANGES_REQUESTED** — the schema itself is correct and independently re-verified (DDL exact vs §6.2 both directions, longest name 57 bytes; `compare_metadata(compare_type=True)` reports 0 diffs on all nine tables; C1 round-trip + C5(a)/(b) re-run on a disposable DB with reused-type oids unchanged; M-a/M-b both bite; P2-5 shapes and all deliberate absences correct; scope fence clean; suite 1628/23/1 with the failure set byte-identical to the phase-1 baseline). The **tests** do not hold it: 4 blocking — B1 C2 entirely unimplemented (0 of 22 rows; stripping a clause from three multi-clause index predicates leaves 23/23 green), B2 the C1(b) downgrade proxy survives all three defects it names incl. the literal M-b, B3 the five `ck_pcbv_*` boundary rows pass on `uix_production_cost_basis_versions_open` not on their CHECKs (A1/A2 have no live test), B4 nine of sixteen CHECKs behaviorally untested + the enumerated accept-rows largely absent — plus 3 should-fix (S1 unregistered 4th currency column reusing `item_valuation_currency_enum`, S2 five-new-enum-types clause unasserted, S3 test name overclaims) and 7 notes. P2-4 stall confirmed pre-existing (reproduces at `7758ea23764e`) but recorded-not-filed → owner card 1. P2-6: 15 items, all anchors exact — 14 promote / 1 edit, contradictions are heuristic false positives, edge count reconciled to the handoff's 6. Coordinator (post-review): card 1 answered — own the stall NOW (maintenance prompt authored, `prompts/maintenance/2026-08-12_migration-chain-stall_r1.md`); S1 registry decision = reuse ratified (§6.3 lists columns, not counts); lessons folded (§9 P-G(a) DDL-site, P-J, P-K, P-L); fix-r2 prompt authored (`prompts/implementer/2026-08-12_phase2_fix_r2.md`); graph items 14 promote / 1 edit held for post-approval confirmation. Fix r2: B1–B4 and S1–S3 resolved; 79 focused tests passed; full suite 1684 passed / 23 known failures / 1 deselected; all 14 predicate and 14 CHECK mutations reddened and were reverted on disposable state; B2's three source mutations reddened; dev DB at head; archgraph delta zero. Fix r2 (Codex, `39e6fbe`): B1 25 C2 cases + 14 DDL-site clause mutations bite; B2 getsource proxy + 3 source mutations bite; B3 sole-cause + constraint names; B4 full CHECK coverage; S1-S3 + N2; focused 79 passed, full 1684/23/1. Maintenance (parallel, `7e1b11d`): stall root-caused — CYCLE in the historical revision graph; guarded env.py repair; from-scratch upgrade 1.80s; §10 recipe verified. Coordinator: both handoffs consumed (perimeters exact; maintenance handoff was misfiled at repo root — relocated; closing protocols now carry full deposit paths); re-review r2 prompt authored. **Review r2: CHANGES_REQUESTED** — perimeter exact on both commits (`39e6fbe` four files, `7e1b11d` three); R2-P1 the 25 C2 cases map one-to-one onto the table (r1's "22" was the arithmetic error — lesson L1); B1–B4/S1–S3 all re-derived independently, two verified harder than declared (full 16-CHECK sweep — every CHECK reddens a *behavioural* row, not just the inventory; both halves of S2's `pg_type` assertions drop-simulated); 7 of 14 predicate clauses re-run at the DDL site, all three B2 source mutations bite; suite 1684/23/1 with the failure set byte-identical to the phase-1 baseline and the transient collection error gone; R2-P4 from-scratch `upgrade head` verified (empty→`90cdd23a828e` in 1.52s, 106 tables), env.py guarded on the exact legacy graph and inert at head, rule 7 intact; archgraph zero delta (`9476e89a…`, 15 pending). **1 blocking: B5** — INV-G1's C2 (a) row uses one group instead of the cell's "two groups", so widening the index key to include `production_cost_group_id` (destroying INV-G1) leaves all 79 tests green; one-fixture fix. 6 notes (N8 proxy regex, N9 handoff commit hash wrong, N10/N11 env.py cold-build row + private-internals shim → maintenance ledger, N12/N13 next touch); r1's N2 closed; N3→phase 4, N4/N5→phase 9; lessons L1–L3. Coordinator (post-r2): B5 → fix-r3 prompt (one fixture: second group for the INV-G1 rows + key-widening mutation); N10/N11 filed as maintenance follow-up prompt (shim residues — cold-build workspace row, private-internals repair; run at owner's choosing); N9 provenance lesson in fix prompts (final hash); lessons L1–L3 folded (§9 P-L extended, new P-M); 14/15 graph items still held for post-approval. Fix r3: B5 resolved by adding a second same-workspace production cost group to the sections conflict/removal fixture; focused 79 passed; named widened-key mutation reddened `sections_conflict` and was reverted; full suite 1684/23/1 baseline-identical; dev DB at head; archgraph delta zero. **Review r3: APPROVED** — perimeter exact (three files; test diff is +5/−2, not the prompt's +7/−2 — coordinator transcription); B5 resolved and re-derived: on a from-scratch disposable DB the widened-key mutation reddens **exactly** `sections_conflict` (1 failed / 78 passed, zero collateral) and the reviewer-added paired mutation (drop `removed_at IS NULL`) reddens **exactly** `sections_removed`, so INV-G1 now has both arbiters live and one of r2's seven undeclared clause mutations is closed; DDL restored and re-read; clean full suite 1684/23/1 with the failure set byte-identical to the phase-1 baseline; archgraph zero delta (`9476e89a…`, 15 pending). New note **N14** (passing-glance, pre-existing, outside phase 2): `test_process_shopify_products_…` compares an unordered `SELECT` as an ordered list (`:176`) and flaked once under load — it can redden any future baseline at random → next touch of that file. N12/N13 correctly not taken. Phase 2 closed: B1–B5 and S1–S3 all resolved; carry-forward table final in the Review log. |
| 3 | Canonical calculator | `plans/phase_3_canonical_calculator.md` | ⚑ (rows 1–14) | **APPROVED** | 2026-08-12 | Codex; reviewer r1 (Claude); Codex (fix r2); reviewer r2 (Claude); Codex (fix r3); reviewer r3 (Claude); Codex (fix r4); reviewer r4 (Claude) | pure calculator + C1–C9 unit proof; 54 focused tests, full suite 1738 passed / 23 known failures / 1 deselected (failure set baseline-identical); all named C2×5, C6, C7 FK-read, and C9×2 mutations reddened and reverted; checkpoint pending review. Implementer r1 (Codex, `2a860b2`, final hash cited in full): C1-C9 built on the seeded fixtures; 9 named mutations run/reverted per-site with sha256s; focused 54 passed; full 1738/23/1 (+54 exactly); graph delta = 1 inferred node domain-item-economics (pending). Coordinator: handoff consumed, perimeter exact; D1 public API (16 names) folded into §6.5; review r1 prompt authored (P3-1 sampled mutations ... P3-8 API match). **Review r1: CHANGES_REQUESTED** — the calculator is substantially right and independently re-derived (perimeter exact and hashes byte-identical; scope fence clean; purity structural — zero I/O imports; ruff clean; all ten Q-site values re-computed by hand incl. the Diophantine Q2 tie and C5's seeded triple with its exactly-1 divergence; C1 total over type×presence; suite re-run 1738/23/1 with the failure set byte-identical to the phase-1 list; **all nine** declared mutations re-run in a disposable worktree, each reddening exactly its named set; P3-6 verified positively — the plan's other Q3 fixture lets C9(b) pass, so the declared test change genuinely strengthened; P3-8 all 16 names present). **2 blocking:** B1 `calculate_remaining_worker_minutes`/`calculate_variance_worker_minutes` do Decimal arithmetic OUTSIDE `localcontext()`, violating §6A.2-as-amended — under `prec=6` remaining(100000.00, 0.33) returns `99999.7` not `99999.67`, and C9 cannot see it because it enumerates only Q1–Q5 (exactly P3-4's hole); B2 C6's `money × None (system-supplied)` cell has no row — every money guard row drives a *user-supplied* field, so `_require_money`'s system branch is unexercised and turning it into `return 0` (the R-9/P-B inferred zero) leaves **54/54 green**. **3 should-fix:** S1 C8's `or` disjunction means dropping the right-hand currency from the message reddens only 1 of 3 rows; S2 `ITEM_COST_SNAPSHOT_MISMATCH` unregistered in §6.4 (→ card 1); S3 C9's docstring row asserts no never-bump token. 7 notes (N1 duplicate test, N2 surface exceeds §6.5's 16 + no `__all__`, N3/N4 two untested unrequested additions → card 2, N5 dead `required=False`, N6 collection-time fixtures shift parametrize ids, N7 Q3 "consumes persisted rate" unbiteable in phase 3 → phase 4/5). Lessons L1–L4. P3-7: 1 item, all three claims accurate, anchors imprecise and evidence 3 stored as `365–425` ≠ the handoff's declared `371–425` → recommend HOLD and re-anchor after the fix cycle (→ card 3).. Coordinator (post-review): 3 owner cards answered (R9-1 REDERIVE_MISMATCH internal alarm; R9-2 guards absorbed with required rows; card 3 graph node HELD for one post-fix adjudication with corrected anchors); intention round 9; §6.5 registry += Protocols/markers/__all__; lessons folded (P-M ext, P-N, P-O, P-P); N7 -> phase-4 wiring arbiter; fix-r2 prompt authored; Fix r2 (Codex): B1/B2/S1–S3, absorbed guards, and N2 resolved; focused 59 passed, full 1743 passed / 23 known failures / 1 deselected, failure set baseline-identical; all inherited and new named mutations reddened and were reverted; graph delta zero; checkpoint pending review.. Fix r2 (Codex, `8378a1b`, final): B1 wraps + C9 extended to all Decimal functions; B2 system-None row + inferred-zero mutation bites; S1 per-value; S2 REDERIVE_MISMATCH structured payload; S3 both tokens; 3 absorbed-guard rows; __all__ (20 names); 12 mutations declared; focused 59, full 1743/23/1 (+5 exactly). Coordinator: consumed, perimeter exact; re-review r2 prompt authored. **Re-review r2: CHANGES_REQUESTED** — perimeter exact (four files, hashes byte-identical), suite 1743/23/1 with the failure set byte-identical to the phase-1 list, ruff clean, graph read-only and unchanged (`671fd92a…`, 1 pending, zero delta). **All six r1 findings verified closed**, two harder than declared: B1 closed *structurally* — a sweep of all twelve public callables under `prec=6/ROUND_CEILING` finds zero divergence (the two r1 offenders now both return `99999.67`); B2's new row drives a genuinely system-supplied parameter and the inferred-zero mutation that left 54/54 green in r1 now reddens it; S1 weakening reddens 2 of 3 (P-O bar); S2 zero `ITEM_COST_SNAPSHOT_MISMATCH` in `app/`, structured payload asserted exactly; S3 both tokens bite; all three R9-2 absorbed-guard rows bite on their own branch; `__all__` exact and fully resolvable. **1 blocking: B3** — `rederive` still raises user-facing `ValidationError`s on corrupt snapshots, contravening R9-1's "never raises": a stored snapshot rate of `0` (column has NO CHECK > 0) now reaches `calculate_allowed_worker_minutes` at `:465` and raises `ITEM_COST_RATE_UNDERFLOW` because the S2 refactor replaced the early raise with an appended entry; corrupt term shape and NULL purchase cost raise too (pre-existing, in scope only because R9-1 is new) → scope boundary is owner card 1. **2 should-fix:** S4 the `calculate_percent_consumed` row added to C9 is inert (removing its wrapper leaves 59/59 green; verified fix = fixture `(0.01, 100000.00)`, which reddens); S5 three of four `REDERIVE_MISMATCH` field branches untested (all four verified well-formed; the rate→allowance cascade is unpinned). 4 notes (N8 `__all__` is **19** names not the "20" in the handoff/prompt/tracker — code right, prose wrong, repeat of P-L; N9 the constant's own docstring has no arbiter; N10 variance double-wrap; N11 indentation artifact). Lessons L5 (a "never raises" contract enumerates the input classes it covers), L6 (each added hostile-context row needs a fixture chosen to bite, declared per row — extends P-I). Coordinator (post-r2): re-review card answered (R10-1: rederive total over ALL malformed inputs — intention round 10, incl. pinned rate→allowance cascade); L6 folded (P-I per-row declarations); N8 count corrected (__all__ = 19: the 16 incl. REDERIVE_SKIPPED + 2 Protocols + REDERIVE_MISMATCH — prior '20' was prose double-count); N9/N10/N11 next-touch options; fix-r3 prompt authored (B3 three classes, S4 verified fixture swap, S5 four branch rows + cascade). Fix r3: B3 totality + S4 live hostile fixture + S5 exact payload/cascade; focused 65 passed, full 1749/23/1 baseline-identical; final hashes recorded in the handoff; archgraph zero delta.. Fix r3 (Codex, `8908619` = HEAD): B3 three conversion seams (rederive never raises; cascade preserved); S4 verified fixture swap in both tuples; S5 four branch rows + cascade; per-row mutations declared (P-I ext); focused 65, full 1749/23/1 (+6 exactly). Coordinator: consumed; process slip noted (handoff committed INSIDE the checkpoint, no hash citation — recorded, not re-filed); re-review r3 prompt authored (R3-P1 hunts a FOURTH escape route beyond the three named classes). **Re-review r3: CHANGES_REQUESTED** — perimeter exact (five files, hashes byte-identical), suite 1749/23/1 with the failure set byte-identical to the phase-1 list, focused 65, ruff clean, graph read-only and unchanged (`671fd92a…`, 1 pending, zero delta). **B3 CLOSED and verified TOTAL:** all three R10-1 classes return the marker, and a hunt across **17 further hostile inputs** (negative rate, NaN rate, NaN allowance, zero hours, zero utilization, Q2 underflow, float rate, None/str price, None budget/allowance/term-amount, str calculation_type, float percent, negative percent, empty term_rows, None version, version 2) found **zero `ValidationError` escapes**; both conversion-seam re-raise mutations bite. Critical regression check passed: the except tuple excludes `AssertionError`, so the C7 closed-set tripwire still bites through the new catch-all (a broader `except Exception` would have swallowed the phase's closed-set guarantee). **S4 CLOSED** — r2's counterfactual is the shipped fixture in both C9 tuples and the wrapper removal now reddens where it left 59/59 green. **S5 four of five parts closed** (both sampled field-label corruptions redden exactly their rows). **1 should-fix: S6** — the pinned rate→allowance cascade (`or rate != stored_rate`, `:533`) has **no live arbiter**: deleting the clause leaves 65/65 green because the cascade row's fixture (rate `399.0000`) carries a second sufficient cause (allowance re-derives to `5.43` vs stored `5.42`), so the entry appears for the ordinary reason — charter rule 2's sole-predicate companion, same shape as phase-2 B5, and the clause *looks* redundant so a future cleanup would silently drop the owner's pin. Verified correction: stored rate `399.5000` + expected allowance entry `5.42`/`5.42` → clause deleted then reddens exactly the cascade row. **Declaration defect:** the fix-r3 handoff and Review log both claim the cascade inversion reddened the cascade row; re-run independently it reddens `test_rederive_reports_allowed_worker_minutes_mismatch_payload` instead — the mis-attribution is how the gap survived. 5 notes (N12 `term_row.name` the one unguarded attribute read — unreachable for ORM rows; N13 dead branching at `:472-477`, three identical returns behind two `if`s; N14 heterogeneous payload shape — `"error"` key only on converted entries; N15 the catch-all converts programmer errors into integrity markers → phase 7/8 must not read the marker as proof of corruption; N16 one new rederive row uses `SimpleNamespace` vs C7's ORM pin — bundle with S6). Lessons L7 (implication-shaped pins need a fixture where the consequent would not otherwise fire), L8 (a mutation declaration must be checked against the run that produced it — extends L6/P-I). Coordinator (post-r3): B3 verified TOTAL (17 extra hostile inputs, zero escapes; C7 tripwire regression-checked); S6 cascade arbiter (verified fixture 399.5000) + N16 ORM swap + N14 shape pin (R10-2: homogeneous 4-key entries) -> fix-r4 prompt; L7/L8 folded (P-Q implication fixtures; P-I: observed node ids); N15 -> phase-7/8 forward notes; N12/N13 next-touch options. Fix r4 (Codex): S6 cascade arbiter, N14 homogeneous payload shape, N16 ORM fixture; focused 65 passed; full 1749/23/1 with the established 23-failure baseline; all named mutations run/reverted; checkpoint pending review.. Fix r4 (Codex, `71f137b`; handoff AFTER checkpoint citing final hash): S6 verified fixture; N14 4-key shape with per-branch OBSERVED node ids (L8 landed); N16 ORM swap; +4 lines production. Coordinator: consumed; re-review r4 prompt authored (probes: clause-deletion arbiter, shape rows, main-worktree probe deviation hash check). **Re-review r4: APPROVED** — perimeter exact (four files; handoff alone in `3a80ee3`), suite 1749/23/1 with the failure set byte-identical to the phase-1 list, focused 65, ruff clean, graph read-only and unchanged (`671fd92a…`, 1 pending, zero delta); zero new findings. **S6 CLOSED — the pin has its arbiter:** verified by hand that `2166/399.5000 = 5.421777…` → Q3 gives exactly the stored `5.42`, so the allowance agrees and the cascade clause is the sole possible cause; deleting `or rate != stored_rate` (`:533`) now reddens **exactly** the cascade row where in r3 it left 65/65 green (r3's mis-declared `and` inversion now reddens both rows — moot). **N14 CLOSED:** all eight entry shapes (four plain, four converted) carry exactly `{field, rederived_value, stored_value, error}`, so callers may key `error` unconditionally; each of the four plain-entry additions probed separately and each bites. **N16 CLOSED:** AST sweep confirms all six rederive rows now build `ItemCostEvaluationTerm`; `_term`/SimpleNamespace survives only in the non-rederive duplicate-purchase shape test (settled r1). **Main-worktree probe deviation resolved as procedural only** — working-tree sha256s equal the declared values AND the sha256 of the blobs as committed in `71f137b`, and `git diff 71f137b..HEAD -- app/` is empty with no post-checkpoint commit touching `app/`: zero probe residue. Carry-forward dispositions table in the Review log (N7→phase 4/5; N15→phase 7/8; N8→coordinator prose; N1/N5/N6/N9–N13→next touch). Card-3 anchors for the single held adjudication (calculator now 547 lines): **1–52**, **131–242**, **375–547**. **Phase 3 closed: B1, B2, B3 and S1–S6 all resolved and independently re-verified across four review rounds; zero findings outstanding.** |
| 4 | Configuration services | `plans/phase_4_configuration_services.md` | ⚑ (rows 15–20) | **APPROVED** | 2026-08-13 | coordinator; Codex; reviewer r1 (Claude); Codex (fix r2, 2026-08-13); reviewer r2 (Claude); Codex (fix r3); reviewer r3 (Claude) | groups, chains, guarded deletes, config status; projection r0 prompt authored (`prompts/reviewer/2026-08-12_phase4_projection_r0.md`; forwards: N3 enum order, N7 persisted-rate arbiter, S4 request parse). Projection r0 AMENDMENTS_REQUIRED (24 rows, 6 blocking; 1 owner card) — fully routed: R11-1 canonicalize-then-derive (intention round 11; owner: round, never refuse); B2 index-discrimination idiom; B3+S7 registry += 3 dual-path identities + audit vocabulary; B4 concurrency harness block; B5 split C6 mutations; B6 structural enum-order guard + N7 in-phase row; S1-S9 + N-pins folded into tasks/criteria C1-C11; N7-consumption -> phase 5, C6 counterparty -> phase 7; implementer prompt authored; Codex implementation: 72 focused tests passed, full suite 1755 passed / 23 established failures / 1 deselected with the failure set unchanged; one batched architecture-graph delta recorded; checkpoint and handoff follow.. Implementer r1 (Codex, `98c75a8`, final): full surface delivered (7 commands + _common helper, 4 queries, 13 routes, canonicalize-then-derive, index discrimination, after_lock seam, structural precedence tuple); graph delta 9 commands + 13 endpoints + 25 edges (47 pending). Coordinator consumption findings -> review probes: P4-1 only 7 NEW test nodes vs 60+ enumerated criteria rows (+6 net suite; the '72 focused' includes phase-3 tests — P-L framing); P4-2 mutation ledger cites archgraph ids not pytest ids (L8 partial); P4-3 C6 concurrency mutations honestly deferred to review. Review r1 prompt authored. **Review r1: CHANGES_REQUESTED** — the production code is substantially right and was independently re-derived on the configured dev DB with a disposable probe suite (C1 all 20 admission rows both chains; C2 adjacency + the three `is_applicable` boundary rows + §7A.3's theorem; **C3 both chains on the genuine two-session DB-conflict path** — loser blocked, exact registered `ConflictError`, exactly one open row after; C4 underflow + `173.46`/`12.0105` + smuggle ignored; **C5 all 12 §6A.4 cells**; C6 serial guard; C7 INV-G1 + three delete rows; C8 rows 1–6 through the status query; C10 scoping/is_deleted/ordering/limit+1; C11 all 9 registered audit strings; 13 routes exactly per §6.5, all ADMIN/MANAGER; scope fence clean; ruff clean; perimeter exact — `git diff 98c75a8 ef21f1e -- app/` empty). Measured suite **1756 passed / 23 known failures / 1 deselected**, failure set byte-identical to the phase-1 baseline, collection **+7 exactly** (the handoff's 1755/+6 is off by one — N8). **2 blocking:** B1 coverage — 7 test nodes against ~60 enumerated rows (C1 2/20; C2/C3/C5/C6/C7/C9/C10/C11 zero; C8 rows 1–4 only as a pure call on `SimpleNamespace`, row 5 absent; **no test in the repo references the item-economics router**, so removing MANAGER from `POST /cost-groups` and deleting the C9 percent docs each leave the FULL suite byte-identical); B2 request models validate shape only — `hours=0`/`util=0` raise `DivisionByZero` inside the calculator (derivation precedes the INSERT, so §6A.6's CHECK premise is not yet in force), `util=150`/`fixed=-1`/`hours=-5`/`percent=-1`/`fixed_amount=-5` re-raise `IntegrityError`, `percent=1000` raises `DataError` — all eight reach the client as HTTP 500 "An unexpected internal error occurred.", violating §6A.4's "rejected twice (request + DB CHECK)" where §6.2 pins that no upper-bound CHECK exists. **3 should-fix:** S1 the router body model **declares** the derived `cost_per_worker_minute_minor` as input (OpenAPI advertises it; value verified dropped) vs §5/§6A.6; S2 dead `_common.reference_exists` + never-true `get_group(for_update=)` (rule 4); S3 C6's interleaved row **cannot be built as written** — a referencing INSERT needs `KEY SHARE` on the version row and blocks under `FOR UPDATE` (verified), so the plan's interleaving deadlocks; corrected arbiter supplied (mutation (b) flips "blocked while locked" True→False; mutation (a) is live and reddens a serial row). 11 notes (N1 S1-before-S2 rests on SQLAlchemy's flush order, unpinned; N6 C5's term-index DB paths are unreachable by construction; N7 `has_open_*` vs applicability verified consistent; N9 ledger cites archgraph ids not pytest ids; N11 §7.5's residual hazard verified live → phase 7's FOR SHARE). All 8 mutations re-run with observed pytest node ids. P4-6: 47 graph items — every claim true, all 22 node anchors correct-or-narrow (4 exact, 5 imprecise), but **all 25 edges share one blanket anchor** `item_economics.py:88-215`, including `command --writes_to--> table` edges whose evidence is in the command modules → recommend promote 13 endpoints + 4 exact commands, edit-then-promote 5 commands + all 25 edges.. Review r1 (Claude): CHANGES_REQUESTED — mechanisms verified substantially correct (all 20 admission rows, both chain races on the real DB path, 12 term cells, classifier, audit, canonicalization); evidence ~6/60 rows (B1); B2 REAL defect: out-of-range numerics -> HTTP 500s (request models validate shape only); S1 router advertises the derived rate as input; S3 plan's C6 interleaving deadlocks via FK KEY SHARE (corrected arbiter supplied); C6/C3 concurrency EXECUTED by the reviewer (works; §7.5 residual verified live -> phase-7 counterparty load-bearing). Graph: 47 items, 17 promote / 30 edit-then-promote, HELD post-approval. Coordinator: plan amended (C5 reachability, C6 observable, B2 bounds task), lessons L1-L5 folded (P-R router harness, P-S reachability, P-T lock observables/counterparties, P-U canonicalization≠validation), fix-r2 prompt authored; Fix r2 (Codex, 2026-08-13): B1/B2/S1/S2/N2 resolved; 126 focused passed; full suite 1875/23/1 baseline-identical; mutation ledger recorded with observed pytest nodes and checksums; graph delta zero; checkpoint commit follows. Fix r2 (Codex, `4e19506`, final; handoff after): +119 tests EXACTLY (focused 126; full 1875/23/1); all criterion families enumerated incl. genuine two-session races + the corrected interleaved observable; B2 bounds; S1/S2/N2/N10; 12 mutations with observed pytest ids AND per-mutation sha256 pairs (new rigor bar); deviation: disposable local CLONES not worktrees (managed .git limitation — hashes recorded). Coordinator: consumed, perimeter exact (10 files); re-review r2 prompt authored (probes + anchor-spans service for the 47 held graph items) **Re-review r2: CHANGES_REQUESTED** — perimeter exact (10 files; `git diff 4e19506..HEAD -- app/` empty) and the disposable-CLONE deviation resolved as procedural only: all six declared main sha256s equal both the worktree files and `4e19506`'s blobs, zero probe residue. Suite 1875/23/1 twice, failure set byte-identical to the phase-1 baseline; focused 126; ruff clean; DB at head; graph read-only and unchanged (`bf6dad5b…`, 47 pending, zero delta). Every sampled ledger mutation bites, three reviewer-applied mutations hash byte-identical to the declared mutated values, and C11 verified HARDER than declared — removing MANAGER from all 13 allow-lists reddens exactly the 13 MANAGER rows, zero collateral (P-G satisfied); C8's B6 structural probe re-run (enum order reversed → 126/126 unchanged); R2-P3 races genuine (`db_session` is a real session; C3/C6 run twice with zero residue; two full-suite runs also zero — rule 11½ holds); R2-P4 all eight r1-proven 500s now 422 naming the field, bounds mirroring §6.2 exactly; R2-P5 all four trims verified. **2 blocking:** B1 — §7A.4's `effective_from IS NULL` open-row column (table rows 4/5/6) is unenumerated: the shipped 20 rows duplicate rows 2 and 8 and never build a live NULL-from open row, so deleting the `open_from is not None` guard leaves C1+C2 green (row 5 is the ordinary supersede path); B2 — C10's rows are decoration: with `limit=1` plus ordering, dropping `workspace_id` from the group list, `is_deleted` from the group list, `is_deleted` from the model list, or `workspace_id` from the basis list each leaves 126/126 green (only 2 of 6 filter rows have an arbiter), and the `ITEM_COST_GROUP_NAME_TAKEN` rename pre-check can be deleted entirely with the suite green. **4 should-fix:** S1 C3 asserts only the ConflictError CLASS, so the index→identity swap reddens only the excluded hand-built proxy; S2 C4's S4-forward row still absent (`Decimal(str(v))`→`Decimal(v)` leaves 126/126 green); S3 bound strictness/accept side unarbitrated (`gt=0`→`ge=0` green, yet 0 would then 500 on `ck_pcbv_fixed_monthly_cost_minor_positive`); S4 C3's seam has no timeout and hung the suite for 120 s under probe. 6 notes (N1 C2 theorem row at `second_day` not today — covered transitively; N2 two r1-'exact' command anchors now STALE from this fix, corrected spans in the handoff; N3 dev-DB residue from interrupted fix-r2 runs, not a teardown defect; N4 4-dp scale unasserted; N5 C8 loop-not-parametrized; N6 C3's monkeypatched-audit seam undeclared in the plan). Anchor-spans service delivered for all 47 held graph items.. Re-review r2 (Claude): CHANGES_REQUESTED, all test-side — B1 the 20 admission rows matched the COUNT not the TABLE (§7A.4 rows 4-6 / the NULL-open column unenumerated; guard-delete stayed green); B2 4/6 filter rows vacuous under limit=1 ordering (5 deletions green) + rename dual-path missing; S1 races assert class not identity; S2 no straddling parse fixture; S3 no adjacent pairs (gt->ge green, reintroduces a 500); S4 unbounded waits (caused a 120s hang + the N3 residue). Coverage otherwise CLOSED; clone deviation procedural (blobs triple-checked); C11 mutation now reds all 13 retention rows. Anchor-spans service delivered for the 47 held items + N7 two missing cost-model-term edges. Coordinator: lessons folded (P-V counts map to tables, P-W filter rows compete for the slice, P-T bounded waits, P-I ledger-recorded gaps close in-cycle); N3 residue -> closeout purge item; fix-r3 prompt authored (test-side only, pre-verified). Fix r3 (Codex, `74b280b`, test-side only, 4 files): B1 table-mapped admission rows (NULL-open fixtures + predecessor close assertion); B2 4 sole-cause filters + both rename paths; S1 identity on the real races; S2 2.675; S3 adjacent pairs; S4 bounded waits; 9 mutations with observed ids + sha256 pairs; focused 139, full 1892/23/1. Coordinator: consumed — probe-file PATHS garbled but sha256s match the real files (transcription defect, recorded); +13 focused vs +17 suite for the reviewer to reconcile; re-review r3 prompt authored. **Re-review r3: APPROVED** — 0 blocking, 0 should-fix, 4 notes. Perimeter exact (4 files, +405/-27; `git diff 2567fc7..HEAD -- app/beyo_manager/` empty; zero production changes). Every r2 gap independently re-proven closed: B1's `open_from is not None` drop (mutant hash = declared) reddens exactly the two `table-row-5` nodes; S1's index->identity swap now reddens the REAL race row, not only the proxy; all SIX C10 filter drops (not just the four declared) redden their own sole-cause row, and `models-workspace` / `basis-is_deleted` redden the legacy arbiter too; the rename pre-check delete, S2's `Decimal(v)` and S3's `gt->ge` each redden exactly their named row (mutant hashes = declared); C1's original `is_deleted=false` mutation survives the table rewrite. P-V mapping verified one-for-one against §7A.4 (20 ids, rows 1-10 x 2 chains, no duplicates/omissions, row 5 asserts the predecessor close). S4 proven by re-running the r2 hang configuration: 120 s hang -> 3.35 s red. Concurrency subset (now 6, incl. the new committing rename-DB row) twice with flat row counts (rule 11½). Suite 1892/23/1, failure set byte-identical to the phase-1 baseline; ruff clean; DB at head. Consumption notes resolved: the garbled probe PATHS are a transcription defect (all six declared sha256s match the real files), and the +13/+17 gap is two different focused sets — on one consistent set 124 -> 141 = +17, exactly the suite's collection delta. Graph read-only, `bf6dad5b…`, 47 pending, zero delta; r2's spans still valid (two spot-checked exact). 4 notes: N8 the three accept-boundary rows are one fixture with three names (tightening any bound reddens all three); N9 a duplicated percent-1000 reject row; N10 the new 0.3/0.5 s waits are wall-clock bounds — first flake suspect; N11 (outside phase 4) the full suite commits ~116 non-economics workspaces per run while phase-4's own tests leave zero. Carry-forwards routed. |
| 4B | Category-driven group selection (§7C, round 12) | `plans/phase_4b_category_selection.md` | ⚑ (selection = S1 mechanism; inventory row 19 superseded by §7C) | **APPROVED** | 2026-08-13 | coordinator; Codex; reviewer r1; Codex (fix r1); re-reviewer r2 | owner scope decision pre-v1: major_category NOT NULL + INV-G3 + classifier rework + per-category status; plan to be authored by a focused planner session (`prompts/planner/2026-08-12_phase4b_planner_r1.md`); starts only after phase 4 APPROVED. Plan authored (planner r1, consumed: perimeter exact, 0 owner cards; pins L1-L4 RATIFIED; registry additions applied — ItemMajorCategoryEnum/item_major_category_enum ownership, 2 identities, resolve_major_category, slug); projection r0 prompt authored (`prompts/reviewer/2026-08-12_phase4b_projection_r0.md`, parallel-safe with phase-4 review); implementation gated on phase 4 APPROVED. Coordinator (2026-08-13, gate open at `8ca2bf9`): N-f dependency greps re-run against the final tree — task 8 gains T8-7…T8-10 (the fix cycles' `test_phase4_fix_coverage.py` helper/fixtures/C8-shape + the router role-gate payload), appended to the plan as a GOVERNING prompt-time block; env facts pinned (groups table 0 rows post-purge, head `90cdd23a828e`); implementer r1 prompt authored (`prompts/implementer/2026-08-13_phase4b_implement_r1.md`). Implementer r1: migration/model/request and command category contracts, category-aware classifier and per-category status shape, serializer/router surfaces, tests and mutation ledger; focused 256 passed twice; full non-e2e 1926 passed / 23 known failures / 1 deselected twice; ruff clean; checkpoint follows.. Implementer r1 (Codex, `cfec9df`, final): migration `5caae620088c` (pre-flight report-first, enum reuse, INV-G3 partial unique); category-aware create/update with the immutability guard; §7C.2 classifier + resolve_major_category; per-category status shape; surfaces + T8-7..T8-10; 17-row mutation ledger; focused 256 x2; full 1926/23/1 x2 baseline-identical; graph +6 source links (`5e4f368d…`). ONE owner card OD-1 (env.py rollback outside the fence) — ANSWERED: retain, reviewer verifies both directions. Coordinator: consumed — perimeter exact incl. the declared exception; arithmetic exact (+34 selected = +34 passed); one declaration defect (63-char mutant SHA, router row) for the reviewer to recompute; review r1 prompt authored  Reviewer r1 (Claude Opus 5, CHANGES_REQUESTED): OD-1 probes run — P4B-0a REPRODUCED (warm upgrade silently persists neither revision nor DDL; Alembic `_in_external_transaction` set by the cold-build preflight; cold builds were rescued only by two historical `op.execute("COMMIT")` revisions), P4B-0b FAILED → **B1 blocking**: the retained rollback leaves `mig_cold_build_workspace` + 7 pause_reasons in every cold build (cleanup's DELETEs are never committed). S1 `compare_metadata` is blind to partial-index predicate drift; S2 C6(c) has no arbiter. Notes N1–N6 (M2 declared 1 of 7 nodes; the 63-char SHA is a transcription typo, mutation reproduces; the vacuous-mutation report is correct). C1–C8 otherwise re-derived green; suite 1926/23/1 twice, baseline-identical; ruff clean on all 21 changed files; dev DB at head; graph untouched. ONE owner card (authorize the second env.py edit).. Coordinator (post-review r1): card 1 answered OPTION ONE (second env.py edit authorized — that file only, this cycle only; N6 routed to migration-infra owner); P4B-0a outcome recorded (rollback load-bearing; historical CONCURRENTLY COMMITs masked the defect); lessons folded (P-X harness visibility, P-Y per-row assertion shape, P-I fifth ext full observed set, P-Z scope-exception property test, L5 -> §10 history correction); N3/N4 -> phase-8 forward notes; plan gains the GOVERNING fix-r1 amendments block (C9 cold-build end-state, C1(e) predicate structural row, C6 exact-dict restatement + C6(b) collapse); fix-r1 prompt authored (`prompts/implementer/2026-08-13_phase4b_fix_r1.md`). Fix r1 (Codex): B1 cleanup commit plus C9 cold-build proof; S1 predicate structural row; S2 whole-payload exact-dict status row; focused 200 x2; full 1927/23/1 with the baseline failure set; ruff clean; graph N5 anchor correction was completed by the coordinator at `5d8b6a6` (revision `5c60534d…`) before that session.. Coordinator: fix-r1 handoff consumed — perimeter exact (env.py +1 line the whole production diff), arithmetic exact (+1 = S1's row; selector named, 200x2), hashes byte-identical incl. B1's mutant = the r1 reviewer's pre-fix env.py hash (cross-corroborated); N5 coordinator-performed (unlink+link, revision 5c60534d, commit 5d8b6a6); transcription defect recorded (S1 restored-SHA strings truncated — real file verified); re-review r2 prompt authored (`prompts/reviewer/2026-08-13_phase4b_rereview_r2.md`)  **Re-review r2 (Claude Opus 5): APPROVED — 0 blocking, 0 should-fix, 0 new findings.** B1 CLOSED: from-scratch cold build ends at head with workspaces/pause_reasons/cold-build rows all ZERO (state-queried, not exit code), and reverting the one commit line reproduces 1/7/1 — its mutant hash equals review r1's pre-fix env.py hash, proving the fix is that line alone. Failure-path depth added by the re-reviewer: the C1(b) pre-flight refusal still exits 1 leaving revision/column/index untouched, and downgrade still persists — the finally-block commit publishes no partial DDL. S1 CLOSED (both r1-green predicate probes now redden C1(e); mutant hashes reproduce). S2 CLOSED (whole-payload exact-dict row; Probe B now bites). N5 CLOSED (span 44-82 exact; graph `5c60534d…`, 2 pending N7 untouched). §10 history correction verified. Suite 1927/23/1 twice, baseline-identical; focused 200x2 and 257; ruff clean; dev DB at head; zero residue. Carry-forward unchanged: N1 next-touch, N3/N4 -> phase 8, N6 -> migration-infra owner.. Coordinator: CLOSED OUT (`377d0b9`) — 12 artifacts to archive/plan_4b/; N7 edges promoted, graph fully human_confirmed 0 pending (`41b178d`, revision 88e185f7); no purge owed |
| 5 | Valuation surface | `plans/phase_5_valuation_surface.md` | ⚑ (rows 15,16 — valuation chain; 34) | **IMPLEMENTED** | 2026-08-14 | planner; Codex; reviewer r1 (Claude) | ItemValuation chain command + preview implemented. Projection r0 prompt authored 2026-08-13 (`prompts/reviewer/2026-08-13_phase5_projection_r0.md`; folds §7C shipped signatures, N-d live re-measure, forward-notes block, head 5caae620088c, baseline 1927/23/1). **Projection r0 (Claude Opus 5): AMENDMENTS_REQUIRED** — 16 rows (6 blocking), 7 notes, 2 owner cards; probes EXECUTED (persisted-rate Q2-tie fixture computed 76800.20 vs 76800.00; self-FK teardown hazard disproven; N-d re-measured 53/225/193 of 471; L7 parser leading-token loss verified; L18 INV-V1 premise re-confirmed live). Coordinator: cards ANSWERED and folded as intention round 13 (R13-1 preview key + computable-state numerics + first-save-is-version-1 no-confirmation pin, confirmed against a coordinator story; R13-2 deleted rows hidden from history, INV-V1 current predicate, created_at DESC+client_id DESC); §9 P-B refined; §6.4 += item_valuation.created/.deleted; §6.5 += resolve_economics_selection/EconomicsSelection + ITEM_READINESS_PRECEDENCE/resolve_item_economics_status + the response envelope + L15 correction; plan gains the GOVERNING amendments block (L1-L16 + notes + delegations); implementer r1 delivered set/delete/history services, persisted-rate preview, request validation, three ADMIN/MANAGER routes, tests, router README, and additive architecture delta (5 nodes, 7 edges; revision b5e6fe094cae). Implementer r1 (Codex, `8b4ac06`, final; handoff after): full surface (set/delete commands, history query, 3 routes, selection + readiness resolvers per §6.5, preview envelope with the persisted-rate fixture 76800.20, R13-2 history pins, audit events); focused 111; graph delta 5 nodes + 7 edges (`b5e6fe09…`, pending). Coordinator: consumed — perimeter exact (16 files), 3 restored hashes byte-identical, but TWO findings routed to review: arithmetic off by one (claimed 1951+23 vs 1973 selected; expected 1950/23/1) and the ledger declares 3 mutations vs ~10 named in the amendments (L1/L2x2/L15/L16/L7/audit owed — the central review probe); review r1 prompt authored (`prompts/reviewer/2026-08-13_phase5_review_r1.md`). **Review r1 (Claude Opus 5): CHANGES_REQUESTED** — perimeter exact (16 files, tree clean, `git diff 8b4ac06..HEAD -- app/` empty, 3 declared hashes byte-identical), ruff clean, suite **1950/23/1** with the failure set byte-identical to the phase-1 baseline (**P5-A resolved: the handoff's 1951 is derived-not-read — +23 tests, not +24**), DB at head, graph read-only zero delta. **P5-B resolved: 7 owed mutations run, 4 do not bite.** 4 blocking — B1 `delete_item_valuation` omits `is_deleted = false` from INV-V1's predicate, so after delete-then-reset the live valuation is permanently undeletable (reproduced; one-clause fix verified 346/0); B2 C5's routed 12-value enumeration (L4) not built (3 statuses in one monolithic test, no P-V ids, no `item_cost_evaluations` assertion — reviewer probes for the missing rows pass, so the code is right and the evidence absent); B3 the L15 structural row does not exist (inlining a snapshot read leaves 345 green); B4 the three-way currency equality has no per-clause arbiter (all three clause drops green) and the ids misname their pairs — equality is transitive so the middle clause is provably redundant; verified 2-clause correction gives both clauses sole-cause arbiters. 5 should-fix — S1 the purchase-cost↔currency adjacent pair unarbitrated (swap green; verified fixture supplied); S2 C6 unbuilt (drop *and* reverse of the history ordering both green — the only assertion is a one-element list); S3 C4's re-set row absent (the row that would have caught B1); S4 C2 cannot count INV-V1's predicate and neither race path's observable is asserted; S5 C3 missing the missing-currency and three accept rows. 8 notes (N1 L12's *named* mutation is inert — only raw re-division bites, verified fixture `13.0000`→`76923.08`; N2 DELETE's hardcoded `item_unvalued` → phase 8; N4 pre-checkpoint dev-DB residue → closeout purge, not a teardown defect; N6/N7 graph read-boundary + stale `domain-item-economics` anchor). Verified correct: chain order, race identity on the real conflict path, L1 delegation (12-node blast radius), L2(i) structural independence, L7 exact leading token, L9 both audit events, P-R role gates (exactly 3 MANAGER rows), R13-2 filter, L12 arithmetic, L5/L6/L18/L20. Anchor-spans service delivered for all 12 pending items (9 exact, 3 corrected) plus the undeclared stale link. Lessons: routed amendments need ledger rows (P-I ext); transitive relations enumerate by state not clause; a named mutation must be checked against the implementation it meets (P-Q ext); a monolithic test cannot discharge an enumerated criterion (P-V ext). **Review r1 (Claude Opus 5): CHANGES_REQUESTED** — 4 blocking, 5 should-fix, 7 notes, 0 owner cards. B1 REAL defect: delete-then-reset makes the new price undeletable (delete predicate missing is_deleted=false; reachable via PUT-DELETE-PUT-DELETE; one-line fix executed+verified 346/0). B2 C5's 12-value enumeration unbuilt (3 statuses in one monolithic node); B3 the L15 structural row absent (inline snapshot read leaves 345 green); B4 the 3-clause currency check has NO per-clause arbiter (transitivity — provably unfixable pairwise; verified 2-clause correction). S1 precedence pair 2 unarbitrated; S2 C6 unbuilt (ordering droppable/reversible green); S3 the re-set row absent (B1's would-have-caught); S4 races can't count; S5 C3 missing 4 rows. N1 L12's NAMED mutation inert by construction (calculator re-derives the persisted value exactly; corrected fixture 13.0000 -> 76923.08). P5-A resolved: true suite 1950/23/1 — the handoff's 1951 was DERIVED (1927+24), not read. P5-B resolved: 7 owed mutations run, 4 don't bite. Graph: 12 claims all TRUE, anchor service delivered (2 imprecise/2 wide), N6 five missing reads_from edges, N7 domain source-link stale (L1 moved the function; re-link resolve_economics_selection 80-126). Coordinator: lessons folded (P-I 6th ext N-named=N-rows; P-AA transitive states not clauses; P-Q ext mutation-vs-implementation; P-V 2nd ext monolithic nodes); plan gains the GOVERNING fix-r1 amendments block; fix-r1 prompt authored (`prompts/implementer/2026-08-14_phase5_fix_r1.md`). Fix r1 (Codex, `a0cebde`, final): production diff exactly TWO lines (delete predicate +1, redundant currency clause -1); C5 rebuilt as 12 ids; L15 structural row; shared delete-then-reset fixture (C4/C6/L13); S1/S4/S5; N1 fixture 13.0000->76923.08; 14-row ledger, all previously-inert mutations now red. Coordinator: consumed — perimeter exact, arithmetic READ (1968/23/1 = 1991 selected exactly), and BOTH final production hashes byte-identical to files the r1 REVIEWER produced (ab9aebbe = the B1 correction file; 75087586 = the M5.b 2-clause probe) — the fix shipped the verified corrections to the byte; re-review r2 prompt authored (`prompts/reviewer/2026-08-14_phase5_rereview_r2.md`) |
| 6 | Legacy money migration & API bridge | `plans/phase_6_legacy_migration_api_bridge.md` | ⚑ (rows 31,32) | NOT_STARTED | 2026-08-11 | planner | journaled migrate-and-drop + reject-iff-non-null bridge |
| 7 | Evaluations | `plans/phase_7_evaluations.md` | ⚑ (rows 2,5,7,10,14,16,17,19,21–25) | NOT_STARTED | 2026-08-11 | planner | commit tx, projections, promotion, auto path, mirror |
| 8 | Status & results | `plans/phase_8_status_results.md` | ⚑ (rows 9,26–30,34) | NOT_STARTED | 2026-08-12 | coordinator | status query, result handler, §8B boundary emissions (round-6 fold: READY/reopen hooks, widened guard, C6b) |
| 9 | Living docs & drift routing | `plans/phase_9_docs_and_drift.md` | waivable (no S1/S2 mechanism; docs only) | NOT_STARTED | 2026-08-11 | planner | living-docs page, §2.6 + D-1…D-4 landing spots |

## 5. Contract resolution (goal-mapping guide protocol)

Run per `task_system/backend_contract_goal_mapping_guide.md` from intention §15's
bundle. Implementing sessions re-emit this list before coding. Pattern-authority
rule binds: contracts say how to write; implementation files say only what exists.

**Selected (core):** `01_architecture`, `04_context`, `05_errors`,
`06_commands` + `06_commands_local` (maybe_begin, session-call safety,
subordinate-command event rule), `07_queries` + `07_queries_local` (offset
pagination override), `09_routers`, `21_naming_conventions`, `40_identity` +
`40_identity_local`, `41_user` + `41_user_local`, `42_event` + `42_event_local`,
`48_presence` + `48_presence_local`.

**Selected (intention §15 bundle):** `03_models`, `08_domain`, `11_infra_events`,
`15_testing`, `16_background_jobs`, `24_multi_tenancy`, `25_soft_delete`,
`28_roles_permissions`, `29_feature_workflow`, `30_migrations`, `36_audit_log`,
`46_serialization` + `46_serialization_local`, `50_testing_strategy`,
`51_worker_runtime`, `52_replayability`.

**Added from guide:**
- `12_infra_redis`: trigger "worker" — the result handler rides the outbox →
  `queue:analytics` pipeline.
- `32_concurrency`: the goal explicitly requires row-locking discipline (§7A.2 race
  arbitration, §7A.6 `FOR UPDATE`/`FOR SHARE`, §7B.1 task lock).

**Excluded (with reasons):**
- `13_sockets`: no new socket surface; workspace events follow 42/11.
- `53_operational_cli`: the CLI re-emit is "only if cheap" (§13, R4-1) — load at
  prompt time iff the coordinator picks it up.
- `55_query_filters_local`: v1 list endpoints take no search/filter params; add at
  prompt time if that changes.
- `37_scheduled_jobs`: future-dated config versions are deferred — no scheduler.
- `49_observability_runtime`, `54_ci_cd_runtime`, `33_deployment`,
  `31_health_observability`: no new worker process, no CI/deploy change — the handler
  registers in the existing analytics worker.
- `57_shopify_integration`, `34_file_storage`, `35_gdpr_erasure`, `18_security`,
  `19_integrations`, `22_performance`, `20_api_versioning`, `26/27/38/39/43/44/45/47/56`:
  no touchpoint in this domain's v1 surface.

**Contract gap found by the planner (coordinator to route):** canonical `05_errors.md`
defines a `code: str` attribute on `DomainError` subclasses; the implementation
(`app/beyo_manager/errors/base.py`, `validation.py`, `not_found.py`) carries only
`message` + `http_status` — no code field, and no `05_errors_local.md` records the
divergence. This plan does not repair the drift; §6's error-identity carrier decision
below is valid under either resolution.

**Contract gap 2 (phase-1 projection D7, recorded 2026-08-12):** `46_serialization.md`
mandates router-owned serialization ("services never call serializer functions";
dataclasses, never dicts); the repo's entire task / working-section query layer does
the opposite, and `46_serialization_local.md` is an unmodified template recording no
override. **Standing divergence record:** phases of this project keep serialization
where the code they modify has it (the query layer); re-emitting the contract bundle
is never license to relocate serialization mid-phase. The local contract file's
actual amendment lands with the phase-9 drift batch, alongside the `05_errors` gap.
Verified not in conflict: `28_roles_permissions` blesses `require_roles` route
dependencies and the `role_name` claim — identity-derived flags at the query boundary
are contract-faithful.

## 6. Shared skeleton & naming registry (FINAL — authority over intention's proposals)

Registry authority per intention §4 preamble. Conventions per §2.5 and
`21_naming_conventions`. Every name below is fixed; a session needing an unlisted
name routes it back to the coordinator rather than inventing one.

### 6.1 Tables, model classes, client_id prefixes

| Table | Class | Prefix | Model file (`app/beyo_manager/models/tables/item_economics/`) |
|---|---|---|---|
| `production_cost_groups` | `ProductionCostGroup` | `pcg` | `production_cost_group.py` |
| `production_cost_group_sections` | `ProductionCostGroupSection` | `pcgs` | `production_cost_group_section.py` |
| `production_cost_basis_versions` | `ProductionCostBasisVersion` | `pcbv` | `production_cost_basis_version.py` |
| `cost_model_versions` | `CostModelVersion` | `cmv` | `cost_model_version.py` |
| `cost_model_terms` | `CostModelTerm` | **`cmvt`** | `cost_model_term.py` |
| `item_cost_evaluations` | `ItemCostEvaluation` | `ice` | `item_cost_evaluation.py` |
| `item_cost_evaluation_terms` | `ItemCostEvaluationTerm` | `icet` | `item_cost_evaluation_term.py` |
| `item_cost_results` | `ItemCostResult` | `icr` | `item_cost_result.py` |
| `item_valuations` | `ItemValuation` | `ival` | `item_valuation.py` |

- **`cmvt` replaces the intention's proposed `cmt`, which collides with
  `ContentMention | cmt`** in `client_id_prefix_map.md` (verified 2026-08-12).
  Mnemonic: cost-model-version term. All other proposed prefixes verified free.
- All nine registered in `models/__init__.py` and appended to
  `client_id_prefix_map.md`; one table guide `models/tables/item_economics/README.md`.
- **ORM annotation caveat (phase-3 projection S7, binding on phases 3–8):** eleven
  phase-2 `Numeric` columns are annotated `Mapped[float]`
  (`production_cost_basis_version.py:24-26`, `item_cost_evaluation.py:33-38`,
  `item_cost_evaluation_term.py:22`, `cost_model_term.py:22`,
  `item_cost_result.py:23,25`). Runtime is correct (asyncpg returns `Decimal`);
  only the annotations lie. **§6A.1 governs boundary types, not the annotations** —
  fixtures on unsaved instances assign `Decimal` explicitly (no DB round-trip
  coerces them). Annotation fix queued in the phase-9 drift batch (repo precedent:
  `user_work_profile.py:33` annotates `Mapped[Decimal | None]`).
- Migration journal table `item_valuation_migration_journal` (§10A.1) is
  migration-internal: no ORM model, no prefix, PK `item_client_id`; created and
  dropped by the phase-6 migrations only.
- Column names exactly as intention §4/§4A (as amended: `cost_per_worker_minute_minor`,
  `cost_per_worker_minute_minor_snapshot`, `percent_value`, `fixed_amount_minor`).
  Temporal columns `effective_from`/`effective_to` (Date) — a deliberate, recorded
  deviation from `21`'s `<context>_date` suffix guidance, justified by §7A.3's
  calendar-date resolution semantics and vocabulary continuity with the sibling
  compensation intention. *(Correction, projection D14: the previously cited
  `issue_category_configs` precedent was dropped from the schema by `99accdeba8b9`
  and used `DateTime`, not `Date` — no live effective-dated table exists; the
  decision stands on the semantics, not on precedent.)*

### 6.2 Constraint & index names (repo idiom: `uix_` partial uniques, `ck_` CHECKs)

| Invariant | Name |
|---|---|
| group name unique per workspace (non-deleted) | `uix_production_cost_groups_name_active` |
| **INV-G3** one active group per (workspace, major_category) — round 12 | `uix_production_cost_groups_major_category_active` |
| INV-G1 one active group per section | `uix_production_cost_group_sections_active` |
| INV-B1 one open basis version per group | `uix_production_cost_basis_versions_open` |
| INV-M1 one open model version per workspace | `uix_cost_model_versions_open` |
| A5 one `item_purchase_cost` term per version | `uix_cost_model_terms_purchase_cost` |
| term name unique per version (non-deleted) | `uix_cost_model_terms_name_active` |
| INV-E1 one current committed evaluation per task | `uix_item_cost_evaluations_current` |
| INV-V1 one current valuation per item | `uix_item_valuations_current` |
| one result per episode | `uq_item_cost_results_task_id` (plain unique) |

**CHECK constraints (CLOSED enumerated list — phase-2 projection D1/D2, 2026-08-12;
this replaces the earlier pattern rows).** Registry rule: names use the full table
name unless the result exceeds **60 bytes** (PostgreSQL truncates at 63 silently —
verified empirically), in which case the table token is the registered client
prefix. C1 asserts exactly this list, nothing else.

| Constraint | Name (bytes) |
|---|---|
| `production_cost_basis_versions.fixed_monthly_cost_minor > 0` (A1) | `ck_pcbv_fixed_monthly_cost_minor_positive` |
| `production_cost_basis_versions.cost_per_worker_minute_minor > 0` (A2) | `ck_pcbv_cost_per_worker_minute_minor_positive` |
| `production_cost_basis_versions.monthly_paid_hours > 0` | `ck_pcbv_monthly_paid_hours_positive` |
| `production_cost_basis_versions.planning_utilization_percent > 0` | `ck_pcbv_planning_utilization_percent_positive` |
| `production_cost_basis_versions.planning_utilization_percent <= 100` | `ck_pcbv_planning_utilization_percent_max` |
| basis-version window | `ck_production_cost_basis_versions_effective_window` |
| model-version window | `ck_cost_model_versions_effective_window` |
| term per-type nullability (6A.4) | `ck_cost_model_terms_value_by_type` |
| `cost_model_terms.percent_value >= 0` | `ck_cost_model_terms_percent_value_non_negative` |
| `cost_model_terms.fixed_amount_minor >= 0` | `ck_cost_model_terms_fixed_amount_minor_non_negative` |
| `item_cost_evaluations.expected_sale_price_minor >= 0` | `ck_ice_expected_sale_price_minor_non_negative` (full name is 63 bytes — prefix token per the rule) |
| `item_cost_evaluations.purchase_cost_minor >= 0` | `ck_ice_purchase_cost_minor_non_negative` |
| `item_valuations.expected_sale_price_minor >= 0` | `ck_item_valuations_expected_sale_price_minor_non_negative` |
| `item_valuations.purchase_cost_minor >= 0` | `ck_item_valuations_purchase_cost_minor_non_negative` |
| valuation ≥1 amount | `ck_item_valuations_amount_present` |
| `item_cost_results.actual_worker_seconds >= 0` | `ck_item_cost_results_actual_worker_seconds_non_negative` |

**Deliberate CHECK absences (registry decisions — stated so nobody "fixes" them):**
`production_budget_minor` / `allowed_worker_minutes` carry NO CHECK (A8);
`task_state_snapshot` carries NO narrowing CHECK (admission is the §8B.2 handler's
job); `percent_value` has NO upper-bound CHECK — `Numeric(6,3)` is the bound (1000
raises `NumericValueOutOfRangeError`, a DataError, before any CHECK — verified;
projection D12).

**Named foreign keys (projection D7):** the three self-FKs are `use_alter=True`
per §2.5's pointer convention, explicitly named, and **hand-added to the migration**
— autogenerate omits `use_alter` FKs in this repo (precedent `243e62bcd858`):
`fk_item_cost_evaluations_superseded_by_id`,
`fk_item_cost_evaluations_promoted_from_id`,
`fk_item_valuations_superseded_by_id`.

### 6.3 Enums

| Where | Python class | PG type | Notes |
|---|---|---|---|
| term calculation type | `CostModelTermCalculationTypeEnum` | `cost_model_term_calculation_type_enum` | members `PERCENTAGE_OF_EXPECTED_SALE_PRICE`, `FIXED_AMOUNT`, `ITEM_PURCHASE_COST`; lowercase values |
| evaluation kind | `ItemCostEvaluationKindEnum` | `item_cost_evaluation_kind_enum` | `PROJECTION`, `COMMITTED` |
| `item_valuations.currency` | **reuse `ItemCurrencyEnum`** (`domain/items/enums.py`) | `item_valuation_currency_enum` (`create_type=True` — ownership here) | per-table type |
| `production_cost_basis_versions.currency` | reuse `ItemCurrencyEnum` | `production_cost_basis_version_currency_enum` (`create_type=True`) | per-table type |
| `cost_model_versions.currency` | reuse `ItemCurrencyEnum` | `cost_model_version_currency_enum` (`create_type=True`) | per-table type |
| `item_cost_evaluations.currency` | reuse `ItemCurrencyEnum` | **reuses `item_valuation_currency_enum`** with `create_type=False` — ownership stays on `item_valuations.currency` (registry decision 2026-08-12, review-r1 S1: the intention's fourth currency column was missed by the count-based registry row; reuse ratified — R2-1 pattern, drop order verified safe; a fourth type would cost a follow-up revision for no behavioral difference) | four columns, three PG types |
| evaluation episode snapshots | reuse `TaskTypeEnum` / `TaskReturnSourceEnum` | **reuse** `business_task_type_enum` / `task_return_source_enum` with `create_type=False` | type-creation ownership stays on `tasks` columns (R2-1 lesson: pin ownership explicitly; PG enums are append-only, so snapshots can never hold a value the type lost) |
| result lifecycle snapshot (round 6) | reuse `TaskStateEnum` | **reuse** `task_state_enum` with `create_type=False` (ownership stays on `tasks.state`, `task.py:52`) | `item_cost_results.task_state_snapshot` — §4.6 as amended, §8B.2 |
| `production_cost_groups.major_category` (round 12, §7C) | reuse **`ItemMajorCategoryEnum`** (`domain/items/enums.py:17`; WOOD="wood", SEAT="seat") | **reuse `item_major_category_enum`** with `create_type=False` (ownership: `item_categories.major_category`, `item_category.py:24-28`, `create_type=True` there; migration-site enforcement per the phase-2 lesson; pinned by the 4B planner 2026-08-12, PG labels verified live) | wood \| seat |
| economics status | `EconomicsStatusEnum` | **none — never persisted** | code-owned (§11A.4, catalog lesson); the ordered members of §11A.4 **as amended by §7C.3** (now incl. `ITEM_MISSING_MAJOR_CATEGORY = "item_missing_major_category"`) — the list derives from §11A.4, never a count (P-L); lowercase values. **Declaration order carries NO precedence** (corrected 2026-08-12, phase-4 projection B6: as shipped the declaration order differs from §11A.4's evaluation order — precedence lives in `configuration.py`'s explicit ordered sequence, never in enum iteration) |

All new enums via `configure_sa_enum_values` (`models/base/sa_enum.py`), lowercase
values, in `app/beyo_manager/domain/item_economics/enums.py`.

### 6.4 Error identities

The implementation's `DomainError` classes carry no `code` field (§5 gap). **Carrier
decision:** an error identity is the leading token of `message`, format
`<IDENTITY>: <human sentence>`. Tests assert the exact leading token (and class /
http_status). Raised as `ValidationError` unless noted `ConflictError`.

Identity list (FINAL — includes registry-authored names for errors the intention
required but did not name):

- Selection (§7A.5, in order): `ITEM_COST_NO_COST_GROUP`,
  `ITEM_COST_AMBIGUOUS_COST_GROUP` (message names count + group ids),
  `ITEM_COST_NO_BASIS_VERSION` (rows 3 AND 4 — same identity, pinned),
  `ITEM_COST_NO_COST_MODEL_VERSION`.
- Inputs (§6A.9, §6A.4, §7B): `ITEM_COST_ITEM_UNVALUED`,
  `ITEM_COST_EXPECTED_PRICE_REQUIRED` (registry-authored),
  `ITEM_COST_PURCHASE_COST_REQUIRED`, `ITEM_COST_CURRENCY_MISMATCH` (message names
  both sides and which pair failed), `ITEM_COST_TASK_TERMINAL`,
  `ITEM_COST_NO_PRIMARY_ITEM`,
  **`ITEM_COST_TERM_SHAPE_INVALID`** (registry-authored 2026-08-12, phase-3
  projection B3 — the §6A.4 calculator re-validation: raised as `ValidationError`,
  message names the `calculation_type` and the offending column; also covers a
  duplicate `item_purchase_cost` snapshot term, projection S8).
- Rate: `ITEM_COST_RATE_UNDERFLOW` (§6A.6).
- Chain races (`ConflictError`, §7A.2): `ITEM_COST_CONCURRENT_COMMIT`,
  `ITEM_COST_CONCURRENT_VALUATION`, `ITEM_COST_CONCURRENT_BASIS_VERSION`,
  `ITEM_COST_CONCURRENT_MODEL_VERSION`.
- Version admission (§7A.4; chain named in the identity, registry-authored):
  `ITEM_COST_BASIS_VERSION_EFFECTIVE_FROM_FUTURE` / `_REQUIRED` / `_NOT_AFTER_OPEN`,
  `ITEM_COST_MODEL_VERSION_EFFECTIVE_FROM_FUTURE` / `_REQUIRED` / `_NOT_AFTER_OPEN`.
- Guarded deletes (§7A.6, §7.5; registry-authored):
  `ITEM_COST_BASIS_VERSION_IN_USE`, `ITEM_COST_MODEL_VERSION_IN_USE`,
  `ITEM_COST_GROUP_IN_USE`.
- Valuation validation (§4.7A, test 11; registry-authored):
  `ITEM_COST_VALUATION_AMOUNT_REQUIRED` (both amounts NULL),
  `ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE` (delete attempted on a superseded
  valuation row, §7.5). Negative amounts and missing currency are request-schema
  rejections (pydantic 422) + DB CHECK — no domain identity.
- Group membership (INV-G1; registry-authored): `ITEM_COST_SECTION_ALREADY_GROUPED` —
  same identity on the application pre-check (`ValidationError`) and on the DB
  conflict path (`ConflictError`), mirroring the §7A.5 rows-3/4 same-identity rule.
- Config uniqueness conflicts (registry-authored 2026-08-12, phase-4 projection B3 —
  dual-path like the membership identity: `ValidationError` on the pre-check,
  `ConflictError` on the DB conflict):
  `ITEM_COST_GROUP_NAME_TAKEN` (`uix_production_cost_groups_name_active`),
  `ITEM_COST_TERM_NAME_TAKEN` (`uix_cost_model_terms_name_active`),
  `ITEM_COST_PURCHASE_TERM_DUPLICATE` (`uix_cost_model_terms_purchase_cost` — the
  command's DB-conflict carrier; the calculator's re-validation keeps its own
  `ITEM_COST_TERM_SHAPE_INVALID`).
- Category selection (registry-authored 2026-08-12, phase-4B planner, ratified):
  `ITEM_COST_GROUP_CATEGORY_TAKEN` — INV-G3
  (`uix_production_cost_groups_major_category_active`), dual-path
  (`ValidationError` pre-check on create AND update-flip; `ConflictError` on the
  DB conflict), message names the category value **on the pre-check path only** (4B projection L-9: the DB-path translation emits the uniform conflict sentence per phase-4 N4);
  `ITEM_COST_GROUP_CATEGORY_IMMUTABLE` — `ValidationError`, §7C.4's refusal,
  message names the group and its current category. Audit vocabulary: NO 4B
  additions (event names unchanged; payloads only).
- **Audit event vocabulary (registry-authored 2026-08-12, phase-4 projection S7)** —
  `write_audit` events for this domain, format `<entity>.<action>`:
  `production_cost_group.created` / `.updated` / `.deleted`;
  `production_cost_group_section.added` / `.removed`;
  `production_cost_basis_version.created` / `.deleted`;
  `cost_model_version.created` / `.deleted`;
  `item_valuation.created` / `item_valuation.deleted` (phase 5, registered
  2026-08-13 per projection L9);
  (phase 7 adds `item_cost_evaluation.*` rows here before use — never
  free-formed in a command.)
- API bridge (§10A.3): pydantic `ValidationError` with message
  `ITEM_MONEY_MOVED: item money fields moved to the item-valuation endpoint`.
- Migration pre-flight P1/P2 (§10A.2): `RuntimeError` aborting `upgrade` with a row
  report — never a DomainError (no request context).

### 6.5 Files — domain, services, workers, routers

- **Domain (pure, no I/O):** `app/beyo_manager/domain/item_economics/`
  `calculator.py` (§6A entire: boundary guards, Q1–Q5, budget, rate, allowance,
  consumption/variance, `CALCULATION_VERSION: int = 1`, `rederive()`).
  **Public API (D1 report folded 2026-08-12 — phases 4/5/7/8 call these names;
  pending phase-3 review):** `CALCULATION_VERSION`, `REDERIVE_SKIPPED`,
  `calculate_percentage_term_amount`, `calculate_term_amount`,
  `calculate_term_amounts`, `calculate_production_budget`,
  `calculate_cost_per_worker_minute`, `calculate_allowed_worker_minutes`,
  `calculate_actual_worker_minutes`, `calculate_consumed_cost_minor`,
  `calculate_remaining_worker_minutes`, `calculate_percent_consumed`,
  `calculate_variance_worker_minutes`, `calculate_variance_cost_minor`,
  `validate_currency_equality`, `rederive`.
  **Registry decision (review N2, 2026-08-12; count corrected per re-review N8 —
  P-L: items, never counts):** the two structural Protocols `EvaluationSnapshot`
  and `TermSnapshot` join the public surface (phases 7/8 type against them), as
  does the marker constant `REDERIVE_MISMATCH` (R9-1); `REDERIVE_SKIPPED` is
  already among the 16 names above. The module declares **`__all__`** with exactly
  this enumerated surface (the 16 + the 2 Protocols + `REDERIVE_MISMATCH`) —
  stray re-exports (`Decimal`, `ROUND_HALF_EVEN`, `Sequence`, `ValidationError`)
  are not public API.
  4B additions (planner, ratified): `serialize_production_cost_group` carries
  `major_category`; migration slug `add_major_category_to_production_cost_groups`.
  `enums.py`, `configuration.py` (pure §7A.5 ordered classifier over loaded rows →
  `EconomicsStatusEnum` / selection outcome; **also owns `is_applicable(version,
  on_date)` — §7A.3's resolution predicate, registered 2026-08-12 per phase-4
  projection S3**; and `resolve_major_category(snapshot) -> ItemMajorCategoryEnum | None` (4B, ratified 2026-08-12; scope corrected per 4B projection L-8 — the only reader **within the item-economics domain**: no module under `domain/item_economics/` or `services/**/item_economics/` reads `item_major_category_snapshot` except through it (the structural row ships in PHASE 5 with the first production caller — projection r0 L15 corrected the earlier claim that 4B guarded this; 4B forwarded the per-item path; several legacy queries outside the domain read the column and are untouched); unknown strings → None → the `item_missing_major_category` outcome); precedence from an explicit ordered sequence, never enum. **Phase-5 additions (projection r0 L1/L2, registered 2026-08-13):** `resolve_economics_selection(major_category, groups, basis_versions, cost_model_versions, on_date) -> EconomicsSelection` — a frozen dataclass `(status, selected_group, basis_version, cost_model_version)`; `resolve_economics_configuration` is REIMPLEMENTED as `resolve_economics_selection(...).status` so the two can never disagree (the status query's inline `selected_group` re-derivation collapses onto it at its next touch); and `ITEM_READINESS_PRECEDENCE` (explicit ordered sequence: `ITEM_UNVALUED` → `ITEM_MISSING_EXPECTED_PRICE` → `ITEM_MISSING_PURCHASE_COST` → `CURRENCY_MISMATCH` → `NOT_EVALUATED`) with resolver `resolve_item_economics_status(...)` — consumed by phase 5's preview and phase 8's status query; `item_missing_purchase_cost` fires ONLY when the selected model version carries an `item_purchase_cost` term (§11A.4 row 7), so the caller loads the model's non-deleted terms; declaration order carries NO precedence (§6.3), the sequence does. Valuation response envelope: `{"item_valuation": …, "preview": …}` (R13-1: the preview key never merges with committed figures; DELETE returns the status-only preview)
  iteration), `serializers.py` (config-surface serializers — phase 4 — plus manager
  evaluation / status serializers AND the worker status serializer — the worker one
  has **no monetary keys at all**, a separate function, per §11A.3; S8: this module
  is in phase 4's write perimeter).
- **Commands:** `app/beyo_manager/services/commands/item_economics/` with
  `requests/__init__.py`:
  `create_production_cost_group.py`, `update_production_cost_group.py`,
  `delete_production_cost_group.py`, `add_section_to_cost_group.py`,
  `remove_section_from_cost_group.py`, `create_production_cost_basis_version.py`,
  `delete_production_cost_basis_version.py`, `create_cost_model_version.py`,
  `delete_cost_model_version.py`, `set_item_valuation.py`, `delete_item_valuation.py`,
  `commit_item_cost_evaluation.py`, `create_item_cost_projection.py`,
  `delete_item_cost_projection.py`, `promote_item_cost_projection.py`.
- **Queries:** `app/beyo_manager/services/queries/item_economics/`:
  `get_economics_configuration_status.py`, `list_production_cost_groups.py`,
  `list_production_cost_basis_versions.py`, `list_cost_model_versions.py`,
  `get_item_valuation_history.py`, `get_task_budget_status.py` (ADMIN/MANAGER),
  `get_task_budget_status_worker.py` (WORKER/SELLER — separate service, §11A.3),
  `list_task_evaluations.py`, `get_item_lifetime_economics.py`.
- **Worker handler:** `app/beyo_manager/services/tasks/analytics/process_item_cost_result.py`
  (`handle_process_item_cost_result`), registered in
  `beyo_manager/workers/analytics_worker.py` handler map.
- **Task type & routing:** `TaskType.PROCESS_ITEM_COST_RESULT = "process_item_cost_result"`
  (`domain/execution/enums.py`), routed `"queue:analytics"` in
  `services/infra/execution/task_router.py`.
- **Payload:** `domain/execution/payloads/item_cost_result.py` —
  frozen dataclass `ItemCostResultPayload(workspace_id, task_id)` and nothing else
  (§8A.3).
- **Router:** `routers/api_v1/item_economics.py`, blueprint `api_v1_item_economics`,
  path root `/api/v1/item-economics/`. Routes (kebab-case):
  `POST|GET /cost-groups`, `PATCH|DELETE /cost-groups/<client_id>`,
  `POST /cost-groups/<client_id>/sections`,
  `DELETE /cost-groups/<client_id>/sections/<working_section_client_id>`,
  `POST|GET /cost-groups/<client_id>/basis-versions`,
  `DELETE /basis-versions/<client_id>`, `POST|GET /cost-model-versions`,
  `DELETE /cost-model-versions/<client_id>`, `GET /configuration-status`,
  `PUT /items/<item_client_id>/valuation` (set + returns §11A.5 preview),
  `GET /items/<item_client_id>/valuations`, `DELETE /items/<item_client_id>/valuation`,
  `POST /tasks/<task_client_id>/evaluations/commit`,
  `GET /tasks/<task_client_id>/evaluations`,
  `POST /tasks/<task_client_id>/projections`, `DELETE /projections/<client_id>`,
  `POST /projections/<client_id>/promote`,
  `GET /tasks/<task_client_id>/budget-status` (all roles; handler selects the worker
  service for WORKER and SELLER identities, the manager service for ADMIN/MANAGER),
  `GET /items/<item_client_id>/economics` (lifetime read model).
  Role gates: everything ADMIN/MANAGER except budget-status (all roles, role-split
  serialization) per cards 2/4 and §11A.1.
- **Workspace event:** `item_economics:evaluation-committed` (matches
  `task:state-changed` shape; dispatched after the transaction per §7B.1 step 9).
- **Living docs:** `docs/domains/item_economics.md` (phase 9).
- **Config keys / env vars:** none — this domain adds no configuration.
- **Tests:** under `tests/` mirroring existing layout; factories/fixtures added by a
  phase must have a caller in that same phase (charter rule 4).

## 7. Sequencing & gates

Linear chain; phase N starts only when phase N−1 is APPROVED.

1 (redaction — no schema dependency, closes a live exposure first)
→ 2 (schema) → 3 (calculator; imports phase-2 enums)
→ 4 (config services; rate derivation calls the calculator)
→ **4B (category-driven group selection, §7C — round 12: schema delta + classifier
     rework + per-category status; inserted so phases 5/7/8 build against the final
     selection rule)**
→ 5 (valuation; preview needs calculator + the §7C-resolved classifier)
→ 6 (legacy migration; the valuation surface of 5 must exist before item CRUD loses
     money — replacement before removal)
→ 7 (evaluations; needs 3+4+5, runs on final schema after 6)
→ 8 (status & results; needs 7)
→ 9 (docs & drift; documents what shipped).

**§10A.3 sequencing note (planner-owned):** the API-bridge validator ships in
phase 6 and is **kept for at least one release**; its removal (together with the
request-schema keys) is explicitly OUT of this project's scope and is recorded as a
follow-up item for the release after the frontend stops sending the keys. No phase
in this plan deletes it.

## 8. Tool protocols

Archgraph per §3 obligations. Named orientation nodes per phase are listed in each
phase plan.

**D-3: RESOLVED 2026-08-12** — owner-authorized; the node was promoted to
`human_confirmed` with corrected anchors (161–234); audit record
`.archgraph/reviews/2026-08-12T10-23-51-250Z--45ed55.yml`; graph revision now
`810325a0…`, pending 243. Ledger record:
`../archGraph_mapping_mantainance/resolved/node-analytics-recompute-step-time-totals.md`.
Its three outgoing edges still carry the stale 138–211 span and remain pending —
queued for the phase-8/9 delta adjudication.

**Graph-delta adjudication flow (standing owner authorization, 2026-08-12):** for
review items **created or changed by this implementation's phases** (and the three
stale-anchor edges above), the phase reviewer verifies the delta as part of the
phase review, and the **coordinator confirms** (promote/reject via
preview→apply) after the phase is APPROVED — batched per phase, each with its
audit record and a commit. The pre-existing pending backlog (unrelated to this
project) remains owner-adjudicated; sessions still never adjudicate it.
Reporter discipline (learned on D-3): a discrepancy is "filed" only when its file
exists in the maintenance ledger's `open/` — a handoff row alone is not a filing.

## 9. Standing rules

Charter rules 1–11½ imported wholesale. Project-specific additions:

- **P-A (two cost numbers):** `task_steps.total_cost_minor` and any item-economics
  money figure never co-occur in one payload, query projection, or doc sentence
  without the §8A.2 divergence statement. The disjointness test (phase 8) is the
  structural guard.
- **P-B (R-9, no inferred zeros; refined R13-1):** absent input ⇒ named error or
  `null` + status — never 0. Every status payload row for a **non-computable**
  status carries `null` numerics (§11A.4 as refined by §11A.5(b)): inside the
  valuation endpoint's dedicated `preview` key, the computable preview state
  (`not_evaluated`) carries fully computed numerics; everywhere else, and for
  every other status, the null rule stands unmodified.
- **P-C (vocabulary):** "worker-minutes" everywhere; "minutes per worker" is banned
  from schema, API names, payload keys, docs, and test names (R-14).
- **P-D (presentation rule, R4-2):** wherever a percentage term is documented or
  serialized, it is presented as a planning allocation; never as computing legally
  payable tax. Phase 4 (API field docs) and phase 9 (living docs) carry it as
  tasks + criteria.
- **P-E (HC-3):** no phase modifies `step_state_records` writers, the concurrency
  sweep, or `_recompute_step_time_totals` — except the four §8B emission touch
  points, all phase 8: the §8A.5 guarded re-emit line in
  `handle_process_step_transition` (guard: READY ∪ terminal, round 6), one emit hook
  in `maybe_evaluate_task_ready`, one in `maybe_reopen_task_to_working`
  (`services/commands/tasks/_task_state_transitions.py`), and the three terminal
  commands' side-effect lines. Nothing else in the execution path.
- **P-F (calculator monopoly):** every derived economic value is produced by
  `domain/item_economics/calculator.py`; no service computes money/rate/minutes
  arithmetic inline. Snapshots are written only from calculator outputs.
- **P-G (review-r1 lesson 1; extended by re-review r2):** when a criteria table
  carries rows whose expected outcome is identical to a neighbour's (e.g. ADMIN
  mirroring MANAGER), the plan names them **separately required** or collapses
  them explicitly — a row that looks redundant is the row that gets sampled.
  Additionally: (a) such **retention rows get their own named mutation** ("removing
  ADMIN from the allow-list must redden every ADMIN row") so they cannot be
  dismissed as redundant — charter rule 11 applied to retention, not only guards;
  (b) role/audience-parametrized tests **name the audience in the test name**, not
  one example member (opacity about covered roles is what produced S1/N7).
  Implementer prompts restate this where such rows exist.
- **P-I (re-review-r2 lesson 3; extended by phase-3 re-review L6):** a fix cycle
  that adds test rows to satisfy a coverage finding **mutation-tests those rows
  itself** — "do the new rows bite?" never reaches the re-reviewer unanswered —
  and the declaration is **per row, not per test**: when a criterion is extended
  to new functions, each added row's mutation is named and its reddening reported
  individually (one blanket "hostile-context row red" hid an inert row among two
  live ones). Fixtures for extended rows are chosen so the mutation actually
  bites at the fixture's scale.
- **P-G(a) extension (phase-2 review lesson 1):** a named mutation on a **schema
  object** names its site as *the migration or direct DDL on a disposable database*
  — never the ORM model. Tests run against the migrated schema, so a model-side
  DDL mutation is inert and reports a false green.
- **P-J (phase-2 review lesson 2):** a criterion that substitutes a static check
  for a runtime one names the **source the test inspects** (e.g.
  `inspect.getsource(migration.downgrade)`) and carries its own named mutation — a
  static proxy that reads adjacent constants survives the defect it names.
- **P-K (phase-2 review lesson 3):** charter rule 2's sole-predicate companion
  reaches **shared fixture helpers**: any helper a criterion row uses is audited
  for constraints it pre-satisfies or pre-violates (a second sufficient cause in a
  helper poisons every row built on it).
- **P-L (phase-2 review lesson 5; extended by re-review r2 L1):** an implementer's
  declared gap states **what was built** for the criterion, not only what was
  skipped — the coordinator sizes the next cycle from it. Registries list
  **columns/items, never counts**; and a criterion stating a count derives it from
  its own table or omits it (r1 filed a finding on a wrong prose count).
- **P-M (re-review-r2 L2; extended by phase-3 review L2):** criteria for a
  partial-unique index enumerate one accept row per **key column** as well as one
  per predicate clause — the (a) conflict row's fixture must share exactly the key
  columns and differ everywhere else, or the key's width has no live arbiter (B5).
  Companion (L3, extends P-K): when rows hang off a shared factory, each criterion
  cell states **which field of the shared fixture that row varies** — and, for
  guard matrices, **which parameter the row drives** (phase-3 B2: every money row
  happened to drive a user-supplied parameter, leaving half a cell untested while
  the matrix looked complete).
- **P-N (phase-3 review L1):** a criterion proving a **module-wide** construction
  rule enumerates over the module's **public surface**, not over the mechanism
  list that motivated the rule (C9 scoped §6A.2 to Q1–Q5 and was structurally
  blind to two unwrapped functions — B1).
- **P-O (phase-3 review L3):** charter rule 2's no-disjunction clause applies to
  **message-content assertions** too: "asserts both values" means each value
  asserted individually — an `or` between them is satisfiable by half (S1).
- **P-P (phase-3 review L4):** a criterion mandating a comparison names the
  **outcome and its carrier** (error identity or marker) — otherwise the
  implementer authors one and it ships unregistered (S2 →
  `ITEM_COST_SNAPSHOT_MISMATCH`, replaced by `REDERIVE_MISMATCH` per R9-1).
- **P-Q (phase-3 re-review-r3 L7):** a criterion pinning an **implication**
  ("X also implies Y") needs a fixture in which Y would NOT otherwise fire —
  otherwise the row passes for the ordinary reason and the pin has no arbiter
  (S6: the cascade entry appeared from plain disagreement; the pinned clause
  could be deleted green). Rule 2's sole-predicate companion, extended to
  cascade/implication pins.
- **P-I second extension (re-review-r3 L8):** mutation declarations cite the
  **observed failing test node id from the run that produced it** — never a
  prose description of which row "should" redden. A plausible-but-wrong row name
  converts an unguarded clause into an apparently-verified one (S6's declaration
  defect: the cascade inversion actually reddened the plain allowance row).
- **P-R (phase-4 review L1):** a criterion only the ROUTER can satisfy (role
  gates, OpenAPI field docs, route-surface assertions) names its harness in the
  plan (`TestClient` / `app.routes` introspection), the way §10 names the DB
  recipe — otherwise "router-surface assertion" ships satisfiable by inspection
  and the whole route layer has zero arbiters (C9/C11 shipped with none).
- **P-S (phase-4 review L2):** a dual-path identity criterion first establishes
  the DB path is REACHABLE (a concurrent writer can exist) — §6.4 dual-path rows
  carry a reachability judgment; unreachable paths are satisfied by the pre-check
  row + a recorded note, never by an impossible test.
- **P-T (phase-4 review L3+L4, extends P-I/P-Q):** a lock/race criterion names
  the **observable that flips** (e.g. `reference_blocked_while_locked`), not the
  outcome it "should" cause, and names **which counterparty acquires which lock**
  — FK `KEY SHARE` is a counterparty PostgreSQL supplies for free, and it can
  deadlock a naively-worded interleaving (phase-4 C6's original row hung).
- **P-U (phase-4 review L5):** request **canonicalization** and request
  **validation** are separate criteria — R11-1's quantization shipped perfectly
  while every range bound on the same fields 500'd (B2); plans list both.
- **P-V (phase-4 re-review-r2 L1, extends P-L/P-M):** a criterion stating a row
  COUNT names the **table the rows enumerate**, and the implementer's rows map
  back to it one-for-one — "20 rows" was met numerically by duplicating two
  table rows while omitting three; the arithmetic hid the gap for two rounds.
- **P-W (r2 L2, extends P-K/P-M):** a **filter** criterion row (workspace
  scoping, `is_deleted`) names the fixture property that makes the filtered row
  **compete for the asserted slice** — under `limit=1` + an ordering key,
  foreign/deleted rows sort out of view and the row passes with the filter
  deleted.
- **P-T extension (r2 L3):** every wait in a synchronization seam is **bounded**
  — an unbounded `Event.wait()` turns an upstream failure into an infinite hang
  (strictly worse than red) and killed runs leave committed residue.
- **P-I third extension (r2 L4):** a fix ledger sentence recording that a
  mutation reddened only a proxy while the integrated row stayed green is a
  **finding the implementer already found** — fix prompts require it closed in
  the same cycle, never merely reported.
- **P-V extension (phase-4 re-review-r3 L5):** for any enumerate-a-table
  criterion, the parametrize **id names the authority row it discharges**
  (`table-row-5-null-open-…`). Verifying P-V then costs one `--collect-only`
  plus per-row fixture re-derivation instead of a full re-audit — this is the
  standing form.
- **P-I fourth extension (r3 L6):** every enumerated row's mutation is
  **executed**, never reasoned about — the fix-r3 ledger declared four of six
  filter mutations and argued the other two "remain protected by the existing
  arbiter"; both in fact reddened their own new row. A reasoned-not-run entry
  understates the work and forces the reviewer to run it anyway.
- **Rule-11½ record (r3 L7):** a residue check **states its table scope** — an
  economics-scoped "two runs → flat" read as "the suite is clean" while the
  suite at large commits ~116 non-economics workspaces per full run (r3 N11).
- **P-X (4B review L1, P-J applied to a harness):** a criterion that delegates
  model/migration agreement to a harness names **which differences that harness
  can see** — `compare_metadata(compare_type=True)` is blind to partial-index
  predicates, `server_default` expressions and comments (4B S1: deleting AND
  inverting the model predicate both left every row green under the very
  harness L-13 named to protect it); the invisible classes get structural rows.
- **P-Y (4B review L2, extends P-M/P-G):** when a criterion mandates an
  assertion **shape** (exact-dict equality), the implementer prompt restates
  the shape **per row** — C6's preamble said exact-dict, two of four rows
  shipped partial, and the cell that lost its arbiter was the one its row
  existed to pin (4B S2).
- **P-I fifth extension (4B review L3/N1):** a mutation declaration states the
  **full observed red set**, and any divergence from the plan's predicted
  blast radius is flagged as a finding, never narrowed to the predicted subset
  — M2's "1 node" declaration hid that the precedence tuple is positionally
  consumed (7 nodes actually red), which is design information.
- **P-Z (4B review L4, scope exceptions):** a scope exception touching
  **shared machinery** carries, in the same cycle, a before/after property
  test: name the property the machinery had before the change and re-assert it
  after (OD-1's rollback fixed migration persistence and silently broke the
  cold-build cleanup; only a hand-written coordinator probe caught it).
- **P-I sixth extension (phase-5 review L1):** a prompt carrying N named
  mutations gets **N ledger rows** — a missing row is itself the finding, and
  the coordinator's consumption counts them before the review runs (phase 5
  shipped 3 of 10; the seven undeclared rows were exactly where three blockers
  and two should-fixes hid).
- **P-AA (phase-5 review L2, transitive relations):** when a criterion
  enumerates the ways a **transitive** relation can fail (three-way equality),
  it enumerates the **states** (which pair holds equal), never the clauses —
  no fixture can break exactly one pairwise clause, one clause is provably
  redundant, and the implementation carries only the independent clauses.
- **P-Q extension (phase-5 review L3):** a plan's named mutation is checked
  against the implementation it will MEET — L12 named a mutation that is inert
  by construction (the calculator re-derives exactly the persisted value); the
  pin needs a fixture where persisted ≠ derived.
- **P-V second extension (phase-5 review L4):** a monolithic integration test
  cannot discharge an enumerated criterion — the parametrize id IS the mapping
  evidence; folding twelve values into one node is how "the assertion exists"
  and "the assertion can fail" drift apart.
- **P-H (review-r1 lesson 4):** a phase that redacts or reshapes an existing
  payload carries a one-line **structural criterion** for the HTTP boundary — "no
  `response_model` (or equivalent coercion) on the affected routes re-adds the
  field" — because the query-level harness cannot observe it. Applies to phase 8's
  worker status payload.
- **Projection practice (review-r1 lesson 2):** projections enumerating breaking
  tests grep the affected **payload keys** across the test tree, not only callers
  of the changed symbol (D8 missed one of three this way).

## 10. Environment topology (VERIFIED 2026-08-12 in this workspace — update here if reality disagrees)

- **Working directory for all commands:** `backend/app/` (repo-root-relative:
  `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app`).
- **Infra:** `make dev-up` starts postgres + redis in Docker (hybrid mode: app local,
  infra containerized). `make dev-up-full` runs backend + worker containerized.
  Service addresses: PostgreSQL `127.0.0.1:5433`, Redis `127.0.0.1:6380`.
- **Codex sandbox access — RESOLVED by permanent configuration (owner,
  2026-08-12):** the default Codex sandbox originally could not reach
  `127.0.0.1:5433` / `127.0.0.1:6380` (this burned the phase-1 baseline —
  connection-noise failures recorded as a baseline). The owner has since granted
  the access in Codex's own configuration, so **prompts no longer carry an
  elevated-permissions clause**. The environment-agnostic rule stands for every
  agent and session: **a run whose environment cannot reach the database/Redis is
  never recorded as a baseline or as evidence** — the session verifies
  connectivity is real (no connection-refused / `OperationalError` noise in the
  output) and otherwise stops and reports "baseline unobtainable".
- **Tests:** `PYTHONPATH=. pytest -m 'not e2e'` — **`PYTHONPATH=.` is required**;
  bare `make test` (which omits it) fails at conftest import
  (`ModuleNotFoundError: beyo_manager`), verified 2026-08-12. Collection verified:
  `PYTHONPATH=. pytest --collect-only -q` → **1602 tests, 1.72s**. Markers:
  `unit` / `integration` / `e2e` (`pytest.ini`, strict markers, asyncio_mode auto).
  **Verified branch baseline (reviewer r1, healthy containers, elevated
  permissions, 2026-08-12):** pre-phase-1 `545e504` → 1578 passed / **23 failed** /
  1 deselected; phase-1 checkpoint `4416570` → 1600 passed / **23 failed** /
  1 deselected — failure sets byte-identical (zero phase-1 regressions). The 23
  pre-existing failures are enumerated in the phase-1 Review log (S2 correction);
  later phases compare against that list, not the implementer's original
  sandbox-invalidated numbers.
- **Migrations:** `APP_ENV=development alembic upgrade head` (= `make db-migrate`);
  autogenerate via `APP_ENV=development alembic revision --autogenerate -m "<msg>"`
  then hand-fix per `30_migrations` (partial uniques via `postgresql_where`, idiom
  `595e7b840926:44,50`; journaled data-migration exemplar `97b60e06d42a`; both files
  verified present in `migrations/versions/`).
- **Analytics worker launch caveat (VERIFIED):** the analytics worker starts ONLY via
  `make analytics-worker` (`PYTHONPATH=. APP_ENV=development python -m
  beyo_manager.workers.analytics_worker`). It is **absent from the Procfile** (which
  carries web / worker / task-router / delayed- & recurring-scheduler / tasks-worker /
  email-idle-watcher) **and from docker-compose** (services: postgres, redis, backend,
  generic `worker: python worker.py`). Outbox dispatch additionally needs
  `make task-router`. Gotcha: `make worker-logs` tails the *Docker* `worker` service,
  not any Makefile-launched local worker.
- **DB safety:** destructive verification (migration round-trips, downgrade tests)
  on disposable databases only; the configured DB is always left at `head`
  (charter rule 7). `make reset-db` is dry-run by default. Tests that commit rows
  own their teardown (charter rule 11½). Residue checks name the tables they
  scanned (§9 rule-11½ record): the wider suite is KNOWN to commit non-economics
  residue per full run (~116 `shift-hook-*`/`Workspace <hex>` workspaces, +101
  users, +19 tasks, +20 working sections — phase-4 r3 N11, maintenance prompt
  filed 2026-08-13).
- **Disposable-database recipe (projection D4, verified mechanics 2026-08-12):**
  the suite and alembic both resolve `settings.database_url`, and a real
  `DATABASE_URL` env var **overrides `.env`** (pydantic-settings precedence;
  `config.py` alias `DATABASE_URL`). So, from `backend/app/`:
  1. `DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager_disposable PYTHONPATH=. APP_ENV=development python3 -m scripts.create_db`
  2. same `DATABASE_URL=…` prefix on `alembic upgrade head` / `alembic downgrade <rev>` for the round-trip;
  3. drop afterwards: `docker compose exec postgres psql -U postgres -c 'DROP DATABASE beyo_manager_disposable;'`.
  **Without the `DATABASE_URL` override, every pytest/alembic command targets the
  configured development database** (`.env` → `beyo_manager` @ 5433) — there is no
  built-in test-schema creation anywhere in `tests/` (no `create_all`, no alembic
  hook). Plans must say per criterion which database it runs against.
  **From-scratch recipe (CORRECTED 2026-08-13, 4B review r1 B1):** create the
  named disposable database with `PYTHONPATH=. APP_ENV=development DATABASE_URL=…
  python3 -m scripts.create_db`, run the same `DATABASE_URL=…` prefix on
  `PYTHONPATH=. APP_ENV=development alembic upgrade head`, then drop the database
  with `docker compose exec -T postgres dropdb -U postgres --if-exists <name>`.
  The owner-authorized metadata correction in `8cf57fa23110` makes the on-disk
  revision graph acyclic; `env.py` contains no private-Alembic graph repair. During
  a genuinely cold build it creates a transient migration workspace solely for the
  historical pause-reason migrations, then deletes that workspace and its
  anchor-owned rows before the command returns. **History note:** the maintenance
  r2 paragraph previously here claimed "verified twice … empty database to
  `90cdd23a828e` in 2s, zero workspaces/pause reasons/shim rows". The 4B review
  proved that claim was never true as stated: until 4B's `env.py` rollback,
  the cold-build preflight's implicit transaction made Alembic treat the
  connection as externally owned, so those runs exited 0 while **persisting
  nothing** (the "zero rows" observations were of an effectively empty
  database; warm upgrades on the configured DB persisted only because two
  historical `CONCURRENTLY` migrations issue raw `op.execute("COMMIT")`).
  Environment facts recorded from a command's exit code need a **state
  assertion** behind them (4B review L5). The 4B fix cycle re-verifies the
  recipe end-state (head + zero residue) and updates this entry with the
  verified facts. Fix-r1's timed cold build on disposable database
  `beyo_manager_4b_fix_r1_verified` took 1.70s and ended at
  `5caae620088c`; state queries returned zero `workspaces` rows for
  `mig_cold_build_workspace`, zero `pause_reasons` rows owned by it, and zero
  `mig_cold_build_workspace` rows. The database was dropped after verification.
  Known open defect for the migration-infrastructure owner:
  a cold build targeting a revision below the pause-reason migrations crashes
  in cleanup (`UndefinedTableError: pause_reasons` — 4B review N6).
- **Error surface:** `run_service` (`services/run_service.py`) is the single error
  boundary; DomainError → `StatusOutcome(success=False, error=exc)`; identities per
  §6.4 travel in `error.message`.

## 11. Only-if-cheap ledger (coordinator picks up at prompt time; never blocks a gate)

Per intention §13: embedded budget block in step/task payloads (minutes/percent only,
every role); operational CLI re-emit of `PROCESS_ITEM_COST_RESULT`
(`53_operational_cli` pattern — a convenience, NOT the repair path, R4-1);
evaluation `note` field; projection comparison endpoint.
