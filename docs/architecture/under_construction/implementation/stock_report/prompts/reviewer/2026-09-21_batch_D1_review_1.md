---
batch: D1
phases: [12, 13]
role: review
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Opus
---

# Batch D1 review — plans 12 and 13

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/independent-reviewer.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

**Scope:** `SR/plans/plan_12.md` and `SR/plans/plan_13.md`. Read `SR/master_plan.md` (§3B for how
this project runs the tester whose stamp you consume, §6 registry, §9's standing rules, §9A lesson
register, §10 environment). The intention is `SR/planning/intention.md` — **RATIFIED, and it wins
over any plan.** Check its `status:` header first.

## Read this before you plan your budget: **you cannot approve this batch**

**D1 is already blocked**, on a production defect that is confirmed, reproduced, and parked on the
owner's desk (card D-5 in `SR/OWNER_CARDS_batch_D.md`). The fix reopens an **APPROVED** phase, so
it is the owner's call and it will not be made tonight.

So the honest verdict available to you is `CHANGES_REQUESTED` or a **conditional** pass on
everything except the blocked rows. **Do not resolve the blockage by weakening anything**, and do
not treat "the owner hasn't ruled yet" as a reason to wave a row through.

Doctrine note, recorded so you are not surprised: §3B says a tester handoff with a
`BLOCKED-PRODUCTION` row returns to the **implementer** before any review is compiled. That step
is **deferred, not skipped** — it is blocked on the owner, and running your review in the meantime
buys the morning both answers instead of one. Say so if you disagree.

## Inputs

- **Tester handoff:** `SR/handoffs/tester/2026-09-21_batch_D1_test_1_handoff.md` — the three-table
  ledger, `78 == 78`, and an unusually candid §8. Its §13 tells you where *it* did not spend
  variation; that is the cheapest place for your budget to buy something new.
- **Implementer handoff:** `SR/handoffs/implementer/2026-09-21_batch_D1_implement_1_handoff.md`.
- **Checkpoints:** implementer `568a1cb` (phase 12) and `b6cbbb9` (phase 13); tester `a0bb9b4`
  (tests + Review logs; `app/` byte-identical to the stamped production tree) and `a7c9af1`.
- **Owner cards already parked, do not re-raise as findings:** `SR/OWNER_CARDS_batch_D.md` cards
  **D-1** (priority-order tenancy row), **D-4** (intention says three keys, code and the published
  contract say four), **D-5** (the blocker), **D-6** (C2(b) cannot fail), **D-7** (three smaller
  rulings). **New** owner questions are welcome; re-litigating these is not.

## The tree is red on purpose — one failure, and it is evidence

`BEYO_TEST_SLOT=<yours> PYTHONPATH=. pytest -m 'not e2e'` gives **24 failed / 3739 passed /
1 skipped**. The 24th is
`test_stock_report_priority_and_ordering.py::test_the_priority_record_snapshots_the_live_awaiting_counter`
— the tester's **deliberate witness** for card D-5, documenting input → expected → observed. It
kept the suite red rather than dropping an assertion to ship green. **Confirm that judgement or
challenge it**, but do not delete it.

Baseline is the checked-in 23-ID set at
`SR/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`. Diff both ways, print both.
**Your slot:** set `BEYO_TEST_SLOT=dr` on **every** pytest command (`pytest.ini` carries
`-n 6 --dist loadfile`; even a single-file run claims six worker databases).

## What I already verified by hand — consume these, do not re-buy them

All on a clean tree, each probe reverted with `git diff --quiet` exit 0.

1. **My own L4 on the implementer's tree: 23 / 3739 / 1**, ID diff empty both directions, passes
   reconciling as 3679 + 60.
2. **Plan 12 C4(e) is genuinely armed.** Two mutants: dropping `image_url` reddens only that test
   in its file; **emitting it only when non-`None`** reddens it too — which is what proves the
   **null half** is asserted independently rather than riding on the populated row's key-set
   check.
3. **The `_row_values` consolidation is inert** — no donor test file was edited and all three
   donor suites are green.
4. **The cascade's two fresh `SELECT`s exist** and it imports no context type.
5. **Card D-5's defect, both halves**, against ratified text: `consistency.py:200-222` applies the
   `goal_total` rule to every history record though §14C line 1594 scopes it to *goal records* and
   §6.2 line 794 defines those as `quantity_requested_change`; and `repair_stock_report.py:248-255`
   zeroes the record by `client_id` with no type filter.
