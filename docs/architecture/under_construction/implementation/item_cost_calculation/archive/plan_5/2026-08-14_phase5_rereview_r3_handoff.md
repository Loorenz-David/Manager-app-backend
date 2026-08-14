---
plan: phase 5 (valuation surface)
role: review
round: 3 (re-review, delta-scoped — S1 only)
verdict: APPROVED
date: 2026-08-14
actor: reviewer (Claude Opus 5)
---

# Phase 5 re-review r3 handoff — APPROVED

## Summary

The one item left is closed. The L15 guard now quantifies over its whole module
set, and all three shapes of the defect it exists to prevent — including the two
that stayed green at 363 in r2 — redden it exactly, with zero collateral. I also
checked the thing a quantified assertion most easily gets wrong, that it cannot
pass on an empty set: it can't, the test fails loudly first.

**Verdict: APPROVED** — 0 blocking, 0 should-fix, **1 new note** (one file under
an `item_economics` package sits outside the guard's walk; near-impossible place
for the defect, one-token correction verified, routed to next touch).

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Phase 5 is done.

## Step 1 — perimeter

- `git show e71b5b4 --stat` = the **3 declared files**; one code file,
  `test_configuration.py` (+11 lines).
- `git status --porcelain` clean; `git diff e71b5b4..HEAD -- app/` **empty**.
- Final hash `da1c4e28144e1466887b542f9ae078679c8f400dfbae1bd97776fd97df319a87`
  matches the declaration and the tree.
- Ruff clean on the changed file.
- **Zero production change this cycle** — `set_item_valuation.py`
  (`05587c2b…`), `delete_item_valuation.py` (`ab9aebbe…`) and
  `configuration.py` (`75087586…`) are byte-identical to r2's approved state.

**Suite (foreground, hash-verified-clean tree): 1968 passed / 23 failed /
1 deselected** in 70.51 s; collection `1991/1992 (1 deselected)`. Failure set
**byte-identical** to the phase-1 baseline (zero-line diff). Focused selector
**363 passed**; `test_configuration.py` **9 passed**. DB at head
`5caae620088c`.

## Step 2 — the delta, re-derived

### The shipped assertion quantifies correctly

```python
unmediated = {}
for path, source in module_sources:
    extra = (source.count("item_major_category_snapshot")
             - source.count("resolve_major_category(item.item_major_category_snapshot)"))
    if extra:
        unmediated[path.name] = extra
assert unmediated == {}, unmediated
```

It loops over **all** of `module_sources`, not a member — the r2 finding's exact
correction. I verified the walk resolves to **24 modules** covering both L15
roots: `domain/item_economics/*.py` (the package has no sub-packages, so `glob`
≡ `rglob` there) and every file whose immediate parent is an `item_economics`
package under `services/` — i.e. both `services/commands/item_economics/` and
`services/queries/item_economics/`. Exactly one in-scope reader exists today
(`set_item_valuation.py`, 1 occurrence, 1 mediated), so the assertion is
satisfiable as written rather than trivially true.

The r2 removal of `assert "ItemMajorCategoryEnum(" not in set_source` is correct
— that check never generalised (M4a's `ItemMajorCategoryEnum.WOOD` form contains
no `ItemMajorCategoryEnum(`), and the quantified quantifier subsumes it.

### The three probes — all redden, zero collateral

| Probe | Mutation | Mutant sha256 | Restored sha256 | r2 | r3 red set |
|---|---|---|---|---|---|
| **M4a** | inline classification chain in `_load_preview_inputs`, bypassing the resolver | `df1f79b3a23081cf21cc785f6660999fdc3648d786fd074167bcb074cbfb7c88` | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | red | `…is_read_only_by_the_registered_resolver` (1 failed / 362 passed) |
| **M4b** | resolver call KEPT + a second unmediated read in the same module | `1309a947c5fcc87adf21468a32192c90886d1182a052021c4947a4b4d7e1feed` | `05587c2b…5bda8` | **363 green** | `…is_read_only_by_the_registered_resolver` (1 failed / 362 passed) |
| **M4c** | snapshot-classifying helper added to `delete_item_valuation.py` | `e02b028ec37294faa77c7301009d95918afb8f69f4eca413c98f729c47b7e4b3` | `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1` | **363 green** | `…is_read_only_by_the_registered_resolver` (1 failed / 362 passed) |

Each reddens **exactly** the guard — no C5 row, no chain row, no collateral —
which is the right blast radius for a structural assertion: it fires on the
source shape, not on behaviour.

**Byte provenance, stated honestly.** M4a reproduces r2's mutant hash exactly
(`df1f79b3…`, same construction both rounds). M4b and M4c are the *same
mutations* as r2's but not the same bytes (`1309a947…` vs r2's `e1ca0625…`;
`e02b028e…` vs r2's `88c9f5aa…`) — I omitted the explanatory comment line I had
included in r2. Semantically identical, different bytes; recorded rather than
glossed. Per the prompt, Codex's own equivalent mutants (`e818fa2b…`,
`c4abb17d…`, `ead1b99e…`) were not chased; my bytes stand on their own.

