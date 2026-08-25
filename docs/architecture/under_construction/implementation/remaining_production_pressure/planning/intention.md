# Intention: Remaining Production Pressure (a step's current allocation of the budget that is left)

```
status: **RATIFIED** (round 3, 2026-08-25) — ratified by the owner (**David**) on
        2026-08-25 on the ratification surface at **§10.6** (outcome in plain language,
        the §1A ledger M1–M7 verbatim, the §7 scope boundaries, the HC-5 sequencing
        block). Before the act the owner explicitly confirmed three calls the document had
        made on the owner's behalf — **D1–D3** (§10.7). The owner answered **"Yes — ratify
        as presented."** Recorded in §11 round 3. The semantic gate is open;
        **implementation remains BLOCKED by HC-5** until the sibling's phases 1–3 are all
        APPROVED. Next actor: coordinator — verify HC-5, then mechanism-inventory.
        Prior header, superseded — READY_FOR_RATIFICATION (round 2, 2026-08-25): O6 folded.
        Prior header, superseded — READY_FOR_RATIFICATION (round 1, 2026-08-24).
role: intention (pipeline root artifact)
shaped_from: docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md
             (the frontend's request, authored by the frontend's Claude Fable 5 agent)
             plus the backend assessment relayed to the owner on 2026-08-24, the owner's
             five decisions O1–O5 of the same conversation, and O6 of 2026-08-25 (§10).
sibling:     docs/architecture/under_construction/implementation/task_budget_overrun_signal/
             planning/intention.md (RATIFIED round 10) — its D1, D5, D9 and §3.4 are cited
             here as established facts, never re-litigated.
date: 2026-08-25
round: 3
```

---

## 1. Objective & hard constraints

A worker opening a step sees one number today — the step's **static allowance** — and works
to it. If earlier sections of the same task overran, that number is no longer achievable, and
nobody on the floor learns it until the task is over budget. This intention adds a second
number beside the first, on both surfaces that show a step's budget: **the step's current
allocation of the production budget that is left** — its *remaining production pressure*.
When earlier sections ran over, the number is smaller than the allowance and the worker
knows to move faster or escalate; when they ran under, it is larger. The static allowance
survives untouched beside it, because the allowance is the benchmark that later tells "this
worker was slow" from "this worker inherited a mess", and it is what feeds the typicals.

**The pressure figure is an allocation, not a countdown.** It is the answer to "of the budget
that is still distributable, how much is this step's share?" — and a step's own work does
not change the answer while the step is within its allowance. Locked as invariant **I-1**
(§3.3). The one exception is the step that has *exceeded* its allowance: it is already in the
escalate state the existing `over_share` fact names, its share is `0`, and from that poll on
its live overrun squeezes the steps still to come (owner O6).

**Hard constraints:**

- **HC-1 — Read-only, derive-on-read.** No new table, no migration, no persisted value, no
  worker, no event, no socket. `CALCULATION_VERSION` (`calculator.py:20`) is not bumped —
  nothing is persisted. Same reasoning as the sibling's HC-1.
- **HC-2 — One calculation, projected twice.** Exactly one pure function computes pressure
  (§3.5). `budget-allocations` and `production-time` both serve it, through their existing
  serializers, by addition of keys. No second formula, no client-side derivation, no
  duplicated rule (owner O4).
- **HC-3 — The division is not touched.** `divide_production_budget`, its section slices,
  step allowances, `left_seconds`, `share_state`, `charged_seconds`, `distributable_seconds`
  and `ALLOCATION_METHOD = "static_proportional_section_v2"` keep their exact values and
  meaning. Pressure is computed *from* the division's output, never by changing it (owner
  O1, O3). Every pre-existing key on both payloads is byte-identical before and after.
- **HC-4 — Additive keys only, no new endpoint, no new roles.** `budget-allocations`
  (ADMIN/MANAGER/WORKER/SELLER) and `production-time` gain keys; their request shapes,
  caps, error identities, envelopes and role gates are unchanged. No monetary field is
  involved, so `decision-money-audience-admin-manager-only` is not engaged.
- **HC-5 — Implementation is BLOCKED behind the sibling project.** See §9. This is a header
  check for every downstream role: no plan, projection, prompt or implementation session
  for this project may start while the sibling tracker shows any phase not `APPROVED`.

