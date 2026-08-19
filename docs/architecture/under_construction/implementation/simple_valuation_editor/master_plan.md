# Master plan — simple_valuation_editor

```
state: PRE-PLAN — intention RESOLVED, mechanism-inventory gate OPEN
date: 2026-08-19
phases: not yet defined (implementation-planner runs after the inventory gate)
```

## 1. Mission

Ship **one read-only endpoint** — `GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario` —
that hands the "Expected sold price" screen the closed set of constants it needs to
project the consequences of a price live, at every frame of a slider drag, without a
network round trip.

The item-economics domain already owns the price → budget → allowance function as pure,
no-I/O code. This pipeline publishes the function's **inputs** instead of one evaluated
output at a time. It persists nothing, changes no existing payload, and is deleted by
removing what it added.

Authorities: `planning/intention.md` (RESOLVED, round 2), `planning/owner_decisions.md`
(D1–D7, ledger empty).

## 2. Folder layout

Charter tables: `planning/` (intention, owner decisions), `plans/`, `prompts/<role>/`,
`handoffs/<role>/`, `archive/plan_<n>/`. State is positional — closed plans move to
`archive/` **and** their own `state:` line is corrected at closeout (carried from
`simple_production_budget_division`, where a plan sat in `plans/` reading `PROMPT_READY`
after approval, and from `inline_valuation_versioning`, where the correction was applied).

`prompts/coordinator/` holds standing coordinator documents — never handed to a session.

**One extension to the archive partition, recorded because it deviates from the charter's
`archive/plan_<n>/` scheme.** The mechanism-inventory ran *before* any phase existed, so
its spent prompt, consumed handoff and opened seal have no `plan_<n>` to belong to. They
are archived under **`archive/gate_inventory/`**. The rule the scheme actually encodes —
state is positional, a consumed row never sits in a live table — is preserved; only the
partition key changes, because the partition key is the phase and this work predates
phases. Historical references to `prompts/reviewer/…` and `handoffs/reviewer/…` for these
three files resolve there, and are not rewritten.

## 3. Phase registry & tracker

Phases are **not yet defined**. The implementation-planner authors them from the
intention *after* the mechanism-inventory gate closes (§7). Until then this table has one
row, and it is a gate row, not a phase row.

| Phase | Scope | State | Date | Actor | Note |
|---|---|---|---|---|---|
| — | Mechanism-inventory gate over intention §3–§9 (M1, M1b, M2, M2b, M3, M4, M5, M6) | **PASSED** | 2026-08-19 | Opus 5 (inventory) + coordinator (fold) | Eight mechanisms swept, twelve lettered sections added, nothing renumbered. Three owner cards raised and all three closed (D8, D9, D10). Coordinator verified the load-bearing claims independently rather than consuming them: break-even `1 211 335` re-derived (the intention's `1 211 364` solved a real-arithmetic equation instead of §4.1's least-integer search — off by 29), `ival` prefix, `usable = not None and > 0` at `budget_division.py:326`, and the commit path ignoring a request price when no valuation row exists (`:212-213`). **One defect found in the delta and corrected at the fold**: §9A.1's "can return only nine of the twelve" is ten, contradicted by its own B1–B10 table and by §12A. Ledger empty; intention now `RESOLVED and PLAN-READY (round 4)`. |
| — | Implementation planning | **DONE** | 2026-08-19 | coordinator | Two phases, split at the domain/service boundary the codebase already draws (`budget_division.py` / `calculator.py` are pure; `services/queries/` does I/O). Criteria built from §12 + §12A's eleven obligations. **HC-2 extended to a fourth artifact** — one new pure domain module — recorded in plan_1 §2 under the HC-1a precedent, no new owner card. |
| 1 | The pure price mechanisms: `round_half_even`, the collapsed form, the break-even and infeasibility searches, the step helpers, the band. No I/O. | **PROMPT_READY** | 2026-08-19 | Opus 5 (projection r0) + coordinator (fold) | Projection returned `AMENDMENTS_REQUIRED`, **0 owner cards**, 17 ledger rows — 4 upstream, 11 plan amendments, 4 written delegations — **all routed before the implement prompt compiled**. Three named mutations (C7, C17, C10) proved unable to fail and were replaced; `infeasible_at_or_below_minor` for the mockup is **29**, not the `0` §4.2A claimed. Design survived intact: M1's form faithful to the shipped calculator, all four literals exact, the bound holds on every shape. Coordinator re-derived each load-bearing claim, including confirming the unflushed-ORM `is_deleted = None` trap empirically. |
| 2 | The read model, the route, the mirror: M3, M4, M6, the status table, `can_commit`, HC-2a's four artifacts. | **NOT_STARTED** — blocked on phase 1 APPROVED | — | — | Plan at `plans/plan_2.md`, 15 criteria; amended at phase 1 closeout with its review lessons. |

