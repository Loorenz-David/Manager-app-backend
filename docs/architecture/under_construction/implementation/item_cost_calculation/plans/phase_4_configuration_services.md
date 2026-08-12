# Phase 4 — Configuration services

```
plan: phase 4
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Ship the manager-facing economics configuration: cost groups + section membership,
the two effective-dated version chains with their races and guarded deletes, the
pure §7A.5 selection classifier, and the configuration-status query.
**NOT in this phase:** valuations, evaluations, results, or any read of items/tasks;
no term edit/delete commands exist at all (A6).

## Read first

1. `master_plan.md` §§5, 6 (registry: names, routes, error identities), 9, 10.
2. Intention §4.1–§4.4 (+§4A A1–A6), §7.1, §7.4, §7.5, **§7A entire** (chains,
   races, resolution, admission, selection, deletion-guard race), §6A.6 (underflow),
   §6A.4 + R4-2 (percent semantics — the API field docs duty lands here), §11
   (configuration surface), §11A.4 (status vocabulary).
3. Contracts: `06_commands`+local, `07_queries`+local, `09_routers`,
   `28_roles_permissions`, `32_concurrency`, `36_audit_log`, `05_errors` (+ core).

## Dependencies

Phase 3 APPROVED (rate derivation calls the calculator).

## Files expected to change

- `app/beyo_manager/domain/item_economics/configuration.py` (new — pure §7A.5
  ordered classifier over loaded rows)
- `app/beyo_manager/services/commands/item_economics/` — the seven config commands +
  `requests/__init__.py` (registry §6.5)
- `app/beyo_manager/services/queries/item_economics/` —
  `get_economics_configuration_status.py`, `list_production_cost_groups.py`,
  `list_production_cost_basis_versions.py`, `list_cost_model_versions.py`
- `routers/api_v1/item_economics.py` (new; config routes only this phase) +
  `routers/api_v1/__init__.py` registration; `routers/README.md` OpenAPI mirror rows
- tests

## Implementation tasks (ordered)

1. Group CRUD (ADMIN/MANAGER; audit; soft delete; name partial unique).
   Membership add/remove per §4.2 (INV-G1; `ITEM_COST_SECTION_ALREADY_GROUPED` on
   both paths per registry §6.4). Membership is analytic attribution only — no
   selection logic reads it (R-8).
2. `create_production_cost_basis_version`: admission per **§7A.4's full table**;
   chain construction per **§7A.1** (S1 close-if-open, S2 insert; config chains have
   no S3 — close columns are `effective_to` only); derived rate via the calculator
   (never accepted from the request — the schema has no such field); quantized-zero
   → `ITEM_COST_RATE_UNDERFLOW` (§6A.6). `create_cost_model_version`: same admission
   and chain; terms created with the version per §6A.4 (typed columns, per-type
   nullability, A5 one purchase-cost term, unique names); no term mutation commands.
3. Race handling per **§7A.2**: no isolation-level changes; the partial unique is
   the arbiter; `IntegrityError` surfaces as `ConflictError` with the chain's
   identity — never caught, retried, or logged-and-continued.
4. Guarded deletes per **§7A.6/§7.5**: version delete takes `SELECT … FOR UPDATE`
   on the version row and re-runs the reference-existence check inside the lock
   (identities `ITEM_COST_BASIS_VERSION_IN_USE` / `ITEM_COST_MODEL_VERSION_IN_USE`);
   group delete guarded on live basis versions / active memberships
   (`ITEM_COST_GROUP_IN_USE`).
5. Pure classifier `resolve_economics_configuration(...)` implementing §7A.5's
   ordered rows over caller-loaded rows; `get_economics_configuration_status` loads
   and returns `{group_count, has_cost_group, has_open_basis_version,
   has_open_cost_model_version, evaluable, first_failure}` with `first_failure`
   drawn from `EconomicsStatusEnum`.
6. Request docs for `percent_value` carry the pinned R4-2 wording (planning
   allocation; never legally payable tax; the 25→20 gross-base example) — master
   plan rule P-D.

## Acceptance criteria

DB tests on production ORM instances; error identities asserted as exact leading
message tokens + class.

**C1 — §7A.4 admission, both chains:** all 10 rows × 2 chains = 20 rows, each with
its one exact outcome (accept, or the chain-qualified identity per registry §6.4).
No sampling.

**C2 — chain adjacency (intention test 8):** creating v2 with `effective_from = d`
closes v1 at `d`; boundary rows `applicable(v1, d−1)` true, `applicable(v1, d)`
false, `applicable(v2, d)` true — one row per adjacent pair, both chains; §7A.3's
theorem row: the open row is the resolution for today.

**C3 — §7A.2 conflict path, both chains:** two sessions both past S1, both attempt
S2 → afterwards exactly one row satisfies the open predicate AND the loser's exact
`ConflictError` identity (`ITEM_COST_CONCURRENT_BASIS_VERSION` /
`_MODEL_VERSION`). The application pre-check alone does NOT satisfy this row
(charter rule 2, error-contract clause).

**C4 — rate rows (intention test 16):** underflow inputs → command rejects
`ITEM_COST_RATE_UNDERFLOW` AND direct insert violates the DB CHECK (both paths, two
rows); a request smuggling `cost_per_worker_minute_minor` does not influence the
persisted derived value (derived-never-accepted row, §5).

**C5 — term validation:** command-level rows mirroring 6A.4 (3 valid, 5 invalid);
second `item_purchase_cost` term → rejected on the app path AND the A5 partial
unique on the DB conflict path; term immutability: no update/delete route exists for
terms (test asserting the router exposes no term mutation route; A6).

**C6 — §7A.6 guard race:** delete of a version referenced by an evaluation row
(fixture inserts an `ItemCostEvaluation` ORM row referencing it — the table exists
since phase 2) → `…_IN_USE` on the locked re-check path; a concurrent
delete-vs-reference test: with the delete transaction holding `FOR UPDATE`, a
reference that commits first causes the re-check to reject. Named mutation:
removing the `FOR UPDATE` + in-lock re-check at its definition site
(`delete_production_cost_basis_version.py`) must turn this row red.

**C7 — INV-G1 & group guards:** section active in a second group → identity on both
paths; group delete with live version / active membership / clean — three rows,
exact outcomes.

**C8 — §7A.5 via the status query:** five fixtures (rows 1–5, each the sole failing
predicate) → exact `first_failure` values
(`not_configured_no_cost_group`, `not_configured_ambiguous_cost_group`,
`not_configured_no_basis_version` for BOTH rows 3 and 4 — deliberately the same,
`not_configured_no_cost_model_version`) and a sixth all-present fixture →
`evaluable = true`.

**C9 — P-D docs proxy:** the `percent_value` request-field description contains
"planning allocation" and the never-legally-payable-tax sentence (string assertion
on the schema's field metadata); OpenAPI mirror row updated (reviewer-checked).

## Notes

- Command-created versions require `effective_from ≤ today` in the UTC date frame
  (§7A.3) — same frame as resolution, so the two can never disagree.
- `monthly_paid_hours` is the **aggregate** for the group (HC-5); the UI may compute
  headcount × 160 but the API stores the total — no per-worker field exists.
- Config chains never write `superseded_by_id` (that is the evaluation/valuation
  chains' S3).
- Archgraph: orient on the phase-2 table nodes; delta = command/endpoint nodes for
  the configuration surface.

**Forward items routed here (coordinator, 2026-08-12):**
- Phase-2 review N3: `EconomicsStatusEnum`'s declaration order ≠ §11A.4's
  evaluation order — the §7A.5 ordered classifier must NOT derive precedence by
  iterating the enum.
- Phase-3 projection S4: the `Decimal(str(v))` request-layer parse criterion moved
  here — this phase ships the first request schemas; prove the parse on a value
  with more decimals than target scale (never `Decimal(v)` on a float, §6A.1).
- Phase-3 review N7: C2's "Q3 consumes the persisted rate" cannot bite inside the
  pure module (the rate arrives as a parameter). **The real arbiter lands here**:
  when this phase wires basis-version creation, a criterion must prove the
  persisted (quantized) `cost_per_worker_minute_minor` — not the raw division —
  is what later calls receive.

## Review log

(append-only)
