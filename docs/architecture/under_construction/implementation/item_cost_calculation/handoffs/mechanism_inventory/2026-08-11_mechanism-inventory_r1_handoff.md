---
plan: pre-plan gate (mechanism-inventory)
role: mechanism_inventory
round: 1
date: 2026-08-11
state: COMPLETE — contracts written; gate held pending 2 owner decisions
verdict: GATE_HELD (not PASS) — every silent-failure mechanism now has a
         contract-grade definition in the intention; two of them are marked
         PROVISIONAL pending owner cards 1 and 2
actor: Claude (mechanism-inventory doctrine, /Users/davidloorenz/agent-skills/mechanism-inventory.md)
---

# Mechanism inventory — item_cost_calculation, round 1

Gate check passed before work: `planning/intention.md` read `status: resolved` with §17
**EMPTY**; `planning/owner_decisions.md` showed all 4 cards with filled `ANSWER:` lines;
§16's changelog ended at Round 2 with no mechanism-contracts delta.

I inventoried the whole intention, not only §15's flagged list. **31 load-bearing
mechanisms**, of which 20 needed a contract they did not have. The delta is written into
`planning/intention.md` as seven inserted lettered sections — **§4A, §6A, §7A, §7B,
§8A, §10A, §11A** — plus changelog **Round 3 (M-1…M-20)**, §14 test items 15–21,
inline supersession pointers on every numbered passage a contract overrides, and a
rewritten §17. No section was renumbered.

Six of the twenty are **defects in the intention as written**, not merely
under-specification — each would have produced working-looking code:

- **M-1** §7.2's commit steps are ordered insert-then-close. Against INV-E1's
  non-deferrable partial unique that raises `UniqueViolation` on *every* second commit
  of a task, not only under concurrency. §7A.1 pins close → insert → back-link for all
  four chains.
- **M-2** "auto-path failure never fails task creation" (card 3) is unimplementable with
  a `try/except` — `create_task` runs one transaction (`create_task.py:76`) and a failed
  statement poisons it in PostgreSQL. §7B.5 pins pre-checks plus `begin_nested()`.
- **M-3** `fixed_monthly_cost_minor ≥ 0` permits a zero rate, and §6.4 then divides by
  it; the quantized rate can also underflow to `0.0000` from entirely legal inputs.
- **M-8** Time can settle *after* an episode closes — `transition_step_state` guards only
  on the **step** being terminal (`transition_step_state.py:150`), and nothing re-emits
  the result event — so a stored result can disagree with a live recompute forever.
  (⚠ owner card 1.)
- **M-10** The §10.2 journal covers non-deleted items while the column drop destroys
  soft-deleted items' amounts too: `downgrade` would be silently lossy.
