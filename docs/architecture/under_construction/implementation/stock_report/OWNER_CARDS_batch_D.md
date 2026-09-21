---
subject: stock_report — owner cards parked during the unattended batch D run
date: 2026-09-21
actor: orchestrator
status: OPEN — nothing here has been applied
---

# Owner cards parked during batch D

**Read this with `FINALIZATION_STEPS.md`.** That file is the plan; this one is the short list of
things the plan could not decide.

**The rule I am holding myself to overnight** (recorded in `FINALIZATION_STEPS.md`): I rule cards
along the ratified intention, but I **park anything that turns on a domain invariant or a
published contract**. Those land here with their evidence, and the batch keeps moving around
them. The reason is measured, not caution: earlier today I read a nullable column and a permissive
request model as evidence of a domain rule, called it "decisive", and was wrong — you caught it.
Unattended, nobody catches it.

**Nothing below is applied.** Each card states what I would do, so a one-word answer is enough.

---

## Card D-1 — `PATCH …/priority-order` has no tenancy criterion

**Class:** criterion row. **Authoring a row is yours, always** — so this is a proposal, not an
amendment. I have not touched plan 12.

**The gap.** Plan 12 **C1(o)** enumerates all three visibility cells — foreign workspace,
soft-deleted, absent — for the `PATCH …/priority` route. There is **no equivalent row for
`PATCH …/priority-order`**, which is a second route with its own `require_roles` list, its own
request model, and its own command module.

**Why it is probably harmless, and why that is not the point.** The two commands share the same
row-lookup shape, so the behaviour is most likely already right. What is missing is the row that
would notice if it were not. This pipeline has now found the same shape eleven times in one batch
— *a row whose evidence is delegated to something that never performs the check* — and three
unarmed promises were closed in a single day (C4(i), C4(j), C4(k)). A second route whose tenancy
is asserted only by its sibling's row is that shape.

**Cost if you say yes:** three assertions in a file the tester is already writing. Near zero.

**Proposed cell text** — a new row **C1(p)**, modelled exactly on C1(o) and using the same
cross-workspace reference the §6 preamble already defines:

> | C1(p) | three calls as U of W — `SO(row of the foreign workspace, 1)`, `SO(a soft-deleted row of W, 1)`, `SO("sri_absent", 1)`. The foreign row is a **cross-workspace reference** (preamble): same category, same properties, same `high` group with the same orders, so tenancy is the only reason it refuses | `NotFound` each; no state anywhere changes; the foreign workspace's group is byte-identical | three mutants at `set_stock_report_item_priority_order.py`'s row lookup (def.), **all three runs recorded** (L-34's three visibility cells): (i) drop the `workspace_id` term → the foreign row is found and reordered; (ii) drop `is_deleted = false` → the soft-deleted row is reordered and its live neighbours are renumbered around it → `order_density` diverges; (iii) return the serialized row instead of raising when the lookup finds nothing → the absent id answers 200 | M4 |

**One claim in that text I verified rather than assumed.** Mutant (ii) says `order_density`
diverges. `compute_stock_report_divergences` loads rows under
`StockReportItem.is_deleted.is_(False)` (`consistency.py:126`) and then walks each priority group
expecting `1..n` dense (`:184-197`), so a soft-deleted row that gets reordered shifts its **live**
neighbours and the group stops being dense. The divergence kind is right.

**If you would rather not add a row:** say so and I will record the gap as a known-uncovered
surface in plan 12 §7, which is honest and costs nothing. The wrong outcome is silence.

---

## Card D-2 — where `stock_report_item:deleted` is built (likely self-resolving)

**Class:** registry, not criterion — **I can apply this one** and expect to.

Plan 13 never says where the `stock_report_item:deleted` event is constructed. §6.5's `_events.py`
registers only the `:updated` and assignment builders, and `stock_report_item:created` is built
**inline** in `apply_stock_demand.py` — so both a shared builder and an inline construction have a
shipped precedent, and the plan is genuinely silent rather than wrong.

I told the implementer to pick one and state the exact `file:symbol`, and I register it in §6.5 in
the same act (§9 rule 18). It matters because **plan 14's C1(b) accuracy guard** is rooted in
`_events.py` plus every `event_name=` site: a name built somewhere no registry entry explains is
exactly what that guard exists to catch.

**Listed here only so you can see it was noticed and closed, not so you have to answer it.**

---

## Card D-3 — plan 13A's conditional validator extraction (D2, not yet live)

**Class:** perimeter over an APPROVED file. **Parked — this is yours.**

Plan 13A §4 makes the shared per-field validator extraction **conditional**: *"only if the
per-field validators must be exposed for reuse."* §7 records the recommendation to extract with no
behaviour change, and notes plainly that this is *"silent freedom over a phase-7 APPROVED file."*

**I will not let an implementer resolve that on its own judgement**, and I will not resolve it
myself either, because it is a perimeter question over approved code rather than a question the
intention settles. Before D2 starts I will write the decision into the D2 prompt one way or the
other; if you are awake by then, it is a one-word answer. My recommendation, for the record:
**extract, with a behaviour-preserving refactor and phase 7's suite green unchanged as the proof**
— the same shape as D1's authorised `_row_values` consolidation, which the registry already
ordered for the same reason (one shared helper, divergence is the failure mode).

---

## Card D-4 — the ratified intention still calls `item_category` three keys

**Class:** ratified intention **and** a published frontend contract. **Parked — this is the exact
class I do not rule unattended**, and the D1 implementer was right to raise it rather than fix it.

**The state of the three documents.** You asked on 2026-09-21 for the item category's picture to
reach the stock-report board. The code now sends it: `serialize_stock_report_item` emits
`item_category` as **four** keys, and I verified at the D1 gate that the key is genuinely armed —
including the case that matters, a category with **no** image, where the key must be present and
`null` rather than absent. `HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` §6.1 promises it
to the frontend as `string | null`. **But intention §9 "Response shapes" still says three.**

**Nobody is blocked and nothing is wrong today.** The risk is entirely in the future, and it is
the one this project has already been bitten by: the intention is the document everything is
re-derived from. Someone re-deriving the board from it drops a key the app renders, and the
pictures disappear from a screen that has shown them for a year.

**Why I am not amending it myself,** even though the answer looks obvious: the intention is
RATIFIED and carries a status header every gate reads, and the key is in a **published** contract.
Both halves of my overnight limit apply at once. Earlier today I reasoned from a schema to a
domain rule, called it "decisive", and was wrong — the failure mode there was propagating
something outward into a contract, and this is the same direction.

**Branches.**
- **Amend the intention** (a lettered note under §9, the way other owner amendments land): the
  three documents agree again, nothing in the code or the frontend moves.
- **Drop the key from the code:** reverts the row you personally asked for and breaks a promise
  already made to the frontend in writing. I would advise against this, but it is available.
- **Leave it:** shipped behaviour stays right, the root document stays wrong.

**Recommendation: amend.** The four-key shape is the one you instructed, the one already promised
to the frontend, and the only one that renders.

**On silence:** nothing changes. The code keeps four keys, the contract stands, and the batch is
**not** gated on this — the gate holds on the amendment, not on D1.

**Trace.** Intention §9 "Response shapes"; plan 12 C4(e) and its Review-log notes;
`HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` §6.1.


---

## Card D-5 — **THE ONE THAT MATTERS.** Phase 12 activates a data-destroying defect in APPROVED phase 3

**Class:** production defect in **APPROVED, VERIFIED** phase-3 code. **Parked because fixing it
reopens an approved phase**, which is a gate decision and yours — not because the direction is
unclear. The direction is settled by ratified text; only the authority to act is missing.

**This is the reason D1 is not APPROVED.** Found by the tester as `BLOCKED-PRODUCTION` on plan 12
**C3(d)**; I confirmed both halves by hand against the code and the intention.

### What breaks

Change a row's priority while it has work out (`quantity_awaiting > 0`) and two things follow:

1. **The board reports phantom drift forever.** MC-6 requires the `priority_change` record to
   snapshot the live `quantity_awaiting`, and phase 12 does exactly that. But
   `consistency.py:compute_stock_report_divergences` runs its `goal_total` rule over **every**
   `StockReportHistoryRecord` in the workspace with no `type` filter (`:200-222`), comparing each
   record's `quantity_awaiting` against the sum of assignments *credited to it*. Nothing is ever
   credited to a priority record, so the expected value is `0` and the snapshot is reported as a
   divergence — permanently, on every health check.
2. **Running the repair endpoint then destroys the record.** `repair_stock_report.py:248-255`
   answers that divergence with
   `UPDATE stock_report_history_records SET quantity_awaiting = 0` keyed on `client_id` alone,
   again with **no type filter**. The snapshot MC-6 required is overwritten with zero. History
   records are append-only by §6.2; this silently rewrites one.

### Why the intention settles the direction

§14C's divergence table, line 1594, scopes the rule to **"`quantity_awaiting` of each goal
record"** — and §6.2 (line 794) and MC-5 (line 836) both define a *goal record* as the row's
`quantity_requested_change` record. The code applies the rule to all three record types. **The
code contradicts ratified text**; the fix is a `type == quantity_requested_change` filter in the
two places above.

### Why nobody caught it before, and why it is phase 12's problem anyway

**Phase 3 was not observably wrong when it was approved.** Until this batch, the only history
records that existed were `quantity_requested_change` — phase 12 is the first writer of
`priority_change` and `priority_order_change`. The defect was **latent and unreachable**, and
phase 3's suite could not have seen it. Phase 12 is what makes it live.

That cuts both ways, and I want to be straight about it: phase 12's own code is **correct** — it
snapshots the counter MC-6 tells it to. But shipping phase 12 as it stands turns on a path that
corrupts data, so I do not think D1 should be approved without this resolved.

### Branches

- **Authorise the fix inside D1** (my recommendation): add the type filter in `consistency.py` and
  `repair_stock_report.py`, re-run phase 3's suite unchanged as the proof of inertness — the same
  shape as the `_row_values` consolidation the registry already ordered. Reopens phase 3's
  approval for one narrowly-scoped, ratified-text-directed change.
- **Defer it to its own phase after D:** honest, but D1 then ships a live corruption path, and the
  tester's witness test stays red on the tree.
- **Rule that priority records should not snapshot the counter at all:** contradicts MC-6 and
  changes a criterion row. I do not recommend it, but it is the only branch that leaves phase 3
  untouched.

**On silence.** Nothing is fixed, C3(d) stays `BLOCKED-PRODUCTION`, D1 is **not** approved, and
the suite carries one deliberate red (`test_the_priority_record_snapshots_the_live_awaiting_counter`)
that documents input → expected → observed. The tester kept it red on purpose rather than deleting
an assertion to ship green, which was the right call.

**Trace.** Intention §14C (line 1594), §6.2 (line 794), MC-5 (line 836), MC-6;
`consistency.py:200-222`; `repair_stock_report.py:248-255`; plan 12 C3(d).

---

## Card D-6 — a tripwire that cannot trip, and the correction that saves D2

**Class:** criterion row (C2(b)'s restatement is yours). **The D2 half I resolved myself, by
measurement.**

**Two findings here, and the second one reverses the first's implication — so read both.**

### The confirmed half: plan 13 C2(b) cannot fail

C2(b) exists purely as a tripwire: it should redden if anyone makes the counter repair read a
stale ORM copy of `stored_before` instead of re-reading it. The tester planted exactly that
defect, at the site the cell names *and* at the site the code actually lives
(`_move_assignment.py:_apply_counter_delta`), and **the test stayed green both times**.

**Confirmed by my own measurement.** The counter statement is
`update(StockReportItem).where(client_id == …).values(…).returning(…)` — an ORM-enabled UPDATE
whose criteria SQLAlchemy can evaluate, so it synchronises the identity-mapped instance. I probed
it directly: after the update the ORM attribute reads **7** and a fresh `SELECT` reads **7**. The
stale-copy defect is not merely hard to observe here; it **cannot occur**. The production code is
correct; the proof behind it is empty.

### The half the tester got wrong — and it is the one that decides D2

The tester extrapolated: *"13A C5(b), the only armed evidence anywhere for the gap-close's fresh
`removed_order`, is likely to be inert for the same reason."* If true, that would have removed the
entire stated reason for splitting batch D.

**It is not true, and I measured it rather than reasoning about it.** I probed
`close_priority_gap`'s shift statement in the exact shape 13A C5(b) will use — load a row into the
identity map, run the shift, then compare. Result: **ORM attribute = 3, fresh `SELECT` = 2.** The
instance **is stale**.

The asymmetry is real and now explained, both halves measured in one run:

| statement | shape | ORM after | DB after | stale? |
|---|---|---|---|---|
| counter (`_apply_counter_delta`) | equality on `client_id`, `RETURNING` | 7 | 7 | **no** — synchronised |
| shift (`close_priority_gap`) | range criteria `priority_order > n`, column-referencing SET | 3 | 2 | **yes** |

SQLAlchemy can match and refresh an instance identified by a simple primary-key equality; it
cannot evaluate the shift's range criteria, so those instances are left untouched.

**Consequences, and they are good news:** §9 rule 3 holds for the shift statements it was written
about. **13A C5(b) is armable, the cascade's fresh `removed_order` is a real requirement with real
evidence coming, and the D1-before-D2 split was correct.** No action needed on 13A.

### What I need from you, narrowly

Only C2(b)'s disposition. The tester recommends *accept it unguarded and record why*; I agree —
the requirement it guards is genuine but unobservable at that site, so a restatement would be
inventing a defect to catch. **Restating the row is yours.** On silence it stays `BLOCKED-PLAN`
and is not counted as covered, which is the honest state.

**Worth keeping as a lesson regardless (L-40):** *"ORM-enabled `update(Model)` is not a Core
update — whether it leaves an instance stale depends on whether SQLAlchemy can evaluate the
criteria. A staleness rule stated over 'any UPDATE' is too coarse, in both directions: it
over-promises evidence at PK-equality sites and it under-credits real evidence at range-criteria
sites."*

---

## Card D-7 — three smaller rulings the tester raised

Grouped because each is a sentence, none blocks anything, and all three are yours.

1. **Plan 13 C3(a) counts three assignment-deletion events; its own C1(a) fixture makes four.**
   Stale since the round-8/9 `resolved_early` addition. The code emits four and the tests agree —
   only the written rule disagrees with its own setup. *Recommendation: correct it to four.*
   Correcting a criterion outcome is yours, so it stays `BLOCKED-PLAN`.
2. **Plan 13 C1(c)'s "empty history" is not achievable** for a re-created row, per the tester.
   Needs your reading of what the row should say.
3. **Plan 13 C1(a) mutant (i) is inert** (soft-deleting the row before the assignment loop is
   unobservable) and **the tester could find no replacement** — MC-16's cascade-ordering clause is
   genuinely unguarded. *Whether that deserves a criterion row is yours.* I folded five other
   inert mutants this round where a working replacement existed and was measured; this is the one
   where none does.


---

## Card D-8 — the "row deleted" announcement is pinned by nothing (reviewer's R-1)

**Class:** criterion row. **Yours to author.** Recommendation: **yes, add it.**

This batch created `build_stock_report_item_deleted_event` and I registered it in §6.5 at the D1
gate. **§9 rule 18 says every registered public signature must be pinned by a row in its own
plan, and this one is pinned by nothing.** The reviewer proved it rather than asserting it: it
changed the announcement's `extra` block from `{}` to junk and ran the entire deletion test file
— **every test passed.** Two references exist in the tree and neither reads `extra`.

So a later change could start shipping fields the frontend never agreed to, or drop the empty
block a renderer relies on, and nothing would notice. The guard is one assertion in a test file
that already captures these events.

**Rule 18 exists because of exactly this**, and this is its first violation since it was written.
Worth noting as a process lesson in its own right: *registering a signature should emit a pin
obligation at the same moment* — I registered it and did not check that anything pinned it.

**On silence:** the row stays unpinned and is recorded as a finding, never as coverage.

---

## Card D-9 — seven statements address a row by id with no workspace term (reviewer's R-2)

**Class:** production, but **no behaviour change and nothing is wrong today.** Recommendation:
**yes, but as a follow-up after D — not inside this batch.**

Both the tester and the reviewer raised this independently, and the reviewer found it is **seven
statements, not the four I noticed**: five in the deletion cascade (assignment `SELECT`, counters
`SELECT`, position `SELECT`, row soft-delete, history soft-delete) and two in the priority
commands (the mover `UPDATE`, the serialize re-read).

**No tenancy hole exists.** The caller has already resolved and locked the row by workspace and
`client_id` is a globally unique prefixed ULID. The problem is legibility: *the same function
threads `workspace_id` into three of its statements and omits it from five others*, so no reader
can tell which omission is deliberate. This project has already repaired exactly this shape once
(batch B1 added `Task.workspace_id` to `set_task_stock_flag`).

Seven one-line additions; the existing suite staying green is the proof of inertness.

---

## Card D-10 — eight tests answer to no rule (reviewer's R-3)

**Class:** plan. Recommendation: **fold four, delete three, and decide the fifth with them.**

Five tests were declared as candidates by the implementer and carried unchanged by the tester;
the reviewer found **three more** that re-check at the HTTP layer something two existing rows
already prove one layer down. None is credited against any row, so none inflates coverage — but
they are surface nobody is assigned to keep honest.

The reviewer's recommendation, which I endorse: **fold the four request-body guards** (unknown
fields ×2, an explicit `null` priority, an absent filter) because they guard a defect this project
actually shipped once (batch C1's S1), and **drop the three HTTP-layer duplicates.**

**The lesson under it is the one worth keeping:** *a candidate test must be adopted or deleted in
the round that creates it.* These have now been deferred twice and the question comes back bigger
each time.


## Carried OUT of the pipeline entirely — not cards, not for tonight

Repeated from `FINALIZATION_STEPS.md` so this file stands alone:

1. **The mandatory-category enforcement gap.** An Item cannot validly exist without a category,
   but the backend does not enforce it and `Item.item_category_id` is nullable; the invariant has
   been held by frontend validation. Needs its own intention, a migration, a **backfill audit** for
   category-less rows already in the database, and a decision for every existing caller.
2. **`test_database_isolation.py` slot-sensitivity** — a foreign APPROVED project's file. Costs
   nothing today: both IDs are named in the 23-ID baseline.
3. **The `migrations` exclusion from the MC-2 write-site guard.** A migration can change task state
   invisibly, in **any** form — arguably a wider door than the four constructs card R-1 closed.
   Noticed 2026-09-21, never ruled.
