---
batch: D2
phases: [13A, 14]
role: implement
round: 1
state: PROMPT_READY
date: 2026-09-22
actor: orchestrator
model: Opus
authority: owner, 2026-09-22 — "apply after D1 approves, then continue with D2. you should complete all the remaning task by your self"
---

# Batch D2 — implement phases 13A and 14. The last implementation batch in this project.

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/implementation-executor.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Plans: `SR/plans/plan_13A.md` (37 rows / 7 criteria), `SR/plans/plan_14.md` (5 rows / 2 criteria).
Intention: `SR/planning/intention.md` — **RATIFIED**, check its header; it wins over any plan.
Master plan: `SR/master_plan.md` — §4 tracker, §6.5 signatures, §6.7 events, §9 rules, §9A lessons.

**D1 (phases 12 + 13) is APPROVED at `d800e73`.** 14 of 16 phases are VERIFIED. Both your plans
have just been through projection round 0 and carry **20 folded corrections**; the projection's
handoff is `SR/handoffs/projectionist/2026-09-22_batch_D2_projection_1_handoff.md`. **The plans are
current — build from them, not from the handoff.**

## Read this section before you read the plans

Four things were wrong in these plans two hours ago and are now right. If you find yourself
reasoning from the old version of any of them, you are reading a stale memory of the project.

1. **13A does NOT touch phase 7.** Owner card D-3 is **closed as "no change"**. There are no
   per-field validator *functions* in `stock_demand_request.py` — only inline expressions — so
   "sharing" them would mean writing a new helper inside APPROVED code for no observable gain.
   **Write the two field checks inline in your new parser.** `stock_demand_request.py` is in the
   **Not changed** perimeter and a diff there is a violation.

2. **`StockDemandDeletedOutcomeEnum` does not exist yet.** The plan used to claim it ships from
   phase 1; it does not — `enums.py:67-69` is a *docstring* saying it belongs to 13A. `enums.py`
   is now in your **Edited** perimeter for **that one name only** (`deleted`, `not_found`,
   `category_not_found`), on the batch B2 / blocker B4 precedent. **Do NOT add
   `INLINE_REPAIR_TRIGGERS`** — it has no caller and charter rule 4 forbids it.

3. **C5(b)'s mutant (i) is retired and replaced.** The old claim was that the cascade's held ORM
   copy goes stale after the previous gap-close. **It does not.** Measured on the production shape:
   `synchronize_session="auto"` → `"evaluate"`, the WHERE clause evaluates identically in Python and
   SQL when the caller passes an **enum member** (it does), so the identity map is **SYNCHRONISED**.
   The cascade's fresh `SELECT` **stays** — recorded "unobservable, not unnecessary", correct
   defensive code, **not to be deleted for being inert**. The replacement **mutant (i-r)** arms what
   actually matters: that **each cascade in the loop closes its own gap against the positions the
   previous one left.**

4. **Plan 14 task 3 is RE-VERIFY, not author.** See §5 below.

## Perimeter — and one deliberate exception

Your perimeter is exactly the two plans' §4 lists. Two points the reviewer's perimeter check will
test:

- **`_events.py` mutation-probe exception.** C5(b) mutant (ii) and C3(d) mutant (i) are planted in
  `_events.py`, which is APPROVED phase-8 code. They are **probes, reverted in the same act**. Plan
  13A §4 names this so a mid-mutation check does not read it as an edit. **Any `_events.py` diff
  surviving at the end of the phase is a violation.** Prove it: `git diff --quiet` after each.
- **No test file outside the plans' declared homes.** `test_process_stock_demand_deleted_locks.py`
  is C5(g)'s declared home and is in §4.

## The five lessons that will decide whether your evidence is real

These are not background. Each one cost this project a round.

- **L-41 — an additive mutant is absorbed here.** Seven for seven across D1. A spurious write is
  overwritten by a later `UPDATE … RETURNING`; a spurious event is dropped by
  `coalesce_stock_report_events`. **Prefer subtractive and reordering mutants.** The projection
  already found and replaced the one absorbed cell in your plans (13A C3(d) mutant (i)) — but it
  also found five additive cells that are **not** absorbed, so do not apply this blanket: check at
  the site.