## 4. Naming registry

Reserved before any code exists, so two sessions cannot pick two names for one thing.

| Thing | Name | Home |
|---|---|---|
| Query service | `get_task_price_scenario` | `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` |
| Route | `GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario` | `app/beyo_manager/routers/api_v1/item_economics.py` |
| Serializer | `serialize_task_price_scenario` | `app/beyo_manager/domain/item_economics/serializers.py` |
| Slider-band rule label | `break_even_band_v1` | `domain.rule` in the payload (HC-6) |
| Typical method label | `median_completed_section_totals` | existing `TYPICAL_METHOD` (`budget_division.py:16`) — **reused, never re-declared** |

Binding constraints on names and copies:

- **`basis` is taken.** It means `production_cost_basis_version` in this domain. No new
  meaning for it (intention §8).
- **One-copy rule** (earned `simple_production_budget_division` r1 lesson 4). The typical
  statement, the participating-section rule and the median fallback are **imported** from
  `budget_division.py` / `get_working_section_typical_times.py`, never reimplemented.
  HC-2 forbids *changing* those modules; it does not forbid calling them. A second copy
  of a registered mechanism is a review finding.
- **`serialize_user_light`'s three-key shape is re-declared, not imported** (intention §6,
  a deliberate decision). Both sites carry a comment pointing at the other so a later
  consolidation finds both. This is the one sanctioned duplication in the pipeline; any
  other requires a decision.
- The `round_half_even(a, b)` integer helper is **one** function. If it appears in both
  the query service and a domain module, that is a finding, not a convenience.

## 5. Standing rules

Charter rules 1–11½ apply in full, plus every rule earned by the three prior pipelines.
The ones that bite hardest on *this* feature, restated because they are load-bearing here
rather than merely inherited:

- **Rule 5 — no adjectives for mechanisms.** "A nice step", "near", "sensible band" are
  not specifications. Any surviving adjective in a mechanism is a gate failure, not a
  style note. This rule is the reason the inventory gate is open (§7).
- **Rule 2 — enumerate, never sample**, with its companion: each row's fixture makes its
  own predicate the ONLY reason its outcome holds. The status matrix and the M3 fallback
  rows are exactly where a shared-cause fixture would pass for the wrong reason.
- **Rule 3 — invariants proven on the production object type.** The M1 fidelity test holds
  real `CostModelTerm` ORM instances; the shape guard inside `calculate_term_amount` is
  part of what is being proven (intention §12.7).
- **Rule 6 — effort by silent-failure risk.** This whole feature is rule-6 surface: money
  arithmetic, quantization, a rounding-mode contract, a monotonicity argument, a search,
  and an ordering-free statistic. Nothing here fails loudly.
- **Rule 11 — named mutations name their site** (file, definition-vs-call-site). Intention
  §12.2 already names one; the planner enumerates the rest.
- **Precedence-disagreement rule** — a fixture pinning a ranked rule makes every level of
  it disagree.
- **No-weaker-assertions rule** — exact literals; absence asserted as absence, never as
  zero (intention §9.1 depends on this distinction being testable).
- **Perimeter-by-path rule** — every handoff declares its full write perimeter by path,
  generated from `git`, never retyped.
- **Verification-scope rule** (earned `inline_valuation_versioning`) — a claim that
  something appears *nowhere* is only as good as the directory the search ran in. State
  the root; run "appears nowhere" searches from the **repository root**. This cost an
  implementer round last pipeline.
- **Widen the allowlist, never remove the filter** — if the docs-accuracy guard's coverage
  is extended, add extensions. Removing its extension filter makes it crash on a binary
  `.docx` in its own root and go red forever for the wrong reason.
- **Prove each root alone** — a combined probe proves *something* caught it; single-target
  probes prove *each target*.
- **MVP calibration** (owner-raised 2026-08-16) — mutation ledgers with observed-red are
  mandatory for rule-6 mechanisms and tenant boundaries; routes, serializers, role
  admission and envelopes get ordinary tests with no ledger row. **Note the consequence
  for this pipeline: the calibration does not buy a cheap review here**, because almost
  everything this feature ships is rule-6.

### Rules earned before the first line of code

