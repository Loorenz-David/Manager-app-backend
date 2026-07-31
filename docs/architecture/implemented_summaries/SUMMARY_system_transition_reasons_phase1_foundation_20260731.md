# SUMMARY_system_transition_reasons_phase1_foundation_20260731

## Metadata

- Summary ID: `SUMMARY_system_transition_reasons_phase1_foundation_20260731`
- Status: `summarized`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-07-31T14:13:35Z`
- Source plan: `backend/docs/architecture/archives/implementation/system_transition_reasons/PLAN_system_transition_reasons_phase1_foundation_20260731.md`
- Master plan: `backend/docs/architecture/under_construction/implementation/system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
- Related debug plan: `none`

## What was implemented

Phase 1 of four. It is **observably inert**: nothing writes `transition_reason`, so every existing
response stays byte-identical. Its value is the evidence and the foundation phases 2–4 build on.

- **Step A — inventory.** Model-outward read-path audit (24 entries, R1–R24), volume report,
  per-workspace distribution, label-resolution strings, out-of-repo slug-consumer audit, and an
  executed reproduction of the second-workspace `IntegrityError`. Recorded in the master plan under
  "Phase 1 inventory".
- **Step B — vocabulary.** `TransitionReasonEnum` (`SHIFT_ENDED`, `OTHER_TASK_PRIORITY`,
  `WORKER_DECLARED_STATE`) in a new `domain/transitions/`, plus the single code-owned label map.
- **Step C — schema.** Nullable, indexed, unconstrained `transition_reason` on `step_state_records`
  and `user_shift_state_records` via an additive-only migration. **No column on
  `user_declared_state_records`** (T3).
- **Step D — read tolerance.** Thirteen label-resolving read paths resolve `transition_reason`
  while resolving `pause_reason_id` exactly as before, with precedence asserted.

### Three corrections the inventory forced on its own inputs

1. **The intention's "3132 workspaces, exactly 1" came from the shared *test* database**, which now
   holds 4118 workspaces and zero `pause_reasons` rows. It is accumulated test residue. The
   architectural argument stands; the "3131 broken production workspaces" framing is not supported
   by evidence obtainable from the operator's machine (the RDS is unreachable).
2. **`UserShiftStateRecord.reason` holds no free text at all.** All 272 non-`par_` values are legacy
   slug strings plus the literal `"unspecified"`. Phase 3's backfill is therefore a direct slug map
   with **no unmappable tail** — reproduced exactly on re-measurement.
3. **`image_url` cannot be reproduced by a code-owned map** (the seeded value is a
   workspace-specific S3 path), so `labels.py` returns `None`. Inert here; phase 3 owns the
   consequence.

### T6 amended — an operator ruling was overturned by evidence

The slug-consumer audit found **live out-of-repo consumers** of `pause_reasons.slug`, so the
implementer stopped and escalated before writing code. The decisive one is
`frontend/packages/pause-reasons/src/types.ts:19`, where `slug: z.string()` is **required and
non-nullable** — dropping the column would fail Zod validation on *every* pause-reasons response,
not merely break the ended-shift branch. Two shipped call sites and the published
`HANDOFF_TO_FRONTEND_pause_reasons_step_transition_contract_20260722.md` ruling also key off it.

**Operator amended T6: keep the `slug` column; phase 4 scopes `uq_pause_reasons_slug` to
`(workspace_id, slug)` instead of dropping it.** No phase 1–3 deliverable depended on the drop.

### Intention Finding 2 — confirmed by execution

On a disposable database (`beyo_str_repro_tmp`, created and dropped for the test; never the shared
one), driving the real `seed_pause_reasons` against `pause_reasons` built from live model metadata:
`UniqueViolationError: duplicate key value violates unique constraint "uq_pause_reasons_slug"`.

## Files changed

- `app/beyo_manager/domain/transitions/__init__.py`: **new** package.
- `app/beyo_manager/domain/transitions/enums.py`: **new** — `TransitionReasonEnum`, the enum alone,
  so it stays importable from `models/` under `01_architecture.md`'s dependency table.
- `app/beyo_manager/domain/transitions/labels.py`: **new** — the single label map plus
  `resolve_transition_reason_label` / `is_transition_reason`. Imported by read paths only.
- `app/beyo_manager/models/tables/tasks/step_state_record.py`: added nullable indexed
  `transition_reason` (`String(32)`).
- `app/beyo_manager/models/tables/users/user_shift_state_record.py`: same column.
- `app/migrations/versions/a7d21f4c8b03_add_transition_reason_columns.py`: **new** — additive-only,
  hand-written to avoid autogenerate sweeping in pre-existing schema drift.
- `app/beyo_manager/domain/users/serializers.py`: `transition_reason` resolves to a `pause_reason`
  reference when no catalog row does; precedence catalog > transition > free text;
  `pause_reason_reference_is_unresolved` no longer flags typed rows.
- `app/beyo_manager/services/queries/worker_stats/get_worker_linear_timeline_breakdown.py`:
  `_StepTimelineRecord.transition_reason` + `bucket_key(resolved_catalog_ids)`; label map and
  segment-level key tolerate the new vocabulary.
- `app/beyo_manager/services/queries/worker_stats/list_workers_linear_timeline.py`: bucket key falls
  back to `transition_reason`; `_load_pause_reasons_lookup` resolves transition keys from memory
  with no round trip.