- **L-42 — fixture discrimination is per row, not per batch.** For every ordered assertion, state
  what your fixture makes distinguishable and what it does not. The same defect was fixed in one
  plan and found untouched in its twin hours later.
- **L-46 — a subset assertion is not a shape assertion.** Where a criterion says "exactly", the test
  says `==`, never `in` or `issubset`. A reviewer replaced a whole event payload with junk and six
  tests passed because nothing asserted equality.
- **L-47 — plant the mutant at every surface the outcome passes through.** Three mutants in D1 were
  absorbed because they were planted at the first of two guards and the second re-raised.
- **L-49 — a probe that does not pass production's own values is not a measurement of production.**
  This is the newest and it is why item 3 above exists: one substitution of a string for an enum
  member produced a false lesson, a false plan cell, and a batch split justified by a claim that was
  not true. **When you probe, derive the values from the call site.**

## Phase 14 specifics — task 3 is the one people get wrong

**Task 3 is RE-VERIFY, not author.** Read the published
`SR/handoffs/to_frontend/HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` against shipped code,
route by route and field by field; flip each **SPECIFIED** tag to **VERIFIED**; and **re-issue only
if something moved** — a new dated file carrying a `supersedes:` key naming the current one, with
the current one **moved** (never edited) to `archived/`. If nothing moved, say so in your handoff
and **leave the published file untouched**. `…_match_preview_v2_20260921.md` is **not** superseded
and **not** moved.

**An in-place edit of a published handoff once cost the frontend team four days.** That is the
whole reason this task was changed from "author" to "re-verify".

**One known defect to check while you are in there:** the contract's §6.1 example shows
`"properties": { "wood_group": "teak" }`. The shipped normalized form is `{"wood_group": ["teak"]}`
(`criteria_normalization.py:9-10`; `criteria_matcher.py:96` does `token in accepted`, a membership
test against a list). **The code is right and the document is wrong.** If you confirm it, that is
"something moved" and the re-issue path applies. Report it either way.

**C2(a) is now met by a TEST, not by a reviewer** (owner ruling, 2026-09-22). Build the test that
compares the handoff's field/nullability table against `domain/stock_report/serializers.py`.

## Environment

**Slot `BEYO_TEST_SLOT=d2i` on every pytest command** — every one, without exception. `pytest.ini`
carries `-n 6 --dist loadfile`, so even a single-file run claims six worker databases and an unset
slot corrupts another session's.

Baseline: the checked-in 23-ID set at
`SR/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`.
**Current L4, hand-taken by the orchestrator: 23 failed / 3742 passed / 1 skipped**, both ID diffs
empty. **Your L4 must still be 23 failures with both diffs empty**; the pass count rises by exactly
the tests you add. Diff the IDs both ways and print both — a count alone is not evidence.

**Budget:** L1 per file you touch, L2 over the stock_report surface, **exactly one L4** at the end.

## Handoff

`SR/handoffs/implementer/2026-09-22_batch_D2_implement_1_handoff.md`: the diff summary; per criterion
row, the test that satisfies it and the mutation you ran with its observed red and its revert proof;
the perimeter declaration; your answer on the §6.1 `properties` defect; the L4 with both ID diffs;
anything you found wrong in the plans; owner questions under `⚠ OWNER DECISIONS REQUIRED (n)`.

Checkpoint: `CHECKPOINT (not approved): stock_report batch D2 — phases 13A and 14 implemented`.

**Report what you could hide.** Every session in this batch has, including a fabricated placeholder
SHA, an arithmetic error in one of my prompts, a measurably false claim I folded into a plan cell,
and — this week — a probe of mine that overruled a correct agent finding because it passed a string
where production passes an enum. That norm is the point and it is holding.

**Never push. Commit with explicit paths, never `git add -A`.**

## Stop conditions

Every criterion row satisfied by a test whose mutation was observed red and reverted · perimeter
exact · `_events.py` clean at the end · one L4 at 23 with both ID diffs · lint clean · Review logs
written · handoff complete · checkpoint committed.

**Not reasons to continue:** another defect you noticed (report it), a test you think is missing
(propose it), tidying, or anything in phase 7.
