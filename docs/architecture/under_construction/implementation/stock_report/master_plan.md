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
       Phases 1–3 VERIFIED. **Gate closed 2026-09-20 with the owner's authorization: approval
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
| 4 | Transition operation: moves over six states, unit counters, inline self-heal, removal, stamps, payloads | PENDING | 2026-09-19 | planner | rows 62, criteria 7; complex: yes (guarded statement, lock order) (round 9: +13 rows) |
| 5 | Goal credit: the MC-5 table incl. `resolved_early`, goal self-heal, the worked sequence | PENDING | 2026-09-19 | planner | rows 22, criteria 3; complex: no (round 9: +5 rows) |
| 6 | Demand service, set-based (D6): find-or-create, goal records, replay, deadline, statement bound, locked-set assertion | PENDING | 2026-09-19 | planner | rows 36, criteria 8; complex: yes (set-based SQL, two-session rows) (round 8: +1 row, `_demand_lookup.py`) |
| 7 | Demand endpoint: key auth, body validation, duplicates, identity invariant over real bytes, envelope | PENDING | 2026-09-19 | planner | rows 52, criteria 7; complex: no |
| 8 | Assignments: batch create with the matcher, override and `already_processed_by_scanner`, batch delete, race error, role cells | PENDING | 2026-09-19 | planner | rows 65, criteria 8; complex: yes (lock order, race row) (round 9: +7 rows) |
| 9 | Processed webhook: §14F F5 order, `early` reason, grouped per-column counter update, replay, one owning transaction | PENDING | 2026-09-19 | planner | rows 42, criteria 8; complex: yes (grouping, sorted locks) (round 9: 4 rows rewritten, +9 rows) |
| 10 | Task-state sync at S1–S9, the registry guard, three two-writer interleavings | PENDING | 2026-09-19 | planner | rows 35, criteria 7; complex: yes (nine-site sweep, two-session rows) (round 9: 1 row rewritten, +5 rows) |
| 11 | Removal hooks (task, item, PRIMARY unlink) and the category guard on both item writers | PENDING | 2026-09-19 | planner | rows 27, criteria 7; complex: yes (five existing commands, new locks) (round 9: +1 row) |
| 12 | Priority, dense ordering, history records for user actions, the list endpoint | PENDING | 2026-09-19 | planner | rows 45, criteria 7; complex: yes (advisory lock, shift statements) |
| 13 | Row deletion cascade, second self-heal trigger, assignment reads and compact serializers | PENDING | 2026-09-19 | planner | rows 18, criteria 5; complex: yes (cascade, lock order) (rounds 8–9: 2 rows rewritten) |
| 13A | Scanner delete webhook: find-and-delete through the cascade, six carried questions (intention §14E) | PENDING | 2026-09-19 | planner | rows 36, criteria 7; complex: yes (multi-row cascade, deterministic contention rows); projection mandatory, not waivable |
| 14 | Frontend handoff and domain docs (thin; refine at prompt time) | PENDING | 2026-09-19 | planner | rows 5, criteria 2; complex: no (rounds 8–9: +1 row; depends on 13A) |

Totals (derived from the plan files by the planner's count script, 2026-09-19, after the round-8/9
delta): **615 criterion rows in 98 criteria across 15 phases** (planning-0: 532 / 90 / 14). No phase
exceeds eight criteria (3, 6, 8, 9 sit at eight).

**Trace coverage (derived by the same script from the trace cells).** Ledger: M1 → 1, 3, 4, 8, 10,
13, 13A · M2 → 9, 10, 11, 13A · M3 → 6, 9, 13A · M4 → 1, 6, 7, 8, 9, 12, 13, 13A · M5 → 5, 9, 12 ·
M6 → 3, 12, 13A · M7 → 7, 9, 13A · M8 → 2, 8, 11 · M9 → 3, 14. Every contract MC-1…MC-20 appears
in at least one trace cell (MC-10 only in 9; MC-11 in 10 and 13A; MC-20 in 3 and 13A). Amendment
rows are cited as `§14E En` / `§14F Fn` beside the contract they amend.

