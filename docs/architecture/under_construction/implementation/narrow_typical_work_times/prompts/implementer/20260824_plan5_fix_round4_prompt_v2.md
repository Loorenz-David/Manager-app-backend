---
plan: plan_5
role: implementer
round: 4
date: 2026-08-24
supersedes: 20260824_plan5_fix_round4_prompt.md
---

# Plan 5 — fix round 4 (v2). Two items, no production change.

**This supersedes `20260824_plan5_fix_round4_prompt.md`, which carried a false gate condition and
correctly halted a session.** That prompt said *"`git status --porcelain -- app/` is NOT empty at
your start — round 3's fix is uncommitted."* **That was wrong.** The coordinator committed round 3's
work in the same act that wrote the prompt (`387d36e`), inverting the condition it had just
written. The original prompt is left unedited on purpose; this document replaces it.

**The halting session did exactly the right thing** — it checked the gate at source, found it
false, changed nothing, and reported. Do the same if anything below does not match.

## Gate check — every line re-run by the coordinator against **this** tree

| # | check | expected | verified |
|---|---|---|---|
| 1 | `git status --porcelain -- app/` from `backend/` | **empty** | ✓ |
| 2 | `git log --oneline -1` | `387d36e` | ✓ |
| 3 | `plans/plan_5.md` header `state:` | `CHANGES_REQUESTED` | ✓ |
| 4 | master plan §4 row 5 | `CHANGES_REQUESTED` | ✓ |
| 5 | `planning/intention.md` header `status:` | **`RATIFIED`** | ✓ |
| 6 | `redis-cli ping` | `PONG` | ✓ |
| 7 | round 3's test-file work present in `HEAD` | yes — `387d36e` carries it | ✓ |

**Round 3's fix is committed and is your starting point.** `test_narrowed_price_scenario.py` at
HEAD already has the DB-backed C1(b) and the end-to-end C8. `.archgraph/` is closed under D31 — do
not read it for state.

## Item 1 — point C1(b) at `plain_task`, not `narrowed_task`

C1(b) currently drives `fixture["narrowed_task"]` (`test_narrowed_price_scenario.py:118`) and
asserts `600`. That makes the clock row sensitive to narrowing.

**Measured by the coordinator on this tree, both probes reverted and md5-verified:**

| mutation | round 3's ledger declared | **measured** |
|---|---|---|
| C8(ii) — `None` at the service call site | C8(c) | **`test_c1b` + `test_c8`** |
| C8(i) — `specs = ()` at the derivation line | C8(a) | **`test_c1b` + `test_c2d` + `test_c5` + `test_c8`** |

**The extra reds are correct behaviour** — a test asserting an exact served value is properly
sensitive to anything that changes it. Nothing is unarmed. Two things follow:

1. The declared bite sets are **narrower than the truth**, which costs the next reviewer a finding
   against correct work.
2. **M7's only composed guard reddens for M1 reasons**, so its red no longer names the clock —
   master plan **§8A lesson 3**.

**The fix.** Drive **`plain_task`** (§6A.F — category-less, non-narrowing). Section-wide is
**`375`** with the boundary group in and **`0`** with it out, so C1(i) still reddens the row **on a
number**, and no narrowing mutation touches it.

**Keep everything else round 3 built for this row**: the real `db_session`, the `FakeDatetime` on
`…get_working_section_typical_times.datetime` returning `ctx.now - 1s` then `ctx.now + 1s`, and
`frozen = 2026-10-30` landing the fixture's existing `max(closed_at) = 2026-08-01` exactly on the
90-day boundary. **Do not modify `_narrowing_fixture.py`.**

## Item 2 — reorder C1(b)'s assertions

The numeric assertion precedes the byte-identity assertion, so under C1(i) pytest stops at the
number and **byte-identity never executes**. It is the row's stated observable and M7's — put it
**first**, then the numeric literals. Confirm by measurement which line reddens.

## Ledger

**Re-derive every mutation's bite set by running it, not by reasoning about it.** The two above are
corrected; check the rest the same way. `C1 2 · C2 3 · C3 2 · C4 2 · C5 2 · C6 1 · C7 1 · C8 2` =
**15** named mutations plus **2** planted-defect probes = **17 rows**. Print the summands.

**Rows whose site and observed red are unaffected by this edit may be cited from your round-3
handoff.** Say which you cited and which you re-ran.

## Evidence

**One L4 at the end.** Everything else L1. **No production change is expected** — if you find
yourself editing `app/beyo_manager/`, stop and report.

## Closing

Handoff to `handoffs/implementer/<date>_plan5_fix_round4_handoff.md`: both items with observed
reds · the corrected bite-set table · which ledger rows were cited and which re-run · write
perimeter diffed · md5 table · closing stamp with the 21-ID diff.

**Do not push. Never `git add -A`.** Stop and report rather than working around a failed gate —
as the last session correctly did.
