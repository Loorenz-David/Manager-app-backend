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
| 1 | M1+M2 domain module, E1+E2 endpoints, full test set | **APPROVED** | 2026-08-17 | Opus 5 (reviewer r4) | Verdict APPROVED, 0 open findings. 4 review rounds: 7 should-fix + 12 notes, **ZERO production defects** — M1/M2 correct as first written, changed only by the behaviour-preserving S1 extraction. Closeout done: baseline §7 → 2287/26/1 (23 v1 byte-identical + 3 foreign bootstrap), MVP calibration rule §6, frontend handoff folded (§6 rewritten with E1/E2 contracts, §8 worker cards added), archived to `archive/plan_1/`, gate commit + graph pass below. Checkpoints `0b85701` → `d4d51af` → `fb48d13` → `7f09637` → `99ade31` → `1290cc0` |

| 2 | E3 — one task-scoped, section-keyed production-time endpoint (intention §12, mechanism M3) | **IMPLEMENTED** | 2026-08-17 | Codex (GPT-5) | E3 implemented and verified: targeted phase suite 164 passed; full suite 2337 selected, 2311 passed, 26 inherited failures, 1 deselected. Checkpoint follows the implementer handoff. |

The projection (round 0) runs under the reviewer tables; the implementer prompt is
compiled only after its ledger is fully routed.

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
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
  (E1/M1) — ALSO exports the shared grouped-median statement builder
  `typical_times_statement(...)` (registered per review r1 S1 / one-copy rule):
  the ONLY implementation of the M1 aggregation; E2 imports and calls it rather
  than inlining a copy.
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` (E2)
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py` (E3,
  phase 2) — composes M1 + M3 + the budget-status resolution; computes no arithmetic
  of its own (HC-6/M3.7). It MUST import `divide_production_budget` and
  `typical_times_statement` rather than reimplementing either.

**Phase 2 additions (names fixed 2026-08-17; shapes in intention §12.7):**
- Section grouping and ordering live in `budget_division.py` beside the allocator, NOT
  in the service — they are M3 mechanism, and the one-copy rule applies to them the
  moment a second surface wants a section view. Registered name:
  `group_steps_by_section(...)`. The M3.2 order key is `_section_sort_key(...)`,
  sibling of the existing `_sort_key` at `:72`.
- Payload builders extend the existing `division_serializers.py` (same module — E3 is
  the same contract family; a third serializer module would fragment it):
  `serialize_task_production_time(...)`, `serialize_production_time_section(...)`.
- D11 resolved to variant B: the change is INSIDE `divide_production_budget` (the
  allocation unit becomes the group), which now returns **both** `sections` and `steps`
  keys (B1). **The per-step split lives in the domain module, not in E2** — this settles
  the earlier "E2 becomes a consumer that splits its section share" wording against C19.
  **No new allocator function may appear** (HC-6).
- `ALLOCATION_METHOD` (`budget_division.py:17`) becomes
  **`static_proportional_section_v1`** (P2 ruling). Grouped-unit remainder tie key is
  `working_section_id` ASC for both callers (B6) — deliberately not M3.2's render order.
- Liveness predicate: `state NOT IN TERMINAL_STEP_STATES`, **imported** from
  `domain/task_steps/constants.py` (B7), never re-listed.

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
- E3 (phase 2) → same `routers/api_v1/item_economics.py` router, `GET
  /tasks/{task_client_id}/production-time`. Declared inside the parameterized
  `/tasks/{task_client_id}/…` block (beside `budget-status` at `:360`) and therefore
  BELOW the fixed `/tasks/budget-allocations` path at `:346` — the comment at `:345`
  is the standing reason. **HC-1a applies a third time:** both hand-written route
  mirrors (`test_phase9_item_economics_route_mirror.py` and
  `tests/unit/routers/api_v1/test_item_economics_router.py`) plus `routers/README.md`
  take one additive row each, count assertions incremented. Same D10 rationale, no
  new owner card.
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

Earned by review r1 (2026-08-16; each from a probe-confirmed coverage hole):

