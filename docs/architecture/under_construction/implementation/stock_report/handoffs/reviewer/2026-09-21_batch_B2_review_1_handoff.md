---
plan: batch B2 (6, 7)
role: review
round: batch_B2-review-1
state: CHANGES_REQUESTED
date: 2026-09-21
actor: pipeline-reviewer (Claude Opus 5, skill `plan-reviewer`)
tree: ff39a96
---

# Batch B2 review 1 — phases 6 and 7 (`stock_report`)

**Gate check.** `planning/intention.md` begins `status: RATIFIED — by the owner (David): ratified
2026-09-18 … re-ratified 2026-09-19 (round 9)` — PASS. Batches A and B1 APPROVED per master plan
§4A. My tree: `git status --porcelain` empty; `git diff ff39a96..HEAD -- app/` empty (HEAD `ff6fefe`
is docs-only), so the implementer's L4 stamp and L1/L2 records are **tree-matched and consumed by
citation**. No L4 run (prompt §"What I verified"); the analytics drifter was not investigated.

## 1. Verdict

**CHANGES_REQUESTED** — one blocking finding group, test-only remedy, no production defect found.

| | rows | PASS | FAIL | NOT_VERIFIED |
|---|---|---|---|---|
| Phase 6 (`plan_6.md`) | 36 | **36** | 0 | 0 |
| Phase 7 (`plan_7.md`) | 52 | **44** | **8** | 0 |
| **Total** | **88** | **80** | **8** | **0** |

The eight FAILs are plan 7 **C4(a)–(h)**, one finding, one cause (B1 below). Production code in both
phases is, as far as I can measure, correct: I found **no** defect in `apply_stock_demand.py`,
`_demand_lookup.py`, `stock_demand_request.py`, `stock_demand_entries.py`,
`receive_stock_demand_webhook.py`, `webhook_verifier.py`, the router or the two perimeter
extensions. The fix round is nine or so test additions and zero production lines.

## ⚠ OWNER DECISIONS REQUIRED (1)

**Card 1 — Should three uncovered invariants become criterion rows?**

*Story.* Three guarantees this build relies on have no test that could ever catch them breaking.
Scanner's webhook must never stamp itself as the editor of a stock row — today it correctly leaves
the "last edited by / at" fields empty, but if a later phase starts stamping them, nothing goes
red and your audit trail quietly starts crediting a robot. Two concurrent Scanner deliveries must
take their row locks in the same order or they deadlock; the code sorts correctly, and I measured
that deleting *both* sorting rules leaves every test in the batch green. And the shared webhook
key-check refuses an unconfigured workspace setting; I measured that deleting that refusal also
leaves everything green, because the demand command happens to refuse it a moment later — which
stops being true the day the second Scanner webhook (phase 9) ships without its own check.

*Branches.*
- **Author all three** — three small rows, roughly four tests, spread over phases 7, 9 and a later
  concurrency phase. Each closes a guard that currently cannot fail.
- **Author only the third** (the shared key-check) — cheapest, and it is the one that becomes a real
  hole on a fixed date (phase 9).
- **Author none** — the code stays correct today and the debt is recorded in this handoff.

*Recommendation.* Author all three, because each is the "guard that cannot fail" shape the charter
calls the most expensive family in this project's history, and none of them is expensive to close.

*On silence.* Nothing gates on this: batch B2's fix round proceeds without it, and the three items
stay in the carry-forward table below. The gate holds; no row is authored by an agent.

*Trace.* intention §4B MC-17 (demand authorship cells); §4A MC-4 ("sorting the VALUES"); §8B MC-8
step 2 + plan 7 C1(c); carry-forward rows CF-1, CF-2, CF-3.

## 2. Per-phase verdict tables

### 2.1 Phase 6 — `plan_6.md` (36 rows, 36 PASS)

