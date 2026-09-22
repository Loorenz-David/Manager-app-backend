---
plan: 13A, 14 (batch D2)
role: projection
round: 0
verdict: BLOCKED
state: OWNER_DECISIONS_PENDING
date: 2026-09-22
actor: projectionist (Opus)
tree: e3ca0a6, `git status --porcelain` empty, `git diff` digest da39a3ee5e6b (clean)
prompt: prompts/projectionist/2026-09-22_batch_D2_projection_1.md
---

# Batch D2 projection — round 0. Verdict: **BLOCKED**

## Owner-readable opening

I walked both remaining plans against the code that actually ships, and the batch is not ready to
implement. The blocking problem is the one thing this batch was split apart to protect: the plan
says a particular bookkeeping step can go wrong in a way that one test will catch, and I measured
that it cannot go wrong that way at all. If that measurement is right, the test everyone is
counting on would pass whether the code is correct or not — the exact "looks proven, proves
nothing" failure this project has been hunting all week. Separately I found a small piece of
shared vocabulary the new webhook needs that nobody ever built, and one document instruction that
still says "write this" when it should say "check this". Three things need you personally; the rest
is routine amendment the orchestrator can apply. Nothing was changed in the tree: I wrote only this
report.

---

## ⚠ OWNER DECISIONS REQUIRED (3)

### Card 1 — Re-measure the stale-copy claim before batch D2 is implemented?

**Question.** Should the orchestrator re-run its own measurement of the stale-copy behaviour on the
real database before anyone builds phase 13A — yes, or proceed on the existing measurement?

**Story.** Batch D was split in two specifically so one test could exist. The story was: when the
board deletes two rows of one priority list in a single request, the code keeps an in-memory copy
of the second row that has gone out of date, so it must re-read the position from the database or
the list ends up with a hole in it. I tried to break the code the way the plan says it breaks, and
the breakage did not happen — the library keeps that in-memory copy up to date by itself. If that
holds on the production database, the guard everyone is relying on would stay green no matter what,
and we would ship believing we had proof we never had.

**Branches.**
- **Re-measure first** — one short run on the real database settles it; costs minutes, and either
  confirms the split was right or retires a guard that cannot fail.
- **Proceed on the existing measurement** — the batch gets built around a test that may be
  incapable of failing, and nobody finds out until something breaks in production.

**Recommendation.** Re-measure first — two measurements disagree, they cannot both be right, and
this is the cheapest moment in the project to find out which.

**On silence.** The gate holds; no implementer prompt is compiled for phase 13A.

**Trace.** plan_13A §6 C5(b) mutant (i); §7 Q2; master_plan.md §4 batch D tracker row (the split
rationale); `_delete_stock_report_item_cascade.py:146-156`; `_ordering.py:41-55`.

---

### Card 2 — Does the new webhook get its own copy of the field checks, or share phase 7's?

**Question.** Should the two small field checks the new delete webhook needs be pulled out of the
already-approved demand webhook into a shared place, or simply written again in the new file?

**Story.** Both webhooks read entries that carry a category name and a properties object, and both
must reject an entry where either is malformed. Today those checks are four lines living inside the
approved demand parser, with no name of their own — there is nothing to import. Sharing them means
editing a file that is already signed off; copying them means two places that could one day drift
apart and reject things differently. Nothing in either plan checks that the two rejection messages
stay identical, so the drift the sharing is meant to prevent would be invisible either way.

**Branches.**
- **Share** — one edit to approved code, both webhooks reject identically forever.
- **Copy** — approved code is untouched, four lines exist twice, and drift would go unnoticed.

**Recommendation.** Copy. The new webhook does not need the shared version, the drift risk is
unguarded in both directions, and touching approved code needs a reason better than tidiness.

**On silence.** The gate holds; one criterion's test instruction cannot be written either way.

**Trace.** owner card D-3; plan_13A §4 "Edited", §8 "Shared per-field validators", C1(h);
`stock_demand_request.py:48-56`.

---

### Card 3 — The last documentation check: a person's eye, or an automated one?

**Question.** Should the final documentation criterion be checked by an automated test like its four
siblings, or stay a reviewer reading the document by eye?

**Story.** The last phase publishes the contract the frontend builds against, including which fields
can come back empty and under what condition. Four of its five checks are automated. The fifth — the
one about empty fields — is written as "the reviewer reads the serializers". That is the only check
in the project with no test behind it, on the document the frontend will trust most, and it is the
kind of check that quietly stops happening once the reviewer is tired or the document grows.

**Branches.**
- **Automate it** — a small test compares the document's field table against the code; it keeps
  working after everyone has moved on.
- **Leave it to the reviewer** — nothing to build now, and the contract's accuracy depends on one
  person reading carefully once.

**Recommendation.** Automate it — the project's own standing rule is that criteria are met by tests,
and this is the last one that is not.

**On silence.** The gate holds; the row ships as written, unarmed.

**Trace.** plan_14 §6 C2(a); charter standing rule 1; master_plan.md §9 rule 15.

---

## 1. Gate check

| Check | Result |
|---|---|
| Intention status header = `RATIFIED` | **PASS** — `planning/intention.md` line 2: `status: RATIFIED — by the owner (David): ratified 2026-09-18, re-ratified 2026-09-18 … and 2026-09-19 …` |
| Dependencies APPROVED (13, 9 for 13A; 10, 11, 13A for 14) | PASS for 13A — batch D1 APPROVED at `d800e73` |
| No upstream gate handoff in `OWNER_DECISIONS_PENDING` for these phases | PASS |
| Tree identity | `e3ca0a6`, clean |

**Doctrine note (not a finding against the work, but recorded).** The prompt's read-first list names
`/Users/davidloorenz/agent-skills/plan-projectionist.md`. **That file does not exist.** The canonical
doctrine is `plan-projection.md`, which I read and followed. Worth correcting in the prompt template
so a future session does not silently proceed with no doctrine loaded.

