---
plan: 2
role: review
round: 1
verdict: CHANGES_REQUIRED
date: 2026-08-17
actor: Opus 5 (reviewer)
---

# Review round 1 — plan 2 (task-scoped section-keyed production-time view)

**Verdict: CHANGES_REQUIRED.** 1 blocking, 6 should-fix, 8 notes.

The phase is substantially right. E3 is composed, not reimplemented; HC-6 holds
mechanically; **P-AGREE and P-SUM3 hold exactly in all eight M3.5b branches I could
construct**, which is the property this phase existed to establish; the wire is
time-only and role-flat; T7b changed exactly the two rows it was allowed to change and
loosened nothing. Five of the six unverified mutation probes reproduce byte-for-byte.

What did not hold is **M3.4/D12 — the governing-step rule is not implemented at all**
(B1). `_governing_step` picks the most recently *created* step; it has no preference
for the non-closed step. C6's fixture makes the live step also the newest one, so the
criterion's own guard passes for the wrong reason, and the DB half of C6 survives the
named mutation entirely. Four further findings are guards that do not guard
(C1's tie-break, C9's mixed row, `state_entered_at`, M3.9's snapshot source), each
found the same way: delete the construction, watch the suite stay green.

Suite re-derived independently: **2311 passed / 26 failed / 1 deselected**, and the 26
failure IDs diff **byte-identical** to the phase-1 r4 closeout set (zero added, zero
removed). The handoff's numbers are accurate.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — should a section read "over share" when the overrun came from a failed pass?

**Question.** A section whose live work is well inside its slice, but whose *failed*
pass already ate more than the slice: should the card read **over share**, or stay
**on track**?

**Story.** Upholstery is allotted 10 minutes on a chair. A first pass fails after 100
minutes of work; the wood was split, nothing was salvageable. A worker picks the
section up again and has done 10 minutes so far. The card shows "110m worked",
"10m allotted", "−100m left" — and, today, a green **on track** badge beside them.

**Branches.**
- **Over share** — the badge matches the numbers on the same card; the failed pass stays
  visible as time this section cost you.
- **On track** — the badge tracks only work that is still alive, but contradicts the
  "−100m left" printed next to it.

**Recommendation.** Over share — it is what D13's wording already says ("the section's
*total* worked"), and it is the only reading under which the three numbers on one card
cannot disagree.

**On silence.** The gate holds; the contradiction is not shipped either way.

**Trace.** Intention §12.5 M3.3 / M3.5b `share_state`; D13; D15; criterion C9. See S1.

---

## Findings

### B1 — BLOCKING. M3.4/D12's governing-step rule is not implemented

`domain/item_economics/budget_division.py:181-199` (`_governing_step`), called at
`:151` for the section's `state` / `state_entered_at` and at `:239` for M3.5b's
no-open-step branch.

**Authority.** Intention §12.5 **M3.4**: the governing step is *"its single non-closed
step if one exists; otherwise its most recently closed step"*, resolved by **D12**
(owner: *"the recomendation is the correct approach"* — the live step governs, because
"the section genuinely has work to do again and the row's time keeps climbing").

**What the code does instead.** Three stacked stable sorts leave the precedence
`created_at DESC → latest_state_record.entered_at DESC → client_id ASC`. **Liveness is
never consulted.** Two separate deviations:

(a) *The primary rule is absent.* Whenever a section's closed step is not also its
newest-created step, a closed step governs a section that still has open work:

| fixture | M3.4/D12 | code |
|---|---|---|
| pending created 5 min ago, completed created 2 min ago | `pending` | **`completed`** |
| both created in one transaction (identical `created_at`), completed entered its state later | `pending` | **`completed`** |
| `created_at` absent on both | `pending` | **`completed`** |

(b) *The documented tie-break is inverted.* M3.4 specifies "most recent
`latest_state_record.entered_at`, **then** `created_at` DESC, then `client_id` ASC".
The code makes `created_at` outrank `entered_at`. Fixture: A (created 9 min ago, entered
1 min ago) vs B (created 8 min ago, entered 7 min ago) → M3.4 says A governs, the code
returns B's state and B's `state_entered_at`.

**Why the guard did not bite.** `test_budget_division.py:261-271` builds the completed
step at `now−2min` and the pending step at `now−1min`, so *live* and *newest-created*
are the same step — a fixture satisfying two independent sufficient causes, which
charter rule 2's companion forbids. Row 2 of the table above is that same fixture with
only the confound removed, and it flips.

**Reachability.** Zero instances in the current snapshot: all five real
`{completed, pending}` groups have their completed step created first, so `created_at
DESC` happens to agree with D12. It is not a theoretical shape, though — the database
already holds groups of three steps on one section sharing an identical `created_at` to
the microsecond (bulk step creation), and row 2 of the table is exactly that shape with
one step completed. Urgency, not correctness, is what the zero count bounds.

**Correction.** Partition first, sort second: among the group's steps, prefer those with
`state NOT IN TERMINAL_STEP_STATES` (imported, per B7); if any exist, the governing step
is chosen from that subset, otherwise from the closed ones. Within the chosen subset
apply M3.4's stated order — `entered_at` DESC, then `created_at` DESC, then `client_id`
ASC — i.e. reverse the last two `sort` calls at `:191-198`. `:239`'s call passes only
`completed` steps and so needs the precedence fix but not the partition.

**Named mutation for the repaired criterion (rule 11).** In
`budget_division.py::_governing_step`, at the **definition**: delete the liveness
partition. C6's DB row must turn red, on a fixture whose completed step is created
**after** its pending step.

### S1 — mixed-section `share_state` contradicts `left_seconds` (adjudicates F1)

`budget_division.py:357-361` computes `worked_for_share` **excluding** excluded steps;
`:367` computes `left_seconds = allowance − worked` where `worked` (`:343`) is M3.3's
group total **including** them. Step rows inherit the same state at `:383`.

Reproduced through the allocator — a section holding one `skipped` step (100 s worked)
and one `pending` step, slice 0 s:

    worked_seconds=100   allowance_seconds=0   left_seconds=-100   share_state="on_track"

**The ruling: `share_state` moves; `left_seconds` stays.** Reasons, in order of force:

1. **D13 already says so literally** — a step reports `over_share` when *"the section's
   **total** worked exceeds its slice"*, and M3.3 defines the section's total as
   including excluded steps. `worked_for_share` is not that quantity.
2. **M3.5b's exclusion clause governs a different computation.** "The residual must
   never subtract an excluded step's seconds" is about `slice − Σ closed worked`, the
   number split across a section's steps (`_section_step_allowances:223`). That code is
   correct and untouched by this fix. Charging decides *how much is allocated*;
   `share_state` reports *what the section has spent*. Both can be true at once.
3. **`left_seconds` is pinned by the published payload.** §12.7's example gives
   `worked_seconds: 1500`, `allowance_seconds: 3600`, `left_seconds: 2100` — the
   difference of the two fields printed on the same row. Moving `left_seconds` instead
   would make the row's own three numbers unreproducible by the client and weaken HC-10.

**Correction.** `budget_division.py:362` becomes
`section_state = "over_share" if worked > allowance else "on_track"`; delete
`worked_for_share` (`:357-361`), which then has no reader.

**Recommended intention wording**, appended to M3.5b's `share_state` paragraph:

> `share_state` on a section row, and on every step row that inherits it, compares
> **M3.3's `worked_seconds`** — the section's total over all its non-deleted steps,
> including excluded ones — against `allowance_seconds`: `over_share` iff
> `worked_seconds > allowance_seconds`, else `on_track`. This is the same quantity the
> row displays, so `share_state`, `worked_seconds` and `left_seconds`
> (= `allowance_seconds − worked_seconds`) can never contradict each other on one card.
> M3.5b's exclusion rule applies **only** to the residual that splits a slice across a
> section's steps, never to this comparison: charging decides how much is allocated,
> `share_state` reports what the section has spent.

**Reachability.** Fixture-only — zero `skipped`/`cancelled`/`failed` steps exist in the
database (re-confirmed this session).

**Yes, C9 must be strengthened — and it is weaker than "it passed".** C9's mixed row is
`test_production_time_query.py:124`, `assert mixed["share_state"] == "on_track"`. The
mixed section it names is `_seed`'s: a `failed` step of 1200 s beside a `pending` step
of 0 s, under a 6000 s budget → slice 4800. Both readings return `on_track` (0 ≤ 4800
and 1200 ≤ 4800), so the row **cannot fail under either contract** — charter rule 2's
companion again. C9 also claims "skipped seconds in `worked_seconds`" and never asserts
`mixed["worked_seconds"]`. The repaired C9 needs a fixture whose excluded seconds alone
cross the slice, an exact `worked_seconds` assertion on the mixed row, and the named
mutation "comparing only non-excluded worked seconds must turn this red".

### S2 — C1's `name` tie-break is unguarded; the insertion-reversal clause was not built

`test_production_time_query.py:54-76` inserts Alpha then Beta (both `order_list = 2`),
asserts the order, then calls E3 a second time and asserts `result == again`. §12.10
row 1 and criterion C1 both require *"then again with insertion order **reversed**"* —
idempotence is not reversal.

**Probe (applied, red not observed — that is the finding).** Replacing the `name`
component of `_section_sort_key` (`budget_division.py:90`) with `""` leaves the whole
phase-2 suite at **25 passed**. The key stays a total order via the id backstop, so the
sections array is still deterministic — just ordered by id instead of name. `sorted()`
is stable and the fixture's insertion order already equals the expected order, so
nothing can see it.

Today's two real ties (`cleaning seat`/`cleaning wood` at 2, `upholstery installation`/
`weaving` at 7) happen to have ULIDs in name order, so the mutation is invisible on live
data as well. The moment a section is added to an existing tie — a new "cleaning frame"
at `order_list = 2` gets the newest ULID and sorts last, not alphabetically — the
widget's order silently stops matching the contract.

