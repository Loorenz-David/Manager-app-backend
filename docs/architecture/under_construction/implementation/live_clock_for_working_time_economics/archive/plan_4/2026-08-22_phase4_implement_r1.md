---
plan: 4
role: implementer
round: 1
date: 2026-08-22
project: live_clock_for_working_time_economics
---

# Phase 4 — implement r1: the closeout handoff and the graph delta

You are the **implementing agent** for phase 4 of `live_clock_for_working_time_economics`.
This phase writes **documentation and architecture-graph state only. No code.**

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`

## 0. Doctrine — read these two files first, by absolute path

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

They are your session doctrine, not background reading. The charter gained four
amendments on 2026-08-22 (rules 12–14 and the closing-stamp clause); read it fresh rather
than from memory of a previous session.

**The plan file is your task list. Where this prompt differs from the plan file, the plan
file wins.**

## 1. Gate check — confirm before writing anything, stop and report if any fails

- `plans/plan_4.md` frontmatter reads `state: PROMPT_READY` and `master_plan.md` §3's
  phase-4 row agrees. If either still reads `BLOCKED` or `NOT_STARTED`, you are looking at
  a tree older than this prompt; stop.
- `master_plan.md` §6's **first** block is headed **"⛔ THE GATE IS SATISFIED — 2026-08-22"**.
- `git status --porcelain` is empty **except** for files belonging to master §7's
  recognized external stream 3 (the owner's uncommitted Shopify work). Anything else
  dirty: stop and report.
- `git diff 0aae85e HEAD -- app/` is **empty** — this is the load-bearing one, and it is
  written as a diff deliberately. Do **not** check `HEAD == <sha>`; coordinator doc
  commits land above the gate routinely and an equality check would fail on a tree that
  is substantively correct.
- `archgraph_status` returns 0 pending, 0 stale, 0 diagnostics. Record the revision and
  the node/edge counts you observe — you will state them again after your delta.

## 2. Read order

1. **`master_plan.md` §6's gate block first** — before any other baseline sentence
   anywhere in this repository. The test runner changed on 2026-08-22 and **nothing in
   the invocation announces it**; every baseline printed lower in §6 is superseded.
   Then §7 (the obligations table — your task list, **all seven rows**) and §5.
2. **`plans/plan_4.md`** — your phase. Read §5's criteria **including C9**, which was
   added 2026-08-22, and read §6A's baseline bullet, which was **superseded the same
   day** and is kept only as provenance.
3. **`planning/intention.md`** — the semantic authority for everything the handoff
   asserts: §5.4, §6A C, §2.5A, §2.3A, §3.4A, §1A HC-3A, §9 T1, §8.
4. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md`
   — the document whose §1 you retire and whose §2/§3 you restate as surviving.
5. `docs/architecture/under_construction/implementation/archGraph_mapping_mantainance/open/tooling-repair-anchors-batch-and-contains-canonical-check.md`
   — **one file, two findings** (the plan says "both tooling findings"; they live in that
   single file — nothing is missing). Read it **before** any `archgraph_repair_anchors`
   call and before trusting a `conflicting-canonical-relationship` diagnostic.

## 3. What you are writing

