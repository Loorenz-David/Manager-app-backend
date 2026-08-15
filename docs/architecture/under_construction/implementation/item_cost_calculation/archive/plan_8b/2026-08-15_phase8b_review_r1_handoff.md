---
plan: phase 8B (inline item prices at task creation — round 18)
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-15
actor: Claude (plan-reviewer)
---

# Phase 8B review r1 — handoff

**Verdict: CHANGES_REQUESTED.** 0 blocking · 2 should-fix · 3 notes.

The production mechanism is **correct on every branch I re-derived**, including
two shapes no shipped test reaches. Both should-fix findings are test-integrity
defects, not behaviour defects: one load-bearing predicate conjunct has no
regression guard, and two tests leak committed rows into the configured
database whenever they go red. Both corrections are small and local to the test
file. The implementer's ledger discipline is the best in the project so far —
four of five mutant hashes reproduced byte-identically from their written
descriptions alone.

⚠ OWNER DECISIONS REQUIRED (0)

Nothing here needs the owner. One item needs a **human graph adjudication**
(N2) — that is the standing post-approval pass, not a new decision.

---

## Findings ledger

| id | severity | what | authority | status |
|---|---|---|---|---|
| S1 | should-fix | `superseded_at IS NULL` conjunct of the refusal predicate has no covering row; B4's second branch-B sub-row never shipped | plan B4 (GOVERNING); intention §7B.6(b); charter rule 2 companion, rule 11 | CONFIRMED by mutation + reachability probe |
| S2 | should-fix | C4 rows 2/3 leak committed rows on their own failure path (cleanup dereferences expired ORM instances) | charter rule 11½ | CONFIRMED, reproduced deterministically |
| N1 | note | handoff's "the teardown removed them" state claim is not reproducible | 4B review L5 | CONFIRMED |
| N2 | note | pending `command-task-create` evidence anchors partly inaccurate | archgraph evidence accuracy | CONFIRMED, human-adjudicated |
| N3 | note | M1's "observed red" is the named node only; M1's bytes not reproducible | §9 expected-red / ledger discipline | CONFIRMED |

### S1 — the `superseded_at IS NULL` conjunct is unguarded (should-fix)

`create_task.py:326-336` carries the full INV-V1 predicate, and it is
**correct**. What is missing is any test that holds it in place.

Reviewer mutation **M6** — delete `ItemValuation.superseded_at.is_(None)` from
`create_task.py:331`:

```
66 passed
```

The entire focused scope stays green. By contrast **M7** (delete
`ItemValuation.is_deleted.is_(False)`) reddens C4 row 3, and **M8** (delete the
`workspace_id` conjunct) also leaves 66 green but is redundant by construction
(`item_id` already determines the workspace) — M8 is not a finding.

B4 required **two** branch-B sub-rows: "*deleted/superseded-only → NEXT
version — two sub-rows, the second asserting the chain grew rather than
resurrected*". Only the deleted-only sub-row shipped (C4 row 3), and its
fixture — a single `is_deleted = True` row with `superseded_at` NULL — cannot
exercise the superseded conjunct. The implementer handoff is candid about this:
"covered for never-valued and deleted-only histories".

**The state is reachable**, through three shipped production commands:
`set_item_valuation` (v1) → `set_item_valuation` (v2, supersedes v1) →
`delete_item_valuation` (v2). Result: v1 `superseded_at` set / not deleted, v2
deleted / not superseded, **no current valuation**. §7B.6(b) requires
ACCEPT-and-grow. A reviewer probe built exactly that state through those
commands:

- shipped code → **PASS**: accepts, chain grows to 3 rows, v3 is current;
- under M6 → **FAIL**: `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` raised.

