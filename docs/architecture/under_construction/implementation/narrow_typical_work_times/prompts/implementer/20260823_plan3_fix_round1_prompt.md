---
plan: plan_3
role: implementer
round: 2 (fix round 1)
date: 2026-08-23
---

# Session prompt — implementation-executor, phase 3 fix round 1

## Read this first: your implementation was correct

The production diff is **exactly** what §6A prescribed and **nothing in it changes**. The
coordinator verified at source: `None if item is None else derive_spec_from_primary_item(item)`
at both load sites, `_load_task_and_item` still a 2-tuple, required keyword-only carrier with
no default, `item_id=evaluation.item_id` preserved on the evaluated path, `typical_filters.py`
untouched, perimeter clean, and the L4 arithmetic checking out (2661 + 13 new cases = 2674,
21-ID set unchanged in both directions).

**This round changes no production code and no assertions.** It corrects the **mutation
evidence** — and two of the three corrections are to **§6A, a coordinator fold**, not to
anything you did. You inherited a mutation that could not run.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Never push.** **Never `git add -A`** — explicit paths only.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below `<project>/`).

Doctrine first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

Then **`plans/plan_3.md` §6B**, which is the whole of this round's scope. **§6B wins over
§6A wherever they differ.**

## Gate check (stop-and-report if any fails)

1. `<project>/plans/plan_3.md` header reads `state: CHANGES_REQUESTED` and the file
   contains a section titled **`§6B. Coordinator consumption fold`**.
2. Your checkpoint `186027a` is an **ancestor of `HEAD`**
   (`git merge-base --is-ancestor 186027a HEAD`). **Do not pin `HEAD` to a SHA** — a
   coordinator fold commit sits on top of your work by design.
3. `git status` shows no modified tracked files under `app/`. Untracked
   `?? .archgraph/contexts/` is expected. **The owner may have `.archgraph/agent-operating-policy.md`
   modified — that is the owner's live edit; leave it alone and do not report it as a finding.**

## Scope — three ledger rows, no production change

**You may not modify** any file under `app/beyo_manager/`, nor any assertion in
`test_budget_status_filter_spec.py`. If you believe a correction requires either, **stop and
report** — that is a finding worth more than a guess.

### 1. C4 — replace the mutation, then withdraw the old row

§6A prescribed *"re-load `Item` by `evaluation.item_id` and derive from that ORM instance"*.
**It cannot run.** `_ScalarSession` is a **content-blind iterator** — `scalar()` returns the
next list value regardless of the query — so its length encodes the *expected query count*,
and the extra reload exhausts it.

**Run the old mutation once to confirm the withdrawal is honest**, then run the replacement.

**Replacement mutation** (query count unchanged, source changed): in
`get_task_budget_status.py`, move the derivation **below** the evaluation load and derive
from `evaluation` itself, i.e. `typical_filter_spec = None if item is None else
derive_spec_from_primary_item(evaluation)`.

**Record what C4 actually proves.** Against a content-blind double, C4 demonstrates *"the
carrier stopped coming from the loaded PRIMARY item"*. It **cannot** demonstrate *"it came
from the evaluated item specifically"*, because no mutation can make the double return a
different `Item`. **State the narrower claim.** Do not restate the withdrawn
`cat_chair` → `cat_table` both-sides.

### 2. C1 — replace the mutation

"Move the defaulted field before non-default `result`" is a `TypeError` at **class
creation**: a collection error naming **no failing test id**, which the evidence budget
requires. It is also unfalsifiable — `result` is the last non-default field, so the language
forbids the position, not the test.

**Replacement mutation:** swap two **existing** field declarations (`evaluation_id` /
`item_id`) in `TaskBudgetStatus`. Legal Python; every keyword construction keeps working;
only the ordering assertion should move.

### 3. C-N1(a) no-`WHERE` row — name the test id

"Legal shapes failed at their legal flush" is a description. **State the failing test id.**

## Expected observables — these are CHECKSUMS, not values to copy

