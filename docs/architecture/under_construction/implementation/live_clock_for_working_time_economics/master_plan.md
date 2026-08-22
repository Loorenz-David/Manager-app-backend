# Master plan — live_clock_for_working_time_economics

```
state: IN PROGRESS. Gate PASSED; phase 1 APPROVED (`d21fe9e`); **phase 2 APPROVED**
       (`efd6b99`, 2026-08-21, six rounds); **phase 3 APPROVED** (2026-08-21, three
       rounds, gate measurement `26 / 2515 / 1` at `808eead`); phase 4 **BLOCKED**.
       **0 owner cards open** (OD-10 ratified 2026-08-21).
       **Next is NOT a phase-4 prompt.** Phase 4 is gated (§6 ⛔) behind the
       test-environment work: build a correctly migrated test database, then
       `pytest-xdist` with per-worker isolation, then **re-enumerate the failure-ID
       baseline under the new runner**. Phase 4 compiles only after that.
       Test-evidence policy (charter, 2026-08-21) is live; phase 3 was its pilot and
       spent **zero L4 runs** in its final round.
       **Environment: the graph is NOT clean** (9 pending / 2 stale **plus stream 3's
       uncommitted node** — re-measure, never cite); **the suite runs on the DEVELOPMENT
       database** (§6); **recognized stream 3 is uncommitted and live** — attribute any
       count movement to it before concluding.
       §3's tracker is the authority on state — this line is a convenience and is
       refreshed at every gate.
date: 2026-08-20 (header refreshed after phase 1 approval)
coordinator: Claude Fable 5 (incoming 2026-08-20, per ORIENTATION_for_new_coordinator_20260820.md
             — that document is SUPERSEDED as an instruction set; see its banner)
```

## 1. Mission

Make the worked-seconds basis **live**: settled work plus the concurrency-averaged share
of any currently-open `working` interval, evaluated at request time, computed by **one**
backend function and consumed by every present-tense surface — the production-time
widget (E-P), both faces of budget-status (E-B), and the worker step cards
(E-A budget-allocations) — so `share_state`, `worked_seconds` and `left_seconds` stop
disagreeing on the same card. Nothing live is ever persisted; no shape, route, field,
role gate or socket event changes. The whole pipeline is a behaviour change behind
existing contracts.

