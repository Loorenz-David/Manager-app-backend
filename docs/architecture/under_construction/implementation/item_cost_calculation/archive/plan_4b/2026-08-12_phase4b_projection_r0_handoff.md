---
plan: phase 4B
role: reviewer
round: 0
date: 2026-08-12
state: AWAITING_COORDINATOR
verdict: AMENDMENTS_REQUIRED
actor: reviewer (Claude), plan-projection doctrine
---

# Projection handoff — phase 4B: category-driven group selection (round 0)

## Opening summary

I did the implementer's first hour of phase 4B on paper, from the plan and its cited
authorities alone, and the plan is close but not yet buildable. The design is sound —
splitting cost groups by wood and seat, refusing a second group of the same kind, and
refusing to re-label a group once it has priced anything — and I found nothing wrong
with the product decisions. What I found is mechanical: making the category compulsory
breaks a shared test fixture the plan does not mention, so roughly a dozen existing
schema tests would fail on the first run; two of the plan's own test recipes cannot
actually be written as described; and one wording detail ("the field is present") would,
if read the obvious way, make every ordinary rename of a group fail for real users while
every test still passed. Nothing here needs the owner personally — the four
interpretation pins were already ratified and I did not reopen them. Fifteen points go
back to the coordinator, six of them blocking, and the implementer prompt should compile
once they are routed.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing in this projection needs the owner. The round-12 scope decision and pins 1–2 are
answered, and the plan's four interpretation pins (L1–L4) were ratified by the
coordinator before this session — I did not relitigate them.

---

## Gate check

| Check | Result |
|---|---|
| Tracker row 4B present, `NOT_STARTED`, ⚑ MANDATORY | ✅ `master_plan.md:89` |
| Plan exists | ✅ `plans/phase_4b_category_selection.md` (498 lines) |
| Plan's Review log empty | ✅ `:496-498` (header + "(append-only)") |
| No 4B implementer handoff | ✅ `handoffs/implementer/` holds only the phase-4 r1 handoff |
| §6.3 major-category registry row applied | ✅ `master_plan.md:267` |
| §6.4 `ITEM_COST_GROUP_CATEGORY_TAKEN` / `_IMMUTABLE` applied | ✅ `master_plan.md:322-329` |
| §6.5 `resolve_major_category`, serializer note, migration slug | ✅ `master_plan.md:365-366`, `:370` |
| §6.2 INV-G3 index name | ✅ `master_plan.md:206` |

Gate passes. No upstream handoff for 4B sits in `OWNER_DECISIONS_PENDING`.

**Tree state.** `HEAD = ef21f1e`; `app/` is byte-identical to the phase-4 checkpoint
`98c75a8` (phase-4 review r1 verified this and I re-read the files it names). Phase 4 is
`CHANGES_REQUESTED` and a fix-r2 prompt is already authored but unrun
(`prompts/implementer/2026-08-12_phase4_fix_r2.md`, untracked) — see N-f: its perimeter
overlaps 4B's and it will add ~54 test rows, several of which will construct cost groups.

---

## Decision ledger

Severity: **B** = blocking (implementer prompt must not compile until routed),
**S** = should-fix, **D** = delegation (freedom granted on purpose).

