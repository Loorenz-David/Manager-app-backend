# ARCHIVE_RECORD_PLAN_system_transition_reasons_phase2_cutover_20260731

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_system_transition_reasons_phase2_cutover_20260731`
- Archived at (UTC): `2026-07-31T17:40:00Z`
- Archive owner agent: `claude-opus-5` (on operator direction, post-review)

## Source references

- Plan: `backend/docs/architecture/archives/implementation/system_transition_reasons/PLAN_system_transition_reasons_phase2_cutover_20260731.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_system_transition_reasons_phase2_cutover_20260731.md`
- Master plan (intention role): `backend/docs/architecture/under_construction/implementation/system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention: `backend/docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
- Debug chain: `none`

## Outcome classification

- Result: `completed`
- Acceptance criteria: 19 of 20 met with evidence; **criterion 11 recorded as a deliberate
  non-completion**, discharged by phase 3 (see below). APPROVED at round 3, after `NEEDS_CHANGES` at
  rounds 1 (4 findings, 2 blocking) and 2 (3 findings, 1 blocking).
- Validation gates: **not waived.** Failure node sets identical across all three rounds
  (`26 failed / 1396 passed`, run-1 == run-2), zero new failure nodes, `ruff check` clean on touched
  files. The pre-existing repository baseline was neither absorbed nor repaired (T8).

## Final notes

- **The outage is ended.** Clock-out and task switching no longer resolve a catalog row, so both work
  in a workspace with an empty catalog. Every behavioural claim was proved **failing-first by
  reverting the writer**, never asserted: the zero-catalog tests reproduce the exact `NotFound` the
  intention described.
- **The change is in `clock_out_shift_for_user` itself.** Connecteam and the overnight safeguard
  inherit it by design. The Connecteam test previously *patched* the catalog resolver to make the old
  behaviour work; that patch is deleted and the test now exercises the real path.
- **The finding worth remembering: R2, and then R2 again.** Phase 1's audit closed row R2 with *"Phase
  2 decides whether step payloads need the transition surfaced"* — a deferred decision with no owner —
  so the path was skipped rather than decided, and a transition-typed record serialized `pause_reason:
  null` where a populated object used to be. Round 1 caught it at
  `domain/tasks/serializers.py:186,377`. **Round 2 caught the same bug again** at
  `get_worker_linear_timeline_breakdown.py:432`, which round 1's sweep had missed because it grepped
  `.pause_reason` while that site calls `serialize_pause_reason` on a separately-fetched local.
  The method was the defect. Re-deriving by **caller of `serialize_pause_reason`** plus **construction
  of a twelve-field pause-reason-shaped dict** enumerates the surface exhaustively — three render
  sites across two shapes, four catalog-leaf endpoints structurally unable to receive a transition,
  no third copy. **"Phase N decides" must name what happens if phase N does not**; recorded in the
  master plan's R2 row.
- **Two phase 1 inputs were overturned.** (i) `image_url` is *not* per-environment — the seeded URLs
  are hardcoded literals identical in every workspace, appearing byte-identically in
  `seed_pause_reasons.py` and migration `49bd666da846`. Phase 1 read the URL's shape as evidence of
  provenance. `labels.py` now reproduces them, which **closes phase 3's icon-loss consequence rather
  than passing it on** (master plan phase-3 binding item 3, struck). (ii) The documented `NameError`
  in `_step_transition_core.py` was still present, and execution showed it fired *before* the catalog
  lookup — so no test that claimed to cover that auto-pause was reaching it, and the branch is
  unreachable in production because the batch command rejects non-batch-capable steps up front.
- **The load-bearing guard this phase had to get right** was the mirror image of phase 1's F1:
  `owner.interval.reason or UNSPECIFIED_REASON` reads as a null check but means "this pause explains
  nothing", and `reason is None` became the *normal* state of a system transition. Left alone, every
  auto-pause and ended-shift segment would have bucketed as `unspecified`. Fixed so the fallback is
  reachable only when both channels are absent, and made structural: the two channels travel as
  **separate fields** through the sweep, so no writer can recover the distinction by inspecting a
  string.
- **Documentation caught a real divergence.** `states.md` claimed the rebuild preserves
  `changed_by_id` generally; the code preserves it only for legacy manual rows. Investigated rather
  than patched: the archived declared_worker_states plan states *"Reconcile-authored declaration
  projections have `changed_by_id IS NULL`"*, which is the discriminator holding an actor-authored
  manual pause sticky against re-derivation. **The code was right and the doc wrong** — giving a
  declaration projection an actor would reintroduce the H1 defect class and violate T7. The doc now
  states the narrowness *and why it is load-bearing*, and criterion 10's test pins both arms.
- **Criterion 11 is an open, recorded non-completion.** The `startswith(CLIENT_ID_PREFIX)` branch is
  provably alive under the operator's "keep `reason`" ruling, because pre-cutover rows still carry
  both `par_…` ids and legacy strings. **Phase 3's backfill discharges it.** It was reported as a
  gap in every round rather than counted as passing.
- **Carried into phase 3:** the `backfill_worker_shift_state_records.py` script builds
  `LinearInterval`s without `transition_reason` (same R14 mechanism, outside this phase's named
  scope); `pause_case_created` must not be nulled; and the phase-3 plan's clarification 3 still
  presumes that row needs its own enum member, which phase 1's F4 disposition contradicts.
- **Accepted risk, not a finding:** hardcoded S3 URLs now sit in runtime domain code. One row per
  slug database-wide, host matching production configuration, self-repairing on bootstrap rerun,
  worst case a stale icon. The missing `is_system_managed` guard on `update_pause_reason.py:43` is
  real but is a separate change with its own blast radius. **Production was never measured** — the
  RDS is unreachable from the operator's machine — so this rests on repository evidence alone.