Authorities: `planning/intention.md` (**RESOLVED and PLAN-READY**, rounds 4a–4g,
2026-08-21 — the gate passed and its folds are in; **4g is the latest fold** and 4d
supersedes 4c on HC-3A's failure site), `planning/owner_decisions.md`
(D1–D9, ledger empty). Provenance: `planning/coordinator_review_of_intention_20260819.md`
(all six findings folded round 3, verified against code by the outgoing coordinator),
`ORIENTATION_for_new_coordinator_20260820.md`.

## 2. Folder layout

Charter tables: `planning/` (intention, owner decisions, review provenance), `plans/`,
`prompts/<role>/`, `handoffs/<role>/`, `archive/plan_<n>/`. State is positional — a
consumed row never sits in a live table; closed rows move to `archive/` and their own
`state:` line is corrected at closeout.

The `archive/gate_inventory/` partition precedent from `simple_valuation_editor` §2 is
adopted: the mechanism-inventory gate predates phases, so its spent prompt, consumed
handoff and calibration seal archive under `archive/gate_inventory/` when the gate
closes. Historical path references are never rewritten; after closeout they resolve
under the archive partition by convention.

`prompts/coordinator/` holds standing coordinator documents (including the sealed
calibration file) — never handed to a session.

## 3. Phase registry & tracker

Newest state first; superseded rows kept as provenance.

| Phase | Scope | State | Date | Actor | Note |
|---|---|---|---|---|---|
| 3 | D9: the frozen blocks freeze whole — both feed sites (N-4), T13's two rows, re-commit immunity, **OD-10's boundary** | **APPROVED** | 2026-08-21 | Codex (r1, fix r2) + Opus 5 (projection r0, review r1, re-review r3) + coordinator | **Three rounds; 0 blocking outstanding; 9 phase rows; gate measurement 26 / 2515 / 1 at `808eead` (dirty — stream 3), failing-ID set `comm`-diffed empty BOTH directions against §6's 26.** Ships the frozen percent at both feed sites: `calculate_percent_consumed(actual + variance, actual)` inside the existing `result is not None` branch, reciprocal site comments, the falsified docstring corrected, and the two internal `docs/domains/` numerics lines split into live-vs-frozen. **The production code was correct at implement r1 and never changed again** — `git diff 5b8329b HEAD -- app/beyo_manager/` is empty across both later rounds. **Every blocking-or-should-fix finding in all three rounds was in a plan, a criterion, an intention section or a coordinator note; none in the code** — now the third consecutive phase for which that holds. Findings by author: **S1** (the coordinator's inverted C6 attribution, in three documents — C6b measurably *passed* under the edit it was documented as stopping); **S2** (the over-budget region guarded by nothing in the repository, ∅/∅ at L4 under a clamp-at-100 mutant → **C6c**, `"150.00"` on both faces); **N7/N8/N9** (all three coordinator artifacts: a correction whose premise its own order invalidated; an unmeasured justifying number, `120.00` where `170.00` is measured; a stream perimeter that under-declared tool-recorded state and went stale twice in a day). **Eleventh instance of the row-that-cannot-fail class and a fifth shape — degenerate output range**; §5B now binds criteria to enumerate the regions their authority names, and P2 closed that enumeration (three OD-10 regions + the `100.00` boundary pinned four times + the `≤ 0` inequality pinned at exactly zero by probe C). **The evidence policy's clearest round yet:** re-review r3 spent **zero L4 runs**, five probes, ~25 s of pytest, and produced a new structural fact (C6b and C6c partition the negative-variance space; neither covers the other). The coordinator cited two stamps by cryptographic tree identity rather than re-running them, and dated a foreign stream against a measurement by digest. **Four rules earned into §5** (shelf-life of enumerated sets and corrections; a justifying number is a claim; perimeters cover tool-recorded state; per-file digests beat an aggregate while a foreign stream is live). Checkpoints `5b8329b` → `874f02d`. Baseline published per obligation 7 with **database and dirty-tree identity**, a schema amendment this phase earned. **Carried, non-blocking:** the archgraph backlog (9 pending / 2 stale **plus stream 3's uncommitted node/edge** — re-measure at phase 4, never cite) and r1's N6 → owner adjudication at `plans/plan_4.md` C6; the `percent < 0` unreachability basis (writer, not guard) → plan 4 notes. **Phase 4 remains BLOCKED** on the ⛔ test-environment gate. |
| 3 | D9 + OD-10's boundary | **APPROVED** (re-review r3) | 2026-08-21 | Opus 5 (re-review r3) | **0 blocking, 0 should-fix, 3 notes — all documentation drift in coordination artifacts, none in code or criteria.** Handoff `handoffs/reviewer/2026-08-21_phase3_rereview_r3_handoff.md`. Tree `808eead` (four coordinator doc commits above the checkpoint; `git diff 874f02d HEAD -- app/` **empty**, so the gate's substance holds and the prompt's SHA was stale), dirty via the shopify stream, `app/` diff digest `f0722645…` identical across every probe and measurement — then moved to `020e77c9…` after the last revert because the stream modified a further file mid-round (N9), with **no phase-3 file moving**, proven per-file (`d9160f92…` / `65558c51…` / `16cb98a9…` / `90da6486…`); `division_serializers.py`'s digest also corroborates the coordinator's C5-probe revert from a second session. **Lesson: while an uncommitted foreign stream is live, per-file digests over the reviewed perimeter are the revert instrument; an aggregate `app/` digest conflates a leaked probe with the owner saving a file.** **Zero L4 runs** — every hypothesis was a named-row bite, so all six evidence rows are L1 over the two phase files, which kept the foreign stream's +17 tests out of every measurement (~25 s of pytest for five new mutant shapes). **S1 closed on the merits:** C6b's `null` has exactly one sufficient cause — `status == "ok"` on both faces closes the status channel, `result is not None` the absent-result channel, a fallback denominator yields a number, and the row bites on the **exact zero** boundary (probe: weaken `calculate_percent_consumed` to `allowed < 0` ⇒ C6b red on the frozen side, C6a on the live side). **S2 closed, and C6c is non-redundant:** a **variance-sign blanking** implementation (no ledger had run it) leaves **C6c alone red, 1 failed / 34 passed, C6b green** — C6b and C6c partition the negative-variance space at the zero-allowance boundary and neither covers the other's half. **N-4's argument order is now mutation-guarded, not merely read-correct:** argument transposition reddens C3/C6a/C6b/C6c/`test_c17` at E-P (5f/30p) and C3/C6a/C6b/C6c at E-B (4f/31p), reproducing the recorded C5 site asymmetry independently. **§5B's region corollary closes:** all three OD-10 regions carry an exact literal, the `100.00` boundary is pinned four times, and `percent < 0` is **unreachable by construction** (`calculate_actual_worker_minutes` over a non-negative seconds count, single writer). **No blast radius** from the fix cycle; 35 passed / 1 deselected over both phase files. **Notes:** N7 — intention §5.3A's S1 correction still asserts C6b's old `allowed = 0.00` premise, which fix r2 deleted; conclusion survives for the opposite reason, but a reader reconciling document to tree could "restore" the `0.00` and undo S1. N8 — **the "non-vacuous against a live **`170.00`** (measured at re-review r3; C6c serves at `now`, the **open** state — `120.00` is the pre-open value C6c never serves, and was the coordinator's unmeasured figure, N8)" figure in this table's prior row and in `plans/plan_3.md` §7 is wrong; measured `170.00`** (C6c serves at `now`, the open state); non-vacuity unaffected. N9 — **the shopify stream moved twice during this round and §7's perimeter covers neither move:** `.archgraph/architecture.yml` gained an uncommitted delta at 10:16:07 (1 node + 1 edge, `ai_inferred`), and ~1 h later the **tracked, existing** `app/tests/unit/services/infra/shopify/test_product_sync_client.py` was modified. Widen §7's stream-3 perimeter to `.archgraph/architecture.yml`, `.archgraph/.internal/` and `app/tests/unit/services/infra/shopify/`; re-measure the graph at phase 4 rather than citing §6's 9/2; and **narrow §7's "additions that pass do not touch the failing-ID set"** — true of the stream's untracked new file, false of an edit to an existing test file, and the enumerated 26 already carries a shopify row with a shopify flake beside it. **P5 answered, no owner card:** a dev-database baseline **is** acceptable evidence here — §6's ⛔ GATE step 1 already binds phase 3 to the serial runner, the dev DB is at head while `app_test` lacks `cost_model_versions`/`item_cost_results` outright, and the phase rests on DB-independent mutation bites. One correction owed: §7's published-baselines table records neither database nor dirty-tree digest — the gate publishes failure-ID set + tree identity + **database identity**, count subordinate. Probes: five across four files, all reverted byte-identical; no schema change, no committed rows, no archgraph call. |
| 3 | D9 + OD-10's boundary | **REVIEWING** (re-review r3) | 2026-08-21 | Codex (fix r2) + coordinator (consumption) | **Fix r2 consumed — both should-fix closed, verified at source. Suite 26 / 2487 / 1 (+1), cited not re-run.** Digest `b50bda39…` reproduces exactly as `git diff ac953a0 874f02d -- app/`; perimeter exactly five files, **nothing under `app/beyo_manager/`** across the whole cycle. **S1 closed:** C6b re-specified to frozen `15.00 / −15.00` against a **positive** current allowance, `status == "ok"` asserted on both faces, comment rewritten to claim only what the fixture shows — the `null` now has one sufficient cause. **S2 closed:** C6c asserts `"150.00"` on both faces (frozen `15.00 / −5.00` → allowance `10.00`), non-vacuous against a live **`170.00`** (measured at re-review r3; C6c serves at `now`, the **open** state — `120.00` is the pre-open value C6c never serves, and was the coordinator's unmeasured figure, N8). N1, N4 present. The implementer corrected the coordinator's `+2` forecast to the true `+1`. **Coordinator finding against the coordinator's own correction:** yesterday's C5 expected-bite-set class 2 ("C3, C6a, C6b") went **stale one round after it was written** — measured, the C5 mutant now also reddens **C6c** (5 failed / 31 passed, probe reverted byte-identical). Left alone it would have turned the next round's correct result into a false finding, the exact failure the list prevents. Standing rule added: **an enumerated expected set is a claim with a shelf life — a row that asserts the same mechanism joins the class in the cycle that adds it.** **Environment established and folded to §6:** every baseline in this pipeline — including phase 2's published one — was measured against the **development** database (`…:5433/beyo_manager`), while `.env.testing` designates `…:5432/app_test`, stamped `67cfba8fcb2d` with 96 tables and **missing `cost_model_versions` and `item_cost_results`**. That is the starting input for the per-worker-DB work gating phase 4: build a migrated test database and re-enumerate the baseline there **before** adding workers. **Round spent rather than skipped, reason recorded:** C6c and the re-specified C6b guard a money-adjacent number and have had one author and one reader — the coordinator who wrote their criterion. Re-review r3 prompt `prompts/reviewer/2026-08-21_phase3_rereview_r3.md`, delta-scoped; P5 asks whether a dev-database baseline is acceptable evidence to approve on. |
| 3 | D9 + OD-10's boundary | **IMPLEMENTED** (fix r2) | 2026-08-21 | Codex | 26 failed / 2487 passed / 1 deselected / 2 warnings; baseline failure IDs ∅ added / ∅ removed. C6b re-specified with positive current allowance; C6c exact frozen `150.00`; N1/N4 closed. Handoff: `handoffs/implementer/2026-08-21_phase3_fix_r2_handoff.md`. |
| 3 | *(prior row — fix r2 dispatched)* | *superseded (PROMPT_READY, fix r2)* | 2026-08-21 | Opus 5 (review r1) + coordinator (fold) | See current row above; fix prompt `prompts/implementer/2026-08-21_phase3_fix_r2.md`. |
| 3 | D9: the two frozen-percent feed sites (N-4) + T13 both rows, re-commit immunity, **OD-10's boundary** | **CHANGES_REQUESTED** (review r1) | 2026-08-21 | Opus 5 (review r1) | **0 blocking, 2 should-fix, 6 notes — the production code is correct and no production line is in scope for the fix cycle.** Handoff `handoffs/reviewer/2026-08-21_phase3_review_r1_handoff.md`. Tree `184f48a`; `git diff 5b8329b HEAD -- app/ docs/domains/` empty, so the L4 stamp was **cited, not reproduced** — the first review round in this project to spend its whole budget on variation. Two mutant shapes no ledger had run. **S1: intention §5.3A names the wrong guard.** It says C6 row (b) reddens on a "blank whenever `status == infeasible`" edit; row (b)'s own fixture sets the current allowance to `0.00`, so its status *is* `infeasible` and the blanking edit produces exactly the `null` it asserts. Measured at L1 with the mutant at **both** sites: 1 failed / 24 passed, the single red is **C6a**, C6b green. The implementer's ledger already held the disproof (one ID where the prose implies two) and was read only in the "did C6a bite?" direction. Same inversion in `plans/plan_3.md` §5 C6 and in this table's PROMPT_READY row. **S2: the frozen percent's over-budget region has no guard anywhere in the repository.** Every numeric frozen literal in the phase is ≤ 100 (`100.00` ×4, `80.00`, `15.00`, goldens `15.00`, `test_c17` `20.00`), and C6b — the only negative-variance row — is placed exactly where the reconstructed allowance is `0.00` and the answer is `null`, so `variance < 0` *with a positive allowance* (OD-10's own first table row: a job that overran) is never evaluated. Clamp-at-100 mutant at both sites, **L4** as an absence claim: `26 / 2486 / 1`, ID set `comm`-diffed against §6's 26 → **∅ added, ∅ removed**; focused surface 100 passed. **§5B's degeneracy is one worse than recorded** — `variance = 0.00` also lands the frozen percent on exactly `100.00`, the boundary of the whole mutant family. Fix scope: new row **C6c** (`actual 15.00 / variance −5.00` ⇒ `"150.00"`, current allowance positive), the three attribution swaps, plus notes N1/N4. Notes: C4b-inside-`test_c1` judged **sufficient** (each mutation trips its own literal); C3 shows the live percent landing not moving; T13's E-B block byte-identity is proven only on the percent key; `test_c17`'s record is durable but sits where its readers will not look. Verified correct: N-4's argument order, the `result is not None` guard complete via `_empty_status`, HC-4, C4a structural, the P7 absence claim at L4 (two producers, both changed), and the P5 doc sweep (both corrections true; `api.md` and the 2026-08-18 handoff sit at the no-drift point and stay valid). Probes reverted, SHA-256 byte-identical, tree clean, no archgraph call. |
| 3 | *(prior row — review r1 dispatched)* | *superseded (REVIEWING)* | 2026-08-21 | Codex (implement r1) + coordinator (consumption) | **Implement r1 consumed; checkpoint `5b8329b`. Suite 26 / 2486 / 1 (+7), baseline IDs unchanged — cited, not re-run.** First consumption under the new evidence policy to **verify a stamp cryptographically instead of reproducing it**: the declared dirty-tree digest `d2ca0320…` reproduces exactly as the `app/` + `docs/domains/` diff `88c8f5f..5b8329b`, proving the shipped content is byte-identical to what was measured. Perimeter exact (10 declared = 10 in the commit); the archgraph revision `120c4c38…` is byte-identical to the coordinator's pre-session reading, proving the "no graph writes" claim; ruff clean on the five changed files with the repo-wide 136 unchanged from the parent. Ledger arithmetic reconciles on every row (all three L4 runs total 2512 collected), and **the C5 site asymmetry is self-authenticating** — E-P reddens `test_c17` while E-B does not, and neither reddens C1/C2, which is exactly what the `variance = 0.00` fixture forces. Criteria checked at **assertion level, not by ID**: C4b sits inside `test_c1` but carries its own exact literals, so each mutation trips its own assertion; C6a and C6b are jointly complete (C6a kills status-based blanking, C6b kills a positive fallback, neither fixture satisfies the other's predicate); C3 escapes §5B's degeneracy via `variance = 5.00`. Doc corrections read as claims and verified against §5.3A. **Coordinator class sweep beyond the handoff:** `test_c17` is the only test in the repository of its shape, so the recorded-not-retargeted disposition covers the whole class. Review prompt `prompts/reviewer/2026-08-21_phase3_review_r1.md` — seven probes, settled ground marked do-not-re-spend. |
| 3 | *(prior row — implement r1 dispatched)* | *superseded (IMPLEMENTED)* | 2026-08-21 | Codex (implement r1) | Implemented at checkpoint pending commit: two serializer feed sites, C1–C6 rows, Decimal fixture corrections, and internal numerics-doc corrections. Focused surface 90 passed; final L4 stamp 26 failed / 2486 passed / 1 deselected / 2 warnings, with the published 26-ID baseline unchanged. Named mutations were run at every required site and reverted; C5 per-site unions were the two legacy IDs plus C3/C6a/C6b. Handoff: `handoffs/implementer/2026-08-21_phase3_implement_r1_handoff.md`. |
| — | Implementation planning | **DONE** | 2026-08-20 | coordinator | Four phases, split so no payload changes before its guards exist: goldens + clock boundary + loader (1) → the three surfaces (2) → D9 frozen blocks (3, needs the live basis for T13 to discriminate) → closeout handoff + graph delta (4, docs only). Strictly sequential 1→2→3→4 — plans 2 and 3 share files, and the valuation pipeline's parallel doc phase collided on a tripwire despite disjoint perimeters. The four pre-registered decisions resolved as **N-1…N-4** (§4), each grounded in source read this session (`run_service` is a pure error boundary over an already-built ctx, so the boundary is ctx construction; `ItemCostResult` stores `actual_worker_minutes` + `variance_worker_minutes`, which reconstructs the frozen denominator without touching the current evaluation). D5 satisfied: no release before plan 3 approves, all four §4.1 rows ship together. |
| 1 | Pre-change T5 goldens; `ServiceContext.now` (N-1); the loader `load_live_worked_seconds` (N-3) + its contract proven at loader level (T2/T3/T4/T10, window anchor, HC-1A) | **APPROVED** | 2026-08-20 | Codex (r1, r2, r3, r5) + Opus 5 (review r1, re-review r4) + coordinator | **Six rounds; 0 blocking outstanding; 23 tests; suite 26 / 2459 / 1.** Ships: the three pre-change goldens (captured at `1081a2b`, before any code — proven from that checkpoint's own content), `ServiceContext.now` (N-1), and `load_live_worked_seconds` (N-3) with C1–C12 all proven at loader level. **The production loader was correct at its first attempt and never changed except one message string at r5** — every round since `a7659bc` was about whether the tests prove what they claim, which is the cheap direction for that error to run. Findings by author: **every blocking finding in this phase was in a coordinator or reviewer artifact, none in the implementer's code** (B1/B2: criteria that pinned their fixtures at addition's identity element and used `==` to test a type; F-C1: a criterion promising locus discrimination whose fixture sat where both loci coincide; B1-r4: the coordinator's own round-4c correction naming an unprobed failure site). Coordinator verified every round independently rather than reading ledgers: 14 whole-suite runs, every named mutation re-applied at its site with ID-set diffs in both directions, reverts hash-verified. **The decisive closure is measured**: with the guard deleted the C9 row now reddens at `+02:00` **and** under `TZ=UTC`, where pre-fix it passed under UTC. No r6 spent — reason recorded in `plans/plan_1.md` §7 (r4 swept the docstring class; r5 replaced two members; the coordinator, who authored neither, verified both claims empirically; the C12 arithmetic lines are byte-identical in the diff). Checkpoints `1081a2b` → `a7659bc` → `a4f5b97` → `bc309e2` → `4cf6f4b`. Nine rules earned into §5, two environment facts into §6. **Carried, non-blocking:** 3 pending `ai_inferred` graph items + r1's N6 → owner adjudication, tracked at `plans/plan_4.md` C6. |
| 1 | *(prior row — fix r5 dispatched)* | *superseded (PROMPT_READY, fix r5)* | 2026-08-20 | Opus 5 (re-review r4) + coordinator (fold) | **CHANGES_REQUESTED: 1 blocking, 0 should-fix, 4 notes — r2/r3 confirmed correct in full; the blocking finding is in the coordinator's own round-4c correction.** Perimeter verified (reviewer wrote one file; loader hash unchanged; its three mutations reproduce r3's ledger with zero removals). **B1-r4, coordinator-verified and upgraded from derived to measured:** the guard raises CPython's byte-identical message one frame above `concurrency.py:_sweep`, so `pytest.raises(TypeError)` cannot tell them apart — delete the guard and the C9 row **fails at the host's `+02:00` but passes under `TZ=UTC`**. The phase's only safety test discriminated by accident of the host offset, and on an ordinary UTC CI box the guard could have been deleted with nothing red. r4's counter-measurement (same code, naive `now` an hour later ⇒ the sweep *does* raise) independently falsifies round 4c. **Sixth instance of the class-inside-its-own-correction shape, and the first authored by the coordinator.** Folded: intention **round 4d** (HC-3A's third and measured failure-site statement + the guard-distinguishability obligation); §5 **+4 rules** (both-direction site probes · a guard must not imitate its own failure · host-dependent observations are environment facts · capture the ID set *before* repeating); §6 **+2 environment facts** (a third intermittent test — identity permanently unrecoverable because a repeat was performed against a bare count; `TZ` matters here). N2-r4 recorded as a structural fact in plan 1 §6 (the `+=` form is untestable by construction — no row owed). Fix prompt `prompts/implementer/2026-08-20_phase1_fix_r5.md`: B1-r4 + N1-r4 + N4-r4, **one production line in scope** (the guard's message — coordinator's choice between r4's two options, reasoned in the prompt), ledger must prove host-independence under two `TZ` settings plus re-confirm C12's three mutations. |
| 1 | *(prior row — re-review r4 dispatched)* | *superseded (REVIEWING)* | 2026-08-20 | Codex (fix r3) + coordinator (consumption) | **F-C1 closed on one row, exactly as specified.** Perimeter three files; **zero production lines across both fix cycles** — the loader is unchanged since `a7659bc`, so every round since has been about whether the tests prove what they claim. Suite **26 / 2459 / 1**. Coordinator re-applied both isolating mutations whole-suite: **M-locus ⇒ exactly the locus row, M-mode ⇒ exactly the mode row, neither removing an ID** — the three C12 rows (type · mode at 61 s/settled 0 · locus at 63 s/settled 1) are measurably orthogonal, and the locus row is mode-neutral *by construction* because `round(31.5)` and `floor(31.5+0.5)` agree. Reverts hash-verified. The implementer hit §6's baseline flake on their first M-locus run (26 failed **with** the new ID = a vanished baseline ID) and applied the repeat rule correctly — identifying that ID is probe P5 of r4, since a **third** flaky test would be a new §6 environment fact. Checkpoint `bc309e2`. Re-review prompt at `prompts/reviewer/2026-08-20_phase1_rereview_r4.md` — delta-scoped, perimeter check as step 1, r1's settled list marked do-not-re-spend. r1's carry-forwards: **N2 folded** (intention round 4c); **N6 routed to `plans/plan_4.md` C6** for owner adjudication (an archgraph evidence summary is immutable through review *and* maintenance, so closing it means reject-and-re-record — never unilateral). |
| 1 | *(prior row — fix r3 dispatched)* | *superseded (PROMPT_READY, fix r3)* | 2026-08-20 | Codex (fix r2) + coordinator (consumption) | **Fix r2 applied correctly and completely — B1, B2, S1, S2, N1, N3, N7 all closed.** Perimeter exactly the declared three files; **zero production lines changed** (`git diff ae7d723..HEAD -- app/beyo_manager/` empty, loader hash unchanged) — the code was right, the proof was not. Suite **26 / 2458 / 1** (+4). Coordinator re-applied all four named mutations whole-suite: every observed-red set matches the ledger **ID-for-ID**, including the half-up row's claim that the type row stays green; reverts hash-verified. Checkpoint `a4f5b97`. **One new coordinator finding, against the coordinator's own criterion (F-C1):** C12 promised locus discrimination and delivered mode + type — its fixture sat at `settled = 0`, where both loci coincide, so the sum-locus mutation left the **whole suite green (∅)**. §3.1A A's locus term — the one whose stated purpose is to keep §4.1's two-resolutions claim true, and thereby keep N-2's choice safe — had no test that could fail. B1/B2's class **inside the correction of its own class**, the fifth such instance here. C12 amended to three isolating rows (type / mode at 61 s · settled 0 / locus at 63 s · settled 1, mode-neutral by construction); rule earned in §5. Fix prompt `prompts/implementer/2026-08-20_phase1_fix_r3.md` — **one row**, one new mutation plus two confirmations. |
| 1 | *(prior row — fix r2 dispatched)* | *superseded (CHANGES_REQUESTED, r1)* | 2026-08-20 | Opus 5 (review r1) + coordinator (fold) | **CHANGES_REQUESTED: 2 blocking, 2 should-fix, 7 notes — and the code is correct; every finding is about the proof.** B1/B2: the loader's two defining terms (`settled +`, `int(round)`) survive their own deletion with **∅** added failures — all 17 fixtures sit at `settled = 0`, addition's identity element, and `1800.0 == 1800` hides the type. **Coordinator re-applied all three decisive mutations whole-suite before folding: B1 ∅, B2 ∅, guard-deletion exactly 1 ID — reviewer's measurements reproduced exactly, reverts hash-verified.** S1 resolved P1 *against the intention*: on this driver a naive bind never reaches the sweep (0 rows, no error), so HC-3A's named failure site could not fire and the implementer's unplanned guard is the only loud path — absorbed as contract (intention round 4c), not merely tolerated. Folds applied: intention round 4c (HC-3A fails-closed + §3.1 attribution in settlement's `or` form per N2); master plan §5 +5 earned rules (identity-element, isinstance, failure-site-claims-inherit-the-mutation-rule, delegation-medium, multi-use-mutation-shape); plan 1 C9 reworded, **C11/C12 added**. N6 (graph summary count) queued for owner adjudication with the 3 pending items; N2/N6 carry to phase 4 if still open at approval. Fix prompt at `prompts/implementer/2026-08-20_phase1_fix_r2.md` — one-file test-only perimeter, correction clauses verbatim, four ledger re-measurements owed (C11, C12 ×2, C9 under the renamed test). Review perimeter: exactly its one handoff file ✓. |
| 1 | *(prior row — review r1 dispatched)* | *superseded (REVIEWING)* | 2026-08-20 | Codex (implement r1) + coordinator (consumption) | Implemented at checkpoints `1081a2b` (goldens ONLY — sequencing proven from the checkpoint's own content) and `a7659bc`; handoff committed `ecd24e8`. 18 tests, suite **26 / 2454 / 1**. Coordinator verified at consumption rather than reading the ledger: perimeter = declared 10 items exactly; clean suite re-run with failure IDs byte-identical to §6's set; **all three named mutations re-applied whole-suite, reverted, hash `6d11b922…fa82ca`** — mutations 1 and 2 match the ledger ID-for-ID (8 and 1); **mutation 3 needed a second shape to reconcile**: sweep-timestamp-only adds 11 IDs, both-args (window-end + sweep timestamp) adds the ledger's exact 12 — the observation was true, the site description under-stated the mutant's reach; recorded in plan 1 §7 with the rule-11 extension (state which *uses* a multi-use argument's mutation covers). Delegations D1–D3 taken and recorded. One unplanned semantic addition found (the naive-`now` boundary guard) → review probe P1 with a fold-back recommendation obligation. Review prompt at `prompts/reviewer/2026-08-20_phase1_review_r1.md` (P1–P7; the three named mutations marked do-not-re-spend). Graph: 3 pending `ai_inferred` items created by the delta — owner adjudication queued, does not block the review. |
| 1 | *(prior row — implement prompt compiled)* | *superseded* | 2026-08-20 | coordinator | Implement prompt at `prompts/implementer/2026-08-20_phase1_implement_r1.md` — goldens-first sequencing as a hard constraint, delegations D1–D3 carried, mutation-ledger obligations inline, baseline 26/2436/1 + ID set referenced. |
| 1 | *(prior row — projection folded)* | *superseded (PROJECTED)* | 2026-08-20 | Fable 5 (projection r0) + coordinator (fold) | Verdict `AMENDMENTS_REQUIRED`, 0 owner cards, 12 ledger rows — **all routed before the implement prompt**: 8 plan amendments applied verbatim into `plans/plan_1.md` (headline: the E-A golden must be one single-task call per task — its task `SELECT` has no `ORDER BY`, so a batched byte-golden is order-luck; C10's expire-then-dirty order passed under the exact HC-1A assignment it guards; T2's "production transition path" pinned to `_step_transition_core.py:_apply_step_transition(now=t)` since `transition_step_state` stamps its own clock; C7's anchor mutation needs >1-day separation or the buffer swallows it), 3 written delegations (plan 1 §6), 1 upstream (L3: the typicals cutoff wall-clock read §2.3A missed — intention round 4b + plan 2 C11 + the §6 fact correction here). Coordinator verified L3/L5/L4 at source before applying; the citation fix was class-swept (3 sites, projection saw 1). Baseline re-measured at `2711b58` (A4): **26 / 2436 / 1**, ID set enumerated in §6; count matches history, no repeat owed. Projection perimeter: exactly its one handoff file ✓. Next: implement prompt. |
| 1 | *(prior row — projection prompt compiled)* | *superseded* | 2026-08-20 | coordinator | Prompt at `prompts/reviewer/2026-08-20_phase1_projection_r0.md` — fresh-session inputs only, depth on the loader arithmetic / T2 ledger / golden determinism / clock boundary. |
| 2 | The three surfaces live: the fold (N-2), E-P one-map composition, E-A batch + `today_utc()`→`ctx.now.date()`, the typicals `now` shim **+ the config-date shim (round 4e)**; C1–C12 | **APPROVED** | 2026-08-21 | Codex (r1, r2, r4, r6) + Opus 5 (review r3, re-review r5) + coordinator | **Six rounds; 0 blocking outstanding; 18 phase tests; suite 26 / 2479 / 1 at `efd6b99`, failure-ID set unchanged from §6.** Ships the fold (N-2, E-B's SQL aggregate **deleted**), E-P's one-map composition, E-A's batch probe + `today_utc()`→`ctx.now.date()`, `DivisionStep` substitution at both surfaces with strict indexing, and **two** additive clock shims — the typicals cutoff and, added mid-phase as intention **round 4e**, the configuration date in `_common.py:_load_preview_inputs`. **The production code was correct at implement r1 and changed by exactly three lines afterwards** — two D7 comments and one token (`now or` → `now is not None`). **Every blocking finding across all six rounds was in a plan, a ledger, a criterion or a coordinator artifact; none in the code**, now the second phase running for which that holds. The class that dominated: **ten instances of the row-that-cannot-fail**, in four distinct shapes — degenerate fixture *value* (C3's SKIPPED at 0, C8's one-task batch), degenerate *controlling term* (C2's zero allowance, review r3 B1), degenerate *procedure* (C6 row 1, whose recompute equalized its own two sides, re-review r5 S2), and *absent-but-recorded-as-shipped* (C6 clause (iii), r5 S1). Coordinator verified every round independently rather than reading ledgers: **11 whole-suite runs this phase**, every named mutation re-applied at its site with both-direction ID diffs, reverts tree- or hash-verified. Three ledger claims failed to reproduce and were struck or corrected in place (fix r2 row 4's seven IDs vs one — a foreign cap commit landed mid-sweep; fix r6's twenty-one vs two — the mutation's own shape crashed unrelated fixtures; §4.1A C.1's closing sentence, which **this coordinator** wrote at round 4f). §4.3A **path 3 — "the most expensive mistake available in this feature" — had no guard anywhere in the repository until r6**, and the coordinator proved the new row bites at **both** E-P's and E-A's typicals sites, the second of which the ledger never probed. Checkpoints `e7d65b9` → `a28e9e5` → `a9a143f` → `efd6b99`. **Ten rules earned into §5**; intention folded at rounds **4e, 4f, 4g**; baseline published above per closeout obligation 7. **Carried, non-blocking:** 3 pending `ai_inferred` graph items + r1's N6 → owner adjudication (`plans/plan_4.md` C6); N3's wider section-weight coverage debt → `plans/plan_4.md` notes. 14 session artifacts archived to `archive/plan_2/`. |
| 2 | *(prior row — fix r6 dispatched)* | **IMPLEMENTED** | 2026-08-21 | Codex (fix r6) | **Fix r6 closes B1 and S2 in a test-only perimeter.** Added one two-section fixture with five qualifying typicals per section and an open record; exact E-P/E-A allowances are asserted as `(3040, 1520)`, while the named live-typicals mutant produces `(3192, 1368)`. Re-anchored C6 to the same positive-allowance fixture; the settled-substitution mutant still reddens the existing four-ID set, including C6. Focused phase tests: 18 passed; Ruff clean. Clean whole-suite tree `b099423`: 26 failed / 2479 passed / 1 deselected / 2 warnings, with the 26-ID set unchanged from §6. No production files changed; no Architecture Graph delta. |
| 2 | *(prior row — re-review r5 dispatched)* | *superseded (REVIEWING)* | 2026-08-20 | Codex (fix r4) + coordinator (consumption) | **B1, S1–S4 and N4 closed; perimeter is three production lines and they are the three the prompt named** — two D7 comments and N4's single token; `git show a9a143f -- app/beyo_manager/` is four `+`/`-` lines total. Phase file 15 → **17 tests**. Coordinator re-measured at `a9a143f`: clean **26 / 2478 / 1**, failing-ID set `comm`-diffed empty in both directions, and the ledger's arithmetic reconciles on every row. **B1(a) reproduces ID-for-ID** — the settled-substitution mutant adds exactly the four claimed IDs, zero removed, and moves the **category** from `over_share` to `on_track`; the new row pins `186 / 1500 / −1314`, the exact integers plan §5 C2's decidability note derived. **S3's 2026-11-17 expiry is gone** (`closed_at=datetime.now(UTC) - timedelta(days=1)`, statement call still argument-free), so the published baseline will not acquire a 27th member on a date. S4's comments name the fail-loud consequence at both sites; N4 puts both shims on one form. **F-R4 — new coordinator finding, from an unowed probe:** replacing `ctx.now` with a wall-clock read at E-P's loader reddens **the same four IDs as B1(a)**, and `test_c4_frozen_open_record_payloads_are_byte_identical` is **not** among them — two serves microseconds apart round to the same integer, so byte-identity is blind to the clock leak it sounds like it guards. **This is the T1 defect the gate already caught and rewrote as T1′, resurfaced one level up inside the row written to satisfy the criterion T1′ replaced.** The rows are not worthless (the leak is caught loudly by the C2/C6/C9 value rows, and the two-serve loader count carries weight) but review r3's justification for them — the only guard that would see a serializer determinism regression — is now the claim in doubt, and **no mutation has yet been found that these rows alone catch.** Routed as re-review r5's lead probe. Disposition: **re-review r5, delta-scoped** — fix r4 authored **+199 lines of new proof** with new fixtures, and the coordinator's verification covered B1(a)/S3/S4/N4 but not S1's three clauses, S2's recursive walk, or B1(b)'s discriminating power. Prompt `prompts/reviewer/2026-08-20_phase2_rereview_r5.md`. |
| 2 | *(prior row — fix r4 dispatched)* | **IMPLEMENTED** | 2026-08-20 | Codex (fix r4) | **Fix r4 closes B1 and S1–S4, and N4 is applied.** Added the positive-allowance/category-moving C2 row, frozen-clock byte-identity rows for E-P/E-B/E-A, C6's excluded-record/settled-charge/typicals assertions, C7's recursive key walk and live-over-settled assertion, and the wall-clock-derived C11 fixture. Production perimeter is exactly the two D7 comments plus the N4 `is not None` form. Focused phase tests: 17 passed; Ruff clean. Clean whole-suite tree `771ff46`: 26 failed / 2478 passed / 1 deselected / 2 warnings, with the 26-ID set unchanged from §6. Mutation probes were whole-suite, restored, and recorded in `handoffs/implementer/2026-08-20_phase2_fix_r4_handoff.md`. No Architecture Graph delta. |
| 2 | *(prior row — review r3 dispatched)* | *superseded (REVIEWING)* | 2026-08-20 | Codex (fix r2) + coordinator (consumption) | **All four blocking findings and all three should-fix closed; perimeter test-only, zero production lines** (`git show --name-only a28e9e5` touches nothing under `app/beyo_manager/`). Phase file 6 → **15 tests**. Coordinator re-measured on the post-cap tree: clean **26 / 2476 / 1**, failing-ID set `comm`-diffed empty in both directions; arithmetic reconciles (2465 + 9 fix tests + 2 cap tests). **The two mutations that were ∅ last round now bite and are isolated:** C6 `created_at` ⇒ exactly 1 added ID, C8 loop-local ⇒ exactly 2, zero removals. C6's ordering fixtures verified at source — row 2 **ties** `entered_at` so `created_at` decides, row 3 keeps them distinct and swaps it, and they are not merged, which is the part most likely to have been got wrong. **External stream:** the cap's `bb6cc43` landed underneath this fix and touched **none** of our files and **no golden** — no escalation; two of its paths (`domain/item_economics/serializers.py`, `.archgraph/architecture.yml`) are marginally wider than the owner's description, recorded not raised. **F-L4 (should-fix, routed as a review probe):** ledger row 4 claims **seven** added IDs for the C6 `created_at` mutant where the coordinator measures **one** — six are structurally impossible (the goldens hold one step per section, so no ordering field can move them) or sit in the cap's own areas, so that probe's run almost certainly overlapped the cap commit landing. **First instance of the external stream corrupting a measurement — the hazard §7 was written for, arriving in the same round.** Row 5 is unaffected and reproduces the coordinator's pre-fix measurement exactly. N5: C9 correctly names no mutant (three-point contract); N6: the 50-task fixture was removed after measuring, correctly — 50 IDs ⇒ 1 probe + 1 sweep, 51 ⇒ rejected before querying. Disposition: **review r3, full checklist — the phase's first review.** Prompt `prompts/reviewer/2026-08-20_phase2_review_r3.md`, with F-L4 as its lead probe and instructions to re-measure a sample of ledger rows. |
| 2 | *(prior row — fix r2 dispatched)* | **IMPLEMENTED** | 2026-08-20 | Codex (fix r2) | **B1–B4 and S1–S3 closed in a test-only perimeter. Final clean suite: 26 failed / 2476 passed / 1 deselected / 2 warnings; the 26-ID failure set matches master §6 in both directions. C6, C8, C9, C11, and C3 population proof rows added; all named mutation probes restored; C8's 50-task ceiling measured. Production tree and Architecture Graph unchanged. Handoff: `handoffs/implementer/2026-08-20_phase2_fix_r2_handoff.md`.** |
| 2 | *(prior row — implement r1 dispatched)* | *superseded (PROJECTED)* | 2026-08-20 | Opus 5 (projection r0) + coordinator (fold) | Verdict `AMENDMENTS_REQUIRED`, **0 owner cards, 22 ledger rows — all routed before the implement prompt**: 12 amendments applied verbatim (A1–A4, A7–A10, A12–A15), 6 written delegations recorded as **D4–D9** in `plans/plan_2.md` §6, 1 upstream fold (**U1 → intention round 4e**). Headlines: C4's invocation counter must sit on **all three** consumer bindings and its fixture needs a committed evaluation or the fold never runs; E-A's `today_utc()` mutation is inert without a `effective_from` straddle; C5's "fresh session" is unconstructible on the rollback-scoped `db_session`, and the dirty-check must precede `expire_all()`; E-A must **not** gain a `selectinload` (it would silently move `allowance_seconds` through `_governing_step`). Coordinator verified every load-bearing claim at source before applying (11 of them, listed in plan 2 §7) and **re-measured the baseline independently: 26 / 2459 / 1, failing-ID set `comm`-diffed empty in both directions** — §6 now carries both baselines (A14; plan 2 §2 and the orientation banner had both cited §6 for a figure it did not hold). **Three amendments corrected by the coordinator before entering the tree:** **F-A6** (blocking, measured) — A6's row could not fail, because `_governing_step`'s last-applied stable sort is primary and A6's own fixture pinned distinct `entered_at`; split into two measured fixtures, one per field, with the inertness of the wrong pairing measured too (**eighth** instance of the class, **second** arriving inside a correction of that class); **F-A5** — the criterion contradicted delegation D7 from the same handoff (strict indexing turns the stated divergence into a `KeyError`), re-anchored to the E-B face; **F-A11** — the widen-the-perimeter amendment enumerated 4 of 7 suites, omitting E-A's own. **U1 disposition, coordinator's call:** `_load_preview_inputs`'s `today_utc()` conversion is brought **into** phase 2 (task 4b + **C12**) rather than deferred — same construct as E-A's, and leaving one converted and one not would ship a live counterexample to HC-3A. Perimeter widened into `services/commands/item_economics/`, named explicitly. Three rules earned into §5. Implementation and validation are recorded in `plans/plan_2.md` §7 and the implementer handoff. |
| 2 | *(prior row — projection prompt compiled)* | *superseded (PROMPT_READY, projection r0)* | 2026-08-20 | coordinator | `plans/plan_2.md` refreshed against what phase 1 actually shipped (loader signature and its fails-closed guard, `ctx.now`, the goldens) and its read-first list extended to plan 1 §5/§7 and §5's nine new rules. Projection prompt at `prompts/reviewer/2026-08-20_phase2_projection_r0.md` — fresh-session inputs only; depth on the fold's **population equality**, E-P's composition and the one-map contract, E-A's batch keying and call counts, the typicals shim's inertness, C1's golden invariance through the new code path, and C9's constructibility. | `plans/plan_2.md` refreshed against what phase 1 actually shipped (loader signature and its fails-closed guard, `ctx.now`, the goldens) and its read-first list extended to plan 1 §5/§7 and §5's nine new rules. Projection prompt at `prompts/reviewer/2026-08-20_phase2_projection_r0.md` — fresh-session inputs only; depth on the fold's **population equality** (a silent divergence moves a headline without its rows), E-P's composition and the one-map contract, E-A's batch keying and call counts, the typicals shim's inertness, C1's golden invariance through the new code path, and C9's constructibility. Implement prompt compiles only after the ledger is fully routed. |
| 3 | Projection gate r0 over `plans/plan_3.md` | **PROJECTED** (verdict `AMENDMENTS_REQUIRED`) | 2026-08-21 | Opus 5 (projection r0) | Handoff at `handoffs/reviewer/2026-08-21_phase3_projection_r0_handoff.md`. **14 ledger rows — 10 plan gaps, 1 owner card, 3 proposed delegations (D10–D12); none routed yet, so the implementer prompt does not compile.** Measured at `6508ce1` (clean, asserted twice) by applying plan 3 §3's default shape as a monkeypatched pytest plugin against an unmodified tree. Headlines: **N-4's identity holds on every input tried** — negative variance, zero and negative allowance, zero actual — its sole behavioural boundary is `calculate_percent_consumed` returning `None` when the reconstructed allowance ≤ 0, which is independent of the payload's `status` and contradicts the documented "`percent_consumed` is `null` for `infeasible`" rule with nothing in the suite to catch it (**owner card 1**); **§3's file set is wrong** — the default shape reddens 4 tests in 2 files outside it (`test_phase8_serializers.py`, `test_item_economics_handoff_accuracy.py`), because both hand-build `result` with string minutes and `"120.00" + "40.00"` silently concatenates before failing a frame later in the calculator; **C3's and C5's mutation sites are singular where §3 creates two** — mutating E-P alone and mutating both give the identical two-ID delta (goldens + `test_c17`) while E-B alone gives one, so a site can ship unproven; **C5's contract side is confirmed non-vacuous** (goldens reach the path, 295 passed; C5's mutant reddens 2 IDs) but its scope is L4, coupling discovery, not the L2 floor measured here; **C4b has no E-B analogue** and freezing E-B's top-level percent reddens nothing; and the phase-2 fixture the implementer will reach for (`_make_live_fixture`) carries §5A's named degeneracy `variance = 0.00` verbatim, on which C1/C2/C4b bite (100.00 / 120.00 / 170.00) but C3's and C5's denominator mutations are inert. Notes: `test_c17_frozen_final_uses_live_percent_without_money` stays green after D9 by fixture coincidence while its name asserts D9's negation; `_serialize_production_time_final`'s docstring ("with the live percentage") becomes a false claim; §6's "internal key" describes §3's *alternative*, not its default. Perimeter: this row plus the handoff — no plan, no intention, no code, no graph write; §6's archgraph line reads "0 pending, 0 stale" while `archgraph_status` reports 9 pending / 2 stale (coordinator's to reconcile). **Owner card 1 ANSWERED the same session** (owner, 2026-08-21: the frozen percentage keeps its own number when the current status is `infeasible`; the documents are corrected, not the code) — recorded in the handoff's §9 addendum, and the fold owes it a home-artifact entry in `planning/owner_decisions.md` + intention §10, plus a **naming-registry collision to settle**: `D8`/`D9` already mean different things in the intention (owner decisions) and in `plans/plan_2.md` §6 (delegations), and both this answer and plan 3's proposed delegations would otherwise mint `D10`. The answer added one finding (F-14) and one ledger row (L15): the `infeasible` ⇒ `percent_consumed` `null` promise also sits in the **published** `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`, so that half of the correction is a phase-4 closeout item — new dated handoff, never an edit (§7 obligation 2). **Revised totals: 15 ledger rows — 11 plan gaps, 1 owner decision ANSWERED, 3 proposed delegations; 0 owner cards open. 14 findings.** **Supersedes the `PROMPT_READY` row below at the coordinator's fold; that row is not mine to relabel.** |
| 3 | D9: the two frozen-percent feed sites (N-4) + T13 both rows, re-commit immunity, **OD-10's boundary** | **PROMPT_READY** (implement r1) | 2026-08-21 | coordinator (projection fold) | **Projection r0 consumed and all 15 ledger rows routed; OD-10 ratified and folded upstream.** Perimeter verified: the projection wrote exactly its handoff plus one tracker row (`1 insertion`). **The coordinator reproduced all 14 findings independently at source rather than reading the ledger — every one held**, including the count that looked wrong (one `result=None` construction × exactly ten parametrize cases). Independently re-derived N-4's identity at nine quantization-stressing values the projection never tried (sub-cent actuals, three-decimal inputs, half-even boundaries): holds at every one, so §4 task 1 changed from "verify the identity" to "cite it and handle its undefined region". Amendments applied to `plans/plan_3.md`: §6's internal-key note **described the wrong shape** and is corrected in place (L1); §3's file set widened by **enumeration** to two existing test files whose string minute fields trip `_guard_type` — one of which plan 2 §5 C7 had deliberately excluded (L2); C3/C5 now require **one observation per reconstruction site**, because mutating E-P alone and mutating both produce the identical ID delta (L3); **C4c** added — the E-B live percent was unguarded and *unguardable* by the existing row, which compares two faces reading the same expression (L5); §5B carries the measured both-sides numbers and the evidence scope per row (L6); C5 carries its expected two-ID bite set, an **L4** scope, and the short-circuit trap that its golden test is one function looping over three goldens (L7); **C6a/C6b** added for OD-10's boundary — row (b) exists to stop a later "null it whenever status is infeasible" edit (L4) **[CORRECTED at review r1, S1: it is row (a) that stops that edit, measured; row (b) passes under it because its own fixture is `infeasible` too — see the r1 row above]**; §6 records `test_c17_frozen_final_uses_live_percent_without_money`, a **pre-existing row that cannot fail wearing a name asserting D9's negation** (L8); §4 task 2 gained the `result is not None` guard and the docstring correction it would otherwise falsify (L9, L11); §1 names the third `_serialize_result` producer as out of scope with its measured reason (L10); §6A records delegations **P3-D1…P3-D3** (L12–L14). Folded elsewhere: OD-10 into `owner_decisions.md` + intention **§10.4 / §5.3A** (round 4h); L15 into `plans/plan_4.md` **C8** (the published frontend handoff carries the same promise — new dated document, never an edit); the **`D`-namespace collision** into §4 (three meanings were competing for `D10`); the **archgraph drift** into §6 (9 pending / 2 stale, measured — the "inherited clean" line is superseded) and `plans/plan_4.md` C6. Implement prompt at `prompts/implementer/2026-08-21_phase3_implement_r1.md`. |
| 3 | *(prior row — projection prompt compiled)* | *superseded (PROMPT_READY, projection r0)* | 2026-08-21 | coordinator | Projection prompt at `prompts/reviewer/2026-08-21_phase3_projection_r0.md` — REQUIRED (money/percent derivation = rule 6), and the **first prompt compiled under the charter's test-evidence policy**. Three pre-dispatch repairs by the coordinator, all in coordinator-owned artifacts: §1's authority line and the intention's status block both still pointed at phase 2 (rounds `4a–4e`, "Next: phase 2 implement prompt") — the stale-state-line class this project has now hit four times; and `plans/plan_3.md` §5 carried named mutations on C1/C2 only while its own §5A requires one per row — C3, C4a, C4b and C5 now have them, C4 split in two, recorded in that plan's Review log. **C5's addition is the load-bearing one**: it asserted only that plan 1's golden stays green, which an unreached golden does under every mutation — it now names the mutation that must redden it. |
| 3 | *(prior row — plan authored)* | *superseded (NOT_STARTED)* | 2026-08-20 | coordinator | `plans/plan_3.md`. Projection REQUIRED (money/percent derivation = rule-6). |
| 4 | Closeout handoff + the five-node graph delta | **REVIEWING** (review r3) | 2026-08-22 | Codex (fix r2) + coordinator (consumption) | **Fix r2 consumed — B1, S1, S2 all closed and independently verified; nothing added beyond them. Review r3 dispatched: the phase's first external review, full checklist.** Checkpoint `3df02ae`. Perimeter is exactly the ten declared items, **nothing under `app/`**, and `master_plan.md` shows **1 insertion / 0 deletions** — the row was added above the coordinator's rather than over it, so r1's overwrite did not repeat. **B1 closed at the level it failed:** five descriptions edited through five preview→apply pairs, one operation per call; `…-task-budget-status`'s drifted phrase — *"live non-deleted task-step seconds"*, the exact string intention §8 names — is gone; **zero `+`/`-` lines match `summary:` or `inferenceReason:`**, so the immutability constraint held under measurement rather than in claim; HC-5 present once, wording unchanged. The five nodes stay `human_confirmed` — **a maintenance edit to a confirmed description does not re-pend it**, as the dry run predicted. Graph reproduces exactly: `897d57b3…`, 194 / 296, 5 pending, 0 stale, 0 diagnostics. **S1 closed** (§6A C's *"the time is gone at once, not gradually"* now shipped, no-clamp half kept); **S2 closed** (`dc76db8` published with subject and check-out instruction; the SHA resolves and its `app/` diff against HEAD is empty, both re-verified). **Coordinator variation, and it was aimed at this project's signature class:** both rounds reported *"docs guard 59 passed before and after"* — a claim that is equally true of a guard that cannot see the file at all, which is the **row-that-cannot-fail** shape recorded eleven times here in five shapes. Measured instead of assumed: the retired identity token inserted into the new handoff turns the guard **red, 1 failed / 58 passed**, the single red being the rglob test itself. **C7 is non-vacuous over this document.** Probe reverted, file SHA-256 byte-identical, tree clean; marked do-not-re-spend in the review prompt. **Evidence:** 0 L4 (the gate stamp's tree is still `app/`-identical to HEAD, cited by identity), one ~3 s L1 probe. Note recorded, not raised: the implementer's L1 row identifies a dirty tree by SHA without a diff digest; the tree is now committed as `3df02ae` so the record is recoverable, and the probe establishes the same fact more strongly. Review prompt `prompts/reviewer/2026-08-22_phase4_review_r3.md` — eight probes, settled ground marked do-not-re-spend, **reviewer model Opus 5, never Sonnet**. |
| 4 | *(prior row — fix r2 dispatched)* | *superseded (IMPLEMENTED, fix r2)* | 2026-08-22 | Codex (fix r2) | **B1, S1, S2 closed; nothing added beyond them.** B1: the graph's node half is now done — five projection descriptions edited through `archgraph_apply_maintenance_changes`, one operation per call (the open tooling finding's constraint), each preview applied on its own token. The four present-tense projections now state the live basis (settled step seconds **plus** the concurrency-averaged share of any open WORKING interval, resolved once per request from the shared loader, persisted nowhere); the fifth, price-scenario, records the dependency as **transitive** and explicitly denies a direct open-interval read. `architecture.yml` now shows **38 insertions / 20 deletions** where r1 showed zero deletions — the instrument that caught B1. No evidence `summary` or `inferenceReason` touched, and the budget-allocations HC-5 invariant sentence is byte-identical (verified whitespace-normalised, count 1). Graph before → after: `9bcb347f…` → `897d57b3…`, **194 → 194 nodes, 296 → 296 edges, 5 → 5 pending, 0 stale, 0 diagnostics** — maintenance edits moved no count, and the 5 pending are still r1's `ai_inferred` relationships awaiting the owner. S1: §6A C's rule carried in substance — the descent is rendered in one step, not eased down over time; the no-clamp rule kept. S2: tree identity published as the resolvable commit **`dc76db8`** with its subject, plus the note that `git diff dc76db8 HEAD -- app/` is empty. **N1 left untouched by instruction** — the reviewer's probe. Evidence: L1 docs guard `PYTHONPATH=. pytest tests/unit/docs/` → **59 passed** at `e13923f` + this session's edits; **zero L4**, budget was 0 and the derivation still holds. Perimeter: `.archgraph/` (architecture.yml + 5 change records), the closeout handoff, this row, `plans/plan_4.md`, and the fix handoff — **nothing under `app/`** (`git diff --name-only -- app/` empty). Handoff: `handoffs/implementer/2026-08-22_phase4_fix_r2_handoff.md`. |
| 4 | Closeout handoff + the five-node graph delta | **CHANGES_REQUESTED** (coordinator consumption of implement r1) | 2026-08-22 | Codex (implement r1) + coordinator (consumption) | **Implement r1 consumed adversarially. Perimeter exact, evidence budget honoured, the document is strong — and obligation 6 is half-done. 1 blocking, 2 should-fix, 1 note; fix r2 dispatched before any review round.** Checkpoint `80b8cca`. **Verified, not read from the ledger:** perimeter is exactly the four declared files plus the handoff (`git show --stat`), **nothing under `app/`**, and the only file touched under `docs/handoff/` is the new one — no published handoff edited, which is this project's scar. The **21 published IDs `comm`-diff empty in both directions** against the authoritative enumeration in `test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md`, and the five removed IDs match §6's five exactly. L4 budget honoured — **0 L4 runs**, two L1 docs-guard runs at 59 passed. Evidence summaries carry no counts and every anchor is symbol-without-span, verified in the diff. No review item promoted, rejected or edited; 5 pending is the correct outcome for `ai_inferred` additions, not a defect. C4 cites **both** §2.3A and §3.4A (the pre-prompt amendment held); C1/C2/C3/C8 present and correct at source. **B1 (blocking) — the graph delta added edges and updated no node.** 194 → 194 nodes, 291 → 296 edges, **zero deletions in `architecture.yml`**: the four present-tense projection descriptions still assert the settled-only basis (`projection-item-economics-task-budget-status` still reads "live non-deleted task-step seconds"), which is the exact drift intention §8 and C6 exist to correct — §8 names the description update *first* and the edges second. The divergence **was declared** (rule 14 satisfied: "existing settled graph descriptions were preserved rather than rewritten through maintenance"), but the reason does not hold: **measured by dry-run `archgraph_preview_maintenance_changes` on the budget-status node — a `human_confirmed`, non-pending node accepts an `edit` on `fields.description`, returning a clean before/after diff with no cascades and no review adjudication.** The prompt's prohibition was on adjudicating *review items* (pending `ai_inferred`), never on maintenance. Preview not applied; token left to expire. **The ledger row hid it:** obligation 6's Result column describes the *frontend document's* §6 prose, so the row reads discharged while the graph half is untouched — the "a ledger entry is a claim" rule biting exactly where the orientation said it would. **S1 — a per-event client rule drifted in substance.** §6A C's ">1 s" rule is *"do not animate the descent over time; the time is gone at once, not gradually"*; the document ships *"never animate time that the workspace has disowned"* — a different instruction that permits the very ease-out animation the authority forbids, while sounding compliant. **S2 — the published tree identity is unresolvable by its consumer.** It reads "`996a77a` plus the coordinator's two-test deletion", copied from the isolation project's internal phrasing, which reads as a dirty tree a successor cannot reconstruct; that state was **committed** as `dc76db8` (the source row says "gate-committed" — the word was dropped), and `git diff dc76db8 HEAD -- app/` is **empty**, so the citation is sound and only its identity is unusable. Give D23 a SHA. **N1 (reviewer probe, not a fix item)** — record deletion is named to the client; §6A A says naming E5 *as a decrease cause* would tell another codebase to handle an event our API cannot emit, and the document names it as a **non**-cause, so C5's literal is met and the authority's rationale is brushed. **Resolved and NOT raised:** §6A B's two-drops-from-one-action fact is absent from the document and that is **correct** — §6A C opens "the closeout handoff tells the frontend what to do, not what we believe", and C's "any decrease → render the served value" already covers the second drop. Fix prompt `prompts/implementer/2026-08-22_phase4_fix_r2.md`. **Docs guard 59 passed before and after.** Projection **WAIVED**; full review still required, after the fix. |
| 4 | *(prior row — implement r1 dispatched)* | *superseded (IMPLEMENTED, r1)* | 2026-08-22 | Codex (implement r1) | **Docs guard 59 passed before and after.** New dated frontend handoff discharges all seven obligations, including the six-worker runner-qualified 21-ID baseline and OD-10's live-versus-frozen correction; no published handoff or `app/` file changed. Graph delta applied in one batch: 5 inferred relationships, 194 nodes / 296 edges after, 5 pending, 0 stale, 0 diagnostics, revision `9bcb347…`. Handoff: `handoffs/implementer/2026-08-22_phase4_implement_r1_handoff.md`. Projection **WAIVED**; full review still required. |
| 4 | *(prior row — implement prompt compiled)* | *superseded (PROMPT_READY)* | 2026-08-22 | coordinator | **⛔ gate SATISFIED and re-verified; implement prompt compiled at `prompts/implementer/2026-08-22_phase4_implement_r1.md`.** Gate confirmed on all four conditions, the third as a **diff** (`git diff 0aae85e HEAD -- app/` empty), which also made the new runner's stamp citable rather than re-measurable — the prompt's **L4 budget was 0**, derived: the only suite surface reading `docs/` is `tests/unit/docs/`, grep-verified. **Two blocking findings in the plan file itself, fixed before the prompt compiled** (`plans/plan_4.md` §7): **(F1)** §6A's baseline bullet still instructed the closeout to publish phase 2's `efd6b99` / 26 / 2479 / 1 — a *serial*-runner, *development*-database number, i.e. exactly the baseline the owner gated this phase to avoid handing `narrow_typical_work_times` D23; superseded in place with the old text kept as provenance. **(F2)** closeout **obligation 7 had no acceptance criterion** — C1–C6 cover obligations 1–6, C7 the guard, C8 OD-10, and the baseline publication this phase exists to produce had no row, so a handoff omitting it would have passed every criterion; **C9 added**. **(F3)** C4 and intention §5.4 cited different sections for the same frontend question; C4 now requires both halves — **and implement r1 honoured it**. **(F4)** the new handoff is an **input to the suite** (the handoff-accuracy guard rglobs every `*.md` under `docs/handoff/`), named in the prompt as a token not to spell. **Carried item closed:** phase 2's "3 pending `ai_inferred`" were promoted in the owner's 13-item adjudication of 2026-08-21 (record `…eed27f.yml`, commit `3b14447`); the graph had since moved to `cec60a24…` / 194 nodes / 291 edges, all four new nodes belonging to `test_isolation_and_xdist` — §6's graph line corrected. Obligations 1–6 re-verified as still owed **at source**. Zero pytest runs spent on the fold; the 21⊂26 subset relation reproduced by `comm`. Commit `0ef5a3f`. |
| 4 | *(prior row — the gate that blocked this phase)* | *superseded (BLOCKED)* | 2026-08-21 | — | `plans/plan_4.md`. **⛔ Does not start until `pytest-xdist` + per-worker DB isolation ships and the baseline failure-ID set is re-enumerated under the new runner** — owner decision 2026-08-21, conditions in §6's gate block. Its closeout publishes the baseline `narrow_typical_work_times` D23 consumes, so that baseline must be the new runner's, stated with its runner. Projection **WAIVED**: documentation only, no mechanism — waiver recorded here per charter. Full review round regardless. **+C8** (2026-08-21): the OD-10 correction to the published frontend handoff, as a new dated document. **Released 2026-08-22** by merge `0aae85e`; kept because it is the record of *why* the closeout publishes a runner-qualified baseline — "stated with its runner" was written here, before the runner it names existed. |
| — | Mechanism-inventory gate over the intention's mechanisms (M-1…M-9, §7 trigger table) | **PASSED** | 2026-08-20 | Opus 5 (inventory) + owner (D8–D9) + coordinator (fold) | Nine mechanisms swept, 11 lettered sections added (+758/−5), nothing renumbered. Session verdict `OWNER_DECISIONS_PENDING`; both cards answered the same day (**D8** ship-and-disclose the settlement window, **D9** freeze the frozen blocks whole) and folded at round 4a → **PASS**, no second reviewer session (no card branch changed a contract, only behaviour). Coordinator verified at consumption rather than reading the ledger: perimeter matches `git diff` exactly (the one undeclared `app/` change in the tree — `items/lookup/` — is the owner's concurrent item-lookup work, excluded from every pipeline commit); **12 load-bearing claims re-verified at source** (sync-close + async-enqueue in `_step_transition_core.py`, the flag disjunction and `_BUCKET_STATE` in `averaged_time.py`, `uix_step_state_records_active`, the worker-face `percent_consumed` branch, settlement's single `int(round(Σ))` across users, the 8-member enum, `DivisionStep`, `today_utc()` in E-A's loop, `_MAX_TASK_IDS = 50`, `FALLBACK_POLL_SECONDS = 30`, `max_try = 3`); all four §3.2 worked examples re-followed. **Calibration (seal opened at the fold, §7)**: H1 and H2 found and exceeded — H2's own arithmetic corrected, the per-user denominator is *impossible*, not merely loose; **H3 missed by the sweep** (§8's three-vs-four count), fixed at the fold as a coordinator finding. T1's named mutation proved inert and rewritten as T1′ — the both-sides rule biting a fourth time, this round on the coordinator lineage's own artifact. Unilateral resolutions U1–U9 recorded in the handoff; none reopens D1–D7; ratified by the owner's round-4a acceptance. Commits `da4ebcd` (scaffolding) → `e2e7c24` (gate delta) → gate-close commit. |
| — | *(prior row — prompt compiled)* | *superseded* | 2026-08-20 | coordinator | Prompt at `prompts/reviewer/2026-08-20_inventory_mechanism_inventory.md`; calibration seal sealed pre-prompt at `prompts/coordinator/2026-08-20_inventory_calibration_seal.md`. Gate REQUIRED, NOT WAIVABLE. Both resolve under `archive/gate_inventory/` after closeout. |

