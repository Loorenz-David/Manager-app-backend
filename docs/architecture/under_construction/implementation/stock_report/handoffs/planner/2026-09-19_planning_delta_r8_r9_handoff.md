---
plan: master_plan.md + plans/plan_1.md … plan_14.md, plus new plans/plan_13A.md (planning delta over the round-7 set)
role: planner (implementation-planner) — planning delta
round: planning-1 (fold intention rounds 8 and 9)
date: 2026-09-19
state: DONE — delta folded; zero owner cards; the plan set awaits the owner's review before phase 1's projection is dispatched
actor: Claude Fable 5.1 (pipeline-planner agent, orchestrated mode; launched by the coordinator)
---

# Planning delta handoff: `stock_report`, intention rounds 8 (§14E) and 9 (§14F)

## Opening summary

Gate check passed on all three lines at tree `c231dfb`: the intention header reads `status:
RATIFIED … round 8 (§14E) and round 9 (§14F …)`, round 9, and §18 carries the owner's round-8
("about the card 12: A . card 13: A …") and round-9 ("about card 14 : "A" is correct …")
re-ratification entries; `git status --porcelain` on the intention and the Scanner handoff printed
nothing and `git log -1 --format=%h -- planning/intention.md` is `c231dfb`; `master_plan.md`,
`plans/plan_1.md` … `plan_14.md` and the previous handoff exist, untracked.

The delta is folded, not rewritten. **Round 8** became a new phase file `plans/plan_13A.md` (after
13, depending on 13 and 9; 36 rows in 7 criteria; projection mandatory and not waivable) whose §7
answers the six carried questions of §14E each with a stated rule and a row that can fail. **Round
9** touched the owner's six phases (1, 4, 5, 8, 9, 10) and five more found by searching the set
(3, 6, 11, 13, 14), all listed in §1 with reasons. The plan set is now **616 criterion rows in 98
criteria across 15 phases** (was 532 / 90 / 14), counts derived by script (§1, §5); no phase
exceeds eight criteria; every MC-1…MC-20 and every M1–M9 is served (§5). The retired reason
`not_awaiting` has **zero** hits in the plan set (§4). The plan's wire shapes match the Scanner
handoff §4A, §4.2 and §4.3 exactly; no mismatch between the handoff and the intention was found (§3).

Nothing was committed. Nothing under `app/`, the intention, the Scanner handoff, the inventory
handoffs, the previous planner handoff or any prompt file was touched. No archgraph write, no
database access, no test run (§6).

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner from this session. Card 1 of the planning-0 handoff (which of the 21
baseline failures to fix) stays open and untouched, as the delta prompt instructed.

## 1. Phase plans changed

Counts are derived by the script in §5 (before = the planning-0 tracker; after = this tree).

