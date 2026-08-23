---
plan: plan_3
role: implementer
round: 1
date: 2026-08-23
---

# Session prompt — implementation-executor, phase 3 of `narrow_typical_work_times`

## Role and workspace

You are the **implementer** for phase 3: `TaskBudgetStatus` carries the derived
`TypicalFilterSpec`, **additively**, across every construction surface including the
WORKER/SELLER face. **No payload changes anywhere.** No serializer publishes the field, no
golden regenerates, and no consumer reads it yet — plan 4 is the first reader.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Never push.** **Never `git add -A`** — explicit paths only.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below `<project>/`).

Doctrine first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## Gate check (stop-and-report if any fails)

1. `<project>/master_plan.md` §4: phases 1 and 2 **`APPROVED`**, phase 3 **`PROMPT_READY`**.
2. `<project>/plans/plan_3.md` header reads `state: PROMPT_READY` and its §8 Review log
   carries the 2026-08-23 projection fold entry.
3. The phase-2 gate commit `a2712d3` is an **ancestor of `HEAD`**
   (`git merge-base --is-ancestor a2712d3 HEAD`). **Do not pin `HEAD` to a SHA.**
4. `git status` clean (only `?? .archgraph/contexts/` expected).

## ⚠ TASK 0 — TESTS FIRST

**Before you write a line of production code**, transcribe every criterion row and prose
clause of `plans/plan_3.md` §6 — **as corrected by §6A** — into
`test_budget_status_filter_spec.py` as executable cases. Run them. They must be **red for
the right reason** (a missing field, a wrong value — not an import error). Only then
implement to green, then run the named mutations.

**A row you cannot transcribe is a PLAN DEFECT — stop and report it.** The projection
already removed fifteen; if a sixteenth survives, it is worth more as a report than a guess.

**§6A wins over §5 and §6 wherever they differ.** Read §6 for intent, then §6A for what
binds. **Every criterion carries a correction** — there is no "transcribable as written"
list this time.

## The four traps the projection measured — know them before you start

1. **Passing the item is necessary and NOT sufficient (§6A T-L1).**
   `derive_spec_from_primary_item(None)` returns **`TypicalFilterSpec()`, not `None`**
   (`typical_filters.py:71-75`). That collapses exactly the two cases C5 exists to separate,
   and the plan, the intention and the shipped helper all *appear* to agree. The value you
   carry is **`None if item is None else derive_spec_from_primary_item(item)`**, computed at
   the load site. **Do not "fix" `derive_spec_from_primary_item`** — it is plan 1's shipped
   contract and changing it is forbidden by §6.1's fold rule and would be an automatic
   finding.
