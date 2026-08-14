---
plan: phase 6
role: review
round: 2 (re-review)
verdict: APPROVED
date: 2026-08-14
actor: Claude Opus 5 (plan-reviewer)
---

# Phase 6 re-review handoff — round 2

## Opening summary

**APPROVED — 0 blocking, 0 should-fix, 4 notes, 0 owner cards.**

Both r1 blockers were real and both are now provably fixed: every mutation that
was **green** in r1 **bites** now, and the two behaviours that were wrong on a
seeded database are right when re-derived independently. The four should-fixes
are closed with shipped arbiters, not with assurances. What remains is four
notes, none of which changes behaviour — the largest is that one r1 note was only
half fixed while the fix record says it was fixed in full; I have corrected the
record in this round's Review log entry and routed the one-line code correction
to phase 9.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Owner card 1 from r1 was answered and folded as R15-1; the code matches
the corrected clause verbatim.

## Verified perimeter

- `51d8b7c` touches **8 files**; every one is declared in the fix handoff's write
  perimeter. Nothing outside it.
- `git diff 51d8b7c..HEAD -- app/` is **empty** — no production drift after the
  checkpoint. Post-checkpoint doc commits are the handoff, the tracker line and
  the coordinator's own r2 prompt.
- Working tree clean (`git status --short` empty) before and after every probe;
  every probed file re-hashed byte-identical to its baseline.
- Declared final production hashes reproduce exactly:
  `a3228a851997a90c6fdc7239da42370864b8149c5e27fbf79988ef93e7562160` (data
  migration), `65f93a2153c1ca81abccd256da4addef08b77398e7af3eb62ce426756b103995`
  (drop migration).
- The fix prompt's perimeter LINE named one production file while its item list
  named N8 on the drop migration. The implementer edited both, matching the items.
  Recorded by the coordinator; **not a finding**.

## Environment

- Suite re-run **foreground** on a hash-verified-clean tree (phase-5 r2 lesson —
  no background run overlapping probes): **2012 passed / 23 failed / 1 deselected**
  in 101.66s. The 23 are the phase-1 baseline set, one-for-one identical to my r1
  run.
- Collection **+15** over r1, exact: the three phase-6 files collect 43 nodes
  (r1: 29) and N7's extracted tie test adds the fifteenth.
- Ruff: clean on the fix perimeter (6 files). The 131 repo-wide errors predate the
  phase and lie outside it.
- Configured DB: `be9dfe42a035 (head)`, `item_valuation_migration_journal` 0 rows,
  legacy `items` columns 0. `items` = 483 (479 at projection → 481 after my r1 run
  → 483 now): the known suite-wide residue class, master plan §10.
- Zero `beyo_manager_%` databases other than `beyo_manager` (catalog query).

## Delta probe results

### R2-P1 (B1) — CLOSED

`_assert_postconditions` now counts eligible-but-unmigrated items from the
items/valuations side and compares against zero — an independent construction
from the journal side, which is what R14(a) asked for.

EXECUTED on disposable `beyo_manager_rev_p6_r2pc2`, one eligible seeded item
(5000/2500/euro, non-deleted, attributed), the identical `rows[1:]` skip mutation:

| | r1 | r2 |
|---|---|---|
| `alembic upgrade 5420acc6a7b3` | **exit 0** | **exit 1** |
| message | — | `RuntimeError: item money migration left 1 eligible item(s) unmigrated` |
| journal table | present, 1 row | absent (rolled back) |
| `item_valuations` | 0 | 0 |
| `alembic_version` | `5420acc6a7b3` | `5caae620088c` |

Baseline `a3228a85…` → mutant
`6c8ce6e7ab4c5db9f3f1c5b52ee4926f2776b4900a7ac339055ed9efb7c0f2f0`. (My mutant
hash differs from the implementer's declared `0190fb19…` because mine carries a
marker comment; same mutation, same observed abort.) **Not over-tight:** all 13
migration rows pass at baseline.

### R2-P2 (B2, the four valuation states) — CLOSED

