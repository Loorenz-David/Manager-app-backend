---
subject: stock_report — what happened overnight, and the one decision that unblocks everything
date: 2026-09-22
actor: orchestrator
---

# Morning brief

**Read this first, then `OWNER_CARDS_batch_D.md`. Everything else is detail.**

## The state in one paragraph

**Batch D1 (phases 12 + 13) is implemented, tested, reviewed, and one fix round deep. It is
`CHANGES_REQUESTED` and it is not approved.** Every route you asked for works and the product code
holds up — 58 of 64 criterion rows pass with evidence that can actually fail. It stops on **one
production defect**, and that defect sits in **APPROVED phase-3 code**, so fixing it reopens an
approved phase. That is a gate decision and it is yours. I did not take it.

**D2 (13A + 14) has not started** and correctly cannot: it needs D1 approved.

## The one decision — card D-5

**Change a row's priority while it has work out, and two things follow.** The board's health
check reports phantom drift **forever**, and pressing repair **overwrites the history record with
zero** — destroying an append-only record MC-6 required.

**Phase 12 is not at fault.** It snapshots the counter exactly as MC-6 says. The defect is in
`consistency.py`, which applies its `goal_total` rule to *every* history record, though §14C
scopes it to *goal records* and §6.2 defines those as `quantity_requested_change` only. The fix is
a type filter in two places.

**Nobody could have caught it before.** Until this batch, `quantity_requested_change` was the only
record type that existed — phase 12 is the first writer of the other two. The defect was latent
and unreachable. Phase 12 is what turns it on.

**My recommendation: authorise the fix inside D1.** Narrow, directed by ratified text, with phase
3's suite staying green as the proof of inertness.

**Until you rule, the suite carries one deliberate red** —
`test_the_priority_record_snapshots_the_live_awaiting_counter` — the tester's witness, documenting
input → expected → observed. It kept the suite red rather than dropping an assertion to ship
green. That was the right call and I left it alone.

## The other ten cards, in the order I would take them

| Card | One line | My recommendation |
|---|---|---|
| **D-5** | the blocker above | **authorise the fix** |
| **D-4** | the ratified intention still says `item_category` is three keys; code and the published frontend contract say four | amend the intention |
| **D-8** | the new "row deleted" announcement is pinned by **nothing** — set its payload to junk and all six delete tests pass | add the row (one assertion) |
| **D-6** | plan 13 C2(b)'s tripwire cannot trip; **13A C5(b) is fine, I measured it** | accept unguarded, record why |
| **D-7** | three small ones: an event count that contradicts its own fixture (3 vs 4), "empty history", an unguarded cascade ordering | correct to four; the rest your reading |
| **D-11** | the assignment list's `client_id` tiebreaker cannot be proven by any honest test | accept the structural check |
| **D-1** | `PATCH …/priority-order` has no tenancy row; its sibling does | add the row (text drafted) |
| **D-10** | eight tests answer to no rule | fold four, drop three |
| **D-9** | seven statements address rows by id with no workspace term — safe today, illegible tomorrow | yes, but **after** D |
| **D-3** | plan 13A's conditional validator extraction over an APPROVED file — needed before D2 | extract, behaviour-preserving |
| **D-2** | where the deleted-event is built — **closed, I registered it** | nothing needed |

## What the night actually bought, beyond the code

**A real bug was written and caught before it reached review.** The list endpoint's priority sort
was built in a SQLAlchemy form asyncpg rejects outright — **every `priority=` request would have
been a 500**. The implementer's own test caught it and it reported the near-miss rather than
quietly fixing it.

**Seven named mutants across the batch could not fail, and the mechanism is now named.** In code
this idempotent, an **additive** mutant is always absorbed — a spurious write is overwritten by
the mover's own later `UPDATE … RETURNING`, a spurious event is eaten by the coalescer. **Seven
for seven.** Only subtractive and reordering mutants bite. Five had replacements measured red and
I folded them; two became cards. This is now **L-41** and it must reach D2's projection before it
runs.

**The correction I am most glad I chased.** The tester found C2(b)'s tripwire inert and
extrapolated that 13A C5(b) would be inert for the same reason — which would have removed the
entire rationale for splitting batch D. **I measured it instead of accepting it:** the counter
statement (PK equality) leaves the ORM **synchronised** (7 vs 7); `close_priority_gap`'s shift
(range criteria) leaves it **stale** (3 vs 2). So C2(b) genuinely cannot fail, **13A C5(b) is
armable, and the split was right.** §9 rule 3 is too coarse as written — **L-40**.

**Your `image_url` row is armed, and I checked the half that actually mattered.** Dropping the key
reddens its test; so does **emitting it only when non-null**, which is what proves the
*present-and-null* case is asserted rather than riding on the populated row's key check. That was
the real risk in your request.

## Numbers, all hand-taken by me on clean trees, never consumed from a stamp

| | result |
|---|---|
| baseline before D1, at `fa301fd` | 23 failed / 3679 passed / 1 skipped |
| after implementation, at `b6cbbb9` | 23 / **3739** / 1 — ID diff **empty both ways**, passes reconciling 3679 + 60 |
| after the fix round, now | 24 / 3739 / 1 — the **only** new ID is the declared D-5 witness |

Rows: **64 in D1** — 58 PASS, 2 FAIL, 4 NOT_VERIFIED. Criterion totals unchanged at **652 rows in
107 criteria across 16 plans** (by the committed script; never typed).

## My own mistakes this run, recorded

- My review prompt cited `/Users/davidloorenz/agent-skills/independent-reviewer.md`, **which does
  not exist** — the file is `plan-reviewer.md`. The reviewer proceeded and flagged it.
- **Plan 12 C4(e) said "two mutants" and listed three** — my defect from when I added your
  `image_url` mutant. Left alone, the tester's arithmetic would have closed while your own key
  went unproven. Fixed before the tester was dispatched.
- I registered `build_stock_report_item_deleted_event` in §6.5 and **did not check that anything
  pinned it** — §9 rule 18's first violation since that rule was written (now card D-8, lesson
  L-43).

Each agent also self-reported something costly, including a fabricated placeholder SHA that
shipped in one commit before its author replaced it. That norm is holding.

## What I did not do, on purpose

- **Did not touch APPROVED phase-3 code** (D-5), because reopening an approved phase is a gate
  decision.
- **Did not amend the ratified intention** (D-4), because it is both a ratified document and a
  published contract — the two halves of the limit I set for an unattended run.
- **Authored no criterion row.** Where a row was needed I drafted the cell text and left it.
- **Did not start D2**, and did not re-review D1 — a re-review before the blocker is ruled would
  buy nothing.
- **Did not skip §3B's return-to-implementer step for the blocked row** — it is **deferred**, and
  recorded as deferred, because it is blocked on you.
