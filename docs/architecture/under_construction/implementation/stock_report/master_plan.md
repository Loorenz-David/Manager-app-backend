# Master plan — stock_report

```
state: PLANNED — plan set written 2026-09-19 (planner, planning-0) against the round-7 intention,
       then folded (planner, planning-1, same day) to the intention as **RATIFIED at round 9,
       committed c231dfb**: round 8 (§14E, the Scanner delete-row webhook → new phase 13A) and
       round 9 (§14F, the terminal state `resolved_early` → phases 1, 3, 4, 5, 8, 9, 10, 11, 13, 14).
       Plan set committed 67dd815 with the owner's rulings. **Execution model changed by the owner
       (2026-09-19): phases stay the units of specification and verification; four batches (A–D)
       are the units of implementation and review — §3A, §4A.** **Batch A: review 1
       CHANGES_REQUESTED (125/30/15 of 170) → fix 1 (`983d774`) → re-review CHANGES_REQUESTED at
       **168/2/0** → fix 2 → re-review 2 **APPROVED at 170/0/0, zero findings** (`f2157bd`).
       Phases 1–3 VERIFIED. **Batch B complete 2026-09-21: B1 (4, 5) APPROVED 84/84 and B2 (6, 7)
       APPROVED 88/88 — phases 4–7 VERIFIED. Suite 3103 → 3445 passing, the 21-ID baseline
       unchanged throughout.** Batches C and D not started. **Gate closed 2026-09-20 with the owner's authorization: approval
       commit, graph delta (10 nodes / 12 edges, revision f260fc41…), archive to
       `archive/batch_A/`.** Batches B–D not started; lessons L-10…L-18 owed as a plan fold
       before batch B is implemented.**
date: 2026-09-20
tree: 0d5d31d (clean)
phases: 15 planned (1–13, 13A, 14) — see §4 and §7. The owner's non-binding suggestion was 6; the
        departure and its reasons are in §7.1.
intention: planning/intention.md — RATIFIED round 9 at c231dfb (what this plan set cites; later
           amendments win in the order §14C states, §14F last and strongest);
           mechanism-inventory PASS at round 7 (handoffs/reviewer/2026-09-19_inventory_mechanism_inventory_recheck_handoff.md);
           the owner waived the inventory re-check of §14E — its six questions are plan 13A §7
```

Paths are relative to `backend/` unless they start with `app/`. `app/beyo_manager/` is abbreviated
`bm/`. `SR/` is this folder, `docs/architecture/under_construction/implementation/stock_report/`.

## 1. Goal

Scanner tells Manager how much stock is missing (demand), which rules no longer exist (delete, round
8) and which repaired items it has processed; Manager turns demand into rows on a board, removes a
row with everything on it when Scanner deletes the rule, lets users assign existing task+item pairs
to a row, keeps three unit counters on each row as a cached projection of the assignments' states,
follows every task-state change onto the assignment, closes an assignment early when Scanner
processes the item before the task is ready (`resolved_early`, round 9), keeps the goal's history,
and self-heals a wrong counter before it can block anyone. Semantics live **only** in
`planning/intention.md` (read its Status section, then §14B–§14F: later amendments win in the
order §14C states, **§14F last and strongest**). The twenty mechanism contracts MC-1…MC-20 are the
lettered sections registered in intention §13A, as amended by §14E–§14F; every criterion row in
`plans/` traces to one of them, to an amendment row (`§14E En`, `§14F Fn`) or to a ledger entry
M1–M9. This document never restates semantics.

## 2. Sources of truth

| Content | Artifact |
|---|---|
| Product semantics, invariants, the measurement ledger M1–M9, mechanism contracts MC-1…MC-20, supersession ledger | `planning/intention.md` (RATIFIED; only the owner writes its status) |
| Scanner-side facts (the sender, its worker, its matcher, its tables) | `planning/scanner_source_evidence.md` (E1–E10 + sender notes) |
| The published wire contract Scanner builds against (read-only; v2 is complete on its own and supersedes the handed-over v1; a further change is a v3 file) | `docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v2_20260919.md` |
| Inventory findings, U1–U21, the matcher hand-walk H1–H16, the write-site audit | `handoffs/reviewer/2026-09-18_inventory_mechanism_inventory_handoff.md` §3–§6 |
| Re-check findings, X1–X3, the carried instrument list | `handoffs/reviewer/2026-09-19_inventory_mechanism_inventory_recheck_handoff.md` |
| Shared skeleton: naming registry, contract resolution, environment, standing rules, tracker | this file |
| Phase-local goal, files, tasks, criteria, Review log | `plans/plan_<n>.md` |
| Session framing | `prompts/<role>/`, generated just-in-time, never reused |
| Repo contracts (how to write code) | `architecture/*.md`, resolved in §5 |

**Fold-back rule.** A semantic change amends the intention (lettered section, never renumbered;
a material change re-opens the intention gate). A skeleton change (a name, a path, an
environment fact, a standing rule) amends this file. A criterion change amends the phase plan
**and** is checked against this file's registry. Nothing is patched into a downstream artifact
to make it agree with an upstream one.

## 3. Roles and session workflow

> **Superseded where it conflicts by §3A** (owner, 2026-09-19): no per-phase projection agent, no
> per-phase Codex or review session, no per-phase approval gate, no agent launched by the
> coordinator. The text below is kept as the planning-time record; §3A governs execution.

Orchestrated mode (owner-set, 2026-09-19): the **coordinator** (`pipeline-coordinator`) compiles
prompts and runs the tracker; the **implementer is Codex** in a fresh `codex exec` session per
round, working only from the phase file's Read-first list and the compiled prompt (complex phases
run on the larger Codex model — the `complex:` line in each plan's Notes and in §4 is the switch);
**projection** (`plan-projection`, reviewer role, round 0) and **review** (`plan-reviewer`) run as
pinned Opus agents. The owner is not in the loop except at the stops the coordinator doctrine
names (after this plan set, on every APPROVED phase, on any second fix round, on any card).