| File | On the owner's round-9 list? | What changed (row ids) | Rows before → after | Criteria before → after |
|---|---|---|---|---|
| `plans/plan_1.md` | yes | Goal, Read-first, task 1 (six-member enum; the active/terminal partition; rule 16); **added** C1(i)–(j) (the partial indexes exclude `resolved_early`, both indexes), C6(j) (no task state maps to `resolved`/`resolved_early`), **new criterion C7** (a: the two frozensets partition the enum; b: `RESOLVED_EARLY` terminal, not active); new test file `test_assignment_state_enum.py`; note | 48 → 53 | 6 → 7 |
| `plans/plan_3.md` | **no** — the consistency check must neither count the new state nor drop its goal credit (§14F F10–F11); task 1 names the frozensets | **added** C1(l); task 1 text; note. C2(a) untouched | 41 → 42 | 8 → 8 |
| `plans/plan_4.md` | yes | Goal, Read-first (C47 superseded); task 1 now carries the **six-state allowed-move table** (MC-1 + §14F F2) verbatim; **added** C1(s)–(u) (`in_queue`/`in_progress → resolved_early`, `resolved_early → DELETE`), C2(f) (sixth `=` cell), C3(n)–(v) (`∅ → resolved_early`, `awaiting → resolved_early`, every exit from `resolved_early`, terminal → `resolved_early`); **rewritten** C3(d)–(e) trace cells (no longer "§5 r2", which C47 superseded); note | 49 → 62 | 7 → 7 |
| `plans/plan_5.md` | yes | Goal, Read-first (F4, F11, card 14); task 1 (credit on entering `resolved_early` = credit on entering `awaiting`; `resolved_early → DELETE` keeps it); **added** C1(n)–(q), C2(d) (recomputation includes the `resolved_early` credit); **repaired** C3(a)'s merged fixture/outcome cells (a planning-0 table defect, content unchanged); note | 17 → 22 | 3 → 3 |
| `plans/plan_6.md` | **no** — two round-8 consequences: (i) §14E E4 "the same engine as find-or-create" → the category resolution and identity discovery are factored into `_demand_lookup.py` so 13A imports them instead of copying two statements; (ii) §14E carried question (1) exposed a discover-then-lock gap against a concurrent soft-delete that the round-7 set did not cover for the user delete either → task 2 step 6 gained the locked-set assertion (500, Scanner retries) | Files list (+`_demand_lookup.py`); task 2 steps 3, 4, 6; **added** C5(c) (deterministic: a held lock plus an uncommitted soft-delete, then the demand raises `RuntimeError`, nothing written, a retry creates the fresh row); note. C7(a) untouched | 35 → 36 | 8 → 8 |
| `plans/plan_8.md` | yes | Goal, Read-first (F9/P44); task 2 (the reason `already_processed_by_scanner` after `item_not_task_primary`, any row, non-deleted `resolved`/`resolved_early` of the pair); task 4 (the coalescer drops `:updated` for a row `:deleted` in the same request — needed by 13A's multi-row requests, exercised by 13A C5(b)); **added** C1(p)–(u) (the refusal; new task not affected; deleted not counted; both adjacent pairs of MC-13's order), C6(i) (deleting a `resolved_early` assignment moves no counter, keeps the credit); note | 58 → 65 | 8 → 8 |
| `plans/plan_9.md` | yes | Goal, Read-first (C47, C48, C50; v1 §4.2–§4.3); task 2 rewritten to the §14F F5 order with the per-column grouped delta, the goal step per assignment, the task never written, and the grouped entry point renamed `resolve_processed_group`; **rewritten** C3(c)–(f) (no `not_awaiting`; `in_queue`/`in_progress` → `resolved`/`early`); **added** C3(l) (closed vocabulary), C4(d)–(g) (early resolution: counters, goal credit, task byte-identical, events), C5(b) (duplicate after an early resolution), C6(b) (replay after an early resolution), C7(d)–(e) (mixed-state group: one UPDATE; two repair records for two wrong columns); note. **C7(a)'s statement-count clause untouched** (it resolves three `awaiting` rows; round 9 does not force a change; C7(d) is the mixed-state twin) | 33 → 42 | 8 → 8 |
| `plans/plan_10.md` | yes | Goal, Read-first (F3, F5, F6; C49); task 1 (terminal test reads the frozenset); **added** C3(c)–(f) (a `resolved_early` assignment stays put when the task reaches `ready`, fails, is cancelled, reopens to `pending` — M2's round-9 sentence, one row per exit §14F F3 names); **rewritten** C5(b) (reopen-first now ends in `resolved_early` with the goal re-credited, F6); **added** C5(c) (Scanner first while `in_progress`, F6's new row); note. **Registry guard C4 untouched** | 30 → 35 | 7 → 7 |
| `plans/plan_11.md` | **no** — the category guard's "terminal does not block" now has a third terminal state; a hand-typed terminal list would refuse it | task 1 (reads `ACTIVE_ASSIGNMENT_STATES`); **added** C4(i); note (fixture route if 9 is not yet APPROVED) | 26 → 27 | 7 → 7 |
| `plans/plan_13.md` | **no** — the cascade must carry a `resolved_early` credit through (F4), the assignment read must list the state (F10), and the cascade gains a second caller (§14E E5) | task 1 (second caller; stamps from arguments); **rewritten** C1(a) (adds A4 `resolved_early`, `G` 10 → 8; the fixture no longer depends on `PR`, which is phase 9 — plan 13 depends on 12 and 8), C4(a) (lists A4); note. **C4(c) untouched** | 19 → 19 | 5 → 5 |
| `plans/plan_13A.md` (**new**) | round 8 | The Scanner delete webhook: goal, Read-first, dependencies (13, 9), file perimeter (no table/column/migration/reset phase — reviewer-checked), tasks (the owning command with the advisory lock **before** discovery, the shared lookup, sorted locks per class, the cascade per candidate row ascending, deadline), criteria C1–C7, **§7 "§14E carried questions"** (Q1–Q6 → rule → row → status), notes | — → 36 | — → 7 |
| `plans/plan_14.md` | **no** — the docs must carry the third webhook, the sixth state and the new reason; the phase now depends on 13A | Header (`depends_on: 13A, 11, 10`), Goal, Read-first (§14E, §14F F1/F3/F9/F10/P45), dependencies, tasks 1–4; **added** C1(d) (every enum value appears in `states.md` and the handoff); note | 4 → 5 | 2 → 2 |
| `plans/plan_2.md`, `plan_7.md`, `plan_12.md` | no | header line only (`phase: N of 15`); no row changed. Plan 12 was checked: it serializes rows, not assignments, so `resolved_early` does not reach it | 75 / 52 / 45 unchanged | 7 / 7 / 7 unchanged |
| `master_plan.md` | — | Header block (RATIFIED round 9 at `c231dfb`; 15 phases; gate closed); §1 goal; §3 (rule-17 phases incl. 13A); **§4 tracker** (every changed row's counts, the real 13A row replacing the provisional one, totals 616/98/15, a derived trace-coverage paragraph); **§6.1** (six states, the partition, `StockDemandDeletedOutcomeEnum`, `ItemsProcessedReasonEnum` with `early`, the `stock_demand_deleted` trigger); **§6.3** (the timeout governs both stock messages); **§6.4** (the closed reason vocabulary of `StockAssignmentRefused` with `already_processed_by_scanner` in MC-13's order; `StockDemandDeadlineExceeded` shared); **§6.5** (`resolve_processed_group`, `_demand_lookup.py`, `DemandDeleteEntry`, `stock_demand_deleted_request.py`, `process_stock_demand_deleted.py`, the demand locked-set assertion, the coalescer's `:deleted` clause, the cascade's two callers); **§6.6** (third route; "three webhook routes"); §6.8 (new test files); §6.9; §7.1 (13A in the split table); **§7.2** (13A row; 14 depends on 13A; fixture note); **§7.4** rewritten from "gate re-opened" to the delta record; **§9 rule 16** (active/terminal are the frozensets, never a spelled list); one escaped `\|` in the §6.1 `scanner_property_tables.py` row (a planning-0 table defect) | — | — |