- **Rationale-site rule (r1 lesson 1)** — a named mutation is applied at the site
  the criterion's RATIONALE names, not merely at a site that reddens the test; a
  criterion that specifies a fixture property is checked as a fixture property.
- **Lettered-parts rule (r1 lesson 2)** — multi-part criteria get one lettered row
  per part (C17a/b/c style) so the criterion→test map cannot mark a compound
  criterion green on partial coverage.
- **Service-identity rule (r1 lesson 3)** — route mount/ordering risks are guarded
  by `calls[0][0] is <service>` assertions, never by status-code + call-count
  (precedent `test_item_economics_router.py:133`).
- **One-copy rule (r1 lesson 4)** — a registered mechanism implemented in a second
  call site needs either the registry to name a shared helper both sites call, or
  a criterion per copy; an unregistered second copy is a finding.
- **Guard-is-the-reason rule (r1 lesson 5)** — mirror of charter rule 2's
  companion: each criterion's guarded construction must be the only reason its
  test passes; "delete the construction, suite stays green" is the review probe.

Earned by re-review r2 (2026-08-17):

- **No-weaker-assertions rule (r2 lesson 1)** — a fix that satisfies a criterion
  by changing a fixture must strengthen, never weaken, the assertions that pin
  that fixture; no assertion may become weaker than it was at the previous
  checkpoint (cheaply checkable: diff for `==` → `!=`/`in` in the changed seam).
  Earned: F2 met C14's fixture requirement while degrading two exact status pins
  to `!= "ok"`, leaving the fixture property silently regressable (S6).
- **Fixture-property-pin rule (r2 lesson 2, rationale-site companion)** — when a
  criterion's fixture property is what makes a guard meaningful, that property
  gets its OWN exact assertion whose value the degenerate fixture cannot produce
  (here: resolver-produced `not_configured_no_cost_group` vs short-circuit
  `not_evaluated`).

Earned by re-review r3 (2026-08-17):

- **Letter-verification rule (r3 lesson 1)** — applying the lettered-parts rule
  retroactively, each new letter is checked against the test body in the same
  pass; a letter without a test converts an invisible gap into documented false
  assurance (earned: C14c inherited a row demanded since r1 that never existed).
- **Tenant-boundary-row rule (r3 lesson 2)** — workspace scoping on any
  batch-read endpoint gets its own enumerated criterion row, like error codes
  under charter rule 2; the load-bearing top-level filter is distinguished from
  redundant defence-in-depth in advance (probe-4 equivalence: the M1 subquery's
  step-level workspace filter is redundant via globally-unique section ids —
  recorded, do not re-open).

### MVP calibration rule (owner-raised 2026-08-16, adopted at closeout)

The owner asked mid-phase whether the test discipline was over-engineered. The
assessment and the resulting rule, recorded so future pipelines inherit the
calibration rather than the ceremony:

- **Mutation probes with recorded observed-red are MANDATORY only for rule-6
  mechanisms** — derivations, rounding, filters, admission rules, statistical
  choices, money, time, ordering, dedupe keys — **plus tenant boundaries**
  (r3 lesson 2). Routes, serializers, role admission and envelopes get ordinary
  tests with no ledger row (this phase already did that: C15/C17/C18 never had
  named mutations).
- **Reviewer rounds are the expensive resource, not implementer rounds.** After a
  projection has walked the mechanisms against real data and a ledger exists, the
  first review is LIGHT-SCOPED: verify the ledger by sampling (5–6 rows), take
  full adversarial depth only on the rule-6 seams, and declare the rest settled
  ground in the handoff so later rounds never re-derive it. This phase's r1 did
  exactly that and still found five real holes.
- **Fix cycles are delta-scoped**: only the changed guards are re-probed; earlier
  ledger rows stand.
