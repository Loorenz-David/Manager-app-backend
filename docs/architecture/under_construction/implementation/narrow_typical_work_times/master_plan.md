# Master plan — `narrow_typical_work_times`

```
plan: master_plan
role: implementation-planner
round: 0
date: 2026-08-22
status: IN PROGRESS — phase 1 APPROVED 2026-08-22; phases 2–6 NOT_STARTED
intention: planning/intention.md (RESOLVED round 8, D1–D25 settled, gate PASS-WITH-CONTRACTS)
```

**⚠ Read the intention's header before any section of it.** It carries a
**section-letter precedence rule**: where a lettered section and the numbered section it
amends disagree, the letter wins. §4A supersedes the signature and call forms in §3.1,
§4.2 and §5; §4B supersedes §4.4; §4B+§4C supersede §4.4/§4.5's reachability; §4C (D25)
amends §3.4's `BROADEN_TO_SECTION` first rung, §4.3's quantifier and §11A rows T10b/T16b;
§6B supersedes §6.4's `is_estimated`. A plan built from a superseded numbered section
alone is the failure mode those pointers exist to prevent.

---

## 1. Goal

Make the typical work time of a working section item-aware — history narrowed to work
comparable to the task at hand (V1: same item category as the task's active PRIMARY
item) — through **one** centralized engine that all four consumers use, so a worker, a
manager and the budget-division arithmetic can never see three different "typicals" for
the same task and section.

Product semantics live in `planning/intention.md` and are **not** restated here. This
document carries only what every phase shares: the tracker, the naming registry, the
sequencing gates, the environment, and the standing rules.

---

## 2. Sources of truth

| Content | Artifact |
|---|---|
| Product semantics, domain invariants, mechanism contracts | `planning/intention.md` |
| Owner decisions D1–D25, verbatim | `planning/owner_decisions.md` |
| Mechanism inventory (18 ranked mechanisms) and the gate's reasoning | `handoffs/reviewer/20260822_mechanism_inventory_gate_handoff.md` |
| Naming registry, contract resolution, environment topology, standing rules, tracker | **this file** |
| Phase-local goal / files / tasks / criteria + Review log | `plans/plan_<n>.md` |
| §12 query-cost measurements (10 rows) | `planning/query_cost_measurements.md` (created in phase 2) |
| Session framing | `prompts/<role>/`, generated just-in-time, never reused stale |
| Neighbouring approved authority (settled-basis, clock, allowance independence) | `docs/architecture/archives/live_clock_for_working_time_economics/planning/intention.md` §1A HC-3A, §2.5A, §4.3A |
| The D23 approval baseline (runner, Redis, 21-ID set) | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7 |
| The earned-rules corpus (~30 rules, **binding, adopted by reference**) | `docs/architecture/archives/simple_valuation_editor/master_plan.md` §5 |

**Fold-back rule.** A semantic change amends the **intention**; a skeleton change amends
**this file**; a phase-local change amends **its plan file**. Nothing is patched
downstream into divergence. Amendments never renumber sections other documents cite —
insert lettered sections instead.

**Archive ritual (charter layout, plus one recorded extension).** Rows move to
`archive/plan_<n>/` **at the phase's approval gate, in the gate commit** — never earlier:
a row's folder *is* its state, and several handoffs stay **live inputs** until their phase
closes (plan 1's read-first list cited its own projection and implementation handoffs
while the phase was open). Historical path references are **not** rewritten; they resolve
under the archive by convention.
*Extension (owner question, 2026-08-22):* the charter partitions the archive by phase, but
this project has **project-level** rows belonging to no phase — the planner prompt and
handoff, the voided calibration seal, and the previous coordinator's orientation document.
They live in **`archive/planning/`**, closed after the plan set was folded.
*The one deliberate exception:* the **mechanism-inventory gate prompt and handoff stay
live** until the project closes — §2 above cites the handoff as a standing source of truth
and plans 1–6 read it, so archiving it mid-project would break live read-first lists.

---

## 3. Roles & session workflow

- **Implementer sessions may be Codex.** The coordinator compiles a self-contained prompt
  directing the session to read `/Users/davidloorenz/agent-skills/pipeline-charter.md` and
  `/Users/davidloorenz/agent-skills/implementation-executor.md` by absolute path.
