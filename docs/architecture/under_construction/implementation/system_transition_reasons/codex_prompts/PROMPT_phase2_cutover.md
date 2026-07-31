# Implementer prompt — System Transition Reasons, Phase 2: cutover

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

**This is the phase that ends the outage.** In 3131 of 3132 workspaces, clocking out with an open
working step fails, and starting a task while another is active fails, because both resolve a
catalog row that does not exist there. After this phase both succeed — and **no backfill is needed
for that to be true**, because new rows do not require the row that is missing.

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process as: implement → validate → review-log entry → **STOP for independent review**.
   Summary/archive only after the reviewer approves.
2. Read, in order:
   - `docs/domains/worker_shifts/` — **all three files, before any code.** This is the living map of
     the domain you are changing. It will tell you things the code does not: that
     `user_shift_state_records` is derived and rebuilt, that state is computed twice by two
     different algorithms, that all three clock sources share one core.
   - `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md` — decisions
     T1–T8, and the **"Phase 1 inventory"** section, whose read-path audit (R1–R24) is your
     checklist.
   - Your plan: `.../system_transition_reasons/PLAN_system_transition_reasons_phase2_cutover_20260731.md`
   - The intention, for the reasoning: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
3. **Clarification-first.** Three clarifications are open; two are operator decisions. Escalate and
   wait before writing code they affect.

## Hard constraints

- **Change `clock_out_shift_for_user` itself, not a wrapper.** The Connecteam handler and the
  overnight safeguard call it directly, and inherit this change by design. A fix applied one layer
  up will silently not reach them — that exact mistake has already shipped once in this codebase.
  Criteria 5 tests both paths.
- **Both task-switch sites.** `transition_step_state.py` and `_step_transition_core.py` are separate
  paths reached by different endpoints. One test per path. Changing one and not the other is the
  likeliest defect in this phase.
- **Do not touch `manually_recorded` or the `changed_by_id` provenance heuristic** (T7 — deferred).
  Both will look redundant once transitions are typed. Removing either is a scope violation.
- **Do not edit any `docs/handoff/to_frontend/` file.** Operator-owned. If a contract change is
  needed, write the proposal in the Review log and STOP.
- **The archived declared_worker_states master plan must not be edited.** D3/D5 amendments go in
  *this* feature set's master plan.
- `get_system_pause_reason_id` stays defined; phase 4 deletes it. Zero **runtime callers** is this
  phase's proof of completion.

## The failure shape to avoid — read this before touching a conditional

Phase 1's one blocking finding was a guard that looked incidental and was load-bearing:
`details[0]["pause_reason"]` was not a null check, it was a **workspace-resolution check**. Dropping
it leaked another workspace's id into a workspace-scoped response, and an in-code comment asserting
the two reads were "identical" is what let it through.

**You are rewriting the modules that guard lived in.** For every conditional you touch, ask what it
is actually testing rather than what it appears to test. Watch for a `None` check standing in for a
resolution check, and for a fallback chain whose first element can now be non-null where it
previously could not.

Follow phase 1's fix pattern: make the guard **structural**. Pass the resolved set as a required
argument so a caller cannot obtain a key without proving resolution, rather than relying on a
side-effect being falsy. And do not write a comment asserting two expressions are equivalent —
either prove it with a test or do not claim it.

## Two invariants that cost four fix cycles last time

- **The rebuild must stay idempotent.** Run it twice over the same source data; the derived rows
  must be identical. This is the invariant to protect above all others in the rebuild path.
- **Declarations must survive the rebuild.** They are a *source* table precisely so the clock-out
  rebuild cannot erase them. Declare, clock out, assert the declaration is in the derived timeline.

Also: the rebuild must not launder `changed_by_id`. It did once, and the healing job then reopened
the laundered row.

## Domain documentation is a deliverable

`docs/domains/worker_shifts/` must be updated **in this change** (acceptance criterion 20). This
phase changes what a transition records, what the rebuild carries, and possibly the serializer's
output — all documented behaviour.

Specifically: the README's `UserShiftStateRecord.reason` entry carries a warning that the field is
overloaded and readers distinguish meanings by inspecting the id prefix. **If you remove that prefix
check, the warning becomes false.**

Domain docs describe what is true **now**. No references to this plan, to phases, to migrations, or
to previous behaviour. If you write "previously" or "as of phase 2", you are putting history in a
living document. Nothing about phases 3–4 belongs there either — they describe a system that does
not exist yet.

## Definition of done

- All 20 acceptance criteria met with evidence.
- The two zero-catalog tests (clock-out and task switch) **fail against pre-phase code** — verify
  that, do not assume it.
- One test per task-switch path; Connecteam and the overnight safeguard tested explicitly.
- Rebuild-twice idempotence and declaration-survival asserted.
- `grep -rn "get_system_pause_reason_id" app/beyo_manager` returns the definition only.
- Four serializer contract-conformance cases asserted against handoff §5.3.
- `docs/domains/worker_shifts/` updated and consistent with what shipped.
- Full suite: no new failure nodes vs. baseline. Compare **node sets**, not counts, and **run-2 vs
  run-2** — the test DB and Redis are shared and not reset, so three nodes fail on any second
  consecutive run including in an unmodified tree. Copy `app/.env*` into any baseline worktree;
  without `.env` the app cannot start. Sanity-check against the figures recorded in phase 1's Review
  log, not against older canonical numbers.
- `ruff check` clean on touched files.
- Review log entry with the three clarification rulings, the D3/D5 amendments, and the
  guard-shape sweep. Then STOP — no summary, no archive, no phase-table flip, no handoff edit.
