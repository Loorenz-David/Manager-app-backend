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
- `app/beyo_manager/domain/item_economics/serializers.py` (new — the config-surface
  serializers; projection S8, registered in §6.5)
- `routers/api_v1/item_economics.py` (new; config routes only this phase) +
  `routers/api_v1/__init__.py` registration; `routers/README.md` OpenAPI mirror rows
- tests

## Implementation tasks (ordered)

1. Group CRUD (ADMIN/MANAGER; audit; soft delete; name partial unique).
   Membership add/remove per §4.2 (INV-G1; `ITEM_COST_SECTION_ALREADY_GROUPED` on
   both paths per registry §6.4). Membership is analytic attribution only — no
   selection logic reads it (R-8).
2. **Request canonicalization first (R11-1 / projection B1 — owner: round-then-
   derive):** every request numeric destined for a `Numeric` column is quantized to
   the column's exact scale (`ROUND_HALF_EVEN`) **in the request model**, before
   any derivation reads it — `monthly_paid_hours` → 2 dp,
   `planning_utilization_percent` → 2 dp, `percent_value` → 3 dp. (The S4 forward
   item — `Decimal(str(v))` parsing — is SEPARATE and does not close this; both are
   criteria.) Then `create_production_cost_basis_version`: admission per **§7A.4's
   full table**; chain construction per **§7A.1** (S1 close-if-open, S2 insert;
   config chains have no S3); derived rate via
   `calculate_cost_per_worker_minute` **from the canonicalized inputs**, persisted
   verbatim (it already returns the quantized 4-dp value — projection N7's
   in-phase half; the consumption half is forwarded to phase 5); quantized-zero →
   `ITEM_COST_RATE_UNDERFLOW` (§6A.6 — raised INSIDE the calculator, N8: add no
   duplicate command-side guard). `create_cost_model_version`: same admission and
   chain; **the request carries the complete term set — full replacement, nothing
   is copied forward from the closed version, and an empty term list is legal**
   (S9; §6A.5's empty-set semantics); terms per §6A.4 (typed columns, per-type
   nullability, A5, unique names); no term mutation commands.
3. **Race handling per §7A.2 — the index-name discrimination idiom (projection
   B2):** flush inside `maybe_begin`; catch `IntegrityError` **discriminating on
   the violated index name in `exc.orig`** (precedent:
   `services/commands/users/update_user_admin.py:115-123`), mapping each index to
   its registered identity — `uix_*_versions_open` → the chain's
   `ITEM_COST_CONCURRENT_*` (`ConflictError`), `uix_cost_model_terms_purchase_cost`
   → `ITEM_COST_PURCHASE_TERM_DUPLICATE`, `uix_cost_model_terms_name_active` →
   `ITEM_COST_TERM_NAME_TAKEN`, `uix_production_cost_groups_name_active` →
   `ITEM_COST_GROUP_NAME_TAKEN` — and **re-raising anything unrecognized**. The
   blanket wrap-everything idiom (`create_email_template.py`) is forbidden here: a
   duplicate-term submission must not read "concurrently modified". §7A.2's
   "never caught" means never *swallowed* — the conversion catch is required.
4. Guarded deletes per **§7A.6/§7.5**: version delete takes `SELECT … FOR UPDATE`
   on the version row and re-runs the reference-existence check inside the lock
   (identities `ITEM_COST_BASIS_VERSION_IN_USE` / `ITEM_COST_MODEL_VERSION_IN_USE`);
   **the reference predicate counts ALL `item_cost_evaluations` rows holding the
   FK — any kind, deleted or not** (projection N3 pin: history existed, the
   escape hatch is only for truly-unreferenced versions); group delete guarded on
   non-deleted basis versions / active (`removed_at IS NULL`) memberships
   (`ITEM_COST_GROUP_IN_USE`). Note: the lock's genuine counterparty (§7B.1's
   `FOR SHARE` commit path) ships in phase 7 — see C6's split mutations.
5. Pure classifier `resolve_economics_configuration(...)` implementing §7A.5's
   ordered rows over caller-loaded rows, **precedence from an explicit ordered
   sequence in `configuration.py` — NEVER from iterating `EconomicsStatusEnum`**
   (projection B6: the shipped declaration order is wrong, and C8's fixtures
   cannot detect iteration because the first four members coincide — the guard is
   structural, see C8's probe); also `is_applicable(version, on_date)` (§7A.3,
   registry §6.5); `get_economics_configuration_status` loads and returns
   `{group_count, has_cost_group, has_open_basis_version,
   has_open_cost_model_version, evaluable, first_failure}` — `first_failure` is
   **`None` when evaluable** (N2 pin).
