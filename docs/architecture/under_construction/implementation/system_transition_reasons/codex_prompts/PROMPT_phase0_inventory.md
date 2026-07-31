# Implementer prompt — System Transition Reasons, Phase 0: inventory & verification

You are performing a **read-only investigation** in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process this work as: investigate → record findings → review-log entry → STOP for independent
   review. Summary/archive happen ONLY after the reviewer approves.
2. Read, in order:
   - `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
     — the seven traced findings and the root-cause mechanism. Do not re-derive them; verify and
     extend.
   - `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
     — decisions T1–T8 and the phase table.
   - Your plan: `.../system_transition_reasons/PLAN_system_transition_reasons_phase0_inventory_20260731.md`
3. Clarification-first: the plan's "Clarifications required" asks which database you are measuring.
   **Answer it before running anything**, and STOP if you cannot.

## Hard constraints

- **Write no production code.** No schema change, no migration, no fix. If you find a bug, record
  it. Fixing it is a scope violation, however small.
- The only files you may modify are the master plan (adding the "Phase 0 inventory" section) and
  this plan's Review log. `git status` at the end must show nothing else.
- **The `IntegrityError` reproduction requires a DISPOSABLE database.** Do not run it against the
  shared dev/test database. If you cannot provision one, STOP and report — do not substitute.
- Every figure you record must name the database it came from. A number without its source is not
  evidence.
- Record the **query text** alongside every figure, so any of it can be re-derived.

## What matters most, in order

1. **The read-path audit (criterion 3) is this phase's most valuable output.** It becomes phase 2's
   literal checklist, and a path missed here ships broken there. Audit from the model **outward** —
   find inbound references to `PauseReason` and `pause_reason_id` — rather than guessing at call
   sites. Cross-check that your list contains the three runtime call sites the intention already
   names (`_clock_worker_shift.py:200`, `transition_step_state.py:274`,
   `_step_transition_core.py:114`); if it doesn't, your audit method is wrong, not the intention.
2. **The out-of-repo slug audit (criterion 5) can veto an operator ruling.** T6 says drop the `slug`
   column, and the operator made that call *conditional on this audit finding nothing*. Search the
   handoff documents, export/report code, webhook payload builders, and API response shapes. If you
   find a consumer, say so plainly — that is a valuable finding, not a failure.
3. **The `IntegrityError` (criterion 4) must be confirmed by execution, not inspection.** The
   intention's Finding 2 is a static reading. If bootstrapping a second workspace does NOT raise,
   the intention is wrong and must be corrected — report that outcome with the same confidence you
   would report a confirmation.
4. **Label resolution (criterion 6)** — for each of the three system rows, the exact human-visible
   strings historical data currently resolves to. Phase 8 must reproduce these, and master-plan
   success criterion 5 is unverifiable without them.

## Definition of done

- All seven acceptance criteria answered with evidence, recorded in a new "Phase 0 inventory"
  section of the master plan, with query text.
- Review log entry noting anything that contradicts the intention's findings — corrections are
  expected and welcome; a phase that finds nothing surprising has probably not looked hard enough.
- `git status` shows only the master plan and this plan modified.
- Then STOP for independent review. No summary, no archive, no phase-table flip.