The coordinator measured all three on your tree at `186027a`. **Derive each independently by
running it, then compare.** If your run disagrees with the checksum, **stop and report** —
a disagreement means something moved, and the owner needs to know. Do not silently prefer
either number.

| what you run | expected (checksum) |
|---|---|
| C4 **old** mutation (reload `Item`) | **4 failed / 9 passed**; `test_C4_manager_...` fails with `RuntimeError: coroutine raised StopIteration`, **not** an assertion; C5-a, C5-b, C5-e red as collateral |
| C4 **replacement** (derive from `evaluation`) | **2 failed / 11 passed**; `test_C4_manager_uses_loaded_primary_item_not_evaluation_item` and `test_C5_...[C5-e-manager-categorized-primary]`, **both on their own assertion** |
| C1 **replacement** (swap `evaluation_id`/`item_id`) | **1 failed / 12 passed**; `test_C1_task_budget_status_appends_defaulted_spec_after_result`, message containing `At index 11 diff: 'item_id' != 'evaluation_id'` |

Command used for all three (serial, deterministic ordering):
`BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py -n 0 -p no:randomly`

**Revert each mutation immediately after observing it**, and confirm `git diff` is empty
under `app/beyo_manager/` before you commit.

## Already settled — do not re-open

The coordinator measured these; they are **not** findings and need no work:

- **C3 is sound.** Under the shared-`payload` mutation both key-set tests fail on the
  frozenset comparison (`Extra items in the left set: 'typical_filter_spec'`); the
  `TypeError: Object of type TypicalFilterSpec is not JSON serializable` belongs to the
  **golden** row only. Only your prose was ambiguous — tighten it, run nothing.
- **`asyncio_mode = auto`** (`app/pytest.ini:7`), so the `@pytest.mark.integration` tests
  carrying no `@pytest.mark.asyncio` do run. Cosmetic inconsistency, not a silent skip.
- **C-N1(a) avoided §6A(ii)'s trap** — five distinct items, so the `IntegrityError` comes
  from `uix_task_items_primary_active`. Confirmed.
- **C5-b is inert against a wrong-source derivation** (it passes under C4's replacement,
  because the wrong source yields `TypicalFilterSpec()` — exactly what it asserts). It stays
  armed for its **own** hazard. **Record this in the ledger as a known limit; change nothing.**
- **`C5-e-manager-categorized-primary`**, which you added beyond the plan, is the **only**
  C5 row that catches a wrong-source derivation. **Keep it**, and say so.

## Evidence budget

- The three mutations run at **L1** — the whole contract file, **never `-k`**.
- **No L4 is owed this round.** Production code does not change, so the approved stamp at
  `186027a` (2674 / 21 / 1) still describes the tree. **Re-running the suite would be
  over-evidence and is itself a finding.** If you change any production file, that judgment
  reverses and you owe a fresh stamp — which is a reason to stop and report instead.

## Closing protocol

1. `git diff` empty under `app/`; the only changes are `plans/plan_3.md` §8 and this round's
   handoff.
2. Append a **round-2 entry** to `plans/plan_3.md` §8 — **append-only, never rewrite the
   round-1 entry.** Restate only the three corrected rows and mark the C4 row **withdrawn
   and replaced**, with the reason.
3. Update `<project>/master_plan.md` §4 row 3 to `IMPLEMENTED`.
4. **Checkpoint commit**, subject prefixed `CHECKPOINT (not approved): `, explicit paths.
   Never squash, never push.
5. Handoff at
   `<project>/handoffs/implementer/20260823_plan3_fix_round1_handoff.md`, frontmatter
   `plan: plan_3`, `role: implementer`, `round: 2`, `date`, `actor`. Body: the three
   corrected rows with **both sides and the failing test id**; each checksum comparison
   stated as **matched** or **disagreed**; confirmation that no production file changed and
   no L4 was run; the write perimeter from `git status`; the checkpoint SHA.
6. Final chat message is the charter's **owner layer**: what you did → what it means → what
   happens next → what needs the owner; one pointer line naming the handoff.
