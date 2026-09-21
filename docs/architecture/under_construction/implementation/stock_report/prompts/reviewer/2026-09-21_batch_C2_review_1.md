---
batch: C2
phases: [9, 10]
role: review
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Opus
---

# Batch C2 review — plans 9 and 10

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/plan-reviewer.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

**Scope:** `SR/plans/plan_9.md` and `SR/plans/plan_10.md`. The authority above them is
`SR/planning/intention.md` — RATIFIED — and it **wins over any plan**. Read `SR/master_plan.md`
§3B (how this project runs the tester), §6 (registry), §9 (standing rules), §9A (lessons), §10
(environment facts).

## Trees and artifacts

- **Implementer handoff:** `SR/handoffs/implementer/2026-09-21_batch_C2_implement_1_handoff.md`
- **Tester handoff:** `SR/handoffs/tester/2026-09-21_batch_C2_test_1_handoff.md`
- **Implementer checkpoints:** phase 9 `8a5ebc2`, phase 10 `ffa591e`
- **Tester checkpoint:** `a00d858`
- **Production diff must be empty:** `git diff ffa591e..HEAD -- app/beyo_manager/` — the tester
  left no production change, and I re-verified `git diff a00d858..HEAD -- app/` is **empty** for
  all committed work.

## ⚠ A second workstream is in this tree — do not charge it to this batch

**Set `BEYO_TEST_SLOT=c2` on every pytest invocation, not just the L4.** `pytest.ini` carries
`-n 6 --dist loadfile`, so even a single-file run claims six worker databases. Omitting the slot
silently shares the default `main` slot with the other workstream and makes both results
worthless **while looking like genuine failures**.

Phase 8A (match preview + the MC-21 extraction) landed at `9105f71`, implemented on Codex, and is
**implemented but NOT approved** — its own review ran in parallel and may have landed fixes. Its
files:

```
app/beyo_manager/domain/stock_report/assignment_checks.py
app/beyo_manager/domain/stock_report/enums.py                      <-- THE ONE OVERLAP
app/beyo_manager/routers/api_v1/stock_report.py
app/beyo_manager/services/commands/stock_report/create_stock_task_assignments.py
app/beyo_manager/services/queries/stock_report/assignment_check_inputs.py
app/beyo_manager/services/queries/stock_report/preview_stock_task_assignment_match.py
app/tests/unit/domain/stock_report/test_stock_report_assignment_checks.py   <-- 8A FIX, LIVE NOW
```

**A phase 8A fix round is running as you work** and is editing that last file (rebuilding a
fixture off `SimpleNamespace`). It may commit mid-review. It is **not yours**: do not revert it,
do not report it as tester residue, and do not let it into your diffs.

**Exactly one is also this batch's: `enums.py`, declared in plan 9 §4.** I checked both plans'
declared perimeters against 8A's file list — the other five appear in neither plan 9 §4 nor plan
10 §4. **8A's content is out of your scope and is not a finding here.** What *is* in your scope:
whether this batch's changes to `enums.py` are correct and declared, and whether anything in this
batch touched the other five at all (that would be an undeclared perimeter breach and a finding).
If you cannot separate the two authorships in a diff, say so rather than guessing.

## Already verified by the orchestrator — consume by citation, do not re-run

**The tester's L4 is tree-matched and I verified the tree, not the number.**
`BEYO_TEST_SLOT=c2 PYTHONPATH=. pytest -m 'not e2e'` at `a00d858` → **23 failed / 3661 passed /
1 skipped**, failure-ID diff empty in **both** directions against (published 21-ID set + the two
named slot IDs). Pass arithmetic: `3619 + 42 = 3661`. I confirmed `git diff a00d858..HEAD -- app/`
is **empty**, so that stamp still describes the tree you are given.

I also independently reproduced the slot behaviour itself rather than accepting it:
`tests/integration/infrastructure/test_database_isolation.py` gives **51 passed** with
`BEYO_TEST_SLOT` unset and **2 failed / 49 passed** with it set, on a byte-identical tree.

