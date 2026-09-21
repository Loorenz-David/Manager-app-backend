---
batch: C2
phases: [9, 10]
role: projection
round: 0
state: AMENDMENTS_REQUIRED (OWNER_DECISIONS_PENDING — 5 cards)
date: 2026-09-21
actor: projectionist (Opus, orchestrated subagent)
---

# Batch C2 projection — plans 9 and 10

Gate check: intention status header reads **RATIFIED** (`planning/intention.md:4`, round 9,
re-ratified 2026-09-19; round 10's §14G is owner-declared additive). No upstream gate handoff for
9 or 10 is in `OWNER_DECISIONS_PENDING`. Gate passes.

Tree: `798fc69`. **I ran no tests and no mutations.** Every "verified" below means I opened the
file and read the symbol. Write perimeter of this session: **this one file**. No commits, no
`git add`, no plan/master-plan/source/test edit, no archgraph delta.

## Owner-readable opening

Both phase plans are implementable, but neither is ready to hand to an implementer as written. I
found two rows that cannot fail no matter what anyone writes, one row that asks for an ordering
the database cannot be made to guarantee, and a file list in plan 9 that omits two files the plan's
own instructions require editing — which would make the reviewer's perimeter check flag correct
work as a violation. The most valuable finding is about the three concurrency rows in plan 10: the
recipe the plan gives for forcing two users to collide **cannot be built** (there is no place in
the code for the test to hold the door open), and the thing those rows say they will break to prove
themselves **does not exist as a separate step in the code**. I have written replacements for both,
both modelled on a pattern this repository already ships and has already approved. Five decisions
need you personally; everything else is a mechanical patch the orchestrator can apply.

---

## ⚠ OWNER DECISIONS REQUIRED (5)

### Card 1 — Plan 9 C7(b) asks for a count of database statements as its outcome

**Question** — Re-state C7(b) as an outcome, drop it, or keep it as written?

**Story** — Scanner reports two repaired items that sit on two different board rows. You want to
know the board is right afterwards: both rows' counters at zero, both rows' updates sent to the
screens. What the row asks for instead is "two UPDATE statements, rows ascending" — a count of
what happened *inside* the database, not what anyone can see. On 2026-09-19 you ruled that out for
its two sibling rows, and they were changed the same day; this one was missed. It also asks the two
rows to be written in id order, and ids in this system sort randomly, so the test would pass or fail
on a coin flip about half the time.

**Branches** — *Re-state*: the row says both rows end at zero counters and each gets exactly one
screen update, and the ascending lock order is checked by reading the code, as C8(b) already does ·
*Drop*: C7(a)/C7(d) already cover grouped counters; nothing is lost but the row · *Keep*: the phase
ships a test that fails randomly and asserts nothing you can see.

**Recommendation** — Re-state. It keeps the grouping evidence and removes the coin flip in one move.

**On silence** — The gate holds: C7(b) stays as written, unfolded, and I flag it to the tester as
a known random failure.

**Trace** — plan 9 C7(b); master plan §10 (`client_id` is not creation order); §9 rule 7; §9A L-15,
L-22; the owner ruling of 2026-09-19 recorded in plan 9 §7.

### Card 2 — Plan 10 C2(a) describes a sequence the code cannot perform

**Question** — Re-point C2(a) at a real double-write, mark it unfailable-by-design, or drop it?

**Story** — The row is meant to catch a real hazard: if the sync ran on every intermediate step of
a task rather than once at the end, a finished item would be un-credited and re-credited and the
screens would flash twice. The scenario chosen to provoke it is "remove one of two finished steps,
watch the task dip to pending and come back to ready." I read the command: with a step left over it
never dips — it goes straight to the "is it still ready?" check, which sees the task is already
ready and does nothing at all. The task's state never changes, so the sync is never even offered
the task. The row passes today, will pass under every mutation, and proves nothing.

**Branches** — *Re-point*: find a command that really writes the task's state twice in one
transaction and use it — if none exists, this hazard is not reachable · *Mark unfailable*: keep the
row as a regression guard, labelled, with the registry guard (C4) as its real evidence · *Drop*:
the registry already refuses a sync call inside the three helpers, which is the same protection.

**Recommendation** — Mark it unfailable and name C4 as its evidence. The protection is genuinely
there; only this row's proof of it is fictional, and a re-point may find no real site.

**On silence** — The gate holds: C2(a) stays as written and the tester is told it cannot fail.

**Trace** — plan 10 C2(a); `remove_task_step.py:224-236`; `_task_state_transitions.py:90-91`;
inventory handoff §5 U1; charter rule 15.

### Card 3 — Plan 10 C7(b) cannot fail either

**Question** — Keep C7(b) labelled unfailable with a structural check, or drop it?

**Story** — The row says: try to finish a task that is already finished, and make sure no stock
message goes out and the assignment is untouched. The command refuses on its very first check,
before it has written anything, and long before the new sync code would run. And even if someone
wired the sync in the wrong place, the failed request is rolled back and messages are only sent
after a clean finish — so both halves of this row are guaranteed by machinery this phase does not
touch. There is no edit anywhere in this phase that turns it red.

**Branches** — *Keep, labelled*: the row stays as a cheap regression guard, marked the way the plans
already mark rows that cannot force their conditions, and the reviewer confirms by reading that the
sync sits after the refusal · *Drop*: one less row, one less thing to explain.

**Recommendation** — Keep it labelled. It costs nothing and the label is what stops a future
reviewer counting it as evidence.

**On silence** — The gate holds: the blank mutation cell stays blank and unexplained, which is the
state that cost batch B a round.

**Trace** — plan 10 C7(b); `resolve_task.py:51-52`; master plan §9 rules 6 and 9; charter rule 15.

### Card 4 — Nothing checks that Scanner gets its own article number back

**Question** — Add the echo clause to plan 9 C3(g)'s outcome?

**Story** — Scanner sends `" SR-x "` with stray spaces and expects to see `" SR-x "` come back
next to the verdict, exactly as it sent it — that is how it matches our answer to its own list.
The plan's instructions say so twice. No row checks it. If the code trims the number on the way
back out, every verdict is still correct and every test is still green, and Scanner quietly fails
to match half its own report against ours.

**Branches** — *Add*: C3(g)'s outcome also says the response's article number is `" SR-x "`, the
untouched string · *Leave*: the guarantee ships untested and fails silently at Scanner, not here.

**Recommendation** — Add it. It is one clause on a row that already sends the padded string.

**On silence** — The gate holds: the clause is not added and I flag the gap to the tester as a
candidate criterion.

**Trace** — plan 9 task 1 ("as received (echo)"), task 2 (`"article_number": <as received>`), C3(g);
Scanner v2 handoff §4.3; §9A L-3.

### Card 5 — One new shared function ships with nothing pinning its shape

**Question** — Add one row to plan 9 pinning the grouped resolve function's shape?

**Story** — Phase 9 adds a new shared function to the registry — the one that resolves a whole
group of items in a single pass and repairs a wrong counter while it does it. Every other name this
project registers has a row that pins what it takes and what it gives back, because the standing
rule you adopted this morning says a registered name with no such row is how a plan ends up citing
a contract that never shipped. This one has none: it is exercised only through the webhook, so a
future phase calling it directly has nothing to rely on.

**Branches** — *Add a row*: one row asserting the function's arguments and that it returns the two
event kinds for a group · *Leave*: the rule is written down and broken in the same week, and phase
13's callers inherit an unpinned contract.

**Recommendation** — Add the row. It is the cheapest possible instance of the rule you just adopted.

**On silence** — The gate holds: no row is added and the plan ships one unpinned registered name.

**Trace** — plan 9 task 2 and §6.5 (`resolve_processed_group`); master plan §9 rule 18; §9A L-8.

---

## 1. Counts, measured by script

```
cd .../stock_report/plans && for f in plan_9.md plan_10.md; do python3 - "$f" <<'PY'
import sys
rows=[]
for line in open(sys.argv[1]):
    s=line.rstrip("\n")
    if not s.startswith("| C"): continue
    cells=[c.strip() for c in s.strip().strip("|").split(" | ")]
    if len(cells)!=5: print("  SHAPE?",len(cells),cells[0]); continue
    rows.append(cells)
print("rows:",len(rows),"empty:",sum(1 for r in rows if r[3] in ("—","-","")))
PY
done
```

| Plan | Criterion rows | Empty (`—`) mutation cells | Named cells |
|---|---|---|---|
| 9 | **43** | **18** | 25 |
| 10 | **35** | **15** | 20 |

Both totals match the plans' own §7 sizing notes (43 in 8 criteria; 35 in 7 criteria) and both
empty-cell counts match §9A's debt table and the prompt's expectation. No row failed the 5-cell
shape check.

Empty cells — plan 9: `C1(a) C1(b) C1(c) C2(a) C2(c) C2(d) C2(f) C2(h) C3(a) C3(b) C3(e) C3(g)
C4(b) C4(e) C5(b) C6(a) C6(b) C7(b)`. Plan 10: `C1(b) C1(d) C1(g) C1(h) C1(i) C1(j) C1(k) C1(l)
C3(b) C3(d) C3(e) C3(f) C4(a) C7(b) C7(c)`.

**Measured classification** — plan 9 **15 / 2 / 1** (as hypothesised). Plan 10 **13 / 1 / 1**, not
13/2/0: I moved C7(b) from class 2 to class 3 (owner card 3) because it is not merely
site-undetermined, it cannot fail. Separately, two *named* cells in plan 10 (C2(a), and the C5
trio) are class-3 defects even though they are not in the empty-cell scope.

**Where the prior pass was wrong at the site** (the prompt predicted a similar rate; I found four):

| Cell | Prior claim | What the code says |
|---|---|---|
| 10 C3(b), C3(d)–(f) | the mutant "moves the assignment to `failed`/`in_queue`" | `_move_assignment.py:66-69` refuses **every** move out of a terminal state — the mutant raises `IllegalAssignmentMove` (500), it does not move anything |
| 10 C1(i) | "remove the `state == target → skip`" | inert on its own: `move_assignment` has its **own** `assignment.state == target → return []` at `:195-200`, which absorbs the no-op. Both must go |
| 10 C1(l) | "pass `actor_user_id = ctx.user_id`" | S9 is a dormant handler with **no `ctx`** (`finalize_pending_step_completion.py:34` reads `payload["performed_by_user_id"]`); only `None` is an available mutant |
| 9 C6(a), C6(b) | "the replay re-resolves and writes" / "re-credits `G`" | both consequences are uncertain (the terminal refusal at `:66`, or `move_assignment`'s `from == target` short-circuit, absorbs the write). The certain, binding clause is the **second delivery's result** |

Plus the C5 trio in plan 10 — see §3, where the site the cells name does not exist.

## 2. The patch table

Class 1 = fold. Class 2 = keep `—`, add the labelled note. Class 3 = see §4 / a card.
`Site verified?` — **read** = I opened the file and the symbol is there; **plan-determined** = the
site is in a file phase 9/10 creates, so it is derived from the plan's own task text and a shipped
sibling, not read; **corrected** = the prior pass named a site or effect the code contradicts.

### 2.1 Plan 9 — mutation cells

| Plan | Row | Cell | Current text (verbatim) | Proposed text (verbatim) | Class | Lesson(s) | Site verified? |
|---|---|---|---|---|---|---|---|
| 9 | C1(a) | Named mutation | `—` | ``process_items_processed.py`` (call site) — replace ``workspace_id = verify_location_tracker_webhook(ctx.incoming_data["headers"])`` with ``workspace_id = settings.location_tracker_webhook_workspace_id`` (verification skipped; the workspace still resolves, so the module still imports) → the keyless request proceeds and returns 200. Line shape per ``receive_stock_demand_webhook.py:30``. Also bites C1(b) and C1(d): all three runs recorded (§9 rule 8) | 1 | L-10, L-28 | read (sibling call site) |
| 9 | C1(b) | Named mutation | `—` | ``infra/location_tracker/webhook_verifier.py:39`` (definition site) — replace ``if not hmac.compare_digest(provided.encode("utf-8"), api_key.encode("utf-8")):`` with ``if not provided:`` → a wrong but non-empty key passes and the request returns 200. Row-local: C1(a)'s keyless request still 401s on the ``provided is None`` guard at ``:32``. **Out of perimeter — see §6** | 1 | L-25 | **read** |
| 9 | C1(c) | Named mutation | `—` | ``process_items_processed.py`` (definition site) — delete the MC-8 step-4 workspace ``SELECT`` and its refusal → the request (run through ``PR``, so the key is valid and step 3 cannot mask the bite — L-19) proceeds to 200 with ``ignored``/``item_not_found`` and no write. C1(c) is the **unknown-id** case; the blank-setting case is C1(e) (MC-8 step 2), so the two are not one row | 1 | L-19, L-10 | plan-determined |
| 9 | C2(a) | Named mutation | `—` | `—` *(deliberate blank, class 2: under the shipped sibling's single guard — ``stock_demand_request.py:34``, ``not isinstance(payload, list) or len(payload) == 0`` — no mutant isolates the list-ness clause on ``b"{}"``: weakening it still lands ``{}`` on the non-empty clause, and deleting the whole guard is C2(b)'s mutant. The tester sites it on the real code and may declare EQUIVALENT with C2(b)'s run recorded.)* | 2 | L-10 | **read** (sibling) |
| 9 | C2(c) | Named mutation | `—` | ``items_processed_request.py`` (definition site) — delete the per-entry ``isinstance(entry, dict)`` guard and its ``continue`` (sibling shape ``stock_demand_request.py:43-45``) → the bare-string entry raises ``AttributeError`` on ``.get`` instead of the collected ``ValidationError`` | 1 | L-10 | plan-determined |
| 9 | C2(d) | Named mutation | `—` | `—` *(deliberate blank, class 2: the missing-key and blank-string defects are one guard in the shipped sibling — ``stock_demand_request.py:47-49`` reads ``item.get(...)`` then ``isinstance(str) and bool(strip())``, so ``None`` fails the same clause a blank string fails. Whether a separate required-key site exists is an implementation choice; the tester sites it on the real code.)* | 2 | L-10 | **read** (sibling) |
| 9 | C2(f) | Named mutation | `—` | ``items_processed_request.py`` (definition site) — drop the non-blank half of the ``article_number`` check, keeping ``isinstance(..., str)`` → ``"  "`` parses, the command strips it to ``""``, matches no item, and the request returns 200 ``ignored``/``item_not_found`` instead of 422 | 1 | L-12 | plan-determined |
| 9 | C2(h) | Named mutation | `—` | ``items_processed_request.py`` (definition site) — replace the defect collection (``defects.append(...)`` + ``continue``) with an immediate ``raise ValidationError`` on the first malformed entry (sibling raise at ``stock_demand_request.py:87``) → the 422 names index 0 only, not 0 **and** 2 | 1 | L-12 | plan-determined |
| 9 | C3(a) | Named mutation | `—` | ``process_items_processed.py`` (definition site) — delete the ``item_not_found`` rung of the F5 ladder so an unmatched number falls through to the assignment lookup → the entry reports ``ignored``/``no_open_assignment`` | 1 | L-13 | plan-determined |
| 9 | C3(b) | Named mutation | `—` | ``process_items_processed.py`` (definition site) — swap the two ignore-reason literals in the F5 ladder → an item that exists with no active assignment reports ``ignored``/``item_not_found``. Inverse direction of C3(a); both runs recorded (L-13, L-24) | 1 | L-13, L-24 | plan-determined |
| 9 | C3(e) | Named mutation | `—` | ``process_items_processed.py`` (definition site) — narrow the **unlocked assignment-discovery predicate** from ``StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES)`` to a hand-typed ``.in_([IN_QUEUE, AWAITING])`` (rule 16's literal). The frozenset in ``enums.py`` is **not** edited — that would move C3(d), C3(f) and shipped rows in three other phases → the ``in_progress`` assignment is not discovered and the entry reports ``ignored``/``no_open_assignment`` | 1 | L-25, §9 r16 | **read** (`enums.py:15-21`) |
| 9 | C3(g) | Named mutation | `—` | ``process_items_processed.py`` (definition site) — drop the ``.strip()`` applied when the request's numbers are turned into the item-lookup set (task 2, "the set of stripped numbers") → ``" SR-x "`` matches no item and reports ``ignored``/``item_not_found``. (See owner card 4: the row's echo clause is missing and is the owner's to add) | 1 | L-3 (card 4) | plan-determined |
| 9 | C4(b) | Named mutation | `—` | ``_move_assignment.py::resolve_processed_group`` (definition site) — delete the ``build_stock_report_item_updated_event(...)`` append for the touched row, keeping the per-assignment ``state-changed`` event → the dispatched list is ``[stock_task_assignment:state-changed {state: resolved}]`` only. **Out of perimeter — see §6** | 1 | L-12, L-25 | **read** (`_move_assignment.py:260-267`) |
| 9 | C4(e) | Named mutation | `—` | ``_move_assignment.py::resolve_processed_group`` (definition site) — restrict the F4 goal credit to assignments whose re-read state is ``in_queue`` → this row's ``in_progress`` assignment is not credited and ``G == 0`` instead of ``8``. C4(d) (``in_queue``) stays green: that pair is the sub-check split, both runs recorded (L-12, L-13) | 1 | L-12, L-13 | plan-determined |
| 9 | C5(b) | Named mutation | `—` | ``process_items_processed.py`` (definition site) — decide each entry on the pre-request snapshot of the assignment's state instead of on the state as earlier entries in the same request left it → the second ``"SR-x"`` also reports ``resolved``/``early``. **The binding clause is the second result, not ``−q`` applied once**: whether the doubled decision produces a doubled delta, a guarded-statement self-heal or a refusal depends on how the group is built | 1 | L-10, L-19 | plan-determined |
| 9 | C6(a) | Named mutation | `—` | ``process_items_processed.py`` (definition site) — drop ``StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES)`` from the unlocked discovery predicate (frozenset unedited, as C3(e)) → the second delivery no longer reports ``ignored``/``no_open_assignment``: it re-decides the ``resolved`` assignment, whose target is ``resolved_early``, which ``_move_assignment.py:66-69`` refuses with ``IllegalAssignmentMove`` (500). The row reddens on the raise, so its ``count_writes == 0`` clause is not reached (rule 12) | 1 | L-10, L-12 | **corrected / read** |
| 9 | C6(b) | Named mutation | `—` | ``process_items_processed.py`` (definition site) — hand-type the same discovery predicate as ``state.not_in([RESOLVED, FAILED])`` (rule 16's literal) → the second delivery discovers the ``resolved_early`` assignment as active and reports ``resolved``/``early`` instead of ``ignored``/``no_open_assignment``. **Do not state "re-credits G"**: the target equals the state, so ``move_assignment``'s ``from_state == target → return []`` (``:195-200``) may absorb the whole move | 1 | L-10, §9 r16 | **corrected / read** |
| 9 | C7(b) | Named mutation | `—` | *(class 3 — owner card 1; no mutation proposed until the outcome is re-stated)* | 3 | L-15, L-22 | n/a |

### 2.2 Plan 10 — mutation cells

| Plan | Row | Cell | Current text (verbatim) | Proposed text (verbatim) | Class | Lesson(s) | Site verified? |
|---|---|---|---|---|---|---|---|
| 10 | C1(b) | Named mutation | `—` | ``bm/domain/stock_report/state_map.py:9`` (definition site) — set ``TaskStateEnum.READY`` to ``StockTaskAssignmentStateEnum.IN_PROGRESS`` → A ``in_progress``, counters ``(0, 4, 0)``, ``G == 0``. **Not row-local and out of perimeter (§6):** it also reddens ``app/tests/unit/domain/stock_report/test_state_map.py:27`` (which parametrizes the whole map) and every shipped row creating an assignment on a ``ready`` task — record the observed-red set across the suite (§9 rule 8) | 1 | L-25, L-28 | **read** |
| 10 | C1(d) | Named mutation | `—` | ``bm/services/commands/tasks/force_task_ready.py`` (call site) — delete the ``sync_task_stock_assignments(...)`` call → A stays ``in_queue`` instead of moving to ``awaiting``. **Double kill:** also reddens ``test_task_state_write_sites_are_registered`` (a registered ``task_write`` whose sync function has no call) — both observed reds recorded (§9 rule 8, L-28) | 1 | L-28 | **read** (file + `original_state` at `:111`) |
| 10 | C1(g) | Named mutation | `—` | ``bm/services/commands/tasks/fail_task.py`` (call site) — delete the sync call → A stays ``in_progress`` and counters stay ``(0, 4, 0)`` instead of A ``failed`` / ``(0, 0, 0)``. Double kill with the registry guard as C1(d) | 1 | L-28 | **read** (`:54`) |
| 10 | C1(h) | Named mutation | `—` | ``bm/services/commands/tasks/cancel_task.py`` (call site) — delete the sync call → A stays ``in_queue`` instead of ``failed``. Double kill with the registry guard as C1(d) | 1 | L-28 | **read** (`:54`) |
| 10 | C1(i) | Named mutation | `—` | **Two sites, applied together** — ``sync_task_stock_assignments.py`` (definition site): remove the MC-2 step-5 ``state == target → skip``; **and** ``_move_assignment.py:195-200`` (definition site): remove ``move_assignment``'s own ``assignment.state == target → return []``. **Either alone is EQUIVALENT** (the other absorbs the no-op). With both gone the net delta is zero so counters and ``:updated`` are unchanged, but a ``stock_task_assignment:state-changed`` event is emitted and the row's "no stock event" clause reddens. Same mutant as C1(f); show it reaches C1(i)'s own assertion (L-28). **`_move_assignment.py` is out of perimeter — see §6** | 1 | L-10, L-25, L-28 | **corrected / read** |
| 10 | C1(j) | Named mutation | `—` | ``bm/services/commands/task_steps/add_task_steps.py`` (call site) — delete the sync call → A stays ``awaiting``, ``G`` stays 4 and ``mem`` is unchanged, instead of A ``in_progress`` / ``G == 0`` / ``mem IS NULL``. Double kill with the registry guard as C1(d) | 1 | L-28 | **read** (reopen via `maybe_reopen_task_to_working` at `:182`) |
| 10 | C1(k) | Named mutation | `—` | ``bm/services/commands/task_steps/remove_task_step.py`` (call site) — delete the sync call **and** its event append → A stays ``in_progress`` and counters stay ``(0, 4, 0)`` instead of A ``in_queue`` / ``(4, 0, 0)``. Double kill with the registry guard as C1(d) | 1 | L-28 | **read** (`task.state = PENDING` at `:225`) |
| 10 | C1(l) | Named mutation | `—` | ``bm/services/tasks/task_steps/finalize_pending_step_completion.py`` (call site) — pass ``actor_user_id=None`` instead of ``payload["performed_by_user_id"]`` (``:34``). **``ctx.user_id`` is not an available mutant here — this handler has no ``ctx``** → ``move_assignment`` stamps ``updated_by_id`` NULL (``_move_assignment.py:213``) and the row's ``updated_by_id == payload["performed_by_user_id"]`` reddens | 1 | L-10 | **corrected / read** |
| 10 | C3(b) | Named mutation | `—` | ``sync_task_stock_assignments.py`` (definition site) — replace the MC-2 skip ``state in TERMINAL_ASSIGNMENT_STATES`` with a hand-typed ``state == StockTaskAssignmentStateEnum.RESOLVED`` (rule 16's literal; the frozenset in ``enums.py`` is not edited) → the ``failed`` assignment is no longer skipped and ``move_assignment`` **raises ``IllegalAssignmentMove`` (500)** at ``_move_assignment.py:66-69`` rather than moving it to ``in_queue``. The row reddens on the raise, so its later clauses are not reached (rule 12) | 1 | L-10, §9 r16 | **corrected / read** |
| 10 | C3(d) | Named mutation | `—` | ``sync_task_stock_assignments.py`` (definition site) — same skip hand-typed as ``state in {RESOLVED, FAILED}`` (rule 16's literal) → the ``resolved_early`` assignment is no longer skipped and ``move_assignment`` raises ``IllegalAssignmentMove`` (500) on ``resolved_early → failed``. **One mutant shape across C3(c)–(f):** run it once per row and record that it reaches this row's own task exit (§9 rule 8, L-28) | 1 | L-10, L-28 | **corrected / read** |
| 10 | C3(e) | Named mutation | `—` | As C3(d) — the same hand-typed skip; here the task exit is S6 ``cancel_task`` and the refused move is ``resolved_early → failed``. Own run recorded (L-28) | 1 | L-10, L-28 | **corrected / read** |
| 10 | C3(f) | Named mutation | `—` | As C3(d) — the same hand-typed skip; here the task exit is S8 ``remove_task_step`` and the refused move is ``resolved_early → in_queue``. Own run recorded (L-28) | 1 | L-10, L-28 | **corrected / read** |
| 10 | C4(a) | Named mutation | `—` | `—` *(deliberate blank, class 2: this is the guard's control row. Its arming is the probe set C4(b)–(h) — the six MC-2 probes plus the staleness row — which is charter rule 15's required positive observation for this instrument (L-26 is discharged here). A mutation of C4(a) itself could only edit the collector or the registry, i.e. test-side data.)* | 2 | L-26, r15 | **read** (probe sites verified below) |
| 10 | C7(b) | Named mutation | `—` | *(class 3 — owner card 3: the row cannot fail. ``resolve_task.py:51-52`` raises before any state write and long before the sync's call site, and the rollback plus the after-commit event rule guarantee both clauses independently of this phase. No mutation proposed until the owner rules.)* | 3 | r15, §9 r9 | **read** |
| 10 | C7(c) | Named mutation | `—` | ``sync_task_stock_assignments.py`` (the ``move_assignment`` call site) — pass ``trigger="task_sync_x"`` → ``_move_assignment.py:172`` writes ``inline:task_sync_x`` and the row's ``trigger == "inline:task_sync"`` reddens | 1 | L-10 | **read** |

### 2.3 Fixture, preamble and structural folds (orchestrator)

| Plan | Where | Current text (verbatim) | Proposed text (verbatim) | Lesson(s) |
|---|---|---|---|---|
| 9 | §4 "Files expected to change", the `New:` sentence | `New: bm/services/commands/stock_report/items_processed_request.py, process_items_processed.py;` | `New: bm/services/commands/stock_report/items_processed_request.py, process_items_processed.py;` **and add to the `Edited:` sentence:** `bm/services/commands/stock_report/_move_assignment.py` (task 2's `resolve_processed_group` entry point), `bm/domain/stock_report/enums.py` (`ItemsProcessedOutcomeEnum`, `ItemsProcessedReasonEnum` — §6.1's 2026-09-21 correction records both as still unshipped; verified absent at `798fc69`) | manifest p.2 |
| 9 | §6 preamble, after the `PR(body_bytes)` sentence | *(insert)* | **Where a row states `q = n`, the fixture sets item I's `quantity` to `n` before `CR`** — the assignment's quantity is copied from the item (plan 8 C4(g)), and F0's default is `4`, not the `8` the C4 rows assume. | L-17 (preamble half) |
| 9 | §7 | *(insert bullet)* | **Perimeter extension (§9 rule 17 / L-25).** Two named mutations are applied outside §4's file list and are authorized here: `bm/services/infra/location_tracker/webhook_verifier.py` (C1(b) definition site, C1(e) both guards — phase 7's file) and, for the reviewer's perimeter diff, the two `Edited:` additions above. Every probe is reverted in the same round. | L-25, §9 r17 |
| 10 | §7 | *(insert bullet)* | **Perimeter extension (§9 rule 17 / L-25).** Four named mutations are applied outside §4's file list and are authorized here: `bm/domain/stock_report/state_map.py` (C1(b)); `bm/services/commands/stock_report/_move_assignment.py` (C1(i)'s second site, and C3(c)'s "with plan 4 mutated too"); `bm/services/commands/tasks/update_task.py` (probes P-a…P-d, rows C4(b)–(e)); `bm/services/commands/users/_clock_worker_shift.py` (probe P-f, row C4(g)). Each is planted, observed, and reverted inside the round; C1(b)'s observed-red set spans other phases' files and is recorded whole (§9 rule 8). | L-25, §9 r17 |
| 10 | §6 preamble | *(insert, after "Every row ends with `assert_stock_report_clean`.")* | **C5's three orders are forced by a held lock, never by a barrier** (§9 rule 9). Precedent, shipped and APPROVED in batch B2: `app/tests/integration/services/commands/stock_report/test_apply_stock_demand.py:821-867`. Per row: a third **referee** session on `get_db_session()` takes `SELECT … FROM stock_report_items WHERE client_id = R FOR UPDATE` and sets `held`; the row's **first** session's command is started as a task and **observed to block** (`with pytest.raises(asyncio.TimeoutError): await asyncio.wait_for(asyncio.shield(task1), 0.5)`); only then is the **second** session's command started and likewise observed to block; the referee then commits and both tasks are awaited under `asyncio.wait_for(…, timeout=10)`. Postgres queues both waiters on the row's tuple lock in arrival order, so the first session acquires first. **Both observed blocks are assertions of the row, not setup:** they are what proves the order was forced *and* that each session finished its unlocked discovery read before the other committed — the overlap every C5 mutation needs. A barrier is not used: it releases both sides at once and expresses a race, not an order. Every session is released and the workspace purged in `finally`. | L-29, §9 r9 |
| 10 | §7, the C5 bullet | `- C5's ordering is forced by lock acquisition, not by sleeps: the first session holds the row lock across an `asyncio.Event` until the second has issued its `FOR UPDATE` (bounded with `wait_for`), then releases (master plan §9 rule 9).` | `- C5's ordering is forced by lock acquisition, not by sleeps — by a **third, referee session** holding the row lock, never by either participant (§6 preamble). Both participants run whole production commands that take and release their own locks inside `maybe_begin`, so neither can be made to hold one open for the other; the earlier wording named a seam that does not exist.` | L-29, §9 r9 |
| 10 | C5(a) | fixture cell fragment: `barrier after both discovered ids; session 1 takes the row lock first (session 2 is made to wait by session 1 holding the lock until session 2 has started its lock statement — bounded)` | `order forced by the §6 referee-lock choreography, session 1 started first; both blocks observed` | L-29 |
| 10 | C5(b) | fixture cell fragment: `the mirror ordering — session 2 (`add_task_steps`, T `ready → working`) takes the row lock first` | `the mirror ordering, forced by the §6 referee-lock choreography with **session 2 started first**; both blocks observed — session 2 (`add_task_steps`, T `ready → working`) acquires the row lock first` | L-29 |
| 10 | C5(c) | fixture cell fragment: `session 1 takes the row lock first` | `order forced by the §6 referee-lock choreography, session 1 started first; both blocks observed` | L-29 |
| 10 | C5(a) | Named mutation: `skip the post-lock re-read → session 2 moves a resolved assignment` | `sync_task_stock_assignments.py` (definition site) — capture `pre = a.state` immediately after the unlocked discovery query and decide the terminal skip on `pre in TERMINAL_ASSIGNMENT_STATES` instead of on `a.state` → session 2 moves the `resolved` assignment. **There is no separate post-lock re-read statement to delete:** the re-read is `_locks.py:22-41`'s `populate_existing=True`, which refreshes the same identity-mapped instance in place; deleting it there would change every locking caller in the project | L-10, L-25, L-31 |
| 10 | C5(b) | Named mutation: ``decide on the pre-lock read (`awaiting`) → Scanner moves `awaiting → resolved` on an assignment that is `in_progress` `` | `process_items_processed.py` (definition site) — capture the assignment's state at the unlocked discovery step and run the §14F F5 ladder on that captured value instead of on the state after `lock_stock_task_assignments` → Scanner decides `awaiting → resolved` on an assignment the reopen has already moved to `in_progress`, and `_move_assignment.py:74-79` refuses it (`IllegalAssignmentMove`, 500). Same "no separate re-read" note as C5(a) | L-10, L-31 |
| 10 | C5(c) | Named mutation: `skip the post-lock re-read in the sync → session 2 moves a terminal assignment` | As C5(a) — `sync_task_stock_assignments.py` (definition site), decide the terminal skip on the value captured at discovery → session 2 moves the `resolved_early` assignment and `_move_assignment.py:66-69` refuses it (`IllegalAssignmentMove`, 500) | L-10, L-31 |

## 3. Plan 10's C5 rows — conclusion and proposed fixture text

**This is the session's main result. Three separate defects, only one of which the prompt's
hypothesis addresses.**

### 3.1 On the connection asymmetry: it is real, it is not the whole cause, and the proposed fix is not sufficient

What I can ground by reading: both `db_session` (`app/tests/conftest.py:107-111`) and
`get_db_session` (`bm/models/database.py:66-72`) come from the **same** `async_sessionmaker` on the
**same** process-wide engine, and neither pre-opens a connection. The engine sets
`pool_pre_ping=True` (`:30`), so a checkout that finds an idle pooled connection pays one round
trip while a checkout that must open a new one pays TCP + auth + the `server_settings` timezone set
— several. That is a large, real asymmetry, and it falls **after** the barrier for whichever side
checks out second.

But the stated mechanism — "session A holds an already-warm connection" — is **not** what the code
shows. `test_create_stock_task_assignments_race.py:129` is `await db_session.commit()`, and a
SQLAlchemy session in commit-as-you-go mode releases its connection to the pool on commit. At the
barrier **neither** session holds one. So the asymmetry is not "warm vs. lazy"; it is "whoever the
event loop resumes first from `asyncio.Barrier.wait()` gets the idle connection, and the other pays
to open one." **I could not determine by reading which side that is** — it depends on
`asyncio.Barrier`'s wake order interacting with `gather`'s task order — and I was forbidden to run.
I report that as unverified rather than guess.

**Where I do disagree with the hypothesis:** `await session2.execute(select(1))` before the barrier
removes the connection-establishment head start, and for **plan 8 C5(a)** that is probably enough,
because that row names no order — it only needs the two pre-checks to *overlap*, and with overlap
the losing call's pre-check passes and the Item lock becomes the only thing standing between it and
a unique-index `IntegrityError` instead of a clean `item_already_assigned`. For **plan 10** it is
not enough, and adopting it alone would make things worse. Plan 10's three rows each name **one
specific order**. A barrier releases both sides simultaneously; making the sides symmetric converts
a reliably-wrong order into a coin flip, i.e. converts a silent pass into an intermittent failure.
**A barrier expresses a race. It cannot express an order.**

### 3.2 The second defect: the rows need overlap, not just order — and plan 10 already knows it but cannot build it

Each C5 mutation only bites when the **losing** session has completed its *unlocked discovery read*
before the **winning** session commits. If the two commands merely run one after the other, the
loser's very first query already returns the final state, the ordinary terminal/state check catches
it, and removing the post-lock decision changes nothing — the mutant is equivalent and the row is
green. So the choreography is three-phase: **both discover → winner locks and commits → loser
locks, re-reads, decides.**

Plan 10 C5(a)'s fixture cell says "barrier after both discovered ids", so the author saw this. But
the mechanism §7 prescribes — *"the first session holds the row lock across an `asyncio.Event`
until the second has issued its `FOR UPDATE`, then releases"* — **cannot be built.** Both
participants are whole production commands (`process_items_processed`, `add_task_steps`,
`transition_step_state`); each takes and releases its own row lock inside its own `maybe_begin`
block, and there is no seam for the test to hold it open. A tester meeting this at arming time is
blocked mid-session, which is exactly the failure §3B's class-3 rule exists to prevent.

**Proposed replacement (verbatim text in §2.3).** A third *referee* session holds the row lock; each
participant is started in turn and **observed to block** on it; the referee then releases and
Postgres grants the queued tuple-lock waiters in arrival order. This is not invention: it is the
shipped, APPROVED pattern at
`app/tests/integration/services/commands/stock_report/test_apply_stock_demand.py:821-867`
(`test_c5c_concurrent_soft_delete_under_lock_raises_and_heals`), which already includes the
"prove it blocked" probe (`pytest.raises(asyncio.TimeoutError)` around
`asyncio.wait_for(asyncio.shield(task), 0.5)`). It needs four concurrent pooled connections
(`db_session` + referee + two participants); `DB_POOL_SIZE=20` in `app/.env`, so that is safe. It
uses no sleep and no barrier, satisfying §9 rules 9 and 10.

Deadlock check: the referee holds only `stock_report_items`; `process_items_processed` locks rows
then assignments and never touches `tasks` (F3); the sync locks items then assignments. Neither
participant holds an assignment lock while waiting for the row lock, so there is no cycle.

### 3.3 The third defect, and the one most likely to cost a round: the site the C5 cells name does not exist

All three C5 mutation cells say "skip the post-lock re-read". **There is no post-lock re-read to
skip.** `_locks.py:22-41` issues the lock as
`select(model)…order_by(client_id).with_for_update().execution_options(populate_existing=True)` —
the lock statement *is* the re-read, and it refreshes the same identity-mapped ORM instance the
discovery query returned. There is no separate statement, and no retained stale value to decide on.
Removing `populate_existing` would edit a phase-3/4 helper shared by every locking caller in the
project.

So each cell must be re-sited onto the **decision**, as an additive mutation: capture the state at
discovery and decide on the captured value. Verbatim text is in §2.3. This is precisely the L-31
class ("a fold that replaces a vague mutation with a precise site must verify the site executes
under the row's own fixture") and the plan-8 C5(b) failure the prompt warned about, one plan later.

### 3.4 Forceability verdict

| Row | Order | Forceable? | Why |
|---|---|---|---|
| C5(a) | Scanner first (`PR` wins), reopen loses | **Yes** | Referee holds R's lock; `PR` blocks first, `add_task_steps` blocks second behind it; both discovered before either committed |
| C5(b) | Reopen first (`add_task_steps` wins), Scanner loses | **Yes** | Same choreography, session 2 started first. `PR`'s unlocked discovery sees `awaiting` while the referee still holds the lock, which is exactly what the mutation needs |
| C5(c) | Scanner first while `in_progress` | **Yes** | Same as C5(a) with S1 `transition_step_state` as the loser |

**None of the three needs to be declared `UNFORCEABLE`.** Plan 9 C8(b) and plan 11 C7(a)–(b) stay
`UNFORCEABLE` as already declared; I propose no change there.

One caveat I could not close by reading: the "observed block" probe assumes a participant that is
not blocked would finish inside 0.5 s. The referee holds only the row lock, so nothing else can
delay it, and the shipped precedent relies on the same assumption — but the bound is empirical and
a tester should confirm it on the first run rather than assume it.

## 4. Class-3 rows in full

| # | Row | The defect | Minimal fix | Whose authority |
|---|---|---|---|---|
| 1 | **9 C7(b)** | Outcome stated as internals ("two `UPDATE`s on `stock_report_items`, rows ascending"). The identical clause was stripped from C7(a) and C7(d) by the owner ruling of 2026-09-19 (plan 9 §7 records it), so this row survived a ruling it should have been folded into. Separately, "rows ascending" is a two-element ordering claim whose fixture never fixes which of R/R2 sorts first, and §10 records that `client_id` is not creation order (977 of 1999 consecutive pairs out of order) — so the assertion is a coin flip, and L-15 forbids a `sorted()` claim on fewer than three elements | Re-state as an outcome: both rows end at `(0,0,0)` and each receives exactly one `:updated`; the single ascending lock statement is verified structurally, as C8(b) already declares (the statement is `_locks.py:22-41`'s `ORDER BY client_id … FOR UPDATE`, which already provides X2) | **Owner** — card 1 (outcome cell) |
| 2 | **10 C2(a)** *(named cell; class 3 by §3B's "reveals a defect")* | The fixture's path does not exist. `remove_task_step.py:224-236` is `if len(remaining_steps) == 0: task.state = PENDING else: await maybe_evaluate_task_ready(...)` — mutually exclusive — and `_task_state_transitions.py:90-91` early-returns when the task is already `READY`. With two completed steps and one removed, one step remains, so the `else` branch runs and returns immediately: **T never changes state**, `old_task_state == task.state`, and the sync is never offered the task. The row's outcome is trivially true and its named mutation ("sync inside the helpers, per intermediate write") names a defect that cannot occur at S8. Inventory U1's premise (`remove_task_step`'s ready→pending→ready) is refuted by the shipped code | Mark `UNFAILABLE — structural` and name C4 (the registry, which classifies the three helpers as `no_sync` and probes helper detection with P-d) as its evidence; or re-point at a command that really writes `Task.state` twice in one transaction, if one exists | **Owner** — card 2 (fixture + outcome) |
| 3 | **10 C7(b)** | Cannot fail. `resolve_task.py:51-52` raises `ConflictError` before any state write and before the sync's call site (which task 2 places after the last `Task.state` write). Both clauses are additionally guaranteed by machinery this phase does not touch: the rollback (A unchanged) and §9 rule 6's after-commit dispatch (no event). Even a misplaced sync call would satisfy both. Charter rule 15's fifth named instance — an absence measured true only because the form is never written | Keep, labelled `UNFAILABLE — structural`, with the reviewer confirming by reading that the sync sits after the terminal guard; or drop | **Owner** — card 3 (criterion row) |

## 5. Decision ledger — what the artifacts do not determine

| # | Decision point | Class | Routing |
|---|---|---|---|
| D1 | Four of the nine sites capture the old state as a **string**: `force_task_ready.py:111`, `resolve_task.py:54`, `fail_task.py:54`, `cancel_task.py:54` all read `original_state = task.state.value`. The registered signature is `changed: list[tuple[Task, TaskStateEnum]]` (§6.5). The implementer must convert or compare `.value`, and nothing says which | plan gap | Orchestrator: add one sentence to plan 10 task 2 — "at S3–S6 the captured value is `task.state.value` (a `str`); convert with `TaskStateEnum(original_state)` before building the `changed` tuple." |
| D2 | Plan 10 task 1 writes `lock_stock_report_items([row])` and `lock_stock_task_assignments([a])`; the real signatures are `(session, workspace_id, client_ids)` (`_locks.py:44-49`). Shorthand, but it disagrees with the registry | free choice / reference | Orchestrator: correct the two call forms in task 1. Low risk — the implementer reads the helper. |
| D3 | S8 must append the sync's events "into the tuple its dispatcher consumes". `_remove_task_steps_in_session` returns a 5-tuple with **no** event list (`remove_task_step.py:238`); `_dispatch_remove_step_events` builds events itself. Whether to extend the tuple or thread a list is undetermined | free choice | Orchestrator: record the delegation explicitly in plan 10 task 2 so the implementer's freedom is granted, not taken. |
| D4 | Plan 9 task 2's grouped entry point: whether `resolve_processed_group` keeps `move_assignment`'s `from_state == target → return []` short-circuit is undetermined, and it decides what C6(a)/C6(b)'s mutants actually produce (a 500, a no-op, or a write) | plan gap | Orchestrator: one sentence in task 2. The mutation cells I propose are worded to bind regardless, so this is not a blocker. |
| D5 | Plan 9 task 2 requires `resolve_processed_group` to live in `_move_assignment.py`, and §6.1's 2026-09-21 correction requires two new enum members — neither file is in §4 | plan gap | Orchestrator: §4 fold (§2.3 row 1). **Blocker 1.** |
| D6 | Plan 9 §6's `q = 8` rows are unbuildable from F0 (item quantity 4) unless the fixture overrides the item's quantity | plan gap (fixture) | Orchestrator: §6 preamble fold (§2.3 row 2). |
| D7 | Plan 9 C8(a)'s **named** mutation ("execute any statement on `ctx.session` before `maybe_begin` … → subordinate mode → nothing commits") collides with task 2's own `assert not ctx.session.in_transaction()`, which fires first and produces an `AssertionError` rather than the uncommitted-transaction symptom | plan gap (mutation cell) | Orchestrator: amend the cell — "delete the `assert not ctx.session.in_transaction()` **and** execute the workspace `SELECT` before `maybe_begin`; both edits together produce the subordinate-mode symptom the row names." |
| D8 | §9 rule 18: plan 9 registers `resolve_processed_group` in §6.5 and no row pins its shape. `parse_items_processed_body` (C2 rows), `process_items_processed` (C3(l), C4 rows) and the two enums (C3(l)) are pinned | plan gap | **Owner** — card 5 (adding a criterion row is owner authority). |
| D9 | Plan 9 task 1 mandates echo-as-received; no row asserts it | plan gap | **Owner** — card 4. |

## 6. Perimeter extensions and §6.1b entries

### 6.1 Proposed §7 perimeter declarations

Verbatim text in §2.3, rows 3 and 4. Summary of every out-of-perimeter file a named mutation must
touch:

| Plan | Foreign file | Rows | Read? |
|---|---|---|---|
| 9 | `bm/services/infra/location_tracker/webhook_verifier.py` | C1(b) *(proposed)*, C1(e) *(already named)* | yes |
| 10 | `bm/domain/stock_report/state_map.py` | C1(b) | yes |
| 10 | `bm/services/commands/stock_report/_move_assignment.py` | C1(i) second site; C3(c) "with plan 4 mutated too" | yes |
| 10 | `bm/services/commands/tasks/update_task.py` | C4(b)–(e), probes P-a…P-d | yes — `update_task` at `:48`, `_DIRECT_FIELDS` at `:24` |
| 10 | `bm/services/commands/users/_clock_worker_shift.py` | C4(g), probe P-f | yes — `clock_out_shift_for_user` at `:131`, `new_state=TaskStepStateEnum.PAUSED` at `:213` |

Also note (not a mutation, but a perimeter fact): plan 9's §4 additions in §2.3 row 1 are
*production* edits, and the reviewer's `git diff` perimeter check will otherwise flag them.

### 6.2 Proposed master plan §6.1b rows

| File (foreign) | The load-bearing detail | What it arms | How it was found |
|---|---|---|---|
| `bm/services/commands/tasks/update_task.py` | that `update_task` writes **no** `Task.state` (`:48-113`; `_DIRECT_FIELDS` at `:24-37` excludes `state`) | It is the landing site for MC-2 probes P-a…P-d, i.e. plan 10 **C4(b)–(e)**. If a future change adds a real `Task.state` write here, four probe rows stop being planted defects and **C4(a)** ("the guard on the current tree passes") flips red | batch C2 projection, L-25 |
| `bm/services/commands/users/_clock_worker_shift.py` | `new_state=TaskStepStateEnum.PAUSED` at `:213` inside `clock_out_shift_for_user` (`:131`) | The registry's `paused_driver` classification and probe P-f — plan 10 **C4(g)** and the guard's `paused_driver` rule. Changing the literal breaks the guard's own contract, not just the probe | batch C2 projection, L-25 |
| `bm/services/tasks/task_steps/finalize_pending_step_completion.py` | `performed_by = payload["performed_by_user_id"]` at `:34` — this handler has **no `ctx`**, so the payload key is the only actor source | MC-17's "performer, not credited user" at S9 — plan 10 **C1(l)**. It is also why `ctx.user_id` is not an available mutant there | batch C2 projection, L-25 |

## 7. Standing projection checks — results

- **Every cited path exists.** All nine S1–S9 command files, the three helpers,
  `_step_transition_core.py`, `update_task.py`, `_clock_worker_shift.py` and the cited integration
  test all resolve. Plan 10 §2's line numbers (verified 2026-09-19) still hold within ±3 at
  `798fc69`: `transition_step_state.py:177`→`:177`, `force_task_ready.py:111`→`:111`,
  `resolve_task/fail_task/cancel_task.py:54-56`→`:54`, `add_task_steps.py:91`→`:91`,
  `remove_task_step.py:225`→`:225`, `finalize_pending_step_completion.py:93`→`:93`.
  Plan 9's new files correctly do not exist.
- **§6.5 / §6.1 names match.** `resolve_processed_group(session, assignments, *, row, workspace_id,
  now, trigger)`, `parse_items_processed_body(raw: bytes) -> list[str]`,
  `process_items_processed(ctx) -> dict`, `sync_task_stock_assignments(session, changed, *,
  workspace_id, actor_user_id, now)` — all as the plans cite. `ItemsProcessedOutcomeEnum` and
  `ItemsProcessedReasonEnum` are **absent from `enums.py`** (only named in a comment at `:60-62`),
  which §6.1's own correction predicted — hence the §4 fold.
- **Rule 19 (unique test-file names).** All seven new names are unique across the whole test tree
  (`find tests -name <n>` empty for each); the only duplicated basename in the tree today is
  `conftest.py`. ✔
- **Rule 16 (the two frozensets).** Both plans' hand-typed-list mutations name real sites:
  plan 9 C3(c) mirrors the discovery predicate's `ACTIVE_ASSIGNMENT_STATES` inclusion; plan 10
  C3(b)–(f) mirror the sync's `TERMINAL_ASSIGNMENT_STATES` skip. **All my proposals hand-type
  locally and never edit `enums.py`** — editing the frozenset would also redden
  `tests/unit/domain/stock_report/test_assignment_state_enum.py:15`, which asserts
  `RESOLVED_EARLY in TERMINAL_ASSIGNMENT_STATES` directly.
- **§10's `client_id` fact.** Exactly one ordering claim across both plans depends on creation
  order: plan 9 **C7(b)** ("rows ascending", two elements) — owner card 1. Plan 9 C5(a)/C5(b) and
  C7(a)/(d) order by *request* order, not id; plan 10 C1(c) asserts a coalesced count, not an
  order; plan 10 task 1's "per task ascending `client_id`" is an implementation rule with no
  assertion. Plan 9 C8(b) is already declared unforceable. ✔
- **Rule 17 (externally-derived fixtures).** Plan 9's parsing fixtures are grounded against the
  shipped sibling `stock_demand_request.py` (stdlib `json`/UTF-8, no invented shapes):
  `b"{}"`→`dict`, `b"[]"`→`list`, `[{"article_number": 612}]`→`int` failing `isinstance(str)`.
  C7(c)/C7(e)'s `stored "2"` / `recomputed "0"` are grounded: `_repair_records.py:9-14`'s `_text`
  stringifies before the Text column. X2's ascending lock is already provided by
  `_locks.py:22-41`. No ungrounded rule-17 row found in either plan.
- **Arithmetic audit (L-17 outcome half).** I recomputed plan 9 C7(c), C7(d), C7(e) and plan 10
  C5(a)/(b)/(c) against `_move_assignment.py`'s actual delta and self-heal logic. **All correct.**
  C7(e)'s "exactly two repair records" is right: `in_queue` `0+(−2) ≠ 0` and `in_progress`
  `1+(−3) ≠ 0` each write one, `awaiting` `1+(−1) == 0` writes none (`:160-176`). C7(d)'s `G == 6`
  is right (1 kept from the `awaiting` exit, +2, +3). C5(b)'s counter walk `(0,0,4) → (0,4,0) →
  (0,0,0)` and `G == 4` are right. **No L-17 outcome defect found** — the only outcome-cell issues
  are cards 1–3, which are not arithmetic.
- **L-1 (enumerate, never sample) and L-22 (`≤` on a derived count).** No new instance in either
  plan. `grep "≤"` returns nothing in plans 9 and 10. Plan 9's F5 ladder is fully enumerated by
  C3(a)–(f) (all three active states, all three terminal states via C3(c)'s three sub-cases); plan
  10's map is enumerated by phase 1's `test_state_map.py:27` (`STALLED` has no write site among
  S1–S9 — it is the value probe P-a plants precisely because nothing writes it). C3(l)'s
  membership clauses read as a closed-vocabulary guard, not an outcome disjunction, since each of
  C3(a)–(f) already asserts its one exact pair; I did **not** raise it as an L-1 card.
- **Task text vs. criterion (L-3).** One instance: plan 9 task 1/2's echo-as-received, asserted by
  no row → card 4.

## 8. Blockers, ranked

1. **Plan 9 §4 omits two files the plan's own task 2 requires editing** (`_move_assignment.py`,
   `enums.py`). Consequence if unfixed: the reviewer's perimeter diff flags correct work as an
   automatic finding, costing a round — the exact shape batch B2 paid for. Fix is mechanical
   (§2.3 row 1). **Must land before the implementer prompt compiles.**
2. **Plan 10's C5 mechanism is unbuildable as specified** (§3.2) and **its three mutation cells
   name a site that does not exist** (§3.3). Consequence: the tester is blocked mid-session on a
   fixture cell it may not edit, or ships three rows that cannot fail. Fixes are the §2.3 folds.
   **Must land before the implementer prompt compiles** (the fixture text shapes the test file).
3. **Two unfailable rows and one coin-flip row** (cards 1–3). They do not block implementation, but
   each will be scored as verified evidence it is not. Should be ruled before the tester prompt.
4. **D1's string-vs-enum mismatch at four of the nine sites.** Will be resolved silently in code if
   not folded — the class this gate exists to catch, though the consequence is small.
5. **D7's plan 9 C8(a) cell** — an already-named mutation whose stated symptom the code contradicts.
   Cheap fold; if unfixed the tester records the wrong observed red.

## 9. What I did not check

- **I ran nothing.** No test, no mutation, no suite, no `pg_locks` probe. Every claim about what a
  mutation *produces* is derived from reading `_move_assignment.py`, `_locks.py`,
  `_repair_records.py` and the nine command files. The mutants I marked **corrected** are the ones
  where reading contradicts the prior pass; the mutants marked **plan-determined** name sites in
  files that do not exist yet and are derived from task text plus a shipped sibling — a tester must
  still confirm each executes under its row's own fixture (L-31).
- **Which side wins plan 8 C5(a)'s barrier race, and why.** §3.1 explains what I could and could not
  ground. The "warm connection" account is not supported by the code I read; I could not replace it
  with a verified account without running.
- **The 0.5 s "observed block" bound** in the proposed C5 choreography is empirical; I took it from
  the shipped precedent rather than measuring it.
- **Whether a reachable two-`Task.state`-writes-in-one-transaction command exists anywhere** (card
  2's re-point branch). I read `remove_task_step.py` and `_task_state_transitions.py` closely enough
  to rule S8 out; I did **not** trace `transition_step_state.py` (570 lines) or
  `transition_step_state_batch.py` exhaustively for such a path.
- **Plan 9's and plan 10's *named* (non-empty) mutation cells**, except where a check in §7 or a
  finding above crossed one (9 C3(c), 9 C8(a), 10 C2(a), 10 C5(a)–(c), 10 C4(b)–(h)). The prompt
  scoped me to the `—` cells; the other named cells are unaudited.
- **Plan 10's C4 registry-guard design** (the AST collector's search space, the five site classes,
  the `no_sync` reasons). I verified the six probe *sites* exist; I did not project the collector.
  §9A L-11 targets exactly this and is folded only as far as the probe sites.
- **Phases 1–8 and 11.** Two notes in passing, neither a blocker on C2: (a) `_locks.py:22-41`'s
  `populate_existing=True` is the project's only "post-lock re-read" mechanism, which affects how
  any future plan words a re-read mutation; (b) inventory U1's `remove_task_step` ready→pending→ready
  premise is refuted by the shipped code (card 2) — that is an inventory-handoff fact, not a plan 8
  or 11 defect.
- **The archgraph.** No graph orientation or delta this session: projection writes no code, and my
  write perimeter is this file alone.