## 4. Naming registry

Reserved before any code exists, so two sessions cannot pick two names for one thing.
This feature adds no route, no field, no table (HC-1, HC-4); the minted names are
internal seams only.

### The `D` namespace — disambiguated 2026-08-21 (raised by plan 3's projection)

`D<n>` was minted twice in this project before anyone noticed: **owner decisions**
D1–D9 (`planning/owner_decisions.md`, intention §10) and **written delegations to the
implementer** D4–D9 (`plans/plan_2.md` §6). `D8` and `D9` therefore already denote
different things in different files, and phase 3 was about to mint a third `D10`
(an owner answer) alongside three proposed `D10–D12` delegations. Binding from now on:

| kind | prefix | example | home |
|---|---|---|---|
| owner decision | **`OD-<n>`**, continuing the existing sequence | `OD-10` | `planning/owner_decisions.md` + intention §10 |
| delegation granted to an implementer | **`P<phase>-D<n>`**, numbered per phase from 1 | `P3-D1` | that phase's plan §6 |

Historical references are **not rewritten** (charter): intention §10.3's `D1`–`D9` are
owner decisions and read as `OD-1`–`OD-9`; `plans/plan_2.md` §6's `D4`–`D9` are
delegations and read as `P2-D4`–`P2-D9`. Only new names take the prefixed form. The
collision was one fold away from shipping — the projection flagged it rather than
minting into it, which is the behaviour the registry exists to produce.

