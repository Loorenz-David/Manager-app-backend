---
plan: 3
role: implement
round: 3 (fix)
date: 2026-08-19
state: IMPLEMENTED
actor: Claude (Opus 5) — replacing Codex
---

# Phase 3 fix r3 handoff — the two coordinator findings on the r2 delta

Both findings are applied inside the two-file perimeter. G-1 is comment-only. G-2 adds one
integration row and closes the coverage gap it named — **the gap was reproduced before the row
was written, and the row was mutation-tested after.**

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required. No STOP was entered; no third file was opened.

## G-1 — the clause is corrected, and the finding was verified first

`TaskBudgetStatus` does carry an object: `result: ItemCostResult | None`, at
`get_task_budget_status.py:48` (dataclass spans lines 33–48). The landed r2 text said "no
objects" one line above it. The clause is replaced verbatim; the surrounding two sentences are
untouched:

```python
    # it means returning those objects from get_task_budget_status, whose TaskBudgetStatus
    # carries item_id and the evaluation result but none of the objects re-read here — not
    # the Task, the Item, the selection, the terms or the valuation — and is a contract
    # other screens consume. Reusing this
```

**One cosmetic note, not acted on.** The verbatim splice ends mid-sentence, so the paragraph now
carries a short line (`# other screens consume. Reusing this`) before the unchanged closing line.
The wrapping is ragged where the rest of the block is flush to ~88 columns. Reflowing would have
meant editing text the prompt gave verbatim, which this project has repeatedly ruled the worse
error, so it was left exactly as issued. Flagging it so the coordinator can decide.

## G-2 — the gap was real, and it is now closed

**The gap was reproduced before anything was written.** With the r2 tree shipped and
`ItemValuation.is_deleted.is_(False)` deleted from `_current_valuation`, the focused file was
**49 passed in 0.53s** — fully green. The comment F-1 landed called that predicate load-bearing
and nothing could see it move.

The user-reachability claim was also checked rather than inherited:
`delete_item_valuation.py:41` sets `valuation.is_deleted = True` and leaves `superseded_at`
null, reachable from `routers/api_v1/item_economics.py:route_delete_item_valuation`
(`DELETE /items/{item_client_id}/valuation`, ADMIN/MANAGER). The soft-deleted-with-null-
`superseded_at` fixture is therefore the ordinary post-delete state, and it is legal under
`uix_item_valuations_current`, whose partial predicate covers live rows only.

**New row:** `test_phase3_g2_soft_deleted_valuation_is_hidden_from_the_price_screen`.
One workspace, one user, one item, and one committed `ItemValuation` with `is_deleted=True`,
`deleted_at` and `deleted_by_id` set as the command sets them. It exercises the real
`_current_valuation` against `db_session` — only `get_task_budget_status`,
`_load_task_and_item`, `_load_preview_inputs` and `_typical_block` are monkeypatched, exactly
as C1 does. Teardown is rule 11½: `try/finally` naming `item_valuations`, `items`, `users`,
`workspaces`; the four residue assertions sit outside it.

### E2 — how the four fields are asserted, and one deviation reported

`serialize_task_price_scenario` (`serializers.py:295-316`) emits `saved` **wholesale**: when the
query hides the row, `saved_payload` is `None`, so there is no dict to hold `valuation_id`,
`expected_sale_price_minor` or `created_by`. `assert result["saved"] is None` is therefore the
strictest available form of all three; writing `saved.get("valuation_id") is None` after it
would be a statement that cannot fail, which is the defect this phase exists to remove.

So the row asserts three things, not four, and **adds a fourth leak channel the criterion did not
name**: top-level `currency`, which the service also reads off the valuation
(`currency: valuation.currency if valuation is not None else None`). Every one of the three
discriminates independently under the mutant — measured, not assumed:

| Assertion | Contract side | Mutation side |
|---|---|---|
| `result["saved"] is None` | `None` | dict — `valuation_id='ival_price_del_<token>'`, `expected_sale_price_minor=910000`, `created_by={'client_id': 'usr_price_del_<token>', 'username': …}` |
| `result["currency"] is None` | `None` | `'swedish_krona'` |
| `result["can_commit"] is False` | `False` | **`True`** |

The `can_commit` flip is the one the finding cared about: task `ASSIGNED`, selection `OK`,
currencies agreeing and no purchase term leave valuation-presence as the only false conjunct, so
the deleted row readmits commit. Each mutation-side value was read off a separate probe run with
the assertions reordered, then both files restored byte-identical.

## Mutation ledger (E3)

Applied at the definition site, measured across the **whole non-E2E suite**, reverted by file
restore, SHA-256 checked.

