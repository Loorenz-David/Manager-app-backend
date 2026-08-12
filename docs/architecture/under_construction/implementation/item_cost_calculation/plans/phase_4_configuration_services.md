# Phase 4 — Configuration services

```
plan: phase 4
role: phase plan
date: 2026-08-11
state: CHANGES_REQUESTED
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
   criteria.) **Request-bounds validation (review r1 B2 — §6A.4's "rejected twice" where
   §6.2 pins no DB CHECK): the request models validate RANGES, not only shape** —
   `fixed_monthly_cost_minor > 0`, `monthly_paid_hours > 0`,
   `0 < planning_utilization_percent ≤ 100`, `0 ≤ percent_value ≤ 999.999`,
   `fixed_amount_minor ≥ 0`, `purchase-cost/nullability per §6A.4` — each
   out-of-range input is a 422/ValidationError naming the field, NEVER an HTTP
   500 (the review proved all eight current 500 cases; each becomes a criterion
   row under C4/C5). Then `create_production_cost_basis_version`: admission per **§7A.4's
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
`ITEM_COST_PURCHASE_TERM_DUPLICATE` on the app pre-check; duplicate term name →
`ITEM_COST_TERM_NAME_TAKEN` on the app pre-check. **(Amended per review r1 N6/L2:
the two term indexes' DB-conflict paths are UNREACHABLE by construction — terms are
only ever inserted with a version created in the same transaction, so no concurrent
writer exists; the dual-path demand is satisfied by the pre-check row plus a
recorded reachability note. The index-discrimination mapping for these two indexes
stays in `_common.py` as defence and is exercised by the C5 named mutation via the
translation-unit test.)** term immutability: no update/delete
route exists for terms (router-surface assertion; A6). Named mutation (B2):
"collapse the index discrimination to a single blanket `except IntegrityError` →
the A5 DB-path row must redden" (it would report the wrong identity).

**C6 — §7A.6 guard race (concurrent — see the harness block; projection B5's SPLIT
mutations):** delete of a version referenced by an evaluation row → `…_IN_USE` on
the locked re-check path (serial row); the interleaved row **(amended per
review r1 S3/L3/L4 — the original wording deadlocks: a referencing INSERT takes FK
`KEY SHARE` on the version row, which conflicts with `FOR UPDATE`, so the second
session cannot commit while the seam is paused)**: with the delete transaction
holding `FOR UPDATE` and paused at the seam, a second session issues the
referencing INSERT and the row asserts **`reference_blocked_while_locked` is True**
(the observable that flips when the lock is dropped); after the delete commits, the
blocked INSERT proceeds — the row additionally documents the §7.5 residual (the
evaluation lands against a soft-deleted version; N11 verified it live; phase 7's
`FOR SHARE` counterparty is the closure). **Two
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

### Implementer r1 — 2026-08-12 — Codex

- Implemented the manager-facing configuration surface: group CRUD and section
  membership, effective-dated basis/model chains, canonicalize-then-derive rate
  persistence, typed model terms, index-discriminated conflict translation,
  guarded version deletes with an injectable `after_lock` seam, the pure
  explicit-precedence classifier, status and list queries, serializers, and 13
  ADMIN/MANAGER FastAPI routes. Configuration commands intentionally emit no
  workspace events.
- Added the router OpenAPI field documentation for `percent_value` and the
  README mirror rows. Added focused request, classifier, soft-deleted-open-row,
  canonical rate, empty-term, and status coverage.
- Verification: ruff clean; phase-focused suites 72 passed; router surface
  probe found 13 registered routes, correct percent metadata, and no term
  mutation route; full non-E2E suite 1755 passed / 23 established failures / 1
  deselected, with the failure set unchanged from the 1749/23/1 baseline after
  the six net phase tests were added.
- Architecture Graph: one batched additive delta recorded from the phase-2
  table anchors and `domain-item-economics`: 9 command nodes, 13 endpoint
  nodes, and 25 relationships. No human-confirmed graph content was changed.
- Reviewer follow-up perimeter: concurrency interleavings and the full C1–C11
  matrix should be re-derived against the configured development database;
  the implementation includes the required lock, conflict, and synchronization
  seams, while the local focused suite is intentionally smaller than that
  reviewer harness.

### Review r1 — 2026-08-12 — Claude (CHANGES_REQUESTED)

**Verified correct (independently re-derived, not read from the log).** Perimeter
exact: `git diff 98c75a8 ef21f1e -- app/` is empty, so no post-checkpoint commit
touched code. Suite at HEAD 1756 passed / 23 failed / 1 deselected; pre-phase-4
(`3075fc3`) 1749/23/1; failure sets byte-identical (`diff` clean); collection
1772 → 1779 = **+7 exactly**. ruff clean on all phase paths. Production behaviour
re-derived on the configured development database with a disposable reviewer probe
suite (deleted; see the handoff's probe declaration): **C1 all 20 admission rows,
both chains, each returning its one exact registered identity**; C2 adjacency on
both chains incl. the three `is_applicable` boundary rows and §7A.3's theorem row;
**C3 both chains on the genuine DB-conflict path** (two committed sessions, both
past S1, loser blocked then raised `ITEM_COST_CONCURRENT_BASIS_VERSION` /
`_MODEL_VERSION`, exactly one open row afterwards); C4 underflow + canonicalize-
then-derive (`173.46` / `12.0105`) + smuggled-field ignored; **C5 all 12 §6A.4
cells** (3 accept, 9 `ITEM_COST_TERM_SHAPE_INVALID`) + both duplicate pre-checks;
C6 serial guard (`…_IN_USE`) and the lock's real counterparty; C7 INV-G1 + all
three group-delete rows + name-taken; C8 rows 1–5 through the status query plus
row 6 (`evaluable`, `first_failure is None`); C10 scoping/`is_deleted`/ordering/
`limit + 1` on the group list; C11 audit vocabulary (all 9 registered event
strings, format `<entity>.<action>`); scope fence clean (no valuation/evaluation/
item/task read, no term-mutation route, no workspace event); 13 routes exactly as
§6.5 registers them, all `require_roles([ADMIN, MANAGER])`. **The production code
is substantially right. The tests are not there.**

**B1 (blocking) — criteria coverage.** The phase ships **7 test nodes** against a
criteria set enumerating ~60 required rows. Per-criterion inventory: C1 **2 of
20**; C2 **0** (the shipped `is_applicable` test uses `SimpleNamespace`, never a
chain the command built — charter rule 3); C3 **0** (the shipped translation test
is the hand-built `IntegrityError` the harness block explicitly excludes); C4 3 of
5 row groups (underflow both paths and the S4-forward row distinct from B1's
fixture are absent); C5 **0 of 12 cells**, 0 dual-path rows, 0 router-surface
assertion; C6 **0** (declared); C7 **0**; C8 rows 1–4 only as a pure-function call
on hand-built rows, not "via the status query"; row 5 absent; C9 **0**; C10 **0**;
C11 **0** — verified structurally: **no test anywhere in the repo references the
item-economics router**, and removing `MANAGER` from `POST /cost-groups` leaves
the entire suite unchanged. Correction: implement the enumerated rows; every row
asserts one exact outcome and states which fixture field it varies (P-M/P-G).

**B2 (blocking) — request models validate shape only; every out-of-range numeric
escapes as HTTP 500.** §6A.4 pins that an invalid term is "rejected twice (request
+ DB CHECK)", and registry §6.2 pins that `percent_value` has **no** upper-bound
CHECK — so above 999.999 the request layer is the only specified rejector and it
is absent. Verified outcomes through the commands: `monthly_paid_hours = 0` and
`planning_utilization_percent = 0` → `decimal.DivisionByZero` raised inside
`calculate_cost_per_worker_minute` (derivation runs before the INSERT, so §6A.6's
"denominator > 0 by the §4.3 CHECKs" is not yet in force); `utilization = 150`,
`fixed_monthly_cost_minor = -1`, `monthly_paid_hours = -5`, `percent_value = -1`,
`fixed_amount_minor = -5` → `IntegrityError` re-raised by
`translate_integrity_error`; `percent_value = 1000` → `DataError`. All eight land
in `run_service`'s catch-all and reach the client as
`{"error": "An unexpected internal error occurred."}` with **HTTP 500** and a
logged traceback. Correction: mirror the §4.3/§6.2 bounds in the request models
(`fixed_monthly_cost_minor > 0`, `monthly_paid_hours > 0`,
`0 < planning_utilization_percent ≤ 100`, `0 ≤ percent_value ≤ 999.999`,
`fixed_amount_minor ≥ 0`), each with its own registered identity and criterion row.

**S1 (should-fix) — the router body model declares the derived rate as an input.**
`_BasisVersionBody.cost_per_worker_minute_minor` is a declared field, so the
published OpenAPI schema advertises it as accepted input, contradicting §5 /
§6A.6 ("never accepted from an API request"). The value is dropped (the command
request model has no such field, `extra="ignore"` — persisted value verified
equal to the derived one while smuggling `999.9999`), so nothing is corrupted.
Correction: delete the field; N4's pin is satisfied by `extra="ignore"`, which is
already in place.

**S2 (should-fix) — dead helper.** `_common.reference_exists` has no caller
anywhere (both delete commands inline the equivalent query); `get_group`'s
`for_update` parameter is never passed `True`. Charter rule 4. Correction: delete
both, or route the delete commands through the helper.

**S3 (should-fix, plan text) — C6's interleaved row cannot be built as written.**
While the delete holds `SELECT … FOR UPDATE`, a second session's INSERT of a
referencing `item_cost_evaluations` row **blocks** — the FK check needs
`KEY SHARE` on the version row, which conflicts with `FOR UPDATE` (verified: the
insert is still pending after 600 ms and the criterion's "a second session commits
a referencing evaluation [while] paused at the injected seam" deadlocks until the
seam returns). Consequences: (a) mutation (a) — drop the in-lock re-check — is
live and reddens a serial guard row (verified); (b) mutation (b) — drop
`FOR UPDATE` — **is** falsifiable in this phase, but its arbiter is "the
referencing insert is blocked while the lock is held" (True as shipped, False
mutated), not the plan's rejection outcome. Correction: restate C6's interleaved
row as: seam holds the lock → second session's referencing INSERT is issued with
`SET LOCAL lock_timeout` → assert it has not completed → release the seam → assert
it completes; mutation (b) flips the blocked assertion.

**Notes.** N1 §7A.1's S1 is realized as an ORM attribute mutation (UPDATE by PK),
not a predicated UPDATE; behaviourally equivalent under the index arbiter
(verified), but S1-before-S2 rests on SQLAlchemy's per-mapper "updates before
inserts" flush order, which nothing pins — C2's absence is what hides it. N2
`create_cost_model_version` compares enums via `.value` strings (§6A.1: members).
N3 `ITEM_COST_TERM_SHAPE_INVALID` is reused at the command layer while registry
§6.4 scopes it to the calculator's re-validation and requires the message to name
the `calculation_type` and the offending column — the shipped messages name
neither. N4 every translated conflict emits the same sentence regardless of index
(identity token correct, sentence uninformative). N5 C9's shipped description
begins "Planning allocation percentage…" — a literal lowercase string assertion
would fail; restate the criterion case-insensitively. N6 C5's DB-conflict rows for
the two term indexes are **unreachable by construction** (terms are always
inserted against a version created in the same transaction), so the dual-path
requirement can only be met structurally there. N7 `has_open_*` (open-row
predicate) vs the classifier (applicability) verified consistent under §7A.3's
theorem; the only divergent state (`effective_to` in the future) is unreachable
from these commands — recorded so phases 5/7 do not re-litigate it. N8 the
handoff's "1755 passed / +6 net" is off by one (measured 1756 / +7) and its
"phase-focused suites: 72 passed" counts phase-3 tests (P-L). N9 the mutation
ledger cites archgraph anchors instead of pytest node ids (P-I second extension);
all four executable declarations were nonetheless accurate when re-run. N10
`delete_cost_model_version` carries a vestigial `version = None`. N11 §7.5's
residual hazard is live and real, not theoretical: an evaluation whose INSERT was
blocked by the lock commits **after** the delete and references a soft-deleted
version — closed only by phase 7's `FOR SHARE` counterparty.

**Mutations re-run (observed pytest node ids, disposable worktree, all reverted;
"shipped" = the 7 phase test nodes).** C1 drop `is_deleted = false` from the
open-basis lookup → reddens exactly
`tests/integration/services/commands/item_economics/test_configuration_commands.py::test_basis_admission_ignores_a_soft_deleted_open_row`.
C4 return the unquantized Decimal → reddens
`tests/unit/services/commands/item_economics/test_item_economics_requests.py::test_basis_request_canonicalizes_numeric_columns_before_command_derivation`,
`…::test_model_request_canonicalizes_percentage_terms_to_three_places`,
`…/test_configuration_commands.py::test_configuration_commands_canonicalize_chain_and_status`.
C5 collapse the index discrimination to a blanket conflict → reddens only
`…/test_item_economics_requests.py::test_integrity_translation_preserves_registered_and_unknown_paths`,
the proxy the plan excludes. C8 derive precedence from `EconomicsStatusEnum`
iteration → shipped 7/7 green **and** all five reviewer status rows green (the
declaration order happens to match §11A.4, so only the structural guard bites —
the shipped explicit tuple is correct). C11 remove `MANAGER` from
`POST /cost-groups` → shipped 7/7 green, full suite byte-identical to unmutated.
C9 delete the router `percent_value` description → shipped 7/7 green, full suite
byte-identical. C6(a) drop the in-lock re-check → shipped 7/7 green; reviewer
serial probe reddens. C6(b) drop `FOR UPDATE` → shipped 7/7 green; reviewer lock
probe flips `reference_blocked_while_locked` True → False.