- **A worked example is a test, not an illustration** (coordinator, 2026-08-19). An
  intention that reproduces a mockup's numbers from its own rule is claiming the rule is a
  rule and not a fit. That claim is checkable by arithmetic at inventory time, for free,
  before an implementer spends a round on it. Do the arithmetic. (Earned in §7's gate
  assessment; it then found six of ten worked examples not following their own rule.)
- **A named mutation is not accepted until someone has computed both sides of it**
  (projection r0, 2026-08-19). Charter rule 11 says a named mutation must turn a test red.
  It does not say who checks that the mutation *can*. Three of this phase's mutations were
  proved inert — one could only weaken a `<=` bound, one asserted the property the mutation
  preserves by construction, one named a mutation of a circular definition that no
  implementer could write. All three read perfectly well in prose. **The check is cheap and
  mechanical: state the value under the contract and the value under the mutation, and
  confirm they differ.** A mutation whose two sides were never computed is a claim, not a
  guard.
- **Corollary — inert mutations are inherited, not invented.** All three came from §12A,
  faithfully transcribed into the plan. A wrong criterion propagates downstream unchanged
  because each layer is copying, not re-deriving. Corrections therefore go **upstream first**
  (home-artifact rule), or the next phase plan copies the same defect from the same source.

## 6. Environment

- Working directory `backend/app/`; infra `make dev-up`; tests
  `PYTHONPATH=. pytest -m 'not e2e'`.
- **Start baseline: 2320 passed / 26 failed / 1 deselected** (2347 collected), head
  `f1c0ebb`, branch `main`. **Measured by the coordinator, 2026-08-19, on a clean tree** —
  a full run of `PYTHONPATH=. pytest -m 'not e2e'` completed in 118.54s. The figure is
  verified, not carried over from the previous pipeline's closeout, and the 26 failure IDs
  are byte-identical to that closeout set.
- **This phase ADDS routes.** The route-mirror counts move 25 → 26 (HC-2a). State the
  before and after counts in every handoff.
- **SUITE INSTABILITY — measured at ±1 in BOTH directions.** On unchanged code the failure
  count has been observed at **25, 26 and 27** across separate full runs, with byte-identical
  ID sets and no duplicates. The drifting test is unidentified and inherited, not introduced
  by any of these pipelines.
  **Binding consequence: a single run is not evidence.** A run disagreeing with the
  baseline count is repeated and its **ID set** diffed before any conclusion is drawn. Only
  an ID added or removed across repeated runs is a finding. A count alone — higher or lower
  — is noise.
- The suite leaves ~24 `task_steps` and ~40 `step_state_records` behind per full run, from
  tests outside these pipelines. Row-count drift is never evidence of a code change.
- **Nothing in this pipeline writes to the database.** A handoff reporting new rows from
  this feature's own tests is reporting a defect, not residue.

## 7. Gates

### Mechanism-inventory — REQUIRED, NOT WAIVED (coordinator, 2026-08-19)

The two prior pipelines waived this gate and were right to: one was a comparison with two
inputs, the other a composition of two already-contracted mechanisms. **This one is the
case the gate was built for.** Charter rule 6 triggers on every mechanism the feature
ships:

| Mechanism | Rule-6 trigger |
|---|---|
| M1 §3.1 | money arithmetic, quantization, an explicit rounding-mode contract that must hold in **two languages** (Python server, BigInt client) |
| M1 §3.2 | a numeric error bound asserted as a contract |
| M2 §4.1 | a search whose correctness rests on a monotonicity argument |
| M3 §5.2 | a statistic with a substitution fallback that must agree with a second screen |
| M5 §7.2 | a derived band with a step rule |

A silent-failure mechanism without a contract-grade definition is a gate failure, and
this feature is nothing but silent-failure mechanisms: every one of them produces a number
that looks plausible when it is wrong.

**Gate result, 2026-08-19: PASSED.** All eight mechanisms left with contract-grade
definitions; three owner cards raised and closed (D8–D10); ledger empty.

**Calibration outcome — the seal, opened.** Before authoring the prompt the coordinator
found three defects by arithmetic and sealed them in
`prompts/coordinator/2026-08-19_inventory_calibration_seal.md`, unopened by the session
(mtime confirmed). All three were found independently by the sweep, two of them deeper
than the seal had them: M5's band (the seal had three contradictions; the sweep added that
no step ladder produces 15 000 and that the `min_minor` floor sits off-grid),
`infeasible_at_or_below_minor` undefined, and the §12.6 status-matrix miscount — where the
sweep went past the seal entirely and found that the resolver cannot produce `ok` or
`infeasible` at all, which is what turned a test-criterion defect into owner card 1 and a
screen that would have been blank for every first pricing.