## 2. Grounding — what exists (verified 2026-08-24)

### 2.1 The allocator (`app/beyo_manager/domain/item_economics/budget_division.py`)

- `divide_production_budget(allowed_worker_minutes, steps, typicals_by_section,
  section_attributes)` (`:289`) is pure. Its universe is the non-deleted steps.
- Pot: `budget_seconds` = minutes × 60, ROUND_HALF_EVEN (`:69`). `charged_seconds` = Σ worked
  of **excluded** steps (`:327`). `distributable_seconds = max(0, budget − charged)` (`:328`).
- Section slices: typical-weighted `Fraction` shares of `distributable_seconds`, integerised
  by `_largest_remainder` (`:165`), ties by section id (`:350`). Sections whose every step is
  excluded get `allowance_seconds = None, share_state = "excluded"` (`:357`).
- **Step split inside a section** — `_section_step_allowances` (`:222`): completed steps get
  their own `total_working_seconds` as allowance; `residual = section_allowance −
  Σ completed`; the residual is split **equally** across the section's open steps
  (largest-remainder, tie by `_sort_key`); with no open step the residual lands on the
  governing completed step. **Consequence (owner O3):** a step's `allowance_seconds` is
  static only in single-step sections. In a reassigned section the open step's allowance
  *is* the section's residual. Excluded steps are not in this split at all.
- `worked_seconds` is `total_working_seconds` of the input step; both query services feed it
  the **live** figure from `load_live_worked_seconds(..., ctx.now)`
  (`get_task_budget_allocations.py:241`, `get_task_production_time.py:60`). So an open
  step's `worked_seconds` ticks between polls.
- `_step_result` (`:257`) does **not** emit the step's state. Section rows do, as the
  governing step's raw enum value (`group_steps_by_section`, `:149`, via `_governing_step`
  `:180`).

### 2.2 State vocabulary (`app/beyo_manager/domain/task_steps/`)

- `TaskStepStateEnum` (`enums.py`): pending, working, paused, blocked, completed, skipped,
  failed, cancelled.
- `TERMINAL_STEP_STATES` (`constants.py:4`) = {completed, skipped, failed, cancelled}.
- `EXCLUDED_STEP_STATES` (`budget_division.py:25`) = {skipped, cancelled, failed}.
- The allocator's predicates: `_step_state_is_terminal` (`:202`), `_step_state_is_excluded`
  (`:206`), `_step_state_is_open` = not terminal (`:218`). **These are the only definitions
  of open/settled this intention uses** (owner O2, §3.2).

### 2.3 The two surfaces

- `GET /api/v1/item-economics/tasks/budget-allocations` — `item_economics.py:348`, roles
  ADMIN/MANAGER/WORKER/SELLER, repeatable `task_ids`, cap 50
  (`BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS`), invisible ids silently omitted. Serializers
  `serialize_budget_step` / `serialize_budget_allocation` (`division_serializers.py:42-67`).
  Step keys today (10): `step_id, working_section_id, section_name_snapshot,
  typical_worker_seconds, typical_basis, sample_count, allowance_seconds, worked_seconds,
  left_seconds, share_state`. Task keys: `task_id, status, allowed_worker_minutes,
  actual_worker_seconds, remaining_worker_minutes, allocation_method, typical_resolution,
  steps[]`. Under no usable committed evaluation, `allowed/actual/remaining` are `null`
  and steps carry `share_state = "no_budget"` (`get_task_budget_allocations.py:290-308`).
- `GET …/tasks/{task_id}/production-time` — `serialize_task_production_time`
  (`division_serializers.py:168`), with `budget{}`, `final{}` (frozen, from the stored
  result) and `sections[]` via `serialize_production_time_section` (`:135`), which carries
  `state`, `worked_seconds`, `allowance_seconds`, `left_seconds`, `share_state`.
- Both services call the **same** `divide_production_budget` on the same live inputs.

### 2.4 Established facts inherited from the sibling (never re-derived here)