**Correction.** Add the reversal: seed the same two sections with insertion order (and
step insertion order) swapped and assert the identical expected order. Criterion C1
records the named mutation "delete the `name` component of `_section_sort_key`
(definition site) must turn this red".

### S3 — C6's DB row survives its own named mutation, and `state_entered_at` is untested anywhere

Two distinct gaps in one criterion.

(a) **Probe re-applied**: `budget_division.py:151`, `_governing_step(group["steps"])` →
`group["steps"][0]`. `test_budget_division.py::test_c6_later_live_step_governs_section_state`
goes red (`assert 'completed' == 'pending'`), but
`test_production_time_query.py::test_c4_c6_c25_grouped_row_preserves_state_and_snapshot`
— the row the plan classifies as **DB** — stays **green**. The DB half of C6 does not
guard.

(b) C6 also requires *"`state_entered_at` from that step"*. `grep -rn state_entered_at
tests/` returns **no phase-2 test**. The field is on the wire
(`division_serializers.py:95`), the README documents it, and §6.5's client-side live
tick is built on it. Zero coverage, on both the DB and the unit side, and C7's
`result["sections"][0]["state"] == "pending"` is vacuous besides — both its steps are
pending, so it holds under any governing rule.

**Correction.** Apply the lettered-parts rule: C6a state (DB, on a fixture where the
completed step is created last — see B1), C6b `state_entered_at` exact value, C6c the
multi-open tie-break with a non-vacuous expected state.