**A new dated document** at
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_<today>.md`,
discharging master §7's seven closeout obligations, one section per obligation, in the
table's order — plus the architecture-graph delta of `plans/plan_4.md` §3.

Nothing under `app/`. No edit to any published handoff.

### The absolute rule of this phase

**Never edit a published handoff.** Corrections to `…_20260815.md` (obligation C8) and to
`…_20260818.md` (obligation 3) ship as statements *in your new document*, naming what they
supersede. This project has a scar here: an in-place edit of a published handoff cost the
frontend team four days and a feature built on a refusal that no longer existed. If you
find yourself opening a published handoff with an editor, you have taken a wrong turn.

### Two things a reviewer will check first, because they are the phase's whole point

- **C1/obligation 1 — the go-live statement.** The 2026-08-19 document's §4 promised the
  frontend that *this pipeline's own dated handoff* signals the retirement of their
  interim verdict-suppression flag. They built it behind one removable flag on that
  promise. A closeout handoff without an unambiguous retirement statement is incomplete
  regardless of what else it contains.
- **C9/obligation 7 — the published baseline, stated with its runner.** Read C9's
  enumeration and satisfy it item by item. A bare count is not acceptable output. Write
  out all 21 failing IDs; do not cite another project's folder as the enumeration, because
  a successor pipeline cannot diff against a pointer.

### The audience rule

The frontend reads this with **no access to our tree**. Every instruction must execute
from their side alone. No internal symbol soup in client-facing sections; `path:symbol`
citations belong in a provenance appendix.

### One tripwire, named precisely

`tests/unit/docs/test_item_economics_handoff_accuracy.py::test_retired_inline_refusal_identity_is_absent_from_live_sources`
walks **every `*.md` under `docs/handoff/`**, so your new file is an input to the suite the
moment you save it. It reddens if your document contains the retired identity token
`ITEM_COST_INLINE_PRICE` + `_ON_PRICED_ITEM` as one string. Do not spell that token — not
in a status table, not in a quotation, not in the appendix. This is a signal, not an
obstacle: it is doing its job.

## 4. The graph delta

Five nodes, one batched `apply_changes`, per `plans/plan_4.md` §3 and intention §8:
`projection-item-economics-task-budget-status`, `…-task-budget-status-worker`,
`…-task-budget-allocations`, `…-task-production-time`, and
`projection-item-economics-task-price-scenario` (the transitive dependency — it composes
`get_task_budget_status` without consuming a worked-derived field, and the delta should
say so rather than implying it reads live seconds).

Binding protocol:

- **Keep, never restate,** the budget-allocations node's existing HC-5 invariant ("the
  response's time-only fields reconcile with the same non-deleted step set used by budget
  status"). It is already correct in the graph; rewriting it is how a true invariant
  acquires a false paraphrase.
- Evidence summaries **describe what the evidence shows and carry no counts** — a count
  inside a summary is immutable once recorded and cost this pipeline an owner
  adjudication (master §6, N6).
- Symbol anchors preferred; **never symbol + span on one entry**.
- `archgraph_repair_anchors`: **one operation per call**; batches fail (tooling finding 1).
- **You never promote, reject or edit a review item.** Graph adjudication is human-owned.
  If your delta lands as `ai_inferred` and pends, that is the correct outcome — report it,
  do not resolve it.
- Re-measure `archgraph_status` after the batch and report pending / stale / diagnostics
  and the new revision. C6 asks that *your* delta be clean on a graph that is clean when
  it lands; it does not ask you to clear anything you did not create.

## 5. Evidence budget

**This session's L4 budget is exactly 0 runs.** That is deliberate and derived, not an
oversight, and the derivation is yours to keep honest:

- `git diff 0aae85e HEAD -- app/` is empty, so the authoritative baseline stamp
  (**21 failed / 2576 passed**, collection 2597, coordinator-measured at the isolation
  project's gate on 2026-08-22) was taken on a tree `app/`-identical to yours. The charter
  makes tree-matched evidence citable across agents without re-execution, and re-running a
  command whose tree identity matches yours is a **finding against the session**, the same
  severity as an unrun named mutation.
- Your perimeter is `docs/` and `.archgraph/`. The only suite surface that reads `docs/`
  is `tests/unit/docs/` — verified by grep at fold time, the other two matching files are
  docstring mentions — so the delta you introduce is fully covered at L1.

**What you run:** `PYTHONPATH=. pytest tests/unit/docs/` from `app/`, **before** writing
and **again** after (C7). That is L1 and is not part of the L4 budget.

**What you cite instead of running:** master §6's gate block for the baseline, and the
enumerated 21 IDs from
`docs/architecture/under_construction/implementation/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md`.
The subset relation to the old 26 (∅ added, five removed) was reproduced by document
arithmetic at fold time — cite it, do not re-derive it by running anything.

If you believe an L4 run is genuinely required, the charter's authorization line is
written **before** the run, never reconstructed after: one sentence saying "narrower
evidence insufficient because …". Then it is not a violation.

Two hazards if you do run the suite anyway: `PYTHONPATH=.` is still required, and **two
pytest runs in the same checkout collide** — both default to slot `main` with workers
`gw0…gw5`, so a second concurrent run drops the first's databases mid-flight.

## 6. Closing protocol

1. Docs guard green (C7), and `git diff --name-only` shows **nothing under `app/`**.
2. Update `plans/plan_4.md`'s tracker frontmatter and append your round to its §7 Review
   log. Update **your own row only** in `master_plan.md` §3.
3. Checkpoint commit the moment you reach `IMPLEMENTED`, subject prefixed
   `CHECKPOINT (not approved):`, under the owner's standing authorization — no round stops
   to ask. **Commit explicit paths; never `git add -A`** (stream 3 is live in the working
   tree and would be swept into your commit under your subject line).
4. Deposit a handoff at
   `handoffs/implementer/2026-08-22_phase4_implement_r1_handoff.md` with the charter's
   frontmatter (`plan`, `role`, `round`, `date`, `state`, `actor`).

Your handoff must declare:

- the session's **full write perimeter** — documents, and **tool-recorded state** (the
  archgraph delta counts as a write; several rounds in this project under-declared exactly
  that);
- **one row per obligation**, saying where in the new document each is discharged — the
  reviewer diffs your ledger against the criteria row by row, so a row reading "done as
  expected" against a criterion whose text says otherwise is the failure mode here;
- the archgraph before/after status (revision, nodes, edges, pending, stale, diagnostics);
- the evidence rows you cited and the two L1 runs you performed, each with hypothesis,
  scope, command, tree identity and result;
- a section headed **`⚠ OWNER DECISIONS REQUIRED (n)`** immediately after your opening
  summary — cards in the charter's format, or **one line saying zero** so the owner learns
  nothing needs them without reading further.

A full review round follows this phase despite its waived projection gate. That is
deliberate: this project's documentation phases have drawn more blocking findings than its
code phases, and every one was in prose someone was confident about.