- **M-12** `serialize_step` has **five** call sites, not the two §10.4 names. `GET
  /tasks/{task_id}` (WORKER **and** SELLER) and `GET
  /working-sections/steps/user-last-active` (WORKER — the worker's live step card) also
  leak `total_cost_minor` today.

---

## ⚠ OWNER DECISIONS REQUIRED (2)

### Card 1 — Does time logged after a task closes still count?

**Question:** When a worker closes a step *after* the task was already resolved, should
the item's final cost result pick that time up, or stay frozen at the moment of closing?

**Story:** A chair is resolved on Friday afternoon; the result says 84 minutes allowed,
71 used, 13 to spare. But one worker forgot to close their step and does it Monday
morning, adding 40 real minutes of Friday's work. The step's own numbers update the way
they always have. The item's result does not — it still says 71 used, and it will say 71
used a year from now, while every live view of the same episode says 111. Nobody gets an
error; the two numbers simply disagree forever.

**Branches:**
- **Re-emit** — the result refreshes itself whenever late time lands; the number is
  always the truth about the episode, and a closed result can move after close.
- **Freeze at close** — the result is "as of closing time" by definition; late time is
  visible in the step data but never in the item economics, and correcting one needs a
  manual command.

**Recommendation:** re-emit — one guarded line at the existing analytics seam, and it is
the only branch under which the intention's own replay invariant (§8.4) is true.

**On silence:** the gate holds. The planner is not given a guess about which number is
authoritative.

**Trace:** intention §8A.5, §8.3, §8.4, §13 ("only if cheap" CLI re-emit), §14 test 18.

---

### Card 2 — Is a 25 % VAT term entered as 25 or as 20?

**Question:** Confirm that percentage terms are a percentage **of the sale price you
type in** — so Swedish VAT is entered as 20.00, not 25.00?

**Story:** You price a cabinet at 4,000 kr and add a "VAT 25 %" term, because 25 % is
what VAT is. The system subtracts 1,000 kr. But VAT is 25 % *on top of* the net price,
which means it is 800 kr of a 4,000 kr sticker — so the budget is 200 kr smaller than it
should be, on this cabinet and on every item you ever price. Nothing looks broken: the
allowance is just a few minutes short, every time.

**Branches:**
- **Confirm (enter 20.00)** — the field is documented as "% of the sale price"; you
  translate VAT once when you set the term up.
- **Add a VAT-style term type** — you type 25 and the system converts; one more term
  type to build and to keep correct.

**Recommendation:** confirm — the base is already named in the field, and one converting
term type invites a second reading of every other percentage.

**On silence:** the gate holds. Written provisionally as "% of the gross sale price"; no
planning proceeds on an unconfirmed money base.

**Trace:** intention §6A.4, §6.1, term-creation API docs, the living-docs page.

---

## Inventory table

Rank = silent-failure risk (charter rule 6): **S1** = wrong number, no error, forever;
**S2** = wrong behavior that eventually surfaces; **S3** = fails loudly when wrong.

| # | Mechanism | Rank | Contract status | Where written |
|---|---|---|---|---|
| 1 | Term amount per `calculation_type` (units, nullability) | S1 | **defined** (M-4) | §6A.4, A3 |
| 2 | Percentage base (gross vs net — VAT) | S1 | **provisional — card 2** (M-15) | §6A.4 |
| 3 | Cost-per-worker-minute denomination + underflow | S1→S3 | **defined** (M-3, M-5) | §6A.3 Q2, §6A.6, A1/A2 |
| 4 | Quantization sites and rounding mode | S1 | **defined** (M-13, M-14) | §6A.2, §6A.3 |
| 5 | Which rate the allowance/consumption divide by (raw vs persisted) | S1 | **defined** | §6A.3, §6A.11 |
| 6 | Double rounding minutes → cost | S1 | **defined** (M-14) | §6A.3 Q5 |
| 7 | Budget sum order-sensitivity | S1 | **defined** (proved, not asserted) | §6A.5 |
| 8 | Negative budget / negative allowance persistence | S2 | **defined** | A8, §6A.7 |
| 9 | `percent_consumed` when `allowed ≤ 0` | S1 | **defined** | §6A.8, §11A.4 |
| 10 | Currency resolution order + three-way equality | S1 | **defined** (M-6) | §6A.9, A4 |
| 11 | Duplicate `item_purchase_cost` terms | S1 | **defined** (M-7) | A5 |
| 12 | Term mutability on a live version | S1 | **defined** (M-16 totality) | A6 |
| 13 | `calculation_version` semantics | S1 | **defined** (M-17) | §6A.10 |
| 14 | Snapshot completeness / HC-7 closed field set | S1 | **defined — proved** (M-17) | §6A.11 |
| 15 | Chain statement order (4 chains) | S2 | **defined — was a defect** (M-1) | §7A.1 |
| 16 | Chain race arbitration + error identities | S1 | **defined** | §7A.2 |
| 17 | Version resolution predicate + date frame (UTC) | S1 | **defined** (theorem) | §7A.3 |
| 18 | Version-creation admission table | S3 | **defined — total** | §7A.4 |
| 19 | Basis/model selection failure modes | S3 | **defined — total** | §7A.5 |
| 20 | Deletion-guard race (§7.5) | S2 | **defined** (M-18) | §7A.6 |
| 21 | Commit procedure ordering + locking | S2 | **defined** | §7B.1 |
| 22 | Task-state admission (8 values) | S3 | **defined — total** | §7B.2 |
| 23 | PRIMARY-item binding predicate | S1 | **defined — 3-valued** | §7B.3 |
| 24 | Mirror-rule predicate (NULL semantics) | S1 | **defined** (M-19) | §7B.4 |
| 25 | Auto-path transaction isolation | S2 | **defined — was a defect** (M-2) | §7B.5 |
| 26 | Consumption read (COALESCE, filters) | S1 | **defined** (M-20) | §8A.1 |
| 27 | Two-cost-numbers labeling | S1 | **defined — 4 structural rules** | §8A.2 |
| 28 | Result upsert / idempotency key / payload | S2 | **defined** | §8A.3 |
| 29 | Replay identity vs `computed_at` | S1 | **defined** (M-9) | §8A.4 |
| 30 | Post-close time settlement | S1 | **provisional — card 1** (M-8) | §8A.5 |
| 31 | Migration journal scope + pre-flight predicates | S1 | **defined** (M-10) | §10A.1–10A.2 |
| 32 | API-bridge silent-drop vs hard-reject | S1 | **defined** (M-11) | §10A.3 |
| 33 | Money-exposure boundary + call-site census | S1 | **defined** (M-12) | §11A.1–11A.3 |
| 34 | "Not configured" vocabulary (never a 0) | S1 | **defined — one ordered enum** | §11A.4 |

Mechanisms inspected and found **already contract-grade** in the intention, needing no
delta: the concurrency-sweep dilution inheritance (§2.3/§9.2 — verified against
`domain/analytics/concurrency.py`), the projection/committed structural filter (§7.3),
INV-G1's one-active-group-per-section, and the compensation seam (§10.3).

---

## Unilateral resolutions — for owner ratification (no answer needed to proceed)

Each resolved a contradiction inside the intention. Deciding which side wins carries
consequences even where no product sentence changed.

1. **HC-6 beats the §4.4/§6.3 table sketches.** Money-as-major-units appeared twice —
   `CostModelTerm.value` for `fixed_amount`, and `cost_per_worker_minute`. HC-6 is a hard
   constraint, so both were redenominated to minor units (A2, A3). Consequence: three
   ÷100/×100 conversions leave the formulas, and the rate gains ~2 significant digits of
   precision (a 3,000 kr budget resolves to 576.00 allowed minutes instead of 576.01).
2. **SELLER is excluded from money along with WORKER** (§11A.1). Card 4's answer says
   "money ADMIN/MANAGER" but its story spoke only of workers. Consequence: a seller loses
   the step cost number they can see on task detail and task steps today.
3. **ROUND_HALF_EVEN is this domain's own decision, not an inherited precedent**
   (§6A.2). §6.6 cited `_cost_minor` as the repo's banker's-rounding precedent; it is
   not — it calls `.to_integral_value()` with no argument and inherits the ambient
   decimal context, and the repo's only *explicit* quantize rounds HALF_UP
   (`services/commands/upholstery/requests/__init__.py:17`). The rule stands on its own
   merits, passed explicitly at all five sites.
4. **`fixed_monthly_cost_minor` CHECK > 0** (A1). Consequence: a workspace cannot
   configure a zero-cost production pipeline. The alternative is an infinite allowance.
5. **One `item_purchase_cost` term per version** (A5) and **terms immutable with their
   version** (A6). Consequence: correcting a term means a new model version, as INV-M2
   already said but the soft-delete trio contradicted.
6. **API-bridge rejection is `present AND non-NULL`** (§10A.3), not "key present".
   Consequence: the manager app keeps working (it sends `item_value_minor: null` on
   every task creation), while a real price can no longer be silently swallowed.
7. **Result rows record the evaluation's `item_id`, never the live PRIMARY** (§7B.3).
   Consequence: after an item swap the economics stay attached to the item the decision
   was made for, and the mismatch is surfaced rather than repaired.

---

## Could not define without an owner decision

Exactly two — both carried as cards above, both with a provisional contract written into
the intention so the planner can see the shape of either branch:

- **Post-close time settlement (§8A.5).** Both branches are fully written; the phase
  plan builds whichever card 1 selects. Not definable by me: it is a statement about
  what "the final result" means, not about how to compute it.
- **The percentage base (§6A.4).** The arithmetic is unambiguous; what the owner *means*
  by "VAT 25 %" is not, and getting it wrong is invisible.

---

## Documentation drift and graph discrepancies (coordinator to route)

New this round (the §2.6 and research_context §8 lists still stand unrouted):

| # | Finding | Where | Severity |
|---|---|---|---|
| D-1 | `serialize_step`'s `total_cost_minor` reaches WORKER/SELLER through **five** call sites; both `intention §10.4` and `research_context §5` name two | intention (corrected in §11A.2), `research_context.md:338-345` (**not** corrected — evidence docs are records) | high — it is the census a must-ship item is built from |
| D-2 | intention §6.6's "the repo's banker's-rounding precedent in `_cost_minor`" is not a precedent | intention (corrected in §6A.2) | medium — it was load-bearing for a money rule |
| D-3 | Archgraph anchor drift: node `analytics-recompute-step-time-totals` carries evidence span `process_step_transition.py:138-211`; the symbol is at **161-234**. Same file, same symbol, semantics agree — anchors only | `.archgraph` (node is `ai_inferred`, `reviewState: pending`) | low — `archgraph_repair_anchors` territory, not a semantic discrepancy; filed per archgraph-discrepancies protocol, **not** fixed here (no code changed, and this session never adjudicates pending reviews) |
| D-4 | `transition_step_state` guards on step terminality but not task terminality, and the terminal commands leave open step records open. Not drift — undocumented live behavior that M-8/card 1 depends on | `transition_step_state.py:150`, `resolve_task.py`/`fail_task.py`/`cancel_task.py` | informational — worth a line in the step-transition living docs |

**One citation inherited, not re-verified:** §10A.3's rationale cites
`use-create-task.ts:84-85` ("the manager app sends `item_value_minor: null` on every
task creation") from `research_context.md:353`; the frontend repo is outside this
session's working directories. The contract itself does not depend on it — rejecting
only *present-and-non-NULL* keys is correct whether or not the app sends nulls, and is
strictly the more permissive of the two candidate predicates. Everything else asserted
about the backend in the delta was read in the tree this session.

Archgraph state re-verified this session: initialized, valid, **116 nodes / 157 edges**,
revision `b0702c3c…`, 0 stale, **244 pending reviews**, permissionMode `review` —
unchanged from research_context §7. Oriented on `table-task-step` and
`analytics-recompute-step-time-totals`; no review was adjudicated and **no graph delta
was recorded** (this session changed no code).

---

## Write perimeter (full, declared)

| Path | Change |
|---|---|
| `docs/architecture/under_construction/implementation/item_cost_calculation/planning/intention.md` | header block (status/round); new §4A, §6A, §7A, §7B, §8A, §10A, §11A; supersession notes inserted into §4.3, §4.4, §4.5, §6.1, §6.3, §6.4, §6.5, §6.6, §7.2, §10.4, §11, §13, §15; §14 items 15–21 appended; §16 Round 3 (M-1…M-20); §17 rewritten. 1107 → 1957 lines. **No section renumbered.** |
| `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/mechanism_inventory/2026-08-11_mechanism-inventory_r1_handoff.md` | this file (new) |

**Nothing else.** No code, no migrations, no other document — `owner_decisions.md`,
`research_context.md` and `raw_intention.md` are untouched by design (drift found in
them is routed above, never patched in place). No tool-recorded state changed: no
archgraph write of any kind (`archgraph_status`, `archgraph_get_node` only — both
read-only), no git operation, no test run.

---

## Exit gate

**Held, not passed.** Every silent-failure mechanism in the inventory now has a
contract-grade definition in `intention.md`. Two of those definitions are marked
**PROVISIONAL**:

- mechanism 30 (post-close time settlement) — §8A.5, blocked on **card 1**;
- mechanism 2 (percentage base) — §6A.4, blocked on **card 2**.

Until both are answered the gate stays open and **implementation-planner does not
start**. Nothing else blocks it: the seven ratification items need visibility, not
answers, and the planner can build every other phase's criteria from the contracts as
written.
