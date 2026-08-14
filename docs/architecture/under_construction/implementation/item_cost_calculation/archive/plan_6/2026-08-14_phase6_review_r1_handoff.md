---
plan: phase 6
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-14
actor: Claude Opus 5 (plan-reviewer)
---

# Phase 6 reviewer handoff — legacy money migration & API bridge, round 1

## Opening summary

**CHANGES_REQUESTED — 2 blocking, 4 should-fix, 11 notes, 1 owner card.**

The behaviour this phase ships is, in the parts I could execute, correct: the
bridge rejects exactly present-and-non-NULL on all four surfaces with the exact
D1 message and envelope, the pre-flight refusals abort before any write, the
downgrade restores every journaled row byte-identically, the nine read surfaces
are factually the right nine and all of them are clean, and the cold build from
empty reaches `be9dfe42a035` with the enum ownership flip working. What does not
hold is the migration's own safety net and one contradictory clause in the
intention:

- **B1** — the in-`upgrade` post-condition that is supposed to catch a partial
  copy is a tautology. I ran the migration with the copy loop skipping its only
  eligible row: it exited 0 with zero valuations created. The very next migration
  then drops the columns.
- **B2** — the eligibility predicate filters on `is_deleted = false` alone, so an
  item whose only valuation was deliberately deleted **is re-valued** (the exact
  outcome §10A.1(c)'s heading forbids, and exactly what §10A.1(c)'s own verbatim
  predicate produces — the clause contradicts itself), while an item whose only
  valuation is superseded is **skipped** even though it has no current valuation.
  Neither row is in C1's fixture set.

Both are unreachable on the live database today (D17: zero legacy money rows), so
nothing is broken in production right now. They matter because this is the phase
that destroys the data — the guard exists for the one run nobody gets to repeat.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — When an item's price was deleted on purpose, should the migration bring it back?

**Question.** Should the legacy-money migration re-create a price for an item
whose only saved price was deleted by a person — yes, or leave it deleted?

**Story.** A colleague opens a chest of drawers in the app, sees the imported
price of 4 900 kr is wrong, and deletes it. The old imported number still sits in
the item's own record, invisible, from before prices moved to their own place.
Migration night runs. Next morning the chest shows 4 900 kr again, marked as the
current price, attributed to whoever first created the item. Nobody was told, and
the only trace that a human ever removed it is a deleted row nobody looks at.

**Branches.**
- **Leave deleted prices deleted** — the chest stays without a price; your
  colleague's decision survives the migration. Anyone who wants the old number
  can still type it in.
- **Re-create the price (what the code does today)** — every deliberately deleted
  price comes back on migration night, across every item it happened to.

**Recommendation.** Leave deleted prices deleted — it is what the written
decision says in words, and a price that reappears by itself is the kind of thing
people stop trusting the system over.

**On silence.** The gate holds; the phase stays CHANGES_REQUESTED and nothing is
guessed.

**Trace.** Intention §10A.1(c) (heading vs verbatim predicate); plan C1; finding
B2.

## Verdict and findings

Full technical detail, per-probe hashes and the verified corrections are in the
plan file's Review log (`plans/phase_6_legacy_migration_api_bridge.md`,
"2026-08-14 — reviewer r1"). Summary by severity:

### Blocking

- **B1 — §10A.1 post-condition 2 is a tautology; a partial copy passes and the
  drop then destroys the money.** `_assert_postconditions` (`5420acc6a7b3:161-182`)
  compares two counts that range over the same rows by construction. R14(a)/D3
  restated pc2 over the *eligible items*; the shipped form dropped that side.
  EXECUTED on `beyo_manager_rev_p6_pc2`: one eligible seeded item, copy mutated to
  `rows[1:]` → `alembic upgrade 5420acc6a7b3` **exit 0**, journal 1 row,
  `item_valuations` **0 rows**. Verified correction executed (see Review log):
  shipped tests stay green (2 passed), the mutant aborts with
  `item money migration left 1 eligible item(s) unmigrated` and rolls back.
- **B2 — the eligibility predicate is neither "no current valuation" nor "no
  valuation"; §10A.1(c)'s two untested rows both come out wrong.** EXECUTED on
  `beyo_manager_rev_p6_elig` with the **unmutated** shipped migration:
  soft-deleted-only → **new valuation created**; superseded-only → **skipped**.
  Needs owner card 1, then one sole-predicate C1 row per valuation state.

