# Master plan — simple_production_budget_division

```
role: master plan (coordination hub)
intention: planning/intention.md (rounds 0–3, D1–D8 settled, 0 cards open)
charter: /Users/davidloorenz/agent-skills/pipeline-charter.md
created: 2026-08-16
coordinator: Claude (orchestrator per owner instruction, 2026-08-16)
```

## 1. Mission

Ship the two read-only surfaces of `planning/intention.md`: E1 typical section times
(`GET /api/v1/working-sections/typical-times`) and E2 per-step budget allocations
(`GET /api/v1/item-economics/tasks/budget-allocations`), backed by mechanism contracts
M1 (median typical) and M2 (live-step-set proportional division, D8). One
implementation phase. Hard constraints HC-1..5 of the intention are binding on every
session; HC-2 means **any migration or schema diff appearing in this pipeline is an
automatic review finding**.

## 2. Folder layout (charter tables)

```
simple_production_budget_division/
  master_plan.md            ← this file
  planning/                 ← intention.md, owner_decisions.md (pipeline root artifacts)
  plans/                    ← plan_1.md (single phase)
  prompts/{reviewer,implementer,coordinator,maintenance}/
  handoffs/{reviewer,implementer}/
  archive/plan_1/           ← created at closeout
```

## 3. Phase registry & tracker

| Phase | Scope | State | Date | Actor | Note |
|---|---|---|---|---|---|
| 1 | M1+M2 domain module, E1+E2 endpoints, full test set | IMPLEMENTED (r1b) | 2026-08-16 | Codex | Fixed the second route mirror; focused fix suite 131 passed; full suite 2277 passed, 26 failed, 1 deselected = 23 baseline + 3 foreign bootstrap failures. Complete mutation ledger and criterion map are in the r1b handoff; C13b was already present at checkpoint. |

Single-phase pipeline. The projection (round 0) runs under the reviewer tables; the
implementer prompt is compiled only after its ledger is fully routed.

## 4. Naming registry (final authority on names; intention §5 governs payload shapes)

**Domain (one module owns every constant and formula):**
- `app/beyo_manager/domain/item_economics/budget_division.py`
  - `TYPICAL_WINDOW_DAYS = 90`, `TYPICAL_MIN_SAMPLE_SIZE = 5`,
    `TYPICAL_METHOD = "median_completed_section_totals"` (D9: per-(task,section)
    group totals, not per-step samples),
    `ALLOCATION_METHOD = "static_proportional_v1"`
  - `EXCLUDED_STEP_STATES = frozenset({SKIPPED, CANCELLED, FAILED})` (M2 partition;
    the allocated set is its complement over non-deleted steps)
  - `divide_production_budget(...)` — the pure M2 function (P-SUM / P-PROP / P-DET /
    P-FOLLOW / P-STABLE); returns per-step allowance/left/share_state rows plus the
    task-level charged `C` and distributable `D`
- `app/beyo_manager/domain/item_economics/division_serializers.py` — E1/E2 payload
  builders (new module; v1 `serializers.py` is closed, HC-1)

**Query services:**
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` (E1/M1)
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` (E2)

**Routes:**
- E1 → existing `routers/api_v1/working_sections.py` router (prefix
  `/api/v1/working-sections`), `GET /typical-times`. **Declaration order is
  load-bearing (projection P7):** `@router.get("/{working_section_id}")` at `:128`
  shadows any fixed path declared after it — E1 MUST be declared above `:128`,
  following the in-file precedent of `/me` (`:93`) and `/steps/user-last-active`
  (`:111`). This file is tab-indented (N12) — match it.
- E2 → existing `routers/api_v1/item_economics.py` router, `GET
  /tasks/budget-allocations`. Declaration-order note: fixed two-segment path; no
  two-segment `/tasks/{param}` route exists there today (projection-verified), but
  declare it ABOVE the parameterized `/tasks/{task_client_id}/…` block with a
  one-line comment anyway.
- **HC-1a authorized v1 edits (D10, the ONLY permitted v1 changes):**
  `tests/unit/routers/test_phase9_item_economics_route_mirror.py` — one row added to
  `_EXPECTED_ROUTES` (`:34-63`) and the count assertions 23 → 24 (`:126-131`);
  `beyo_manager/routers/README.md` — one Quick Index row + one detail section for
  each of E1 and E2 (README rows for E1 are unenforced by any test — P11 — so the
  reviewer checks them by hand).
- **Query-param style (P12, deliberate first-of-kind):** `working_section_ids` and
  `task_ids` are FastAPI repeatable params (`list[str] = Query(...)`) — the repo's
  first; every prior multi-value filter is CSV. Chosen for native validation and the
  clean `len(task_ids) > 50` cap. The reviewer must not file this as a convention
  break. Degenerate pin: `?task_ids=` yields `[""]` = one unknown id, omitted per
  batch-read semantics.

**Error identity (new, registered here):**
- `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS` — 422, E2 called with more than 50 task ids.
  DomainError with identity per `architecture/05_errors_local.md` (branchable errors
  carry identities; plain schema errors stay pydantic).

**Tests (new files, placement corrected per projection P8 — DB-backed files live
under `integration/`, `tests/unit` is DB-free by convention):**
- `app/tests/unit/domain/item_economics/test_budget_division.py` — M2 pure-function
  properties + M1 constants (no DB)
