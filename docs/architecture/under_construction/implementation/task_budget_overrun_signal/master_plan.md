# Master plan — Task Budget Overrun Signal

```
project: task_budget_overrun_signal
role: master plan (coordination hub — indexes plans/, prompts/<role>/, handoffs/<role>/, archive/)
authored: 2026-08-24, implementation-planner round 1 (Claude Fable 5)
intention: planning/intention.md — status RATIFIED (round 10, 2026-08-24), mechanism-inventory complete
tree at authoring: f376928 (app/ byte-identical to the narrow_typical_work_times gate 49a6e50 — `git diff --stat 49a6e50 HEAD -- app/` is empty)
```

## 1. Goal

Ship **one batched, read-only, ADMIN/MANAGER endpoint** —
`GET /api/v1/item-economics/tasks/budget-signals?task_ids=…` — that serves, per visible
requested task, a flat ten-key row naming whether the task is over its production budget,
heading there, and what each costs. The projection rule moves out of the frontend's
`buildOutlook` into a new pure domain module; money is a **call** into the shipped
`calculate_consumed_cost_minor`; nothing existing changes except the four enumerated
route-mirror artifacts. **Semantics live in the intention and are never restated here** —
read `planning/intention.md` §1 (objective + HC-1…HC-7), §1A (the measurement ledger M1–M6
and the 22 registered mechanism contracts), §§3–7A (the contracts), §8 (scope ladder).

Three phases (§7): the pure rule, the service + serializer, the route + mirror artifacts +
frontend handoff. **Why three and not the intention's tentative two** (§9 item 3): the
inventory registered **22** contracts against the ledger; the service/serializer/route half
alone carries §§5A, 6A.1, 6A.4, 7A.1–7A.6 — more than eight independent obligations — so a
two-phase set would ship a second phase far above the charter's ≤ 8-criteria target. The
seam between phases 2 and 3 is the service's dict return value (stable; the sibling
`get_task_budget_allocations` already has exactly this shape), so each closes green alone.

## 2. Sources of truth

| Content | Artifact |
|---|---|
| Product semantics, HC-1…HC-7, the ledger M1–M6, every mechanism contract (§§3–7A), owner decisions D1–D10 | `planning/intention.md` (**RATIFIED**, round 10) |
| Grounding research, probes verbatim, the shaper's anchor map | `handoffs/shaper/20260824_shaping_context_handoff.md` (reference, never authority) |
| Inventory ranking, probes P1–P12, planner routing hazards (§6) | `handoffs/planner/20260824_mechanism_inventory_round_1.md` |
| The frontend's request (read-only; **never edited** — memory `never-rewrite-a-published-handoff`) | `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823.md` |
| The colliding request — **a different project by D5; excluded here** | `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md` |
| Shared skeleton: naming registry (§6), contract resolution (§5), environment (§10), standing rules (§9), tracker (§4) | **this file** |
| Phase goal / files / tasks / criteria / Review log | `plans/plan_1.md`, `plans/plan_2.md`, `plans/plan_3.md` |
| Session framing | `prompts/<role>/…`, generated just-in-time by the coordinator, never reused stale |
| Session reports | `handoffs/<role>/…`; closed rows move to `archive/plan_<n>/` at the coordinator's closeout |

**Fold-back rule.** A semantic change amends the intention (lettered sections, never
renumbering); a skeleton change amends this file; a phase plan is never patched into
divergence with either. Review lessons fold into the *consumer* plan's Read-first list, not
into the plan that earned them.

**Planner findings folded upstream** (recorded here so their provenance is not lost;
none blocks planning — see the planner handoff §5 for the full text):