**Second prompt correction.** Prompt item 5 says "§9 rule 17 also applies: Postgres lock
re-evaluation and deadlock shapes." Master plan **§9 rule 17** is *"Relocating a row's test to a
narrower surface is a criterion change"*. The rule that governs Postgres-owned shapes is **charter
rule 17** (externally-derived fixtures), which is what plan 13A's own header means. No work was
misrouted; flagging so the next prompt does not send someone to the wrong rule.

---

## 2. THE BLOCKER — C5(b)'s armability, measured

**The prompt's instruction:** *"Do not let C5(b) be retired on the strength of C2(b)'s inertness. If
you believe C5(b) cannot be armed, that is a stop-and-report, not a fold."* I did not accept C2(b)'s
inertness as evidence about C5(b). I measured C5(b)'s own mechanism directly, and I am reporting a
result that **contradicts L-40's measurement**.

### 2.1 What the plan and the split assert

Master plan §4, batch D tracker row:

> phase 13's cascade must re-read a row's `priority_order` from the database on every call (the
> previous gap-close makes a held ORM copy stale, §9 rule 3), and **no criterion in phase 13 can
> observe that** — its only armed evidence anywhere is 13A **C5(b)**

`_delete_stock_report_item_cascade.py:141-145` says the same in the shipped code:

> `priority`/`priority_order` come from a **fresh `SELECT`**, never from the ORM instance loaded at
> the lock. Phase 13A calls this cascade once per row inside one transaction, so by the second call
> that instance is stale after the first cascade's Core shift (§9 rule 3; 13A C5(b) is the only
> armed evidence of it anywhere …)

L-40, as relayed in the prompt: *"the counter statement (PK equality + `RETURNING`) leaves the ORM
**synchronised** (7 vs 7), while `close_priority_gap`'s shift (range criteria) leaves it **stale**
(3 vs 2)."*

### 2.2 What I measured

The shift is `_ordering.py:41-55`, an **ORM-enabled** `update(StockReportItem)` with no
`synchronize_session` option, so SQLAlchemy's default `"auto"` applies. `"auto"` tries the
`evaluate` strategy first and falls back to `fetch` only if the WHERE clause cannot be evaluated in
Python (`orm/bulk_persistence.py:990-1005`). Under `evaluate`,
`_apply_update_set_values_to_objects` (`orm/bulk_persistence.py:1811+`) recomputes each SET value in
Python and writes it into every matching object in the identity map.

**Probe A — is the `evaluate` path selected?** Run against the **real** `StockReportItem` model and
the **real** `StockReportPriorityEnum`, using the exact WHERE and SET of
`close_priority_gap(removed_order=2)`:

```
WHERE  : EVALUABLE  -> synchronize_session='auto' resolves to 'evaluate'
SET stock_report_items.priority_order: EVALUABLE  -> written into the ORM instance in Python
```

**Probe B — does a held instance actually go stale?** Standalone reproduction of both statement
shapes L-40 distinguishes (group `A1 R2 C3 D4` loaded with `populate_existing=True`, then the two
statements as shipped, `.returning(...)` included):

```
(a) counter, PK equality  : DB=6  heldORM=6  -> SYNCHRONISED
(b) shift,   range criteria: DB=2  heldORM=2  -> SYNCHRONISED
```

**The asymmetry L-40 asserts does not reproduce. Both shapes synchronise.**

### 2.3 What this means for C5(b)

C's held ORM instance ends R's cascade carrying `priority_order = 2`, not 3. Substituting
`row.priority_order` for the cascade's fresh `SELECT` therefore produces **identical** behaviour:
C's gap closes from 2, D moves 3 → 2, `high` = `A1 D2`, dense. **C5(b) mutant (i) is inert**, and
with it the sub-claim that the D1/D2 split exists to protect.

### 2.4 What I did **not** establish, stated plainly

- I ran on **SQLite with a sync `Session`**, not PostgreSQL + asyncpg + `AsyncSession`. `aiosqlite`
  is not installed, and I had no database credentials (`app/beyo_manager/config.py` requires
  `DATABASE_URL`; no `.env` is present) and would not have raced another session's slot for them.
- The evaluate/fetch decision and the Python-side value application are both made in SQLAlchemy's
  Python layer **before and independently of** the backend, which is why I expect the result to
  hold — but "expect" is not "measured", and I am not asserting C5(b) is unarmable on Postgres.
- I did **not** reproduce the preceding `remove_assignment` Core statements. They would, if
  anything, refresh the instance further — they cannot make it staler.

**This is why the verdict is BLOCKED rather than an amendment.** Two measurements disagree and only
one can be right. The resolution is cheap (owner card 1) and must happen before an implementer
prompt compiles.

### 2.5 What survives regardless

C5(b) is **not** worthless. Its other clauses are sound and armable: the dense `high = A1 D2`
outcome, the coalescer's `:deleted` rule, and the one-statement-per-lock-class measurement.
Mutants (ii) and (iii) are real (see §6 and §7). What is unarmable is specifically the ORM-staleness
sub-claim — and if card 1 confirms my measurement, the honest disposition is to record that
sub-claim as **unprovable with the reason**, not to manufacture a red for it.

**Consequential, and the orchestrator owns it:** `_delete_stock_report_item_cascade.py:141-145`'s
comment would then be **wrong in shipped, APPROVED code**. I changed no production code. Routed.

---

## 3. Prompt item 1 — Card D-3: does 13A need phase 7's validators exposed? **No.**

**I established this from 13A's tasks and phase 7's code, not from the plan's assertion.**

**Evidence — there is nothing to extract.** `stock_demand_request.py` has no per-field validator
functions. The "validators" are three inline expressions inside one loop:

```
48	        item_category_raw = item.get("itemCategory")
49	        category_ok = isinstance(item_category_raw, str) and bool(item_category_raw.strip())
50	        if not category_ok:
51	            defects.append(f"entry {index}: itemCategory must be a non-blank string")
52	
53	        properties_raw = item.get("properties")
54	        properties_ok = isinstance(properties_raw, dict)
55	        if not properties_ok:
56	            defects.append(f"entry {index}: properties must be an object")
```

13A needs exactly those two (task 2 excludes `quantityRequested`). "Exposing" them means **writing a
new shared helper inside an APPROVED file** and re-pointing phase 7's loop at it — not importing
something that exists.

