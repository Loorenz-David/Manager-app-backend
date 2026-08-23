---
plan: plan_3
role: reviewer
round: 0
date: 2026-08-23
model: Opus 5
scope: PROJECTION (plan-projection doctrine)
---

# Session prompt — plan-projection, phase 3 of `narrow_typical_work_times`

## Role and workspace

You are the **projection** for phase 3. You do not implement. You read the plan as the
implementer will have to, and you report **every place it cannot be executed as written** —
a criterion that cannot be turned into a test, a fixture that cannot be built, a mutation
that would not catch what it claims, a claim about the code that is no longer true.

**Phases 1 and 2 are APPROVED.** Phase 3 is `NOT_STARTED` and its projection gate is
**mandatory**: it adds a field to a **shipped cross-pipeline dataclass** across **five
construction surfaces**, which is where this lineage has historically paid.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Never push.** **Never `git add -A`.**
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below `<project>/`). **Do not read `<project>/prompts/coordinator/`.**

Doctrine first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

## Gate check (stop-and-report if any fails)

1. `<project>/master_plan.md` §4: phases 1 and 2 **`APPROVED`**, phase 3 **`NOT_STARTED`**.
2. The phase-2 gate commit `a2712d3` is an **ancestor of `HEAD`**
   (`git merge-base --is-ancestor a2712d3 HEAD`). **Do not pin `HEAD` to a SHA.**
3. `git status` clean (only `?? .archgraph/contexts/` expected).

## Read first

- `<project>/plans/plan_3.md` in full.
- `<project>/master_plan.md` §§3, 4, **6.2**, 7, **9** (the standing rules — this project has
  earned ~20 and several were earned *by* the failure modes you are looking for), 10.
- Intention **header** (the section-letter precedence rule), then §2.2 F-A
  (**stale — see §2B S-1/S-2/S-3**), §2B S-1/S-2/S-3, §3.2, §6.2 row 1, **§6A** in full, §7.
- `<project>/planning/owner_decisions.md` — D9, D11, **D27**.
- `<project>/archive/plan_2/` — phase 2's projection, review and re-review handoffs. **Read
  at least the re-review**: four of its findings are about *this* class of defect.
- Code, at source: `get_task_budget_status.py` (whole file), `get_task_budget_status_worker.py`
  (whole file), `routers/api_v1/item_economics.py`, `domain/item_economics/serializers.py`,
  and `domain/item_economics/typical_filters.py` (what plan 1 actually shipped).

## What this phase is

`TaskBudgetStatus` gains `typical_filter_spec`, **additively**, across all five construction
surfaces including the WORKER/SELLER face. **No payload changes anywhere**; no golden
regenerates; no consumer reads it yet (plan 4 is the first reader).

## ⚠ Re-verify every claim the plan makes about the code

The plan's line numbers and counts were written **2026-08-22**, and its own §5 task 5 warns
that this lineage has watched line numbers drift twice. Phase 2 then lost an owner card to
exactly this: master plan §8 asserted "0 pending / 0 stale" for a queue that had filled up
underneath it.

**Treat every number, name and count in plan 3 as a claim with a shelf life**, and re-derive
it at source: the field list and its order, the construction-surface count, the
`_empty_status` call-site count, §6.2's table size, the helper and symbol names plan 1
shipped. **Report each as confirmed or drifted.** A confirmed claim is a result — say so;
do not report only the drift.

## Depth areas — where this plan is most likely to be unexecutable

Ranked. Mechanisms, **not** predicted conclusions — confirm or refute each.

1. **What `_empty_status` is actually given, versus what C5 needs it to know.** C5 demands
   that "no primary item" and "a primary item whose category is NULL" produce **different**
   values (`None` vs `TypicalFilterSpec()`) at all four call sites. Read what those call
   sites pass today and ask whether the helper can tell those two cases apart. If it cannot,
   say what would have to change and whether §4/§5 declares it.
2. **The exact key sets C2(b) and C3(b) demand.** Both require an **exact frozenset literal,
   explicitly not a subset check** — and neither supplies the literal. A criterion that
   specifies rigour without supplying the value is the shape that cost phase 1 three
   findings (master plan §9's closing-sentence rule). Decide whether these are transcribable.
3. **Mutation prose that has never been run.** Phase 2's re-review found a mutation that had
   survived a projection, three implementation rounds and two reviews **asserting a bite set
   that was never true**, because nobody ran it. Master plan §9: *a mutation that has never
   been run is not evidence of anything, including of what it would catch.* Check each of
   plan 3's mutations against the code: **would it redden the row the plan says it reddens,
   and does it catch the defect the criterion names?** Two different questions — ask both.
4. **Blanket claims with one probe.** C5 says the other three call sites "each have their own
   call-site mutation of the same shape" without writing them; C2 says row (c) bites on a
   different, unnamed-in-the-ledger mutation. Master plan §9: *"one per sub-check" is a
   count, and the ledger is checkable against it.*
5. **Can C4's `mismatched` fixture be built?** It needs a committed evaluation bound to item
   X, an active PRIMARY `TaskItem` at item Y, and `item_binding == "mismatched"` — three
   facts made to coexist. Name the seeding path, or say that the plan owes one.
6. **C-N1(a)'s aborted transaction — this one is already owed to you** (phase-2 re-review
   N-c, owner ruling D27). Row (a) asserts an `IntegrityError` **and** two clean inserts in
   the same criterion, and after an `IntegrityError` PostgreSQL aborts the transaction until
   a rollback or savepoint. **Settle on paper**: do the legal shapes insert before the
   violating one, or inside a nested savepoint? Get it wrong and the row fails for the wrong
   reason or swallows its own evidence.
7. **The worker face.** §5 task 6 says §6.2's table is **seven** rows, not the "all four" its
   header claims. Verify that count, and check that C3 covers the face the way the phase
   needs — its own source comment ("must not inherit a future manager change") is the
   standing instruction and this *is* a manager change.
8. **Fixture arithmetic** (the class that cost this project six rounds): for every criterion
   asserting a value, does the fixture contain a row the named mutation actually **moves**?

## Standing rules that are binding, not advisory

Master plan §9 is long because it was paid for. The ones most likely to bite here:

- A criterion's **closing prose sentence is a criterion**, not commentary.
- **"Identical object" and "unchanged payload" criteria must name the compared fields.**
- **An equality between two computed values is weaker than an exact literal** — prefer the
  literal, and say what makes the equality able to fail.
- **Absence criteria ship as committed tests**, never as a reviewer's grep.
- **Route an amendment to its consumers**, and name them as files.

## Output

Handoff at `<project>/handoffs/reviewer/20260823_plan3_projection_handoff.md`, frontmatter
`plan: plan_3`, `role: reviewer`, `round: 0`, `date`, `actor`, `verdict`.

- **Verdict**: `READY` or `AMENDMENTS_REQUIRED`.
- **A numbered ledger**, each row ranked **blocking / non-blocking**, naming the criterion or
  task it attaches to, what specifically cannot be executed, and your proposed correction.
  Blocking means *an implementer would have to stop and ask*.
- **Reality checks**: every plan claim you re-derived at source, **confirmed or drifted**.
- **Owner cards** for anything only the owner can decide — a product-semantic question, a
  scope trade. Zero is a fine answer; do not manufacture one. Note that two architecture-graph
  items are already open with the owner and need no card from you.
- **Say which depth areas you refuted.** A refuted hypothesis is a result; phase 2's
  projection refuted two and both refutations were worth more than the rows they replaced.
- Final chat message is the charter's **owner layer**: what you did → what it means → what
  happens next → what needs the owner; one pointer line naming the handoff.
