# INTENTION_system_transition_reasons_20260730

## Metadata

- Intention ID: `INTENTION_system_transition_reasons_20260730`
- Status: `active`
- Owner: David (operator) — planning to be executed by a fresh session
- Created at (UTC): `2026-07-30T16:38:18Z`
- Last updated at (UTC): `2026-07-30T16:38:18Z`
- Related intention: `INTENTION_custom_pause_reasons_20260722` (this intention corrects an
  over-reach of that one — see "Relationship to the custom pause reasons intention")

## Goal

Migrate system-controlled state transitions (ended shift, auto-pause on task-switch, and any future
system transition) out of the workspace-managed `pause_reasons` catalog and into **explicit transition
semantics carried on the source records themselves**, so that system behaviour never depends on a
seeded catalog row existing in a given workspace.

## Why this matters

`INTENTION_custom_pause_reasons_20260722` correctly made *worker-selectable* pause reasons
workspace-managed data. It then went one step too far and expressed *system* transitions in the same
catalog, flagged with `is_system_managed = True` and resolved at runtime by slug lookup. The
consequence is that a core state machine transition is only as reliable as the presence of a data row
a workspace administrator can, in principle, never receive.

This is not hypothetical. Measured on the shared database at commit `de0b3b3`:

- **3132 workspaces exist; exactly 1 holds a `pause_ended_shift` row.**
- In the other 3131, `clock_out_shift_for_user` raises `NotFound("System pause reason
  'pause_ended_shift' is not configured.")` whenever the worker has an open WORKING step — i.e.
  **clock-out fails for the normal case**.
- The same applies to `pause_other_task_priority`, which means **starting a task while another task
  is active also fails** in those workspaces.

The tracing brief below records the exact mechanism that produced that 1-of-3132 state, because the
mechanism itself is evidence for the architectural argument: it is not a seeding bug that better
seeding would fix.

## Architectural direction (the thing to plan)

System-controlled transitions become a **stable, code-owned vocabulary** — an enum or constrained
string on the source state records — while `pause_reasons` remains purely a workspace-owned catalog
of things a *worker chooses*.

Target semantics:

| Case | `transition_reason` | `pause_reason_id` |
|---|---|---|
| Clock-out closing an open working step | `SHIFT_ENDED` | `NULL` |
| Auto-pause because another task took priority | `OTHER_TASK_PRIORITY` | `NULL` |
| Worker declared an off-task state | `WORKER_DECLARED_STATE` | the chosen catalog row |
| Worker paused a step with a catalog reason | `WORKER_PAUSED` (name TBD) | the chosen catalog row |

Hard requirement: **clock-out must not depend on a workspace-seeded `PauseReason` row.** The same
must become true of task switching.

Explicit non-solution: changing or scoping the unique index alone is **not** the architectural fix.
It would make seeding work per-workspace and would leave the state machine still depending on
catalog data. It may still be a necessary *supporting* change (see Finding 2) — but it is not the
answer.

## Traced evidence (do not re-derive; verify and extend)

The following was traced from `app/beyo_manager/models/tables/pause_reasons/pause_reason.py` outward
on 2026-07-30. The planning session should treat this as a starting map, confirm each item still
holds, and extend it — not spend its budget rediscovering it.

### Finding 1 — there are **two** system slugs resolved at runtime, in **three** call sites

`get_system_pause_reason_id(session, workspace_id, slug)`
([get_system_pause_reason.py](app/beyo_manager/services/queries/pause_reasons/get_system_pause_reason.py))
is the single resolution point. Its callers:

| Call site | Slug | Trigger |
|---|---|---|
| [_clock_worker_shift.py:200](app/beyo_manager/services/commands/users/_clock_worker_shift.py#L200) | `pause_ended_shift` | clock-out, only when open WORKING rows exist |
| [transition_step_state.py:274](app/beyo_manager/services/commands/task_steps/transition_step_state.py#L274) | `pause_other_task_priority` | auto-pause a conflicting step on task switch |
| [_step_transition_core.py:114](app/beyo_manager/services/commands/task_steps/_step_transition_core.py#L114) | `pause_other_task_priority` | same, batch/core path |

The `pause_other_task_priority` sites also build a free-text
`auto_pause_description = f"started working with {identifier}"`, which is a second system-authored
value riding on a user-facing field. The plan must decide where that description belongs once
`transition_reason` exists.

### Finding 2 — the root cause of 1-of-3132 is a **global** unique index, and it also breaks bootstrap

`pause_reasons.slug` carries `Index("uq_pause_reasons_slug", "slug", unique=True)` — **globally
unique, not scoped to `workspace_id`**. Two consequences, both load-bearing for the plan:

1. Seed migration `49bd666da846_seed_default_pause_reasons` inserts for
   `SELECT client_id FROM workspaces LIMIT 1` — **one arbitrary workspace** — with
   `ON CONFLICT (slug) DO NOTHING`. That is precisely how exactly one workspace ended up holding the
   rows.
2. [seed_pause_reasons.py:34-39](app/beyo_manager/services/commands/bootstrap/phases/seed_pause_reasons.py#L34-L39)
   guards existence by `(workspace_id, slug)`. For a *second* workspace the guard finds nothing,
   proceeds to INSERT, and hits the global index — so **bootstrapping a second workspace raises
   `IntegrityError`**, it does not silently no-op. Verify this; if confirmed it is a live bug
   independent of this migration and should be called out as such.

The plan should state whether the index becomes `(workspace_id, slug)` as a supporting change, and
whether `slug` survives at all once system rows are gone (see Open question 3).

### Finding 3 — `UserShiftStateRecord.reason` is the most overloaded field, with shipped proof

It holds a `par_…` catalog id for derived rows **and** free text for legacy manual pauses. The proof
is in production code: [serializers.py](app/beyo_manager/domain/users/serializers.py) disambiguates
with a literal prefix test —

```python
if is_paused and current.reason is not None and pause_reason is None:
    data["reason_text"] = (
        None
        if current.reason.startswith(f"{PauseReason.CLIENT_ID_PREFIX}_")
        else current.reason
    )
```

— and the published frontend contract consequently carries a three-way `reason_text`
(absent / string / null). A field whose type is decided by sniffing an id prefix is the clearest
single argument for this migration. Include this serializer in the tracing entry points.

### Finding 4 — a **third** legacy representation exists: `pause_case_created`

`pause_case_created` was dropped from the live default set but survives as a **soft-deleted anchor
row** seeded by migration `fb10ac7fd439`, purely so that historical
`step_state_records.reason = 'pause_case_created'` rows still backfill correctly. Both
[seed_pause_reasons.py:16-20](app/beyo_manager/services/commands/bootstrap/phases/seed_pause_reasons.py#L16-L20)
and the migration carry explicit warnings not to change one without reconciling the other.

Any historical-data migration in this plan must not corrupt that anchor. This is a hard constraint on
§6 of the analysis, not a footnote.

### Finding 5 — `pause_type` is doing double duty

`PauseTypeEnum` is `PERSONAL | BLOCKER`. Both system slugs are seeded `BLOCKER`, and decision D2 of
the declared-worker-states master plan uses `PERSONAL` as the filter for what a worker may declare.
So a *display category* is currently also the de-facto "is this worker-selectable" predicate.

Once `transition_reason` exists, "declarable" should follow from **catalog ownership** (it is in the
workspace catalog, therefore a worker can pick it), not from a display enum. Name this in the
semantic-categories analysis as a field with mixed responsibility.

### Finding 6 — `is_system_managed` is not merely a label

It is read in at least three places: [guards.py](app/beyo_manager/domain/pause_reasons/guards.py)
(`can_delete_pause_reason` returns `not pause_reason.is_system_managed` — i.e. **delete protection**),
the pause-reason serializer, and `create_pause_reason.py` (hardcoded `False`). It is also a filter
condition inside `get_system_pause_reason_id` itself.

So "does `is_system_managed` become obsolete?" has a delete-protection consequence and must be an
explicit decision, not an inference:

- If system rows disappear from the catalog entirely, the guard's purpose disappears with them.
- If they linger as display-only rows (for historical label resolution), the guard must stay.

### Finding 7 — `StepStateRecord.pause_reason_id` is a real FK with `ondelete="RESTRICT"`

Deleting a catalog row is already blocked by the database when history references it. Whatever the
migration does to existing rows must respect that, and the plan should say whether `RESTRICT` remains
appropriate once system transitions no longer point at catalog rows.

## Decisions this migration would amend

The declared-worker-states master plan
(`.../implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`) holds
binding decisions D1–D14. This migration touches at least:

- **D3** — a declared state surfaces as `IN_PAUSE` with `reason = pause_reason_id` and
  `manually_recorded = true`. Under explicit transition semantics, `reason` should stop being a
  polymorphic slot.
- **D5** — auto-pause carries the declared `pause_reason_id`. Needs restating in terms of
  `transition_reason`.
- **D14** — kiosk clock-out analytics return `pause_by_reason` keyed by reason id plus a
  `pause_reasons` label map. See Open question 1.

Additionally, the plan **must state explicitly whether `transition_reason` subsumes
`manually_recorded`**. Phase 2 of the declared-worker-states work burned four fix cycles (F1/F2, G1,
H1, I1) on provenance discrimination, eventually settling on a `changed_by_id IS NOT NULL` heuristic
to tell a worker-initiated pause from a system-derived one. A proper transition field would have made
that heuristic unnecessary. This is the concrete instance of "avoid encoding the same concept
redundantly" — treat it as a named deliverable of the analysis, not a general principle.

Per the rules of the master plan, any amendment must be proposed as a **minimal amendment with its
rationale**, not a silent rewrite.

## Sequencing against Phase 7

Phase 7 (clock-out analytics) is planned, **not yet implemented**, and its contract is already
published to the frontend in
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §5.1. It reads
`pause_by_reason` keyed by catalog reason id and resolves labels through a `pause_reasons` map.

**Recommendation: land Phase 7 first.** It is small, the frontend is blocked on it, and the migration
then has one fewer moving target — plus Phase 7's `pause_by_reason` becomes a concrete compatibility
test for the migration's read layer. The plan must state its assumed ordering either way; if it
assumes the migration lands first, it owns the change to the published contract.

## Scope boundary

- **In scope:** the transition vocabulary; the source records that carry it (`StepStateRecord`,
  `UserDeclaredStateRecord`, and the derived `UserShiftStateRecord` read path); the three runtime
  slug call sites; catalog ownership and the constraints that enforce it; historical data migration;
  API/frontend compatibility for the fields this touches.
- **Out of scope:** unrelated cleanup discovered en route (log it, do not fold it in); redesigning
  the shift-state system as a whole; the derived-table rebuild algorithm itself, except where
  provenance discrimination (`manually_recorded`) is directly implicated.
- **Non-goals:** treating the unique index change as the architectural solution; changing what
  workers can declare; touching the Connecteam path or the midnight safeguard.

## Success criteria

1. Clock-out succeeds in a workspace that holds **zero** `pause_reasons` rows, with an open WORKING
   step, and the resulting record is unambiguously identifiable as a shift-ended transition.
2. Task switching auto-pauses a conflicting step in that same zero-catalog workspace.
3. `get_system_pause_reason_id` has **no runtime callers** (or is deleted).
4. No field in the shift/step state model requires prefix-sniffing to determine its meaning; the
   `startswith(CLIENT_ID_PREFIX)` branch in `domain/users/serializers.py` is gone or provably dead.
5. Historical rows — including `pause_case_created` anchored history — resolve to the same
   human-visible labels after migration as before.
6. Bootstrapping a second workspace succeeds.

## Instructions for the planning session

**Do not implement any code.** Produce a plan only, then stop. Implementation begins only after the
plan is reviewed and explicitly approved.

Required analysis sections:

1. **Semantic categories** — which reasons are system-controlled vs. worker-chosen, and which fields
   currently conflate the two (Findings 3, 5, 6).
2. **Source-of-truth tables** — which records must carry `transition_reason`, and which are derived
   and must merely read it.
3. **Transition vocabulary** — the proposed enum/constrained-string values, plus an explicit ruling
   on whether it subsumes `manually_recorded`.
4. **API and frontend compatibility** — every published contract field affected, with the ordering
   decision against Phase 7 stated.
5. **DB constraints and catalog ownership** — the unique index, the `RESTRICT` FK, `is_system_managed`
   and its delete-protection consequence, and the bootstrap `IntegrityError` (Finding 2).
6. **Historical data migration** — including the `pause_case_created` anchor constraint (Finding 4)
   and the fact that only 1 of 3132 workspaces holds system rows, so "backfill from the catalog" is
   not available as a general strategy.
7. **Runtime invariants** — what must remain true during a partial deploy, given that source records
   are written continuously.
8. **Tests** — what proves the migration, including a zero-catalog-workspace probe as a first-class
   test rather than an edge case.

Then a **phased plan** (~10 phases suggested), each phase independently deployable and validated,
following `docs/architecture/under_construction/implementation/TEMPLATE_PLAN.md`, with the
review-first gate: implement → validate → review-log entry → STOP for independent review. Summary and
archive happen only after reviewer approval. Do not carry acceptance criteria that instruct the
implementer to flip liveness rows in an operator-owned handoff.

Where the migration changes a binding decision of the declared-worker-states master plan, identify
the decision by number and propose the **minimal** amendment.

## Open questions

1. **Phase 7 ordering** — does Phase 7 land first (recommended), or does the migration own the
   published `pause_by_reason` contract change? Impact if unresolved: the frontend either waits on a
   larger piece of work than necessary, or ships against a key that moves under it.
2. **Do system rows leave the catalog entirely, or linger display-only?** Impact: determines whether
   `is_system_managed` and `can_delete_pause_reason` survive, and whether historical label resolution
   needs a code-owned label map.
3. **Does `slug` survive?** Its only current purpose is system-row lookup. If system rows leave the
   catalog, `slug` and `uq_pause_reasons_slug` may both be removable — which resolves Finding 2
   without a scoping migration. Impact: changes the shape of the DB work substantially.
4. **Where does `auto_pause_description` ("started working with …") belong** once the transition is
   typed? Impact: it is currently system-authored text in a field the contract presents as
   user-facing.

## Relationship to the custom pause reasons intention

`INTENTION_custom_pause_reasons_20260722` is archived and its outcome largely stands: workspace-owned
pause reasons with CRUD were the right call. What this intention reverses is one specific line of
that one's stated outcome — *"the two system-triggered reasons remain protected (cannot be deleted,
resolved by a stable internal identifier)"*. Resolving them by slug **is** the stable internal
identifier it promised, and it is exactly what failed. The correction is that system transitions
should never have been catalog rows at all.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved` (all success criteria met) or `superseded`
- Transition trigger: all phases of the linked implementation plan archived with reviewer approval,
  and success criterion 1 verified against a real zero-catalog workspace.

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| _(none yet)_ | — | — | To be produced by the planning session per "Instructions for the planning session" |

## Progress notes

- 2026-07-30: Intention filed. Tracing from `pause_reason.py` produced Findings 1–7 above; the
  1-of-3132 measurement was taken at commit `de0b3b3` and is recorded in the declared-worker-states
  master plan's "Repository validation baseline" section. No code changed. Planning deferred to a
  fresh session.