**Evidence — the drift the extraction is meant to prevent is unguarded either way.** No test in the
repository pins those defect strings:

```
$ grep -rn "must be a non-blank string\|properties must be an object\|quantityRequested must be an integer" app/tests/
(no matches)
```

And 13A's own C1(f)/C1(g)/C1(h) assert `422`, never the message text. So extraction buys **no
observable guarantee** — it buys tidiness at the cost of editing approved code.

**Conclusion.** 13A does not need them. Card D-3 closes as **"no change" — phase 7 is not touched at
all**, and §4's conditional clause `stock_demand_request.py` (only if the per-field validators must
be exposed…) should be **struck**, removing the silent freedom §8 flagged. I make no
recommendation beyond the card, because C1(h)'s mutation site depends on the ruling (§6).

---

## 4. Prompt item 2 — D-13: the deleted event's `workspace_id` provenance. **Not observable. No red manufactured.**

**Ratified rule** (intention line 1495, restated in master plan §6.7):
> `workspace_id` on every event comes from the entity's row, never from `ctx`.

**The site.** `_delete_stock_report_item_cascade.py:201-205` builds the event from its
`workspace_id` **parameter**:

```
201	    events.append(
202	        build_stock_report_item_deleted_event(
203	            client_id=row.client_id, workspace_id=workspace_id
204	        )
205	    )
```

*(Citation correction: the prompt cites `delete_stock_report_item.py:126` as the site that fills it
from `ctx`. The actual site is **`:121`** — `workspace_id=ctx.workspace_id`; line 126 is a closing
paren.)*

**Does 13A's second caller make it observable? No — and the reason is stronger than in phase 13.**

`process_stock_demand_deleted` never reads `ctx.workspace_id` (task 3 step 4.5 says so explicitly).
It takes the value from `verify_location_tracker_webhook`, which returns a **single configured
workspace**:

```
webhook_verifier.py:25	    workspace_id = settings.location_tracker_webhook_workspace_id
webhook_verifier.py:42	    return workspace_id
```

Every candidate row is then discovered under that same value —
`_demand_lookup.py:69` `StockReportItem.workspace_id == workspace_id` — so
`event.workspace_id == row.workspace_id` **by construction, for every row in the loop, no matter how
many rows the batch deletes.** Looping over many rows does not create the divergence, because all
rows are scoped to the one workspace before the loop begins.

**Answer.** Card D-13 closes as **"unobservable, not unnecessary"**, with this measurement recorded.
13A's §4 perimeter should **not** be widened, no provenance fix is proposed, and **no cell text is
proposed for a row observing it** — there is nothing for such a row to observe.

**Separately, and it is a different claim:** C3(d)'s mutant *"build `workspace_id` from `ctx`
(`""`)"* **is** armable. `ServiceContext.workspace_id` is `self.identity.get("workspace_id", "")`
(`context.py:36-37`) and the webhook constructs `ServiceContext(identity={}, …)`
(`location_tracker_webhooks.py:34`), so the mutated value is `""` ≠ W. That mutant stays.

---

## 5. Prompt item 3 — plan 14 C1(b)'s guard root. **The cell is CORRECT. The prompt's premise is wrong.**

This is the item I most expected to confirm, and the measurement refused. Reporting it as found.

**The prompt says** C1(b) "must root in master plan §6.7 plus every `event_name=` site in
`app/beyo_manager/`, not in `_events.py` alone — otherwise it cannot see
`build_stock_report_item_deleted_event` … nor `stock_report_item:created`."

**The cell does not root in `_events.py` alone.** Its current text already reads:

> every event name in **master plan §6.7** and every name constructed at an `event_name=` site under
> `bm/services/commands/stock_report/` (the `stock_task_assignment:{kind}` template's three values
> included)

**Measured — every stock-report event name is inside that directory.** `grep -rn "event_name=" app/beyo_manager/`, filtered to stock-report names:

| Name | Site | Under `…/commands/stock_report/`? |
|---|---|---|
| `stock_report_item:deleted` | `_delete_stock_report_item_cascade.py:59` | **yes** |
| `stock_report_item:created` | `apply_stock_demand.py:271` | **yes** |
| `stock_report_item:updated` | `_events.py:12` | yes |
| `stock_task_assignment:{kind}` (created / state-changed / deleted) | `_events.py:33` | yes |

Master plan §6.7 lists exactly these six names. **The guard as written sees all of them, including
the two the prompt feared it would miss.**

**Widening to `app/beyo_manager/` would be a defect, not a fix.** The same grep returns ~60 further
`event_name=` sites — `task:note-updated`, `item:upholstery-requirement-state-changed`,
`upholstery:order-created`, `notification:new`, `workspace:reset` and so on. C1(b) fails **in both
directions**, so a root of `app/beyo_manager/` would demand that every event name in the entire
application appear in the *stock report* frontend handoff. The guard would be red on arrival.

**Disposition:** do not widen the root. One accuracy improvement is worth applying (§7, F-14): the
cell still says `stock_report_item:deleted` lives "wherever phase 13 puts it" — it now has a
concrete home, `_delete_stock_report_item_cascade.py:59`.

**Real defect found in C1(b) instead — its two mutants bite the same direction.** See §7, F-13.

---

## 6. Prompt item 4 — plan 14 task 3. **The plan still says "author". Confirmed defect.**

Plan 14 **§5 task 3** reads, unchanged:

> 3. The frontend handoff: the routes, roles, payload shapes **with nullability per field**, the
>    override retry contract (MC-13), …

That is authoring language, and §4 "Files expected to change" reinforces it by listing the new dated
handoff unconditionally under **New:**.

The **Review log** (lines 175-206) states the correction:

> **Task 3 therefore changes from *author* to *re-verify and re-issue*.** … re-read each against the
> code, flip its tag to VERIFIED, correct anything that moved, and — **only if something moved** —
> publish a new dated file superseding this one … If nothing moved, say so in the handoff and leave
> the published file alone. **Never edit it in place.**

