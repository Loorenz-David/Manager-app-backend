---
batch: D
plans: [12, 13, 13A, 14]
role: projection
round: 0
verdict: PROJECTED (was AMENDMENTS_REQUIRED; all 8 cards ruled and applied — see the addendum, §9)
state: DONE
date: 2026-09-21
actor: projectionist (Opus, plan-projection)
---

# Batch D — projection round 0 and the lesson fold

## 0. Opening — for the owner

Batch D's four plans (priority and ordering, the row-deletion cascade, Scanner's delete webhook,
and the frontend/domain documents) are implementable, and the risky one — the Scanner delete
webhook — holds up: I walked all six questions the mechanism-inventory re-check would have asked
and every one of them is answered correctly by the plan, now with the evidence checked against
the code that actually ships rather than against the plan's own summary. I folded twenty-eight
review lessons into the three plans that had never received a fold: every one of the 27 criterion
rows that carried no named defect now carries one (or says plainly why it cannot), the fixtures
that could not tell right from wrong have been tightened, and the two dependency-owned shapes this
batch relies on (PostgreSQL's deadlock error and Pydantic's number coercion) are now grounded in
the versions this machine installs instead of being described in prose.

Three things I found are worth your attention before anyone writes code. One is a real trap: the
cascade that phase 13 builds has to re-read a row's position from the database each time it runs,
and only a phase-13A test can ever notice if it does not — but phase 13A is forbidden from editing
that file, so the requirement has to be right the first time. One is a straightforward miss: the
documents phase never mentions the match-preview endpoint that shipped today, and its automatic
accuracy guard is pointed at a file that contains only one of the six event names it is supposed
to check. The third is arithmetic: a plan says a task summary has eleven fields and the shipped
code returns twelve.

**Eight decisions need you personally**, all of them one-line rulings on wording I am not allowed
to change — criterion outcomes and task text belong to you. Nothing is blocked on anything else:
the moment those eight are ruled, the implementer prompt can compile.

---

## ⚠ OWNER DECISIONS REQUIRED (8)

### Card 1 — Replace `≤ 7` with the two exact statement counts (plan 13A C5(d))

**Question.** Change C5(d)'s bound from "`≤ 7`" to the two derived exact counts, 5 and 4?

**Story.** This row exists to prove that when Scanner sends thirty deletions instead of three,
Manager does not quietly start making thirty round trips to the database. A "no more than seven"
bound passes at five, at six and at seven — so the day somebody adds a stray lookup inside the
loop, the row stays green and the slowdown ships. We already know the true numbers, because I
counted them off the code that ships today.

**Branches.**
- *Exact (5 and 4):* the row bites the first time anyone adds a statement to this path, the way
  the demand budget already does.
- *Keep `≤ 7`:* three statements of silent slack on the one row that guards batch size.

**Recommendation.** Exact. It is the lesson this project wrote down (L-22) and the derivation is in
the plan's own §7 now, so the number is checkable rather than typed.

**On silence.** The gate holds; the implementer prompt does not compile with the row unresolved.

**Proposed cell text** (outcome cell of C5(d), the rest of the row unchanged):

> total statements recorded during `DD` are **exactly 5** for the *all `not_found`* shape and
> **exactly 4** for the *all `category_not_found`* shape, **identical for 3 entries and for 30**
> in each shape; no write. (5 = `set_config`, workspace check, advisory lock,
> `resolve_categories_for_entries`, `discover_live_rows_by_identity`; 4 = the same minus
> discovery, which executes nothing when no entry resolved a category. Steps 4.6–4.9 issue no
> statement on an empty id set.)

**Trace.** plan 13A C5(d); §7 Q3; §9A L-22; master plan §9 rule 7.

---

### Card 2 — "eleven" task fields is twelve (plan 13 C4(b) and task 3)

**Question.** Correct plan 13's "the eleven fields of §9B" to twelve, in both places?

**Story.** The compact task summary the board renders has twelve keys — I read them off the
shipped function. The plan says eleven twice. A tester writing the row from the plan will assert a
set of eleven, the assertion will fail against correct code, and the round will be spent deciding
which document is wrong.

**Branches.**
- *Twelve:* the row matches the code and the intention's own enumeration.
- *Leave it:* one guaranteed false failure, or worse, a test that drops a real field to make the
  count come out.

**Recommendation.** Twelve, worded as "`client_id` plus the eleven fields", so the two readings
that produced this can never diverge again.

**On silence.** The gate holds.

**Proposed cell text** (C4(b), outcome cell, the `task` clause only): "`task` keys exactly the
**twelve** of §9B — `client_id` plus the eleven fields §2 lists". Same substitution in §5 task 3.

**Trace.** plan 13 C4(b), §5 task 3; intention §9B; `bm/domain/stock_report/serializers.py:26`;
§9A L-2.

---

### Card 3 — The Scanner-delete row samples five of the six assignment states (plan 13A C3(a))

**Question.** Add a sixth assignment in `in_progress` to C3(a)'s fixture, and restate its outcome?

**Story.** The whole promise of this webhook is that when Scanner drops a rule, *everything* hanging
off that board row goes — a repair already on a bench included. C3(a) seeds five assignments and
covers five of the six states; the one it leaves out is `in_progress`, which is the state a job is
in while somebody is physically working on it. If the code ever filters that one state out, this
row still passes and the bug reaches a shop floor.

**Branches.**
- *Add it:* the row enumerates the contract instead of sampling it (the intention says "any state").
- *Leave it:* the most visible state on the board is the one state no row deletes.

**Recommendation.** Add it. It costs one more assignment in a fixture that already has five.

**On silence.** The gate holds.

**Proposed change** (C3(a), fixture and outcome; everything else in the row unchanged): add
`A6 in_progress q = 3` on a sixth task/item; the "before" counters become `(1, 3, 2)` and the
"before" goal total stays `G == 10` (an `in_progress` assignment is not credited); the outcome
reads "all **six** assignments `is_deleted` … all **six** tasks' `is_stock_assignment` false", and
"five" becomes "six" in the events row C3(d) (six `stock_task_assignment:deleted`).

**Trace.** plan 13A C3(a), C3(b), C3(d); intention §14E E5; §9A L-1; charter rule 2.

---

### Card 4 — Plan 12 tests one of the three ways a row can be invisible

**Question.** Author the two missing visibility rows for the priority commands, or restate C1(o) to
carry all three cases?

**Story.** A row can be invisible to a command in three ways: it never existed, it was deleted, or
it belongs to somebody else's workspace. Plan 12 checks only the third. The priority commands are
the ones a seller drives all day from a stale browser tab, so "the row was deleted while my tab
was open" is the *most* likely of the three — and nothing in the phase says what happens.

**Branches.**
- *Three cases:* the phase matches what the same enumeration already does in plans 13 and 13A.
- *One case:* the delete-while-open path ships unspecified and untested.

**Recommendation.** Restate C1(o) to enumerate all three, rather than add rows — it keeps the
criteria count where it is.

**On silence.** The gate holds.

**Proposed cell text** (C1(o), replacing the current fixture and outcome):

> Fixture/input: three calls as U of W — `SP(row of the foreign workspace, low)`, `SP(a
> soft-deleted row of W, low)`, `SP("sri_absent", low)`. The foreign row is a cross-workspace
> reference (preamble).
> Outcome: `NotFound` each; no state anywhere changes; the foreign workspace's group is byte-identical.

**Trace.** plan 12 C1(o); §9A L-34; intention §5A MC-16 predicate table; M4.

---

### Card 5 — Plan 13's task text contradicts itself and describes work that already shipped

