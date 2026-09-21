---
batch: C2
phases: [9, 10]
role: projection
round: 0
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Opus
---

# Batch C2 projection + lesson fold — plans 9 and 10

Follow the `plan-projection` skill and `/Users/davidloorenz/agent-skills/pipeline-charter.md`;
read both by absolute path first. This prompt frames the session — **where it and a plan file
differ, the plan file wins.**

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
HEAD at dispatch: `798fc69`. Batch C1 is **APPROVED**; phases 1–8 and 11 are VERIFIED and shipped.

## Scope

**Plans 9 and 10 only.** Plan 9 = the Scanner "items processed" webhook (§14F F5 order, the
`early` reason, grouped counter updates, replay, one owning transaction). Plan 10 = task-state
sync at nine write sites, the registry guard, and three two-writer interleavings. Inside C2,
**10 depends on 9**. Plans 8 and 11 are closed — do not fold them; anything wrong there is a note.

Read master plan **§3B** in full before acting on anything else in this prompt, then §6, §9
(19 standing rules now), §10 (environment), §9A (the lesson register).

## Task 1 — the mutation-cell classification

Master plan §3B's amended *Mutation cells* bullet is the specification: each empty (`—`) cell is
**plan-determined** (fold it), **site-undetermined** (leave `—` **with a one-line note that the
blank is deliberate**), or **reveals a defect** (fixture folds to the orchestrator; outcomes and
new rows are owner cards).

A prior pass classified these plans before any of batch C existed. **Treat it as a hypothesis,
not fact** — Appendix A below. Expected: plan 9 has **18** empty cells (15/2/1), plan 10 has
**15** (13/2/0). Verify the counts yourself by script and report what you measure.

For every class-1 proposal, **open the file the site names and confirm the symbol is really
there and executes under this row's own fixture** (L-31). Phases 1–8 and 11 are shipped, so most
sites are real code you can read. Correct or demote anything that does not hold.

Two cautions this batch paid for:

- **A cell naming a site that was never written costs a round.** That happened on plan 8 C5(b) —
  the cell named a `sorted(...)` in a file that delegates to a shared helper. Prefer demoting to
  class 2 over guessing.
- **The prior pass got 3 of 34 wrong at the site** on plans 8/11 — one named a symbol not there,
  one named the wrong file entirely and would have crashed the suite rather than proving
  anything. Assume a similar rate here.

**You edit no plan file.** Output a patch table; the orchestrator applies it (§3B, L-20).

## Task 2 — plan 10's three two-writer rows, and a fixture defect they would inherit

**This is the most valuable thing this session can do.** Read it before you plan your time.

Plan 10 C5(a), C5(b) and C5(c) are the three MC-11 / §14F F6 serialization orders, and §3B says
they are *exactly* phase 10's concurrency evidence — no interleaving, repetition or thread-count
variants are to be added. Each is forced by lock acquisition and armed by removing the post-lock
re-read or deciding on the pre-lock value.

**Measured in batch C1, 2026-09-21:** plan 8 C5(a)'s two-session race fixture **does not force
its race**. The item lock was removed and the test stayed **green 9 runs out of 9**, at two
independent mutation sites plus a 50 ms-pause diagnostic. Cause, from the query log: session A
(`db_session`) holds an already-warm connection while session B's connection opens **lazily on
its first statement, after the barrier** — so A wins by scheduling every time and B's pre-check
never runs before A commits. The row demonstrates nothing about the lock (§9A L-29: a fixture
that models an environment cannot fail). The owner accepted that as a known gap for plan 8.

**The pattern is shared.** Plan 8's race file states it was copied from
`test_apply_stock_demand.py`'s C5 tests (phases 6/7, APPROVED), and those use the same
`get_db_session()` → `barrier.wait()` shape with no warm-up. Plan 10's three rows will inherit it.

So: **determine what plan 10's C5 rows must say so they actually force their orders.** The
hypothesis to test by reading — not by running, you run nothing — is that forcing B's connection
open **before** the barrier (e.g. `await session2.execute(select(1))`) removes the asymmetry.
Propose the fixture-cell text that pins it, for all three rows. If you conclude the asymmetry is
*not* the cause, say so and say what is; that is at least as useful.

Also state whether you believe each of the three orders is genuinely forceable, or whether one
should be honestly `UNFORCEABLE` with a structural check — §9 rule 9 requires that a row which
cannot force its interleaving says so rather than pretending.

## Task 3 — the lesson fold (§9A)