State machine per phase (charter): `NOT_STARTED → PROJECTED → PROMPT_READY → IMPLEMENTING →
IMPLEMENTED → REVIEWING → CHANGES_REQUESTED (→ IMPLEMENTING) → APPROVED`. A phase starts
implementation only when every phase it depends on (§7.2) is APPROVED. Every `IMPLEMENTED` is a
`CHECKPOINT (not approved):` commit; the approval gate commits again; nothing is squashed or
pushed by a role session. Re-reviews are delta-scoped with a verified perimeter (charter "Review
protocol"). Test evidence follows the charter's L1–L4 scopes; §10 names the exact commands.

**Projection is mandatory** for every phase marked `projection: mandatory` in §7.2 (silent-failure
mechanisms, and every phase whose fixtures are externally derived under charter rule 17); it is
waivable with a recorded one-line reason for the others. The self-retiring rule does not apply to
the rule-17 phases (2, 6, 7, 9, 13A).

## 3A. Batch execution model (owner, 2026-09-19) — governs execution; wins over §3, §7.2's projection column and §7.3

> **Amended from batch C on by §3B** (owner, 2026-09-21): a tester session sits between Codex and
> the reviewer, and takes over the named mutations and the coverage map. Where they differ, §3B wins.

**Principle.** Phases remain the units of specification and verification; **batches are the units
of implementation and review.** The fifteen phase plans are unchanged and authoritative: every
criterion row, trace cell, named mutation, dependency, contract and test obligation stands. Batching
changes execution granularity only.

**Batches** (validated against §7.2: every dependency points to an earlier batch or to an earlier
phase of the same batch; no adjustment was needed):

| Batch | Phases, in implementation order | Depends on (batch APPROVED) | Rows / criteria | Codex model |
|---|---|---|---|---|
| A — Foundation | 1 → 2 → 3 | — | 170 / 22 | terra, medium (phase 3 is complex) |
| B — Core engine and demand | 4 → 5 → 6 → 7 | A | 172 / 25 | terra, medium |
| C — Assignment lifecycle and sync | 8 → 9 → 10 → 11 | A, B | 169 / 30 | terra, medium |
| D — Completion surfaces | 12 → 13 → 13A → 14 | A, B, C | 104 / 21 | terra, medium |

Inside a batch the order above satisfies every intra-batch edge (2←1, 3←1; 5←4, 7←6; 9←8, 10←9,
11←8; 13←12, 13A←13, 14←13A). 6 may run before 4–5, and 11 before 9–10, but the listed order is the
default because plans 11 and 13 build `resolved_early` fixtures through `PR` once 9 exists (§7.2 note).

**Roles.**
- **Orchestrator** (the Claude coordinator session): maintains this master plan and the trackers
  (§4, §4A); validates dependencies; performs the **batch projection** itself; compiles one Codex
  prompt per batch and one reviewer prompt per batch; routes review findings into one focused fix
  prompt per round; decides when the next batch may start; runs the approval gate commit and the
  final closeout. It **launches no agent of any kind** (no Codex, reviewer, projectionist or planner)
  and neither implements nor reviews.
- **Codex** (implementer): one fresh session per batch implementation, one per fix round. **The
  owner launches it by hand** with the orchestrator's prompt.
- **Independent reviewer** (a Claude session with `plan-reviewer`, never Sonnet): one session per
  batch review or re-review, **launched by the owner** with the orchestrator's prompt. It shares no
  context with the implementer or the orchestrator.
- **Owner**: carries artifacts between sessions — orchestrator → owner → Codex → owner →
  orchestrator → owner → reviewer → owner → orchestrator — and decides exceptional questions.

**Suspended for batch C.** The three "launched by the owner" clauses above are overridden for the
duration of batch C by §3B's owner exception of 2026-09-21: the orchestrator launches all four
roles as subagents, and the implementer is a Sonnet subagent rather than Codex. Read §3B's *Who
launches* bullet, not this list, until batch C is APPROVED.

**Batch projection (replaces per-phase round-0 projection).** Before compiling a batch prompt the
orchestrator reads the batch's phase plans and checks only: cross-phase contradictions, dependency
problems, integration hazards, externally derived assumptions still unverified (rule 17), locking
and concurrency hazards, silent-failure risks, anything that makes handing the whole batch to Codex
unsafe. It regenerates no criteria and writes no projection artifact; its result is a short list
of notes placed in the batch prompt and a one-line entry in §4A. §7.2's per-phase `projection:
mandatory / not waivable` flags now mean **"the batch projection must look at this phase's rule-17
facts and name how the batch prompt settles them"**. The six §14E questions (plan 13A §7) are
checked in batch D's projection.

**Implementation inside a batch.** Codex implements the phases in order and does not return control
at a phase boundary. A phase boundary triggers no projection, no review and no owner gate. At each
phase's end Codex runs that phase's L1 tests and its named mutations, and may make a
`CHECKPOINT (not approved): phase <n>` commit for recoverability — **a checkpoint is not a gate.**
Codex stops early only for a genuine blocker: a contradiction between plans, an impossible
criterion, a missing prerequisite, an unplanned schema need, a contract conflict, or a semantic
question only the owner can answer (a decision card). Ordinary implementation problems are solved
in the session.

**Dependency reading inside a batch.** A plan header's `depends_on: N (APPROVED)` means: if N is in
an earlier batch, that batch is APPROVED; if N is in the same batch, N is IMPLEMENTED earlier in the
same session with its L1 tests green and its named mutations run. The executor's gate check reads
§4A (predecessor batches APPROVED, this batch `IMPLEMENTATION_PROMPT_READY` or `IMPLEMENTING`), not
per-phase APPROVED rows.

**Handoffs.** Codex returns **one batch handoff** with a section per phase (criteria rows
implemented, test ids, test results, the named-mutation ledger with `executed == declared`, judgment
calls, deviations) and a batch section (cross-phase integration evidence, contract compliance,
locking evidence, the combined L2 and L4 results against the §10 baseline, the commits, blockers).
A generic "batch implemented successfully" is not a handoff. Each phase plan's Review log still gets
its own entry.

**Review.** One reviewer session per batch evaluates **every phase against its own criteria rows**
(a per-row verdict table, `P<n> C<k>(<x>) PASS/FAIL/NOT_VERIFIED`) and the batch as a whole:
contract compliance, cross-phase integration, lock/transaction invariants, workspace isolation,
event semantics, later phases breaking earlier assumptions, and perimeter escape. Findings route
into **one** focused Codex fix prompt per round, grouped by cause; the re-review is delta-scoped.
**Owner stop kept:** the first fix round runs on the orchestrator's prompt; a re-review that still
returns CHANGES_REQUESTED stops for the owner's ruling per finding before any second fix round.
Findings that only ask for an implementation-coupled test are backlog notes (charter rule 2).

**Re-review scope (owner, 2026-09-20).** The first review of a batch is full. A re-review after a
fix round is **light by default**: it reads only the fix diff and re-verdicts (i) every row a
finding named, (ii) every row whose test or source the fix touched, and (iii) the orchestrator's
L4 against the 21-ID baseline in both directions — that run is 66s and is the only cheap way to
catch a fix that breaks a row which already passed. It does **not** re-verdict the rows the first
review passed and the fix did not touch, and it does not re-derive evidence the first review
already supplied (Scanner conformance, the mutation audit). The reviewer widens the scope on its
own judgment in exactly one case: the fix touched a **shared foundation** — the test kit,
`_locks.py`, consistency recomputation, the migration, an enum or a state list — and then only to
the rows that depend on it, naming them and why. A light re-review that returns CHANGES_REQUESTED
still triggers the owner stop above.

**Evidence (unchanged rigor, less repetition).** L1 per test file as it lands; each phase's named
mutations at the scope its plan requires; concurrency rows as written. Expensive runs are not
repeated at every internal phase boundary when the next phase extends the same code, unless a
criterion requires that evidence at that point. At the batch boundary Codex runs the batch's L2
perimeter and **one L4** full run, diffing failure IDs against §10's 21-ID baseline in both
directions; the reviewer consumes that stamp when its tree matches. The final L4 and baseline
comparison at closeout stay.

**States.** Batch (§4A): `BATCH_NOT_STARTED → PROJECTED → IMPLEMENTATION_PROMPT_READY → IMPLEMENTING
→ IMPLEMENTED → REVIEW_PROMPT_READY → REVIEWING → (CHANGES_REQUESTED → FIX_PROMPT_READY →
IMPLEMENTING → IMPLEMENTED → REVIEW_PROMPT_READY → REVIEWING)* → APPROVED`. Phase (§4): `PENDING →
IMPLEMENTED` (Codex's handoff shows the phase's rows discharged) `→ VERIFIED` (the batch review
passed every row of the phase). A phase is never APPROVED on its own; it becomes VERIFIED when its
batch is APPROVED. Only the orchestrator writes tracker rows, from the handoffs it consumes.

**Git and closeout per batch.** Codex commits only its perimeter (`CHECKPOINT (not approved): …`),
never pushes. At batch APPROVED the orchestrator, with the owner's authorization, makes the approval
gate commit and moves the batch's spent prompts and consumed handoffs to `archive/batch_<X>/`; the
owner may compact then. Prompts live in `prompts/implementer/` and `prompts/reviewer/`, handoffs in
`handoffs/implementer/` and `handoffs/reviewer/`, named `…batch_<X>_<role>_<n>.md`.

## 3B. Tester role (owner, 2026-09-21) — amends §3A from batch C on

**Declared: this project runs the charter's tester role** (charter "The tester role"; procedure in
`/Users/davidloorenz/agent-skills/verification-engineer.md`, skill `verification-engineer`). This
section records only what is specific to this project; the role's procedure, ledger format, stop
conditions and anti-over-testing rules live in the skill and are not restated here. Every
criterion row, outcome, fixture cell, trace cell, dependency and contract in the fifteen plans
stands unchanged. Batches A, B1 and B2 are closed under the old split and are not re-opened.

**Why.** Reviews of A–B2: production code right in round 1 almost everywhere; 26 of batch A's 30
first-review FAILs, all four of B1's findings and all of B2's were tests weaker than their row,
mutations that could not fail, or ledgers that did not add up. Each cost a full review → fix →
re-review cycle. **Implement once. Prove only what must be proved. Review independently.**

**Batch shape.** Per batch: `projection + lesson fold → implementer → tester → reviewer →
APPROVED, or a fix routed by cause → light re-review`. Batch C is split by the owner into
**C1 = 8 → 11** and **C2 = 9 → 10**, each with its own implement → test → review → approval cycle
(§7.2 holds: 11←8 inside C1; 9←7, 8 and 10←9 put C2 after C1 APPROVED; plan 11 already names its
`resolved_early` fixture path when 9 does not exist yet — its §7). Batch D's split is decided at
its projection.

**What changes against §3A, and nothing else:**
- *Implementation inside a batch:* the implementer no longer runs each phase's named mutations nor
  writes the row-level coverage map (executor "When the project runs a tester"). It runs each
  phase's L1 tests as it goes, the batch L2 and **one L4** against §10's baseline, and hands over
  the tester contract. §3A's dependency reading becomes: a same-batch predecessor is IMPLEMENTED
  earlier in the session **with its L1 tests green** (its mutations are the tester's).
- *Handoffs:* Codex's batch handoff drops the named-mutation ledger and gains the tester contract.
  The **tester's handoff** (`handoffs/tester/`, prompts in `prompts/tester/`) carries the
  three-table verification ledger per phase with `executed == declared` and its own L4 on the tree
  it hands over. The reviewer consumes the tester's stamp.
- *Mutation cells (amended by the owner, 2026-09-21 — supersedes this bullet's original text,
  which left every `—` cell to the tester):* a cell that names a mutation is binding (closed set).
  The **projection** attempts a mutation for every `—` cell in its scope and sorts it into three
  classes, because the 94 cells are not one kind of thing:
  1. **Plan-determined** — the mutation is derivable from the row's own fixture/outcome/trace text
     without knowing how the code will be written (drop a named filter, unsort a named list,
     delete a named guard or call, flip a named literal or map cell). **The orchestrator folds
     these**, restoring the `executed == declared` gate on them.
  2. **Site-undetermined** — the outcome is real but the line that makes it true is an
     implementation choice. The cell stays `—` **with a one-line note saying the blank is
     deliberate**, so the tester knows to site it on real code rather than read it as an
     oversight; the tester sites it, declares it in ledger table 1, and proposes the backfill.
  3. **Reveals a defect** — the attempt exposes a fixture too uniform to discriminate, a sort/set
     row with < 3 elements, a tenancy row with no cross-workspace reference, a paraphrased
     outcome, or a contradiction with another row. Fixture cells fold to the orchestrator;
     anything touching an outcome or a criterion row is an **owner card**.

  *Why the split.* Measured over batch C's 67 cells (plans 8, 9, 10, 11) before any code existed:
  **57 plan-determined, 5 site-undetermined, 5 defective.** Leaving all 67 to the tester would
  hand it 57 derivations it gains nothing by making and would drop the closed-set gate on all 67
  to keep 5 honest; pre-naming all 67 would repeat batch B's inert and declined mutations, which
  are concentrated in exactly the 5. The class-3 finding is the load-bearing one: trying to name a
  mutation is the cheapest known test of a row, and when it fails the repair is usually a
  **fixture** cell — which neither implementer nor tester may edit, so a tester meeting it at
  arming time is blocked mid-session.

  The tester prompt states the split explicitly: *declared = the N named cells in your scope; the
  M deliberate blanks are yours to site and propose.* The tester still edits no plan cell. §9
  rules 8 and 9 bind the tester as written.
- *Review:* per §3A, against the tester's ledger; every finding carries `route: production |
  verification | plan`. *Fix:* one prompt **per routed role**, not one Codex prompt — production
  first when both exist, and the tester then re-arms only the rows whose test or mutation site the
  fix touched. §3A's owner stop on a second CHANGES_REQUESTED and its light re-review scope are
  unchanged.
- *Who runs it:* a Claude session with `verification-engineer`, **never Sonnet**. It shares no
  context with the implementer.
- *Who launches (owner exception, 2026-09-21 — batch C only):* **the orchestrator launches all
  four roles directly** — projectionist, implementer, tester, reviewer — as subagents, suspending
  §3A's manual bridge for the duration of batch C. Granted by the owner to measure the tester
  addition end-to-end against batch B's overnight run (which was reliable but long); the
  hypothesis under test is *shorter and still reliable*. A subagent starts with a fresh context,
  so the no-shared-context requirement above is satisfied by construction. Models for batch C:
  projectionist Opus · implementer Sonnet (measured: production was right in round 1 across A, B1
  and B2 under Sonnet, and the proof burden that exposed it has moved to the tester) · tester
  Opus · reviewer Opus. **The exception expires at batch C APPROVED**; batch D re-reads this
  bullet. Everything else in §3A's bridge — the owner stop on a second CHANGES_REQUESTED, owner
  cards, and the reservation of criterion-row authorship to the owner — is untouched.
- *States (§4A):* `… IMPLEMENTED → TEST_PROMPT_READY → TESTING → TESTED → REVIEW_PROMPT_READY →
  REVIEWING → (CHANGES_REQUESTED → FIX_PROMPT_READY[role] → … → TESTED → …)* → APPROVED`. A
  tester handoff with a `BLOCKED-PRODUCTION` row returns to the implementer before any review is
  compiled. Phase rows (§4) are unchanged: `PENDING → IMPLEMENTED → VERIFIED`.

**Phase 10 (C2).** Its concurrency evidence is exactly plan 10's three C5 rows — the three
serialization orders MC-11/§14F F6 distinguish — each forced by lock acquisition (§9 rule 9) and
each armed by its own cell's mutation (the post-lock re-read / the pre-lock decision). The tester
adds no interleaving, no repetition loop and no thread-count variant; its work on C5 is to show
that each test **forces** its order, i.e. that the cell's mutation produces the wrong outcome
deterministically (the B1 lesson: a lock test inside one transaction ran and could not fail). Rows
the plans already declare unforceable (plan 9 C8(b), plan 11 C7(a)–(b)) stay `UNFORCEABLE` with the
reviewer's structural check — the tester does not try to make them bite.

## 4. Progress tracker

One row per phase, newest state first; earlier states are appended below as *superseded* rows.
Only the actor named for a transition writes its row. **Since §3A (2026-09-19) phase rows use
`PENDING → IMPLEMENTED → VERIFIED` and are written only by the orchestrator; the batch tracker is
§4A.**

| Phase | Scope (one line) | State | Date | Actor | Note |
|---|---|---|---|---|---|
| 1 | Schema, migration, reset phases, enums (six assignment states), state map, criteria normalization, settings, test kit | **VERIFIED** | 2026-09-20 | orchestrator | batch A APPROVED; every row of this phase passed re-review 2 and is mutation-armed. rows 53, criteria 7; complex: no (round 9: +5 rows, +1 criterion) |
| 2 | Matcher mirror: Scanner tables, bag builder, evaluation, hand-walk fixtures | **VERIFIED** | 2026-09-20 | orchestrator | batch A APPROVED; every row of this phase passed re-review 2 and is mutation-armed. rows 75, criteria 7; complex: no; projection mandatory (rule 17) |
| 3 | Consistency check, manual repair, repair records, task-flag writer, their two endpoints | **VERIFIED** | 2026-09-20 | orchestrator | batch A APPROVED; every row of this phase passed re-review 2 and is mutation-armed. rows 42, criteria 8; complex: yes (advisory lock, renumber, multi-kind recomputation) (round 9: +1 row) |
| 4 | Transition operation: moves over six states, unit counters, inline self-heal, removal, stamps, payloads | **VERIFIED** | 2026-09-21 | orchestrator | batch B1 APPROVED at `6b0e7d5`; every row of this phase passed re-review 1 and is mutation-armed. rows 63, criteria 8; complex: yes (guarded statement, lock order) (round 9: +13 rows; owner card 1 fold 2026-09-21: +1 row, new criterion C8) |
| 5 | Goal credit: the MC-5 table incl. `resolved_early`, goal self-heal, the worked sequence | **VERIFIED** | 2026-09-21 | orchestrator | batch B1 APPROVED at `6b0e7d5`; every row of this phase passed re-review 1 and is mutation-armed. rows 23, criteria 3; complex: no (round 9: +5 rows; owner card 1 fold 2026-09-21: +1 row) |
| 6 | Demand service, set-based (D6): find-or-create, goal records, replay, deadline, statement bound, locked-set assertion | **VERIFIED** | 2026-09-21 | orchestrator | batch B2 APPROVED; every row of this phase passed re-review 1 and is mutation-armed. rows 36, criteria 8; complex: yes (set-based SQL, two-session rows) (round 8: +1 row, `_demand_lookup.py`) |
| 7 | Demand endpoint: key auth, body validation, duplicates, identity invariant over real bytes, envelope | **VERIFIED** | 2026-09-21 | orchestrator | batch B2 APPROVED; every row of this phase passed re-review 1 and is mutation-armed. rows 52, criteria 7; complex: no |
| 8 | Assignments: batch create with the matcher, override and `already_processed_by_scanner`, batch delete, race error, role cells | **PROJECTED** | 2026-09-21 | orchestrator | rows 67, criteria 8; complex: yes (lock order, race row) (round 9: +7 rows; owner card 1 fold 2026-09-21: +1 row, C4(m) — one-file perimeter extension, §7; **batch C1 fold 2026-09-21: +1 row, C5(b) — the caller's lock order, owner card C / L-29**; 24 mutation + 4 fixture cells folded; cards A, B, D ruled) |
| 9 | Processed webhook: §14F F5 order, `early` reason, grouped per-column counter update, replay, one owning transaction | PENDING | 2026-09-19 | planner | rows 43, criteria 8; complex: yes (grouping, sorted locks) (round 9: 4 rows rewritten, +9 rows; owner card 1 fold 2026-09-21: +1 row, C1(e)) |
| 10 | Task-state sync at S1–S9, the registry guard, three two-writer interleavings | PENDING | 2026-09-19 | planner | rows 35, criteria 7; complex: yes (nine-site sweep, two-session rows) (round 9: 1 row rewritten, +5 rows) |
| 11 | Removal hooks (task, item, PRIMARY unlink) and the category guard on both item writers | **PROJECTED** | 2026-09-21 | orchestrator | rows 26, criteria 7; complex: yes (five existing commands, new locks) (round 9: +1 row; **batch C1 fold 2026-09-21: −1 row, C4(h) WITHDRAWN as unbuildable — owner card F**; 8 mutation + 4 fixture cells folded; cards B, E ruled) |
| 12 | Priority, dense ordering, history records for user actions, the list endpoint | PENDING | 2026-09-19 | planner | rows 45, criteria 7; complex: yes (advisory lock, shift statements) |
| 13 | Row deletion cascade, second self-heal trigger, assignment reads and compact serializers | PENDING | 2026-09-19 | planner | rows 19, criteria 6; complex: yes (cascade, lock order) (rounds 8–9: 2 rows rewritten; **batch C1 tester card 2, 2026-09-21: +1 row and +1 criterion, C6(a) — plan 8 C4(l)'s cross-shape clause moved here, the only phase where both shapes exist**) |
| 13A | Scanner delete webhook: find-and-delete through the cascade, six carried questions (intention §14E) | PENDING | 2026-09-19 | planner | rows 37, criteria 7; complex: yes (multi-row cascade, deterministic contention rows); projection mandatory, not waivable (owner card 1 fold 2026-09-21: +1 row, C5(g)) |
| 14 | Frontend handoff and domain docs (thin; refine at prompt time) | PENDING | 2026-09-19 | planner | rows 5, criteria 2; complex: no (rounds 8–9: +1 row; depends on 13A) |

Totals (derived from the plan files by the planner's count script, 2026-09-19, after the round-8/9
delta): **615 criterion rows in 98 criteria across 15 phases** (planning-0: 532 / 90 / 14). No phase
exceeded eight criteria (3, 6, 8, 9 sat at eight).

**Owner card 1 fold, 2026-09-21 — totals now 620 / 99 / 15.** Five criterion rows authored by the
owner, one per plan: 4 C8(a), 5 C2(e), 8 C4(m), 9 C1(e), 13A C5(g). Derivation: the 2026-09-19
script total **+5**, each addition verified as exactly one `^+| C` line in `git diff` per file (a
new script disagrees with the published totals on row shape, so the published figure is carried
forward and incremented rather than re-derived). Criteria 98 → 99: plan 4 gains C8. Phase 4 now
also sits at eight criteria (3, 4, 6, 8, 9). **Rows 4 C8(a) and 5 C2(e) are born satisfied** (tests
exist, mutations measured red); **8 C4(m), 9 C1(e) and 13A C5(g) are owed by their phases' rounds.**

**Batch C1 fold, 2026-09-21 — totals stay 620 / 99.** Derivation: plan 8 `git diff` shows
**+29 / −28** `^| C` lines (net **+1**: C5(b), owner card C) and plan 11 **+11 / −12** (net
**−1**: C4(h) withdrawn, owner card F); +1 − 1 = 0 against the carried 620. Criteria unchanged —
C5(b) joins plan 8's existing C5 and C4(h) leaves a C4 that keeps other rows. Per the standing
practice since the owner card 1 fold, the published total is carried and adjusted by verified
per-file diffs rather than re-derived, because a row-shape regex still disagrees with it (the
C1 projection found the cause for plan 8: two shorthand lines, `C8(a)–C8(d)` and `C8(e)–C8(h)`,
each stand for four criteria — **this is a reporting artefact, not a row count error**).

**Batch C1 verification fold, 2026-09-21 — totals now 621 / 100.** One row and one criterion
added: plan 13 **C6(a)**, the create-vs-list key-set cross-check moved out of plan 8 C4(l) by
owner card 2 because phase 8 cannot compare against an endpoint phase 13 builds. Derivation:
620 + 1, the addition verified as exactly one `^| C` line in `git diff` on plan 13; criteria
99 → 100 because plan 13 gains a C6 group. No other row count moved — the tester edited no
criterion cell (`git diff` over the criteria tables: 0 lines).

**Trace coverage (derived by the same script from the trace cells).** Ledger: M1 → 1, 3, 4, 8, 10,
13, 13A · M2 → 9, 10, 11, 13A · M3 → 6, 9, 13A · M4 → 1, 6, 7, 8, 9, 12, 13, 13A · M5 → 5, 9, 12 ·
M6 → 3, 12, 13A · M7 → 7, 9, 13A · M8 → 2, 8, 11 · M9 → 3, 14. Every contract MC-1…MC-20 appears
in at least one trace cell (MC-10 only in 9; MC-11 in 10 and 13A; MC-20 in 3 and 13A). Amendment
rows are cited as `§14E En` / `§14F Fn` beside the contract they amend.

## 4A. Batch tracker (§3A)

| Batch | Phases | State | Date | Actor | Note |
|---|---|---|---|---|---|
| — | 4, 5, 8, 9, 13A | **OWNER FOLD** | 2026-09-21 | owner | **Owner card 1 ruled, both batches: author all five.** B1 re-review card 1 → plan 4 **C8(a)** (MC-19 payload spells `priority` as the enum's value) and plan 5 **C2(e)** (an upward goal drift survives a subtracting move, §12A (c)); both **born satisfied** — the tests exist and their mutations were measured red, so nothing is owed. B2 card 1 → plan 8 **C4(m)** (CF-1, demand authorship), plan 9 **C1(e)** (CF-3, blank-config refused before any DB read) and plan 13A **C5(g)** (CF-2, sorted VALUES / sorted `FOR UPDATE` do not deadlock); all three **owed by their own phases' rounds**, so batch C picks up two and batch D one. **No fix round and no reopened gate** — phases 4–7 stay VERIFIED. Also applied: plan 6 §5 task 2 step 1 replacement text (O1/N9 **closed**), and N15 — plan 5's divergence assertion now reads the list unfiltered to match C2(e) verbatim. Totals 615 → **620** rows / 98 → **99** criteria |
| A | 1, 2, 3 | **APPROVED** | 2026-09-20 | orchestrator | Re-review 2 (`handoffs/reviewer/2026-09-20_batch_A_rereview_2_handoff.md`, tree `f2157bd`): **170 PASS / 0 FAIL / 0 NOT_VERIFIED**, zero findings, 0 owner cards. All three findings CONFIRMED by measurement: the six tenancy filters all redden (four were inert), F-R2's record mutation reddens exactly its test, F-R3 deleted the right copy. Charter-rule-15 presence probe M10 on C1(k): 9 divergences across all 8 MC-20 kinds, so the absence row's instrument can observe presence. Path: review 1 125/30/15 → fix 1 → re-review 1 168/2/0 → fix 2 → **170/0/0**. Four new notes (N-S1…N-S4), three lessons (L-16…L-18) |
| A | 1, 2, 3 | REVIEWING | 2026-09-20 | orchestrator | *superseded.* final re-review, narrow — prompt `prompts/reviewer/2026-09-20_batch_A_rereview_2.md`, tree `f2157bd`, Opus + plan-reviewer, launched by the owner. Three findings and a regression check on C1(d)/C1(e); the 168 armed rows are not re-opened |
| A | 1, 2, 3 | IMPLEMENTED | 2026-09-20 | orchestrator | *superseded.* Fix round 2 (`handoffs/implementer/2026-09-20_batch_A_fix_2_handoff.md`, state `IMPLEMENTED`, checkpoints `5dbb9eb` + `f2157bd`). Ledger `declared = executed = 7`, all seven red — the five C1(k) workspace filters, F-R2's record value, and the `expected_task_flag` predicate. Perimeter 4 app files (+261/−31). Orchestrator L4 on `f2157bd`: 21 failed / 3264 passed / 2 skipped, baseline-identical both ways; the −1 against 3265 is exactly the duplicate test F-R3 deleted |
| A | 1, 2, 3 | FIX_PROMPT_READY | 2026-09-20 | orchestrator | *superseded.* fix round 2 (final), prompt `prompts/implementer/2026-09-20_batch_A_fix_2.md`, Codex terra/medium. Scope: F-R1 (restore the filter + arm C1(k) per kind), F-R2, F-R3 — nothing else. **Owner stop honoured:** the owner ruled re-review card 1 (restore `expected_task_flag`'s workspace filter; §6.5 amended accordingly) before this round was prepared |
| A | 1, 2, 3 | CHANGES_REQUESTED | 2026-09-20 | orchestrator | *superseded.* Re-review 1 (`handoffs/reviewer/2026-09-20_batch_A_rereview_1_handoff.md`, tree `983d774`): **168 PASS / 2 FAIL / 0 NOT_VERIFIED** of 170 — phase 1 53/0/0, phase 2 75/0/0, phase 3 40/2/0. Delta on review 1: PASS +43, FAIL −28, NOT_VERIFIED −15. All six production corrections CONFIRMED in behaviour; the fix round's declared mutation gap **closed** — 54 distinct mutations run, 3 equivalent mutants and 1 inert mutation recorded with calibrating controls. 1 blocking (F-R1 `expected_task_flag` lost its workspace filter and plan 3 C1(k) is inert for 4 of 5 filters), 2 should-fix (F-R2, F-R3), 9 notes, lessons L-10…L-15 owed upstream before batch B |
| A | 1, 2, 3 | REVIEWING | 2026-09-20 | orchestrator | *superseded.* light re-review (§3A), widened — prompt `prompts/reviewer/2026-09-20_batch_A_rereview_1.md`, tree `983d774`, Opus + plan-reviewer, launched by the owner. Widened for two reasons: the fix touched shared foundations (six §6.5 signatures, `_locks.py`, `consistency.py`, normalization, `reset_app`), and the fix round **declared its own mutation gap** — ~45 rows armed, 8 mutations run, `executed == declared` explicitly not claimed. The reviewer runs the missing mutations |
| A | 1, 2, 3 | IMPLEMENTED | 2026-09-20 | orchestrator | *superseded.* Fix round 1 (`handoffs/implementer/2026-09-20_batch_A_fix_1_handoff.md`, state `IMPLEMENTED_WITH_MUTATION_GAPS`, checkpoints `90f6b82` + `983d774`). All 16 findings and both notes dispositioned; perimeter is 8 production files, 8 test files (2 deletions: the orphan `test_settings.py` and the sole test-package `__init__.py`), 3 plan Review logs. Orchestrator L4 on `983d774`: 21 failed / 3265 passed / 2 skipped, baseline-identical both ways (3103 → 3265 passing). **Open gap:** mutations were run for only 8 of the rows armed this round |
| A | 1, 2, 3 | FIX_PROMPT_READY | 2026-09-20 | orchestrator | *superseded.* | fix prompt `prompts/implementer/2026-09-20_batch_A_fix_1.md`, Codex terra/medium, launched by the owner. Owner ruled the review's card 1: `CRITERIA_NORMALIZATION_VERSION` **stays at 1** (no live rows to re-sign; golden vectors updated instead). Next: a **light delta-scoped re-review** per §3A |
| A | 1, 2, 3 | CHANGES_REQUESTED | 2026-09-20 | orchestrator | *superseded.* Review 1 (`handoffs/reviewer/2026-09-20_batch_A_review_1_handoff.md`, Opus + plan-reviewer, tree `0d5d31d`): **125 PASS / 30 FAIL / 15 NOT_VERIFIED** of 170 rows — phase 1 40/8/5, phase 2 64/7/4, phase 3 21/15/6. 2 blocking (F-B1 repair crashes on priority-null/order-set; F-B2 normalization keeps blank list elements), 14 should-fix, 9 backlog notes, 9 plan lessons (L-1…L-9) owed upstream. 26 of the 30 FAILs are "the test is weaker than the row", not wrong production code. Prompt gaps 1 and 3 closed by the reviewer: Scanner conformance discharged for the criteria side, divergent on the item side (F-S1); the mutation audit found one surviving mutant (plan 2 C3(d)) |
| A | 1, 2, 3 | REVIEW_PROMPT_READY | 2026-09-20 | orchestrator | *superseded.* | handoff `handoffs/implementer/2026-09-19_batch_A_implement_1_handoff.md`; checkpoint `0d5d31d` (made by the orchestrator — the Codex session ended with nothing committed); review prompt `prompts/reviewer/2026-09-20_batch_A_review_1.md` |
| A | 1, 2, 3 | IMPLEMENTED | 2026-09-20 | orchestrator | *superseded.* Orchestrator L4 on `0d5d31d`: 21 failed / 3241 passed / 2 skipped, failure IDs identical to the 21-ID baseline in both directions (3103 + 138 new). Handoff frontmatter says `PARTIAL_NOT_READY_FOR_REVIEW` and its §"Current implementation state" claims the work is incomplete; both are **stale** — they were written early in an append-only log and are contradicted by the same handoff's later stamps and by the orchestrator's own run. Four evidence gaps carried into review: no Scanner `normalizeCriteria`/`node` transcripts (prompt projection note 3), no row-level Task 0 coverage map, no tree SHAs on the stamps, no graph delta text |
| A | 1, 2, 3 | IMPLEMENTATION_PROMPT_READY | 2026-09-19 | orchestrator | *superseded.* projected, no blocker; prompt `prompts/implementer/2026-09-19_batch_A_implement_1.md`; Codex terra/medium, launched by the owner |
| B1 | 4, 5 | **APPROVED** (gate pending a clean L4) | 2026-09-21 | orchestrator | Re-review 1 (`handoffs/reviewer/2026-09-21_batch_B1_rereview_1_handoff.md`, tree `60d6a12`): **84 PASS / 0 FAIL / 0 NOT_VERIFIED**, zero blocking, zero should-fix, 12 mutation probes. **The declared C5(c) gap is closed** — the reviewer planted it in six seconds, exactly the right test reddened, so `executed == declared == 34`. Path: review 1 83/1/0 → fix 1 → **84/84**. **Key finding, routed to phase 8:** the S2 lock fixture *runs and cannot fail* — the reviewer dropped the task lock and reversed the order and all 63 tests still passed, because a test owns one transaction and nothing can contend with it. Keep it as the caller contract written down, never cite it as proof. 7 notes routed, 2 to phase 8. **Card 1 (promote the two new guards to criterion rows) is left for the owner** — see below |
| B1 | 4, 5 | REVIEWING | 2026-09-21 | orchestrator | *superseded.* light delta-scoped re-review (§3A) — prompt `prompts/reviewer/2026-09-21_batch_B1_rereview_1.md`, tree `60d6a12`, Opus |
| B1 | 4, 5 | IMPLEMENTED | 2026-09-21 | orchestrator | Fix round 1 (`handoffs/implementer/2026-09-21_batch_B1_fix_1_handoff.md`, state DONE, checkpoint `60d6a12`). All five items closed. **Zero production-code diff against `1351b5f`** — tests and plan docs only (+177 lines across the three test files). Orchestrator L4 on `60d6a12`: **22 failed / 3349 passed / 2 skipped**. The 22nd is `test_ended_shift_bucket_collapse.py::test_list_workers_totals_reports_an_open_clock_out_record_as_ended_shift`, **outside this perimeter and provably independent**: I ran the file alone with no stock-report test present and it still fails, and its line 554 computes `datetime.now(timezone.utc)` then subtracts 3 h, so between 00:00 and ~03:00 UTC the clock-in lands on the previous UTC day. Run at 00:31 UTC. **A clean 21-ID L4 must be re-taken after 03:00 UTC before the approval gate.** Ledger honestly re-derived: `executed 33 != declared 34`; the single gap is plan 4 C5(c)'s mutation, declared as note N12, not hidden. Two further gaps found and closed this round (C5(a), C5(b) were counted in the original prose sum but had no run anywhere) |
| B1 | 4, 5 | FIX_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* | fix round 1, prompt `prompts/implementer/2026-09-21_batch_B1_fix_1.md`, Sonnet. Scope: S1, S2, S3, S4 + card 2's scenario. **Orchestrator rulings (owner asleep, autonomous run):** card 1 — the intention settles it (§9D MC-19's payload block names `"high"\|"medium"\|"low"\|null`), so the guard is added tonight as a test plus a **candidate criterion in plan 4's Review log**; I did **not** author a criterion row, because the owner's fold authority is mutation and fixture cells only. Card 2 — judgment, not settled; proceeding **provisionally** on the reviewer's recommendation to close it now, flagged for the owner. §6.5 amended with the three batch B1 signatures and the spent N-S3 sentence deleted; plan 4's C1(u) and C6(c) mutation cells corrected per review notes N2/N3 |
| B1 | 4, 5 | CHANGES_REQUESTED | 2026-09-21 | orchestrator | Review 1 (`handoffs/reviewer/2026-09-21_batch_B1_review_1_handoff.md`, Opus, tree `1351b5f`): **83 PASS / 1 FAIL / 0 NOT_VERIFIED** of 84, **zero blocking, no production defect**. Four should-fix, all in tests and paperwork: S1 plan 4 C5(b) asserts 3 of its 4 clauses; S2 no test in either phase takes a lock, so H6/N-R1's caller premise is unproven and undeclared; S3 MC-19's priority payload is implemented but exercised by nothing; S4 both mutation ledgers assert counts that cannot be derived from their own artifacts. 11 notes routed. **The fold was judged: no over-reach in any of the 22 cells**, but two carried analytical errors (N2, N3) — corrected here |
| B1 | 4, 5 | REVIEW_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* | review prompt `prompts/reviewer/2026-09-21_batch_B1_review_1.md`, tree `1351b5f`, Opus + plan-reviewer, launched by the orchestrator (owner asleep; autonomous run authorized 2026-09-21) |
| B1 | 4, 5 | IMPLEMENTED | 2026-09-21 | orchestrator | Handoff `handoffs/implementer/2026-09-21_batch_B1_implement_1_handoff.md` (Sonnet, state DONE, 0 owner cards). Checkpoints `e50807b` (phase 4), `1351b5f` (phase 5). 84 rows mapped 1:1; ledgers `executed == declared` at 33 (phase 4) and 15 (phase 5). **Orchestrator L4 on `1351b5f`: 21 failed / 3349 passed / 2 skipped, baseline-identical both ways; 3349 = 3264 + 85 exactly.** Perimeter verified: 4 new production files, 3 new test files, 3 authorized edits (`_repair_records.py` +delta, `_task_flag.py` +workspace predicate, `repair_stock_report.py` call site). Two self-reported findings: phase 4 C3's 22 rows reduce to 4 guard branches (four rows double-guarded, combined removal run to prove they can fail); phase 5 C2(c)'s mutation was inert at its literal site and was re-sited with both runs recorded |
| B1 | 4, 5 | IMPLEMENTATION_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* | **Batch B split into B1 (4, 5) and B2 (6, 7) by the owner, 2026-09-21**, because the implementer for batch B is a **Sonnet** agent and 172 rows in one session is the largest ask this pipeline has made of any implementer. Each half gets its own implement → review → approval cycle. Projection `handoffs/projectionist/2026-09-21_batch_B_projection_handoff.md` (7 blockers, 38 fold cells, 1 outcome defect). Lesson fold applied to plans 4-5 at `a306298` — 22 mutation/fixture cells. Prompt `prompts/implementer/2026-09-21_batch_B1_implement_1.md` |
| B2 | 6, 7 | **APPROVED** | 2026-09-21 | orchestrator | Re-review 1 (`handoffs/reviewer/2026-09-21_batch_B2_rereview_1_handoff.md`, tree `29b4395`): **88 PASS / 0 FAIL / 0 NOT_VERIFIED**, unhedged. 8 mutation probes across 4 production files, all reverted and hash-matched. **The arming question is closed, and the fix round's reasoning was wrong even though its conclusion was right:** its single mutation could only break identity *apart*, so it was physically incapable of arming the three "two rows" cases, and it justified them by citing review 1's mutations — which had been run against *different tests*. The reviewer ran the right three (lower-case keys, trim key whitespace, blur 1 into 1.0) and each reddened exactly its own test on its own row count. Two by-products: the key-order row is armed by a line in `properties_signature.py`, a file **neither plan mentions**, so editing it silently edits a stock-report guarantee; and the repo-wide "nothing was written" instrument had **never been observed to fire** until this round made it fire. New lesson **L-23** |
| B2 | 6, 7 | REVIEWING | 2026-09-21 | orchestrator | *superseded.* light delta-scoped re-review (§3A) — prompt `prompts/reviewer/2026-09-21_batch_B2_rereview_1.md`, tree `29b4395`, Opus |
| B2 | 6, 7 | IMPLEMENTED | 2026-09-21 | orchestrator | Fix round 1 (`handoffs/implementer/2026-09-21_batch_B2_fix_1_handoff.md`, DONE, checkpoint `29b4395`). All three findings closed. **`git diff ff39a96..HEAD -- app/beyo_manager/` is empty — verified by me; tests only** (+300/−13 across two test files). Orchestrator L4 at 02:58 UTC: **21 failed / 3445 passed / 2 skipped**, baseline-identical both ways; 3445 = 3436 + 9 net new tests. **One wrinkle the implementer recorded honestly and the re-review must judge:** the single arming mutation reddened 5 of the 8 new endpoint tests on their own row-count assertion, while the other 3 failed through an unrelated consistency check instead — so those three may not discriminate on their own terms |
| B2 | 6, 7 | FIX_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* | fix round 1, prompt `prompts/implementer/2026-09-21_batch_B2_fix_1.md`, Sonnet, **TESTS ONLY**. **Orchestrator ruling:** B1 is settled by the intention — §4A MC-3's final bullet states the proof form and observable verbatim ("proven through the webhook endpoint with real JSON bytes … Each of (a)–(e) is its own row, and so is each 'two rows' case") — so I ruled it without the owner and scoped the round to tests. **Card 1 (promote three uncovered invariants to criterion rows) is left for the owner**: authoring a criterion row is reserved to them, nothing gates on it, and the three are in the carry-forward table. Master plan §6.5 and §9 amended; the third amendment (plan 6 §5 task 2 step 1) is a **task cell, outside this run's fold authority** — the replacement text is recorded in plan 6's Review log for the owner to apply |
| B2 | 6, 7 | CHANGES_REQUESTED | 2026-09-21 | orchestrator | Review 1 (`handoffs/reviewer/2026-09-21_batch_B2_review_1_handoff.md`, Opus, tree `ff39a96`): **80 PASS / 8 FAIL** of 88 — phase 6 **36/36**, phase 7 44/52. **One blocking finding, one cause, no production defect found anywhere.** B1: plan 7 C4(a)–(h) prove the MC-3/M4 identity invariant at the parser (comparing two signatures) where the rows' outcomes name persisted rows and the intention names the endpoint. Structurally safe — the signature is computed once and is the single value used by the duplicate check, discovery, insert and lock — so the remedy is tests only. S1: three more rows whose outcomes name database state are asserted at parser scope. S2: one orphan test. The reviewer **closed the seven declined mutations itself** against approved phase-1 code, restoring it byte-for-byte. It also measured the statement budget exact (not slack), confirmed the two-session rows force their race, and confirmed the implementer's self-caught false green is genuinely fixed |
| B2 | 6, 7 | REVIEW_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* | review prompt `prompts/reviewer/2026-09-21_batch_B2_review_1.md`, tree `ff39a96`, Opus |
| B2 | 6, 7 | IMPLEMENTED | 2026-09-21 | orchestrator | Handoff `handoffs/implementer/2026-09-21_batch_B2_implement_1_handoff.md` (Sonnet, DONE, 0 cards). Checkpoints `4ca6da1` (phase 6), `ff39a96` (phase 7). Perimeter is **purely additive** — 17 files, +2687/−0, so `record_statements`/`count_writes` are provably byte-identical. Phase 6: 31 tests, 30/30 mutations red. Phase 7: 55 tests, 22/29 run, **7 declined** (plan 7 C4(b)–(h) name properties of phase 1's approved `criteria_normalization.py`; the implementer cited that file's golden-vector coverage instead of mutating out-of-perimeter code — **the reviewer closes these, per the B1 lesson**). **Orchestrator L4 on `ff39a96` at 02:13 UTC: 21 failed / 3436 passed / 2 skipped, baseline-identical both ways.** The implementer's one unexplained extra pass is resolved: 3436 = 3349 (the `60d6a12` stamp, taken at 00:31 UTC while the analytics drifter was red) + 86 new + 1 drifter recovered. Measured directly: that test failed in isolation at 00:31 and passes in isolation at 02:11 — time-dependent and independent of this project, exact window unverified. One self-caught false green: the implementer's first-draft C1 auth fixture used a nonexistent workspace id, so two mutations looked green because verification failure and the command's own workspace check raise the same type; it found this with a probe-landed check, fixed the fixture and re-confirmed both red |
| B2 | 6, 7 | IMPLEMENTATION_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* | prompt `prompts/implementer/2026-09-21_batch_B2_implement_1.md`, Sonnet. Fold applied to plans 6-7 at `a2f4fc2` — 21 mutation/fixture cells. Blockers B3 (statement listener cannot see parameters → `record_statement_calls` added, perimeter extended), B4 (`StockDemandOutcomeEnum` never shipped → `enums.py` added to the perimeter for that name only), B5 (every row commits and purges), B6 (self-defeating monkeypatch) and outcome defect O1 (bind two distinct parameters, which satisfies the cell verbatim) are all resolved in the prompt |
| B2 | 6, 7 | BATCH_NOT_STARTED | 2026-09-21 | orchestrator | *superseded.* | waits for B1 APPROVED. Fold for plans 6-7 (16 cells) applied at B2 prompt time, not now. Carries blockers B3 (statement listener cannot see parameters), B4 (`StockDemandOutcomeEnum` never shipped), B5 (every row must commit and purge), B6 (plan 7 C7(a)'s monkeypatch is self-defeating), and outcome defect O1 (plan 6 C7(a) says "two parameters"; one shared bind compiles to one) |
| B | 4, 5, 6, 7 | BATCH_NOT_STARTED | 2026-09-19 | orchestrator | *superseded by the B1/B2 split.* |
| C1 | 8, 11 | **TESTED** | 2026-09-21 | orchestrator | Tester (`handoffs/tester/2026-09-21_batch_C1_test_1_handoff.md`, Opus + verification-engineer, checkpoint `8c60fb0`). **93 rows, 103 mutation runs, ZERO production defects** — every mutant changed behaviour the way its plan said it would. `executed == declared == 95` with summands printed; 29 tests added, 0 removed. **Eleven rows could not fail** as shipped or as written, in five shapes: outcome indistinguishable from a DB constraint (C5(a)); guarded twice so no single-site mutant exists (8 C4(k), C6(c), C6(i), C6(e)); the named mutation's site not load-bearing (8 C1(r), C4(c); 11 C2(b)); fixture with two sufficient causes or unordered against its key (8 C3(e), C3(a)); assertion read from a stale identity map (11 C3(a), C2(c)). All eleven now armed or recorded unprovable with the reason. Plan 11 C5(a)'s rollback clause — which the implementer honestly reported as unobservable in its fixture — is proven on a second fresh session. **Boundaries verified by me, not cited:** `git diff 6eaf2d3..8c60fb0 -- app/beyo_manager/` empty, 0 criteria-table lines edited, and my own L4 on the tester tree **21 failed / 3541 passed / 1 skipped**, IDs identical to the published baseline both ways, `3512 + 29 = 3541` exactly. Best single find, entirely measured: plan 8 C3(a)'s "sorted failures" sub-check **cannot fail** — criteria are JSONB and Postgres orders JSONB keys by length-then-bytes, which for `quantity`/`upholstery`/`wood_group` coincides with alphabetical. **Two owner cards, both ruled the same day:** card 1 (C5(a) gains `count_writes == 0`, §9 rule 7's use again) and card 2 (C4(l)'s cross-shape clause **moved to plan 13 C6(a)** — the only phase where both shapes exist; totals 620 → **621 / 100**). 13 backfills folded, plus `criteria_matcher.py` added to plan 8 §7's probe perimeter — it was probed without a declaration covering it. 5 candidate criteria carried, including the implementer's own (category change plus another field in one request, confirmed covered by nothing). Next: the review prompt |
| C1 | 8, 11 | TEST_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* Implemented (`handoffs/implementer/2026-09-21_batch_C1_implement_1_handoff.md`, Sonnet, DONE, **0 owner cards**). Checkpoints `00c21c9` (8), `4561746` + `6eaf2d3` (11). Perimeter: 5 new production files, 8 edited, 8 new test files, 2 edited. **Orchestrator L4 on `6eaf2d3`, run independently rather than consumed: 21 failed / 3512 passed / 1 skipped, the 21 IDs identical to the published baseline in both directions (`comm` both ways empty).** 66 new tests for 88 rows — **lean, not padded**, which is the first evidence the tester split is landing: the implementer named a long list of rows it did not exercise instead of covering them weakly. Three self-caught items, all reported rather than hidden: a test-module name collision that only a full-suite collection can catch (→ new §9 **rule 19**), a checkpoint whose `git add` silently missed five production edits (fixed by `6eaf2d3`, not amended), and **plan 8 C5(b)'s mutation cell naming a site that was never written** — the orchestrator verified and corrected it to `_locks.py:_lock`'s `.order_by(client_id)`, and extended §7's probe perimeter to that file. One undeclared judgment call carries no criterion (the category guard's placement before `_DIRECT_FIELDS`) and is routed to the tester as a candidate criterion. Test prompt `prompts/tester/2026-09-21_batch_C1_test_1.md`, Opus |
| C1 | 8, 11 | PROJECTED | 2026-09-21 | orchestrator | *superseded.* Projection r0 (`handoffs/projectionist/2026-09-21_batch_C1_projection_handoff.md`, Opus, tree `b95780b`, prompt `prompts/projectionist/2026-09-21_batch_C1_projection.md`). **34 empty mutation cells classified 29 / 1 / 4** under §3B's amended bullet; the fold applied 32 mutation and 8 fixture cells, left 2 labelled blanks, and added §9 rules 17 and 18, a rule 7 fifth use, a rule 8 amendment, two §6.1b rows and a §10 environment fact. **Three of the pre-pass's proposed mutations were wrong at the site** (one named a symbol not there, one named the wrong file and would have crashed the suite, one predicted an impossible result) — caught by reading shipped phase 1-7 code, which is what this gate is for. **Six owner cards, all ruled the same day:** A (C1(j)/C1(k) could not fail behind the unique index → `count_writes == 0` clause, rule 7's fifth use — the owner overruled the recommended fixture route because it would have armed the rows by proving *check ordering* and put two independent refusal reasons in one fixture), B (plan 11 C1(c) and plan 8 C6(g) were unbuildable against the round-9 §14F F9 ruling → both rebuilt through a **`failed`** assignment), C (**C5(b) authored** — the caller's lock order, forceable form with a recorded `UNFORCEABLE` fallback; closes L-29, the batch B1 fixture that ran and could not fail), D (C4(l) re-stated to the fourteen-key shape), E (plan 11 C4(b)/C5(b) **known-unarmed** — guarded twice, and the restructure would take a row lock on every ordinary item save), F (plan 11 C4(h) **withdrawn** — `complete_task_post_handling` builds `UpdateItemRequest(client_id, item_zone)` and structurally cannot change a category; verified at source by the orchestrator). Totals unchanged at 620 / 99 (+1 row plan 8, −1 plan 11, both verified by `git diff`). Next: the implementer prompt |
| C2 | 9, 10 | BATCH_NOT_STARTED | 2026-09-21 | orchestrator | waits for C1 APPROVED (9←8). Phase 10's concurrency evidence is bounded by §3B |
| C | 8, 9, 10, 11 | BATCH_NOT_STARTED | 2026-09-19 | orchestrator | *superseded by the C1/C2 split.* |
| D | 12, 13, 13A, 14 | BATCH_NOT_STARTED | 2026-09-19 | orchestrator | waits for C APPROVED; projection checks plan 13A §7 (the six §14E questions) |

## 5. Contract resolution

The repo has an architecture contract system (`architecture/*.md`; `_local.md` files extend the
canonical ones and win). Implementing sessions re-emit this list before coding and read
implementation files only to learn *what exists* (relational reads), never to learn *how to
write* (pattern reads).

**Selected (binding for every phase):**

| Contract | Why |
|---|---|
| `01_architecture.md`, `21_naming_conventions.md` | layer map; file/function/table/route naming (boolean `is_`/`has_`, `ix_`/`uq_`/`ck_` prefixes, kebab-case URLs) |
| `03_models.md` | `IdentityMixin`, FK `String(64)` + `index=True`, enum columns via `configure_sa_enum_values`, `updated_at` — **overridden for the four new tables**: no `onupdate=` anywhere (intention MC-17, MC-15) |
| `06_commands.md` + `06_commands_local.md` | one `maybe_begin` per command, subordinates never commit/dispatch, events after the block |
| `07_queries.md` + `07_queries_local.md` | workspace filter first, `is_deleted` filter, dict results — **overridden for `GET /stock-report/items`**: unpaginated by ratified owner answer (intention §9, §12 "pagination deferred"); the `_pagination` key is not emitted |
| `05_errors.md` + `05_errors_local.md` | `DomainError.http_status`; identities as the leading message token — **two ratified exceptions**: the two assignment errors carry `code` + `details` (intention MC-13, C25), and the category-guard 409 keeps its ratified sentence verbatim with no identity token (intention MC-14) |
| `09_routers.md`, `10_auth.md`, `28_roles_permissions.md` | thin routers, `Depends(require_roles([...]))` from `bm/routers/utils/roles.py`, `run_service`, `build_ok`/`build_err` |
| `11_infra_events.md` | `build_workspace_event`, `<entity>:<verb>` names, dispatch after commit only |
| `24_multi_tenancy.md`, `25_soft_delete.md` | `workspace_id` on every table; soft-delete trio; explicit cascade decisions (intention MC-16) |
| `30_migrations.md` | autogenerate, descriptive message, never edit an applied revision; one revision for this project (P1) |
| `32_concurrency.md` | `FOR UPDATE`, column-referencing updates, no read-then-assign — made exact by intention MC-1's lock order |
| `46_serialization.md` + `46_serialization_local.md` | serialize inside the query service (the local reality for read layers); envelope shape |
| `15_testing.md`, `50_testing_strategy.md` | markers (`unit`, `integration`), file mirroring, module-local `_ctx`, `SUPPRESS_EVENT_BUS` |
| `19_integrations.md`, `18_security.md` | inbound webhook secret in env, constant-time compare (bytes, MC-8), fail closed |
| `23_documentation.md` | `docs/domains/stock_report/api.md` + `states.md` (phase 14) |

**Read for grounding only (not binding here):** `53_operational_cli.md` — the consistency report
and repair are endpoints by ratified proposal P35, not CLI commands; `52_replayability.md`,
`51_worker_runtime.md` — no Manager-side worker or queue exists for these webhooks (§14D D6).

**Excluded:** `57_shopify_integration.md`, `47_notifications*`, `44_case*`, `43_image*` (only
`serialize_image_light` is reused, by import), `35_gdpr_erasure.md`, `36_audit_log.md` (the new
events are not audited: `get_audited_events()` is not extended by this project).

## 6. Shared skeleton and naming registry

Fixed before any code exists. A session that needs a name not listed here adds it to this
section in the same round and says so in its handoff; a second name for a registered thing is a
review finding.

### 6.1 Domain package `bm/domain/stock_report/`

| Module | Public names |
|---|---|
| `enums.py` | `StockTaskAssignmentStateEnum` (`in_queue`, `in_progress`, `awaiting`, `resolved`, `failed`, `resolved_early` — six members, intention §14F F1); `ACTIVE_ASSIGNMENT_STATES = {in_queue, in_progress, awaiting}`, `TERMINAL_ASSIGNMENT_STATES = {resolved, failed, resolved_early}` (frozensets; a partition of the enum — §9 rule 16); `StockReportPriorityEnum` (`high`, `medium`, `low`); `StockReportHistoryRecordTypeEnum` (`quantity_requested_change`, `priority_change`, `priority_order_change`); `StockReportRepairTargetKindEnum` (`stock_report_item`, `history_record`, `task`, `group`); `StockCriteriaMismatchReasonEnum` (`missing_on_item`, `value_not_accepted`, `no_group_for_value`, `criterion_not_understood`); `StockDemandOutcomeEnum` (`applied`, `category_not_found`); `StockDemandDeletedOutcomeEnum` (`deleted`, `not_found`, `category_not_found` — §14E E7); `ItemsProcessedOutcomeEnum` (`resolved`, `ignored`); `ItemsProcessedReasonEnum` (`item_not_found`, `no_open_assignment`, `early` — §14F F5/P43; the response's `reason` is JSON `null` for a resolution from `awaiting`); `REPAIR_TRIGGER_MANUAL = "manual"`; `INLINE_REPAIR_TRIGGERS` = frozenset of `inline:` + {`create_assignments`, `task_sync`, `delete_assignments`, `delete_task`, `remove_item_from_task`, `delete_item`, `items_processed`, `delete_stock_report_item`, `stock_demand_deleted`} (all shipped by phase 1; 13A adds no enum)  **Correction (2026-09-21, batch B2):** §6.1's names are **not** all shipped by phase 1. At batch A's close `enums.py` held five enums plus the two frozensets; `StockDemandOutcomeEnum` shipped in **phase 6**, and `StockDemandDeletedOutcomeEnum`, `ItemsProcessedOutcomeEnum`, `ItemsProcessedReasonEnum`, `REPAIR_TRIGGER_MANUAL` and `INLINE_REPAIR_TRIGGERS` are still unshipped — they belong to phases 9 and 13A and must not be added before they have a caller (charter rule 4). Plan 1 never mentioned them, so batch A's 170/170 is unaffected; the §6.1 claim was what was wrong. |
| `state_map.py` | `ASSIGNMENT_STATE_BY_TASK_STATE: dict[TaskStateEnum, StockTaskAssignmentStateEnum]` (intention §5, total over the 8 members) |
| `criteria_normalization.py` | `normalize_stock_criteria(raw: dict) -> dict`; `compute_stock_criteria_signature(raw: dict) -> str` (= `compute_properties_signature(normalize_stock_criteria(raw))`, the existing function imported unchanged from `bm/domain/items/properties_signature.py`); `CRITERIA_NORMALIZATION_VERSION = 1` |
| `scanner_property_tables.py` | `WOOD_GROUPS`, `DRAWER_RANGES`, `WOOD_TYPE_KEY`, `WOOD_GROUP_KEY`, `DRAWERS_QTY_KEY`, `DRAWERS_RANGE_KEY`, `EXCLUDED_ITEM_PROPERTY_KEYS` (`qty_extensions`, `quantity`, `wood_group`, `drawers_range`), `SCANNER_SOURCE_COMMIT = "0d80bf2"`, `SCANNER_SOURCE_READ_ON = "2026-09-18"`, `validate_wood_groups(groups) -> None`, `validate_drawer_ranges(ranges) -> None` (both called at import), `wood_group_of_token(token) -> str \| None`, `drawer_range_of(stored: str) -> str \| None` |
| `criteria_matcher.py` | `CriterionFailure` (frozen dataclass: `key: str`, `reason: StockCriteriaMismatchReasonEnum`); `build_item_property_bag(item) -> dict[str, str]`; `tokenize_property_value(value: str) -> list[str]`; `evaluate_stock_criteria(item, criteria: dict) -> list[CriterionFailure]` (sorted by key); `matches_stock_criteria(item, criteria) -> bool` |
| `serializers.py` | `serialize_stock_report_item(row, *, category) -> dict`; `serialize_stock_task_assignment(assignment, *, item, task, images) -> dict`; `serialize_item_compact(item, *, images) -> dict`; `serialize_task_compact(task) -> dict` |

### 6.1b Foreign load-bearing dependencies (owner, 2026-09-21 — lesson L-25)

Files **outside every plan's perimeter** that nonetheless arm a Stock Report guarantee. Editing one
silently edits this project. Any phase touching them re-reads this table; any future plan that
depends on a new one adds a row here in the same act.

| File (foreign) | The load-bearing detail | What it arms | How it was found |
|---|---|---|---|
| `bm/domain/items/properties_signature.py` | `sort_keys=True` in the `json.dumps` of `compute_properties_signature` (line ~25) | Row identity under JSON key reordering — intention §4A MC-3, **plan 7 C4(a)**. Every mutation cell in that family pointed at `criteria_normalization.py`, where C4(a) is provably **inert** (measured, batch B2 re-review P1). | batch B2 re-review, L-25 |
| `bm/services/commands/tasks/add_item_to_task.py` | the one-active-PRIMARY-per-task check (`:47-57`) and the `removed_at IS NULL` duplicate check (`:59-68`) | MC-13's `item_not_task_primary` and MC-14's "a swap is removal then add" — and, negatively, the **constructibility** of plan 8 C6(g) / plan 11 C1(c): because a task holds one active PRIMARY item, "one task with two assignments" is reachable only as terminal + active for the same item | batch C1 projection, L-25 |
| `bm/services/commands/task_post_handling/complete_task_post_handling.py` | its `_update_item_in_session` call builds `UpdateItemRequest(client_id=…, item_zone=…)` (`:120-129`) — `item_category_id` is never in `model_fields_set` | MC-14's "the guard covers both callers" is true by *placement*, not because this caller can change a category. This is why plan 11 C4(h) was withdrawn (owner card F, 2026-09-21) | batch C1 projection, L-25 |

A source comment now marks the argument in place and points back here, so the next editor of that
file sees the dependency without reading this plan set.

### 6.2 Models `bm/models/tables/stock_report/` (registered in `bm/models/__init__.py`; prefixes added to `bm/models/tables/client_id_prefix_map.md`)

| Class / file | Prefix | Table | Columns beyond `client_id`, `workspace_id` |
|---|---|---|---|
| `StockReportItem` / `stock_report_item.py` | `sri` | `stock_report_items` | `item_category_id` FK; `properties` JSONB not null; `properties_signature` String(64) not null; `quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting` Integer not null default 0 server_default `0`; `priority` enum nullable; `priority_order` Integer nullable; `created_at`, `created_by_id`, `updated_at` (**no `onupdate`**), `updated_by_id`, `is_deleted`, `deleted_at`, `deleted_by_id` |
| `StockTaskAssignment` / `stock_task_assignment.py` | `sta` | `stock_task_assignments` | `stock_report_item_id` FK; `task_id` FK; `item_id` FK; `credited_history_record_id` FK nullable; `quantity` Integer not null; `property_mismatch_overridden` Boolean not null default false; `state` enum not null; authorship + soft-delete trio as above (no `onupdate`) |
| `StockReportHistoryRecord` / `stock_report_history_record.py` | `srh` | `stock_report_history_records` | `stock_report_item_id` FK; `type` enum; `quantity_requested`, `quantity_awaiting` Integer not null; `priority` enum nullable; `priority_order` nullable; `created_at`, `created_by_id`; soft-delete trio; **no `updated_*`** |
| `StockReportRepairRecord` / `stock_report_repair_record.py` | `srr` | `stock_report_repair_records` | `target_kind` enum; `target_client_id` String(64) **no FK**; `field` String(64); `stored_value` Text nullable; `recomputed_value` Text nullable; `trigger` String(64); `created_by_id` FK nullable; `created_at`; **no soft-delete trio, no `updated_*`** |
| `Task.is_stock_assignment` (edit to `bm/models/tables/tasks/task.py`) | — | `tasks` | Boolean not null, default `False`, **`server_default=sa.false()`** so raw inserts elsewhere keep working |

Every FK column has `index=True` (03_models). Postgres enum type names: `stock_task_assignment_state_enum`,
`stock_report_priority_enum`, `stock_report_history_record_type_enum`,
`stock_report_repair_target_kind_enum`. Named indexes and constraints:

| Name | Definition |
|---|---|
| `uix_stock_report_items_identity_active` | unique `(workspace_id, item_category_id, properties_signature)` `WHERE is_deleted = false` |
| `ix_stock_report_items_workspace_priority_order` | `(workspace_id, priority, priority_order)` |
| `ck_stock_report_items_quantity_requested_nonneg`, `…_quantity_in_queue_nonneg`, `…_quantity_in_progress_nonneg`, `…_quantity_awaiting_nonneg` | `>= 0` |
| `uix_stock_task_assignments_item_active` | unique `(workspace_id, item_id)` `WHERE is_deleted = false AND state IN ('in_queue','in_progress','awaiting')` |
| `uix_stock_task_assignments_task_active` | unique `(workspace_id, task_id)`, same predicate |
| `ix_stock_task_assignments_row_state` | `(stock_report_item_id, state)` |
| `ck_stock_task_assignments_quantity_positive` | `quantity >= 1` |
| `ix_stock_report_history_records_row_type_created` | `(stock_report_item_id, type, created_at)` |
| `ck_stock_report_history_records_quantity_awaiting_nonneg` | `>= 0` |
| `ix_stock_report_repair_records_target_client_id` | `(target_client_id)` |

Migration: **one** autogenerated revision, message `create_stock_report_tables`, `down_revision =
"ce99896e6f49"`, written in phase 1 and never edited afterwards. Every later phase works on the
schema as phase 1 ships it; a later schema need is a new revision plus a Review-log entry, never
an edit.

### 6.3 Settings (`bm/config.py`, `Settings`)

| Field | Alias | Type / default |
|---|---|---|
| `manager_api_key_to_location_tracker_app` | `MANAGER_API_KEY_TO_LOCATION_TRACKER_APP` | `str \| None = None` |
| `location_tracker_webhook_workspace_id` | `LOCATION_TRACKER_WEBHOOK_WORKSPACE_ID` | `str \| None = None` |
| `stock_demand_webhook_timeout_ms` | `STOCK_DEMAND_WEBHOOK_TIMEOUT_MS` | `int = 5000` |

Unset or blank key/workspace → every webhook request answers 401 (fail closed). The timeout setting
governs both Scanner stock messages — demand (7) and delete (13A; §14E E9) — and not the processed
webhook. Tests read the default from `Settings.model_fields["stock_demand_webhook_timeout_ms"].default`,
never as a typed literal (charter rule 13).

### 6.4 Errors (`bm/errors/stock_report.py`, new file)

| Class | Base | `http_status` | Message / extras |
|---|---|---|---|
| `LocationTrackerWebhookAuthError` | `DomainError` | 401 | message exactly `Unauthorized.` for every cause; the cause is logged |
| `StockDemandDeadlineExceeded` | `DomainError` | 503 | `Stock demand request exceeded its time limit.` — raised by the demand **and** the delete webhook (§14E E9; both are Scanner "stock messages") |
| `StockAssignmentRefused` | `ValidationError` | 422 | `code = "stock_assignment_refused"`, `details: list[{"index", "reason"}]`; message `Stock assignment refused.` **Closed reason vocabulary, in MC-13's order** (§14F F9 inserted): `duplicate_item_in_batch`, `duplicate_task_in_batch` (phase 1 of the check), then `stock_report_item_not_found`, `task_not_found`, `item_not_found`, `item_not_task_primary`, `already_processed_by_scanner`, `task_failed_or_cancelled`, `item_already_assigned`, `item_has_no_category`, `category_mismatch` |
| `StockAssignmentPropertyMismatch` | `ConflictError` | 409 | `code = "stock_assignment_property_mismatch"`, `details: list[{"index", "stock_report_item_id", "task_id", "item_id", "failures": [{"key", "reason"}]}]`; message `Stock assignment property mismatch.` |
| `IllegalAssignmentMove` (lives in `_move_assignment.py`) | `RuntimeError` | (500 via `run_service`) | a programming error, never a domain error (MC-1 ✗ cells) |

Registered message identities (05_errors_local leading-token form): `STOCK_REPORT_TARGET_OUT_OF_RANGE`
(422, MC-7 `target_out_of_range`), `STOCK_REPORT_ROW_HAS_NO_PRIORITY` (422, MC-7
`row_has_no_priority`), `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER` (422, §7A unknown token). The
category guard raises `ConflictError("Unassign this item from the stock report before changing its
category.")` — ratified sentence, no token. Webhook 422 messages start `Malformed request: ` and
name every offending entry by zero-based index (MC-8); Scanner does not parse them.

### 6.5 Services

`bm/services/commands/stock_report/` (subordinate operations are private modules; commands take
`ctx`):

| Module | Public names / signature |
|---|---|
| `_move_assignment.py` | `ASSIGNMENT_DELETE` (sentinel); `move_assignment(session, assignment, target, *, workspace_id, actor_user_id, now, trigger, is_creation=False) -> list[WorkspaceEvent]` (the allowed-move table is plan 4 task 1's six-state table — MC-1 as amended by §14F F2); `IllegalAssignmentMove`; phase 9 adds `resolve_processed_group(session, assignments, *, row, workspace_id, now, trigger) -> list[WorkspaceEvent]` — `move_assignment` in grouped form for the processed webhook: each assignment's target is `resolved` from `awaiting` and `resolved_early` from `in_queue`/`in_progress` (§14F F5), one guarded statement per row whose delta vector is the per-column sum (`−Σq` on each *from* column), the goal step per assignment (F4), sharing the same statement builder and repair routine |
| `_remove_assignment.py` | `remove_assignment(session, assignment, *, workspace_id, actor_user_id, now, trigger) -> list[WorkspaceEvent]` = `move_assignment(…, ASSIGNMENT_DELETE)` then `recompute_task_stock_flag` |
| `_goal_credit.py` (phase 5) | `current_goal_record_id(session, stock_report_item_id) -> str \| None`; `apply_goal_effect(session, assignment, *, from_state, to_state, trigger, now) -> None` (called inside `move_assignment` after the counter statement) |
| `_repair_records.py` | `write_repair_record(session, *, workspace_id, target_kind, target_client_id, field, stored_value, recomputed_value, trigger, created_by_id, now, delta=None) -> StockReportRepairRecord` (**`delta` added 2026-09-21, batch B1** — keyword-only, passed into the existing `logger.warning`'s `delta=%s` slot, which was unreachable before; intention §5A MC-1 requires the warning to carry the move's delta. Phase 3's three call sites omit it and are behaviourally unchanged) + one `logger.warning` per record (fields: row, field, stored, recomputed, delta, trigger) |
| `_task_flag.py` | `set_task_stock_flag(session, workspace_id, task_id, value, *, require_update=False) -> None` (the MC-15 Core UPDATE with `updated_at = tasks.updated_at`, `is_distinct_from(value)`, and — **added 2026-09-21, batch B1** — `Task.workspace_id == workspace_id`, closing the write half of the tenancy boundary the owner's card-1 ruling closed on the read half. Two call sites thread it: `recompute_task_stock_flag` and `repair_stock_report`'s direct call. The guard itself is untested — re-review note N7); `recompute_task_stock_flag(session, workspace_id, task_id) -> bool` (**amended 2026-09-20**, same owner ruling as `expected_task_flag` in the `consistency.py` row — a ruling that amends one registry row amends its callers in the same act; re-review 2 N-S2 / L-18). |
| `_locks.py` | `acquire_stock_report_order_lock(session, workspace_id)` (`pg_advisory_xact_lock(hashtext('stock_report_order:' \|\| :ws))`); `lock_stock_report_items(session, workspace_id, client_ids) -> dict[str, StockReportItem]`; `lock_stock_task_assignments(session, workspace_id, client_ids) -> dict[str, StockTaskAssignment]`; `lock_items(session, workspace_id, client_ids) -> dict[str, Item]`; `lock_tasks(session, workspace_id, client_ids) -> dict[str, Task]`; `lock_stock_report_history_records(session, workspace_id, client_ids) -> dict[str, StockReportHistoryRecord]` (**added 2026-09-20, batch A fix 1** — §12A's repair lock order requires it after the assignments; see batch A re-review 1 §6) — each one `SELECT … FOR UPDATE ORDER BY client_id` with `populate_existing` |
| `_events.py` | `build_stock_report_item_updated_event(*, client_id, workspace_id, values) -> WorkspaceEvent`; `build_stock_task_assignment_event(kind, *, client_id, workspace_id, stock_report_item_id, task_id, state) -> WorkspaceEvent` (`kind` ∈ `created`, `state-changed`, `deleted`); `coalesce_stock_report_events(events, *, initial_row_values) -> list[WorkspaceEvent]` (phase 8; MC-19 net-change per entity per request; a row that is `:created` **or `:deleted`** in the request gets no `:updated`)  **Batch B1 (2026-09-21):** both builders construct `WorkspaceEvent(event_name=…, client_id=…, workspace_id=…, extra=…)` directly rather than calling `build_workspace_event`, which requires an object carrying `.client_id` while these are registered with a bare `client_id: str`. No shim was introduced. `build_stock_report_item_updated_event` emits `priority.value` (or `None`), never the enum member, per MC-19's payload spec. |
| `_ordering.py` (phase 12) | `close_priority_gap(session, *, workspace_id, priority, removed_order) -> list[RowValues]`; `append_to_priority_group(session, *, workspace_id, priority) -> int`; `shift_within_group(session, *, workspace_id, priority, from_order, to_order) -> list[RowValues]` — each shift one column-referencing statement with `RETURNING` |
| `_category_guard.py` (phase 11) | `assert_item_category_change_allowed(session, *, workspace_id, item_id, current_category_id, incoming_category_id) -> None` |
| `repair_stock_report.py` | `repair_stock_report(ctx) -> dict` → `{"repaired": [...], "not_repaired": [...]}` |
| `create_stock_task_assignments.py` | `create_stock_task_assignments(ctx) -> dict` → `{"stock_task_assignments": [...]}` |
| `delete_stock_task_assignments.py` | `delete_stock_task_assignments(ctx) -> dict` → `{"deleted_client_ids": [...]}` |
| `_delete_stock_report_item_cascade.py` (phase 13) | `cascade_delete_stock_report_item(session, row, *, workspace_id, actor_user_id, now, trigger) -> list[WorkspaceEvent]` — the MC-16 cascade as a subordinate operation (caller holds the advisory lock and the tasks → row+group → assignments locks); `actor_user_id=None` stamps NULL (MC-17). One owner in the tree; **two callers**: `delete_stock_report_item` (13, `trigger="delete_stock_report_item"`) and `process_stock_demand_deleted` (13A, `actor_user_id=None`, `trigger="stock_demand_deleted"`) |
| `delete_stock_report_item.py` | `delete_stock_report_item(ctx) -> dict` → `{"client_id": …}` (locks, then calls the cascade with `trigger="delete_stock_report_item"`) |
| `set_stock_report_item_priority.py` / `set_stock_report_item_priority_order.py` | `…(ctx) -> dict` → `{"stock_report_item": {...}}` |
| `sync_task_stock_assignments.py` | `sync_task_stock_assignments(session, changed: list[tuple[Task, TaskStateEnum]], *, workspace_id, actor_user_id, now) -> list[WorkspaceEvent]` |
| `stock_demand_entries.py` | `DemandEntry` (frozen: `index`, `item_category_raw`, `item_category_key`, `properties_raw`, `properties_normalized`, `properties_signature`, `quantity_requested`); `DemandOutcome`; `StockDemandResult(outcomes, events)`; phase 13A adds `DemandDeleteEntry` (`DemandEntry` without `quantity_requested`) and `DemandDeleteOutcome(index, item_category_raw, properties_raw, outcome)` |
| `_demand_lookup.py` (phase 6) | `resolve_categories_for_entries(session, *, workspace_id, entries) -> dict[str, str \| None]` (MC-8 category resolution over the request's key set, one `SELECT`; key → category `client_id` or `None`); `discover_live_rows_by_identity(session, *, workspace_id, identities) -> dict[tuple[str, str], str]` (the unlocked identity discovery, one `SELECT`, `is_deleted = false`). The one lookup engine both stock webhooks use (§14E E4) |
| `stock_demand_request.py` (phase 7) | `parse_stock_demand_body(raw: bytes) -> list[DemandEntry]` (MC-8 steps 5–7, raises `ValidationError`) |
| `stock_demand_deleted_request.py` (phase 13A) | `parse_stock_demand_deleted_body(raw: bytes) -> list[DemandDeleteEntry]` (the demand rules for `itemCategory` and `properties`, `quantityRequested` ignored as an unknown key, duplicates → 422) |
| `apply_stock_demand.py` | `apply_stock_demand(session, *, workspace_id, entries, now, deadline, timeout_ms) -> StockDemandResult` (the D6 statement plan inside one owner-mode `maybe_begin`; after its sorted lock it asserts every identity was locked — a row soft-deleted between discovery and lock → `RuntimeError`, 500, Scanner retries; plan 6 task 2 step 6) |
| `receive_stock_demand_webhook.py` (phase 7) | `receive_stock_demand_webhook(ctx) -> dict` → `{"results": [...]}` |
| `items_processed_request.py` / `process_items_processed.py` (phase 9) | `parse_items_processed_body(raw: bytes) -> list[str]`; `process_items_processed(ctx) -> dict` → `{"results": [...]}` |
| `process_stock_demand_deleted.py` (phase 13A) | `process_stock_demand_deleted(ctx) -> dict` → `{"results": [...]}`; the owning command of the third webhook: deadline → verify → parse → one owner-mode transaction (`set_config`, workspace, **advisory lock before discovery**, the two `_demand_lookup` statements, id discovery, sorted locks tasks → rows+groups → assignments, then `cascade_delete_stock_report_item(…, actor_user_id=None, trigger="stock_demand_deleted")` per candidate row ascending, deadline check) → coalesced events |
| `requests/__init__.py` | `CreateStockTaskAssignmentsRequest` (`entries: list[StockTaskAssignmentEntry]`, `model_config = ConfigDict(extra="forbid")`, ≥ 1 entry), `StockTaskAssignmentEntry` (`stock_report_item_id`, `task_id`, `item_id`, `override_property_mismatch: bool = False`), `DeleteStockTaskAssignmentsRequest` (`client_ids: list[str]`, ≥ 1), `SetStockReportItemPriorityRequest` (`priority: StockReportPriorityEnum \| None`), `SetStockReportItemPriorityOrderRequest` (`priority_order: int`), `DeleteStockReportItemRequest` — **removed** (**owner ruling 2026-09-21: `client_id` travels in the path, never in the body.** The three item-scoped routes in §6.6 already declare `{client_id}`; the router injects it into `incoming_data` and the request models no longer carry the field. `DELETE` therefore takes **no body at all**, so its request model is dropped. This resolves the §6.5/§6.6 contradiction the endpoint inventory found) and their `parse_*_request` functions |

`bm/services/infra/location_tracker/webhook_verifier.py` (new): `verify_location_tracker_webhook(headers: Mapping[str, str]) -> str`
— MC-8 steps 2–3, returns the configured workspace id, raises `LocationTrackerWebhookAuthError`.

`bm/services/queries/stock_report/`:

| Module | Public names |
|---|---|
| `consistency.py` | `compute_stock_report_divergences(session, workspace_id) -> list[Divergence]` (sorted by `(kind, client_id, field)`); `recompute_row_counters(session, stock_report_item_id) -> dict[str, int]`; `recompute_goal_total(session, history_record_id) -> int`; `expected_task_flag(session, workspace_id, task_id) -> bool` (**amended 2026-09-20 by owner ruling** on batch A re-review 1 card 1: the `workspace_id` filter is restored. The unfiltered shape registered here let the check answer "does *any* assignment in the installation name this task?", so a cross-workspace assignment row would make W's board report — and `repair_stock_report` write — a task flag it does not own. A tenancy boundary that holds only while every other file stays correct fails silently and late); `Divergence` TypedDict `{"kind", "client_id", "field", "stored", "expected"}` |
| `get_stock_report_consistency.py` | `get_stock_report_consistency(ctx) -> dict` → `{"workspace_id", "checked_at", "divergences"}` |
| `list_stock_report_items.py` | `list_stock_report_items(ctx) -> dict` → `{"stock_report_items": [...]}` (unpaginated, §5) |
| `list_stock_task_assignments.py` | `list_stock_task_assignments(ctx) -> dict` → `{"stock_task_assignments": [...]}` |

Divergence conventions (fixing what MC-20 leaves to the planner): `order_density` emits one
divergence **per row** whose order differs from the dense renumbering of its group (`client_id` =
the row, `field` = `priority_order`, `stored` = current, `expected` = dense value);
`priority_order_nullness` emits one per offending row (`field` = `priority_order`; priority set and
order null → `expected` = `max(group) + 1`; priority null and order set → `expected` = `NULL`);
`task_flag` `field` = `is_stock_assignment`, values as `"true"`/`"false"`; `signature` `field` =
`properties_signature`, `stored` = the column, `expected` = `compute_stock_criteria_signature(properties)`.

Reset phases (`bm/services/commands/reset/phases/`): `delete_stock_report_repair_records.py`,
`delete_stock_task_assignments.py`, `delete_stock_report_history_records.py`,
`delete_stock_report_items.py`, called **in that order as the first four phases** of `reset_app`,
before `delete_task_events`.

### 6.6 Routers

`bm/routers/api_v1/stock_report.py`, mounted at prefix `/api/v1/stock-report`, tag `stock-report`;
`bm/routers/api_v1/location_tracker_webhooks.py`, mounted at prefix `/api/v1/location-tracker`,
tag `location-tracker-webhooks` (the existing `location_tracker.router` keeps its own mount).

| Method + path | Service | Roles (`require_roles`) | Phase |
|---|---|---|---|
| `GET /api/v1/stock-report/consistency` | `get_stock_report_consistency` | ADMIN, MANAGER | 3 |
| `POST /api/v1/stock-report/repair` | `repair_stock_report` | ADMIN, MANAGER | 3 |
| `POST /api/v1/location-tracker/webhooks/stock-demand` | `receive_stock_demand_webhook` | key (`x-api-key`) | 7 |
| `POST /api/v1/stock-report/assignments` | `create_stock_task_assignments` | ADMIN, MANAGER, WORKER | 8 |
| `POST /api/v1/stock-report/assignments/delete` | `delete_stock_task_assignments` | ADMIN, MANAGER, WORKER | 8 |
| `POST /api/v1/location-tracker/webhooks/items-processed` | `process_items_processed` | key | 9 |
| `POST /api/v1/location-tracker/webhooks/stock-demand-deleted` | `process_stock_demand_deleted` | key | 13A |
| `GET /api/v1/stock-report/items?priority=high,medium,low` | `list_stock_report_items` | ADMIN, MANAGER, WORKER, SELLER | 12 |
| `PATCH /api/v1/stock-report/items/{client_id}/priority` | `set_stock_report_item_priority` | ADMIN, MANAGER, SELLER | 12 |
| `PATCH /api/v1/stock-report/items/{client_id}/priority-order` | `set_stock_report_item_priority_order` | ADMIN, MANAGER, SELLER | 12 |
| `DELETE /api/v1/stock-report/items/{client_id}` | `delete_stock_report_item` | ADMIN, MANAGER | 13 |
| `GET /api/v1/stock-report/items/{client_id}/assignments` | `list_stock_task_assignments` | ADMIN, MANAGER, WORKER, SELLER | 13 |

The three webhook routes take `Request`, read `await request.body()`, and build
`ServiceContext(identity={}, incoming_data={"raw_body": raw, "headers": dict(request.headers)}, session=session)`
exactly as `bm/routers/api_v1/connecteam_webhooks.py` does. The two structured assignment errors
are rendered explicitly in the router as `{"error", "ok": false, "code", "details"}` (the
`routers/api_v1/auth.py:125` precedent); everything else goes through `build_err`.

### 6.7 Events (intention §9B/MC-19)

`stock_report_item:created` (`extra` `{}`), `stock_report_item:updated` (`extra` = the six fields
`quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting`,
`priority`, `priority_order`, from `RETURNING`/refreshed values), `stock_report_item:deleted`
(`{}`), `stock_task_assignment:created` / `:state-changed` / `:deleted` (`extra`
`{"stock_report_item_id", "task_id", "state"}`). `workspace_id` on every event comes from the
entity's row, never from `ctx`.

### 6.8 Tests

| Location | Content |
|---|---|
| `app/tests/helpers/stock_report.py` (phase 1, extended in phase 3) | `SeededWorkspace` dataclass; `seed_stock_report_workspace(session, *, suffix=None) -> SeededWorkspace` (workspace, manager user, worker user, two categories "Dining Chairs"/"Coffee Tables", item `quantity=4` with `article_number = f"SR-{suffix}"`, task `pending` with the PRIMARY `TaskItem`; flushed, not committed); `purge_stock_report_workspace(session, workspace_id)` (raw `DELETE`s in FK order over every table the phases write, then the workspace and its users); `make_ctx(session, seeded, *, role_name="manager", user=None, incoming_data=None, query_params=None) -> ServiceContext`; `capture_dispatch(monkeypatch, import_site: str) -> list` (monkeypatches `event_bus.dispatch` at the named consumer module); phase 3 adds `assert_stock_report_clean(session, workspace_id)` (check `== []` **and** zero repair records for that workspace — one helper, never split) |
| `app/tests/helpers/statement_listener.py` (phase 3) | `record_statements()` async context manager attaching `before_cursor_execute` on the engine's `sync_engine`, yielding the list; `count_writes(statements, tables: set[str]) -> int` (INSERT/UPDATE/DELETE whose target table is in the set) — precedent `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py:470-487`  **Added 2026-09-21 (batch B2):** `record_statement_calls(session)`, an `asynccontextmanager` yielding `list[tuple[str, Any]]` of `(statement, parameters)` from the same `before_cursor_execute` hook. It exists because `record_statements` discards parameters and a parameterized value never appears in the statement text (SQLAlchemy compiles the bind to `$1`), which made plan 6 C7(a) unmeasurable. `record_statements` and `count_writes` are byte-identical, so batch A's caller is unaffected.  Use it whenever a criterion asserts a **bound value**: the compiled text carries `$1`/`$2`, never the value. |
| `app/tests/unit/domain/stock_report/` | pure-function tests (phases 1, 2), incl. `test_assignment_state_enum.py` (the active/terminal partition) |
| `app/tests/unit/services/commands/stock_report/test_stock_demand_deleted_request.py`, `app/tests/integration/services/commands/stock_report/test_process_stock_demand_deleted.py`, `test_process_stock_demand_deleted_locks.py` | phase 13A |
| `app/tests/integration/models/stock_report/` | schema and migration parity (phase 1) |
| `app/tests/integration/services/commands/stock_report/`, `app/tests/integration/services/queries/stock_report/` | command/query tests, one file per subject named in each plan |
| `app/tests/unit/routers/api_v1/test_stock_report_router.py`, `test_location_tracker_webhooks_router.py` | role cells and router wiring (`TestClient` + `dependency_overrides[get_jwt_claims]` + faked `run_service`, precedent `app/tests/unit/routers/api_v1/test_item_economics_router.py:60-115`) |
| `app/tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py` + `task_state_write_site_registry.py` (phase 10) | the MC-2 AST guard and its checked-in registry |

Standard fixture shorthand used in every plan's criteria tables, **F0**: `seed_stock_report_workspace`
→ workspace **W**, manager **U**, category **K** (Dining Chairs, `seat`), item **I** (`quantity 4`,
`properties {"wood_type": "Teak", "upholstery": "Down"}`), task **T** (`pending`, PRIMARY = I), row **R**
(identity K + `{"wood_group": ["teak"]}`, `quantity_requested 10`) with goal record **G** (awaiting 0),
assignment **A** on (R, T, I) in the stated state. Before phase 8, A and R are inserted as ORM
instances (charter rule 3: production types); from phase 8 on, through `create_stock_task_assignments`.
Every row also seeds a **foreign workspace** with the same shapes and asserts it is untouched.

### 6.9 Documents (phase 14)

`docs/domains/stock_report/api.md`, `docs/domains/stock_report/states.md` (cascade strategy per
25_soft_delete; the six-state machine), `docs/handoff/to_frontend/STOCK_REPORT_API_v1_<YYYYMMDD>.md`.
The Scanner v1 and v2 files are not edited; nothing is owed to Scanner at closeout (intention §18, the
2026-09-19 entries — the v2 file already carries §4A and the `early` reason).

## 7. Sequencing and gates

### 7.1 Departure from the owner's suggested phasing (6 → 14), with reasons

The owner's six phases were split by contract so that no phase exceeds the charter's target of
eight criteria and every phase can close green on its own:

| Owner's phase | Planned phases | Reason for the split |
|---|---|---|
| 1 Foundation | **1** schema/normalization, **2** matcher | The matcher alone carries 75 externally-derived rows (rule 17, projection mandatory); the schema phase is DB-bound. Mixing them would put a pure-function projection on the critical path of the migration |
| 2 Core engine | **3** check + repair, **4** transition operation, **5** goal credit | The self-heal inside `move_assignment` *calls* the recomputation, so the recomputation and the shared clean helper must exist first (3). MC-1 and MC-5 are two contracts with 49 and 17 rows; the goal step is an additive extension of the move (4 ships moves with no goal record present; 5 adds the goal statement after the counter statement) |
| 3 Demand webhook | **6** service, **7** endpoint | 35 + 52 rows; the service (set-based statements, two-session rows, the 5 s budget) is complex and the endpoint (validation tables) is not — different Codex model, different projection depth |
| 4 Assignments + processed | **8** assignments, **9** processed | Two surfaces, 58 + 33 rows; 9 also reuses 7's verifier |
| 5 Sync + hooks + guards | **10** sync, **11** hooks + guards | The owner allowed this split; it is taken because the rows came out at 30 + 26, and MC-11 (two writers) needs the processed webhook (9) before the sync |
| 6 Ordering + row delete + endpoints | **12** ordering + list, **13** row deletion + assignment reads, **13A** Scanner delete webhook (round 8), **14** docs | 45 + 19 rows; the consistency/repair endpoints moved **up** to 3 because the tests of every later phase use the repair command, and role cells ship with their operation's phase (owner's own rule). The GET endpoints, absent from the suggestion, are placed with the ordering (rows) and the row cascade (assignments). 13A is the cascade's second caller (§14E E5) and lands directly after 13, where §14E suggested |

### 7.2 Dependency graph, projection requirement, default order

| Phase | Depends on (APPROVED) | Projection | Why the dependency |
|---|---|---|---|
| 1 | — | mandatory (schema predicates are silent-failure) | — |
| 2 | 1 | **mandatory, not waivable** (rule 17) | package and enums from 1 |
| 3 | 1 | mandatory | tables |
| 4 | 3 | mandatory | recomputation, repair records, flag writer, clean helper |
| 5 | 4 | mandatory | `move_assignment` |
| 6 | 3 | **mandatory, not waivable** (rule 17: asyncpg/SQLAlchemy shapes) | clean helper, tables, normalization; does **not** need 4 or 5 |
| 7 | 6 | **mandatory, not waivable** (rule 17: Starlette/JSON shapes) | the service |
| 8 | 2, 5 | mandatory | matcher; moves with goal credit |
| 9 | 7, 8 | **mandatory, not waivable** (rule 17) | verifier from 7; assignments created through 8 |
| 10 | 9 | mandatory | MC-11 needs the processed webhook |
| 11 | 8 | mandatory | assignments through the command |
| 12 | 5 | mandatory | counters unaffected; needs rows and the repair renumber semantics from 3 |
| 13 | 12, 8 | mandatory | gap closing from 12; assignments from 8 |
| 13A | 13, 9 | **mandatory, not waivable** (the owner waived the §14E inventory re-check — the six carried questions are checked at projection; rule 17: Postgres lock re-evaluation and deadlock shapes) | the cascade from 13; the verifier and parser shape from 7 and the owning-transaction shape from 9 (9 brings 7 and 8); `_demand_lookup.py` from 6 |
| 14 | 13A, 11, 10 | waivable | every route, state and event exists (13A implies 13, 9, 7) |

Default linear order is the numbering, with 13A between 13 and 14. Parallel branches exist (6–7
beside 8; 12 beside 10–11) but in orchestrated mode one implementer runs at a time; the
coordinator may reorder inside the graph and records the reason in the tracker. Plans 11 and 13
reach `resolved_early` in fixtures with `PR` (phase 9) when 9 is APPROVED before them (the default
order) and with phase 4's `move_assignment` otherwise; each plan says so.

**Since §3A:** "Depends on (APPROVED)" reads per §3A's dependency rule (earlier batch APPROVED, or
same-batch phase IMPLEMENTED earlier in the session), and the projection column is an instruction
to the orchestrator's batch projection, not a separate session.

### 7.3 Gates

> Since §3A: projection, review and approval gates apply **per batch**; the intention gate and
> the L4-with-baseline-diff stamp are unchanged.

- **Intention gate:** every session's gate check reads `status: RATIFIED` in
  `planning/intention.md` and stops on anything else.
- **Projection (round 0):** per §7.2; the implementer prompt compiles only after the projection
  ledger is fully routed.
- **Review:** first review full checklist; re-review delta-scoped with verified perimeter; the
  owner has ruled (2026-09-19) that a second fix round on one phase is not automatic — the
  coordinator stops and relays each finding for a ruling.
- **Approval:** L4 stamp on the handed-over tree with the failure-ID set diffed against §10's
  baseline; the tracker row and the gate commit; closeout ritual moves the phase's rows to
  `archive/plan_<n>/`.

### 7.4 The round-8/9 planning delta (2026-09-19) — record

The plan set was written (planning-0) against the round-7 intention; while it was written the
owner added §14E (round 8) and §14F (round 9) and re-ratified both the same day (`c231dfb`). The
gate that this section previously recorded as re-opened is **closed**; the planning delta
(planning-1) folded both rounds without a rewrite:

1. **Round 8 → phase 13A** (`plans/plan_13A.md`), after 13 and depending on 13 and 9, the cascade's
   second caller. The owner waived the mechanism-inventory re-check of §14E; the six carried
   questions are answered as stated rules with rows in plan 13A §7 (Q1 also in plan 6 C5(c)), and
   13A's projection is mandatory and not waivable.
2. **Round 9 → the sixth state `resolved_early`**: phases 1 (enum, partition), 4 (six-state
   table), 5 (goal credit F4), 8 (refusal F9), 9 (F5 order, `early` reason, per-column grouped
   delta), 10 (sync skip F3, MC-11 rows F6) — the owner's list — plus 3 (the check never counts
   it), 11 (the category guard reads the active frozenset), 13 (cascade fixture, assignment read),
   14 (docs), found by searching the set.
3. Skeleton consequences recorded in §6: `_demand_lookup.py` (one lookup engine for both stock
   webhooks, E4), the demand path's locked-set assertion (a row soft-deleted between discovery and
   lock — a gap the round-7 set did not cover for the user delete either), the coalescer's
   `:deleted` clause, `resolve_processed_group` (renamed from the round-7 `resolve_awaiting_group`
   because it now resolves from three states), and §9 rule 16.
4. Untouched by the delta, by the delta prompt's instruction: card 1 and §10.1–§10.2; plan 3 C2(a),
   plan 6 C7(a), plan 9 C7(a)'s statement-count clause, plan 13 C4(c), plan 10's registry guard.
5. **Owner rulings after the delta (2026-09-19, orchestrator fold):** card 1 → **A** (fix none of the
   21; baseline stays 21). Outcomes, not internals: plan 13 C4(c) **removed** (615 rows); plan 9
   C7(a) and C7(d) lose the "exactly one `UPDATE`" clause (outcomes and new mutations kept); plan 3
   C2(a) asserts the data unchanged instead of counting writes; plan 6 C7(a) and plan 10's registry
   guard **kept** as written. The demand locked-set 500 (plan 6 C5(c)) stays a plan-level mechanism;
   the intention is not amended.

## 8. Tool protocols

- **Architecture graph** (`.archgraph/`, archgraph MCP): every session orients at start
  (`archgraph_status`, `archgraph_search_nodes("stock report")` — 0 nodes at planning time,
  revision `fa1c510e…`) and the implementer records the phase delta at end as **one batched
  `apply_changes`** with evidence anchored on symbols, never counts in summaries (evidence
  summaries are immutable). Nobody promotes, rejects or edits review items; the owner adjudicates.
  Node naming for this capability: `capability-stock-report`, one `command-*`/`query-*`/`model-*`
  node per registered module in §6, edges `calls`/`writes`/`reads`. Discrepancies found in existing
  nodes (`helper-task-state-transitions` already has two known ones, inventory handoff §9) are filed
  through `archgraph-discrepancies`, not fixed in passing.
- **Git:** checkpoint commit at every `IMPLEMENTED`; approval commit at every `APPROVED`; no push,
  no squash, no history rewrite by any role session. Since §3A: checkpoints may be per phase inside a
  batch; the approval commit is per batch.
- **Graph delta since §3A:** one batched `apply_changes` per batch implementation (not per phase),
  made by Codex at the batch end; fix rounds add a delta only for what they change.
- **Owner's standing anchor-observation brief:** not a session obligation; the owner maintains it.

## 9. Standing rules

Charter rules 1–17 apply in full. Project-specific rules, each binding on every phase:

1. **Every test is workspace-scoped.** Each test seeds its own workspace through the phase-1 kit,
   scopes every query and assertion to it, asserts no global total, and holds with foreign rows
   present (measured 2026-09-19: 819 rows in 37 tables leak within a run from 23 files, incl.
   `item_categories`, `items`, `execution_tasks`, task/step tables). Tests that commit purge in a
   `try/finally` via `purge_stock_report_workspace` (charter rule 11½).
2. **Every scenario that plants no drift ends with `assert_stock_report_clean`** (from phase 3 on):
   check `[]` **and** zero repair records for the workspace, one helper. A scenario that passes
   only because it self-healed is a failure (intention §12A (e)).
3. **Counters, flags and goal totals are written by Core statements only** — column-referencing
   `UPDATE … RETURNING`; never an ORM attribute assignment. An ORM instance is stale after any
   Core UPDATE of the same row in the same transaction; event payloads and `stored_before` come
   from `RETURNING` or a fresh `SELECT` (MC-1). Planting an ORM write is a named mutation in
   phases 3, 4 and 13.
4. **Lock order is MC-1's, everywhere**: advisory (ordering ops only) → items → tasks →
   `stock_report_items` → `stock_task_assignments` → history; ascending `client_id` within a
   class; re-read `state`/`is_deleted` after the lock and decide on that. An unlocked read only
   discovers ids.
5. **`ctx.workspace_id` is never read on a webhook path** (it is `""`); the workspace is the
   configured setting, passed explicitly to every subordinate. Webhook tests build
   `ServiceContext(identity={})` exactly as the router does.
6. **Events**: built after the transaction block exits normally, from committed values;
   dispatched once per request by the owning command; subordinate operations return them. Tests
   capture them with `capture_dispatch` at the consumer's import site and assert the list — never
   an internal call.
7. **Statement counting is reserved for the ratified bounds** (MC-9 zero-write replay, D6 counts,
   MC-20 read-only, the image batch bound, and — **fifth use, owner card A, 2026-09-21** — a
   *refused-before-the-write* clause where a database constraint would otherwise reproduce the
   refusal's whole observable, as in plan 8 C1(j)/C1(k)) and always through `record_statements`.
   It is never used to assert query text or internal structure.
8. **Named mutations name file and definition-vs-call-site; the row is run whole-file, never
   `-k`;** a mutation's observed-red set is recorded across the suite when the symbol is
   asserted in more than one file (earned three pipelines running).
   A mutation ledger is scoped to a **test id**, never to a mutant: a test that moves re-runs its
   mutations at the new surface, and a cell shared between two rows must be shown to reach the
   **second** row's distinguishing assertion before one run may discharge both. "The dependency's
   own suite covers it" and "it is the same code edit" are claims to be measured in this round,
   never substitutes for a run. (Folds §9A lessons L-21, L-23 and L-28, which are one
   proposition-conflation defect at three levels.)
9. **Two-session rows** open the second session with `beyo_manager.models.database.get_db_session()`,
   synchronise with `asyncio.Event`/`asyncio.Barrier`, bound every wait with `asyncio.wait_for`,
   and always release and purge (precedent
   `app/tests/integration/services/commands/item_economics/test_phase7_concurrency.py`). A row
   whose interleaving cannot be forced says so in its plan cell and names the structural check the
   reviewer performs instead of pretending the row bites.
10. **Exactly one test in the whole project sleeps past the 5 s default** (MC-9 instrument (ii),
    phase 6). Every other timing row uses the patched clock or a held lock with a bounded wait.
11. **Before writing under `docs/handoff/` or `docs/domains/`, run `pytest tests/unit/docs/`**
    (1.3 s) — those guards have roots wider than any phase perimeter.
12. **Schema is fixed in phase 1.** No later phase edits the revision; a later schema need is a
    follow-up revision and a Review-log entry.
13. **No new `onupdate=`** on any table this project creates (MC-17); the flag flip on `tasks`
    uses the self-assigning form (MC-15).
14. **Scanner-owned shapes are cited, not invented** (rule 17): every matcher fixture cites the
    `file:symbol` in intention MC-12 or the hand-walk row in the inventory handoff §3; every
    asyncpg/SQLAlchemy shape cites the re-check handoff §2 measurements.
15. **The frontend contract is written from the shipped router and serializers**, never from the
    intention's examples; nullability gets its own row (earned `simple_valuation_editor` phase 4).
16. **Active and terminal are the two frozensets, never a spelled list.** Every query predicate,
    branch and recomputation that asks "is this assignment active / terminal" reads
    `ACTIVE_ASSIGNMENT_STATES` / `TERMINAL_ASSIGNMENT_STATES` (§6.1); a literal `state IN ('resolved',
    'failed')` or `NOT IN (...)` is a review finding. Earned 2026-09-19: round 9 added a sixth
    member after ten phases were planned, and every hand-typed terminal list would have counted
    `resolved_early` as active. Plans 3, 9, 11, 13 carry a row whose named mutation is exactly that
    list. (The DB partial indexes are the one place a literal list stands — as an *inclusion* list of
    the three active states, fixed in the phase-1 migration.)

17. **Relocating a row's test to a narrower surface is a criterion change, and criterion changes
    are the owner's.** Moving a row's evidence from the boundary its outcome names to a cheaper
    one — a command row proven at its parser, an endpoint row proven at a helper — changes what
    the row claims even when the assertion text is identical. An implementer or tester that
    judges a relocation necessary declares it and stops; the owner authorizes it, and the plan's
    cell is amended in the same act. Earned: batch B2 review 1 B1/S1 (four rows proven at parser
    scope) and batch B2 card 1 (plan 8 C4(m)'s one-file relocation, which the owner did
    authorize). (§9A lesson L-20.)
18. **Every phase pins the public signatures it registers.** A phase that adds a name to §6.5 or
    §6.1 is complete only when some row in its own plan asserts that name's shape at its own
    boundary — arity, the keys of what it returns, and the error it raises. A signature registered
    but unpinned is how a plan cites a contract that never shipped. Earned: §9A lesson L-8,
    explicitly unimplemented across ten phases and already the cause of batch B projection blocker
    B1 (`StockDemandOutcomeEnum` was cited by two plans and existed in neither). Adopted as one
    standing rule rather than one criterion row per phase (orchestrator, 2026-09-21).
19. **Every new test file gets a name unique across the whole test tree.** This repo's test
    packages carry no `__init__.py`, so pytest's rootdir import mode uses the **bare filename**
    as the module name: two `test_serializers.py` under different subpackages are a *collection
    error*, and the second one silently never runs. An L1 or L2 run of the new file alone can
    never catch this — only a full-suite collection can, and this project takes exactly one L4
    per cycle. Prefix the domain: `test_stock_report_serializers.py`, not `test_serializers.py`.
    Earned batch C1: a new phase-8 unit file collided with `tests/unit/domain/shopify/
    test_serializers.py` and was caught only because the implementer re-ran the whole suite.


**The demand statement budget, measured 2026-09-21 (batch B2 review 1).** Exact counts, not bounds:
all-new **8**, all-changed **7**, all-unchanged **5**, one-unknown-category **8**. Verified by
inserting exactly one stray `SELECT` inside `apply_stock_demand`'s transaction block: plan 6 C6(a),
C6(c) and C6(d) redden, C6(b) does not. A later phase that adds a statement to this path must move
these numbers deliberately.

## 9A. Reviewer lesson register (owner, 2026-09-21) — the batch C/D fold worklist

Consolidated from the seven reviewer handoffs of batches A, B1 and B2. **Batch B1's re-review
restarted its numbering at L-1 and collided with batch A's L-1…L-4; those four are renumbered
L-27…L-30 here, and no id is ever reused.** One lesson was unnumbered prose in the B1 review; it is
L-31. Verbatim texts stay in their source handoffs — this table is the worklist, not the archive.

**The finding that matters most: plans 8–13A have never received a lesson fold.** `git log` on those
files shows only `67dd815` (the original plan set) and `ff05bb3` (owner card 1). Every lesson from
four review rounds is unlanded there, and the concrete debt is **94 criterion rows carrying an empty
(`—`) mutation cell** — plan 8: 26, plan 9: 18, plan 10: 15, plan 11: 8, plan 12: 16, plan 13: 6,
plan 13A: 5.

**Batch C1 fold executed, 2026-09-21 (plans 8 and 11).** Order followed as prescribed: L-20
first (→ §9 rule 17, then plan 8 §7), L-17's preamble half second (→ both §6 preambles; its
outcome half found **no** arithmetic defect — the one candidate, plan 8 C4(k)'s `(8,0,0)`, is
correct once the second item is specified as a copy of I, which is a fixture fold), then L-9,
L-10, L-12, L-13, L-15, L-16, L-21, L-23, L-24, L-25, L-28, L-30. **32 mutation cells and 8
fixture cells folded across the two plans**; 2 cells left deliberately blank with a labelled
reason (plan 8 C3(d) class 2, plan 11 C5(b) class 3 known-unarmed). Owner-only lessons were not
folded: L-29 became card C and is now applied; L-5 was checked and recorded as **not blocked**
(`ValidationError` 422 is unambiguous in this repo — pydantic's own escaping a command reaches
`run_service`'s generic handler and becomes a 500, so only `bm.errors.validation.ValidationError`
can produce 422); L-2 resolved into §4's count note; L-17's outcome half found nothing. Six owner
cards were raised and all six ruled the same day.

**Fold order is not free.** L-20 lands **first** (it defines which cells an agent may touch), then
L-17 (the projection called its batch-B instance "the single most important item"; plans 12/13/13A
seed rows by ORM and raw SQL under the same `assert_stock_report_clean` obligation and carry no
preamble clause), then the rest.

| Id | Rule, in one line | Status | Fold targets | Cell type |
|---|---|---|---|---|
| L-1 | Charter rule 2's "enumerate, never sample" binds the *value table*, not only ordered rules | OPEN | 9, 12 | **OUTCOME (owner)** |
| L-2 | The count and the enumeration must be derived from one another | OPEN | 8, 12, 13, §4 totals | **OUTCOME (owner)** |
| L-3 | Task text must not contradict its own criterion | OPEN | 9, 12, 13A | **TASK (owner)** |
| L-4 | Provision the contracts the plan cites | **APPLIED** (§6.5 `lock_stock_report_history_records`) | — | — |
| L-5 | A row whose outcome is an error identity must pin the identity | OPEN (partly folded into 4, 6) | 8, 12, 13, 13A | **OUTCOME (owner)** + fixture |
| L-6 | A plan must not require a file the repo's convention forbids | **APPLIED** (no forward target) | — | — |
| L-7 | A fixture must make its own predicate the only reason the outcome holds | OPEN | **12** (`high = A1 B2 C3` is dense), 13, 13A | FIXTURE |
| L-8 | Pin each phase's registered public signatures with a criterion | **APPLIED** (§9 **rule 18**, 2026-09-21 — adopted as one standing rule, not one row per phase) | — | — |
| L-9 | Rule-17 rows carry the *rule* next to the literal | OPEN (folded into 4–7) | 8, 9, 13A | NOTE + mutation |
| L-10 | Say "equivalent mutant"; do not name a defect that cannot exist | OPEN | **all of 8–13A — the 94 `—` cells** | MUTATION |
| L-11 | A mutation against a dependency's comparison engine must be grounded in what that engine compares | OPEN | **10** (the AST registry guard C4(a)–(g)), 13A | MUTATION |
| L-12 | One mutation per sub-check | OPEN (folded into 4, 5, 7) | 8, 9, 10, 12, 13, 13A | MUTATION |
| L-13 | Inverse directions of one write each need their own assertion | OPEN | 10, 11, 13 | MUTATION / outcome |
| L-14 | At least one fixture must order rows against their ordering key | OPEN | **12** (the dedicated ordering phase, ascending-only), 13, 13A | FIXTURE |
| L-15 | `sorted()` over a `set` is not deterministically mutation-testable (needs ≥3 elements, or the assertion is the guard) | OPEN | 8, 9, 10, 13, 13A | FIXTURE + mutation |
| L-16 | A tenancy row needs a *cross-workspace reference* fixture, not a foreign-only one | OPEN (folded into 4, 5, 6) | 8, 12, 13, 13A | FIXTURE |
| L-17 | A row's exact outcome is computed from its own fixture, side effects included | OPEN — **highest yield** | §6 preambles of **8, 9, 10, 11, 12, 13, 13A** | FIXTURE preamble + **outcome (owner)** where an outcome is arithmetically wrong |
| L-18 | A ruling that amends one registry row amends its callers in the same act | **APPLIED** (both instances) | residual: not a §9 standing rule | NOTE |
| L-19 | A mutation whose bite depends on a preamble condition repeats that condition in the cell | OPEN | 9, 10, 13A | MUTATION |
| L-20 | **Relocating a row's test to a narrower surface is a criterion change, and criterion changes are the owner's** | **APPLIED** (§9 **rule 17** + plan 8 §7, 2026-09-21; landed first as planned) | residual: 12, 13 at their folds | NOTE (authority boundary) |
| L-21 | "The dependency's own suite covers it" never discharges a mutation cell | **APPLIED** (§9 rule 8 amended 2026-09-21, the three-lesson cluster folded as one) | residual: 9, 13A cells | NOTE + mutation |
| L-22 | Bound the shape you derived — no `≤` on a derived count | OPEN (the §9 statement budget landed; the cells did not) | **13A C5(d) `≤ 7`**, audit 9, 12 | **OUTCOME (owner)** |
| L-23 | A mutation ledger is scoped to a **test id**, never to a mutant — a test that moves re-runs its mutations at the new surface | **APPLIED** (§9 rule 8, same act) | residual: 12, 13 | NOTE |
| L-24 | A bidirectional invariant needs one mutation per direction | OPEN | 13A C1/C2, 8 C3, 11 C6 | MUTATION |
| L-25 | Name the arming *site*, and verify it is the site the row depends on | OPEN (residual — §6.1b landed, the verification clause did not) | §9 rule 8; 10, 11 (foreign sites) | NOTE + mutation |
| L-26 | An absence instrument deserves one positive observation per project | OPEN | §9 rule 7; 9, 10, 12, 13A | NOTE + mutation |
| L-27 | Route a declined mutation to the reviewer in the same round, not to a fold | OPEN | §3A / fix-prompt template | NOTE (process) |
| L-28 | "Same code edit" is a claim to be measured, not asserted | **APPLIED** (§9 rule 8, same act; every shared cell in 8 and 11 now says "both runs recorded") | residual: 9, 10, 12, 13, 13A | NOTE + mutation |
| L-29 | A fixture that models an environment cannot fail — write the premise as a criterion on the caller | **APPLIED for 8** (owner card C, 2026-09-21 → plan 8 **C5(b)**, forceable form with a recorded `UNFORCEABLE` fallback) | residual: 13 | **OUTCOME (owner)** |
| L-30 | Where a plan offers a choice of fixture, the criterion names the choice that keeps the row armed | OPEN | 8, 12, 13 | FIXTURE |
| L-31 | A fold that replaces a vague mutation with a precise site must verify the site executes under the row's own fixture | OPEN as a standing rule (honoured once, in batch B2) | the fold protocol itself | NOTE (process) |

**Clusters — fold as one pass, not one at a time.**
- **L-21 + L-23 + L-28** are one proposition-conflation defect at three levels. One §9 rule 8
  amendment: *a mutation ledger is scoped to a test id; a shared or mirrored cell must be shown to
  reach the second row's distinguishing assertion.*
- **L-10 / L-11 / L-19 / L-25 / L-30** are one family — "the named mutation cannot fail", by five
  different causes. One pass over the 94 `—` cells, not five.
- **L-16 ⊂ L-12** (tenancy instance of one-mutation-per-sub-check) but they fix different cells.
- **L-24 ≠ L-13**: L-13 is one *assertion* per direction, L-24 one *mutant of opposite sign*.

**Authority split.** Owner-only (OUTCOME or TASK cells): **L-1, L-2, L-3, L-5, L-8, L-17's outcome
half, L-22, L-29** — a projection agent must not fold these. Foldable (mutation/fixture cells):
**L-7, L-9, L-10, L-11, L-12, L-13, L-14, L-15, L-16, L-17's preamble half, L-19, L-24, L-28, L-30.**
Process/NOTE only: **L-18, L-20, L-21, L-23, L-25, L-26, L-27, L-31.**

## 9B. Owner API rulings, 2026-09-21

Both resolve contradictions the endpoint inventory found, and both are frontend-visible.

1. **`client_id` travels in the path, never in the body**, on `PATCH …/items/{client_id}/priority`,
   `PATCH …/items/{client_id}/priority-order` and `DELETE …/items/{client_id}`. The router injects
   the path param into `incoming_data`; the request models drop the field; `DeleteStockReportItemRequest`
   is removed entirely because `DELETE` now takes **no body**. §6.5 amended.
2. **`POST /stock-report/assignments` returns the full read shape** — `serialize_stock_task_assignment`,
   fourteen keys with nested `item` and `task`, identical to `GET /items/{client_id}/assignments`.
   This moves the three serializers from phase 13 into **phase 8**, and phase 8's command must load
   each assignment's item (with images) and task. Plan 8 §5 task 2 amended; its criterion rows that
   name the old seven-key shape are superseded and re-stated at the batch C fold.

## 10. Environment topology (verified 2026-09-19 by the planner; if reality disagrees, update here)

**`client_id` order is not creation order (measured, 2026-09-21).** `IdentityMixin` mints
`f"{prefix}_{ULID()}"` (`bm/models/base/identity.py:11`); `python-ulid` 3.0.0 fills the 80-bit
randomness with `os.urandom` and keeps **no monotonic counter** (`ulid/__init__.py:120`). Two ids
minted in the same millisecond therefore have random relative order — measured by the
orchestrator over 2000 ids minted in a tight loop: **977 of 1999 consecutive pairs sorted out of
order**, i.e. a coin flip. No fixture may assume the first row created sorts first; a criterion
asserting an ascending-`client_id` or ascending-`item_id` order binds its labels by **sorting the
real ids at runtime**. (Charter rule 17 — the shape is owned by a dependency. Folded into plan 8
C4(k) and C6(h); every `ascending client_id` claim in §6.5 should be re-read against it.)

- **Working directory** `backend/app/`; virtualenv `app/.venv` (activate, or prefix commands with
  `.venv/bin/`). Installed: SQLAlchemy 2.0.40, asyncpg 0.30.0 (the re-check's timeout shapes were
  measured on exactly these).
- **Infra:** Postgres 18.6 at `localhost:5433`, Redis at `localhost:6380` (from `app/.env`; the
  compose file maps `${POSTGRES_PORT:-5432}` / `${REDIS_PORT:-6379}`, the owner's env sets 5433/6380).
  `DATABASE_URL` and `REDIS_URL` in `app/.env`; the dev database is `beyo_manager` and is **never**
  a test target.
- **Tests:** `PYTHONPATH=. pytest -m 'not e2e'` from `app/` (= `make test`). `pytest.ini` adds
  `-n 6 --dist loadfile --strict-markers`. Each xdist worker gets `beyo_test_main_gwN`, cloned from
  `beyo_test_main_template` (built at the Alembic head by `tests/database_isolation.py`) and dropped
  at the end; the dev DB's row counts are asserted unchanged across the run. Markers: `unit`,
  `integration`, `e2e`.
  - **L1:** `PYTHONPATH=. pytest <file>` (whole file, never `-k`). **L2:** the phase's test folders
    plus the folders of every production module the phase edits (`tests/integration/services/commands/tasks`,
    `…/task_steps`, `…/items` for phases 10–11). **L3:** `tests/integration`. **L4:** the full command
    above; ~2–3 minutes; exactly one per cycle close plus gates.
- **Alembic head:** `ce99896e6f49` (`app/migrations/versions/ce99896e6f49_add_completed_at_to_tasks.py`),
  single head as `ScriptDirectory.get_heads()` reports it. Phase 1 adds the one revision of this
  project on top of it. Autogenerate: `cd app && alembic revision --autogenerate -m "create_stock_report_tables"`,
  then review the file against §6.2 (partial-index `postgresql_where`, `server_default`, enum names,
  checks) — autogenerate does not always emit partial-index predicates or CHECK constraints; add them
  by hand inside the generated file if missing, and say so in the handoff.
- **Baseline: 21 failed / 3103 passed / 1 skipped, collection 3125, at `cce4b1b`** (unchanged at
  `f575488`, which touched only docs). The failing set is exactly the published 21-ID set in
  `docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3.
  Every L4 run diffs its failure IDs against that set in both directions. One inherited drifter is
  known from earlier pipelines (`test_c3_real_concurrent_open_insert_translates_the_loser[model]`,
  load-dependent; capture the ID set before repeating an anomalous run).
- **Known hazards for these phases:** (a) `tasks` gains a NOT NULL column — the revision must carry
  `server_default`, or every raw-SQL task insert in the suite and in `app/scripts/` breaks; (b) nine
  task commands gain a flush and one indexed query in phase 10 — any existing statement-count test
  wrapping one of them moves by a fixed amount (none found by grep on 2026-09-19: the
  `before_cursor_execute` users are worker-stats, item-economics, users, acknowledgments and
  presentations tests); (c) two existing guard suites read documents — `tests/unit/docs/` (phase 14);
  (d) `TestClient` router tests fake `get_db` and `run_service`; DB-backed webhook tests call the
  command with `raw_body` bytes, not the HTTP layer.

### 10.1 The 21 baseline failures against the phases (owner table 1)

Column meaning: *module* = the production module the test exercises; *overlaps* = a phase edits that
module or a direct caller of it; *adjacent* = no phase edits it, but a phase changes a model or a
callee its fixtures or routes depend on; *unrelated* = neither. **No phase fixes any of them.**

| # | Failing test ID (file::test) | Module exercised | Phase | Verdict |
|---|---|---|---|---|
| 1 | `bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values` | `commands/bootstrap/phases/seed_item_economics` | — | unrelated |
| 2 | `bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections` | `commands/bootstrap/phases/seed_working_sections` (fixtures build `Task`, `Item`) | 1 (`tasks` column) | adjacent |
| 3 | `items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events` | `commands/items/batch_update_item_positions` | — | unrelated |
| 4 | `items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing` | same | — | unrelated |
| 5 | `upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_promotes_expected_candidates` | `commands/upholstery/set_current_stored_amount_inventory` | — | unrelated |
| 6 | `…::test_set_current_stored_amount_inventory_demotes_low_priority_available_first` | same | — | unrelated |
| 7 | `…::test_set_current_stored_amount_inventory_noop_emits_no_events` | same | — | unrelated |
| 8 | `working_sections/test_batch_working_section_integration.py::test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value` | `commands/working_sections/*` (fixtures build `Task`, `TaskStep`) | 1 (`tasks` column) | adjacent |
| 9 | `…::test_worker_working_sections_excludes_counts_for_deleted_parent_tasks` | same | 1 | adjacent |
| 10 | `working_sections/test_working_section_ordering_integration.py::test_reorder_rewrites_sort_order_and_worker_view_follows_it` | `set_user_working_sections_order` + `_membership_ordering` (read as precedent by phase 12, not edited) | — | unrelated |
| 11 | `…::test_reorder_rejects_payload_not_matching_active_set` | same | — | unrelated |
| 12 | `tests/integration/test_audit_log.py::test_write_audit_from_event_inserts_row` | `infra/audit/write_audit` | — | unrelated |
| 13 | `…::test_detail_defaults_to_empty_dict` | same | — | unrelated |
| 14 | `unit/domain/shopify/test_dimension_migration.py::test_legacy_seat_height_without_height_maps_without_zero_values` | `domain/shopify/dimension_migration` | — | unrelated |
| 15 | `…::test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values` | same | — | unrelated |
| 16 | `unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name` | `commands/auth/sign_in_user` | — | unrelated |
| 17 | `unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes` | `queries/worker_stats/*` | — | unrelated |
| 18 | `unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields` | `domain/cases/serializers` | — | unrelated |
| 19 | `unit/test_items_router.py::test_route_list_item_issues_forwards_client_id` | `routers/api_v1/items.py` (a direct caller of `find_or_create_item`, whose behaviour phase 11 changes; the failing routes are the issue routes) | 11 | adjacent |
| 20 | `unit/test_items_router.py::test_route_delete_item_issues_forwards_ids` | same | 11 | adjacent |
| 21 | `unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params` | `routers/api_v1/upholstery_inventories.py` | — | unrelated |

Result: **0 overlaps, 5 adjacent, 16 unrelated.** Card 1 answered **A** by the owner (2026-09-19):
fix none; every phase diffs against the published 21-ID baseline; the five adjacent tests are
revisited at closeout.

### 10.2 Leaking test files against the phases (owner table 2)

**No Stock Report code reads across workspaces.** The consistency check and the manual repair take
`(session, workspace_id)` and filter every table by it (MC-20); the webhooks resolve their
workspace from the setting and filter categories, rows and items by it (MC-8, MC-10); the sync and
hooks act on the ids the command already holds; the AST guard reads no database. So rows left by
other files in `item_categories`, `items`, `execution_tasks`, `tasks` and step tables are
invisible to every phase's production code, and the only remaining exposure is a **global-count
assertion**, which §9 rule 1 forbids in every criterion.

The precise 23-file list was measured in the owner's 2026-09-19 audit session with a scratch
plugin that is not in the repo; it was **not re-measured here** (the prompt forbids building a
probe). A cheap approximation — test files that construct `ItemCategory(`, `Item(`, `Task(` or
`ExecutionTask(` and also commit (`.commit()` or `session.begin()`) — returns 22 files; the ones
the audit named by count are marked **★**:

`integration/models/shopify/test_shopify_foundation_constraints.py`,
`integration/models/shopify/test_shopify_metafield_preference_constraints.py` ★ (item_categories),
`integration/services/commands/cases/test_case_created_step_pause.py` ★ (128 rows),
`integration/services/commands/item_economics/test_phase4_fix_coverage.py`,
`…/item_economics/test_phase7_concurrency.py`, `…/item_economics/test_phase7_evaluations.py`,
`…/item_economics/test_phase8_reviewer_r1_probe.py`, `…/item_economics/test_phase8_status_results.py`,
`…/item_economics/test_phase8b_inline_task_prices.py`, `…/item_economics/test_valuation_surface.py`,
`integration/services/commands/shopify/test_create_shopify_metafield_preferences.py` ★,
`…/shopify/test_delete_shopify_metafield_preferences.py` ★,
`…/shopify/test_update_shopify_metafield_preference_sequence_order.py` ★,
`integration/services/commands/task_steps/test_step_time_settlement_integration.py` ★ (execution_tasks),
`integration/services/commands/tasks/test_delete_task_upholstery_requirements_integration.py`,
`integration/services/commands/users/test_reconcile_worker_shift_state.py`,
`…/users/test_worker_shift_commands.py`,
`integration/services/queries/item_economics/test_price_scenario_query.py`,
`integration/services/queries/shopify/test_get_shopify_metafield_preferences.py`,
`integration/services/tasks/analytics/test_process_step_transition_shift_hook.py`,
`integration/services/tasks/shopify/test_shopify_worker_handlers_integration.py`,
`integration/services/tasks/task_steps/test_finalize_pending_step_completion_integration.py`.

None of them would be seen by any phase's cross-workspace code, because there is none. The phases
that exercise existing task commands (10, 11) share worker databases with these files under
`--dist loadfile`, which is why §9 rule 1 is a rule and not advice.