| Definition site and mutation | Contract side | Mutation side | Complete observed-red delta | Revert SHA-256 |
|---|---|---|---|---|
| `get_task_price_scenario.py:_current_valuation`, drop `ItemValuation.is_deleted.is_(False)` | `saved` null, `currency` null, `can_commit` `False` | `saved.valuation_id='ival_price_del_<token>'`, price `910000`, byline present, `currency='swedish_krona'`, `can_commit` `True` | `…test_price_scenario_query.py::test_phase3_g2_soft_deleted_valuation_is_hidden_from_the_price_screen` **only** | `b248b3c77fa9fc37077b41e300848c5dc9820710b234f6d3cca0fd822dbbfbb5` |

```text
Shipped r3 tree:  26 failed, 2431 passed, 1 deselected  (122.26s)
is_deleted mutant: 27 failed, 2430 passed, 1 deselected  (124.11s)

diff r3_baseline_ids.txt r3_mutant_ids.txt
16a17
> …::test_phase3_g2_soft_deleted_valuation_is_hidden_from_the_price_screen
```

One ID added, none removed. Test-file SHA-256, unchanged across all three probes and the
mutation run: `c9d59c196e2edc1c107ca8ba065f9d28ca1bc1d9ca17623a4a120fb39dc74568`.

## E4 — no fixture was shared

The new row is **self-contained**: its own token, its own workspace/user/item, its own
`_scenario_objects()` instance, its own teardown. It shares nothing with `test_phase3_c1_…`
beyond the module-level helpers C1 itself already used. **C1's named mutation was therefore not
re-measured this round**, per E4's "if and only if". C1 is untouched and green in both whole-suite
runs above.

## Verification

```text
Focused phase file:  50 passed in 0.72s          (49 → 50, one row added)
Whole non-E2E suite: 26 failed, 2431 passed, 1 deselected   ← E6 exact
Failure IDs:         byte-identical to the r2 set — diffed, not counted

ruff check <the two Phase 3 files>          All checks passed!
ruff format --check <the two Phase 3 files> 2 files already formatted
git diff --check                            clean
```

**E1 verified against `ef55f6d`, not against r2** — the complete non-comment diff of
`get_task_price_scenario.py` across r2 **and** r3 combined is **empty**:

```text
git diff -U0 ef55f6d -- …/get_task_price_scenario.py | grep '^[+-]' | grep -v '^[+-] *#'
(no output)
```

Twenty comment lines changed across two rounds; zero executable lines. (r2 landed as `af6589f`;
the two files hash to `b248b3c7…` and `c9d59c19…` at close.)

## §6 — the drifting test

**It did not appear.** Ninth and tenth observations, both green in full-suite runs:
`test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
was absent from both of this round's whole-suite runs, and the 26 failure IDs were byte-identical
to r2's in both. Running tally: **implementer r1b 27, 27; coordinator 26; reviewer 26; fix r2 26,
26; coordinator 26, 26; fix r3 26, 26.**

The suite was again run as `PYTHONPATH=. pytest -m 'not e2e'` from `app/`; the bare form fails
collection with `ModuleNotFoundError: beyo_manager` under this shell. Collection is otherwise
identical.

## Architecture Graph delta

**No graph mutation: 0 nodes, 0 relationships, 0 source links.** No `archgraph_*` tool was
invoked — N-6 (anchor drift on the pending `ai_inferred` items) is the coordinator's, and was
deliberately not touched.

One consequence to route, not a request: the new row inserts ~146 lines at what was line 887 of
the test file, **after** the C1 table/test span the r1b handoff recorded as stored `387–419` /
actual `416–448`, so that span is unmoved. Any stored anchor pointing at `test_c14_…` or
`test_c16_…` further down the file has shifted by that amount.

## STOPs and scope

None. G-2 did not require reaching into `price_scenario.py` or `test_price_scenario.py` —
N-2 stays with plan 5, and phases 1, 2 and 4 were not opened. Nothing was committed; neither the
master plan tracker nor plan 3's Review log was updated.

## Full write perimeter

From the closing `git status --porcelain --untracked-files=all`.

Session-owned writes:

1. `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py`
2. `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py`
3. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/implementer/2026-08-19_phase3_fix_r3_handoff.md`

**Not this session's — the owner's concurrent, unrelated change**, present in the same status
output and neither touched, staged, reverted nor counted:

- `.archgraph/architecture.yml`
- `app/beyo_manager/services/queries/items/lookup/purchase_api.py`
- `app/tests/unit/services/queries/items/test_lookup_item_by_article_number.py`