### The four resolved decisions (planner, 2026-08-20 — grounded in source, not chosen in the abstract)

- **N-1 — HC-3A reading: `ServiceContext` gains `now`.**
  `now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))` in
  `services/context.py:ServiceContext` — tz-aware UTC, stamped once at context
  construction, which **is** the service boundary (`run_service.py:run_service` is a
  pure error boundary over an already-built ctx and needs no change). `now` is request
  data like `incoming_data`, not a flag or config value, so the class's standing
  prohibition is not violated — the docstring says so explicitly. Every service reads
  `ctx.now` and never a clock; tests freeze it by passing `now=`. Chosen over a
  threaded parameter because the parameter route forces a signature default on
  `get_task_budget_status` for its four callers, and **a default that silently reads
  the clock is the defect T1 exists to catch** (intention §1A HC-3A); `ctx.now` gives
  the shipped price-scenario endpoint its one clock read with zero code change in that
  file.
- **N-2 — the E-B aggregate is replaced by the per-step fold.**
  `_build_evaluated_status` loads the task's non-deleted steps (no state filter —
  intention §4.1A A population check) and computes `actual_seconds` as the sum of the
  loader's per-step figures; the `func.sum` aggregate is deleted. Chosen over
  keep-and-add because keep-and-add leaves **two code paths producing one number**
  (E-P passes a map; standalone E-B would sum SQL + shares) — the exact defect class
  this pipeline exists to remove — and saves nothing (§4.1A A: the per-step figures
  are needed anyway).
