# Batch C1 projection + lesson fold — plans 8 and 11

```
batch: C1
phases: [8, 11]
role: projection
round: 0
state: OWNER_DECISIONS_PENDING
verdict: AMENDMENTS_REQUIRED
date: 2026-09-21
actor: pipeline-projectionist (Opus 5, plan-projection)
tree: b95780b, clean (`git status --porcelain` empty)
intention gate: planning/intention.md status header = RATIFIED (round 9, 2026-09-19) — PASS
write perimeter: THIS FILE ONLY. No plan file, master plan, intention, source or test touched.
                 No commit, no `git add`, no archgraph write, no test run, no mutation run.
```

> **Tree note.** The prompt names `05ec920`. HEAD is now `b95780b` ("batch C1 dispatched — §3B
> mutation-cell policy amended"), the direct child of `05ec920`, tree clean. All line numbers and
> code quotations below are against `b95780b`.

## Owner-readable opening

I did the implementer's first hour on paper for the two plans in batch C1, and I tried to write a
mutation — a deliberate one-line break in the code — for every criterion that does not yet have
one, so that the tester does not have to invent them. The good news is that the counts are exactly
what the master plan says and that four of the five plans' mutation guesses hold up. The bad news
is concentrated: **three criteria in these two plans describe a situation the system cannot
actually get into**, and **two more describe a check that would still pass even if the code were
broken** — those are rows that would go green and prove nothing. Six of those need your signature
because fixing them means changing what a criterion claims, and only you write criteria. Nothing
else blocks: once the six are answered, the implementer prompt can be compiled.

## ⚠ OWNER DECISIONS REQUIRED (6)

### Card A — two "already assigned" rows cannot fail as written (plan 8 C1(j), C1(k))

**Question.** For the two rows that prove an item cannot be assigned twice, pick the repair:
(1) add a "nothing was inserted" clause, (2) give the item no category so the refusal reason
changes, or (3) accept them as unarmed and say so.

**Story.** A worker assigns a chair that is already on someone else's board row. Today they get a
clean 422, "already assigned", and nothing is written. If a future edit deleted the friendly
up-front check, the database's own uniqueness rule would still stop it and the code would still
answer 422 "already assigned" — same message, same status, nothing written. The test would stay
green through the very defect it exists to catch, and the next person to touch that code would
have no warning.

**Branches.**
- **(1) statement clause** — the row also asserts no insert was attempted. Strongest, but it is a
  new use of statement counting, which §9 rule 7 currently limits to four ratified cases, so that
  rule needs one sentence added in the same act.
- **(2) change the fixture** — give the item a NULL category too; with the up-front check deleted
  the answer becomes "item has no category" instead, so the row reddens. No new machinery, but the
  row now also depends on check ordering.
- **(3) accept unarmed** — mark both cells "no mutant: the database backstop produces the same
  observable" and move on. Cheapest, leaves two rows that cannot fail.

**Recommendation.** (2) — it arms both rows with a fixture change only, needs no rule amendment,
and the reason it produces is already in the closed vocabulary.

**On silence.** The gate holds; both cells stay `—`, and the tester is told they are known-unarmed.

**Trace.** plan 8 C1(j), C1(k); master plan §9 rule 7; intention §9C MC-13 phase 3.

---

### Card B — two plans disagree about whether one task can hold two assignments (plan 11 C1(c), plan 8 C6(g))

**Question.** Plan 11 builds a task with two assignments by re-assigning an item Scanner has
already reported; plan 8 refuses exactly that. Approve replacing both fixtures with the one
construction that actually works?

**Story.** A chair is repaired, Scanner reports it, and the assignment closes. A user tries to put
the same chair and the same task back on another board row. In round 9 you ruled that this is
refused — Scanner reports an item once, and a re-added pair would sit waiting forever. Two later
criteria were written as if that ruling did not exist, so as written they cannot be built at all;
whoever implements them will improvise, and improvisation at fixture time is how a test ends up
proving nothing.

**Branches.**
- **Approve the replacement** — build the second assignment through a *failed* one instead of a
  resolved one: create, move it to `failed`, then create again. Failed is terminal but is not one
  of the two states your ruling refuses, so the pair is legal and the task genuinely holds two
  non-deleted assignments. Both rows keep their outcomes word for word.
- **Withdraw both rows** — the "removes every assignment, not just the first" guarantee then has
  no test on either side.

**Recommendation.** Approve the replacement. It is a fixture change only, it keeps both outcomes
unchanged, and it is the only construction that survives your round-9 ruling.

**On silence.** The gate holds; plan 11 C1(c) and plan 8 C6(g) stay unbuildable and the implementer
must stop on them.

**Trace.** plan 11 C1(c); plan 8 C6(g), C1(p), C1(q); intention §14F F9.

---

### Card C — the lock-order promise still has no test of its own (plan 8, lesson L-29)

**Question.** Should plan 8 carry a new criterion row proving the two batch commands take their
locks in the ratified order, and if so, in the forceable form or the honest "cannot be forced" form?

**Story.** Two people press Assign at the same moment on overlapping work. The system's protection
against them corrupting each other is that every command grabs the same things in the same order.
Batch B wrote that order into a test fixture; when the reviewer deliberately broke it, all
sixty-three tests still passed, because one test lives in one transaction and a transaction cannot
collide with itself. So the promise is currently written down and unproven, and plan 8 is the first
place two real sessions exist.

**Branches.**
- **Forceable form** — one new row, two sessions, each creating two assignments naming the same two
  items in opposite request order; both calls must finish, neither may raise a deadlock. Proves the
  ordering, but I could not measure whether the deadlock is deterministic without running it.
- **Honest form** — mark it `UNFORCEABLE`, with the reviewer reading the command and confirming the
  four lock calls appear in order, as plan 11's two race rows already do.
- **Neither** — the promise stays unproven for the rest of the project.

**Recommendation.** Author the forceable form, and authorize the tester to fall back to the honest
form *with the reason recorded* if the deadlock does not reproduce deterministically. That is the
only branch that cannot end in a silent gap.

**On silence.** The gate holds; no row is added and plan 8's existing race row C5(a) remains the
only concurrency evidence.

**Trace.** plan 8 C5(a) and §7; master plan §9 rules 4 and 9; §9A L-29; batch B1 re-review S2.

---

### Card D — the create response row still describes the old seven-field shape (plan 8 C4(l))

**Question.** Approve the re-stated row that matches your 2026-09-21 ruling — the full fourteen-field
shape with the nested item and task?

**Story.** You ruled that creating an assignment returns exactly what reading one returns, so the
board can draw a newly created assignment without a second round trip. The plan's task text was
updated the same day; the criterion that checks the response was not, and still says "exactly the
seven keys". As it stands the implementer must obey one of two documents that contradict each
other, and the test would lock in whichever one it picked.

**Branches.**
- **Approve the re-statement** — the row asserts the fourteen keys of `serialize_stock_task_assignment`
  with its nested `item` and `task`. Text is drafted below and needs only your signature.
- **Leave it** — the contradiction ships into the implementer prompt.

**Recommendation.** Approve. Your ruling already decided the substance; this only moves it into the
cell that checks it.

**On silence.** The gate holds; the implementer prompt is not compiled with a row that contradicts
its own task text.

**Trace.** plan 8 C4(l), §5 task 2; master plan §9B ruling 2, §6.1.

---

### Card E — the "changing nothing is allowed" rows are protected twice, so they cannot fail (plan 11 C4(b), C5(b))

**Question.** Should the category guard decide on its own whether a change happened, instead of its
two callers deciding first — or should the two rows be marked unarmed?

**Story.** Someone saves an item form without touching the category. That must not be refused, and
two criteria say so. But the code will check "did it change?" twice — once in the caller and once
inside the guard — so breaking either check alone changes nothing observable. A test that stays
green no matter which half you break is decoration, and both halves are currently specified.

**Branches.**
- **One decision point** — the callers call the guard whenever the category field is present, and
  the guard alone decides. Both rows become armed by one precise break. Cost: an item row gets
  locked on saves that do not change the category.
- **Mark unarmed** — leave the design and write "no single-site mutant; protected twice" in both
  cells, so nobody mistakes the blank for an oversight.

**Recommendation.** Mark unarmed. Your ratified wording already describes the caller-side check,
the behaviour is right either way, and taking an extra row lock on every ordinary item save is a
real cost to pay for one test.

**On silence.** The gate holds; both cells stay `—` without a note, which is exactly the shape §3B
was written to stop.

**Trace.** plan 11 C4(b), C5(b), §5 tasks 5–6; intention §5B MC-14 row 4 and "made exact";
§9A L-10.

---

### Card F — one row asks a command to do something it structurally cannot (plan 11 C4(h))

**Question.** Withdraw the row that tries to change an item's category through task post-handling,
or replace it with a weaker one?

**Story.** The rule is that the category guard must sit deep enough to cover both ways an item gets
edited. The second way is the task post-handling step, which writes the item's storage zone when a
task completes. I read it: it builds its request with exactly two fields, the item id and the zone.
There is no way for it to change a category, so the row can never be built and the break it names
can never be observed. The guarantee is real; this particular test of it is not.

**Branches.**
- **Withdraw** — record in the plan's notes that the second caller cannot change a category, with
  the file and line, so the next reader does not re-derive it. The placement guarantee stays true
  and is enforced by there being one implementation point.
- **Replace with the inverse** — assert the second caller's zone update is *not* refused while an
  assignment is active. Constructible, but it duplicates what C4(c) already proves.
- **Add a structural guard** — a check that the only two places writing an item's category are both
  behind the guard. Real protection, but it is a new instrument for one row.

**Recommendation.** Withdraw. The second caller is one call site with two fields; a note naming it
is worth more than a test that cannot fail.

**On silence.** The gate holds; the row travels to the implementer, who cannot build it.

**Trace.** plan 11 C4(h); `complete_task_post_handling.py:120-129`; intention §5B MC-14 row 4.

---

## 1. Counts — measured, with the command

Script (written to the scratchpad, not to the repo): splits every table line on unescaped pipes,
keeps rows whose first cell matches `^C\d+\([a-z]\)`, and counts column 4 (`Named mutation (site)`)
equal to `—`.

```
python3 <<'PY'
import re
BASE="docs/architecture/under_construction/implementation/stock_report/plans/plan_%s.md"
for plan in ("8","11"):
    rows=[]
    for line in open(BASE%plan):
        s=line.strip()
        if not s.startswith('|'): continue
        c=[p.strip() for p in re.split(r'(?<!\\)\|', s)][1:-1]
        if len(c)<5 or not re.match(r'^C\d+\([a-z]\)', c[0]): continue
        rows.append(c)
    empty=[c[0] for c in rows if c[3] in ('—','-','–','')]
    print(plan, "table lines:", len(rows), "empty mutation cells:", len(empty))
    print("  ", ", ".join(empty))
PY
```

Measured result:

| Plan | Criterion **table lines** | Criterion **rows** (lines, compound ranges expanded) | Empty (`—`) mutation cells, by line | Empty cells, expanded |
|---|---|---|---|---|
| 8 | 60 | **66** | **26** | 32 |
| 11 | 27 | **27** | **8** | 8 |

**The count discrepancy is fully explained and is not a defect.** Plan 8 contains exactly two
compound table lines — `C8(a)–C8(d)` and `C8(e)–C8(h)` — each standing for four addressable rows.
`60 − 2 + 8 = 66`, which is what plan 8 §7 and master plan §4 both publish. Plan 11 has no compound
line: 27 = 27.

**The prompt's "plan 8 is published at 67 rows" is a transcription slip.** Nothing publishes 67 rows
for plan 8 (§7 and §4 both say 66). The number 67 in this project is master plan §3B's count of
batch C's empty **mutation cells** across all four plans: 26 + 18 + 15 + 8 = 67 (§9A). So §3B's
"67 cells", §9A's per-plan table and my measurement all agree.

**Empty-cell counts by line match §9A and Appendix A exactly** (plan 8: 26; plan 11: 8). I have
**not** reconciled or re-published any total, per the prompt.

## 2. The patch table

Authority: the orchestrator applies these; I edited no plan file (§3B, L-20).
`Class` is master plan §3B's classification. `Site verified?` means *I opened the named file at
`b95780b` and confirmed the symbol/line exists and executes under this row's own fixture* (L-31);
`n/a — new file` means the site is in code phase 8/11 will write, so only the plan text can
determine it.

Every mutation cell listed below currently reads exactly `—` (one em dash), so the "current text"
column is `—` unless stated. For fixture/outcome/note cells the verbatim current text is quoted.

### 2.1 Plan 8 — mutation cells

| Plan | Row | Cell | Current text (verbatim) | Proposed text (verbatim) | Class | Lesson(s) | Site verified? |
|---|---|---|---|---|---|---|---|
| 8 | C1(a) | mutation | `—` | `delete the phase-3 `stock_report_item_not_found` existence check (`create_stock_task_assignments.py`, definition site)` | 1 | L-10, L-25 | n/a — new file; check named verbatim in §5 task 2 |
| 8 | C1(d) | mutation | `—` | `delete the phase-3 task-existence check (`create_stock_task_assignments.py`) → the absent `task_id` falls through to `item_not_task_primary`` | 1 | L-10 | n/a — new file; fall-through verified against MC-13's order |
| 8 | C1(e) | mutation | `—` | `delete the phase-3 item-existence check (`create_stock_task_assignments.py`) → the absent `item_id` falls through to `item_not_task_primary`` | 1 | L-10 | n/a — new file; fall-through verified |
| 8 | C1(h) | mutation | `—` | `drop `failed` from the refused task-state set of the phase-3 `task_failed_or_cancelled` check (`create_stock_task_assignments.py`) → phase 5 reaches `move_assignment(is_creation=True, target=failed)` and raises `IllegalAssignmentMove` (500), not a refusal` | 1 | L-10 | **yes** — corrected (see §3.1) |
| 8 | C1(l) | mutation | `—` | `delete the phase-3 `item_has_no_category` check (`create_stock_task_assignments.py`) → the NULL-category item falls through to `category_mismatch`` | 1 | L-10 | n/a — new file; fall-through verified |
| 8 | C1(m) | mutation | `—` | `drop the row-category ↔ item-category comparison in phase 3 (`create_stock_task_assignments.py`) → the K2 item passes the matcher (F0's properties still derive `wood_group = Teak`) and is created on the K row` | 1 | L-10, L-19 | **yes** — matcher path read at `criteria_matcher.py:39-61` |
| 8 | C2(b) | mutation | `—` | `drop the repeated-`task_id` detection from phase 1, keeping only `item_id` (`create_stock_task_assignments.py`) → both entries reach phase 3 and the answer becomes `item_not_task_primary` @ 1` | 1 | L-10 | n/a — new file; one-PRIMARY-per-task verified at `add_item_to_task.py:47-57` |
| 8 | C3(f) | mutation | `—` | `remove the `min_length=1` constraint on `entries` in `CreateStockTaskAssignmentsRequest` (`requests/__init__.py`, definition site) → `{"entries": []}` no longer raises` | 1 | L-10 | n/a — new file; §6.5 registry names the model |
| 8 | C4(a) | mutation | `—` | `set the `TaskStateEnum.PENDING` cell of `ASSIGNMENT_STATE_BY_TASK_STATE` (`bm/domain/stock_report/state_map.py:5`, definition site) to `AWAITING` — **out-of-perimeter, plan 1; see §7**` | 1 | L-12, L-25, L-28 | **yes** — `state_map.py:5` |
| 8 | C4(b) | mutation | `—` | `set the `TaskStateEnum.ASSIGNED` cell of the same map (`state_map.py:6`) to `IN_PROGRESS` — **out-of-perimeter, plan 1; see §7**` | 1 | L-12, L-25 | **yes** — `state_map.py:6` |
| 8 | C4(d) | mutation | `—` | `set the `TaskStateEnum.STALLED` cell of the same map (`state_map.py:8`) to `IN_QUEUE` — **out-of-perimeter, plan 1; see §7**` | 1 | L-12, L-25 | **yes** — `state_map.py:8` |
| 8 | C4(e) | mutation | `—` | `set the `TaskStateEnum.READY` cell of the same map (`state_map.py:9`) to `IN_QUEUE` → kills state, `(0,0,4)` and the `G == 4` credit at once — **out-of-perimeter, plan 1; see §7**` | 1 | L-12, L-25 | **yes** — `state_map.py:9` |
| 8 | C4(g) | mutation | `—` | `replace `max(item.quantity, 1)` with the literal `1` at the phase-5 insert (`create_stock_task_assignments.py`) → A `quantity 1`, counters `(1,0,0)`. Distinct from C4(h)'s "drop `max(…,1)`": this one keeps a value, that one removes the floor` | 1 | L-12, L-28 | n/a — new file; expression named verbatim in §5 task 2 |
| 8 | C6(a) | mutation | `—` | `delete the `recompute_task_stock_flag(session, workspace_id, assignment.task_id)` **call** in `_remove_assignment.py:21` (call site) → the flag stays `true`; reaches the "flag false" sub-check only — **out-of-perimeter, plan 4; see §7**` | 1 | L-12, L-25, L-31 | **yes** — corrected symbol (see §3.1) |
| 8 | C6(b) | mutation | `—` | `delete the `await _uncredit(session, assignment, trigger, now)` call in `apply_goal_effect`'s `from_state == AWAITING` branch (`_goal_credit.py:129`, call site) → `G` stays 4 and the credit memory stays set — **out-of-perimeter, plan 5; see §7**` | 1 | L-24, L-25, L-31 | **yes** — `_goal_credit.py:113-131` read; DELETE reaches this branch because the sentinel matches no terminal target |
| 8 | C6(c) | mutation | `—` | `remove the `if any(value != 0 for value in deltas.values()):` guard around the `stock_report_item:updated` append (`_move_assignment.py:260-261`, definition site) → a `:updated` is emitted for a terminal delete — **out-of-perimeter, plan 4; see §7**` | 1 | L-10, L-25, L-28, L-31 | **yes** — corrected file (see §3.1) |
| 8 | C6(e) | mutation | `—` | `drop the `is_deleted.is_(False)` predicate from the delete command's discovery/re-read (`delete_stock_task_assignments.py`) → the soft-deleted assignment is found and re-removed instead of raising `NotFound`` | 1 | L-10, L-31 | n/a — new file; **`is_deleted` is `Boolean NOT NULL`** (`stock_task_assignment.py:84-86`), so the cell may not say `IS NULL` |
| 8 | C6(h) | mutation | `—` | `dispatch the delete events without `coalesce_stock_report_events` (`delete_stock_task_assignments.py`, call site) → two `:updated` for R. Same mutant *shape* as C7(a), different call site — both runs recorded (L-28)` | 1 | L-15, L-28 | n/a — new file |
| 8 | C8(a)–C8(d) | mutation | `—` | ``require_roles([...])` on `POST /api/v1/stock-report/assignments` (`bm/routers/api_v1/stock_report.py`, route decorator) — four mutants, one per sub-row, each run separately: drop `ADMIN` → (a) reddens · drop `MANAGER` → (b) · drop `WORKER` → (c) · add `SELLER` → (d)` | 1 | **L-12** | **yes** — decorator shape confirmed at `stock_report.py:27-30, 34-38` |
| 8 | C8(e)–C8(h) | mutation | `—` | ``require_roles([...])` on `POST /api/v1/stock-report/assignments/delete` — the same four mutants, one per sub-row` | 1 | **L-12** | **yes** — same pattern |
| 8 | C8(j) | mutation | `—` | `remove `StockAssignmentPropertyMismatch` from the router's explicit-rendering branch (`stock_report.py`, call site) → `build_err` renders `{"error", "ok"}` only, dropping `code` and `details` (status stays 409)` | 1 | L-10 | **yes** — `build_err` body read at `routers/http/response.py:14-24`; it emits no `code`/`details` |
| 8 | C3(d) | mutation | `—` | `— (deliberate blank, class 2)` **plus** the note in the row's Trace cell or a §7 bullet: `C3(d) has no site: "re-evaluated from scratch" is not a branch any task mandates — each request is stateless, so the only mutant would invent caching that no implementation has. Its observable equals C1(i)'s, which is armed. The tester sites it on real code or declares it equivalent; it is not an oversight.` | **2** | L-10, §3B class 2 | n/a — by construction |

### 2.2 Plan 8 — fixture / note cells (class-3 repairs that fold)

| Plan | Row | Cell | Current text (verbatim) | Proposed text (verbatim) | Class | Lesson(s) | Site verified? |
|---|---|---|---|---|---|---|---|
| 8 | C4(k) | fixture | `two entries on R (two tasks/items)` | `two entries on R — a second task T2 with a second item I2 (a copy of I: `quantity 4`, same properties, PRIMARY on T2), **supplied in the request ordered descending by `item_id`**, computed at runtime from the two created ids and never from creation order (ULIDs minted in one millisecond have random relative order — master plan §10)` | 3 → fixture fold | L-14, L-15, L-17, L-30 | **yes** — ULID randomness read at `ulid/__init__.py:120` |
| 8 | C4(k) | mutation | `—` | `drop the ascending-`item_id` sort at the phase-5 write loop (`create_stock_task_assignments.py`) → the response lists the two in request order, i.e. descending` | 1 (after the fixture fold) | L-14, L-15 | n/a — new file |
| 8 | C6(h) | fixture | `` `DL([A, B])` two assignments on R `` | `` `DL([A, B])` — two active assignments on R (a second task/item pair matching R's category and criteria), **labelled so that A's `client_id` sorts before B's**, since ULIDs minted in one millisecond have random relative order (master plan §10) `` | 3 → fixture fold | L-15, L-17 | **yes** — same ULID evidence |
| 8 | C1(p) | fixture | `A on (T, I) driven to `resolved` in the fixture (`move_assignment(awaiting → resolved)`, as C6(c) does); `CR([I on R])` again` | `A on (T, I) created by `CR` (T `pending` → `in_queue`), then `move_assignment(in_queue → awaiting)` and `move_assignment(awaiting → resolved)` — the intermediate move is required, `awaiting → resolved` is the only Scanner exit (MC-1); `CR([I on R])` again` | 3 → fixture fold | L-17, L-30 | **yes** — `_assert_allowed_move` at `_move_assignment.py:60-79` |
| 8 | §6 preamble | note | *(append after "Every success row ends with `assert_stock_report_clean`.")* | `Every outcome in this table is computed from **F0**'s own values (I `quantity 4`, R `quantity_requested 10`, goal G awaiting 0) plus this row's own deltas, side effects included. Where a row names a second task or item, it is a copy of F0's unless stated. An outcome that disagrees with its own fixture is a plan defect: report it, never reconcile it in the test.` | fold | **L-17 (preamble half)** | n/a |
| 8 | §6 preamble | note | *(append)* | `Tenancy rows (C1(c), C6(f)) use a **cross-workspace reference**: the foreign entity is otherwise a valid target of this request (same category, same criteria, same PRIMARY link), so tenancy is the only reason the call refuses.` | fold | **L-16** | n/a |
| 8 | §7 | note | *(new bullet)* | `**Perimeter extension for mutation probing (2026-09-21 fold).** Five named mutations in §6 land in files belonging to APPROVED phases: `bm/domain/stock_report/state_map.py` (plan 1 — C4(a), C4(b), C4(d), C4(e)), `_remove_assignment.py` (plan 4 — C6(a)), `_move_assignment.py` (plan 4 — C6(c)), `_goal_credit.py` (plan 5 — C6(b)), and `apply_stock_demand.py` (plan 7 — C4(m), already declared above). Applying and reverting a probe in these files is **authorized for this phase's tester**; leaving any change is not. Collateral reds, measured by reading: each `state_map.py` cell mutant reddens exactly one parametrized case of plan 1's `app/tests/unit/domain/stock_report/test_state_map.py::test_task_state_map_is_exact`, and every F0-based test of plans 4–11 when the mutated cell is `PENDING`; plan 1 C6(a) and C6(j) stay **green** under all four (the key set and the value *set* are unchanged). That is expected, not a regression.` | fold | **L-20**, L-25, L-27, L-28 | **yes** — plan 1's test file read in full |
| 8 | §7 | note | *(new bullet)* | `**L-20, 2026-09-21.** Relocating a row's test to a narrower surface is a criterion change and is the owner's alone. C4(m)'s relocation to the demand test file is owner-authorized (batch B2 card 1, 2026-09-21) and is the only one in this phase; no implementer or tester may make another.` | fold | **L-20 (lands first)** | n/a |
| 8 | §4 | files | `New: `bm/services/commands/stock_report/requests/__init__.py` (or extended if phase 3 created it), `create_stock_task_assignments.py`, `delete_stock_task_assignments.py`;` | `New: `bm/domain/stock_report/serializers.py` (`serialize_stock_task_assignment`, `serialize_item_compact`, `serialize_task_compact` — master plan §6.1; **due in this phase** by the owner ruling of 2026-09-21, §9B ruling 2), `app/tests/unit/domain/stock_report/test_serializers.py`; `bm/services/commands/stock_report/requests/__init__.py` (or extended if phase 3 created it), `create_stock_task_assignments.py`, `delete_stock_task_assignments.py`;` | **reality-check gap** | — | **yes** — `bm/domain/stock_report/` contains no `serializers.py` at `b95780b` |

### 2.3 Plan 11 — mutation cells

| Plan | Row | Cell | Current text (verbatim) | Proposed text (verbatim) | Class | Lesson(s) | Site verified? |
|---|---|---|---|---|---|---|---|
| 11 | C2(c) | mutation | `—` | `remove the PRIMARY-unlink removal hook from `remove_item_from_task.py` (call site, before the `TaskItem` write) → A survives the swap, so no-non-deleted-assignment fails and `CR([J on R])` hits `uix_stock_task_assignments_task_active` and is refused by the `IntegrityError` backstop. Same code edit as C2(a): both runs recorded, and this cell's bite is the `CR` half (L-28)` | 1 | L-10, L-28 | **yes** — index predicate at `stock_task_assignment.py:103-110`; host file `remove_item_from_task.py:23-33` |
| 11 | C3(b) | mutation | `—` | `restrict the `delete_item` hook's assignment query to `ACTIVE_ASSIGNMENT_STATES` (`delete_item.py`, call site) → the `failed` assignment is left non-deleted. Twin of C1(b) on the item side; both runs recorded (L-28)` | 1 | L-10, L-28, §9 r16 | **yes** — host file `delete_item.py:26-37` |
| 11 | C5(d) | fixture | `I with no active assignment; `create_task` with `K2`` | `I with **no assignment at all** (the choice that keeps this row armed — with a terminal assignment a weaker "widen the lookup to any non-deleted assignment" mutant would also kill it, and that finer mutant is already carried by C4(f)/C4(g) on the `update_item` caller); `create_task` with `K2`` | 1 (fixture named) | **L-30**, L-28 | n/a — fixture-side |
| 11 | C5(d) | mutation | `—` | `delete the active-assignment lookup in `assert_item_category_change_allowed` (`_category_guard.py`, definition site) and refuse whenever the incoming category differs → 409 instead of a created task` | 1 | L-10, L-30 | n/a — new file |
| 11 | C5(e) | mutation | `—` | `delete the `assert_item_category_change_allowed(...)` call from `find_or_create_item.py`'s existing branch (call site, before `:98`) → no refusal on either caller. Same code edit as C5(a): both runs recorded, and this cell's bite is the items-route ctx (L-28)` | 1 | L-10, L-28 | **yes** — existing branch at `find_or_create_item.py:95-119`; first write to `existing` is the `setattr` at `:100`, loop head `:98` |
| 11 | C6(a) | mutation | `—` | `pass `trigger="manual"` instead of `trigger="delete_task"` at `delete_task.py`'s `remove_assignment` call (call site) → the repair record's trigger reads `inline:manual`` | 1 | L-10 | **yes** — the record's trigger is built as `f"inline:{trigger}"` at `_move_assignment.py:163` |
| 11 | C6(b) | mutation | `—` | `the same substitution at `remove_item_from_task.py`'s `remove_assignment` call (call site) → `inline:manual` ≠ `inline:remove_item_from_task`` | 1 | L-10, L-28 | **yes** — same chain |
| 11 | C6(c) | mutation | `—` | `the same substitution at `delete_item.py`'s `remove_assignment` call (call site) → `inline:manual` ≠ `inline:delete_item`` | 1 | L-10, L-28 | **yes** — same chain |
| 11 | C5(b) | mutation | `—` | `— (deliberate blank, class 3)` **plus** a §7 bullet: `C5(b) and C4(b) have no single-site mutant: "setting the same value is not a change" is guarded twice — the caller's own `differs` term (§5 tasks 5–6) and the guard's `incoming == current` short-circuit (§5 task 1). Dropping either alone is an **equivalent mutant**, because the other still short-circuits. See owner card E.` | **3** | **L-10**, L-12 | **yes** — the double guard is stated in §5 tasks 1/5/6 and in intention §5B MC-14 |

### 2.4 Plan 11 — fixture / note cells

| Plan | Row | Cell | Current text (verbatim) | Proposed text (verbatim) | Class | Lesson(s) | Site verified? |
|---|---|---|---|---|---|---|---|
| 11 | C4(i) | fixture | `` A `resolved_early` only (via `PR` while T `pending`); change category `` | `` A `resolved_early` only, reached with `move_assignment(in_queue → resolved_early)` — **`PR` (phase 9) is not available: the owner split batch C into C1 = 8 → 11 and C2 = 9 → 10, so 11 runs before 9 (master plan §3B)**; change category `` | 3 → fixture fold | **L-30**, L-17 | **yes** — the move is legal, `_move_assignment.py:73-79` |
| 11 | C1(c) | fixture+outcome | *the whole row, verbatim below* | *see §3.2 — owner card B* | **3** | L-10, L-17, L-30 | **yes** |
| 11 | C2(c) | fixture | `swap: `remove_item_from_task(T, I)` then `add_item_to_task(T, J as PRIMARY)`` | `swap: `remove_item_from_task(T, I)` then `add_item_to_task(T, J as PRIMARY)`, where **J is a copy of I** (same category K, same properties, so `CR([J on R])` clears MC-13's category and matcher checks)` | fold | **L-17 (preamble half)** | **yes** — `add_item_to_task.py:47-57` allows the add once I's link carries `removed_at` |
| 11 | §6 preamble | note | *(append after "Every row ends with `assert_stock_report_clean` unless drift is planted.")* | `Every outcome is computed from **F0**'s own values (I `quantity 4`, R `quantity_requested 10`, goal G awaiting 0) plus this row's own deltas, side effects included; a second item or task named by a row is a copy of F0's unless stated. **`PR` is not available in batch C1** (phase 9 is batch C2): a terminal assignment is reached with `move_assignment` directly. An outcome that disagrees with its own fixture is a plan defect: report it, never reconcile it in the test.` | fold | **L-17 (preamble half)**, L-30 | n/a |
| 11 | §7 | note | *(replace the second half of the round-9 bullet)* | `Round 9 (2026-09-19): C4(i) added — the category guard reads the active frozenset, so the sixth terminal state does not block a category change. **The coordinator did reorder: batch C1 is 8 → 11 and phase 9 is batch C2, so `PR` does not exist when this phase runs. C1(c) and C4(i) therefore reach their terminal states through `move_assignment` directly** (master plan §3B).` | fold | L-30 | n/a |
| 11 | §7 | note | *(new bullet)* | `**Foreign fixture-side dependencies (2026-09-21 fold, L-25).** Two rows depend on files no plan names: C2(c) on `tasks/add_item_to_task.py` (its one-active-PRIMARY-per-task check, `:47-57`, is what makes the swap and C1(c)'s construction behave as the row assumes) and C4(h) on `task_post_handling/complete_task_post_handling.py:120-129`. Both are registered in master plan §6.1b.` | fold | **L-25** | **yes** — both files read |

### 2.5 Master plan — standing-rule proposals (lesson fold, order fixed)

| Target | Cell | Proposed text (verbatim) | Lesson |
|---|---|---|---|
| §9, **new rule 17** (lands first) | standing rule | `17. **Relocating a row's test to a narrower surface is a criterion change, and criterion changes are the owner's.** Moving a row's evidence from the boundary its outcome names to a cheaper one — a command row proven at its parser, an endpoint row proven at a helper — changes what the row claims even when the assertion text is identical. An implementer or tester that judges a relocation necessary declares it and stops; the owner authorizes it, and the plan's cell is amended in the same act. Earned: batch B2 review 1 B1/S1 (four rows proven at parser scope) and batch B2 card 1 (plan 8 C4(m)'s one-file relocation, which the owner did authorize).` | **L-20** |
| §9 rule 8 | amendment (append) | `A mutation ledger is scoped to a **test id**, never to a mutant: a test that moves re-runs its mutations at the new surface, and a cell shared between two rows must be shown to reach the **second** row's distinguishing assertion before one run may discharge both. "The dependency's own suite covers it" and "it is the same code edit" are claims to be measured in this round, never substitutes for a run.` | **L-21 + L-23 + L-28** (the §9A cluster, folded as one) |
| §6.1b | new registry row | `\| `bm/services/commands/tasks/add_item_to_task.py` \| the one-active-PRIMARY-per-task check (`:47-57`) and the `removed_at IS NULL` duplicate check (`:59-68`) \| MC-13's `item_not_task_primary` and MC-14's "a swap is removal then add" — and, negatively, the constructibility of plan 8 C6(g) / plan 11 C1(c): because a task holds one PRIMARY item, "one task with two assignments" is reachable only as terminal + active for the same item \| batch C1 projection, L-25 \|` | **L-25** |
| §10 | new environment fact | `**`client_id` order is not creation order.** `IdentityMixin` mints `f"{prefix}_{ULID()}"` (`bm/models/base/identity.py:11`); `python-ulid` 3.0.0 fills the 80-bit randomness with `os.urandom` and keeps **no monotonic counter** (`ulid/__init__.py:120`). Two ids minted in the same millisecond therefore have random relative order. No fixture may assume that the first row created sorts first; a criterion asserting an ascending-`client_id` or ascending-`item_id` order binds its labels by sorting the real ids at runtime. (Charter rule 17 — the shape is owned by a dependency. Affects plan 8 C4(k), C6(h) and every `ascending client_id` claim in §6.5.)` | rule 17, L-15 |

### 2.6 Lessons checked and found already satisfied (no patch)

| Lesson | Where it would land in 8/11 | Finding |
|---|---|---|
| **L-9** (rule-17 rows carry the rule next to the literal) | plan 8 C3(a) | Already satisfied: the fixture cell names "H8's rule" and the trace cell cites `MC-12 (H8)`. No change. |
| **L-13** (inverse directions each need their own assertion) | plan 11 C4(d)/C4(e) | Already satisfied: `None → X` and `X → None` are two separate rows with two opposite mutants. No change. |
| **L-16** (tenancy needs a cross-workspace *reference*) | plan 8 C1(c), C6(f) | Rows are correct; only the §6 preamble clause above is added, so the foreign entity is otherwise valid. |
| **L-24** (bidirectional invariant, one mutant per direction) | plan 8 C3, plan 11 C6 | plan 8 C3(b)/C3(c) already carry opposite-sign mutants (`store false` / `store the flag as sent`). plan 11 C6's inverse ("no drift → no repair record") is carried by `assert_stock_report_clean` on every other row. No change. |
| **L-5** (a row whose outcome is an error identity pins the identity) | plan 8 C3(e), C3(f) | **Not blocked, so no card.** "`ValidationError` 422" is unambiguous in this repo: pydantic's own `ValidationError` escaping a command reaches `run_service`'s generic handler and becomes a 500 (`run_service.py:44-63`), so only `bm.errors.validation.ValidationError` can produce 422. The house pattern that converts it (`parse_update_item_request`, `items/requests/__init__.py:443-451`) is registered for these models in master plan §6.5. Recorded, not folded. |

## 3. Class-3 rows in full

### 3.1 Three Appendix-A proposals that were wrong at the site (kept class 1, corrected)

These are **not** class-3 rows; I list them here because a binding cell copied from Appendix A
would have been wrong, which is exactly the L-31 failure the fold protocol exists to prevent.

1. **plan 8 C6(a).** Appendix A: *"in `_remove_assignment.py`, drop the `set_task_stock_flag(..., False)` call."*
   **That symbol is not at that site.** `_remove_assignment.py` (24 lines, read in full) calls
   `recompute_task_stock_flag(session, workspace_id, assignment.task_id)` at `:21`;
   `set_task_stock_flag` lives in `_task_flag.py` and is called by `recompute_task_stock_flag` and
   by `repair_stock_report`. Mutating `set_task_stock_flag` would also hit plan 3's repair path.
   Corrected cell in §2.1.
2. **plan 8 C6(c).** Appendix A: *"in `_remove_assignment.py`, treat a terminal assignment like an
   active one — same mutant C6(i) names."* `_remove_assignment.py` contains **no state logic at
   all**; the delta decision is `_delta_vector` in `_move_assignment.py:91-99`. Worse, the literal
   edit Appendix A describes (drop `from_state in ACTIVE_ASSIGNMENT_STATES`) raises `KeyError` —
   `_COUNTER_COLUMN` (`:37-41`) has no `resolved` key — so it reddens by crashing everything rather
   than by producing a wrong counter. I replaced it with the precise single-sub-check mutant: remove
   the `if any(value != 0 …)` guard at `_move_assignment.py:260`, which reaches exactly C6(c)'s
   "no `:updated`" clause. **What it does not reach:** the "no counter change" clause, which is
   already discharged by plan 4's own terminal→DELETE rows; adding a second mutant there would be
   over-evidence.
3. **plan 8 C1(h).** Appendix A predicts *"the entry is created"*. It is not.
   `ASSIGNMENT_STATE_BY_TASK_STATE[FAILED]` is `FAILED` (`state_map.py:11`), and
   `_assert_allowed_move` refuses any creation whose target is not active
   (`_move_assignment.py:61-64`), so the mutant produces `IllegalAssignmentMove` → 500. The test
   still reddens, but the cell must not state a consequence that cannot happen (L-10).
   **The same defect sits in C1(i)'s already-filled cell** ("allow cancelled"): `CANCELLED` also
   maps to `FAILED`. Reported in §7 as a passing observation; it does not block C1.

Also corrected without ceremony: **C6(e)** — `is_deleted` is `Boolean NOT NULL`
(`stock_task_assignment.py:84-86`), so the cell may not say `is_deleted IS NULL`.

### 3.2 plan 11 C1(c) — the fixture contradicts plan 8 (owner card B)

*Current text, verbatim:*

> `| C1(c) | T with A active on R and B resolved on R2 (a second item is impossible — one active per task; use A active + a resolved earlier assignment of the same item on R2 that a new active replaced? **not constructible**: a task has one PRIMARY item; use A `awaiting` then `PR` resolves it, then `CR` refused… ) — **row withdrawn at planning**: one active per task and one PRIMARY per task make "two assignments on one task in different states" reachable only as terminal + active for the same item on two rows: build A resolved on R (via `PR`) then `CR` on R2 for the same item → B active; `delete_task(T)` | both A and B soft-deleted; R2's counters `(0,0,0)`; R's unchanged; flag false | remove only the first found | MC-14 "every non-deleted assignment of the task" |`

*The defect.* Intention §14F F9 is explicit and is the strongest amendment: creating an assignment
for a `(task_id, item_id)` pair that already has a non-deleted `resolved` **or** `resolved_early`
assignment is refused, `already_processed_by_scanner`, **on any row**. Plan 8 C1(p)/C1(q) implement
exactly that. So `CR` on R2 for the same item after `PR` resolved it on R cannot succeed, and the
cell's construction cannot be built. **Plan 8 is right; plan 11's fixture is wrong.** The cell also
carries its own abandoned planning monologue, which is unreadable as a directive.

*Minimal fix (proposed row text, outcome and mutation unchanged):*

> `| C1(c) | T holds two non-deleted assignments — the only reachable shape: `CR([I on R])` → A `in_queue`; `move_assignment(A, failed)` (terminal, and **not** one of the two states §14F F9 refuses); `CR([I on R2])` → B `in_queue`; `delete_task(T)` | both A and B soft-deleted; R2's counters `(0,0,0)`; R's unchanged; flag false | remove only the first found | MC-14 "every non-deleted assignment of the task", §14F F9 |`

*Why it is constructible, verified by reading:* `move_assignment(..., FAILED)` from any active state
is allowed (`_move_assignment.py:69-70`); `failed` is not in `ACTIVE_ASSIGNMENT_STATES`, so neither
partial unique index applies (`stock_task_assignment.py:93-110`); §14F F9 names only `resolved` and
`resolved_early`; `item_already_assigned` looks for an **active** assignment (MC-13 phase 3); and T
stays `pending` throughout, so `task_failed_or_cancelled` never fires.

*Whose authority:* the outcome cell is unchanged, so this is a fixture-cell repair that §3B would
let the orchestrator fold. I raise it as a card anyway because it resolves a **contradiction between
two plans** and the prompt reserved it for you.

### 3.3 plan 8 C6(g) — the same contradiction, item side (owner card B)

*Current text, verbatim:*

> `| C6(g) | T has A (active) and B (resolved, another item legal); `DL([A])` | flag stays true | — | MC-15 (P21) |`

*The defect.* "another item" is impossible: a task has one active PRIMARY item
(`add_item_to_task.py:47-57`), and `item_not_task_primary` refuses any other. Forced onto the same
item, the pair becomes resolved-then-active, which §14F F9 refuses. Appendix A blamed the
`(workspace_id, task_id)` partial index; that is only the *reverse* order's blocker — the forward
order is blocked by the round-9 refusal, which is the newer and stronger reason.

*Minimal fix (same construction as C1(c)):*

> `| C6(g) | T has A (`in_queue`, via `CR`) and B — the only reachable second assignment: a **`failed`** one on the same item, built as `CR([I on R2])` → `move_assignment(→ failed)` **before** A is created, so neither active index nor §14F F9 applies; `DL([A])` | flag stays true | drop the "any non-deleted assignment of this task" term from `recompute_task_stock_flag`'s predicate (`consistency.py:expected_task_flag`) → the flag goes false | MC-15 (P21), §14F F9 |`

Note the build order is reversed relative to C1(c): B must reach `failed` before A exists, because
one task may hold only one **active** assignment. The mutation cell is filled at the same time
because the row currently has none and the site is real and shipped
(`bm/services/queries/stock_report/consistency.py:expected_task_flag` — out of perimeter, plan 3;
covered by the §7 declaration in §2.2).

### 3.4 plan 8 C1(k) and C1(j) — the row cannot fail (owner card A)

*Verified premises.* `uix_stock_task_assignments_item_active` is unique on `(workspace_id, item_id)`
`WHERE is_deleted = false AND state IN ('in_queue','in_progress','awaiting')`
(`stock_task_assignment.py:93-102`, and the same in the shipped migration
`10d97764a5a7_create_stock_report_tables.py:369`). Plan 8 §5 task 2 maps an `IntegrityError` in
phase 5 to `StockAssignmentRefused` with `item_already_assigned`. So deleting the phase-3
pre-check leaves the observable identical: 422, `code stock_assignment_refused`, reason
`item_already_assigned`, nothing persisted. **C1(j)'s already-filled cell ("check only the same
row") fails the same way**, because the index is keyed on the item, not the row.

*Options with exact text* (card A):
- **(1) statement clause.** Outcome cell gains `; `count_writes(statements, {"stock_task_assignments"}) == 0`
  over the call (`record_statements`)`. `record_statements` attaches `before_cursor_execute`, so the
  backstop's attempted INSERT **is** recorded even though it rolls back — the clause discriminates.
  It needs master plan §9 rule 7 to gain a fifth ratified use in the same act.
- **(2) fixture change (recommended).** Fixture cell becomes
  `I already active on R **and** I's `item_category_id` raw-set to NULL after that assignment was
  created (a category-less item cannot be assigned, MC-13)`. Outcome unchanged
  (`item_already_assigned` @ 0). Mutation cell becomes `delete the phase-3 `item_already_assigned`
  check → the next matching reason in MC-13's order, `item_has_no_category`, is returned instead`.
  Precedent for the raw NULL: plan 11 C4(d) and its §7 note.
- **(3) accept.** Both cells become `— (no mutant: the partial unique index on `(workspace_id,
  item_id)` plus the `IntegrityError` backstop reproduce the same 422 and the same reason; the row
  is known-unarmed)`.

### 3.5 plan 8 C4(l) — the outcome contradicts its own task (owner card D)

*Current text, verbatim:* `| C4(l) | response shape | each element has exactly the seven keys of task 2 | — | §9 |`

Plan 8 §5 task 2 now says the response is the fourteen-key `serialize_stock_task_assignment` shape
with nested `item` and `task` (owner ruling 2026-09-21, master plan §9B ruling 2), and says in the
same paragraph that the rows naming the seven-key shape "are re-stated during the batch C fold".
`grep` over plan 8 finds exactly one such row: C4(l).

*Proposed row text:*

> `| C4(l) | response shape | each element is `serialize_stock_task_assignment`'s shape — the fourteen keys of master plan §6.1, with nested `item` (`serialize_item_compact`, images included) and `task` (`serialize_task_compact`); `set(element) == set(GET /items/{client_id}/assignments`'s element)` | drop the nested `item` load and return the flat columns → the key set shrinks | §9, master plan §9B ruling 2, §6.1 |`

The row must be authored together with the §4 file amendment in §2.2 (the serializers module does
not exist yet).

### 3.6 plan 11 C5(b) / C4(b) — protected twice (owner card E)

Task 1 gives the guard an `incoming == current` no-op. Tasks 5 and 6 give **both** callers a
"differs from the stored one" term **before** the call, and intention §5B MC-14's "made exact"
bullet repeats it. So under either caller the guard is never entered with an unchanged category:
dropping the guard's short-circuit changes nothing observable, and dropping the caller's term
changes nothing either, because the guard still short-circuits. Appendix A's proposed mutant for
C5(b) is therefore an **equivalent mutant**. Plan 11 C4(b) already half-admits this
("the bite is (d)/(e)"); C5(b) does not. Card E offers the restructure and the honest-blank.

### 3.7 plan 11 C4(h) — the row cannot be built (owner card F)

*Current text, verbatim:*

> `| C4(h) | `complete_task_post_handling` path that calls `_update_item_in_session` with a category change while A active | 409; nothing written by that command | guard only in `update_item` (the public function) | MC-14 "covers both" |`

*Measured.* `_update_item_in_session` has exactly two callers in the tree
(`grep -rn "_update_item_in_session" app/beyo_manager/`): `update_item.py:124` and
`complete_task_post_handling.py:120`. The second builds
`UpdateItemRequest(client_id=primary_item.client_id, item_zone=effective_zone)`
(`complete_task_post_handling.py:126-129`) — `item_category_id` is never in `model_fields_set`, and
nothing in that command can put it there. So the fixture is unbuildable and the named mutation
("guard only in `update_item`") is unobservable.

Intention §5B MC-14 says the guard's placement "covers both `update_item` and
`complete_task_post_handling`'s call" — a statement about **where the guard sits**, not a claim that
the second caller can change a category. The intention needs no amendment; the criterion does.
Note that calling `_update_item_in_session` directly from a test to force a category change would
assert at a private helper, which charter rule 2 forbids as a criterion boundary.

## 4. Perimeter extensions and §6.1b entries

Proposed text is in §2.2 (plan 8 §7 bullet), §2.4 (plan 11 §7 bullet) and §2.5 (§6.1b row, §10 row).
Summary of every out-of-perimeter site a named mutation in batch C1 must touch:

| File | Owning phase (state) | Rows | Does the mutant also redden the owning phase's tests? |
|---|---|---|---|
| `bm/domain/stock_report/state_map.py` | 1 (VERIFIED) | 8 C4(a), C4(b), C4(d), C4(e) | **Yes, precisely one case each** — `test_state_map.py::test_task_state_map_is_exact` is parametrized per cell. Plan 1 C6(a) (key set) and C6(j) (value **set**) stay green under all four: I checked each mutant's resulting value set and none of them changes it. |
| `bm/services/commands/stock_report/_remove_assignment.py` | 4 (VERIFIED) | 8 C6(a) | Expected yes — plan 4's removal rows assert the flag. Not enumerated (I did not run anything). |
| `bm/services/commands/stock_report/_move_assignment.py` | 4 (VERIFIED) | 8 C6(c), and C6(i)'s second mutant | Expected yes, broadly — the `:updated` guard is on every move. |
| `bm/services/commands/stock_report/_goal_credit.py` | 5 (VERIFIED) | 8 C6(b) | Expected yes — plan 5's un-credit rows. |
| `bm/services/queries/stock_report/consistency.py` | 3 (VERIFIED) | 8 C6(g), if card B's repair lands | Expected yes — plan 3 C1(k) family. |
| `bm/services/commands/stock_report/apply_stock_demand.py` | 7 (VERIFIED) | 8 C4(m) | **Already declared** in plan 8 §7; unchanged. |
| `bm/services/commands/stock_report/_locks.py` | 3 (VERIFIED) | only if card C's lock row lands in the forceable form | unmeasured |

**Plan 11 needs no mutation-side perimeter extension.** All eight of its mutation sites are in files
plan 11 §4 already declares. Its two *fixture*-side foreign files (`add_item_to_task.py`,
`complete_task_post_handling.py`) are registered via the §6.1b row and the §7 bullet.

## 5. Standing projection checks (task 4)

| Check | Result |
|---|---|
| Every cited path in plan 8 §2/§4 exists or is marked new | **PASS with one gap** — `bm/domain/stock_report/serializers.py` is due in this phase (owner ruling 9B.2) and is absent from §4. Amendment in §2.2. All repo citations resolve: `batch_create_item_issues.py`, `auth.py:120-130` (the `code` render is at `:120-129`), `task_item.py`, `_locks.py`. |
| Every cited path in plan 11 §2/§4 exists | **PASS.** All five commands and all four secondary citations exist. Line drift, all minor: `delete_task.py`'s locking `SELECT` spans `:66-76` with `with_for_update()` at `:73` (plan says `:71-77`); `remove_item_from_task.py`'s `TaskItem` lookup is `:23-31` (plan says `:23-32`); `delete_item.py` `:26-35` and `:37` are **exact**; `update_item.py:73-74` is **exact**; `find_or_create_item.py`'s existing branch is `:95-119` and its first write to `existing` is the `setattr` at `:100` inside the loop opening at `:98` (plan says branch `:94-118`, write `:98` — the insertion point is right, the write line is `:100`); `create_task.py`'s call is `:253-261` (plan says `:250-262`); `items.py`'s second caller is `:222-236` with `require_roles` at `:225`. None of these changes an instruction. |
| Every cited contract / §6.5 signature / §6.1 name exists and matches | **PASS.** Intention §4.2, §4A MC-4, §5 r3, §9/§9A/§9C/§9D/§9E, §12A, §14C/§14E/§14F, §5B MC-14, §13A all resolve and say what the plans claim. Master plan §6.4's two error classes, §6.5's three new modules and `coalesce_stock_report_events`, §6.6's two routes, §9 rules 2–4/6/9/16 all resolve. Registry names not yet shipped and correctly scheduled: `serializers.py` (8), `_category_guard.py` (11), `requests/__init__.py` (8), `coalesce_stock_report_events` (8). |
| Task text does not contradict its own criterion | **ONE contradiction**: plan 8 §5 task 2 (fourteen keys) vs C4(l) (seven keys) — card D. Nothing else. Plan 8 task 2's MC-13 phase-3 order matches intention §9C exactly, with §14F F9 inserted after `item_not_task_primary` as F9 requires. |
| Fixtures constructible under the rules the plan itself imposes | **THREE not constructible**: plan 8 C6(g) (card B), plan 11 C1(c) (card B), plan 11 C4(h) (card F). **One stale construction**: plan 11 C4(i) and C1(c) reach a terminal state through `PR`, which does not exist in batch C1 — folded in §2.4. I walked every other row of both plans against the CR-only rule, the two partial unique indexes, §14F F9 and one-PRIMARY-per-task; the rest build. |
| Externally-derived fixtures re-grounded (charter rule 17) | **ONE new finding**: the `client_id` ordering assumption — see §2.5's §10 row; evidence `python-ulid` 3.0.0 `ulid/__init__.py:120` (`os.urandom`, no monotonic counter) and `identity.py:11`. **Two grounded and confirmed**: (a) the `IntegrityError` backstop — SQLAlchemy surfaces the constraint name in the message, evidenced by the shipped green test `app/tests/integration/models/stock_report/test_stock_report_schema.py:121,162`, and because §5 task 2 flushes **per entry**, the failing entry's index is known at the flush; (b) pydantic `extra="forbid"` → the repo's 422, see §2.6 L-5. |
| Trace cells resolve, both directions | **PASS at row level** for the 34 cells in scope: every one cites a live MC or amendment row. I did **not** run the reverse half (every ledger entry M1–M9 served by at least one row across plans 8 and 11) — see §7. |

## 6. Blockers, ranked

Nothing here is an implementation blocker in the sense of "the code cannot be written"; each is a
row the implementer or tester would have to improvise on.

1. **Cards B and F — three unbuildable rows** (plan 8 C6(g), plan 11 C1(c), plan 11 C4(h)). These
   stop a session mid-flight, which is the expensive failure §3B's class 3 exists to prevent.
2. **Card D — plan 8 C4(l) contradicts its own task text.** The implementer must pick one; whichever
   it picks gets locked in by a test.
3. **Plan 8 §4 is missing `serializers.py`** (§2.2). A file perimeter that omits a file the phase
   must create makes the reviewer's perimeter check report a violation on correct work.
4. **Plan 11 C4(i) / C1(c)'s `PR` fixtures** (§2.4). `PR` is phase 9 = batch C2. Foldable, but if it
   is not folded the implementer meets a symbol that does not exist.
5. **Cards A, C, E — three rows that cannot fail.** These do not stop a session; they ship green and
   prove nothing, which is the defect family that cost batches A and B most of their rounds.
6. **The `client_id` ordering fact** (§2.5). Two rows (8 C4(k), 8 C6(h)) are currently a coin flip
   per run *and* undiscriminating. Foldable.

## 7. What I did not check

Stated plainly, so the tester and reviewer know where their budget buys something.

- **I ran nothing.** No test, no mutation, no `pytest`, no database. Every "reddens" in this handoff
  is derived by reading code and plan text. The three verdicts I am least sure of, in order:
  (a) **card C's forceable lock row** — whether the crossing-pair deadlock reproduces
  deterministically depends on how Postgres orders row locks under `ORDER BY … FOR UPDATE`, which I
  could not settle by reading and did not measure; (b) **plan 8 C6(c)'s replacement mutant** — I am
  confident it reddens the "no `:updated`" clause and confident it does not reach "no counter
  change", but I did not observe either; (c) **the collateral-red sets** in §4 marked "expected" —
  only the `state_map.py` row is measured (by reading plan 1's parametrized test), the other four
  are inference.
- **Sites in unwritten code are unverifiable by construction.** Eleven of the 21 plan-8 class-1
  cells name a site inside `create_stock_task_assignments.py`, `delete_stock_task_assignments.py`
  or `requests/__init__.py`, which do not exist. I verified that the *plan text* determines each
  edit (which is what class 1 means), not that the line will be there. If the implementer writes
  the check differently, the tester re-sites and declares it — that is the normal path, not a
  finding.
- **Plan 11's hook and guard sites are equally unwritten.** I verified the **host files, their
  insertion points and the surrounding code** at `b95780b`; the hooks themselves are phase-11 code.
- **I did not check the reverse trace half** — that every measurement-ledger entry M1–M9 which
  plans 8 and 11 claim to serve is served by at least one row. Forward traces all resolve.
- **I did not re-derive the criteria counts of plans 9, 10, 12, 13, 13A**, and I did not reconcile
  or re-publish any total (per the prompt). §1 reports the cause of the plan-8 discrepancy without
  changing anything.
- **I did not re-litigate phases 1–7.** Two passing observations, neither a blocker on C1:
  (i) plan 8 C1(i)'s **already-filled** cell ("allow cancelled") carries the same wrong consequence
  as C1(h) — `CANCELLED` maps to `FAILED`, so the mutant yields `IllegalAssignmentMove`/500, not a
  creation; worth correcting in the same fold. (ii) `handoffs/projectionist/2026-09-21_batch_B_projection_handoff.md`
  is a live row in a role folder while an identical copy sits in `archive/batch_B1/`; batch B is
  closed, so by the charter's positional-state rule the live copy should have moved. Housekeeping.
- **I did not read plans 9, 10, 12, 13, 13A or their lessons' targets there.** Out of scope by the
  prompt.
- **I did not estimate the runtime cost** of the extra row lock that card E's option 1 would add.

## 8. Fold order actually followed

L-20 first (§2.5 rule 17, then applied to plan 8 §7) → L-17's preamble half (§2.2, §2.4 preambles;
the outcome half produced no arithmetic defect — the one candidate, C4(k)'s `(8,0,0)`, is correct
once the second item is specified as a copy of I, which is a fixture fold, not an owner card) →
then L-9, L-10, L-12, L-13, L-15, L-16, L-21, L-23, L-24, L-25, L-28, L-30 as recorded per cell in
§2 and per lesson in §2.6. Owner-only lessons (L-2, L-5, L-17's outcome half, L-29) were **not**
folded: L-29 is card C, L-5 is recorded in §2.6 as not-blocked, L-2 is §1's count report, and
L-17's outcome half found nothing. L-8 was left to the orchestrator, untouched.
