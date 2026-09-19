---
plan: (project-level — this session created master_plan.md and plans/plan_1.md … plan_14.md)
role: planner (implementation-planner)
round: planning-0
date: 2026-09-19
state: OWNER_DECISIONS_PENDING — plan set complete; one owner card (which of the 21 baseline failures, if any, to fix); no phase waits on it
actor: Claude Fable 5.1 (pipeline-planner agent, orchestrated mode; launched by the coordinator)
---

# Planning handoff: `stock_report`

## Opening summary

Gate check passed on all four lines at tree `f575488` (clean): the intention header reads `status:
RATIFIED` with the owner's 2026-09-19 re-ratification in §18; `git status --porcelain --
planning/intention.md` is empty; the re-check handoff exists with `verdict: PASS` and `⚠ OWNER
DECISIONS REQUIRED (0)`; no `master_plan.md` or `plans/` existed.

The plan set is written: one master plan and **fourteen** phase plans holding **532 criterion rows
in 90 criteria** (counts derived from the files by script, not typed — see §5). The owner's
suggestion was six phases; the split is by contract so that no phase exceeds the charter's target of
eight criteria and every phase closes green on its own. Reasons per split are in master plan §7.1
and §3 below. Every row carries a trace cell to a mechanism contract (MC-1…MC-20) or a ledger entry
(M1–M9); every MC and every M is served by at least one row (§6 below). The re-check's carried list
is scheduled: D6's statement-count criterion (plan 6 C6), MC-1 instruments (a)–(c) (plan 4 C5(a),
C5(c); plan 13 C2(b)), MC-9 rule-10 rows (i)–(iii) (plan 6 C7 — (ii) is the project's one sleeping
test), §12A (a)–(e) with the double-decrement probe (plan 3 C3–C7, plan 4's required ledger row),
X2 and X3 (plan 9 tasks and C8).

Two owner tables are in master plan §10.1–§10.2 and summarized in §4 below: **none** of the 21
baseline failures overlaps a phase (5 adjacent, 16 unrelated), and **no Stock Report code reads
across workspaces**, so the leaking test files are invisible to it; the only exposure is a
global-count assertion, which the standing rules forbid.

Nothing was committed (prompt: the owner reviews the plan set first). No file under `app/`, the
intention, either inventory handoff or the Scanner handoff was touched by this session. No
archgraph write, no database write, no test run.

**The intention gate was re-opened while this session ran — read before anything else.** At the
gate check the intention was `RATIFIED` and clean. At close, `git status` shows
`planning/intention.md` **modified by another actor** (104 insertions, 18 deletions, uncommitted):
the header now reads `status: COLLABORATING — round 8`, a new **§14E** adds a third Scanner webhook
(Scanner deletes a board row; proposals P37–P41; cards 12 and 13), M3 gains a round-8 sentence, and
§14E itself says rounds 0–7 stay ratified, the owner waived a mechanism-inventory re-check for it,
and the planner decides where it lands (its own suggestion: phase 13 or directly after). This
session did **not** plan §14E: the doctrine forbids planning against an unratified intention, and
the two cards are open. What it did instead: the fourteen plans stand against the committed
round-7 text (`git show f575488:…/intention.md`); the master plan header, tracker and a new §7.4
record the re-open, the hold, and the owed **planning delta** (provisional phase 13A, depending on
7 and 13, answering §14E's six carried questions); phase 13's cascade was factored into a
subordinate operation (`cascade_delete_stock_report_item`, master plan §6.5) so the delta adds a
caller instead of a copy. **The coordinator's gate now holds: no projection or implementation
prompt for any phase until the header reads `RATIFIED` again.** The state line of this handoff is
`OWNER_DECISIONS_PENDING` for this session's own card; the re-open is the owner's and the shaper's
round, not a planner card.

## ⚠ OWNER DECISIONS REQUIRED (1)

**Card 1: which of the 21 already-failing tests should this project fix?**
- **Question:** Fix none of them (A), or fix the five whose fixtures or routes sit next to code
  Stock Report changes (B)?
- **Story:** The suite has had the same 21 red tests since August, all in code this project never
  edits: seeding, item positions, upholstery stock, working-section ordering, the audit log,
  Shopify dimensions, sign-in, worker stats, case types, two item-issue routes and one upholstery
  route. Five of them build tasks or call the items router, so when phase 1 adds a column to tasks
  and phase 11 changes how an item's category may change, those five sit one step away from the
  work; none exercises the code we write. Fixing any of them means a session on unrelated code
  while fourteen phases wait.
- **Branches:** A: baseline stays 21, every phase diffs against it, nothing extra is done. B: a
  small maintenance session before phase 1 repairs the five adjacent ones and re-publishes the
  baseline as 16.
- **Recommendation:** A — zero of the 21 overlaps a phase, so a fix buys no protection for this
  project and costs a session; the adjacent five can be revisited at closeout.
- **On silence:** the gate holds on the question, but no phase waits on it: the plans proceed
  against the published 21-ID baseline.
- **Trace:** master plan §10 (baseline), §10.1 (table 1); prompt "Two tables the owner needs".

## 1. Files written (all new; none pre-existed)

- `docs/architecture/under_construction/implementation/stock_report/master_plan.md`
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_1.md` … `plan_14.md`
  (fourteen files)