- **N-3 — the loader.**
  `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py`,
  `async def load_live_worked_seconds(session, workspace_id, steps, now) ->
  dict[str, int]` — keyed by step `client_id`, values are intention §3.1A's
  `settled + int(round(open_share))`. Item-economics owns the seam; analytics keeps
  the crediting rule (§8). The future alerting scheduler is this function's first
  external customer (§7 non-goal, §4.1). Threading: `get_task_budget_status(ctx, *,
  live_seconds=None)` where `None` means "compute from `ctx.now`", never "skip".
  Allocator rows carrying live figures are **`budget_division.py:DivisionStep`**
  instances (already exists, carries every field the allocator reads) — never
  ORM-attribute assignment (HC-1A).
- **N-4 — the D9 frozen-percent source.**
  Both feed sites compute
  `calculate_percent_consumed(result.actual_worker_minutes +
  result.variance_worker_minutes, result.actual_worker_minutes)` — the denominator
  reconstructed from the frozen record alone via the identity
  `allowed ≡ actual + variance` (`calculator.py:calculate_variance_worker_minutes`),
  so the frozen percent survives a later re-commit with a different allowance
  (plan 3 C3 is the row that proves it). Feed sites:
  `division_serializers.py:serialize_task_production_time` (the argument to
  `:_serialize_production_time_final`) and
  `serializers.py:serialize_task_budget_status` (the `percent_consumed=` argument to
  `:_serialize_result`). The identity is verified against the calculator's definition
  before first use (plan 3 task 1) — a formula asserted in a registry is a claim like
  any other.

Binding constraints, in force now:

- **One crediting rule, one home (HC-2).** The live share is computed by
  `concurrency.py:averaged_seconds_by_record` through
  `averaged_time.py:compute_record_contributions` — **imported, never reimplemented,
  never forked**. A second averaging rule, or a `now − entered_at` elapsed, anywhere in
  this feature is a defect by definition, not a simplification.
- **The shared loader** — resolved: **N-3** above (name, home, signature, threading).
- **The E-B aggregate decision** (intention §4.1, review finding 4; condition pinned by
  the gate at §3.1A A) — resolved: **N-2** above. The loader's step set is exactly
  "the task's non-deleted steps" — no state filter — or T6's headline-equals-rows
  breaks (§4.1A A population check; plan 2 C3 carries the row).
- **The D9 frozen-percent source** (intention §5.3, §4.1A B) — resolved: **N-4** above.
- **`task_steps.total_working_seconds` keeps its exact meaning** — settled,
  concurrency-averaged, recomputed at transitions. No name in this pipeline may imply
  otherwise.

## 5. Standing rules

Charter rules 1–11½ apply in full, **plus the entire earned corpus at
`simple_valuation_editor/master_plan.md` §5** (~30 rules from five pipelines) — adopted
by reference, binding, not restated. The ones that bite hardest on *this* feature,
restated because they are load-bearing here:

- **Rule 6 — this whole feature is rule-6 surface.** Time arithmetic, a
  concurrency-averaging rule, a windowing rule with an anchor and a buffer, a numeric
  parity bound, money derived from seconds. Every mechanism produces a number that looks
  plausible when it is wrong. Nothing here fails loudly.
- **Every named mutation: compute both sides, name its site (file,
  definition-vs-call-site), run it at the scope its hypothesis requires, record the
  full evidence record** — hypothesis, scope, command, tree identity, result,
  observed-red ID delta (both directions at that scope). *Amended 2026-08-21 per the
  charter's "Test-evidence scope and reuse" section (owner decision, test-execution-policy
  audit): the earlier form mandated the whole suite for every observation; L4 is now
  reserved for gates, absence claims, and coupling discovery — an absence claim
  ("nothing anywhere guards X") still runs, and can only run, whole-suite.*
- **A single run is not evidence.** Two named flaky tests exist (§6). A count that
  disagrees with baseline is repeated and its **ID set** diffed before any conclusion.
  Only an ID added or removed across repeated runs is a finding.
- **A fixture whose expected value is the same under the defect proves nothing** — check
  the assertion form, and evaluate the function at the values the assertion claims to
  tell apart, before the row ships.
- **An absence claim is only as good as its scope AND its term set.** Earned in this
  exact query family: `today_utc()` wraps `datetime.now` and defeated a
  `datetime.now|utcnow|func.now` grep — two calls in `services/queries/item_economics/`'s
  neighbourhood (`worker_stats`). Record the search terms beside every absence claim.
- **Citations are `path:symbol`, never bare line numbers** — a cross-reference from any
  artifact must resolve from a clean checkout. Intention round 3a is the local record of
  why (a call cited by line sat at six different lines across six commits while the code
  never changed).
- **T5 goldens are captured and committed at the pre-change checkpoint.** A golden
  captured after the change compares the new payload to itself; writing one is a gate
  failure, not a test.
- **Never rewrite a published handoff.** New dated documents, amendment by reference
  (frontend-adopted convention; an in-place edit cost them four days once).
- **"Record the decision" names its post-closeout medium** — code comment, this master
  plan, or graph node; never only a handoff, which archives.
- **A comment asserting a property is a claim and inherits the mutation rule; sweep the
  class, not the instance.** When a finding names one member of a set, probe every member.
- **Before citing a test as proof of a SQL predicate, check that the test issues SQL.**
  This pipeline's tests will assert `WHERE` clauses over `step_state_records`; a fake
  session makes those predicates untestable while looking covered.
- **Tests that commit rows own their teardown** (charter 11½) — live-interval fixtures
  will commit `step_state_records`; cleanup runs on the failure path too.

### Rules earned by this pipeline (each from a measured defect)

- **Any enumerated set describing something still in motion carries the date and the tree
  it was measured at** — and a correction inherits the shelf life of the thing it corrects
  (phase 3, three consecutive rounds, three different artifact types). Measured instances:
  the **C5 expected-bite-set** went stale one round after it was written, when C6c joined
  the class it enumerates; **intention §5.3A**'s S1 correction diagnosed a fixture *and
  ordered it changed*, and the very next fix cycle falsified its premise while leaving its
  conclusion true; **master §7's stream-3 perimeter** under-declared twice in one day and
  its "additions that pass do not touch the failing-ID set" clause was true of the stream
  as first observed and false a day later. All three read as timeless present-tense fact.
  Two consequences: **(a)** when a correction both diagnoses a state and orders it changed,
  the diagnosis goes in the **past tense** with the order beside it, **in every document
  that receives the fold** — not only where the fix is executed; **(b)** an enumerated
  expected set is updated **in the same cycle** that adds a member to the class it names,
  or it converts the next round's correct result into a false finding.
