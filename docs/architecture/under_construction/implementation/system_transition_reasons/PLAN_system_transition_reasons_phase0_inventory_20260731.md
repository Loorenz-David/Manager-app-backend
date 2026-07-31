# PLAN_system_transition_reasons_phase0_inventory_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase0_inventory_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: produce the measured evidence every later phase depends on — data volumes, a complete
  read-path audit, and confirmation of the second-workspace `IntegrityError` — **without writing any
  production code**.
- Business/user intent: phases 8 (backfill) and 9 (retirement) are sized and shaped entirely by what
  this phase finds. Guessing at volume or missing a read path turns a safe migration into an outage.
- Non-goals: no schema change, no code change, no migration, no fix for anything discovered.

## Scope

- In scope: read-only database measurement; exhaustive static audit of pause-reason read paths;
  reproduction of the bootstrap `IntegrityError`; an out-of-repo slug-consumer audit; recording all
  of it in the master plan.
- Out of scope: every code change. If this phase finds a bug, it records it — it does not fix it.
- Assumptions: the implementer has read access to a database representative of production. If the
  only reachable database is the shared dev/test one, that must be stated explicitly alongside every
  figure, because volumes there do not predict production.

## Clarifications required

- [ ] Which database are the measurements taken against, and is it representative of production?
      Blocks safe implementation because phase 8's backfill strategy (single migration vs. batched)
      is chosen from these numbers.

## Acceptance criteria

1. **Volume report**, recorded in the master plan: total `step_state_records`; how many carry a
   non-null `pause_reason_id`; how many of those point at each of the three system rows
   (`pause_ended_shift`, `pause_other_task_priority`, `pause_case_created`); the same breakdown for
   `user_shift_state_records.reason` split by "looks like a `par_…` id" vs "free text" vs null; and
   total `user_declared_state_records`.
2. **Per-workspace distribution** of the above, at minimum: how many workspaces hold any
   `pause_reasons` row at all, and how many hold each system slug. (Expected from the intention:
   3132 workspaces, 1 holding `pause_ended_shift` — confirm or correct.)
3. **Read-path audit**: an exhaustive list of every code location that resolves a `pause_reason_id`
   into a label, name, or map — services, serializers, analytics composers, migrations. Each entry
   as `file:line` with a one-line description of what it produces. This list is the definition of
   done for phase 2; a path missed here ships broken there.
4. **Second-workspace `IntegrityError` confirmed or refuted** by execution, not inspection. Create a
   second workspace through the ordinary bootstrap path against a disposable database and record
   what happens. If it does NOT raise, explain why — the static reading in the intention (Finding 2)
   is then wrong and must be corrected.
5. **Out-of-repo slug-consumer audit** (T6): search the frontend handoff documents, any export or
   reporting code, webhook payload builders, and API response shapes for anything that surfaces
   `pause_reasons.slug` outside this backend. Operator ruled "drop the column" on the basis that
   nothing does — **escalate rather than proceed if this finds a consumer.**
6. **Label-resolution inventory for the three system rows**: for each, exactly which human-visible
   strings historical data currently resolves to. Phase 8 must reproduce these; success criterion 5
   of the master plan is unverifiable without them.
7. All findings recorded in the master plan under a new "Phase 0 inventory" section, with the query
   text used, so any figure can be re-derived.

## Contracts and skills

### Contracts loaded

- `backend/architecture/23_documentation.md`: recording findings.
- `backend/architecture/01_architecture.md`: layering, to classify the read paths found.

### File read intent — pattern vs. relational

This phase is **entirely relational reads**. Every read is to establish what exists. No pattern reads
are needed because no code is being written.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`
- Excluded alternatives: none — this phase writes no code.

## Implementation plan

1. Confirm which database is being measured; state it in every recorded figure.
2. Run and record the volume queries (criterion 1) and the per-workspace distribution (criterion 2).
3. Statically audit every consumer of `pause_reason_id` and of `PauseReason` — start from the model
   file and follow inbound references. Include analytics composers, the linear-timeline services,
   the kiosk clock-out analytics composite, serializers, and migrations. Record as `file:line`.
4. Provision a disposable database, run `alembic upgrade head`, bootstrap one workspace, then
   bootstrap a second. Record the exact outcome (criterion 4).
5. Grep the handoff documents and any export/webhook/report surface for `slug` (criterion 5).
6. For each of the three system rows, record the exact `name` string historical data resolves to
   (criterion 6).
7. Write the "Phase 0 inventory" section into the master plan, including query text.
8. Review log entry, then STOP for independent review.

## Risks and mitigations

- Risk: measurements taken against the shared dev database are mistaken for production figures.
  Mitigation: criterion 1 requires the database to be named alongside every figure; the
  clarification above blocks until answered.
- Risk: the read-path audit misses a consumer, which then breaks in phase 2.
  Mitigation: audit from the model outward (inbound references) rather than by guessing at call
  sites; cross-check against the three runtime call sites already named in the intention.
- Risk: the disposable-database test is run against the shared database and damages it.
  Mitigation: criterion 4 says **disposable**. If none can be provisioned, STOP and escalate — do
  not substitute the shared database.

## Validation plan

- Every figure in the report reproducible from the recorded query text: same numbers on re-run.
- The read-path audit contains, at minimum, the three runtime call sites named in the intention
  (`_clock_worker_shift.py:200`, `transition_step_state.py:274`, `_step_transition_core.py:114`).
  Their absence proves the audit is incomplete.
- No files changed outside the master plan and this plan's Review log: `git status` shows nothing
  else.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