**The plan body was never updated to match its own Review log.** An implementer compiling from §5
tasks and §4 files — which is what an implementer does — authors a replacement document and moves a
correct published file to `archived/` for no reason. Given this project's history (an in-place edit
cost the frontend four days), leaving the contradiction in the body is not acceptable. Proposed
replacement text in §7, F-15/F-16.

**Two further path defects in plan 14, both measured:**

- **§2 read-first item 5** cites `HANDOFF_TO_FRONTEND_stock_report_api_20260921.md` as living under
  `handoffs/to_frontend/`. **It does not** — it is at
  `handoffs/to_frontend/archived/HANDOFF_TO_FRONTEND_stock_report_api_20260921.md`. The live
  document is `…_api_v2_20260921.md`. The same sentence describes it as "tagged PROVISIONAL"; the
  live v2 file uses **VERIFIED / SPECIFIED** tags (its §1), not PROVISIONAL.
- **§4** sets the `supersedes:` minimum to `HANDOFF_TO_FRONTEND_stock_report_api_20260921.md`. If a
  re-issue happens it must supersede **`…_api_v2_20260921.md`**, the current document.

**Confirmed correct, and left alone:** `…match_preview_v2_20260921.md` is live at
`handoffs/to_frontend/`, is **not** archived and is **not** listed as superseded anywhere. Owner
card 7 is honoured.

---

## 7. Prompt item 5 — the six carried questions of §14E

The owner waived 13A's mechanism-inventory re-check on the condition that these are checked here.
Discharged, one by one, against the shipped tree.

| Q | Plan's stated rule | My check | Verdict |
|---|---|---|---|
| **Q1** lock order / cycles | every path ascends MC-1's classes | **Re-derived independently.** `create_stock_task_assignments` items→tasks→rows `:79-81`; `delete_stock_task_assignments` tasks→rows→assignments `:68-70`; `repair_stock_report` advisory→tasks→rows→assignments→history `:169,173,182,194,206`; `process_items_processed` rows→assignments `:114,118`; `sync_task_stock_assignments` rows `:76`→assignments `:82`; `apply_stock_demand` rows (`with_for_update()` `:185`) then goal; `delete_stock_report_item` advisory `:69`→tasks `:94`→row+group `:99`→assignments `:105`. `_locks.py:_lock` sorts within every class (`sorted(client_ids)` `:31`, `.order_by` `:33`). **No path acquires a lower class after a higher one. Q1's conclusion HOLDS.** | **CONFIRMED** — but three of §7 Q1's own `file:line` citations have drifted (F-11) |
| **Q2** several rows / two of one group | one advisory lock, one sorted statement per class, cascades in ascending `client_id`, each closing its own gap from post-previous positions | The sequencing rule holds. **But C5(b), the row that proves it, carries a false event order (F-04), a mutation at the wrong site (F-02), an inert mutant (§2) and an unproducible seeding premise (F-06).** | **AT RISK — see §2 and F-02/F-04/F-06** |
| **Q3** does the D6 statement bound apply | no bound on the cascade; the find step is bounded exactly — 5 statements for *all not_found*, 4 for *all category_not_found*, identical at 3 and 30 entries | **Citations verified exactly.** `_demand_lookup.py:25-26` (`if not keys: return {}`) and `:61-62` (`if not identities: return {}`) are correct to the line. `_locks.py:22-24` returns `{}` without executing on an empty id set. **But the derivation has a hole: step 4.8 is a bespoke statement, not a `_locks.py` call, and nothing specifies that it short-circuits on zero candidates.** As written it would execute and the count would be 6, not 5. | **PLAN GAP — F-05** |
| **Q4** replay instrument after a self-heal | first delivery may write repair records; replay reads `not_found`, zero writes over five tables, dispatches nothing, record count unchanged | `write_repair_record` takes a free-form `trigger` string (`_repair_records.py:17-41`); the cascade builds `f"inline:{trigger}"` (`:134`). C4(b)'s expected record shape is producible. | **CONFIRMED** |
| **Q5** MC-20 check after a Scanner deletion | `[]` for W and for W′; the soft-deleted goal record stays consistent | **Derived rather than assumed, and it is right.** `consistency.py`'s `histories` query carries **no `is_deleted` filter**, so the soft-deleted goal record **is** evaluated — the clause is not vacuous. `_recompute_goal_totals_for_workspace` also has no `is_deleted` filter, so it sums deleted assignments. After C3(a): A1 (`awaiting`) is uncredited by `_goal_credit.py:129` → `credited_history_record_id = None`, G 10 → 8; A2 (`resolved`) and A4 (`resolved_early`) fall to `apply_goal_effect`'s final branch and **keep** their credit memory. Recompute = 3 + 5 = **8** = stored. **No divergence. C5(e)'s parenthetical arithmetic is exactly correct.** | **CONFIRMED** |
| **Q6** reset unaffected | no new table; the four phase-1 reset phases hard-delete what Scanner left soft-deleted | 13A adds no table, column or migration; §4's "Not changed" list covers `app/migrations/`, `bm/models/`, `bm/services/commands/reset/`. C5(f)'s mutation (move the reset phases after `delete_tasks` → FK RESTRICT) is a reordering mutant and bites. | **CONFIRMED** |

**§9 rule 17 / CF-2 (C5(g)).** The row is present in plan 13A §6 and owed by this batch. Its two
mutants (drop `sorted(...)` from `absent_identities`; drop `.order_by(StockReportItem.client_id)`
from the `FOR UPDATE`) are **subtractive** and sound. Its file home is undeclared by §4 — §8 proposes
`test_process_stock_demand_deleted_locks.py`; that needs to become a §4 entry, not a note (F-10).

---

## 8. L-41 — the additive-mutant audit

**Every mutation cell in 13A (37 rows) and plan 14 (5 rows) classified.** Shape taxonomy:
**subtractive** (delete a term/call), **reordering** (move a step), **substitutive** (replace one
behaviour with another), **additive** (add a write, an event or a statement). L-41's absorption
mechanism is specific: a spurious **write** is overwritten by a later `UPDATE … RETURNING`, and a
spurious **event** is dropped by `coalesce_stock_report_events`. It does **not** absorb an addition
that a row observes by *count* or by *absence*.

