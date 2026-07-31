# PLAN_system_transition_reasons_phase2_cutover_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase2_cutover_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: every writer stops resolving system reasons from the catalog. Clock-out, both task-switch
  sites, the derivation rebuild, and the serializer all move to `transition_reason`.
- Business/user intent: **this phase ends the outage.** In the 3131 workspaces with no
  `pause_ended_shift` row, clock-out with an open WORKING step currently fails, and starting a task
  while another is active fails too. After this phase both succeed — **without any backfill**,
  because new rows do not need the row that is missing.
- Non-goals: historical data (phase 3); the catalog itself (phase 4); `manually_recorded` and the
  `changed_by_id` heuristic (T7 — deferred; touching either is a scope violation).

## Scope

- In scope: `services/commands/users/_clock_worker_shift.py` (~line 200);
  `services/commands/task_steps/transition_step_state.py` (~line 274) and
  `_step_transition_core.py` (~line 114); the rebuild
  (`_reconstruct_shift_middle.py`, `reconcile_worker_shift_state.py`, `heal_open_shifts_today.py`);
  `domain/users/serializers.py`.
- Out of scope: the command wrappers, routes, and analytics composers — the Connecteam handler and
  the midnight safeguard call `clock_out_shift_for_user` **directly** and must inherit this change
  by design. Verify they do; do not special-case them. Every `docs/handoff/to_frontend/` file is
  operator-owned: **propose, never edit**.
- Assumptions: phase 1 archived. Readers already tolerate `transition_reason`.

## Clarifications required

- [ ] **Q4** — `auto_pause_description = f"started working with {identifier}"` is written to
      `StepStateRecord.description`. Provisional ruling: it stays unchanged, being a per-instance
      detail that typing the transition does not make redundant. Confirm or escalate.
- [ ] **Does `UserShiftStateRecord.reason` keep holding the catalog id for worker-chosen pauses**, or
      does the derived row gain its own `pause_reason_id` column? The second is cleaner and finishes
      the job; the first is smaller. Decides whether this phase carries a migration.
      **Operator decision — escalate rather than choosing.**
- [ ] **Does the API surface `transition_reason` to clients**, or keep producing the existing
      `reason` / `reason_text` shape with the type resolved server-side? Default if unanswered: the
      invisible option, because it needs no frontend work. Escalate.

## Acceptance criteria

### The outage fix

1. **Zero-catalog clock-out**: a workspace with **no `pause_reasons` rows at all**, a worker clocked
   in with an open WORKING step, clock-out succeeds, the step closes, and the record carries
   `transition_reason = SHIFT_ENDED` with `pause_reason_id = NULL`. **Must fail against pre-phase
   code** — verify that it does.
2. **Zero-catalog task switch**: same workspace, a worker starts a task while another is active, the
   conflicting step auto-pauses with `OTHER_TASK_PRIORITY` and `pause_reason_id = NULL`. Must fail
   against pre-phase code.
3. **Both task-switch sites changed.** `transition_step_state.py` and `_step_transition_core.py` are
   separate paths reached by different endpoints (single vs. batch). **A test per path.** One test
   hitting one path is the likely failure mode of this phase.
4. `get_system_pause_reason_id` has **zero runtime callers** — confirm by grep across `app/`
   excluding tests. The function is deleted in phase 4, not here; zero callers is this phase's proof
   of completion.
5. **The midnight safeguard and Connecteam inherit the fix**, tested explicitly. They are the paths
   most likely to run in a workspace nobody has curated.

### Derivation

6. Derived rows from the rebuild carry `transition_reason` reflecting their source: clock-out →
   `SHIFT_ENDED`; auto-pause → `OTHER_TASK_PRIORITY`; declaration → `WORKER_DECLARED_STATE`.
7. **The rebuild remains idempotent** — running it twice over the same source data produces
   identical derived rows. declared_worker_states Phase 2 burned four fix cycles here; treat this as
   the central invariant, not a nice-to-have.
8. **Declarations survive the rebuild.** The architectural spine of declared_worker_states is that
   declarations are a *source* table the rebuild cannot erase. Declare a state, clock out, assert it
   is represented in the derived timeline.
9. Ownership priority preserved: where a step-sourced segment and a declaration overlap, the same
   one wins as before. Assert against existing expected behaviour, not a fresh derivation of it.
10. The rebuild does not launder `changed_by_id`. It did once (H1), and `heal_open_shifts_today.py`
    then reopened the laundered row. Assert the original actor survives end-to-end.

### Serializer

11. The `startswith(f"{PauseReason.CLIENT_ID_PREFIX}_")` branch in `domain/users/serializers.py` is
    gone, or provably dead with a test showing no input reaches it (master-plan success criterion 4
    accepts either).