| # | Decision point | Class | Routing |
|---|---|---|---|
| L-1 | Task 8's named-test list omits `_foundation()`, the phase-2 schema fixture that builds a group with no category | plan gap (B) | amend task 8 |
| L-2 | The `sections_conflict`/`sections_removed` fixture creates a second same-workspace group — INV-G3 now collides with it | plan gap (B) | amend task 8 |
| L-3 | `groups_conflict` loses its sole cause: INV-G3 becomes a second sufficient cause for the name index's row | plan gap (B) | amend task 8 |
| L-4 | C3(b) is unbuildable: a seeded conflicting row is visible to the command's own pre-check | plan gap (B) | amend C3 (+ P-S note) |
| L-5 | "the request field is present" is undecidable through the router — `model_dump()` always emits `major_category: None` | plan gap (B) | amend task 3 + C4(e) |
| L-6 | C5's unsaved ORM fixtures need explicit `client_id`s — `IdentityMixin` assigns at flush, so `None == None` | plan gap (B) | amend C5 preamble |
| L-7 | C2(c) "varies `major_category` only" is refused by the name index | plan gap (S) | amend C2 |
| L-8 | §6.5's "the ONLY reader of the snapshot string" is false repo-wide; the rule has no arbiter | registry gap (S) | master plan §6.5 (+ optional 4B row) |
| L-9 | §6.4's "message names the category value" cannot hold on the DB path | registry gap (S) | master plan §6.4 |
| L-10 | C4(a) does not assert §6.4's message content for `_IMMUTABLE` | plan gap (S) | amend C4(a) |
| L-11 | No C5 row for a soft-deleted group of the right category — the `is_deleted` filter has no arbiter | plan gap (S) | amend C5 |
| L-12 | Task 7's `routers/README.md` doc task has nothing to update; the stale doc is the models README | plan gap (S) | amend task 7 |
| L-13 | C1(a)'s `compare_metadata` row has no harness and no precedent in the suite | plan gap (S) | amend C1(a) |
| L-14 | Pre-check ordering (name vs category; name vs immutability) is undetermined | free choice (D) | record delegation |
| L-15 | The migration's remediation instruction understates the operator's work (RESTRICT FKs) | plan gap (S) | amend task 1 / C1(b) |

---

## Blocking rows in full

### L-1 — task 8 omits the fixture that breaks first (B)

`tests/integration/models/item_economics/test_item_economics_schema.py:83`:

```python
group = ProductionCostGroup(workspace_id=workspace.client_id, name=f"group {token}", created_by_id=user.client_id)
```

`_foundation()` is called at `:112`, `:238`, `:279`, `:447`, `:479`, `:527`, `:579`,
`:625`, and indirectly through `_evaluation()` at `:362`, `:363`, `:398`, `:462`,
`:509`, `:546` — thirteen test functions, several of them parametrized into dozens of
cases. With `major_category` NOT NULL every one raises `IntegrityError` on its first
`flush()`. The plan names only the `INDEX_NAMES` addition for this file
(`plans/phase_4b_category_selection.md:231-234`).

**Proposed amendment (task 8):** add
`tests/integration/models/item_economics/test_item_economics_schema.py::_foundation` —
the group gains `major_category=ItemMajorCategoryEnum.WOOD` (authority: §7C.1, NOT NULL);
mechanical, no assertion change. This also silently fixes the plan's Dependencies grep
list, which greps for `create_production_cost_group` but not for `ProductionCostGroup(`
(see N-f).

### L-2 — INV-G3 collides with the phase-2 B5 fixture (B)

`test_item_economics_schema.py:291-297`, the `sections_conflict` / `sections_removed`
cases:

```python
second_group = ProductionCostGroup(
    workspace_id=workspace.client_id, name=f"group {uuid4().hex}", created_by_id=user.client_id,
)
db_session.add_all([section, second_group])
await db_session.flush()
```

Same workspace, second **active** group. If it inherits `_foundation`'s category, this
`flush()` — which is outside any `pytest.raises` — raises `IntegrityError` on
`uix_production_cost_groups_major_category_active` and both cases hard-error. This is
the fixture phase-2 fix r3 added to give INV-G1 its arbiter (B5) and phase-2 review r3
approved; it must survive 4B intact.

**Proposed amendment (task 8):** `second_group` takes the OTHER category
(`ItemMajorCategoryEnum.SEAT` if `_foundation` is wood). Authority: §7C.1 / registry §6.2.

### L-3 — `groups_conflict` loses its sole cause (B)

`test_item_economics_schema.py:283-288` builds the second group with the **same name**
in the same workspace, and `_assert_c2_second` (`:250-260`) asserts only
`pytest.raises(IntegrityError)` — no index name. Once both rows also share a category,
two indexes are sufficient causes for the same raise. Consequence: widening or dropping
`uix_production_cost_groups_name_active` leaves `groups_conflict` green, because INV-G3
catches it. This is exactly the phase-2 B5 shape (charter rule 2's sole-predicate
companion; P-K; P-M) reintroduced from the other side.