- `app/tests/unit/domain/transitions/test_transition_reason_domain.py`: **new**, 19 tests.
- `app/tests/integration/services/queries/worker_stats/test_transition_reason_read_tolerance.py`:
  **new**, 7 tests.
- Docs: master plan gained "Phase 1 inventory"; the phase plan's Review log carries the rulings;
  `review_prompts/REVIEW_phase1_foundation.md` had its baseline instructions corrected.

**No existing test was modified.**

## Contract adherence

- `01_architecture.md` (layering): `models/` imports only `domain/transitions/enums.py`; the label
  map lives beside it in `labels.py` and is imported by `domain/` and `services/queries/` only. No
  `services/queries/` → `services/infra/` import.
- `04_migrations.md`: additive-only, reversible; `upgrade → downgrade → upgrade` verified
  schema-identical by information_schema + `pg_indexes` snapshot diff.
- `46_serialization.md` / criterion 17: no serializer surfaces the new column; no response gains a
  field. The step-payload nested `pause_reason` stays a **catalog** object and remains `null` for a
  typed row.
- T1/T2 (code-owned vocabulary), T3 (no column on `user_declared_state_records`), T7
  (`manually_recorded` and the `changed_by_id` heuristic untouched), T8 (no baseline debt absorbed).

## Validation evidence

- **Full suite, failure node sets, run-2 vs run-2** (both trees run twice so each faced an equally
  dirty shared database; baseline `git worktree` at `26d290d` with all of `app/.env*` copied in):
  baseline **27 failed / 1338 passed**, working **27 failed / 1364 passed** — **node sets identical,
  zero new failure nodes**, +26 passing (the new tests). Independently re-run by the reviewer with
  the same result.
- **Anti-vacuity:** mutating `resolve_transition_reason_label` to return `None` kills **9 of 26**
  new tests; restoring returns 26/26. Re-run by the reviewer after the fix cycle.
- **F1 regression test binds to its guard:** reverting `bucket_key` to its pre-fix body fails
  exactly `test_breakdown_never_emits_a_catalog_id_that_did_not_resolve`.
- **Query counts:** `test_transition_reason_labels_cost_no_extra_query` asserts a transition-only
  roster issues **no** `pause_reasons` query; `test_catalog_reason_still_queries_pause_reasons` is
  the control. Local SQLAlchemy listener — the shared `count_queries` fixture is broken.
- **Kiosk contract:** existing `test_pause_reasons_resolves_every_timeline_key_including_unspecified`
  re-run unmodified and green; new coverage adds a transition key alongside `"unspecified"`.
- **Inventory reproducibility:** every figure marked STABLE re-derived from its recorded query text
  by the reviewer, including both figures phase 3 leans on hardest.
- `ruff check` clean on all touched files.

## Known gaps or deferred items

- **R14 / R15 — the highest-risk carry-forward.** `_reconstruct_shift_middle` and
  `reconcile_worker_shift_state` are *writers* of the derived table, so phase 1 correctly leaves them
  alone. Once phase 2 types `step_state_records`, they will produce `reason=NULL` and bucket the
  kiosk as `unspecified` unless phase 2 rewrites them. **Phase 2 must treat this as a required
  deliverable, not a discovery.**
- **`image_url` for system transitions is `None`.** Phase 3's backfill flips real rows onto the
  code-owned map, at which point the kiosk pause icon for system transitions becomes null unless a
  code-owned asset is chosen. Flagged, not decided.
- **`pause_case_created` disposition.** No enum member; it is a catalog reason a user action selects,
  not a system transition. **Phase 3 must null only `pause_ended_shift` and
  `pause_other_task_priority`** — nulling the 7 anchored rows without a `transition_reason` to carry
  would lose their label and fail master-plan success criterion 5.
- **Repo health (i) — pre-existing, verified at `26d290d`.** The breakdown endpoint's
  `pause_reasons` map is built from step records only, so a segment key coming from the worker-level
  shift record is emitted unresolvable. Criterion 17 forbids repairing it in this phase.
- **Repo health (ii) — pre-existing, verified at `26d290d`, live data affected.** The
  `pause_case_created` anchor is seeded already soft-deleted, and `list_pause_reasons` filters
  `is_deleted IS false`, so the frontend's slug lookup returns `undefined` and **case-created pauses
  are being written today with no `pause_reason_id` at all**. Phase 3's backfill will meet these
  rows. Worth the operator's attention independently of this feature set.
- **`create_pause_reason.py:37` sets `slug=None`** while the frontend schema requires a string — a
  pre-existing contract mismatch, out of scope per the intention's scope boundary.
- **Open for the operator:** `PLAN_..._phase3_backfill_20260731.md` clarification 3 still says
  `pause_case_created` "likely needs its own member", which the F4 disposition now contradicts.
  Editing a sibling phase plan is outside phase 1's remit; the operator may want it updated before
  phase 3 is handed to an implementer.

## Handoff notes (if needed)

- To frontend: **none.** Zero behaviour change; no published contract moved. The T6 amendment
  *avoids* a frontend-breaking change that the original ruling would have caused.
- From frontend dependency: none.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/system_transition_reasons/ARCHIVE_RECORD_PLAN_system_transition_reasons_phase1_foundation_20260731.md`
