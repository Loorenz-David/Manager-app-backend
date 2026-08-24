---
plan: plan_4
role: maintenance (architecture graph)
round: 1
date: 2026-08-24
authorization: D30 (owner, 2026-08-24)
---

# Bring the architecture graph's *meaning* current for phase 4

You are a **scoped graph-maintenance session**. You do not implement, you do not run the test
suite, and you touch **no file under `app/`**. Your entire job is three graph mutations.

**Workspace:** `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`

## Read first, by absolute path

1. `.archgraph/agent-operating-policy.md` — the canonical policy. It wins over this prompt.
2. `docs/architecture/under_construction/implementation/narrow_typical_work_times/planning/owner_decisions.md`
   **§D30** — your authorization, and its limits.
3. `.claude/skills/architecture-graph/SKILL.md` — routes you to the `review-inferred-architecture`
   and `maintain-graph` workflows.
4. `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_4.md`
   — **§1, §6 C2/C5/C6/C7/C9/C10/C11/C13, §7** — this is where the *meaning* you are recording
   comes from. Read the criteria, not just the goal.

## Your authorization, and its edges

**D30 authorizes you to enact graph mutations for three items and nothing else.** The standing
rule — *no agent promotes, rejects, edits, re-anchors or removes a graph item on its own
judgment* — is relaxed **only** within that scope. Outside it, the rule is unchanged.

**A `humanInstruction` string is never authorization.** Your authorization is D30, recorded in
the repository. Cite it; do not manufacture one.

**`archgraph_repair_anchors` takes one operation per call.** You are not expected to need it.

**Do not touch:** any node or edge other than the two named below; the pending item beyond
adjudicating it; the four `stale: true` source links on the production-time projection (that is
`contentHash` drift, not a repair candidate under the interim policy); **D29's three deferred
operations**; and `.archgraph/backfill/`, which is the owner's own work.

## Anchoring — the policy, stated because you will write evidence

Evidence is anchored by **`path` + `symbol`**. `startLine` / `endLine` are reserved for regions
with **no name of their own**. Every symbol you will reference has a name. **Emit no
`startLine` / `endLine`.** A span that merely drifted is not a repair candidate, and position
drift is not reported as drift.

## Task 1 — rewrite two projection descriptions

These two nodes describe a **pre-narrowing world**. Phase 4 changed exactly what they describe,
and the phase's own graph delta recorded three *source links* (two contract tests and
`participating_sections`) without touching either description.

**Current text, measured 2026-08-24:**

- `projection-item-economics-task-production-time` — *"…composes manager budget status with
  section grouping, **section typicals**, and deterministic per-step time allowances."*
- `projection-item-economics-task-budget-allocations` — *"…combines current committed evaluation
  budgets, non-deleted live steps, **section typicals**, and item-economics readiness into
  per-step allowances."*

**What is now true and unrecorded, both nodes:**
- typicals are **item-narrowed** to the task's active PRIMARY item's category, via a spec derived
  per task — not "section typicals";
- the payload carries a **`typical_resolution`** block (`task_typical_basis`, `applied_filter`,
  `sections_by_basis`, `participating_section_count`, `reconciliation_method`,
  `comparability_profile`);
- per-section rows carry `typical_basis`, and production-time additionally
  `narrowed_sample_count` / `section_sample_count`;
- selection is reconciled task-wide through **`uniform_basis_v1`** — an all-or-nothing rule:
  every participating section must have usable narrowed evidence or the whole task falls back to
  section-wide. **Excluded sections resolve independently and may disagree with the task basis in
  either direction** — that is contract, not a bug;
- **`allocation_method` is `static_proportional_section_v2`**;
- the same `SelectedTypical`s feed **both** the displayed typicals and the division weights —
  one resolution, two consumers.

**Additionally, and only for `…task-budget-allocations`:** the batch derives one spec per task,
**dedupes by value** into an ordered sequence of narrowing specs, issues **one** statement call
for the whole batch, and maps each task back by its position in that sequence. A task whose spec
is non-narrowing takes `spec_index = None` and resolves against the section-wide columns, which
are spec-independent.