- **⚠ TESTS FIRST, from phase 2 onward — the criteria table IS the test file** (owner
  ruling, 2026-08-22, after phase 1 took four implementation rounds to produce a normal
  1.4:1 test-to-production ratio). Every implementer prompt's **task 0** is: *transcribe
  every criterion row in §6 into the test files as executable cases, before writing a line
  of production code; run them; they must be red for the right reason.* Only then
  implement to green, then run the named mutations.
  **Why this is the whole fix and not a style preference:** of the thirteen findings
  phase 1's audits produced, **eleven were "a row the plan enumerates is missing from the
  tests" or "a row is present but its assertion projects away the field the criterion
  names"** — the entire class is a transcription failure, and transcription failures are
  invisible after the fact but obvious while transcribing with the plan open. The three
  audit passes were each spent re-deriving a comparison the implementer could have made
  in the first ten minutes.
  Corollaries: a row that cannot be transcribed is a **plan defect — stop and report**,
  not a row to invent (that is the projection gate's decidability check, cashed at the
  right moment); and a criterion's **prose** clauses transcribe too, not just its row
  table (§9's closing-sentence rule).
- **Reviewer sessions are Opus 5 — never Sonnet as the only reviewer.** Measured
  head-to-head on an identical tree: Sonnet APPROVED a phase carrying an inert safety
  switch and a silent `DROP DATABASE`, and affirmed coverage that did not exist by
  trusting the implementer's ledger. Sonnet may run as a *comparison* reviewer beside
  Opus 5, never instead of it.
- **Projection sessions** (`plan-projection` doctrine) run under the reviewer role's
  tables as `round: 0`.
- **State machine:** `NOT_STARTED → PROJECTED → PROMPT_READY → IMPLEMENTING →
  IMPLEMENTED → REVIEWING → CHANGES_REQUESTED (→ IMPLEMENTING) → APPROVED`.
  **⚠ A session's gate check names the state that exists when the session opens, not the
  state that existed when the prompt was written.** Compiling an implementer prompt *is*
  the `PROJECTED → PROMPT_READY` transition, so an implementer prompt gates on
  `PROMPT_READY` — never on `PROJECTED`. Earned 2026-08-22: the phase-2 prompt gated on
  the pre-transition state and a session correctly refused to start.
  **The coordinator writes the gate check after advancing the state, and re-reads the
  tracker while writing it.** And the corollary for the session: **a gate check that
  disagrees with the tree is a coordinator defect — stop and report it. Never edit the
  tracker or the plan header to match your own instructions**, which would convert a
  prompt typo into a false project state.
- **The PROJECTED gate is risk-triggered.** It is **mandatory** for every phase that
  touches a rule-6 silent-failure mechanism; §7 states the trigger per phase. Waivers are
  the coordinator's, with a recorded one-line justification. Two consecutive empty
  ledgers demote the gate to optional for this project — record the demotion here.
- **Checkpoint commits.** Every implementation and every fix cycle is committed the
  moment it reaches `IMPLEMENTED`: subject prefixed `CHECKPOINT (not approved):`,
  **explicit paths only, never `git add -A`**, under the owner's standing authorization
  so no round stops to ask. Never squashed. The phase is committed again at its approval
  gate.
- **Re-review after a fix cycle** is delta-scoped with a verified perimeter: `git diff`
  confirms only the fix prompt's allowed files changed; full adversarial depth on the
  changed seam; evidence per §10; settled areas are not re-verified, but anything seen
  wrong in passing is reported.
- **Do not push.** The branch is deliberately ~127+ commits ahead of `origin/main`.

---

## 4. Progress tracker

| # | Phase | State | Date | Actor | Note |
|---|---|---|---|---|---|
| 1 | Pure typicals domain + the pre-refactor SQL snapshot | **`APPROVED`** | 2026-08-22 | Opus 5 (re-review r2) | Delta re-review: 0 blocking / 0 should-fix / 4 notes / 0 cards. All 9 round-1 findings closed **and biting** (15 L1 probes, 41-test baseline; L4 runs 0 — round-3 stamp consumed by citation and corroborated +8/+8). Notes routed: N6 → plan 4 C0, N7 → plan 2 C0, N8/N9 → plan 1 prose. Rows archived to `archive/plan_1/`. |
| 2 | Statement extension: spec→predicate, K-spec shape, HC-4 + §12 measurements | `IMPLEMENTED` | 2026-08-22 | Codex | Implemented after task-0 criteria transcription. Predicate/query perimeter is green; 11-row EXPLAIN matrix recorded (10 required cells + 50×20 ceiling). Checkpoint handoff ready for review. |
| 3 | `TaskBudgetStatus` carries the derived spec (§6A) | `NOT_STARTED` | — | — | Projection **mandatory** (shipped cross-pipeline dataclass, 5 construction surfaces; the lineage has paid one round on it). No payload change anywhere. |
| 4 | Division contract + production-time + budget-allocations | `NOT_STARTED` | — | — | Projection **mandatory** (settled-basis guard — the neighbouring pipeline's "most expensive mistake available in this feature"). Two goldens regenerate, keys only. |
| 5 | Price-scenario: injected clock, shared reconciliation, §6B | `NOT_STARTED` | — | — | Projection **mandatory** (`is_estimated` reverses a shipped payload value if read literally; the clock move extends an APPROVED pipeline's determinism contract). |
| 6 | Closeout: frontend handoff, living docs, graph delta | `NOT_STARTED` | — | — | Projection **waivable** — no rule-6 code surface. Never edits a published handoff. |

Agents update only their own row. Findings go to the plan file's Review log.

---

## 5. Contract resolution

**⚠ Corrected at the plan-1 projection fold (2026-08-22, projection R1).** This section
originally stated the repo has no `architecture/*.md` contract system, reasoning from
`docs/architecture/`. **The system exists at the repo root: `backend/architecture/` — 69
files, README "Canonical backend contracts live here."** Its index is thin (a three-line
README, no goal-mapping guide), so the charter's standing rules (§9) plus the earned-rules
corpus remain the *routing* baseline — but the `architecture/*.md` files are
**authoritative for how code is written**, and three bind this pipeline directly:

- `architecture/01_architecture.md` — layer map and hard dependency rules.
- `architecture/08_domain.md` — domain purity (F-J's independent source) and **"fully
  annotated signatures, no `Any`"** (constrains §6.2's two loosely-written signatures;
  the resolution is delegated in plan 1's implementer prompt: a local `Protocol`, never a
  `models.tables` import).
- `architecture/15_testing.md` — "test files mirror the module they test."
  **Two recorded deviations, deliberate:** `test_participating_sections.py` splits
  `budget_division.py`'s coverage by mechanism rather than mirroring it 1:1, and
  `test_typical_times_sql_identity.py` names its *claim* (SQL identity) rather than its
  module (`get_working_section_typical_times.py`) because plan 2 extends it across the
  refactor boundary. Recorded here so neither reads as a silent violation.

Any phase touching errors, commands, queries or routers reads the matching numbered file
before writing.

Two further affordances the charter's detection finds, and every session honours:

1. **Architecture graph** (`.archgraph/` + `archgraph_*` MCP) — §8.
2. **Living docs under `docs/domains/item_economics/`**, guarded by
   `app/tests/unit/docs/test_item_economics_docs.py` (four files: `README.md`, `api.md`,
   `events.md`, `states.md`, each pinned to its semantic authorities) and
   `test_item_economics_handoff_accuracy.py`. Any phase changing a published payload or a
   method constant checks whether the guard names a file it must update — the guard, not
   judgement, decides.

---

## 6. Shared skeleton & naming registry

Every name below is fixed here **once**. A phase that needs a name not in this table adds
it here in the same edit, before using it.

### 6.1 New and moved modules

| Path | Phase | Contents |
|---|---|---|
| `app/beyo_manager/domain/item_economics/typical_constants.py` | 1 | **NEW.** `TYPICAL_METHOD`, `TYPICAL_WINDOW_DAYS`, `TYPICAL_MIN_SAMPLE_SIZE`, moved here verbatim. Values unchanged. |
| `app/beyo_manager/domain/item_economics/typical_filters.py` | 1 | **NEW.** The pure engine (§6.2). |
| `app/beyo_manager/services/queries/working_sections/_typical_item_filter.py` | 2 | **NEW.** `build_item_match` — the only module that knows Task → primary TaskItem → Item. |
| `app/beyo_manager/domain/item_economics/budget_division.py` | 1, 4 | **MOD.** Imports and **re-exports** the three constants (its `__all__` already lists all three, so no existing import site changes); its `_median` moves to `typical_filters.median` and is imported back (internal call sites rename); gains `participating_sections`; phase 4 changes the division contract. |

**Why the constants move (planner decision, reported in the handoff).**
`typical_filters` needs `TYPICAL_MIN_SAMPLE_SIZE`; `budget_division` needs
`apply_business_fallback` from `typical_filters` at runtime (D22/§8: one implementation,
two terminals). That is a circular import. Moving the three constants to a leaf module and
re-exporting them from `budget_division` breaks the cycle, changes no value, and changes
no call site — `budget_division.__all__` already exports all three
(`budget_division.py:402-410`). Import direction after this pipeline:
`typical_constants ← typical_filters ← budget_division`.

**The median moves too (plan-1 projection fold, ledger L1).** `apply_business_fallback`
needs `median(usable)` (§8, plan 1 C11 row d), and plan 1's import direction forbids
`typical_filters` importing `budget_division`, where `_median` lives
(`budget_division.py:69`). A second copy whose even-length rule drifts from
`(a+b)/2` would silently move phase 4's allowances. Resolution: **`_median` moves
verbatim into `typical_filters.py` as public `median`** (it gains external callers), and
`budget_division` imports it from there — an edge that already exists at runtime for
`apply_business_fallback`, so no new dependency. `budget_division`'s internal call sites
rename `_median(` → `median(`; no behavior change. The even-length rule is pinned by
plan 1 C18.

### 6.2 `typical_filters.py` — the fixed API

```python
COMPARABILITY_PROFILE = "primary_item_category_v1"
RECONCILIATION_METHOD = "uniform_basis_v1"

@dataclass(frozen=True)
class TypicalFilterSpec:
    item_category_ids:   frozenset[str] | None = None
    major_categories:    frozenset[ItemMajorCategoryEnum] | None = None
    width_cm:            tuple[int | None, int | None] | None = None   # inclusive (min, max)
    height_cm:           tuple[int | None, int | None] | None = None
    depth_cm:            tuple[int | None, int | None] | None = None
    can_have_upholstery: bool | None = None
    designers:           frozenset[str] | None = None
    # __post_init__ canonicalizes per §3A C1; @property is_narrowing

def derive_spec_from_primary_item(item) -> TypicalFilterSpec: ...
def parse_spec_from_query_params(params) -> TypicalFilterSpec: ...

@dataclass(frozen=True)
class SectionTypicalEvidence:
    working_section_id: str
    narrowed_typical_worker_seconds: int | None
    narrowed_sample_count: int
    section_typical_worker_seconds: int | None
    section_sample_count: int
    # @property has_narrowed / has_section / has_usable_narrowed   (§3.3, §4C)

class TypicalResolutionPolicy(Enum):
    BROADEN_TO_SECTION = "broaden_to_section"
    ANSWER_AS_ASKED    = "answer_as_asked"

def resolve_section_typical(evidence, spec, policy) -> SelectedTypical: ...

@dataclass(frozen=True)
class SelectedTypical:
    working_section_id: str
    typical_worker_seconds: int | None
    typical_basis: str                    # item_narrowed | section_wide | insufficient_sample
    evidence: SectionTypicalEvidence
    participates: bool
    sample_count: int                     # the population typical_basis names (§3.6, §3B B3)

@dataclass(frozen=True)
class TaskTypicalSelection:
    task_typical_basis: str               # item_narrowed_uniform | section_wide_uniform
    reconciliation_method: str
    comparability_profile: str
    applied_filter: TypicalFilterSpec | None
    participating_section_ids: frozenset[str]
    selected: Mapping[str, SelectedTypical]

def reconcile_task_typicals(
    evidence_by_section: Mapping[str, SectionTypicalEvidence],
    spec: TypicalFilterSpec | None,
    participating_section_ids: frozenset[str],
    section_ids: frozenset[str],
) -> TaskTypicalSelection: ...

def apply_business_fallback(
    selected_values: Sequence[int | None], *, terminal: Fraction
) -> list[Fraction]: ...

def median(values: Sequence[Fraction]) -> Fraction: ...
    # moved verbatim from budget_division._median (projection fold, L1);
    # even-length rule (ordered[m-1] + ordered[m]) / 2 is contract — plan 1 C18
```

Three of these signatures are **planner-fixed** because no upstream artifact states them
(reported in the handoff, not owner-decidable):

- `apply_business_fallback` — §8 writes `-> resolved values`. Fixed as order-preserving
  `Sequence[int | None] -> list[Fraction]`, `terminal` keyword-only, with an
  `isinstance(terminal, Fraction)` **entry guard that fails closed** (§11A T14's repair,
  charter rule 11). Callers zip the result against their own ordered section ids.
- `reconcile_task_typicals` — written nowhere. `section_ids` is the task's **full** section
  set (§3.5: `selected` covers every section in the task, including excluded), and it is
  what makes §3B B4 total: a section id present here and absent from `evidence_by_section`
  yields the zero-evidence row, never a `KeyError`.
- `SelectedTypical.sample_count` — §3.6 defines the value but §3.5's shape omits the field.
  Carried on the object so no consumer re-derives §3.6's rule (the fork HC-1 forbids).

### 6.3 `_typical_item_filter.py` — the fixed API

```python
def build_item_match(spec: TypicalFilterSpec) -> tuple[bool, ColumnElement | None]:
    """(needs_category_join, predicate). predicate is None exactly when
    spec.is_narrowing is False."""
```

### 6.4 `budget_division.py` additions

```python
def participating_sections(steps: Sequence[Any]) -> frozenset[str]: ...
```

Home per §6.1: beside the division, because `EXCLUDED_STEP_STATES` and
`_step_state_is_excluded` already live there and it is domain vocabulary. All three task
services **and** `divide_production_budget`'s internal `allocated_groups` predicate resolve
to this one implementation.

### 6.5 Wire field names (§7)

Per-section `typical` block (production-time): `typical_worker_seconds`, `sample_count`,
**`typical_basis`**, **`narrowed_sample_count`**, **`section_sample_count`**, `method`,
`window_days`, `min_sample_size`.

`steps[]` (budget-allocations): existing keys + **`typical_basis`**, **`sample_count`**.
`narrowed_sample_count` / `section_sample_count` are deliberately **omitted** here.

Task-level `typical_resolution` (identical object on production-time, budget-allocations
and price-scenario):

```jsonc
"typical_resolution": {
  "task_typical_basis": "section_wide_uniform",
  "reconciliation_method": "uniform_basis_v1",
  "comparability_profile": "primary_item_category_v1",
  "applied_filter": {"item_category_ids": ["icat_chair"]},   // null when the spec is empty
  "participating_section_count": 3,
  "sections_by_basis": {"item_narrowed": 0, "section_wide": 2, "insufficient_sample": 1}
}
```

Serializer names (home `domain/item_economics/division_serializers.py`, imported by
`serializers.py` for the price-scenario block so there is one implementation):
`serialize_filter_spec(spec) -> dict | None`, `serialize_typical_resolution(selection) -> dict`.

**Every new field is non-nullable with an explicit default and always present** — the
standing frontend requirement; nullable-then-absent fields have taken the frontend down
twice. `applied_filter` is the one deliberate `null`, and it is always the key `"applied_filter"`.

### 6.6 Statement result columns (§4A K2)

```
len(specs) == 0  ->  (client_id, name, sample_count, typical_worker_seconds)      # today's shape
len(specs) == K  ->  (client_id, name, spec_index,
                      section_sample_count,  section_typical_worker_seconds,
                      narrowed_sample_count, narrowed_typical_worker_seconds)
```

`spec_index` positionally indexes the caller's own `specs` sequence. **No spec hash,
digest or fingerprint is introduced anywhere in this pipeline.**

### 6.7 Method constants after V1

| Constant | Value | Home | Changes? |
|---|---|---|---|
| `TYPICAL_METHOD` | `median_completed_section_totals` | `typical_constants.py` | no |
| `TYPICAL_WINDOW_DAYS` / `TYPICAL_MIN_SAMPLE_SIZE` | 90 / 5 | `typical_constants.py` | no |
| `ALLOCATION_METHOD` | **`static_proportional_section_v2`** | `budget_division.py` | **yes**, phase 4 (§6.3, D20) |
| `COMPARABILITY_PROFILE` | `primary_item_category_v1` | `typical_filters.py` | new |
| `RECONCILIATION_METHOD` | `uniform_basis_v1` | `typical_filters.py` | new |

### 6.8 Deferred statistics-route query parameters (planner-fixed)

`parse_spec_from_query_params` ships in phase 1 with full unit coverage (§9: the parser and
the `ANSWER_AS_ASKED` branch ship **now**; retrofitting policy later would re-open
`resolve_section_typical`'s contract). Its parameter names are fixed nowhere upstream, and
they become the deferred route's public contract, so they are fixed here:

`item_category_ids` (repeatable) · `major_categories` (repeatable) · `designers`
(repeatable) · `width_cm_min` / `width_cm_max` · `height_cm_min` / `height_cm_max` ·
`depth_cm_min` / `depth_cm_max` · `can_have_upholstery`.

A band with only one bound supplied yields `(lo, None)` / `(None, hi)`; both absent means
the field is not set at all — **not** `(None, None)`, which is a different population
("the dimension is recorded", §3A C2). Unknown parameters are ignored.

**Request grammar (plan-1 projection fold, ledger L8/L9; semantics in intention §3C).**
The parser's input is the router's **already-typed** `ctx.query_params` dict — this
repo's universal router convention (typed FastAPI `Query(...)` parameters assembled into
a plain dict; nearest instance `routers/api_v1/working_sections.py`, typical-times
route). Signature: `parse_spec_from_query_params(params: Mapping[str, object]) ->
TypicalFilterSpec`.

- Repeatable families (`item_category_ids`, `major_categories`, `designers`) arrive as
  `Sequence[str] | None`; bounds as `int | None`; `can_have_upholstery` as `bool | None`.
- **An absent parameter arrives as an absent key OR an explicit `None` value — the two
  are equivalent** (routers pass `None` for unset `Query(None)` params).
- String→int coercion, numeric parse failures and boolean spellings are the future
  route's FastAPI declarations — **outside the parser's contract**.
- `major_categories` values convert to `ItemMajorCategoryEnum`
  (`domain/items/enums.py`); an unrecognised value raises **`ValidationError`** (§3C) —
  silently ignoring it would answer a different narrowed question than asked.
- An inverted band (`lo > hi`) raises **`ValidationError`** at the parser boundary
  (§3C); `TypicalFilterSpec.__post_init__` keeps `ValueError` for direct construction.
- An empty sequence for a repeatable family canonicalizes with §3A C1 (→ `None`).
- **A bare `str`/`bytes`, or any non-iterable, is rejected with `ValidationError` for
  every repeatable family** — symmetrically (intention §3C, plan-1 review S2). A `str`
  structurally satisfies `Sequence[str]`; iterating it character-wise yields a spec that
  narrows to a population of zero, silently.

### 6.9 Test files and fixtures

| Path | Phase |
|---|---|
| `app/tests/unit/domain/item_economics/test_typical_filters.py` | 1 |
| `app/tests/unit/domain/item_economics/test_participating_sections.py` | 1 |
| `app/tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py` | 1 |
| `app/tests/unit/services/queries/working_sections/snapshots/typical_times_no_spec_sql.txt` | 1 (**captured pre-refactor**) |
| `app/tests/unit/services/queries/working_sections/test_typical_item_filter.py` | 2 |
| `app/tests/integration/services/queries/working_sections/test_typical_times_narrowing.py` | 2 |
| `app/tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py` | 3 |
| `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py` | 4 |
| `app/tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py` | 5 |
| Seeded narrowing fixture: `seed_narrowing_history(...)` in `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py` | 4 (created), 5 (reused) |

The seeded fixture (§11.1): chair category; ≥5 same-category completed groups in two
sections, <5 in a third; one task with no active primary item in history; one task with a
removed primary and a current one; one task with one PRIMARY + two secondary items. The
**live-clock golden fixture is NOT taught to narrow** — item-aware cases live here.

---

## 7. Sequencing & gates

Strictly serial. **A phase starts only on its predecessor's `APPROVED`** — D23's serial
ruling, and the corpus rule *parallel phases share a baseline* (two phases with disjoint
file perimeters still collided, because a test's roots are not a perimeter).

```
1 (pure domain + pre-refactor snapshot)
  → 2 (statement + §12 measurements)
      → 3 (TaskBudgetStatus spec carrier)
          → 4 (division + production-time + budget-allocations)
              → 5 (price-scenario)
                  → 6 (closeout)
```

Four sequencing constraints are **structural**, not preferences:

1. **The T11 frozen snapshot is captured from the PRE-refactor tree** (§4A K5, §11A). The
   pre-refactor compiled SQL string is committed in **phase 1**, before any statement
   change lands. It cannot be retrofitted honestly after phase 2 — a snapshot taken from
   the changed function is `f(x) == f(x)` and survives any mutation of `f`.
2. **§12 is a conditional-acceptance gate.** The matrix is **5 shapes × 2 statements = 10
   measurements** — single task; batch of 50 tasks × 5 categories; × 10; × 20; the no-spec
   shape — each measured against the **current** statement and the **new** one. §12 states
   no count, and an unstated count is where a matrix silently ships at 6: **enumerate all
   ten; a silent subset is a gate failure.** Recorded in
   `planning/query_cost_measurements.md`. Phase 2's acceptance, and every phase downstream
   of the statement extension, is conditional on it.
3. **Goldens regenerate once**, on the post-live-clock baseline (D23), keys-only criterion
   (§11.2): **any changed numeric value is a gate failure, not a regeneration.** Both
   changed goldens (`golden_production_time.json`, `golden_budget_allocations.json`) are
   regenerated in **phase 4**, in one act; `golden_budget_status.json` is unchanged by
   every phase. Planner reading of D23, recorded so a reviewer does not read a gate
   failure into two files moving at once.
4. **D18's removal edits two production files** (§6C / §2B S-4) —
   `get_task_production_time.py:50-62` and `get_task_budget_allocations.py:217-229` both
   construct `DivisionStep(..., typical_worker_seconds=None, ...)`. F-F's "only 8 test call
   sites plus fakes" is false since `e7d65b9`. Both are inside phase 4's perimeter.

**Why the division change forces two consumers into one phase:** changing
`divide_production_budget`'s third parameter to `Mapping[str, SelectedTypical]` breaks both
call sites at once, and a phase must close green. Price-scenario never calls division, so
it separates cleanly into phase 5 — which is also where T6's cross-service equality can
finally be asserted over all three surfaces.

---

## 8. Tool protocols

**Architecture graph.** Measured this session, read-only: **194 nodes / 296 edges,
revision `7241b831c3bd…`, 0 pending / 0 stale / 0 diagnostics.** (The archived live-clock
master plan §6 cites `cec60a24…`, 194 / 291 — a stale citation in an archived document,
not a graph/code disagreement. Cite the measurement, never a document's copy of it.)

Per implementing session:

- **Start:** orient read-only — `archgraph_status`, then the impact context at
  `.archgraph/contexts/current-task.md` (built 2026-08-22, start node
  `projection-working-section-typical-times`, 51 impacted nodes). Do not rebuild it.
- **End:** record the phase's architectural delta as **one batched `archgraph_apply_changes`
  per implementing session**, with accurate evidence spans. Never during planning or
  shaping (intention §13.4).
- **Never** promote, reject or edit a review item — the human adjudicates.
- **Evidence summaries are immutable** through both review and maintenance. **Never put a
  count in one**; describe what the evidence shows. A stale number can only be corrected by
  rejecting the item and re-recording it.
- **`archgraph_repair_anchors` takes one operation per call** — a multi-operation batch
  returns `INTERNAL_ERROR` with empty `details` and writes nothing. Read the two open
  tooling findings in `docs/architecture/under_construction/implementation/archGraph_mapping_mantainance/open/`
  before any repair call.
- A graph node that disagrees with the code is **filed** via the `archgraph-discrepancies`
  skill, never worked around silently.

Expected deltas by phase: 1 — new domain module; 2 — new query module + the typical-times
projection's changed contract; 4 — the division contract and two projections; 5 — the
price-scenario projection's clock; 3 and 6 — likely none, which is a claim to check
against timestamps, not to assert (four "no delta" claims in the neighbouring pipeline
were wrong, and only the timestamps showed it).

---

## 9. Standing rules

Charter rules 1–14 apply in full, plus the **~30-rule earned corpus** adopted by reference
in §2. Restated here only where they bite hardest on *this* feature:

- **Rule 6 — effort by silent-failure risk.** Five of the inventory's mechanisms are
  **Critical**: spec→predicate translation, the K-spec result shape, spec dedupe identity,
  the two-population `FILTER` arithmetic, and the settled-basis guard. Every phase touching
  one is projection-mandatory (§4) and gets ledger-grade mutation evidence.
- **Rule 11 + 12 — a named mutation names its site (file · definition-vs-call-site), and
  one mutation per sub-check.** §11A found **five** of the intention's own mutations inert
  (T5, T7, T11, T14, T19) and repaired them. **Do not re-introduce the inert forms.** Every
  mutation in these plans states the value under the contract and the value under the
  mutation, and they differ.
- **Rule 2 — enumerate, never sample**, with its companion: each row's fixture makes its
  own predicate the ONLY reason its outcome holds. Applies to ranked ladders, to `>=`
  boundaries (two rows, not one), to error contracts, and to **prose** — a sentence with a
  count in it is a checklist.
- **Rule 3 — invariants proven on the production object type.** Rows that constrain
  `participating_sections`, `derive_spec_from_primary_item` and the `TaskBudgetStatus`
  spec hold real ORM instances, never hand-built dicts.
- **Rule 13 — assert the contract, not the literal**, *except* where the literal **is** the
  contract: `static_proportional_section_v2`, `primary_item_category_v1` and
  `uniform_basis_v1` are version strings the frontend keys on, so they are asserted as
  exact literals. Sample floors are asserted through `TYPICAL_MIN_SAMPLE_SIZE`, never as `5`.
- **Prefer an exact literal over an equality between two calls.** `f(a) == f(b)` throws away
  the discriminating power; two literal assertions keep it. This killed four inert checks in
  the lineage, two of them the coordinator's.
- **Before citing a test as proof of a SQL predicate, check that the test issues SQL.**
  `_TypicalSession.execute` in `test_price_scenario_query.py` discards the statement and pops
  pre-built results — eight `_typical_block` tests never issue SQL. Phase 5 must not inherit
  that blind spot for its new predicates.
- **Every `max(`, `min(` and `or 0` in a contract is a candidate criterion row.** §11A's own
  correction to §8 is this rule firing: the division terminal `Fraction(1,1)` is a
  **division-by-zero guard**, not only a weight choice, and T4's swap mutation reddens by
  **raising**.
- **Absence claims state their root and their term set**, or are restated as the presence
  claim they stand in for. Run them from the **repository root**.
- **Grep the whole repository for a symbol before moving or renaming it — a leading
  underscore is a convention, not a guarantee.** Earned in phase 1 (2026-08-22): moving
  `budget_division._median` broke `get_task_price_scenario.py:13`, which imported the
  private name across modules. Neither the plan, the projection, nor the coordinator
  checked; the full suite found it as **27 collection errors**. The bridge alias is
  routed out in plan 5 task 0.
- **A criterion's closing sentence is a criterion.** Earned at plan 1's review: C8's
  closing line — *"both sides are exact-literal assertions … on each section's tuple"* —
  was the one line no session implemented, and it carried **three** of the review's
  findings while the row table above it looked complete. When a criterion states its
  assertion *shape* in prose after its rows, that prose gets its own enumerated mutation,
  or it lapses silently.
- **When a criterion proves "this branch never reads X", at least one row must make X's
  value differ from the value the branch does read.** Plan 1's C7 proved policy
  independence with rows whose two populations were equal by construction, so no row
  could tell `has_section` from `has_narrowed`; the mutation swapping them left the whole
  phase suite green.
- **"Identical object" criteria must name the fields the assertion compares.** A row that
  differs from another only in a field the assertion projects away is a duplicate: C7's
  T17 pair asserted three of six fields, so it proved identity of the projection, and
  `participates` survived unconstrained.
- **A guard that walks a directory needs a row proving the walk found something.** Phase
  1's purity guard accumulated **three** escapes in one small file and all three shared a
  shape — the guard's own preconditions were unasserted: a non-recursive walk, an
  exception that stripped every occurrence instead of the pinned one, and a directory
  scan that **passed vacuously on an empty result**. Assert non-emptiness as a contract,
  never as a literal count. (Closed in plan 4 C0.)
- **Enumerate a mutation's bite set from the code AFTER the repair, never from the finding
  that requested it** — charter rule 12's second half. Phase 1 paid for this twice: an
  attribution was corrected once from the finding, and the correction itself was stale by
  the time the repair landed. **Cheap enforcement, now required:** a fix cycle states,
  per named mutation, **which test id failed**. The implementer already has that output;
  it costs one column and makes the plan's claims falsifiable.
- **"Reject the malformed input" is per-family, and families drift apart.** Phase 1's
  parser fix closed two of four parameter families; a third took any object verbatim and
  a fourth rejected a bare string only because no enum member happened to be one
  character long. A criterion that fixes a boundary for one family **enumerates the
  others** and says which are in scope and which are deferred. (Closed in plan 2 C0.)
- **Absence criteria ship as committed tests, never as a session grep** (charter rule 1;
  the exemption is environment-lifecycle checks only). Plan 1's C4(c) and C17 were both
  re-measured *correct* at review — the defect was the form: nothing in the suite went
  red, so later phases inherited an unguarded claim. A package walk asserting a term set
  costs a few lines; pin any known exception **by name** so removing it does not silently
  widen the claim.
- **Report measured values, not remembered ones.** Two phase-1 handoff claims restated
  measurements inaccurately (a snapshot byte value; an absence grep called "empty" that
  returns one out-of-scope hit). Neither changed a conclusion, and both cost review time
  to re-measure. If a number appears in a handoff, it was read off a command in that
  session.
- **Never rewrite a published handoff.** Supersede with a new dated document (§11.3).
- **Before writing any document under a guarded root, run the guard** —
  `PYTHONPATH=. pytest tests/unit/docs/` costs ~3 s.
- **A criterion that cannot name the defect it would catch is decoration and is cut.** A
  criterion asserting documented third-party behaviour never appears.
  **Sharpened by the owner, 2026-08-22 — apply this at plan-writing time, not at review.**
  The test is: *what would a user, a worker's card, or a downstream consumer see if this
  were wrong?* If the honest answer is "nothing, ever", the row is decoration however
  rigorous it looks. Phase 1 carried four grid rows describing evidence shapes the SQL can
  never produce (a narrowed population larger than the section population containing it);
  they are defensible for a pure function a future caller could misuse, but they are the
  first thing to cut when a criteria table gets long. **Rank rows by what breaks on the
  wire**, and say so in the plan so the implementer and reviewer spend depth in the same
  place. Guards over guards — a test protecting a test's coverage — are the far end of
  this and belong to whichever phase already edits the code they guard, never to a
  dedicated round.
- **A clause that cannot be tested yet is marked `structurally held`** with the named
  trigger that converts it into a real assertion — never left looking testable when it is
  not. This project has exactly one: §3A C3's `coalesce(..., FALSE)` (plan 2, C11).
- **A snapshot compiled without `literal_binds` freezes SQL *structure*, not values**
  (plan-1 review S3, measured 2026-08-22). Every bound value — the percentile, the
  sample floor, the 90-day cutoff, the step-state filter, the workspace id — renders as
  `%(...)s` and cannot move the frozen string: `percentile_cont(0.5)` → `0.6` leaves it
  byte-identical and the test passes. Compiling without `literal_binds` is still the
  right trade (with it the cutoff inlines and the assertion becomes a clock race), but
  **a green HC-4 snapshot criterion means "the shape did not change", never "the
  behaviour did not change"**. Any phase that changes a bound value of a snapshotted
  statement covers it with an integration assertion over real rows. Recorded beside the
  inherited criterion in `plans/plan_2.md` C1.
- **`typical_times_no_spec_sql.txt` is written once, in phase 1, and never regenerated**
  (plan-1 projection fold, ledger L12). A red C15 in any later phase is a **finding**,
  never a regeneration — re-capturing from a changed tree restores exactly the
  `f(x) == f(x)` vacuity §11A repaired T11 to remove. The only authorized re-derivation
  is a SQLAlchemy/dialect version bump, and it requires a recorded authorization line in
  the acting phase's Review log before the write.

---

## 10. Environment topology

Verified this session against `app/pytest.ini` and the published baseline. **If reality
disagrees, update this section.**

- **Working directory `backend/app/`.** Tests: `PYTHONPATH=. pytest -m 'not e2e'`.
  `PYTHONPATH=.` is required; the four `app/Makefile` test targets carry it.
- **The invocation is parallel and nothing announces it.** `app/pytest.ini`'s `addopts`
  carries `-ra --strict-markers --strict-config **-n 6 --dist loadfile**` — six xdist
  workers (verified at source this session). **`-n 0` is the serial comparator.**
- **Redis must be reachable at `settings.redis_url`.** Without it this machine measures
  **23 failed / 2 errors**, not 21. Check Redis before concluding a baseline moved.
- **Databases.** Server `localhost:5433`. Every pytest process creates its own database
  from the migrated template `beyo_test_<slot>_template` and drops it at session end;
  `beyo_manager` is the **development** database and is never a target. `BEYO_TEST_SLOT`
  (`[a-z0-9]{1,12}`, default `main`) is the **per-checkout** discriminator.
- **⚠ Two suite runs in one checkout collide.** They share the default slot, so both target
  `beyo_test_main_gw0…gw5` and destroy each other's databases mid-run. **Never run two
  concurrent suite sessions in this checkout** — distinct worktrees need distinct
  `BEYO_TEST_SLOT` values.
- **Baseline (D23):** **21 failed / 2576 passed, collection 2597**, ~50.6 s, on tree
  `dc76db8` (`app/` byte-identical to today's). The **21-ID set is the durable comparator**,
  not the count — it is enumerated in
  `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7.
  **Two named intermittents are NOT members** of the 21
  (`test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
  and
  `test_process_shopify_products_integration.py::test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task`);
  a third, unrecoverable, **is**. So the set can shrink as well as grow: **a single run is
  not evidence — repeat and ID-diff before concluding the set changed**, and **capture the
  failing-ID set before repeating an anomalous run**, never after.
- **Host timezone matters.** The suite runs on the host's local zone unless `TZ` is set. Any
  mutation touching naive/aware datetime handling — the 90-day cutoff is one — runs under at
  least two `TZ` settings, one of them `UTC`.
- **Migrations:** never rewrite an applied migration; destructive verification only on
  disposable databases; the configured DB is left at head. `app/migrations/env.py` carries a
  `connection.rollback()` guard against the Alembic trap where `upgrade` exits 0 and
  persists nothing — **assert the DDL after migrating, never accept the exit code**.
- **Docs guard:** `PYTHONPATH=. pytest tests/unit/docs/` (59 tests, ~3 s) before any write
  under `docs/domains/item_economics/` or `docs/handoff/`.
- **Residue:** the suite leaves rows from tests outside this pipeline; row-count drift is
  never evidence of a code change.

### Evidence budgets (charter, "Test-evidence scope and reuse")

- **Exactly one L4 stamp closes each implement/fix cycle**, taken on the tree actually
  handed over. Citing an earlier stamp whose tree the cycle then changed is a finding; so is
  re-running evidence whose tree identity matches yours with no variation and no pre-run
  authorization line. **A session that invalidates its own stamp by changing anything after
  taking it re-takes it, and the re-take is not over-budget.**
- **Mutations run at hypothesis scope** — L1 (named test / phase file) by default, L2 where
  the criterion names a cross-file bite set. An L1 miss is already a finding.
- **L4 is required** for: the cycle stamp; review entry on a changed tree; the approval gate;
  **absence claims** (plan 4 C1's live-seconds sweep, plan 5 C7's fork sweep); and baseline
  re-enumeration.
- **A phase whose criteria enumerate L4 measurements states that matrix as its budget** —
  plan 2's §12 matrix is ten distinct conditions and each is variation, not redundancy.
- Every evidence record carries hypothesis, scope, exact command, **tree identity** (SHA +
  asserted-clean `git status --porcelain`; a dirty tree adds a `git diff` digest), result,
  and the failure-ID delta in both directions.