### Vacuity — the failure mode a quantified assertion invites

A `for`-loop over an empty collection followed by `assert unmediated == {}`
passes silently. **Executed:** breaking the root resolution so the walk yields
nothing (mutant
`fd389abfc6a0e14f6837404762796b8438e4090dee585adea80e0ae4d31301fd`) does **not**
produce a false green — the test dies first on
`FileNotFoundError` at `set_path.read_text()`. The unconditional `set_path` read
plus the `any(path == set_path and …)` membership assertion are the non-vacuity
arbiters, and they are load-bearing. This was not owed by the prompt; it is the
doctrine's "would this loop pass vacuously?" check.

### The N3 comment is accurate

```python
# [basis-model] proves valuation != basis; [valuation-basis] proves basis != model.
```

Verified against my own r2 executions: dropping `valuation ≠ basis` reddened
`[basis-model]`, and dropping `basis ≠ model` reddened `[valuation-basis]`. The
comment states the inversion correctly and closes the misreading trap.

## Findings

**0 blocking. 0 should-fix.**

### N1 (note) — one file under an `item_economics` package sits outside the walk

The `services` filter is `path.parent.name != "item_economics"`, so a file whose
*immediate* parent is not that package is skipped even when it lives under one.
Exactly one such file exists:
`app/beyo_manager/services/commands/item_economics/requests/__init__.py`.

**Executed (M4d, reviewer-added).** A snapshot-classifying helper added there
(mutant `a5261ce8cb00bbaa5bf6129c910f36290a3ce99403236c9ee2ae8460106da53f`,
restored `5da4c3646170e9b72f99027e59eaa61e6cdfbe361f6e45731ee14917a11da132`)
leaves **363 green**.

**Why this is a note and not a finding.** That module holds pydantic request
models, which parse incoming JSON and never hold an `Item` ORM row — the defect
has no plausible route there, unlike the two shapes r2 filed. The guard now
catches every realistic case.

**Verified correction (executed), one predicate:**
`path.parent.name != "item_economics"` → `"item_economics" not in path.parts`.
With it applied, M4d reddens the guard and the clean tree stays at 9 passed.
→ next touch of the file.

## Verified correct this round

- Perimeter exact; zero production change; final hash matches.
- The quantifier covers both L15 roots and all 24 in-scope modules; today's
  single reader is mediated.
- All three r2 probe shapes redden exactly the guard; M4b and M4c were green at
  363 in r2.
- The guard cannot pass vacuously.
- The N3 comment matches the executed clause→id mapping.
- Suite 1968/23/1 with the failure set byte-identical to the phase-1 baseline;
  collection 1991+1; focused 363; DB at head.
- Economics tables unchanged across the round (`item_valuations=2`,
  `item_cost_evaluations=0`, config tables 1 each — r1's N4 pre-checkpoint
  residue, still flat).

## Step 3 — architecture graph (read-only)

**Zero delta.** `archgraph_status`: revision
`b5e6fe094caee2191414a297bb1ab63507ebda8ee4ee54c26cc612a5d940fc94`,
**153 nodes / 195 edges**, **12 pending**, 0 diagnostics, 1 stale node —
identical to r1 and r2. No decision made; the 12 pending items are not mine to
adjudicate.

**Anchor spans: r2's table stands unchanged.** This cycle touched a test file
only, so no production span moved. Final table for the coordinator's
post-approval pass:

| Item | Final span |
|---|---|
| node `command-…-set-item-valuation` | `set_item_valuation.py` **102–168** |
| node `command-…-delete-item-valuation` | `delete_item_valuation.py` **17–44** |
| node `endpoint-…-put-valuation` | `item_economics.py` **229–241** |
| node `endpoint-…-get-valuations` | `item_economics.py` **244–256** |
| node `endpoint-…-delete-valuation` | `item_economics.py` **258–269** |
| edge set `--writes_to-->` table | `set_item_valuation.py` **128–159** |
| edge delete `--writes_to-->` table | `delete_item_valuation.py` **39–42** |
| edge get-valuations `--reads_from-->` table | `get_item_valuation_history.py` **23–31** |
| edge get-valuations `--returns-->` table | `get_item_valuation_history.py` **32–33** |
| edge put-valuation `--returns-->` table | `item_economics.py` **229–241** |
| edge put-valuation `--accepts-->` command | `item_economics.py` **229–241** |
| edge delete-valuation `--accepts-->` command | `item_economics.py` **258–269** |