**Result: 42 criterion rows audited. 2 carry no mutant at all (13A C7(a), 14 C2(a) — F-19). Of the
40 that do, exactly **1 cell is ABSORBED**: 13A C3(d)'s first mutant. The other 39 bite.**
*(Counted per cell, not per mutant: C5(b) carries three mutants, C1(b) and several others two.
C3(d) also carries a second mutant, which is sound — only its first is absorbed.)*

### 8.1 The one absorbed cell

| Cell | Current mutant | Absorbed? | Why | Replacement |
|---|---|---|---|---|
| **13A C3(d)** | "emit `:updated` for R" | **YES — ABSORBED** | `_events.py:90-92`: the coalescer drops **every** `:updated` whose `client_id` is in `row_deleted`. R carries a `:deleted`, so an *added* `:updated` for R is dropped exactly as the genuine ones are. C3(d) stays green. The guarantee lives in the coalescer, so the mutation must be applied there. | **see F-01 below** |

**F-01 — proposed replacement for C3(d)'s first mutant (exact text):**

> `_events.py` `coalesce_stock_report_events` (def., `:91`): drop `or client_id in row_deleted` from
> the `:updated` skip condition → the `stock_report_item:updated` events `remove_assignment` already
> built for R (`_move_assignment.py:260-266`, emitted whenever a counter delta is non-zero — A1
> `awaiting` q=2, A3 `in_queue` q=1 and A6 `in_progress` q=3 each produce one) survive coalescing and
> R gains `:updated` events it must not have → red. The site is APPROVED phase-8 code and is probed,
> not edited.

*(I verified the premise rather than assuming it: `_move_assignment.py:260` emits a row `:updated`
only `if any(value != 0 for value in deltas.values())`. In C3(a)'s fixture three of the six
assignments produce a non-zero delta, so the coalescer genuinely has something to drop and the
mutation genuinely reddens. In C5(b)'s fixture both R and C hold one `in_queue` assignment, so both
produce one.)*

### 8.2 Additive cells that are **not** absorbed, and why (stated so the class is not over-applied)

| Cell | Mutant | Shape | Why it still bites |
|---|---|---|---|
| 13A C1(i) | "reject or validate the key" | additive (validation) | Adds a **refusal**, not a write or event. 422 ≠ the expected 200/`deleted`. |
| 13A C2(h) | "find-or-create (call the demand insert)" | additive (write + event) | The row asserts the **absence** of the write and event by name — "zero `INSERT` on `stock_report_items`", "no `:created` event". `coalesce_stock_report_events` never drops a `:created` (`_events.py:90` filters `kind == "updated"` only). Both halves redden. |
| 13A C5(b) mutant (iii) | locks inside the per-row loop | additive (statements) | The row counts statements under `record_statements` and asserts **exactly one** per class. An addition is precisely what the instrument sees. |
| 13A C5(d) | "one `SELECT` per entry" | additive (statements) | Same — the assertion is an exact count (5 / 4). |
| 13A C6(a) | "any statement before it" | additive (statement) | The assertion is on the **first** recorded statement's identity. |
| 13A C3(b) | "cancel / soft-delete the task; touch a step" | additive (write) | The row snapshots task `state`/`updated_at`/`updated_by_id`/`is_deleted` and step state before, asserts byte-identity after. **Verified no overwrite exists:** `_task_flag.py:14` writes `is_stock_assignment` with `updated_at=Task.updated_at` — it preserves `updated_at` and never touches `is_deleted`. Nothing overwrites the planted change. Also "no task event dispatched" holds: `_coalesce_key` maps a non-stock-report event to `("other", id(event))`, a unique key per event, so foreign events are **never** coalesced away. |
| 14 C1(b) mutant (ii) | add a name to §6.7 / a new `event_name=` site | additive (name) | The guard's forward direction is an absence claim over the handoff. Bites — **but it duplicates mutant (i)'s direction; see F-13.** |

### 8.3 Full classification (remaining 35 cells)

Subtractive: C1(a), C1(b), C1(d), C1(h), C1(k), C2(a), C2(b), C2(d), C2(f), C2(g), C4(a), C4(b),
C5(e)×2, C5(g)×2, C6(b), C5(b) mutant (ii), 14 C1(a), 14 C1(c), 14 C1(d).
Reordering: C1(c), C5(a), C5(c), C5(f).
Substitutive: C1(f), C1(g), C1(j), C2(c), C2(e), C3(a)×2, C3(c), C3(e), C7(b), C5(b) mutant (i),
C3(d) mutant (ii).
**None of these is absorbed** — L-41's mechanism reaches only spurious writes and spurious
`stock_report_item:updated` events.

---

## 9. L-42 — per-row fixture audit of every ordered assertion

Audited **individually**, per the lesson. Nine ordered assertions across both plans.

