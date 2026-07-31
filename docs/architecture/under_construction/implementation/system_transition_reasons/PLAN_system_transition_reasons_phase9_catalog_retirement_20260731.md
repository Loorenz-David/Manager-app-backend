# PLAN_system_transition_reasons_phase9_catalog_retirement_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase9_catalog_retirement_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: retire the system catalog rows and everything that existed to serve them — the slug lookup,
  `slug` itself, its global unique index, and the `is_system_managed` machinery.
- Business/user intent: `pause_reasons` becomes what it was always meant to be, a catalog of things
  a worker chooses. Dropping `uq_pause_reasons_slug` also **fixes the second-workspace
  `IntegrityError`** (master-plan success criterion 6) as a consequence of the design, not as a
  patch.
- Non-goals: constraints on `transition_reason` (phase 10).

## Scope

- In scope: soft-deleting the three system rows; deleting `get_system_pause_reason_id`; removing
  `is_system_managed` and its consumers; dropping `slug` and `uq_pause_reasons_slug`; the bootstrap
  seed phase and seed migration.
- Out of scope: worker-choosable catalog rows and the CRUD surface, beyond removing system-row
  special-casing.
- Assumptions: phases 1–8 archived. **Entry condition: phase 8's zero-remaining-references query
  returns zero.** Re-run it — do not trust the recorded result.

## Clarifications required

- [ ] Soft-delete or hard-delete the three system rows? Soft-delete is safer (FK intact, reversible)
      but leaves rows a manager could see unless filtered. Hard-delete is only possible once phase 8
      guarantees zero references, and `ondelete="RESTRICT"` will enforce that for us. **Recommend
      soft-delete**; escalate for the ruling.

## Acceptance criteria

1. **Entry condition re-verified**: zero rows in any table reference the three system catalog rows.
   Recorded, freshly run. If non-zero, STOP — phase 8 is incomplete.
2. The three system rows are retired per the clarification's ruling and no longer appear in any
   worker-facing picker or manager-facing catalog list. Assert against the actual endpoint response.
3. `get_system_pause_reason_id` is **deleted** (master-plan success criterion 3), along with its
   module if nothing else lives there, and its tests.
4. `is_system_managed` and its consumers are removed: `domain/pause_reasons/guards.py`
   (`can_delete_pause_reason`), the pause-reason serializer field, and the hardcoded `False` in
   `create_pause_reason.py`. **`can_delete_pause_reason` returning `not is_system_managed` is
   delete protection** — confirm nothing else depended on it before removing, and state what
   replaces it (likely: nothing, because there is nothing left to protect).
5. `slug` and `uq_pause_reasons_slug` are dropped (**T6**, operator-confirmed 2026-07-31). Phase 0's
   out-of-repo consumer audit must have found none; if it found one, STOP.
6. **Second-workspace bootstrap succeeds** — the mirror of phase 0's criterion 4. Create two
   workspaces through the ordinary path against a disposable database and prove the
   `IntegrityError` is gone. This is master-plan success criterion 6.
7. The bootstrap seed phase and seed migration `49bd666da846` no longer seed system rows. Their
   duplicated `_PAUSE_REASONS` tuples are reconciled — both carry explicit comments requiring the
   other to be updated in step; leaving them inconsistent is a finding.
8. Serializer output for pause reasons no longer includes removed fields, and the change is
   **proposed** to the operator for the handoff — not written into it.

## Contracts and skills

### Contracts loaded

- `backend/architecture/04_migrations.md`
- `backend/architecture/03_models.md`
- `backend/architecture/46_serialization.md`

### File read intent — pattern vs. relational

- Permitted (relational): `pause_reason.py`; `guards.py`; `create_pause_reason.py`; the pause-reason
  serializer; `seed_pause_reasons.py` and migrations `49bd666da846` / `fb10ac7fd439`.
- Prohibited (pattern): style reads.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Re-run phase 8's zero-references query. If non-zero, STOP.
2. Escalate the soft/hard-delete clarification.
3. Retire the rows per ruling; assert they are gone from pickers and catalog listings.
4. Delete `get_system_pause_reason_id` and its tests.
5. Remove `is_system_managed` and each consumer; confirm nothing else relied on the guard.
6. Drop `slug` and `uq_pause_reasons_slug`.
7. Reconcile the bootstrap phase and the seed migration.
8. Two-workspace bootstrap test on a disposable database (criterion 6).
9. Review log entry; handoff proposal, not edit. STOP.

## Risks and mitigations

- Risk: an out-of-repo consumer of `slug` breaks silently after the column is gone.
  Mitigation: criterion 5 depends on phase 0's audit; the operator's T6 ruling was explicitly
  conditional on that audit finding nothing.
- Risk: removing `is_system_managed` removes delete protection that something else was quietly
  relying on.
  Mitigation: criterion 4 requires confirming what depended on it before removal.
- Risk: the seed phase and seed migration drift apart, so a fresh database and an upgraded one end
  up with different catalogs.
  Mitigation: criterion 7 requires reconciling both; both files carry comments demanding it.

## Validation plan

- Zero-references query returns zero, freshly run.
- Two-workspace bootstrap succeeds on a disposable database.
- `grep -rn "get_system_pause_reason_id\|is_system_managed\|slug" app/beyo_manager` returns nothing
  in the pause-reasons domain.
- Fresh-database `alembic upgrade head` produces a catalog with no system rows.
- Full suite: no new failure nodes vs. baseline. `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