6. Request docs for `percent_value` carry the pinned R4-2 wording — **on the
   ROUTER body model** (projection S4: OpenAPI renders only the router layer's
   descriptions; a command-model description satisfies a string assertion while
   the API surface carries nothing) — planning allocation; never legally payable
   tax; the 25→20 gross-base example (P-D).
7. **Deliberate absence (N6):** config commands emit NO workspace event — §6.5
   registers only `item_economics:evaluation-committed` (phase 7). Divergence from
   the repo habit is intentional; do not "fix" it.

## Acceptance criteria

DB tests on production ORM instances; error identities asserted as exact leading
message tokens + class.

**Databases & harness (projection B4 — per master plan §10, stated per criterion):**
C1/C2/C4/C5/C7/C8/C9/C10/C11 run against the **configured development database at
head**, flush-only on the rolled-back `db_session` (rule 11½ by construction).
**C3 and C6's concurrency rows** need genuinely concurrent sessions and therefore
**commit**: second session from `_session_factory()` (precedent:
`tests/integration/services/commands/items/test_create_item_sku_template.py:133-135`);
seed rows committed so both sessions see them; the loser's INSERT issued while the
winner's transaction is still open (both past S1 — otherwise nothing is proven);
a hard timeout on the blocked statement (`SET LOCAL lock_timeout` or asyncio
timeout) so a deadlock cannot hang the suite; `try/finally` teardown DELETEs every
committed row (rule 11½). Monkeypatching `flush` to raise a hand-built
`IntegrityError` (`test_update_user_admin_clock_in_code.py:261-286`) does NOT
satisfy these rows. For C6's in-lock window, the delete command accepts an
injectable test-only synchronization seam (e.g. an optional `after_lock` awaitable
parameter defaulting to None) — declared in the plan so the reviewer reads it as
designed, not smuggled.

**C1 — §7A.4 admission, both chains:** all 10 rows × 2 chains = 20 rows, each with
its one exact outcome (accept, or the chain-qualified identity per registry §6.4).
No sampling. **At least one "Open version: none" row is realized via a
soft-deleted open row, not an empty chain** (projection S2 — otherwise the
`is_deleted = false` clause of the open-row lookup has no arbiter); named
mutation: "drop `is_deleted = false` from the open-row lookup at its definition
site" must redden exactly that row.

**C2 — chain adjacency (intention test 8):** creating v2 with `effective_from = d`
closes v1 at `d`; boundary rows asserted **through the registered
`is_applicable(version, on_date)` predicate** (projection S3): `is_applicable(v1,
d−1)` true, `is_applicable(v1, d)` false, `is_applicable(v2, d)` true — one row
per adjacent pair, both chains; §7A.3's theorem row: the open row is the
resolution for today.

**C3 — §7A.2 conflict path, both chains (concurrent — see the harness block):**
two sessions both past S1, both attempt S2 → afterwards exactly one row satisfies
the open predicate AND the loser's exact `ConflictError` identity
(`ITEM_COST_CONCURRENT_BASIS_VERSION` / `_MODEL_VERSION`). The application
pre-check alone does NOT satisfy this row; a monkeypatched flush does not either.

**C4 — rate rows (intention test 16 + R11-1 + N7 in-phase):**
- underflow inputs → command rejects `ITEM_COST_RATE_UNDERFLOW` AND direct insert
  violates the DB CHECK (both paths, two rows);
- **canonicalize-then-derive row (B1):** request `monthly_paid_hours = 173.456`,
  `util = 80.00`, `fixed = 100000` → stored hours `173.46` AND stored rate
  `12.0105` (derived from the canonicalized value — the raw value would give
  `12.0107`); then `rederive()` on the stored row reproduces the stored rate
  exactly (the §6A.11 theorem holds). Named mutation: "derive before quantizing
  the request inputs" must redden this row.
- **persisted-rate row (N7 in-phase half):** the persisted
  `cost_per_worker_minute_minor` equals the calculator's return verbatim, exactly
  4 dp, on a fixture whose unrounded quotient differs from the quantized one
  (seed from the phase-3 Q2 tie family). The consumption half is phase 5's.
- **derived-never-accepted row (N4 pinned):** a request smuggling
  `cost_per_worker_minute_minor` **succeeds** (pydantic `extra='ignore'` — both
  layers) and the persisted value equals the derived one; asserting a 422 here is
  wrong.
- **S4-forward row:** `Decimal(str(v))` parse proven on a request value with more
  decimals than target scale (arrives intact BEFORE canonicalization — distinct
  from the B1 row; never `Decimal(v)` on a float).