- **F1 — intention §6A.2 row 4 is unreachable, and the table's third column header is
  stale.** `over_seconds > 0` ⇒ `actual > max(0, raw)` ⇒ `raw − actual < 0` ⇒
  `projected_over_seconds = max(0, commitment − (raw − actual)) ≥ 1`. So an `over` row can
  never carry `projected_over_seconds == 0` (derived from the shipped allocator, planner
  probe P-H4: `over 1 / projected 1`), and the three fixtures §6A.2 maps to "row 4" all carry
  a non-zero projection. The column header still reads `remaining_commitment > 0` where
  D10 replaced it with the set test. **Precision, not meaning** (§6's cascade is unaffected);
  the plans enumerate the six reachable rows plus the derived invariant
  `over ⇒ projected_over_seconds ≥ over_seconds`. Coordinator: route to the intention as a
  §6A.2A in intention round 10.
- **F2 — the two-step price-scenario inverse does not disagree at the half-tie durations.**
  At rate `3.7500` the exact-rational mutant disagrees at 136 s / 152 s (as §4.2 says); the
  two-step mutant **agrees** there and first disagrees at **40 s** (`2` shipped vs `3`).
  Plan 1 C5 therefore carries a 40-second row so the second prohibited derivation has a row
  that reddens. §4A.1's "each was measured to disagree" is true in aggregate, not per row;
  folded as §4A.1A in intention round 10.
- **F3 — §7A.7 is not a deviation; it is the local contract.** `backend/architecture/
  46_serialization_local.md` lists item-economics query services among those that serialize
  inline and rules "a change keeps serialization where the code it modifies already has it".
  §5 below resolves it; no reviewer should file it.

## 3. Roles & session workflow

Charter state machine per phase:
`NOT_STARTED → PROJECTED → PROMPT_READY → IMPLEMENTING → IMPLEMENTED → REVIEWING →
CHANGES_REQUESTED (→ IMPLEMENTING) → APPROVED`. A phase starts only when the previous is
APPROVED. Every implementation and fix cycle is committed at `IMPLEMENTED` as
`CHECKPOINT (not approved): …`; the phase is committed again at its gate.

- **Coordinator** compiles one prompt per session from the plan file + this file + the
  intention, header-checks `status: **RATIFIED**` on every compile, keeps §4 honest, folds
  review lessons upstream, runs the closeout ritual (archive rows, gate commit).
- **Projection (reviewer role, round 0)** — risk-triggered per charter. **Mandatory for
  phases 1 and 2** (both touch rule-6 mechanisms: money, derivations, ordering). **Phase 3:
  waivable** with a recorded one-line justification (route wiring, hand-maintained docs,
  no derivation) — the coordinator decides. Self-retiring after two consecutive empty ledgers.
- **Implementer** follows `implementation-executor`: gate check, Task 0 (forward + reverse
  trace map: every criterion row → test; every test → row or declared candidate), tests
  first from the criteria table, every named mutation run at hypothesis scope and recorded
  with the observed red, exactly one L4 stamp on the handed-over tree, handoff with full
  write perimeter, graph delta assessment (§8).
- **Reviewer** follows `plan-reviewer`: first review full; re-reviews delta-scoped with a
  verified perimeter (`git diff` against the checkpoint), variation not reproduction.
- **Owner layer**: every session's final message follows the charter's four-part shape; all
  owner cards in one `⚠ OWNER DECISIONS REQUIRED (n)` section.

## 4. Progress tracker

| Phase | Title | State | Date | Actor | Note |
|---|---|---|---|---|---|
| 1 | Pure rule — `budget_signal.py` (§§3A, 4A, 5A.3, 6A.2/6A.3) | `APPROVED` | 2026-08-24 | coordinator | Review r1 findings dispositioned: neither expands plan-1 acceptance; production rule, 35 row mutations, and baseline evidence accepted; no fix cycle |
| 2 | Service + serializer — `get_task_budget_signals.py`, `serialize_budget_signals` (§§3A.1, 5A.1/5A.2, 6A.1, 6A.4, 7A.1/7A.2, M2 on the production path) | `NOT_STARTED` | 2026-08-24 | planner | 8 criteria; projection **mandatory**; integration tests on the disposable DB |
| 3 | Route + HC-2a artifacts + `to_frontend` handoff (§§7A.3–7A.6, §8 item 5) | `NOT_STARTED` | 2026-08-24 | planner | 6 criteria; projection waivable (coordinator's call); graph delta = endpoint node |

## 5. Contract resolution

**Two copies of the contract system exist and were both read.** The canonical source is
`/Users/davidloorenz/Desktop/Developer/Application_contracts/backend/architecture/` (55
files; README carries the navigation matrix — row *"Add a new endpoint to an existing
domain → 29_feature_workflow.md §B; then 06 or 07, 09, 15"*). The **repo-local copy** is
`backend/architecture/` (69 files: the 55 plus fourteen `*_local.md` app-local extensions
and three app-only files). **The local copy governs where it extends** — its `_local`
files record standing divergences the canonical text does not know about. Verified:
`grep -rln "item-economics|budget-allocations|item_economics"` over the canonical repo
returns **nothing** — **no published endpoint row exists for any item-economics route**, so
nothing there needs a row (inventory R6-f independently confirmed).

| Status | Contract | Why |
|---|---|---|
| **selected** | `01_architecture.md` | layer map; the new module is `domain/`, the service `services/queries/`, the route `routers/api_v1/` |
| **selected** | `04_context.md` | `ServiceContext` (`query_params`, `workspace_id`, `now`, `session`) — the service's only input |
| **selected** | `05_errors.md` + **`05_errors_local.md`** | local: **no `code` field**; identity is the message prefix; `ValidationError.http_status = 422` (intention §7A.3) |
| **selected** | `07_queries.md` + **`07_queries_local.md`** | read-operation structure; local pagination override does **not** apply (this surface is an id-batch, not a page — mirrors the sibling) |
| **selected** | `08_domain.md` | domain purity (no I/O, no SQLAlchemy — enforced by `tests/unit/domain/item_economics/test_domain_purity.py`, which sweeps every module in the package **including the new one**); "fully annotated signatures, no `Any`" — §6.2 uses `Mapping[str, object]` |
| **selected** | `09_routers.md` | routers own the role gate and the envelope only |
| **selected** | `15_testing.md` | test files mirror the module; `phase`-free names; the disposable-DB fixture backbone (`tests/conftest.py`, `tests/database_isolation.py`) |
| **selected** | `21_naming_conventions.md` | `route_<verb>_<resource>`, `get_<resource>` query names, `serialize_<resource>` |
| **selected** | `22_performance.md` | N+1 prevention — plan 2 C1(b) asserts a constant statement count across batch sizes |
| **selected** | `25_soft_delete.md` | the three-clause visibility predicate (intention §7A.1) |
| **selected** | `28_roles_permissions.md` | `require_roles([ADMIN, MANAGER])`; fail-closed money boundary (graph decision `decision-money-audience-admin-manager-only`) |
| **selected** | `29_feature_workflow.md` §B | the playbook for a new endpoint on an existing domain |
| **selected** | `46_serialization.md` + **`46_serialization_local.md`** | **local rule binds**: item-economics query services serialize inline and return dicts; the router passes them to `build_ok`. The new service calls `serialize_budget_signals` itself, exactly as the sibling does. This retires §7A.7's "deviation" framing (finding F3). Local decisions also bind: no floats; **but** this row carries **no `Decimal`** at all (intention §5A.1), so `Decimal`-as-string never applies to it |
| **excluded** | `29_feature_workflow.md` §B step 6 / README rule 11 ("an endpoint without a shape in `docs/domains/<domain>/api.md` is incomplete") | **Intention §7A.6 forbids** adding the new path to `docs/domains/item_economics/api.md` or that folder's `README.md`: `test_no_document_invents_a_fully_qualified_item_economics_path` accepts only the hand-written 23-route set (`test_item_economics_handoff_accuracy.py:40-70`), and the three newer sibling routes are likewise absent from `api.md` (verified: `grep` finds only `budget-status`). The documentation home is `routers/README.md` (HC-2a artifact 2, OpenAPI shape) plus the dated `to_frontend` handoff (plan 3). |
| **excluded** | `07_queries_local.md` pagination pattern, `12`, `18`, `37`, `47` | no pagination, no cache, no rate limit, no scheduler, no notification — all deferred by intention §8 |
| **local** | charter standing rules + §9 below | routing baseline for everything the contracts do not name |

Implementing sessions **re-emit this table** in their handoff before coding (planner
doctrine §5) and add any contract they had to open that is not listed.

## 6. Shared skeleton & naming registry

Every name is fixed here once. A phase needing a name not in this section adds it here in
the same edit, before using it.

### 6.1 Files

| Path | Phase | Status |
|---|---|---|
| `app/beyo_manager/domain/item_economics/budget_signal.py` | 1 | **NEW** — the pure rule (§6.2) |
| `app/tests/unit/domain/item_economics/test_budget_signal.py` | 1 | **NEW** |
| `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py` | 2 | **NEW** — the batched query service |
| `app/beyo_manager/domain/item_economics/division_serializers.py` | 2 | **MOD, additive**: `serialize_budget_signal`, `serialize_budget_signals`, two `__all__` entries. **Nothing existing in the file changes** |
| `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py` | 2 | **NEW** — self-contained fixtures (copies, never imports, the sibling test's `_seed`) |
| `app/beyo_manager/routers/api_v1/item_economics.py` | 3 | **MOD, additive** — HC-2a artifact 4: one import, one route declared **immediately after** `route_get_task_budget_allocations` (`:347-360` today) |
| `app/beyo_manager/routers/README.md` | 3 | **MOD, additive** — HC-2a artifact 2: one Quick Index row after `:79`, one detail section after the `budget-allocations` section (`:1648-1700`) |
| `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` | 3 | **MOD** — HC-2a artifact 1: `_EXPECTED_ROUTES` +1 row (`:33` opens; sibling row at `:60`), both counts `26 → 27` (`:127-128`), **and the function name** `test_the_registry_ships_twenty_six_routes` (`:124`) → `..._twenty_seven_routes` (§7A.6) |
| `app/tests/unit/routers/api_v1/test_item_economics_router.py` | 3 | **MOD** — HC-2a artifact 3: `_ROUTES` (`:14`) +1 row; **`_ALL_ROLE_ROUTES` (`:49`) untouched** |
| `app/tests/unit/routers/api_v1/test_budget_signals_route.py` | 3 | **NEW** — dispatch, precedence, cap, envelopes |
| `app/tests/unit/docs/test_budget_signals_handoff.py` | 3 | **NEW** — pins the frontend handoff's corrections |
| `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_budget_overrun_signal_<YYYYMMDD>.md` | 3 | **NEW** — date = the day phase 3 is implemented; follows `TEMPLATE_HANDOFF_TO_FRONTEND.md` headings |

**No other pre-existing file is touched in any phase** (M6). In particular: not
`budget_division.py`, not `calculator.py`, not `get_task_budget_allocations.py`, not the
sibling test files, not `docs/domains/item_economics/*`, not `Application_contracts`.

### 6.2 `budget_signal.py` — the fixed API

```python
NO_CURRENCY: Final[str] = "no_currency"                       # the ONLY place this literal exists in beyo_manager/
CURRENCY_VOCABULARY: Final[frozenset[str]] = frozenset(c.value for c in ItemCurrencyEnum) | {NO_CURRENCY}   # derived (§5A.3)

BUDGET_STATE_NO_BUDGET: Final[str] = "no_budget"
BUDGET_STATE_OVER: Final[str] = "over"
BUDGET_STATE_PROJECTED_OVER: Final[str] = "projected_over"
BUDGET_STATE_WITHIN_BUDGET: Final[str] = "within_budget"
BUDGET_STATES: Final[frozenset[str]] = frozenset({...the four...})

PROJECTED_OVER_FLOOR_SECONDS: Final[int] = 60                  # D6

_TERMINAL_STATE_VALUES: Final[frozenset[str]] = frozenset(state.value for state in TERMINAL_STEP_STATES)   # derived (§3A.2) — never typed, never the enum set itself

def contributes(section: Mapping[str, object]) -> bool          # §3A.2: left_seconds is not None and state not in _TERMINAL_STATE_VALUES
def remaining_commitment(sections: Sequence[Mapping[str, object]]) -> int    # §3A.4: sum(max(0, left) for contributing) — clamp INSIDE the sum
def has_work_ahead(sections: Sequence[Mapping[str, object]]) -> bool         # D10: any(contributes(s) for s in sections) — a set test, never a sum

@dataclass(frozen=True)
class BudgetSignal:
    budget_state: str
    over_seconds: int
    over_cost_minor: int
    projected_over_seconds: int
    projected_over_cost_minor: int
    allowed_seconds: int                      # SERVED value: max(0, allowed_seconds_raw)  (D9)
    actual_worked_seconds: int
    cost_per_worker_minute_ten_thousandths: int

NO_BUDGET_SIGNAL: Final[BudgetSignal] = BudgetSignal(BUDGET_STATE_NO_BUDGET, 0, 0, 0, 0, 0, 0, 0)   # §5A.2: constructed, never computed

def compute_budget_signal(
    *,
    sections: Sequence[Mapping[str, object]],          # divide_production_budget(...)["sections"], unchanged
    allowed_seconds_raw: int,                          # division["budget_seconds"] — the allocator's own int, MAY BE NEGATIVE (§3A.5)
    actual_worked_seconds: int,                        # integer sum of the live map
    cost_per_worker_minute_minor_snapshot: Decimal,    # evaluation.cost_per_worker_minute_minor_snapshot (§4.1)
) -> BudgetSignal
```

`compute_budget_signal` is the **only** place the §3A.4 arithmetic block lives, verbatim:

```
commitment            = remaining_commitment(sections)
remaining_pot_seconds = allowed_seconds_raw - actual_worked_seconds            # D1, UNCLAMPED
projected_over        = max(0, commitment - remaining_pot_seconds)
over                  = max(0, actual_worked_seconds - max(0, allowed_seconds_raw))   # D9
state                 = OVER if over > 0
                        else PROJECTED_OVER if projected_over >= PROJECTED_OVER_FLOOR_SECONDS and has_work_ahead(sections)
                        else WITHIN_BUDGET
over_cost             = calculate_consumed_cost_minor(over, rate)              # §4.2 — a CALL
projected_cost        = calculate_consumed_cost_minor(projected_over, rate)
served allowed        = max(0, allowed_seconds_raw)
rate_ten_thousandths  = int(rate.scaleb(4))                                    # §4A.2
```

**Task id and currency are not in `BudgetSignal`** — they are facts the service attaches
(§5.4). The `no_budget` case never calls `compute_budget_signal` (§5A.2 short-circuit in
the service).

**Naming rules implied by the repo:** module-level constants `UPPER_SNAKE`; private
module symbols `_leading_underscore`; booleans as predicates (`contributes`,
`has_work_ahead`), never `is_`-prefixed dataclass fields on the wire; no `Any`; the domain
purity guard (`test_domain_purity.py`) rejects the substrings `hashlib`, `sha1`, `sha256`,
`md5`, `fingerprint`, **`digest`**, `sqlalchemy`, `models.tables` **anywhere in the module's
text, comments and docstrings included** — do not write "digest" in prose either.

### 6.3 `get_task_budget_signals.py` — the fixed API

```python
_MAX_TASK_IDS: Final[int] = 50
from beyo_manager.services.queries.item_economics.get_task_budget_allocations import _BUDGET_STATUSES   # reused, not respelled (HC-6, D2, §6A.1)

async def get_task_budget_signals(ctx: ServiceContext) -> dict      # returns serialize_budget_signals(rows)
```

- Over-cap: `ValidationError("BUDGET_SIGNALS_TOO_MANY_TASK_IDS: at most 50 task ids may be requested")`, raised on the raw list **before** any query (§7A.1).
- Visibility query: the sibling's three clauses (`get_task_budget_allocations.py:61-63`) **plus `.order_by(Task.client_id.asc())`** — the one and only ordering site (§7A.2). No `sorted(...)` afterwards.
- Loading: the sibling's statements and shapes (`:69-200`), copied — **never** refactored into a shared helper (HC-2). Status resolution `:203-229` copied verbatim; the no-evaluation branch **must** still run (§6A.1).
- Per task: `division = divide_production_budget(allowed, division_steps, selection.selected)` with the sibling's four arguments (§3A.1; `section_attributes` omitted = `None`); `actual_seconds = sum(live_seconds[step.client_id] for step in task_steps)` (strict indexing).
- Branch: `status in _BUDGET_STATUSES and evaluation is not None` → `compute_budget_signal(sections=division["sections"], allowed_seconds_raw=division["budget_seconds"], actual_worked_seconds=actual_seconds, cost_per_worker_minute_minor_snapshot=evaluation.cost_per_worker_minute_minor_snapshot)` and `currency = evaluation.currency.value`; else `NO_BUDGET_SIGNAL` and `currency = NO_CURRENCY`.
- Row dict — **exactly these ten keys, in this order**: `task_id, budget_state, over_seconds, over_cost_minor, projected_over_seconds, projected_over_cost_minor, currency, allowed_seconds, actual_worked_seconds, cost_per_worker_minute_ten_thousandths`.
- Envelope: `{"budget_signals": [...]}`; `warnings` stays `[]` (D7).

### 6.4 Serializer (in `division_serializers.py`, additive)

```python
def serialize_budget_signal(row: dict) -> dict      # copies the ten keys; NO _decimal(), NO str(); ints stay ints
def serialize_budget_signals(rows: Iterable[dict]) -> dict   # {"budget_signals": [...]}
```

### 6.5 Route (in `item_economics.py`, additive)

```python
# Declared IMMEDIATELY after route_get_task_budget_allocations (§7A.4).
@router.get("/tasks/budget-signals")
async def route_get_task_budget_signals(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    task_ids: list[str] = Query(...),
):
    return await _run(get_task_budget_signals, claims, session, query={"task_ids": task_ids})
```

README operationId: `route_get_task_budget_signals_api_v1_item_economics_tasks_budget_signals_get`.
Mirror-test row: `("GET", "/api/v1/item-economics/tasks/budget-signals", _ADMIN_MANAGER)`.
Router-test row (in `_ROUTES`): `("GET", "/api/v1/item-economics/tasks/budget-signals?task_ids=tsk_1", None)`.

### 6.6 Wire vocabulary

| Field | JSON | Values |
|---|---|---|
| `budget_state` | string | exactly `no_budget \| over \| projected_over \| within_budget` |
| `currency` | string | exactly `swedish_krona \| danish_krona \| euro \| no_currency` |
| the eight numerics | number (JSON integer) | `>= 0`; never `null`, never a string |

### 6.7 Architecture-graph ids (recorded at phase close, §8)

`projection-item-economics-task-budget-signals` (phase 2),
`endpoint-item-economics-task-budget-signals` (phase 3). Parent `domain-item-economics`.
Names/descriptions are the implementer's, evidence spans from the tree they close on.

### 6.8 Test fixture vocabulary (shared by all three test files)

Fixtures build section rows **only** through `divide_production_budget` with `DivisionStep`
inputs and `SelectedTypical` typicals (`tests/unit/domain/item_economics/test_budget_division.py:15-33`
shows the `selected(...)`/`step(...)` helpers to copy locally — copy, do not import from a
test module). A hand-built section dict is forbidden (intention §3A.4 note, §11 R8-b).
Every expected figure in a plan's criteria table is **derived** — the planner's probe is
reproduced in each plan's §7 and the implementer re-runs it in Task 0.

## 7. Sequencing & gates

```
phase 1 (pure rule)  ──APPROVED──▶  phase 2 (service + serializer)  ──APPROVED──▶  phase 3 (route + artifacts + handoff)
```

- Phase 2 imports phase 1's API exactly as §6.2 fixes it; if phase 1's review changes a
  signature, §6.2 is amended **here** before phase 2 is dispatched.
- Phase 3 is the only phase that trips the route-mirror tripwires; until it lands the
  mirror tests stay at 26 and green.
- The `to_frontend` handoff is written in phase 3 **after** the route is green, so every
  figure it quotes is measured on the shipped surface.
- **Compaction** is recommended at each APPROVED gate (charter); the coordinator writes the
  context handoff first. Owner's call.

## 8. Tool protocols

**Architecture graph** (`.archgraph/`, permission mode `review`, 204 nodes / 308 edges at
authoring, 6 stale, 3 pending — pre-existing, observations not gates):

- Session start: `archgraph_status`; `archgraph_search_nodes("budget")`;
  `archgraph_get_node` on `projection-item-economics-task-budget-allocations`,
  `endpoint-item-economics-task-budget-allocations`, `decision-money-audience-admin-manager-only`.
- **Never call `archgraph_build_context`** in any session of this project until the
  coordinator lifts this line: `.archgraph/contexts/current-task.md` belongs to a different
  active task and must not be overwritten. Do not read or edit that file.
- Never promote/reject/edit review items; the owner adjudicates.
- **Phase close — one batched `archgraph_apply_changes`**, recording only what the tree
  proves, with evidence spans on the closing commit:
  - phase 1: expected delta **none or one `source_file` node** — a pure module reachable from
    no endpoint yet; state the assessment explicitly even when it is "no delta".
  - phase 2: **one `projection` node** under `domain-item-economics` with `reads_from`
    edges mirroring the sibling's four (`table-task-step`, `table-item-cost-evaluation`,
    `projection-live-worked-seconds`, `table-step-state-record`) and an `implements` edge
    from `source-file-item-economics-budget-division` only if the tree shows the call.
  - phase 3: **one `endpoint` node** with `accepts` → the projection; a governance link to
    `decision-money-audience-admin-manager-only` if the tool supports it.
  - The intended likely total is "one endpoint + one projection + reuse relationships"
    (intention §9 item 5); **record what the implementation proves, not the intention.**

**Pytest** — §10. **Git** — checkpoint commits at `IMPLEMENTED`, gate commits at `APPROVED`;
never squash checkpoints.

## 9. Standing rules

The charter's rules 1–16 apply in full. Project-specific, each with its reason:

1. **Session write perimeters are closed.** *(Coordinator finding, 2026-08-24.)* The
   mechanism-inventory session wrote `docs/archgraph-anchor-observations.md` outside its
   prompt's stated perimeter, discharging an external standing brief. It declared the write
   honestly — and it is still a perimeter breach: **an external standing brief never silently
   expands a prompt's explicit allowed-files list.** A session that believes it must write
   elsewhere stops, reports the conflict in its handoff, and lets the coordinator rule.
   *Process lesson only — no product requirement, no criterion.*
2. **Section rows come from the allocator, never from a dict literal.** §3A.4's note and
   §11 R8-b: a hand-built row with positive `left_seconds` under a negative pot is a state
   the allocator cannot emit, and a criterion built on it cannot fail. Every fixture in this
   project calls `divide_production_budget`.
3. **Every expected figure is re-derived, not copied.** Task 0 of each phase re-runs the
   plan's §7 probe on the implementer's tree and diffs the output against the criteria table
   before a single test is written. A mismatch is a finding against the plan, not a number
   to "correct" in the test.
4. **The terminal predicate has two forbidden spellings** (§3A.2): a typed-out string set
   *and* membership in `TERMINAL_STEP_STATES` itself. The only admissible forms are the
   derived value set or `budget_division._step_state_is_terminal`.
5. **Money is a call.** Any arithmetic on seconds × rate outside `calculator.py:326` is a
   defect, however clean (§4A.1 lists the three prohibited derivations for grep).
6. **Four pre-existing files, no more** (HC-2a; M6). Any other pre-existing file in a diff
   is an automatic finding. Sibling *test* files included — copy their fixtures, never edit
   them.
7. **Rows that cannot fail — the six this project invites** (inventory §6): equal typicals
   under §3A.1; no completed section under §3A.2; a two-call ordering test that does not
   reverse the request; an infeasible fixture that always logs work; a `no_budget` fixture
   with no logged time; a both-pairs fixture that keeps `over` and `projected_over` exclusive.
   Each plan's criteria name the fixture that escapes the trap; the implementer proves it by
   running the named mutation and recording the red.
8. **Identity is a prefix, not a code** (§7A.3, `05_errors_local.md`): assert
   `error.startswith("BUDGET_SIGNALS_TOO_MANY_TASK_IDS:")`, never the whole sentence.
9. **Do not write "digest" or "fingerprint" in the new domain module** — the purity guard
   greps module text (§6.2).
10. **Frontend documents are immutable once published** — the 2026-08-23 and 2026-08-24
    `from_frontend` files are never edited; the answer is a **new dated** `to_frontend` file.
11. **The evidence budget is exactly one L4 per cycle**, taken on the handed-over tree.
    Mutations run at L1 (the phase's test file) unless a criterion names a wider bite set.
    Baseline comparison is by **failing-ID set**, never by count (§10).

## 10. Environment topology

Verified this session (2026-08-24) against `app/pytest.ini`, `app/Makefile`,
`tests/conftest.py`, `tests/database_isolation.py`, and the last published stamp. **If reality
disagrees, update this section.**

- **Working directory `backend/app/`.** Interpreter `.venv/bin/python`; `PYTHONPATH=.` is
  required (the `Makefile` targets carry it).
- **Levels and exact commands** (charter scopes):
  - **L1** — `PYTHONPATH=. pytest <file>` or `<file>::<test_id>` — the default for every
    named mutation and criterion check.
  - **L2** — `PYTHONPATH=. pytest tests/unit/domain/item_economics tests/integration/services/queries/item_economics tests/unit/routers/api_v1 tests/unit/routers/test_phase9_item_economics_route_mirror.py tests/unit/docs` — the item-economics radius (**147 tests** collected across the five files this project touches or mirrors, **67** in `tests/unit/docs/`; both counts derived by `--collect-only -q` this session).
  - **L3** — `PYTHONPATH=. pytest tests/integration -m integration`.
  - **L4** — `PYTHONPATH=. pytest -m 'not e2e'` (the `make test` target). **Reserved** for the cycle stamp, review entry on a changed tree, the gate, and absence claims rooted in the repository.
- **The suite is parallel and nothing announces it**: `pytest.ini` `addopts = -ra --strict-markers --strict-config -n 6 --dist loadfile`. `-n 0` is the serial comparator. `asyncio_mode = auto`; markers `unit / integration / e2e` are strict.
- **Databases.** Postgres on `localhost:5433` (`.env` `DATABASE_URL`). Each pytest process creates its own disposable database from the migrated template `beyo_test_<slot>_template` and drops it at session end (`tests/database_isolation.py`); `BEYO_TEST_SLOT` (`[a-z0-9]{1,12}`, default `main`) discriminates checkouts. **Never run two suite sessions concurrently in one checkout** — they destroy each other's `beyo_test_main_gw0…5`. The development database `beyo_manager` is never a target. Tests that commit rows own their teardown (charter rule 11½ — the sibling test's `_cleanup` shows the pattern).
- **Redis** must be reachable at `settings.redis_url`; without it the machine measures 23 failed / 2 errors instead of the baseline. Check Redis before concluding a baseline moved.
- **Last published stamp (cited, not measured by this session):** **21 failed / 2716 passed / 1 skipped**, `narrow_typical_work_times` plan-6 closeout, 2026-08-24. **`app/` on this tree is byte-identical to that gate tree** (`git diff --stat 49a6e50 HEAD -- app/` empty), so the stamp describes the tree phase 1 starts from. The durable comparator is the **21-ID failing set**, enumerated in `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7; two named intermittents are **not** members and one unrecoverable failure **is**, so a single run is not evidence — repeat and ID-diff before concluding the set changed, and capture the failing-ID set before repeating an anomalous run.
- **The planner ran no tests** — planning used `--collect-only` and pure-domain probes only (charter: no L4 in a planning session). Phase 1's implementer takes the first stamp of this project on its own tree.
- **Host timezone** matters only for datetime-handling mutations; this project's arithmetic is clock-free, but plan 2 C7 injects `ctx.now` — run its mutation under `TZ=UTC` and the host zone.
- **Docs guard:** `PYTHONPATH=. pytest tests/unit/docs/` (67 tests, ~5 s) before and after any write under `docs/handoff/`. The `to_frontend` handoff is swept only by `test_retired_inline_refusal_identity_is_absent_from_live_sources` (an rglob over `docs/handoff/**/*.md`) — do not name the retired identity.
- **Migrations:** none in this project (HC-1). Should any session believe one is needed, it stops — that is a gate re-open, not a task.
- **Residue:** the suite leaves rows from tests outside this pipeline; row-count drift is never evidence of a code change.
