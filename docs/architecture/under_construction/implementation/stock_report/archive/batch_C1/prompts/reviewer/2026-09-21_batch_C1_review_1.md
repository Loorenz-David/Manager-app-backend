---
batch: C1
phases: [8, 11]
role: review
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Opus
---

# Batch C1 review — plans 8 and 11

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/plan-reviewer.md` — **including its "When the project runs a
  tester" section, which changes what you audit.**
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

**Scope:** plans 8 and 11 — 93 live criterion rows (plan 8: 67; plan 11: 26, C4(h) withdrawn).
Read `SR/master_plan.md` (**§3B** for how this project runs the tester role, then §6, §9, §10)
and `SR/intention.md` (RATIFIED; it wins over any plan).

## Trees and artifacts

| | |
|---|---|
| Implementer checkpoint | `6eaf2d3` — handoff `SR/handoffs/implementer/2026-09-21_batch_C1_implement_1_handoff.md` |
| Tester checkpoint | `8c60fb0` — handoff `SR/handoffs/tester/2026-09-21_batch_C1_test_1_handoff.md` |
| Projection (round 0) | `SR/handoffs/projectionist/2026-09-21_batch_C1_projection_handoff.md` |
| HEAD at dispatch | the commit below this prompt; everything after `8c60fb0` is documentation only |

**This project ran a tester, so the evidence you audit is its three-table ledger, not an
implementer's.** Per your doctrine you audit five things: the production satisfies the plan; the
tester's evidence actually proves the rows it claims; the required mutations are genuinely
discriminating; important behaviour left unverified; and **unnecessary verification complexity** —
redundant tests, same-sign duplicate mutants, orphan tests, extra stages. Over-evidence is a
should-fix against the tester exactly as an uncovered row is.

**Every finding carries a `route`:** `production` (code wrong → implementer) · `verification`
(code right, proof weak/missing/excessive → tester) · `plan` (row ambiguous, contradictory or
unprovable at its boundary → coordinator/owner). One finding, one route; a defect with both
halves is two findings.

## Already verified by the orchestrator — consume by citation, do not re-run

I did these myself rather than taking the tester's word:

- `git diff 6eaf2d3..8c60fb0 -- app/beyo_manager/` — **empty.** (Your doctrine's first one-command
  check. Re-run it if you like; it is one command.)
- The tester edited **zero** criteria-table lines (`git diff` over both plans' tables: 0).
- **L4 on the tester tree: 21 failed / 3541 passed / 1 skipped**, failure IDs identical to the
  published 21-ID baseline by `comm` in both directions, and `3512 + 29 = 3541` exactly.

Your tree matches `8c60fb0` plus documentation. **An L4 of your own is over-evidence unless you
change a file.** Spend the budget on variation instead.

## Where your budget buys something new

The tester's handoff §10 states what variation it did **not** spend. Its own list: one mutant
shape per site and no second same-sign mutant; no `TZ`/locale/clock variation; no repetition or
worker-matrix variation; no boundary sweep on quantities (C4(g) uses 8, C4(h) uses 0 — 1, 2 and
large values unexplored); no permutation of batch sizes; no cross-phase regression sweep under
the `state_map.py` and quantity probes; nothing on the HTTP surface beyond the role cells and the
two renderings; and the `IntegrityError` backstop's own happy path untouched.

**Sample the dispositions that can hide a row that cannot fail** — `ARMED-SHARED`, `EQUIVALENT`
and `UNFORCEABLE`. This round has a lot of them, several newly created by the fold, and they are
where a claim like "either alone is equivalent" or "the same code edit arms both rows" is
asserted rather than measured (§9 rule 8).

Specific places worth adversarial attention, offered as leads and not as a checklist:

1. **Plan 8 C5(b)** is recorded `UNFORCEABLE` under the owner's authorized fallback. Its mutation
   cell was **wrong when I authored it** — it named a `sorted(...)` in
   `create_stock_task_assignments.py` that was never written; the real site is `_locks.py:_lock`'s
   `.order_by(model.client_id)`. I re-sited it. The structural check is named for you, and the
   question you are better placed than anyone to answer is whether "one statement with `ORDER BY
   … FOR UPDATE`" genuinely discharges the lock-order promise for a *batch* of items.
2. **Eleven rows were found unable to fail** (tester §0). Each was repaired. The repairs are
   where a new inert mutation would hide.
3. **Plan 11 C7(a) has no automated instrument** — `test_removal_locks.py` covers `delete_task`
   and `delete_item`, not `remove_item_from_task`. Its cell now says so and calls it a reading
   check. Judge whether that is honest or whether the row should bite.
4. **Five candidate criteria** in tester §8, including one the implementer raised itself: the
   category guard's lock-and-refresh sits before the `_DIRECT_FIELDS` loop (because
   `populate_existing=True` would otherwise discard the request's other field changes), and no row
   covers "category change plus another field in one request". Both agents say nothing would catch
   a regression. If you agree, it is a `plan`-routed finding.
5. **Two undeclared judgment calls** in implementer §8: phase-1 duplicate check ordering, and the
   matcher batching every mismatch rather than stopping at the first.
6. **Plan 8 C3(e)'s router asymmetry** — an unrecognized top-level field gets FastAPI's own
   validation error, not the project's envelope. The row is proven at the command boundary, which
   is where the plan's own fixture shorthand lives. Whether that is a gap is a judgment call the
   implementer flagged rather than hid.

## Owner rulings binding on this review

Six cards were ruled at the projection and two more after the tester, all on 2026-09-21. **They
are settled; do not re-litigate them** — but *do* check they were applied correctly, which is a
different question:

- Plan 8 C1(j)/C1(k) and C5(a) carry `count_writes == 0` clauses (§9 rule 7's fifth use).
- Plan 8 C5(b) authored (the caller's lock order); C4(l) re-stated to the fourteen-key shape, its
  cross-shape clause **moved to plan 13 C6(a)**.
- Plan 8 C6(g) and plan 11 C1(c) rebuilt through a `failed` assignment (§14F F9).
- Plan 11 C4(b)/C5(b) are **known-unarmed** by owner ruling; C4(h) is **withdrawn**.

New standing rules this batch: §9 **17** (relocation is a criterion change), **18** (phases pin
their registered signatures), **19** (test files need tree-unique names). §10 gained the
`client_id`-is-not-creation-order fact.

## Deliverable

Your handoff at `SR/handoffs/reviewer/2026-09-21_batch_C1_review_1_handoff.md`, per your closing
protocol: per-row PASS / FAIL / NOT_VERIFIED for all 93, the verdict, findings each with a
`route`, notes, and any owner cards under `⚠ OWNER DECISIONS REQUIRED (n)`.

You fix nothing. Never push. If you run a probe in production code, revert it and show the file
byte-identical.

Report what you did not check, plainly. Both prior sessions did, and it is why this prompt could
point you at something useful instead of everything.