### Should-fix

- **S1 — C5's nine-row census is one assertion wearing nine labels.**
  `endpoint_id` is never consumed; re-exposing all three money keys inline at
  `upholstery_orders_query.py:496` leaves all 9 serializer rows and all 27 phase-6
  unit nodes green. D18 records these as the only arbiters this surface will ever
  have. Fixture is a `SimpleNamespace`, not an ORM `Item` (charter rule 3).
- **S2 — the three refusal rows never assert the row report.** Stripping every
  offending `client_id` from the `RuntimeError` leaves both migration tests green;
  and one message always carries `P1`, `P2` and `P3`, so `assert "P2" in stderr`
  is satisfied by a P1-only refusal.
- **S3 — C4's 12 rows are schema-level; 1 of 4 surfaces is proven end-to-end.**
  Reviewer probe confirms `PUT /items`, `PATCH /items/{id}` and
  `POST /items/find-or-create` all return 422 with the exact envelope — **evidence
  gap, not a defect**. Three more harness rows close it.
- **S4 — the enumerated case tables are for-loops inside two monolithic tests.**
  Zero `parametrize` in the migration test file; D23's authority-naming ids absent;
  the first failing assertion masks every later row.

### Notes (11)

N1 ledger hashes/red sets (P6-B, below) · N2 D9's "2 → 1" enum arithmetic is wrong
at head · N3 `metadata.create_all` broken repo-wide, pre-existing, vindicates D9 ·
N4 the idempotency row has two sufficient causes and never re-runs the
post-conditions · N5 "manual valuation survives" asserted by count, not identity ·
N6 no intermediate assertion after the drop-only downgrade · N7 the D14 tie row is
unlabelled and buried in another test · N8 `be9dfe42a035`'s docstring names the
wrong parent revision; `print()` instead of a logger · N9 deploy ordering unstated
(old ORM selects dropped columns) · N10 the journal node carries no edges ·
N11 P6-C arithmetic reconciled.

## Coordinator probes — outcomes

- **P6-A — RESOLVED, legitimate.** The `item_upholstery_requirement.py` change is
  exactly the R2-1 flip: one line, `create_type=False` → `True`, and it is now the
  only model declaring `item_currency_enum`. The drop migration's downgrade re-adds
  `items.item_currency` with `create_type=False` (D10). Cold build empty → head on
  `beyo_manager_rev_p6_cold`: **exit 0**, version `be9dfe42a035`, 0 legacy columns,
  enum present, journal present at 0 rows. The five write-path command files beyond
  the prompt's fence remove **only** the three-key writes — verified line by line
  (`_create_item_in_session` signature + call, `create_item`, `find_or_create_item`
  incl. `_DIRECT_FIELDS`, `update_item` `_DIRECT_FIELDS`, `create_task`).
  Caveat on the cold-build clause as written: the enum has **two** column users at
  head, not one — see N2.
- **P6-B — RESOLVED, partially unverifiable.** 3 of 5 ledger records reproduce; 2
  do not. Details and all hashes in the probe declaration below.
- **P6-C — RESOLVED.** 18 bridge + 9 serializer + 2 migration = 29 collected nodes;
  the phase-5 tie row is an assertion inside an existing test, so it adds 0 to
  collection — that reconciles "29 focused + 1 tie-breaker" with "+29 collected".
  1991 + 29 = 2020 selected ✓. `items` 479 → 480 → **481** after my own suite run:
  the known suite-wide residue class (master plan §10), not phase-6 tests.

## Mutation-probe declaration

Every probe was applied, observed and reverted; the working tree was verified
clean (`git status --short` empty) before and after, and every reverted file
re-hashed byte-identical to its baseline.

