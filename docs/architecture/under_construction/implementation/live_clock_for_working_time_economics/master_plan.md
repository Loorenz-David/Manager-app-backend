# Master plan — live_clock_for_working_time_economics

```
state: IN PROGRESS. Gate PASSED; phase 1 APPROVED (`d21fe9e`); phase 2
       **CHANGES_REQUESTED** (review r3 folded; fix r4 dispatched); phases 3–4
       NOT_STARTED.
       Next: hand `prompts/implementer/2026-08-20_phase2_fix_r4.md` to an implementer.
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

Authorities: `planning/intention.md` (**RESOLVED and PLAN-READY**, rounds 4a–4e,
2026-08-20 — the gate passed and its folds are in), `planning/owner_decisions.md`
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
| 2 | The three surfaces live: the fold (N-2), E-P one-map composition, E-A batch + `today_utc()`→`ctx.now.date()`, the typicals `now` shim **+ the config-date shim (round 4e)**; C1–C12 | **CHANGES_REQUESTED** | 2026-08-20 | Opus 5 (review r3) + coordinator (fold) | **First full review of the phase. 1 blocking, 5 should-fix, 6 notes — and a second independent pass confirms the production code correct**, including a field-by-field walk of all four payloads on one fixture where every worked-derived field agrees on one number (E-P, E-B manager, E-B worker, E-A all read `2040` / `"34.00"` / `"-14.00"` / `"170.00"`). Review perimeter: exactly its one handoff file ✓, three probe files hash-verified, its temporary probe test deleted. **F-L4's sampled re-measurement came back clean:** ledger rows 3, 6 and 11 reproduce **ID-for-ID** with zero removals, so the corruption is isolated to row 4 — and the reviewer sharpened the structural argument beyond the coordinator's (`created_at` is read at **one** site and reaches no payload field; `latest_state_record` at **two**, the sort *and* `group_steps_by_section`'s `state_entered_at`, so row 4's golden attribution is impossible and row 5's is necessary). **B1, coordinator-reproduced by direct measurement:** §5.2 criteria 1 and 2 are adopted verbatim as contract and neither is discriminated — C2's only `share_state` assertion sits on a section whose `allowance_seconds` is **0**, so `over_share` holds at 2040 (live) **and** 1440 (settled): the row returns the same verdict with the whole phase reverted. **Ninth instance of the row-that-cannot-fail class, in a new shape — the degenerate term was the *allowance*, not the addend**, so a comparison-based verdict was blind where the arithmetic was fine. C4's byte-identity half never shipped (the reviewer measured that the property holds — unwritten, not unwritable). **S3, coordinator-verified at source: a delivered test expires on 2026-11-17** — it pins `closed_at` to a hard-coded date while deliberately calling the shim's wall-clock branch, so it fails on a date with nothing in the repo changing, and would add a 27th member to the enumerated ID set this pipeline publishes as the next pipeline's reference point (§7 obligation 7). S1/S2: C6 row 1 and C7 each shipped their headline and dropped every subordinate clause; S4: D7's comments absent at both substitution sites. **Systemic finding recorded against this plan:** four criteria written as headline-plus-clauses shipped headline-only, while C6's rows 2–4 — lettered, one named mutation each — shipped complete; **plan 3 is to be written in the lettered-row form throughout.** Folded now, not deferred: intention **round 4f** (§4.1A C.1 — `allowance_seconds` is non-worked-derived only while no *excluded* step holds an open record; holds today because `_apply_step_transition` closes unconditionally, so no live defect); §5 **+2 rules** (the degenerate *controlling* term; **a multi-hour sweep is not a round** — every ledger row records its tree, and a sweep spanning a foreign commit is re-based, not annotated); §7's external-stream clause gains that sentence. S5 applied in place at the fold: plan §7's fix-r2 entry now states its tree (2474 vs the delivered 2476) and row 4's seven-ID claim is struck for the measured one. Fix prompt `prompts/implementer/2026-08-20_phase2_fix_r4.md` — perimeter is the phase test file plus **exactly two** named production edits (D7's comments, N4's one token). |
| 2 | *(prior row — review r3 dispatched)* | *superseded (REVIEWING)* | 2026-08-20 | Codex (fix r2) + coordinator (consumption) | **All four blocking findings and all three should-fix closed; perimeter test-only, zero production lines** (`git show --name-only a28e9e5` touches nothing under `app/beyo_manager/`). Phase file 6 → **15 tests**. Coordinator re-measured on the post-cap tree: clean **26 / 2476 / 1**, failing-ID set `comm`-diffed empty in both directions; arithmetic reconciles (2465 + 9 fix tests + 2 cap tests). **The two mutations that were ∅ last round now bite and are isolated:** C6 `created_at` ⇒ exactly 1 added ID, C8 loop-local ⇒ exactly 2, zero removals. C6's ordering fixtures verified at source — row 2 **ties** `entered_at` so `created_at` decides, row 3 keeps them distinct and swaps it, and they are not merged, which is the part most likely to have been got wrong. **External stream:** the cap's `bb6cc43` landed underneath this fix and touched **none** of our files and **no golden** — no escalation; two of its paths (`domain/item_economics/serializers.py`, `.archgraph/architecture.yml`) are marginally wider than the owner's description, recorded not raised. **F-L4 (should-fix, routed as a review probe):** ledger row 4 claims **seven** added IDs for the C6 `created_at` mutant where the coordinator measures **one** — six are structurally impossible (the goldens hold one step per section, so no ordering field can move them) or sit in the cap's own areas, so that probe's run almost certainly overlapped the cap commit landing. **First instance of the external stream corrupting a measurement — the hazard §7 was written for, arriving in the same round.** Row 5 is unaffected and reproduces the coordinator's pre-fix measurement exactly. N5: C9 correctly names no mutant (three-point contract); N6: the 50-task fixture was removed after measuring, correctly — 50 IDs ⇒ 1 probe + 1 sweep, 51 ⇒ rejected before querying. Disposition: **review r3, full checklist — the phase's first review.** Prompt `prompts/reviewer/2026-08-20_phase2_review_r3.md`, with F-L4 as its lead probe and instructions to re-measure a sample of ledger rows. |
| 2 | *(prior row — fix r2 dispatched)* | **IMPLEMENTED** | 2026-08-20 | Codex (fix r2) | **B1–B4 and S1–S3 closed in a test-only perimeter. Final clean suite: 26 failed / 2476 passed / 1 deselected / 2 warnings; the 26-ID failure set matches master §6 in both directions. C6, C8, C9, C11, and C3 population proof rows added; all named mutation probes restored; C8's 50-task ceiling measured. Production tree and Architecture Graph unchanged. Handoff: `handoffs/implementer/2026-08-20_phase2_fix_r2_handoff.md`.** |
| 2 | *(prior row — implement r1 dispatched)* | *superseded (PROJECTED)* | 2026-08-20 | Opus 5 (projection r0) + coordinator (fold) | Verdict `AMENDMENTS_REQUIRED`, **0 owner cards, 22 ledger rows — all routed before the implement prompt**: 12 amendments applied verbatim (A1–A4, A7–A10, A12–A15), 6 written delegations recorded as **D4–D9** in `plans/plan_2.md` §6, 1 upstream fold (**U1 → intention round 4e**). Headlines: C4's invocation counter must sit on **all three** consumer bindings and its fixture needs a committed evaluation or the fold never runs; E-A's `today_utc()` mutation is inert without a `effective_from` straddle; C5's "fresh session" is unconstructible on the rollback-scoped `db_session`, and the dirty-check must precede `expire_all()`; E-A must **not** gain a `selectinload` (it would silently move `allowance_seconds` through `_governing_step`). Coordinator verified every load-bearing claim at source before applying (11 of them, listed in plan 2 §7) and **re-measured the baseline independently: 26 / 2459 / 1, failing-ID set `comm`-diffed empty in both directions** — §6 now carries both baselines (A14; plan 2 §2 and the orientation banner had both cited §6 for a figure it did not hold). **Three amendments corrected by the coordinator before entering the tree:** **F-A6** (blocking, measured) — A6's row could not fail, because `_governing_step`'s last-applied stable sort is primary and A6's own fixture pinned distinct `entered_at`; split into two measured fixtures, one per field, with the inertness of the wrong pairing measured too (**eighth** instance of the class, **second** arriving inside a correction of that class); **F-A5** — the criterion contradicted delegation D7 from the same handoff (strict indexing turns the stated divergence into a `KeyError`), re-anchored to the E-B face; **F-A11** — the widen-the-perimeter amendment enumerated 4 of 7 suites, omitting E-A's own. **U1 disposition, coordinator's call:** `_load_preview_inputs`'s `today_utc()` conversion is brought **into** phase 2 (task 4b + **C12**) rather than deferred — same construct as E-A's, and leaving one converted and one not would ship a live counterexample to HC-3A. Perimeter widened into `services/commands/item_economics/`, named explicitly. Three rules earned into §5. Implementation and validation are recorded in `plans/plan_2.md` §7 and the implementer handoff. |
| 2 | *(prior row — projection prompt compiled)* | *superseded (PROMPT_READY, projection r0)* | 2026-08-20 | coordinator | `plans/plan_2.md` refreshed against what phase 1 actually shipped (loader signature and its fails-closed guard, `ctx.now`, the goldens) and its read-first list extended to plan 1 §5/§7 and §5's nine new rules. Projection prompt at `prompts/reviewer/2026-08-20_phase2_projection_r0.md` — fresh-session inputs only; depth on the fold's **population equality**, E-P's composition and the one-map contract, E-A's batch keying and call counts, the typicals shim's inertness, C1's golden invariance through the new code path, and C9's constructibility. | `plans/plan_2.md` refreshed against what phase 1 actually shipped (loader signature and its fails-closed guard, `ctx.now`, the goldens) and its read-first list extended to plan 1 §5/§7 and §5's nine new rules. Projection prompt at `prompts/reviewer/2026-08-20_phase2_projection_r0.md` — fresh-session inputs only; depth on the fold's **population equality** (a silent divergence moves a headline without its rows), E-P's composition and the one-map contract, E-A's batch keying and call counts, the typicals shim's inertness, C1's golden invariance through the new code path, and C9's constructibility. Implement prompt compiles only after the ledger is fully routed. |
| 3 | D9: the two frozen-percent feed sites (N-4) + T13 both rows, re-commit immunity | NOT_STARTED | 2026-08-20 | — | `plans/plan_3.md`. Projection REQUIRED (money/percent derivation = rule-6). |
| 4 | Closeout handoff (six §7 obligations, headline: retire the frontend's interim flag) + the five-node graph delta | NOT_STARTED | 2026-08-20 | — | `plans/plan_4.md`. Projection **WAIVED**: documentation only, no mechanism — waiver recorded here per charter. Full review round regardless. |
| — | Mechanism-inventory gate over the intention's mechanisms (M-1…M-9, §7 trigger table) | **PASSED** | 2026-08-20 | Opus 5 (inventory) + owner (D8–D9) + coordinator (fold) | Nine mechanisms swept, 11 lettered sections added (+758/−5), nothing renumbered. Session verdict `OWNER_DECISIONS_PENDING`; both cards answered the same day (**D8** ship-and-disclose the settlement window, **D9** freeze the frozen blocks whole) and folded at round 4a → **PASS**, no second reviewer session (no card branch changed a contract, only behaviour). Coordinator verified at consumption rather than reading the ledger: perimeter matches `git diff` exactly (the one undeclared `app/` change in the tree — `items/lookup/` — is the owner's concurrent item-lookup work, excluded from every pipeline commit); **12 load-bearing claims re-verified at source** (sync-close + async-enqueue in `_step_transition_core.py`, the flag disjunction and `_BUCKET_STATE` in `averaged_time.py`, `uix_step_state_records_active`, the worker-face `percent_consumed` branch, settlement's single `int(round(Σ))` across users, the 8-member enum, `DivisionStep`, `today_utc()` in E-A's loop, `_MAX_TASK_IDS = 50`, `FALLBACK_POLL_SECONDS = 30`, `max_try = 3`); all four §3.2 worked examples re-followed. **Calibration (seal opened at the fold, §7)**: H1 and H2 found and exceeded — H2's own arithmetic corrected, the per-user denominator is *impossible*, not merely loose; **H3 missed by the sweep** (§8's three-vs-four count), fixed at the fold as a coordinator finding. T1's named mutation proved inert and rewritten as T1′ — the both-sides rule biting a fourth time, this round on the coordinator lineage's own artifact. Unilateral resolutions U1–U9 recorded in the handoff; none reopens D1–D7; ratified by the owner's round-4a acceptance. Commits `da4ebcd` (scaffolding) → `e2e7c24` (gate delta) → gate-close commit. |
| — | *(prior row — prompt compiled)* | *superseded* | 2026-08-20 | coordinator | Prompt at `prompts/reviewer/2026-08-20_inventory_mechanism_inventory.md`; calibration seal sealed pre-prompt at `prompts/coordinator/2026-08-20_inventory_calibration_seal.md`. Gate REQUIRED, NOT WAIVABLE. Both resolve under `archive/gate_inventory/` after closeout. |

## 4. Naming registry

Reserved before any code exists, so two sessions cannot pick two names for one thing.
This feature adds no route, no field, no table (HC-1, HC-4); the minted names are
internal seams only.

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
  definition-vs-call-site), run the WHOLE SUITE, record the complete observed-red ID
  set.** A `-k` or single-file run is not an observation.
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
- **Architecture graph: inherited clean** — 0 pending, 0 stale, 0 diagnostics, every node
  `human_confirmed` as of `0bab586`. Keep it that way. Two open tooling findings sit in
  `implementation/archGraph_mapping_mantainance/open/` — read them before any
  `archgraph_repair_anchors` call (one operation per call; batches fail) and before
  trusting a `conflicting-canonical-relationship` diagnostic.
- Checkpoint commits at every `IMPLEMENTED`, prefixed `CHECKPOINT (not approved):`,
  under the owner's standing authorization; never squashed. The phase is committed again
  at its approval gate.

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
2. **Narrow the mutation *set* per round, never the suite.** From review r3 onward only
   mutations whose criteria changed that round are re-measured (typically 3–4);
   confirmed measurements stand in the Review log and are cited, not re-run. Fix r2's
   full sweep is a one-time correction of B4, not the steady state.

**The one thing that does not get narrowed: every mutation run stays whole-suite.**
Scoping a probe to the phase's own test file destroys both signals the protocol exists
for — **∅ detection** (a phase-scoped run cannot show that a mutation reddened nothing
anywhere, and both of this round's blocking findings were ∅) and **removed IDs /
cross-file coupling** (C6's `latest_state_record` mutation reddened two tests *outside*
the phase file; a scoped run would have reported the opposite of the truth). xdist is the
enabler precisely because it makes keeping this rule affordable rather than tempting to
break.

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

### Recognized external commit streams (owner note, 2026-08-20)

Two owner-committed streams run alongside this pipeline. Both are **foreign-but-expected**:
a reviewer's `git diff` perimeter check attributes files below to their stream instead of
raising an automatic finding. Anything *outside* these lists is still a finding.

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
