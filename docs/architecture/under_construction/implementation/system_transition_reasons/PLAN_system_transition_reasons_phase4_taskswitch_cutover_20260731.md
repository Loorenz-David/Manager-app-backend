# PLAN_system_transition_reasons_phase4_taskswitch_cutover_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase4_taskswitch_cutover_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: both auto-pause-on-conflict sites stop resolving `pause_other_task_priority` from the
  catalog and write `transition_reason = OTHER_TASK_PRIORITY` with `pause_reason_id = NULL`.
- Business/user intent: the second half of the outage. In a workspace lacking the catalog row,
  starting a task while another is active currently fails. After this phase it succeeds.
- Non-goals: derivation (phase 5); historical data (phase 8); the catalog (phase 9).

## Scope

- In scope: `services/commands/task_steps/transition_step_state.py` (~line 274) and
  `services/commands/task_steps/_step_transition_core.py` (~line 114).
- Out of scope: the batch-transition endpoint's contract; anything the two modules share beyond the
  auto-pause record.
- Assumptions: phases 1–3 archived.

## Clarifications required

- [ ] **Q4 (master plan)** — `auto_pause_description = f"started working with {identifier}"` is
      written to `StepStateRecord.description`. Provisional ruling: it stays unchanged, because it
      is a per-instance detail that typing the transition does not make redundant. Confirm or
      escalate; record the ruling.

## Acceptance criteria

1. **Zero-catalog test**: in a workspace with no `pause_reasons` rows, a worker starts a task while
   another is active; the conflicting step auto-pauses; the record carries
   `transition_reason = OTHER_TASK_PRIORITY` with `pause_reason_id = NULL`. Must fail against
   pre-phase code.
2. **Both sites changed.** The two modules are separate code paths reached by different endpoints
   (single transition vs. batch/core). A test must cover **each** — one test hitting one path is the
   likely failure mode of this phase.
3. `get_system_pause_reason_id` now has **zero runtime callers**. Confirm by grep across `app/`
   excluding tests. The function is still deleted in phase 9, not here — but its caller count
   reaching zero is this phase's proof of completion.
4. `description` handling unchanged per the clarification: the auto-pause text is still written and
   still surfaced wherever it is today.
5. `credited_user_id` on the auto-pause record is still set (a post-archive correction to the
   custom_pause_reasons feature set added it; do not regress it).
6. Existing task-switch behaviour otherwise identical: same steps paused, same timestamps, same
   partial-unique-index invariants, same response shapes.
7. Pre-phase rows still resolve via phase 2's fallback; prove with a seeded row.
8. `_step_transition_core.py` has a documented pre-existing `NameError` (missing `select` import) on
   the auto-pause path, recorded in the custom_pause_reasons intention. **Determine whether it is
   still present.** If it is, it is baseline debt (T8) — record it, do not fix it here, and note
   that any test claiming to exercise this path before the fix was not actually reaching it.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: command conventions.
- `backend/architecture/01_architecture.md`: layering.

### File read intent — pattern vs. relational

- Permitted (relational): the two modules being changed; `step_state_record.py` for field names;
  the batch-transition router entry to confirm which module each endpoint reaches.
- Prohibited (pattern): reading other commands for style.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Resolve the clarification; record the ruling.
2. Change both sites to write `transition_reason` directly.
3. Write a zero-catalog test for **each** path (criterion 2).
4. Verify `get_system_pause_reason_id` has no runtime callers left.
5. Check the `NameError` (criterion 8); record findings without fixing.
6. Verify pre-phase rows still resolve.
7. Review log entry. STOP.

## Risks and mitigations

- Risk: only one of the two sites is changed, and the untouched one keeps failing in zero-catalog
  workspaces. This is the single most likely defect in this phase.
  Mitigation: criteria 2 and 3 — a per-path test plus a zero-caller grep.
- Risk: the pre-existing `NameError` means the auto-pause path was never actually exercised, so
  "existing behaviour unchanged" is unverifiable.
  Mitigation: criterion 8 forces the question to be answered explicitly rather than assumed.

## Validation plan

- Two zero-catalog tests (one per path): pass now, fail on pre-phase code.
- `grep -rn "get_system_pause_reason_id" app/beyo_manager` returns definition only.
- Pre-phase seeded row still resolves.
- Full suite: no new failure nodes vs. baseline. `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