### S4 — `section_name_snapshot` is not the governing step's, and the E3 step query has no `ORDER BY`

`budget_division.py:155-162` takes the **first non-null** `working_section_name_snapshot`
in `group["steps"]` order. `get_task_production_time.py:28-38` selects steps with **no
`order_by`**, so that order is whatever PostgreSQL returns.

**Authority.** M3.9: each row carries `section_name_snapshot` *"(from the governing
step)"*, and the contract instructs the frontend to **render the snapshot** on the row.

**Demonstrated**, one group, two steps with divergent snapshots, only the input order
changed:

    query returns old first  →  section_name_snapshot='Upholstery'
    query returns new first  →  section_name_snapshot='Upholstery installation'

with the governing step being the newer one in both cases. So the label the widget
prints can differ between two calls on unchanged data — HC-11's "two calls against
unchanged data must return the identical order" is about the array, but the same
guarantee is what the frontend needs from the row it renders.

**Reachability.** Requires a section renamed between two steps of one group; §12.4
measured the two names identical on all 2833 live rows, so fixture-only today. C25's
fixture gives both steps the *same* snapshot, so it cannot see this.

**Correction.** Read the snapshot from the governing step (`governing` is already in
hand at `:151`), falling back to the first non-null only when the governing step's is
null. Independently, give E3's step select a deterministic `order_by` — it costs
nothing and removes the whole class.

