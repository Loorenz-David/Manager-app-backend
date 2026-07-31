# PLAN_system_transition_reasons_phase1_foundation_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase1_foundation_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: establish the evidence, the vocabulary, the schema, and read tolerance — in that order,
  within one phase — so that phase 2 can cut every writer over in a single pass.
- Business/user intent: nothing here changes observable behaviour. Nothing writes
  `transition_reason` yet, so every existing response stays byte-identical. That is what makes this
  phase safe to deploy on its own and safe to review in one pass.
- Non-goals: no writer changes; no backfill; no constraints; no catalog changes; no
  `manually_recorded` work (T7 — deferred).

## Scope

- In scope: the inventory (step A); `TransitionReasonEnum`; nullable `transition_reason` on
  `step_state_records` and `user_shift_state_records`; the additive migration; the shared label map;
  read tolerance across every path the inventory finds.
- Out of scope: `UserDeclaredStateRecord` (T3 — no column); every writer;
  `get_system_pause_reason_id` (still live, still called — phase 2 removes its callers);
  `manually_recorded` and the `changed_by_id` heuristic (T7 — touching either is a scope violation).
- Assumptions: declared_worker_states Phase 7 is archived.

## Clarifications required

- [x] **Which database are the inventory figures taken from, and is it representative of
      production?** *Resolved 2026-07-31 (operator):* use the `.env` database,
      `localhost:5433/beyo_manager`. **Not** representative of production — the RDS is unreachable
      from this machine, so phase 3 must treat the backfill row selection as unvalidated against
      production. See the master plan's "Phase 1 inventory".
- [x] **Does a worker-chosen step pause need a `WORKER_PAUSED` member**, or is the catalog reference
      alone sufficient? *Resolved 2026-07-31 (operator):* **no member.** See the Review log.
- [x] **Where does the shared label map live**, given `01_architecture.md:43` forbids
      `services/queries/` importing `services/infra/`? *Resolved 2026-07-31 (operator):* new
      `domain/transitions/` — `enums.py` holds the enum only (the models-importable surface),
      `labels.py` holds the map and is imported by read paths only. See the Review log.

## Acceptance criteria

### Step A — inventory (do this first; it defines the rest of the phase)

1. **Read-path audit**: an exhaustive `file:line` list of every location that resolves a
   `pause_reason_id` into a label, name, or map — services, serializers, analytics composers,
   migrations. Audit from the model **outward** (inbound references to `PauseReason` and
   `pause_reason_id`), not by guessing at call sites. **This list is the checklist for step D**; a
   path missed here ships broken in phase 2. It must contain the three runtime call sites the
   intention names (`_clock_worker_shift.py:200`, `transition_step_state.py:274`,
   `_step_transition_core.py:114`) — their absence proves the method was wrong.
2. **Volume report**: total `step_state_records`; how many carry a non-null `pause_reason_id`; how
   many point at each of the three system rows (`pause_ended_shift`, `pause_other_task_priority`,
   `pause_case_created`); the same split for `user_shift_state_records.reason` by "looks like a
   `par_…` id" vs free text vs null; total `user_declared_state_records`. Each figure with the query
   text and the database it came from.
3. **Per-workspace distribution**: how many workspaces hold any `pause_reasons` row, and how many
   hold each system slug. (Intention expects 3132 / 1 — confirm or correct.)
4. **Out-of-repo slug-consumer audit (T6)**: search handoff documents, export/report code, webhook
   payload builders, and API response shapes for anything surfacing `pause_reasons.slug`. The
   operator ruled "drop the column" *conditional on this finding nothing*. **Escalate rather than
   proceed if it finds a consumer.**
5. **Label-resolution strings**: for each of the three system rows, the exact human-visible string
   historical data resolves to today. Phase 3 must reproduce these; master-plan success criterion 5
   is unverifiable without them.
6. **Second-workspace `IntegrityError` confirmed or refuted by execution**, on a **disposable**
   database — not by inspection, and not against the shared database. If it does not raise, the
   intention's Finding 2 is wrong and must be corrected. Reporting that is success.

### Step B — vocabulary

7. `TransitionReasonEnum` in the domain layer, following existing enum conventions (lowercase
   values — see `ddc5bf50153b_rename_enum_labels_to_lowercase`). Members at minimum: `SHIFT_ENDED`,
   `OTHER_TASK_PRIORITY`, `WORKER_DECLARED_STATE`, plus whatever the clarification resolves.

### Step C — schema

8. Nullable, indexed `transition_reason` on `step_state_records` and `user_shift_state_records`. No
   default, no constraint. **No column on `user_declared_state_records`** (T3) — if you believe T3
   is wrong, STOP and escalate rather than adding it.
9. Migration is additive-only and reversible: `upgrade` adds, `downgrade` drops, no data touched.
   Verify `upgrade` → `downgrade` → `upgrade` leaves the schema identical.
10. Column type recorded in the Review log with reasoning — native PG enum vs constrained string.
    Note this repo has already paid to remove a native enum once (`b58cdffb5ccc` dropped
    `step_event_reason_enum`), which is evidence for the string+check approach.

### Step D — read tolerance

11. **Every** path from criterion 1 resolves a `transition_reason` row to a label, and a
    `pause_reason_id` row exactly as today. The audit list is the checklist — each entry ticked with
    its test.
12. Label resolution lives in **one** place and is imported. Duplicated maps are a finding.
13. **Precedence is explicit and tested**: if a row somehow carries both, which wins is asserted,
    not incidental. It should not happen after phase 2, but "shouldn't happen" is not a behaviour.
14. New behaviour proven by **seeding `transition_reason` rows directly in tests** — the only way to
    exercise it before writers exist. Each read path gets one.
15. The kiosk clock-out analytics `pause_by_reason` / `pause_reasons` contract (published, live)
    is unchanged, and every key still resolves — including the literal `"unspecified"` key, which is
    part of the published contract. Re-run its existing tests.
