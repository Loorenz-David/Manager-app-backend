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
| 1 | M1 compare/inherit/version in `create_task`, identity retired, tests | **APPROVED** | 2026-08-19 | Opus 5 (reviewer r3) | Re-review r3: **S1 CLOSED**, verified by two fresh single-root plants the earlier rounds never probed — `app/migrations/` and `docs/handoff/presentation_system/` each turn the guard red alone (P7, P8); `app/.venv/` correctly stays green (P9) and is gitignored, so it cannot hide committed source. **F1 ruled note, not should-fix**: removing the extension filter would make the guard crash on `docs/handoff/to_frontend/archived/beyo_partner_api (1).docx` (`UnicodeDecodeError`) and go red forever for the wrong reason; the narrowing is stated in C9, satisfying r1's own rule. Nothing loosened. All three implementer DECISIONS ruled correct, including declining `ruff format` — reformatting an HC-1 file mid-fix would have destroyed the perimeter diff the round runs on. Suite 2320/26/1, IDs byte-identical. **N2 closed at closeout** by the coordinator: a banner comment now names which C-range belongs to which plan; suite re-verified unchanged. |

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

**Rules earned in this pipeline:**

- **Verification-scope rule.** A claim that something appears *nowhere* is only as good as
  the directory the search ran in. State the root covered, and run "appears nowhere" searches
  from the **repository root**. HC-1's three-file scope was wrong for exactly this reason and
  cost an implementer round.
- **Stated-narrowing rule (earned r1, ruled r3).** A guard may cover less than its criterion
  names — but the narrowing lives **in the criterion**, never silently in the test. A *silent*
  narrowing is a guard claiming a perimeter it does not hold; a *stated* one is a scope
  decision on the record, which is what a criterion is for.
- **Widen the allowlist, never remove the filter (r3 refinement).** If C9-style coverage is
  ever extended, add extensions (`.yml`, `.json`, `.sh`, `.txt`). Removing the filter is not
  the stricter option — it is the broken one: the guard's own root contains a binary `.docx`
  that raises `UnicodeDecodeError`, which would pin the criterion red forever for a reason
  unrelated to what it guards. **A tripwire that fires on the wrong thing trains people to
  ignore it.**
- **Prove each root alone.** A combined plant proves *something* caught it; single-root
  plants prove *each root* is covered. Three rounds each extended the plant set rather than
  repeating it (coordinator: `app/scripts/`, `docs/handoff/from_frontend/`; reviewer r3:
  `app/migrations/`, `docs/handoff/presentation_system/`, plus a green control on
  `app/.venv/`), and only that layering established all four newly-covered roots.
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