| Row | Ordered claim | What the fixture makes distinguishable | What it does **not** | Verdict |
|---|---|---|---|---|
| **13A C5(b)** | the event list "exactly: `:deleted` R, `:deleted` C, two assignment `:deleted`, one `:updated` for D" | counts (1 R, 1 C, 2 assignment, 1 D) and payloads | **The stated order is not the order the shipped coalescer produces.** Derived: `_events.py:87` orders by **first-seen key index**, so the true sequence is `[a_R:deleted, D:updated, R:deleted, a_C:deleted, C:deleted]`. Asserted literally, the row is **red against correct code**. | **DEFECT — F-04** |
| **13A C3(d)** | "exactly: one `:deleted` (R), six assignment `:deleted`, one `:updated` for C" | counts and payloads | Same defect: true order is `[six a:deleted …, C:updated, R:deleted]`. **Additionally** the six assignment events are emitted in ascending `client_id` (`_delete_stock_report_item_cascade.py:81 .order_by(StockTaskAssignment.client_id)`), which is **not** the fixture's A1…A6 naming order — `client_id` is a ULID with no monotonic counter. A positional pairing of event *i* to A*i*'s state is flaky by construction. | **DEFECT — F-04, F-07** |
| **13A C5(c)** | `results [deleted, not_found, deleted]` in request order | **Strong.** `not_found` sits in the **middle**, so both named mutants (sort by outcome, sort by `client_id`) move it and redden. The three entries span two priority groups and one never-created identity. | It does not pin the relative `client_id` order of R and X — but no sort order of the three produces the expected middle-`not_found` sequence, so discrimination holds regardless. | **SOUND** |
| **13A C2(d)** | `[category_not_found, deleted]` in request order | The two outcomes differ, and category-name sorting ("Dining Chairs" < "Serving Trolleys") would reverse them. | **The ordering claim is unarmed** — the named mutant ("reject the request / stop at the first miss") is not an ordering mutation. C5(c) carries the ordering arming for the phase. | Sound but unarmed; acceptable (C5(c) covers) |
| **13A C7(b)** | `outcomes [deleted, category_not_found, not_found]` | **Strong** — three *distinct* outcomes, so any permutation is visible; plus byte-for-byte echo of differing raw values. | — | **SOUND** |
| **13A C5(b)** | `high = A1 D2` (dense) | the density | **The §6 preamble demands "`priority_order` ascending **disagrees** with `client_id` ascending inside `high`" and gives no mechanism to produce it.** `client_id` is a ULID; creation order does not determine sort order (the plan says so itself at line 149). Seeding four rows in sequence produces the required disagreement **by chance**. | **DEFECT — F-06** |
| **13A C3(c)** | `high = A1 C2` | the density and that R keeps `priority_order 2` | Fixture label drift: C3(a) calls the middle row "**B2** of `A1 B2 C3`" and then says it is R; C3(c) calls the same group `A1 **R2** C3`. Resolvable but a transcription hazard. | Sound; label drift noted (F-12) |
| **13A C1(j)** | 422 naming "entries 0 and 1" | the two raw property values differ (`["Teak","Dark"]` vs `["dark","teak"]`) while normalising to one signature, so "compare raw dicts → 200" bites | — | **SOUND** |
| **13A C1(k)** | 422 naming "entry 0" **and** "entry 2" | entry 1 is valid and sits **between** two defects, so "stop at the first defect" and "apply entry 1" both redden | — | **SOUND** |

**Plan 14** carries no ordered assertion. C1(a)–C1(d) are set-membership guards.

---

## 10. Decision ledger

| # | Decision point | Classification | Proposed routing |
|---|---|---|---|
| D-1 | Does the cascade's held ORM copy actually go stale? Whole D1/D2 split rests on it | **intention/plan premise gap** | **BLOCKING — owner card 1** |
| D-2 | `StockDemandDeletedOutcomeEnum` does not exist; §4 says it ships in phase 1 | **plan gap** | F-08 — add `enums.py` to §4 for that name only (B4 precedent) |
| D-3 | Are phase 7's field checks extracted or copied? | **free choice, currently silent** | **owner card 2** — §4's "only if" struck either way |
| D-4 | C3(d) mutant (i) is absorbed | **plan gap** | F-01 — replacement text supplied |
| D-5 | C5(b) mutants (i)/(ii) name the wrong file | **plan gap** | F-02/F-03 — sites supplied |
| D-6 | C5(b)/C3(d) event **order** is ambiguous and, if literal, false | **plan gap** | F-04 — assert as multiset + counts |
| D-7 | Does step 4.8 short-circuit on zero candidates? C5(d)'s exact 5 depends on it | **plan gap** | F-05 — task 3 step 4.8 gains the guard |
| D-8 | How is the `priority_order` / `client_id` disagreement produced? | **plan gap (producibility)** | F-06 — explicit two-step seeding |
| D-9 | How are the six assignment events paired to states? | **plan gap** | F-07 — assert a mapping, never a position |
| D-10 | C5(g) has no §4 file home | **plan gap** | F-10 — §8's note becomes a §4 entry |
| D-11 | Plan 14 task 3 still says "author" | **plan gap** | F-15 — replacement text supplied |
| D-12 | Plan 14 §2/§4 cite an archived path and the wrong supersedes target | **plan gap** | F-16/F-17 |
| D-13 | Deleted event's `workspace_id` provenance | **resolved by measurement** | closes "unobservable, not unnecessary" (§4) |
| D-14 | Plan 14 C1(b) both mutants bite one direction | **plan gap** | F-13 |
| D-15 | Plan 14 C1(d) plants in `states.md` only, asserts "both" | **plan gap** | F-18 |
| D-16 | Two `—` mutation cells remain (13A C7(a), 14 C2(a)) | **plan gap / criterion** | F-19; **C2(a) → owner card 3** |

**Zero silent freedom remains.** Every point above is routed to an amendment, a card, or a recorded
measurement.

---

## 11. Findings — proposed replacement text

**Nothing below was applied. Mutation and fixture cells are the orchestrator's.**

- **F-01** — 13A C3(d) mutant (i): text in §8.1 above.
- **F-02** — 13A C5(b) mutant (i) **site is wrong**. The cell says `process_stock_demand_deleted.py`
  (def.), but the gap close happens inside `cascade_delete_stock_report_item`, whose signature
  (`session, row, *, workspace_id, actor_user_id, now, trigger`) accepts **no positions** — there is
  no edit at the named site that produces the described defect. Correct site, **if card 1 confirms
  the staleness exists**: `_delete_stock_report_item_cascade.py:146-156` (def.) — replace the fresh
  `SELECT priority, priority_order` with `row.priority` / `row.priority_order`. **If card 1 confirms
  my measurement instead, this mutant is retired as unprovable with the reason recorded.**
- **F-03** — 13A C5(b) mutant (ii) site: `_events.py` `coalesce_stock_report_events` (def., `:91`),
  not `process_stock_demand_deleted.py`. Mutant (iii)'s site is correct as written.
- **F-04** — 13A C5(b) and C3(d): replace "events exactly: …" with **"the coalesced event list
  contains exactly these and nothing else, asserted as a multiset with per-name counts; order is not
  asserted"**. Rationale and derived true order in §9. If order *is* wanted, C5(b)'s true sequence is
  `[a_R:deleted, D:updated, R:deleted, a_C:deleted, C:deleted]`.