- **§3.4 two-operand divergence.** Section `left_seconds` double-charges an excluded step
  that sits inside a participating section (cause 1: `group_steps_by_section` sums every
  step's worked at `:131` while `charged_seconds` also subtracts it at `:327`), and the pot
  is floored at zero while the task pot is not (cause 2). **This intention's numerator and
  denominator are both taken from the step-level split, which excludes excluded steps
  (§2.1), so cause 1 cannot enter the pressure figure.** Cause 2 enters by design (§3.4
  row 4).
- **D1** — the sibling's projection subtracts the *task* pot. Pressure does not compete with
  that verdict: it is per-step, and it is the *worker's* figure; the manager's over/projected
  verdict stays the sibling's.
- **D5** — this is a separate project. **D9** — a negative pot before any work is a forecast
  that becomes a fact at the first worked second; §3.4 row 4 is consistent with it.

### 2.5 Tests and goldens that assert the exact current shape

- `app/tests/unit/routers/api_v1/test_budget_division_routes.py` —
  `test_time_payload_serializers_have_exact_money_free_key_sets` asserts exact key sets.
- `app/tests/integration/services/queries/item_economics/goldens/golden_budget_allocations.json`
  and `golden_budget_status.json` — full sorted-key payloads.
- `app/tests/unit/domain/item_economics/test_budget_division.py` — 17 tests, helpers
  `step(...)`, `selected(...)`, `allocated_rows(...)`, criteria-named.
- The sibling's `M6` asserts byte-identical `budget-allocations` and `production-time`
  responses across its own phases. Additive keys here would falsify that assertion if shipped
  first — the concrete reason for HC-5.

## 3. The rule

### 3.1 Vocabulary

| Term | Definition (anchored) |
|---|---|
| **participating step** | non-deleted, not in `EXCLUDED_STEP_STATES` (= the steps `_section_step_allowances` allocates) |
| **open step** | participating and `_step_state_is_open` — i.e. state ∉ `TERMINAL_STEP_STATES` |
| **settled step** | participating and terminal — with today's vocabulary, exactly `completed` |
| **consuming step** | open **and** `left_seconds < 0` — i.e. live `worked_seconds > allowance_seconds`, the step-level form of the existing `over_share` fact (owner O6) |
| **allocatable step** | open and not consuming — the only steps that receive a share |
| **excluded step** | state ∈ `EXCLUDED_STEP_STATES`; already charged at the pot (`charged_seconds`); has no allowance and no pressure |
| **allowance** | the step's `allowance_seconds` as the allocator serves it today (§2.1) — the section residual for an open step in a multi-step section |
| **distributable** | the allocator's `distributable_seconds` |

### 3.2 Open vs settled is the domain's, not this feature's (owner O2)

Pressure reads open/settled through the allocator's own predicates, which read
`TERMINAL_STEP_STATES` / `EXCLUDED_STEP_STATES`. It defines no state set of its own. If the
domain later adds a state or moves one between sets, pressure follows without an edit; a
literal state list anywhere in the pressure module is a defect. (Mechanism-inventory will
name the mutation: adding a member to `TERMINAL_STEP_STATES` must change the pressure
denominator without touching the pressure code.)

### 3.3 The invariant that makes it a target and not a countdown (owner O2)

**I-1.** Work recorded on an allocatable step does not, by itself, change that step's
pressure figure. Formally: for fixed states and fixed worked seconds of every *other* step,
the figure is constant in the step's own `worked_seconds` on the whole interval
`0 ≤ worked ≤ allowance`.

**I-1x (the single named exception, owner O6).** At the poll where a step's own
`worked_seconds` first exceeds its `allowance_seconds`, its figure becomes `0` and stays `0`.
This is one transition into the escalate state — never a gradual descent, never before the
allowance is crossed, and never reversible except by a served decrease of its worked seconds
(disowning). The crossing point is the **allowance**, not the pressure share: the allowance
is static and already served, whereas a threshold at the share would make the figure depend
on itself (§11 R2-b).

**I-2.** Two events change an allocatable step's figure, both caused by *other* steps:
(a) settlement of another participating step (state entering `TERMINAL_STEP_STATES`), by the
difference between what it consumed and what it was allocated; (b) another open step being
or becoming consuming — from that poll on, that step's **live** worked seconds enter the
numerator, so the figure decreases poll by poll while the overrun continues. Both are
authoritative decreases (or increases, for (a)) and are never smoothed.

**I-3.** The figure is never `allowance − own_worked`, never `left_seconds`, and never
smoothed. A decrease is authoritative (live-clock handoff §5 applies as written).

What a worker sees under I-1: "23 m of 36 m budgeted" stays 23 m while they work; their
own `worked_seconds` climbs beside it. Whether they are ahead or behind that target is a
client comparison of two served figures, not a served countdown.

### 3.4 The formula (owner O1)

For a task with a usable pot, let `S` be its settled steps, `C` its consuming steps, and
`A` its allocatable steps (open and not consuming). `S ∪ C` is the *charged* set.

```
remaining_distributable = distributable_seconds − Σ_{s ∈ S ∪ C} worked_seconds(s)
total_open_allowance    = Σ_{a ∈ A} max(0, allowance_seconds(a))

pressure_ratio          = remaining_distributable / total_open_allowance        (exact Fraction)
pressure_share(a)       = allowance_seconds(a) × pressure_ratio, integerised across A by
                          largest remainder so that Σ_{a ∈ A} pressure_share(a)
                          = max(0, remaining_distributable) exactly; each share floored at 0
pressure_share(c)       = 0   for every c ∈ C
```

`worked_seconds` of a consuming step is the **live** figure the services already feed the
allocator (§2.1), so the numerator moves every poll while a consuming step keeps working.

Row table — every case an implementer could reach, with its exact answer:

| # | Situation | `pressure_ratio` | `pressure_share_seconds` |
|---|---|---|---|
| 1 | Allocatable steps exist, `remaining_distributable > 0` | exact decimal string, may exceed 1 (served honestly, never clamped above) | integer ≥ 0 per allocatable step; sum = `remaining_distributable` |
| 2 | Allocatable steps exist, `remaining_distributable == 0` | `"0"` | `0` per allocatable step |
| 3 | Allocatable steps exist, `remaining_distributable < 0` (charged work already exhausted the pot) | negative decimal string, served honestly | `0` per allocatable step — "there is no time left for you" (frontend open question 2: `0`, not `null`) |
| 4 | Infeasible or fully charged pot: `distributable_seconds == 0` | as rows 2–3 | `0` per allocatable step from the first poll — consistent with sibling D9: the price was set before the work began |
| 5 | No allocatable step (task finished, only excluded steps remain, or every open step is consuming) | `null` | consuming steps still answer `0` |
| 5b | Consuming step (open, `left_seconds < 0`) | — | `0`, from the crossing poll on; its live worked is in the numerator |
| 6 | Settled step | — | `null` |
| 7 | Excluded step | — | `null` |
| 8 | No usable pot (`share_state == "no_budget"`, `allowed_worker_minutes` null) | `null` | `null` on every step |
| 9 | `total_open_allowance == 0` with allocatable steps (every allocatable step's allowance is 0) | `null` — undefined, not infinite | `0` per allocatable step (nothing to distribute *to*) |

Row 9 is reachable: a section can receive a 0-second slice, and an open step in a
reassigned section can inherit a 0 or negative residual. **Negative allowances:** an open
step whose allowance is negative (residual exhausted by a completed sibling in the same
section) has `left_seconds < 0` at zero worked and is therefore **consuming from its first
poll** (row 5b): share `0`, and its own worked (0 so far) in the numerator. Its section's
shortfall is already in the numerator through the completed sibling's worked seconds, so
nothing is charged twice — this is the same outcome round 1 reached by the `max(0, …)`
clause, now derived from the consuming rule rather than a special case.

Worked example (the frontend's, `tsk_01KXGHT2BP0JXVHW065KSJSRVZ`, 2026-08-22):
`distributable = 16589`, settled worked `6961 + 4977 + 2981 = 14919`, remaining `1670`,
open allowances `2210 + 409 = 2619`, ratio `0.63765…`, shares **1409 / 261** (sum 1670),
`allowance_seconds` unchanged at 2210 / 409.

I-1 check on the same task: weaving records 600 s. `S ∪ C` is unchanged (weaving is within
2210), `A` and its allowances are unchanged → ratio and both shares unchanged. Photography
records 100 s concurrently: likewise unchanged. Structural repair had instead settled at
9000 s rather than 4977: remaining `−2353` → row 3, both shares `0`.

O6 check: cleaning seat is still **open** at 6961 s against 2958 (consuming), the other two
settled as above. Charged = 6961 + 4977 + 2981 = 14919 → remaining 1670 → weaving 1409,
photography 261 — the same figures the settled case gives, served *before* cleaning seat
completes. Next poll, cleaning seat at 7021 s: remaining 1610 → shares 1358 / 252. Cleaning
seat's own share is `0` throughout; before it crossed 2958 it was `2958 × ratio`.

### 3.5 One calculation, two projections (owner O4)

One pure function — working name `compute_remaining_pressure(division) -> PressureResult`
in a new module beside `budget_signal.py` — takes the allocator's output and returns, per
step, `pressure_share_seconds: int | None` and, per task, `pressure_ratio: Fraction | None`.
A section's figure is the **sum of its open steps' shares** — consuming steps contribute `0` —
(exact, since integerisation is done over steps), so the section projection is a fold of the step projection, not a second
formula. Both query services call it once, after `divide_production_budget`, and the
serializers add the keys. Neither service owns any arithmetic of its own.

### 3.6 Weights follow the division (frontend open question 4)

The share basis is `allowance_seconds` as served — which is already the v2 item-aware,
fallback-resolved, largest-remainder slice, split to the step by the section residual rule.
Pressure introduces no weight of its own. The honest sentence for workers: *your number
moved because another section finished over or under its slice — never because your typical
changed.*

## 4. Wire contract

### 4.1 `budget-allocations` — additive keys

Per step (`serialize_budget_step`), two new always-present keys:

| Key | Type | Value |
|---|---|---|
| `state` | string | the step's **own** `TaskStepStateEnum` value — same vocabulary production-time uses for `sections[].state`, but the subject is the step, not its section's governing step |
| `pressure_share_seconds` | int \| null | §3.4 table |

Per task, two new always-present keys:

| Key | Type | Value |
|---|---|---|
| `pressure_ratio` | decimal string \| null | §3.4 table; exact `Fraction` rendered at the precision the sibling's decimal strings use; never clamped |
| `pressure_method` | string | `"open_share_proportional_v1"` — a method identity separate from `allocation_method`, which stays `static_proportional_section_v2` because the division did not change |

Ordering of steps, envelope, cap, omission rule, error identities: unchanged.

### 4.2 `production-time` — additive keys

Per section (`serialize_production_time_section`): `pressure_share_seconds: int | null` —
the sum of the section's open steps' shares; `null` when the section has no open step.
Per task: `pressure_ratio` and `pressure_method`, identical in value to what
`budget-allocations` serves for the same task at the same instant. `final{}` is not
touched — it is frozen and pressure is `null` for a finished task anyway (row 5).

### 4.3 Nullability

`null` means "we cannot say" (no pot, no open step, settled/excluded step). `0` means "there
is no time left for you". The two are never conflated; a client distinguishes escalate-now
(`state` open and share `0`) from not-applicable (`null`) without a further field.

### 4.4 Published contracts

No published contract in `Application_contracts` names the two payload families
(verified by grep, 2026-08-24). The `to_frontend` handoff of §8 is the contract vehicle.

## 5. Provenance — facts vs derived

| Field | Layer | Written by | Never overwritten by |
|---|---|---|---|
| `worked_seconds`, step state | fact | ingestion (`StepStateRecord`, live clock) | this feature |
| `allowance_seconds`, `left_seconds`, `share_state` | derived, existing | `divide_production_budget` | this feature (HC-3) |
| `pressure_share_seconds`, `pressure_ratio` | derived, new | `compute_remaining_pressure` on read | anything — never stored |

Pressure is a projection of a projection. No value it produces is stored, fed to the
typicals, or fed back into the division.

## 6. Operations

Nothing new: no config, no flags, no scheduler. The one operational cost is one more pure
pass per task per poll, over data already in memory. The 45-second poll and the
`task:step-state-changed` invalidation the frontend already runs are sufficient; I-2 means
the figure changes only on state transitions and on the settled-work refresh those imply.

## 7. Scope ladder

**Must ship**

1. `state` on `budget-allocations` `steps[]`.
2. `pressure_share_seconds` on `steps[]` and `pressure_ratio` + `pressure_method` on the task
   row of `budget-allocations`.
3. The same figures on `production-time` (`sections[]` share, task ratio and method).
4. The pure module with I-1/I-2/I-3 proven on the production allocator's output.
5. Updated exact-key-set test and goldens; the dated `to_frontend` answer handoff.

**Only if cheap**

- Nothing identified. (A per-section `pressure_share_seconds` on `budget-allocations` was
  considered and rejected: that payload carries no `sections[]` and adding one is the shape
  regression the sibling handoff exists to prevent.)

**Explicitly deferred / non-goals**

- **Fixing §3.4 cause 1** (section `left_seconds` double-charge). Out of scope by HC-3; the
  pressure figure is immune to it by construction. Standing observation in the sibling.
- **Rush / escalate thresholds.** Presentation, frontend-owned (handoff §"What we do NOT
  need").
- **Clamping the ratio above 1 server-side.** Served honestly; acting only below 1 is a
  presentation choice (frontend open question 1, answered: honest).
- **Squeezing peers by a still-open section that is within its allowance.** Under I-1 an
  open step's own work is invisible until it crosses its allowance; only then (I-1x/I-2b)
  does its live overrun reach others. The live "this task is heading over" fact stays the
  sibling's manager verdict.
- **Any change to typicals, `allocation_method`, `budget-status`, `price-scenario`,
  `budget-signals`.**
- **Events, sockets, persistence.**

## 8. Pre-implementation protocol

1. HC-5 gate (§9) verified against the sibling tracker by every session, first thing.
2. mechanism-inventory on this document (its I-1/I-2/I-3 and the §3.4 table are the
   silent-failure mechanisms; rule 6).
3. implementation-planner: expected two phases — (a) pure module + unit tests on the real
   allocator output; (b) both services, both serializers, key-set test, goldens, handoff.
4. The `to_frontend` handoff answers every open question of the frontend handoff by name
   and is a **new dated file** (standing rule: never rewrite a published handoff).
5. **The handoff states the client-side asymmetry as an expectation (owner, 2026-08-25):**
   the worker card renders `min(allowance_seconds, pressure_share_seconds)` — pressure only
   ever tightens the number a worker sees — while manager surfaces may show the honest
   share and ratio above 1. Reason: typicals are the median of actual worked seconds, so a
   worker shown an inflated share would inflate next period's allowance. This is a display
   rule, deliberately not a served field (§11 R3-a); it must also say that the manager still
   sees a live overrun through `left_seconds` / `share_state` before a step turns consuming.

## 9. Implementation dependency — HC-5 (owner O5)

**Blocked on:** `task_budget_overrun_signal` — every phase `APPROVED` in its
`master_plan.md` tracker. At writing (2026-08-24): phase 1 `APPROVED`, phase 2
`PROMPT_READY`, phase 3 `NOT_STARTED`.

**Why:** the sibling's M6 asserts byte-identical `budget-allocations` and `production-time`
responses across its phases; its phases 2–3 touch `division_serializers.py`, the item-
economics router, the route-mirror tests and `routers/README.md`; this project changes the
same serializers, the exact-key-set test and both golden files. Interleaving them produces
conflicting golden regenerations and a false M6 failure in whichever lands second.

**Gate text for downstream roles:** *Before any planning, projection, prompt or
implementation act for `remaining_production_pressure`, read
`task_budget_overrun_signal/master_plan.md` §tracker. If any row is not `APPROVED`, stop and
report; do not proceed on the owner's earlier ratification of this intention — ratification
opens the semantic gate, not the sequencing gate.*

## 1A. Measurement ledger (root of the trace chain)

| ID | Observable outcome | Defect family guarded | Trace |
|---|---|---|---|
| **M1** | For the frontend's worked example, fed through the real `divide_production_budget`, the open steps' `pressure_share_seconds` are **1409 / 261**, their sum equals `distributable − Σ settled worked` exactly, and every `allowance_seconds` is unchanged. | **The wrong denominator.** Summing positive `left_seconds` (7192) tells the weaver to do 36 min in 8; the frontend measured this on production data. | §3.4 rows 1, ex.; HC-3 |
| **M2** | Recording work on an allocatable step anywhere in `0 ≤ worked ≤ allowance` — including past its own *share* — leaves that step's `pressure_share_seconds` and the task's `pressure_ratio` unchanged. The poll it exceeds its allowance, its share is `0` and every other allocatable step's share decreases; each further second it records decreases them again while its own stays `0`. | **The countdown** (a target retreating under the worker before the escalate state) and **the blind window** (an upstream overrun invisible to downstream until completion). | I-1, I-1x, I-2, §3.4 rows 1, 5b |
| **M3** | A settled step that finished **under** its slice contributes its actual worked seconds — never its unused slice — and a step in a reassigned section carries the section residual as its basis, with the completed sibling's worked in the numerator only once. | **Unused time counted as future work; double-counting a residual.** | §3.4 rows, §2.1, §3.1 |
| **M4** | Rows 2–9 (incl. 5b) of the §3.4 table each answer exactly as tabulated; `0` and `null` are never swapped; a ratio above 1 and a negative ratio are served unclamped. | **Null/zero conflation** (escalate-now read as not-applicable) and **silent clamping**. | §3.4, §4.3 |
| **M5** | `production-time` and `budget-allocations` serve the same `pressure_ratio` for the same task at the same instant, and each section's `pressure_share_seconds` equals the sum of its open steps' shares on the other surface — from one function, called by both services. | **Cross-surface disagreement** (manager and worker see different targets) and **the second formula**. | HC-2, §3.5, §4 |
| **M6** | Open/settled classification changes when `TERMINAL_STEP_STATES` changes and the pressure module is untouched — no literal state set exists in it. | **Semantic drift** between task-state and budget domains. | §3.2 |
| **M7** | Every pre-existing key of both payloads is byte-identical for identical state before and after; the sibling's own M6 evidence still holds at this project's gate commit. | **Collateral regression** on the surfaces two shipped apps read. | HC-3, HC-5 |

## 10. Owner decisions (all RESOLVED in the shaping conversation, 2026-08-24)

- **O1 — Semantics.** Pressure = step allowance × (remaining distributable after settled
  participating work ÷ total open allowance), on the existing domain calculations. → §3.4.
- **O2 — Open/settled.** Anchored to the domain's terminal-state semantics; own work never
  retreats own figure; NOT `allocation − own_worked`. → §3.2, §3.3.
- **O3 — Multi-step sections.** Preserve the section-level economics; the open step carries
  the section residual; no competing per-step static model. → §2.1, §3.1.
- **O4 — Parity.** `production-time` exposes the same semantics; one calculation, two
  projections. → HC-2, §3.5, §4.2, M5.
- **O5 — Sequencing.** Blocked behind the sibling; recorded so no implementer can miss it. →
  HC-5, §9.
- **O6 — Consuming steps (2026-08-25).** An open step that is over its allowance charges its
  live worked seconds to the numerator and leaves the denominator, so subsequent steps feel
  the overrun before settlement; its own share is `0` — the over-budget signal, not the ratio,
  is what the floor reads for that step. → §3.1, §3.3 I-1x / I-2b, §3.4, M2.

### 10.6 Ratification surface (relay verbatim)

**What this achieves.** Beside the budget a step was given, the worker and the manager both
see the step's share of the budget that is actually left after other sections finished — or
are currently running — over or under. The share is a target, not a clock: the worker's own
minutes never shrink it while they are inside their budget; it changes only when other
sections finish, or when another section is over its budget and still working. A section
that goes over its own budget shows `0` from that moment and is the over-budget signal's
business, not the target's. Nothing already shown changes.

**What we measure** — the ledger at §1A, verbatim, M1–M7 (M2 restated in round 2).

**Scope.** Ships: `state` and the pressure share on every step of the worker payload; the
same share per section and the task ratio on the manager's production-time payload; one
formula. Not shipping: thresholds, clamping above 1, changes to the division, events, a
fix to the known section-level double-charge, a new endpoint.

**Sequencing.** Nothing is built until the budget-signal project is fully approved.

**Decisions outstanding:** none.

### 10.7 Confirmations taken before the act (2026-08-25, owner David)

- **D1 — Crossing point = allowance.** A step becomes consuming when its live worked exceeds
  its *original* `allowance_seconds`, never its squeezed share. (Confirms §11 R2-b.)
- **D2 — Negative ratio served honestly.** When charged work has exhausted the pot,
  `pressure_ratio` is served negative while every share is `0`; no floor. (Confirms §3.4
  row 3, §11 R1-f.)
- **D3 — Names.** `pressure_share_seconds`, `pressure_ratio`, `pressure_method =
  "open_share_proportional_v1"`; `allocation_method` unchanged. (Confirms §11 R1-a.)

## 11. Shaping changelog

**Round 1 (2026-08-24, shaper: Claude Fable 5).** Grounded against the allocator, both
query services, both serializers, the state constants, the exact-key-set test, the goldens
and the sibling intention. Repo-derivable resolutions made by the shaper, with rationale:

- R1-a **Names.** `pressure_share_seconds` / `pressure_ratio` / `pressure_method` instead of
  the frontend's `remaining_share_seconds` / `remaining_pressure_ratio`. The frontend
  offered the names; "remaining" invites the countdown reading I-1 forbids.
- R1-b **Integerisation** by `_largest_remainder` over open steps, floored at 0 — the
  allocator's own device, so the sum identity is exact and rounding rules do not multiply.
- R1-c **Section figure = sum of open steps' shares**, so parity (M5) is an arithmetic
  identity rather than a second computation.
- R1-d **Negative open allowance enters as 0** (§3.4 note) — otherwise a reassigned
  section's shortfall is charged twice.
- R1-e **`pressure_method` is a separate identity**; `allocation_method` is unchanged
  because the division is unchanged (HC-3).
- R1-f **Ratio precision**: rendered as the sibling renders decimal strings; unclamped in
  both directions (frontend open question 1).
- R1-g **Row 4 (infeasible pot → shares 0 from the first poll)** is consistent with sibling
  D9 and needs no new owner ruling.
- R1-h **Cause 1 of §3.4 is out of scope**, and the pressure figure is immune to it because
  both operands come from the step-level split. Recorded so the next reader does not
  "fix" it here.

Nothing material was resolved silently: O1–O5 were the owner's, given before writing.
Status set to READY_FOR_RATIFICATION; RATIFIED awaits the owner's act on §10.6.

**Round 2 (2026-08-25, shaper: Claude Fable 5).** Owner decision **O6** folded: an open step
over its allowance is *consuming* — charged live, out of the denominator, share `0`. Material
semantic change, so the round-1 READY claim is withdrawn and re-made here. Repo-derivable
resolutions:

- R2-a **Consuming is `left_seconds < 0`**, the step-level form of the existing `over_share`
  fact — no new predicate, no new threshold.
- R2-b **Crossing point = allowance, not pressure share.** The allowance is static and
  already served; a threshold at the share would make the figure a function of itself.
- R2-c **Round 1's `max(0, allowance)` clause for negative residuals is now a consequence**
  of the consuming rule (row 5b), not a special case; kept in the denominator formula for
  the trivial positive-allowance path.
- R2-d **M2 restated** to guard both the countdown and the blind window; no other ledger
  entry changed in meaning.
- R2-e §7 non-goal narrowed accordingly; §10.6 surface reworded; O1–O5 untouched.

**Round 3 (2026-08-25, owner: David; shaper: Claude Fable 5).** **RATIFIED.** Surface
presented: §10.6 verbatim (outcome, ledger M1–M7, scope, sequencing). Confirmations D1–D3
(§10.7) taken as four one-line answers, then "Yes — ratify as presented." No text changed
between the round-2 surface and the act other than this entry, §10.7 and the header. HC-5
is unaffected by ratification: the next act is the coordinator's HC-5 check, then
mechanism-inventory.

**Round 3 addendum (2026-08-25, owner: David).** Post-ratification, non-semantic. R3-a: the
`min(allowance, share)` worker-display rule is the client's, confirmed by the owner, and is
recorded as §8 item 5 for the answer handoff; a served `pressure_target_seconds` was
considered and declined (more surface than the rule deserves; the manager wants the honest
figure). No ledger entry, contract or invariant changed; the gate stays RATIFIED.