### S5 — T7b's "restate, do not loosen" was not carried out on the P-PROP row

`tests/integration/services/queries/item_economics/test_budget_allocations_query.py:171`
still asserts the ratio at the **step** unit:
`steps[section]["allowance_seconds"] == 2 * second["allowance_seconds"]`.

Plan T7b: *"`test_uses_shared_typicals_for_two_section_proportional_split` stays
unchanged in value under (ii) but its invariant is now section-level (P1) — restate it,
do not loosen it."* Intention §12.6 P1 is explicit that the per-step ratio *"is no
longer a true invariant"*. Nothing was changed: not the name, not the assertion, not a
comment. The value is still correct only because each section in that fixture holds
exactly one open step and no closed step — i.e. the assertion is true by accident of the
fixture rather than by contract.

Not a loosening and not a wrong number, so it is contained — but it is a named T7b task
that was not done, and it leaves a step-unit claim standing where the contract now has a
section-unit one.

**Correction.** Rename to `..._section_proportional_split` and assert the ratio over the
**section** rows (or over Σ step allowances per section), with a one-line comment citing
P1.

### S6 — declared perimeter is incomplete (adjudicates F2)

Confirmed and upheld. Checkpoint `98aa31b` contains `.archgraph/architecture.yml`; the
handoff's "Files in the implementation perimeter" list does not. **The content is
clean** — independently verified: the commit's change to that file is **purely
additive** (104 lines added, **0 removed**) and contains **zero** lines matching
`bootstrap|seed`; it is exactly the two phase-2 nodes and their two edges.

The finding stands regardless of content, and rule 11's reason is worth restating
verbatim: a declared perimeter that does not match `git show --stat` cannot be audited.
The two claims every review depends on — "every probe was reverted" and "nothing changed
outside the perimeter" — are reconstructed from that comparison, so a file present in
the commit and absent from the declaration silently removes one file from the audit.
The handoff's own §"Architecture graph" section *describes* the graph delta, which makes
the omission a filing error rather than concealment; that is why this is should-fix, not
blocking.

`master_plan.md` and `plans/plan_2.md` **are** declared and their edits are legitimate
(tracker row = the phase's own row; Review log = the implementer's entry). No finding
there.

**Correction.** One line added to the handoff's file list. Standing rule for the
project: **tool-recorded state is part of the perimeter and is declared by path**, not
only narrated in prose.

---

## Notes

- **N1 (adjudicates F4 — confirmed, record it).** B8's *"5 production tasks"* framing
  was overstated. Re-derived independently: `sanding` (`wsec_01KVX0G12ZSNWRPRBM67CF1HCR`,
  `order_list = 4`, `is_deleted = true`) carries 5 live steps across 5 tasks, and **all
  five of those tasks are themselves `is_deleted = true`**. `get_task_budget_status`
  filters `Task.is_deleted.is_(False)` (`get_task_budget_status.py:52-59`) and raises
  `NotFound` before E3's step query runs, so every one 404s. **Zero reachable production
  instances.** C22's outer-join contract is right to exist and its probe reproduces
  (below); only the urgency was wrong. Do not re-escalate.

- **N2 (F3 — not re-opened).** The tenant-probe equivalence was adjudicated by the
  coordinator and is accepted as recorded. I did not re-run it. For the record, the
  mechanism is visible in the code cited above: the 404 fires in
  `_load_task_and_item` before any step query.

- **N3.** `DivisionStep.created_at: datetime | None` (`budget_division.py:40`) —
  `datetime` is **never imported** in that module. It survives only because
  `from __future__ import annotations` keeps annotations as strings. Any future
  `typing.get_type_hints`, pydantic adoption, or `dataclasses.fields(...)` type
  resolution over this dataclass raises `NameError`. One-line import.

