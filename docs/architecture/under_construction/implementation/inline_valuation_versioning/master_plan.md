# Master plan — inline_valuation_versioning

```
state: phase 1 IMPLEMENTED
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
| 1 | M1 compare/inherit/version in `create_task`, identity retired, tests | **CHANGES_REQUESTED → fix r2 PROMPT_READY** | 2026-08-19 | Opus 5 (reviewer r1) | Review r1: **1 should-fix, 5 notes, 0 blocking.** M1 faithful; C1–C8 and C10 all bite under mutation; two independent suite runs 2320/26/1 with byte-identical ID sets. **S1:** C9's standing guard scans `app/beyo_manager` + `app/tests` + `docs/handoff/to_frontend`, but C9 states `app/` and `docs/handoff/` — proved by planting the literal in `app/scripts/` and `docs/handoff/from_frontend/` and watching 51 tests stay green. Fix is ~2 lines in one HC-1 file. **Card 1 → owner authorized**, coordinator applied: `command-task-create` anchor widened 72-580 → 72-594 (AST-verified; graph rev `50b39402…`). Prompt: `prompts/implementer/2026-08-19_phase1_fix_r2.md`. |

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
- **Verification-scope rule (earned here).** A claim that something appears *nowhere* is
  only as good as the directory the search ran in. State the root the search covered, and
  for "appears nowhere" claims run it from the **repository root**, not from whichever
  directory the previous command left you in. HC-1's three-file scope was wrong for exactly
  this reason and cost an implementer round. The enumeration was right; the search wasn't.

## 6. Environment

- Working directory `backend/app/`; infra `make dev-up`; tests
  `PYTHONPATH=. pytest -m 'not e2e'`.
- **Start baseline: 2314 passed / 26 failed / 1 deselected** (2340 selected), head
  `c1d2e3f4a5b6`. Measured independently by the implementer at r1 and re-measured by the
  coordinator; both agree. **Corrected from 2313** — the figure carried over from
  `simple_production_budget_division`'s closeout. The 26 failure IDs are byte-identical to
  that closeout set, so the **+1 passing test is unexplained**: every commit between the
  two measurements was documentation-only, and no test file changed. Recorded as unknown
  rather than rationalised. It is precisely why the rule below exists. **Diff failure IDs, never totals** — one run in three has been
  observed at 25 and the drifting test is not identified.
- The suite leaves ~24 `task_steps` behind per full run (tests outside these pipelines);
  row counts drift, so never read a changed count as evidence of a code change.
- **SUITE INSTABILITY — measured at ±1 in BOTH directions (coordinator, 2026-08-19).**
  On unchanged code the failure count has now been observed at **25, 26 and 27** across
  separate full runs. At r1b consumption one run gave `27 failed / 2319 passed` and the very
  next gave `26 failed / 2320 passed`, with **26 unique IDs byte-identical to baseline and
  no duplicates** — so this is a genuinely flaky test, not a parametrisation artefact, and
  it can add a failure as readily as remove one.
  **Binding consequence: a single run is not evidence.** A run disagreeing with the baseline
  count must be repeated and its **ID set** diffed before any conclusion is drawn; only an ID
  added or removed across repeated runs is a finding. A count alone — higher or lower — is
  noise. The drifting test remains unidentified and is inherited, not introduced here.
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
