---
batch: C2
phases: [9, 10]
role: reviewer
round: 2 (re-review)
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Opus
---

# Batch C2 re-review — one production fix, two guard closures, five new rows

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/plan-reviewer.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Plans: `SR/plans/plan_9.md`, `SR/plans/plan_10.md`. Authority: `SR/planning/intention.md` —
RATIFIED, and it **wins over any plan**.

Your round 1: `SR/handoffs/reviewer/2026-09-21_batch_C2_review_1_handoff.md` (`CHANGES_REQUESTED`).
Fix round answering it: `SR/handoffs/implementer/2026-09-21_batch_C2_fix_1_handoff.md` (DONE, 0 cards).
Tree: **clean at `a21bb59`**; the fix round's last code commit is `d3c93a3`.

## What already happened, so you do not re-spend on it

I hand-verified the fix round rather than consuming its stamp. **Do not repeat these; extend past
them.**

- C2 surface **124 passed**.
- F-1's fix reverted at the site → `test_c1m_sync_selects_the_active_assignment_over_a_terminal_one`
  alone goes red. The row is genuinely armed.
- A `sync_task_stock_assignments` call planted inside `maybe_advance_task_to_working` →
  `test_c4i_no_sync_call_inside_the_task_state_helpers_or_the_shared_core` fires.
- Raw SQL against `tasks` appended **at EOF** (so no registered line number moved) → the scanner
  collects the site. Class (f) detection is real, against a 7-passed clean baseline.
- All three reverted, `git diff --quiet` exit 0.
- **Gate L4, clean tree, mine:** `23 failed / 3669 passed / 1 skipped`, every ID matched one-to-one
  against the published 21-ID set + the two `test_database_isolation` slot IDs, zero unexplained in
  either direction. Passes reconcile as 3661 + 3 + 5.

**Your gate is 23, not 21** (master plan §10). Set `BEYO_TEST_SLOT` on **every** pytest command —
`pytest.ini` carries `-n 6 --dist loadfile`, so even a single-file run claims six worker databases.
Use a slot of your own, e.g. `rv2`.

```
cd app && BEYO_TEST_SLOT=rv2 PYTHONPATH=. pytest <file>
```

**Phase 8A round 2 also landed in this tree** (`efaf9f6`, the match-preview `item_category_id` fix).
It is **disjoint in files** from batch C2 and is not yours to review. Ignore it. If you see it
referenced in a shared file, say so rather than acting.

## Where I want your budget — read this before planning your round

Round 1's best find came from going *past the rows* to the ratified authority, and your AST bet
paid: you proved the guard **noticed** six planted things but never that it **missed** a seventh.
Point that same instinct at the two places this fix round created new risk.

**1. `resolve_processed_group` took a production behaviour change, and it is the least-guarded
thing in the round.** Folding N-5 added three things to an already-approved-adjacent function:

- a `from_state == target` short-circuit (`continue`),
- an early `if not moved: return []` before the flush,
- a zero-delta guard suppressing the row's `:updated` event.

All three **change observable behaviour**. The event is now *not* emitted in cases where it
previously always was. I checked one thing myself: the short-circuit runs **before**
`_assert_allowed_move`, which mirrors `move_assignment` exactly — that part is faithful, not an
invented asymmetry. I did **not** check the rest. Ask:

- Does any consumer — a projection, a cache invalidation, a frontend subscription, an audit path —
  depend on that `:updated` event arriving unconditionally? A suppressed event is a silent failure
  of exactly F-1's shape.
- Is `return []` before the flush safe, or did the flush have a side effect the caller relied on?
- Does the short-circuit create a path where a caller believes an assignment moved and it did not?
- Is there a row that would fail if these three were reverted? If not, **they shipped unguarded** —
  N-5 was a routed note, not a criterion, and a note does not carry evidence.

**2. Does the extended collector miss a seventh form?** You proved five holes by writing them. The
fix closed those five. The question the round cannot answer about itself is whether a sixth and
seventh construct still slip through — walrus targets, `setattr`, a re-exported alias, a
`Mapped[...]` bulk `update()` built from a variable, a comprehension target, `exec`. Plant, do not
reason. Use plan 10 §7's authorized perimeter file and site your plants **at EOF** so no registered
line number moves — my first plant was ambiguous with line drift and I had to re-run it clean.

## Also confirm, at lower cost

- **F-1 is complete, not just present.** The query is fixed; is every *other* reader of that
  assignment in this command consistent with it? A second stale read would reproduce the bug.
- **The five owed rows are armed, not merely green** — C1(m), C4(i), C4(j) (plan 10), C8(d)
  (plan 9, **fixture restated by the owner** — check the test matches the restated cell, not the
  original), C8(a) (may be satisfied by existing tests; the fix round claims it traced them rather
  than duplicating — verify that trace is honest).
- **The six notes** N-1…N-6, each disposed of in the handoff §5. Is each disposition true at the
  site, or is one of them a paraphrase? Round 1 earned L-33 on exactly this.
- **The four judgment calls** in handoff §6. I read them and believe all four are within authority
  and none touches a published contract — but I am the one who wrote the prompt they followed, so
  check me rather than agreeing with me.

## Route every finding by cause

`production | verification | plan`. A finding that is really a plan defect must say so — round 1's
split is why the plans are now correct.

**Do not weaken a criterion to make the round pass.** If a row cannot be satisfied as written, that
is a finding and an owner card, never a quiet restatement. **Authoring or restating a criterion row
is the owner's alone** — propose, never apply.

## Handoff

`SR/handoffs/reviewer/2026-09-21_batch_C2_review_2_handoff.md`: verdict
(`APPROVED` / `CHANGES_REQUESTED`) · a disposition table with one line per criterion row and its
verdict · every finding routed by cause and severity · what you planted and what it proved ·
**what you looked for and did not find** (that is evidence too) · owner questions under
`⚠ OWNER DECISIONS REQUIRED (n)`.

Do not edit `master_plan.md`, the intention, or any criterion cell. **Never push.**

## Stop conditions

Verdict stated · every row dispositioned · the `resolve_processed_group` behaviour change judged
explicitly · a seventh-form attempt made and its result reported either way · the six notes checked
at their sites · findings routed · handoff complete.