- **N4.** `_section_step_allowances`'s no-open branch calls `_governing_step(completed)`
  (`:239`); `_governing_step` ends in `candidates[0]` (`:199`), an `IndexError` → 500 on
  an empty list. Safe **today** only because `TERMINAL_STEP_STATES ∖ EXCLUDED_STEP_STATES
  == {COMPLETED}`, an invariant that is implicit, unasserted and one enum addition away
  from being false. A cheap assertion or an explicit `terminal-and-not-excluded` filter
  removes the coupling.

- **N5.** `if group not in allocated_groups` (`:344`) is an O(n²) dict-equality scan over
  dicts that hold ORM instances. It works (section ids are distinct) but compares by
  value where identity is meant. `allocated_ids = {g["working_section_id"] for g in
  allocated_groups}` is cheaper and says what it means.

- **N6.** Master plan §8's open owner item — *"the graph pass's file change is applied in
  tool state but is deliberately left uncommitted"* — is **stale**. `.archgraph/` is
  fully tracked (nothing ignored) and clean at HEAD; the working copy equals the
  committed blob. The 26 `bootstrap|seed` references in the file arrived via the owner's
  own commit `08092a2`, not via any pipeline checkpoint. The coordinator should reword or
  close that item rather than relay it again.

- **N7.** `tests/unit/services/queries/item_economics/test_production_time_contract.py`
  **earns its place** — it is C19's only home, it duplicates nothing, and its three-part
  structural assertion (importer set / no arithmetic tokens / single exported allocator)
  is exactly the "verify structurally, not behaviorally" form HC-6 needs. Two small
  things: it carries no `@pytest.mark.unit` where its siblings under
  `tests/unit/routers/api_v1/` do, and its `"//" not in source` clause would also reject
  a URL in a docstring — harmless, worth a comment so a future author does not delete it
  as a false positive.

- **N8.** `test_c15_c21_c22_task_scope_and_soft_deleted_section_outer_join` contains **no
  tenant assertion**; C15's real coverage lives in `test_c14_c16_...:211-212`. The
  criterion ledger maps C15 correctly so nothing is uncovered, but under the
  letter-verification rule a test named for a criterion it does not test is how a future
  reader inherits false assurance. Rename.

---

## Verified correct (settled ground — later rounds need not re-derive this)

1. **P-AGREE holds exactly, in every M3.5b branch (C12).** Σ of a section's step
   allowances == the section's `allowance_seconds` in all eight branches I constructed:
   no-open `{completed, completed}` (the 45-of-50 case), `{completed, pending}`, negative
   residual (closed burned 100 000 s against a 15 s slice), single closed step (the 98.2%
   case), multi-open, mixed `{skipped, completed}`, mixed `{skipped, pending}`, and fully
   excluded. **Zero disagreements.** The property this phase exists to establish is real.
2. **P-SUM3 holds in all eight** — Σ section allowances == `distributable_seconds`
   exactly, including where the residual is negative and where a section is weightless.
3. **HC-6 / C19, mechanically.** Repo-wide grep: `divide_production_budget`,
   `group_steps_by_section`, `_section_step_allowances` and `_largest_remainder` exist in
   exactly one module, `domain/item_economics/budget_division.py`. The per-step split is
   `_section_step_allowances` at `:210-242` — in the domain module, **not** in E2, which
   reads `division["steps"]` and nothing else (`get_task_budget_allocations.py:212,231`).
   No second allocator anywhere.
4. **T7b closed exactly as instructed.** `git diff 8a1f815 98aa31b -- app/tests/` is the
   whole evidence base: the only changes to pre-existing test files are the two
   `live_partition` value rows (`20/20/20/0` and `15/15/15/0/15`), the three additive
   route-mirror rows, and the mirror's count `24 → 25`. **No other phase-1 assertion
   moved, and none was loosened** — no `==` degraded to `!=`/`in`, no assertion deleted,
   no fixture weakened. r2's lesson is satisfied.
5. **B10's third dispatch branch is correct.** `test_item_economics_router.py:137-139`
   adds `if "production-time" in path: assert calls[0][0] is
   item_economics.get_task_production_time; return` — the service-identity form, placed
   before the worker/seller branch. The pre-existing budget-status assertion at `:140-144`
   is **byte-identical** to `8a1f815`. Not loosened.