| # | File | Baseline sha256 | Mutant sha256 | Observed red set |
|---|---|---|---|---|
| R1 | `migrations/versions/5420acc6a7b3_…py` (`for row in rows[1:]`) | `bdf89d8e5f7317cbda35e9eee25a8c100d63910eb91dac7c388b2af1b6ed6290` | `e6ff898b741ab2de32014459e170c65c71c6b85aa90586048471b3a2fe250e62` | **none** — `alembic upgrade` exit 0, 0 valuations (B1) |
| R2 | `migrations/versions/5420acc6a7b3_…py` (report drops all `client_id`s) | `bdf89d8e…` | `0911d0d8985526088172f751f0e4b21eb4cc768847eba6407fc45c0551377177` | **none** — 2 passed (S2) |
| R3 | `beyo_manager/services/queries/upholstery/upholstery_orders_query.py` (re-expose 3 keys inline) | `b34e8e0ef0446f62c84781621f66cecabea6ccc0eb73e5dbe5f3ef3e81d5f746` | `99a34732bd6795a3d8f71fca227fa368221340ae1477d48c49e05889677a3b5e` | **none** — 27 phase-6 nodes green (S1) |
| R4 | `services/commands/tasks/requests/__init__.py` (delete validator — ledger probe 1) | `20cc505469fb282288537f48f0c649189347946ca9bafba803ef9d9b24048e3c` | `f09c368224e1b5a0735eeea8966be15b766eda7479c77fe4106799cae2942a28` | `test_bridge_is_reject_iff_present_and_nonnull[create-task-nested-item-present-nonnull]`, `test_create_task_router_preserves_nonnull_money_into_domain_validator` — **2**, ledger declared 1 |
| R5 | `services/commands/items/requests/__init__.py` (delete 3 validators — ledger probe 2) | `bf132dd05d7e346a230b03c9d912a85f16a7e47167d39de10c2d6d018ab114ce` | `c8515e219b0f25229e4f80d83492589df286b1d00db780e7eb023babe3d9759c` | 3 `-present-nonnull` rows + 3 `create-item-<key>` rows — **6**, matches |
| R6 | `services/commands/items/requests/__init__.py` (neuter the shared helper — D5's items-file half, reviewer-added) | `bf132dd0…` | `1d9eec248bdf2044c2c1f8a9a92c466a135364bb65c35fce41eed6d8d70b2fbf` | all 4 `-present-nonnull` rows + 3 per-key rows + the create_task router row — **8** |
| R7 | `beyo_manager/domain/items/serializers.py` (re-add 3 keys — ledger probe 3) | `b7fa431a17cd6d69906873771a4c64748b3ff298dffaced962713996d4142104` | `808aef9533a525f4642665423fe50ba42baa6ca706c321ddac388ebf9f4abfad` | `items-list`, `items-detail`, `customer-detail-linked-items` — **3**, hashes and set reproduce byte-identically |
| R8 | `beyo_manager/routers/api_v1/tasks.py` (drop `item_cost_minor` — ledger probe 5) | `aafc1f53946b8076fd9a00297343a2c09aa16aa6660021b2da696410313fbd1a` | `2d541c16b09a77d9360e221be52df41e52ae2ffc60b547f0df3cf125b7297bef` | `test_router_bodies_retain_money_keys_until_command_validator` — **1**, hashes and set reproduce byte-identically |
| R9 | `migrations/versions/5420acc6a7b3_…py` (B1's **verified correction**) | `bdf89d8e…` | `8f5bf7ceb7adac5b0169af57ef3492d5d793a6a814e26717cadb79f1770d43d0` | shipped tests **2 passed** (correction is not over-tight) |
| R10 | `migrations/versions/5420acc6a7b3_…py` (correction + skip mutation) | `bdf89d8e…` | `6086956bb341b6ffbe17e0fc34cff587cfbfb0ce20a0a7c103f17c46cd8a7ec7` | `alembic upgrade` **exit 1**, `left 1 eligible item(s) unmigrated`, version rolled back to `5caae620088c` |

**Ledger reconciliation (P6-B).** The Review log's declared baselines for probes 3,
4 and 5 match the checkpointed files exactly, and probes 3 and 5 reproduce their
mutant hashes and red sets byte-identically. Probe 1's declared baseline
(`9dccde99…`) and probe 2's (`0f3b5a79…`) do **not** match the checkpointed files
(`20cc5054…`, `bf132dd0…`), so those two records cannot be verified against the
shipped code; re-run here, probe 2's red set reproduces but probe 1's is
**incomplete** — the router-survival node reddens too.

**Database and state side effects.** Four disposable databases created and
dropped: `beyo_manager_rev_p6_pc2`, `beyo_manager_rev_p6_cold`,
`beyo_manager_rev_p6_metacreate`, `beyo_manager_rev_p6_elig`, plus
`beyo_manager_rev_p6_fix`; a catalog query for `beyo_manager_%` other than
`beyo_manager` returns **zero rows**. The configured development database was
read only and remains at `be9dfe42a035 (head)`. `items` went 480 → 481 through my
own full-suite run (the known residue class); no economics rows were written.

## Verified correct (the settled ground for the re-review)

Bridge: `ValidationError` is a `DomainError(Exception)`, not a `ValueError`, so
pydantic structurally cannot wrap it — D1 is met by construction; all four
surfaces return 422 with the exact message and `{"error", "ok": false}`; absent
and present-null both pass into the command; all four router bodies retain the
three keys (D6). Migration: P1/P2/P3 all abort before any write and persist
nothing (refusals precede `_create_journal`); the collision row is journaled with
`valuation_client_id` NULL and its valuation untouched; downgrade restores all
three columns byte-identically on all four journaled rows including the
soft-deleted one and drops the journal; the mapping is byte-equal on all three
pairs; `generate_id("ival")` Python-side per D8; no audit events per D12.
Removal: five write paths clean, `Item.__table__` clean, both serializers clean,
zero production references remain, `routers/README.md` has zero residual mentions.
Environment: suite **1997/23/1** with the 23 matching the phase-1 baseline
one-for-one; ruff clean on the phase-6 perimeter.

## Architecture graph (read-only; zero adjudications)

7 pending = 1 new (`table-item-valuation-migration-journal`) + the 6 prior
phase-5 read-surface items, exactly as expected. The journal node's two evidence
spans (`45-75`, `200-243`) are exact and every claim it makes holds in both
migration directions. `set_item_valuation.py` was **not** touched this phase (last
modified at `8b4ac06`) and all five prior edge spans still land exactly. The
`node:table-item` description edit is correctly LEFT to the coordinator per D19 —
and its evidence *summary* has drifted with it (":51" → **:46**, "legacy money
columns" now false), which belongs in the same §8 maintenance edit.

Anchor-spans service, all 7:

| Item | Span | Status |
|---|---|---|
| `node:table-item-valuation-migration-journal` | `5420acc6a7b3:45-75`, `:200-243` | exact |
| `node:table-item` | `item.py:1-60` | span valid; **summary** stale (:51 → :46, money columns gone) |
| edge → `table-production-cost-group` | `set_item_valuation.py:39-44` | exact |
| edge → `table-production-cost-basis-version` | `:47-52` | exact |
| edge → `table-cost-model-version` | `:55-60` | exact |
| edge → `table-cost-model-term` | `:72-78` | exact |
| edge → `table-item` | `:106-110` | exact |

## Lessons for the plans

1. A post-condition whose two sides are built from the same construction is a
   tautology. A criterion mandating an in-migration post-condition owes a row
   naming the mutation that must abort it — this extends P-J's non-vacuity rule
   from tests to production guards, where it matters more because there is no
   second run.
2. A parametrize id is a label, not a probe. When the parameter is never consumed
   by the test body, N rows are one row (P-V ext). An enumerated census criterion
   should require that each row's *expression* differ, not just its id.
3. An intention clause whose prose and its own "verbatim" predicate disagree
   cannot be discharged by instructing the implementer to follow it verbatim. The
   projection's decidability pass should reject a clause where the stated intent
   and the given predicate select different rows.
4. A refusal criterion that names a row report owes an assertion on the report's
   *contents*. Asserting the identity token is worthless when one message carries
   every identity.
5. D9's enum arithmetic ("2 → 1") was computed without the journal's own snapshot
   column. A criterion counting users of a shared type must be written against the
   end state the phase actually produces.

## Carry-forward dispositions

Not applicable at this verdict — no notes are being carried past an approval. On
approval, N3 (`metadata.create_all` broken repo-wide) → only-if-cheap ledger; N9
(deploy ordering) → phase 9 docs; N2 (the D9 arithmetic) → plan text correction at
the fix cycle; the `node:table-item` description **and** summary edits → the
coordinator's post-approval graph pass.
