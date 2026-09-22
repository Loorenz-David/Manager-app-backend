---
subject: stock_report — owner cards parked during the unattended batch D run
date: 2026-09-21
actor: orchestrator
status: OPEN — nothing here has been applied
---

# Owner cards parked during batch D

---

## ✅ OWNER RULINGS, 2026-09-22 — all remaining cards ruled

Verbatim: *"apply after D1 approves, then continue with D2. you should complete all the remaning
task by your self."* Taken together with the previous turn's *"yes"* to the recommendations, with
the four caveats I raised and the owner accepted by not overriding them.

**Timing is part of the ruling:** every row addition waits until **D1 is APPROVED**, so D1's
re-review scope stays clean (§3B — a fold that adds an assertion behind a running review produces
a ratified clause with no evidence; that became findings S2/S3 in batch C1).

| Card | Ruling | When |
|---|---|---|
| **D-5** | fix approved, scoped to goal records | **in flight now** |
| **D-4** | amend intention §9 to four keys — **and sweep §9 for other drift**, not just this key | after D1 |
| **D-1** | author C1(p), the priority-order tenancy row, from the drafted cell text | after D1 |
| **D-8** | author the row pinning `stock_report_item:deleted` — **highest priority of the three**, it is a published-contract promise with no guard | after D1 |
| **D-10** | **per-test, not as a block of four** (my caveat, unoverridden): fold the two `refuse_unknown_fields` guards, which guard a defect class this project actually shipped in C1; re-check the other two against existing rows before authoring, and drop the three HTTP-layer duplicates | after D1 |
| **D-6** | accept C2(b) unguarded — **record the SQLAlchemy version it was measured on**, because the inertness is dependency-owned (charter rule 17) and an upgrade reopens it | after D1 |
| **D-11** | accept the tiebreaker as a structural check — **record the query plan and table size**, same reason | after D1 |
| **D-7 (1)** | correct C3(a) to **four** assignment-deletion events | after D1 |
| **D-7 (2)** | "empty history" is unachievable and the row is reworded — see below | after D1 |
| **D-7 (3)** | **do NOT add a criterion row** — reversal of my own card, see below | after D1 |
| **D-9** | yes, but **after batch D closes**, not inside it | post-D |
| **D-3** | **not ruled now, by my recommendation** — D2's projection establishes whether 13A needs the validators exposed at all; if it does not, phase 7 is not touched | D2 projection |
| **D-2** | closed — registered by me at the D1 gate | done |

### Both labels must say "unobservable, not unnecessary" (D-6, D-11)

`EQUIVALENT` is accurate and **dangerous**: the next reader takes it as *"this code does nothing"*
and deletes it. D-6's fresh `SELECT` is inert only because of how the installed SQLAlchemy
synchronises the identity map; D-11's tiebreaker is invisible only under today's query plan on a
small table — and a bigger table is exactly the case the clause exists for. Both records carry the
measurement **and its conditions**.

### D-7 (2) — the reworded outcome

`apply_stock_demand` writes a goal record whenever `quantity_requested` rises above the previous
value, and **creation counts as previous = 0** (intention line 784; verified at
`apply_stock_demand.py:202-208, 243-258`). So a re-created row has **one** history record the
instant it exists, and "empty history" can never be true. The row's real intent is that **the
deleted row's history does not carry over**. Proposed outcome, for the record — the owner
authors:

> *a **new** live row whose history contains **only its own new goal record**, and none of the
> deleted row's records*

### D-7 (3) — I reversed my own recommendation

My card punted ("whether that deserves a criterion row is yours"). That was wrong. The tester
looked for a mutation that could observe MC-16's cascade ordering and **found none**. Where no
observable exists, **a criterion row cannot be armed either** — authoring one would manufacture
exactly the unarmable promise this project has now closed four times (C4(i), C4(j), C4(k), and
plan 10 C2(a)). It is recorded as a **structural check** instead.

**One honesty note:** this rests on the tester's measurement. It is one of the few claims in this
batch I did **not** re-verify myself.


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