2. **"The worker serializer" does not exist (§6A C3).** There is exactly one —
   `serialize_task_budget_status(status, *, include_monetary)` — and the worker face is that
   same function called with `include_monetary=False`. C2's and C3's mutations differ by
   **placement inside it**: the shared `payload` dict reaches both faces (C3's mutation),
   inside `if include_monetary:` reaches the manager only (C2's).
3. **A fixture can satisfy two independent sufficient causes (§6A C-N1(a)(ii)).**
   `task_items` carries a **second** partial unique index, `uix_task_items_active` on
   `(workspace_id, task_id, item_id)`. If your second active PRIMARY reuses the first's
   `item_id`, the `IntegrityError` comes from the **wrong index** and dropping
   `uix_task_items_primary_active` leaves the row **green**. **The second active primary
   must name a different item**, and so must both legal shapes.
4. **A duck-typed helper turns a "wrong source" mutation into a "no source" mutation
   (§6A C4).** Deriving from `evaluation.item_id` passes a `str`, which has no
   `item_category_id`, so you get the *empty* spec, not the *wrong* one. C4's mutation must
   re-load an `Item` and derive from that ORM instance.

## Decided for you (do not re-litigate)

- **`_load_task_and_item` keeps its 2-tuple return** (§6A T-L8). Compute the spec in
  `get_task_budget_status` and `get_task_budget_status_worker`, immediately after that call.
  The 3-tuple branch breaks `get_task_price_scenario.py:196` — **out of perimeter** — and
  `test_price_scenario_query.py`'s `fake_task_and_item`.
- **The helper signature is fixed** (§6A T-L2):
  `_empty_status(status, *, binding, item_id, typical_filter_spec: TypicalFilterSpec | None)`
  and the same **required keyword-only** parameter on `_build_evaluated_status`. **No
  default** — the default lives on the dataclass (C1) and nowhere else.
- **All exact literals are supplied** in §6A: C1's fifteen-name list (index base is
  **0-based**), C2(b)'s 14-key frozenset, C3(b)'s 9-key frozenset. Transcribe them; do not
  re-derive them from a golden and do not "improve" them into subset checks.
- **C3(b) asserts the service-level call** `serialize_task_budget_status(worker_status,
  include_monetary=False)` — the exact call the route makes — not the route.

## Perimeter

**Modified:** `get_task_budget_status.py`, `get_task_budget_status_worker.py`.
**New:** `app/tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py`.
**Plus** the plan/tracker updates and this round's handoff.

**Anything else is a finding** — in particular any serializer, any golden,
`get_task_production_time.py`, `get_task_price_scenario.py`,
`get_task_budget_allocations.py`, and `typical_filters.py`.

**C-N1's two rows** (the one-active-primary rule, owner ruling **D27**) live in this phase
and may need a second test file or fixtures for `task_items` / `add_item_to_task`; declare
whatever you add in the handoff perimeter.

## Architecture graph — new interim policy, read this

**Owner policy, 2026-08-23 (master plan §8):** graph nodes carry **meaning, not
coordinates**. When you record this phase's delta, a source link names the **file** whose
meaning the node describes; the node and its relationships explain what that substance means
for the application and what it affects. **Do not emit `startLine`/`endLine`.** Existing
span-bearing links are legacy and are repaired only under scoped owner authorization —
never opportunistically, and never by you.

Orient read-only at start (`archgraph_status` + `.archgraph/contexts/current-task.md`,
untracked, never rebuilt or committed); record the delta at the end as **one batched**
`archgraph_apply_changes`. **Never promote, reject or edit a review item** — one entry is
already pending the owner's adjudication and is not yours to touch.

## Evidence budget

- Every named mutation runs at **L1 hypothesis scope** — whole files, **never `-k`**. C2 and
  C6 name cross-file bite sets and run at L2
  (`tests/integration/services/queries/item_economics/`); C6 additionally names
  `tests/unit/routers/api_v1/test_item_economics_router.py`, which sits **outside** that root.
- **The mutation count is the plan's, not one per criterion.** §6A writes out C5's four
  call-site mutations and C-N1(a)'s two. A ledger with one row per criterion under-reports —
  master plan §9 makes it checkable.
- **State, per mutation, which test id failed** — the id, not "the file reddened".
- **Exactly one L4 stamp** closes the cycle, on the tree you hand over, with the failing-ID
  delta against the **21-ID set in both directions**. Check Redis first (`redis-cli ping`);
  use the documented default `BEYO_TEST_SLOT=main`. Phase 2's approved suite was
  **2661 passed / 21 failed / 1 skipped**; that is your starting point.
- Run the command the environment section names **verbatim** — a stamp taken with extra
  flags is not the stamp (measured: `-p no:logging` removes the `caplog` fixture and
  manufactures 35 errors).

## Environment (master plan §10 is authoritative)

From `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`; xdist 6 workers is in `addopts`,
`-n 0` is the serial comparator. **Redis must be reachable.** Databases: server
`localhost:5433`, per-process disposable templates — **never run two suite sessions
concurrently in this checkout.**

## Closing protocol

1. Tests green at the perimeter; every named mutation run with both sides and its failing
   test id.
2. Update `<project>/master_plan.md` §4 row 3 and `plans/plan_3.md` (`state:` + §8).
3. **Checkpoint commit**, subject prefixed `CHECKPOINT (not approved): `, explicit paths.
   Never squash, never push.
4. Handoff at
   `<project>/handoffs/implementer/20260823_plan3_implementation_handoff.md`, frontmatter
   `plan: plan_3`, `role: implementer`, `round: 1`, `date`, `actor`. Body: owner-readable
   opening (3–5 sentences, plain words); **a task-0 section stating what you transcribed,
   what was red before implementation, and any row you could not transcribe**; the criteria
   ledger with per-mutation both-sides and failing test id; the L4 stamp; the full write
   perimeter from `git status`; the checkpoint SHA.
5. Final chat message is the charter's **owner layer**: what you did → what it means → what
   happens next → what needs the owner; one pointer line naming the handoff.
