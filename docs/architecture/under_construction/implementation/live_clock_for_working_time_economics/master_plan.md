# Master plan — live_clock_for_working_time_economics

```
state: PLANNED. Four phases (plans/plan_1..4.md), all NOT_STARTED. Next: plan 1
       projection (round 0) — REQUIRED, see §7.
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

Newest state first; superseded rows kept as provenance.

| Phase | Scope | State | Date | Actor | Note |
|---|---|---|---|---|---|
| — | Implementation planning | **DONE** | 2026-08-20 | coordinator | Four phases, split so no payload changes before its guards exist: goldens + clock boundary + loader (1) → the three surfaces (2) → D9 frozen blocks (3, needs the live basis for T13 to discriminate) → closeout handoff + graph delta (4, docs only). Strictly sequential 1→2→3→4 — plans 2 and 3 share files, and the valuation pipeline's parallel doc phase collided on a tripwire despite disjoint perimeters. The four pre-registered decisions resolved as **N-1…N-4** (§4), each grounded in source read this session (`run_service` is a pure error boundary over an already-built ctx, so the boundary is ctx construction; `ItemCostResult` stores `actual_worker_minutes` + `variance_worker_minutes`, which reconstructs the frozen denominator without touching the current evaluation). D5 satisfied: no release before plan 3 approves, all four §4.1 rows ship together. |
| 1 | Pre-change T5 goldens; `ServiceContext.now` (N-1); the loader `load_live_worked_seconds` (N-3) + its contract proven at loader level (T2/T3/T4/T10, window anchor, HC-1A) | NOT_STARTED | 2026-08-20 | — | `plans/plan_1.md`. Payloads byte-frozen throughout (C1). Projection REQUIRED. |
| 2 | The three surfaces live: the fold (N-2), E-P one-map composition, E-A batch + `today_utc()`→`ctx.now.date()`; T1′/T5–T9/T11/T12 | NOT_STARTED | 2026-08-20 | — | `plans/plan_2.md`. Frozen-percent wiring untouched until phase 3. Projection REQUIRED. |
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

### Commits

Checkpoint commits at every `IMPLEMENTED` under the owner's standing authorization;
approval-gate commit at each phase close; the gate itself closes with an archive move +
commit per the closeout ritual.