> ## ✅ RULED BY THE OWNER, 2026-09-22 — **APPROVED, scoped**
>
> Verbatim: *"yes i approve the fix ( only assignment reconciliation against goal records )."*
>
> **The parenthesis is the specification** and it is narrower than "fix the bug": the
> assignment-reconciliation rule applies to goal records and to nothing else. Dispatched as a
> production fix round — **one** type predicate on the `histories` selection in
> `consistency.py`, so the `goal_total` rule is computed over `quantity_requested_change`
> records only.
>
> **The repair's mirror guard is deliberately NOT added.** I checked the callers before writing
> the prompt: `repair_stock_report` obtains its divergence list *only* from
> `compute_stock_report_divergences` (`:170`, `:217`, `:294`) and never builds one itself, so
> once the check stops emitting these entries the repair branch can never receive one. A second
> guard there would be an **unreachable mirror no test could arm** — the exact shape this project
> already recorded as **L-37** in batch C2. One filter fixes all three consumers (the repair, the
> read endpoint, and `assert_stock_report_clean`).
>
> **Phase 3 stays VERIFIED.** This is an owner-authorized amendment to shipped code, following
> the batch B1 precedent (`_task_flag.py` gained its `workspace_id` term the same way), not a
> reopened gate. The proof of inertness is phase 3's own suite green with **no test file
> touched**.
>
> **The proof the fix worked** is that plan 12 **C3(d)**'s witness test —
> `test_the_priority_record_snapshots_the_live_awaiting_counter`, deliberately red since the
> tester round — goes green **without being edited**.

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


---

# Resolutions, 2026-09-22 (post-D1-gate) — orchestrator

Under the owner's instruction *"apply after D1 approves, then continue with D2. you should complete
all the remaning task by your self"*. **Every ruling below is the owner's own, applied; where
measurement changed a card's shape, the change and its evidence are stated rather than folded away.**

## D-10 — RESOLVED, and its shape changed under measurement

**Ruled:** fold four, delete three. **Applied:** fold **six** under **one new criterion**, delete
**none**, author **no** row for the seventh.

The ruling carried an explicit condition — *delete only if confirmed by execution that the
behaviour is already proven one layer down.* The arming round tested it per test, as the card
required, and **the condition is not met**:

| Test(s) | Measured | Verdict |
|---|---|---|
| `test_ordering_routes_refuse_unknown_fields` ×2 | dropping `extra="forbid"` from both ordering body models reddens **exactly these 2 ids**, 51 passed | keep → **C8(a)** |
| `test_ordering_routes_refuse_malformed_bodies` ×3 | weakening the router's models reddens **exactly those 3 ids** (50 passed) while the integration file where C1(m)/C1(n) are armed stays **18/18 green** | keep → **C8(b), C8(c), C8(d)** |
| `test_priority_route_accepts_an_explicit_null` | narrowing the router model reddens **only that id** — a **422 where the published contract promises 200** | keep → **C8(e)** |
| `test_list_items_route_passes_no_priority_when_the_param_is_absent` | C4(b) + C4(d) already produce the identical payload for both inputs; the residue is an assertion on a **mocked collaborator's call argument** (charter rule 2) | **no row authored** |

**Why the three "duplicates" are not duplicates:** the two ordering routes declare their **own**
body models, separate from the `requests/__init__.py` models that C1(m)/C1(n) pin. The layer below
never executes the router's declarations. Deleting them would have left the 422 contract the
**published** frontend handoff actually promises pinned by nothing — the exact shape of §9 rule 18,
three months' worth of it.

So it was never *"eight tests answering to no rule"*. It was **one missing criterion**, now plan 12
**C8**, covering five promises of the published contract (§2.3, §5.2, §5.3). Totals 655 → **660**
rows, 107 → **108** criteria.

**All five mutants were re-measured by the orchestrator before the rows were recorded** — not
consumed from the tester's stamp — each reddening its own id alone, file restored `git diff --quiet`
exit 0. *A row recorded before its mutation is observed red is the failure this project has closed
four times; it is not being reopened for a card that looked clerical.*

**The eighth id** in the reviewer's list, `test_a_row_with_no_assignments_answers_an_empty_list`,
was outside the arming round's scope and remains **undecided**. It is the only piece of D-10 still
open and it is carried to closeout, not to D2.

## D-6, D-11, D-7(3) — recorded as **unobservable, not unnecessary**, with their conditions

