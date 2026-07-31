# PLAN_system_transition_reasons_phase5_derivation_cutover_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase5_derivation_cutover_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: the clock-out rebuild writes `transition_reason` onto derived `UserShiftStateRecord` rows,
  and `reason` stops being a polymorphic slot holding either a `par_…` id or free text.
- Business/user intent: `UserShiftStateRecord.reason` is the field the intention identifies as most
  overloaded, evidenced by the shipped `startswith("par_")` disambiguation. This phase removes the
  ambiguity at the **write** side; phase 7 removes the read-side workaround.
- Non-goals: `manually_recorded` (phase 6); the serializer branch and published contract (phase 7);
  historical rows (phase 8).

## Scope

- In scope: `services/commands/users/_reconstruct_shift_middle.py` (the rebuild),
  `reconcile_worker_shift_state.py`, and `heal_open_shifts_today.py` where they write derived rows.
- Out of scope: the source tables; live state derivation (`derive_target_state`) unless phase 0's
  audit shows it writes rather than reads.
- Assumptions: phases 1–4 archived. Source rows now carry `transition_reason`, so the rebuild has
  something to carry through.

## Clarifications required

- [ ] Does `reason` keep holding the catalog id for worker-chosen pauses, or does the derived row
      gain a proper `pause_reason_id` column of its own? The second is cleaner and finishes the job;
      the first is smaller. Blocks because it decides whether this phase carries a migration.
      **Operator decision — escalate rather than choosing.**

## Acceptance criteria

1. Derived rows produced by the rebuild carry `transition_reason` reflecting their source: a step
   closed by clock-out yields `SHIFT_ENDED`; an auto-pause yields `OTHER_TASK_PRIORITY`; a
   declaration yields `WORKER_DECLARED_STATE`.
2. **D3/D5 amendment recorded** — in **this** feature set's master plan ("Amendments to
   declared_worker_states decisions"), and in this plan's Review log stating which decision changed
   and how. The declared_worker_states plan is **archived and must not be edited**. This is a
   deliverable, not documentation housekeeping.
3. **The rebuild remains idempotent.** Running it twice over the same source data produces identical
   derived rows. Declared_worker_states Phase 2 burned four fix cycles here (F1/F2, G1, H1, I1);
   treat idempotence as the phase's central invariant, not a nice-to-have.
4. **Declarations survive the rebuild.** The architectural spine of declared_worker_states is that
   declared states are a *source* table so the clock-out rebuild cannot erase them. Prove it still
   holds: declare a state, clock out, assert the declaration is represented in the derived timeline.
5. Ownership priority is preserved: where a step-sourced segment and a declaration overlap, the same
   one wins as before this phase. Assert against the existing expected behaviour, not a fresh
   derivation of it.
6. Legacy rows written before any of this — free-text `reason`, no `transition_reason` — still
   rebuild correctly and still resolve via phase 2's fallback.
7. `manually_recorded` is written exactly as today. Phase 6 owns it; changing it here is a scope
   violation and will look like a fix.
8. The `changed_by_id`-based provenance distinguisher introduced by declared_worker_states Phase 2
   (G1) still functions. Phase 6 removes it; until then it must keep working, and this phase must
   not accidentally invalidate it.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`
- `backend/architecture/01_architecture.md`
- `backend/architecture/03_models.md` (only if the clarification produces a new column)

### File read intent — pattern vs. relational

- Permitted (relational): the rebuild module and its callers; `user_shift_state_record.py`;
  `user_declared_state_record.py`; the declared_worker_states master plan's D1–D14 for the semantics
  being amended.
- Prohibited (pattern): reading other commands for style.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Escalate the clarification; wait for the operator ruling.
2. Carry `transition_reason` from source rows through the rebuild onto derived rows.
3. Idempotence tests (criterion 3) — run the rebuild twice, assert identical output.
4. Declaration-survival test (criterion 4).
5. Legacy-row rebuild test (criterion 6).
6. Amend D3/D5 in the declared_worker_states master plan.
7. Review log entry, including the idempotence evidence. STOP.

## Risks and mitigations

- Risk: the rebuild launders provenance, as it did in declared_worker_states Phase 2 (H1) — the
  original actor was lost and `heal_open_shifts_today.py` then reopened the laundered row.
  Mitigation: criterion 8 plus an explicit test that the original `changed_by_id` survives.
- Risk: ownership priority silently changes, erasing declarations (the F1/F2 failure).
  Mitigation: criterion 5 asserts against existing expected behaviour.
- Risk: this phase is treated as the place to "clean up" `manually_recorded` too.
  Mitigation: criterion 7 makes that a scope violation.

## Validation plan

- Rebuild-twice idempotence: identical derived rows.
- Declaration survives clock-out.
- Legacy free-text row rebuilds and resolves.
- `changed_by_id` provenance preserved end-to-end.
- Full suite: no new failure nodes vs. baseline. `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
