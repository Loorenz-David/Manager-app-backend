---
plan: plan_3
role: implementer
round: 2 (fix round 1, redispatch)
date: 2026-08-23
supersedes: 20260823_plan3_fix_round1_prompt.md
---

# Session prompt — phase 3 fix round 1, **redispatch**

## You were right to stop, and the gate you stopped at was wrong

The previous dispatch asked you to confirm the **withdrawn** C4 mutation against a checksum
of 4 failed / 9 passed. You measured **3 failed / 10 passed** and stopped. **That was the
correct call, and the checksum should never have been there.**

The coordinator re-ran the original mutant on this same tree and reproduced **4 failed /
9 passed** — so **the tree has not moved.** What differs is *where the extra query is
placed*, which that mutation's prose never specified. Three faithful readings, three
observables, all measured on an identical tree:

| placement | observable |
|---|---|
| unconditional, before `binding` | 4 failed / 9 passed |
| guarded on `evaluation is not None` | 1 failed / 12 passed |
| yours | 3 failed / 10 passed |

That instability **is** the reason the mutation was withdrawn. Demanding a canonical number
from it was incoherent. **The confirmation run is removed from this round** — a withdrawal is
argued from the fixture's structure, not re-measured.

**Nothing about your implementation is in question.** No production code changes this round.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Never push.** **Never `git add -A`** — explicit paths only.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below `<project>/`).

Doctrine first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

Then **`plans/plan_3.md` §6B and §6B.1**, which are this round's whole scope.

## Gate check (stop-and-report if any fails)

1. `plans/plan_3.md` reads `state: CHANGES_REQUESTED` and contains **`§6B.1`**.
2. `git merge-base --is-ancestor 186027a HEAD` succeeds. **Do not pin `HEAD` to a SHA.**
3. No modified tracked file under `app/`. Untracked `?? .archgraph/contexts/` is expected,
   and the owner may have `.archgraph/agent-operating-policy.md` modified — **that is the
   owner's live edit; leave it alone and do not report it.**

## Scope — three ledger rows, no production change

**You may not modify** any file under `app/beyo_manager/`, nor any assertion in
`test_budget_status_filter_spec.py`. If a correction seems to require either, **stop and
report** — that is worth more than a guess.

Run each mutation, observe, **revert immediately**, and confirm `git diff` is empty under
`app/beyo_manager/` before committing.

### 1. C4 — apply exactly this edit

In `get_task_budget_status.py`, **delete** this line from `get_task_budget_status`:

```python
    typical_filter_spec = None if item is None else derive_spec_from_primary_item(item)
```

and **insert** this line immediately **above** the `binding = ...` line:

```python
    typical_filter_spec = None if item is None else derive_spec_from_primary_item(evaluation)
```

Net effect: the source changes, **the query count does not** — which is what makes the
observable stable.

**Expected: `2 failed / 11 passed`** — `test_C4_manager_uses_loaded_primary_item_not_evaluation_item`
and `test_C5_...[C5-e-manager-categorized-primary]`, **both failing on their own assertion.**

**Record the narrower claim.** Against a content-blind double, C4 demonstrates *"the carrier
stopped coming from the loaded PRIMARY item"*. It **cannot** demonstrate *"it came from the
evaluated item specifically"* — no mutation can make the double return a different `Item`.
Do **not** restate the withdrawn `cat_chair` → `cat_table` both-sides.

### 2. C1 — apply exactly this edit

In `TaskBudgetStatus`, swap the two existing declarations so they read:

```python
    item_id: str | None
    evaluation_id: str | None
    result: ItemCostResult | None
```

Legal Python; every keyword construction keeps working; only the ordering assertion moves.

**Expected: `1 failed / 12 passed`** — `test_C1_task_budget_status_appends_defaulted_spec_after_result`,
with a message containing `At index 11 diff: 'item_id' != 'evaluation_id'`.

**Why this replaces the old C1 mutation:** moving a defaulted field before a non-default one
is a `TypeError` at **class creation** — a collection error naming **no failing test id** —
and unfalsifiable besides, since `result` is the last non-default field, so the grammar
forbids the position rather than the test.

### 3. C-N1(a) no-`WHERE` row — name the test id

"Legal shapes failed at their legal flush" is a description, not an id. **State the id.**
No re-run is required if you already have it; re-run only if you do not.

## Command, and what to do on a disagreement

```
BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest \
  tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py \
  -n 0 -p no:randomly
```

The two expected values above **are** checksummable, because the mutations are now pinned to
exact code rather than described in prose. Both were re-verified on this tree after the
disagreement. **If either disagrees, stop and report** — that one would be real.

## Already settled — do not re-open

- **C3 is sound.** Under the shared-`payload` mutation both key-set tests fail on the
  frozenset comparison (`Extra items in the left set: 'typical_filter_spec'`); the JSON
  `TypeError` belongs to the **golden** row only. Tighten the prose; run nothing.
- **`asyncio_mode = auto`** (`app/pytest.ini:7`) — the unmarked integration tests do run.
- **C-N1(a) avoided §6A(ii)'s trap** — five distinct items, so the `IntegrityError` comes
  from `uix_task_items_primary_active`.
- **C5-b is inert against a wrong-source derivation** (it passes under C4's replacement,
  because the wrong source yields `TypicalFilterSpec()` — exactly what it asserts). It stays
  armed for its **own** hazard. **Record as a known limit; change nothing.**
- **`C5-e-manager-categorized-primary`**, added beyond the plan, is the **only** C5 row that
  catches a wrong-source derivation. **Keep it, and say so.**

## Evidence budget

- Both mutations run at **L1** — the whole contract file, **never `-k`**.
- **No L4 is owed.** Production code does not change, so the stamp at `186027a`
  (2674 / 21 / 1) still describes the tree. **Re-running the suite is over-evidence and is
  itself a finding.** If you change any production file, that reverses and you owe a fresh
  stamp — which is a reason to stop and report instead.

## Closing protocol

1. `git diff` empty under `app/`; the only changes are `plans/plan_3.md` §8 and this round's
   handoff.
2. Append a **round-2 entry** to `plans/plan_3.md` §8 — **append-only, never rewrite the
   round-1 entry.** Restate only the three corrected rows; mark C4 **withdrawn and replaced**
   with the reason.
3. Update `<project>/master_plan.md` §4 row 3 to `IMPLEMENTED`.
4. **Checkpoint commit**, subject prefixed `CHECKPOINT (not approved): `, explicit paths.
   Never squash, never push.
5. Handoff at
   `<project>/handoffs/implementer/20260823_plan3_fix_round1_handoff.md`, frontmatter
   `plan: plan_3`, `role: implementer`, `round: 2`, `date`, `actor`. Body: the three
   corrected rows with **both sides and the failing test id**; each expected value stated as
   **matched** or **disagreed**; confirmation that no production file changed and no L4 ran;
   the write perimeter from `git status`; the checkpoint SHA.
6. Final chat message is the charter's **owner layer**: what you did → what it means → what
   happens next → what needs the owner; one pointer line naming the handoff.