| Row | Test | Shape matches | Verdict |
|---|---|---|---|
| C1(a) | `test_apply_stock_demand.py::test_c1a_…` | row values + outcome + exactly one `:created`, no `:updated` | PASS |
| C1(b) | `test_c1b_…` | one row, same `client_id`, qty 7, one `:updated` with `quantity_requested 7` | PASS |
| C1(c) | `test_c1c_…` | `count_writes == 0`, no events, `applied` | PASS |
| C1(d) | `test_c1d_…` | two rows, old soft-deleted untouched, one goal record each | PASS |
| C1(e) | `test_c1e_…` | both `applied`, one `:created` + one `:updated` | PASS |
| C1(f) | `test_c1f_…` | class + `http_status` + message | PASS (note N3: the cell's "nothing written" half is unasserted; equivalent — see N3) |
| C2(a) | `test_c2a_…` | resolved category id | PASS |
| C2(b) | `test_c2b_…` | resolved via case-insensitive fallback | PASS |
| C2(c) | `test_c2c_…` | `category_not_found`, zero rows | PASS |
| C2(d) | `test_c2d_…` | exact wins over ambiguous | PASS |
| C2(e) | `test_c2e_…` | outcomes in request order, one row | PASS |
| C2(f) | `test_c2f_…` | resolves to the `Sofas` id | PASS |
| C2(g) | `test_c2g_…` | `category_not_found` | PASS |
| C3(a) | `test_c3_sequence_…` step (a) | all seven record fields incl. `created_at == t0` | PASS |
| C3(b) | same, step (b) | no record, `count_writes == 0` | PASS |
| C3(c) | same, step (c) | no record, row at 3 | PASS |
| C3(d) | same, step (d) | record on 3→4, not vs. historical max 5 | PASS |
| C3(e) | same, step (e) | no record, row at 0 | PASS |
| C3(f) | `test_c3f_…` | no record for a new row at 0 | PASS |
| C3(g) | `test_c3g_…` | `priority high`, `order 2`, record `quantity_awaiting 0` against a live 3 | PASS (armed — I re-measured, see §6 P3) |
| C4(a) | `test_c4a_…` | `count_writes == 0`, zero events, all `applied` | PASS |
| C4(b) | `test_c4b_…` | zero writes on `stock_report_items` | PASS |
| C5(a) | `test_c5a_…` | barrier-released two sessions, one row, exactly one `:created` | PASS |
| C5(b) | `test_c5b_…` | both complete, two rows | PASS — **behavioural mutation confirmed unforceable by measurement** (§6 P5); the plan's delegated **structural check passes**: step 5 sorts VALUES (`sorted(absent_identities)`), step 6 is `.order_by(StockReportItem.client_id).with_for_update()` |
| C5(c) | `test_c5c_…` | not returned after 0.5 s, `RuntimeError`, zero writes, heals on retry | PASS |
| C6(a) | `test_c6a_…` | equal 3 vs 300, ≤ 8 | PASS (measured exact count **8**) |
| C6(b) | `test_c6b_…` | equal, ≤ 8 | PASS (measured exact count **7** — see note N6) |
| C6(c) | `test_c6c_…` | equal, **== 5** | PASS (measured exact) |
| C6(d) | `test_c6d_…` | equal, ≤ 8 | PASS (measured exact count **8**) |
| C7(a) | `test_apply_stock_demand_timing.py::test_c7a_…` | first statement is `set_config`, `tuple(params) == ('5000','5000')` | PASS |
| C7(b) | `test_c7b_…` | `DBAPIError`, sqlstate `57014`, elapsed bound, holder still held, state unchanged | PASS |
| C7(c) | `test_c7c_…` | `StockDemandDeadlineExceeded`, 503, zero rows | PASS |
| C8(a) | via `test_c1a_…` | `:created` only | PASS |
| C8(b) | `test_c8b_…` | full six-field payload from `RETURNING`, `priority` as `"high"` | PASS |
| C8(c) | `test_c8c_…` | zero events for unchanged + skipped | PASS |
| C8(d) | `test_c8d_…` | `workspace_id == W`, `!= ""` | PASS |

### 2.2 Phase 7 — `plan_7.md` (52 rows, 44 PASS / 8 FAIL)

| Row | Test | Shape matches | Verdict |
|---|---|---|---|
| C1(a) | `test_receive_stock_demand_webhook.py::test_c1a_…` | 401 + `http_status`; real seeded workspace (fixture fix) | PASS |
| C1(b) | `test_c1b_…` | 401 against a blank key whose value the header repeats | PASS (re-armed — §6 P6) |
| C1(c) | `test_c1c_…` | 401 | PASS — **but see note N1: measured equivalent mutant** |
| C1(d)–C1(f) | `test_c1d/e/f_…` | 401; C1(f) asserts 401 **not** 500 | PASS |
| C1(g) | `test_c1g_…` | 401 from the command's mapping of phase 6's SELECT | PASS |
| C1(h) | `test_c1h_…` | the three messages collapse to exactly `{"Unauthorized."}` | PASS |
| C1(i) | `test_c1i_…` | 401 not 422 on a bad header + bad body | PASS |
| C1(j) | `test_location_tracker_webhooks_router.py::test_c1j_…` | headers arrive lower-cased | PASS (note N10: "accepted" proven compositionally, as the cell itself routes it) |
| C2(a) | `test_stock_demand_request.py::test_c2a_…` | 422 | PASS (cell's "nothing written" half unasserted — finding S1) |
| C2(b)–C2(d) | `test_c2b/c/d_…` | 422 | PASS |
| C2(e)–C2(h) | `test_c2_whole_entry_defects[…]` | 422, message names `entry 0` + `must be an object` | PASS |
| C2(i)–C2(k) | `test_c2_item_category_defects[…]` | 422, names `entry 0` | PASS |
| C2(l)–C2(q) | `test_c2_properties_defects[…]` | 422, names `entry 0` | PASS |
| C2(r)–C2(v) | `test_c2_quantity_requested_defects[…]` | 422, names `entry 0` | PASS |
| C2(w) | `test_c2w_…` | 422 above int32 max | PASS |
| C2(x) | `test_c2x_…` | names `entry 0` **and** `entry 2`, not `entry 1` | PASS (cell's "nothing written" half unasserted — S1) |
| C2(y) | `test_c2y_…` | parser accepts the extra key | PASS (cell's "200, `applied`" is asserted as "the parser returns the entry" — S1) |
| C3(a)–C3(d) | `test_c3a/b/c/d_…` | 422 naming `entries i and j`, or 200 for the two-category case | PASS |
| **C4(a)** | `test_c4a_…` | asserts two **signatures are equal**; the cell's outcome is "**one live row**" | **FAIL — B1** |
| **C4(b)–(e)** | `test_c4b/c/d/e_…` | assert signature equality; cells say "**one row**" | **FAIL — B1** |
| **C4(f)–(h)** | `test_c4f/g/h_…` | assert signature inequality; cells say "**two rows**" | **FAIL — B1** |
| C5(a) | `test_c5a_…` | full `results` list echoed as received + stored row normalized | PASS |
| C5(b) | `test_c5b_…` | exact key set per result | PASS |
| C5(c) | `test_c5c_route_…` + `test_c5c_router_renders_build_err_…` | raw bytes, headers, `identity == {}`, `build_ok` / `build_err` bodies and statuses | PASS |
| C6(a) | `test_c6a_…` | created row + dispatched event carry the configured W | PASS |
| C7(a) | `test_c7a_…` | `run_service` `success False`, 503, zero rows, zero dispatch | PASS |

## 3. The seven declined mutations — ruling and what I ran

**Ruling: the decline was factually accurate but doctrinally insufficient, and all seven are now
closed by me.**

The implementer's factual claim checks out: `app/tests/unit/domain/stock_report/test_criteria_normalization.py`
does assert exact golden-vector output (`test_normalization_value_table`,
`test_signature_uses_normalized_golden_vectors`, `test_normalization_preserves_string_property_key_spelling`)
for sort, strip, lower, dedupe, string-wrap, key-case/whitespace preservation and number
pass-through. Each of the seven mutations would indeed redden phase 1's own suite.

But that is a different claim from the one a mutation cell makes. A cell asserts **"this mutation
turns *this row's* test red."** Phase 1's coverage says nothing about whether plan 7's C4(b)–(h)
tests can fail. The two were conflated. Per the batch B1 rule cited in my prompt, I closed them.

Probe file: `app/beyo_manager/domain/stock_report/criteria_normalization.py` (phase 1, APPROVED,
out of perimeter). Seven mutants applied one at a time, each reverted before the next; test run each
time: `PYTHONPATH=. pytest tests/unit/services/commands/stock_report/test_stock_demand_request.py -q`
(control: 37 passed).

| Cell | Mutant I applied | Result |
|---|---|---|
| C4(b) "drop `sorted()`" | keep the dedupe set, emit first-seen order (`list(dict.fromkeys(...))`) | **red** — `test_c4b_…` (and `test_c3b_…` as a bonus); 2 failed / 35 passed |
| C4(c) "drop strip/lower" | `sorted({v for v in value if v.strip().lower() != ""})` | **red** — `test_c4c_…` (+ `test_c3b_…`); 2 failed / 35 passed |
| C4(d) "drop dedupe" | `sorted([...])` instead of `sorted({...})` | **red** — `test_c4d_…`; 1 failed / 36 passed |
| C4(e) "drop the string-wrap" | bare `value.strip().lower()`, no list | **red** — `test_c4e_…`; 1 failed / 36 passed |
| C4(f) "lower keys" | `return {k.lower(): v …}` | **red** — `test_c4f_…`; 1 failed / 36 passed |
| C4(g) "strip keys" | `return {k.strip(): v …}` | **red** — `test_c4g_…`; 1 failed / 36 passed |
| C4(h) "normalise numbers" | new branch coercing `int`/`float` (not `bool`) to `float` | **red** — `test_c4h_…`; 1 failed / 36 passed |

All seven bite 1:1 on their own row. `criteria_normalization.py` sha256 before **and** after:
`5be822d6b3c90fd4b993866a066ca6061a40e833502116a1ef98e66bcabd3791`. Phase 1's code is exactly as
found.

Two consequences worth recording. (i) The declined set is now **executed 29 = declared 29** for
plan 7; nothing is outstanding. (ii) `test_c4h_…`'s second assertion pair
(`a == compute_stock_criteria_signature({"n": 1})`) is inert under every mutant in this family —
both sides move together. It is harmless, but it is not the thing arming the row; `a != b` is.

## 4. The five risk areas (§1)

**Risk 1 — the statement budget is exact, not slack. CONFIRMED CORRECT, and I measured the exact
counts nobody had.** The plan's cells only bound C6(a)/(b)/(d) by `≤ 8`, so a green suite would not
have told anyone the real number. I inserted exactly one stray `await session.execute(text("SELECT 1"))`
inside the transaction block and ran the phase-6 file: C6(a), C6(c) and C6(d) went red and C6(b)
stayed green. That pins the true counts at **all-new 8, all-changed 7, all-unchanged 5,
unknown-category 8** — identical to the projection's H16 derivation, and it proves the demand path
takes no stray `SELECT`, no `session.get`, no autoflush and no lazy load. Structurally: steps 3–6
are Core/`select()` statements issued once each, `discover_live_rows_by_identity` selects three
columns rather than entities, and step 6's `populate_existing=True` is what makes the one ORM load
safe. Consequence for the plans, not the code: C6(b)'s row carries one statement of slack (note N6).

**Risk 2 — identity re-discovery under `ON CONFLICT DO NOTHING`. CONFIRMED CORRECT.**
`apply_stock_demand.py:169-195` locks with
`tuple_(StockReportItem.item_category_id, StockReportItem.properties_signature).in_(identity_list)`
— by identity, never by the ids steps 4/5 saw — and `created_client_ids` comes only from step 5's
`RETURNING`, so an identity won by a concurrent inserter yields no `:created` event here and the
row's real id is discovered by the lock. H17 is satisfied in the only way that keeps C5(a) true.
The locked-set assertion (`len(locked_by_identity) != len(identity_list)`) compares two
identity-keyed collections, so it cannot be fooled by duplicates. I also checked the one way
`entries_by_identity` could silently swallow an entry — two distinct `item_category_key`s resolving
to one `item_category_id` — and it cannot happen: distinct keys produce disjoint candidate sets in
`resolve_categories_for_entries`, and phase 7 rejects two entries sharing a key and a signature.

**Risk 3 — the three two-session rows. CONFIRMED CORRECT, with one fixture deviation (N2).**
C5(c)'s `record_statements` window opens at line 822, **after** the holder's `UPDATE` has been
issued and its `holder_locked` event awaited (line 820), and closes at line 833 — before the
`count_writes` assertion and long before the purge. So the engine-wide listener cannot charge the
holder's write to this row; H15/F6-5 are satisfied. `asyncio.shield(demand_task)` inside
`wait_for(…, 0.5)` cancels the waiter and not the task, which is what makes "has not returned after
0.5 s" a real observation rather than a cancelled one; the wait is bounded by a held lock plus a
5 s `lock_timeout`, so it is deterministic. C5(a)'s barrier genuinely forces the interleaving: both
coroutines yield at every statement, both reach step 4 before either inserts, and the loser's
`ON CONFLICT DO NOTHING` blocks on the speculative-insertion lock — which is exactly the race the
row exists for. C5(b)'s interleaving is **not** forceable (measured, §6 P5) and its structural check
passes. Deviation: all three open the second session as `async for s in get_db_session(): … return`
rather than the `finally`-closed form the fold's fixture cell prescribes (note N2).

**Risk 4 — the committing-test shape. CONFIRMED CORRECT.** Every one of the 28 + 3 + 13 tests that
seeds anything carries `finally: await purge_stock_report_workspace(...); await db_session.commit()`.
The three that seed nothing (plan 6 C1(f), plan 7 C1(c), C1(g)) write nothing — each raises at or
before `apply_stock_demand`'s step 2, inside `maybe_begin`, which rolls back. Every assertion is
workspace-scoped or row-id-scoped: I grepped every `select(` in the three integration files and
found no unscoped query and no global total. The intermediate-read helpers (`_quantity_requested`,
`_history`, and the two inline `await db_session.commit()` calls at
`test_apply_stock_demand.py:607` and `:847`) correctly close the autobegun transaction before the
next `AD`, which is the B5 trap.

**Risk 5 — the self-caught false green. FIX IS REAL; THE SHAPE SURVIVES AT ONE OTHER ROW, WHERE IT
IS AN EQUIVALENT MUTANT.**
*The fix.* Verified by measurement with a **varied** mutant (not the implementer's): I replaced
`if api_key is None or not api_key.strip():` with `if not api_key:` in `webhook_verifier.py` and
ran the integration file. `test_c1b_key_setting_blank_is_401` went **red** (1 failed / 12 passed).
Under the first-draft fixture it would have stayed green, because verification would have succeeded
and `apply_stock_demand`'s own step-2 check would have raised the identical
`LocationTrackerWebhookAuthError`. The real workspace in the corrected fixture is what arms it. Fix
confirmed.
*The sweep.* I then audited all ten C1 rows for the same two-sufficient-causes shape. C1(a), (b),
(d), (e), (f), (h), (i) all seed a real workspace and configure it, so a verification bypass reaches
`apply_stock_demand` and *writes*, which reddens them. C1(g) is by design the row that proves the
command maps phase 6's SELECT, so its single cause is correct. **C1(c) still carries the shape**: it
configures `location_tracker_webhook_workspace_id = None` and seeds nothing, so its 401 has two
independent sufficient causes. Measured: deleting the entire workspace-setting guard from the
verifier leaves **13/13 integration and 2/2 verifier tests green**. Ruling: at today's public
boundary this is an **equivalent mutant** (same status, same message, same "nothing written"), so
doctrine says record it and never demand a test for it. It stops being equivalent the moment a
second consumer of this shared verifier ships without its own workspace check — phase 9's
items-processed webhook. Routed as note N1, carry-forward CF-3, and owner card 1.

## 5. The fold (§4) and the O1 decision (§3)

### 5.1 The fold — sound, and the batch B1 lesson was applied

I derive **19** amended table cells, not 21 (note N8): plan 6 — the §6 fixture preamble, C1(b),
C1(d), C1(f), C2(f), C3(a), C3(g), C5(a), C5(b), C5(c), C7(a), C7(c) = 12; plan 7 — C1(e), C2(w),
C3(c), C4(a), C5(b), C6(a), C7(a) = 7. No outcome cell was touched; I diffed `a2f4fc2` cell by cell
and confirm the authority limit was respected.

**The lesson — "a fold that replaces a vague mutation with a precise site must verify the site
executes under that row's fixture" — was applied.** I checked every precise-site substitution
against its row's fixture, and independently measured the two that the batch B1 failure mode would
have broken:

- **M6-2 / C3(a) + F6-2 / C3(g) — the equivalence call, verified by measurement.** This is the exact
  pair batch B1 got wrong (a mutant declared equivalent when it was not). I applied the disputed
  mutant — step 8's `"quantity_awaiting": 0` → `row.quantity_awaiting` — and ran the whole phase-6
  file: **C3(a)'s test stayed green and C3(g) went red** (1 failed / 27 passed). The equivalence
  claim is exactly right *and* the fixture amendment that re-arms it at C3(g) works. Calibrated, not
  guessed.
- **M6-3 / C1(f)** — deleting step 2 leaves every entry `category_not_found` because step 3's
  category `SELECT` is itself workspace-scoped, so no FK is ever exercised. Site executes; the
  predicted mechanism is right; the earlier "FK failure (500)" prediction was wrong and correctly
  replaced.
- **M6-4 / C2(f)** — the `.strip()` in `DemandEntry.__post_init__` does execute under C2(f)'s
  fixture (the test builds entries through `DemandEntry`), and the predicted chain
  (`"  sofas "` → `lower(name) IN (…)` matches nothing → `category_not_found`) is correct. Note that
  a *second* `.strip()` exists in `resolve_categories_for_entries` for the exact-match comparison;
  naming the file and the construction site is what disambiguates them, and the fold did that.
- **M6-1 / C1(b)** — both enumerated mutants execute under the fixture (step 5 always runs; the
  event filter always runs), and the "insert a second row" impossibility is correctly reasoned from
  the measured `ON CONFLICT` behaviour.
- **M7-3 / C6(a)** — `ctx.workspace_id` is `""` for `identity={}`, so step 2 finds nothing and 401s
  before any write. Correct; the earlier FK prediction was wrong and correctly replaced.
- **M7-1 / C1(e)**, **M7-2 / C2(w)**, **M7-4 / C3(c)**, **M7-5 / C5(b)**, **M7-6 / C4(a)** — each
  site executes under its own fixture; all five predictions match what the implementer measured.
- **F7-1 / C7(a)** — the B6 correction is the single most valuable cell in the fold; without it the
  row was unachievable. Verified in the shipped test: `receive_stock_demand_webhook`'s own
  `time.monotonic()` is untouched, so a real deadline is computed and then exceeded.
- **F6-1** (the committing-test preamble) is the reason all 88 rows exist at all; **F6-5**
  (window-opens-after-H) is the reason C5(c)'s `count_writes == 0` is not a lie; **F6-6** is the
  only cell the implementation diverged from (N2).

**Did the fold weaken anything? No.** Every amended cell is strictly stronger or strictly more
determinate than what it replaced. The one place the fold left something on the table is C1(e) of
plan 7: its corrected mutation ("return the configured workspace id as soon as the header is
present") only reddens if the configured workspace *exists*, and that requirement lives in the §6
preamble ("the two settings configured for W") rather than in the cell. The preamble does carry it,
so the fold is not at fault — but the implementer's first draft ignored the preamble and
manufactured precisely that false green. **Lesson L-19 below.**

### 5.2 The O1 decision — the right call; no owner escalation was warranted

Instructing "bind two distinct parameters" rather than escalating the outcome cell was correct, for
four reasons. (i) It satisfies the cell **verbatim** — `tuple(first_params) == ('5000','5000')` — so
no acceptance criterion was weakened, reinterpreted, or amended by a non-owner. (ii) It changes no
observable behaviour: `set_config('statement_timeout', $1, true), set_config('lock_timeout', $2,
true)` and the single-bind form are semantically identical to PostgreSQL, so nothing about MC-9,
the 5 s budget or C7(b) moves. (iii) It genuinely strengthens the row — with one shared bind the
assertion could not distinguish "both limits set" from "one limit set twice", and now it can.
(iv) It was declared in plan 6's Review log under charter rule 14, so the record shows why the
shipped statement differs from the task text.

The one thing that must not be left as it is: **plan 6 §5 task 2 step 1 still prescribes the
single-`:ms` form, and the plan now contradicts the shipped code.** Amendment text in §8. That is a
task cell, not a criterion cell, so it is yours to write.

Where I would push back, plainly: nothing here is over-reach. The fold stayed inside mutation and
fixture cells, the one outcome-cell contradiction was resolved by changing the *implementation* to
meet the criterion rather than the criterion to meet the implementation, and the choice was
recorded. That is the correct direction of travel. The only honest criticism is the typed "21"
(N8) — small, but it is the named anti-pattern this project has already lost a round to.

## 6. Mutation audit

**Derived, not typed — both ledgers reconcile against my own count of the plan tables.**

- **Plan 6.** Counting non-`—` mutation cells, with C1(b) and C3(a) as two each: C1 6, C2 6, C3 6,
  C4 2, C5 3, C6 3, C7 3, C8 2 = **31**; minus C5(b)'s declared-unrunnable interleaving = **30**
  declared. The ledger table lists **30** executed (C1(c)/C4(a) correctly recorded as one physical
  change against two cells; C8(a) correctly recorded as a reuse of C1(a)). `declared 30 = executed
  30`. ✅
- **Plan 7.** C1 6, C2 9, C3 3, C4 8, C5 2, C6 1 = **29** declared; `29 = executed 22 + declined 7`.
  After §3, `29 = executed 29`. ✅
- **Re-sitings** (C2(d), C3(f), C6(a)) are each declared with the reason the first attempt was inert,
  and each final mutation realises the *plan cell's own predicted consequence* rather than a weaker
  one. C2(d)'s re-site ("stop at the ambiguous case-insensitive result") is in fact a faithful
  reading of the cell ("case-insensitive first → ambiguous"); the inert first attempt was the
  unfaithful one. Accepted.
- **Equivalent mutants declared:** C3(a)-iii — **independently verified equivalent by me** (P3).
  C5(b) — **independently verified unforceable by me** (P5).
- **New equivalent mutant found by me:** plan 7 C1(c)'s workspace-setting guard (N1).

### What I ran (all L1, whole-file, never `-k`)

| # | Hypothesis | Probe | Scope | Result |
|---|---|---|---|---|
| — | control | none | `test_stock_demand_request.py` | 37 passed |
| — | control | none | `test_receive_stock_demand_webhook.py` | 13 passed |
| P1–P7 | the seven declined C4 mutations bite on their own rows | `criteria_normalization.py` × 7 | `test_stock_demand_request.py` | all red 1:1 (§3) |
| P3 | is C3(a)-iii equivalent, and does C3(g) carry it? | `apply_stock_demand.py` step 8 `quantity_awaiting` | `test_apply_stock_demand.py` | C3(a) green, **C3(g) red** — 1 failed / 27 passed |
| P4 | is the C6 bound exact? | one stray `SELECT 1` inside the block | `test_apply_stock_demand.py` | C6(a)/(c)/(d) red, C6(b) green — 3 failed / 25 passed |
| P5 | can C5(b)'s interleaving be forced? | unsorted VALUES **and** no `ORDER BY client_id` | `test_apply_stock_demand.py` | **28 passed** — unforceable, as declared |
| P6 | is the C1 fixture fix real? | `if not api_key:` (varied shape) | `test_receive_stock_demand_webhook.py` | **C1(b) red** — 1 failed / 12 passed |
| P8 | does the C1(c) masking shape survive? | delete the workspace-setting guard | `test_receive_stock_demand_webhook.py` + `test_location_tracker_webhook_verifier.py` | **13 + 2 green** — equivalent today (N1) |

No L4 was run (prompt §"What I verified"; the stamp is tree-matched). No L2 was run: the
implementer's 334-passed L2 is on my exact tree and nothing I did changed it.

## 7. Findings, grouped by cause

### BLOCKING

**B1 — plan 7 C4(a)–(h): the MC-3 / M4 identity invariant is proven at the parser, not at the
endpoint, and the rows' stated outcome is never asserted.** (8 rows.)

*What is wrong.* Each of C4(a)–(h) is implemented in
`app/tests/unit/services/commands/stock_report/test_stock_demand_request.py` as a comparison of two
hex signatures returned by `parse_stock_demand_body` (`test_c4a_…` through `test_c4h_…`). The rows'
outcome cells say "**one live row**" (a)–(e) and "**two rows**" (f)–(h) — persisted database state.
No test anywhere in batch B2 delivers two requests carrying equivalent-but-differently-spelled
properties and counts live `stock_report_items` rows. Plan 6's replay rows (C1(b), C4(a), C4(b))
re-send the *identical* `DemandEntry` objects, and plan 7 C5(a) makes a single delivery.

*Violated authority.* Intention §4A MC-3, final bullet, verbatim: "**Invariant (M4), proven through
the webhook endpoint with real JSON bytes:** entries differing only in (a) key order, (b) list
element order, (c) list element case or outer whitespace, (d) duplicate list elements, or (e) a bare
string vs a one-element list resolve to **one** row. Entries differing in key case or whitespace, or
in any not-understood value, resolve to **two**. **Each of (a)–(e) is its own row, and so is each
'two rows' case.**" Measurement ledger **M4**: "Payloads differing only in JSON key order resolve to
one StockReportItem." Also plan 7 §1 goal ("the M4 identity invariant proven through the endpoint
with real JSON bytes") and the eight outcome cells themselves. The intention wins over the plan and
over any file-organization judgment.

*Why it is blocking rather than a note.* M4 is the ledger entry that "protects identity" and this
was its one scheduled proof. As shipped, the entire end-to-end claim rests on transitive inference
across three tests in two phases — exactly what a criterion row exists to refuse. It is also the
root cause of §3: relocating the rows to parser scope is what made seven of the eight mutations look
like out-of-perimeter phase-1 work.

*What does **not** block.* I found no production defect behind this. `DemandEntry.properties_signature`
is computed once in `stock_demand_request.py:74` and is the single value used for the duplicate
check, step 4 discovery, step 5 insert and step 6 lock, so parser-level equality does imply
row-level convergence. **The remedy is tests only.**

*Suggested correction.* Keep the eight parser tests (they now carry verified mutation arming, §3)
and add the endpoint half in
`app/tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py`: for
each of (a)–(h), two successive `receive_stock_demand_webhook` calls with the two raw bodies the
cell names, then `select(StockReportItem).where(workspace_id == W, is_deleted == False)` asserting
**1** row for (a)–(e) and **2** for (f)–(h), with the usual `finally: purge + commit`. Eight tests,
about ten lines each, no production change. If the owner prefers to spend less, the minimum the
intention will bear is C4(a) — the literal wording of M4 — with (b)–(h) recorded as a deviation; I
do not recommend it, because the intention says each case is its own row.

### SHOULD-FIX

**S1 — same cause as B1: three more plan 7 rows whose outcome cells name database state are
asserted at parser scope.** C2(a) ("422; **nothing written**"), C2(x) ("…; **nothing written**
(entry 1 not applied)"), C2(y) ("**200, `applied`**"). The parser tests assert the 422/acceptance
half only. Authority: the rows' own outcome cells; intention §8 (atomic batch) and ledger **M3**
("a rejected batch leaves no trace"). Structurally the write half is safe —
`receive_stock_demand_webhook` calls `parse_stock_demand_body` before `apply_stock_demand`, and
`apply_stock_demand` is the command's only writer — so this is contained, not blocking. Correction:
one integration test that delivers a malformed body through the command and asserts W's four tables
unchanged discharges C2(a) and C2(x); one that delivers the C2(y) body and asserts the created row
plus `outcome == "applied"` discharges C2(y). Fold into B1's fix.

**S2 — one orphan test.** `app/tests/unit/services/infra/test_location_tracker_webhook_verifier.py::test_raises_unauthorized_when_key_is_missing_or_wrong`
traces to no criterion row in the phase-7 coverage map and duplicates C1(d) and C1(e) at a narrower
scope. Charter rule 16 and the trace chain's link 3 require an untraced test to be deleted or
declared as a candidate criterion **with the defect it catches and the ledger entry it serves**;
plan 7's Review log declares only the file's *other* test (the success return value) that way.
Correction: delete it, or give it the same one-line declaration the sibling has. The sibling —
`test_returns_the_configured_workspace_id_on_success` — is a legitimate candidate criterion and
should be routed as one (it is the only thing that pins the verifier's return value, which C6(a)
otherwise proves only indirectly).

### NOTES (backlog)

- **N1 — the workspace-setting guard is an equivalent mutant today, and will not stay one.**
  Measured: deleting `if workspace_id is None or not workspace_id.strip(): raise` from
  `webhook_verifier.py` leaves 13/13 and 2/2 green, because `apply_stock_demand`'s step-2 check
  produces the identical 401 for the identical input. Doctrine: record as equivalent, never demand a
  test. But the verifier's own docstring declares it shared by phases 7, 9 and 13A, and phase 9's
  items-processed webhook may not carry its own workspace lookup. Carry-forward CF-3 + owner card 1.
- **N2 — undeclared fixture divergence in the three two-session rows.** The fold's F6-6 cell
  prescribes "closed and purged in a `finally` (§9 rule 9)"; `test_c5a`, `test_c5b`, `test_c5c` and
  `test_c7b` instead `return` from inside `async for … in get_db_session()`, leaving closure to the
  event loop's async-generator finaliser. No leak observed (pytest-asyncio runs
  `shutdown_asyncgens`, `pool_size` is 10) and the purge is covered by the main session's
  workspace-wide `finally`. Charter rule 14: the divergence should have been declared. Note only.
- **N3 — plan 6 C1(f): the cell's "nothing written" half is unasserted.** Equivalent in practice:
  under the row's own named mutation nothing is written either (the fold's own analysis), so an
  added assertion could not fail. Recording it so the next reviewer does not re-derive it.
- **N4 — MC-17's two demand rows are implemented correctly and asserted nowhere.** Intention §4B
  MC-17: "Demand creates a row — `created_by_id` NULL; `updated_*` NULL" and "Demand changes
  `quantity_requested` — `updated_*` unchanged". The code is exactly right: step 5 omits
  `updated_at`/`updated_by_id`, step 7's raw UPDATE sets `quantity_requested` only, and
  `StockReportItem.updated_at` carries no `onupdate`. C1(a) asserts `created_by_id is None` but no
  row asserts the `updated_*` cells, while `repair_stock_report.py:70,126,271` *does* stamp
  `updated_at` — so the two writers legitimately differ and nothing guards the difference.
  Candidate criterion; carry-forward CF-1; owner card 1.
- **N5 — MC-4's "sorting the VALUES" has no test that can fail.** Measured (P5): removing
  `sorted(absent_identities)` **and** `.order_by(StockReportItem.client_id)` leaves all 28 phase-6
  tests green. The plan predicted this and delegated a structural check, which passes. The residual
  debt is real: a future refactor that drops either sort ships a deadlock with a green suite.
  Candidate criterion for a later concurrency phase; carry-forward CF-2; owner card 1.
- **N6 — plan 6 C6(b) carries one statement of slack.** Measured true count 7 against a `≤ 8` cell,
  where C6(c) pins `== 5`. A plan lesson (bound the shape you derived), not an implementer defect.
- **N7 — two criteria in this batch are implementation-coupled by design.** C6 (statement counts)
  and C7(a) (bound parameters of a specific statement) assert generated-query properties, which
  charter rule 2 normally forbids. Both discharge ratified decisions (§14D D6's statement plan;
  MC-9's instrument (i)) and are the only way to observe a set-based contract, so they stand — but
  they *will* redden on a correct refactor of the statement plan. Recorded as a known cost so the
  next round does not read a red C6 as a regression.
- **N8 — a typed count.** The fold commit `a2f4fc2` and the review prompt both say "21 cells"; I
  derive **19** amended table cells (12 + 7). Charter manifest property 3.
- **N9 — plan 6 §5 task 2 step 1 contradicts the shipped code** after the O1 decision. Amendment
  text in §8.
- **N10 — plan 7 C1(j)'s "accepted" is proven compositionally**, not directly: `run_service` is
  faked in the router test, so the 200 says nothing about acceptance. The chain (Starlette
  lower-cases → the verifier reads `"x-api-key"`) is closed by this test plus C1(d)/(e)/(f). The
  cell routes it through C5(c) itself, so PASS. No action.

### What I verified correct, specifically (so the next round can skip it)

Perimeter: `git diff a2f4fc2..ff39a96 -- app/` is 17 files, **+2687/−0**, purely additive; I
confirmed `record_statements` and `count_writes` are byte-identical in the diff and that
`record_statement_calls` is a sibling using the same hook; `enums.py` gained
`StockDemandOutcomeEnum` with exactly two members and **none** of the other five names §6.1 claims;
`routers/api_v1/__init__.py` gained one import and one `include_router` and the existing
`location_tracker.router` mount is untouched (H22). Cross-phase: `receive_stock_demand_webhook`
opens no transaction (`run_service` neither begins nor commits — `run_service.py` is a pure error
boundary), `apply_stock_demand` is the sole owner via `maybe_begin`, and `deadline =
time.monotonic() + timeout_ms / 1000` is the command's first executable line, before verify and
parse, so the 5 s budget covers the whole request. Contracts: MC-8's 9-step order (set_config →
workspace → categories → discover → insert-absent → sorted lock → update → goal records → deadline)
matches task 2 step for step; MC-8's 401 rule (identical body, cause never returned) holds at all
five raise sites; MC-9's three instruments are each pinned by a row; MC-19's net-change rule (a row
created in this request never also emits `:updated`) is implemented at
`apply_stock_demand.py:278-284`; H9 is honoured — `_events.py` emits `priority.value`, not the enum
member, and C8(b) asserts the string. Settings-coverage restoration from batch A's fix round is
complete: C7(a) reads `Settings.model_fields["stock_demand_webhook_timeout_ms"].default` (never a
literal, charter rule 13) and plan 7 C1(a)/(b)/(c) exercise the other two settings unset and blank.
Workspace isolation: every query in the three integration files is workspace- or row-scoped; no
global count anywhere.

## 8. Master-plan / plan amendments as final text

**(1) Plan 6 §5 task 2 step 1 — replace** (closes N9; task cell, not a criterion):

> 1. `SELECT set_config('statement_timeout', :statement_timeout_ms, true),
>    set_config('lock_timeout', :lock_timeout_ms, true)` with both binds set to `str(timeout_ms)`.
>    **Two distinct bind names, not one used twice** (O1): a repeated bind compiles to a single
>    `$1` with one parameter, which cannot satisfy C7(a)'s "its two parameters"; two names compile
>    to `$1`/`$2` and make the row pin that *both* limits are set. Semantically identical to
>    PostgreSQL.

**(2) Master plan §6.5 — `statement_listener.py` row, append:**

> `record_statement_calls(session)` — `asynccontextmanager` yielding `list[tuple[str, Any]]` of
> `(statement, parameters)` from the same engine-wide `before_cursor_execute` hook as
> `record_statements`, which it leaves byte-identical (batch B2, blocker B3). Use it whenever a
> criterion asserts a **bound value**: the compiled text carries `$1`/`$2`, never the value.

**(3) Master plan §9, statement-budget note — add** (records what P4 measured, so no later phase
re-derives it):

> **The demand statement budget, measured 2026-09-21 (batch B2 review 1).** Exact counts, not
> bounds: all-new **8**, all-changed **7**, all-unchanged **5**, one-unknown-category **8**. Verified
> by inserting exactly one stray `SELECT` inside `apply_stock_demand`'s transaction block: plan 6
> C6(a), C6(c) and C6(d) redden, C6(b) does not. A later phase that adds a statement to this path
> must move these numbers deliberately.

**(4) Master plan §6.1 enums row — no further correction needed.** Today's correction is accurate as
written; `StockDemandOutcomeEnum` shipped in phase 6 with exactly `applied` and `category_not_found`,
and the other five names are still absent (verified by reading `enums.py`).

## 9. What I ran, and the mutation-probe declaration

**Commands** (all from `app/`, all L1 whole-file, `-o addopts=--strict-markers` for the unit file so
xdist did not mask per-test ids):

```
PYTHONPATH=. pytest tests/unit/services/commands/stock_report/test_stock_demand_request.py -q
PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_apply_stock_demand.py -q
PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py -q
PYTHONPATH=. pytest tests/unit/services/infra/test_location_tracker_webhook_verifier.py -q
```

Two controls + thirteen probe runs; see the table in §6. No L2, no L3, **no L4**.

**Mutation-probe declaration.** Every probe was applied, run, and reverted before the next; each
file's sha256 was captured before the session and re-captured after the last revert, and **all
seven are identical**:

| File | sha256 before **and** after | Probes |
|---|---|---|
| `app/beyo_manager/domain/stock_report/criteria_normalization.py` | `5be822d6b3c90fd4b993866a066ca6061a40e833502116a1ef98e66bcabd3791` | the seven declined C4(b)–(h) mutations (**phase 1, APPROVED code** — reverted and checksum-verified after each) |
| `app/beyo_manager/services/commands/stock_report/apply_stock_demand.py` | `f4d28e62005868502fd20423d0031e28196b9871362d15c9f15aa218a1d20009` | P3 (step-8 `quantity_awaiting`), P4 (stray `SELECT`), P5 (unsorted VALUES + no `ORDER BY`) |
| `app/beyo_manager/services/infra/location_tracker/webhook_verifier.py` | `5cc45abe9a505ead3b63c2062f33a0cf501b236875a909f89988df3c26241d35` | P6 (blank-key guard → falsy check), P8 (delete the workspace-setting guard) |
| `_demand_lookup.py` | `9b8325e393fd1f1974bebb216a405d5e3dd4393b9d17e6a214d5763b50132a22` | none (listed for completeness) |
| `stock_demand_request.py` | `d8578ce3826a5e66d27b8dada075f26b481163941567e3146132be5b122c5d84` | none |
| `stock_demand_entries.py` | `9cd1c61e307d0d491d392ccb40fb33a00abed5c8c32b2bf5471ae0a7e9c365a8` | none |
| `receive_stock_demand_webhook.py` | `a151ad89d0577488dd0089dc3dacd30e1b3aaff1d3b393b2d7bdfb1f1df6d487` | none |

No test file, plan, prompt or other handoff was modified by a probe. `git status --porcelain` is
**empty** at close. **Database/state side effects:** none persisted — every test I ran carries its
own `finally: purge_stock_report_workspace + commit`, all runs ended green-or-expected-red with the
teardown executing, and the xdist worker databases are dropped by `tests/database_isolation.py` at
the end of each run. The dev database (`beyo_manager`) was never a target. Three throwaway probe
scripts live in the session scratchpad, outside the repository.

**My write perimeter for this session:** this handoff file; one appended Review-log entry in
`plans/plan_6.md` §8 and one in `plans/plan_7.md` §8. Nothing else. No commit, no tracker row (the
batch row is the orchestrator's), no archgraph write, no master-plan edit (§8 supplies the text).

## 10. Carry-forward dispositions

| id | Item | Destination |
|---|---|---|
| CF-1 | MC-17's two demand-authorship cells have no row (N4) | candidate criterion → phase 7 fix round or phase 8; owner card 1 |
| CF-2 | MC-4's sorted-VALUES / `ORDER BY` lock order has no test that can fail (N5) | candidate criterion → the next phase with a forceable two-writer fixture (13A) ; owner card 1 |
| CF-3 | The shared verifier's workspace-setting guard is unguarded and stops being an equivalent mutant at phase 9 (N1) | phase 9 (`items processed` webhook); owner card 1 |
| CF-4 | `test_returns_the_configured_workspace_id_on_success` is an undeclared candidate criterion (S2) | fold into the B2 fix round's Review-log declaration |
| CF-5 | C6 / C7(a) are implementation-coupled by design and will redden on a statement-plan refactor (N7) | master plan §9 note (§8 item 3) |
| CF-6 | `app/tests/helpers/test_settings.py` still exists as a test-named helper module (N-R9, inherited) | unchanged; still outside any batch-B perimeter |

## Lessons for the plans

- **L-19 — a mutation cell that depends on a preamble fixture must say so.** Plan 7 C1(e)'s
  corrected mutation ("return the configured workspace id as soon as the header is present") only
  reddens if the configured workspace actually exists. The §6 preamble carries that ("the two
  settings configured for W"), but the cell does not, and the implementer's first draft substituted
  a placeholder id and manufactured a false green in which two distinct causes raised the same
  exception class. Where a mutation's bite depends on a preamble condition, repeat the condition in
  the cell. (This cost nothing here only because the implementer caught itself.)
- **L-20 — an outcome cell naming persisted state cannot be discharged at a narrower scope, however
  reasonable the file split.** Plan 7's C4 and three C2 rows were relocated to parser-level unit
  tests on the fold's own C2(w) reasoning; that reasoning was about *where the defect lives*, not
  about *what the row observes*. The rule the plans should carry: relocating a row's test to a
  narrower surface is a criterion change, and criterion changes are the owner's.
- **L-21 — "the dependency's own suite covers it" never discharges a mutation cell.** A cell asserts
  that *this row's* test reddens. Phase 1's golden vectors reddening is a different proposition, and
  the conflation cost seven declared-but-unrun mutations. When a cell's site genuinely lives in
  approved code, the reviewer runs it (batch B1's rule, applied here) — but the plan can pre-empt the
  question by siting the mutation at the wiring instead, exactly as the fold did for C4(a).
- **L-22 — bound the shape you derived.** The projection derived 8/7/5/8 for C6; the cells say
  `≤ 8` for three of the four and `== 5` for one. A `≤` bound on a derived count buys a green suite
  one statement of slack for free (N6).

## Review log entries appended

`plans/plan_6.md` §8 and `plans/plan_7.md` §8 each carry one appended entry, layer 1 only.
