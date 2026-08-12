# Phase 1 — Worker money redaction

```
plan: phase 1
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Close the existing `total_cost_minor` exposure to WORKER and SELLER identities by
making `serialize_step`'s money emission a declared, fail-closed interface field
(intention §11A.3), across the complete five-call-site census of §11A.2.
**NOT in this phase:** anything item-economics — no new tables, services, or payloads;
no change to what ADMIN/MANAGER see; no change to `worker_stats` money emission
(site 5 keeps it).

## Read first

1. `master_plan.md` §§3, 5, 6.4–6.5, 9, 10 (workflow, contracts, environment).
2. Intention §11A.1–§11A.3 (exposure predicate, verified census, boundary
   declaration, named mutations M1–M5), §10.4, card 4 + R1-5 (owner decision).
3. Contract bundle per master plan §5 (re-emit before coding); especially
   `46_serialization` + local, `28_roles_permissions`, `15_testing`.

## Dependencies

None (first phase). Independent of all schema work — that is why it runs first: it
closes a live exposure and its review cannot be entangled with new-domain defects.

## Files expected to change

- `app/beyo_manager/domain/tasks/serializers.py` (`serialize_step`, verified at
  `:152` on 2026-08-12 — line numbers below date to 2026-08-11; re-verify by symbol)
- `app/beyo_manager/services/queries/tasks/tasks.py` (call site ~`:702`, `get_task`)
- `app/beyo_manager/services/queries/tasks/list_task_steps.py` (~`:57`)
- `app/beyo_manager/services/queries/working_sections/steps_list_payload.py` (~`:320`)
- `app/beyo_manager/services/queries/working_sections/step_record_payload.py` (~`:208`)
- `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py`
  (~`:436` — site 5, passes `include_monetary=True`)
- tests (new payload/role tests; existing step-payload tests updated for the
  signature)

## Implementation tasks (ordered)

1. `serialize_step(step, *, include_monetary: bool)` — keyword-only, **no default**
   (§11A.3). When False, `total_cost_minor` is **absent from the dict** (never
   `null`).
2. Update all five call sites; each derives the flag **from the request identity at
   the query boundary** (role ∈ {ADMIN, MANAGER} ⇒ True; WORKER and SELLER ⇒ False —
   §11A.1), never from the step row. Site 5 (worker_stats, ADMIN/MANAGER-only route)
   passes True.
3. Tests per the criteria table below. No other serializer or payload changes.

## Acceptance criteria

All automated (charter rule 1). Role-per-site enumeration (§11A.2 route roles;
enumerate, never sample — charter rule 2). "money present" = `total_cost_minor` key
present with value; "money absent" = key absent (assert key ∉ dict, not `is None`).

| Row | Endpoint | Identity | Expected |
|---|---|---|---|
| 1 | `GET /tasks/{id}` | ADMIN | money present |
| 2 | `GET /tasks/{id}` | MANAGER | money present |
| 3 | `GET /tasks/{id}` | WORKER | money absent |
| 4 | `GET /tasks/{id}` | SELLER | money absent |
| 5 | `GET /tasks/{id}/steps` | ADMIN | money present |
| 6 | `GET /tasks/{id}/steps` | MANAGER | money present |
| 7 | `GET /tasks/{id}/steps` | WORKER | money absent |
| 8 | `GET /tasks/{id}/steps` | SELLER | money absent |
| 9 | `GET /working-sections/{id}/steps` | ADMIN | money present |
| 10 | `GET /working-sections/{id}/steps` | MANAGER | money present |
| 11 | `GET /working-sections/{id}/steps` | WORKER | money absent |
| 12 | `GET /working-sections/steps/user-last-active` | ADMIN | money present |
| 13 | `GET /working-sections/steps/user-last-active` | MANAGER | money present |
| 14 | `GET /working-sections/steps/user-last-active` | WORKER | money absent |
| 15 | `GET /worker-stats/{user_id}/daily-steps` | MANAGER | money **present** (the anti-blanket-redaction row) |
| 15b | `GET /worker-stats/{user_id}/daily-steps` | ADMIN | money present |
| 16 | direct call `serialize_step(step)` with no keyword | — | raises `TypeError` |

Each redacted row's fixture gives the step a non-NULL `total_cost_minor`, so absence
can only come from redaction (sole-predicate companion, rule 2).

**Named mutations (intention §11A.3 table — file + definition-vs-call-site; each must
turn the listed row red):**

- M1: default `include_monetary=True` in `domain/tasks/serializers.py::serialize_step`
  (definition) → row 16.
- M2: hardcode `include_monetary=True` at the `get_task` call site → rows 3, 4.
- M3: same at the `list_task_steps` call site → rows 7, 8.
- M4: same at the `steps_list_payload` call site → row 11.
- M5: same at the `step_record_payload` call site → row 14.

Row 15 bites on the complementary mutation (blanket `False` at site 5).

## Notes

- Site 4 is the worker's live step card (`LastActiveStepCard.tsx`) — the most
  frequently fetched worker payload; a frontend smoke after deploy is a coordinator
  note, not a criterion.
- SELLER exclusion is the ratified round-3 unilateral resolution 2 (R4-3) — not
  revisitable here.
- Archgraph: orient on `table-task-step`; expected delta ≈ zero new nodes (this is
  evidence-level change to existing payload behavior) — record the zero-delta
  statement explicitly at close.
- Criteria amendment 2026-08-12 (coordinator fold, rule 2): row 15b added — site 5's
  route admits ADMIN and MANAGER (`routers/api_v1/worker_stats.py:133`, verified);
  the table previously sampled MANAGER only. Row numbering preserved (M1 cites row 16).

## Review log

(append-only; implementer and reviewer entries land here)