- **Evidence this calibration is right, not merely cheaper:** across four review
  rounds the discipline found **zero production defects** (M1/M2 were correct as
  first written) and **seven guards that did not guard** — including a monetary
  key admissible on the worker surface, a route-shadowing regression that would
  have passed green, and an unguarded tenant boundary. Every one was found by
  deleting a construction and observing the suite stay green. That probe — not the
  paperwork around it — is the part worth keeping.

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
  **CLOSEOUT BASELINE (2026-08-17, APPROVED — measured three times independently:
  implementer, reviewer, coordinator): 2287 passed / 26 failed / 1 deselected.**
  The 26 decompose as the same **23 v1 IDs byte-identical** + **3 FOREIGN**
  `tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py`
  failures belonging to the owner's in-flight bootstrap-seeding work (untracked at
  this gate; NOT caused by and NOT owned by this pipeline). Head unchanged
  `c1d2e3f4a5b6` — no migration in this pipeline. **The successor pipeline inherits
  2287 / 23 (+3 foreign, expected to vanish when the bootstrap work lands) / 1** —
  diff against this figure, not the v1 one (reviewer r4 closeout input 4).
- **PHASE-2 START BASELINE (verified by the coordinator 2026-08-17, three consecutive
  full runs): 2287 passed / 26 failed / 1 deselected**, ~112 s, head unchanged
  `c1d2e3f4a5b6`. The 26 failure IDs are **byte-identical to the phase-1 closeout set** —
  verified by full-set diff against the fix-r4 handoff's enumerated list, zero added, zero
  removed. Composition confirmed by `git log` on the test files: **23 long-standing
  inherited** (including
  `bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`,
  last touched in `92ec8a1`, i.e. NOT the owner's recent work) **+ 3 from the owner's
  bootstrap item-economics seeding** (`test_seed_item_economics_configuration.py`, commit
  `08092a2`). All 4 bootstrap-folder failures reproduce in isolation, so they are
  deterministic, not order-dependent.
- **KNOWN SUITE INSTABILITY (recorded, unresolved).** Of three consecutive runs, two gave
  26 failed / 2287 passed with identical IDs; **one gave 25 failed / 2288 passed**. That
  run's failure IDs were not captured, so the drifting test is **not named** — it is not
  one of the four bootstrap tests (all four fail in isolation). Consequence, binding on
  every session: **diff failure IDs, never totals.** A run reporting 25 is not "better
  than baseline"; it means one test moved and the session must identify which before
  claiming green-per-baseline. Related to the long-standing N11 suite-residue item.
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

### Post-approval graph pass — DONE 2026-08-17 (coordinator)

Scope: exactly the 14 items this phase recorded (created `2026-08-16T16:56Z`).
Each re-derived from source before its stored claim was read (skill anti-pattern
rule). Result: **13 promoted to `human_confirmed`, 1 rejected.**

- **Rejected:** `source-file-item-economics-budget-division --implements-->
  projection-working-section-typical-times`. `budget_division.py` contains no SQL
  and no query construction — it owns the constants (`:14-17`) and the pure
  `divide_production_budget` (`:78-191`); the typicals projection is implemented
  by `get_working_section_typical_times.py`, whose `typical_times_statement()`
  builds the grouped-median SQL and merely *imports* those constants. The item's
  own `inferenceReason` conceded this and its confidence was 0.35. Rejected, not
  deprecated: never true, so no provenance to preserve.
- **Promoted:** the 2 endpoints, the 2 projections, the source-file node, the
  surviving `implements` edge, both `accepts`, all three `reads_from`, and both
  domain `contains` edges. The `contains` "contradictions" the validator raised
  are noise — `contains` is legitimately one-to-many and the confirmed graph
  already carried two such edges from `domain-item-economics`.
- Deliberate placement note: the typicals projection sits under
  `domain-item-economics` even though its route/service live under
  working-sections, because **no working-sections domain node exists** (only
  `domain-task-execution`) and its constants + purpose are item-economics.
- **Left untouched:** the 6 older pending items (`2026-08-16T06:01Z`) describing
  `seed_item_economics_configuration` — the owner's unrelated in-flight bootstrap
  work, not this pipeline's to adjudicate.
- Graph: **181 nodes / 273 edges, 0 stale, pending 20 → 6**, revision
  `0372ff7c…`. Audit record:
  `.archgraph/reviews/2026-08-17T10-41-50-945Z--97cac7.yml`.

**K5 RESOLVED — it was a false alarm.** The r1 handoff self-reported that
checkpoint `0b85701` had committed `.archgraph/architecture.yml` "whole,
carrying a pre-existing foreign graph delta", and both the coordinator and the
reviewer carried that forward to this gate. Verified at closeout by reading the
committed blob: `git show 0b85701:.archgraph/architecture.yml` contains the
phase's 5 own records and **zero** `bootstrap-seed-item-economics` records. No
foreign graph state was ever bundled into a phase commit. Nothing for the owner
to accept.

**Open, owner's call (not blocking):** the graph pass's file change is applied in
tool state but is **deliberately left uncommitted**, because the working copy of
`.archgraph/architecture.yml` now also carries the owner's 6 uncommitted foreign
bootstrap graph records, and the file is rewritten wholesale by the tool — so
committing it would bundle descriptions of still-untracked bootstrap code into
this pipeline's history (the exact thing K5 feared and which never actually
happened). Options: commit it alongside the bootstrap work when that lands, or
authorize the coordinator to commit the graph file as-is.

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