Stale link (r1 N7, still undeclared by any handoff): `domain-item-economics` →
`configuration.py:44-82`, symbol `resolve_economics_configuration`. Recommended
re-link: symbol `resolve_economics_selection`, span **80–126** (re-verified
unmoved).

## Mutation-probe declaration

Applied in the main worktree, run against the focused selector (363 tests,
~10 s), reverted with `git checkout --`. Restored hashes copy-pasted from the run
output; tree clean and `git diff e71b5b4..HEAD -- app/` empty, so zero probe
residue.

| Probe | File | Mutant sha256 | Restored sha256 | Red set |
|---|---|---|---|---|
| M4a | `set_item_valuation.py` | `df1f79b3a23081cf21cc785f6660999fdc3648d786fd074167bcb074cbfb7c88` | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `test_item_major_category_snapshot_is_read_only_by_the_registered_resolver` |
| M4b | `set_item_valuation.py` | `1309a947c5fcc87adf21468a32192c90886d1182a052021c4947a4b4d7e1feed` | `05587c2b…5bda8` | same, only |
| M4c | `delete_item_valuation.py` | `e02b028ec37294faa77c7301009d95918afb8f69f4eca413c98f729c47b7e4b3` | `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1` | same, only |
| M4d (note N1) | `requests/__init__.py` | `a5261ce8cb00bbaa5bf6129c910f36290a3ce99403236c9ee2ae8460106da53f` | `5da4c3646170e9b72f99027e59eaa61e6cdfbe361f6e45731ee14917a11da132` | **none — 363 passed** |
| Vacuity | `test_configuration.py` | `fd389abfc6a0e14f6837404762796b8438e4090dee585adea80e0ae4d31301fd` | `da1c4e28144e1466887b542f9ae078679c8f400dfbae1bd97776fd97df319a87` | same guard (`FileNotFoundError`, not a silent pass) |
| N1 correction check | `test_configuration.py` + `requests/__init__.py` | — | `da1c4e28…` / `5da4c364…` | reddens M4d; clean tree 9 passed |

## Full write perimeter

- **Documents written:** this handoff; the Review log entry in
  `plans/phase_5_valuation_surface.md`; the phase-5 tracker row in
  `master_plan.md`. Nothing else.
- **Code / tests:** **zero net changes.** Every probe reverted; tree clean; all
  four touched files restored to their committed hashes.
- **Database:** configured dev DB, left at head `5caae620088c`. Economics tables
  unchanged by this session.
- **Scratchpad (outside the repo):** suite log only.
- **Architecture graph:** **READ-ONLY, zero delta.** One `archgraph_status` call.

## Carry-forward dispositions

Phase 5 approves with these open notes, each routed to a named destination.

| Item | Origin | Destination |
|---|---|---|
| N1 — `requests/__init__.py` outside the guard's walk (one-predicate fix verified) | r3 | next touch of `test_configuration.py` |
| C5 row numbers are a hybrid of two numbering schemes; L4's example is pre-round-12 | r2 N1 | next touch + plan correction |
| `client_id DESC` tie-breaker has no arbiter (no fixture ties `created_at`) | r2 N2 | **phase 6** — bulk valuation creation is where it becomes load-bearing |
| M4 label reuse — a mutation name needs a mutant hash beside each red set | r2 N4 | coordinator — ledger convention |
| Race path (ii) has no rowcount observable (gate-guaranteed) | r2 N5 | not owed; recorded |
| Phase-2 citation is prose, not a pytest node id | r2 N6 | next touch |
| DELETE's hardcoded `item_unvalued` vs §11A.4's order | r1 N2 | **phase 8** status query |
| Dev-DB residue `ws_765225a0…` (pre-checkpoint, flat across all runs) | r1 N4 | closeout purge |
| Valuation payload field list | r1 N5 | phase 9 docs |
| Five missing `reads_from` edges; stale `domain-item-economics` anchor | r1 N6/N7 | coordinator post-approval graph pass |

## Lessons for the plans

1. **A quantified structural assertion needs a non-vacuity arbiter, and the
   criterion should name it.** `assert unmediated == {}` over an empty walk is a
   silent pass; here the unconditional `set_path.read_text()` and the membership
   assertion supply the arbiter by accident of construction rather than by
   design. Candidate P-J extension: a criterion mandating a property over a
   discovered set also mandates a row proving the set is non-empty.
2. **Scope predicates should match the scope's wording.** L15 says
   "`services/**/item_economics/`"; the implementation reads "immediate parent is
   `item_economics`". The two agree for every file but one. When a plan writes a
   glob, the test should use the glob's semantics (`in path.parts`), not a
   convenient approximation.

## Exit gate

Phase 5 is **APPROVED**. Across four rounds: B1 (a real, reproduced data-access
defect), B2, B3, B4 and S1–S5 all resolved and independently re-verified;
every governing round-0 amendment (L1–L16) now has a live arbiter; zero findings
outstanding.
