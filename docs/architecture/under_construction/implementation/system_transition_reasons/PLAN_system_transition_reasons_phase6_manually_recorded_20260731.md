# PLAN_system_transition_reasons_phase6_manually_recorded_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase6_manually_recorded_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: determine whether `transition_reason` subsumes `manually_recorded` (**T7**) and, if it does,
  remove the redundant field and the `changed_by_id`-based provenance heuristic that stands in for
  it.
- Business/user intent: declared_worker_states Phase 2 spent four fix cycles (F1/F2, G1, H1, I1)
  discriminating worker-initiated from system-derived rows, settling on `changed_by_id IS NOT NULL`.
  A typed transition field should make that unnecessary. This phase is the payoff — or the proof
  that the two concepts are genuinely distinct.
- Non-goals: the serializer contract (phase 7); historical rows (phase 8).

## Scope

- In scope: `UserShiftStateRecord.manually_recorded` and every reader/writer of it; the
  `changed_by_id` provenance distinguisher; `_LEGACY_MANUAL_PAUSE_PRIORITY` in the rebuild.
- Out of scope: source tables; the published contract (phase 7 proposes changes there).
- Assumptions: phases 1–5 archived.

## Clarifications required

- [ ] None expected — but see criterion 1. If the analysis concludes the two concepts are **not**
      equivalent, this phase's scope collapses to documenting why, and that is a legitimate outcome.
      **STOP and report rather than forcing a removal.**

## Acceptance criteria

1. **A written equivalence analysis comes first**, in the Review log, before any code changes:
   enumerate every distinct `(transition_reason, manually_recorded, changed_by_id)` combination that
   currently occurs, from real data where phase 0's inventory allows and from code paths otherwise.
   Show either that `manually_recorded` is derivable from `transition_reason` in every case, or
   identify the case where it is not. **This analysis is the deliverable.** Removal without it is
   the finding, even if the removal is correct.
2. If equivalent: `manually_recorded` reads are replaced by `transition_reason` checks, and the
   column is dropped only after phase 8's backfill guarantees every row has a `transition_reason`.
   If the backfill has not run, the column stays and only the *readers* change — record which.
3. If NOT equivalent: T7 is amended in the master plan with the counterexample, both fields stay,
   and the phase closes with documentation only. This is success, not failure.
4. The `changed_by_id` provenance heuristic is removed **only** if criterion 1 shows
   `transition_reason` covers every case it covers. `changed_by_id` itself stays — it is real
   attribution data, not provenance machinery.
5. Legacy manual-pause stickiness (declared_worker_states G1) and `/resume` behaviour are preserved.
   These broke once already from exactly this kind of change; assert them explicitly.
6. `_LEGACY_MANUAL_PAUSE_PRIORITY` in the rebuild is re-examined: state whether it is still
   load-bearing after the change, and remove it only with evidence.
7. Rebuild idempotence (phase 5 criterion 3) still holds.

## Contracts and skills

### Contracts loaded

- `backend/architecture/03_models.md` (if the column is dropped)
- `backend/architecture/04_migrations.md` (if the column is dropped)
- `backend/architecture/01_architecture.md`

### File read intent — pattern vs. relational

- Permitted (relational): every reader/writer of `manually_recorded`; the rebuild; the
  declared_worker_states Phase 2 plan's Review log, which records why the heuristic exists — read it
  before removing it.
- Prohibited (pattern): style reads.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Write the equivalence analysis (criterion 1). Record it before touching code.
2. If not equivalent: amend T7, document, STOP.
3. If equivalent: replace readers; decide column-drop timing against phase 8.
4. Remove the `changed_by_id` heuristic if and only if covered.
5. Assert G1 stickiness, `/resume`, and rebuild idempotence.
6. Review log entry with the analysis and the decision. STOP.

## Risks and mitigations

- Risk: the removal is made because it is tidy, not because it is proven — and a provenance case
  silently changes behaviour.
  Mitigation: criterion 1 makes the analysis the deliverable and removal-without-it a finding.
- Risk: `/resume` strands with a 409, as it did in declared_worker_states G1.
  Mitigation: criterion 5 asserts it explicitly.
- Risk: the column is dropped before backfill, leaving rows with neither field meaningful.
  Mitigation: criterion 2 ties the drop to phase 8.

## Validation plan

- Equivalence analysis present in the Review log, with the enumerated combinations.
- Legacy stickiness and `/resume` tests pass.
- Rebuild idempotence holds.
- Full suite: no new failure nodes vs. baseline. `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