This is precisely the R15-1-adjacent hazard the review prompt named ("a missing
conjunct silently turns branch B into branch A for deleted-only items"). Today
the conjunct is right; nothing stops a future edit from dropping it.

**Correction.** Add C4 row 4 (superseded-only): seed the chain through
`set_item_valuation` ×2 + `delete_item_valuation` — production commands, not
hand-built rows (charter rule 3) — assert the pre-state has no current
valuation, then assert `create_task` accepts and the chain GREW to three rows
with the new row current. Name M6 (`create_task.py:331`, definition site) as its
expected-red mutation in the plan and the ledger.

### S2 — C4 rows 2 and 3 leak committed rows on their failure path (should-fix)

Both rows commit (`await db_session.commit()`) and then rely on:

```python
finally:
    await _cleanup_committed_workspace(db_session, workspace.client_id, user.client_id)
```

When the body raises, the owning `maybe_begin` has already rolled the
transaction back, which **expires every ORM instance**. Evaluating
`workspace.client_id` in the `finally` therefore triggers a lazy reload, which
raises inside `_load_expired` — *before the helper is even entered*, so not one
DELETE is issued. Captured under M2:

```
During handling of the above exception, another exception occurred:
...test_phase8b_inline_task_prices.py:534: in test_c4_row_2_...
    await _cleanup_committed_workspace(db_session, workspace.client_id, user.client_id)
.../sqlalchemy/orm/attributes.py:566: in __get__
    return self.impl.get(state, dict_)
.../sqlalchemy/orm/loading.py:1670: in load_scalar_attributes
```

The SQL log for that run ends at `ROLLBACK` with no DELETEs. Residue grew
2 → 7 → 8 `phase8b` workspaces (plus users, items, categories, valuations)
across this review's probe runs; I removed all eight by hand and re-verified
zero.

**C4 row 1 is immune** and shows the fix: it captures `workspace_id`,
`user_id`, `item_id`, `item_article_number` into locals *before* the `try`.
Rows 2 and 3 do not.

This is charter rule 11½ exactly — cleanup that does not run on the path that
matters. The cost compounds: every future red run of these rows pollutes the
shared development database, and the real assertion failure gets buried under a
SQLAlchemy attribute-loading traceback.

**Correction.** Give rows 2 and 3 row 1's shape — capture `workspace.client_id`
/ `user.client_id` (and any other instance attribute the assertions need) into
locals before the `try`. `_cleanup_committed_workspace` itself is correct and
needs no change.

### N1 — an unverified state claim in the implementer handoff (note)

The handoff states the inverted-predicate mutant's four `phase8b` workspaces
"were removed by the owning test teardown helper after the probe". The teardown
cannot have removed them — it raises before deleting (S2). The rows were
evidently removed some other way. 4B review L5 stands: an environment/state
claim needs a state assertion behind it, not an inference from what the harness
was supposed to do. (No blame attaches to the outcome — the database *was*
clean when I started; only the stated mechanism is wrong.)

### N2 — pending `command-task-create` anchors are partly inaccurate (note, human-adjudicated)

Nobody had verified these spans; the prompt asked me to. Read-only check
against the shipped file:

| item | recorded span | reality | verdict |
|---|---|---|---|
| node `command-task-create` | `create_task.py:69-580` | `:69` is the module-level `logger = logging.getLogger(...)`; `async def create_task` is `:72`. End `:580` correct. | starts 3 lines early |
| `writes_to table-task` | `:105-139` | `task = Task(` is `:113`; `ctx.session.add(task)` / `flush()` are `:182-183` — **outside** the span, though the summary asserts "adds it to the session, and flushes it" | excludes what it claims |
| `reads_from table-item` | `:228-248` | first ~8 lines belong to the *other* (`create_item_in_session`) branch; the `find_or_create_item` + `session.get(Item, …)` it describes are `:236-248` | loose but covering |
| `writes_to table-item-valuation` | `:317-353` | exact — the whole inline-price block through the audit call | ✅ |
| `writes_to table-task-item` | `:307-315` | exact — TaskItem construction, add, flush | ✅ |

The two edges recording 8B's **new** behaviour are exact; the imprecision is in
the two that record pre-existing behaviour at the node's birth.

**Corrected spans for the post-approval human pass:** node `:72-580`;
`writes_to table-task` `:113-183`. I made **no graph mutation** — all five
items remain pending, revision unchanged.

### N3 — mutation-ledger scope and byte-reproducibility (note)

Mutant M1 ("delete the valuation write at its definition site") is recorded as
"1 failure". Re-run over the focused scope, the same deletion reddens **9**
nodes (all six C1 rows, B8, C4 rows 2 and 3) — the declared count reflects
running only the named node. That satisfies the expected-red rule but
under-reports blast radius.

Byte-reproduction from the written descriptions alone: **4 of 5 exact.**

| mutant | declared | reviewer-recomputed | |
|---|---|---|---|
| M1 delete valuation write | `e19300d2…` | `0a5041f0…` (10-line cut) / `bfc70ce7…` (9-line cut) | ✗ boundary not pinned |
| M2 invert refusal predicate | `f0776418…` | `f0776418…` | ✅ |
| M3 validator order swap | `f4670bde…` | `f4670bde…` | ✅ |
| M4 delete `reject_legacy_money` | `dbfe1548…` | `dbfe1548…` | ✅ |
| M5 delete `_TaskItemInputBody` trio | `aafc1f53…` | `aafc1f53…` | ✅ |

**Lesson:** a named mutation should pin its deletion boundary by line range,
and "observed red" should state the scope it was observed over.

---

## Row-coverage map (P8B-2)

21 phase nodes + 24 added bridge retention nodes. Observed ids ↔ B1–B10:

| criterion | rows shipped | observed | verdict |
|---|---|---|---|
| B3 / C1 (six enumerated rows) | `C1-row-1-full-trio-purchase-term-commits` · `row-2-expected-price-commits` · `row-3-purchase-term-missing-purchase-cost` · `row-4-purchase-only-missing-expected-price` · `row-5-full-trio-currency-mismatch` · `row-6-unconfigured-workspace` | 6 | ✅ every row asserts the valuation EXISTS with exact figures/currency/`created_by_id`/`superseded_at IS NULL`; skip rows assert the verbatim `item_economics.auto_commit_skipped | task_id=… item_id=… status=<value>` literal; no disjunctions; rows 2 vs 3 differ ONLY in `purchase_term` |
| C2 regression | `test_c2_absent_inline_prices_preserves_item_unvalued_flow` | 1 | ✅ zero valuations, no evaluation, `status=item_unvalued` |
| B8 non-vacuity companion | `test_b8_inline_no_mirror_has_explicit_commit_mirror_companion` | 1 | ✅ explicit commit DOES mirror (chain 1→2, override 1500 current) — so C1's no-mirror assertion is not vacuous |
| B5 / C3 (three rows + order pin) | `C3-row-1-legacy-plus-valid-trio` · `row-2-legacy-plus-amount-without-currency` · `row-3-legacy-plus-negative-amount` | 3 | ✅ rows 1–2 `ITEM_MONEY_MOVED`; row 3 asserts the documented `ge=0`-beats-bridge precedence verbatim |
| B2 / C5 (five rows) | `C5-row-1-expected-without-currency` · `row-2-purchase-without-currency` · `row-4-negative-expected` · `row-5-negative-purchase` · `test_c5_row_3_currency_alone_…` | 5 | ✅ C5.3 is the sole-predicate form (ZERO rows in `item_valuations`, not "no current") and is non-vacuous |
| B4 / C4 (owning harness) | row 1 refusal · row 2 never-valued accept · row 3 deleted-only accept | 3 | ⚠ **S1** — the superseded-only sub-row B4 required is absent; ⚠ **S2** — rows 2/3 teardown |
| B6 / C6 (two harnesses) | `test_c6_router_body_declares_inline_trio_fields` · `test_c6_create_task_endpoint_preserves_trio_into_domain_validator` | 2 | ✅ field-presence introspection + full `model_dump` equality, and endpoint survival through `exclude_unset=True` |

C4 row 1 additionally asserts the `designer` trick: a different `designer` sent
alongside the prices, with the stored value asserted to be the ORIGINAL after
the refusal — plus NO task, NO TaskItem, and the valuation chain unchanged.
Since `get_db` yields an **untransacted** session, `maybe_begin` OWNS in
production, so this row tests production's own rollback, not the test's.

## Mutation ledger (P8B-1) — re-run

All five declared mutations re-applied, run, and reverted; three reviewer-original
mutations added. Every restored hash equals the shipped final hash.

| # | mutation | mutant sha256 | reproduces declared? | expected red | observed |
|---|---|---|---|---|---|
| M1 | delete valuation write + its audit (`create_task.py:344-353`) | `0a5041f0a9e2cc47401d39a4e51b3e5acf22d9cbbb3e05a859a5d4237b6d6095` | ✗ (declared `e19300d2…`) | C1 row 1 | **9 red** incl. C1 row 1 ✅ |
| M2 | invert refusal predicate (`:337` → `if not …`) | `f0776418c7cdc77faf76907bc47545ce70d244106e35d6e88ba9f09940cb2f95` | ✅ byte-identical | C4 rows 1,2,3 | **3 red**, exactly those ✅ |
| M3 | move `require_currency_for_amounts` above `reject_legacy_money` | `f4670bdeaab4a0aad48e238c4b6e479c4e1def9078ffc300d4c5e4d1712c9d24` | ✅ byte-identical | C3 row 2 | **1 red**, exactly that ✅ |
| M4 | delete `reject_legacy_money` from `FindOrCreateItemInput` | `dbfe1548b9ea68212532b470131bcbd0f61cd9fb05b0a5c8c6913f02695b5142` | ✅ byte-identical | 3 `create-task-nested-item-*-present-nonnull` retention nodes | **6 red** incl. all three ✅ |
| M5 | delete the three `_TaskItemInputBody` fields | `aafc1f53946b8076fd9a00297343a2c09aa16aa6660021b2da696410313fbd1a` | ✅ byte-identical | C6 survival row | **2 red** incl. it ✅ |
| M6 † | drop `superseded_at.is_(None)` from the refusal predicate | — | reviewer-original | *(none)* | **66 passed — S1** |
| M7 † | drop `is_deleted.is_(False)` from the refusal predicate | — | reviewer-original | — | **1 red** (C4 row 3) — conjunct covered ✅ |
| M8 † | drop `workspace_id` from the refusal predicate | — | reviewer-original | — | 66 passed — redundant by construction, not a finding |
| M9 † | add `or currency is not None` to `inline_price_requested` | — | reviewer-original | — | **1 red** (C5 row 3) — sole-predicate row is non-vacuous ✅ |

**Reversion proven.** After every probe the working tree is byte-identical to
checkpoint `513856d`:

```
app/beyo_manager/services/commands/tasks/create_task.py       e9c2ccc1bfda4c133149195e530977860eaefba31508b30e492a42bd6e41d547
app/beyo_manager/services/commands/tasks/requests/__init__.py 2bc2b7bb018357d2e437096aac8e81263adddffae1e7a1c9c09fbe564b1e9da4
app/beyo_manager/routers/api_v1/tasks.py                      6a3654dd7aa602bc5f7435960f9bdce06e82d521c585e418a54962ef67061560
app/beyo_manager/routers/README.md                            291aae658bf026c9ad1f68e031c07e367c13b5fa36bd90e95b51efab6150fdec
app/tests/unit/test_phase6_api_bridge.py                      68a34b62f37339434acfecbf1fd13ecd1130d8700669d810fd3799572b7e4a38
app/tests/…/test_phase8b_inline_task_prices.py                f23d7724b8e8f92fd0cbd24c65064be62e524caabfef805661fcd4b41cfe9855
.archgraph/architecture.yml                                   53fdbc785621c38a295ae90ac09c67339ca654563d0b2f6480d034fc11868fd1
```

`git status --porcelain` → empty.

## Probe declaration (P8B-4, P8B-6, P8B-7)

**Files touched by probes** (all applied-and-reverted, hashes above):
`create_task.py`, `requests/__init__.py`, `routers/api_v1/tasks.py`.

**Files created and deleted by probes:**
`app/tests/integration/services/commands/item_economics/test_zz_reviewer_probe.py`
(two throwaway tests, run then removed with its `__pycache__`; absent from the
tree — `git status` clean).

**Database side effects, restored.** The M2 probes left 8 `phase8b` workspaces
with their users, items, categories and valuations (S2). All removed by an
explicit scoped delete; re-verified zero across `workspaces` (name `phase8b %`),
`users` (`phase8b\_%`), `item_categories` (`Wood category %`), `audit_logs`
(`actor_label phase8b%`), orphan `items`, `item_cost_evaluations`. Database left
at `c1d2e3f4a5b6 (head)`; no migration created or run; no disposable database
created.

**Pre-existing residue, NOT mine (passing-glance clause):** one row in
`item_valuations` (`ival_01M012JEV…`, `created_at 2026-08-14`) under workspace
`phase7 1aa0f269…` — a phase-7 rule-11½ leak that predates this session. Left
in place; routed below.

**Numbers, all re-measured in foreground by this session:**

- full non-E2E suite: **2183 passed / 23 failed / 1 deselected**, 130.25s;
- sorted failure IDs **byte-identical** to the phase-1 S2 baseline list
  (`diff` empty, 23/23);
- collection: **2207 collected**, +45 over 2162 reconciled exactly by
  `--collect-only` — phase file 21 nodes, `test_phase6_api_bridge.py` 21 → 45
  (+24, measured against the `513856d~1` blob);
- focused scope (phase file + bridge file): **66 passed**;
- `ruff check` on all five touched Python files: **All checks passed**.

**§7B.5 / B8(ii) verified LIVE, not only by construction.** A probe patched
`auto_commit_item_cost_evaluation_in_session` to write an `ItemCostEvaluation`
inside the savepoint and then raise. Result: `item_economics.auto_commit_failed`
logged, **no evaluation row** (savepoint rolled back), task created, and the
inline valuation **survives** (4200, `superseded_at IS NULL`). The plan's
"a price that survives a failed auto-commit is CORRECT" now has a live
observation behind it.

**Effect set (P-AB).** The inline birth write does exactly the PUT path's
effects: `write_item_valuation_chain_in_session` + one `item_valuation.created`
audit. Diffed against `set_item_valuation.py` — the only extra work there is the
ephemeral `preview` computed for the response envelope, which persists nothing.
No history record, no workspace event, no preview on the inline path.

**Graph (P8B-7).** Read-only. `archgraph_status` → 174 nodes / 260 edges,
revision `53fdbc785621c38a295ae90ac09c67339ca654563d0b2f6480d034fc11868fd1`,
0 stale, **5 pending**, mode `review`, 0 diagnostics — identical to the state
the handoff declared. Zero delta from this session; no promotion, rejection,
edit or maintenance action. Anchor accuracy: see N2.

## Carry-forward dispositions

| item | destination |
|---|---|
| S1, S2 | fix cycle r2 (this phase) — both land in `test_phase8b_inline_task_prices.py` |
| N1, N3 | coordinator: fold into §9's ledger discipline (pin deletion boundaries by line; state the scope behind "observed red") |
| N2 | the human's post-approval graph pass, together with the 5 HELD pending items — corrected spans recorded in the plan Review log |
| phase-7 `item_valuations` residue row | the existing rule-11½ maintenance prompt filed 2026-08-13 (§10 residue record) |
| `create_item_in_session` branch never exercised with the trio | no action — B7 made the write site shared and post-branch; recorded as an observation |

## Lessons for the plans

1. **A criterion that enumerates alternatives ("deleted **or** superseded-only")
   needs one row per alternative, and each row's expected-red mutation must be
   the conjunct that alternative uniquely exercises.** S1 is charter rule 2's
   companion in a new dress: C4 row 3's fixture satisfied the outcome for a
   reason (`is_deleted`) that is not the reason the missing row would test
   (`superseded_at`), so the shipped row looked like coverage of both.
2. **Rule 11½ has a second failure mode worth naming in §9: cleanup that cannot
   run because the transaction it depends on is gone.** "Own your teardown" is
   not enough — a `finally` that dereferences ORM instances the rollback
   expired will raise before deleting anything. The rule should read: capture
   the identifiers cleanup needs into plain locals BEFORE the `try`. Phase 8B
   contains both the defect (rows 2/3) and the correct pattern (row 1) side by
   side, which makes it a good exemplar to cite.
3. **A named mutation must pin its boundary.** "Delete X at its definition site"
   was reproducible byte-for-byte for four of five mutants; the fifth failed
   only because the deletion's line range was not stated. Cheap to fix, and it
   is what makes an implementer's ledger independently re-runnable.
4. **Evidence spans recorded at a node's birth deserve the same scrutiny as the
   phase's new edges.** The two edges describing 8B's own behaviour were exact;
   the two describing pre-existing behaviour were not. A node born mid-project
   inherits unverified anchors for everything it already did.
