# SUMMARY_system_transition_reasons_phase2_cutover_20260731

## Metadata

- Summary ID: `SUMMARY_system_transition_reasons_phase2_cutover_20260731`
- Status: `summarized`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-07-31T17:40:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/system_transition_reasons/PLAN_system_transition_reasons_phase2_cutover_20260731.md`
- Master plan: `backend/docs/architecture/under_construction/implementation/system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
- Related debug plan: `none`

## What was implemented

Phase 2 of four. **This is the phase that ends the outage.** Clock-out with an open working step and
starting a task while another is active no longer resolve a `pause_reasons` row, so both succeed in a
workspace whose catalog is empty — **with no backfill**, because the new rows do not need the row
that is missing.

- **Clock-out** — `clock_out_shift_for_user` writes `transition_reason = SHIFT_ENDED` with
  `pause_reason_id = NULL`. Changed in the shared core, not a wrapper, so the Connecteam handler and
  the overnight safeguard inherit it by design rather than by special-casing.
- **Both task-switch sites** — `transition_step_state.py` and `_step_transition_core.py` write
  `OTHER_TASK_PRIORITY` with `pause_reason_id = NULL`. Separate modules kept in sync by convention,
  so each has its own test.
- **The derivation** — the clock-out rebuild and the live reconcile carry `transition_reason` onto
  derived rows (R14/R15, phase 1's flagged carry-forward). `LinearInterval` / `_RawSegment` /
  `LinearSegment` carry the two explanation channels **as separate fields end to end**, so the
  writer never has to recover which kind of value it holds by inspecting the string.
- **Three embedded-object render sites** synthesize the published `PauseReason` shape from the
  code-owned vocabulary when a record carries no catalog row, so no surface that rendered a pause
  label went blank.
- `get_system_pause_reason_id` reaches **zero runtime callers**; phase 4 deletes it.
- `docs/domains/worker_shifts/` updated in the same change (all three files).

Three review rounds: round 1 `NEEDS_CHANGES` (4 findings, 2 blocking), round 2 `NEEDS_CHANGES`
(3 findings, 1 blocking), round 3 **APPROVED**.

### The defect class this phase kept re-finding, and what finally closed it

Rounds 1 and 2 both raised the same underlying bug in a different place: **a serializer emitting
`null` for a record whose explanation moved from the catalog to the vocabulary.** Phase 1's audit had
ended row R2 with *"Phase 2 decides whether step payloads need the transition surfaced"* — a deferred
decision with no owner — and the path was skipped rather than decided.

- **Round 1 (R2)** found it at `domain/tasks/serializers.py:186,377`.
- **Round 2 (F1)** found it again at `get_worker_linear_timeline_breakdown.py:432`, which round 1's
  sweep missed **because the sweep grepped `.pause_reason` while that site calls
  `serialize_pause_reason` on a separately-fetched local.**

The method, not the diligence, was the problem. Re-deriving by **every caller of
`serialize_pause_reason`** plus **every construction of a twelve-field pause-reason-shaped dict**
enumerates the surface exhaustively: three render sites across two shapes, four catalog-leaf
endpoints structurally unable to receive a transition, and no third hand-rolled copy.

**Procedural lesson, recorded in the master plan's R2 row:** "phase N decides" must name what happens
if phase N does not.

### Two inputs this phase proved wrong

1. **`image_url` was never per-environment.** Phase 1 recorded that the seeded URLs are
   workspace-specific S3 paths and that `labels.py` must therefore return `None`, handing phase 3 an
   icon-loss consequence to own. They are hardcoded literals appearing in exactly two places —
   `seed_pause_reasons.py::_PAUSE_REASONS` and migration `49bd666da846:50-51` — **byte-identical to
   each other and to every workspace**; the `ws_workspace_test` segment is part of the constant, not
   a substitution. Phase 1 read the URL's *shape* as evidence of provenance. `labels.py` now
   reproduces them, and **phase 3's icon-loss consequence is closed, not inherited.**
2. **The documented `NameError` was real, and it proved more than it claimed.**
   `_step_transition_core.py` used `select` without importing it. Verified by execution that the
   auto-pause branch died at line 95 **before** reaching the catalog lookup at line 117 — so no test
   that claimed to cover that path was reaching it, and the branch is unreachable in production
   because `transition_step_state_batch` rejects non-batch-capable steps up front. Operator ruled the
   one-line import in, because criterion 3 is otherwise unmeetable.

## Files changed

**Writers (the outage fix)**

- `app/beyo_manager/services/commands/users/_clock_worker_shift.py`: catalog lookup removed; writes
  `SHIFT_ENDED` / `pause_reason_id=None`. Changed in the shared core so all three clock sources
  inherit it.
- `app/beyo_manager/services/commands/task_steps/transition_step_state.py`: auto-pause writes
  `OTHER_TASK_PRIORITY` / `pause_reason_id=None`.
- `app/beyo_manager/services/commands/task_steps/_step_transition_core.py`: same, plus
  `_apply_step_transition` gains a `transition_reason` parameter, plus the missing
  `from sqlalchemy import select` (see above).

**Derivation**

- `app/beyo_manager/domain/analytics/linear_timeline.py`: `LinearInterval`, `_RawSegment` and
  `LinearSegment` carry `transition_reason` alongside `reason`; `UNSPECIFIED_REASON` is now reachable
  only when **both** channels are absent; `transition_reason` added to the segment merge key.
- `app/beyo_manager/services/commands/users/_reconstruct_shift_middle.py`: reads and re-feeds
  `transition_reason` from step rows and from its own prior output; declarations contribute
  `WORKER_DECLARED_STATE`; writes the column onto rebuilt rows.
- `app/beyo_manager/services/commands/users/reconcile_worker_shift_state.py`: copies both channels
  off the owning step record; declaration projections carry `WORKER_DECLARED_STATE`; the no-op
  comparison includes `transition_reason`.

**Render (all three embedded-object sites)**

- `app/beyo_manager/domain/transitions/labels.py`: the seeded `image_url`s, plus `slug`,
  `requires_description`, `is_system_managed`; new
  `resolve_transition_reason_catalog_reference()` beside the existing label resolver, both served
  from one map.
- `app/beyo_manager/domain/tasks/serializers.py`: new `serialize_step_pause_reason`, used at both
  step render sites.
- `app/beyo_manager/services/queries/worker_stats/get_worker_linear_timeline_breakdown.py`:
  `record_detail`'s nested object takes the same two channels.

**Comments corrected to what is true now** (three sites that still claimed nothing writes the
column): `models/tables/tasks/step_state_record.py`,
`models/tables/users/user_shift_state_record.py`,
`services/queries/worker_stats/list_workers_linear_timeline.py` — the last sits directly above the
now-live fallback and stated it was inert.

`app/beyo_manager/services/commands/bootstrap/phases/seed_pause_reasons.py`: the drift guard now
names all three copies of the row data, not two.

**Tests** — `tests/integration/services/commands/test_system_transition_reasons_cutover.py` (new,
11); `tests/unit/domain/transitions/test_step_payload_pause_reason_render.py` (new, 8);
`tests/unit/domain/transitions/test_reason_text_contract_conformance.py` (new, 10); plus updates to
`test_transition_reason_domain.py`, `test_transition_reason_read_tolerance.py`,
`test_reconcile_worker_shift_state.py`, `test_batch_working_step_transition_integration.py`,
`tests/connecteam/test_clock_actions_integration.py`.

**Docs** — `docs/domains/worker_shifts/{README,states,api}.md`; master plan (D3/D5 amendments, audit
rows R2 and R9, the label-resolution correction, phase-3 binding item 3 closed).

## Contract adherence

- **Clarification rulings honoured.** `reason` keeps the catalog id (no migration); the API stays
  invisible — a transition serializes into the *existing* response shapes, gaining no field.
- **No `docs/handoff/to_frontend/` file was edited**, no liveness row flipped.
- **The archived declared_worker_states master plan was not edited**; D3/D5 amendments live in this
  feature set's master plan.
- T1/T2 (code-owned vocabulary, `pause_reason_id = NULL` for system transitions), T3 (no column on
  `user_declared_state_records`), **T7 (`manually_recorded` and the `changed_by_id` heuristic
  untouched — verified clean by the round-2 reviewer)**, T8 (no baseline debt absorbed; the five
  pre-existing `F401`s in `transition_step_state.py` were left alone).
- `46_serialization.md`: the published `PauseReason` shape is reproduced in full — all twelve fields,
  non-nullable `slug`, so an embedded object cannot fail client validation.

## Validation evidence

- **Full suite, failure node sets, run-2 vs run-2:** `26 failed / 1396 passed`, run-1 and run-2 node
  sets identical to each other and unchanged across all three review rounds. **Zero new failure
  nodes.** No worker-shift or clock-out node appears in the set at all.
- **Failing-first proven by reverting, never assumed** — for every behavioural claim:
  - zero-catalog clock-out → `NotFound: System pause reason 'pause_ended_shift' is not configured.`
  - zero-catalog task switch (single endpoint) → the `pause_other_task_priority` equivalent.
  - task switch via the shared core → `NameError: name 'select' is not defined` at line 95, i.e.
    *before* the catalog lookup.
  - R2 → 6 of 8 render tests fail, the 2 controls pass.
  - R9/F1 → `assert None is not None`, with the catalog-carrying control green and unmodified.
- **Anti-vacuity mutations:** restoring the naive `reason or UNSPECIFIED_REASON` fallback kills the
  rebuild test; untyping the declaration kills both declaration tests.
- **Zero-catalog tests cannot pass vacuously:** every one asserts its workspace holds zero
  `pause_reasons` rows before exercising anything.
- **Criterion 18 measured, not claimed:** with clock-out reverted, `test_worker_shift_commands.py`
  fails exactly one node through the `pause_ended_shift` `NotFound`; with the phase applied, 42/42
  pass. The declared_worker_states baseline recorded *two* clock-out failures here; only one
  reproduces in this tree, so that note is stale.
- `ruff check` clean on every touched file.

## Known gaps or deferred items

- **Criterion 11 is not met, deliberately.** The `startswith(CLIENT_ID_PREFIX)` branch in
  `domain/users/serializers.py` is provably **alive**, not dead: under the operator's "keep `reason`,
  no migration" ruling, that field still holds `par_…` ids and legacy strings on pre-cutover rows,
  and the branch is what distinguishes a dangling catalog id (`reason_text: null`) from displayable
  text (`reason_text: "<raw>"`). **Phase 3's backfill discharges it**, after which it can be shown
  dead. Master-plan success criterion 4 is a feature-set criterion and is unaffected.
- **`app/scripts/backfill/backfill_worker_shift_state_records.py` builds `LinearInterval`s without
  `transition_reason`.** Same R14 mechanism, in a module this phase's scope list does not name. It is
  a one-time historical script and phase 3 owns historical data, so it was flagged rather than folded
  in. **Phase 3 should pick this up.**
- **Hardcoded S3 URLs in runtime domain code — accepted risk, not a finding.** Assessed by the
  round-2 reviewer: blast radius is one row per slug database-wide (`uq_pause_reasons_slug` is
  globally unique); the host matches `.env.production.ec2`'s `STORAGE_BUCKET`;
  `update_pause_reason.py:43` has no `is_system_managed` guard so an admin *can* diverge that row,
  but `seed_pause_reasons.py:39-46` repairs `image_url` on bootstrap rerun, making divergence
  transient and the worst case a stale icon. The same exposure already applied to `name`, which
  round 1 accepted under criterion 5. **Adding the missing guard to `update_pause_reason` is a
  separate change with its own blast radius** and was deliberately not made here.
- **Production was never measured.** The RDS is unreachable from the operator's machine, so every
  figure in this feature set comes from the dev/test database. This bears on the URL risk above.
- **`pause_case_created` disposition (phase 3)** and **the phase-3 plan's clarification 3**, which
  still presumes that row needs its own enum member, remain as phase 1 left them.

## Handoff notes (if needed)

- To frontend: **none.** The operator ruled the invisible option, and the phase holds to it — a
  system transition serializes into the *existing* shapes (`pause_reason` object, `pause_by_reason`
  key, the three-way `reason_text`), gaining no field. Rendered names and icons are preserved rather
  than changed, which is why no handoff update was proposed.
- From frontend dependency: none.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/system_transition_reasons/ARCHIVE_RECORD_PLAN_system_transition_reasons_phase2_cutover_20260731.md`