6. **Four of the five re-applied probes reproduce** (fifth is S3 above). Ledger below.
7. **Route + mirrors + README (T6/C18).** Declared beside `budget-status` with
   `response_model=None` and no return annotation (`item_economics.py:369-370`); all four
   roles; both hand-written mirrors updated by addition; README carries the Quick Index
   row (`:81`) and a complete field table (`:1692-1723`) that matches the shipped payload.
8. **P-COVER's two-sources requirement is honoured and exercised.**
   `get_task_budget_status.py:138-147` sums `total_working_seconds` in SQL with **no
   state filter**, so an excluded step's seconds are in the headline; E3 sums them again
   in Python via M3.3. C11's fixture has a `failed` step carrying 1200 s, so the
   excluded case is genuinely covered by both paths, not just the happy one.
9. **Typicals agree between E2 and E3.** E3's `typical_times_statement(ws).where(
   WorkingSection.client_id.in_(section_ids))` adds a plain predicate to the outer select
   — the same shape E1 already uses for `working_section_ids` — and touches neither the
   grouped subquery nor the `GROUP BY`. A section missing from the result resolves to
   `None` on both surfaces (E2 via an explicit `None` value, E3 via an absent key), so
   the fallback-median path is entered identically. No divergence.
10. **Degradation and the money perimeter.** `budget.*` all null including
    `actual_worker_seconds`, every `share_state: "no_budget"`, typicals and
    `worked_seconds` still populated; recursive key walk over the serialized body finds
    no `_minor`/`cost`/`price`/`currency`/`money`/`valuation` at any depth; four roles
    `sha256`-identical through the single manager code path. `step_ids` is absent from
    the wire (round 10's removal) while still available internally to M3.5b.
11. **Suite, re-derived from scratch.** 2311 passed / 26 failed / 1 deselected. The 26
    failure IDs diff **byte-identical** to the phase-1 fix-r4 closeout set — zero added,
    zero removed. No phase-2 test is among them.
12. **No fixture residue.** Zero rows remain from the phase-2 fixtures
    (`wsec_tie_*`, `wsec_null_*`, `wsec_excluded_*`, `wsec_left_*`, `wsec_second_*`,
    `tsp_extra_*`, `tsp_failed_*`, `tsp_live_*`, `icr_*`, `Allocations *` workspaces) after
    three full-suite runs. Rule 11½ is being honoured. The 12 multi-open step groups now
    visible in the database are **other suites'** leftovers (the documented N11 residue,
    `connecteam-parity` / `Case pause` workspaces), not this pipeline's, and not a
    counter-example to §12.4's "0 groups with 2+ non-closed steps" over real workspaces.

---

## Mutation-probe declaration

Every probe applied and reverted; every file `sha256`-verified byte-identical to its
pre-probe blob afterwards, and `git status -- app/ .archgraph/` is empty at close.

| # | File (definition site) | Mutation | Observed |
|---|---|---|---|
| 1 | `budget_division.py:151` | `_governing_step(group["steps"])` → `group["steps"][0]` | unit C6 **RED** (`'completed' == 'pending'`); **DB C6 GREEN** → S3 |
| 2 | `division_serializers.py:68-77` | `_serialize_production_time_final` → `return serialize_item_cost_result(result)` | **RED** ×2 — C14's recursive money walk and C17 |
| 3 | `get_task_production_time.py:49` | inner-join: drop steps whose section is absent from `section_by_id` | **RED** — C22 |
| 4 | `division_serializers.py:92` | `section_name_snapshot` ← live `section_name` | **RED** ×2 — C25 and C22 |
| 5 | `budget_division.py:337` | remainder tie key → `_section_sort_key` (M3.2 render order) | **RED** — C23, E2/E3 section allowances diverge |
| 6 | `budget_division.py:90` | drop the `name` component of `_section_sort_key` | **GREEN, 25 passed** → S2 |

Non-mutating derivations (no repo file touched): the B1 governing-step tables and the S4
snapshot demonstration were produced by calling `group_steps_by_section` from a scratch
interpreter session; the S1 branch table by calling `divide_production_budget` directly.

**Database side effects: none.** All DB access this session was read-only `psql`
`SELECT`s plus test runs whose fixtures own their teardown; residue re-checked to zero
(verified item 12 above). The configured DB is at head; no migration was written or run.

---

## Fix work list (for the coordinator's r2 prompt)

Perimeter for the fix cycle — nothing outside it may change:

- `app/beyo_manager/domain/item_economics/budget_division.py` — B1, S1, and optionally
  N3/N4/N5
- `app/tests/unit/domain/item_economics/test_budget_division.py` — B1's unit fixture, C6c
- `app/tests/integration/services/queries/item_economics/test_production_time_query.py` —
  C1 reversal (S2), C6a/C6b (S3), C9 (S1), C25 divergent-snapshot row (S4), N8 rename
- `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`
  — S5 only, and only by strengthening
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py` — S4's
  `order_by` only