- **F-05** — 13A task 3 step 4.8: append **"skipped entirely when the candidate set is empty (no
  statement issued) — C5(d)'s count of exactly 5 depends on this"**. Without it, `client_id.in_([])`
  still compiles and executes and the *all `not_found`* shape counts **6**, not 5.
- **F-06** — 13A §6 preamble: replace the assertion that the seed disagrees with a **procedure** —
  "seed the four rows, read back their `client_id`s, then assign `priority_order` through phase 11's
  `set_stock_report_item_priority_order` so that ascending `priority_order` is the **reverse** of
  ascending `client_id`; assert the disagreement in the fixture before the act under test." ULIDs
  carry no monotonic counter, so creation order cannot be relied on to produce it.
- **F-07** — 13A C3(d): "six `stock_task_assignment:deleted` with the states at deletion" → **"…
  asserted as a mapping `{assignment client_id: state}`, never by list position — the cascade emits
  them in ascending `client_id` (`_delete_stock_report_item_cascade.py:81`), which is not the
  fixture's A1…A6 order."**
- **F-08** — 13A §4: the sentence *"The enums this phase reads (`StockDemandDeletedOutcomeEnum`, the
  `stock_demand_deleted` member of `INLINE_REPAIR_TRIGGERS`) ship in phase 1 from the master plan
  registry"* is **false against the tree**. Neither exists:
  `grep -rn --include='*.py' 'StockDemandDeletedOutcomeEnum|INLINE_REPAIR_TRIGGERS' app/` returns only
  `enums.py:67,69` — a **docstring** saying they *"belong to phases 9 and 13A and are not shipped
  here (charter rule 4 — no constant with no caller)"*. Master plan §6.1 already carries the same
  correction (2026-09-21, batch B2). Proposed: add to **Edited** — **"`bm/domain/stock_report/enums.py`
  — `StockDemandDeletedOutcomeEnum` (`deleted`, `not_found`, `category_not_found`) **only**;
  precedent is batch B2 blocker B4, which added `enums.py` to the perimeter for one name."** And
  **do not add `INLINE_REPAIR_TRIGGERS`** — `write_repair_record` takes a free-form `trigger` string
  (`_repair_records.py:38`) and the cascade builds `f"inline:{trigger}"` (`:134`), so the frozenset
  has **no caller** and charter rule 4 forbids it.