**Question.** Apply the three corrections below to plan 13 §5 and §4?

**Story.** Task 1 tells the implementer that the cascade must take every stamp value from its
arguments and never from the request context — and then, two lines later, spells the stamps as
`ctx.now` and `ctx.user_id`. Whoever follows the second sentence writes a cascade that Scanner's
webhook cannot reuse, and the failure only shows up a phase later. The same task also asks for
three serializers that were moved into phase 8 by your own ruling and are live in the code today.

**Branches.**
- *Correct it:* the implementer reads one instruction instead of two contradictory ones.
- *Leave it:* a near-certain rework cycle in phase 13A, and a phase-13 round spent re-adding
  functions that exist.

**Recommendation.** Apply all three; they are transcription fixes, not design changes.

**On silence.** The gate holds.

**Proposed changes.**
1. Task 1, the row soft-delete clause: `deleted_at = now`, `deleted_by_id = actor_user_id`,
   `updated_at = now`, `updated_by_id = actor_user_id` — **the cascade's own arguments, never
   `ctx`** (the command passes `now=ctx.now, actor_user_id=ctx.user_id`).
2. Task 1, the counter check: make the loop boundary explicit — "**after the assignment loop
   ends**, one fresh `SELECT` of the three counters; any column ≠ 0 → one `UPDATE` setting that
   column to 0 …" (MC-16 puts it after every assignment is moved out, and C2(a)/C2(b) both read it
   that way; the current run-on sentence reads as though it is inside the loop).
3. Task 3 and §4: the three compact serializers **already ship in phase 8** (owner ruling §9B.2);
   this phase adds none. §4's "Edited: `bm/domain/stock_report/serializers.py` (three serializers
   added)" and "`requests/__init__.py`" both drop out — `DELETE` takes no body.

**Trace.** plan 13 §5 tasks 1 and 3, §4; master plan §9B rulings 1–2, §6.5; §9A L-3.

---

### Card 6 — Phase 14's accuracy guard is pointed at a file that holds one of six event names

**Question.** Change C1(b)'s root from `_events.py` to every event-name site (or master plan §6.7)?

**Story.** The frontend builds its live board on six event names. C1(b) is the guard that stops the
handoff from silently going out of date, and it reads them out of one module — which contains
exactly one of them written out in full. Two are assembled from a template, one is built in the
demand file, and the last one does not exist yet. As written, the guard checks one name, passes,
and tells everybody the document is accurate.

**Branches.**
- *Widen the root:* the guard actually guards the six names the board subscribes to.
- *Leave it:* a green guard over a document that can drift on five of six names.

**Recommendation.** Root it in master plan §6.7's list (the registry the events are named in) and
cross-check it against every `event_name=` site under `bm/services/commands/stock_report/`, so the
guard fails both when a name is missing from the handoff and when a new name appears in the code.

**On silence.** The gate holds.

**Proposed cell text** (C1(b), fixture and outcome): "over the handoff, with the root stated in the
test: every event name in master plan §6.7 **and** every name constructed at an `event_name=` site
under `bm/services/commands/stock_report/` (including the `stock_task_assignment:{kind}` template's
three values) appears in the handoff; a name present in the code and absent from the handoff
reddens, and so does the reverse."

**Trace.** plan 14 C1(b); master plan §6.7; `_events.py:12,33`; `apply_stock_demand.py:271`;
§9A L-32, L-38.

---

### Card 7 — What phase 14 actually publishes, and the endpoint it forgets

**Question.** Confirm that phase 14 issues a **superseding** handoff under the existing name and
folder, and that it must document the match-preview endpoint?

**Story.** Two frontend documents for this project are already out: the early API handoff that
promises "the nullability contract arrives in phase 14", and the ratified match-preview contract
from today. Plan 14 names a third file, in a different folder, under a different naming scheme,
and never mentions match-preview at all. If it ships as written, the frontend has three live
documents and no statement of which one wins — the exact failure that cost this team four days
once already.

**Branches.**
- *Supersede in place:* one current document, the old one archived, and the preview endpoint
  documented with `item_category_id` required, as you ruled today.
- *As planned:* a third document beside two live ones, and the only endpoint the frontend can
  build against today is missing from it.

**Recommendation.** Supersede: keep the `HANDOFF_TO_FRONTEND_stock_report_*` name and the project's
own `handoffs/to_frontend/` folder, add the supersession sentence and the archive move, and add
match-preview to tasks 1 and 3. No v3 of the preview contract — v2 is correct and stays.

**On silence.** The gate holds.

**Trace.** plan 14 §2, §4, §5 tasks 1 and 3; the two published handoffs under
`handoffs/to_frontend/`; intention §14G; master plan §9 rule 15.

---

### Card 8 — The one "unforceable" clause in phase 13A is forceable, if you allow a sixth use

**Question.** Allow statement counting to prove that each lock class is taken in **one** statement
(a sixth use of §9 rule 7), and make C5(b)'s structural clause a measured clause?

**Story.** C5(b) asks the reviewer to eyeball four steps and confirm each issues a single
statement — the property that keeps a multi-row delete from taking locks row by row and deadlocking
with a task command. Eyeballing is how this project's most expensive defect survived: a row ruled
"unfailable by design" whose delegate performed no check. The same property is measurable in one
line with the instrument we already own, but that instrument is fenced to a list of approved uses
and this is not on it.

**Branches.**
- *Allow it:* the promise is measured, and the row stops depending on someone reading carefully.
- *Keep it structural:* the clause is honest but unarmed, and a future refactor to per-row locking
  passes every test in the phase.

**Recommendation.** Allow it. It is the same class of ratified bound as the D6 counts already on
the list, and it converts the batch's last unarmed promise into a test.

**On silence.** The gate holds; the clause stays structural and the reviewer performs it by hand.

