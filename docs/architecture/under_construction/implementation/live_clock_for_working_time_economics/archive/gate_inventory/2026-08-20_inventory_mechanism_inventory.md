---
plan: (pre-plan, project-level — no phase plans exist yet)
role: reviewer (mechanism-inventory gate)
round: inventory
date: 2026-08-20
project: live_clock_for_working_time_economics
---

# Session prompt — mechanism-inventory gate, `live_clock_for_working_time_economics`

## 1. Role and workspace

You are running the **mechanism-inventory** gate. You are adversarial to the intention's
author — treat every mechanism description as hiding an ambiguity an implementer will
resolve silently in code, and treat "obvious" as the strongest warning sign in the
document. This feature is time arithmetic with a concurrency-averaging rule, a windowing
rule and a parity bound: **every mechanism in it produces a number that looks plausible
when it is wrong.** Nothing here fails loudly.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (commands run from here; `PYTHONPATH=. pytest -m 'not e2e'`)
Project folder:
`backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

**Read these two files first and follow them as this session's doctrine** (plain
markdown, read by absolute path):

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/mechanism-inventory.md`

If you are a Claude session, invoking the `mechanism-inventory` skill loads (2); read (1)
regardless.

## 2. Gate check — stop and report if any of these is false

- `planning/intention.md` reads `status: RESOLVED (round 3, …)`.
- `planning/owner_decisions.md` records D1–D7 and the intention's §10.2 reads
  **Ledger empty**.
- `plans/` contains no plan files. **No phase plans exist yet, by design** — this gate
  runs *before* the implementation-planner. If you find any, stop: someone ran the
  planner early and the gate's purpose is defeated.
- `master_plan.md` §3 shows this gate as the only tracker row.

## 3. Read order

1. `master_plan.md` — §4 naming constraints, §5 standing rules, §6 environment and
   verified code facts, §7 gates (the rule-6 trigger table the coordinator already
   classified).
2. `planning/intention.md` — **in full**. It is the artifact you are auditing.
3. `planning/owner_decisions.md` — D1–D7 with their rejected branches. A decision
   recorded there is settled; you do not reopen it. You may find that a decision's
   *consequence* was folded into the intention incorrectly — that is a finding, and a
   different thing.
4. `planning/coordinator_review_of_intention_20260819.md` — **provenance only.** All six
   findings are folded into round 3; they are not an open list and not your scope. Two
   verifications in it may be **consumed rather than re-derived** (they were checked at
   source twice, by the reviewer and again at the fold): the §4.3 keystone
   (`budget_division.py:_section_step_allowances` reads worked seconds only for
   completed steps, so live figures cannot move allowances) and the §5.3 status
   immunity (OK↔INFEASIBLE tests the committed allowance, never worked seconds).
   Everything else you verify yourself, at source.