**Proposed amendment (task 8):** the `groups_conflict` / `groups_soft_deleted` second row
takes the OTHER category, so only the name index can fire. Recommended companion: assert
the index name in the raised message, which would have made this class of collision
self-reporting.

### L-4 — C3(b) describes a test that cannot be written (B)

C3(b) (`plan:317-323`) asks for "the conflicting row seeded by direct insert" and then a
"flush-level `IntegrityError` on the INV-G3 index passed through
`translate_integrity_error`". The create command's pre-check runs in the same session
(`create_production_cost_group.py:16-24`) and the DB is READ COMMITTED, so a seeded row —
committed or not, in this session — is visible to the pre-check, which raises
`ValidationError` before any INSERT. The only way the flush reaches the index is a
**concurrent uncommitted writer**, i.e. the harness the plan explicitly declines
(`plan:257-263`).

For the sibling identity the plan cites as precedent (phase-4 C10, `ITEM_COST_GROUP_NAME_TAKEN`
"both paths"), phase 4 shipped the DB path as a unit table with a hand-built
`IntegrityError` — `tests/unit/services/commands/item_economics/test_item_economics_requests.py:37`.

**Proposed amendment (recommended option i):** C3(b) is satisfied by the task-8 extension
of `test_integrity_translation_preserves_registered_and_unknown_paths` plus a recorded
**P-S reachability judgment** ("the DB path is reachable in production under concurrency;
proving it in-test requires the phase-4 C3 harness and is not built here") — and the
"plus a live-DB row" clause is struck. Option (ii), building one genuine INV-G3 race on
the phase-4 C3 harness, is available and was proven workable by the phase-4 reviewer; it
costs a committing test with `try/finally` teardown (rule 11½). The named mutation on
`INDEX_IDENTITIES` survives either option unchanged.

### L-5 — "present" is undecidable through the router (B)

Task 3(a) (`plan:132-141`) says the guard fires iff "the request field is **present** AND
`request.major_category != group.major_category`". The PATCH route builds the command's
payload as:

```python
data={"client_id": client_id, **body.model_dump()}   # routers/api_v1/item_economics.py:117
```

`model_dump()` without `exclude_unset` emits **every** field, so an optional
`major_category` on `_UpdateGroupBody` arrives as `"major_category": None` on every
name-only PATCH. If the implementer reads "present" as `"major_category" in
request.model_fields_set` — the natural reading — then:

- through HTTP, renaming a group that has any basis version returns
  `ITEM_COST_GROUP_CATEGORY_IMMUTABLE` (because `None != WOOD`) — a live defect;
- C4(e), a command-level row built from a dict that omits the key, stays **green**.

**Proposed amendment:** pin in task 3(a) that "present" means
`request.major_category is not None` (an explicit JSON `null` is therefore an accepted
no-op, same as absence — record it as pin L5 beside L1–L4), and give C4(e) a router-level
row per P-R (`TestClient`) so the boundary has an arbiter. If the coordinator prefers the
other resolution, the equivalent is `body.model_dump(exclude_unset=True)` on the PATCH
route — but that changes a shipped route's behaviour for `name` too and I do not
recommend it.

### L-6 — C5's ORM fixtures join on `None` (B)

`IdentityMixin.client_id` is a python-side `default=lambda: generate_id(prefix)`
(`models/base/identity.py:22-30`), applied at INSERT. Verified in this workspace:

```
unsaved group client_id = None
unsaved group is_deleted = None
basis fk = None | equal: True
explicit client_id works = 'pcg_explicit'
```

So an unsaved `ProductionCostBasisVersion(production_cost_group_id=wood_group.client_id)`
carries `None`, and the classifier's `version.production_cost_group_id == group.client_id`
is `None == None → True`. C5's V4 row ("the only applicable basis version hangs on the
WOOD group") would then find the basis applicable to the seat group and return `OK` — the
row passes only if the implementer happens to assign ids. The plan's preamble
(`plan:249-252`) pins `Decimal`/enum fields explicitly but says nothing about `client_id`.

**Proposed amendment (C5 preamble):** "every unsaved `ProductionCostGroup` /
`ProductionCostBasisVersion` / `CostModelVersion` instance is constructed with an explicit,
distinct `client_id`" — the join key must not be defaulted. (Secondary: unsaved
`is_deleted` is `None`, which is falsy and therefore reads as active — correct for the
active rows, and V4b/L-11's deleted rows must set `is_deleted=True` explicitly.)

---

## Should-fix rows

**L-7 — C2(c) as written is refused by the wrong index.** `plan:309-311` specifies the
key-accept row as "same workspace, both active, wood + seat" varying `major_category`
only — which implies the same `name`, and
`uix_production_cost_groups_name_active` (`production_cost_group.py:26`) rejects it.
Amendment: state that every multi-group C2 fixture differs in `name` (a background
invariant, audited per P-K), and that (c) isolates `major_category` **against (a)**, which
shares the category and already differs in name. (d)'s two-workspace row is unaffected —
the name index is per workspace.

**L-8 — the sole-reader rule overstates and has no arbiter.** §6.5 (`master_plan.md:370`)
registers `resolve_major_category` as "the ONLY reader of the item's category-snapshot
string". Repo-wide that is false today: `services/queries/items/seat_tasks_pending_upholstery.py:25`,
`services/queries/utils/task_search.py:55`, `services/queries/upholstery/upholstery_order_needs.py:270,489`,
`services/queries/upholstery/upholstery_orders_query.py:204,387`,
`services/queries/working_sections/list_working_section_steps.py:147`,
`domain/items/serializers.py:86`, `domain/tasks/serializers.py:116` all read the column.
Route to §6.5: scope the claim to the item-economics domain. Optional in-4B structural
row (recommended, cheap): no module under `domain/item_economics/` or
`services/**/item_economics/` reads `item_major_category_snapshot` except through
`resolve_major_category` — vacuous in 4B, bites the moment phase 5's preview reads the
column directly.

**L-9 — §6.4's message clause cannot hold on the DB path.** `translate_integrity_error`
emits a fixed sentence with no category in scope
(`_common.py:37`: `f"{identity}: configuration conflicts with an existing row"`), while
§6.4 (`master_plan.md:322-326`) says the identity's "message names the category value".
Route to §6.4: scope that clause to the pre-check path (consistent with phase-4 N4's
uniform conflict shape). Left as-is, a 4B reviewer files it as a defect against correct code.

**L-10 — C4(a) asserts the token but not the message.** §6.4 requires
`ITEM_COST_GROUP_CATEGORY_IMMUTABLE`'s message to name "the group and its current
category"; C4(a) (`plan:337-341`) asserts only the leading token. Add both substrings,
asserted individually (P-O — an `or` is satisfiable by half).

**L-11 — the classifier's `is_deleted` group filter has no arbiter.** Every C5 group
fixture is active (V2's wood group, V3's two seat groups, V4–V6's seat group), so deleting
`not getattr(group, "is_deleted", False)` from the active-group comprehension
(`configuration.py:43`) leaves all C5 rows green. Add **(V2b)**: the only seat group is
soft-deleted → `not_configured_no_cost_group`, with that deletion as its named mutation.

**L-12 — task 7's documentation target is wrong.** `routers/README.md` is a route table
(method | path | tag | operation id — see `:58-65` for the cost-group rows) and 4B adds no
route, so there is nothing to mirror. The documentation that does go stale is
`beyo_manager/models/tables/item_economics/README.md`, whose closing paragraph enumerates
the reused enum types and states "migrations must not create or drop those reused types" —
`item_major_category_enum` belongs in that sentence. Retarget the doc task (still a task,
not a criterion — phase-4 S5 precedent).

**L-13 — C1(a)'s `compare_metadata` row has no harness.** No test in `tests/` calls
`compare_metadata` (phase 2's zero-diff result was a reviewer-run check, not a shipped
row). Run by hand against the configured dev DB today it returns **4 diffs repo-wide** —
removed table `ended_shift_collapse_journal`, removed unique
`email_sync_states_connection_id_key`, removed indexes
`ix_step_state_records_ws_credited_entered` / `ix_step_state_records_ws_flagged_entered` —
and **0 on `production_cost_groups`**. So the row is buildable and the table is clean, but
an unfiltered assertion reddens on pre-existing drift. Amendment: C1(a) names the harness —
`MigrationContext.configure(sync_conn, opts={"compare_type": True})` +
`compare_metadata(ctx, Base.metadata)`, filtered to `production_cost_groups` — the way §10
names the DB recipe (P-R's spirit, applied to autogenerate).

**L-15 — the pre-flight's remediation is not a single DELETE.** `production_cost_groups`
is referenced with `ondelete="RESTRICT"` by `production_cost_group_sections`,
`production_cost_basis_versions` and `item_cost_evaluations`, so "the operator deletes them
and re-runs" (`plan:110-111`) can itself fail. Amendment: the `RuntimeError` report names
the dependent tables and their counts alongside the group `client_id`s (report-never-guess,
extended to the repair). Context: the dev DB holds **0** group rows and 0 dependents today
(verified), but phase-4 fix r2's C3/C6 rows commit, and their teardown is the only thing
keeping it at 0 — if the pre-flight fires on the dev DB, the implementer's instruction is
to delete the residue, never to weaken the guard.

---

## Explicit delegations (freedom granted, not taken)

| # | Delegated | Constraint |
|---|---|---|
| D-1 | Internal decomposition of `resolve_economics_configuration` | pure, no I/O, date injected (phase-4 N1, restated) |
| D-2 | **Pre-check ordering** — `ITEM_COST_GROUP_NAME_TAKEN` before/after `ITEM_COST_GROUP_CATEGORY_TAKEN` on create; the existing name pre-check before/after the immutability guard on update (L-14) | recommend keeping the shipped name pre-check first in both commands; the plan's fixtures already avoid overlap (C4(a) reuses the group's own name and `update_production_cost_group.py:21` excludes self) |
| D-3 | Exact wording/format of the pre-flight `RuntimeError` | must carry count + `client_id`s + dependent-table counts (L-15) |
| D-4 | Declaration position of `ITEM_MISSING_MAJOR_CATEGORY` in `EconomicsStatusEnum` | already granted by the plan (§6.3: order carries no precedence); C5's M3 probe is the guard |
| D-5 | Which layer carries C7(d)'s canonicalization rows | recommend the command request model; the router body model is already covered structurally by C7(c) |
| D-6 | New 4B test file names and layout | mirror the existing `tests/{unit,integration}/…/item_economics/` layout |
| D-7 | Exact assertion shape of C1(a)'s `compare_metadata` row | recipe and filter per L-13 |

---

## Reality checks (paths, citations, dependencies)

**Verified accurate — cite, do not re-derive:**

| Plan claim | Verification |
|---|---|
| `ItemMajorCategoryEnum` at `domain/items/enums.py:17`, `WOOD="wood"`, `SEAT="seat"` | ✅ exact; plain `enum.Enum` (not a str-enum), so pydantic rejects `"WOOD"` — C7(d) is decidable |
| Type ownership on `item_categories.major_category`, `create_type=True` | ✅ `models/tables/items/item_category.py:24-28` |
| PG labels live in the dev DB: `wood`, `seat` | ✅ queried `pg_enum` — exactly two, in that order |
| `items.item_major_category_snapshot` is `String(64)`, nullable | ✅ `models/tables/items/item.py:51` |
| Snapshot writers assign `.value` or `None` only | ✅ `_create_item_in_session.py:86`, `update_item.py:80,93`, `find_or_create_item.py:106,119,145` |
| `resolve_economics_configuration`'s only production caller is the status query | ✅ grep-verified across `app/` |
| The group serializer feeds create/update/delete/list | ✅ all four call `serialize_production_cost_group` |
| Pre-flight idiom `97b60e06d42a` (RuntimeError before DDL) | ✅ `:104`, `:195`, `:202` |
| Reused-enum idiom `677ed7131bb2` / `90cdd23a828e` (`create_type=False`) | ✅ present in both |
| Partial-unique idiom `595e7b840926` (`postgresql_where`) | ✅ `:44,50` |
| `test_schema_inventory_is_closed` asserts CHECKs exactly, indexes as a **subset** | ✅ `:141-144` — the new index is invisible until `INDEX_NAMES` grows, exactly as the plan says |
| Group delete guard counts only non-deleted basis versions (the escape hatch) | ✅ `delete_production_cost_group.py:20-26` — and it also refuses on **active section memberships** (`:28-34`), which the plan's escape-hatch sentence omits |
| Phase-4 C10 is the non-concurrent name-uniqueness precedent the plan cites | ✅ `plans/phase_4_configuration_services.md:237-242` ("both paths") |
| Static-proxy idiom for C1(b)/(c) | ✅ `test_item_economics_schema.py:180-203` (`importlib.import_module` + `inspect.getsource`) |
| Alembic head for the new revision | ✅ single head `90cdd23a828e`; phase 4 added no migration |
| `compare_metadata` clean on `production_cost_groups` | ✅ 0 of 4 repo-wide diffs (see L-13) |

**Inaccurate or incomplete:**

- The plan's Read-first calls **§7A.5** "superseded rows" — but §7A.5 (`intention.md:1020-1034`)
  carries **no** supersession pointer, unlike §7.4 which does (`:907-909`). §11A.4
  (`:1710-1729`) likewise still lists nine group-2 values with no pointer to §7C.3's twelve.
  Route to the intention: pointer lines only, no renumbering (charter's amendment rule). (N-b)
- "Files expected to change" says "**the four** named phase-4/phase-2 test changes (task 8)"
  (`plan:93`) while task 8 names **five**. P-L: items, never counts. (N-a)

---

## Criteria decidability

Could I write each row today, from the artifacts alone, with one exact expected outcome?

| Criterion | Decidable | Note |
|---|---|---|
| C1(a) live-schema rows | ⚠ | harness unnamed → L-13; the rest (atttypid join, one `pg_type` row, `get_indexes` predicate) is exact |
| C1(b) pre-flight proxy + mutations | ✅ | source-assertion idiom exists; report contents → L-15 |
| C1(c) downgrade proxy | ✅ | `.drop(` / `DROP TYPE` absence assertions are exact |
| C1(d) enum reuse at the migration site | ✅ | source assertion + the one-`pg_type` behavioural arbiter |
| C2(a),(b),(d) | ✅ | key/predicate coverage complete under P-M |
| C2(c) | ❌ | unbuildable as written → L-7 |
| C3(a) | ✅ | |
| C3(b),(d) | ❌ | unbuildable as written → L-4 |
| C3(c) | ✅ | sole-cause stated (no basis row) |
| C4(a) | ⚠ | message content unasserted → L-10 |
| C4(b),(c),(d) | ✅ | P-Q fixtures correct; the breadth mutation is well-sited |
| C4(e) | ⚠ | green for the wrong reason through HTTP → L-5 |
| C5 V0–V6, P1–P5 | ⚠ | totality is right; fixtures join on `None` → L-6; missing deleted-group row → L-11 |
| C5 M1–M3 | ✅ | M3's disposable-worktree permutation is the shipped phase-4 idiom |
| C6(a)–(d) | ✅ | exact-dict equality; the phase-4 idiom exists (`test_configuration_commands.py:65-72`); (d)'s named mutation is well-sited |
| C7(a),(b),(d) | ✅ | |
| C7(c) | ✅ | `model_fields` introspection is its own harness |
| C8 | ⚠ | depends on phase-4 fix r2 actually landing the C11 route rows — today **no test references the item-economics router** (phase-4 B1), so "must remain green" has nothing to keep green (N-e) |

**Totality of §7C.2 (depth target 1).** The rule set is total over
(category present / absent) × (0 / 1 / ≥2 same-category groups) × basis × model states:
`resolve_major_category` collapses "unknown string" into `None` before the classifier sees
it (L2 pin), so the classifier never faces a third category state. `item_missing_major_category`
is first, the ambiguous row is retained as the unreachable defence row, and each C5 fixture
fails exactly its own predicate. The one uncovered cell is the soft-deleted same-category
group (L-11). Adjacent pairs P1/P3/P4 are correct; P2's "N/A — predicates disjoint" is a
genuine gap, correctly declared rather than sampled; P5's collapse into V5 is explicit (P-G).

---

## Notes (no routing required)

- **N-a / N-b** — see "Inaccurate or incomplete" above.
- **N-c** — §6.4's "Selection (§7A.5, in order)" error list registers no
  `ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY`, but §7C.2 says the missing category is a
  "status/**refusal**". 4B builds only the status side; phase 7's commit path will need the
  identity registered before use. Forward to phase 7.
- **N-d** — live vocabulary check: `items.item_major_category_snapshot` holds exactly
  `wood` (225), `seat` (193), `NULL` (37) in the dev DB. So L2's unknown-string branch is a
  defence row against a population that does not exist, and `item_missing_major_category`
  is a **live** outcome for 37 items — worth knowing when phase 5's preview ships.
- **N-e** — C8's regression premise (see the table above).
- **N-f** — phase-4 fix r2's perimeter overlaps 4B's (`requests/__init__.py` bounds,
  `routers/api_v1/item_economics.py` field removal, `_common.py` dead-code deletions) and it
  adds ~54 test rows, many of which will construct cost groups. The plan's Dependencies
  block already tells the coordinator to re-run its greps at prompt time; add
  `ProductionCostGroup(` to that grep list — it is the pattern that hides L-1.
- **N-g** — `compare_metadata(compare_type=True)` is clean on all nine economics tables
  today, so task 2's reused-enum mirroring starts from a verified-clean baseline.
- **N-h** — the plan's escape-hatch sentence ("the group delete guard counts only
  non-deleted versions") is true but partial: the guard also refuses on active section
  memberships (`delete_production_cost_group.py:28-34`). Delete-and-recreate after a refused
  flip therefore also requires removing the group's sections. Not a defect — worth one
  clause so the implementer does not read the guard as basis-only.
- **N-i** — `group_count` is the only numeric in the reshaped payload and is a count, not an
  economic figure; P-B (no inferred zeros) is not engaged by `group_count: 0`. Verified, not
  a finding.

---

## Write perimeter (full)

- **Documents written:** this handoff only —
  `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase4b_projection_r0_handoff.md`.
- **Code written:** none. No plan, intention, master-plan or `app/` file was edited.
- **Scratch:** one throwaway script in the session scratchpad
  (`…/scratchpad/cmp.py`, the `compare_metadata` probe) — outside the repo.
- **Database:** read-only. Four `SELECT`s against the configured dev database
  (`production_cost_groups` counts, dependent-table counts, `pg_enum` labels,
  `items.item_major_category_snapshot` distribution) and one read-only
  `compare_metadata` connection. No DDL, no writes; the dev DB is untouched and at head.
- **Archgraph:** no `archgraph_*` call made this session; **zero delta**. Per the prompt,
  the 47 pending phase-4 items were neither touched nor verified.
- **Git:** nothing committed, nothing staged.

## Exit gate

Verdict **AMENDMENTS_REQUIRED**. Six blocking rows (L-1…L-6), seven should-fix
(L-7…L-13, L-15) and one delegation cluster (L-14 / D-1…D-7). The implementer prompt
compiles once the ledger is routed **and** phase 4 is APPROVED. Zero owner cards — the
gate does not need the owner to move.