6. **The ORM-staleness asymmetry (card D-6)**, measured in one run: the counter statement
   (PK equality + `RETURNING`) leaves the instance **synchronised** (ORM 7, DB 7) — so C2(b)
   genuinely cannot fail; the shift statement (range criteria) leaves it **stale** (ORM 3, DB 2) —
   so **13A C5(b) is armable and the D1-before-D2 split was right.** The tester predicted the
   opposite for the shift; it reasoned rather than measured, and I measured.

## Six inert mutants were found this round. Assume there are more.

Four cells in plan 12 (C1(a), C1(b), C1(h), C6(a)) and two in plan 13 named mutants that **could
not fail**. Five had working replacements, measured red, and I folded them; plan 13 C1(a)(i) has
none and is owner card D-7.

**The mechanism is now named, and it should shape where you look:** in a phase whose production
code is deliberately idempotent and de-duplicating, **additive mutants get absorbed** — a spurious
write is overwritten by the mover's own later `UPDATE … RETURNING`, and a spurious event is
dropped by `coalesce_stock_report_events`. **Subtractive mutants bite.** Every remaining
additive-shaped mutation cell in these two plans is a candidate for the same defect.

**This is the highest-value place for your budget.** The standing bet in this project is *prove
the instrument misses, not that it notices* — it has paid three times running (C4(i), C4(j),
C4(k), then this round's six).

## Where the evidence is thin, stated plainly rather than hidden

- **Plan 12 C2(a)/C2(b) have no test at all** — class-3, unforced interleaving, owner-ruled. So
  MC-7's *density-under-a-real-race* is proven by **nothing** in this project. C2(c) proves the
  advisory lock is taken and nothing more. Confirm you agree that is the true coverage state.
- **Plan 13 C1(c) is NOT EXERCISED.** Its existing test probes the premise
  (`discover_live_rows_by_identity` returns `{}`), not the row's outcome at the demand-delivery
  surface. Proving it at the lookup would be a §9 **rule 17** relocation, which is the owner's.
- **Plan 13 C3(a) is `BLOCKED-PLAN`** — the cell says three assignment-deletion events, its own
  fixture makes four (card D-7).
- **Five tests trace to no criterion row** and are declared candidates, credited against nothing.
- **The cascade's two fresh `SELECT`s carry no `workspace_id` term.** Safe today (the caller has
  locked by workspace, `client_id` is a prefixed ULID) and both the tester and I would still add
  it, since the same function *does* thread `workspace_id` into its other statements. Rule on it.

## Standing rules that bite here

- **Never approve a batch a review failed**, and never weaken a criterion to make a round pass.
- **Rule 3** (ORM staleness) — now known to be **too coarse as written**; see card D-6. If you
  agree, say so as a finding against the rule's wording, not against the code.
- **Rule 7** `count_writes`; **rule 8** (same edit at the same site counted once); **rule 9**
  (forced, not raced); **rule 16** frozensets, never a spelled list; **rule 17** relocation is the
  owner's; **rule 18** every registered signature pinned by a row in its own plan — including the
  newly registered `build_stock_report_item_deleted_event`.
- **§10** — `client_id` order is not creation order. The tester fixed one flaky *arming* here
  (C4(b)'s two null rows agreed on both orderings about a third of the time); look for others.

## Your authority

Every finding carries `route: production | verification | plan`. **You author no criterion row and
edit no plan cell** — recommendations go in your handoff; the owner authors. Report perimeter
violations by file.

## Deliverable

`SR/handoffs/reviewer/2026-09-21_batch_D1_review_1_handoff.md`: verdict and per-row PASS / FAIL /
NOT_VERIFIED for all 64 rows; every finding with its route, its evidence, and the command whose
output you pasted; the perimeter check; your one L4 with both ID diffs; and owner questions under
`⚠ OWNER DECISIONS REQUIRED (n)`.

**Review by execution, not by judgment:** every claim you make is backed by a command you ran.
**You may not discharge a mutation cell by reading a ledger** — that is the failure mode this
project measured a reviewer into.

**Never push. Commit with explicit paths, never `git add -A`.**
