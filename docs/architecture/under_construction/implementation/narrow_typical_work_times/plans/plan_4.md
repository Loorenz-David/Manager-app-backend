# Plan 4 — The division contract, production-time and budget-allocations

```
plan: plan_4
project: narrow_typical_work_times
state: NOT_STARTED
projection_gate: MANDATORY
```

## 1. Goal

Turn the engine on for task economics: both division consumers derive a spec, call the
statement with specs, build `SectionTypicalEvidence`, reconcile through
`uniform_basis_v1`, and feed **the same `SelectedTypical`s** to display and to weights.
`divide_production_budget`'s third parameter becomes `Mapping[str, SelectedTypical]`,
`DivisionStep.typical_worker_seconds` and both fallback reads are removed,
`ALLOCATION_METHOD` becomes v2, and §7.2/§7.3's new keys ship.

**Explicitly NOT in this phase:** price-scenario — it never calls division, and its clock
change, its private ladder and `is_estimated` are **plan 5**. `/working-sections/typical-times`
stays byte-identical (D24). No new domain object (plan 1 shipped them). No statement change
(plan 2 shipped it). No `/statistics/typical-times` route.

**Why two consumers are in one phase:** changing `divide_production_budget`'s third parameter
breaks both call sites at once, and a phase must close green.

## 2. Read first