5. The source the intention grounds itself on — **read, not assumed**. Every citation in
   the intention is `path:symbol` and every one is checkable. The files, all verified to
   exist at `a0aaacc`:
   - `app/beyo_manager/domain/analytics/concurrency.py` (the sweep — the crediting rule)
   - `app/beyo_manager/services/queries/analytics/averaged_time.py` (the IO wrapper,
     `RecordContribution`)
   - `app/beyo_manager/models/tables/tasks/step_state_record.py` (the ledger)
   - `app/beyo_manager/domain/task_steps/constants.py` (`TIME_BEARING_STATES` — and the
     full state vocabulary it is a subset of)
   - `app/beyo_manager/services/tasks/analytics/process_step_transition.py` (settlement:
     `_recompute_step_time_totals`)
   - `app/beyo_manager/domain/item_economics/budget_division.py` (the allocator)
   - `app/beyo_manager/domain/item_economics/calculator.py` (the pure money path)
   - `app/beyo_manager/domain/item_economics/division_serializers.py` (E-P shapes,
     the `final` block)
   - `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`,
     `get_task_budget_status_worker.py`, `get_task_production_time.py`,
     `get_task_budget_allocations.py` (the three surfaces, both faces)
   - `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py`
     (the shipped cross-pipeline caller — §2.6)
   - `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py`
     and `list_workers_totals.py` (the live-`now` precedents §2.3)
   - `app/beyo_manager/services/commands/task_steps/mark_step_time_inaccurate.py` (the
     D7 disowning path)
   - `app/beyo_manager/services/tasks/users/auto_clock_out_open_shifts.py` and
     `app/beyo_manager/services/commands/users/_clock_worker_shift.py` (the overnight
     close — the §3.2 window note's operational premise)
6. `.archgraph/` via the archgraph MCP if available — orient with `archgraph_status` and
   a search around the item-economics projections and the analytics sweep boundary.
   **You never promote, reject or edit review items**; the human adjudicates. Record
   what you would have recorded, in your handoff.

## 4. What this gate must produce

The skill's procedure, applied to this intention. Concretely: **every mechanism below
leaves this gate with a contract-grade definition written into the intention itself**,
or with an owner decision card explaining why it cannot be defined without one.

Contract-grade, per the skill: inputs and every type they may arrive as (including what
the ORM actually returns, not what a test would construct); per-type canonicalization;
per-field semantics wherever order, precision, rounding mode or unit matters; the
invariant a test must prove **on the production code path** (charter rule 3); and, for
every numeric bound, the derivation — a bound asserted without its arithmetic is an
adjective wearing a number.

### The mechanisms in scope — all of them, in this order

| # | Mechanism | Where |
|---|---|---|
| M-1 | `open_working_share`: the full selection predicate set (open record, state, the marked-wrong disjunction record-OR-step, deletion), the `COALESCE` attribution, and the filter applied to `RecordContribution` rows — each predicate checked against what the sweep and the wrapper actually do | §3.1 |
| M-2 | the window rule: the `min(entered_at)` anchor over the user's open working records, the 1-day buffer, and the buffer's **sufficiency** for the live case (settlement's buffer serves a different query shape — is the argument transferable or merely borrowed?) | §3.1, §3.2 window note |
| M-3 | the no-snap parity bound: derive its arithmetic yourself — who rounds what, where, summed per what unit — and state whether "≤ 1 s per credited user" is exactly what the two rounding loci produce, and whether rounding is provably the **only** drift source | §3.3, §2.1 |
| M-4 | the cost model and the stated ceiling: the per-user sweep count, the "one batched open-record probe", the ~2-day window bound, and what T8 can actually observe | §3.4, §9 T8 |
| M-5 | one-basis propagation under **composition**: the per-surface field table row by row; how "one computation per request" and HC-3's "`now` once at the service boundary" behave when one query service calls another (E-P composes E-B's service; the shipped price-scenario endpoint calls it too) | §4.1, HC-3, HC-5, §2.6 |
| M-6 | the pre-registered planner decision on the E-B SQL aggregate: verify the two named resolutions are in fact arithmetically identical, per field they feed | §4.1 |
| M-7 | the identity claims that bound the change: completed step ⇒ M1 figure ≡ settled column (§4.3); idle task ⇒ byte-identity (§4.2, §5.2 c4); what stays settled, item by item | §4.2, §4.3, §2.5, §5.3 |
| M-8 | the disowning-event semantics: the exact event family, the immediate-zero contract, what `mark_step_time_inaccurate` actually selects and sets, and the §5.4 client instruction (snap down, never clamp) as a contract another codebase executes | §6, D7, §5.4 |
| M-9 | the tests as mechanisms: T1–T8, each **writable as stated** — fixtures constructible, assertions decidable, sequencing honest; every named mutation with **both sides computed** and its **site named** (file, definition-vs-call-site) | §9 |

**Do not scope yourself by the intention's own self-assessment.** §11's closing line
nominates three claims as "most worth attacking." That line was written by the author of
the mechanisms, and in the neighbouring project the same kind of line pointed away from
the weakness three times running — every defect worth a round was in a section nobody
had flagged, and the nominated claims all survived. It is a hypothesis, never a scope.
Sweep all nine rows at equal depth, **and sweep the sections that read as prose —
§2.5, §2.6, §5.3, §5.4, §6, §7, §8 — at the same depth as §3**. Where the document
sounds most confident, be most suspicious.

### Method rules that apply to this sweep specifically

1. **A worked example is a test, not an illustration.** §3.2's four failure cases each
   carry arithmetic (60 vs 30; 20 + 10/2 vs 15; the cross-task divisor; 20/2 + 10 vs
   30). Do every one by hand against the sweep's actual segment rules as coded in
   `concurrency.py`, and say whether each example follows the rule it claims to
   illustrate. Same for any other number the document derives.
2. **Charter rule 5 — no adjectives for mechanisms.** Hunt them explicitly. Any word
   doing specification work without a definition ("bounded", "small", "typically",
   "hours, not history") is a gate failure, not a wording preference.
3. **Charter rule 2 — case analyses must be total.** §3.1's zero-cases are a ranked
   rule over the open record's possible states: check the enumeration is total over the
   **real** state vocabulary (read the enum, not `TIME_BEARING_STATES` alone) and that
   every state's treatment is decidable. The same totality check applies to §4.1's
   field table (every worked-derived field on every surface appears in exactly one row —
   walk the serializers key by key) and to §2.5's untouched list.
4. **Every named mutation: compute both sides before accepting it.** State the value
   under the contract and the value under the mutation and confirm they differ — for the
   specific fixture named, not in general. A mutation whose two sides were never
   computed is a claim, not a guard. Name where each applies: file, definition site or
   call site. (Three named mutations were proved inert at the last project's projection;
   the check is cheap and mechanical.)
5. **An absence claim is only as good as its scope AND its term set.** The intention
   makes several ("no clock in this family", "none of them reads through these
   endpoints", "a completed step has no open working record"). For each: state what
   search or reading would verify it, run it, and record the scope and terms beside the
   claim. This query family already defeated one grep via the `today_utc()` wrapper.
6. **Two-codebase contracts.** §5.4 writes rules the frontend executes (snap down, never
   clamp; smoothing from time-of-receipt). A rule that is precise in this repo and
   ambiguous in a client is not contracted — per event, say exactly what the client must
   do. That text lives in the intention now and ships in the closeout handoff; it
   produces no code here.
7. **Time-fixture honesty.** Any test the intention names that commits
   `step_state_records` rows owns its teardown (charter 11½), and any test cited as
   proof of a `WHERE` clause must issue real SQL (master plan §5). Where a T-row's
   fixture cannot satisfy that as stated, say so now, not at implementation.

## 5. Constraints

- **You write documents, never code.** No file under `app/` changes. No test runs are
  required, though you may read anything and run read-only queries.
- **The delta goes into `planning/intention.md`** — that is its home per the artifact
  map; a contract patched into a downstream document is how document sets diverge.
- **Never renumber a section.** Other artifacts cite §2.6, §3.1–§3.4, §4.1–§4.3,
  §5.2–§5.4, §6, §9, §10, §11. Insert **lettered** sections (`§3.1A`, `§4A`) so every
  existing citation stays true. Amend in place only when the amendment moves no number.
- **Citations are `path:symbol`, never bare line numbers** — the intention's own round
  3a records why; do not reintroduce the defect class it just removed.
- **Add a changelog entry** to §11 recording round 4: what you added, what you changed,
  and why.
- **Owner decisions.** Anything you cannot define without a product call becomes a
  **decision card** in the charter's format — question, story in the owner's world,
  branches with lived consequences, one recommendation with its reason, on-silence
  behaviour, trace line. All cards live together in ONE section headed
  `⚠ OWNER DECISIONS REQUIRED (n)` immediately after your handoff's opening summary. If
  there are none, say so in one line. Cards are the only owner-facing prose in the
  handoff; everything else stays technical.
- **Unilateral resolutions get listed separately for ratification.** Where you resolve
  an internal contradiction by picking a side, list every one, with what you chose and
  what the other side would have produced in shipped behaviour.
- **Do not reopen D1–D7.** They are settled, with their rejected branches recorded.

## 6. Closing protocol

1. Write the intention delta (lettered sections + §11 round-4 changelog entry).
2. Deposit your report at
   `handoffs/reviewer/2026-08-20_inventory_mechanism_inventory_handoff.md`, with charter
   frontmatter: `plan`, `role`, `round`, `date`, `state`/`verdict`, `actor`.
3. The handoff **declares your full write perimeter** — every document touched, by path,
   generated from `git status` / `git diff --name-only`, never retyped from memory. The
   coordinator diffs your declaration against the tree; any undeclared write is a
   finding, whoever made it.
4. Do **not** update the master plan tracker row — the coordinator owns it.

## 7. Report back — what the handoff must contain

- **Opening summary**, then the owner-cards section (or its one-line "none").
- **The inventory table**: one row per mechanism M-1…M-9 — *mechanism / silent-failure
  risk / contract status before / contract status after / where the contract now
  lives*. Cover all nine even where the answer is "already contract-grade, verified
  against source at `path:symbol`".
- **The worked-example audit**: one row per derived number in the intention, with the
  arithmetic you did and whether it follows its own rule.
- **The T1–T8 writability walk**: per test, constructible-as-stated yes/no, plus the
  both-sides table for every named mutation (value under contract, value under
  mutation, site).
- **Contradictions found**, each with both sides quoted by section, which side you
  chose, and what the other side would have produced in shipped behaviour.
- **What you could not settle from the source**, with what evidence would settle it.
- **Gate verdict**: `PASS` (every rule-6 mechanism now has a contract-grade definition
  in the intention) or `OWNER_DECISIONS_PENDING` (cards outstanding — the gate holds)
  or `FAIL` with what is missing. The implementation-planner does not start on anything
  but `PASS`.