- **A justifying number is a claim and inherits the mutation rule** (phase 3, N8). The
  coordinator wrote that C6c was "non-vacuous against a live `120.00`"; the measured value
  is `170.00`, because C6c serves at the **open** state and `120.00` is the pre-open value
  it never serves. The conclusion survived only because both candidates differ from
  `150.00`. §5B already requires computing both sides before *choosing* a fixture — the
  same discipline binds the justification written **afterwards**, which had been done by
  inspection.
- **A stream/write perimeter covers documents, code AND tool-recorded state** (phase 3,
  N9). §7's stream perimeters were written code-only while the charter's handoff rule
  already names all three, so they under-declared by construction — and the omission hid a
  foreign stream writing `.archgraph/architecture.yml`. Perimeters of every kind use the
  handoff schema.
- **While an uncommitted foreign stream is live, an aggregate-diff digest is the wrong
  revert instrument; use per-file digests over the reviewed perimeter** (phase 3,
  re-review r3). The reviewer's `app/`-scoped digest went stale between its last probe and
  its last artifact write through no action of its own — the owner saved a file. An
  aggregate digest conflates "my probe leaked" with "someone else edited the tree"; per-file
  digests over the files under review separate them and are what carried the claim.

- **Every term of a defining equation gets a criterion that varies it away from its
  identity element** (phase 1 review r1, B1). All 17 loader fixtures pinned
  `total_working_seconds = 0` — addition's identity — so deleting the `settled +`
  term left the whole suite green. 0 for addition, 1 for multiplication, ∅ for a
  union: a fixture sitting at the identity element makes the operator untestable
  while the row's name says otherwise.
- **Equality assertions do not test types in Python** (r1, B2). `{k: 1800.0} ==
  {k: 1800}` is `True`. A criterion naming an output type requires an explicit
  `isinstance` row; a value row can never carry it. And a criterion naming a
  rounding **mode** needs a fixture where the modes disagree — an exact
  half-second share here.
- **A claim that names WHERE a failure surfaces is a mechanism claim and inherits
  the mutation rule** (r1, S1). HC-3A named `concurrency.py:_sweep` as the loud
  failure site without probing it; on the configured driver the rows never reach
  the sweep and the true un-guarded behaviour is a silent wrong answer. Probe the
  named site before the claim ships — the same discipline rule 11 imposes on named
  mutations.
- **A delegation grant names its post-closeout medium** (r1, N7). "Recorded in the
  test beside the row" was granted; the record landed only in the handoff, which
  archives. D-grants say "as a comment in the test" (or the plan, or the graph),
  never merely "recorded".
- **A failure-site claim must be probed in BOTH directions before it ships — and the
  correction of one is itself one** (re-review r4, B1-r4). HC-3A named where a naive
  `now` surfaces three times: the sweep raises (round 4), the sweep cannot fire
  (round 4c), and finally the measured truth — it depends on the client host's UTC
  offset. Round 4c's claim was written *in the act of correcting* round 4's, then
  passed through a coordinator fold, an implementer transcription and two
  consumption re-verifications untouched, **because all of us re-ran the same
  fixture in the same direction**. One fixture where the mechanism fires, one where
  it does not, or the claim is unproven.
- **A guard that imitates the failure it pre-empts is untestable by
  `pytest.raises(Type)`** (r4, B1-r4). The loader's guard raised CPython's exact
  message at a lower frame than `concurrency.py:_sweep`, so a type-only assertion
  cannot distinguish them: on a UTC host, deleting the guard leaves the safety test
  **green** (measured by the coordinator with `TZ=UTC`). A safeguard duplicating a
  downstream failure's signature must be pinned by **site** — a distinctive message,
  the traceback origin, or an observable absence of side effects — never by type
  alone. Generalizes charter rule 11 from "name where the mutation is applied" to
  "name where the failure must originate".
- **An observation that depends on the host's timezone, locale or clock is an
  environment fact, not a mechanism fact** (r4). "0 rows observed" held by a
  ten-minute margin against a sixty-minute shift and inverts on a UTC host. Record
  the host offset beside such an observation, or build the fixture so the
  observation is offset-independent — and run the mutation under at least two `TZ`
  settings, one of them `UTC`.
- **A count is not a set: capture the failing-ID set BEFORE repeating an anomalous
  run** (r4, N3-r4). §6 already mandates the ID diff, but a repeat performed against
  a bare count makes the diff impossible and the anomaly unattributable forever —
  which is why the identity of this project's third flaky test is now unrecoverable.
- **When a contract's reason for a rule is "form A and form B differ", the fixture
  must be placed where they differ — compute that before choosing it** (coordinator,
  fix-r2 consumption, F-C1). §3.1A A mandates rounding the share rather than the sum
  *because* the two diverge on exact halves; the criterion written to guard it put
  its fixture at `settled = 0`, where they **coincide**, so the whole suite stayed
  green under the sum-locus. A criterion naming two properties in one breath
  ("type **and** locus") must name a mutation per property and give each its own
  row, each fixture isolating one — otherwise the strong-sounding title is the only
  thing guarding the second property. Corollary to the identity-element rule above,
  and it arrived **inside the correction of that same class** (the fifth such
  instance on this project).
- **A mutation of a multi-use argument states which uses it covers** (coordinator
  consumption of implement r1). The same named mutation applied to one of two uses
  of `now` reddens 11 tests; applied to both, 12. Two shapes, two observations —
  a ledger row that does not say which shape it ran is not reproducible.
- **Where a sort is a stack of stable sorts, only the last one applied is primary —
  a field below it is observable only on a fixture that ties every key above it**
  (coordinator, plan 2 projection r0 consumption, F-A6). `budget_division.py:_governing_step`
  sorts by `client_id`, then `created_at`, then `entered_at`; a criterion written to
  prove the substituted row carries `created_at` specified a fixture with **distinct**
  `entered_at`, where `created_at` is never consulted — the mutation left the governing
  step unchanged on both sides. One field per fixture, each tying the keys above it,
  and **measure the ordering against the real function before writing the row**: the
  arithmetic of a sort stack is not readable off the criterion's prose. Eighth instance
  of the row-that-cannot-fail class, second to arrive inside a correction written to
  fix that class.
- **An amendment that widens a perimeter is itself an enumeration, and inherits
  "enumerate, never sample"** (coordinator, same consumption, F-A11). The amendment
  raised precisely because C10's blast-radius perimeter was too narrow listed four of
  the seven suites that reach the changed function — omitting the one belonging to the
  surface the phase rewrites hardest. Generate such a list mechanically (`grep -rln`
  over `tests/`) and record **each entry's mode of contact** (executes it / drives it
  with a hand-rolled session / references it by identity), because "reaches" is not one
  relationship and the remedy differs per mode.
- **A criterion that pins an outcome must be placed where the outcome's *controlling
  term* is non-degenerate — and the degenerate term is not always the addend**
  (reviewer r3 B1, plan 2; coordinator-measured). Eight prior instances of the
  row-that-cannot-fail class were identity elements of the arithmetic (`settled = 0`,
  `∅` for a union). The ninth is a new shape: C2's fixture arithmetic was fine and its
  **allowance** was degenerate at `0`, so a *comparison*-based verdict
  (`worked > allowance` ⇒ `over_share`) returned the same answer under the live basis
  (2040) and the pre-phase settled basis (1440) — measured both ways. **Compute the
  verdict under both bases before choosing the fixture**, not just the values. Corollary:
  when a criterion asserts a categorical field, the mutation must be able to move the
  *category*, not merely the number feeding it.
- **When a criterion compares state before and after an operation, check the operation
  does not erase the difference the comparison exists to see** (re-review r5 S2, plan 2 C6
  row 1; measured). The row served a payload, closed the open record, ran
  `_recompute_step_time_totals`, served again, and compared allowances — but the recompute
  makes the settled figure **equal** the live one, so both sides were computed from an
  identical input vector (captured and shown identical). A mechanism that made
  `allowance_seconds` live-dependent would move both sides equally and the comparison would
  still hold. **Tenth instance of the row-that-cannot-fail class and a third distinct
  shape:** eight were degenerate fixture *values*, the ninth a degenerate *controlling
  term*, this one a degenerate **procedure**.
- **When a finding condemns a fixture as degenerate, sweep every row standing on that
  fixture — not the row the finding named** (re-review r5 S2). Review r3's B1 condemned
  `_make_live_fixture`'s zero allowance; fix r4 built C2 a new fixture and left C6 row 1
  asserting `0 == 0` on the old one. This is "sweep the class, not the instance" applied to
  **fixtures**, and it is the second construct that rule has had to reach (after comments).
- **A finding can come back closed-in-the-record and absent-in-the-file — so the consuming
  fold greps for the clause, it does not read the sentence claiming it** (re-review r5 S1).
  C6 clause (iii) was recorded as shipped in a handoff *and* a Review-log entry; `grep`
  found no occurrence of the word it turns on. Same defence this project already applies to
  ledger counts, extended to prose claims of delivery.
- **A criterion guarding a derivation names the term the derivation *reads*, not a payload
  field that happens to carry the same number** (re-review r5 B1). C6 clause (iii) named the
  payload's `typical` block; the value that reaches the allocator is `typicals_by_section`,
  a different dict built in the same loop. Guarding the echo is not guarding the input.