**Phase-2 follow-ups recorded, deliberately NOT done in phase 2:**

- **Extract `status` + `item_binding` into a single home.** `status` is derived in three
  places (`get_task_budget_allocations.py:179-201`, `get_task_budget_status.py:112-127`,
  `get_task_budget_status_worker.py:36-52`); `item_binding` is a verbatim duplicate across
  the latter two, whose duplication carries a deliberate money-redaction comment. E3 avoids
  becoming a fourth/third site by calling `get_task_budget_status(ctx)` directly (P4).
  Extraction is a real improvement whose blast radius crosses HC-1's v1 perimeter.
- **Three ordering expressions for two orders** (N3): `_sort_key`
  (`budget_division.py:72`) is already duplicated inline at
  `get_task_budget_allocations.py:203-206`, and T1 adds `_section_sort_key`. The one-copy
  rule's trigger is visible; not phase 2's to fix.
- **`routers/api_v1/item_economics.py:345`'s ordering comment is already half untrue** —
  `/tasks/{task_client_id}/evaluations` (`:331`) is declared above the fixed batch path,
  and N1 proves segment-count difference makes the ordering non-load-bearing. Worth
  correcting so a future reader does not treat it as a constraint.

**Phase 2 gates (added 2026-08-17):**

- **Owner-card gate: C1 and C2 must be answered before the phase-2 plan is compiled.**
  C1 (allocation unit) additionally decides whether phase 1's shipped E2 numbers change,
  so it may not be deferred past projection r0.
- **Mechanism-inventory gate: WAIVED again, same reasoning, same condition.** M3 is a
  composition of the two contracted phase-1 mechanisms plus one new grouping rule, all
  contracted inline at inventory depth in intention §12.5. The waiver's condition
  carries verbatim: any mechanism the projection finds operating without a contract is a
  GATE FAILURE routed to the intention, never a note.
- **Projection gate: MANDATORY.** Charter rule 6 triggers are all present again (integer
  division with rounding residue — now at a changed unit; multi-source read consistency
  across three surfaces; a cross-surface agreement property, P-AGREE, that no phase-1
  test covered). The projection additionally owns: **re-measuring §12.4 on the database
  as it stands at that moment** (the local copy was refreshed from RDS mid-pipeline and
  the excluded-state and skipped-step counts moved), and enumerating whether variant B
  can be reached without a second allocator (HC-6).
- **Documentation closeout differs from phase 1.** The frontend handoff is **rewritten
  from scratch**, not edited (owner, 2026-08-17: "less prone to semantic errors than
  editing"). The rewrite must carry the four gaps the coordinator found on 2026-08-17 —
  step ordering authority, the transition endpoint for the card's Start action,
  `working_section_id` in the step example, and the `section_name` vs
  `section_name_snapshot` rule — plus the empty-`task_ids` warning.
