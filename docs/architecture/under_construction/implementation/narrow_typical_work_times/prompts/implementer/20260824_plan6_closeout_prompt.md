---
plan: plan_6
role: implementer
round: 1
date: 2026-08-24
---

# Implement plan 6 — closeout: the frontend handoff, the living docs, the graph

**This is the last phase of `narrow_typical_work_times`. It writes documents.** No production
code, no test-behaviour change, no golden regeneration. If you find yourself editing
`app/beyo_manager/` or changing what an existing test asserts, **stop and report** — a production
defect found here goes back to the phase that owns it as a fix cycle; it is not patched from a
closeout phase.

## Gate check — content only

| # | check | expected |
|---|---|---|
| 1 | `git status --porcelain -- app/` from `backend/` | empty |
| 2 | `plans/plan_6.md` header `state:` | `PROMPT_READY` |
| 3 | master plan §4 rows **1–5** | all **`APPROVED`** |
| 4 | master plan §4 row 6 | `PROMPT_READY` |
| 5 | `planning/intention.md` header `status:` | **`RATIFIED`** |
| 6 | `ls docs/handoff/to_frontend/ \| grep narrow_typical` | **no hit** — the document you are here to write |
| 7 | `redis-cli ping` | `PONG` |

**No SHA is gated on, and no count under `.archgraph/` is gated on.** Both are values that move
for reasons unrelated to your work.

## Read order

1. `master_plan.md` §§4, 5, 6.5, 6.7, **8** (the D30 graph lesson and its applied/owed status),
   **8A** (five lessons from phase 5), 9, 10.
2. `planning/intention.md`: header, **§1A (the measurement ledger, M1–M7)**, §5, **§6.3 — the
   exact eligibility phrasing, normative, do not paraphrase**, §6B, **§6D**, §7 and §§7.1–7.4,
   §9, **§11.3 in full**, §4C.
3. **`plans/plan_6.md` — read §6's ⚠ banner first.** Three criteria (C2, C3, C4), each with a
   trace cell. **C1 and C5 were demoted to task obligations, not deleted** — task 1 still runs
   the docs guard first and still owes its planted-defect probe; task 6 still owes the tracker.
4. `plans/plan_5.md` §8's Review log, and plan 4's — including the projection and review
   handoffs' ledgers, not only the intention's sections.
5. `planning/owner_decisions.md` — D18, D19, D20, D23, D24, **D25**, D30, **D31**.

**Where a lettered section and the numbered section it amends disagree, the letter wins.**

## The three things this phase must get right

**1. The frontend handoff is the deliverable.** `§5 task 2` lists its obligations section by
section. Two that are easy to get subtly wrong:

- **`ALLOCATION_METHOD` v2** — quote §6.3's eligibility phrasing **verbatim**. The contract
  changes for every task even where an individual number does not.
- **`is_estimated` carries NO value change.** §6B keeps the `sections_total == 0` disjunct
  verbatim, so every shipped value is preserved. Say plainly: *nothing to change; the definition
  is now written down.* **But §6D binds too** — the flag *does* move under
  `item_narrowed_uniform` wherever the narrowed and section-wide medians differ in usability,
  and that is the feature working, not a regression. **Both sentences belong in the document.**

**2. Never edit the 2026-08-18 handoff.** Supersede it with the new dated document naming the
file and the section. An in-place edit of a published handoff cost the frontend four days in this
lineage, building a feature on a refusal that no longer existed. **C4(a) verifies the old file is
unchanged from `git diff`, not from memory.**

**3. The architecture graph — read task 5 as rewritten, not as originally published.** In short:
this phase changes no code so it almost certainly owes no delta (**check, do not assert**);
**take anchoring instruction from `.archgraph/agent-operating-policy.md`**, which is committed and
authoritative — not from this plan and not from me; **never gate on `staleNodeCount` or any count
under `.archgraph/`** (it is **5** today and all five are outside D31's scope by name); and never
promote, reject or re-anchor anything — adjudication is the owner's.

**Do not dispatch or execute `prompts/maintenance/20260823_archgraph_reanchor_prompt.md`.** It is
live, unconsumed, and scoped to an operation measured on 2026-08-24 to be incapable of removing a
span. It must be rewritten first, and that is not this phase's work.

## Criteria

**§6, as amended: C2, C3, C4.** Each traces — C2 → M3·M6, C3 → M6, C4 → M3.

**C1's contract is "zero failures", not a test count.** The guard collects 59 today and **task 4
of this plan adds pinned assertions to it**, so any criterion pinning 59 would fail on green code
after your own work. Derive the count when you run it; assert the failure count.

**Task 0 runs both ways** (charter trace chain). If you add pinned assertions, each maps to C2,
C3 or C4. A test that discharges no row is deleted or declared in the Review log as a **candidate
criterion**. You will add few tests here — the reverse half is still owed.

## Environment

From `backend/app/`, **verbatim**: `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'`.
Extra flags invalidate the stamp. Baseline comparator is the **21-ID failing set, not the count**;
phase 5's gate stamp was **2708 passed / 21 failed / 1 skipped**. **One L4 at the end.** The docs
guard alone is `PYTHONPATH=. pytest tests/unit/docs/` and costs ~3 seconds — run it **first**, per
task 1.

## Closing

Handoff to `handoffs/implementer/<date>_plan6_closeout_handoff.md`: the new document's path · what
each of C2/C3/C4 asserts and where · the docs-guard planted-defect probe with its **observed red**
· C4(a)'s `git diff` proof that the 2026-08-18 handoff is unchanged · what you found in the graph
and what you recorded (**including "nothing", if nothing**) · write perimeter diffed · the closing
stamp with the 21-ID diff.

**Do not push. Never `git add -A`.** Stop and report rather than working around a failed gate.