`_NO_CURRENT_VALUATION` → `_NO_VALUATION` = `NOT EXISTS (any item_valuations row)`,
matching intention §10A.1(c) as corrected by R15-1 **verbatim** (verified folded at
`intention.md:1575-1588`).

EXECUTED on disposable `beyo_manager_rev_p6_r2elig` with the **unmutated** shipped
migration (exit 0), four sole-predicate seeds, all outcomes by state query:

| seeded state | journaled | `valuation_client_id` | new valuations | r1 |
|---|---|---|---|---|
| never-valued `itm_C` (300/euro) | yes | `ival_01M005W80S5VDS6Q7AR4EBFA3J` | **1** | — (non-vacuity arbiter) |
| current-valued `itm_D` (400/euro) | yes | NULL | 0; `ival_D_current` still reads **777** | same |
| soft-deleted-only `itm_A` (100/euro) | yes | NULL | **0** | **1 — was re-valued** |
| superseded-only `itm_B` (200/euro) | yes | NULL | **0** | same (recorded unreachable) |

The collision row is checked **by identity** (the pre-existing valuation's amount),
per r1's N5 standard. The shipped
`test_phase6_eligibility_is_solely_no_valuation_at_entry` carries the same four rows
under `10A1-row1…row4` ids.

### R2-P3 (S1) — CLOSED

The nine rows now each carry `(endpoint_id, source_path, source_line)`, read the real
call expression at those coordinates, assert it names a serializer and contains no
money key, then assert the serializer's output key set — on an ORM `Item` fixture
(charter rule 3).

EXECUTED: the identical inline re-exposure at `upholstery_orders_query.py:496`
(baseline `b34e8e0e…`, mutant `99a34732bd6795a3d8f71fca227fa368221340ae1477d48c49e05889677a3b5e`
— byte-identical to my r1 mutant) reddens **exactly**
`test_nine_serializer_surfaces_omit_legacy_money[upholstery-orders-…-496-serialize_item]`;
**1 failed, 8 passed**. In r1 the same bytes left all 27 phase-6 nodes green.

### R2-P4 (S2) — CLOSED

EXECUTED: emptying all three refusal id lists (mutant
`ebb503d84ebe9c85617b171035de1f59e3629332a28690fcf5cbdd98a63606f6`) reddens **all
three** refusal rows. Each row now asserts its own seeded `client_id` in the report
**and** `client_ids=[]` for the other two classes, so the shared message can no
longer satisfy a foreign row — the exact r1 weakness.

### R2-P5 (S3/S4) — CLOSED

`test_item_router_surfaces_reject_present_nonnull_money` runs `PUT /items`,
`PATCH /items/{id}` and `POST /items/find-or-create` through TestClient, each
asserting 422 and `{"error": "ITEM_MONEY_MOVED: item money fields moved to the
item-valuation endpoint", "ok": false}` — the three surfaces r1 could only verify by
reviewer probe now have shipped arbiters. Collection confirms 12 independent,
authority-named migration nodes where r1 had two for-loops; no masking.

### R2-P6 — adversarial depth on the changed seam (unbidden)

Deleting the journal back-link `UPDATE` from `_copy_eligible_valuations` (mutant
`69b9398060ec58f4669bfc40b7b7cf2218f163e700c84e12386fa37f252a0ab3`) creates a
valuation the journal never records. The new guard alone cannot see it —
`NOT EXISTS(any valuation)` is false once the row exists — but the orphan then
survives downgrade, and the round-trip test's N5 identity set bites: **1 failed, 12
passed**. The property is guarded; the labour is divided between the migration guard
and the round-trip row.

### R2-P7 — the surviving conjunct

Removing `AND j.valuation_client_id IS NULL` from the copy SELECT (mutant
`ca90691fcc382f3b9fc2607b54dd6b7459a2a8b6fc3fb47fc16d7ff27bc54931`) leaves **all 13
rows green** — `_NO_VALUATION` alone excludes an already-migrated item. See note N3.

## r1 notes — status

| r1 note | status |
|---|---|
| N5 identity not count | **CLOSED** — `{ival_existing, ival_manual}` set assertion |
| N6 intermediate downgrade state | **CLOSED** — 3 columns present, 0 rows non-NULL |
| N7 tie test labelled + own node | **CLOSED** — `test_synthetic_history_tie_breaker_uses_client_id_desc`, docstring names it synthetic and why |
| N1 ledger accuracy | **CLOSED** — all three fix rows declared against FINAL hashes; the migration baseline reproduces exactly |
| N2 enum arithmetic | plan text corrected; structural row added but see r2 N2 |
| N4 idempotency | post-conditions re-run on pass 2 ✓; single-cause half open, see r2 N3 |
| N8 docstring + logger | logger ✓; docstring **not** fixed, see r2 N1 |

## Notes (4)

**N1 — r1's N8 is half closed and the fix record says otherwise.** The drop
migration still reads `Revises: 5caae620088c` (`:4`) while
`down_revision = "5420acc6a7b3"` (`:15`). Both the fix-r1 Review log entry and the
fix handoff state "the drop migration docstring names the actual parent revision".
It does not. The code correction is one line; the record correction is in this
round's Review log entry. Routed to phase 9's drift batch. *(This is the round's
only finding of substance, and it is about the record, not the behaviour — which is
why it does not hold the gate.)*

**N2 — SQL precedence in the head enum-user assertion**
(`test_phase6_legacy_migration.py:451-466`). `AND` binds tighter than `OR`, so the
journal branch is constrained by neither `t.typname` nor `NOT a.attisdropped`.
EXECUTED read-only against the dev DB: as written → 2; with a **bogus** typname → 1
(should be 0); parenthesised → 2. The asserted property is still true and still
reddens if the journal disappears; the correction is one pair of parentheses.

**N3 — a conjunct that no case depends on.** Per R2-P7, `AND j.valuation_client_id
IS NULL` is redundant now that `_NO_VALUATION` is the eligibility predicate. So the
run-twice row still satisfies two independent sufficient causes (r1 N4's
single-cause half). No defect — `_NO_VALUATION` is load-bearing and the
post-conditions now genuinely re-run on pass 2, which was N4's substantive half.

**N4 — fixture path and pinned windows.** `test_phase6_serializers.py:47` resolves
`Path(source_path)` against the CWD while its sibling uses
`_APP_ROOT = Path(__file__).parents[2]`; running pytest from the repo root errors all
nine rows rather than failing meaningfully. The five-line source windows are
line-number pinned and will drift as those query files change (loudly, via the
`serialize_item` assertion — but they will drift).

## Mutation-probe declaration

Every probe applied, observed and reverted; tree verified clean before and after;
every reverted file re-hashed byte-identical to its baseline.

| # | File | Baseline sha256 | Mutant sha256 | Observed |
|---|---|---|---|---|
| R2-P1 | `migrations/versions/5420acc6a7b3_…py` (`rows[1:]`) | `a3228a851997a90c6fdc7239da42370864b8149c5e27fbf79988ef93e7562160` | `6c8ce6e7ab4c5db9f3f1c5b52ee4926f2776b4900a7ac339055ed9efb7c0f2f0` | upgrade exit **1**, rolled back to `5caae620088c` |
| R2-P4 | same file (empty refusal id lists) | `a3228a85…` | `ebb503d84ebe9c85617b171035de1f59e3629332a28690fcf5cbdd98a63606f6` | all **3** refusal rows red |
| R2-P6 | same file (drop the journal back-link UPDATE) | `a3228a85…` | `69b9398060ec58f4669bfc40b7b7cf2218f163e700c84e12386fa37f252a0ab3` | round-trip row red (1 failed / 12 passed) |
| R2-P7 | same file (drop `j.valuation_client_id IS NULL`) | `a3228a85…` | `ca90691fcc382f3b9fc2607b54dd6b7459a2a8b6fc3fb47fc16d7ff27bc54931` | **13 green** — redundant conjunct (N3) |
| R2-P3 | `beyo_manager/services/queries/upholstery/upholstery_orders_query.py` | `b34e8e0ef0446f62c84781621f66cecabea6ccc0eb73e5dbe5f3ef3e81d5f746` | `99a34732bd6795a3d8f71fca227fa368221340ae1477d48c49e05889677a3b5e` | exactly `[upholstery-orders]` red, 8 green |

**Database and state side effects.** Two disposable databases created and dropped:
`beyo_manager_rev_p6_r2pc2`, `beyo_manager_rev_p6_r2elig`. The shipped migration
tests create and drop their own `beyo_manager_phase6_*` databases. A final catalog
query for `beyo_manager_%` other than `beyo_manager` returns **zero rows**. The
configured development database was read-only apart from the ordinary suite residue
(`items` 481 → 483) and remains at `be9dfe42a035 (head)` with the journal at 0 rows.

## Architecture graph (read-only; zero delta; zero adjudications)

Revision `4eb1d8d0d2ba50466e1c54e9f0b76f5d268e7773e3cab802b0499b33438ccc9e` —
**byte-identical to r1**. 155 nodes / 200 edges, **7 pending** (the journal node +
the 6 phase-5 read-surface items). Nothing promoted, edited, rejected or
deprecated.

**Corrected anchor spans.** The data migration grew by 23 lines, so the journal
node's two evidence spans have MOVED:

| Item | r1 span | **r2 corrected span** |
|---|---|---|
| `node:table-item-valuation-migration-journal` — `_create_journal/_journal_legacy_rows` | `45-75` | **`44-74`** (`_create_journal` 44-57, `_journal_legacy_rows` 60-74) |
| `node:table-item-valuation-migration-journal` — `upgrade/downgrade` | `200-243` | **`203-246`** (`upgrade` 203-220, `downgrade` 223-246) |

Both spans' *claims* still hold verbatim in both directions after the fix — the
journal still covers every legacy-bearing row with an `ON CONFLICT` guard, and
downgrade still restores, deletes only journal-linked valuations, and drops the
table. All other spans anchor in files this fix did not touch and were re-verified
exact in r1: `node:table-item` `item.py:1-60` (span valid, **summary** still stale —
`:51` → `:46`, "legacy money columns" now false), and the five
`set_item_valuation.py` edges at `39-44` / `47-52` / `55-60` / `72-78` / `106-110`.

## Lessons for the plans

1. **A fix cycle's own record is evidence and gets verified like any other claim.**
   This round's only finding is a record asserting a closure that did not happen —
   extending r1's P-I lesson from ledger hashes to ledger prose. A fix criterion
   naming N sub-items owes a per-sub-item observation, not a summary sentence.
2. **An `OR`ed structural assertion needs its precedence arbitrated.** The cheap
   arbiter is to re-run the query with one conjunct falsified and confirm the count
   drops; a query that keeps counting is mis-parenthesised.
3. **When a fix replaces a predicate, its old supporting clauses may become dead
   weight.** A fix criterion can ask, per surviving conjunct, whether any case still
   depends on it — the same non-vacuity question rule 2 asks of fixtures.

## Carry-forward dispositions

| Item | Destination |
|---|---|
| r2 N1 — drop-migration docstring parent + the record correction | phase 9 drift batch |
| r2 N2 — enum-user assertion precedence | next touch of `test_phase6_legacy_migration.py` |
| r2 N3 — redundant conjunct; run-twice row dual-cause | next touch of the migration; no action required |
| r2 N4 — CWD-relative fixture path + line-pinned windows | next touch of `test_phase6_serializers.py` |
| r1 N3 — `Base.metadata.create_all` broken repo-wide (pre-existing) | only-if-cheap ledger |
| r1 N9 — deploy ordering (old ORM selects dropped columns) | phase 9 docs |
| r1 N10 — journal node carries no edges | coordinator's post-approval graph pass |
| `node:table-item` description **and** evidence summary | coordinator's post-approval graph pass (D19) |
| Journal-node spans `44-74` / `203-246` | coordinator's post-approval graph pass |
