# Implementer prompt — System Transition Reasons, Phase 1: foundation

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process this work as: implement → validate → review-log entry → **STOP for independent review**.
   Summary/archive happen ONLY after the reviewer approves.
2. Read, in order:
   - `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
     — seven traced findings and the root-cause mechanism. **Do not re-derive them**; verify and
     extend.
   - `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
     — decisions T1–T8 and the four-phase table.
   - Your plan: `.../system_transition_reasons/PLAN_system_transition_reasons_phase1_foundation_20260731.md`
3. **Clarification-first.** Three clarifications block parts of this phase. Answer the database one
   before running anything; escalate the other two and wait.

## This phase has four steps, in order. Do not reorder them.

**A — inventory. B — vocabulary. C — schema. D — read tolerance.**

Step A is not preamble. Its read-path audit **is** step D's checklist and phase 2's safety net, and
its slug audit can overturn an operator ruling. Do it properly before writing any code.

## Hard constraints

- **Zero behaviour change.** Nothing writes `transition_reason` in this phase. Every existing
  response must stay byte-identical, no existing test may be modified, and no serializer may surface
  the new column. Prove it — do not assert it.
- **The read-path audit is done model-outward** — find inbound references to `PauseReason` and
  `pause_reason_id` — never by guessing at call sites. It must contain the three runtime sites the
  intention names (`_clock_worker_shift.py:200`, `transition_step_state.py:274`,
  `_step_transition_core.py:114`). If it doesn't, your method is wrong, not the intention.
- **`user_declared_state_records` gets no column** (T3). Its `pause_reason_id` is `NOT NULL`, so the
  column would be constant in every row. If you believe T3 is wrong, STOP and escalate.
- **Do not touch `manually_recorded` or the `changed_by_id` provenance heuristic** (T7 — deferred to
  a follow-up). Both look redundant. Removing either is a scope violation.
- **Do not remove the `startswith("par_")` branch** in `domain/users/serializers.py` — that is
  phase 2.
- `get_system_pause_reason_id` stays and keeps its callers. Phase 2 removes them.
- The `IntegrityError` reproduction needs a **disposable** database. Never the shared dev/test one.
  If you cannot provision one, STOP and report — do not substitute.
- Every inventory figure names the database it came from and records its query text. A number
  without its source is not evidence.
- Migration is **additive only**: `upgrade` adds, `downgrade` drops, no data touched either way.

## Two things that can overturn your inputs — reporting either is success

- **The slug-consumer audit can veto operator ruling T6.** The operator confirmed "drop the `slug`
  column" *conditional on this audit finding no out-of-repo consumer*. Search handoff documents,
  export/report code, webhook payload builders, and API response shapes — not just `grep app/`. If
  you find one, STOP and escalate.
- **The `IntegrityError` reproduction can falsify the intention's Finding 2**, which was traced
  statically and never executed. If bootstrapping a second workspace does not raise, say so with the
  same confidence you would report a confirmation.

If your inventory contradicts nothing in the intention, look harder — a static trace by one reader
does not usually survive measurement intact.

## Definition of done

- All 17 acceptance criteria met with evidence.
- Inventory recorded in the master plan under "Phase 1 inventory", with query text.
- Review log entry carrying: the `WORKER_PAUSED` ruling, the label-map-location ruling, the
  column-type reasoning, and the audit list with each entry's test.
- Zero behaviour change proven; query counts unchanged (use a local SQLAlchemy listener — the shared
  `count_queries` fixture is broken).
- Full suite: no new failure nodes vs. the recorded baseline. Compare **node sets**, not counts.
  A baseline git worktree needs `app/.env.testing` copied in — `.gitignore` excludes `app/.env.*`,
  and without it the run reports wildly inflated failures. Verify config parity with a small smoke
  run in both trees first. Run sequentially; the test DB and Redis are shared.
- `ruff check` clean on touched files.
- Then STOP. No summary, no archive, no phase-table flip, no handoff edit.