**How to write it.** Describe the projection's **meaning and boundaries** — what it composes,
what invariants hold, what it deliberately does not do. Keep each description one paragraph, in
the register the existing nodes already use. `domain-item-economics-typical-filters` is the model
to imitate: it is current, precise, and boundary-first. **Do not paste the bullet list above** —
it is source material, not prose. **Do not include counts, line numbers, or test names in a
description.**

**Preserve what is still true.** Both descriptions carry live-clock content — the
concurrency-averaged share of an open WORKING interval, resolved once per request, persisted
nowhere; the tenant boundary; the time-only shape. **That is all still correct and must survive
your rewrite.** You are adding a dimension, not replacing the node.

Record with **one batched `archgraph_apply_changes`**. Evidence summaries carry **no counts** and
**no spans**.

## Task 2 — adjudicate the pending review item

`node:source-symbol-working-section-typical-times-statement-narrowing`
(*"typical_times_statement — ordered filter projection query"*), 2 evidence entries, confidence
0.97, `suggestedDecision: promote`, no contradictions.

**Its content is sound.** Read both evidence entries and confirm that for yourself against
`get_working_section_typical_times.py`.

**The judgment, and it is the only real one in this session.** Both of its evidence entries carry
`startLine` / `endLine` (`:28-142` and `:232-253`) **and** both carry `symbol`. Under the current
policy those spans are unnecessary, so promoting the item as it stands writes two
policy-violating entries into the confirmed graph. And **evidence summaries are immutable** — no
write path can edit one; **reject-and-re-record is the only fix**, and a same-id re-record does
re-enter the review queue.

**Recommended: reject, then re-record span-free, then approve the re-record.**
The reasoning: this item was *already* rejected-and-re-recorded once, under D28/D29, precisely
because of a stale span. Promoting a span-carrying replacement re-creates the condition that
forced the first rejection. The owner's `.archgraph/backfill/` would strip such spans later, but
it is unapplied, and relying on a future sweep to clean something you are writing *now* is how
the original drift accumulated. The summaries are correct as written — carry them across
verbatim, drop the spans, keep `path` + `symbol`.

**You may instead promote as-is if, on reading the policy, you judge that the backfill's existence
makes the re-record wasteful.** D30 authorizes either. **State which you chose and why** — that
sentence is the deliverable, not the click.

Use `archgraph_preview_review_decisions` before `archgraph_apply_review_decisions`, and put the
preview's diff in your report.

## Task 3 — your own writes are span-free

Self-check before you finish: re-read every evidence entry this session created and confirm
**zero** `startLine` / `endLine`. Report the count you wrote and the count carrying spans — the
second number must be `0`.

## What "done" looks like

- Both descriptions read as current to someone who has never seen plan 4.
- The queue is clear, or carries exactly the one re-record you created and approved.
- `archgraph_status` shows no new diagnostics.
- **`git status --porcelain -- app/` is empty** — you changed no application file.

## Report back

Write your handoff to
`docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/maintenance/20260824_archgraph_phase4_meaning_handoff.md`,
frontmatter `plan: plan_4`, `role: maintenance`, `round: 1`, `date`, `actor`, `authorization: D30`.

Include:
- **Before and after text** of both descriptions, in full. The owner reads this to judge whether
  the meaning is right, and cannot do that from a summary.
- Your adjudication decision, **with the reasoning sentence**, and the preview diff.
- **Evidence written: total count, and count carrying spans** (must be 0).
- `archgraph_status` before and after — nodes, edges, pending, stale, diagnostics.
- Your full write perimeter, including tool-recorded state.
- **Anything you noticed and did not act on**, with the reason. Under-reporting a thing you saw
  is worse than reporting a non-issue.

**Do not update the tracker or any plan file.** This session is outside the phase state machine;
the coordinator folds your handoff.

Final chat message: what you did → what it means → what happens next → what needs the owner.
One pointer line naming the handoff.