- `docs/architecture/under_construction/implementation/stock_report/handoffs/planner/2026-09-19_planning_handoff.md`
  (this file)

## 2. Write perimeter

Checked against `git status --porcelain` at close (the command's output is appended in §9): the
sixteen paths above, all untracked (`??`), under two new directories `plans/` and
`handoffs/planner/`, **plus two foreign entries that are not this session's**: ` M
docs/architecture/under_construction/implementation/stock_report/planning/intention.md` — the
round-8 / §14E edit described in the opening summary — and ` M
docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v1_20260918.md`, which appeared between this
session's two status checks (the same actor, presumably folding the §14E webhook into the
not-yet-handed-over v1 file). Both were made by another actor after this session's gate check
(which found the intention clean) and neither was opened for writing here; this session's own
final check re-ran `git status` and found no third entry. **Not touched by this session:** the intention, both inventory handoffs, the two reviewer prompts, the planner prompt,
`docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v1_20260918.md`, anything under `app/`,
`docs/archgraph-anchor-observations.md`. Tool-recorded state: **none** (no archgraph
`apply_changes`, no review decisions, no DB access; the only commands run were reads, `git status`
and `git diff`, an Alembic `ScriptDirectory.get_heads()` and version imports inside `app/.venv`,
and the row-count and trace-check scripts over the plan files). Scratch: none written outside the
repo. Not committed.

After the row counts were derived, 26 trace cells that read `same`/`row n`/a bare Scanner filename
(plan 2 C4–C7) and one that read `all-or-nothing` (plan 8 C6(d)) were rewritten to name their
contract explicitly; a second pass found zero rows without an `MC-`/`M`/`HC-`/`§` trace. Row and
criteria counts did not change.

## 3. Phase list with sizing lines (rows / criteria / complex)

| Phase | Scope | Rows | Criteria | complex | Depends on | Projection |
|---|---|---|---|---|---|---|
| 1 | Schema, migration, reset, enums, state map, criteria normalization, settings, test kit | 48 | 6 | no | — | mandatory |
| 2 | Matcher mirror (Scanner tables, bag, evaluation, hand-walk H1–H16) | 75 | 7 | no | 1 | mandatory, not waivable (rule 17) |
| 3 | Consistency check, manual repair, repair records, flag writer, 2 endpoints + 8 cells | 41 | 8 | yes | 1 | mandatory |
| 4 | Transition operation: moves, counters, inline self-heal, removal, stamps, payloads | 49 | 7 | yes | 3 | mandatory |
| 5 | Goal credit (MC-5 table, goal self-heal, worked sequence) | 17 | 3 | no | 4 | mandatory |
| 6 | Demand service, set-based (find-or-create, goal records, replay, deadline, D6 bound) | 35 | 8 | yes | 3 | mandatory, not waivable |
| 7 | Demand endpoint (auth, validation tables, duplicates, M4 over bytes, envelope) | 52 | 7 | no | 6 | mandatory, not waivable |
| 8 | Assignments create/delete, override retry, race error, coalescing, 8 cells | 58 | 8 | yes | 2, 5 | mandatory |
| 9 | Processed webhook (vocabulary, grouped counter update, replay, X2, X3) | 33 | 8 | yes | 7, 8 | mandatory, not waivable |
| 10 | Task-state sync S1–S9, registry guard with 6 probes, MC-11 | 30 | 7 | yes | 9 | mandatory |
| 11 | Removal hooks + category guard on both item writers | 26 | 7 | yes | 8 | mandatory |
| 12 | Priority, ordering, user history records, list endpoint, 12 cells | 45 | 7 | yes | 5 | mandatory |
| 13 | Row deletion cascade, second trigger + instrument (c), assignment reads, 8 cells | 19 | 5 | yes | 12, 8 | mandatory |
| 14 | Frontend handoff + domain docs (thin) | 4 | 2 | no | 13, 11, 10 | waivable |
| **Σ** | | **532** | **90** | | | |
| 13A | **provisional, not planned** — Scanner delete-row webhook (§14E, unratified at close) | — | — | — | 7, 13 | mandatory, not waivable (owner waived the inventory re-check, so the plan carries the contracts) |

Rows above eight criteria per phase: none (phases 3, 6, 8, 9 sit exactly at eight). Rows per phase
vary widely because parametrized pure-function tables (phases 1, 2, 7) are cheap rows; the charter's
cost predictor is the criteria count.

**Departure from the owner's six phases (master plan §7.1).** Foundation split into schema (1) and
matcher (2) because the matcher is a rule-17 phase with 75 Scanner-derived rows. The core engine
split into check/repair (3), moves (4) and goal credit (5) because the self-heal *calls* the
recomputation (so 3 precedes 4) and MC-1/MC-5 are two contracts. Demand split into service (6) and
endpoint (7) — complex vs not. Assignments (8) and processed (9) are two surfaces. The owner's
phase 5 split as allowed: sync (10) needs the processed webhook for MC-11; hooks (11) do not. The
owner's phase 6 split into ordering + list (12), row deletion + assignment reads (13) and docs (14);
the consistency/repair endpoints moved **up** to phase 3 because every later phase's tests use the
repair command and role cells ship with their operation. The two GET endpoints, absent from the
suggestion, live in 12 (rows) and 13 (assignments).

## 4. The two owner tables, in short

**Table 1 — 21 baseline failures vs phases** (full table: master plan §10.1). 0 `overlaps`,
5 `adjacent`, 16 `unrelated`. Adjacent: `test_seed_working_sections_integration` (1), the two
`test_batch_working_section_integration` tests (2) — fixtures build `Task` rows and phase 1 adds a
`tasks` column with a `server_default`; the two `test_items_router` tests — the items router is a
direct caller of `find_or_create_item`, whose behaviour phase 11 changes, though the failing routes
are the issue routes. Nothing is fixed by any phase (card 1).

**Table 2 — leaking test files vs phases** (full list: master plan §10.2). No phase's production
code reads across workspaces (check, repair, webhooks, sync and hooks are all workspace- or
id-scoped), so leaked `item_categories`/`items`/`execution_tasks`/task rows are invisible to it. The
precise 23-file audit list was not re-measured (no probe built, as instructed); a cheap grep
(constructs those rows **and** commits) names 22 candidate files, with the audit's named offenders
marked. The residual risk is a global-count assertion, forbidden by master plan §9 rule 1.

## 5. Manifest properties (charter "phase manifest")

- **Identity:** every criterion row is lettered (`C3(b)`); ranges such as `C8(a)–C8(d)` expand to one
  obligation per letter.
- **References resolve:** every `file:line` in the plans was read on 2026-09-19 at `f575488`
  (task-state writes: `resolve_task.py:56`, `fail_task.py:56`, `cancel_task.py:56`,
  `add_task_steps.py:158`, `remove_task_step.py:225`, `_task_state_transitions.py:28/52/109`; hook
  sites `delete_task.py:71-92`, `remove_item_from_task.py:23-35`, `delete_item.py:26-37`,
  `update_item.py:73-74`, `find_or_create_item.py:94-118`, `create_task.py:250-262`,
  `routers/api_v1/items.py:225-237`; precedents `message_writes.py:60-75`,
  `test_budget_signals_query.py:465-490`, `test_item_economics_router.py:60-115`,
  `test_phase7_concurrency.py`, `tasks.py:425-450`). Scanner citations are at commit `0d80bf2`,
  re-read for `wood-groups.ts` and `drawer-ranges.ts` (tables match E8).
- **Counts derived:** the row and criteria numbers in every sizing line, the tracker and §3 were
  produced by one script over the plan files (`^\| C<n>(<letter>)` with range expansion) and
  substituted; the script found no placeholder left.
- **Mutation sets:** each rule-6 row names its mutation and site; rows marked `—` are enumerated
  neighbours of a mutated row or literal transcriptions; role cells and envelopes carry no ledger
  row (MVP calibration). Rows that cannot force an interleaving say so in their cell (plan 6 C5(b),
  plan 9 C8(b), plan 11 C7, plan 12 C2(a)/(b)) and name the structural check.
- **Trace, both directions:** every row cites an MC or M. Coverage of the ledger by phase: M1 (3,
  4, 5, 8, 13), M2 (10, 11), M3 (6, 7, 9), M4 (1, 6, 7, 8, 12, 13), M5 (5, 6, 12), M6 (3, 12), M7
  (7, 9), M8 (2, 8, 11), M9 (3, 8, 12, 13 cells + MC-17 rows in 4, 8, 10, 12, 13); every MC-1…MC-20
  appears in at least one trace cell (MC-19 in 4, 6, 8, 9, 10, 12, 13; MC-18 in 3, 8, 12, 13).

## 6. Skeleton decisions the planner made (owner may strike; none is semantic)

1. **Error identities** (05_errors_local): `STOCK_REPORT_TARGET_OUT_OF_RANGE`,
   `STOCK_REPORT_ROW_HAS_NO_PRIORITY`, `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER` as leading tokens of the
   422 messages the intention names by reason; the category-guard 409 keeps its ratified sentence
   verbatim with no token (the intention fixed the text).
2. **Two ratified contract divergences declared, not silently applied:** the list endpoint is
   unpaginated (owner answer) against `07_queries_local`'s gate; the two assignment errors carry
   `code` + `details` (MC-13) against `05_errors_local`'s "no code" rule.
3. **No history read endpoint** in this project — §9's API table does not list one; the frontend
   handoff says so (phase 14).
4. **Event coalescing** per request lives in `coalesce_stock_report_events` (phase 8) fed with the
   row values snapshotted at the row lock — MC-1's `move_assignment -> list[event]` signature stays
   as ratified, MC-19's net-change rule is applied by the owning command.
5. **Grouped processed update** is `resolve_awaiting_group` in `_move_assignment.py` (phase 9),
   sharing the guarded-statement builder and repair routine — HC-3's "one module owns it".
6. **The MC-2 registry lives in tests** (`task_state_write_site_registry.py`), beside the guard.
7. **Consistency/repair are endpoints** (P35), shipped in phase 3 with their eight cells.
8. **One migration** for the whole project (phase 1), `server_default=false` on the `tasks` column so
   raw-SQL task inserts elsewhere keep working.
9. **Test kit** in `app/tests/helpers/stock_report.py` (+ `statement_listener.py`) — a shared seed,
   purge, ctx, dispatch-capture and the one two-assertion clean helper.

## 7. For the projectionist (round 0), per phase

- Phase 1: autogenerate's omission of partial-index predicates and CHECKs; the golden vectors' hand
  derivation (C5(d)); C4(f)'s declared non-isolation.
- Phase 2: whether each H-row's criteria literal is what `normalizeCriteria` yields from the report
  line (N7 was never read from Scanner's DB); `String(4.0)`; the C2(e) tie-break is Manager-only.
- Phase 3: the `order_density`/`nullness` divergence conventions (master plan §6.5) against the
  repair's one-record-per-`(row, field)` rule; the read-only listener's table set.
- Phase 4: the ✗/`—` cell enumeration against MC-1's table; the RETURNING-payload row (C4(c)).
- Phase 6: the measured asyncpg/SQLAlchemy shapes on the installed versions; the 8-statement
  arithmetic per shape (C6); the deadline patch seam (C7(c)).
- Phase 7: Starlette header folding; `json.loads` duplicate-key behaviour; the 401 identity of
  messages across causes.
- Phase 9: the grouped statement's per-row UPDATE count (C7) and X2's structural check.
- Phase 10: the six probes' exact planting sites; the C5 lock-ordering harness.
- Phase 11: C1(c)'s constructibility note; the None-aware rows.
- Phase 12: the inherent disjunction in C2(a)/(b) versus the deterministic C2(c).
- Phase 13: instrument (c)'s exact numbers (stored `1`, recomputed `0`).

## 8. Gate check record

| Line | Command / observation | Result |
|---|---|---|
| 1 | `grep -n '^status:' planning/intention.md` | `status: RATIFIED — by the owner (David): … re-ratified 2026-09-19 incl. round 7 …`; §18 carries "Re-ratification — 2026-09-19 (owner, David)" |
| 2 | `git status --porcelain -- planning/intention.md` | empty |
| 3 | re-check handoff | exists; `verdict: PASS`; `⚠ OWNER DECISIONS REQUIRED (0)` |
| 4 | `ls master_plan.md plans/` | neither existed |

Environment facts re-verified: single Alembic head `ce99896e6f49` via `ScriptDirectory.get_heads()`;
SQLAlchemy 2.0.40 / asyncpg 0.30.0 in `app/.venv`; `app/.env` points at `localhost:5433` and
`localhost:6380`; `pytest.ini` `-n 6 --dist loadfile`; tree `f575488`, clean.

## 9. `git status --porcelain -uall` at close (final run)

```
 M docs/architecture/under_construction/implementation/stock_report/planning/intention.md
 M docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v1_20260918.md
?? docs/architecture/under_construction/implementation/stock_report/handoffs/planner/2026-09-19_planning_handoff.md
?? docs/architecture/under_construction/implementation/stock_report/master_plan.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_1.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_10.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_11.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_12.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_13.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_14.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_2.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_3.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_4.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_5.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_6.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_7.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_8.md
?? docs/architecture/under_construction/implementation/stock_report/plans/plan_9.md
```
