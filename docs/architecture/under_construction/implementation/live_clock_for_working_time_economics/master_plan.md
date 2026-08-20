# Master plan — live_clock_for_working_time_economics

```
state: PRE-PLAN. Intention RESOLVED (round 3); mechanism-inventory gate PROMPT_READY.
       No phases exist yet — the implementation-planner runs only after the gate PASSES.
date: 2026-08-20
coordinator: Claude Fable 5 (incoming 2026-08-20, per ORIENTATION_for_new_coordinator_20260820.md)
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

Authorities: `planning/intention.md` (RESOLVED, round 3, 2026-08-20 — **not plan-ready
until the mechanism-inventory gate passes**), `planning/owner_decisions.md` (D1–D7,
ledger empty). Provenance: `planning/coordinator_review_of_intention_20260819.md`
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

No phases exist. Phase rows appear here when the implementation-planner produces them,
newest state first, superseded rows kept as provenance.

| Phase | Scope | State | Date | Actor | Note |
|---|---|---|---|---|---|
| — | Mechanism-inventory gate over the intention's mechanisms (see §7 trigger table) | **PROMPT_READY** | 2026-08-20 | coordinator | Prompt at `prompts/reviewer/2026-08-20_inventory_mechanism_inventory.md`. Calibration seal written and sealed at `prompts/coordinator/2026-08-20_inventory_calibration_seal.md` **before** the prompt was authored; unopened by any session until the gate handoff is consumed. Gate is REQUIRED, NOT WAIVABLE (§7). |

## 4. Naming registry

Reserved before any code exists, so two sessions cannot pick two names for one thing.
**Nothing is minted yet** — this feature adds no route, no field, no table (HC-1, HC-4),
so the only names to reserve are internal seams, and those are the planner's to register
here before any implementer session.

Binding constraints, in force now:

- **One crediting rule, one home (HC-2).** The live share is computed by
  `concurrency.py:averaged_seconds_by_record` through
  `averaged_time.py:compute_record_contributions` — **imported, never reimplemented,
  never forked**. A second averaging rule, or a `now − entered_at` elapsed, anywhere in
  this feature is a defect by definition, not a simplification.
- **The shared loader** (intention §4.1 — takes the step set, the session and `now`,
  returns `{step_id: live_worked_seconds}`) is the planner's to name; the name is
  registered in this section before the first implement prompt compiles.
- **Pre-registered planner decision (intention §4.1, review finding 4):** the fate of
  the SQL aggregate in `get_task_budget_status.py:_build_evaluated_status`
  (`func.coalesce(func.sum(TaskStep.total_working_seconds), 0)`) — replace with a
  per-step fold over the loader's output, or keep it for the settled term and add the
  loader's open shares. **One is picked and recorded in this section plus the owning
  phase plan before any implementer session.** (The named-medium rule: this master plan
  is the record that survives closeout.)
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

## 6. Environment

- Working directory `backend/app/`; tests `PYTHONPATH=. pytest -m 'not e2e'`. The bare
  `make test` form fails collection (`ModuleNotFoundError: beyo_manager`) in some shells.
- **Start baseline, measured by this coordinator 2026-08-20 on a clean tree at
  `a0aaacc`: 26 failed / 2433 passed / 1 deselected.** Matches the outgoing
  coordinator's figure at `ee253cd` (the three intervening commits are doc-only). The
  26 are inherited and pre-existing; none is in `item_economics`.
- **⚠ Suite instability — at least TWO named flaky tests** (named after 21 measured runs,
  `simple_valuation_editor/master_plan.md` §6 carries the full evidence):
  `test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
  and
  `test_process_shopify_products_integration.py::test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task`.
  Binding consequence: **a single run is not evidence** — repeat and ID-diff.
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
historical aggregate).

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

### Projection — pre-declared

REQUIRED for any phase implementing M1 (the live share, the window) or the M2 seam (the
shared loader, `_build_evaluated_status`, the division-calling services). Waivable, with
a recorded one-line justification, only for phases that ship documentation alone.

### Review

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
| 5 | **The decrease semantics, explicitly:** `worked_seconds` drops between polls in exactly two ways — the ≤ 1 s rounding sense (§3.3) and the D7 disowning events (mark-inaccurate, record/step deletion), where it drops by the whole disowned share at once, deliberately. **Client smoothing must snap down to the served value, never clamp** — a clamp keeps displaying time the workspace has explicitly disowned. | intention §5.4, §6, D7 |
| 6 | Graph delta: the item-economics projection node descriptions currently asserting settled-only seconds, plus `reads_from` edges to the step-state-record table node as the vocabulary allows. (The intention names four node slugs; the delta is recorded at closeout in one batched apply.) | intention §8 |

### Commits

Checkpoint commits at every `IMPLEMENTED` under the owner's standing authorization;
approval-gate commit at each phase close; the gate itself closes with an archive move +
commit per the closeout ritual.