- the handoff's perimeter list — S6

**Upstream, the coordinator's to fold (not the implementer's):** S1's intention wording
into §12.5 M3.5b; C1/C6/C9 rewritten in `plans/plan_2.md` with their named mutations and
lettered parts; card 1's answer into `owner_decisions.md`.

**Not in the fix cycle:** N1, N2, N6 (records only); N7's marker (cosmetic, may ride
along).

## Lessons for the plans

1. **A criterion whose fixture confounds two causes is not a criterion.** B1, S1 and S2
   are all one shape: the expected value holds for a second, independent reason, so the
   guard cannot fail. Charter rule 2's companion already says this for *fixtures*; the
   plan should state it for *ordering and precedence rules* too — **when a criterion pins
   a precedence, its fixture must make every level of that precedence disagree with the
   others.** C6's completed step must be created *last*; C1's insertion order must
   contradict the expected order; C9's excluded seconds must be the only thing crossing
   the slice.
2. **The lettered-parts rule was applied to the plan but not to the tests.** C6 carried
   two obligations (`state` and `state_entered_at`) in one row; only the first got a
   test, and only on the unit side. C1 carried two (order, then reversed order); only the
   first was built. Both would have been caught by the **letter-verification rule** if
   the plan had lettered them — it did not, and neither did the implementer's ledger,
   which maps whole criteria to single test names.
3. **A "DB" criterion that is only satisfied by a unit test is a mis-kind, not a pass.**
   The plan classes C6 as DB; the mutation reddens only the unit row. The criterion→test
   ledger should record *which* test bites on the named mutation, per charter rule 11's
   "when two tests divide the labour, the criterion records which test bites on which
   mutation".
4. **Query-order dependence is a rule-6 mechanism and needs a contract.** M3.9 says
   "from the governing step" and the code says "first non-null in query order"; there is
   no `ORDER BY` anywhere on E3's step read. Any field derived by picking *one* row out of
   a group belongs in the mechanism-inventory sweep alongside ordering and dedupe keys.
   The projection's mechanism sweep did not ask "which fields are chosen from a set, and
   by what key?" — it should.
5. **The MVP calibration is still earning its keep.** A light-scoped first review found
   one blocking contract violation and five guards that do not guard, at the cost of six
   probes. Every finding but S5 and S6 came from the same move: delete the construction,
   watch the suite stay green. Phase 1's evidence held; keep the probe, keep dropping the
   ceremony.

## Human-authorization backlog

- **Owner card 1** above — ratify the `share_state` reading. Relay verbatim.
- **Architecture graph:** no adjudication needed from me. The two phase-2 nodes and two
  edges in `98aa31b` are additive and clean; I did not promote, reject or edit any review
  item, and the graph delta for the fix cycle should be recorded by the implementer as
  usual. Master plan §8's stale open item (N6) is the coordinator's to reword.

## Perimeter of this session

Write perimeter: **this file only.** The tracker row (`master_plan.md` §3) and
`plans/plan_2.md`'s Review log were deliberately **not** edited — the review prompt
scoped this session to one handoff file. The coordinator folds both:
tracker `REVIEWING → CHANGES_REQUESTED`, 2026-08-17, Opus 5 (reviewer r1), "1 blocking
(M3.4/D12 governing step not implemented), 6 should-fix, 8 notes; P-AGREE and P-SUM3
verified exact in all 8 branches; suite 2311/26/1 with the 26 IDs byte-identical."
