---
plan: batch B2 — plans/plan_6.md, plans/plan_7.md
role: reviewer (Claude Opus, skill `plan-reviewer`) — re-review after fix round 1
round: batch_B2-rereview-1
date: 2026-09-21
tree: 29b4395
scope: light and delta-scoped (§3A). Three findings and one arming question.
---

# Batch B2 re-review 1 — after fix round 1

Review 1 (`SR/handoffs/reviewer/2026-09-21_batch_B2_review_1_handoff.md`, tree `ff39a96`) returned
**CHANGES_REQUESTED at 80/88** — one blocking finding, one cause, no production defect anywhere.
One fix round ran, tests only. **This re-review decides whether batch B2 is APPROVED**, and with it
batch B.

If you wrote review 1, you have no memory of it — read it. Its verdict table is the baseline.

Keep this narrow. Phase 6 was 36/36 and is untouched. Production code is unchanged. §"What I
verified correct, specifically" in review 1 lists what to skip.

Paths relative to the repo root `backend/`. `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. Run tests from `app/`.

## The delta

`git diff ff39a96..29b4395` is **tests and plan documentation only**:

| File | Change |
|---|---|
| `test_receive_stock_demand_webhook.py` | +289 — B1's eight endpoint identity tests, S1's two write-path tests |
| `test_location_tracker_webhook_verifier.py` | +24/−13 — S2's orphan deleted, sibling declared |
| `plans/plan_7.md` | Review-log entry, carry-forward CF-4 |

## What I verified (consume by citation, do not re-run)

- **`git diff ff39a96..29b4395 -- app/beyo_manager/` is empty.** I checked it myself. The round was
  tests only, as instructed.
- **L4 on `29b4395`, my own run at 02:58 UTC: 21 failed / 3445 passed / 2 skipped**, failure IDs
  identical to the 21-ID baseline **in both directions**. 3445 = 3436 + 9 net new tests. **Do not
  run L4.** The analytics drifter has recovered and is not present.

## What to decide

**1. B1 — is the identity invariant now proven where the contract says?** Intention §4A MC-3's
final bullet requires it "proven through the webhook endpoint with real JSON bytes", with each of
(a)–(e) its own row and each "two rows" case its own row. Check that each of the eight tests
delivers **real JSON bytes** through `receive_stock_demand_webhook` twice — not pre-built
`DemandEntry` objects — and counts live `stock_report_items` rows: 1 for (a)–(e), 2 for (f)–(h).

**2. The arming question — this is the one that matters.** The implementer ran one arming mutation
and recorded honestly that it reddened **5 of the 8** new tests on their own row-count assertion,
while the other **3 failed through an unrelated consistency check instead**. That is the shape of a
row that passes for the wrong reason: a test that only ever fails via a neighbouring assertion is
not armed on its own terms.

Decide whether those three rows genuinely discriminate. If a different mutation arms them directly,
name it and run it. If they cannot be armed without a production change, say so — that is a finding
worth having, and it is exactly what this round was scoped to surface.

**3. S1 and S2.** The two write-path integration tests (C2(a), C2(x), C2(y)) assert what their
outcome cells name — malformed body → nothing written across W's four MC-9 tables; C2(y) → the row
created and `outcome == "applied"`. And S2: the orphan was deleted and its sibling declared as
CF-4. Confirm both, and that nothing else lost coverage.

## Widening — only this

No production code changed, so §3A's shared-foundation clause is not triggered. Confirm the nine
net new tests did not perturb a row review 1 passed — particularly anything asserting
`count_writes`, the statement budget, or event lists, where extra endpoint traffic in the same file
could change what an instrument observes. Name any row you pull in.

Do not re-verdict the other rows.

## Rules

- **Outcomes, not internals.** An implementation-coupled ask is a backlog note, never
  CHANGES_REQUESTED.
- Do not modify source or tests; revert every probe and prove it byte-identical.
- **Owner asleep, authorized unattended run.** On a card: recommend, and say whether the intention
  settles it. **I will not author a criterion row** — reserved to the owner. Review 1's card 1
  (three uncovered invariants) is still open and deliberately untouched; do not re-litigate it,
  just carry it.
- **This closes batch B.** If you approve, say so without hedging. If you request changes, be
  explicit about what genuinely blocks — this is the second round on this batch.

## Do not touch

The intention; the Scanner repository; the plans except one appended Review-log entry each; the
master plan (§6.1, §6.5 and §9 carry today's amendments; the plan-6 task-cell correction is
recorded in its Review log for the owner); other roles' prompts or handoffs;
`docs/archgraph-anchor-observations.md`. No commits, no graph write, no L4.

## Handoff

`SR/handoffs/reviewer/2026-09-21_batch_B2_rereview_1_handoff.md`. Frontmatter: `plan: batch B2 (6,
7)`, `role: review`, `round: batch_B2-rereview-1`, `state: APPROVED | CHANGES_REQUESTED`, `date`,
`actor`, `tree: 29b4395`. Sections:

1. **Verdict** and row totals of 88, with the delta against review 1's 80/8.
2. **B1** — per-row confirmation of the eight, CONFIRMED / PARTIAL / NOT_DONE.
3. **The arming question** — your measurement on the three, and your ruling.
4. **S1, S2** — confirmations.
5. **Any row pulled in under the widening.**
6. **Findings**, blocking first; **backlog notes** separate; **carry-forward** including review 1's
   card 1 and CF-4.
7. **What you ran**, and the mutation-probe declaration.
8. `⚠ OWNER DECISIONS REQUIRED (n)` with recommendations, or `(0)`.

First line of your final message: `HANDOFF: … | STATE: … | OWNER_CARDS: n`, then a short summary
and the most important thing I should know.