- Master plan §§4, 6.2, 6.4, 6.5, 6.7, 6.9, 7, 9, 10.
- Intention **header**, then §2.2 F-C/F-D/F-E/**F-F (stale — see §2B S-4)**/F-G/F-H,
  §2B S-4, S-5, S-6, S-7, §3.5, §3.6, **§3B** in full, §4.3, **§4A** K1–K4, **§4B**,
  **§4C**, §4.5, §6.1, §6.2 rows 2/3/6, §6.3, §6.4 (**superseded on `is_estimated` by §6B —
  but §6B's division half binds here**), **§6C** in full, §7.2, §7.3, §8, §11.1 rows
  T1/T2/T3/T4/T5/T6/T7/T8/T9/T16/T21, **§11A** in full (T10a, T16b as amended by §4C, T23,
  T24, and the correction to §8), §11.2.
- `planning/owner_decisions.md` — D2, D7, D9, D12, D16, D18, D20, D22, D23, **D25**.
- Gate handoff §2 rows 5, 8, 12, 14 and §5.
- **The neighbouring pipeline's approved authority, read at source:**
  `docs/architecture/archives/live_clock_for_working_time_economics/planning/intention.md`
  §1A HC-1A (never assign to `TaskStep.total_working_seconds`), §2.5A (the eight-row settled
  consumer inventory — row 5 is this statement), §4.3A (**three** paths from worked seconds
  to `allowance_seconds`; path 3 is the typicals statement).
- Code: `budget_division.py` (whole file); `division_serializers.py` (whole file);
  `get_task_production_time.py` (whole file); `get_task_budget_allocations.py` (whole file);
  `test_budget_division.py`.

## 3. Dependencies

**Gate: plan 3 `APPROVED`.** production-time reads `status.typical_filter_spec`, which plan 3
adds; budget-allocations derives its own from `item_by_id` / `primary_by_task`.

## 4. Files expected to change

**Modified — production**
- `app/beyo_manager/domain/item_economics/budget_division.py`
- `app/beyo_manager/domain/item_economics/division_serializers.py`
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`

**Modified — tests / goldens**
- `app/tests/unit/domain/item_economics/test_budget_division.py`
- `app/tests/integration/services/queries/item_economics/goldens/golden_production_time.json`
- `app/tests/integration/services/queries/item_economics/goldens/golden_budget_allocations.json`

**New**
- `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py`
- `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`

**Read-only, and a change is a finding**
- `goldens/golden_budget_status.json` · `get_task_price_scenario.py` ·
  `get_working_section_typical_times.py` · the plan-1 SQL snapshot.

## 5. Ordered tasks

1. **`divide_production_budget`'s third parameter becomes `Mapping[str, SelectedTypical]`.**
   Annotate under `if TYPE_CHECKING:`; at runtime keep reading through the existing
   `_value(obj, name)` helper, which already accepts objects and mappings alike. Import
   `apply_business_fallback` from `typical_filters` at module scope — the cycle was broken in
   plan 1 by moving the constants (master plan §6.1).
2. **The weight ladder delegates to `apply_business_fallback(..., terminal=Fraction(1, 1))`.**
   Usable = not `None` and `> 0`; the arithmetic is identical to today's, and D22's two
   terminals stay two. `Fraction(1,1)` is **also a division-by-zero guard**: with
   `terminal = 0` and no usable typical anywhere in the task, every resolved weight is `0`,
   `total_weight` is `0`, and `budget_division.py:338-343`'s `… / total_weight` **raises**
   (§11A's correction to §8). C4's mutation therefore reddens by raising.
3. **`_step_result` emits `typical_basis` and `sample_count`** from the `SelectedTypical`,
   and its `typicals.get(section_id, _value(step, "typical_worker_seconds"))` becomes a
   lookup whose miss is contracted by **§3B B4** — never a `KeyError`, never a step-attribute
   read. Section rows carry the same two fields.
4. **Remove `DivisionStep.typical_worker_seconds` and both fallback reads**
   (`budget_division.py:264`'s two-argument `.get` default and `:324`'s
   `if typical is None` read). **The removal edits two PRODUCTION files** —
   `get_task_production_time.py:50-62` and `get_task_budget_allocations.py:217-229` both pass
   `typical_worker_seconds=None` — plus the test constructors. §11.1 says "8 test
   constructors"; measured, `DivisionStep(` appears 8× in `test_budget_division.py` but only
   **6** pass the field, and the real edit surface is the **20** `typical=` argument passes.
   Count at source before editing. `:324`'s surrounding `if typical is None` branch is **not**
   deleted — only the read inside it.
5. **`ALLOCATION_METHOD` → `static_proportional_section_v2`** (§6.3, D20). §6.3's phrasing is
   **normative for the frontend handoff** and must not be paraphrased: *"Every task is now
   evaluated under the new rule; allowances are **eligible** to change wherever item-category
   narrowing changes the relative section weights… The contract changes even where an
   individual numeric result does not."*
6. **`divide_production_budget`'s internal exclusion predicate delegates to
   `participating_sections`** (§6.1) — one implementation, not a fourth copy.
7. **production-time.** Spec from `status.typical_filter_spec`. `specs=()` when the spec is
   non-narrowing or `None`; otherwise `specs=(spec,)` (§4A K3: callers normalize, and pass
   only *narrowing* specs). Keep `now=ctx.now` — **unchanged**. Build
   `SectionTypicalEvidence` per section, `participating_sections(steps)`, then
   `reconcile_task_typicals`. **Reconcile BEFORE division** (F-D): the
   `allowed_worker_minutes is None` branch returns early computing no participating set, yet
   production-time still renders sections, so the no-budget branch must also get a complete
   reconciled block. The **same** `SelectedTypical`s feed the `typicals` display block and
   the division weights.
   Note §2B S-7: production-time scopes the statement to **every** step's section.
8. **budget-allocations.** Derive one spec per task from `item_by_id` / `primary_by_task`
   (already loaded — zero additional queries). **Dedupe by value** into an ordered sequence of
   *narrowing* specs; a task whose spec is non-narrowing maps to `spec_index = None` and takes
   `narrowed_* := section_*` with a section-wide basis (§4A K3, §3B B1). **One statement call
   for the batch.** If every task's spec is non-narrowing, pass `specs=()`. Keep
   `now=ctx.now` — unchanged. Per-task reconciliation, then division.
   Register the local name `spec_index_by_task` for the mapping back.
9. **§7.2 / §7.3 payloads.** `division_serializers.py` enumerates its keys explicitly
   (`:36-47`, `:102-108`) — new fields must be added **by name**, with the always-present
   defaults of §7. Add `serialize_filter_spec` and `serialize_typical_resolution` here
   (master plan §6.5) so plan 5 imports one implementation.
10. **Goldens.** Regenerate `golden_production_time.json` and `golden_budget_allocations.json`
    on the post-live-clock baseline. **The live-clock fixture is NOT taught to narrow.** It has
    no COMPLETED steps (F-H), so post-refactor it yields counts `0`, basis
    `insufficient_sample`, `task_typical_basis: "section_wide_uniform"`, `applied_filter: null`
    and — one section — an unchanged allowance.
    **Regeneration is approved only if the diff adds keys.** Any changed `allowance_seconds`,
    `left_seconds`, `share_state`, `worked_seconds` or budget figure means the refactor moved
    something it was not supposed to move: that is a **gate failure, not a regeneration**.
11. Tests per §6. Record the architecture-graph delta (one batched `apply_changes`). Update
    the tracker row and the Review log.

## 6. Tests / acceptance criteria

### C0 — inherited: strengthen the domain-purity guard (three measured escapes)

**Carried here from phase 1** (owner ruling 2026-08-22: a guard-over-a-guard does not
justify its own implement-and-stamp cycle; it belongs to the phase that already edits the
code it guards — this one). `app/tests/unit/domain/item_economics/test_domain_purity.py`
holds phase 1's C4(c) and C17 as committed tests. **Three escapes were measured on the
approved phase-1 tree; do not re-measure them, close them:**

| # | escape | measured | fix |
|---|---|---|---|
| 1 | the package walk is `glob("*.py")`, **non-recursive** — a module in a future subpackage is never scanned | `import hashlib` in `…/item_economics/sub/leak.py` → **2 passed** | `rglob("*.py")` |
| 2 | the pinned exception strips **every** occurrence of `config_fingerprint`, not the pinned line, so a second use in another shape is erased before the assertion sees it | a second, differently-shaped use appended to `serializers.py` → **2 passed** | strip only the pinned occurrence; keep the `count(...) == 1` pin |
| 3 | the C17 half **passes vacuously on an empty walk** — nothing asserts the walk found anything (its sibling fails only by accident, via `FileNotFoundError` when it reads `serializers.py` to pin the exception) | `PACKAGE_ROOT` repointed at a non-existent directory → that test **passes** | assert the walk is non-empty, **as a contract, not the literal `10`** (rule 13) |

*Named mutations, all three required, both sides:* re-apply each escape above; each must
now redden. Plus the two regression probes that already bite and must continue to:
`import hashlib` in `typical_filters.py`, and
`from beyo_manager.models.tables.items.item import Item`.
*Defect caught:* a purity guard that phases 4 and 5 rely on while it silently guards
nothing — escape 3 is the shape that makes the whole file a no-op.
*Standing rule this earned (master plan §9):* **a guard that walks a directory needs a row
proving the walk found something.** Three escapes in one small file, all the same shape:
the guard's own preconditions were unasserted.

---

Hypothesis scope: L1 = `test_narrowed_task_economics.py` / `test_budget_division.py`.
C1's third row and C13's sweep are **absence claims** and run at **L4** with their roots and
term sets stated. C5, C7, C11 and C12 name cross-file bite sets and run at L2 =
`tests/integration/services/queries/item_economics/` + `tests/unit/domain/item_economics/`.

**C1 — typicals stay settled-basis (§6C, T24). Critical rank 5.**
(a) **production-time**: a task with an open WORKING record, served **twice at two `ctx.now`
values** over identical database state → every `allowance_seconds` is identical across the
two calls, asserted as exact literals per section.
(b) **budget-allocations**: the same task, the same two `ctx.now` values → the same equality,
asserted separately. (One probe per member: a blanket "both consumers are settled" claim needs
its own row per consumer.)
(c) **absence, L4, root = repository root, terms stated**: no site reachable from
`divide_production_budget`'s inputs passes a value derived from `load_live_worked_seconds`
into a typical, a sample count, or the item-match predicate. Search terms: `live_seconds`,
`load_live_worked_seconds`, `total_working_seconds`. Expected ∅ within the typicals path.
*Mutations, one per sub-check*:
(i) `get_task_production_time` (call site): pass `live_seconds[step]` into one section's
`SelectedTypical.typical_worker_seconds` → **row (a)** flips: contract, allowances identical;
mutation, that section's weight ticks, `total_weight` changes, `_largest_remainder`
redistributes, and **every** section's allowance moves between the two calls.
(ii) `get_task_budget_allocations` (call site): the same substitution → **row (b)** flips;
row (a) does **not** — recorded per rule 12.
*Why this row exists*: the neighbouring pipeline calls a "make it consistent" change here
**"the most expensive mistake available in this feature"**, and records that no guard against
it existed anywhere in the repository until its own phase 2 round 6. After this phase, both
consumers hand `divide_production_budget` `DivisionStep`s whose `total_working_seconds` **is**
the live figure, alongside typicals that must not be. **The two live in the same call.**
*Also binding*: charter rule 3 / HC-1A — no code in this phase assigns to
`TaskStep.total_working_seconds`, ever. Assert it: after serving both endpoints against the
open-record task, the column re-read from the database is unchanged.

**C2 — `ALLOCATION_METHOD` is v2 on every surface that publishes it.**
Assert the exact literal `"static_proportional_section_v2"` on production-time's task block
and on every budget-allocations task entry; and that no payload anywhere carries
`"static_proportional_section_v1"`.
*Mutation* — `budget_division.ALLOCATION_METHOD` (definition): revert to v1.
*Both sides* — contract: both payloads carry v2; mutation: both carry v1.
*Rule 13 note*: this criterion pins a configured **value** as an exact literal, deliberately.
The version string **is** the contract the frontend keys on (D20, §6.3) — it is not the
time-bomb shape rule 13 forbids, which is pinning an incidental setting.

**C3 — `DivisionStep.typical_worker_seconds` is gone, and its absence is total.**
(a) `"typical_worker_seconds" not in {f.name for f in fields(DivisionStep)}`.
(b) `divide_production_budget` given a section id present in the steps and **absent** from
the selection mapping produces a step row with `typical_worker_seconds: None`,
`typical_basis: "insufficient_sample"`, `sample_count: 0`, and its `allowance_seconds`
computed — never a `KeyError` (§3B B4).
(c) A soft-deleted working section named by a task's steps produces row (b)'s shape end to
end on production-time.
*Mutation* — `budget_division._step_result` (definition): index the selection mapping with
`[]`.
*Both sides* — contract (b): the row exists with those three values; mutation: `KeyError`.
*Defect caught*: today's two-argument `typicals.get(section_id, _value(step,
"typical_worker_seconds"))` fires its default only on a **missing key**, never on a `None`
value — an accidental cover that D18's removal deletes. §3B B4 is what replaces it.

**C4 — T4 row (a): the division terminal, and its second job.**
Fixture: a task where **no** participating section has a usable typical (all `None`).
Assert every `allowance_seconds` is the even split of `distributable_seconds` — exact
literals — and that the neutral weight appears **nowhere** as seconds on the payload.
*Mutation* — `get_task_production_time` (call site) / `budget_division` (definition): pass
`terminal=Fraction(0, 1)` to `apply_business_fallback`.
*Both sides* — contract: the even split; mutation: `total_weight == 0` and
`budget_division.py:338-343` raises `ZeroDivisionError`. **The row reddens by raising, not by
asserting a different number** — say so in the test's docstring, because a reader who expects
a value mismatch will "fix" the test.
*T4 row (b)* — price-scenario's `Fraction(0,1)` terminal — is **plan 5 C4**. Each row bites on
its own terminal.

**C5 — layer-2 visibility on division surfaces (T16, T16b′, §6.4, §3B B2).**
| # | fixture | expected step/section row |
|---|---|---|
| a | participating section whose **selected** value is `None` (section-wide count below floor) | `typical_worker_seconds: null`, `typical_basis: "insufficient_sample"`, `sample_count: <section_sample_count>` (§3B B3), `allowance_seconds` present and non-null |
| b | **T16b′** — a `section_wide_uniform` task with a participating section whose **section-wide** median is `0` at count ≥ floor | `typical_worker_seconds: 0`, `typical_basis: "section_wide"`, `sample_count: <n>`, `allowance_seconds` present |
| c | task level, row (a)'s task | `sections_by_basis.insufficient_sample >= 1` |
*Mutations, one per sub-check*:
(i) `budget_division._step_result` (definition): emit the filled weight as
`typical_worker_seconds` → **row (a)** flips `null` → `1` (the `Fraction(1,1)` rendered).
Row (b) does not bite.
(ii) `_step_result` / `division_serializers` (definition): publish `null` +
`insufficient_sample` for a zero-valued statistic → **row (b)** flips `0`/`section_wide` →
`null`/`insufficient_sample`. Row (a) does not bite — recorded per rule 12.
*§4C note, so row (b)'s fixture is not "corrected" back*: §11A's original T16b used **7
same-category groups all summing 0** and expected `typical_basis: "item_narrowed"`. D25 made
that shape unreachable on task surfaces — a zero narrowed median now disqualifies the
narrowed rung. The **reachable** zero form is `section_wide` + `0`, which is row (b). The
assertion (a zero statistic is disclosed as a statistic, never as `insufficient_sample`) is
unchanged.

**C6 — `sections_by_basis` counts participating sections only, and sums to
`participating_section_count` (§7.2).**
Fixture: 3 participating (0 `item_narrowed` / 2 `section_wide` / 1 `insufficient_sample`) and
1 **excluded** section whose independently-resolved basis is `item_narrowed`.
Assert `sections_by_basis == {"item_narrowed": 0, "section_wide": 2,
"insufficient_sample": 1}` (exact dict literal) and `participating_section_count == 3`, and
that the two agree: `sum(sections_by_basis.values()) == participating_section_count`.
*Mutation* — `division_serializers.serialize_typical_resolution` (definition): count every
section in `selected` instead of the participating ones.
*Both sides* — contract `{0, 2, 1}` summing to 3; mutation `{1, 2, 1}` summing to 4 ≠ 3.
*Defect caught*: excluded rows blurring the reconciliation story the object exists to tell.

**C7 — T9 excluded independence, both directions, on the wire.**
(a) a thin **excluded** section beside participating sections that are all
`has_usable_narrowed` → `task_typical_basis` stays `"item_narrowed_uniform"` **and** the
excluded row shows its **section-wide** value with `typical_basis: "section_wide"`.
(b) mirrored — a well-sampled narrowed **excluded** section on a `section_wide_uniform`
task → the excluded row shows `"item_narrowed"` while every participating row shows
`"section_wide"`.
*Mutation* — `typical_filters.reconcile_task_typicals` (definition): include excluded ids in
the quantifier → **row (a)** flips `item_narrowed_uniform` → `section_wide_uniform`.
*Both sides* — exact `task_typical_basis` string literals.
*Note*: plan 1 C8 row (e) observes the **same** mutation at the domain layer. This row is
**variation, not redundancy** — a different site and a different observable (the serialized
payload rather than the returned object), which is exactly what the charter's reuse rule buys
independent verification with.
*Consequence, stated so it is never reported as a bug*: an excluded row's `typical_basis` may
differ from the participating rows' uniform basis, in either direction.

**C8 — T8: the no-budget branch reconciles (F-D).**
Fixture: a task whose economics status is outside `{OK, INFEASIBLE}` (so
`allowed_worker_minutes is None`).
Assert production-time still returns a **complete** `typical_resolution` block — all six keys
present, `task_typical_basis` a real value, `applied_filter` populated for a chair task — and
a complete per-section `typical` block for every rendered section, with
`allowance_seconds: null` and `share_state: "no_budget"`.
*Mutation* — `get_task_production_time` (call site): move reconciliation inside
`divide_production_budget`.
*Both sides* — contract: `typical_resolution` present with `task_typical_basis ==
"item_narrowed_uniform"`; mutation: the `allowed_worker_minutes is None` early return
(`budget_division.py:285-305`) computes no participating set, so the block is absent.

**C9 — T3 + T23: the no-category task converges, and its new string fields tell the truth.**
Fixture: a task whose primary item has no `item_category_id`.
(a) **Every pre-existing numeric field is unchanged** on production-time and
budget-allocations, compared against the pre-refactor payload for the same fixture. §4A K5's
wording is normative and must not be paraphrased: here "unchanged" means *every pre-existing
numeric field unchanged*, **not** byte-identical, since §7.2/§7.3 add keys.
(b) The statement is called with `specs=()` — the K == 0 shape.
(c) `task_typical_basis == "section_wide_uniform"`, every participating `typical_basis ==
"section_wide"`, `applied_filter is None`.
*Mutations, one per sub-check*:
(i) `typical_filters.derive_spec_from_primary_item` (definition): return a non-empty spec for
category-less items → **rows (b), (c)** flip: the statement takes the K ≥ 1 branch and
`applied_filter` is non-null.
(ii) `typical_filters.reconcile_task_typicals` (definition): consult `has_narrowed` before
checking `spec.is_narrowing` → **row (c)** flips `section_wide_uniform` →
`item_narrowed_uniform` beside a **null** filter. **Row (a) does not bite** — it asserts
numeric identity, and these are new string fields. That is precisely why T23 exists as a
separate row.

**C10 — batch dedupe: K distinct specs, one statement call.**
Fixture: 50 tasks — 20 chair, 15 table, 10 stool, 5 with no category.
Assert: (a) exactly **one** execution of `typical_times_statement` in the request, counted by
a session spy that **delegates** (`wraps`), never a fake that discards the statement;
(b) `K == 3` — the five category-less tasks are **not** members of the sequence (§4A K3);
(c) a chair task's step rows carry the chair population's `sample_count`, asserted as an exact
literal; (d) each of the five category-less tasks carries `typical_basis: "section_wide"` and
`applied_filter: null`.
*Mutations, one per sub-check* — both in `get_task_budget_allocations` (call site):
(i) dedupe by `id(spec)` instead of by value → **row (b)** flips `K == 3` → `K == 45`.
(ii) map tasks to `spec_index` by task insertion order rather than by the spec's position in
the deduped sequence → **row (c)** flips: contract, the chair task's `sample_count` is the
chair population's (e.g. `20`); mutation, it is the table population's (e.g. `15`).
*Defect caught*: Critical rank 3 (two specs meaning one population becoming two indices) and
Critical rank 2 (a mis-keyed row attributing one category's history to another task), observed
at the caller rather than at the SQL.
*Fixture caution*: the corpus rule — **before citing a test as proof of a SQL predicate, check
that the test issues SQL.** Rows (c) and (d) must run against a real session; only row (a)
uses the spy.

**C11 — HC-2, first half (T6a): production-time and budget-allocations agree.**
For every participating section of the same task at the same frozen `ctx.now`, the triple
`(typical_worker_seconds, typical_basis, sample_count)` from production-time's section
`typical` block **equals** budget-allocations' step row's — asserted per section as exact
literals on **both** sides, never as an equality between two calls.
*Mutation* — `get_task_budget_allocations` (call site): resolve typicals locally instead of
through the shared selection (e.g. take `section_typical_worker_seconds` unconditionally).
*Both sides* — contract: both surfaces report `("540", "item_narrowed", 7)`-shaped triples;
mutation: budget-allocations reports `(600, "section_wide", 61)` where production-time reports
`(540, "item_narrowed", 7)`.
*This row also discharges charter rule 10* (operational reachability): its fixture is an
ordinary seeded chair task under the **shipped default** configuration, and it asserts
`task_typical_basis == "item_narrowed_uniform"` — the narrowing path is reached by the
defaults, not only by tests.

**C12 — goldens: keys only.**
*Automated half*: after regeneration, the live-clock golden fixture's payloads carry the new
keys at their documented defaults — `typical_basis: "insufficient_sample"`,
`narrowed_sample_count: 0`, `section_sample_count: 0`, `sample_count: 0`,
`task_typical_basis: "section_wide_uniform"`, `applied_filter: null`,
`sections_by_basis` summing to `participating_section_count` — asserted as literals in
`test_narrowed_task_economics.py`, and the byte-golden tests in `test_live_clock_goldens.py`
are green.
*Review half, not automatable and stated as such*: the reviewer diffs each regenerated golden
against its predecessor and confirms the change is **key additions only**. Any changed
`allowance_seconds`, `left_seconds`, `share_state`, `worked_seconds` or budget figure is a
**gate failure, not a regeneration**.
*Mutation for the automated half* — `division_serializers` (definition): default
`typical_basis` to `"section_wide"` instead of `"insufficient_sample"` when no evidence exists
→ the literals flip and the byte-goldens go red.
*Perimeter*: `golden_budget_status.json` is unchanged, byte for byte.

**C13 — one participating-set implementation, on the wire (T7 repaired).**
(a) `divide_production_budget`'s `allocated_groups` predicate and the services' participating
set resolve to `participating_sections`.
(b) A section whose only step is `FAILED` renders `share_state: "excluded"` with
`allowance_seconds: null` and appears in **no** weight.
(c) **absence, L4, root = repository root, terms stated**: no private copy of the
excluded-state predicate remains. Search terms: `SKIPPED`, `CANCELLED`, `FAILED`,
`EXCLUDED_STEP_STATES`, `_step_state_is_excluded`. Expected: every hit outside
`budget_division.py` and the enum definitions is a **test** fixture, enumerated by name.
*Mutation* — `budget_division` (definition): reintroduce a private excluded set that omits
`FAILED`.
*Both sides* — contract: the FAILED-only section is `"excluded"` with a `null` allowance;
mutation: it becomes an allocated group, gains an allowance, and **every** other section's
allowance moves (`distributable_seconds` is unchanged but `total_weight` grows).
*Note*: §11.1's original T7 mutation ("reintroduce a private predicate in one service") was
inert — a faithful copy is what an implementer writes, and a faithful copy agrees. Naming the
**disagreeing form** is what makes it bite.

## 7. Notes

- **F-F is stale, and stale in the direction that costs a round.** Its conclusion survives
  (`DivisionStep.typical_worker_seconds` is always `None` in production) but its stated reason
  is wrong: production now hands `DivisionStep` dataclasses that **do** carry the attribute,
  explicitly set to `None`. Hence two production files in the removal perimeter.
- **F-C is stale on the word "identical".** The three step loads still agree exactly on their
  WHERE predicates — which is what §6.1 rests on — but `production_time.py:30-41` adds
  `selectinload(TaskStep.latest_state_record)` and an `order_by` the other two lack. §6.1's
  shared function takes `steps` and is unaffected.
- **S-6:** production-time's section typical and budget-allocations' step rows are **not**
  pass-throughs — `division_serializers.py:102-108` and `:36-47` enumerate their keys
  explicitly with `typical.get("sample_count", 0)`-style defaults. New fields must be added
  **by name**, or they will silently not ship.
- **F-E:** excluded sections' typicals are display-only — they appear in zero computations.
  Weights iterate `allocated_groups` only.
- **No pace factor, no scaled values, no raw mixed ratios** (D12): every emitted
  `typical_worker_seconds` is identically an integer produced by the SQL, never a product or
  ratio of two of them. Plan 1 C9 pins this at the domain layer; this phase must not
  reintroduce it in a serializer.
- The unused narrowed **seconds** value is never published on task surfaces (§3.6) — only its
  **count** (`narrowed_sample_count`) is, and only on production-time.
- **Architecture-graph delta expected**: `projection-item-economics-task-production-time`,
  `projection-item-economics-task-budget-allocations` and
  `source-file-item-economics-budget-division`. One batched `apply_changes`; evidence
  summaries carry **no counts**; prefer symbol anchors over line spans, **but not both on one
  entry**.

## 8. Review log

*(empty — append-only; shared by implementer and reviewer)*