- **A multi-hour mutation sweep is not "a round", and a foreign commit can land inside
  it** (reviewer r3 S5; master plan §7's external-stream clause). §7 says every round
  re-measures its baseline; that is too coarse when one sweep spans hours and another
  stream commits into the repo mid-sweep. **Every ledger row records the tree it was
  measured at**, and a sweep that spans a foreign commit is **re-based, not annotated** —
  its rows are observations on a tree that no longer exists. First real instance: plan 2's
  fix-r2 sweep was captured at 2474 passes while the delivered tree reads 2476, and the
  row measured closest to the foreign commit attributed six of that stream's failures to
  its own mutant.
- **A delegation and a criterion authored in the same handoff can contradict each
  other** (coordinator, same consumption, F-A5). D7 granted strict indexing of the live
  map; A5's criterion stated a value divergence that strict indexing converts into a
  `KeyError`. Both were individually right. When consuming a ledger, cross-read the
  delegations against the criteria they touch — the rows are written independently and
  nothing inside the handoff does that check.

## 6. Environment

- Working directory `backend/app/`; tests `PYTHONPATH=. pytest -m 'not e2e'`. The bare
  `make test` form fails collection (`ModuleNotFoundError: beyo_manager`) in some shells.
- **⚠ WHICH DATABASE THE SUITE RUNS ON — established 2026-08-21 (fix r2 raised it, the
  coordinator measured it). This is the starting input for the per-worker-DB work that
  gates phase 4.**
  - `app/.env` sets `DATABASE_URL` to the **development** database,
    `postgresql+asyncpg://…@localhost:**5433**/beyo_manager`, and `tests/conftest.py`
    initializes from `settings.database_url`. **Every measurement in this pipeline —
    phase 1's baseline, phase 2's published approval baseline (`efd6b99`, 26/2479/1) and
    all of phase 3's stamps — was taken against the development database.**
  - `app/.env.testing` designates a *different* database on a *different port*:
    `…@127.0.0.1:**5432**/app_test`. That database **exists but is stale**: stamped at
    revision `67cfba8fcb2d` with 96 public tables, and **`cost_model_versions` and
    `item_cost_results` do not exist in it** (measured directly with `to_regclass`).
    That is why fix r2 reported the testing database "lacks the `cost_model_versions`
    table" and fell back — the report is accurate.
  - Consequences, binding: (i) the suite writes its residue into a **development**
    database, which is why §6 already records residue rows as never being evidence;
    (ii) the isolation work does **not** start by adding workers — it starts by building
    a correctly migrated test database and **re-enumerating the 26-ID baseline there**,
    where the failure set may legitimately differ; (iii) charter rule 7's "configured DB
    left at head" is currently satisfied for the dev database and **not** for `app_test`.
  - Hazard to check during that work, not merely assumed:
    `app/migrations/env.py` still carries the `connection.rollback()` guard at line 167
    (verified 2026-08-21) that prevents the Alembic transaction trap where
    `alembic upgrade` logs success, **exits 0 and persists nothing**. A stamped-but-
    incomplete database is exactly that trap's signature, so when migrating a fresh test
    database, **assert the DDL afterwards — never accept the exit code as evidence.**
- **⛔ THE GATE IS SATISFIED — 2026-08-22. READ THIS BEFORE CITING ANY BASELINE BELOW.**
  The `test_isolation_and_xdist` project closed on 2026-08-22 (merge `0aae85e`). Both
  baselines recorded further down are **superseded**, and so is the "which database"
  block above.
  - **New authoritative baseline, under the new runner:** **21 failed / 2576 passed**
    at the shipped default in **50.61 s**; **21 failed / 2575 passed / 1 skipped /
    1 deselected** under the serial comparator in 131.91 s. Collection **2597**.
    Coordinator-measured at the gate; `comm`-empty in both directions between the two
    invocations.
  - **The 21 is a strict SUBSET of the 26 enumerated below — five removed, zero added.**
    Verified by `comm` on 2026-08-22. No criterion that compares against the 26 gains a
    member; five stop appearing. The five the isolation work **fixed** (they were
    dev-database coupling and collection-order coupling, not product defects):
    `test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model`,
    `…::test_person_owned_configuration_and_section_membership_are_not_overridden`,
    `test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`,
    `test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`,
    `test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`.
  - **The invocation changed and nothing announces it.** Bare
    `PYTHONPATH=. pytest -m 'not e2e'` now runs **six xdist workers with
    `--dist loadfile`**, because `app/pytest.ini`'s `addopts` carries `-n 6 --dist
    loadfile` (owner decision OD-10 in that project's intention). The serial comparator
    is `-n 0`, and the `1 skipped` it reports is the criterion asserting the shipped
    default really is parallel. `PYTHONPATH=.` is still required; the four `app/Makefile`
    test targets now carry it.
  - **The "which database" block above is answered, not merely updated.** Every pytest
    process now creates its own database from a migrated template and drops it at
    session end, behind a five-step fail-closed guard. **Suite residue no longer lands in
    the development database** — the only persistent artifact is
    `beyo_test_main_template` — so §6's "residue rows are never evidence" rule is now
    belt-and-braces rather than load-bearing, and charter rule 7's "configured DB left at
    head" holds by construction. `app_test` on port 5432 is no longer used or relevant.
  - **New precondition on the number: Redis must be reachable at `settings.redis_url`.**
    Two logout rows assert against a live Redis by name and the `redis_client` fixture's
    teardown has no connection guard, so a machine without Redis measures **23 failures
    and 2 errors**, not 21. A published baseline in this pipeline now states its failing-ID
    set, tree identity, database identity **and the services that must be reachable**.
  - Authoritative record and full provenance:
    `docs/architecture/under_construction/implementation/test_isolation_and_xdist/master_plan.md`
    §8, with the enumerated 21 in that project's `archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md`.
    **Phase 4's closeout publishes this baseline for `narrow_typical_work_times` D23,
    stated with its runner** — six workers, `--dist loadfile`, Redis up.

- **Start baseline, pre-phase-1, re-measured by this coordinator 2026-08-20 on a clean
  tree at `2711b58`: 26 failed / 2436 passed / 1 deselected** (supersedes the `a0aaacc`
  measurement of 26/2433/1 — commit `6c15678` added/changed item-lookup tests, +3
  passed, failed set unchanged; re-measure forced by projection r0 finding L4).
- **Current baseline, phase 1 approved: 26 failed / 2459 passed / 1 deselected** —
  measured by plan 2's projection r0 at `0151775` and **re-measured independently by
  the coordinator at the same tree**, 123.97 s. The +23 are phase 1's own tests. The
  failure-ID set is **unchanged between the two baselines** and is what every criterion
  compares against; both coordinator runs `comm`-diffed empty in both directions
  against the enumeration below. Cite *this* line for a phase-2 baseline, not the
  pre-phase-1 one (plan 2 projection r0, A14 — plan 2 §2 and the superseded-orientation
  banner at `646fb9a` both cited §6 for `2459` while §6 carried only `2436`).
  The 26 are inherited and pre-existing; none is in `item_economics`. **The enumerated
  failure-ID set C1 compares against:**

  ```
  tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values
  tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model
  tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_person_owned_configuration_and_section_membership_are_not_overridden
  tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections
  tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events
  tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing
  tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference
  tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task
  tests/integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged
  tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_promotes_expected_candidates
  tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_demotes_low_priority_available_first
  tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_noop_emits_no_events
  tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value
  tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_worker_working_sections_excludes_counts_for_deleted_parent_tasks
  tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rewrites_sort_order_and_worker_view_follows_it
  tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rejects_payload_not_matching_active_set
  tests/integration/test_audit_log.py::test_write_audit_from_event_inserts_row
  tests/integration/test_audit_log.py::test_detail_defaults_to_empty_dict
  tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_seat_height_without_height_maps_without_zero_values
  tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values
  tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name
  tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes
  tests/unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields
  tests/unit/test_items_router.py::test_route_list_item_issues_forwards_client_id
  tests/unit/test_items_router.py::test_route_delete_item_issues_forwards_ids
  tests/unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params
  ```
- **⚠ Suite instability — at least TWO named flaky tests** (named after 21 measured runs,
  `simple_valuation_editor/master_plan.md` §6 carries the full evidence):
  `test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
  and
  `test_process_shopify_products_integration.py::test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task`.
  Binding consequence: **a single run is not evidence** — repeat and ID-diff.
- **⚠ A THIRD intermittent test exists, and its identity is unrecoverable** (r4,
  N3-r4). At fix r3 a mutation run read **26 failed with the new mutation ID
  present** — arithmetically that means one of the enumerated 26 baseline IDs
  *passed*, which neither named flaky test can explain (neither is a member of the
  26). The run was repeated per the rule and came back correct, but only its
  **count** had been recorded, so the ID diff that would have named the test was
  never performable. Consequence, binding: **capture the failing-ID set before
  repeating an anomalous run**, never after. Twelve subsequent whole-suite runs
  (coordinator ×8, r4 ×4) showed zero removals, so it has not recurred.
- **Host timezone matters to this phase's tests.** The suite runs on the host's local
  zone unless `TZ` is set; a naive datetime bound through the driver is reinterpreted
  in that zone. Any mutation touching naive/aware datetime handling is run under at
  least two `TZ` settings, one of them `UTC` (earned r4 — a safety mutation that bit
  at `+02:00` did not bite at all under `TZ=UTC`).
- The suite leaves residue rows (`task_steps`, `step_state_records`) from tests outside
  this pipeline; row-count drift is never evidence of a code change.
- **Architecture graph — CLEARED 2026-08-21: 0 pending, 0 stale, 0 diagnostics**
  (`archgraph_status` revision `fbe0f7c3…`, 190 nodes / 288 edges). Read the history
  below before citing that, because "the graph is clean" is exactly the sentence that
  went stale last time.
  - **Re-measured 2026-08-22 (coordinator, phase-4 pre-prompt): still 0 pending / 0 stale
    / 0 diagnostics, but the revision and the counts above are stale** — now
    `cec60a24…`, **194 nodes / 291 edges**. The +4 nodes and +3 edges are all
    `test_isolation_and_xdist`'s, each with its own review record
    (`infrastructure-test-database-isolation`, `test-database-isolation-contract`,
    `infrastructure-template-copy-contention-lock`,
    `configuration-shipped-pytest-parallel-default`). **The clean *verdict* survived the
    drift and the identifying numbers did not** — which is the third time in this pipeline
    that a graph sentence went stale while staying true, so cite the measurement, never
    this line. Phase 4 re-measures at its own delta per `plans/plan_4.md` C6.
  - **What it drifted to first.** The line here previously read "inherited clean as of
    `0bab586`". Plan 3's projection reported **9 pending / 2 stale**, reproduced by the
    coordinator at `6508ce1`, and it reached **13 pending** by the time it was cleared —
    stream 3 added four items mid-session. Every one was attributable **by timestamp**,
    which is what dissolved the "accrued silently" worry: 3 from phase 1 (11:21 on
    2026-08-20), 4 from phase 2's consumer edges (18:38), 2 from the owner's
    production-budget-cap stream (19:45), 4 from the shopify stream (08:16 on 08-21).
    The phase-2 four are the ones this pipeline's own rounds each declared as "no
    Architecture Graph delta" — that claim was wrong, and only the timestamps showed it.
  - **The two stale nodes, and their causes.** `projection-item-economics-task-production-time`
    (drifted by *our* phase 2/3 — `get_task_production_time` grew 23–45 → **26–121**, so
    the stored span ended mid-function) and `projection-item-economics-task-price-scenario`
    (drifted by the owner's cap stream — 181–311 → **184–315**). Both repaired by
    unlink+link with **spans re-derived from the symbol, never trusted** — the ledger's
    own lesson, and all four stored spans were wrong. One operation per call, per the
    open tooling finding.
  - **The 13 were promoted on owner adjudication 2026-08-21**, seven with per-item
    coordinator verification recorded in the review record and six (the cap and shopify
    streams) explicitly marked *promoted on owner authorization, not coordinator
    verification* — the pipeline has never reviewed those implementations and the audit
    trail says so. Review record `.archgraph/reviews/2026-08-21T08-50-39-304Z--eed27f.yml`.
  - **N6 is closed by decision, not by rebuild.** The owner promoted the `reads_from`
    edge as-is over the count in its summary ("issues one batched probe"), because the
    count is true, its anchor is exact, and phase 2's C8 regression-tests it — where
    reject-and-re-record would have destroyed provenance to delete one tested word.
  - Agents still never promote, reject or edit review items. This queue was cleared
    because the owner adjudicated it. Two open tooling findings sit in
  `implementation/archGraph_mapping_mantainance/open/` — read them before any
  `archgraph_repair_anchors` call (one operation per call; batches fail) and before
  trusting a `conflicting-canonical-relationship` diagnostic.
- Checkpoint commits at every `IMPLEMENTED`, prefixed `CHECKPOINT (not approved):`,
  under the owner's standing authorization; never squashed. The phase is committed again
  at its approval gate.

### ⛔ GATE (owner decision 2026-08-21): the test-environment work blocks phase 4

**Phase 4 does not start until `pytest-xdist` + per-worker database isolation is
implemented and the baseline failure-ID set is re-enumerated under the new runner.**
Owner decision, 2026-08-21, taken after phase 3's implement round demonstrated where the
remaining time actually goes: with hypothesis-scoped selection in force, the inner loop
costs seconds and **every remaining two-minute run is an authoritative one** — the cycle
stamp, the L4 coupling probes, the approval gate. Those are exactly what parallelism
speeds up, so the two optimizations are now sequential rather than alternative: selection
removed the wasteful runs, xdist attacks what is left.

Sequencing, binding:
1. Phase 3 runs to APPROVED on the **current serial runner** — never change the runner
   mid-phase, because every in-flight measurement and the published baseline are stated
   against it.
2. Then the environment work (isolation first, then parallelism), on its own branch of
   work, with the baseline failure-ID set **re-enumerated and re-published** under the new
   runner before any mutation result is trusted on it.
3. Then phase 4 — whose closeout publishes the baseline that
   `narrow_typical_work_times` D23 consumes, so it must be the *new* runner's baseline,
   measured once and stated with its runner.

The tracker's phase-4 row carries this as its gate condition. A phase-4 prompt compiled
before step 2 is complete is a gate violation, not a scheduling preference.

### Post-phase-2 test-environment work (owner-approved 2026-08-20, do NOT start mid-round)

The mutation protocol's cost is one whole-suite run per named mutation, ~2m30s serial
(~2,500 tests, one core; `pytest-xdist` is **not** installed — verified). Fix r2's
fourteen-mutation sweep is therefore ~40 minutes of pytest. Two changes were agreed with
the owner, **both to start only once phase 2 is APPROVED** — never mid-round, because
each would invalidate in-flight measurements:

1. **Install `pytest-xdist` and give each worker its own database or schema.** The
   blocker is not the plugin, it is that this suite's integration tests share one
   database through the rollback-scoped `tests/conftest.py:db_session`; concurrent
   workers would see each other's rows and failures would go nondeterministic — poisoning
   the exact measurements xdist is being bought for. Isolation first, then parallelism,
   then re-enumerate the baseline failure-ID set under the new runner before trusting a
   single mutation result.
2. **Narrow the mutation *set* per round, never re-measure confirmed rows.** From
   review r3 onward only mutations whose criteria changed that round are re-measured
   (typically 3–4); confirmed measurements stand in the Review log and are cited, not
   re-run. Fix r2's full sweep is a one-time correction of B4, not the steady state.

**Superseded 2026-08-21 (owner decision, all three cards of the test-execution-policy
audit approved — the audit is archived at
`archive/plan_2/2026-08-21_test_execution_policy_audit.md`):** this section
previously closed with the absolute "every mutation run stays whole-suite". That
absolute is retired. The governing policy now lives in the charter's
**"Test-evidence scope and reuse"** section (`/Users/davidloorenz/agent-skills/pipeline-charter.md`):
mutation observations run at hypothesis scope (L1 targeted / L2 domain by default);
full-suite (L4) is reserved for the one clean stamp per implement/fix cycle close,
review entry on a changed tree, the approval gate, baseline re-enumeration, and
hypotheses that are repository-wide by construction. The two signals the old absolute
protected are exactly the L4 triggers the charter names: **absence claims** ("no test
anywhere guards X", expecting ∅/∅ — both of review r3's blocking findings and §4.3A
path 3 were this shape) and **removed-ID / cross-file coupling discovery** (C6's
`latest_state_record` mutation reddened two tests outside the phase file). State those
hypotheses explicitly and they still get the full suite; every other observation does
not. Every evidence record carries hypothesis, scope, command, tree identity (SHA +
clean-status assert; dirty trees add a diff digest), result, and ID-delta — and a
record whose tree matches the consumer's is cited, never reproduced. Phase 3 is the
first phase run under this policy.

### Code facts verified at source (this coordinator, 2026-08-20, tree `a0aaacc`)

- **The full production consumer set of `get_task_budget_status` /
  `_build_evaluated_status` is four callers**: the E-B route selector
  (`routers/api_v1/item_economics.py:route_get_task_budget_status` picks manager vs
  worker face), the worker face
  (`get_task_budget_status_worker.py:get_task_budget_status_worker` imports
  `_build_evaluated_status` directly), E-P's composition
  (`get_task_production_time.py:get_task_production_time` calls
  `get_task_budget_status`), and the valuation editor's **shipped** endpoint
  (`get_task_price_scenario.py:get_task_price_scenario` calls `get_task_budget_status`).
  Intention §2.6 as folded is accurate and complete: exactly one cross-pipeline
  coupling; the price-scenario suite inherits T1's fixed-`now` discipline.
- `worked_seconds` on the division payloads derives from `total_working_seconds` at
  exactly two sites: `budget_division.py:group_steps_by_section` (section accumulator)
  and `budget_division.py:_step_result` (per-step row).

Facts carried from the orientation (verified there at `ee253cd`; **re-confirm at source
before citing in any plan or prompt**): `share_state` compares the settled column
against `allowance_seconds` (budget-division D16 — change the basis for all three
fields or re-create the `left_seconds: -100` beside `on_track` bug);
NULL/0-typical sections get the median substituted; `typical_times_statement`'s
grouping subquery has no date predicate (any per-event refetch design runs an unbounded
historical aggregate). **Corrected round 4b (projection r0, L3):** the last fact is
true of the *subquery* but incomplete about the *statement* — the outer qualifying
filter (`latest_closed_at >= cutoff`) derives its cutoff from
`datetime.now(timezone.utc)` at statement build
(`get_working_section_typical_times.py:typical_times_statement`), a wall-clock read on
the E-P and E-A request paths. Resolution in intention §1A HC-3A (round 4b) and
plan 2 C11.

## 7. Gates

### Mechanism-inventory — REQUIRED, NOT WAIVABLE (coordinator, 2026-08-20)

Charter rule 6 triggers on every mechanism this feature ships; each produces a
plausible-looking number when wrong:

| Mechanism | Rule-6 trigger |
|---|---|
| M1 §3.1–§3.2 | time arithmetic; a concurrency-averaged share; a window rule with an anchor (`min(entered_at)`) and a buffer (1 day) whose sufficiency is asserted |
| M1 §3.3 | a numeric parity bound (≤ 1 s per credited user) asserted as a contract, with a rounding-locus argument claimed to be the only drift source |
| M1 §3.4 | a stated cost ceiling on a 50-task batch endpoint |
| M2 §4.1 / HC-5 / HC-3 | one-basis propagation across **composed** service calls; `now` injected once per request; a pre-registered planner decision on a SQL aggregate |
| D7 / §6 | disowning-event semantics — a monotonicity-exception family the frontend builds smoothing on |
| §9 T1–T8 | every named test guards a silent failure; T5 carries a capture-sequencing rule that makes it vacuous if violated |

**Standing doctrine carried from the last gate:** the intention's own "what to attack"
line (§11's closing nominations) is a hypothesis by its author, never a scope — the
prompt forbids it and mandates uniform depth, including over sections that read as
prose. Last time, every defect worth a round was in a mechanism nobody had flagged.

**Exit condition:** every silent-failure mechanism has a contract-grade definition **in
the intention**, added as lettered sections so no existing citation renumbers, with a
round-4 changelog entry. The implementation-planner starts on `PASS` and nothing else.

**Gate result, 2026-08-20: PASSED** (session verdict `OWNER_DECISIONS_PENDING`; D8–D9
ratified and folded the same day, round 4a). All nine mechanisms plus two the sweep
surfaced unprompted (HC-1A ORM-persistence, HC-3A injection-site) left with
contract-grade definitions. See the §3 tracker row for the full consumption record.

**Calibration outcome — the seal, opened at the fold.** Three hypotheses were sealed in
`prompts/coordinator/2026-08-20_inventory_calibration_seal.md` before the prompt was
authored, with an honest contamination statement (the prompt's M-3/M-5 scope rows named
H1's and H2's territory; none of the specific defects; H3's territory not at all):

- **H1 (composition/`now`-threading)** — found and exceeded: the sweep produced the
  per-caller declaration table, the `ServiceContext` constraint, and the
  price-scenario clock regression the seal had not named.
- **H2 (the bound's denominator)** — found and the seal's own arithmetic corrected: the
  sealed hypothesis said a multi-user step could legitimately drift ~2 s under the
  per-user clause; the sweep showed the per-user denominator is **impossible** (one
  open record per step, by unique index) and settled rounds once across users, so the
  true bound is ≤ 1 s per step. The gate out-derived its own calibration probe.
- **H3 (§8's three-vs-four node count)** — **missed by the sweep**, which added a fifth
  node to that very list without catching the count. Fixed at the fold as a coordinator
  finding. Lesson, consistent with five prior pipelines: enumeration/count defects
  survive even a sweep explicitly instructed to treat counted sentences as checklists —
  the *coordinator's* consumption pass must re-count every counted sentence in a
  delta, every round.

### Projection — pre-declared, now instantiated per phase

REQUIRED for any phase implementing M1 (the live share, the window) or the M2 seam (the
shared loader, `_build_evaluated_status`, the division-calling services). Waivable, with
a recorded one-line justification, only for phases that ship documentation alone.

Instantiated against the plan set (2026-08-20): **plans 1, 2 and 3 REQUIRED** (plan 3
is a money/percent derivation — rule-6 by name); **plan 4 WAIVED** (documentation
only, no mechanism; waiver recorded in its §3 tracker row).

### Review

**Perimeter checks consult §7's *Recognized external commit streams* first.** Two owner
streams commit into this repo while we run; files on those lists are foreign-but-expected,
everything else outside a session's declared perimeter is still an automatic finding. A
golden JSON moved by a cap commit is an **escalation**, not an attribution.


**Full rounds, not the light MVP round.** The MVP calibration does not buy a cheap
review here: almost everything this feature ships is rule-6 surface (same finding as the
valuation editor, and truer here — there is no route/serializer scaffolding to discount).

### Closeout obligations — the frontend handoff (tracked here so they cannot scatter)

This pipeline writes backend code only, but it owes a **shipped promise** to the
frontend. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md`
§4 states that *this pipeline's own dated handoff* signals the retirement of the
frontend's interim verdict-suppression flag — they built it behind one removable flag
specifically because we promised to signal its removal.

| # | Obligation | Origin |
|---|---|---|
| 1 | **The go-live statement that retires the frontend's interim verdict-suppression gate.** The single binding promise of this pipeline; a closeout handoff without it is incomplete. | share_state handoff §4; intention §5.4 |
| 2 | **New dated handoff, never an edit.** The 2026-08-19 document's §2 correction and §3 warning do not expire — only its §1 does. Amend by reference. | frontend convention; orientation §4 |
| 3 | The correction owed on the 2026-08-18 "Live time" section: client ticking is superseded by server truth; smoothing from time-of-receipt remains legitimate. | intention §5.4 |
| 4 | Answers to the frontend's four open questions (feasibility/cost §3.4; all-fields-together §4.1; settled-consumers audit §2.5; the determinism test HC-3/T1). | intention §5.4, §11 |
| 5 | **The decrease semantics, explicitly — three modes, per-event rules in intention §6A C** *(corrected round 4a; this row originally said "exactly two ways")*: the ≤ 1 s rounding sense (§3.3A A); the D7 disowning events per §6A A (mark-inaccurate on any record of the step, and step removal — record deletion is NOT a shipped capability and is not named to the client), dropping by the whole disowned share at once, deliberately; and the D8 settlement window (§3.3A C.1), a dip-and-recover at clock-out. **Client smoothing must snap down to the served value, never clamp**; a drop-then-return within seconds is the settlement window and is rendered as served. | intention §5.4, §6A, D7, D8 |
| 6 | Graph delta: the item-economics projection node descriptions currently asserting settled-only seconds, plus `reads_from` edges to the step-state-record table node as the vocabulary allows. (The intention names four node slugs; the delta is recorded at closeout in one batched apply.) | intention §8 |
| 7 | **The approval baseline is a published reference point.** `narrow_typical_work_times` D23 regenerates two goldens keys-only on *this* pipeline's post-approval tree, so the closeout gate commit must state the tree it approves at and the suite baseline measured there (count **and** enumerated failure-ID set). A successor pipeline cannot diff against a baseline we never wrote down. | owner note 2026-08-20 |

### Published approval baselines (closeout obligation 7)

A successor pipeline cannot diff against a baseline we never wrote down.
`narrow_typical_work_times` D23 regenerates the production-time and budget-allocations
goldens keys-only on **this pipeline's post-approval tree**, so each phase approval
publishes the tree it approves at and the suite measured there.

**Schema amended 2026-08-21 (re-review r3, P5). A baseline is published as
`failure-ID set + tree identity + database identity`, with the count explicitly
subordinate.** Phases 1 and 2 were published as a count against a bare SHA, which omits
two things that determine what the count means: (i) **which database** it ran on — every
measurement in this pipeline was taken against the *development* database, not
`app_test` (§6), and a count taken against a mutable database shared with manual work is
not reproducible by a successor; and (ii) **whether the tree was dirty**, which from
2026-08-21 it is, by +17 collected tests from recognized stream 3. The **failure-ID set is
the durable half** — stable across 12+ runs and `comm`-diffed empty in both directions at
every stamp of every phase — and it is what a successor should diff against. The count is
context, not contract.

| Phase | Approved | Tree | Suite (coordinator-measured on that tree) | Failure-ID set |
|---|---|---|---|---|
| 1 | 2026-08-20 | `d21fe9e` | 26 failed / 2459 passed / 1 deselected | §6's enumeration, unchanged |
| **3** | **2026-08-21** | **`808eead`** + dirty (recognized stream 3) — `app/` diff digest recorded in `plans/plan_3.md` §7 | **26 failed / 2515 passed / 1 deselected**, of which **+28 passed is stream 3, attributed test-by-test** (its phase-clean equivalent is fix r2's `26 / 2487 / 1` at `874f02d`) | **§6's enumeration, unchanged — `comm`-diffed empty in BOTH directions by the coordinator at the gate** |
| **2** | **2026-08-21** | **`efd6b99`** (approval gate commit follows it) | **26 failed / 2479 passed / 1 deselected** | **§6's enumeration, unchanged — `comm`-diffed empty in both directions** |

**The enumerated failure-ID set in §6 has not changed across either approval.** The pass
count moved by phase test additions (+23 phase 1, +18 phase 2) and by the cap stream's own
tests (+2, landed under fix r2). Compare against the **ID set**, never the count.

### Recognized external commit streams (owner note, 2026-08-20; **third stream added 2026-08-21**)

**Three** owner streams run alongside this pipeline. All are **foreign-but-expected**:
a reviewer's `git diff` perimeter check attributes files below to their stream instead of
raising an automatic finding. Anything *outside* these lists is still a finding.

**3. Shopify infra — owner work in progress, and the first stream that is UNCOMMITTED**
(owner confirmed 2026-08-21). Perimeter:

- `app/beyo_manager/services/infra/shopify/product_sync_client.py`
- `app/beyo_manager/services/infra/shopify/shop_client.py`
- `app/scripts/shopify/` (untracked: `__init__.py`, `fields.py`, `backfill_from_shopify.py`)
- `app/tests/unit/scripts/test_backfill_from_shopify_fields.py` (untracked)
- **`app/tests/unit/services/infra/shopify/`** — an **existing, tracked** test file
  (`test_product_sync_client.py`) is edited by this stream (added at re-review r3, N9)
- **`.archgraph/architecture.yml` and `.archgraph/.internal/`** — this stream writes
  **tool-recorded state**: an uncommitted node `command-shopify-backfill-expected-sold-price`
  (`origin: ai_inferred`, confidence `0.9`) plus a `calls` edge, with evidence spans into
  `app/scripts/shopify/`. No session in this pipeline has called the graph (added at
  re-review r3, N9).

**⚠ The perimeter above was under-declared twice in one day, and the schema is the reason.**
The charter requires a *handoff's* write perimeter to cover "documents, code, and
tool-recorded state"; §7's **stream** perimeters were being written as code-only, so they
under-declare by construction. **Stream perimeters follow the handoff schema.** A stream
perimeter is also a **live claim, not a one-time note** — this one moved twice during a
single review round — so each entry carries the date it was measured.

**⚠ This stream ADDS TESTS, so the baseline moves under you — measured, not assumed.**
That untracked test file collects **17 tests** (10 test functions, the rest
parametrizations; `pytest --collect-only`, 2026-08-21). Any L4 run taken while it is
present therefore reports **+17 collected** *(measured 2026-08-21 ~10:00; **stale by
~13:00 — see the box below**)* against the cited `26 / 2487 / 1` stamp
*before* anything about this phase is considered. A run that reads `2504 passed` is not a
regression and not an anomaly — it is this stream. Re-measure and **diff the failing-ID
set**; the count alone will mislead every reader who does not know this line exists.

> **THE `+17` WENT STALE WITHIN THREE HOURS — measured at the phase-3 approval gate.**
> That figure was written **specifically to stop a later round misreading a count**, and
> it became wrong faster than any other number in this pipeline. At the gate the suite read
> **26 / 2515 / 1**, i.e. **+28** over the `2487` stamp, not `+17`. Attributed exactly, to
> the test:
>
> | source | then | at the gate | delta |
> |---|---|---|---|
> | `tests/unit/scripts/test_backfill_from_shopify_fields.py` (untracked, all new) | 17 | **22** | +22 |
> | `tests/unit/services/infra/shopify/test_product_sync_client.py` (tracked, edited) | 6 committed | **12** | +6 (6 test functions added, 0 removed) |
> | **total foreign** | | | **+28 — the whole delta** |
>
> Nothing of phase 3's is in that number. **The lesson is the one this pipeline earned
> three times over and then demonstrated on itself: a count describing a live stream is a
> claim with a shelf life, and dating it is not optional.** The instrument that did not
> move is the failing-ID set — 26, `comm`-diffed empty in both directions against the
> enumeration above, exactly as at every prior stamp.

**NARROWED 2026-08-21 (re-review r3, N9) — the sentence above originally continued
"…which is unaffected by additions that pass". That is now too strong.** It was true of the
stream as first observed (a new untracked test file, additive only). The stream has since
edited an **existing tracked test file**, and an edit to an existing test **can move the
failing-ID set in either direction** — while the enumerated 26 already contains a Shopify
row and one of the two named flaky tests is a Shopify integration test. Binding: **an
unchanged ID set is not self-evident while this stream is uncommitted; attribute it.**
Three candidate causes for any movement — this stream, the flake, a real regression — and
only a per-ID diff separates them.

Why this one needs different handling from streams 1 and 2: **it lives in the working
tree, not in git history.** A committed stream is visible to `git log` and excluded from a
measurement by choosing a tree; an uncommitted one is **inside every test run while being
invisible to every commit-based check**. Binding consequences:

- **Dating it is still possible, and was done.** Fix r2's declared stamp digest
  `b50bda39…` matches the *committed-only* `app/` diff, while the `app/` diff *including*
  this stream hashes `2d7604fe…` — proving the stream appeared **after** fix r2's stamp,
  so that stamp is clean of it. This is what the dirty-tree half of the charter's
  tree-identity scheme is for; use it the same way next time rather than guessing.
- **The baseline overlaps this stream's surface.** The enumerated 26 contains
  `test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`,
  and one of the two named flaky tests is
  `test_process_shopify_products_integration.py::test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task`.
  A count that moves has **three** candidate causes here — this stream, the flake, a real
  regression — so **capture the failing-ID set and attribute; never conclude from a count.**
- **The phase-3 approval gate must state which it measured.** Its baseline is published
  for `narrow_typical_work_times` D23, so the gate records the tree identity *including*
  the dirty digest, or is measured on a tree where this stream is committed or absent.
  Prefer L1/L2 evidence for rounds that do not need L4 at all.

**1. Production budget cap — code, parallel, disjoint perimeter.** Commits prefixed
`CHECKPOINT (not approved): production budget cap`. Its perimeter:

- `domain/item_economics/calculator.py`
- `domain/item_economics/price_scenario.py`
- `services/queries/item_economics/get_task_price_scenario.py` (serializer seam)
- those files' test files
- one new dated frontend handoff

Standing facts about it, so no round re-litigates them:

- It bumps `CALCULATION_VERSION` 1 → 2 **deliberately, and this does not contradict this
  intention's "CALCULATION_VERSION is not bumped" clause** — that clause says the
  live-clock change does not *warrant* a bump, which remains true. Not a finding.
- It **must not** move this pipeline's three golden JSONs or any file in our perimeter,
  and the cap session runs our golden test as its own tripwire. **If any round finds a
  golden changed by a cap commit, that is a real escalation to the owner — not noise.**
- **The suite baseline shifts under us:** the cap adds tests. **A multi-hour mutation
  sweep is not a round** — a foreign commit can land *inside* one, so every ledger row
  records the tree it was measured at and a sweep spanning a foreign commit is re-based,
  not annotated (§5, earned at review r3 S5). Every round re-measures the
  baseline on the tree it actually runs on and diffs the *enumerated failure-ID set*
  (§6), which is the stable comparison basis; raw pass counts are not carried between
  rounds and never between streams. This is already the standing rule here — the cap
  stream makes it load-bearing rather than merely prudent.
- `get_task_price_scenario.py` sits in **both** perimeters in different roles: the cap
  edits its serializer seam; plan 2 C10 only *reads* it and measures its suite. A change
  there authored by us is still a finding.

**2. `narrow_typical_work_times` — documents only, downstream of us.** A planning folder
(`docs/architecture/under_construction/implementation/narrow_typical_work_times/planning/`,
intention + owner decisions, RESOLVED). It makes typicals item-aware across the four
consumers of `typical_times_statement`. **Its D23 explicitly serializes it behind this
pipeline**: it starts only once our phases touching the shared files are APPROVED, and it
regenerates the production-time and budget-allocations goldens keys-only on *our*
post-approval baseline. **Do not read it for context** — our intention and plans are
unchanged by it. Consequence for us: our closeout gate commit is the reference point the
next pipeline builds on, so it is recorded as closeout obligation 7.

### Commits

Checkpoint commits at every `IMPLEMENTED` under the owner's standing authorization;
approval-gate commit at each phase close; the gate itself closes with an archive move +
commit per the closeout ritual.