**C5 — term validation (projection S1 — TOTAL):** command-level rows mirroring the
§6A.4 12-cell matrix — 3 valid, **all 9 invalid cells enumerated** (same table as
phase 2 C3 / phase 3 C1); second `item_purchase_cost` term → 
`ITEM_COST_PURCHASE_TERM_DUPLICATE` on the app pre-check AND on the A5 DB conflict
path (registry §6.4, dual-path); duplicate term name →
`ITEM_COST_TERM_NAME_TAKEN` (both paths); term immutability: no update/delete
route exists for terms (router-surface assertion; A6). Named mutation (B2):
"collapse the index discrimination to a single blanket `except IntegrityError` →
the A5 DB-path row must redden" (it would report the wrong identity).

**C6 — §7A.6 guard race (concurrent — see the harness block; projection B5's SPLIT
mutations):** delete of a version referenced by an evaluation row → `…_IN_USE` on
the locked re-check path (serial row); the interleaved row: with the delete
transaction holding `FOR UPDATE` and paused at the injected seam, a second session
commits a referencing evaluation; the re-check inside the lock rejects. **Two
named mutations, separately declared (observed node ids):**
(a) drop the in-lock re-check, keep the lock → the serial guard row reddens;
(b) drop `FOR UPDATE`, keep the re-check → the interleaved row reddens.
Note: the lock's production counterparty (§7B.1 `FOR SHARE`) lands in phase 7 —
forward item recorded there.

**C7 — INV-G1 & group guards:** section active in a second group → identity on both
paths; group delete with non-deleted version / active membership / clean — three
rows, exact outcomes; the reference predicates per task 4's pins.

**C8 — §7A.5 via the status query:** five fixtures (rows 1–5, each the sole failing
predicate) → exact `first_failure` values
(`not_configured_no_cost_group`, `not_configured_ambiguous_cost_group`,
`not_configured_no_basis_version` for BOTH rows 3 and 4 — deliberately the same,
`not_configured_no_cost_model_version`) and a sixth all-present fixture →
`evaluable = true` **and `first_failure is None`** (N2 pin). **Structural N3
probe (B6):** the classifier's precedence is an explicit ordered sequence;
permuting `EconomicsStatusEnum`'s declaration order (in a disposable worktree)
changes NO C8 outcome — declared with the run's evidence. (A behavioral arbiter is
impossible: the first four declared members coincide with §7A.5's order.)

**C9 — P-D docs proxy (S4/S5 amended):** the `percent_value` field description ON
THE ROUTER BODY MODEL contains "planning allocation" and the
never-legally-payable-tax sentence (string assertion against the router model's
field metadata — the command-model copy does not satisfy this). The
`routers/README.md` mirror row is a **documentation task, not a criterion** (S5:
no generator exists; phase 9's C4 sweep is the backstop).

**C10 — queries & group update (projection S6):** for each of the three list
queries: workspace-scoping row (other workspace's rows invisible), `is_deleted`
filtering row, ordering row, and the `limit + 1` pagination idiom row (per
`list_working_sections.py:18-38`); `update_production_cost_group` happy path +
`ITEM_COST_GROUP_NAME_TAKEN` on rename collision (both paths).

**C11 — role gates & audit (projection S7):** per §6.5 every config route is
ADMIN/MANAGER: one WORKER-rejected and one SELLER-rejected row per route family +
ADMIN and MANAGER retention rows (P-G: retention rows get the named mutation
"removing MANAGER from the allow-list must redden every MANAGER row"); each
command writes its registered §6.4 audit event (exact event-string assertion, one
row per command).

## Notes

- Command-created versions require `effective_from ≤ today` in the UTC date frame
  (§7A.3) — same frame as resolution, so the two can never disagree.
- `monthly_paid_hours` is the **aggregate** for the group (HC-5); the UI may compute
  headcount × 160 but the API stores the total — no per-worker field exists.
- Config chains never write `superseded_by_id` (that is the evaluation/valuation
  chains' S3).
- Archgraph: orient on the phase-2 table nodes; delta = command/endpoint nodes for
  the configuration surface.
- **Delegations (projection N1/N5/N7, granted in writing):** N1 the classifier's
  signature (constraints: pure — the evaluation date is an injected parameter per
  §7A.3, no `datetime.now` inside; precedence per task 5's explicit-sequence rule);
  N5 route notation is FastAPI `/{...}` (§6.5's brackets are notation) and the
  create verb is §6.5's `POST`; N7 test placement mirrors the existing layout.
  Internal helper decomposition is free within the registry rule.
- **Recorded, no change (projection N9):** §7A.4 row 1 (NULL `effective_from` on a
  chain whose open row was soft-deleted) creates an unbounded-past open row
  overlapping closed windows — harmless under §7A.3's today-only resolution;
  future reviewers should not file it.
- **Forwarded:** N7's consumption half (later reads receive the persisted rate,
  never a re-division) → phase 5; C6's lock counterparty (§7B.1 `FOR SHARE`) →
  phase 7.

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