A measurement that says "no honest test can see this" is only worth keeping if the conditions that
made it true are recorded with it. **If a condition changes, the measurement expires** — it does not
silently stay true. Installed at the time of measurement: **SQLAlchemy 2.0.40, pydantic 2.11.3,
asyncpg 0.30.0, PostgreSQL as configured by `pytest.ini`'s slot databases.**

- **D-6 — plan 13 C2(b)'s ORM-staleness tripwire cannot trip.** Condition: the counter statement is
  **PK equality + `RETURNING`**, which leaves SQLAlchemy 2.0.40's identity map **synchronised**
  (measured 7 vs 7). **Expires if** the statement's criteria widen from PK equality, `RETURNING` is
  dropped, or the SQLAlchemy major version moves. **It does not generalise:** the same measurement
  on `close_priority_gap`'s shift (range criteria) came back **stale** (3 vs 2), which is why
  **13A C5(b) is armable** and why batch D was split at all. That correction is **L-40**.
- **D-11 — plan 13 C4(a)'s `client_id` tiebreaker.** Conditions: the query plan
  (`Sort(created_at) ← Index Scan using ix_stock_task_assignments_stock_report_item_id`), which
  feeds a **stable** sort, and a table small enough that the planner chooses it. **Expires if** the
  plan changes to a merge/parallel sort or the table grows past the planner's threshold.
  **Narrowed by re-review finding R2-1:** *deleting* the term is unobservable, but **reversing** it
  (`client_id.desc()`) **reddens at the tied pair**. So the row is armed on two of three ordering
  sub-terms, not one, and the blind spot is smaller than this card originally described. The
  decision stands; the description was wrong and is corrected.
- **D-7(3) — the unguarded cascade ordering.** **No row authored, deliberately.** No observable
  exists at any boundary, and authoring one would manufacture a promise nothing can arm — the L-37
  shape this project has already shipped once and recorded. Recorded here so the absence is a
  decision with a reason rather than a gap.

## D-13 — NEW, and it is the owner's, not mine (raised by the arming round)

**Class:** production. **Status: PARKED for the owner; routed to D2's projection for measurement.
Not fixed, not ruled.**

Intention line **1495** is ratified: *"`workspace_id` comes from the entity's row, never from `ctx`
(§2.5)"*, and master plan §6.7 restates it verbatim. But
`_delete_stock_report_item_cascade.py:203` builds `stock_report_item:deleted` from the
`workspace_id` **parameter**, which `delete_stock_report_item.py:126` fills from `ctx.workspace_id`.
**The code contradicts ratified text.**

**Why it is harmless today, and exactly when it stops being:** the delete refuses anything outside
the caller's workspace, so the two values are identical by construction — which is also why plan 13
C3(b)'s named mutant (ii) is recorded `EQUIVALENT` and **unappliable**: "take it from `ctx`" *is* the
shipped form, so there is nothing to mutate. **13A adds a second caller** that deletes rows in a
**loop** rather than one per request. If that caller ever passes a workspace other than the row's,
deletion events address the wrong workspace's screens and **no test anywhere can see it.**

**Why I did not fix it, though it is one line and I hold a broad delegation.** Three reasons, and
the first is sufficient:

1. **It turns on ratified text**, which is the one class the overnight limit parks and the owner
   has not lifted. D-5 was this same class and it went to the owner.
2. Today it is **unfixable-with-evidence**: no test at a public boundary can distinguish the two
   values, so the fix would ship unarmed — and an unarmable guard is **L-37**, which this project
   has shipped once already.
3. It would **reopen phase 13 hours after it was approved**, for a change with no observable effect.

**Routed, not dropped.** D2's projection is asked to answer with evidence whether 13A's second
caller makes the difference **observable at the webhook boundary**. If it does, the one-line fix
belongs in 13A's perimeter with a row that can see it — the batch that creates the need pays for it,
and the named mutant becomes appliable. If it does not, this closes as "unobservable, not
unnecessary" with its conditions, like D-6 and D-11.

**Owner:** this is the one thing from the post-gate round that is genuinely yours. If you would
rather the one-line fix land now than wait for the projection's answer, say so and it is a
five-minute change.

---

# D2 projection cards — owner rulings, 2026-09-22

Verbatim: *"yes for both ( recomendations are correct )"*, answering the two I put to the owner.

