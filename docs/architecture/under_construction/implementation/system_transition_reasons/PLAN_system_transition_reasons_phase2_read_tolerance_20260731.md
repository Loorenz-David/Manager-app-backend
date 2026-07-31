# PLAN_system_transition_reasons_phase2_read_tolerance_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase2_read_tolerance_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: teach **every** read path that resolves a pause reason to handle a `transition_reason` row —
  resolving it to a label from code — while still handling `pause_reason_id` rows exactly as today.
- Business/user intent: this is the phase that makes the writer cutovers (3, 4, 5) safe. Per **T4**,
  no writer may change until this ships. Because nothing writes `transition_reason` yet, this phase
  is observably a no-op in production — which is precisely what makes it safe to deploy alone.
- Non-goals: no writer changes; no schema changes; no contract changes; no catalog changes.

## Scope

- In scope: every read path in phase 0's audit (criterion 3); a single shared label-resolution
  helper for `transition_reason`; tests that prove both representations resolve.
- Out of scope: writers; `get_system_pause_reason_id` (still live, still called — phases 3/4 remove
  its callers); serializer contract changes (phase 7).
- Assumptions: phase 1 archived, so the column exists; phase 0's read-path audit is complete and is
  treated as this phase's definition of done.

## Clarifications required

- [ ] Where does the shared label map for `TransitionReasonEnum` live, given the layering contract?
      `01_architecture.md:43` forbids `services/queries/` importing `services/infra/`. A prior
      feature set's operator proposed exactly that and was corrected by review. Likely home is
      `domain/`. Resolve before writing it, and record the reasoning.

## Acceptance criteria

1. **Every** path in phase 0's read-path audit resolves a row carrying `transition_reason` to a
   human-visible label, and a row carrying `pause_reason_id` exactly as it does today. The audit list
   IS the checklist — each entry ticked with its test.
2. Label resolution lives in **one** place and is imported, not duplicated. Duplicated maps are a
   finding.
3. **Precedence is explicit and tested**: when a row somehow carries both, which wins is a recorded,
   asserted decision — not incidental. (It should not happen after phase 3, but historical or
   partially-migrated rows make it reachable, and "shouldn't happen" is not a behaviour.)
4. **Zero production behaviour change, proven.** Nothing writes `transition_reason` yet, so every
   existing response must be byte-identical. Prove it with existing tests unchanged, not by
   inspection.
5. New behaviour proven by **seeding rows with `transition_reason` directly in tests** — the only
   way to exercise this phase before writers exist. Each read path gets such a test.
6. The kiosk clock-out analytics `pause_by_reason` map (declared_worker_states Phase 7, published
   contract) resolves `transition_reason` rows without a key that has no entry in the accompanying
   `pause_reasons` map. This is the concrete compatibility test named in the master plan's
   "Sequencing" section. **The published contract must not change in this phase.**
7. `manually_recorded` is NOT touched (that is phase 6), and the `startswith("par_")` branch in
   `domain/users/serializers.py` is NOT removed (that is phase 7). Removing either here is a scope
   violation.
8. Query counts unchanged: resolution is from an in-memory map, so no read path gains a round trip.
   Prove with a local SQLAlchemy listener — the shared `count_queries` fixture is broken.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: layering — decides where the shared map lives.
- `backend/architecture/46_serialization.md`: output shapes must not drift.
- `backend/architecture/07_queries.md`: query-service conventions.

### File read intent — pattern vs. relational

- Permitted (relational): every file named in phase 0's audit, to see what each currently returns;
  the analytics composers and linear-timeline services for their existing map shapes.
- Prohibited (pattern): reading a serializer to learn output-shape style — `46_serialization.md`
  covers it.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Resolve the clarification; place the shared label map accordingly.
2. Walk phase 0's audit list in order. For each path: add `transition_reason` resolution, keep the
   `pause_reason_id` path untouched, add a test seeding a `transition_reason` row.
3. Decide and assert precedence when both are present (criterion 3).
4. Add the `pause_by_reason` compatibility test (criterion 6).
5. Prove zero behaviour change and unchanged query counts.
6. Review log entry listing every audit entry with its test, plus the precedence ruling. STOP.

## Risks and mitigations

- Risk: a read path missed here fails in phase 3, in production, on the outage-fixing deploy.
  Mitigation: criterion 1 binds this phase to phase 0's audit as a literal checklist; the reviewer
  is instructed to re-derive the audit independently rather than trust the list.
- Risk: label duplication drifts as members are added later.
  Mitigation: criterion 2, single source, imported.
- Risk: the new branch is never exercised because nothing writes the column, so tests pass
  vacuously.
  Mitigation: criterion 5 requires directly seeded rows; the reviewer should mutate the resolution
  to confirm the tests fail.

## Validation plan

- Every audit entry has a passing test that seeds `transition_reason` directly.
- Existing responses byte-identical; existing tests unmodified.
- Query-count listener shows no new round trips.
- Full suite: no new failure nodes vs. baseline (node sets, not counts).
- `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