12. The published three-way `reason_text` contract — absent / string / null — behaves exactly as
    handoff §5.3 documents, for four cases: a system transition, a worker-chosen catalog pause, a
    declared state, and a legacy free-text row. Four cases, four tests, asserted against the handoff
    text.
13. **No published contract changes without an operator-approved handoff update.** If this phase
    concludes one is needed, write the proposal in the Review log and STOP. Do not edit the handoff,
    do not flip a liveness row.
14. The kiosk clock-out analytics contract is unaffected, or the effect is in the proposal. Re-run
    phase 1's compatibility tests.

### Whole-phase

15. Pre-phase rows still resolve to their existing labels via phase 1's fallback — prove with seeded
    rows of each legacy shape.
16. Existing behaviour otherwise identical: same steps transition, same timestamps, same
    `transitioned_steps` counts, same partial-unique-index invariants, same response shapes.
17. `_step_transition_core.py` has a documented pre-existing `NameError` (missing `select` import)
    on the auto-pause path. **Determine whether it is still present.** If so it is baseline debt
    (T8) — record it, do not fix it, and note that any test claiming to exercise that path before
    the fix was not actually reaching it.
18. The two clock-out tests in the recorded baseline failure set: state whether this phase fixes
    either. If one failed *because* of the missing catalog row, it should now pass — that is
    evidence, and it belongs in the Review log.
19. D3 and D5 amendments recorded in **this feature set's** master plan and in this Review log. The
    declared_worker_states plan is **archived and must not be edited**.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: command conventions.
- `backend/architecture/01_architecture.md`: layering.
- `backend/architecture/46_serialization.md`: output shapes.
- `backend/architecture/17_logging.md`: if any log line changes.

### File read intent — pattern vs. relational

- Permitted (relational): the five modules being changed; the Connecteam handler and
  `auto_clock_out_open_shifts.py` to confirm how they call in; `step_state_record.py` and
  `user_shift_state_record.py` for exact fields; handoff §5.1/§5.3 for the contract being preserved;
  the archived declared_worker_states Phase 2 Review log for why the provenance machinery exists.
- Prohibited (pattern): reading another command for flush/error-raising shape (`06_commands.md`),
  another serializer for output style (`46_serialization.md`).

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Escalate all three clarifications; wait for rulings before writing code they affect.
2. Clock-out first (criterion 1) — the highest-value change. Then both task-switch sites (2, 3).
3. Verify zero runtime callers of `get_system_pause_reason_id`.
4. Test Connecteam and the midnight safeguard explicitly.
5. Derivation: carry `transition_reason` through the rebuild; idempotence and declaration-survival
   tests; assert `changed_by_id` survives.
6. Serializer: remove the prefix branch; four contract-conformance tests.
7. Legacy-row resolution tests; the `NameError` check; the baseline-failure re-check.
8. Record the D3/D5 amendments. Review log entry. STOP for independent review.

## Risks and mitigations

- Risk: the change lands at the wrong level — in a wrapper rather than in `clock_out_shift_for_user`
  — leaving Connecteam and the midnight safeguard broken. This is exactly the shape of
  declared_worker_states Phase 7's F1: a fix applied one layer off, invisible to the tests written
  for it.
  Mitigation: criteria 5 and the zero-catalog tests exercise the real paths.
- Risk: only one of the two task-switch sites is changed.
  Mitigation: criteria 3 and 4 — a test per path plus a zero-caller grep.
- Risk: the rebuild erases declarations or changes ownership priority (F1/F2).
  Mitigation: criteria 8 and 9 assert against existing expected behaviour.
- Risk: a silent breaking change ships to a frontend already built against the contract. This
  happened once here — `pause_by_reason` keys went opaque with no lookup map, caught only in
  post-archive review.
  Mitigation: criteria 12, 13, 14 — assert against handoff text, propose rather than edit.
- Risk: the zero-catalog tests pass vacuously because a fixture seeds reasons anyway.
  Mitigation: criteria 1 and 2 require them to fail against pre-phase code.

## Validation plan

- Zero-catalog clock-out and task-switch tests: pass now, fail on pre-phase code.
- One test per task-switch path; `get_system_pause_reason_id` grep returns definition only.
- Connecteam + midnight-safeguard tests pass.
- Rebuild-twice idempotence: identical derived rows. Declaration survives clock-out.
- Four serializer contract-conformance tests against handoff §5.3.
- Legacy seeded rows resolve identically to pre-phase output.
- Full suite: no new failure nodes vs. baseline (**node sets**, not counts; baseline worktree needs
  `app/.env.testing` copied in). Note any baseline failure this phase legitimately fixes.
- `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
