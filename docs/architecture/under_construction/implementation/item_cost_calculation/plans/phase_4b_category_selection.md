# Phase 4B — Category-driven group selection (§7C)

```
plan: phase 4B
role: phase plan
date: 2026-08-12
state: IMPLEMENTED
```

## Goal

Rework group selection from "the workspace's single active group" to "the active
group for the item's major category (wood | seat)" per intention §7C (round 12):
`major_category` NOT NULL on `production_cost_groups` + INV-G3, category-aware
commands with an immutability guard, the §7C.2 total-ordered classifier, and the
per-category configuration-status payload (a deliberate breaking shape change to
phase 4's status query).
**NOT in this phase:** any item-domain change (owner pin 2 — category-less items
remain creatable; `item_missing_major_category` is an economics precondition
only); any consumer of the per-item classification path (valuation preview →
phase 5, commit path → phase 7, budget status → phase 8); no new routes; no
change to `delete_production_cost_group`, section membership, either version
chain, or the calculator; no list-query category filter (master plan §5 excludes
`55_query_filters_local` for v1).

## Read first

1. `master_plan.md` §§5, 6 (registry as amended for 4B — INV-G3 name in §6.2,
   the §6.3 major-category row, the §6.4 identities `ITEM_COST_GROUP_CATEGORY_TAKEN`
   / `ITEM_COST_GROUP_CATEGORY_IMMUTABLE`), 9 (P-B…P-Q all bind), 10.
2. Intention **§7C entire** (semantic authority), §11A.4 as amended by §7C.3
   (12 ordered values), §7A.5 (superseded rows — the classifier's total order is
   now §7C.2's), §4.1/§4A, §7.5/§7A.6 (the guards the immutability rule composes
   with), §7A.3 (`is_applicable` unchanged), R12-1 + pins 1–2 in
   `planning/owner_decisions.md`.
3. Contracts: `06_commands`+local, `07_queries`+local, `09_routers`,
   `28_roles_permissions`, `30_migrations`, `36_audit_log`, `05_errors`,
   `03_models` (+ core).
4. Phase 4's plan (`plans/phase_4_configuration_services.md`) — tasks 1/3/5 and
   criteria C8/C10/C11 describe the shipped code this phase reworks; its
   harness block is this plan's harness precedent.

## Dependencies

Phase 4 **APPROVED**. (Phase 4 is under review as this plan is written; the
coordinator re-verifies the "shipped tests that change" list below at prompt
time — phase-4 fix cycles may add test nodes touching the old shapes. Grep
before compiling the implementer prompt:
`first_failure|group_count|has_cost_group|has_open_basis_version`,
`resolve_economics_configuration`, `create_production_cost_group`.)

## Verified in-tree facts (planner, 2026-08-12 — cite, don't re-derive)

- Enum owner: `ItemMajorCategoryEnum` (`app/beyo_manager/domain/items/enums.py:17`),
  members `WOOD = "wood"`, `SEAT = "seat"`. PG type `item_major_category_enum`,
  created with `create_type=True` on `item_categories.major_category`
  (`models/tables/items/item_category.py:24-28`) — type-creation ownership stays
  there (R2-1). PG labels verified live in the dev DB: `wood`, `seat`
  (lowercased by `ddc5bf50153b`).
- `items.item_major_category_snapshot` is **`String(64)`, nullable**
  (`models/tables/items/item.py:51`) — NOT enum-typed. Its only writers assign
  `category.major_category.value` or `None`
  (`_create_item_in_session.py:86`, `update_item.py:80,93`,
  `find_or_create_item.py`), so the live vocabulary is `{"wood","seat",NULL}`,
  but the column type does not enforce it.
- `resolve_economics_configuration`'s only production caller is
  `get_economics_configuration_status` (grep-verified). The group serializer
  feeds the create/update/delete/list group payloads.
- Migration idioms: pre-flight report-and-refuse via `RuntimeError` before DDL
  (`97b60e06d42a`); reused-enum columns in migrations via
  `postgresql.ENUM(..., create_type=False)` (`677ed7131bb2`, `90cdd23a828e`).
- Phase-2's `test_schema_inventory_is_closed` asserts CHECKs exactly but
  indexes as a **subset** — the new index does not redden it; extending its
  `INDEX_NAMES` is a deliberate named test change (task 8).

## Files expected to change

- `migrations/versions/<rev>_add_major_category_to_production_cost_groups.py`
  (new; single revision on the chain head at implementation time)
- `app/beyo_manager/models/tables/item_economics/production_cost_group.py`
- `app/beyo_manager/domain/item_economics/enums.py` (`EconomicsStatusEnum` +=
  `ITEM_MISSING_MAJOR_CATEGORY = "item_missing_major_category"`)
- `app/beyo_manager/domain/item_economics/configuration.py` (classifier rework,
  `resolve_major_category`, extended precedence tuple)
- `app/beyo_manager/domain/item_economics/serializers.py`
  (`serialize_production_cost_group` gains `major_category`)
- `app/beyo_manager/services/commands/item_economics/create_production_cost_group.py`,
  `update_production_cost_group.py`, `requests/__init__.py`, `_common.py`
  (INDEX_IDENTITIES entry)
- `app/beyo_manager/services/queries/item_economics/get_economics_configuration_status.py`
- `app/beyo_manager/routers/api_v1/item_economics.py` (`_CreateGroupBody`,
  `_UpdateGroupBody`) + `routers/README.md` mirror rows (documentation task)
- tests: new 4B files + the four named phase-4/phase-2 test changes (task 8)

## Implementation tasks (ordered)

1. **Migration (§7C.1).** One revision adding to `production_cost_groups`:
   `major_category` NOT NULL, PG type `item_major_category_enum` referenced via
   `postgresql.ENUM("wood", "seat", name="item_major_category_enum",
   create_type=False)` — the type is NEVER created or dropped here (ownership:
   `item_categories.major_category`; the model-layer flag is inert — the
   phase-2 lesson: the migration site is what counts); partial unique index
   `uix_production_cost_groups_major_category_active` on
   `(workspace_id, major_category) WHERE is_deleted = false` (registry §6.2,
   idiom `595e7b840926`). **Pre-flight before any DDL** (§7C.1,
   report-never-guess; `97b60e06d42a` idiom): count ALL rows of
   `production_cost_groups` (deleted included — every row is uncategorizable);
   if > 0, raise `RuntimeError` reporting the count and the `client_id`s and
   abort the upgrade (never a DomainError — §6.4; never a guessed default,
   never a backfill). Dev rows are test residue; the operator deletes them and
   re-runs. Downgrade drops exactly the index then the column; it does NOT
   drop the enum type.
2. **Model.** `ProductionCostGroup.major_category:
   Mapped[ItemMajorCategoryEnum]`, `SAEnum(ItemMajorCategoryEnum,
   name="item_major_category_enum", create_type=False)` via
   `configure_sa_enum_values`, `nullable=False`; the INV-G3 partial unique in
   `__table_args__` mirroring the migration exactly (autogenerate-drift is
   caught by C1's `compare_metadata` row). No separate plain index on the
   column — INV-G3's composite covers the read path.
3. **Requests & commands.** `ProductionCostGroupCreateRequest` gains required
   `major_category: ItemMajorCategoryEnum`; `ProductionCostGroupUpdateRequest`
   gains optional `major_category: ItemMajorCategoryEnum | None = None`
   (`name` stays required — the shipped update shape is not this phase's to
   change). Create: pre-check "an active group with this category exists in
   the workspace" → `ITEM_COST_GROUP_CATEGORY_TAKEN` (`ValidationError`,
   message names the category value); DB conflict path via the existing
   `translate_integrity_error` — add
   `"uix_production_cost_groups_major_category_active":
   "ITEM_COST_GROUP_CATEGORY_TAKEN"` to `INDEX_IDENTITIES` (`ConflictError`,
   dual-path per §6.4's sibling identities). Update, in this order:
   (a) **immutability (§7C.4, exact predicate):** refuse
   `ITEM_COST_GROUP_CATEGORY_IMMUTABLE` iff the request field is present AND
   `request.major_category != group.major_category` AND at least one
   `production_cost_basis_versions` row with
   `production_cost_group_id = group.client_id` **exists — deleted or not**
   (the plain reading of §7C.4's "any basis version exists", same breadth as
   phase-4 task 4's N3 reference predicate; escape hatch verified: the group
   delete guard counts only non-deleted versions, so delete-and-recreate stays
   available even when the flip is refused). Field present and **equal** to the
   current value → accepted no-op (idempotent PATCH); field absent → name-only
   update, untouched. (b) when a flip is allowed (no basis-version row at
   all): pre-check the target category is unoccupied →
   `ITEM_COST_GROUP_CATEGORY_TAKEN` (same dual-path; the flush stays wrapped
   by `translate_integrity_error`). Audit events unchanged
   (`production_cost_group.created` / `.updated` — no new vocabulary; verified
   against §6.4's registered list).
4. **Classifier rework (§7C.2 — total, ordered, pure).**
   In `configuration.py`:
   - New pure helper **`resolve_major_category(snapshot: str | None) ->
     ItemMajorCategoryEnum | None`**: `None` for `None`; `None` for any value
     outside the enum vocabulary (**pinned:** a corrupt snapshot string is an
     item-data defect, not a configuration gap — mapping it to
     `not_configured_no_cost_group` would prescribe the wrong repair; R-9's
     never-guess. Ledger row L2 records this pin). Phases 5/7/8 call it on
     `item.item_major_category_snapshot`; in this phase its callers are the
     acceptance tests (charter rule 4 satisfied).
   - `resolve_economics_configuration(major_category:
     ItemMajorCategoryEnum | None, groups, basis_versions,
     cost_model_versions, on_date)` — first match wins:
     1. `major_category is None` → `ITEM_MISSING_MAJOR_CATEGORY`;
     2. active (non-deleted) groups **with that category** — 0 →
        `NOT_CONFIGURED_NO_COST_GROUP`; ≥ 2 →
        `NOT_CONFIGURED_AMBIGUOUS_COST_GROUP` (structurally unreachable under
        INV-G3; retained as the total-order defence row, §7C.2);
     3. the chosen group's applicable basis (`is_applicable`, unchanged §7A.3)
        — none → `NOT_CONFIGURED_NO_BASIS_VERSION` (soft-deleted-open same
        identity, §7A.5 rows 3–4 pin unchanged);
     4. no applicable model version → `NOT_CONFIGURED_NO_COST_MODEL_VERSION`;
     5. `OK`.
     Groups of OTHER categories are invisible to every step (a wood group is
     neither a hit nor ambiguity for seat).
   - `CONFIGURATION_FAILURE_PRECEDENCE` becomes the explicit 5-tuple with
     `ITEM_MISSING_MAJOR_CATEGORY` FIRST — precedence lives in this sequence,
     **never in enum iteration** (§6.3 note; the B6 structural guard extends
     to the new member). Internal decomposition free per phase-4's N1
     delegation; constraints: pure, no I/O, date injected.
5. **`EconomicsStatusEnum`** gains `ITEM_MISSING_MAJOR_CATEGORY =
   "item_missing_major_category"`. Declaration position is free (order carries
   NO precedence — §6.3 correction); the C5 structural probe is the guard.
6. **Status query rework (§7C.3 — breaking shape, exact).**
   `get_economics_configuration_status` returns **exactly**:
   ```
   {
     "categories": {
       "wood": {"group_count": int, "has_cost_group": bool,
                 "has_open_basis_version": bool, "evaluable": bool,
                 "first_failure": str | None},
       "seat": {…same keys…}
     },
     "has_open_cost_model_version": bool
   }
   ```
   - `categories` keys are exactly the `ItemMajorCategoryEnum` values, every
     member always present, built by iterating the enum (a future third
     category appears without a query change — structural note, not a
     criterion).
   - Per block: `group_count` counts the workspace's active groups of that
     category (0 or 1 under INV-G3; int retained as defence);
     `has_open_basis_version` scopes to that category's group (phase-4 N2
     semantics per group); `first_failure` = the reworked classifier called
     with that category (`None` when evaluable — N2 pin). A block's
     `first_failure` therefore ranges over the four `not_configured_*` values
     only — `item_missing_major_category` is unreachable here (category is
     supplied) and item-level values stay out of scope as in phase 4.
     The shared model failure appears in EVERY non-evaluable block (§7C.3:
     shared cost-model fields; a wood-ready workspace with no model shows
     wood `first_failure = "not_configured_no_cost_model_version"`).
   - The old top-level keys `group_count` / `has_cost_group` /
     `has_open_basis_version` / `evaluable` / `first_failure` are REMOVED
     (deliberate); `has_open_cost_model_version` stays top-level (shared).
7. **Serializer & router surfaces.** `serialize_production_cost_group` gains
   `"major_category": group.major_category.value`. `_CreateGroupBody` gains
   required `major_category: ItemMajorCategoryEnum`; `_UpdateGroupBody` gains
   optional — with `extra="ignore"` on both layers, an undeclared field would
   be silently DROPPED at the router and the command would fail on a request
   the client sent correctly, so the body-model field is load-bearing (C7's
   structural row). `routers/README.md` mirror rows updated (documentation
   task, not a criterion — phase-4 S5 precedent). No route or role-gate
   change.
8. **Named phase-4/phase-2 test changes (D8 discipline — each change named,
   with its authority; everything else in those files stays green):**
   - `tests/unit/domain/item_economics/test_configuration.py::test_configuration_classifier_uses_explicit_failure_order_and_same_basis_identity_for_gap`
     — rewritten to the §7C.2 signature and order (authority: §7C.2 supersedes
     §7A.5 rows 1–2; C5 replaces and extends it).
   - `tests/integration/services/commands/item_economics/test_configuration_commands.py::test_configuration_commands_canonicalize_chain_and_status`
     — group-create fixture gains `major_category`; the exact status-shape
     assertion replaced with the task-6 shape (authority: §7C.3).
   - `tests/integration/services/commands/item_economics/test_configuration_commands.py::test_basis_admission_ignores_a_soft_deleted_open_row`
     — group-create fixture gains `major_category` (mechanical; no assertion
     change).
   - `tests/integration/models/item_economics/test_item_economics_schema.py`
     — `INDEX_NAMES` gains `uix_production_cost_groups_major_category_active`
     (authority: master plan §6.2; the subset assertion would otherwise never
     see it).
   - `tests/unit/services/commands/item_economics/test_item_economics_requests.py::test_integrity_translation_preserves_registered_and_unknown_paths`
     — table gains the new index→identity pair (authority: §6.4).
   The list is re-verified by the coordinator at prompt time (see
   Dependencies).
9. **Archgraph.** Orient: the `production_cost_groups` table node, the phase-4
   command/endpoint nodes for group create/update and configuration-status,
   `domain-item-economics`. Delta at end (one batched `apply_changes`,
   accurate evidence spans): column/index on the table node, classifier and
   status-query semantic updates, the two command reworks. Never adjudicate
   pending items (§8 flow).

## Acceptance criteria

Error identities asserted as exact leading message tokens + class (§6.4).
Classifier rows hold production ORM instances — unsaved
`ProductionCostGroup` / `ProductionCostBasisVersion` / `CostModelVersion`
objects with `Decimal`/enum fields assigned explicitly (charter rule 3 +
§6.1 annotation caveat; the phase-3 N16 lesson — no `SimpleNamespace`).

**Databases & harness (per master plan §10, stated per criterion):** C2–C8 run
against the **configured development database at head**, flush-only on the
rolled-back `db_session` (rule 11½ by construction; the INV-G3 conflict rows
trigger at flush, no commit needed — no concurrency harness in this phase: the
dual-path identity follows the name-uniqueness sibling's non-concurrent
precedent, phase-4 C10, and the §7A.2 concurrent-arbitration semantics belongs
to the version chains, not to this index). C1's round-trip rows run on a
**disposable database** (§10 recipe; manual, charter rule-1 exemption, with
the automated proxies below and a Review log record); C1's DDL-site mutations
likewise (P-G(a)). C5 is pure-unit (no DB).

**C1 — migration & DDL (§7C.1):**
- (a) **live-schema rows (automated, dev DB at head):** `production_cost_groups.
  major_category` exists, NOT NULL, `atttypid` resolves to
  `item_major_category_enum` (pg_attribute join, phase-2 idiom); exactly ONE
  `pg_type` row named `item_major_category_enum` (enum reuse — no duplicate
  type); `get_indexes` shows `uix_production_cost_groups_major_category_active`
  unique on `(workspace_id, major_category)` with predicate
  `is_deleted = false`; `compare_metadata(compare_type=True)` reports zero
  diffs on `production_cost_groups` (model/migration agreement, task 2).
- (b) **pre-flight (P-J static proxy):** `inspect.getsource(migration.upgrade)`
  shows the row-count/report query and the `RuntimeError` raise BEFORE any
  `op.` DDL call, and the report includes the `client_id`s. Named mutations
  (site: the migration file's `upgrade`): (i) removing the pre-flight raise
  must redden this row; (ii) replacing the refusal with any backfill/default
  (`server_default`, an `UPDATE … SET major_category`) must redden this row
  (the source is asserted to contain NO such token — report-never-guess).
  Manual disposable check: at the previous head with one seeded group row,
  `alembic upgrade head` aborts with the report and applies no DDL; after
  deleting the row it succeeds. Recorded in the Review log.
- (c) **downgrade (C1(b)-style static proxy, P-J):**
  `inspect.getsource(migration.downgrade)` drops exactly the index and the
  column and contains NO enum `.drop(` and no `DROP TYPE` — the type survives
  downgrade (ownership: `item_categories`). Named mutation (site: the
  migration file's `downgrade`): adding an `item_major_category_enum` drop
  must redden this row. Manual disposable round-trip
  upgrade → downgrade → upgrade recorded in the Review log.
- (d) **enum-reuse at the migration site:** the migration source references
  the type with `create_type=False` (source assertion — the phase-2 lesson:
  the model-layer flag is inert; this is the site that counts), and (a)'s
  ONE-pg_type row is the behavioral arbiter.

**C2 — INV-G3 (P-M: one row per key column and per predicate clause; each
row's cell states which field of the shared fixture it varies; every row a
direct ORM insert + flush, bypassing the command pre-check so the INDEX is the
sole arbiter — P-K):**
- (a) **conflict row:** two active groups sharing exactly `(workspace_id,
  major_category)`, differing in `name` (and ids) → flush raises
  `IntegrityError` naming `uix_production_cost_groups_major_category_active`.
  Named DDL-site mutation (P-G(a), disposable DB): widening the index key
  with `name` must redden exactly this row (the key's width has its arbiter —
  the phase-2 B5 lesson).
- (b) **predicate-clause row:** same pair but the first row
  `is_deleted = true` → second active row accepted. Named DDL-site mutation:
  dropping `WHERE is_deleted = false` must redden exactly this row.
- (c) **key accept row (varies `major_category` only):** same workspace, both
  active, wood + seat → accepted.
- (d) **key accept row (varies `workspace_id` only):** two workspaces, same
  category, both active → accepted.

**C3 — dual-path conflict identity (§7C.4, registry §6.4):**
- (a) **create pre-check:** command-level second active group, same category →
  `ValidationError`, leading token `ITEM_COST_GROUP_CATEGORY_TAKEN`, message
  contains the category value.
- (b) **DB path through the translation map:** with the conflicting row
  seeded by direct insert, a flush-level `IntegrityError` on the INV-G3 index
  passed through `translate_integrity_error` raises `ConflictError` with the
  same leading token (the task-8 extension of
  `test_integrity_translation_preserves_registered_and_unknown_paths` plus a
  live-DB row). Named mutation (site: `_common.py` `INDEX_IDENTITIES`):
  removing the new entry must redden this row (the error would re-raise
  untranslated).
- (c) **update pre-check:** two groups (wood + seat), the seat group has NO
  basis-version row (sole-cause: the immutability guard cannot fire — P-K);
  update seat → wood → `ValidationError` `ITEM_COST_GROUP_CATEGORY_TAKEN`.
- (d) **update DB path: collapsed into (b) explicitly (P-G collapse rule):**
  both commands route flush errors through the same
  `translate_integrity_error`; (b) is the mechanism's arbiter and (c) proves
  the update path reaches the identity. No separate fixture is required; a
  reviewer finding a bypass of `translate_integrity_error` in the update
  command reopens this cell.

**C4 — category immutability (§7C.4 exact predicate; P-Q fixtures):**
- (a) **guard row:** group with one live basis version; update with same
  `name`, different `major_category` → `ValidationError`
  `ITEM_COST_GROUP_CATEGORY_IMMUTABLE`. Fixture per P-Q: absent the guard the
  update would SUCCEED (target category unoccupied, name unchanged) — the
  guard is the sole possible cause of refusal.
- (b) **breadth row (the "any … exists" pin):** the group's ONLY basis
  version is soft-deleted → flip still refused. Named mutation (site: the
  existence predicate's call site in `update_production_cost_group.py`):
  narrowing it with `is_deleted.is_(False)` must redden exactly this row.
- (c) **flip-allowed row:** group with NO basis-version row, target category
  unoccupied → update succeeds; response and a re-read both carry the new
  category; audit event `production_cost_group.updated` (exact string —
  unchanged vocabulary).
- (d) **equal-value row:** request carries the CURRENT category while a live
  basis version exists → accepted no-op. Named mutation (site: the guard's
  inequality clause): refusing on presence instead of inequality (dropping
  `!= group.major_category`) must redden exactly this row.
- (e) **absent-field row:** name-only update while a live basis version
  exists → accepted (the shipped path, untouched).
- Named mutation for the guard itself (site: the guard block in
  `update_production_cost_group.py`, call-site deletion): removing it must
  redden (a) AND (b) while (c)/(d)/(e) stay green — observed node ids
  declared per P-I at implementation time.

**C5 — classifier total order (§7C.2; pure-unit on unsaved ORM instances;
rule 2: one row per value AND one row per adjacent pair; each cell names the
varied field):**
Value rows (each fixture passes every earlier predicate and fails exactly its
own — sole-cause by construction):
- (V0) `resolve_major_category(None)` → `None`;
  `resolve_major_category("metal")` → `None` (pinned, ledger L2);
  `resolve_major_category("wood")` → `ItemMajorCategoryEnum.WOOD`.
- (V1) category `None`, groups/basis/model ALL present for wood →
  `item_missing_major_category` (the category predicate is the only failure).
- (V2) category seat, one ACTIVE WOOD group (varies: the group's category) →
  `not_configured_no_cost_group` — proves the category filter: a group
  exists, the wrong one.
- (V3) two active SEAT groups (unsaved ORM — the DB cannot hold this under
  INV-G3; the defence row is deliberately retained, §7C.2) →
  `not_configured_ambiguous_cost_group`.
- (V4) one seat group; the only applicable basis version hangs on the WOOD
  group (varies: the basis row's `production_cost_group_id`) →
  `not_configured_no_basis_version` — proves per-selected-group basis
  scoping.
- (V4b) seat group's only basis row is a soft-deleted open row →
  `not_configured_no_basis_version` (same identity, §7A.5 rows 3–4 pin).
- (V5) seat group + applicable basis, no applicable model version →
  `not_configured_no_cost_model_version`.
- (V6) all present → `OK`.
Adjacent-pair rows (first-match arbitration — the fixture fails BOTH members
of the pair; expected outcome is the earlier one):
- (P1) category `None` AND zero groups → `item_missing_major_category`.
- (P2) pair (no-group, ambiguous): N/A — predicates disjoint (0 vs ≥2), stated
  here so the gap is deliberate, not sampled.
- (P3) two seat groups AND no basis row anywhere →
  `not_configured_ambiguous_cost_group`.
- (P4) one seat group, no basis, no model → `not_configured_no_basis_version`.
- (P5) seat group + basis, no model = (V5) — the pair (model, OK) collapses
  into it explicitly (P-G).
Named mutations (each with file + definition-vs-call-site per P-I):
- (M1) removing the category filter from the group scan
  (`configuration.py`, definition site) must redden (V2) — observed ids
  declared at implementation.
- (M2) demoting `ITEM_MISSING_MAJOR_CATEGORY` below the no-group member in
  `CONFIGURATION_FAILURE_PRECEDENCE` must redden (P1) (and no value row —
  that is exactly why (P1) exists).
- (M3) **B6 structural probe extended:** permuting `EconomicsStatusEnum`'s
  declaration order (disposable worktree) changes NO C5 outcome — declared
  with the run's evidence (precedence is the explicit sequence, never
  iteration).

**C6 — status query shape (§7C.3; dev DB, flush-only):** exact-dict-equality
assertions (phase-4 test idiom) — the payload IS the task-6 shape, nothing
more (top-level keys exactly `{"categories", "has_open_cost_model_version"}`;
block keys exactly the five; `categories` keys exactly `{"wood", "seat"}` —
the removal of the old top-level fields is arbitrated by these same equality
rows, collapsed explicitly per P-G):
- (a) wood fully configured (group + open basis + open model), seat empty →
  wood block `{group_count: 1, has_cost_group: true, has_open_basis_version:
  true, evaluable: true, first_failure: null}`; seat block `{0, false, false,
  false, "not_configured_no_cost_group"}`; `has_open_cost_model_version:
  true`.
- (b) nothing configured → both blocks `first_failure =
  "not_configured_no_cost_group"`, `has_open_cost_model_version: false`.
- (c) wood group + open basis, NO model version → wood block `evaluable:
  false, first_failure: "not_configured_no_cost_model_version"` with
  `has_open_basis_version: true` (the shared failure surfaces per block);
  seat block unchanged from (b).
- (d) **per-category basis scoping row:** wood group + open basis; seat group
  WITHOUT basis; open model → wood evaluable, seat block `has_cost_group:
  true, has_open_basis_version: false, first_failure:
  "not_configured_no_basis_version"` (varies exactly the seat basis — the
  old workspace-global `has_open_basis_version` would have read true; named
  mutation, site `get_economics_configuration_status.py`: computing
  `has_open_basis_version` without the per-category group scope must redden
  exactly this row's seat cell).

**C7 — command / serializer / router surfaces:**
- (a) create without `major_category` → `ValidationError` (parse layer);
  create with a non-vocabulary value → `ValidationError`; create happy path →
  response payload carries `"major_category": "wood"` (exact), audit
  `production_cost_group.created` (exact string, unchanged), and a re-read
  confirms the enum-typed persisted value.
- (b) list query row: each listed group's payload carries the field (the
  serializer is shared — one list row suffices, collapsed explicitly with
  (a)'s create-response row per P-G; the delete response inherits the same
  serializer, stated, not separately tested).
- (c) **router body-model structural row (task 7's dropped-field hazard —
  P-H's boundary logic):** `_CreateGroupBody.model_fields` contains a
  required `major_category` and `_UpdateGroupBody.model_fields` an optional
  one. Named mutation (site: `routers/api_v1/item_economics.py`, the body
  model): removing the field from `_CreateGroupBody` must redden this row —
  under `extra="ignore"` the router would silently drop what the client sent
  and no command-level test can see it.
- (d) request-canonicalization rows for the enum field are pydantic-native
  (enum coercion from `"wood"`); one row asserts `"WOOD"` (wrong case) is
  rejected — the API vocabulary is the lowercase values, exactly the enum's.

**C8 — role gates & audit (C11 pattern, regression):** no route or gate
changed; the phase-4 C11 role rows (WORKER/SELLER rejected, ADMIN/MANAGER
retention with its named mutation) must remain green over the reworked
create/update/status routes, re-run as part of the full suite; audit
vocabulary verified unchanged — the §6.4 registered `production_cost_group.*`
set is exercised by C4(c)/C7(a) with exact strings, and NO new event string
appears in the phase diff (reviewer greps `audit(` call sites in the two
reworked commands against §6.4).

**Suite discipline:** full non-E2E suite green except the established
23-failure baseline, failure set byte-identical to the phase-1 list (master
plan §10); the phase-4 focused suites (with task-8's named edits) pass; ruff
clean; dev DB left at head; every named mutation run, observed node ids
recorded per P-I, and reverted (sha256 or diff-empty evidence per the
executor protocol).

## Notes

- **Pinned interpretations (ledger rows L1–L4 in the planner handoff; the
  coordinator ratifies or reroutes):** L1 immutability breadth = ALL
  basis-version rows deleted-or-not; L2 non-vocabulary snapshot → treated as
  missing category; L3 equal-value category update = accepted no-op; L4 the
  exact §7C.3 payload shape (task 6) including dropping the old top-level
  keys.
- The per-item path (`resolve_major_category` over
  `item_major_category_snapshot`) gains its first production caller in phase
  5's preview — forwarded there: "preview calls `resolve_major_category`,
  never reads the snapshot directly; `item_missing_major_category` payload
  rows carry null numerics (P-B)". Phase 8's status query likewise.
- Phase 5's plan (`plans/phase_5_valuation_surface.md`) was written before
  round 12 — the coordinator folds the §7C-resolved classifier into its
  prompt at prompt time (master plan §7 already sequences 4B before 5).
- INV-G3 makes group-per-category unique, so the §7C.2 ambiguous defence row
  is unreachable via the DB by construction — it exists to keep the
  classifier total over hostile inputs (same spirit as `rederive`'s R10-1
  totality).
- The items domain is UNTOUCHED (owner pin 2). A later item-domain decision
  to require categories at creation is out of scope and not assumed.
- Archgraph: any graph node contradicting the in-tree facts above is filed
  per the `archgraph-discrepancies` skill, never worked around silently.

## Round-0 projection amendments (2026-08-12, coordinator-routed — GOVERNING where they conflict with the text above)

The r0 projection's ledger (handoff `2026-08-12_phase4b_projection_r0_handoff.md`)
is fully routed. Each entry below amends the named task/criterion in place.

**Task 8 (L-1/L-2/L-3 — the fixture collisions the plan missed):**
- `test_item_economics_schema.py::_foundation` (`:83`) — the group gains
  `major_category=ItemMajorCategoryEnum.WOOD` (mechanical; ~13 test functions
  depend on it and every one would `IntegrityError` on first flush otherwise).
- The `sections_conflict`/`sections_removed` `second_group` (`:291-297`) takes
  **SEAT** — same-category would violate INV-G3 outside any `pytest.raises`
  (this is phase-2 B5's approved fixture; it must survive intact).
- The `groups_conflict`/`groups_soft_deleted` second row takes **SEAT** so the
  NAME index stays the sole cause (otherwise INV-G3 is a second sufficient cause
  and widening/dropping the name index goes green). Companion (recommended):
  assert the index name in the raised message — makes this collision class
  self-reporting.
- Task 8's list is FIVE named test changes + `_foundation` = six (N-a: items,
  never counts); the Dependencies grep list gains `ProductionCostGroup(` (N-f —
  the pattern that hides L-1; re-run all greps at implementer-prompt time, after
  phase-4 fix r2 lands its ~54 rows).

**Task 3(a) + C4(e) (L-5 — pin L5, ratified):** "present" means
`request.major_category is not None`; an explicit JSON `null` is an accepted
no-op, identical to absence (the PATCH route's `model_dump()` emits every field,
so a name-only rename arrives with `major_category: None` — the field-set reading
would break every rename of a versioned group through HTTP while command-level
tests stayed green). C4(e) gains a **router-level row per P-R** (`TestClient`):
a name-only PATCH against a versioned group succeeds through HTTP.

**C3(b)/(d) (L-4 — option (i), P-S applied):** the INV-G3 DB-conflict path is
covered by extending `test_integrity_translation_preserves_registered_and_unknown_paths`
(the translation-unit row) plus this recorded reachability judgment: *the DB path
is reachable in production only under genuine concurrency; proving it in-test
requires the phase-4 C3 harness and is deliberately not built here.* The
"seeded live-DB row" clause is struck (a seeded row is visible to the same-session
pre-check under READ COMMITTED — the flush never reaches the index). The
`INDEX_IDENTITIES` named mutation stands unchanged.

**C5 preamble (L-6):** every unsaved `ProductionCostGroup` /
`ProductionCostBasisVersion` / `CostModelVersion` fixture is constructed with an
**explicit, distinct `client_id`** — `IdentityMixin` assigns ids at flush, so
unsaved FKs join on `None == None → True` and V4's basis would read as applicable
to the wrong group. Deleted-row fixtures set `is_deleted=True` explicitly
(unsaved default is `None`).

**C5 additions (L-11):** new row **V2b** — the only seat-category group is
soft-deleted → `not_configured_no_cost_group`; named mutation: deleting the
`is_deleted` filter from the active-group comprehension
(`configuration.py:43`) must redden exactly V2b.

**C2 (L-7):** every multi-group fixture differs in `name` (background invariant,
P-K-audited); row (c) isolates `major_category` against row (a) (shared category,
different name). Row (d) unaffected.

**C4(a) (L-10):** assert the leading token AND both §6.4 message substrings —
the group identifier and its current category — individually (P-O).

**C1(a) (L-13 — harness named per P-R's spirit):**
`MigrationContext.configure(sync_conn, opts={"compare_type": True})` +
`compare_metadata(ctx, Base.metadata)`, **filtered to `production_cost_groups`**
(4 pre-existing repo-wide diffs exist; unfiltered reddens on drift this phase
does not own; the table itself is verified clean today).

**Task 1 / C1(b) (L-15):** the pre-flight `RuntimeError` report names the
uncategorizable group `client_id`s AND the dependent-table counts
(`production_cost_group_sections`, `production_cost_basis_versions`,
`item_cost_evaluations` — all RESTRICT FKs), because "delete and re-run" can
itself fail on dependents. Report-never-guess extends to the repair. (Dev DB
verified at 0 rows today; phase-4 fix-r2's committing rows are the only
foreseeable residue source.)

**Task 7 (L-12):** the doc target is
`beyo_manager/models/tables/item_economics/README.md` (its reused-enum sentence
gains `item_major_category_enum`), NOT `routers/README.md` (4B adds no route).
Still a task, not a criterion (phase-4 S5 precedent).

**Escape-hatch clause completed (N-h):** delete-and-recreate after a refused
category flip also requires removing the group's active section memberships —
the delete guard refuses on those too (`delete_production_cost_group.py:28-34`).

**Delegations D-1…D-7 (granted in writing):** classifier decomposition (pure,
date injected); pre-check ordering (recommended: shipped name check first in
both commands); pre-flight wording (must carry counts + ids + dependent counts);
`ITEM_MISSING_MAJOR_CATEGORY` declaration position (order carries no precedence;
M3 guards); C7(d) rows at the command request model; test file layout mirrors
the existing structure; C1(a) assertion shape per the named recipe.

## Prompt-time dependency re-verification (2026-08-13, coordinator — the N-f re-grep, GOVERNING for task 8)

Phase 4 is APPROVED (`8ca2bf9`); the Dependencies greps were re-run against the
final tree (post fix-r3, incl. `ProductionCostGroup(` per N-f). The fix cycles
added ONE new touchpoint file — `tests/integration/services/commands/
item_economics/test_phase4_fix_coverage.py` — and one payload row. Task 8's
named-change list is now the six amendments-section items PLUS:

- **T8-7 `_group` helper** (`test_phase4_fix_coverage.py:71-72`): gains a
  `major_category` parameter defaulting `ItemMajorCategoryEnum.WOOD`; every
  SECOND active group created in the same workspace (both rename tests, the
  C10 fixtures) takes **SEAT** — same collision class as L-1/L-3.
- **T8-8 C8 status enumeration**
  (`test_phase4_fix_coverage.py::test_c8_status_query_enumerates_each_first_failure_and_success`,
  `:601`): rewritten to the §7C.3 per-category shape (authority: §7C.3). Its
  DB-built **ambiguous** case (`:623-626`, two active groups one workspace)
  is no longer constructible under INV-G3 — that outcome is covered by C5's
  V3 pure defence row; the DB-backed enumeration covers the four
  `not_configured_*` values per category block.
- **T8-9 direct `ProductionCostGroup(` fixtures**
  (`test_phase4_fix_coverage.py:685-702` sole-cause filter rows, `:897-900`
  ordering rows): every construction gains `major_category`; same-workspace
  ACTIVE pairs take distinct categories (wood/seat) so INV-G3 never fires and
  each C10 row's named sole cause (workspace scope, `is_deleted`, ordering)
  is preserved — v1's list queries have no category filter (§5), so the
  ordering assertions are unaffected.
- **T8-10 router role-gate payload**
  (`tests/unit/routers/api_v1/test_item_economics_router.py:13`): the
  `POST /cost-groups` body row gains `"major_category": "wood"` so the C11
  role rows keep testing the gate, not a 422 parse failure.

Environment facts at prompt time: the dev DB's `production_cost_groups` is at
**0 rows** (N3 residue purged at closeout, enumerated 20-row delete), so
task 1's pre-flight passes on the configured DB; migration head is
`90cdd23a828e` (implementer re-verifies at implementation time).

## Fix r1 amendments (2026-08-13, coordinator-routed from review r1 — GOVERNING)

Owner card 1 ANSWERED (OPTION ONE, `planning/owner_decisions.md`): the fix
cycle is authorized for ONE more edit to `app/migrations/env.py` — commit the
cold-build cleanup — same standing exception shape as OD-1: that file only,
this cycle only. N6 (partial-target cold builds crashing in cleanup) is NOT in
scope — it routes to the migration-infrastructure owner separately.

**New criterion C9 — cold-build end-state (B1; the P-Z before/after property):**
the property §10 always claimed: a from-scratch build ends CLEAN. On a
disposable database, §10's recipe (empty → `alembic upgrade head`) ends at
`alembic_version = 5caae620088c` with **zero `workspaces`, zero
`pause_reasons`, zero `mig_cold_build_workspace` rows** — asserted by state
queries, never by exit code (review L5). Manual disposable check recorded in
the Review log (C1(b) precedent, charter rule-1 exemption). Named mutation
(disposable): reverting the cleanup-commit edit must re-produce the ghost
(workspaces = 1, pause_reasons = 7) — run, observed, reverted. The configured
DB stays at head throughout (rule 7).

**C1 gains row (e) — model-side predicate structural row (S1; P-X):** the
named index in `ProductionCostGroup.__table__.indexes` carries
`dialect_options["postgresql"]["where"]` textually equal to
`is_deleted = false`. Named mutations (both r1-green probes must now bite):
(i) deleting `postgresql_where` from `__table_args__` must redden this row;
(ii) flipping the predicate to `is_deleted = true` must redden this row.
Task 2's parenthetical is corrected: `compare_metadata` catches index
presence/key/type drift but NOT the predicate clause (P-X) — this row is the
predicate's arbiter.

**C6 shape restatement (S2; P-Y):**
`test_status_shared_model_failure_is_repeated_in_each_category_block` becomes
an **exact-dict-equality assertion over the whole payload**, as C6(a)/(d)
already are. Named mutation (the reviewer's r1-green Probe B): collapsing
`has_open_basis_version` to `has_open_basis and evaluable` in
`get_economics_configuration_status.py` must now redden this row — run,
observed, reverted (no production change ships; the query is correct).
**C6(b) collapse stated explicitly (P-G):** its content is discharged by
C6(a)'s exact-dict seat block (the "nothing configured" block shape) plus the
shared-model row's `has_open_cost_model_version: false` pin; no separate
fixture is owed.

## Review log

(append-only)

### 2026-08-13 — implementer r1 (Codex)

- Implementation complete across the scoped migration, `ProductionCostGroup`
  model/README, category-aware request and command paths, pure classifier,
  configuration-status query, serializer, and router body models. The migration
  refuses any existing production-cost-group rows before DDL, reuses
  `item_major_category_enum`, and creates the active workspace/category unique
  index. Category flips are immutable once any basis row exists (including a
  deleted row); equal-category and explicit-JSON-null updates remain no-ops.
- The named 4B tests plus amended phase-4/phase-2 coverage pass: 256 focused
  tests passed twice. Ruff passed on every changed production, migration, and
  test file. The full non-e2e suite passed 1926 tests with 23 known failures and
  1 deselected, twice; the failure set is byte-identical to the established
  phase-1 baseline. The scoped economics residue check is zero rows in the
  production-cost-group/basis/evaluation/cost-model tables and zero matching
  economics audit rows; development Alembic is at `5caae620088c` (head).
- C1 live checks used the configured database and a disposable database:
  empty upgrade, seeded-row preflight refusal with ids and dependent counts,
  downgrade, and upgrade again. The live enum is the single reused
  `item_major_category_enum`; the index is unique on `(workspace_id,
  major_category)` with `is_deleted = false`; filtered `compare_metadata`
  reports no production-cost-group diffs.
- Named mutation probes were executed, each with an observed pytest node or
  live DDL failure, then reverted. Coverage includes migration refusal/default/
  downgrade/type-key/predicate, category identity translation, basis-deleted
  immutability, equal-category no-op, category/deleted-group classifier
  filtering, missing-category precedence, per-category basis scope, HTTP
  category fields, serializer category output, request validation, and the
  create category pre-check. No pending Architecture Graph review item was
  adjudicated. One batched additive graph delta added six source links to the
  existing table, domain, status endpoint, and create/update command anchors;
  graph revision is `5e4f368df1e17bdbad477428f691e91ad15ece9bd9455b668ebe7bf95b4e76f0`.
- Scope exception for owner review: `app/migrations/env.py` gained a
  transaction rollback after the cold-build preflight query. The existing
  migration environment otherwise left Alembic's transaction open, so a
  successful upgrade did not persist its revision; the one-line reset was
  required for the requested migration to commit and for upgrade/downgrade
  verification to be meaningful.

### 2026-08-13 — reviewer r1 (Claude Opus 5) — **CHANGES_REQUESTED**

Independent re-derivation against C1–C8, the §7C authorities and the 17-row
ledger. Suite re-run twice by the reviewer: 1926 passed / 23 failed /
1 deselected, failure set byte-identical between runs and to the phase-1
baseline list, zero connection noise. Ruff clean on all 21 changed `.py` files.
Dev DB at head `5caae620088c`. Economics residue flat at zero across both runs
(scope: `production_cost_groups`, `production_cost_group_sections`,
`production_cost_basis_versions`, `item_cost_evaluations`,
`cost_model_versions`, `cost_model_terms`, plus `audit_logs` rows whose event
matches `production_cost%` / `cost_model%` / `item_cost%` — §9 rule-11½ record).

**OD-1 probes.**
- **P4B-0a — REPRODUCED.** On a disposable database at `90cdd23a828e` with the
  four `env.py` lines reverted, `alembic upgrade head` logs
  `Running upgrade 90cdd23a828e -> 5caae620088c`, exits 0, and persists neither
  the revision (`alembic_version` stays `90cdd23a828e`) nor the DDL
  (`major_category` absent). Mechanism: the cold-build preflight `SELECT`
  autobegins a transaction, so `context.configure()` sets Alembic's
  `_in_external_transaction`, after which **every** `begin_transaction()`
  returns `nullcontext()` and nothing is ever committed; the connection is
  closed (rolled back) by `_run_async_migrations`. The maintenance session's
  from-scratch runs succeeded only because two historical revisions
  (`6787eabf4c32`, `7a3e91c4b2d8`) issue a raw `op.execute("COMMIT")` for
  `CREATE INDEX CONCURRENTLY`; confirmed by adding one `op.execute("COMMIT")`
  to `5caae620088c` — the same warm upgrade then persisted. OD-1's rationale is
  sound and RETAIN is correct **for the migration path**.
- **P4B-0b — FAILED.** See B1.

**Findings.**

- **B1 (blocking) — the retained `env.py` rollback leaves cold-build residue in
  every freshly built database.** §10's from-scratch recipe (empty disposable
  DB → `5caae620088c`) now ends with `workspaces = 1`
  (`mig_cold_build_workspace`, "Migration workspace") and `pause_reasons = 7`
  owned by it; with the four lines reverted the same build ends at 0 / 0.
  Cause: `cleanup_cold_build_workspace()` runs in the `finally` block *after*
  Alembic's per-migration transactions commit; its two `DELETE`s autobegin a
  fresh implicit transaction that nothing commits, so they are discarded at
  connection close. Before the change nothing persisted at all, so cleanup was
  vacuously satisfied. Authority: master plan §10 ("deletes that workspace and
  its anchor-owned rows before the command returns"), charter rule 7.
  Correction: commit the cleanup (`connection.commit()` inside the `finally`,
  or wrap the two DELETEs in `with connection.begin():`), and add a criterion
  that re-runs §10's from-scratch recipe asserting zero `workspaces` /
  `pause_reasons` / `mig_cold_build_workspace` rows. Requires a second edit to
  the out-of-fence `env.py` — see owner card 1.

- **S1 (should-fix) — C1(a)'s `compare_metadata` clause is blind to
  partial-index predicate drift.** Deleting `postgresql_where=text("is_deleted
  = false")` from the model's `__table_args__`, and separately flipping it to
  `is_deleted = true`, each leave all 7 rows of
  `test_phase4b_category_schema.py` GREEN, `compare_metadata` row included.
  Removing the whole `Index(...)` *is* caught. So task 2's parenthetical
  ("mirroring the migration exactly — autogenerate-drift is caught by C1's
  `compare_metadata` row") is false for the predicate clause, which is exactly
  what INV-G3's soft-delete escape hatch rests on. Authority: task 2 + C1(a),
  P-J. Correction: add a model-side structural row asserting the named index in
  `ProductionCostGroup.__table__.indexes` carries
  `dialect_options["postgresql"]["where"]` equal to `is_deleted = false`, with
  the named mutation "changing the model predicate must redden this row".

- **S2 (should-fix) — C6(c) has no arbiter.** Rewriting the payload cell to
  `"has_open_basis_version": has_open_basis and evaluable` leaves the entire
  256-test focused suite green. C6(c) names `has_open_basis_version: true`
  inside a block with `evaluable: false, first_failure:
  not_configured_no_cost_model_version`;
  `test_status_shared_model_failure_is_repeated_in_each_category_block`
  asserts only the two `first_failure`s and `has_open_cost_model_version`, and
  is not an exact-dict-equality row as C6 mandates. Authority: C6 preamble +
  C6(c). Correction: make that test an exact-dict-equality assertion over the
  whole payload, as C6(a)/(d) already are. (C6(b)'s content is discharged by
  C6(a)'s exact-dict seat block plus the shared-model row; collapse it
  explicitly per P-G rather than leaving it implicit.)

- **N1 (note) — M2 declared 1 reddened node, 7 observed.** The ledger's
  precedence-demotion mutant (SHA `22cc4294…`, reproduced exactly) reddens V1,
  V2, V2b, P1, `test_configuration.py`'s classifier row,
  `test_configuration_commands_canonicalize_chain_and_status` and
  `test_c8_status_query_enumerates_each_first_failure_and_success` — not "P1 and
  no value row" as C5's M2 predicted. Cause:
  `resolve_economics_configuration` returns `CONFIGURATION_FAILURE_PRECEDENCE[i]`
  positionally, so the tuple is a branch→identity map, not an independent
  precedence declaration; permuting it changes returned identities, not order.
  No live defect (P1/P3/P4 still arbitrate the order; M3 re-run by the reviewer
  across all 256 focused tests confirms enum declaration order is irrelevant),
  but P-I's per-row declaration was under-stated and C5's M2 wording is
  unsatisfiable by this construction.

- **N2 (note) — the router row's 63-char mutant SHA is a transcription error.**
  Recomputed: original `8ad093a30d7f564c89221d888f2b66fb143572c7686ead57e85f0577e9ae9aee`
  (exact match); mutant
  `56a99ea50ab28480700e1dcde252b88f1f68044335df283e058e60ea5bee123c`. The
  ledger transposes `ea`→`ae` near offset 54 and drops the trailing `c`. The
  mutation itself reproduces and reddens the declared node.

- **N3 (note) — the reported vacuous mutation is correctly reported; no
  criterion row is owed.** Verified at the loader: the status query selects
  basis versions with `is_deleted.is_(False)`, so the comprehension's
  `and not version.is_deleted` is redundant; removing it leaves 256 green. Two
  independent sufficient causes, both correct — defence in depth, not a gap.
  C6(d)'s per-category-scope mutation covers the clause it was written for.
  Carry forward to phase 8's status rework.

- **N4 (note)** — `get_economics_configuration_status` computes
  `evaluable = status.value == "ok"`; prefer `status is EconomicsStatusEnum.OK`.
  Correct today, brittle to any enum-value edit.

- **N5 (note)** — archgraph span imprecision: the `domain-item-economics` link
  is labelled `symbol: resolve_economics_configuration` but spans
  `configuration.py:12-82` (the precedence tuple, `resolve_major_category`,
  `is_applicable` and the function). The migration link
  (`5caae620088c…py:25-58`, `upgrade`) is exact. Nothing contradicts the code,
  so no `archgraph-discrepancies` filing. Graph unchanged at 148 nodes /
  188 edges / revision `5e4f368d…` / 2 pending (N7), not adjudicated.

- **N6 (note, passing glance, pre-existing)** — a cold build targeting a
  revision below the pause-reason migrations crashes in cleanup:
  `alembic upgrade a1312183fdfb` on an empty database raises
  `UndefinedTableError: relation "pause_reasons" does not exist` from
  `cleanup_cold_build_workspace()`. Not introduced by 4B; route with B1.

**Verified correct** (settled ground for the re-review): C1(a)–(d) including a
reviewer-run disposable round-trip (upgrade → downgrade → upgrade; column
dropped, `item_major_category_enum` survives at exactly one `pg_type` row) and
a reviewer-run seeded-row refusal (2 rows, one soft-deleted → `RuntimeError`
naming both `client_id`s and all three dependent counts, exit 1, no DDL,
revision unchanged; after `DELETE` the upgrade succeeds) — confirming the
pre-flight counts deleted rows too; C2(a)/(b) DDL-site mutations re-run on
disposable state with mutant SHAs matching the ledger exactly (`0bb4461c…`,
`10857fee…`), each reddening exactly its own row; C3(a)/(b)/(c) with the
`INDEX_IDENTITIES` mutation reproducing `3b594c36…` and the L-4 reachability
judgment recorded (P-S); C4's guard deletion reddening exactly (a)+(b) with
(c)/(d)/(e) green, the breadth-narrowing reddening exactly (b), the
inequality-drop (`dccb142c…`) reddening exactly (d), and C4(a) asserting the
token plus both substrings individually (P-O); C5's V0–V6 + V2b + P1/P3/P4/P5
on unsaved ORM instances with explicit distinct `client_id`s and explicit
`is_deleted` (L-6), parametrize ids naming their authority rows (P-V), M1
reproducing `c193c89f…` and reddening V2+V4 as declared, M3 re-run across all
256 focused tests; C6(a)/(d) as true exact-dict-equality rows pinning top-level
keys, the five block keys and `{wood, seat}`, with the per-category-scope
mutation reddening (d); C7(a)/(c)/(d) with the body-model mutation re-run; C8
— `audit(` in both reworked commands emits only the registered
`production_cost_group.created` / `.updated`, no new event string appears
anywhere in the phase's production diff, and the ADMIN-retention row still
bites over the reworked create route.

### 2026-08-13 — fix r1 (Codex)

- B1: committed `cleanup_cold_build_workspace()`'s DELETE transaction as the
  last statement of `_do_run_migrations()`'s `finally`. The timed disposable
  cold build `beyo_manager_4b_fix_r1_verified` completed in 1.70s at head
  `5caae620088c`; state queries, rather than exit status, showed zero
  `workspaces` rows for `mig_cold_build_workspace`, zero owned `pause_reasons`,
  and zero `mig_cold_build_workspace` rows. The database was dropped. Reverting
  the edit in disposable `beyo_manager_4b_fix_r1_b1` reproduced `1 / 7 / 1`
  rows; the edit was restored and that database was dropped. N6 remains out of
  scope and routed to migration infrastructure.
- S1: added the C1(e) model-side structural assertion that
  `uix_production_cost_groups_major_category_active` carries the textual
  predicate `is_deleted = false`.
- S2: rewrote
  `test_status_shared_model_failure_is_repeated_in_each_category_block` as a
  whole-payload exact-dict assertion, including the wood block's
  `has_open_basis_version: true` while the shared model failure remains the
  first failure.
- Focused Phase 4B set: 200 passed twice. Full non-e2e suite: 1927 passed,
  23 known baseline failures, 1 deselected; ruff and `git diff --check` passed.
  Configured `beyo_manager` remained at head with zero rows in the six
  economics tables and zero matching economics audit rows.
- Mutation ledger: B1 `app/migrations/env.py`,
  `09261d91c7813483193fc93dd62e422719a956bb0694fda2af6eb586af4b4e13` →
  `db98e1ee8c215861f346bbc69a4b29643f997dbc6721a7a028108a44280beae5`,
  observed disposable state `1 / 7 / 1`, restored to the original hash;
  S1 predicate deletion in
  `app/beyo_manager/models/tables/item_economics/production_cost_group.py`,
  `27d99ecb8b3a0e5ea5a84b4f214d60a94029308e4b2cb48d33875dea99e17b5f` →
  `4f2076e1a7405a94f88c3515fad8370d706a53c95a6febe2c5597755eb439afa`,
  observed red node `test_phase4b_model_index_predicate_is_soft_delete_partial_unique`;
  S1 predicate inversion, same original hash →
  `ceb5248a80d8fa6f9a9c9a1457ce7a93cdf7854e3938e97c04e007fc47d99b52`,
  observed the same red node; S2 query collapse in
  `app/beyo_manager/services/queries/item_economics/get_economics_configuration_status.py`,
  `ce43ca5f132667b3bba598d8b97aa3bd4f51bc60f6ae7a5e9c38e1cd65144a62` →
  `a09aa514df16d8536a1f5545bf526d31e560eaecd9f4b7ab96de6bfa16e68bc0`,
  observed red node
  `test_status_shared_model_failure_is_repeated_in_each_category_block`.
  All probes were reverted; final hashes match the originals.
