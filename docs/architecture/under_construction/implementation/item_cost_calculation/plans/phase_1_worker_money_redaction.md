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
(intention §11A.3), across the complete census of §11A.2 **as corrected by the
round-5 amendment: five call expressions, EIGHT endpoints** (two shared builders
serve three endpoints beyond the round-3 table).
**NOT in this phase:** anything item-economics — no new tables, services, or payloads;
no change to what ADMIN/MANAGER see; no change to money emission on the two
ADMIN/MANAGER-only worker-stats endpoints (site 5 and endpoint 8 keep it); no change
to `serialize_item`'s item-money fields (owner projection card 1, 2026-08-12 → R5-2:
that exposure remains until phase 6 removes the columns).

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
  (~`:436` — site 5)
- **Deliberately NOT changing** (projection D1/D2, design (a)): the three round-5
  endpoint query services (`task_step_acknowledgments/list_reassigned_steps.py`,
  `task_step_acknowledgments/list_pending_step_acknowledgments.py`,
  `worker_stats/list_workers_last_interacted_step.py`) — they inherit correct
  behavior from the builders. An edit to any of them is out of perimeter.
- Existing tests that break under the new signature (projection D8; both named,
  handling pinned in Notes):
  `tests/integration/services/queries/analytics/test_ended_shift_bucket_collapse.py:1019`
  and `tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py`
- tests (new payload/role tests per the criteria table)

## Implementation tasks (ordered)

1. `serialize_step(step, *, include_monetary: bool)` — keyword-only, **no default**
   (§11A.3). When False, `total_cost_minor` is **absent from the dict** (never
   `null`).
2. **One shared pure helper** beside `serialize_step` deriving the flag from the role
   name, written as an **allow-list**: `role_name in {ADMIN, MANAGER} ⇒ True`,
   anything else — including WORKER, SELLER, and an absent/unknown `role_name`
   (`ServiceContext.role_name` defaults to `""`) — ⇒ False (projection D6). The
   deny-list form is forbidden.
3. Derive the flag via that helper **uniformly at every derivation point — no
   hardcoded booleans anywhere, site 5 included** (projection D5): sites 1 and 2 in
   their query services from the request identity; sites 3 and 4 **once inside each
   shared builder** from the `ctx` parameter the builders already receive (design (a),
   projection D2 / intention §11A.2 round-5 correction), so the three round-5
   endpoints inherit redaction (6, 7) and retention (8) with zero changes to their
   query services. If threading a parameter into a builder is ever preferred instead,
   it must be keyword-only with no default — but design (a) is the decided form.
4. Tests per the criteria table below. No other serializer or payload changes.

## Acceptance criteria

All automated (charter rule 1). Role-per-endpoint enumeration over the corrected
eight-endpoint census (§11A.2 incl. round-5 rows; enumerate, never sample — charter
rule 2). "money absent" = `total_cost_minor` key absent (assert key ∉ dict, not
`is None`); "money present" = the key present **and equal to the distinctive non-NULL
value the fixture seeded** — `total_cost_minor` is nullable, so presence alone proves
nothing (projection D4).

**Harness (projection D3):** every (endpoint × identity) row is a
**query-service-level integration test** — hand-built
`ServiceContext(identity={"role_name": ...})`, the query service called directly, a
real `TaskStep` ORM instance seeded via `flush()` on the rolled-back `db_session`
fixture (never committed; rule 11½ satisfied structurally). The repo's router-test
idiom (stubbed `run_service`) is **forbidden for these rows** — under it, mutations
M2–M5 never bite. Route *admission* (which roles reach each endpoint) is a documented
fact evidenced by the `require_roles` citations in §11A.2's tables, not by HTTP
tests. The "Endpoint" column below therefore names the surface whose query service
the row exercises.

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
| 17 | `GET /task-step-acknowledgments/reassigned-steps` | ADMIN | money present |
| 18 | `GET /task-step-acknowledgments/reassigned-steps` | MANAGER | money present |
| 19 | `GET /task-step-acknowledgments/reassigned-steps` | WORKER | money absent |
| 20 | `GET /task-step-acknowledgments/pending` | ADMIN | money present |
| 21 | `GET /task-step-acknowledgments/pending` | MANAGER | money present |
| 22 | `GET /task-step-acknowledgments/pending` | WORKER | money absent |
| 23 | `GET /worker-stats/last-interacted-steps` | ADMIN | money present (anti-blanket row) |
| 24 | `GET /worker-stats/last-interacted-steps` | MANAGER | money present (anti-blanket row) |
| 25 | direct call to the derivation helper (or any row-8-style query) with identity whose `role_name` is absent/unknown (`""`) | — | money absent (the allow-list row, projection D6) |