- `app/tests/integration/services/queries/working_sections/test_typical_times_query.py`
  — M1 against committed fixtures (configured DB, teardown owned)
- `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`
  — E2 read model incl. the two-doors pair and budget-status agreement (configured DB)
- `app/tests/unit/routers/api_v1/test_budget_division_routes.py` — E1+E2 role
  admission, envelope, batch limit, no-money key-set assertions (DB-free: TestClient
  + `dependency_overrides` + monkeypatched `run_service`, precedent
  `test_item_economics_router.py:55-95`)
- plus the HC-1a additions to the v1 mirror test enumerated under Routes above

## 5. Contract resolution (pattern authority)

Binding contracts for how the code is written: `architecture/05_errors_local.md`
(identity-carrying DomainError), `architecture/46_serialization_local.md` (decimal →
string, enum → value), router conventions as practiced in
`routers/api_v1/item_economics.py` (`require_roles`, `build_ok`/`build_err`, `_run`
helper pattern), query-service conventions as practiced in
`services/queries/item_economics/get_task_budget_status.py`. Implementation files are
read to learn what exists, contracts govern what is written.

## 6. Standing rules

Charter standing rules 1–11½ apply as written. The item-cost pipeline's earned rule
library (`../item_cost_calculation/master_plan.md` §9) is **precedent**: the reviewer
applies any rule whose trigger appears. Rules with triggers already visible in this
phase, named now so prompts carry them:

- **Rule 11 named mutations** — every M1/M2 acceptance criterion names the mutation
  that must turn its test red AND where it is applied (file, definition-vs-call-site).
- **P-I 9th/10th ext** — fix-cycle mutations phrased for byte-reproducibility;
  observed-red is a HARD handoff field.
- **Set-assertion / distinct-values** — the no-money key-set tests assert the exact
  key set, not key absence one-by-one; fixture money/second values are pairwise
  distinct so a swapped column cannot pass.
- **Rule 11½ teardown** — every test that commits rows deletes them in `finally`;
  residue checks name their tables.
- **Suite-number verification (P-L)** — baseline figures are verified at consumption,
  never trusted from a handoff.

## 7. Environment topology (imported from the v1 master plan §10, verified 2026-08-12→15; update HERE if reality disagrees)

- Working directory for all commands: `backend/app/`.
- Infra: `make dev-up` (postgres `127.0.0.1:5433`, redis `127.0.0.1:6380`). Codex
  sandbox reaches both (owner-configured 2026-08-12). A run whose environment cannot
  reach the DB is never recorded as baseline or evidence.
- Tests: `PYTHONPATH=. pytest -m 'not e2e'` (bare `make test` fails at conftest
  import). **Suite baseline at pipeline start = the v1 closure baseline: 2249 passed /
  23 failed / 1 deselected = 2272 selected (2273 collected), head `c1d2e3f4a5b6`.**
  The 23 failures are the phase-1 list in the v1 master plan; this pipeline compares
  against that list byte-identically. This phase adds tests and must not change any
  existing count.
- Migrations: none expected (HC-2). The disposable-DB recipe in the v1 §10 exists but
  should not be needed; if any session believes it needs a migration, that is a STOP
  — report to the coordinator, do not write one. **No index either** — projection N4
  measured the full D9 query at 2.2 ms / 470 buffers on the configured DB (3032
  steps, 1438 groups); re-measure only if `task_steps` passes ~100k rows.
- DB safety: tests that commit own their teardown (rule 11½); configured DB stays at
  head; known non-economics residue from the wider suite is documented in v1 §10 (N11).

## 8. Architecture graph

Sessions orient at start (`archgraph_status` + targeted `archgraph_search_nodes`) and
record the phase delta at end (one batched `apply_changes`, accurate evidence spans).
Agents never promote/reject/edit review items. The coordinator runs the post-approval
graph pass at closeout under the owner's standing authorization (v1 practice,
restated for this pipeline).

## 9. Gates & authorizations

- **Mechanism-inventory gate: WAIVED as a separate session** (coordinator,
  owner-ratified 2026-08-16). Justification: intention rounds 0–4 carry the
  per-mechanism contracts inline at inventory depth (M1/M2 exact predicates,
  rounding modes, tie order, fallbacks, named properties, edge semantics) because
  the mechanisms were designed before the intention was written; the residual
  enumeration is assigned to projection r0 (walk items 1–9 + 2b). Condition of the
  waiver: **any mechanism the projection finds operating without a contract is a
  GATE FAILURE routed back to the intention — never downgraded to a note.** The
  waiver is proportionate to a read-only, nothing-persisted, no-money pipeline; it
  is NOT precedent for pipelines that write.
- **Projection gate: MANDATORY** for phase 1 (charter rule 6 triggers: integer time
  division with rounding residue, statistical derivation, multi-source read
  consistency). Prompt: `prompts/reviewer/2026-08-16_phase1_projection_r0.md`.
- **Checkpoint commits** at every IMPLEMENTED under the owner's standing
  authorization (subject prefix `CHECKPOINT (not approved):`), inherited from the v1
  pipeline and restated here.
- Approval-gate commit + archive move at closeout (charter closeout ritual). Closeout
  also owns the two frontend-handoff folds recorded in intention §8 (un-omit
  production-time §6.1; author the worker-card section).
