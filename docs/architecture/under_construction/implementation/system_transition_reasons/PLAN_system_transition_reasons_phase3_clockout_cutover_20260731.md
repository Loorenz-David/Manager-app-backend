# PLAN_system_transition_reasons_phase3_clockout_cutover_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase3_clockout_cutover_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: clock-out stops resolving `pause_ended_shift` from the catalog. It writes
  `transition_reason = SHIFT_ENDED` with `pause_reason_id = NULL`, and the
  `get_system_pause_reason_id` call is deleted from that path.
- Business/user intent: **this phase ends the outage.** In the 3131 workspaces with no
  `pause_ended_shift` row, clock-out with an open WORKING step currently fails. After this phase it
  succeeds, because nothing is looked up. No backfill is required for that to be true — new rows do
  not need the missing row.
- Non-goals: the task-switch path (phase 4); the derivation rebuild (phase 5); historical data
  (phase 8); the catalog itself (phase 9).

## Scope

- In scope: `services/commands/users/_clock_worker_shift.py` — the `pause_ended_shift` resolution at
  ~line 200 and the record it writes.
- Out of scope: `clock_out_worker_shift.py` / `toggle_worker_shift.py` wrappers, the routes, and
  anything analytics-side. The Connecteam handler and the midnight safeguard call
  `clock_out_shift_for_user` directly and inherit this change **by design** — verify they do, and do
  not special-case them.
- Assumptions: phases 1 and 2 archived. **T4 is satisfied** — readers already resolve
  `transition_reason`. If phase 2 is not archived, STOP.

## Clarifications required

- [ ] None expected. If the auto-pause record written on clock-out carries a `description`, decide
      whether it survives unchanged (it should — Q4, master plan) and record it.

## Acceptance criteria

1. **The zero-catalog test is the headline deliverable**: a workspace with **no `pause_reasons` rows
   at all**, a worker clocked in with an open WORKING step, clock-out succeeds, the step is closed,
   and the record carries `transition_reason = SHIFT_ENDED` with `pause_reason_id = NULL`. This test
   must fail against the pre-phase code — verify that it does.
2. `get_system_pause_reason_id` is no longer called from `_clock_worker_shift.py`. The function
   itself stays (phase 4 still has callers); only this call site goes.
3. `clock_out_shift_for_user` keeps its existing signature and return shape. Its callers — the
   command wrappers, the Connecteam handler, and `auto_clock_out_open_shifts` — are unmodified, and
   each is proven to still work.
4. **The midnight safeguard and Connecteam inherit the fix**, tested explicitly. They are the paths
   most likely to run in a workspace nobody has curated.
5. Existing clock-out behaviour otherwise unchanged: the same steps transition, the same timestamps,
   the same `transitioned_steps` count, the same partial-unique-index invariants.
6. Rows written before this phase are untouched, and still resolve to their existing label via
   phase 2's fallback. Prove with a seeded pre-phase row.
7. The two clock-out tests already in the baseline failure set (declared_worker_states master plan,
   "Repository validation baseline") are re-checked: state whether this phase fixes either. If one
   was failing *because* of the missing catalog row, it should now pass — that is evidence, and it
   belongs in the Review log.
8. Declared-state interaction preserved: a worker who declared a state and then clocks out ends with
   the declaration handled exactly as before (declared_worker_states D3/D5 semantics still hold —
   they are amended in phase 5, not here).

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: command conventions.
- `backend/architecture/01_architecture.md`: layering.
- `backend/architecture/17_logging.md`: if any log line changes.

### File read intent — pattern vs. relational

- Permitted (relational): `_clock_worker_shift.py` (the path being changed); the Connecteam handler
  and `auto_clock_out_open_shifts.py` to confirm how they call in; `step_state_record.py` for exact
  field names.
- Prohibited (pattern): reading another command to learn flush/error-raising shape —
  `06_commands.md` covers it.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Confirm phase 2 archived (T4). If not, STOP.
2. Replace the `pause_ended_shift` resolution with a direct `transition_reason = SHIFT_ENDED` write,
   `pause_reason_id = NULL`.
3. Delete the now-unused import if nothing else in the module uses it.
4. Write the zero-catalog test (criterion 1) and confirm it fails against pre-phase code.
5. Test the Connecteam and midnight-safeguard paths explicitly.
6. Verify pre-phase rows still resolve (criterion 6).
7. Re-check the two baseline clock-out failures; record the outcome.
8. Review log entry. STOP for independent review.

## Risks and mitigations

- Risk: a read path missed in phase 2 surfaces here as a null label in production.
  Mitigation: criterion 1's zero-catalog test exercises the full clock-out response, not just the
  DB row; the reviewer should additionally read the response payload end-to-end.
- Risk: the change is made in the wrong layer — e.g. in a wrapper rather than in
  `clock_out_shift_for_user` — leaving Connecteam and the midnight safeguard still broken.
  Mitigation: criteria 3 and 4 test those two paths directly. This is the exact mistake shape that
  produced declared_worker_states Phase 7's F1 (fix applied at the wrong level, invisible to the
  tests that were written).
- Risk: the zero-catalog test passes vacuously because the fixture seeds reasons anyway.
  Mitigation: criterion 1 requires it to fail against pre-phase code.

## Validation plan

- Zero-catalog clock-out test: passes now, fails on pre-phase code.
- Connecteam + midnight-safeguard tests pass.
- Pre-phase seeded row still resolves to its original label.
- Full suite: no new failure nodes vs. baseline (node sets, not counts); note any baseline failure
  this phase legitimately fixes.
- `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