16. Query counts unchanged — resolution is from an in-memory map. Prove with a local SQLAlchemy
    listener; the shared `count_queries` fixture is broken.

### Whole-phase

17. **Zero behaviour change, proven**: no existing test modified, no endpoint response gains a
    field, no serializer surfaces the new column.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: layering — where the enum and the shared map live.
- `backend/architecture/03_models.md`, `04_migrations.md`: model and migration conventions.
- `backend/architecture/07_queries.md`, `46_serialization.md`: read-path conventions.

### File read intent — pattern vs. relational

- Permitted (relational): every file the inventory surfaces; `step_state_record.py`,
  `user_shift_state_record.py`, `user_declared_state_record.py` for exact fields; existing domain
  enums for conventions; `b58cdffb5ccc` / `ddc5bf50153b` for this repo's enum history.
- Prohibited (pattern): reading another model for column-declaration style (`03_models.md`), another
  serializer for output shape (`46_serialization.md`).

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Answer the database clarification. Run step A in full and record it in the master plan under
   "Phase 1 inventory", with query text.
2. If step A's slug audit finds a consumer, STOP and escalate before continuing.
3. Resolve the `WORKER_PAUSED` and label-map-location clarifications; record both rulings.
4. Add the enum; add the columns; generate the additive migration.
5. Walk the audit list in order: add `transition_reason` resolution, keep `pause_reason_id`
   untouched, add a seeded test per path.
6. Assert precedence; re-run the kiosk contract tests; prove query counts unchanged.
7. Prove zero behaviour change.
8. Review log entry: both rulings, the column-type reasoning, and the audit list with each entry's
   test. STOP for independent review.

## Risks and mitigations

- Risk: a read path missed in step A fails in phase 2 — in production, on the deploy meant to *fix*
  an outage.
  Mitigation: criterion 1 fixes the audit method (model-outward); criterion 11 binds step D to it
  literally; the reviewer is told to re-derive the audit independently rather than trust the list.
- Risk: the new branch is never exercised because nothing writes the column, so tests pass
  vacuously.
  Mitigation: criterion 14 requires directly seeded rows; the reviewer should mutate the resolution
  and confirm tests fail.
- Risk: inventory figures from the shared dev database are mistaken for production.
  Mitigation: criterion 2 requires the database named alongside every figure.
- Risk: the disposable-database test is run against the shared database and damages it.
  Mitigation: criterion 6 says disposable; if none can be provisioned, STOP.
- Risk: a native PG enum makes every future member a migration and is costly to remove.
  Mitigation: criterion 10 forces an explicit recorded choice.

## Validation plan

- Every inventory figure reproducible from its recorded query text.
- Every audit entry has a passing test seeding `transition_reason` directly.
- Existing responses byte-identical; existing tests unmodified.
- `alembic upgrade head` → `downgrade -1` → `upgrade head`: schema identical.
- Query-count listener shows no new round trips.
- Full suite: no new failure nodes vs. baseline — compare **node sets**, not counts. A baseline git
  worktree needs `app/.env.testing` copied in (`.gitignore` excludes `app/.env.*`), or it reports
  wildly inflated failures. Verify config parity with a small smoke run in both trees first.
- `ruff check` clean on touched files.

## Review log

