# PLAN_system_transition_reasons_phase10_constraints_cleanup_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase10_constraints_cleanup_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: make the invariants the previous phases established **enforceable by the database** rather
  than by convention, and close out the feature set.
- Business/user intent: the whole point of moving system transitions into code was that a guarantee
  should hold by construction. Constraints are where that guarantee stops depending on every future
  writer remembering.
- Non-goals: new behaviour of any kind.

## Scope

- In scope: constraints on `transition_reason` and `pause_reason_id`; removing phase 2's
  now-unreachable fallback if it is provably dead; final documentation.
- Out of scope: anything behavioural.
- Assumptions: phases 1–9 archived; the backfill has run everywhere the constraints will apply.

## Clarifications required

- [ ] Does `transition_reason` become `NOT NULL`, or does null remain meaningful for
      worker-chosen pauses? Depends on phase 1's `WORKER_PAUSED` ruling. If null is meaningful, the
      constraint is a check (`transition_reason IS NOT NULL OR pause_reason_id IS NOT NULL`) rather
      than `NOT NULL`. Resolve from phase 1's recorded ruling, not by re-deciding it.

## Acceptance criteria

1. The mutual-exclusion invariant is enforced by a check constraint: a row carrying a system
   `transition_reason` must have `pause_reason_id IS NULL`. This is the database making **T2** true
   rather than trusting future writers.
2. Whatever the clarification resolves, **every existing row satisfies the constraint before it is
   added** — verified by query, recorded, not assumed. Adding a constraint that fails validation on
   production data is the failure mode this criterion exists to prevent.
3. Phase 2's `pause_reason_id` fallback in the read paths: either removed with proof that no row can
   reach it, or **kept with a comment explaining why it must stay**. Silently leaving dead code is a
   finding; so is removing a branch that legacy rows still need. Phase 8's parity evidence decides
   which.
4. All six master-plan success criteria are re-verified end-to-end and the evidence recorded — not
   inherited from the phases that first claimed them. In particular criterion 1 (clock-out in a
   zero-catalog workspace) and criterion 6 (second-workspace bootstrap) are re-run fresh.
5. **D3, D5 and D14** carry their final amendment state in **this** master plan's amendments table,
   consistent with what actually shipped. The declared_worker_states plan is archived and is not
   edited — verify no phase edited it.
6. The intention plan's status is moved to `achieved`, its "Linked implementation plans" table is
   filled in, and its open questions are answered or explicitly closed.
7. Any repo-health item found but deliberately not fixed across phases 0–9 (T8) is collected into
   one list in the master plan, so the deferrals are visible rather than lost.

## Contracts and skills

### Contracts loaded

- `backend/architecture/04_migrations.md`
- `backend/architecture/23_documentation.md`

### File read intent — pattern vs. relational

- Permitted (relational): every Review log from phases 0–9, to verify criteria rather than trust
  them; the intention plan.
- Prohibited (pattern): style reads.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Resolve the clarification from phase 1's recorded ruling.
2. Verify by query that every existing row satisfies the intended constraint.
3. Add the constraint migration.
4. Decide phase 2's fallback: remove with proof, or keep with a comment.
5. Re-verify all six success criteria fresh; record the evidence.
6. Finalise the D3/D5/D14 amendments.
7. Move the intention to `achieved`; fill its linked-plans table; close its open questions.
8. Collect deferred repo-health items into the master plan.
9. Review log entry. STOP for final review.

## Risks and mitigations

- Risk: the constraint is added and fails validation against production data mid-deploy.
  Mitigation: criterion 2 requires proving compliance by query first.
- Risk: the fallback is removed while legacy rows still need it, breaking historical labels.
  Mitigation: criterion 3 ties the decision to phase 8's parity evidence.
- Risk: success criteria are marked met by citing earlier phases' claims.
  Mitigation: criterion 4 requires fresh re-verification.

## Validation plan

- Pre-constraint compliance query returns zero violating rows.
- Constraint rejects a deliberately invalid insert.
- All six master-plan success criteria re-verified fresh, with evidence.
- Full suite: no new failure nodes vs. baseline. `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
