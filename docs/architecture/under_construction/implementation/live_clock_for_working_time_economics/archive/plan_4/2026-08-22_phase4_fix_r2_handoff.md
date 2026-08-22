---
plan: 4
role: fix
round: 2
date: 2026-08-22
state: IMPLEMENTED
actor: Codex
---

# Phase 4 fix r2 handoff — B1, S1, S2

Finding-scoped round. All three corrections quoted in the fix prompt are implemented;
nothing was added beyond them. **Rule 14 has nothing to declare** — no quoted correction
was skipped or substituted. N1 was left exactly as it stands, by instruction, as the
independent reviewer's probe.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner in this round.

*(One thing is owner-owned but was **not** created by this round and is not a decision
card: the five `ai_inferred` relationships r1 recorded are still pending human review.
They are the correct outcome of adding inferred items, the coordinator already recorded
them as such, and adjudication happens on the owner's own schedule.)*

## Write perimeter — cycle-scoped, this session only

Documents:

| Path | Why |
|---|---|
| `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` | S1, S2 |
| `docs/…/live_clock_for_working_time_economics/plans/plan_4.md` | frontmatter state + §7 Review log entry |
| `docs/…/live_clock_for_working_time_economics/master_plan.md` | **one new tracker row**, inserted above the coordinator's `CHANGES_REQUESTED` row; that row was not edited |
| `docs/…/live_clock_for_working_time_economics/handoffs/implementer/2026-08-22_phase4_fix_r2_handoff.md` | this file |

Tool-recorded state (the half r1's perimeter under-declared):

| Path | Why |
|---|---|
| `.archgraph/architecture.yml` | five node descriptions edited — **38 insertions / 20 deletions** |
| `.archgraph/changes/2026-08-22T12-55-56-881Z--2e8645.yml` | audit record, budget-status |
| `.archgraph/changes/2026-08-22T12-56-07-697Z--300698.yml` | audit record, budget-status-worker |
| `.archgraph/changes/2026-08-22T12-56-21-228Z--92d2aa.yml` | audit record, budget-allocations |
| `.archgraph/changes/2026-08-22T12-56-32-792Z--d06159.yml` | audit record, production-time |
| `.archgraph/changes/2026-08-22T12-56-48-459Z--e8cffe.yml` | audit record, price-scenario |

**Nothing under `app/`** — `git diff --name-only -- app/` is empty for this session.
**No mutation probe was applied**, so no file was touched-and-reverted; the
applied-and-reverted list for this round is empty, and that is falsifiable against the
checkpoint diff.

## B1 — the graph delta now updates nodes, not only edges

**What changed.** Five projection node descriptions, each through
`archgraph_preview_maintenance_changes` → `archgraph_apply_maintenance_changes`, **one
operation per call**, five previews and five applies, each apply carrying the revision
the preceding one returned.

The four present-tense projections now state the basis the reads actually have — each
non-deleted step's **settled** working seconds **plus** the concurrency-averaged share of
any open `WORKING` interval, resolved once per request through the shared live
worked-seconds loader, **persisted nowhere**:

| Node | Change |
|---|---|
| `projection-item-economics-task-budget-status` | "live non-deleted task-step seconds" — the exact phrase intention §8 names as the drift — replaced by the settled-plus-open-share basis |
| `projection-item-economics-task-budget-status-worker` | the shared `_build_evaluated_status` delegation now says what it carries: the same basis, same loader, same non-persistence |
| `projection-item-economics-task-budget-allocations` | one shared live-seconds map per request, folded into the per-step inputs; **HC-5 invariant untouched** |
| `projection-item-economics-task-production-time` | the basis, and that it is passed both to budget status and into the allocator's response-only rows |

The fifth, `projection-item-economics-task-price-scenario`, was handled on its own terms.
It now records that it composes budget status and so inherits that read's worked-time
dependency **transitively**, and says in the same sentence that it publishes no live
worked-time field of its own and reads no open interval record directly — the line r1's
edge description drew, now drawn on the node as well.

**Binding constraints, verified rather than asserted.**

- **No evidence `summary` or `inferenceReason` touched.** `git diff` over
  `.archgraph/architecture.yml` shows zero `+`/`-` lines matching either key.
  `…-task-budget-status`'s summary still reads "aggregates non-deleted task-step
  seconds" — left alone deliberately, per the prompt: it is immutable through both
  paths, and correcting it would be the owner's reject-and-re-record.
- **HC-5 kept, never restated.** *"Its invariant is that the response's time-only fields
  reconcile with the same non-deleted step set used by budget status."* — present exactly
  once, checked whitespace-normalised against the YAML rather than by eye.
- **One operation per call.** The open tooling finding attributes `INTERNAL_ERROR` to
  batch size on the maintenance path and leaves batching-vs-mixed-kinds unresolved; this
  round did not spend a batch to settle it, so **the cheap experiment that finding
  proposes is still undone**. No `archgraph_repair_anchors` call was needed — no anchor
  moved and no source link changed.

**Graph status, before → after.**

| | Before | After |
|---|---|---|
| revision | `9bcb347f1bf4463ed3522836d86ee102686af9192381d949a5ceb254d173d9b8` | `897d57b3a98553d180fbe15d1af23a3f6c9cd5ef710bdd6c36a2a31bc73a1d66` |
| nodes | 194 | 194 |
| edges | 296 | 296 |
| pending review | 5 | **5** |
| stale | 0 | **0** |
| diagnostics | 0 | **0** |

Stated plainly rather than steered: **maintenance edits moved no count at all**, pending
included. The 5 pending are still r1's `ai_inferred` relationships; this round promoted,
rejected and edited **no** review item. The number that did move is the one that exposed
B1 in the first place — `architecture.yml` went from r1's **zero deletions** to 38
insertions / 20 deletions, which is what a description rewrite looks like in that file.

## S1 — §6A C's rule, carried in substance

Before: *"Never clamp to the previous maximum and never animate time that the workspace
has disowned."* — satisfiable by a 400 ms ease-out, which is what §6A C forbids.

After: *"Never clamp to the previous maximum, and do not animate the descent: render the
drop in one step rather than easing the value down over time — the time is gone at once,
not gradually."*

The no-clamp half is kept; it is separately correct and comes from the same section's
"any decrease" row. §5's closing paragraph ("snap down to the served value rather than
clamp") was already right and is unchanged.

## S2 — a tree identity the consumer can resolve

§7's tree-identity bullet now publishes commit **`dc76db8`** with its subject line
(`CHECKPOINT (not approved): gate stamp + two rows that cannot fail, deleted`), tells the
reader to check that commit out to reproduce the measurement, and adds that as of
2026-08-22 the backend's `app/` tree is identical to it (`git diff dc76db8 HEAD -- app/`
empty), so a measurement on today's tree is comparable without checking anything out.

Both facts were re-verified in this session, not copied: `git log --oneline -1 dc76db8`
resolves to that subject, the `app/` diff is empty, and `git status --porcelain` was
empty at session start.

## Evidence

| Field | Value |
|---|---|
| Hypothesis | The docs tripwires — including `test_item_economics_handoff_accuracy.py`'s rglob over every `*.md` under `docs/handoff/`, which sweeps this document — stay green over the edited handoff |
| Scope | **L1** (targeted; the phase's guard) |
| Command | `PYTHONPATH=. pytest tests/unit/docs/` from `app/` |
| Tree | `e13923f` plus this session's edits (docs + `.archgraph/` only; `git diff --name-only -- app/` empty) |
| Result | **59 passed**, 6 workers, `--dist loadfile` (the shipped parallel default). Run **twice**: once after the handoff edits, once after every document in the perimeter was written — the second run is the one taken on the tree actually handed over |
| ID delta | n/a at this scope — zero failures before and after |

**L4 runs: 0**, matching the budget exactly. The derivation is unchanged and still holds:
`git diff 0aae85e HEAD -- app/` is empty and this session changed nothing under `app/`,
so the authoritative 21 / 2576 stamp's tree is still `app/`-identical to HEAD and is
citable rather than re-measurable. The r1 pre-write docs-guard run was not repeated.
The authoritative baseline (master §6's gate block) was cited, never re-measured.

## Judgment call for the coordinator

**C6 says "five nodes updated"; the fix prompt enumerates four descriptions and then says
to handle the fifth "on its own terms".** I edited the fifth as well, worded so it records
only the transitive dependency and explicitly denies a direct open-interval read. That
meets C6's literal count and the prompt's constraint together. The alternative — leaving
the fifth description alone because r1's edge already carries the claim — would have left
a reviewer checking C6's count against four.

## Not in scope, untouched, and deliberately so

- **N1** — record deletion named as a non-cause. Untouched, exactly as instructed, so the
  independent reviewer meets an unresolved judgment call rather than a pre-empted one.
- **§6A B's two-drops fact** — still absent from the document, which the coordinator
  examined and confirmed correct.
- Everything in the fix prompt's "settled" list.