**Proposed cell text** (C5(b), replacing the sentence beginning "The reviewer verifies
structurally"): "and, under `record_statements`, the request issues **exactly one**
`pg_advisory_xact_lock`, **exactly one** `FOR UPDATE` on `tasks`, **exactly one** on
`stock_report_items` and **exactly one** on `stock_task_assignments`, whatever the number of
candidate rows — mutation: lock the candidate rows one at a time inside the per-row loop → the
row+group count becomes 2 → red." Master plan §9 rule 7 gains this as its sixth listed use.

**Trace.** plan 13A C5(b), §7 Q2; master plan §9 rule 7; §9A L-32; batch C2 F-3 (the
delegate-that-did-not-check defect).

---

## 1. The fold — every lesson, where it landed

Register: master plan §9A, **L-1…L-31**, plus **L-32…L-39** defined outside it (L-32/L-33 batch C1
review handoff §7; L-34/L-35 same, §7; L-36…L-39 batch C2 re-review 2 §13). All 39 were read at
their source. Targets: plans **12, 13, 13A** (the prompt's list verified against the register —
it is complete for §9A's "Fold targets" column; L-32…L-39 had no targets assigned and are assigned
below). Fold order followed §9A: L-20 first (authority boundary), then L-17's preamble half, then
the rest.

**Applied to the plans this round: 56 mutation cells, 4 fixture cells, 3 new §6 preambles, 4 note
blocks, 2 test-file renames, and two §7 answer cells in 13A.** No criterion outcome cell, no task
text, no master-plan section and no intention section was touched.

| Id | Verdict this round | Where it landed |
|---|---|---|
| L-1 | **owner** — one live instance found | 13A C3(a) samples 5 of 6 assignment states → **card 3**. Plan 12's value tables (MC-7 rows 1–10) re-checked against §7A: complete, one row per table row, no sampling |
| L-2 | **owner** — one live instance | plan 13 says "eleven" task fields against a twelve-key function → **card 2**. §4 totals re-derived by script: 652/107, batch D 106/22, matching the tracker rows exactly |
| L-3 | **owner** — three live instances, all in plan 13 | task 1's `ctx` self-contradiction, task 1's ambiguous loop boundary, task 3's already-shipped serializers → **card 5** |
| L-4 | applied upstream | no forward target; §6.5 provisions every contract 12/13/13A cite (checked, §3) |
| L-5 | **not blocked**, re-checked for this batch | every error-identity row in 12/13/13A resolves to `bm.errors.validation.ValidationError`, `NotFound` or `LocationTrackerWebhookAuthError`; the three registered identities of §6.4 are named literally in 12 C1(d)/(e)/(g)/C4(c). The one rule-17 wrinkle (pydantic coercion) is folded into 12 C1(n)'s mutation cell and §7 |
| L-7 | **folded** | new §6 preambles in 12/13/13A state that each row's fixture must make its own predicate the only reason its outcome holds; 12's `high` group is now decorrelated from `client_id`, which was the instance §9A named |
| L-8 | applied (§9 rule 18) | new public names in this batch: `_ordering.py`'s three functions, `list_stock_report_items`, `serialize_stock_report_item`, `cascade_delete_stock_report_item`, `list_stock_task_assignments`, `parse_stock_demand_deleted_body`, `process_stock_demand_deleted`, `DemandDeleteEntry`/`DemandDeleteOutcome`. Each is pinned by a row **except the two `parse_*_request` wrappers plan 12 needs and §6.5 does not register** → ledger D-3 |
| L-9 | **folded** | rule-17 cells in 12 C1(m)/C1(n) and 13A C5(a)/C5(g) now carry the *rule* (pydantic lax coercion; the asyncpg→SQLAlchemy exception mapping) beside the literal, with the installed versions |
| L-10 | **folded — the main pass** | all 27 `—` cells classified and written (§2); every vague cell in 12/13/13A ("write anyway", "drop a filter", "order a null-priority row", "pick the first `.limit(1)`") replaced with a file, a definition-vs-call site and the observable |
| L-11 | considered, **not applicable** | no row in 12/13/13A mutates a dependency's comparison engine. 13A's category matching is our own in-memory comparison (`_demand_lookup.py`), and C2(c)'s cell now names that site instead of a `.limit(1)` that does not exist |
| L-12 | **folded** | one mutation per sub-check on 12 C1(f) (upper boundary, distinct from C1(d)/(e)), C4(b) (filter vs ordering), C4(d) (empty vs unknown token), C4(f) (two predicates), 13 C1(d)/C4(d) (three visibility cells each), 13A C1(e) (shape vs emptiness) |
| L-13 | **folded** | both directions on 12 C4(e) (extra key / missing key), 12 C4(f), 13 C1(d), and every role cell (remove a role / add a role) |
| L-14 | **folded** | the §6 preambles of 12/13/13A now require `priority_order` ascending to **disagree** with `client_id` ascending inside `high`, and 12 C4(b)'s null pair to be seeded by two `AD` calls with `created_at` ascending disagreeing with `client_id` ascending. Without it the dedicated ordering phase proves ordering with a fixture in which three orderings agree |
| L-15 | considered, **one instance, handled** | the only `sorted()` over a set in this batch is `_locks.py:_lock`'s (phase 1, already shipped and armed) and 13A's `sorted(absent_identities)` in the demand path — C5(g)'s fixture is two identities, which is why its evidence is a **deadlock**, not an order assertion; the two-element limit does not apply to it |
| L-16 | **folded** | cross-workspace-reference clauses in all three preambles; 12 C1(o), 13 C1(d)/C4(d), 13A C2(f) named as the tenancy rows |
| L-17 | **preamble half folded; outcome half found two defects** | new preamble paragraph in 12, 13 and 13A ("every outcome is computed from the fixture's own values, side effects included; an outcome that disagrees with its fixture is a plan defect"). Outcome half: 13's "eleven fields" (**card 2**) and 13A C3(a)'s five-of-six enumeration (**card 3**). Arithmetic re-derived and **correct** for 13 C1(a) (`G == 8`), 13A C3(a) (`G == 8` = A2 3 + A4 5), C5(e) (stored 8 = Σ credited), C5(b)/C5(c) (both groups dense) |
| L-18 | considered | no registry row amended this round |
| L-19 | **folded** | 13A C5(a)'s cell now repeats the condition its bite depends on (the deadlock is detected at 1 s, inside the 5 s `lock_timeout`/deadline window); 12 C1(e)/C1(f) repeat the `n = 4` condition |
| L-20 | **honoured first, as prescribed** | no row's evidence was relocated to a narrower surface anywhere in this fold. Two candidates were refused and routed instead: 13A C5(b)'s structural clause (**card 8**) and 12 C1(m)/C1(n), whose evidence stays at the command boundary even though the defect lives in a request model |
| L-21 | **folded** | no cell in 12/13/13A discharges itself with "the dependency's own suite covers it"; 13A C1(b)'s cell says explicitly that `verify_location_tracker_webhook`'s own behaviour is phase 7's and is not re-proved here — the run at *this* surface is still recorded |
| L-22 | **owner** | 13A C5(d)'s `≤ 7` → **card 1**, with the exact counts derived in §7 Q3. Audited 12 and 13 for other `≤`/`≥` on a derived count: **none** |
| L-23 | **folded** | every shared cell now says which row's distinguishing assertion the second run is recorded against (12 C1(l), C3(c), C5(b), C6(b); 13A C1(b), C4(a)) |
| L-24 | **folded** | opposite-sign mutants where the invariant is bidirectional: 12 C4(e), 12 C4(f), 13 C1(d), all role cells. 13A C1/C2: the pairs are `deleted`↔`not_found` and they are separate rows already, so the cells name one mutant each and cite the sibling |
| L-25 | **folded** | every cell names a file and definition-vs-call site, and three sites were **corrected because the named site did not exist or was not load-bearing**: 13A C2(c) (`.limit(1)` → the in-memory `len(...) == 1` guard), 12 C1(c) (unsited "write anyway"), 12 C4(g) (the join shape, not "a filter") |
| L-26 | **folded as a citation** | `count_writes` already has its one positive observation for this project (batch B2 re-review, three writes observed). Recorded in 12 §7 and 13A §8 so no round re-buys it. 13A C2(a) is now the positive control of the `deleted` outcome |
| L-27 | process | nothing declined this round |
| L-28 | **folded** | "both runs recorded" on every mirrored cell (12 C1(e)/C1(l)/C3(c)/C5(b)/C6(b); 13 C4(b); 13A C1(b)/C4(a)) |
| L-29 | considered — **no instance in 13** | the residual §9A names is plan 13. I re-read every plan-13 row: none models an environment as a fixture; the closest (C1(c)'s "a demand delivery afterwards") is a real call to a real command, not a modelled premise. Nothing for the owner here |
| L-30 | **folded** | offered choices closed: 12's "via the demand service **or** ORM" → `AD` + raw-SQL seed; 13 C1(a)'s "(or `PR` once phase 9 is APPROVED)" → `move_assignment`, named; 13A's terminal-state path named per row in the new preamble |
| L-31 | **honoured** | every site substituted above was checked to execute under the row's own fixture. Two failed that check and were not substituted blindly: 13A C2(c) (see L-25) and 12 C2(a)/(b), where no site can arm the row at all (class 3) |
| L-32 | **assigned and folded** (had no target) | 12 C2(a)/C2(b) now state the *post-condition* the reviewer derives, not a statement to inspect. 13A C5(b) is the second instance and is **card 8** |
| L-33 | **satisfied by the batch shape** | this fold runs before the implementer, so no ruling lands after the tester's checkpoint. The eight cards must be ruled **before** the implementer prompt compiles, not after — that is the whole point of the lesson |
| L-34 | **assigned; folded where foldable** | 13 C1(d) and C4(d) already carry all three cells and now carry three mutants each. 13A carries all three (C2(f)/(g)/(h)). **Plan 12 carries one** → **card 4** |
| L-35 | **assigned; considered, not applicable** | 13A is the only batch-D batch command; its loop iterates the discovered candidate set (task 3 step 4.11) and C1(j)'s duplicate-identity 422 makes request-list iteration observationally identical. Recorded in 13A §8 |
| L-36 | **assigned and folded** | 13 C3(a): the `:updated`-for-R suppression is a *pair* (the cascade's event list and the coalescer's `:deleted` clause); either alone is an equivalent mutant. The cell now names the combination and says so |
| L-37 | **assigned and folded** | 13A step 4.10's `RuntimeError` is unreachable while rule Q1 holds — recorded in 13A §8 as dead-by-design, so no round tries to arm it and no reviewer files it |
| L-38 | **assigned to plan 14** | recorded in 14 §7: grep the whole repo, tests included, for how routes/roles/event names are actually written before calling the docs guard armed (the router uses imported role constants, not string literals) |
| L-39 | **folded** | every cell enumerating N plants now says N and "both/all runs recorded": 12 C1(h), C3(a), C4(e), C4(f), C7 cells; 13 C1(a), C1(d), C4(a), C4(b), C4(d); 13A C5(g) |

---

## 2. The 27 empty mutation cells — classified

Counts re-derived from the plan files: plan 12 **16**, plan 13 **6**, plan 13A **5** = **27**.
Result: **24 class 1 (foldable, written), 0 class 2, 3 class 3 (cannot fail — stated with the
mechanism).** Every class-1 site was checked against the shipped code or the plan's own task before
it was written (the measured precedent is that ~1 in 11 proposals is wrong at the site).

| Row | Class | Cell written / reason |
|---|---|---|
| 12 C1(f) | 1 | narrow the range guard to `1..n−1` → the `t == p == n` no-op becomes 422. C1(d)/C1(e) stay green under it, which is why the upper boundary is its own sub-check |
| 12 C1(k) | 1 | delete the `X == Y` short-circuit in the priority command → B re-appends at `high 3`, one record, non-zero `count_writes` |
| 12 C1(l) | 1 | same site, **the null branch**: write the guard as `if Y is not None and X == Y` → `null → null` falls through and re-writes/stamps/records |
| 12 C1(m) | 1 | widen the request model's `priority` to `str \| None` → `"urgent"` reaches the command. Rule-17 note attached (pydantic 2.11.3 rejects it by value) |
| 12 C1(n) | 1 | declare `priority_order` as plain `int` instead of `StrictInt` → **measured: pydantic 2.11.3 coerces `"2"` to `2`**, 200 no-op. The row is only decidable if the field is strict — this cell is where that contract is pinned |
| 12 C1(o) | 1 | drop the `workspace_id` term from the row lookup → the foreign row is moved |
| 12 C2(a) | **3** | **the interleaving is unforced** (§9 rule 9): two barrier-released sessions can serialise either way, so no mutant makes the row deterministically red. It is an invariant check. Post-condition stated in the cell (L-32). **Delegate named and verified:** C2(c) proves the advisory lock is taken, and its mutation (remove `acquire_stock_report_order_lock`) genuinely reddens — I read `_locks.py:13` and `create_task.py:99` and the lock is a real `pg_advisory_xact_lock`. **What C2(c) does not cover is stated in the cell:** the density invariant under an actual race. Nothing in this phase covers it |
| 12 C2(b) | **3** | identical reasoning; same delegate, same stated gap |
| 12 C3(c) | 1 | insert the history record **before** the short-circuit in both commands → one record per no-op. Shared site with C1(c)/C1(k)/C1(l)/C6(b); recorded against this row's record-count assertion |
| 12 C4(d) | 1 | strip empty tokens before the branch → `priority=` takes the unknown-token path and answers 422 |
| 12 C4(e) | 1 | two mutants at `serialize_stock_report_item`: add `item_type`, drop `properties_signature` |
| 12 C5(b) | 1 | add the stamp columns to `shift_within_group`'s SET list → A and B are stamped. Different site from C5(a)'s |
| 12 C6(b) | 1 | build the `:updated` event before the short-circuit → one event on a no-op |
| 12 C7(a)–(d) | 1 | the `PATCH …/priority` route's `require_roles([...])`, both directions |
| 12 C7(e)–(h) | 1 | the `PATCH …/priority-order` route's list — **a second route, not the same edit** |
| 12 C7(i)–(l) | 1 | the `GET …/items` route's list; four runs, one per role; no opposite direction (all four are "reached") |
| 13 C1(c) | 1 | drop `is_deleted = false` from `discover_live_rows_by_identity` → the demand updates the soft-deleted row instead of inserting |
| 13 C1(d) | 1 | three mutants, one per visibility cell (deleted / foreign / absent) |
| 13 C4(b) | 1 | three mutants across the three shipped serializers; observed-red set recorded across the suite because phase 8 rows redden too |
| 13 C4(d) | 1 | three mutants at the row lookup, one per visibility cell |
| 13 C5(a)–(d) | 1 | the `DELETE …/items/{client_id}` route's role list, both directions |
| 13 C5(e)–(h) | 1 | the `GET …/assignments` route's role list; four runs |
| 13A C1(b) | 1 | delete the `verify_location_tracker_webhook` call → the request applies. Shares its site with C1(a); both runs recorded, and the cell says phase 7 owns the verifier's own behaviour |
| 13A C1(e) | 1 | drop the `isinstance(payload, list)` term → a bare object is iterated as its key list. **The fixture was changed to make this bite**: `b"{}"` is caught by the emptiness term alone, so C1(e) could not discriminate the shape term independently of C1(d). It is now a non-empty unwrapped entry |
| 13A C1(h) | 1 | drop `.strip()` from the `itemCategory` non-blank check → `"  "` passes shape and answers 200 `category_not_found` |
| 13A C2(a) | 1 | report `deleted` without calling the cascade → the outcome is right and R is still live. This is the **positive control** of the C2 block: every `not_found` row stays green under it |
| 13A C4(a) | 1 | the same `is_deleted` drop as C4(b); the two rows assert different things, so both runs are recorded |

Three class-3 rows, and **not one of them delegates its evidence to a guard that does not perform
the check** — the batch C2 shape I was told to hunt. C2(a)/C2(b) delegate the *serialization* half
to C2(c), whose mutation I verified reaches a real advisory lock; the half C2(c) cannot cover is
now written into the cells instead of being implied. The only remaining unarmed promise in the
batch is 13A C5(b)'s structural clause — **card 8**, and it is forceable.

---

## 3. Plan 13A §7 — the six §14E questions, answered against the code

All six were re-derived from the shipped tree, not from the plan's summary. Two answers were
strengthened in the plan (Q1's path enumeration, Q3's exact counts).

**Q1 — any lock cycle?** *Answer holds; the plan's enumeration was a sample and is now complete.*
I read every Stock Report path that takes a lock and each ascends MC-1's classes:
`create_stock_task_assignments` 2→3→4 (`:89-91`), `delete_stock_task_assignments` 3→4→5 (`:78-80`),
`repair_stock_report` 1→3→4→5→6 (`:169-206`), `process_items_processed` 4→5 (+6 via the goal
credit, `:114-118`), `sync_task_stock_assignments` 3 (its own flushed task UPDATE) →4→5 (`:86-92`),
`apply_stock_demand` 4→6 only. `_locks.py:_lock` sorts by `client_id` inside every class. No path
takes a lower class after a higher one, so the wait-for graph is acyclic. Q1's consequence (i) is
real in shipped code: `apply_stock_demand:...` raises `RuntimeError` when the locked set is smaller
than the identity set, which is plan 6 C5(c)'s row. Consequence (ii) needs nothing from Manager.
The one premise outside this project is MC-1's "items before tasks" in foreign task commands, which
is MC-1's claim and not this phase's. **Settled.**

**Q2 — several rows, one group, both gaps closed?** *Answer holds, and it depends on a phase-13
property nobody has written down.* The plan is right that each cascade must close its gap from the
positions as they stand after the previous cascade. What makes that true is that the cascade reads
the row's `priority_order` **fresh** — the ORM instance locked at step 8 is stale the moment the
previous cascade's Core shift runs (§9 rule 3), and would send `close_priority_gap` the pre-shift
order. C5(b)'s named mutation is exactly that defect, so the row is armed. **But the module is
phase 13's, plan 13 never states the requirement, and 13A's §4 perimeter forbids editing it** —
see finding **F-1**. Recorded in plan 13 §7. **Settled, with F-1 routed.**

**Q3 — does the D6 statement bound apply?** *Answer holds ("no bound on the cascade"), and the find
step's bound is now exact.* Derived from the shipped `_demand_lookup.py` and task 3's step list,
calibrated against the §9 demand budget (`record_statements` does not see BEGIN/COMMIT: all-unchanged
demand = 5 and that reconciles): *all `not_found`* = **exactly 5**; *all `category_not_found`* =
**exactly 4** (discovery executes nothing on an empty identity list, and `_lock` executes nothing on
an empty id list). Both are size-independent, which is the property Q3 claims. **Settled → card 1.**

**Q4 — the replay instrument for a row whose cascade self-healed.** *Answer holds.* The first
delivery's repair record is written by `_move_assignment`'s inline self-heal with
`created_by_id=None` (verified: `_repair_records.write_repair_record` takes `created_by_id`, and
`move_assignment` passes the caller's trigger through). The replay reads `not_found` because
`discover_live_rows_by_identity` filters `is_deleted = false`, so nothing is written and nothing is
dispatched. C4(b)'s "still exactly one repair record" is the half that makes the row bite, and its
named mutation (drop `is_deleted = false`) reaches it. **Settled.**

**Q5 — the MC-20 check after a Scanner deletion.** *Answer holds, and I verified the two clauses
that could have made it vacuous.* `compute_stock_report_divergences` checks `goal_total` over **all**
history records of the workspace with no `is_deleted` filter (`consistency.py:200-208`), and
`_recompute_goal_totals_for_workspace` sums **all** assignments crediting a record, soft-deleted
included (`:84-98`) — which is MC-16's rule, and it is what makes C5(e)'s "stored 8 = A2 3 + A4 5"
a real assertion rather than a trivially empty one. It is also load-bearing in the other direction:
the cascade must *clear* A1's `credited_history_record_id`, or the recomputation keeps counting it
and `goal_total` diverges. `_goal_credit._uncredit` does clear it, before the subtraction
(`:63-70`). `task_flag` is checked over every task in the workspace. **Settled.**

**Q6 — the workspace reset is unaffected.** *Answer holds.* `reset_app.py:150-153` calls the four
stock phases in the registered order and **before** `delete_tasks` (`:162`); the phases take
`(session, workspace_id)` and hard-delete. C5(f)'s mutation (move them after `delete_tasks`) hits
the `stock_task_assignments → tasks` FK, which is `RESTRICT` by default, so it aborts — the row is
armable. This phase adds no table, column, migration or reset phase. **Settled.**

---

## 4. Decision ledger

| # | Decision the artifacts do not determine | Class | Routing |
|---|---|---|---|
| D-1 | **Where the cascade's `removed_order` comes from.** Plan 13 task 1 never says the gap close must read a fresh `priority_order`; the only evidence anywhere is 13A C5(b), and 13A may not edit the module | **plan gap** | Finding **F-1**; recorded in plan 13 §7 by this round; task text is **card 5**'s neighbour and the coordinator should fold the requirement into task 1 |
| D-2 | **How `client_id` reaches the three item-scoped commands.** §9B ruling 1 says the router injects it and the model drops it; no key is named, and §6.5's registered models carry no `client_id`. Phase 8A's shipped route sets `incoming_data={**body.model_dump(), "client_id": client_id}` and **keeps** `client_id: str` on the service-side model | **plan gap** (a `extra="forbid"` model validated against the enriched dict would 422 every request) | Coordinator: follow 8A's precedent and amend §6.5's two model shapes in the same act. Recorded in plan 12 §7 |
| D-3 | **The two `parse_*_request` wrappers plan 12 needs are not registered.** Only `bm.errors.validation.ValidationError` yields 422; a bare pydantic error becomes a 500 (§9A L-5's finding). §6.5 registers the two models but no parse functions, so §9 rule 18 has nothing to pin | **plan gap** | Coordinator: register `parse_set_stock_report_item_priority_request` / `…_priority_order_request` in §6.5. Recorded in plan 12 §7 |
| D-4 | **`priority_order` must be strict.** Plan 12 C1(n) expects 422 for `"2"`; a plain `int` field coerces it (measured, pydantic 2.11.3) | **plan gap**, rule 17 | Folded into C1(n)'s mutation cell and plan 12 §7 — the outcome is unchanged, so no card |
| D-5 | **Where `stock_report_item:deleted` is built.** §6.5's `_events.py` has no builder for it; `stock_report_item:created` is built inline in `apply_stock_demand.py`. Plan 13 does not say | **free choice** | Delegated in writing (plan 13 §7): either place is acceptable, but it is registered in §6.5 in the same act, and plan 14 C1(b)'s root must see it (**card 6**) |
| D-6 | **`_row_values` — a fourth copy or a shared helper.** The six-key snapshot 13A step 4.8 needs exists three times in the tree and in §6.5 not at all; it must match the coalescer's comparison exactly (`priority` as `.value`, never the enum) or an unchanged row still emits `:updated` | **free choice with a trap** | Delegated in writing (13A §8) with the trap stated; registering one shared helper is a §6.5 change → coordinator |
| D-7 | **Shared per-field validators for the two webhook parsers.** 13A §4 says "only if the validators must be exposed" — silent freedom over a phase-7 APPROVED file | **free choice** | Delegated in writing (13A §8) with a recommendation (extract, no behaviour change) and the cost of the alternative (MC-8 defect strings drift) |
| D-8 | **Which test file owns 13A C5(g).** The row exercises the demand command's two sorts; §4 gives it no home | **free choice** | Delegated in writing (13A §8): `test_process_stock_demand_deleted_locks.py`, which owns the two-session machinery |
| D-9 | **Do the two PATCH body models need `extra="forbid"`?** Batch C1's S1 added it to the three shipped body models; the intention requires unknown-field rejection for assignments (MC-13), not for priority | **free choice** | Delegated: follow the shipped convention (all four router body models carry it). No criterion depends on it either way |
| D-10 | **Batch D's split** (§3B: "decided at its projection") | **execution decision** | **D1 = 12 + 13** (64 rows / 13 criteria), **D2 = 13A + 14** (42 rows / 9 criteria). Reasons: 13A depends on 13 APPROVED and is the batch's whole risk concentration (multi-row cascade, two-session rows, the deadlock shapes); 14 depends on 13A, 11 and 10 and is documents-only, so it costs the D2 reviewer almost nothing; and D1 at 64 rows is the size C1 (93) and C2 (84) showed is already at the edge. F-1 is the clincher: D1 must **close** before D2 starts, because 13A's C5(b) is the only test of a phase-13 property |

---

## 5. Reality checks

**Paths and citations — all four plans.** Every path in every "Files expected to change" and every
"Read first" entry resolves, with two corrections applied and one noted:

- `architecture/07_queries_local.md`, `23_documentation.md`, `25_soft_delete.md` live at
  `backend/architecture/`, not `backend/docs/architecture/` — the plans cite them relatively and
  correctly.
- `create_task.py:99` is the advisory-lock statement ✓. `tasks.py:425-450` is the image batch-load ✓.
  `images/serializers.py:49` is `serialize_image_light` ✓. `test_phase7_concurrency.py` ✓.
  `connecteam_webhooks.py`, `location_tracker_webhooks.py` ✓. Scanner v2 handoff **§4A** exists
  (line 270) with §4A.1/§4A.3 as cited ✓.
- **Corrected (applied):** plan 12's two new test files were bare names (`test_priority_and_ordering.py`,
  `test_ordering_locks.py`) against §9 rule 19 — renamed with the domain prefix. Neither collides
  today; both are the shape that collided in batch C1.
- **Noted, not corrected:** plan 13 §4 lists `serializers.py` and `requests/__init__.py` as edited;
  both are stale (**card 5**).
- Housekeeping: a stale `__pycache__` entry for a deleted `_scratch_priority_check_test.py` sits in
  `app/tests/integration/services/commands/stock_report/`. Harmless; worth sweeping.

**Section citations.** Every intention section a batch-D plan cites was read and says what the plan
claims: §7/§7A MC-7 (the before/after table maps one-to-one onto plan 12 C1(a)–(l); the read order,
the filter and the race table match), §9/§9B (roles, response shapes, event list), §9E MC-18 (all
twenty role cells in 12 and 13 match §6.6 and the §9B role matrix exactly), §4B MC-17 (assignment
deletion leaves `updated_*` unchanged — 13A C3(a) is right and the shipped `move_assignment`
agrees), §5A MC-1/MC-16 (cascade order, the second self-heal trigger, instrument (c)), §14E E1–E13,
§14F F4/F10, §12A. One arithmetic disagreement found: §9B enumerates twelve compact-task fields and
plan 13 says eleven (**card 2**).

**Counts.** `SR/count_criteria.py`, run before and after the fold, unchanged both times:
plan 12 **45/7**, plan 13 **19/6**, plan 13A **37/7**, plan 14 **5/2** → batch D **106 rows / 22
criteria**; project **652 rows / 107 criteria**. These match the §4 tracker rows and the
`60812fb` commit message. No phase exceeds the eight-criteria cap (the largest here is 7).

**Mutation ledgers (§7).** Plans 12, 13, 13A and 14 carry **no** §7 mutation ledger — unlike plan 8,
their §7 is a Notes section (13A's is the carried-questions table). There is nothing to reconcile,
and the declared mutation set for manifest property 4 is the criteria table's fourth column. After
this fold that column is complete: **0 empty cells across all four plans**. The tester's ledger
should be derived from it, and several cells now declare two or three runs — the prompt for the
tester should say `declared` counts *runs*, not rows.

**Dependencies.** 12←5 (VERIFIED, clear). 13←12, 8 (8 VERIFIED; 12 same batch). 13A←13, 9. 14←13A,
11, 10. Phases 9 and 10 are IMPLEMENTED and **not yet VERIFIED** (batch C2's owner gate call is
outstanding) — I checked both C2 changes named in the prompt against batch D:
- **F-1's restoration of `state.in_(ACTIVE_ASSIGNMENT_STATES)` in the sync's discovery query**
  touches nothing batch D reads. 13A's own discovery is by identity, not by task.
- **`resolve_processed_group`'s new `from_state == target` short-circuit, early return and
  zero-delta guard** are reached only by the processed webhook. Batch D uses `PR` in **one** place —
  13A's preamble, as a way of reaching a terminal state in a fixture — and the new short-circuit
  cannot fire there (the fixture moves assignments *into* terminal states from active ones). Plan
  13 no longer uses `PR` at all after this fold (L-30). **Nothing in 13A or 14 assumes a 9/10
  behaviour that C2 changed.**

**CF-2 → plan 13A C5(g).** Present, authored by the owner in §9 (Review log, 2026-09-21), and
**armable at both named sites, which I verified in the shipped file**: `absent_identities = sorted(...)`
and `.order_by(StockReportItem.client_id)` on the `FOR UPDATE` select both exist in
`apply_stock_demand.py`. Its cell now carries the grounded exception shape.

**Rule 17 — the producibility pass** (the question only this session can ask). Every row in this
batch whose fixture, expected error or coerced value is owned outside our code:

| Row(s) | Shape owned outside our code | Grounding (installed versions) |
|---|---|---|
| 13A C5(a), C5(g) | "a deadlock … raises `DBAPIError` (SQLSTATE `40P01`)" | PostgreSQL **18.6**, `deadlock_timeout = 1s`, `lock_timeout = 0`, isolation `read committed` (read from the configured server). asyncpg **0.30.0** raises `DeadlockDetectedError`, `sqlstate = "40P01"`; SQLAlchemy **2.0.40**'s `_asyncpg_error_translate` matches it only at `PostgresError`, so it becomes the **base** `AsyncAdapt_asyncpg_dbapi.Error` and surfaces as `sqlalchemy.exc.DBAPIError` with `exc.orig.sqlstate == "40P01"`. The plan's claim is **right**; a test written against `OperationalError` would not catch it. Folded into both cells |
| 12 C1(n) | "`SO(B, "2")` (non-integer) → 422" | pydantic **2.11.3**: a plain `int` field **coerces** `"2"` to `2` in lax mode (measured). The row is producible **only** with `StrictInt` or a strict model. Folded into the cell and §7 (**D-4**) |
| 12 C1(m) | "`SP(B, "urgent")` → 422 (`ValidationError`)" | pydantic **2.11.3** rejects a value outside a str-enum and accepts `"high"`/`null`; an omitted key is itself an error (no default). Reaching 422 also requires the `parse_*_request` wrapper (**D-3**) |
| 13A C1(f)–C1(j) | raw-bytes JSON shapes | phase 7's, already grounded; `parse_stock_demand_body` ignores unknown keys, which is what makes C1(i)'s `quantityRequested` clause true |
| 13A C2(e), C1(j) | MC-3 normalization producing one identity from two spellings | verified against the shipped `normalize_stock_criteria`: `["Teak", " TEAK "]` → `["teak"]`, and `["Teak","Dark"]` / `["dark","teak"]` → the same signature. Both rows are producible |
| 13 C4(b), 12 C4(e) | serializer key sets | read off the shipped functions: assignment **14**, item **7**, task **12** (the plan says eleven — **card 2**) |
| 13A C5(f) | reset FK behaviour | `stock_task_assignments → tasks` FK is `RESTRICT` by default, so the mutation aborts as claimed |

No row in this batch fails the producibility question, and one (12 C1(n)) would have shipped a
green-and-fictional test without a strict field.

---

## 6. Findings, routed

| Id | Finding | Route | Severity |
|---|---|---|---|
| **F-1** | **The cascade's gap close must read a fresh `priority_order`, and nothing says so.** 13A runs the phase-13 cascade once per candidate row inside one transaction; after the first cascade's Core shift, the second row's ORM instance is stale (§9 rule 3), so `close_priority_gap(removed_order=row.priority_order)` would shift by the pre-shift order and leave the group non-dense. 13A **C5(b)**'s named mutation is exactly this defect, so the evidence exists — but the module belongs to plan 13, plan 13 never states the requirement, **and 13A's §4 perimeter explicitly forbids editing `_delete_stock_report_item_cascade.py`**. If phase 13 ships the ORM read, phase 13A cannot fix it without a perimeter violation | `plan` (→ plan 13 task 1) | **blocking for the D1 prompt.** Recorded in plan 13 §7 this round; the task-text edit is the coordinator's/owner's |
| **F-2** | **Plan 13 task 1 contradicts itself about `ctx`.** The same sentence that requires every stamp value to come from the cascade's arguments spells the row's soft-delete as `ctx.now`/`ctx.user_id`. The 13A path passes `actor_user_id=None`, so the contradiction lands as NULL-vs-actor stamps a phase later | `plan` | **card 5** |
| **F-3** | **Plan 13 asks for three serializers that shipped in phase 8** (owner ruling §9B.2). Task 3 and §4 are stale | `plan` | **card 5** |
| **F-4** | **"Eleven" task fields against a twelve-key function** | `plan` | **card 2** |
| **F-5** | **13A C3(a) enumerates five of six assignment states** — `in_progress` missing against E5's "any state" | `plan` | **card 3** |
| **F-6** | **13A C5(d)'s `≤ 7`** on a count this projection derived exactly (5 and 4) | `plan` | **card 1** |
| **F-7** | **Plan 12 carries one of the three visibility cells** for the priority commands | `plan` | **card 4** |
| **F-8** | **Plan 14 C1(b)'s guard root sees one of six event names**; as written the guard passes while five names can drift | `plan` | **card 6** |
| **F-9** | **Plan 14 publishes a third frontend document** in a different folder under a different name beside two live ones, and never mentions the match-preview endpoint (§14G / MC-21) that shipped today | `plan` | **card 7** |
| **F-10** | **13A C5(b)'s structural clause is the batch's last unarmed promise**, and it is measurable | `plan` / `verification` | **card 8** |
| **F-11** | 12 C1(n) is undecidable without `StrictInt` (rule 17) | `plan` | folded into the cell; **D-4** |
| **F-12** | §6.5 registers no `parse_*_request` for plan 12's two models, and §9 rule 18 has nothing to pin | `plan` (master plan §6.5) | **D-3**, coordinator |
| **F-13** | The `client_id` transport for the three item-scoped routes is unspecified; a `extra="forbid"` model validated against the enriched `incoming_data` would 422 everything | `plan` (master plan §6.5) | **D-2**, coordinator |
| **F-14** | `_row_values` is triplicated, unregistered, and its shape is load-bearing for the coalescer's no-op suppression | `plan` (master plan §6.5) | **D-6**, coordinator |
| **F-15** | 13 C4(b) duplicates phase 8's shipped key rows; kept deliberately (C6(a) needs both surfaces), recorded so the reviewer does not file it as over-evidence | note | recorded in plan 13 §7 |

---

## 7. Write perimeter

**Documents edited (4), all inside `SR/plans/`:**
`plan_12.md`, `plan_13.md`, `plan_13A.md`, `plan_14.md`.

**What changed in them:** 56 "Named mutation (site)" cells, 4 "Fixture / input" cells, 3 new §6
preambles, 4 note blocks appended to §7/§8, 2 test-file renames in plan 12 §4, and 2 answer cells
in plan 13A §7 (Q1's path enumeration, Q3's derived counts). **No outcome cell, no trace cell, no
task text, no row added or removed** — verified by re-running `count_criteria.py` before and after
(652/107 both times) and by a column-integrity check over all four §6 tables.

**Documents created (1):** this handoff.

**Not touched:** `master_plan.md`, `planning/intention.md`, any other plan, any production file,
any test file, any prompt, any other role's handoff. No archgraph delta was recorded (this round
produced no architectural change). No test suite was run — this round writes documents.

**Tree note:** another agent is writing into this tree concurrently (the card R-1 guard extension:
`_task_state_write_scanner.py`, `test_task_state_write_sites_are_registered.py`, `plan_10.md`, and a
new implementer handoff). My checkpoint commit names my five paths explicitly and touches none of
theirs.

---

## 8. Exit state

Verdict **AMENDMENTS_REQUIRED**. Every ledger row is routed: D-1 and D-2/D-3/D-6 to the coordinator,
D-4/D-5/D-7/D-8/D-9 delegated in writing inside the plans, D-10 decided. Eight findings need an
owner ruling and are the eight cards; the other seven are folded or routed to the coordinator.

**The implementer prompt compiles when the eight cards are ruled and F-1's requirement is in plan 13
task 1.** Recommended execution shape: **D1 = 12 + 13**, then **D2 = 13A + 14**, with D1 APPROVED
before D2 starts (F-1).

---

# 9. Addendum — the eight cards ruled and applied (2026-09-21)

Appended, never rewritten: §0–§8 above are the state at the moment the cards were raised and are
left exactly as they were. The orchestrator relayed the owner's delegated rulings — seven approved
as proposed, card 7 approved with a correction — and this section records what changed in the
plans. **F-1 is closed by card 5's third correction.** Verdict moves from AMENDMENTS_REQUIRED to
**PROJECTED — ledger fully routed**.

## 9.1 Every edit, by file and row

| Card | File | Row / section | What changed |
|---|---|---|---|
| 1 | plan 13A | **C5(d)** outcome | `≤ 7` → **exactly 5** (all `not_found`) and **exactly 4** (all `category_not_found`), identical at 3 and 30 entries, with the derivation named inline including the two early-return line refs the orchestrator verified |
| 1 | plan 13A | **§7 Q3** rule + status | "Making the cell exact is an owner card" → APPLIED; status now reads "no bound for the cascade; the find step is bounded **exactly**" |
| 2 | plan 13 | **C4(b)** outcome | "`task` keys exactly the eleven of §9B" → "exactly the **twelve** of §9B — `client_id` plus the eleven fields §2 lists" |
| 2 | plan 13 | **§5 task 3** | same substitution; the three key counts are now stated explicitly (7 / 12 / 14) so the two readings that produced the error cannot diverge again |
| 3 | plan 13A | **C3(a)** fixture | five assignments → **six**; `A6 in_progress q = 3` added on a sixth task/item, with the reason it is never credited (MC-5 credits on entering `awaiting`/`resolved_early`); counters `(1, 0, 2)` → **`(1, 3, 2)`**; `G == 10` unchanged and now explained |
| 3 | plan 13A | **C3(a)** outcome | "all five assignments" → **six**; "all five tasks'" → **six** |
| 3 | plan 13A | **C3(a)** mutation | kept both mutants, added why the sixth assignment matters from the other side: a filter keeping only *terminal* states would leave A3 and A6 alive, which the five-state fixture could not see |
| 3 | plan 13A | **C3(b)** fixture | "each of the five tasks" → **six** |
| 3 | plan 13A | **C3(d)** outcome | "five `stock_task_assignment:deleted`" → **six** |
| 3 | plan 13A | **C5(e)** fixture | "the identical row, group and five assignments" → **six** — *a consequence the card did not name; see §9.2* |
| 4 | plan 12 | **C1(o)** fixture, outcome, mutation | one foreign-row call → **three** calls (foreign / soft-deleted / absent); outcome "`NotFound` each; no state anywhere changes; the foreign workspace's group is byte-identical"; three mutants, one per visibility cell, all runs recorded |
| 5 | plan 13 | **§5 task 1** | split into three numbered stages so the loop boundary is unambiguous: **(i)** the assignment loop does `remove_assignment` and nothing else; **(ii)** *after the loop ends*, once, the fresh counter `SELECT` and the per-column repair; **(iii)** the gap close, the row soft-delete, the history soft-delete |
| 5 | plan 13 | **§5 task 1** | every stamp now reads `now` / `actor_user_id` — **the cascade's own arguments, never `ctx`** — with the reason inline (13A passes `actor_user_id=None`, so a cascade reading `ctx` cannot serve its second caller) |
| 5 | plan 13 | **§5 task 1** (**closes F-1**) | the gap close's `removed_order` now explicitly comes from a **fresh `SELECT` of the row's `priority_order`**, never from the ORM instance loaded at the lock, citing §9 rule 3 and 13A C5(b) as the only row that can observe it |
| 5 | plan 13 | **§5 task 3** | "Serializers: …" → "**this phase adds none**", with the three shipped shapes listed only as what task 2 consumes and re-adding them called a review finding |
| 5 | plan 13 | **§4** | dropped `serializers.py` and `requests/__init__.py` from the edited list, with the reason for each (§9B.2 moved the serializers to phase 8; §9B.1 removed the delete request model and `DELETE` takes no body) and a note that the perimeter check now treats a change to either as a finding |
| 5, 2 | plan 13 | **§7** notes | the three projection notes that said "owner card" now say **APPLIED** and name the card and date; the F-1 note gains the batch-split consequence |
| 6 | plan 14 | **C1(b)** fixture, outcome, mutation | root `_events.py` → **master plan §6.7 plus every `event_name=` site** under `bm/services/commands/stock_report/` (the `{kind}` template's three values included); the row now fails **in both directions**; two mutants, both runs recorded |
| 6 | plan 14 | **§5 task 4** | the guard's event-name clause rewritten to the same roots, with the reason the old root could not work and an instruction to state the roots in the test |
| 7 | plan 14 | **§4** | the third-file-in-another-folder entry replaced by the **supersession protocol** (see §9.2 for the correction I applied) |
| 7 | plan 14 | **§2** | read-first gains §14G/MC-21, the two shipped 8A modules, and **both already-published frontend documents** as item 5 |
| 7 | plan 14 | **§5 tasks 1 and 3** | task 1 now names thirteen routes including `POST /items/{client_id}/match-preview`; task 3 gains the current-document section, the `supersedes:` key, and match-preview with `item_category_id` **required** and a pointer to v2 for that endpoint's semantics |
| 7, 6 | plan 14 | **§7** notes | the three notes that described open cards now say **APPLIED** and carry the ruling |
| 8 | plan 13A | **C5(b)** outcome | the sentence "The reviewer verifies structurally that steps 3, 7, 8, 9 are each one statement — unforceable by a test" replaced by the **measured** clause: under `record_statements` the request issues exactly one advisory lock, one `tasks` `FOR UPDATE`, one `stock_report_items` `FOR UPDATE` and one `stock_task_assignments` `FOR UPDATE`, whatever the number of candidate rows |
| 8 | plan 13A | **C5(b)** mutation | two mutants → **three**, the new one being "take the class-4 and class-5 locks inside the per-row loop" → both counts become 2 while every other assertion in the row stays green |
| 8 | plan 13A | **§7 Q2** status | records that the one-statement-per-class half is now measured, not inspected |
| 8 | plan 13A | **§8** notes | new note: C5(b)'s measured clause depends on a master-plan edit this plan may not make, and rests on the note until §9 rule 7 carries it |

`count_criteria.py` re-run after every pass: **plan 12 45/7, plan 13 19/6, plan 13A 37/7, plan 14
5/2 — batch D 106/22, project 652/107.** Unchanged, as expected: no row was added, removed or
withdrawn, and no criteria group changed.

## 9.2 Where I did not simply transcribe — flagged rather than improvised

Three places where the ruling did not map one-to-one onto the plan's current wording.

**(a) Card 3 reaches a fourth row the card did not name.** The ruling says "update C3(a), C3(b)
counters and C3(d) to six". **C5(e)** also carries the number: its fixture seeds the foreign
workspace W′ with "the identical row, group and **five** assignments" — identical to C3(a)'s, which
is now six. Leaving it would have made C5(e) mirror a fixture that no longer exists. I applied
**five → six** there too. It changes no outcome (W′ is untouched by the webhook and the row asserts
`[]` either way). Say the word if you want it reverted.

**(b) Card 7's "`supersedes:` naming every document it replaces" — I read v2 as NOT replaced.**
The correction says to name every document the new handoff replaces, and separately that v2 is
correct, stays, and has no v3. The new API handoff will *describe* match-preview, which could be
read as partially replacing v2. I resolved it the narrow way: **v2 is neither listed in
`supersedes:` nor moved to `archived/`**; the new document points at it as the ratified source for
that endpoint's semantics, and only `HANDOFF_TO_FRONTEND_stock_report_api_20260921.md` is
superseded and archived. That keeps exactly one ratified statement of the preview contract and
avoids an archive move that would make the live contract harder to find. If you meant v2 to be
folded in and archived, that is a one-line change to plan 14 §4 — but it would need the owner,
because v2 is ratified.

**(c) Card 7's folder.** The ruling says "the SAME folder". The two published documents live in
`…/implementation/stock_report/handoffs/to_frontend/`, not in the repo-wide
`backend/docs/handoff/to_frontend/` that plan 14 originally named (that folder holds another
project's handoffs and a template). I used the project folder, since that is where "the existing
name" actually exists. The repo-wide folder is untouched.

## 9.3 FOR THE ORCHESTRATOR — master_plan §9 rule 7 addition

Card 8 authorizes a sixth use. I did not edit `master_plan.md`. Add this to §9 rule 7's
parenthesised list of authorized uses, after the fifth:

> and — **sixth use, owner card 8, 2026-09-21** — a *one-statement-per-lock-class* clause, where a
> batch command's promise is that each MC-1 lock class is acquired in exactly one sorted statement
> **whatever the number of entities in the request**, and the alternative is a reviewer inspecting
> statements by eye (plan 13A C5(b), §7 Q2)

Two notes for when you apply it. First, the rule's own sentence "It is never used to assert query
text or internal structure" still holds and should not be softened: this use counts **statements
per lock class**, which is an outcome of the batching promise, not the text of any query. Second,
plan 13A §8 now carries a note saying C5(b)'s measured clause rests on that note until §9 rule 7
carries the sentence — once you apply it, that note can be shortened to a pointer.

## 9.4 State after the rulings

Verdict **PROJECTED** — every ledger row routed, every card applied, zero owner cards open.
Remaining items are the coordinator's, unchanged from §4 and §6: **D-2** (`client_id` transport)
and **D-3** (the two `parse_*_request` wrappers) and **D-6** (`_row_values`) are §6.5 registry
edits; **F-15** is a recorded note. The batch split stands: **D1 = 12 + 13**, then **D2 = 13A +
14**, D1 APPROVED before D2 starts — card 5's third correction states the fresh-read requirement,
but 13A C5(b) is still the only test of it anywhere.
