# Master plan — `narrow_typical_work_times`

```
plan: master_plan
role: implementation-planner
round: 0
date: 2026-08-22
status: IN PROGRESS — phases 1–3 APPROVED (2026-08-22, 2026-08-23, 2026-08-23); phase 4 PROMPT_READY (projection gate satisfied 2026-08-23); phases 5–6 NOT_STARTED
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
| Owner decisions D1–D28, verbatim | `planning/owner_decisions.md` |
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
- **State machine:** `NOT_STARTED → PROJECTING → PROJECTED → PROMPT_READY → IMPLEMENTING →
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
  **⚠ Corollary, earned 2026-08-23 on the second instance: a gate check must name state
  that survives the coordinator's own fold commit.** The fix-round-2 prompt gated on
  `git log --oneline -2` showing `406b097, d07028b` — true while it was being drafted,
  false the instant the consumption fold committed on top, and a second session correctly
  refused to start. The coordinator always commits the fold *and the prompt* after the
  round being consumed, so **anything pinning `HEAD` to a SHA is stale before it is read.**
  Gate on **ancestry and content** — "commit X is an ancestor of `HEAD`", "the plan header
  reads `<state>`", "the Review log carries the `<date>` entry" — never on tip position.
  Both instances cost a session start and both were caught by the session, not by me; the
  gate check is the one part of a prompt the coordinator cannot test by reading.
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
| 2 | Statement extension: spec→predicate, K-spec shape, HC-4 + §12 measurements | **`APPROVED`** | 2026-08-23 | Opus 5 (re-review r2) | Delta re-review: 0 blocking / 0 should-fix / 4 notes / 1 card. All 5 should-fix closed, 4 of them **biting** — proven at 5 probe shapes no prior round ran (no-spec-side filter deletion reddens C1×3 + C5's `base` literal; narrowed value column made to publish the section median reddens exactly the new S2 guard). **N4 closed as enumeration but its row cannot fail**, and §6 C10's mutation (i) is measurably wrong and has never been run — prose fold, no round. L4 runs 0 (tree difference measured test-inert; round-3 stamp cited, +1/+1 corroborated). Notes: N-a C5 tautology (record), N-b §4A K2-a not routed to plans 4/5 (fold), N-c C-N1(a) insert order → plan 3 projection, N-d C10 mutation prose (fold). Card: re-anchor authorization for the 2 stale graph links (diagnosed). **⚠ The approval-gate L4 was never run on phase 2's own gate tree and now cannot be** — `app/` has moved on. What IS established: phase 3's gate tree is stamped by measurement (2674/21/1) and its only `app/` delta from phase 2's gate is phase 3's 49 lines, so no unstamped application change sits between them. Recorded as closed-by-succession, not as paid. |
| 3 | `TaskBudgetStatus` carries the derived spec (§6A, §6B) | **`APPROVED`** | 2026-08-23 | Opus 5 (review r1) | First review: 0 blocking / 0 should-fix / 4 notes / 0 cards. Production matches §6A line for line (additive, defaulted, fail-closed keyword-only helpers, 2-tuple loader, `item_id=evaluation.item_id` preserved, `typical_filters.py` untouched). **7 probes, all new sites or shapes, each red on its own assertion**: the never-measured **worker-side** wrong-source derivation (2/11), T-L1's own `None`-guard removal on **both** faces (1/12 each), both helper **definition**-side carrier drops (4/9 and 2/11), a **value-gated** serializer publish (3/125 at L2), and C-N1(a)'s no-`WHERE` row — whose inferred test id is now **observed** and correct. L4 runs **0**: `git diff 186027a HEAD -- app/` empty, so the 2674/21/1 stamp describes this tree. Graph re-read live and unchanged (198/298, `364223…`, 1 pending / 2 stale). Notes: N1 C2(b)'s manager key-set row is blind to a value-gated leak (measured; the two goldens catch the class) → plan 4; N2 `_ScalarSession` encodes the query count, 8 rows → plan 4 task 0; N3 §6 C6's "three"/four count + L2 scope line → fold; N4 C5-d shares C5-b's wrong-source inertness → fold. **GATE (coordinator, 2026-08-23):** rows archived to `archive/plan_3/` (9); N3 + N4 folded; N1 + N2 routed into plan 4's read-first list as the first publisher. **P2 re-verified independently — 3 failed / 125 passed, the reviewer's exact ids, manager row green.** **⚠→✅ The approval-gate L4 was RUN on this gate tree, not cited: `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'` → **2674 passed / 21 failed / 1 skipped** in 54.64s, the 21-ID set unchanged. Doc/archive delta measured test-inert first (both `tests/unit/docs/` tests resolve only to `docs/handoff/to_frontend/` and `docs/domains/item_economics/`). |
| 4 | Division contract + production-time + budget-allocations | **`PROMPT_READY`** | 2026-08-23 | Opus 5 (coordinator) | **Projection r0 `AMENDMENTS_REQUIRED` — 6 blocking / 10 should-fix / 4 notes / 0 owner cards — consumed and FULLY ROUTED 2026-08-23; gate SATISFIED.** The largest finding was measurable and measured: probe P1 applied the phase's own payload additions + v2 flip and reddened **4** tests, **two in files §4 never named**, neither self-healing — the phase could not have closed green as written. Also repaired: three criteria that could not be executed (C9(a) had no baseline, C10's mutation was designed against a 3-item list and applied to a 50-task one, C12's gate rule was false by construction), C1's three unstated fixture preconditions, two unarmed rows (C7(b), C10(b)), two undecidable absence claims (C1(c), C2), **four** drifted `budget_division.py` spans, and a misrouted plan-5 obligation. Plan 4 gained a **task 0** (tests-first + the C9(a) pre-refactor snapshot) and a **task 9a**. Coordinator added one finding the ledger missed (C10's fixture is denominated in tasks, its assertion in sample counts) and corrected three of the projection's own numbers. **10 rules earned → §9.** **SECOND COORDINATOR PASS (§6B, same day):** the fold was re-consumed at source as an artifact rather than trusted, and added **two more blocking** findings the projection's instrument could not reach — **C-1** `beyo_manager/routers/README.md`, a hand-maintained field-by-field contract for both changed endpoints that **no test reads** (so probe P1's green was structural), now §4 + task 9c; and **C-2** an inherited tripwire, `test_c19_…` forbidding the token `Fraction` in either service, which **C4's own mutation instructed the implementer to trip** (measured 17 passed → 1 failed / 16 passed; probe reverted, `md5` identical). Also **C-3**: L9's supporting spans were wrong in the ledger and had been transcribed unverified into the plan — re-derived (`:42`; reads `:133`/`:234`/`:273`/`:321`/`:391`). **3 further rules earned → §9.** Blocking total for the phase: **8**. Largest phase: now 16 tasks, 14 criteria (**C0–C13**), 4 production files, 1 hand-maintained doc, 2 goldens. Carries in **C0**, phase-3 **N1** + **N2**. |
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
3. **Goldens regenerate once**, on the post-live-clock baseline (D23). The accepted diff is
   **key additions plus exactly one value change — `allocation_method`
   `static_proportional_section_v1` → `static_proportional_section_v2`, twice per file** — and
   **any changed numeric value is a gate failure, not a regeneration.** Both changed goldens
   (`golden_production_time.json`, `golden_budget_allocations.json`) are regenerated in
   **phase 4**, in one act; `golden_budget_status.json` is unchanged by every phase. Planner
   reading of D23, recorded so a reviewer does not read a gate failure into two files moving
   at once.
   *(The "keys-only" label was corrected at plan 4's projection fold, 2026-08-23, L3: measured,
   both goldens carry the method constant as a **value**, twice each, so phase 4's own approved
   version bump puts a value change in the diff **by construction**. A gate whose accept
   condition the phase cannot satisfy is not a strict gate, it is a broken one — and this one
   was replicated verbatim into `plans/plan_4.md` §5 task 10 and §6 C12. All three now carry
   the enumerated form.)*
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

**⚠ INTERIM POLICY, owner 2026-08-23 — new graph nodes carry meaning, not coordinates.**
The owner is simplifying the archgraph policy so that **evidence links stop referencing code
line ranges**. A source link names the **file** whose meaning the node describes; the node
and its relationships explain **what that substance means for the application and what it
affects**. Rationale, in the owner's terms: maintaining spans is "too much job and is almost
like duplicating code" — a span restates what the code already says, while the graph exists
for the part code cannot say.
**Binding on every session from now, ahead of the policy landing:** when recording a graph
delta, **do not emit `startLine`/`endLine`**. Describe the boundary and its effect instead.
Existing span-bearing links are legacy and are repaired only under a scoped owner
authorization (D28, D29) — never opportunistically.

**⚠ D29 IS DEFERRED, owner 2026-08-23 — do not dispatch it.** The owner is editing
`.archgraph/agent-operating-policy.md` and will not run the re-anchor session until the
policy change lands. **This is the right call, and it changes what D29 is worth:** two of its
three authorized operations (**1** and **3**) are *span re-anchors*, and if spans leave the
model those operations do not get performed — **they cease to exist**. Only operation **2**
(re-accept `_optional_values`, refreshing a drifted content hash without touching line
numbers) survives the policy change in recognisable form. Running D29 first would spend a
session deriving three spans in order to delete the concept of a span.
**Consequences to hold:** the one **pending review entry stays pending** and the **two stale
nodes stay stale** until the policy lands — that is accepted state, not neglect. D29's
authorization remains valid and scoped; it is not withdrawn, only postponed. When the policy
lands, **re-scope D29 before dispatching it** rather than running it as written, and update
this section plus the graph-delta paragraph in every implementer prompt template.
*Why this is written here and not just awaited:* this project alone paid three drifts on one
entry, two stale nodes, one owner card and two maintenance sessions to keep a cache of
something `grep` answers instantly. The full policy change is the owner's, tracked
separately; this line stops sessions producing more of what it removes.

**Architecture graph.** Measured after the 2026-08-23 queue-adjudication maintenance
session: **198 nodes / 298 edges, revision `364223242014…`, 1 pending / 2 stale /
0 diagnostics.** (The archived live-clock
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
- **Name the criterion that owns a hazard, then check that it can *see* the hazard's
  observable** (plan-2 consumption, measured 2026-08-23). §6A worked the K-multiplication
  hazard out on paper and designated **C5** its guard. C5 shipped asserting counts only,
  and a group-seconds multiplication moves the **median** while leaving `count(task_id)`
  untouched — measured: the `* 2` probe reddened three tests in the file and **not** the
  one named as the guard. Coverage existed, but accidentally, in C8/C9. **Designating a
  guard is a claim about an instrument, and it is checkable the same way any other
  criterion is: name the mutation, name the column it moves, confirm the guard reads that
  column.**
- **"Mutations, one per sub-check" is a count, and the ledger is checkable against it**
  (plan-2 consumption, 2026-08-23). Round 1 reported one mutation per criterion where the
  plan named two (C6), three (C7) and four (C10) — **seven unrun**, with the plan's own
  text calling two of them "the likelier slips". A criteria ledger with one row per
  criterion silently under-reports any criterion that named more than one; **the ledger's
  row count must match the plan's mutation count, not its criterion count.**
- **Tests-first shrinks the transcription-failure class; it does not close it** (plan-2,
  the first tests-first phase). Task 0 eliminated the *missing row* failures that cost
  phase 1 eleven of thirteen findings — every criterion reached a test file this time.
  What survived was the next layer in: rows transcribed into **fixtures too small or too
  uniform to discriminate** (C2 row (d) comparing `None` to `None` on a one-task fixture;
  C8's median assertion on six identical 100s), and **mutations named but not run**.
  Transcribing a row and *arming* it are two different acts. A tests-first prompt should
  ask for both explicitly: the row, and the fixture arithmetic that makes it move.
- **A uniform fixture is an inert fixture.** Seeding every group at the same value makes
  every median assertion in that test survive any multiplicity, ordering or fan-out
  mutation. Where a criterion asserts a typical, the fixture states its group multiset and
  why the mutation moves the median — the median must not equal the mean, and must not be
  invariant under duplication.
- **The 21-ID failing baseline is not stable under adding a test file** (measured
  2026-08-23). Phase 2 added one integration file and the failing set moved by three ids,
  all in `test_user_work_profile_clock_in_code.py`, whose `_two_workspaces` helper reads
  whatever workspaces leaked into its xdist worker (`SELECT ... FROM workspaces LIMIT 2`,
  asserting two exist). Under `--dist loadfile`, adding a file re-partitions the workers
  and changes a leak-dependent test's neighbours. **Consequence for every phase in this
  project: an unexplained delta against the 21-ID set is not automatically a regression,
  and must be diagnosed rather than counted.** Routed to `test_isolation_xdist` phase 3 as
  a free perturbation datapoint.
  **⚠ Superseded in its strong form, 2026-08-23 (phase-2 review, serial L4).** The reviewer
  ran `-n 0` and got the **identical 21-ID set** — so the set is *not* nondeterministic
  run-to-run on a fixed tree, and round 2's clean ∅/∅ was **not** luck. What survives is
  narrower and still true: **the set changed between round 1's tree and round 2's**, which
  added tests to an existing file. And the trio fails 3/3 *in isolation* while passing in
  **both** full runs — they need leaked state a full run supplies. So round **1**'s
  24-failure stamp is the outlier, not round 2's. **Read a delta as composition-dependent,
  not random**: it moves when the test population changes, not between runs of the same tree.
- **A phase that deliberately duplicates a definition owes one criterion asserting the
  copies agree — on a fixture where they could disagree** (phase-2 review S1). HC-4's
  byte-identity requirement forces two `grouped_steps` builders; the plan then wrote no
  criterion over the *second* one's population. C5 *looked* like the guard — it asserts the
  `K ≥ 1` section count against the `K == 0` call's, a genuine cross-branch equality — but
  every fixture seeded only steps that were `COMPLETED`, not deleted, not marked wrong, and
  closed yesterday, so there was nothing for the equality to discriminate. Measured: all
  four population filters deleted from the `K ≥ 1` branch, one at a time, left the full L2
  bite set green (62 passed) every time.
- **"The criterion asserts a cross-call equality" is not "the criterion can see a
  difference."** The extension to §9's hazard-ownership rule, earned three times in one
  phase (S1, S2, S3): after naming the mutation and the column, **confirm the fixture
  contains a row the mutation moves.** An equality between two calls over a fixture with no
  discriminating row is an identity, not a test. Prefer an **exact literal** over an
  equality between two calls wherever one exists.
- **A `match=` on an expected exception is an assertion, and gets the same enumeration
  discipline as any other** (phase-2 review S3). C0's bare-`str` enum row asserted
  `match="major_categories"` — a substring present in **both** the explicit guard's message
  ("must be a sequence of values") and the accidental path's ("contains an unknown value").
  Measured: deleting `str` from the guard left the row **green**, so the row that exists to
  prove the rejection is *explicit* could not tell an explicit rejection from an accidental
  one. **Pin the message only the correct path produces**, never the family or symbol name
  that every path mentions.
- **A measurement harness that seeds cumulatively must say so** (phase-2 review S5).
  `collect_measurement_matrix` loops eleven cases on one session with no cleanup, so each
  row is measured against a table holding every previous row's seed. "Seed cardinalities are
  exact for every row" was true of each *workspace's* seed and not of the *table* the
  planner saw — visible in the doc's own numbers, where the same query costs 0.060 ms at
  position 5 and 0.087 ms at position 10. Record row positions, whether `ANALYZE` ran, and
  any requested-but-unrecorded output (`BUFFERS`).
- **A symmetric hazard needs a mutation from each side** (phase-2 re-review, S1's close).
  S1 was about **two builders diverging**, and three rounds mutated only the `K ≥ 1` copy —
  a right repair with half a proof. Cutting the **no-spec** copy
  (`delete TaskStep.is_deleted.is_(False)` there alone) reddened C1's three snapshot rows
  *and* C5's `base.sample_count == 20` at `21 == 20`. **When a criterion asserts an equality
  between two independently-written computations, the named mutations enumerate both
  operands** — one per sub-check, in both directions.
- **A named mutation's stated bite set is a claim, and it decays** (phase-2 re-review N-d).
  Plan 2 §6 C10's mutation (i) asserted a bite set that **was never true**, and survived a
  projection, three implementation rounds and two reviews **because it was never run** — and
  because a reviewer restated it from a ledger instead of measuring it. **A mutation that has
  never been run is not evidence of anything, including of what it would catch.** Re-derive a
  plan's mutation prose from the code after each repair; never carry it forward unmeasured.
- **`IS NOT NULL` inside a conjunction with bounds is not the guard it looks like.**
  `column.is_not(None)` on a NULL column evaluates to **FALSE, not NULL**, so a *bounded*
  range is already definitely FALSE without it and the `coalesce` never sees a NULL. It is
  load-bearing **only** for the unbounded `(None, None)` case. Any criterion reasoning about
  NULL handling in a predicate must say **which of the two mechanisms** it tests — the
  explicit conjunct, or SQL's three-valued logic — because **no fixture can tell them apart
  for a bounded range**.
- **Route an amendment to its consumers, not to its origin** (phase-2 re-review N-b, and
  N3 one finding earlier in the same phase). §4A K2-a landed in the Read-first of the plan
  that raised it — a plan that never calls the statement — and not in the two plans that do;
  plan 4 caught it only by physical adjacency and plan 5 not at all. Twice in one phase is a
  pattern, not an accident: **"who reads this?" is an explicit line on every fold**, answered
  by naming files, not by judgment made once per project.
- **Deleting an inert assertion is a legitimate close — when the claim moved somewhere that
  bites, and the round says where.** C8's equal-`100` median line was removed in the same
  round S2's test began pinning the value column with distinct literals. The arm-or-delete
  choice is only safe under that condition; a round that deletes owes the sentence saying
  where the coverage went.
- **A fixture that satisfies two independent sufficient causes cannot prove either**
  (plan-3 projection L6(ii)). `task_items` carries **two** partial unique indexes; a
  "second active primary" fixture that reuses the first primary's `item_id` raises
  `IntegrityError` from `uix_task_items_active`, so dropping `uix_task_items_primary_active`
  — the named mutation — leaves the row **green**. Before asserting that an error proves a
  rule, **enumerate every constraint that could produce the same error** and make the
  fixture violate exactly one.
- **A duck-typed helper turns a "wrong source" mutation into a "no source" mutation**
  (plan-3 projection L3). `derive_spec_from_primary_item` reads via `getattr`, so deriving
  from an **id string** rather than an `Item` returns the *empty* spec, not the *wrong*
  spec — the mutant's red is then indistinguishable from "the value was never computed".
  A mutation meant to prove *which* input was used must supply an input of the **right
  type** carrying the **wrong content**.
- **A count in a plan sentence is a checklist, and one that counts to nothing is worse than
  no count** (plan-3 projection, reality checks 18–19). "§6.2's table is seven rows" was
  false (six rows, seventh *surface*), and "five construction surfaces" matches **no**
  measurement in the repository — 2 production construction sites, 4 `_empty_status` call
  sites, 6 helper call sites, 2 test constructions. An inherited phrase that reads like a
  checklist and is not one will be used as one.
- **A line number handed to a session is a claim with a shelf life** (D29, measured
  2026-08-23). The D28 maintenance session re-recorded an evidence span from the *reviewer's
  diagnosis* ("the test now begins at 232") rather than from the file; a fix round landed in
  between and moved the test six lines, so the repair shipped **still wrong** — the third
  drift on the same entry. **Derive every span by locating the symbol in the file at the
  moment of writing, and assert the span begins at a `def` or a decorator** — that one check
  catches this whole family. Expected values in a prompt are a **checksum to compare
  against**, never the value to write; a disagreement is a stop-and-report, because it means
  the tree moved again.
- **A conversion trigger nobody is routed to read cannot fire** (phase-2 review N3). C11's
  trigger names three concrete syntactic conditions and the row it converts into — better
  than most — but no downstream plan's Read-first list included it, and plan 6, whose scope
  names the very construct that fires it, was among them. **A criterion held structurally
  "until X happens" is incomplete until the plan where X would happen is made to read it.**
- **A content-blind test double encodes the query count, so a mutation that changes the
  number of queries reddens for the wrong reason** (plan-3 coordinator consumption, measured
  2026-08-23). `_ScalarSession` returns the next value in a list whatever is asked of it, so
  its length *is* an assertion about how many queries the code issues. §6A prescribed C4's
  mutation as "re-load `Item` by `evaluation.item_id` and derive from that instance" — one
  extra query — and the measured result was `RuntimeError: coroutine raised StopIteration`
  plus **three unrelated C5 rows red as collateral**, not the promised
  `cat_chair` → `cat_table`. **When a criterion's mutation must change *where a value comes
  from*, check that it leaves the query count unchanged**; if it cannot, the double must be
  made content-aware or the criterion must claim only what it can prove. Corollary, and the
  reason this is its own rule: **a "wrong Item" mutation is unprovable against a double that
  cannot return a different Item** — state the narrower claim ("the carrier stopped coming
  from the loaded PRIMARY item") instead of the wider one.
- **A mutation the language rejects is not a mutation** (same round). C1's named mutation —
  move a defaulted field before a non-default one — is a `TypeError` at *class creation*, so
  it produces a **collection error and no failing test id**, which the evidence budget
  requires. It was also unfalsifiable: `result` is the last non-default field, so the
  grammar, not the test, forbade the position. **A mutation must be legal code that runs and
  names a failing test; if the language refuses it, the criterion is untested and a legal
  mutation must be found** — here, swapping two *existing* fields, which reddens C1 alone.
- **A key-set criterion must serialize a *service-produced* object, not a locally
  constructed one** (plan-3 review N1, measured twice 2026-08-23). A payload-key assertion
  built from a hand-made read model can only see leaks that are **unconditional**. Phase 3's
  manager row serializes a `TaskBudgetStatus` whose new field holds the dataclass default
  `None`, so a **value-gated** publish (`if spec is not None: payload[...]`) leaks on both
  faces and that row stays **green** — reproduced independently at **3 failed / 125 passed**.
  This is §9's *"confirm the fixture contains a row the mutation moves"* applied to a **key
  set** rather than a value: **the fixture must contain a populated value for the key whose
  absence is being asserted.**
- **Name the mutation at the *definition* as well as the call site when a helper fans out**
  (plan-3 review P7/P8). §6 named only call-site mutations for C5; the definition-side drop
  reddens a **different** four rows — and it is the shape a careless refactor actually
  produces, since nobody edits four call sites by accident. Charter rule 11 already implies
  this; plan 3 applied it to C-N1 and not to C5.
- **An inferred failing-test id is not an observed one** (plan-3 review, lesson 3). The fix
  round supplied C-N1(a)'s no-`WHERE` id by inference and **said so honestly**; the review
  observed it and it was correct. **Both are legitimate, but they are different claims and a
  ledger must distinguish them** — the cost of observing it was one second. Add the column.
- **A probe that lands in the wrong place measures nothing, and its green is the most
  dangerous result available** (coordinator, plan-3 gate, 2026-08-23). Verifying review
  probe P2, the coordinator inserted a value-gated publish by locating `payload = {` — and
  `serializers.py` has **four**, so the edit landed in `serialize_item_cost_result_worker`.
  The suite returned **128 passed**, which read as "the reviewer's finding is wrong" and was
  in fact "the mutation was never applied to the function under test". Correctly sited, it
  reproduced the reviewer's numbers and ids exactly. **After applying a mutation, assert it
  is inside the symbol you meant** — the same failure as the `python`/`python3` slip in
  phase 2, where an unapplied mutant produced a clean baseline that looked like evidence.
- **A narrower round is not a licence to drop a step that maintains state** (plan-3 fix
  round 1, 2026-08-23). Phase 3's state is recorded in **two** places — `master_plan.md` §4
  row 3 and the plan file's own `state:` header. The round-1 implementer prompt's closing
  protocol named both (*"§4 row 3 and `plans/plan_3.md` (`state:` + §8)"*); when the
  coordinator rewrote that protocol for the narrower fix round it kept the `master_plan`
  half and dropped the `state:` half, so the two artifacts **disagreed** at close — tracker
  `IMPLEMENTED`, plan header `CHANGES_REQUESTED` — and the next session's gate check reads
  the header. **When you rewrite a closing protocol for a smaller round, re-derive it from
  the full one rather than trimming it**; and where state lives in two artifacts, name both
  every time.
- **A checksum is only valid for a fact with one correct value** (plan-3 fix round 1, gate
  stop, measured 2026-08-23). The D29 technique — *publish the expected value as a checksum
  to compare against, and treat a disagreement as stop-and-report* — is sound for a **derived
  span**, because a symbol occupies exactly one range and a mismatch really does mean the tree
  moved. It was carried across to a **mutation observable**, which is not that kind of fact:
  the red depends on **how the mutation is written**. Three faithful readings of one
  mutation's prose measured **4/9, 1/12 and 3/10** on an *identical* tree, so the gate fired
  on a difference that was guaranteed by construction and halted the round. **Before
  publishing a checksum, ask whether the thing being checksummed has a unique correct value.
  If it depends on how the session chooses to do the work, pin the work to exact code first —
  or do not gate on it.**
- **Never demand a canonical observable from a mutation you have just withdrawn** (same
  round). The withdrawn C4 row was withdrawn *because* its observable is unstable; requiring
  a confirmation run of it re-imported the instability into the gate. **A withdrawal is
  argued from the fixture's structure, not re-measured** — and a confirmation run of a
  withdrawn row buys nothing that the withdrawal argument does not already establish.
- **Two of these three corrections were to a coordinator fold, not to an implementer**
  (2026-08-23). §6A caught that C4's original mutation passed a `str` and went one step —
  *produce an `Item`, not an id* — but not two: **the fixture must be able to supply that
  `Item`.** A fold that corrects a defect one layer down inherits the obligation to check
  the layer below it.

- **A plan's "files expected to change" is a claim, and a projection can MEASURE it** (plan-4
  projection L1, 2026-08-23 — the largest finding of the round and a new technique). Phase 4's
  §4 named two goldens and one test file. The projection applied the phase's own payload
  additions and its method-constant flip to the four serializers, ran the scoped surface, and
  found **four** reds — two of them in files §4 never named, and **neither self-healing**
  (exact key-set assertions at `test_budget_division_routes.py:155/:158` and an exact v1
  literal plus two key sets at `test_production_time_query.py:206/:207/:208`). The phase could
  not have closed green as written. **Generalized: any phase adding a wire key or changing a
  published constant can have its declared perimeter measured before an implementer opens —
  apply the payload change, run the import radius, read the reds.** It costs one probe and it
  is the only check that finds an *omission* rather than an error.
- **An exact key-set assertion is a perimeter obligation, not a test detail** (same round).
  `assert set(serialize_x(row)) == {...}` is a tripwire that fires on every *addition*, so it
  redden**s** in exactly the phases that are doing their job. **Grep for exact key-set
  assertions on any payload you are extending, and widen — never delete — each one**: they are
  usually the only guards on that wire, and a phase that deletes one converts a caught
  regression into a silent one for every phase after it.
- **A mutation designed against a small fixture does not survive the fixture growing** (plan-4
  projection L6). C10's mutation "map tasks to `spec_index` by insertion order" was written
  against a 3-item list and applied to a **50-task** fixture, where `spec_index ∈ [0, K)` means
  47 of 50 tasks map to indices with **no row in the result**. The row was exposed to *both*
  paid-for shapes at once: **inert** if the asserted task was the first one, and **red for the
  wrong reason** (`insufficient_sample` / count 0, not a wrong population) for 17 of the
  remaining 19. **A named mutation and the fixture it runs against are one artifact — re-derive
  the mutation whenever the fixture's cardinality changes, and state the mutant's index range.**
- **A criterion's fixture line must state the quantity the criterion asserts** (plan-4 fold,
  coordinator). C10's fixture counted **tasks** (20 chair / 15 table / 10 stool / 5 none) while
  its row asserted a **`sample_count`**, which counts completed section groups in the 90-day
  window — a different quantity the fixture never mentioned. The corrected mutation makes a
  chair task read the table population, which reddens the row **only if the two populations
  differ**, and nothing in the plan said they did. This is §9's *"confirm the fixture contains a
  row the mutation moves"* one level earlier: **at plan-writing time, check that the fixture
  description and the assertion are denominated in the same unit.**
- **An absence claim rooted at the repository root is false the moment the project publishes
  its own history** (plan-4 projection L10). C2's sweep for the *old* method constant would run
  against three published frontend handoffs and an archived plan set that carry it as **history**
  — and §9 forbids rewriting a published handoff, so the claim could never be made true. The
  root is the **code that must not carry it** (`app/beyo_manager/` plus the regenerated
  goldens), never "everywhere". Companion to §9's "absence claims state their root and their
  term set": **choose the root so that ∅ is both true and meaningful, and say in the row why the
  excluded paths are excluded** — otherwise the next session widens it back.
- **A criterion whose instrument cannot return the expected result is undecidable, however
  precise its prose** (plan-4 projection L9). C1(c)'s claim was semantic ("no site passes a
  live-derived value into a typical") but its instrument was a three-term grep expecting ∅ over
  a repository where all three terms are present **by design** — `total_working_seconds` is the
  live-clock contract, at a dataclass field and five read sites. The qualifier that made the
  claim true ("within the typicals path") is not mechanically checkable. **Before shipping an
  absence row, run its own sweep and look at the hits: if the expected result is unreachable,
  the row is prose, and the real guard is the mutation on the value rows.**
- **A pre/post comparison needs a "pre" that something captured** (plan-4 projection L4). C9(a)
  asked for every pre-existing numeric field to be "compared against the pre-refactor payload
  for the same fixture" — but the fixture is **created in that phase**, so no such payload
  existed and no task captured one. Taken after the refactor it is `f(x) == f(x)`, the vacuity
  §11A repaired T11 to remove. **Any criterion containing the words "unchanged", "before" or
  "pre-refactor" owes a task that writes the baseline down, ordered before the first production
  edit** — and that snapshot is then never regenerated.
- **A blanket phrase in a gate is a defect when the phase's own approved work violates it**
  (plan-4 projection L3). "Regeneration is approved only if the diff adds keys" was replicated
  in three artifacts and was **false by construction**: the same phase flips a method constant
  that lives in both goldens as a *value*. The enumerated form ("key additions plus exactly one
  named value change, twice per file") is the same strictness with none of the falsity.
  **Prefer an enumerated accept-list to a blanket adjective in any gate the phase itself must
  pass.**
- **Route a Read-first obligation to the phase that can act on it** (plan-4 projection L15, and
  the third instance of this shape in this project). "Widen the price-scenario `fake_status`
  before you read the field" sat in **plan 4's** Read-first — a phase that never touches
  price-scenario, so obeying the instruction would have breached its own file perimeter. It also
  named **one** fake where the surface is **four**. Both halves are the same error: the
  amendment landed near where it was discovered rather than where it is executed. §9 already
  carries "route an amendment to its consumers"; this instance adds the test — **"could this
  phase act on this without leaving its §4 perimeter?" If no, it belongs to another plan.**
- **A projection's own corrections inherit the obligation to be checked** (plan-4 fold,
  2026-08-23 — the second time in two phases). Three of this round's twenty rows needed a
  further correction from the coordinator: a re-derived span the projection put one line off, a
  measured count restated from memory ("12+" for eleven), and one mutation correction that fixed
  the site but left the fixture unable to discriminate. **Consuming a projection is not
  transcribing it. Re-derive every number that will be written into a plan, by locating the
  symbol at the moment of writing.**
- **A green suite is evidence about the suite's reach, never about a surface the suite does not
  read** (plan-4 consumption fold C-1, 2026-08-23). The projection measured the phase's full
  payload additions and got a clean result on the docs guard, and concluded no documentation
  needed updating. But `beyo_manager/routers/README.md` — hand-maintained, self-declaring
  *"a route added without editing this file silently rots it"*, and enumerating both changed
  endpoints field by field — is read by **no test at all**. The guard rooted elsewhere, so the
  green was structural, not informative. **Before citing a passing suite as proof that a surface
  is unaffected, establish that something in that suite reads the surface.** Corollary: a
  documentation surface with no guard belongs in a plan as a **task**, never as a criterion —
  a criterion that cannot fail is not a criterion.
- **A probe's path set is a claim about coverage, and an unmeasured directory is not a green
  one** (plan-4 consumption fold C-2, 2026-08-23, measured). The projection ran four path groups
  and reported the phase's out-of-perimeter breakage from them. An entire directory —
  `tests/unit/services/queries/item_economics/`, 17 tests — was in none of them, and it holds a
  structural guard forbidding the token `Fraction` in either service this phase rewrites, which
  the plan's own C4 mutation instructed the implementer to trip. **A scoped probe must state its
  path set as a limit, and consuming one means asking what the set excluded** — the excluded
  region is where the next defect is, precisely because nobody looked.
- **A measurement at one site is not a measurement of the surface** (plan-4 seal, 2026-08-23 —
  both unhinted predictions failed this way in one round). A `fake_status` counted at one
  definition was reported as the surface (three, actually four); a defaulted read
  (`row.get(key, CONSTANT)`) was called invisible to a constant-reverting mutation without
  tracing **who supplies the row** — the caller supplied the constant itself, so it was visible
  all along. **A claim about a surface owes a sweep of the surface, and a claim about a data
  flow owes the producer, not just the consumer.**

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
  **absence claims whose root really is the repository**; and baseline re-enumeration.
  *(Corrected 2026-08-23, plan-4 projection L9: plan 4 C1's live-seconds sweep is **no longer**
  an L4 row — it could not return ∅ from the repository root, because `total_working_seconds`
  is present there by design, and it is now an L2 sweep over `typical_filters.py` plus the
  evidence-construction helper. Plan 5 C7's fork sweep still is one.)*
- **A repo-wide claim and a full-suite run are different axes.** An absence criterion that
  ships as a committed test walking the repository (plan 4 C13(c)) is an **L1 test** with a
  repo-wide *claim*; running it does not require and does not consume an L4 suite run. Do not
  spend the stamp on it.
- **A phase whose criteria enumerate L4 measurements states that matrix as its budget** —
  plan 2's §12 matrix is ten distinct conditions and each is variation, not redundancy.
- Every evidence record carries hypothesis, scope, exact command, **tree identity** (SHA +
  asserted-clean `git status --porcelain`; a dirty tree adds a `git diff` digest), result,
  and the failure-ID delta in both directions.