Totals: **616 rows / 98 criteria / 15 phases** (planning-0: 532 / 90 / 14). Phases at exactly
eight criteria: 3, 6, 8, 9 (unchanged set); none above.

## 2. §14E carried questions — Q1–Q6

All six live in `plans/plan_13A.md` §7 as one labeled table (Q → rule → row → status), and the
rules are restated inside the tasks the rows exercise.

| Q | Stated rule (short) | Row id(s) | Status |
|---|---|---|---|
| Q1 lock order vs concurrent demand / processed | No cycle: every path acquires MC-1's classes in one global order, ascending within a class (13A and the user delete: 1 → 3 → 4 → 5 → 6; demand: 4 → 6; processed: 4 → 5 → 6; sync: 3 → 4 → 5 → 6). The advisory lock is taken **before** discovery so the discovered live set cannot shrink. The one real consequence — a delete committing while a demand for the same identity waits at its row lock, whose `FOR UPDATE` then drops the row on re-evaluation (PostgreSQL §13.2.1) — is closed by the demand's locked-set assertion: 500, Scanner retries, the retry creates the fresh row (E10). The reverse order is excluded by the sender rule E3 | 13A **C5(a)** (tasks-before-rows, deterministic; the mutation reverses the order and produces a deadlock, SQLSTATE `40P01`); **plan 6 C5(c)** (the demand side) | settled |
| Q2 several rows in one request; two gaps in one group | One advisory lock per request; one sorted lock statement per class covering every candidate row and every row of every touched group; cascades one row at a time in ascending `client_id`, each closing its gap from the positions after the previous cascade; deleted rows keep the order they held at deletion (MC-7 row 10); no `:updated` for a row `:deleted` in the same request | 13A **C5(b)** (`A1 R2 C3 D4` minus R and C → `A1 D2`; exact events), **C5(c)** (across groups with a `not_found` between; request order) | settled |
| Q3 does the D6 statement bound apply? | **No bound on the cascade**, by ratified design (per-assignment `move_assignment(DELETE)`, per-row gap close — MC-16) and because deletes are rare (E1). The **find step** is bounded: it reuses demand's set-based lookup, so 3 and 30 entries of one shape cost the same statements | 13A **C5(d)** | settled — "no bound", reason stated |
| Q4 replay instrument after a self-healed cascade | The first delivery may write `inline:stock_demand_deleted` records; the replay reads `not_found`, issues zero INSERT/UPDATE/DELETE over the four MC-9 tables **plus `stock_report_repair_records`**, dispatches nothing, and the record count is unchanged | 13A **C4(b)** | settled |
| Q5 the MC-20 check after a Scanner deletion | Unchanged definitions; the check returns `[]` for the workspace afterwards (flags false, group dense, no counters, the soft-deleted goal record consistent with its kept credits) and `[]` for an identical foreign workspace the webhook never touches | 13A **C5(e)** (+ `assert_stock_report_clean` at the end of every non-drift row) | settled |
| Q6 workspace reset unaffected | 13A adds no table, column, migration or reset phase (its §4 perimeter names the untouched paths; the reviewer's perimeter check asserts it); the four phase-1 reset phases hard-delete what a Scanner deletion left soft-deleted, repair records included | 13A **C5(f)** | settled |

No question needed an owner card: each answer follows from ratified text (MC-1's lock order, MC-7,
MC-9, MC-16, MC-20, §12A, E1, E3, E10).

## 3. Wire-shape check against the Scanner handoff

Every shape the plan uses, the handoff section it matches, and the plan location.

| Shape in the plan | Scanner handoff | Match |
|---|---|---|
| `POST /api/v1/location-tracker/webhooks/stock-demand-deleted`, header `x-api-key`, same secret and workspace setting | §4A (path), §2 (auth) | exact (master plan §6.6; 13A task 4, C1(a)–(c)) |
| Body: JSON array, ≥ 1 entry, of `{"itemCategory": str, "properties": object}`; `quantityRequested` ignored if sent; empty array → 422; two entries of one identity → 422, nothing deleted | §4A.1 | exact (13A task 2; C1(d), (i), (j)) |
| Category matching exact-then-unique-case-insensitive; identity = category + normalized properties (key order, string-vs-list, trim/lower/dedupe/sort) | §4A.1 → §3.1.1, §3.3 | exact (13A C2(a)–(e), via `_demand_lookup.py` and MC-3) |
| Response `{"data": {"results": [{"itemCategory", "properties", "outcome"}]}, "ok": true, "warnings": []}`, one per entry in request order, echoing as received; outcomes `deleted` / `not_found` / `category_not_found`; none is an error; other entries still applied | §4A.3, §1 (stable outcomes list) | exact (13A C7(a)–(b), C2(d), C5(c)) |
| Status classes 401 / 422 / 5xx; 401 and 422 not retried; the 5 s limit with 503 (deadline) and 500 (statement/lock timeout or other fault); replay harmless; one transaction per request | §4A.3 → §3.4, §3.5, §5 | exact (13A C6(a)–(b), C4(a)–(b); one owner-mode `maybe_begin`) |
| "Manager's tasks themselves keep running; users re-add the assignments to the new row by hand" | §4A (prose) | exact (13A C3(b), C3(e); E5/E10) |
| Processed: `resolved`/`null` from `awaiting`; `resolved`/`"early"` from `in_queue`/`in_progress`; `ignored`/`item_not_found`; `ignored`/`no_open_assignment` (never assigned **or already closed**, incl. `resolved_early`); "the first that applies, in this order" | §4.2, §4.3 | exact (plan 9 task 2; C3(a)–(f), C3(l), C4(d)–(g), C6(b)) |
| Processed: the same article number twice → the second reads `no_open_assignment`; status codes without 503 | §4.3 | exact (plan 9 C5(a)–(b); no deadline in phase 9) |
| "Once closed, Manager will not put the same task and item back on the board" | §4.2 | exact (plan 8 C1(p)–(u), `already_processed_by_scanner`) |
| "Manager keeps it marked as such so its users can see which items reached you before their task was completed" | §4.2 | exact (`resolved_early` visible in the assignment list, plan 13 C4(a); events, plan 9 C4(g)) |

**Mismatch between the handoff and the intention: none found.** One wording note for the
coordinator, not a mismatch: handoff §4A.3 says "Status codes, the 5 s limit and retry rules are
demand's (3.4, 3.5)" and §3.4 lists 503 for the deadline — the plan gives the delete webhook the
same 503 (13A C6(b)), which is what E9/P39 ratify.

## 4. Superseded text removed

Commands run over the plan set (`master_plan.md` + `plans/*.md`) after the edits:

- `grep -rn 'not_awaiting' master_plan.md plans/` → **0 hits** (was: master plan §6.1, plan 9
  task 2 and C3(c)–(e), plan 10 C5(b)).
- `grep -rn 'resolve_awaiting_group' master_plan.md plans/` → 1 hit, master plan §7.4 item 3, the
  rename record ("renamed from the round-7 `resolve_awaiting_group`") — a historical note; the
  registry (§6.5) and plan 9 use `resolve_processed_group`.
- `grep -rn 'COLLABORATING\|PROVISIONAL\|five states\|unratified' master_plan.md plans/` → 0 hits
  after the tracker rewrite (was: master plan header, §4 13A row, §7.4; plan 4 C2).
- `grep -n '§5 r2' plans/*.md` → 0 hits (plan 4 C3(d)'s trace rewritten per C47).
- The C47–C50 superseded sentences, each located and rewritten rather than annotated: C47 (§5 rule
  2; MC-1's `in_queue`/`in_progress → resolved ✗` as the whole story) → plan 4 task 1 table and
  C1(s)–(u), C3(d)–(e) traces; C48 (`not_awaiting` in MC-10 step 2 and the success-body enum) →
  plan 9 task 2, C3(c)–(f), C3(l), master plan §6.1; C49 (MC-11 "Task reopen first") → plan 10
  C5(b); C50 (P32 "ignored and not remembered") → no plan row cited P32; plan 9's goal no longer
  says any active state is ignored. C46 (v1 "send a final 0 … no delete webhook") → nothing in the
  round-7 set relied on it; master plan §1 and §6.9 now name three webhooks.

## 5. Manifest, counts and trace (derived)

Script: `count_rows.py` in the session scratchpad — parses `^\| C<n>(<letter>)` rows with range
expansion (`C2(a)–C2(f)`), counts rows and distinct criteria per file, collects the trace cell of
every row, and checks each criteria table's cell count against its header. Final run over the
tree at close:

```
plan_1: 53/7  plan_2: 75/7  plan_3: 42/8  plan_4: 62/7  plan_5: 22/3  plan_6: 36/8  plan_7: 52/7
plan_8: 65/8  plan_9: 42/8  plan_10: 35/7  plan_11: 27/7  plan_12: 45/7  plan_13: 19/5
plan_13A: 36/7  plan_14: 5/2      TOTAL rows=616 criteria=98 phases=15
```

Every sizing line and tracker row was substituted from this output (a second run compared them:
15/15 `OK`). Table integrity: 0 mismatches after two planning-0 defects were repaired (plan 5
C3(a), master plan §6.1 `scanner_property_tables.py` row).

**Trace, both directions.** Ledger coverage by phase: M1 → 1, 3, 4, 8, 10, 13, 13A · M2 → 9, 10,
11, 13A · M3 → 6, 9, 13A · M4 → 1, 6, 7, 8, 9, 12, 13, 13A · M5 → 5, 9, 12 · M6 → 3, 12, 13A ·
M7 → 7, 9, 13A · M8 → 2, 8, 11 · M9 → 3, 14. Every MC-1…MC-20 appears in at least one trace
cell (MC-10 only in 9; MC-11 in 10 and 13A; MC-20 in 3 and 13A). Amendment rows are cited as
`§14E En` / `§14F Fn` beside the contract they amend; the two round-8/9 ledger sentences (M3, M2)
are served by 13A C3(a)–(b) and by plan 9 C4(d), plan 10 C3(c)–(f).

**Rows tracing to a bare `D6`** (four, all planning-0 authorship, unchanged by this delta): plan 6
C1(e), C6(b), C6(d); plan 9 C7(b). `D6` is intention §14D D6, a ratified owner decision; the cells
lack the `§14D` prefix a lint keyed on `MC-`/`M`/`§` would want. Left as they are (the prompt
scoped this session to rounds 8–9); a one-token fix for the coordinator's next fold.

**Rule-17 cells added by this delta:** plan 6 C5(c) (a `FOR UPDATE` that waited drops a row whose
committed version fails the `WHERE` — PostgreSQL manual §13.2.1) and 13A C5(a) (deadlock detection
raised as `DBAPIError` `40P01` — §13.3.4); both are public-contract shapes, projection confirms on
the installed 18.6. No new fixture came from prose.

**Deterministic contention rows** (master plan §9 rule 9): plan 6 C5(c), 13A C5(a), C5(b) — a
held lock plus a bounded wait; no new row relies on an unforced interleaving.

## 6. Write perimeter

`git status --porcelain -uall` at close (final run, after the last edit):

```
 M docs/archgraph-anchor-observations.md
?? docs/architecture/under_construction/implementation/stock_report/handoffs/planner/2026-09-19_planning_delta_r8_r9_handoff.md
?? docs/architecture/under_construction/implementation/stock_report/handoffs/planner/2026-09-19_planning_handoff.md
?? docs/architecture/under_construction/implementation/stock_report/master_plan.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_1.md … plan_14.md (fourteen files)
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_13A.md
?? docs/architecture/under_construction/implementation/stock_report/prompts/planner/2026-09-19_planning_delta_r8_r9.md
```

**Written by this session:** `master_plan.md` (edited in place), `plans/plan_1.md`, `plan_3.md`,
`plan_4.md`, `plan_5.md`, `plan_6.md`, `plan_8.md`, `plan_9.md`, `plan_10.md`, `plan_11.md`,
`plan_13.md`, `plan_14.md` (edited in place), `plans/plan_2.md`, `plan_7.md`, `plan_12.md` (one
header line each), `plans/plan_13A.md` (new), and this handoff (new). All untracked, as the
round-7 set was.

**Not this session's, left alone:** ` M docs/archgraph-anchor-observations.md` (the
orchestrator's) and the untracked delta prompt. **Not touched:** the intention, the Scanner
handoff, both inventory handoffs, the previous planner handoff, the planning-0 prompt, anything
under `app/`, the architecture graph (no `archgraph_*` call at all this session), the database.
Tool-recorded state: none. Scratch: `count_rows.py` in the session scratchpad only. **Not
committed.**

**Untouched by instruction:** card 1 and master plan §10.1–§10.2; plan 3 C2(a); plan 6 C7(a);
plan 9 C7(a)'s statement-count clause; plan 13 C4(c); plan 10's registry guard (C4). Round 9 did
not force a change to any of them.

## 7. Skeleton decisions this delta made (owner may strike; none is semantic)

1. **`resolve_processed_group`** replaces the planning-0 name `resolve_awaiting_group` (it now
   resolves from three states).
2. **`_demand_lookup.py`** (phase 6) holds the category resolution and identity discovery both
   stock webhooks use — the mechanical form of E4 "the same engine".
3. **Demand's locked-set assertion** (plan 6 task 2 step 6, C5(c)): a row soft-deleted between
   discovery and lock → `RuntimeError` → 500 → Scanner retries → the retry creates the fresh row.
   Within v1 §3.4's "500: any other Manager fault → retry"; no new outcome, no new status.
4. **The advisory lock before discovery** in 13A (task 3 step 4.3), so a delete request's live set
   is stable; a candidate missing at the lock is a 500, never a silent `not_found`.
5. **The coalescer's `:deleted` clause** (plan 8 task 4): MC-19's "no `:updated` for the deleted
   row" applied per request.
6. **Standing rule 16** (master plan §9): active/terminal are the two frozensets, never a spelled
   list — earned by round 9's arrival after ten phases were planned; plans 3, 9, 11, 13 each carry a
   row whose named mutation is exactly the spelled list.
7. **All enums ship in phase 1** from the §6.1 registry (`StockDemandDeletedOutcomeEnum`, the
   `stock_demand_deleted` trigger included), so 13A edits no enum module.
8. **Phase 14 depends on 13A** (the third webhook must exist before `api.md` lists it).

## 8. For the projectionist (round 0), additions per phase

- Phase 1: C7(a)'s partition row and C1(i)–(j) (the enum type must hold the sixth value in the
  one migration).
- Phase 4: the six-state table in task 1 against C1/C3's enumeration (every cell has a row).
- Phase 5: C1(n)–(q) — the credit on entering `resolved_early` shares the awaiting statement.
- Phase 6: C5(c)'s Postgres re-evaluation shape on 18.6; whether `_demand_lookup.py`'s two
  functions cover exactly D6 steps 3–4.
- Phase 8: the position of `already_processed_by_scanner` in the order (C1(t)–(u)).
- Phase 9: the per-column delta vector of the grouped statement (C7(d)–(e)); the JSON `null`
  reason (C3(f), C3(l)).
- Phase 10: C5(b)'s goal arithmetic under the reopen-first order (`G` 4 → 0 → 4).
- Phase 13A: all six carried questions (§7 of the plan); C5(a)'s deadlock shape; the coalescer's
  `:deleted` clause in C5(b); the perimeter's "nothing under `app/migrations/`".
