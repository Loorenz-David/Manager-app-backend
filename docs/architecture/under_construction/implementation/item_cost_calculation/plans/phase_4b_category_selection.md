# Phase 4B — Category-driven group selection (§7C)

```
plan: phase 4B
role: phase plan
date: 2026-08-12
state: NOT_STARTED
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

## Review log

(append-only)