Fold only rows §9A marks foldable **and** whose Targets name plan 9 or plan 10. From the
register those are: **L-9, L-10, L-11** (plan 10's AST registry guard C4(a)–(g) specifically),
**L-12, L-13, L-15, L-17's preamble half, L-19, L-24, L-25, L-26, L-28, L-30.**

Owner-only — **draft as cards, never fold**: **L-1** (enumerate, never sample — targets 9),
**L-3** (task text contradicting its own criterion — targets 9), **L-22** (no `≤` on a derived
count — audit 9), **L-17's outcome half** where an outcome is arithmetically wrong.

Already standing rules, do not re-fold: L-8 (§9 rule 18), L-20 (rule 17), L-21/L-23/L-28's
cluster (rule 8's amendment).

## Task 4 — the standing projection checks

Every cited path exists; every cited contract, registry signature and §6.5 name exists and
matches; task text does not contradict its own criterion; fixtures are constructible under the
rules the plan itself imposes; rule-17 externally-derived fixtures re-grounded against the real
dependency.

Specifically for these two plans:

- **Perimeter extensions.** Enumerate every out-of-perimeter file a named mutation must touch and
  propose an explicit §7 declaration, as plan 8 §7 now carries. Batch B2 lost a round to seven
  mutations declined for living in an approved phase's file, and batch C1's tester probed
  `criteria_matcher.py` with no declaration covering it.
- **Foreign load-bearing sites** go in master plan §6.1b — propose the row.
- **§10's `client_id` fact:** ids are ULIDs with no monotonic counter (measured: 977 of 1999
  consecutive pairs out of order). Plan 9 groups and orders rows; any cell assuming creation
  order is a defect. Check every ordering claim in both plans against this.
- **Rule 16:** the two frozensets, never a spelled list. Both plans carry rows whose named
  mutation *is* a hand-typed list — verify those still name the real site.
- **Rule 19:** any new test file needs a name unique across the whole test tree.

## Deliverable

One file: `SR/handoffs/projectionist/2026-09-21_batch_C2_projection_handoff.md`, frontmatter
(`batch: C2`, `phases: [9, 10]`, `role: projection`, `round: 0`, `state`, `date`, `actor`), with:

1. **Counts**, measured by script, command shown.
2. **The patch table** — `| Plan | Row | Cell | Current text (verbatim) | Proposed text (verbatim)
   | Class | Lesson(s) | Site verified? |`. Current text copy-pasteable so it can be applied
   mechanically. For class 2 the proposal is the deliberate-blank note.
3. **Plan 10's C5 rows** — your conclusion from task 2, with proposed fixture text.
4. **Class-3 rows in full** — defect, minimal fix, whose authority.
5. **Owner cards** under `⚠ OWNER DECISIONS REQUIRED (n)`, with proposed text ready to ratify.
6. **Perimeter extensions and §6.1b entries** as proposed text.
7. **Blockers**, ranked.
8. **What you did not check.**

## Boundaries

Read-only on plans, master plan and source. **You write exactly one file: your handoff.** No
commits, no `git add`. **Run no tests and no mutations** — another agent is working in this repo
concurrently and a suite run would collide with it on the fixed test-database names
(`beyo_test_main_gw0…gw5`, §10). Checking that a site exists means *reading* the file.

Do not re-litigate phases 1–8 or 11; they are APPROVED. Anything wrong there is a note, never a
blocker on C2.

Report plainly what you could not verify. A stated "unverified" is worth more than a confident
wrong cell, because the cell is binding.

## Appendix A — prior classification (hypothesis; verify)

### plan 9 — 18 empty cells: 15 class 1, 2 class 2, 1 class 3

Class 1, proposed mutations:
- `C1(a)` delete the verifier call at the head of `process_items_processed` (task 2 step 1) → no `x-api-key` proceeds to 200
- `C1(b)` in `infra/location_tracker/webhook_verifier.py`, replace the key equality with a truthiness test → wrong key returns 200
- `C1(c)` delete the MC-8 step-4 workspace `SELECT`/existence refusal → proceeds, 200 with `item_not_found`. *Caveat: if "names no workspace" means a blank setting rather than an unknown id this collapses into C1(e) and the 401 alone is mutation-equivalent — rule on it*
- `C2(c)` drop the per-entry `isinstance(entry, dict)` shape check in `parse_items_processed_body` → a bare-string entry crashes (500) instead of a collected 422
- `C2(f)` drop the non-blank/`.strip()` validation on `article_number` → `"  "` returns 200 `ignored/item_not_found`
- `C2(h)` raise on the first malformed entry instead of collecting → the message names index 0 only
- `C3(a)` delete the `item_not_found` branch of the F5 decision → an unmatched number reports `no_open_assignment`
- `C3(b)` swap the ignore-reason literal: report `item_not_found` when the item exists but has no active assignment
- `C3(e)` narrow the early path to `in_queue` only (drop `in_progress` from the F5 active set) → `ignored/no_open_assignment`
- `C3(g)` drop the `.strip()` when building the match set → `" SR-x "` reports `item_not_found`. *The row omits the echo-as-received clause task 1 mandates — flag it*
- `C4(b)` drop the `stock_report_item:updated` event from the per-row `RETURNING` step → only the assignment event is dispatched
- `C4(e)` skip the F4 goal credit when the source state is `in_progress` (credit only from `in_queue`) → `G == 0`
- `C5(b)` decide the duplicate second entry on the pre-request snapshot instead of the post-move re-read → second result `resolved/early` and `−q` applied twice
- `C6(a)` widen assignment discovery to all non-deleted assignments (drop `state IN ACTIVE_ASSIGNMENT_STATES`) → the replay re-resolves and writes
- `C6(b)` drop `resolved_early` from the terminal exclusion (hand-typed active set) → the second delivery re-credits `G`

Class 2: `C2(a)` (whether "top-level list" and "≥ 1 entry" are one guard or two is an
implementation choice; if two, removing the shape check still lands `{}` on the non-empty check →
equivalent), `C2(d)` (the missing-key and non-blank-string defects are probably the same guard;
a separate required-key site may not exist).

Class 3: `C7(b)` — the outcome is stated as internals ("two `UPDATE`s on `stock_report_items`,
rows ascending"). The identical clause was stripped from siblings C7(a)/C7(d) by the owner ruling
of 2026-09-19 ("outcomes, not internals"), so this row survived a ruling it should have been
folded into; and "rows ascending" is a 2-element ordering claim whose fixture never fixes which
of R/R2 sorts first (and see §10 — ids are not creation-ordered). Proposed: owner re-statement as
an outcome, with the single ascending lock statement verified structurally as C8(b) already
declares.

### plan 10 — 15 empty cells: 13 class 1, 2 class 2, 0 class 3

Class 1, proposed mutations:
- `C1(b)` set the `ready` cell of `ASSIGNMENT_STATE_BY_TASK_STATE` to `in_progress` → kills state, `(0,0,4)` and `G == 4`
- `C1(d)` delete the `sync_task_stock_assignments` call from `tasks/force_task_ready.py` (S3) → A stays `in_queue`
- `C1(g)` delete the call from `tasks/fail_task.py` (S5) → A stays `in_progress`, counters `(0,4,0)`
- `C1(h)` delete the call from `tasks/cancel_task.py` (S6) → A stays `in_queue`
- `C1(i)` remove the `state == target → skip` short-circuit (MC-2 step 5) → the no-op move emits a stock event (same mutant as C1(f))
- `C1(j)` delete the call from `task_steps/add_task_steps.py` (S7) → A stays `awaiting`, `G` stays 4
- `C1(k)` delete the call (and its event-tuple append) from `task_steps/remove_task_step.py` (S8) → A stays `in_progress`
- `C1(l)` pass `actor_user_id = ctx.user_id`/`None` instead of `payload["performed_by_user_id"]` at S9 → `updated_by_id` wrong
- `C3(b)` replace the `state in TERMINAL_ASSIGNMENT_STATES` skip with a hand-typed `state == resolved` test → the `failed` assignment is moved to `in_queue`
- `C3(d)`, `C3(e)`, `C3(f)` drop `resolved_early` from `TERMINAL_ASSIGNMENT_STATES` (hand-typed `{resolved, failed}`) → the sync moves it to `failed`/`failed`/`in_queue`. *One mutant, three rows; C3(c) already names it — L-28 applies, show it reaches each row's own distinguishing assertion*
- `C7(c)` pass a different `trigger` at the sync's `move_assignment` call → repair record trigger ≠ `inline:task_sync`

Class 2 (both borderline): `C4(a)` (control/absence row; the only mutations edit the guard's
collector or the registry, i.e. test-side data, and project policy treats an absence claim as an
L4/structural check), `C7(b)` ("no stock event dispatched when the command raises" is enforced by
the pre-existing command's dispatcher/transaction scope, not by a line this plan adds — the sync
sits after the last state write and never runs, so C7(a)'s mutant leaves this row green; **the
row may be unfailable — judge it**).

Note from the prior pass: every "delete the sync call" mutant is *also* killed by the C4 registry
guard, so those rows overlap C4(f) — a double kill worth recording per L-28.
