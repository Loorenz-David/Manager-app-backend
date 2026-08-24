---
plan: plan_5
role: implementer
round: 4
date: 2026-08-24
---

# Plan 5 — fix round 4. Two items, no production change.

**Round 3 closed both blocking findings, and closed B1 in the preferred form.** C8 drives the
service end to end and asserts the served payload; C1(b) is DB-backed with the prescribed
`FakeDatetime`, the boundary group, and a numeric red. Every prescribed element was declared one by
one. Perimeter was one test file with production untouched, the ledger summands were right at
15 + 2 = 17, and the stamp is clean with the 21 IDs enumerated.

**This round exists because of one consequence round 3 could not have seen from inside itself.**

## Gate check

`plans/plan_5.md` header `state: CHANGES_REQUESTED` · master plan §4 row 5 `CHANGES_REQUESTED` ·
`planning/intention.md` header **`RATIFIED`** · `redis-cli ping` → `PONG`.
**`git status --porcelain -- app/` is NOT empty at your start** — round 3's fix is uncommitted in
the working tree. That is expected; it is your starting point, not drift. `.archgraph/` is closed
under D31 — do not read it for state.

## Item 1 — point C1(b) at `plain_task`, not `narrowed_task`

**Measured by the coordinator on your tree, both probes reverted and md5-verified:**

| mutation | your ledger declared | **measured** |
|---|---|---|
| C8(ii) — `None` at the service call site | C8(c) | **`test_c1b` + `test_c8`** |
| C8(i) — `specs = ()` at the derivation line | C8(a) | **`test_c1b` + `test_c2d` + `test_c5` + `test_c8`** |

**The extra reds are correct behaviour** — a test asserting an exact served value is properly
sensitive to anything that changes it. Nothing is unarmed. But two things follow, and the second
matters more:

1. The ledger's declared bite sets are **narrower than the truth**, which costs the next reviewer a
   finding against correct work.
2. **M7's only composed guard now reddens for M1 reasons.** A clock row that fails when narrowing
   breaks no longer identifies the clock as the cause — master plan **§8A lesson 3**, written one
   round ago.

**The fix is one edit that solves both.** Drive **`plain_task`** (§6A.F — category-less,
non-narrowing) instead of `narrowed_task`. The section-wide value is **`375`** with the boundary
group in and **`0`** with it out, so:

- C1(i) still reddens the row **on a number** (`375` → `0`);
- **no narrowing mutation touches it**, so C8(i) and C8(ii) narrow to their real rows.

**Keep everything else round 3 built for this row** — the real `db_session`, the `FakeDatetime` on
`…get_working_section_typical_times.datetime` returning `ctx.now - 1s` then `ctx.now + 1s`, and
`frozen = 2026-10-30` landing the fixture's `max(closed_at) == 2026-08-01` exactly on the 90-day
boundary. **Do not modify `_narrowing_fixture.py`** — choosing `frozen` to meet the existing
timestamp was the right move and it stands.

## Item 2 — reorder C1(b)'s assertions

The numeric assertion currently precedes the byte-identity assertion, so under C1(i) pytest stops
at the number and **byte-identity never executes**. Byte-identity is the row's stated observable and
M7's — put it **first**, then the numeric literals.

Confirm by measurement that under C1(i) the failing line is now the byte-identity assertion, and
record which line reddened.

## Ledger

**Re-derive every mutation's bite set by running it, not by reasoning about it.** The two measured
above are corrected; check the rest the same way. `C1 2 · C2 3 · C3 2 · C4 2 · C5 2 · C6 1 ·
C7 1 · C8 2` = **15** named mutations plus **2** planted-defect probes = **17 rows**. Print the
summands.

**Rows whose site and observed red are unchanged by this round's edit may be cited from your
round-3 handoff** — only C1(b)'s own row and the two C8 mutations' bite sets are affected. Say
which you cited and which you re-ran.

## Evidence

**One L4 at the end.** Everything else L1. No production change is expected in this round; if you
find yourself editing `app/beyo_manager/`, stop and report instead.

## Closing

Handoff to `handoffs/implementer/<date>_plan5_fix_round4_handoff.md`: both items with their
observed reds · the corrected bite-set table · which ledger rows were cited and which re-run ·
write perimeter diffed · md5 table · closing stamp with the 21-ID diff.

**Do not push. Never `git add -A`.** Stop and report rather than working around a failed gate.
