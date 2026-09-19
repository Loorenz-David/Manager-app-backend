---
plan: master_plan.md + plans/plan_1.md … plan_14.md (round-7 plan set, uncommitted, awaiting owner review)
role: planner (implementation-planner) — planning delta
round: planning-1 (fold intention rounds 8 and 9)
date: 2026-09-19
skill: implementation-planner (`/Users/davidloorenz/agent-skills/implementation-planner.md`, via the pipeline charter)
---

# Planning delta: fold intention rounds 8 (§14E) and 9 (§14F) into the `stock_report` plan set

The plan set in this folder was written against the round-7 intention (`f575488`). While it was
being written, the owner added two rounds and re-ratified both. The intention is now **RATIFIED at
round 9, committed `c231dfb`**. Your job is a **delta, not a rewrite**. Fold both rounds into the
existing master plan and phase plans, so that every criterion row traces to the round-9 text and
nothing in the set contradicts it. No phase is dispatched until you are done and the owner has
reviewed the result.

Paths are relative to `backend/`. `SR/` is
`docs/architecture/under_construction/implementation/stock_report/`.

## Gate check (stop and report `BLOCKED` if any line fails)

1. `SR/planning/intention.md` has a header line beginning `status: RATIFIED`, round 9, and §18
   carries the owner's round-8 and round-9 re-ratification entries.
2. The intention is committed: `git status --porcelain -- SR/planning/intention.md
   docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v1_20260918.md` prints nothing, and `git log -1
   --format=%h -- SR/planning/intention.md` is `c231dfb`.
3. `SR/master_plan.md` and `SR/plans/plan_1.md` … `plan_14.md` exist (untracked, the round-7
   set). The previous planner's handoff is `SR/handoffs/planner/2026-09-19_planning_handoff.md`.

Expected, and not yours: ` M docs/archgraph-anchor-observations.md` (the orchestrator's) and this
prompt file (untracked). Leave both alone.

## Source of truth, and what to read

The intention is the only semantic authority. Later amendments win, and **§14F is last and
strongest**. Read:

1. The charter and your doctrine (as before).
2. The intention: the Status section, **§14E**, **§14F**, §14C rows **C46–C50**, §16 **P37–P45**,
   §17, §18 rounds 8–9, and M2/M3 in §13 (each gained one sentence). Follow any contract §14E/§14F
   cite (MC-1, MC-3, MC-4, MC-5, MC-8, MC-9, MC-10, MC-11, MC-13, MC-16, MC-19, MC-20) back to its
   lettered section.
3. The previous planner handoff (all of it), then the master plan and the phase plans you will
   change.
4. The Scanner contract `docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v1_20260918.md`, revised in
   place and not yet handed over: **§4A** (delete webhook) and **§4.2 / §4.3** (early resolution).
   **Read-only.** The plan's wire shapes (paths, bodies, outcome and reason vocabularies, status
   codes) must match it exactly. Where the handoff and the intention disagree, that is a finding:
   put it in your handoff, do not pick one silently, and do not edit either file.

## Round 8 — §14E, the Scanner delete webhook

- `POST /api/v1/location-tracker/webhooks/stock-demand-deleted`. Same key, validation order
  (MC-8 steps 1–6) and 5 s deadline (MC-9 D5) as demand. Lookup is demand's (MC-3 / MC-4 / MC-8).
  Effect is the existing row-deletion cascade (MC-16), with assignments in any state and tasks
  untouched. Outcomes are `deleted | not_found | category_not_found`. A replay issues zero writes.
- The previous planner reserved a provisional **phase 13A** (after 7 and 13) and factored phase
  13's cascade as `cascade_delete_stock_report_item` (master plan §6.5) so the webhook adds a
  caller. Build on that, or justify a different home in the master plan's sequencing section.
- **The owner waived a mechanism-inventory re-check. The six questions under §14E "Carried to the
  planner" are your obligations.** For each, write a **stated rule** in the plan text and **a
  criterion row that can fail** (named mutation, trace cell citing §14E and the contract it
  touches). Question (3) may be answered "no bound", with the reason stated. Where a question
  cannot be settled without the owner, write a decision card. Do not guess. The round-0
  projection of that phase will check all six, so make each answer findable: one labeled
  subsection, "§14E carried questions", listing Q1–Q6 → rule → row id.