**Your gate condition is 23, not 21** (master plan §10 ruling): the published 21 plus exactly
`test_database_isolation.py::test_worker_name_resolution_uses_xdist_worker` and
`::test_worker_name_resolution[None-None-beyo_test_main_main]`. That is a **pass** — it is my
defect (I mandated slots without checking the isolation suite asserts its own default), the fix
belongs to an APPROVED foreign project, and it is an open owner card. **Do not route it as a
finding against this batch.**

Per the charter's test-evidence rule, tree-matched evidence is consumed by citation. **Do not
re-run an L4 to confirm what is already tree-matched** — spend that budget on variation instead.

### Changed after the tester stamped, deliberately

I folded the tester's **nine plan-cell backfills** (`a567d7b`) into plans 9 and 10 after its
handover. Every one is a **recording of what the tester measured**, not a new assertion, so §3B's
"a ruling that adds an assertion must reach the tester or it is paperwork" is not tripped — but
you should know the cells moved, and each carries a dated `[Backfilled …]` marker so you can find
them. Three matter to you: **B-3/B-4/B-5** (plan 9 C3(c), C6(a), C6(b)) corrected cells that named
**one** mutation site where **two** are required — at the discovery predicate alone the mutant is
`EQUIVALENT` because the F5 ladder's frozenset check absorbs it; **B-8** (plan 10 C5(b)) replaced a
predicted failure mode that was simply wrong; **B-6** corrected plan 9 C8(c)'s file reference.

I also ruled, before the tester ran, that **plan 9 C8(c)'s `stock_task_assignment:updated` is not
a registered kind** and the row is satisfied by `:state-changed` (plan 9 §7). The owner's cell text
is deliberately unedited — amending a criterion row is the owner's — so **do not report the code
as wrong there**.

## Where your budget buys something new

**The tester states what it did not spend (its §11), and one item there is the single best use
of your budget:**

> **No independent re-derivation of the guard's 85-site registry.** It proved the collector
> observes six planted things, but **not that it misses no seventh class.**

That guard is load-bearing far beyond its own rows: by the implementer's own §6, plan 10
**C1(b), (c), (d), (f), (i), (j), (l)** are proven **only** by it — S1's `HC-4` sibling and
S2/S3/S7/S9 were never driven end-to-end through their own commands. **If the AST collector has a
blind spot, seven rows are resting on nothing**, and neither prior session looked. That is exactly
where your budget buys something no one else bought.

Also unspent: no second mutant shape of the same sign anywhere; no `TZ`/locale/worker-count
variation; no HTTP-layer coverage; no `remove_task_steps` path; no repetition of the C5 rows.

**The tester's own results, for calibration:** 76 declared == 76 executed (83 runs), **zero
production defects**, and **five rows that could not fail, all repaired** — plan 9 C3(c) (one of
three sub-cases built, and the cell's mutation bites only the skipped one), C4(c) (a stale
identity map under `expire_on_commit=False` made the task write invisible, so the mutation
reddened a different assertion), C1(e)'s API-key twin (a second sufficient cause), plan 10 C6(a)
(no `credited_user_id` in the fixture at all) and C1(g)/C1(h) (wrong pre-states). **The repairs are
where a newly-inert mutation would hide** — sample them.

Standing leads for this batch, independent of what the handoffs say:

1. **Plan 10's three C5 rows are this batch's hard evidence, and the likeliest place for a row
   that cannot fail.** They assert three serialization orders forced by a **referee** session
   that holds the row's `FOR UPDATE` while each participant's command is observed to block;
   Postgres then queues the waiters in arrival order. The precedent is `test_apply_stock_demand.py:821-867`.
   **The two observed blocks are assertions, not setup** — a C5 test that does not observe both
   has not forced its order, whatever it asserts afterwards. The B1 lesson is exactly this shape:
   a lock test that ran inside one transaction and could not fail. Check that each C5 mutation
   reddens **deterministically**, not once.
2. **Rule 16 makes several rows inert if production spells its states out.** Both plans carry
   rows whose named mutation *is* a hand-typed state list. If the real code does not use
   `ACTIVE_ASSIGNMENT_STATES` / `TERMINAL_ASSIGNMENT_STATES`, those mutations prove nothing even
   though they redden.
