# Master plan — inline_valuation_versioning

```
state: phase 1 PROMPT_READY
date: 2026-08-19
```

## 1. Mission

Make an inline price on task creation re-price an already-priced item — writing a new
valuation version credited to the task creator when the values differ, and doing nothing
when they do not. Retire the rejection that stands in the way.

## 2. Folder layout

Charter tables: `planning/` (intention, owner decisions), `plans/`, `prompts/<role>/`,
`handoffs/<role>/`, `archive/plan_<n>/`. State is positional — closed plans move to
`archive/` **and** their own `state:` line is corrected at closeout (lesson carried from
`simple_production_budget_division`, where a plan sat in `plans/` reading PROMPT_READY
after approval).

## 3. Phase registry & tracker

| Phase | Scope | State | Date | Actor | Note |
|---|---|---|---|---|---|
| 1 | M1 compare/inherit/version in `create_task`, identity retired, tests | **PROMPT_READY** | 2026-08-19 | coordinator | Intention round 1; D17/D18 settled; prompt at `prompts/implementer/2026-08-19_phase1_implement_r1.md` |

## 4. Naming registry

- No new module. The branch lives in
  `services/commands/tasks/create_task.py`, replacing `:324-342`.
- `write_item_valuation_chain_in_session` (`item_economics/_common.py:117`) stays the
  **only** valuation writer (HC-2). No new helper may supersede or insert a valuation.
- If a comparison helper is extracted it is a **pure** function taking the current
  valuation and the effective triple, unit-testable without a session.

## 5. Standing rules

Charter rules 1–11½, plus the rules earned in `simple_production_budget_division` §6 —
in particular:

- **Precedence-disagreement rule** — a fixture pinning a rule must make every level of it
  disagree. Here: C4 exists precisely because C2 and C3 each hold for a second reason.
- **No-weaker-assertions** — exact literals; a row count is asserted as a number.
- **Perimeter-by-path** — declare tool-recorded state by path, generated from `git`,
  never retyped.
- **Deleted-assertion rule** — the rejection test is being *replaced*; the handoff must
  show what now covers the behaviour that test used to pin.

## 6. Environment

- Working directory `backend/app/`; infra `make dev-up`; tests
  `PYTHONPATH=. pytest -m 'not e2e'`.
- **Start baseline: 2313 passed / 26 failed / 1 deselected**, head `c1d2e3f4a5b6`,
  inherited from `simple_production_budget_division` phase 2 closeout. The 26 IDs are the
  documented inherited set. **Diff failure IDs, never totals** — one run in three has been
  observed at 25 and the drifting test is not identified.
- The suite leaves ~24 `task_steps` behind per full run (tests outside these pipelines);
  row counts drift, so never read a changed count as evidence of a code change.
- **This phase removes a test**, so the selected count falls before it rises. State both
  numbers in the handoff.

## 7. Gates

- Mechanism-inventory: **waived** — M1 is one comparison with two inputs, contracted
  inline at inventory depth in intention §3.
- Projection: **waived** — no arithmetic, no rounding, no statistics, no ordering key, no
  new query shape. Charter rule 6 has no trigger here. *If the implementer finds one, that
  is a STOP, not a judgement call.*
- Review: **one light round**, per the MVP calibration rule.
- Checkpoint commits under the owner's standing authorization
  (`CHECKPOINT (not approved):`).