## Round 9 — §14F, the `resolved_early` state

- New **terminal** assignment state `resolved_early`. The processed webhook moves `in_queue` /
  `in_progress` → `resolved_early` (Scanner only): −q on the from-counter, the task is never
  touched, and the later task-state sync skips it because it is terminal.
- Goal credit on entering `resolved_early` is the same as entering `awaiting`, and is never removed
  (F4, card 14 → A).
- Processed decision order (F5): `item_not_found` → `no_open_assignment` → `awaiting` → `resolved`
  (reason null) → `in_queue` / `in_progress` → `resolved` (reason `"early"`). `not_awaiting` is
  retired: remove it from every vocabulary, row and fixture in the set.
- The MC-11 two-writer rows are replaced (F6).
- Creating an assignment for a (task, item) pair that already has a non-deleted `resolved` or
  `resolved_early` assignment → 422 `already_processed_by_scanner`, after `item_not_task_primary`
  in MC-13's order (F9 / P44).
- M2 gained one sentence. C47–C50 name the superseded text: every plan sentence or row built on
  superseded text is rewritten, not annotated.
- The owner's list of touched phases: **1** (enum + terminal set), **4** (transition table), **5**
  (goal credit), **8** (creation refusal), **9** (processed order + MC-11 rows), **10** (one
  sync-skip row). Use it as a starting point, not a boundary. Search the whole set for every
  consequence, such as the consistency check's recomputation (phase 3), counters, events (MC-19),
  the list and assignment reads (12, 13), role cells, and the frontend handoff (14). Report any
  phase you changed that is not on the owner's list, with the reason.

## Rules that still bind (unchanged from the planning-0 prompt)

- Criterion rows state outcomes at a public boundary (charter rule 2, owner rule 2026-09-19).
- Every test creates its own workspace, asserts nothing global, and tolerates other tests' leftover
  rows (within-run leakage measured 2026-09-19).
- The implementer is Codex, fresh per phase, working from the Read-first list alone.
- No phase exceeds eight criteria. If a fold pushes one over, split it and say so.
- Keep the per-phase sizing line (rows, criteria, `complex: yes/no`) current, and **derive every
  count by script** after your edits.

## Do not touch

- **Card 1** (which of the 21 baseline failures to fix) and the master plan's §10.1 / §10.2 tables:
  unanswered by the owner, and out of this delta's scope.
- **These criterion rows, beyond what rounds 8–9 require of them:** plan 3 C2(a), plan 6 C7(a),
  plan 9 C7(a)'s statement-count clause, plan 13 C4(c), and plan 10's registry guard. The owner
  has an open review question on them. If round 9 forces a change to one of them (plan 9 C7(a)
  resolves awaiting rows), change only what round 9 requires, and name it in your handoff.
- The intention, the Scanner handoff, both inventory handoffs, the previous planner handoff, any
  prompt file, anything under `app/`, and the architecture graph (read-only orientation only).
- **Do not commit.**

## Output

- Edit `SR/master_plan.md` and the phase plans in place, and add new phase files if the delta
  needs them. Update the master plan's header and status: the round-8 "COLLABORATING / hold /
  provisional 13A" text is now false, and must say RATIFIED round 9. Also update the tracker, the
  dependency graph (§7), the naming registry (§6: new state, error identity, endpoint, events) and
  the trace-coverage summary.
- Write your handoff at `SR/handoffs/planner/2026-09-19_planning_delta_r8_r9_handoff.md`, with
  frontmatter `plan`, `role: planner`, `round: planning-1`, `date`, `state`, `actor`. It must
  contain:
  1. **Phase plans changed**: one row per file with what changed (rows added, removed or rewritten,
     by id), and before → after row and criteria counts. Include new files. Mark each phase as on
     or off the owner's round-9 list.
  2. **§14E carried questions**: Q1–Q6 → stated rule → criterion row id → `settled` or `owner card n`.
  3. **Wire-shape check** against the Scanner handoff §4A / §4.2 / §4.3: each shape the plan uses,
     with the handoff section it matches, plus any mismatch found.
  4. Superseded text removed (C47–C50, `not_awaiting`): the search commands you ran, and a zero-hit
     result for `not_awaiting` outside historical notes.
  5. The write perimeter, checked against `git status --porcelain -uall` at close, and the owner
     cards in the charter format.
