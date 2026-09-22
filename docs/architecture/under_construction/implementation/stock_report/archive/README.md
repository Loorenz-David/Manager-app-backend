# Archive — spent prompts and consumed handoffs, by batch

**How to resolve a citation.** The `master_plan.md` tracker and the plan Review logs cite artifacts
by their **original** path — `handoffs/reviewer/…` or `prompts/implementer/…`. For an archived
batch those files now live at:

```
archive/batch_<X>/<the same relative path>
```

So `handoffs/reviewer/2026-09-22_batch_D2_review_1_handoff.md` is at
`archive/batch_D2/handoffs/reviewer/2026-09-22_batch_D2_review_1_handoff.md`.

**Citations were deliberately not rewritten.** They record what the path was when the decision was
taken, and rewriting hundreds of them across the tracker and sixteen plans would be a large edit
with no reader benefit over this one rule. Batches A, B1 and B2 were archived the same way before
this note existed; the note is the fix for all of them at once.

| Batch | Phases | Contents |
|---|---|---|
| `batch_A` | 1–3 | prompts, handoffs |
| `batch_B1` | 4, 5 | prompts, handoffs |
| `batch_B2` | 6, 7 | prompts, handoffs |
| `batch_C1` | 8, 11 | prompts, handoffs |
| `batch_C2` | 9, 10 | prompts, handoffs |
| `batch_D1` | 12, 13 | prompts, handoffs |
| `batch_D2` | 13A, 14 | prompts, handoffs |

## What is deliberately still live, and why

Not everything under `prompts/` and `handoffs/` is batch work. These stayed put:

- **`handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`** — the checked-in **23-ID
  baseline**. Every gate in this project diffs against it and several live documents cite it by
  path. It carries a batch name but it is a **live reference artifact**, not a spent one.
- **`handoffs/to_frontend/`** — the published contract
  (`…_api_20260922.md`) and `…_match_preview_v2_20260921.md`, plus that folder's **own**
  `archived/` for superseded contracts. A published handoff is never archived as batch residue.
- **Phase 8A's** prompts and handoffs — 8A was a re-opened phase, not a batch.
- **The planner and mechanism-inventory** artifacts — project-level, not batch-level.
- **`card_R1_*`** — an owner-card change that ran outside any batch.