3. **Two rows are UNFAILABLE BY DESIGN by owner ruling** — plan 10 C2(a) and C7(b) — and **three
   are deliberate class-2 blanks** — plan 10 C4(a) (the guard's control row) and plan 9 C2(a) and
   C2(d) (both landing on one shipped guard at `stock_demand_request.py:34`). The rulings are
   settled; **do not re-litigate them.** Do check they were applied to the right rows, which is a
   different question, and check that the *real* evidence each cell names actually exists.
4. **Plan 9 C8(b)** stays `UNFORCEABLE` with a structural check (§9 rule 9). Judge whether the
   structural check honestly discharges what the row promises.
5. **Plan 9 C8(c) is §9 rule 18's second instance** — it pins `resolve_processed_group`'s callable
   contract and returned event kinds. It is deliberately **not** a second copy of the webhook's
   behavioural coverage; if it has become one, that is over-verification and a `verification`
   finding.
6. **§10 — `client_id` order is not creation order** (ULIDs, no monotonic counter; 977 of 1999
   consecutive pairs measured out of order). Plan 9 groups and orders rows. A test that assumes
   insertion order passes by luck, and any mutation against an order it never established is
   inert. This is a cheap, high-yield thing to grep for.

**Sample the dispositions that can hide a row that cannot fail** — `ARMED-SHARED`, `EQUIVALENT`
and `UNFORCEABLE`. That is where "the same code edit arms both rows" gets asserted rather than
measured (§9 rule 8).

## What this batch is also measuring

Batch C1 was the tester role's first run: **103 mutations, zero production defects, eleven rows
that could not fail.** The reviewer then found **two real production bugs** by going *past the
rows* to the ratified authority — and one was a **missing row**, which the tester structurally
cannot find.

That is the division of labour, and it tells you where your budget is worth most: **the rows are
already the tester's job.** Yours is the authority the rows were derived from. Read §14F and the
MC contracts and ask what they promise that no row in either plan asks about.

## Owner rulings binding on this review

Five cards were ruled at the C2 projection, 2026-09-21 (`13a3e14`). Settled — check application,
not merit:

- Plan 9 **C7(b)** re-stated to the observable grouped outcome (both affected rows end at their
  expected zero counters, each emits exactly one update event). It must **not** assert the number
  of SQL `UPDATE` statements or runtime row ordering; ascending `client_id` lock ordering stays a
  structural invariant verified by the existing structural criterion. **A test asserting statement
  counts here is a finding.**
- Plan 9 **C8(c)** authored (card 5) — the rule-18 pin described above.
- Plan 9 **C3(g)** gained the echo clause; plan 9 §6 gained the quantity preamble (where a row
  says `q = n`, the fixture sets item I's `quantity` to `n` before `CR`; **F0's default is 4, not
  the 8 some C4 rows assume**).
- Plan 10 **§6 gained the referee-lock choreography** and its three C5 fixtures/mutations were
  rebuilt (cards 3 and 4).
- Plan 9 §4 gained `_move_assignment.py` and `enums.py`; both plans gained a §7 bullet authorising
  named mutations in approved phases' files.

Also new since C1: §3B's rule that **a ruling adding an assertion must reach the tester or it is
paperwork** — earned because C1 folds landed behind a handed-over tester and surfaced as findings
S2/S3. If you find a ratified clause in either plan with nothing proving it, check the fold date
against the tester's dispatch before routing it: it may be this failure mode, which routes `plan`
and is the orchestrator's, not the implementer's.

## Deliverable

Your handoff at `SR/handoffs/reviewer/2026-09-21_batch_C2_review_1_handoff.md`, per your closing
protocol: per-row PASS / FAIL / NOT_VERIFIED for every row in both plans, the verdict
(`APPROVED` / `CHANGES_REQUESTED`), findings each with a `route` — `production` (code wrong) ·
`verification` (code right, proof weak, missing or excessive) · `plan` (row ambiguous,
contradictory or unprovable) — notes, and owner cards under `⚠ OWNER DECISIONS REQUIRED (n)`.

**Over-verification is a finding too.** If the tester spent budget where a row did not ask for it,
route it `verification` and say so; the role is being calibrated and a silent pass teaches nothing.

You fix nothing. Never push. If you run a probe in production code, revert it and show the file
byte-identical.

Report what you did not check, plainly. Every prior session in this project did, and it is why
this prompt can point you at something useful instead of everything.
