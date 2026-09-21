---
phase: 8A
role: review
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
agent: Codex (terra)
---

# Phase 8A — review. **Review by execution, not by judgment.**

You are a **Codex** session. Skills are not auto-loaded, so **read these by absolute path first**
and follow them as session doctrine:

1. `/Users/davidloorenz/agent-skills/plan-reviewer.md`
2. `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

Scope: **phase 8A only** — `SR/plans/plan_8A.md`, its 20 criterion rows. Its authority is
`SR/planning/intention.md` **§14G** and **MC-21**, which win over the plan.
Implementer handoff: `SR/handoffs/implementer/2026-09-21_phase_8A_implement_1_handoff.md`.

## Read this before anything else

This project's standing rule is that reviews run on Opus, never on a weaker model. That rule was
**earned by measurement**: in a head-to-head on an identical tree, the weaker reviewer approved a
phase carrying an inert safety switch and a silent `DROP DATABASE`, and **affirmed coverage that
did not exist by trusting the implementer's ledger.**

The owner has knowingly set that rule aside for this one phase. This prompt is built so the
specific failure it names cannot happen here:

> **Every claim you make must be backed by a command you ran and whose output you paste.**
> You may **not** discharge a mutation cell, a coverage claim or a pass/fail verdict by reading
> the implementer's ledger, its handoff, or a comment in a test. If you did not run it, it is
> `NOT_VERIFIED` — and `NOT_VERIFIED` is an honest, acceptable answer. A confident verdict with
> no pasted output is the one outcome that makes this review worthless.

You are strong at executing and reporting precisely. Do that. Where a question is genuinely a
judgment call and you are unsure, **say you are unsure and route it to the owner** rather than
resolving it.

## Step 1 — the perimeter, one command each, paste the output

```
git status --porcelain                                  # must be clean
git log --oneline -5
git diff <implementer-checkpoint>..HEAD --stat           # what actually changed
git diff <implementer-checkpoint>..HEAD -- docs/         # docs should be plan Review log only
```

Anything changed outside plan 8A §4's declared file list is an automatic finding.

## Step 2 — the extraction is proven by an existing suite, so run it

The phase moves the acceptability decision out of `create_stock_task_assignments.py`. It is a
move, not a rewrite: the checks, their order and their reason strings must be unchanged. **Phase
8's own 67 armed rows are the proof.** Run them and paste the result:

```
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_delete_stock_task_assignments.py
```

Then **read the moved code against the original** and confirm by eye that the **order** of checks
is identical — `git show <pre-extraction-sha>:app/beyo_manager/services/commands/stock_report/create_stock_task_assignments.py`
gives you the before. MC-13's order is deliberately unintuitive (`item_already_assigned` comes
**before** `item_has_no_category` and `category_mismatch`); a reordering would pass most tests
and still be wrong.

## Step 3 — run every named mutation yourself

For each row in plan 8A whose mutation cell names a site: apply it, run the row's test file
(whole file, never `-k`), record **which test failed and on which assertion**, then revert and
prove the revert with `git diff --quiet <file>`.

**Do not take the implementer's word that a mutation reddened.** Re-running them is the core of
this review, not duplication — it is the one thing the measurement above says a weaker reviewer
skips.

If a mutation stays **green**, that is a finding. Check in this order: did the edit land inside
the symbol you meant · does that site execute under this row's fixture · is the mutant genuinely
equivalent (record it as `EQUIVALENT` with the reason).

## Step 4 — the four behaviours most likely to be wrong

Test these against the running code, not by reading:

1. **Stored values win.** With an item resolving by `article_number`, supplying a *different*
   category/properties/quantity in the body must not change the answer, and `values_source` must
   read `"stored"` (plan 8A C3(f)). If the body's values leak in, the preview can answer `true`
   where `create` answers `false` — the exact divergence MC-21 forbids.
2. **`refusal_reason` equals what `create` would refuse with.** Build a triple that `create`
   refuses, call both, and compare the strings. This is MC-21's observable.
3. **No item resolved → `not_evaluated`, `can_proceed` true** (C3(e)). The alternative makes the
   endpoint refuse the case it exists for.
4. **`quantity` is matched, not decorative.** Change only `quantity` against a row whose criteria
   constrain it, and confirm the answer changes.

## Step 5 — what the suite says

One L4. Run it — and every other pytest command — under your own test slot:

> **⚠ Run every pytest invocation under your own test slot.** Another workstream is active in
> this repository. Set `BEYO_TEST_SLOT=a8` on **every** pytest command — not just the L4 —
> because `pytest.ini` carries `-n 6 --dist loadfile`, so even a single-file run claims six
> worker databases. The slot gives you your own set (`beyo_test_a8_gw0…gw5`) and its own
> template, so the two workstreams cannot collide and neither has to wait for the other:
>
> ```
> BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest <file>
> BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest -m 'not e2e'
> ```
>
> The first run in a fresh slot builds its template at the Alembic head, so expect it to be
> slower once. If you omit the variable you silently share the default `main` slot with the
> other workstream, and both results become worthless while looking like genuine failures.

```
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest -m 'not e2e'
```

Expected **21 failed / 1 skipped**, the 21 IDs identical to the published set in
`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3.
Diff both directions and paste both diffs. Baseline before this phase: **3547 passed** at
`798fc69`; reconcile the new pass count against the tests the handoff says it added.

## Step 6 — over-verification is a finding too

Plan 8A deliberately carries **no new criterion tests for the extraction half**, because phase
8's existing rows already prove it. If the implementer added parallel tests for it anyway, that
is a **should-fix**, not a bonus. Same for a second mutant of the same shape at one site, or a
test tracing to no row.

## Deliverable

`SR/handoffs/reviewer/2026-09-21_phase_8A_review_1_handoff.md`:

- **per-row PASS / FAIL / NOT_VERIFIED for all 20 rows**, each with the command and output that
  justifies it;
- the verdict: `APPROVED` or `CHANGES_REQUESTED`;
- findings, each with a `route`: `production` (code wrong) · `verification` (code right, proof
  weak, missing or excessive) · `plan` (row ambiguous, contradictory or unprovable);
- your mutation table: site, command, observed red (test id **and** assertion), reverted yes/no;
- owner questions under `⚠ OWNER DECISIONS REQUIRED (n)`;
- **what you did not check, stated plainly.**

**You fix nothing.** If you run a probe, revert it and show `git diff --quiet` clean. Never push.
Do not edit any plan, criteria cell or the master plan.

A review that says "I ran these, here is the output, these three rows I could not verify and
here is why" is worth far more than one that says everything passed.
