---
batch: D1
phases: [12, 13]
role: implement
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Opus
---

# Batch D1 implementation — phase 12, then phase 13

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/implementation-executor.md` — **including "When the project
  runs a tester", which narrows your job. Read that section before Task 0.**
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Read in order: `SR/master_plan.md` (**§3B first**, then §6 in full, §9's 19 standing rules, §10),
then `SR/plans/plan_12.md`, then `SR/plans/plan_13.md`. The intention is `SR/planning/intention.md`
— **RATIFIED**, and it wins over any plan. Check its `status:` header before you start; stop on
anything but `RATIFIED`.

**This is the last batch of a sixteen-phase project.** Phases 1–11 and 8A are APPROVED and
VERIFIED. Only 12, 13, 13A and 14 remain, and D2 (13A + 14) cannot start until this batch is
APPROVED. You are being run unattended, overnight, with the owner asleep.

## This project runs a tester. Your job is narrower.

A separate Opus verification engineer runs **after you and before the reviewer**. **These move to
it and you skip them entirely:**

- Task 0's row-level coverage map, in both directions;
- closing step 1½ — the named mutations and `executed == declared`;
- closing step 1¾ — proving each guard able to fail;
- the named-mutation ledger in your handoff.

**Do not run a single mutation. Do not transcribe the criteria tables into tests row by row.**

**What stays yours:** make the planned behaviour true; the tests you find *useful to build it*
(red → green, outcomes at a public boundary); the existing regression suite; lint and type checks;
closing steps 1, 2, 3, 4, 5; the Review log; the graph delta; rule 17's contradiction check.

**Do not pad the test files to look covered.** Naming a long list of rows you did not exercise is
exactly right and costs the round nothing. A weak test that *looks* like coverage costs a review
round.

## Scope and order

**Phase 12 first, then phase 13** (13 `depends_on: 12, 8`). Phase 13 may start once phase 12 is
implemented with its L1 tests green — it does not wait for a review. Phase 13 consumes phase 12's
`close_priority_gap`, so build 12's `_ordering.py` properly before you start 13.

Everything outside the two plans' §4 file lists is **APPROVED code: you call it, you do not change
it** — with the two explicitly authorised exceptions in the next section. If you believe any other
approved file must change, **stop and report** — that is an owner decision.

## Your test slot — set it on every pytest command

> **Set `BEYO_TEST_SLOT=d1` on every pytest invocation**, not just the L4. `pytest.ini` carries
> `-n 6 --dist loadfile`, so even a single-file run claims six worker databases. The slot gives
> you your own set (`beyo_test_d1_gw0…gw5`) and its own template:
>
> ```
> cd app && BEYO_TEST_SLOT=d1 PYTHONPATH=. pytest <file>
> cd app && BEYO_TEST_SLOT=d1 PYTHONPATH=. pytest -m 'not e2e'
> ```
>
> The first run in a fresh slot builds its template at the Alembic head, so it is slower once.
> Omitting the variable silently shares the default slot and makes the result worthless while
> looking like genuine failures. The orchestrator is on slot `d0` and may run a suite while you
> work.

## Two authorised touches of already-approved code — and nothing else

Both are registry-ordered, not your judgement. Name both in your handoff under their own heading
so the reviewer's perimeter check does not read them as violations.

### 1. `_row_values.py` — create it, and replace exactly three copies (master plan §6.5, ledger D-6)

§6.5 registers `bm/services/commands/stock_report/_row_values.py` → `row_values(row) -> dict` to
**phase 12**, and says in the same row: *"Phase 12 creates it and the three existing copies are
replaced by it in the same act."*

The three copies are byte-identical private `_row_values` functions, and I verified they are
exactly three:

- `bm/services/commands/stock_report/create_stock_task_assignments.py:56`
- `bm/services/commands/stock_report/sync_task_stock_assignments.py:36`
- `bm/services/commands/stock_report/delete_stock_task_assignments.py:34`

Replace those three with imports of the shared helper. **Behaviour-preserving, byte-for-byte
equivalent output.** Those three modules' tests must stay green with no edits to them — that is
your proof the replacement was inert, and the reviewer will check it.

**The trap the registry states, and it is real:** `row_values` must emit `priority` as
**`.value`, never the enum member** — the coalescer compares this dict against the post-state, and
an enum member compared against a string never matches, so an unchanged row would emit a spurious
`:updated`. All three copies already do it right (`row.priority.value if row.priority is not None
else None`); preserve it exactly.

**Do NOT touch a fourth site.** `repair_stock_report.py:325-331` builds the same six keys inline
inside an event `extra=` (and with a truthiness test rather than `is not None`). It is **not** one
of the three copies the registry names, it belongs to APPROVED phase 3, and tidying it is out of
perimeter. If you think it should be folded in, say so in the handoff as a note; do not do it.

### 2. Nothing else. There is no second one.

Listed as a heading so you notice its absence. Phase 13's §4 was corrected by owner card 5:
`bm/domain/stock_report/serializers.py` is **not** in phase 13's perimeter (all three compact
serializers already ship in phase 8) and `requests/__init__.py` is **not** either (DELETE takes no
body). A change to either from phase 13 is a review finding.

## The five things most likely to cost this round

Ranked by what the projection and the previous batches actually found.

### (a) `stored_before` must come from a fresh `SELECT`, and nothing in phase 13 can catch you

Plan 13 task 1 (ii)/(iii) and C2(b). Two separate places in the cascade must read from the
database rather than from the ORM instance loaded at the lock:

- the **counter repair's `stored_before`**, taken after the guarded statement returned zero rows;
- the **gap close's `removed_order`**, taken as a fresh `SELECT` of the row's `priority_order`.

C2(b) arms the first one. **Nothing in this phase arms the second.** Its only armed evidence
anywhere is phase 13A's C5(b), and 13A's perimeter forbids editing this module — so it has to be
right when you ship it, which is the whole reason batch D was split and why D2 waits for D1's
approval. Write it as a fresh `SELECT` and say in your handoff, in one line, that you did and
where.

### (b) The cascade takes every stamp value from its arguments, never from `ctx`

`cascade_delete_stock_report_item(session, row, *, workspace_id, actor_user_id, now, trigger)`
has **two callers**: this phase's command (`actor_user_id=ctx.user_id`,
`trigger="delete_stock_report_item"`) and phase 13A's webhook (`actor_user_id=None`,
`trigger="stock_demand_deleted"`). A cascade that reaches for `ctx` cannot serve its second caller
and D2 will fail on it. The `None` path is **not** exercised by any criterion in this phase — no
test here will catch it. Write it correctly; do not import `ctx` into the module.

### (c) Rule 17 — the request models, measured on the installed pydantic 2.11.3

Plan 12 C1(m)/C1(n) and §7. These are decidable only if the models are declared exactly right:

- `priority_order` must be **`StrictInt`** (or the model strict). A plain `int` coerces the string
  `"2"` to `2` in lax mode, C1(n)'s 422 disappears, and the row is worthless.
- `priority` is `StockReportPriorityEnum | None` **with no default**, so an omitted key is itself a
  422 and `"urgent"` is rejected by value.
- **Only `bm.errors.validation.ValidationError` yields a 422.** A pydantic error escaping the
  command becomes a **500**. Both models therefore need the registered parse wrapper —
  `parse_set_stock_report_item_priority_request` and
  `parse_set_stock_report_item_priority_order_request` (§6.5, ledger D-2/D-3) — which catches
  pydantic's error and re-raises ours. These are the names §9 rule 18 pins.

### (d) `client_id` transport — follow the shipped precedent, do not invent one

§6.5 ledger D-2: the router injects it exactly as phase 8A's shipped route does —
`incoming_data={**body.model_dump(), "client_id": client_id}`
(`bm/routers/api_v1/stock_report.py:141`) — and **both service-side models declare
`client_id: str`**. This was verified necessary at the site: 8A's model carries `extra="forbid"`
alongside `client_id: str`, so a service model lacking the field would 422 every request.

### (e) `client_id` order is not creation order (§10, measured)

ULIDs carry no monotonic counter; 977 of 1999 consecutive pairs sorted out of order. Every
`ascending client_id` lock order and every ordered assertion must **sort the real ids at
runtime**. Both plans' §6 preambles deliberately seed groups whose `priority_order` ascending
**disagrees** with `client_id` ascending — that is a fixture requirement, not an accident, and a
gap close that renumbers by `client_id` must be unable to pass.

## Standing rules that bite here

- **Rule 3** — a Core `UPDATE` in the same transaction leaves the ORM instance stale. This is (a)
  above, and it is the batch's signature hazard.
- **Rule 7** — `count_writes` on the four tables is the no-op proof (C1(c), C1(k), C1(l)). L-26 is
  **already discharged** for this instrument (plan 12 §7): it was measured capable of returning
  non-zero on 2026-09-21. Do not re-buy that observation.
- **Rule 16** — `ACTIVE_ASSIGNMENT_STATES` / `TERMINAL_ASSIGNMENT_STATES`, never a spelled list.
  Plan 13 C4(a)'s second mutant **is** a hand-typed five-state list, so real code that spells the
  list out makes that row inert.
- **Rule 17** — relocating a row's proof to a narrower surface is the **owner's**. Declare and
  stop.
- **Rule 18** — every public signature you register in §6.5/§6.1 must be pinned by a row in your
  own plan.
- **Rule 19** — new test file names must be unique across the **whole** test tree; bare filenames
  are module names here and a clash is a silent collection error. Plan 12 §4 already renamed two
  files for exactly this reason — use the names as written
  (`test_stock_report_priority_and_ordering.py`, `test_stock_report_ordering_locks.py`).
- **§5** — the list endpoint is **exempt** from the `07_queries_local` pagination gate by ratified
  owner answer. Do not add `_pagination`.

## Three things to report, not to decide

These came out of the projection after it closed. Each is the orchestrator's or the owner's, not
yours. Do the work; report the fact.

1. **Where you build `stock_report_item:deleted`.** Plan 13 does not say. §6.5's `_events.py`
   registers only the `:updated` and assignment builders, and `stock_report_item:created` is built
   inline in `apply_stock_demand.py`, so either shape has a precedent. **Pick one, and state the
   exact `file:symbol` in your handoff under its own heading** — the coordinator registers it in
   §6.5 in the same act (§9 rule 18), and plan 14's accuracy guard has to be able to find it. Do
   not edit §6.5 yourself.

2. **`PATCH …/priority-order` has no tenancy criterion.** Plan 12 C1(o) covers foreign /
   soft-deleted / absent for the **priority** route only; there is no equivalent row for
   priority-order. The lookup is shared, so make the behaviour identical on both routes — but
   **you owe no test for it and must not author a row.** Say in the handoff which lookup both
   routes use, so the orchestrator can propose the cell text to the owner.

3. **Rows that cannot fail, already labelled.** Plan 12 **C2(a)** and **C2(b)** are class-3 rows —
   the interleaving is unforced and no mutant can force them. They are invariant checks. **C2(c)**
   is the only deterministic proof that the advisory lock is taken, and it does not cover the
   density-under-a-real-race half. Do not try to make (a)/(b) bite, and do not weaken (c).

## The one row the owner will check personally

Plan 12 **C4(e)** — `serialize_stock_report_item`'s `item_category` block is **four** keys:
`client_id`, `name`, `major_category`, **`image_url`**.

`ItemCategory.image_url` is `Mapped[str | None]`, `String(1024)`, nullable
(`bm/models/tables/items/item_category.py:23`). On a row whose category has no image the key must
be **present and `None`, never absent** — an omitted key and a null key are different things to a
renderer, and the frontend contract published today (`SR/handoffs/to_frontend/
HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md`) states it as `string | null`.

This was added by the owner on 2026-09-21 and folded into this phase rather than patched on
afterwards. C4(e) carries a **second fixture row with a NULL category image** and a **third
mutant** that drops the key. Build the fixture so both cases exist.

## Environment

**Starting HEAD: `fa301fd`** (docs only since the batch C gate). **Baseline for your arithmetic:
23 failed / 3679 passed / 1 skipped** — measured by the orchestrator on slot `d0` at exactly that
HEAD, immediately before this prompt was written. The full 23-ID set is checked in at
`SR/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`; diff against that file.

> **The gate is 23 failures, not 21.** §10's published baseline is the 21-ID set measured on the
> default slot; under any named slot these two `test_database_isolation.py` IDs go red as well:
>
> ```
> tests/integration/infrastructure/test_database_isolation.py::test_worker_name_resolution_uses_xdist_worker
> tests/integration/infrastructure/test_database_isolation.py::test_worker_name_resolution[None-None-beyo_test_main_main]
> ```
>
> That is a known, owner-acknowledged environment property, not a regression, and the 23-ID set is
> your comparator. The published 21 are in
> `docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3.