Rows 17–24 are the round-5 census endpoints (intention §11A.2 correction). Each
redacted row's fixture gives the step a non-NULL `total_cost_minor`, so absence can
only come from redaction; each present row asserts equality against its seeded value
(sole-predicate companion, rule 2 + D4).

**Named mutations (intention §11A.3 table as extended by the §11A.2 round-5
correction — file + definition-vs-call-site; each must turn the listed rows red):**

- M1: default `include_monetary=True` in `domain/tasks/serializers.py::serialize_step`
  (definition) → row 16. (Row 16's test calls the function directly — a routed test
  cannot catch this.)
- M2: hardcode `include_monetary=True` at the `get_task` call site → rows 3, 4.
- M3: same at the `list_task_steps` call site → rows 7, 8.
- M4: hardcode `True` at `build_steps_list_payload`'s flag derivation (the builder,
  design (a)) → rows 11 **and 19**.
- M5: hardcode `True` at `build_step_record_payload`'s flag derivation → rows 14
  **and 22**.
- M6: flip the derivation helper from allow-list to deny-list
  (`not in {worker, seller}`) → row 25.

Rows 15/15b bite on blanket `False` at site 5's derivation; rows 23/24 bite on
blanket `False` at `build_step_record_payload`'s derivation (the retention side of
M5's builder).

## Notes

- Site 4 is the worker's live step card (`LastActiveStepCard.tsx`) — the most
  frequently fetched worker payload; a frontend smoke after deploy is a coordinator
  note, not a criterion.
- SELLER exclusion is the ratified round-3 unilateral resolution 2 (R4-3) — not
  revisitable here.
- **Owner decision (projection card 1 → R5-2, 2026-08-12):** the item-money exposure
  (`item_value_minor`/`item_cost_minor`/`item_currency` via `serialize_item` on
  worker-reachable task payloads) stays until phase 6 removes the columns. Phase 1
  touches `serialize_item` in no way; "money absent" means exactly the
  `total_cost_minor` key, nothing broader.
- **Existing-test handling (projection D8):**
  `test_ended_shift_bucket_collapse.py:1019` calls `serialize_step(step)`
  positionally — minimum edit only: add the keyword, change no assertion (it is a
  characterization test of an earlier project's published-names criterion).
  `test_list_working_section_steps_payload_characterization.py` asserts set-equality
  of `_STEP_KEYS` under a `"role_name": "worker"` context and **will fail on the
  redaction**: re-parametrize it by role (worker → `total_cost_minor` absent,
  manager → present with value) rather than deleting the key from the set, and record
  the key-set change in this Review log so the reviewer reads it as authorized.
- **Contract note (projection D7, recorded in master plan §5):** `46_serialization`'s
  router-owned-serialization rule diverges from the entire existing task/
  working-section query layer; phase 1 **keeps serialization at the query layer**,
  matching the code it modifies. Re-emitting the contract bundle must not be read as
  license to relocate serialization — that would blow the perimeter. The local
  contract file records the divergence in phase 9's drift batch.
- Archgraph: orient on `table-task-step`; expected delta ≈ zero new nodes (this is
  evidence-level change to existing payload behavior) — record the zero-delta
  statement explicitly at close.
- Criteria amendment 2026-08-12 (coordinator fold, rule 2): row 15b added — site 5's
  route admits ADMIN and MANAGER (`routers/api_v1/worker_stats.py:133`, verified);
  the table previously sampled MANAGER only. Row numbering preserved (M1 cites row 16).

## Review log

(append-only; implementer and reviewer entries land here)
