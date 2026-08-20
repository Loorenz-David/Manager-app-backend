---
plan: 2
role: reviewer
round: 5
date: 2026-08-20
project: live_clock_for_working_time_economics
---

# Session prompt — plan 2 re-review (round 5), `live_clock_for_working_time_economics`

## 1. Standing and scope

This is a **delta-scoped re-review** of fix r4, which closed review r3's findings.
Round history:

| Round | What happened |
|---|---|
| projection r0 | 22 ledger rows routed; 3 amendments corrected by the coordinator before applying |
| implement r1 | production code correct; **C6 and C9 absent, C8 unable to fail** — coordinator-measured |
| fix r2 | those closed; 14-row ledger swept |
| **review r3** | first full review — **code confirmed correct**; B1 + 5 should-fix on the proof |
| fix r4 | B1, S1–S4, N4 closed; +199 test lines, **3 production lines** (2 comments, 1 token) |

**Settled ground — the coordinator verified these independently. Do not re-derive them;
report only if you find them wrong:**

- Perimeter: `git show a9a143f -- app/beyo_manager/` is exactly four `+`/`-` lines — two
  D7 comments and N4's token. Nothing else in production.
- Clean suite at `a9a143f`: **26 / 2478 / 1**, failing-ID set identical to master §6's
  enumeration in both directions.
- **B1(a) reproduces ID-for-ID**: the settled-substitution mutation adds exactly the four
  claimed IDs, zero removed, and moves `share_state` from `over_share` to `on_track`.
- **S3 closed at source**: `closed_at=datetime.now(UTC) - timedelta(days=1)` with the
  statement call still argument-free. The 2026-11-17 expiry is gone.
- **S4 and N4 closed at source**, comments present at both substitution sites naming the
  fail-loud consequence.

Read `/Users/davidloorenz/agent-skills/pipeline-charter.md` and
`/Users/davidloorenz/agent-skills/plan-reviewer.md` by absolute path first. Read order
otherwise: `plans/plan_2.md` §5 and §7's **five** consumption entries, master plan §4/§5
(seventeen rules)/§6/§7 including *Recognized external commit streams*, intention §1A,
§4.1A (through **C.1**, round 4f), §5.2, §9A.

## 2. Step 1 — perimeter

`git diff 771ff46..HEAD`. Consult master §7's external-stream list: the cap stream's files
are foreign-but-expected; anything else outside fix r4's declared perimeter is an
automatic finding. **A golden JSON moved by anything other than this phase's own work is
an escalation to the owner, not an attribution.** Measure your own baseline on the tree
you run on; carry no count.

## 3. Lead probe — F-R4: do the byte-identity rows discriminate anything?

`test_c4_frozen_open_record_payloads_are_byte_identical` was added to satisfy intention
§5.2 criterion 2. **Coordinator measurement:** replacing `ctx.now` with
`datetime.now(timezone.utc)` at E-P's loader call reddens four IDs — and **this row is not
one of them.** Two serves microseconds apart round to the same integer, so byte-identity
is blind to a clock leak.

That is the **T1 defect the mechanism-inventory gate already caught once** and rewrote as
T1′ ("two runs milliseconds apart round to the same integer, so the test passes under its
own defect"). It has resurfaced one level up, inside the row written to satisfy the
criterion T1′ replaced.

Your question, and it is the round's most valuable one: **is there any single-site
production mutation that these rows alone catch?** Candidates worth trying: removing
E-P's `.order_by(TaskStep.client_id.asc())`; anything that makes dict or row ordering
non-deterministic; a server-now field reaching a payload. Report one of:

- **A mutation that works** — name it, both sides, and the row is honest.
- **None found** — then say so plainly. The resolution is *not* deletion: the rows still
  assert the loader count across two serves, and §5.2 criterion 2 is a shipped contract.
  The resolution is to **record what they actually guard**, and to state that **plan 3
  must not rely on them** as its open-record determinism guard — because review r3's
  justification for adding them was exactly that reliance.

## 4. Remaining depth targets

Charter rule 6, in order. These are the parts of fix r4 nobody has checked.

- **S1's three clauses (C6 row 1).** (i) no excluded step holds an open working record;
  (ii) `charged_seconds` computed from settled values, asserted on the division input;
  (iii) `typical` blocks byte-identical. For each: **could it fail?** Clause (iii) has no
  substitute anywhere in the phase and guards §4.3A path 3 — the plan's own "expensive
  mistake". Note that after `_recompute_step_time_totals` the settled total equals the
  live one, so check the comparison is not made where the two coincide.
- **S2's recursive walk (C7).** The plan required walking **every key** of
  `serialize_task_budget_status(...)` on the pattern of
  `test_production_time_query.py:test_c14_c16_flat_time_only_degradation_and_tenant_boundary`.
  Verify the walk is genuinely recursive and reaches the top level, including the
  `include_monetary=False` branch's own `payload["allowed_worker_minutes"]`. Then the
  greater-than clause: does the worker settled-basis mutation (ledger row 7) still redden
  it?
- **The C2 positive-allowance fixture.** It asserts 186 / 1500 / −1314 / `over_share`.
  Confirm the fixture makes its own predicate the **only** reason the outcome holds
  (charter rule 2's companion) — in particular that no second sufficient cause produces
  `over_share`, which is how the previous C2 row died.
- **Intention §4.1A C.1** was added at round 4f on review r3's S1. Check the text says
  what the code does, and that C6's clause (i) actually pins it.

## 5. If you find nothing blocking

Say so and recommend approval explicitly — a re-review that ends clean should end clean,
not manufacture a finding. Note what the phase still owes downstream:

- plan 3's D9 work and the criterion-shape lesson (lettered rows, one named mutation
  each — plan §7's review r3 entry);
- closeout obligation 7: the approval commit must publish the tree **and** the baseline
  measured at it, since `narrow_typical_work_times` D23 builds on it;
- the three pending `ai_inferred` graph items + r1's N6, still the owner's
  (`plans/plan_4.md` C6) — **do not adjudicate them.**

## 6. Constraints and closing protocol

Full suite for any mutation; both-direction ID diff; revert; verify the revert by hash.
**Record the tree each measurement was taken at** — a sweep is not a round (master §5), and
a foreign commit can land inside one. Citations `path:symbol`. You write your handoff and
nothing else.

Deposit at `handoffs/reviewer/2026-08-20_phase2_rereview_r5_handoff.md`, frontmatter
`plan: 2`, `role: reviewer`, `round: 5`, `verdict`, `date`, `actor`. Carry: the
owner-readable opening; `⚠ OWNER DECISIONS REQUIRED (n)`; findings as
blocking/should-fix/notes with citations and, where a defect is named, the mutation that
must turn a test red with both sides; your F-R4 conclusion stated plainly either way;
lessons routed by artifact; and your full write perimeter — which must be exactly the one
handoff file.