**The invariant is the failure-ID set, not the pass count.** Diff your failure IDs against the
23-ID set in **both directions** and print both. The pass count rises with every batch and is
never itself the comparator — but **reconcile its arithmetic exactly** (`3679 + <the tests you
added> = <your total>`) and show the sum. One inherited drifter is known
(`test_c3_real_concurrent_open_insert_translates_the_loser[model]`, load-dependent); capture the
ID set before repeating an anomalous run.

**Budget:** L1 as you go, one L2 per phase, **exactly one L4** at the very end. Nothing else.

## Your handoff — the tester contract

`SR/handoffs/implementer/2026-09-21_batch_D1_implement_1_handoff.md`:

1. **Checkpoint SHA per phase**, on a clean tree (`CHECKPOINT (not approved): …`).
2. **The one L4 stamp**, both ID diffs printed, pass-count arithmetic reconciled against 3679.
3. **The production write perimeter** — every file created or edited, explicitly, with the
   `_row_values` replacement called out under its own heading as authorised by §6.5 ledger D-6.
4. **"Tests I wrote → the row each aimed at"**, as *claims*, not evidence.
5. **One load-bearing pointer per criterion** — the `file:symbol` where the behaviour is made
   true. The tester needs these most and cannot cheaply find them:
   - where the advisory lock is taken, and where the group `FOR UPDATE` is taken, in each of the
     three commands;
   - where each shift statement's `RETURNING` is consumed into events;
   - the **two fresh `SELECT`s** in the cascade (counter `stored_before`; gap-close
     `removed_order`);
   - where the `X == Y` / `t == p` short-circuits sit relative to the record insert and the event
     build;
   - where `stock_report_item:deleted` is built.
6. **Rows you know you did not exercise.** Name them plainly.
7. **Any place a test would need a seam the production code does not offer.** Say so rather than
   improvising a variant — the last batch's concurrency rows failed exactly here.
8. Judgment calls, deviations, anything you found wrong in the plans.
9. Owner questions under `⚠ OWNER DECISIONS REQUIRED (n)`.

**Report what you could hide.** Every session in this project's overnight runs has self-reported
something costly — a false green caught in its own draft, a count that did not close, an arming
that only partly bit. That is the norm here, and it is worth more than a clean-looking handoff.

## Stop conditions

Both phases implemented per their plans · every test you wrote green · L2 green per phase · one L4
reconciled with both ID diffs · lint and type checks clean · Review logs written in both plans ·
handoff complete · both checkpoints committed **with explicit paths, never `git add -A`** (another
session may be writing into this tree) · **never push**.

**Not reasons to continue:** a coverage figure; a mutation you thought of; a test for a row you
were not asked to exercise; tidying outside the perimeter.

If you hit a contradiction, an unbuildable fixture, or a required file that does not exist —
**stop and report it as a card.** Eight such problems were found and ruled before you started;
finding a ninth is a good outcome. Improvising past one is the expensive failure.
