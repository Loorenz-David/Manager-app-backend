# MASTER_PLAN_system_transition_reasons_20260731

## Metadata

- Plan ID: `MASTER_PLAN_system_transition_reasons_20260731`
- Status: `under_construction`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal

Move system-controlled state transitions out of the workspace-managed `pause_reasons` catalog and
onto the source records themselves, as a code-owned `transition_reason` vocabulary — so that
clock-out and task switching never depend on a seeded catalog row existing in a workspace.

## Why this matters

Measured at commit `de0b3b3`: **3132 workspaces, exactly 1 holding `pause_ended_shift`.** In the
other 3131, clock-out with an open WORKING step fails with `NotFound`, and — because
`pause_other_task_priority` has the same dependency across two more call sites — **task switching
fails as well**. A mandatory state-machine transition is gated on user-editable data.

Full reasoning, the seven traced findings, and the root-cause mechanism are in the intention plan.
This master plan does not restate them; implementers must read it.

## Architecture (target state)

| Case | `transition_reason` | `pause_reason_id` |
|---|---|---|
| Clock-out closing an open working step | `SHIFT_ENDED` | `NULL` |
| Auto-pause because another task took priority | `OTHER_TASK_PRIORITY` | `NULL` |
| Worker paused a step with a catalog reason | `WORKER_PAUSED` | the chosen catalog row |
| Worker declared an off-task state | *(implicit — see T3)* | the chosen catalog row |

`pause_reasons` returns to being purely a catalog of things a **worker chooses**. No runtime code
path resolves a row by slug.

## Traced model facts (established 2026-07-31; do not re-derive)

- **`StepStateRecord`** — `pause_reason_id` nullable FK → `pause_reasons.client_id`
  `ondelete="RESTRICT"`, plus a separate `description` (which carries the auto-pause text
  `"started working with {identifier}"`). This is the table that needs `transition_reason`.
- **`StepStateRecord` has NO `reason` column.** Migration `b58cdffb5ccc` dropped it together with
  `step_event_reason_enum`. Any plan text implying a live legacy free-text column there is wrong.
- **`UserDeclaredStateRecord.pause_reason_id` is `NOT NULL`** — a declared state always carries a
  catalog reason, so the row's existence already encodes its transition semantics. See T3.
- **`UserShiftStateRecord`** is **derived**, rebuilt at clock-out. `reason` is a `String(512)`
  holding either a `par_…` catalog id or legacy free text; `manually_recorded` is a boolean carrying
  provenance. Historical rows are never rebuilt — they are the migration's real problem.
- **`pause_case_created`** is a soft-deleted catalog row that historical `step_state_records` point
  at via FK. It is a live label-resolution target, not dead weight.

## Cross-phase decisions (binding for every phase)

Numbered `T…` to avoid collision with the declared_worker_states set's `D1–D14`.

- **T1 — The vocabulary is code-owned.** `transition_reason` is a domain enum persisted as a
  constrained string/enum column. It is never resolved through a database lookup.
- **T2 — System transitions write `pause_reason_id = NULL`.** A row carries a catalog reference only
  when a human chose it.
- **T3 — `UserDeclaredStateRecord` does NOT get a `transition_reason` column.** Its
  `pause_reason_id` is `NOT NULL`, so the column would be constant for every row. The declared-state
  semantics are carried by the table identity and surfaced during derivation. If a phase finds a
  concrete case this breaks, escalate rather than adding the column silently.
- **T4 — Readers tolerate both representations before any writer changes** *(relaxed
  2026-07-31)*. Originally this forced read tolerance into its own phase ahead of every writer
  cutover. That protects against a **partial deploy** — a window where new-format rows exist and
  readers discard them. The operator is shipping this set in one deploy, so that window does not
  exist, and the separation bought three extra review cycles for nothing. **Revised rule:** readers
  and writers may ship in the same phase, provided the readers are implemented and tested *first
  within it* and they reach production in the same deploy. If the delivery plan ever changes to
  incremental deploys, this reverts to the strict form.
- **T5 — Retire, do not leave inert** (operator ruling, 2026-07-31). Historical rows are backfilled
  to `transition_reason`, their system `pause_reason_id` nulled, and the system catalog rows then
  soft-deleted. Ends with one representation everywhere. The alternative — permanently dual
  representation — was rejected: it preserves exactly the read-layer ambiguity this feature set
  exists to remove.
- **T6 — `slug` and `uq_pause_reasons_slug` are removed, not scoped.** Once no runtime path resolves
  by slug, the column and its global unique index have no consumer. Dropping them resolves the
  second-workspace `IntegrityError` as a consequence rather than as separate work. Scoping the index
  to `(workspace_id, slug)` is explicitly NOT the fix (intention plan, "Architectural direction").
  **Operator confirmed 2026-07-31: drop the column, not only the index.** Phase 1's inventory step
  must still audit for out-of-repo slug consumers (exports, reports, webhooks, frontend) and escalate if it finds
  one — the ruling was made on the basis that none exist in this repository.