| Card | Ruling | Authority |
|---|---|---|
| **D2-3 / plan 14 C2(a)** — the last documentation check | **AUTOMATE it.** A small test compares the handoff's field table against the serializers. It stops being the one criterion in the project met by a reviewer's eye rather than by a test | **owner, 2026-09-22** |
| **Frontend board bug (BL-1)** | **QUEUE as the first item of the wiring stage**, not fixed today. It is in the frontend repo and outside this pipeline | **owner, 2026-09-22** |
| **D2-1 / C5(b)'s staleness premise** | **Settled by the orchestrator's re-measurement, not by the owner** — the premise is **false**; see L-40's correction and L-49. Mutant (i) is retired as unprovable | orchestrator, measured |
| **D2-2 / D-3, the validators** | **CLOSE as "no change" — phase 7 is not touched.** This is the owner's own conditional ruling of 2026-09-22 discharging itself: *"D2's projection establishes whether 13A needs the validators exposed at all; if it does not, phase 7 is not touched."* The projection established it does not — `stock_demand_request.py:48-56` holds no validator *functions*, only three inline expressions, so "exposing" would mean **writing a new helper inside an APPROVED file**, and no test anywhere pins the defect strings. 13A writes its own four lines | owner's conditional, discharged |

### The one consequence of D2-1 that needs recording rather than ruling

With mutant (i) retired, **nothing in the project observes the cascade's fresh `SELECT` of
`priority`/`priority_order`.** It is recorded as **"unobservable, not unnecessary"**, like D-6 and
D-11, and with its conditions stated:

The re-read is inert **because** `synchronize_session="auto"` resolves to `"evaluate"` and every
term of `_group_where` plus the band evaluates identically in Python and in SQL **when the caller
passes an enum member**, which `cascade_delete_stock_report_item` does (`priority=row.priority`).
**It expires if** any of those becomes true: a criterion is added that Python cannot evaluate (a SQL
function, a subquery, a JSON operator); the caller ever passes a plain string again; the held object
is detached or expired rather than live in the identity map; or SQLAlchemy's default strategy
changes. **In any of those the re-read becomes load-bearing.** It is correct defensive code and is
**not** to be deleted on the strength of being inert — that is exactly the misreading the
`EQUIVALENT` label invites and the reason the owner required this wording.

---

# D2 review card — owner ruling, 2026-09-22

## S3 — the lock-order window — **RULED: FILE IT.** Owner, 2026-09-22.

**Not fixed in D2. Not accepted silently. Recorded with its measurement, and §7 Q1 corrected so it
is not left on record as unqualified.**

**What it is.** Scanner drops a rule and the delete webhook starts removing the board row. In the
same instant a worker assigns a task to that same row. For roughly a millisecond the webhook has
already discovered which assignments exist but has not yet locked anything, so the worker's new
assignment slips in behind the discovery. **The webhook still deletes it and the data still ends up
correct** — but to do so it reaches for a lock in an order §7 Q1 promises it never takes. If a third
actor is deleting an assignment on that same task at that instant, Postgres breaks the tie by
killing one request. Scanner retries; the worker sees a spinner. **Over a year of a busy floor this
is a handful of retries, not a data loss.**

**Why filing is right and is not just the cheap option.** The same shape has been shipping in
**APPROVED phase 13**'s `delete_stock_report_item` since it was approved — **D2 is not where it was
introduced and is not where it should be judged.** Fixing it means one re-discovery under the row
lock across two files, which reopens an approved phase on the project's last day, and the fix would
ship with **no test that can arm it**, because the race is not reproducible on demand. That is the
L-37 shape this project has already shipped once.

**The exact fix, recorded so the backlog item is actionable rather than a worry:** re-discover the
assignment set **under** the row lock rather than before it, in `process_stock_demand_deleted.py`
(steps 4.6–4.9) and in `delete_stock_report_item.py` / `_delete_stock_report_item_cascade.py`
block (i).

**What changes in the documents:** plan 13A **§7 Q1** must stop reading as an unqualified promise.
The reviewer's own wording for it: an unlocked discovery deciding a lock set is **sound for rows**,
because the advisory lock closes that window — but **not for children another path may add**. That
qualification goes into Q1 and into MC-1's note.

**Trace.** Review round 1 finding S3; plan 13A §7 Q1; `process_stock_demand_deleted.py` steps
4.6–4.9; `delete_stock_report_item.py`; `_delete_stock_report_item_cascade.py` block (i).

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