## 4A. Batch tracker (§3A)

| Batch | Phases | State | Date | Actor | Note |
|---|---|---|---|---|---|
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
| B1 | 4, 5 | REVIEW_PROMPT_READY | 2026-09-21 | orchestrator | **light delta-scoped re-review (§3A)** — prompt `prompts/reviewer/2026-09-21_batch_B1_rereview_1.md`, tree `60d6a12`, Opus |
| B1 | 4, 5 | IMPLEMENTED | 2026-09-21 | orchestrator | Fix round 1 (`handoffs/implementer/2026-09-21_batch_B1_fix_1_handoff.md`, state DONE, checkpoint `60d6a12`). All five items closed. **Zero production-code diff against `1351b5f`** — tests and plan docs only (+177 lines across the three test files). Orchestrator L4 on `60d6a12`: **22 failed / 3349 passed / 2 skipped**. The 22nd is `test_ended_shift_bucket_collapse.py::test_list_workers_totals_reports_an_open_clock_out_record_as_ended_shift`, **outside this perimeter and provably independent**: I ran the file alone with no stock-report test present and it still fails, and its line 554 computes `datetime.now(timezone.utc)` then subtracts 3 h, so between 00:00 and ~03:00 UTC the clock-in lands on the previous UTC day. Run at 00:31 UTC. **A clean 21-ID L4 must be re-taken after 03:00 UTC before the approval gate.** Ledger honestly re-derived: `executed 33 != declared 34`; the single gap is plan 4 C5(c)'s mutation, declared as note N12, not hidden. Two further gaps found and closed this round (C5(a), C5(b) were counted in the original prose sum but had no run anywhere) |
| B1 | 4, 5 | FIX_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* | fix round 1, prompt `prompts/implementer/2026-09-21_batch_B1_fix_1.md`, Sonnet. Scope: S1, S2, S3, S4 + card 2's scenario. **Orchestrator rulings (owner asleep, autonomous run):** card 1 — the intention settles it (§9D MC-19's payload block names `"high"\|"medium"\|"low"\|null`), so the guard is added tonight as a test plus a **candidate criterion in plan 4's Review log**; I did **not** author a criterion row, because the owner's fold authority is mutation and fixture cells only. Card 2 — judgment, not settled; proceeding **provisionally** on the reviewer's recommendation to close it now, flagged for the owner. §6.5 amended with the three batch B1 signatures and the spent N-S3 sentence deleted; plan 4's C1(u) and C6(c) mutation cells corrected per review notes N2/N3 |
| B1 | 4, 5 | CHANGES_REQUESTED | 2026-09-21 | orchestrator | Review 1 (`handoffs/reviewer/2026-09-21_batch_B1_review_1_handoff.md`, Opus, tree `1351b5f`): **83 PASS / 1 FAIL / 0 NOT_VERIFIED** of 84, **zero blocking, no production defect**. Four should-fix, all in tests and paperwork: S1 plan 4 C5(b) asserts 3 of its 4 clauses; S2 no test in either phase takes a lock, so H6/N-R1's caller premise is unproven and undeclared; S3 MC-19's priority payload is implemented but exercised by nothing; S4 both mutation ledgers assert counts that cannot be derived from their own artifacts. 11 notes routed. **The fold was judged: no over-reach in any of the 22 cells**, but two carried analytical errors (N2, N3) — corrected here |
| B1 | 4, 5 | REVIEW_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* | review prompt `prompts/reviewer/2026-09-21_batch_B1_review_1.md`, tree `1351b5f`, Opus + plan-reviewer, launched by the orchestrator (owner asleep; autonomous run authorized 2026-09-21) |
| B1 | 4, 5 | IMPLEMENTED | 2026-09-21 | orchestrator | Handoff `handoffs/implementer/2026-09-21_batch_B1_implement_1_handoff.md` (Sonnet, state DONE, 0 owner cards). Checkpoints `e50807b` (phase 4), `1351b5f` (phase 5). 84 rows mapped 1:1; ledgers `executed == declared` at 33 (phase 4) and 15 (phase 5). **Orchestrator L4 on `1351b5f`: 21 failed / 3349 passed / 2 skipped, baseline-identical both ways; 3349 = 3264 + 85 exactly.** Perimeter verified: 4 new production files, 3 new test files, 3 authorized edits (`_repair_records.py` +delta, `_task_flag.py` +workspace predicate, `repair_stock_report.py` call site). Two self-reported findings: phase 4 C3's 22 rows reduce to 4 guard branches (four rows double-guarded, combined removal run to prove they can fail); phase 5 C2(c)'s mutation was inert at its literal site and was re-sited with both runs recorded |
| B1 | 4, 5 | IMPLEMENTATION_PROMPT_READY | 2026-09-21 | orchestrator | *superseded.* | **Batch B split into B1 (4, 5) and B2 (6, 7) by the owner, 2026-09-21**, because the implementer for batch B is a **Sonnet** agent and 172 rows in one session is the largest ask this pipeline has made of any implementer. Each half gets its own implement → review → approval cycle. Projection `handoffs/projectionist/2026-09-21_batch_B_projection_handoff.md` (7 blockers, 38 fold cells, 1 outcome defect). Lesson fold applied to plans 4-5 at `a306298` — 22 mutation/fixture cells. Prompt `prompts/implementer/2026-09-21_batch_B1_implement_1.md` |
| B2 | 6, 7 | BATCH_NOT_STARTED | 2026-09-21 | orchestrator | waits for B1 APPROVED. Fold for plans 6-7 (16 cells) applied at B2 prompt time, not now. Carries blockers B3 (statement listener cannot see parameters), B4 (`StockDemandOutcomeEnum` never shipped), B5 (every row must commit and purge), B6 (plan 7 C7(a)'s monkeypatch is self-defeating), and outcome defect O1 (plan 6 C7(a) says "two parameters"; one shared bind compiles to one) |
| B | 4, 5, 6, 7 | BATCH_NOT_STARTED | 2026-09-19 | orchestrator | *superseded by the B1/B2 split.* |
| C | 8, 9, 10, 11 | BATCH_NOT_STARTED | 2026-09-19 | orchestrator | waits for B APPROVED |
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
| `enums.py` | `StockTaskAssignmentStateEnum` (`in_queue`, `in_progress`, `awaiting`, `resolved`, `failed`, `resolved_early` — six members, intention §14F F1); `ACTIVE_ASSIGNMENT_STATES = {in_queue, in_progress, awaiting}`, `TERMINAL_ASSIGNMENT_STATES = {resolved, failed, resolved_early}` (frozensets; a partition of the enum — §9 rule 16); `StockReportPriorityEnum` (`high`, `medium`, `low`); `StockReportHistoryRecordTypeEnum` (`quantity_requested_change`, `priority_change`, `priority_order_change`); `StockReportRepairTargetKindEnum` (`stock_report_item`, `history_record`, `task`, `group`); `StockCriteriaMismatchReasonEnum` (`missing_on_item`, `value_not_accepted`, `no_group_for_value`, `criterion_not_understood`); `StockDemandOutcomeEnum` (`applied`, `category_not_found`); `StockDemandDeletedOutcomeEnum` (`deleted`, `not_found`, `category_not_found` — §14E E7); `ItemsProcessedOutcomeEnum` (`resolved`, `ignored`); `ItemsProcessedReasonEnum` (`item_not_found`, `no_open_assignment`, `early` — §14F F5/P43; the response's `reason` is JSON `null` for a resolution from `awaiting`); `REPAIR_TRIGGER_MANUAL = "manual"`; `INLINE_REPAIR_TRIGGERS` = frozenset of `inline:` + {`create_assignments`, `task_sync`, `delete_assignments`, `delete_task`, `remove_item_from_task`, `delete_item`, `items_processed`, `delete_stock_report_item`, `stock_demand_deleted`} (all shipped by phase 1; 13A adds no enum) |
| `state_map.py` | `ASSIGNMENT_STATE_BY_TASK_STATE: dict[TaskStateEnum, StockTaskAssignmentStateEnum]` (intention §5, total over the 8 members) |
| `criteria_normalization.py` | `normalize_stock_criteria(raw: dict) -> dict`; `compute_stock_criteria_signature(raw: dict) -> str` (= `compute_properties_signature(normalize_stock_criteria(raw))`, the existing function imported unchanged from `bm/domain/items/properties_signature.py`); `CRITERIA_NORMALIZATION_VERSION = 1` |
| `scanner_property_tables.py` | `WOOD_GROUPS`, `DRAWER_RANGES`, `WOOD_TYPE_KEY`, `WOOD_GROUP_KEY`, `DRAWERS_QTY_KEY`, `DRAWERS_RANGE_KEY`, `EXCLUDED_ITEM_PROPERTY_KEYS` (`qty_extensions`, `quantity`, `wood_group`, `drawers_range`), `SCANNER_SOURCE_COMMIT = "0d80bf2"`, `SCANNER_SOURCE_READ_ON = "2026-09-18"`, `validate_wood_groups(groups) -> None`, `validate_drawer_ranges(ranges) -> None` (both called at import), `wood_group_of_token(token) -> str \| None`, `drawer_range_of(stored: str) -> str \| None` |
| `criteria_matcher.py` | `CriterionFailure` (frozen dataclass: `key: str`, `reason: StockCriteriaMismatchReasonEnum`); `build_item_property_bag(item) -> dict[str, str]`; `tokenize_property_value(value: str) -> list[str]`; `evaluate_stock_criteria(item, criteria: dict) -> list[CriterionFailure]` (sorted by key); `matches_stock_criteria(item, criteria) -> bool` |
| `serializers.py` | `serialize_stock_report_item(row, *, category) -> dict`; `serialize_stock_task_assignment(assignment, *, item, task, images) -> dict`; `serialize_item_compact(item, *, images) -> dict`; `serialize_task_compact(task) -> dict` |

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
| `requests/__init__.py` | `CreateStockTaskAssignmentsRequest` (`entries: list[StockTaskAssignmentEntry]`, `model_config = ConfigDict(extra="forbid")`, ≥ 1 entry), `StockTaskAssignmentEntry` (`stock_report_item_id`, `task_id`, `item_id`, `override_property_mismatch: bool = False`), `DeleteStockTaskAssignmentsRequest` (`client_ids: list[str]`, ≥ 1), `SetStockReportItemPriorityRequest` (`client_id`, `priority: StockReportPriorityEnum \| None`), `SetStockReportItemPriorityOrderRequest` (`client_id`, `priority_order: int`), `DeleteStockReportItemRequest` (`client_id`) and their `parse_*_request` functions |

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
| `app/tests/helpers/statement_listener.py` (phase 3) | `record_statements()` async context manager attaching `before_cursor_execute` on the engine's `sync_engine`, yielding the list; `count_writes(statements, tables: set[str]) -> int` (INSERT/UPDATE/DELETE whose target table is in the set) — precedent `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py:470-487` |
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
   MC-20 read-only, the image batch bound) and always through `record_statements`. It is never
   used to assert query text or internal structure.
8. **Named mutations name file and definition-vs-call-site; the row is run whole-file, never
   `-k`;** a mutation's observed-red set is recorded across the suite when the symbol is
   asserted in more than one file (earned three pipelines running).
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

## 10. Environment topology (verified 2026-09-19 by the planner; if reality disagrees, update here)

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