- **T7 — `manually_recorded` subsumption is a FOLLOW-UP, not part of this set** *(demoted
  2026-07-31)*. `transition_reason` probably subsumes it, and the `changed_by_id IS NOT NULL`
  heuristic that declared_worker_states Phase 2 settled on after four fix cycles (F1/F2, G1, H1, I1)
  probably becomes unnecessary. But removing it fixes nothing user-facing, and proving the
  equivalence safely is a whole phase of work. **Recorded as deferred cleanup** — do it when
  someone next touches that code with a reason to. No phase in this set may remove
  `manually_recorded` or the heuristic; doing so is a scope violation.
- **T8 — No phase repairs baseline debt.** The repository has documented pre-existing validation
  debt (see the declared_worker_states master plan's "Repository validation baseline"). Implementers
  must not absorb it; reviewers must not block on it.

## Amendments to declared_worker_states decisions

This feature set amends three binding decisions of `MASTER_PLAN_declared_worker_states_20260729.md`.

**How amendments are recorded (decided 2026-07-31).** That feature set is **archived** — all seven
phases complete, its folder moved to `archives/implementation/declared_worker_states/`. Archived
documents are historical records and are **not edited**. So each amendment is recorded **here**, in
the table below, and the amending phase's Review log states which decision it changed and how. No
phase edits the archived plan. Anyone reading the archived D3/D5/D14 finds them via this plan, which
the intention links.

- **D3** — declared state surfaces as `IN_PAUSE` + `reason = pause_reason_id` +
  `manually_recorded = true`. Amended: `reason` stops being a polymorphic slot; the derived row
  carries `transition_reason` and a clean catalog reference.
- **D5** — auto-pause carries the declared `pause_reason_id`. Amended: restated in terms of
  `transition_reason`.
- **D14** — kiosk clock-out analytics return `pause_by_reason` keyed by reason id plus a
  `pause_reasons` label map. Amended only if the retirement changes which keys can appear; the
  published contract is preserved (see "Sequencing against Phase 7").

## Sequencing against declared_worker_states Phase 7

Phase 7 (clock-out analytics) is in an active implement→review cycle and its contract is **already
published to the frontend**. Operator ruling: **Phase 7 lands and archives first.** This feature set
does not begin implementation until it does.

Consequence for this plan: Phase 7's `pause_by_reason` map becomes a concrete compatibility test for
the read-tolerance phase. Any phase here that changes what keys can appear in that map owns a
handoff update, and the handoff is operator-owned — phases propose, they do not edit.

## Phase orchestration

**Restructured 2026-07-31 from eleven phases to four.** The original set applied the ceremony of the
declared_worker_states feature set — which built new tables, a new auth scope, new endpoints, and a
kiosk flow — to a migration that adds a column, teaches readers to read it, flips three call sites,
backfills, and deletes the leftovers. Eleven phases meant eleven implement→review→fix cycles, at
roughly seven exchanges each before a single defect. That cost was not justified by the risk.

Three of the removed phases existed only to satisfy the strict form of T4, which guards against a
partial deploy. This set ships in one deploy (see "Delivery shape"), so that guard bought nothing.
One more, `manually_recorded` subsumption, was cleanup that fixes nothing user-facing and is now
deferred under T7.

| # | Phase | Delivers | Independent review earns its cost because |
|---|---|---|---|
| 1 | **Inventory, vocabulary, schema & read tolerance** | The read-path audit and volume figures; `TransitionReasonEnum`; nullable `transition_reason` on `step_state_records` and `user_shift_state_records`; every read path resolves both representations. **Zero behaviour change** — nothing writes the column yet. | The audit is the foundation the rest is built on, and a missed read path ships broken in phase 2. |
| 2 | **Cutover** | Clock-out, both task-switch sites, the derivation rebuild, and the serializer all move to `transition_reason`. `get_system_pause_reason_id` reaches zero runtime callers. **Ends the outage.** | One behavioural change with one question: does clocking out and switching tasks still work, including in a workspace with an empty catalog. |
| 3 | **Historical backfill** | One-time migration: `transition_reason` set on historical rows, their system `pause_reason_id` nulled. | Irreversible. This is where real history gets destroyed if the row selection is wrong. |
| 4 | **Retirement & constraints** | System rows retired; `get_system_pause_reason_id` deleted; `is_system_managed` removed; `slug` + `uq_pause_reasons_slug` dropped; check constraints added; final verification. | Drops columns and adds constraints — cheap to review, but must follow 3. |

**Ordering rationale.** Phase 1 is additive and observably inert, so it carries no deploy risk.
Phase 2 ends the outage **without needing the backfill**: new rows do not require the catalog row
that is missing, so the 3131 broken workspaces work the moment it ships. Phases 3 and 4 are cleanup
that removes the second representation — valuable, but not what unblocks anyone.

**What was preserved from the eleven-phase draft.** The acceptance criteria, which were the real
output: the zero-catalog tests, the label-parity requirement, "select by the three specific system
rows, never by `is_system_managed` alone", the mutation proofs, and the escalation triggers. They
live in fewer, larger plans, unchanged in substance.

**Delivery shape.** Phases 1–4 run as one continuous set, begun immediately after
declared_worker_states Phase 7 archives, and reach production in a single deploy. Each phase must
still be independently deployable, but none is designed as a resting point. If this changes to
incremental deploys, T4 reverts to its strict form and phase 1 must split.

### Per-phase workflow (operator: David)

1. Operator hands the phase's implementer prompt to a fresh implementer session.
2. Implementer: implement → validate → Review log entry → **STOP**.
3. Operator hands the phase's review prompt to a fresh independent reviewer session.
4. On `NEEDS_CHANGES`: operator writes a fix brief; implementer fixes; re-review.
5. On `APPROVED`: **then** summary → archive → master phase-table flip.

No implementer performs step 5. No phase plan may carry an acceptance criterion instructing the
implementer to flip a liveness row or edit an operator-owned handoff.

### Validation baseline

This feature set inherits the recorded baseline in
`MASTER_PLAN_declared_worker_states_20260729.md` → "Repository validation baseline", including:

- Canonical quiet-tree measurement **27 failed / 1275 passed**; compare failure **node sets**, never
  counts; never accept a suite number taken while another session is active.
- **A baseline git worktree needs its gitignored config copied in.** `.gitignore` excludes
  `app/.env.*`, so a fresh worktree lacks `app/.env.testing` and will report wildly inflated
  failures. Verify config parity with a small smoke run in both trees before trusting any full-suite
  number. (Learned the hard way during declared_worker_states Phase 7.)
- 149 pre-existing `ruff check .` errors in untouched files; the shared `count_queries` fixture is
  broken — use a local SQLAlchemy listener.

## Success criteria (feature set as a whole)

1. Clock-out succeeds in a workspace holding **zero** `pause_reasons` rows, with an open WORKING
   step, and the resulting record is unambiguously identifiable as a shift-ended transition.
2. Task switching auto-pauses a conflicting step in that same zero-catalog workspace.
3. `get_system_pause_reason_id` has no runtime callers and is deleted.
4. No field requires prefix-sniffing to determine its meaning; the
   `startswith(CLIENT_ID_PREFIX)` branch in `domain/users/serializers.py` is gone or provably dead.
5. Historical rows resolve to the same human-visible labels after migration as before.
6. Bootstrapping a second workspace succeeds.

## Open questions

- **Q4 (from the intention) — `auto_pause_description`.** `"started working with {identifier}"` is
  written to `StepStateRecord.description`, a genuinely per-instance value. Provisional ruling: it
  stays where it is; typing the transition does not make the instance detail redundant. Phase 4
  confirms or escalates.
- Whether `WORKER_PAUSED` is the right member name for a worker-chosen step pause, or whether that
  case should carry no `transition_reason` at all (catalog reference alone). Phase 1 decides and
  records; it is cheap to change before any writer ships.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved` (operator reads and approves this master plan, then per-phase plans)
- Transition owner: `David`

## Progress notes

- `2026-07-31`: **Restructured from eleven phases to four** (operator call). The eleven-phase draft
  applied declared_worker_states' ceremony — which was sized for new tables, a new auth scope, new
  endpoints and a kiosk flow — to a migration that adds a column, teaches readers, flips three call
  sites, backfills, and deletes leftovers. At ~7 exchanges per implement→review→fix cycle, eleven
  phases cost ~77 exchanges before a single defect. Three of the removed phases existed only to
  satisfy the strict form of T4, which guards against a partial deploy that this delivery shape does
  not have; a fourth (`manually_recorded` subsumption) was cleanup fixing nothing user-facing and is
  now deferred under T7. **The acceptance criteria were preserved verbatim in substance** — they were
  the real output; only the phase boundaries changed. The eleven phase-plan files and the phase 0
  prompts were deleted rather than left alongside the new set.
- `2026-07-31`: **All eleven phase plans written** (phase0 … phase10, this folder). Operator
  resolved the remaining open inputs: T6 confirmed as *drop the column, not only the index*
  (conditional on phase 0's out-of-repo consumer audit finding nothing); delivery runs 0–10 as one
  continuous set with no deliberate stopping point; `pause_ended_shift` confirmed present in the
  production workspace, which this feature set supersedes anyway; `clock_in_code` assignment handled
  manually by the operator; PERSONAL pause reasons already seeded in local and server databases.
  (Superseded by the restructure above.)
- `2026-07-31`: Master plan drafted. Model layer traced: the intention's Finding 4 was corrected
  (`step_state_records.reason` was dropped by `b58cdffb5ccc`; what survives is the soft-deleted
  `pause_case_created` anchor row that history points at via FK). Operator ruled **T5 retire** over
  leaving system rows inert, which makes T6 (drop `slug` + the global unique index) available and
  resolves the second-workspace `IntegrityError` as a consequence. Phase plans not yet written.