- **F-09** — 13A §8: the note *"the sentence itself is added to master plan §9 rule 7 by the
  orchestrator, and **until it is there**, C5(b)'s measured clause rests on this note"* is **stale**.
  §9 rule 7 already carries the sixth use verbatim ("sixth use, owner card 8, 2026-09-21 … plan 13A
  C5(b), §7 Q2"). Strike the conditional.
- **F-10** — 13A §4: add `test_process_stock_demand_deleted_locks.py` as C5(g)'s declared home, so the
  reviewer's perimeter check does not read it as a fourth undeclared test file.
- **F-11** — 13A §7 Q1 citation drift (conclusion unaffected): `create_stock_task_assignments`
  **`:79-81`** not `:89-91`; `delete_stock_task_assignments` **`:68-70`** not `:78-80`;
  `sync_task_stock_assignments` **`:76` and `:82`** not `:86-92`. `repair_stock_report :169-206` and
  `process_items_processed :114-118` are correct.
- **F-12** — 13A C3(a): "R … as **B2** of `A1 B2 C3`" vs C3(c)'s `A1 **R2** C3`. One label.
- **F-13** — 14 C1(b): **both named mutants bite the same direction.** (i) deleting a name from the
  handoff and (ii) adding a name to the code both trip *"a name in the code missing from the
  handoff"*. The **reverse** direction — *"a name in the handoff that no site builds"* — the row
  explicitly claims, is **unarmed**. Proposed mutant (iii): **"add `stock_report_item:archived` to
  the handoff's event table while no `event_name=` site and no §6.7 entry builds it → the reverse
  direction reddens."** (Charter rule 12: one mutation per sub-check.)
- **F-14** — 14 C1(b): "`stock_report_item:deleted` wherever phase 13 puts it" → **"…at
  `_delete_stock_report_item_cascade.py:59`"**. It has a home now.
- **F-15** — 14 §5 task 3: replace the authoring sentence with **"Re-verify the published
  `HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` against shipped code: read each of the six
  SPECIFIED routes field by field, flip its tag to VERIFIED, and correct anything that moved.
  **Re-issue only if something moved** — a new dated file in the same folder under the same name
  scheme, carrying a `supersedes:` key naming `…_api_v2_20260921.md`, with that file **moved**
  (never edited) to `archived/`. If nothing moved, record that in the session handoff and leave the
  published file untouched. `…_match_preview_v2_20260921.md` is not superseded and not moved."**
- **F-16** — 14 §4: move the new handoff from unconditional **New:** to **"New, conditional on task
  3 finding a divergence"**, and change the `supersedes:` minimum to `…_api_v2_20260921.md`.
- **F-17** — 14 §2 item 5: the cited path resolves only under `archived/`; the live document is
  `…_api_v2_20260921.md` and it is tagged **VERIFIED/SPECIFIED**, not PROVISIONAL.
- **F-18** — 14 C1(d) asserts every state value appears in **both** `states.md` and the handoff, but
  plants only in `states.md`. Add a second mutant: **"delete `resolved_early` from the handoff's
  state list → red"**, and record which bites on which (charter rule 12).
- **F-19** — **two `—` mutation cells remain**, contrary to the batch-D r0 claim of "zero empty
  mutation cells left in 12/13/13A/14":
  - **13A C7(a)** `— (wiring; calibration)`. Proposed: **"`location_tracker_webhooks.py` (def.): drop
    `dict(request.headers)` from the third route's `incoming_data` → the command receives no headers,
    the fake `run_service` assertion on `incoming_data` fails → red."**
  - **14 C2(a)** `— (review)` — **owner card 3**; it is also a charter standing-rule-1 exception
    (met by a reviewer, not a test) and should be stated as one if it stays.
- **F-20** — 14 §5 task 1 reads "**thirteen routes** … ; the **three** webhooks", which parses as
  13 + 3 = 16. The true total is thirteen **including** the three webhooks (10 `@router.` in
  `stock_report.py` + 3 in `location_tracker_webhooks.py` once 13A ships). One clause.

**Proposed Review-log line** (for the orchestrator to apply — I did not write it; the doctrine gives
that line to the coordinator):

> **Projection r0, 2026-09-22 (batch D2) — BLOCKED.** C5(b)'s ORM-staleness premise measured false on
> SQLAlchemy 2.0.40 (owner card 1); `StockDemandDeletedOutcomeEnum` unshipped and absent from §4;
> C3(d)'s first mutant absorbed by the coalescer; C5(b)/C3(d) event order false if literal; step
> 4.8's empty-set short-circuit undetermined; the `priority_order`/`client_id` disagreement
> unproducible as specified. 20 findings, 3 owner cards. Handoff
> `handoffs/projectionist/2026-09-22_batch_D2_projection_1_handoff.md`.

---

## 12. Prompt item 6 — the ordinary projection duties

| Duty | Result |
|---|---|
| Decision ledger | §10, 16 entries, all routed |
| Every path in both plans resolves | **Two failures:** plan 14 §2 item 5 (F-17); plan 13A §4's enum claim (F-08). New files correctly marked new. C5(g) has no declared home (F-10). |
| Every citation quotes text at the line it names | **Five drifts:** F-11 (three), the prompt's own `delete_stock_report_item.py:126` → `:121` (§4), F-14. **Verified exact:** `apply_stock_demand.py:271`, `_events.py:12`/`:33`, `_delete_stock_report_item_cascade.py:59`, `_demand_lookup.py:25-26`/`:61-62`, `create_task.py:99` (advisory-lock form), `_locks.py:22-24`. |
| Zero empty mutation cells | **FAIL — 2 remain** (F-19) |
| Criteria sized against §7 | **PASS.** `count_criteria.py` on this tree: `plan_13A 37 rows / 7 criteria`, `plan_14 5 rows / 2 criteria`. Both ≤ 8 criteria (charter target). |
| §7 sizing notes match actual counts | **PASS, derived not typed.** 13A §8 says "37 criterion rows in 7 criteria" ✓; 14 §7 says "5 criterion rows in 2 criteria" ✓; the prompt header's "(37/7)" and "(5/2)" ✓. |
| Trace cells resolve both directions | Every row in both plans carries a trace cell; each names a live §14E item, MC contract or M-ledger id. No unserved claimed entry found. |
| Charter rule 17 (externally-derived fixtures) | 13A §8's grounding block is **correct and re-verified**: SQLAlchemy 2.0.40 installed at `/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/sqlalchemy`; the asyncpg dialect maps `DeadlockDetectedError` at `PostgresError`, so the wrapper is `sqlalchemy.exc.DBAPIError` and the assertion is `exc.orig.sqlstate == "40P01"` — C5(a) and C5(g) say `DBAPIError`, which is right. **I could not re-verify the PostgreSQL 18.6 / `deadlock_timeout = 1s` server facts** — no credentials, no `.env`; cited as the plan's prior measurement, not re-measured. |
| Two-session fixture producibility | **PASS** — `async for fresh_session in get_db_session():` is the shipped precedent (`test_process_items_processed_locks.py:100`). |
| L4 taken | **None, as the prompt required.** All probes at hypothesis scope. **No pytest was run at all**, so `BEYO_TEST_SLOT=dpj` was never needed — no worker database was claimed by this session. |

---

## 13. Write perimeter — full declaration

**Documents written:** exactly one —
`docs/architecture/under_construction/implementation/stock_report/handoffs/projectionist/2026-09-22_batch_D2_projection_1_handoff.md`.

**Documents NOT written, deliberately:** `plans/plan_13A.md`, `plans/plan_14.md` (including their
Review logs), `master_plan.md`, `OWNER_CARDS_batch_D.md`. The prompt offered me the two plans' Review
logs; the projection doctrine's closing protocol assigns that line to the **coordinator**, and
another session is editing this tree concurrently. I took the conservative reading and proposed the
line instead (§11).

**Production code / tests changed:** none.
**Commits:** none. **Pushes:** none. **Archgraph deltas:** none.
**Scratchpad only (outside the repo, not committed):** two throwaway probe scripts under
`/private/tmp/claude-501/…/scratchpad/` (`probe_eval.py`, `probe_stale.py`).
**Tree at exit:** `e3ca0a6`, `git status --porcelain` shows only this new handoff.

---

## 14. Report what I could hide

Four things this session could have quietly smoothed over:

1. **Prompt item 3's premise is wrong.** I was told plan 14 C1(b) has a defect and asked to "report
   whether it has this defect". It does not — and the widening the prompt proposes would have made
   the guard red on arrival by pulling ~60 unrelated event names into a stock-report document. It
   would have been easy to confirm the expected answer.
2. **I contradicted a measurement the orchestrator made and labelled L-40.** The asymmetry it
   records (PK-equality synchronises, range-criteria goes stale) has no mechanism in SQLAlchemy's
   source and did not reproduce for me. I have stated exactly what I ran and exactly what I did not
   (SQLite, sync session, no Postgres) rather than presenting it as settled.
3. **The batch-D r0 claim of "zero empty mutation cells left in 12/13/13A/14" is inaccurate by two**
   for the plans in my scope (13A C7(a), 14 C2(a)).
4. **The prompt's doctrine path does not exist** (`plan-projectionist.md`), and its citation of
   `delete_stock_report_item.py:126` is off by five lines. Neither changed my work; both are
   reported because unreported small errors are how the large ones get through.

I also want to be explicit about a **non**-finding: I did not manufacture a red for D-13. The
provenance divergence is real in the code and genuinely unobservable in 13A, and the prompt
correctly anticipated that outcome. Reporting it as observable would have earned a criterion row
that could not fail — the exact defect family this batch is trying to close.