- `2026-07-31` `implementer`: **Phase 1 implemented; STOPPED for independent review.** No summary,
  no archive, no phase-table flip, no handoff edit.

  **Escalation raised and answered before any code was written.** The step A slug-consumer audit
  found live out-of-repo consumers of `pause_reasons.slug` (frontend monorepo + published handoff;
  full table in the master plan's "Phase 1 inventory"). Per acceptance criterion 4 and implementation
  step 2, work stopped and escalated. **Operator amended T6: keep the `slug` column; phase 4 scopes
  `uq_pause_reasons_slug` to `(workspace_id, slug)` instead of dropping it.** The most severe
  consumer is `frontend/packages/pause-reasons/src/types.ts:19`, where `slug: z.string()` is
  required and non-nullable — dropping the field would fail Zod validation on *every* pause-reasons
  response, not merely break the ended-shift branch. No phase 1–3 deliverable depended on the drop.

  **Ruling — `WORKER_PAUSED` (clarification 2).** **Not added.** `transition_reason` means "system
  transitions only". Reasoning: a `WORKER_PAUSED` member would be exactly redundant with
  `pause_reason_id IS NOT NULL`, which is the redundancy this feature set exists to remove (T7's
  own argument, applied before the field ships rather than after); and it would force phase 2 to
  touch the ordinary worker-pause writer path, which is otherwise untouched. Members shipped:
  `SHIFT_ENDED`, `OTHER_TASK_PRIORITY`, `WORKER_DECLARED_STATE`.

  **Operator qualification carried into phase 4.** Mutual exclusion of `transition_reason` and
  `pause_reason_id` holds for `step_state_records` only. On `user_shift_state_records` the derived
  declared-state row carries **both** `WORKER_DECLARED_STATE` and its catalog reference (the D3
  amendment; phase 2 criterion 6). **Phase 4's check constraint must therefore be per-table, or
  exempt `WORKER_DECLARED_STATE`** — it must not be written as a single global mutual-exclusion
  rule.

  **Ruling — label map location (clarification 3).** New `domain/transitions/`.
  `enums.py` holds `TransitionReasonEnum` alone, because `01_architecture.md`'s dependency table
  permits `models/` to import `domain/<domain>/enums.py` and nothing else from `domain/`; keeping
  the map out of that module is what keeps the model layer clean. `labels.py` holds the single label
  map and is imported by read paths only. A new domain rather than `task_steps` or `users` because
  the column spans both tables, and not `pause_reasons` because the point is that these are not
  pause reasons. `services/queries/` imports `domain/`, never `services/infra/` — the trap named in
  the clarification is avoided.

  **Ruling — column type (criterion 10).** `String(32)`, nullable, indexed, no default, no
  constraint — **not** a native PG enum. Reasoning: (a) this repo has already paid to remove one —
  `b58cdffb5ccc` dropped `step_event_reason_enum` together with the `step_state_records.reason`
  column; (b) a native enum makes every future member a migration, and `ALTER TYPE … ADD VALUE`
  cannot run inside a transaction; (c) phase 4 adds check constraints anyway, which gives the same
  guarantee at lower cost. The Python-side vocabulary stays typed via `TransitionReasonEnum`; the
  column stores `.value`. Lowercase values per `ddc5bf50153b_rename_enum_labels_to_lowercase`,
  confirmed against live data (`user_shift_state_enum` labels are `working`/`idle`/`in_pause`/…).

  **Ruling — precedence (criterion 13).** Catalog reference > `transition_reason` > free-text
  `reason_text`. A catalog row means a human chose it, which is strictly more specific than a
  system-typed transition, and it keeps every existing row byte-identical. Asserted at both layers:
  `test_catalog_reference_wins_over_transition_reason`,
  `test_transition_reason_wins_over_free_text_reason`,
  `test_breakdown_prefers_the_catalog_reason_when_a_row_carries_both`.

  **Audit list with each entry's test:** recorded in the master plan under "Phase 1 inventory →
  Read-path audit". Thirteen label-resolving paths tolerate `transition_reason`; the rest are
  classified with the reason they are untouched. The three runtime call sites the intention names
  are present. **R14/R15 (`_reconstruct_shift_middle`, `reconcile_worker_shift_state`) are flagged
  as the highest-risk carry-forward:** they are writers of the derived table, so phase 1 correctly
  does not change them, but after phase 2 types `step_state_records` they will produce
  `reason=NULL` and bucket the kiosk as `unspecified` unless phase 2 rewrites them. Phase 2 must
  treat this as a required deliverable, not a discovery.

  **Two things that could have overturned the inputs — both reported.** (1) The slug audit vetoed
  T6, above. (2) The `IntegrityError` reproduction **confirmed** the intention's Finding 2 by
  execution on a disposable database (`beyo_str_repro_tmp`, created and dropped for the test; the
  shared database was never used), driving the real `seed_pause_reasons` against `pause_reasons`
  created from live model metadata: `UniqueViolationError: duplicate key value violates unique
  constraint "uq_pause_reasons_slug"`.

  **Three corrections the inventory forced on its inputs.** (a) The "3132 workspaces, exactly 1"
  figure came from the shared **test** database, which now holds 4118 workspaces and zero
  `pause_reasons` rows — it is accumulated test residue, and the "3131 broken production
  workspaces" framing is unsupported by any evidence available here. (b) `UserShiftStateRecord.reason`
  holds **no free text at all** — all 272 non-`par_` values are legacy slug strings plus the literal
  `"unspecified"`, which makes phase 3's backfill a direct slug map with no unmappable tail.
  (c) `image_url` cannot be reproduced by a code-owned map (the seeded value is a
  workspace-specific S3 path), so `labels.py` returns `None` — inert now, but **phase 3's backfill
  is where system-transition rows lose their kiosk icon.** Flagged, not decided.

  **Zero behaviour change — proven, not asserted.** No existing test was modified. Full suite
  compared by **node set** against a baseline git worktree at `26d290d` with `app/.env` copied in
  (config parity verified by a smoke run in both trees first): baseline **24 failed / 1341 passed**,
  working tree **27 failed / 1363 passed**, and the three extra nodes are shared-dirty-database
  artifacts — *a second consecutive run of the unmodified baseline tree reproduces the identical
  27-node set*. **New failure nodes: zero.** Two of those three artifacts fail through the very
  global-unique-slug mechanism the reproduction confirmed. Query counts proven with a local
  SQLAlchemy listener (the shared `count_queries` fixture is broken):
  `test_transition_reason_labels_cost_no_extra_query` asserts a transition-only roster issues **no**
  `pause_reasons` query at all, with `test_catalog_reason_still_queries_pause_reasons` as the
  control. Migration cycle `upgrade → downgrade → upgrade` verified schema-identical by
  information_schema + pg_indexes snapshot diff. `ruff check` clean on all 11 touched files.

  **Anti-vacuity check.** Because nothing writes the column, every new test seeds
  `transition_reason` directly. Mutating `resolve_transition_reason_label` to always return `None`
  **kills 9 of the 25 new tests**; restoring it returns all 25 to green. The new branches are
  genuinely exercised.

  **Files touched:** `domain/transitions/{__init__,enums,labels}.py` (new);
  `domain/users/serializers.py`; `models/tables/tasks/step_state_record.py`;
  `models/tables/users/user_shift_state_record.py`;
  `services/queries/worker_stats/{get_worker_linear_timeline_breakdown,list_workers_linear_timeline}.py`;
  `migrations/versions/a7d21f4c8b03_add_transition_reason_columns.py` (new);
  `tests/unit/domain/transitions/test_transition_reason_domain.py` (new);
  `tests/integration/services/queries/worker_stats/test_transition_reason_read_tolerance.py` (new).

  **Not touched, per the hard constraints:** `manually_recorded` and the `changed_by_id` heuristic
  (T7); the `startswith("par_")` branch in `domain/users/serializers.py` (phase 2);
  `get_system_pause_reason_id` and its three callers (phase 2); `user_declared_state_records`
  (T3 — and it holds 0 rows, so nothing contradicted it).
- `2026-07-31` `independent-reviewer`: **NEEDS_CHANGES.** Four findings; one blocking. Everything
  else on both checklists was re-verified by execution, not by reading the log — results recorded
  below so they are not re-litigated.

  ---

  **F1 — BLOCKING (high). Segment `reason` changes for a step record whose `pause_reason_id` does
  not resolve in the queried workspace.**
  `services/queries/worker_stats/get_worker_linear_timeline_breakdown.py:80-88` (`bucket_key`) and
  `:461-469` (`segment_reason`). Violates **criterion 17** ("zero behaviour change, proven") and
  **criterion 11** ("resolves a `pause_reason_id` row exactly as today").

  The old expression guarded on the *serialized* detail:

      (details[0]["pause_reason"]["client_id"] if details and details[0]["pause_reason"] else None)
      or segment.record.reason

  `details[0]["pause_reason"]` is `None` whenever `pause_reason_objects.get(record.reason)` misses —
  i.e. the step's `pause_reason_id` is set but no catalog row exists **in `ctx.workspace_id`** (both
  the outer join at `:206-212` and the object prefetch at `:264-271` scope by workspace). In that
  case the old code fell through to the worker-level `segment.record.reason`. The new `bucket_key`
  returns `self.reason or self.transition_reason`, so it returns the unresolvable id instead. The
  in-code comment claiming the two reads are "identical … while nothing writes the new column"
  (`:457-460`) is wrong: they differ on `transition_reason IS NULL` rows, which is every row today.

  Reproduced by execution (probe test, since deleted): one step record pointing at a `PauseReason`
  belonging to another workspace, one worker-level shift record with its own in-workspace catalog
  reason. Working tree returns the foreign id as the segment `reason`; the same test against
  `HEAD` returns the worker-level id. Two further consequences: the returned key is absent from the
  response's sibling `pause_reasons` map (that map is only populated when
  `row.pause_reason_name is not None`, `:231`), so the client gets an unresolvable key; and a
  *foreign workspace's* `par_…` id now appears in a workspace-scoped response.

  Not hypothetical. On the `.env` database (`localhost:5433/beyo_manager`, measured 2026-07-31):

      SELECT ssr.state, count(*) FROM step_state_records ssr
        LEFT JOIN pause_reasons pr ON pr.client_id=ssr.pause_reason_id AND pr.workspace_id=ssr.workspace_id
        WHERE ssr.pause_reason_id IS NOT NULL AND pr.client_id IS NULL AND ssr.is_deleted=false
        GROUP BY 1;
      -- paused|12   ended_shift|3

  All 15 resolve globally (`NOT EXISTS … pause_reasons pr WHERE pr.client_id=ssr.pause_reason_id`
  returns 0), so this is purely the workspace-scoping mismatch — the only shape a dangling reference
  can take under the `RESTRICT` FK. No new test covers it; both breakdown tests seed a catalog row
  that resolves.

  Fix shape (not applied): `bucket_key` must reproduce the old guard — yield the catalog id only
  when it actually resolved, otherwise fall through. The resolution is already computed: the
  caller knows `record.reason in pause_reasons`. Add a test seeding a cross-workspace
  `pause_reason_id` and assert the segment `reason` equals the worker-level reason.

  ---

  **F2 — Medium. The inventory's volume figures are irreproducible, and the database they were
  measured on is the one the phase's own validation mutates.** Master plan, "Phase 1 inventory →
  Volumes" and "→ Per-workspace distribution". Violates **criterion 2** ("every inventory figure
  reproducible from its recorded query text").

  Re-derived on 2026-07-31 from the recorded query text, same database, recorded → measured:

  | Figure | Recorded | Re-measured |
  |---|---|---|
  | `step_state_records` total / with / without | 5299 / 570 / 4729 | **5344 / 585 / 4759** |
  | → `pause_ended_shift` | 152 | **155** |
  | → `pause_coffee_break` | 52 | **64** |
  | `user_shift_state_records.reason` null / legacy / `par_` | 3248 / 272 / 100 | **3300** / 272 / 100 |
  | **Workspaces total** | **1** | **313** |

  The workspace figure is the one that matters: `SELECT created_at::date, count(*) FROM workspaces
  GROUP BY 1` returns `2026-06-24 | 1` and `2026-07-31 | 312`. Every one of those 312 was created by
  a suite run — the inventory table and the validation baseline in the same phase were measured
  against the same database, hours apart, and the second moved the first. The plan's own
  disqualifier for `app_test` ("it accumulates workspaces from test runs and is not representative
  of anything") applies verbatim to `beyo_manager`@5433, which the plan itself identifies as the
  suite's database two paragraphs earlier.

  Consequence for the recorded conclusion: "**Workspaces total 1** … A single-workspace dev database
  cannot confirm or refute the 1-of-N claim" is no longer true of that database — it is now 313
  workspaces of which exactly 1 holds any `pause_reasons` row, which superficially *matches* the
  intention's shape. It is still not evidence, for the opposite reason. Phase 3 sizes a backfill
  from this table; it needs figures pinned to a reproducible cutoff (a `WHERE created_at <` bound or
  a recorded max `client_id`), not a bare snapshot.

  Figures that **did** reproduce exactly, and can be relied on: `user_declared_state_records` 0 / 0;
  `description` 157 / 113; `pause_other_task_priority` 228; `pause_case_created` 7; the unmappable
  tail = 0; the complete distinct non-`par_` set (7 values, including the literal `unspecified`);
  and every row of the label table — `name`, `pause_type`, `is_system_managed`, `is_deleted`,
  `image_url`. **Correction (b) of the three the implementer reported — "there is no free text at
  all" — is confirmed**, and it is the finding phase 3 most depends on.

  ---

  **F3 — Medium. `domain/analytics/linear_timeline.py` appears in neither audit table.** Violates
  **criterion 1** ("an exhaustive `file:line` list of every location that resolves a
  `pause_reason_id` into a label, name, or map"), which criterion 11 binds step D to literally.

  `:220` (`state, reason, chosen = "paused", owner.interval.reason or UNSPECIFIED_REASON, …`) and
  `:264` (`pause_by_reason[seg.reason or UNSPECIFIED_REASON] += secs`) are where an interval's
  reason becomes a bucket key and where the published `unspecified` default is applied. The audit
  lists its *callers* (R14 `_reconstruct_shift_middle`, R15 `reconcile_worker_shift_state`) but not
  this module, and the audit is the checklist three later phases inherit — unlisted is not the same
  as classified-and-excluded.

  Nothing is broken today: `compute_linear_timeline` has zero runtime callers (only
  `compute_linear_segments` is reached, from R14), and phase 1 correctly changes neither. But phase 2
  rewrites R14/R15, and this is the module their output flows through. Add it to the
  "deliberately unchanged" table with its ruling.

  ---

  **F4 — Low. `pause_case_created` has a recorded label, no vocabulary, and no stated disposition.**
  Criterion 5 records `pause_case_created -> "Case created"` as one of the three system rows, but
  `TransitionReasonEnum` has no member for it and `labels.py` has no entry — so for the 7
  `step_state_records` pointing at it, master-plan success criterion 5 ("historical rows resolve to
  the same human-visible labels after migration") is unreachable through the new vocabulary. The
  `WORKER_PAUSED` ruling explains why a worker-chosen pause gets no member; it does not cover this
  row. Mitigating, and confirmed against the database: `pause_case_created` is
  `is_system_managed=false`, so phase 4's retirement of the system rows does not target it and those
  7 rows can simply stay on `pause_reason_id`. Say so explicitly, so phase 3 does not discover it.

  ---

  **Re-verified independently — no finding.** Recorded so a fix round does not re-run them.

  - **Read-path audit re-run model-outward** (inbound references to `PauseReason` /
    `pause_reason_id` across `beyo_manager/` and `migrations/`, then outward through each
    consumer). Beyond F3 I found no label-resolving path missing from the two tables. R2
    (`domain/tasks/serializers.py:186,377` — nested catalog object), R16 (`selectinload` feeders,
    incl. `working_sections/step_record_payload.py:237`) and R21 are correctly classified. The three
    runtime call sites the intention names are present at `_clock_worker_shift.py:197`,
    `transition_step_state.py:271`, `_step_transition_core.py:111`.
  - **Migration.** `alembic downgrade -1` → `upgrade head` with an `information_schema.columns` +
    `pg_indexes` snapshot either side: `diff` of before vs after is **empty**. The downgraded
    snapshot differs by exactly the two columns and two indexes and nothing else. Both columns are
    `character varying(32)`, nullable, no default, no constraint. `SELECT … WHERE
    column_name='transition_reason'` returns exactly `step_state_records` and
    `user_shift_state_records` — **no column on `user_declared_state_records`** (T3). Single alembic
    head.
  - **Zero behaviour change, read from the diff.** `git status -- app/tests` shows only the two new
    untracked paths: no existing test modified. No endpoint response gains a field. The serializer
    change surfaces a transition reason only through the existing `pause_reason` key, in the existing
    three-field shape, and only when `transition_reason` is set — which nothing writes. (F1 is the
    exception, and it is not in that category: it changes an existing row's output.)
  - **Anti-vacuity.** Mutating `resolve_transition_reason_label` to `return None` kills **9 of 25**
    new tests; restoring returns 25/25. Matches the implementer's claim exactly.
  - **Query-count listener genuinely counts.** Deleting the
    `reason_ids = reason_ids - transition_labels.keys()` line in `_load_pause_reasons_lookup`
    (i.e. reverting to a per-row catalog lookup) makes
    `test_transition_reason_labels_cost_no_extra_query` fail. The listener is not decorative.
  - **Full suite by failure node set, run by the reviewer.** Baseline `git worktree` at `HEAD`
    (`c3d6e7b`) with all of `app/.env*` copied in: **27 failed / 1338 passed**. Working tree:
    **27 failed / 1363 passed**. `diff` of the two `FAILED` node lists: **identical**. The +25 is the
    new tests. Both trees were run on an already-dirty shared database, which is why both show 27
    rather than the recorded clean-tree 24 — consistent with the double-run artifact the plan and
    the review prompt both describe.
  - **Label parity.** `"Ended shift"` / `"Other task priority"`, both `BLOCKER`,
    `is_system_managed=true`, reproduce the database verbatim. The `image_url: None` decision and its
    phase-3 consequence are correctly flagged rather than silently absorbed.
  - **T6 escalation confirmed at source.** `frontend/packages/pause-reasons/src/types.ts` does carry
    `slug: z.string()` — required and non-nullable. The escalation was right and the amended ruling
    follows from it.
  - **One map, correct layer.** `_TRANSITION_REASON_LABELS` exists only in
    `domain/transitions/labels.py`. `services/queries/` imports `domain/`, never `services/infra/`.
    `labels.py` importing `domain/pause_reasons/enums.py` is cross-*domain*, not cross-*layer*, and
    matches prevailing practice inside `domain/` (e.g. `app_update_presentations` ←
    `domain/roles/enums.py`) — not a violation of `01_architecture.md:43`.
  - **T7 scope respected.** `manually_recorded`, the `changed_by_id` heuristic and the
    `startswith(CLIENT_ID_PREFIX)` expression are byte-identical. A guard was added *above* the
    `startswith` branch in `pause_reason_reference_is_unresolved`; the branch itself is unmodified
    and the guard is unreachable while nothing writes the column. Not a scope violation.
  - **`"unspecified"` still resolves** — asserted in the new kiosk test and in the existing
    `test_pause_reasons_resolves_every_timeline_key_including_unspecified`, which is unmodified and
    green.
  - **Not re-verifiable:** the `IntegrityError` reproduction. Its disposable database
    (`beyo_str_repro_tmp`) was correctly dropped, so the run cannot be replayed. The mechanism is
    present (`models/tables/pause_reasons/pause_reason.py:47` —
    `Index("uq_pause_reasons_slug", "slug", unique=True)`, global, not workspace-scoped) and is
    independently corroborated by two suite nodes failing through it on a second consecutive run.
    Accepted as reported.

  **Verdict: NEEDS_CHANGES.** F1 alone blocks — it is a proven behaviour change in a phase whose
  entire deployability argument is that there is none, on an input class with 12 live rows. F2 and
  F3 are inventory defects, which this phase's own framing makes blocking-class: three later phases
  inherit the inventory, and incomplete or irreproducible evidence is a defect even though nothing
  is broken. F4 is a one-sentence addition. Nothing in the schema, the migration, the vocabulary,
  the layering, or the test method needs to change.
- `2026-07-31` `implementer` — **fix cycle round 1. All four findings closed. STOPPED for
  re-review.** Schema, migration, vocabulary, layering and test method unchanged, as the brief
  required.

  **F1 (blocking) — FIXED.** Confirmed from the code before touching anything: `pause_reason_objects`
  is fetched with `PauseReason.workspace_id == ctx.workspace_id`, so a step carrying a
  `pause_reason_id` from another workspace resolves to nothing; the old
  `details[0]["pause_reason"]` truthiness check was the guard that caught it, and
  `bucket_key` returning `self.reason` unconditionally dropped it. The reviewer's reading is exact.

  Fixed as directed — resolution is now structural, not incidental.
  `_StepTimelineRecord.bucket_key` takes a **required** `resolved_catalog_ids` argument and returns
  `self.reason` only if it is in that set, else `self.transition_reason`, else `None` (the caller's
  signal to fall through to the worker-level reason).
  `resolved_catalog_ids = frozenset(pause_reason_objects)` — exactly the ids `record_detail` embeds
  an object for. A caller cannot obtain a key without proving resolution first.

  The comment asserting the two reads were identical is deleted. It now states what is true: *"The
  step's catalog id is used ONLY when it resolved here — that is what `resolved_catalog_ids`
  enforces, and it is why `bucket_key` takes an argument. An id belonging to another workspace must
  never reach the output."*

  Test added: `test_breakdown_never_emits_a_catalog_id_that_did_not_resolve`. **Verified
  failing-first** against the working tree —
  `AssertionError: an unresolvable catalog id must not become the segment key`, emitting the foreign
  `par_…`. Passes after the fix, and **removing the guard again makes it fail**, so it binds to the
  guard rather than to the scenario.

  **One assertion from the brief was deliberately narrowed, with proof.** The brief asked the test
  to assert that *every* `pause_by_reason` key resolves in the sibling `pause_reasons` map. It does
  not, and never did, on **this** endpoint: the breakdown builds that map from step records only, so
  a worker-level reason with no matching step reason is unresolvable. Verified by running the exact
  scenario against the unmodified tree at `26d290d`, where the segment-key assertion **passes** and
  the map assertion **fails identically**. It is therefore pre-existing and criterion 17 forbids
  repairing it here — **logged as a finding for the operator**, and the test carries a comment
  explaining the omission. What the test does assert: the emitted key is the worker-level reason,
  the foreign id is not a `pause_by_reason` key, and the foreign id appears **nowhere** in the
  serialized response. Full key resolution *is* asserted where the published contract guarantees it
  — the kiosk endpoint, in `test_clock_out_analytics_resolves_transition_and_unspecified_keys`.

  **Same-shape sweep — F1 is a class. One instance; no others.** Re-read every touched read path
  against the diff looking specifically for a guard that looked incidental:
  - `_load_pause_reasons_lookup` — the `workspace_id` predicate is untouched; unresolvable ids still
    simply never enter the returned map. `if not reason_ids: return {}` became
    `return transition_labels`, which is `{}` when the transition set is empty. Clean.
  - `build_recorded_shift_timeline` — emits `reason` raw, and **did so before**; there was no
    resolution guard at this site to drop. The unresolved-key gap here is the same pre-existing one
    proven above. Clean (and deliberately not repaired).
  - `serialize_current_worker_shift_state` — `transition_label` is gated by
    `is_paused and pause_reason is None`, so it can only fill a slot that was already `None`, never
    displace a resolved catalog reference. The `reason_text` branch gained a condition, i.e.
    narrowed. Clean.
  - `pause_reason_reference_is_unresolved` — the early return is an addition ahead of the original
    conditions, not a relaxation of them. Clean.
  - `_load_step_timeline_records` label map — the new branch is `elif row.pause_reason_id is None`.
    This is the F1 shape's near miss: had it been `elif row.pause_reason_name is None` it would have
    admitted unresolvable ids into the map. It is keyed on the id being absent, not on resolution
    failing, so an unresolvable id still stays out of the map exactly as before. Clean.

  **F2 (medium) — re-measured quiescent; every figure now marked STABLE or VOLATILE.** The cause is
  confirmed and worth stating plainly: this database *is* the suite's database, and the first
  inventory was taken before three full-suite runs. The drift is **entirely rows in test
  workspaces** — scoped to `ws_01KVX0G0T7Z6NE69YVRVMFAB98` (the only workspace holding a catalog,
  i.e. the real dev data), **every phase-3-relevant figure reproduces exactly**: 5299 / 570 total,
  and the slug breakdown 228 / 152 / 71 / 52 / 45 / 15 / 7 unchanged. Two quiescent samples 3s apart
  were identical. Marked VOLATILE and explicitly unusable for sizing: global `workspaces`
  (1 → 531), global `step_state_records` (5299 → 5400), global `user_shift_state_records`
  (3620 → 3716), and the *unscoped* slug join (`pause_ended_shift` 152 → 157, `pause_coffee_break`
  52 → 80) — that join counts rows in any workspace pointing at the dev catalog, which is precisely
  why it drifts while the scoped form does not. One figure corrected rather than confirmed: the
  `par_…` count was 100 unscoped, 98 scoped — 2 of those rows are in test workspaces.
  **The "no free text at all" correction reproduced exactly**, scoped and unscoped: count still 0,
  the distinct set still the same 7 values, the legacy-string row count still 272. A standing
  instruction is recorded for phase 3: workspace-scoped and quiescent, or it is not evidence.

  **F3 (low/medium) — audit gap closed.** `domain/analytics/linear_timeline.py:220` and `:264` added
  to the audit as R23/R24, with their ruling: both treat `reason` as an **opaque key** and resolve
  no label, so phase 1 correctly feeds the fallback in at the composers instead. They are listed
  because this audit is phase 2's checklist and phase 2 rewrites both lines — an unlisted line is
  one phase 2 can miss.

  **F4 (low) — dispositioned, with the decision left where it belongs.** The 7 rows are all
  `step_state_records` in state `paused`, entered 2026-06-27 → 2026-07-21, **none still open**; a
  further 6 `user_shift_state_records` carry the legacy string. **No enum member added**, and the
  reasoning is recorded rather than the decision imposed: `pause_case_created` is *not* a system
  transition — the frontend selects it by slug and sends it as a `pause_reason_id` when a worker
  opens a case, which is exactly the catalog-reference case, and its row is
  `is_system_managed = false`. **The consequence phase 3 must not miss is recorded explicitly:**
  T5 nulls *system* `pause_reason_id`s, and this is not one; nulling these 7 without a
  `transition_reason` to carry would lose their label and fail master-plan success criterion 5.
  Recommendation: phase 3 nulls only `pause_ended_shift` and `pause_other_task_priority`.
  Side finding logged for the operator — the anchor is soft-deleted and `list_pause_reasons` filters
  `is_deleted IS false`, so the frontend's slug lookup returns `undefined` today and case-created
  pauses are currently written with no `pause_reason_id` at all. That is why the count is 7 and
  static. Out of scope per the intention's scope boundary.

  **Re-validation.** Full suite compared by node set, run-2 vs run-2 so both trees face an equally
  dirty shared database: baseline `26d290d` **27 failed / 1338 passed**, working tree **27 failed /
  1364 passed** — **failure node sets identical, zero new failures**, +26 passing (the new tests).
  Three `pause_reasons` tests fail in *both* trees through the global-unique-slug collision with the
  seeded dev catalog; verified by running them against the unmodified baseline, where they fail
  identically. `ruff check` clean on all touched files. No existing test modified.
- `2026-07-31` `independent-reviewer` — **round 2 (fix verification): APPROVED.** All four round-1
  findings verified closed **by execution**, not by reading the log. No new findings. Two
  pre-existing defects recorded below as repo health, plus one low non-blocking note.

  ---

  **1. The narrowed assertion — the narrowing REPRODUCES. Legitimate.**

  A standalone probe reproducing F1's exact scenario (step carrying a foreign workspace's
  `pause_reason_id`; worker-level shift record carrying an in-workspace catalog reason) was written
  against only the columns that exist at `26d290d`, split into two assertions, and run in **both**
  trees:

  | Assertion | working tree | unmodified `26d290d` |
  |---|---|---|
  | segment `reason` == worker-level reason | **PASS** | **PASS** |
  | every `pause_by_reason` key resolves in `pause_reasons` | **FAIL** | **FAIL** |

  At `26d290d` the failure is identical and for the identical cause: `pause_by_reason` carries the
  worker-level `par_…` id while `pause_reasons` is `{}` — the map is built from step rows only, and
  this scenario's single step row does not resolve. Evidence reproduces; the narrowing is not a
  regression being explained away. The test's inline comment states the omission accurately.

  Note the first row is also independent re-confirmation of F1's premise: at `26d290d` the old
  serialized-detail guard **did** fall through to the worker-level reason, which is exactly the
  behaviour the pre-fix `bucket_key` dropped.

  **2. The sweep — F1's class, checked independently. One instance; no second.**

  `resolved_catalog_ids = frozenset(pause_reason_objects)` is *exactly* the predicate the deleted
  guard tested: `record_detail:415` computes `pause_reason_objects.get(record.reason)` and emits the
  nested object iff that hits, so the new structural guard and the old truthiness check have
  identical extension. The fix is equivalent-by-construction, not merely equivalent-in-the-tested-case.

  Every changed conditional in the diff re-read against the F1 shape (a resolution check standing in
  as a truthiness/`None` check, or a fallback chain whose head can newly be non-`None`):

  - `_load_step_timeline_records:255` — **the branch that shipped is the safe one.** It is
    `elif row.pause_reason_id is None`, keyed on the id being *absent*. The near miss the implementer
    flagged (`elif row.pause_reason_name is None`) would have admitted unresolvable ids into the map;
    it is not what shipped. Confirmed by reading the diff.
  - `serialize_current_worker_shift_state:194-231` — `transition_label` is gated on
    `is_paused and pause_reason is None`, and the query at `get_current_worker_shift_state.py:55`
    scopes its `pause_reason` outerjoin to `ctx.workspace_id`, so the gate *is* the resolution check.
    It can only fill a slot that was already `None`; it never displaces a resolved reference. The
    `reason_text` branch gained a condition — narrowed, not relaxed.
  - `pause_reason_reference_is_unresolved:151` — early return added *ahead of* the original
    conditions. Its only non-serializer caller (`get_current_worker_shift_state.py:88`) emits a log
    warning; suppressing it for a row that resolves through the code-owned map is correct and inert.
  - `_load_pause_reasons_lookup:117-160` — transition keys are removed from `reason_ids` before the
    query and merged back; `"unspecified"` does not resolve in the map and so still reaches the
    catalog query exactly as before. The legacy slug strings in `UserShiftStateRecord.reason`
    (`pause_ended_shift`, …) cannot collide with the enum values (`shift_ended`, …).
  - `build_recorded_shift_timeline:60` — new middle element in the chain, head unchanged.

  **3. F1's test binds to the guard.** Reverting `bucket_key` to `return self.reason or
  self.transition_reason` (its pre-fix body) makes exactly
  `test_breakdown_never_emits_a_catalog_id_that_did_not_resolve` fail with its own message; the other
  six integration tests stay green. Restored, 26/26 green.

  **4. F2 — figures re-derived; the VOLATILE marking is honest, not a blanket disclaimer.**
  Re-run on `beyo_manager`@5433 from the recorded query text. Every figure marked **STABLE**
  reproduced **exactly**, including both figures phase 3 leans on hardest:

  - `step_state_records` scoped total / with / without → **5299 / 570 / 4729** ✓
  - scoped slug breakdown → **228 / 152 / 71 / 52 / 45 / 15 / 7** ✓ (all seven, in order)
  - the "no free text" correction → unmappable tail **0** ✓, distinct non-`par_` set still the same
    **7** values including the literal `unspecified` ✓, legacy-string count **272** ✓
  - scoped `user_shift_state_records.reason` split → **3256 / 272 / 98** ✓ (the corrected `par_`
    count of 98 confirmed)

  The VOLATILE marking discriminates correctly rather than covering for figures that do reproduce:
  under this review's own four full-suite runs the globals moved **again** — `workspaces` 531 → 843,
  `step_state_records` 5400 → 5445, `user_shift_state_records` 3716 → 3758, unscoped
  `pause_ended_shift` 157 → 160, unscoped `pause_coffee_break` 80 → 92 — while every scoped figure
  above held constant across the same runs. That is the discrimination the marking claims. The
  standing instruction for phase 3 (workspace-scoped and quiescent) is the right rule and is
  demonstrably load-bearing.

  **5. F3/F4 present and useful.** R23/R24 are in the audit with their ruling; independently
  confirmed that `compute_linear_timeline` (R24) has **zero** runtime callers — only
  `compute_linear_segments` is reached, from `_reconstruct_shift_middle.py:194` — so R23 (`:220`,
  inside `_sweep`) is the live one and both are correctly classified as opaque-key sites.

  F4's disposition is confirmed against the database in every particular: `pause_case_created` is
  `is_system_managed=false`, `is_deleted=true`, `name='Case created'`, BLOCKER, `image_url` null; the
  7 `step_state_records` are all `paused`, **none open**, entered 2026-06-27 → 2026-07-21; 6
  `user_shift_state_records` carry the legacy string; 13 rows carry the literal `'unspecified'`.
  **The T5 trap is stated where phase 3 will read it** — the master plan is a declared input in the
  phase 3 plan's metadata, phase 3's clarification 1 sends the implementer to the phase 1 volume
  report, and the disposition explicitly names the collision with phase 3's own criterion 5
  ("selecting by the three *named* rows would wrongly include this one"). That is the trap, stated
  against the precise line that would spring it.

  **Label parity re-confirmed at source:** `pause_ended_shift → "Ended shift"` and
  `pause_other_task_priority → "Other task priority"`, both BLOCKER, both `is_system_managed=true` —
  `domain/transitions/labels.py` reproduces them byte for byte.

  ---

  **Two pre-existing defects — recorded as repo health, not findings against this phase. Both
  verified pre-existing at `26d290d`.**

  - **(i) The breakdown's `pause_reasons` map does not resolve worker-level reasons.** Proven by the
    probe above: the map assertion fails identically at `26d290d`. Any segment whose key comes from
    the worker-level shift record rather than a step record is emitted unresolvable. Criterion 17
    correctly forbids repairing it here.
  - **(ii) The `pause_case_created` anchor is invisible to `list_pause_reasons`.**
    `services/queries/pause_reasons/list_pause_reasons.py:19` filters `is_deleted IS false` and is
    **byte-identical to `26d290d`** (`git diff` empty); the anchor row carries
    `deleted_at = 2026-07-28 09:53:32+00`, equal to its `created_at` — it was seeded already
    soft-deleted, purely as an FK target. So
    `use-task-step-detail.controller.ts:227` (`.find(reason => reason.slug === "pause_case_created")`)
    resolves to `undefined` and **case-created pauses are being written today with no
    `pause_reason_id` at all**. This is why the count is 7 and static, with the last row predating the
    anchor's own creation. Live data is accumulating with no reason; **phase 3's backfill will meet
    it**, and no `transition_reason` exists to carry those rows either. Worth the operator's
    attention independently of this feature set.

  **One low, non-blocking note.** The `pause_case_created` ruling lives in the master plan, but
  `PLAN_…_phase3_backfill_20260731.md` itself is unmodified and still steers the opposite way:
  clarification 3 says the row "likely needs its own member" and criterion 3 presumes one will be
  chosen. Editing a sibling phase plan is outside phase 1's remit, so this is not a finding — but the
  operator may want phase 3's clarification updated to point at the disposition before that phase is
  handed to an implementer.

  ---

  **Re-verified mechanically.**

  - **Suite, node sets, run-2 vs run-2** (both trees run twice back to back so both faced an equally
    dirty shared database; baseline `git worktree` at **`26d290d`** with all of `app/.env*` copied
    in): baseline **27 failed / 1338 passed**, working tree **27 failed / 1364 passed**. `diff` of the
    two sorted 27-node `FAILED` lists: **identical, zero new failure nodes.** +26 passing = the new
    tests. All three documented double-run artifacts present in the baseline set.
  - **Anti-vacuity, re-run because the fixes touched the resolution path.** Mutating
    `resolve_transition_reason_label` to `return None` kills **9 of 26**; restoring returns 26/26.
  - **No existing test modified** — `git status -- app/tests` still shows only the two new untracked
    paths. `ruff check` clean on all touched files.

  **Verdict: APPROVED.**

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