Two conclusions worth keeping:

- **The seal's method hint was the only assistance given**, and the sweep found findings 2
  and 3 without one. The gate is not a rubber stamp of the coordinator's own reading.
- **The document's self-assessment pointed away from its weakest section**, exactly as the
  seal predicted. §14's closing line nominated M1's error bound and M2's monotonicity;
  both survived. Every defect worth a round was in a mechanism nobody flagged. **Standing
  consequence: an intention's own "what to attack" line is a hypothesis by the author, and
  a prompt must forbid it as a scope.** That instruction is now doctrine for this project.

**Not everything the sweep produced was right.** §9A.1's "the resolver can return only
nine of the twelve" is ten, contradicted by its own B1–B10 table and by §12A's correct
"eleven non-`ok` values". Found by the coordinator at the fold and corrected in place with
its reason left visible. Enumeration is one of the two clusters the graph-review evidence
identifies as failure-prone, and this one sat *inside a correction of a miscount*.

**Exit condition (met):** every mechanism in the table has a contract-grade definition **in
the intention**, added as lettered sections (§7A style) so no existing citation is
renumbered, with a changelog entry.

### Projection — REQUIRED (pre-declared)

Charter rule 6 triggers hard; the trigger list above is the same list. The projection gate
is **not** waivable for any phase implementing M1, M2 or M5. It may be waived, with a
recorded one-line justification, for a phase that ships only the route mount and role
admission.

*If an implementer finds an uncontracted mechanism, that is a STOP, not a judgement call.*

### Review

**Full rounds, not the light MVP round.** The MVP calibration's cheap first review is
earned by a projection having walked the mechanisms against real data *and* by most of the
surface being non-rule-6. The second condition fails here.

### Closeout obligations — the frontend handoff (tracked here so they cannot scatter)

**This pipeline writes backend code only.** No frontend file is in any perimeter. But the
feature's value is realised by a screen this repo does not contain, and the intention
places four obligations on the closeout handoff in four different sections. They are
collected here because an obligation recorded only at its point of origin is an obligation
that gets dropped at the gate.

| # | Obligation | Origin |
|---|---|---|
| 1 | **The M1 arithmetic, specified for a second language.** Per operation: integer arithmetic on both sides, BigInt, no float, never a language `round()` (half-away-from-zero). The client executes this function every frame; an ambiguity here makes two screens disagree at the chip's flip point. | §3.1, HC-5 |
| 2 | **Name the accepted divergence.** On a task carrying excluded-step time this screen's `AT PRICE` exceeds the production-time screen's distributable total by exactly `charged_seconds`. D5 ratified it; an accepted inconsistency nobody wrote down is indistinguishable from an undetected one. | §5.4, D5 |
| 3 | **The Save flow**: Save is `POST …/evaluations/commit`; `can_commit: false` **disables** the button; reconciling the commit response against the displayed figures is mandatory, not advisory. | §11, D4 |
| 4 | **Amend §8.4 of `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`** — its *display prohibition* only. Its contract (a valuation is per item, never per unit) is unchanged and stays. | D1 |
| 5 | **Amend §6's status→treatment table in the same document.** D8 publishes `model`/`anchors`/`domain` under `item_unvalued` and `item_missing_expected_price`, where that table says the numerics are `null`. A live consumer reads it. HC-3 is untouched — this endpoint is ADMIN/MANAGER only. | D8, §9A.1 |
| 6 | **State that Save cannot create a valuation row.** With no current valuation the commit path refuses regardless of the price in the body, so `can_commit` is `false` and the purchase price must be set first through `PUT /items/{id}/valuation`. This is the written form of D9's precondition. | D9, §9A.2 |

Obligations 4 and 5 edit a published document and therefore need an enumerated file
perimeter of their own when the closeout phase is planned. Neither is a licence to revise
that handoff generally.

**Obligation 6 is different in kind and must not be dropped as boilerplate.** D9 —
Save stays one call — is the only decision in this pipeline whose soundness rests on
something outside this repository: a frontend flow that sets the purchase price, and
therefore creates the valuation row, before the price screen is reachable. The backend
cannot enforce it and will not fail loudly if it stops holding; the screen will simply
save nothing, every press. Writing the precondition into the handoff is what converts an
assumption about another codebase into a contract. Unwritten, it is a defect waiting for
the first optimisation that skips the prompt.

### Commits

Checkpoint commits at every `IMPLEMENTED`, prefixed `CHECKPOINT (not approved):`, under
the owner's standing authorization. The phase is committed again at its approval gate.
Checkpoints are never squashed.
