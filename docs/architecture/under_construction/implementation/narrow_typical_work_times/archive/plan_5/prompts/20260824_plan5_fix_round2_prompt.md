---
plan: plan_5
role: implementer
round: 2
date: 2026-08-24
---

# Plan 5 — fix round 2 (coordinator consumption; no reviewer has seen this tree)

Your round-1 implementation is in. **Perimeter discipline was exact, the fixture medians were
confirmed at source before assertions, both planted-defect probes ran and reverted with md5s, the
mutation summands match the plan, and the full stamp is clean with the 21-ID set matching.** Three
of the five items below are the **plan's** defects, not yours, and are already corrected in
`plans/plan_5.md`.

Read `plans/plan_5.md` §8's newest entry — *"implementation round 1 consumed"* — in full before
starting. It carries the measurements.

## Gate check

`plans/plan_5.md` header `state: CHANGES_REQUESTED` · master plan §4 row 5 `CHANGES_REQUESTED` ·
`planning/intention.md` header **`RATIFIED`** · `git status --porcelain -- app/` empty (from
`backend/`) · `redis-cli ping` → `PONG`. **`.archgraph/` is the owner's — never gate on it.**

## F1 — BLOCKING. An inert test is claimed as C8(a) coverage

`test_c8_narrowing_changes_the_published_number_and_basis` drives `_TypicalSession`, whose
`execute()` **discards the statement**, and hands it both populations by hand. **Narrowing happens
in SQL. A test that never issues SQL cannot observe it**, and asserting `600` against a fake told
to return `600` supplies its own facts.

**Measured by the coordinator on your tree (`8a4a1cb`), both mutation sites, md5-reverted:**

| mutation | `test_c8_divergent_fixture…` | `test_c8_narrowing_changes_the_published…` |
|---|---|---|
| call site (`specs=()` kwarg) — the plan's published wording | failed | **PASSED** |
| definition (`specs = ()`) — corrected | failed, `assert 375 == 600` | failed, `AttributeError` |

**Under the plan's own mutation the test passes while narrowing is entirely gone.** This is the
row-that-cannot-fail family attached to **M1** — the ledger's top entry, and the criterion the
owner added *this phase* because inert coverage of M1 was the risk.

**Two honest exits, and no third** (charter rule 16):
1. **Delete it.** `test_c8_divergent_fixture_measures_narrowed_600_against_section_375` is the
   real proof and it bites correctly.
2. **Declare it in the Review log as a candidate criterion** for what it *actually* discharges —
   name the defect it catches and the ledger entry it serves. Do not describe it as narrowing
   coverage; it is not.

**Do not "strengthen" it into an integration test.** That duplicates the row that already works,
and over-evidence is a defect symmetrically.

## F2 — the plan's mutation for C8 was sited wrong (plan defect, corrected)

§6A C8 now reads **definition**, at the derivation line
`specs = (spec,) if spec is not None and spec.is_narrowing else ()` → `specs = ()`. Re-run C8's
mutation at the corrected site and record the red as **`assert 375 == 600`**.

**What you owed and did not give:** your ledger reported C8's red as *"fails before narrowed
result, with no `spec_index`"* — an exception, not the number the row demands, and the row says in
bold *"it reddens on a number, not on a label."* **A red that is not the stated observable is a
divergence to route, not a row to tick.** Same rule as §6A.F's medians, one level out.

## F3 — C5(i) has no literal (plan defect, corrected)

§6A C5(i) read *"flips `600` → the stated two-section sum"* and never stated it. Your `750`
entered the ledger from the implementation, not the plan. **Derive it from §6A.F's
excluded-section value, show the derivation, and write the literal into the criterion row.**
Confirm or refute `750`; do not adopt it because it is already written down.

## F4 — C1(c)'s instrument was substituted

§6A C1(c): *"asserted through a spy that delegates"*, and after N1 dropped the payload clause,
*"the spy carries the row alone."* You shipped an `inspect.getsource` substring scan
(`test_narrowed_price_scenario.py:143-146`). It reddens on correct code if the call is reformatted
across lines, and it sees only the exact literal `typical_times_statement(ctx.workspace_id,
now=ctx.now`. **Mutation C1(ii) adds precisely that literal, so its red shows the scan matches the
string it was built from and nothing about its reach.** D24 is a contract and this row is its only
guard.

**Fix:** install the delegating spy the plan specifies, on the statement symbol as imported into
`get_working_section_typical_times`'s namespace, and assert the call arrives with **no** `now`
argument. Re-run C1(ii) against the spy. **Probe on that file is authorized** (§4A N3) — reverted
and md5-verified.

## F5 — the baseline section is a mid-implementation snapshot

The handoff says *"The new file was absent at baseline; collection was 67."* Measured:
`test_price_scenario_query.py` collects **52** alone and `test_narrowed_price_scenario.py`
collects **16**, so 67 **necessarily includes the new file**, and 60 failures require production
to have been edited already. The numbers are real; the label is not.

**Fix in the handoff, not in code:** restate that section for what it is — a post-test-authoring,
post-production-edit slice — and say plainly that **no pre-edit baseline was captured for this
phase's two files**. The declared comparator is the 21-ID set and your stamp matches it, so the
risk is contained. **An admitted absent baseline is the cheaper of the two honest options; a
mislabelled one is not.**

## Closing

Handoff to `handoffs/implementer/<date>_plan5_fix_round2_handoff.md`. Carry: what you did for each
of F1–F5 · the re-run C8 and C1(ii) mutations with their **observed** reds · C5(i)'s derivation ·
the corrected baseline statement · write perimeter diffed · md5 table for every probe · the
closing stamp with the 21-ID diff.

**One L4 run this cycle**, at the end. Everything else is L1. **Consume your own round-1 stamp by
citation for anything the tree did not change.**

**Do not push. Never `git add -A`.** Stop and report rather than working around a failed gate or
an unauthorized perimeter change.
