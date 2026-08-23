---
plan: plan_3
role: reviewer
round: 1
date: 2026-08-23
actor: Opus 5
verdict: APPROVED
---

# Reviewer handoff — plan 3, round 1

## Opening

Phase 3 does exactly one thing and does it correctly: the active PRIMARY item that the
budget-status services already load is no longer thrown away — its derived filter spec now
rides along on `TaskBudgetStatus`, on both the manager and the worker face, without changing
a single byte of any payload. I verified the production change line by line against §6A's
prescription, then spent the round on the five areas the coordinator flagged as unexamined.
**Seven mutation probes, all new shapes or new sites, all reverted and checksum-verified.**
Every one of them turned the intended row red on its own assertion. Nothing blocking, nothing
to fix; four notes, all routed. **Verdict: `APPROVED`.**

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. The one graph item that is unresolved (1 pending review, 2 stale
nodes) is already held deliberately under the owner's own D29 deferral and is not touched
here.

## Tree reviewed

```
2e37f30 docs(narrow-typicals): consume plan-3 fix round — both checksums matched, reviewer dispatched
```

`git status --porcelain`: ` M .archgraph/agent-operating-policy.md` (the owner's live edit,
left alone) and `?? .archgraph/contexts/`. **No modified tracked file under `app/`.**

## Gate check

| # | check | result |
|---|---|---|
| 1 | `master_plan.md` §4: phases 1–2 `APPROVED`, phase 3 `IMPLEMENTED`; `plans/plan_3.md` header `state: IMPLEMENTED` | **agree** |
| 2 | `git merge-base --is-ancestor 07201f3 HEAD` | **succeeds** |
| 3 | no modified tracked file under `app/` | **clean** |

## Evidence posture — why no L4 ran

`git diff 186027a HEAD -- app/` is **empty**, and the working tree adds nothing under `app/`.
The eight files changed since the stamp are all under `docs/` or `.archgraph/`; the only test
that mentions either path (`tests/unit/docs/test_item_economics_docs.py`) reads
`docs/domains/item_economics/` exclusively (`:20`), which did not change. **The implementer's
stamp — 2674 passed / 21 failed / 1 skipped, 21-ID set unchanged both directions — therefore
describes my tree and is consumed by citation.** Re-running it would have been over-evidence
and a finding against this round.

**Control run (the green side of every probe below):**
`BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py -n 0 -p no:randomly`
→ **13 passed in 0.85 s**. `redis-cli ping` → `PONG`.

**One pre-run authorization line, for P9:** *narrower evidence insufficient because the
failing-test id claimed for C-N1(a)'s no-`WHERE` row has never been observed by any actor —
the fix round assigned it by inference and §6B.1 flagged exactly that.*

## Verdict

**`APPROVED`** — 0 blocking / 0 should-fix / 4 notes / 0 owner cards.

## The production change, verified structurally

Read line by line against §6A. Two files, 49 lines, and it is what was prescribed:

- `TaskBudgetStatus` gains `typical_filter_spec: TypicalFilterSpec | None = None`, **appended
  last, defaulted** (`get_task_budget_status.py:56`). No existing field's name, type, order or
  value moves.
- Both services compute `None if item is None else derive_spec_from_primary_item(item)`
  **immediately after** the unchanged 2-tuple `_load_task_and_item`
  (`get_task_budget_status.py:121`, `get_task_budget_status_worker.py:27`) — T-L1's expression,
  T-L8's 2-tuple.
- `_empty_status` and `_build_evaluated_status` take the carrier as a **required keyword-only
  parameter with no default** (`:89-95`, `:168-175`) — fail-closed per T-L2 and charter rule 11.
- `item_id=evaluation.item_id` is preserved on the evaluated path (`:224`) — A3, deliberately
  divergent from the spec's source.
- `typical_filters.py` is **untouched**; plan 1's shipped `derive_spec_from_primary_item(None)
  → TypicalFilterSpec()` contract is intact.
- Layer and typing: a `services → domain` import, fully annotated, no `Any`
  (`architecture/01_architecture.md`, `08_domain.md`). Clean.

**Perimeter.** `git diff 186027a^ 186027a --stat -- app/` is exactly the three declared files.
No serializer, no golden, no `get_task_production_time.py` /
`get_task_price_scenario.py` / `get_task_budget_allocations.py`.

## Probe ledger — seven probes, all new sites or new shapes

Every probe applied to the base tree, run at the stated scope, reverted, and the file's MD5
re-checked byte-identical. **No probe reproduces a cited measurement.**

| id | hypothesis | site (file · definition-vs-call-site) | scope | result | failing test ids |
|---|---|---|---|---|---|
| **P1** | a **worker-side** wrong-source derivation reddens the worker C4 row — the gap area 4 names | `get_task_budget_status_worker.py` · **call site**: derivation moved below the evaluation load and derived from `evaluation`; query count unchanged | L1 | **2 failed / 11 passed** | `test_C4_worker_uses_loaded_primary_item_not_evaluation_item`; `test_C2_and_C3a_worker_service_serialization_is_not_a_payload_change` — **both on their own assertion**: `item_category_ids: None != frozenset({'cat_chair'})`. No `StopIteration`, no collateral. |
| **P2** | a **value-gated** publish (`if status.typical_filter_spec is not None: payload[...]`) in the shared serializer payload | `domain/item_economics/serializers.py` · `serialize_task_budget_status` **definition** | L2 | **3 failed / 125 passed** | `test_C2_and_C3a_worker_service_serialization_is_not_a_payload_change`; `test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical`; `test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files`. **`test_C2_manager_budget_status_payload_has_the_existing_exact_key_set` stayed GREEN** → note N1. |
| **P4** | dropping the `None if item is None` guard — **T-L1's own hazard**, never measured by anyone | `get_task_budget_status.py` · load site | L1 | **1 failed / 12 passed** | `test_C5_...[C5-a-manager-no-primary]` |
| **P4w** | the same guard, worker face | `get_task_budget_status_worker.py` · load site | L1 | **1 failed / 12 passed** | `test_C5_...[C5-c-worker-no-primary]` |
| **P7** | `_empty_status` **definition** stops forwarding the carrier (hits all four call sites at once — the plan named only call-site mutations) | `get_task_budget_status.py` · `_empty_status` **definition** | L1 | **4 failed / 9 passed** | `C5-b`, `C5-d`, `C5-e`, `test_C2_and_C3a_worker_...`. `C5-a`/`C5-c` correctly stay green (they assert `None`). |
| **P8** | `_build_evaluated_status` **definition** stops forwarding the carrier — the sink, not the source | `get_task_budget_status.py` · `_build_evaluated_status` **definition** | L1 | **2 failed / 11 passed** | `test_C4_manager_uses_loaded_primary_item_not_evaluation_item`; `test_C4_worker_uses_loaded_primary_item_not_evaluation_item` |
| **P9** | C-N1(a) sub-check 3: recreate `uix_task_items_primary_active` **without** its `WHERE` (DDL inside the test transaction) | test transaction | L1 | **1 failed / 12 passed** | `test_CN1a_primary_index_is_partial_and_two_legal_shapes_are_valid`, failing at the **legal** flush: `UniqueViolationError: duplicate key value violates unique constraint "uix_task_items_primary_active"` |

## Area-by-area answers to the five questions the prompt asked

**1 — Test-double fidelity: is C4's narrower claim acceptable?** **Yes, for this phase.** I
enumerated every way the carrier can stop coming from the loaded PRIMARY item and made each
one red on its own assertion: wrong source on the worker (P1) and on the manager (§6B's cited
2/11), the guard removed on both faces (P4, P4w), and the value dropped at each of the two
sinks (P7, P8). Nothing in that class survives. What the double genuinely cannot prove is the
*attribution* — "the value came from the evaluated item **specifically**" — because no
mutation can make `_ScalarSession` return a different `Item`. §6B's narrower wording is the
honest one and I would not widen it. A content-aware double would buy diagnosis quality, not
coverage, and it is not worth a round here — see note N2 for where it does start to cost.

**2 — Coverage symmetry between the two faces.** They are **not** symmetric in shape, and one
half is measurably weaker. The **worker** key-set row serializes a status produced by
`get_task_budget_status_worker` itself — the real object, with a real populated spec. The
**manager** key-set row serializes `_status()`, a locally constructed `TaskBudgetStatus` whose
`typical_filter_spec` is the dataclass default `None`. P2 shows the consequence: a serializer
that publishes the spec **only when it is set** leaks the field on both faces, and the manager
row cannot see it. The class is still caught — by the phase's golden row and the live-clock
golden, both of which build the manager payload through the real service
(`test_live_clock_goldens.py:304`) — so this is a note, not a hole. See **N1**.

**3 — Does every criterion in §6 have a transcribed case?** Nine of ten do, each with its own
case:

| criterion | own case | |
|---|---|---|
| C1 | `test_C1_task_budget_status_appends_defaulted_spec_after_result` | exact 15-name list, 0-based index claims, `default is None` |
| C2(a)+(c) | `test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical` | one observable, per §6A L11 |
| C2(b) | `test_C2_manager_budget_status_payload_has_the_existing_exact_key_set` | exact 14-key frozenset ✔ (weak fixture — N1) |
| C3(a) | inside `test_C2_and_C3a_worker_service_serialization_is_not_a_payload_change` | service-produced spec == chair |
| C3(b) | same test | exact 9-key frozenset, on the service-level call the route makes |
| C4 | `test_C4_manager_...` + `test_C4_worker_...` | both faces, `mismatched`, `item_id` = X, spec = Y |
| C5 a–e | five parametrize ids | one per call site, plus the added `C5-e` |
| **C6** | **none** | satisfied by pre-existing suites + §6A(ii)'s no-default mutation |
| C-N1(a) | `test_CN1a_...` | three sub-checks |
| C-N1(b) | `test_CN1b_...` | anchored `match=`, plus `caught.value.message` |

**C6 is the only criterion with no case of its own, and that is correct** — its claim is "four
existing suites stay green with no edits", so those suites *are* its test. Nothing is
satisfied-only-by-elsewhere in a way that hides a gap.

**4 — The worker-side mutation gap.** Real, and now closed. Before this round the only
worker-side rows shown to bite were C3's shared-`payload` mutation and C5(c)/(d)'s call-site
mutations, all by the implementer; the coordinator's independent work was **entirely on the
manager service**, and the withdrawn C4 row's claim that the worker face also reddened was
part of what was withdrawn. **P1 supplies the missing measurement**: the worker C4 row and the
worker C3(a) assertion both bite, cleanly, on the worker's own file. P4w and P8 add two more
worker-reaching sites.

**5 — The ledger's remaining unverified rows (C2, C2(c), C6).** All three were run by the
implementer on a tree byte-identical to mine, so §9's policy consumes them by citation and
re-running them identically would be a finding against this round. I bought **variation**
instead: P2 attacks the same seam as C2/C3 with a shape nobody wrote (value-gated publish) and
returns a result the identical re-run could not have produced — the manager row's blindness.
For C-N1(a)'s no-`WHERE` row, which had an *inferred* rather than *observed* id, P9 observed it:
the id is **correct** and it fails for the stated reason.

## Refutations — recorded because a refutation is a result

- **R1 — `test_C2a_and_C2c_...`'s loop is not vacuous.** I suspected the golden loop could pass
  on an empty iteration (§9's "a guard that walks needs a row proving the walk found
  something"). It cannot: `_payloads` returns a hard-coded three-key dict literal
  (`test_live_clock_goldens.py:318-322`), so the loop always compares all three goldens.
- **R2 — no spec leak into the price-scenario payload.** `get_task_price_scenario.py:195`
  consumes `budget_status` by named field only; there is no `asdict`/`__dict__` call on a
  `TaskBudgetStatus` anywhere in `domain/item_economics/`, the item-economics services, or the
  router. A dataclass-wide dump would have published the new field on a surface plan 3 forbids.
- **R3 — no missed helper call site.** Repo-wide: `_empty_status` has exactly four production
  call sites (`get_task_budget_status.py:134,150`; `_worker.py:43,58`), `_build_evaluated_status`
  exactly two (`:157`, `_worker.py:64`), all passing the required keyword; `TaskBudgetStatus(...)`
  is constructed at two production and three test sites, **all keyword**. C1's positional-rebind
  hazard remains correctly labelled a *future* risk (§6A C1's honesty note).
- **R4 — the fix round's inferred id was right.** P9 confirms
  `test_CN1a_primary_index_is_partial_and_two_legal_shapes_are_valid`, and confirms it fails at
  the *legal* flush rather than at the `pg_indexes` assertions — because the legal shapes flush
  at `:392`, before the catalog read at `:394`. The ordering §6A C-N1(a)(i) settled is what makes
  that attribution true.
- **R5 — the "no graph delta" claim is verified, not asserted.** Live `archgraph_status`:
  **198 nodes / 298 edges, revision `364223242014…`, 0 diagnostics, 1 pending, 2 stale** —
  identical to master plan §8 and to the implementer's ledger. Nothing was promoted, rejected,
  edited or re-anchored, and no `startLine`/`endLine` was emitted anywhere.
- **R6 — the `asyncio_mode = auto` and C-N1(a) five-distinct-items refutations hold** on my
  tree; consumed from §6B by citation, not re-run.

## Findings

### Notes (4) — none blocking, none requiring a fix round

**N1 — C2(b)'s manager key-set row is blind to a value-gated publish.**
*Authority:* plan 3 §6 C2(b) as corrected by §6A C2; master plan §9 — *"after naming the
mutation and the column, confirm the fixture contains a row the mutation moves."*
*What is wrong:* the row serializes `_status()` (`test_budget_status_filter_spec.py:111-129`),
whose `typical_filter_spec` is the dataclass default `None` — so the fixture contains no spec
for a spec-dependent leak to move. **Measured (P2):** under a serializer that publishes the
field only when it is set, the worker row, the phase golden row and the live-clock golden all
go red and **this row stays green**. It remains correctly armed for its own named mutation
(unconditional add inside `if include_monetary:`), which is why this is a note and not a defect.
*Correction:* one argument — `_status(typical_filter_spec=TypicalFilterSpec(item_category_ids=frozenset({"cat_chair"})))`
— or build the manager status through `get_task_budget_status` as the worker row already does.
*Route:* **plan 4**, which is the first publisher and will edit this row anyway.

**N2 — `_ScalarSession`'s length is an unstated assertion about the query count, and eight rows
depend on it.**
*Authority:* master plan §9, the content-blind-double rule; plan 3 §6B's structural finding.
*What is wrong:* nothing today — this is debt with a named trigger. Eight rows in the file
(C4 ×2, C3a, C5 ×5) drive the services through a fake session whose value list encodes how many
`scalar()` calls the code makes. **The first phase that adds or removes a query in either
budget-status service turns all eight red with `RuntimeError: coroutine raised StopIteration`,
a message that names nothing.** §6B already paid one full fix round to this mechanism.
*Correction:* when a later phase touches either service's query sequence, make the double
content-aware (dispatch on the statement's target entity) in the same round, rather than
extending the value list.
*Route:* **plan 4, task 0** — a named trigger, not a scheduled task.

**N3 — §6 C6's prose count and scope line were never amended.**
*Authority:* §6A C6(iii) — *"C6 says 'the three consumer suites' and names four — fix the count
(rule 2), and name the router test file"*; master plan §9, *"a count in a plan sentence is a
checklist."*
*What is wrong:* §6's heading still reads "the **three** consumer suites" above a list of four,
and §6's scope line still declares C6's L2 root as
`tests/integration/services/queries/item_economics/` while C6's actual bite is in
`tests/unit/routers/api_v1/test_item_economics_router.py`. §6A carries both corrections and
wins, and the review prompt folded the router path into its evidence budget, so **no evidence
was lost** — but a later reader of §6 alone still reads a false checklist.
*Correction:* prose fold; no round.
*Route:* **coordinator fold into `plans/plan_3.md` §6**.

**N4 — C5-d shares C5-b's wrong-source inertness, and only C5-b is recorded.**
*Authority:* plan 3 §6B, *"C5-b is inert against a wrong-source derivation."*
*What is wrong:* nothing functional. C5-d (worker, category-less primary, expects
`TypicalFilterSpec()`) is inert against a wrong-source derivation for exactly C5-b's reason —
the wrong source also yields `TypicalFilterSpec()`. The worker face has **no C5-e analogue**;
its wrong-source coverage lives in `test_C4_worker_...` and in C3(a)'s spec assertion, both
proven to bite by P1. Recorded so a later round does not read C5-d's green as wrong-source
coverage, and does not "fix" the missing worker C5-e that C3(a) already is.
*Correction:* one sentence beside §6B's C5-b note.
*Route:* **coordinator fold into `plans/plan_3.md` §6B**.

## Lessons for the plans

1. **A criterion that asserts a payload key set should serialize a *service-produced* object,
   not a locally constructed one** — otherwise it can only see leaks that are unconditional.
   The two faces of this phase differ on exactly this point, and the difference is measurable
   (P2). This is the same family as §9's "confirm the fixture contains a row the mutation
   moves", applied to a key-set assertion rather than a value assertion. Worth adding to the
   corpus before plan 4 writes the publishing criteria.
2. **Name mutation sites at the definition as well as the call site when a helper fans out.**
   §6 named only call-site mutations for C5; the definition-side mutation (P7) reddens a
   *different* four rows and is the shape that a careless refactor actually produces. Charter
   rule 11 already says this; plan 3 applied it to C-N1 and not to C5.
3. **An inferred failing-test id is not an observed one.** §6B.1 correctly demanded an id for
   C-N1(a)'s no-`WHERE` row; the fix round supplied it by inference and said so. It happened to
   be right (P9) — but "retained without re-running" and "measured" are different claims and the
   ledger should distinguish them in a column, since the cost of observing it was one second.
4. **The evidence-reuse policy worked exactly as designed this round.** Zero L4 runs, zero
   reproduced measurements, and seven probes that each bought something no prior actor had.
   The tree-identity stamp (`git diff <stamp> HEAD -- app/` empty) is what made that safe to
   assert rather than assume.

## Carry-forward dispositions

| note | disposition | destination |
|---|---|---|
| N1 | strengthen C2(b)'s fixture when the field becomes publishable | **plan 4** (criteria) |
| N2 | make the double content-aware in the same round that changes a query sequence | **plan 4, task 0** (named trigger) |
| N3 | fix the count and name the router test file in §6's prose | **coordinator fold**, `plans/plan_3.md` §6 |
| N4 | record C5-d's inertness beside C5-b's | **coordinator fold**, `plans/plan_3.md` §6B |

## Write perimeter of this session

**Documents:** `handoffs/reviewer/20260823_plan3_review_handoff.md` (new);
`master_plan.md` §4 row 3 (tracker); `plans/plan_3.md` header `state:` and §8 (Review log).
**Code:** none. **Tool-recorded state:** none — `archgraph_status` only (read-only).

## Mutation-probe declaration

Every probe was applied to the base tree, measured, reverted, and the file re-checksummed
byte-identical to its pre-probe MD5:

| file | pre-probe MD5 | post-revert MD5 | probes |
|---|---|---|---|
| `beyo_manager/services/queries/item_economics/get_task_budget_status.py` | `aec7826f3119694da3bcb3815f22b570` | **identical** | P4, P7, P8 |
| `beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py` | `2b3b7d42e85185c4a6b2e01a63b91179` | **identical** | P1, P4w |
| `beyo_manager/domain/item_economics/serializers.py` | `e433330a94317c80ff024901721bd033` | **identical** | P2 |
| `tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py` | `d14dc521133d46e60d13327800a03308` | **identical** | P9 |

**Database/state side effects:** none persist. P9's `DROP INDEX` / `CREATE UNIQUE INDEX` ran
inside `db_session`'s transaction, which `tests/conftest.py:107-110` rolls back at teardown;
the index was re-read as partial and correct by the control run afterwards. No suite session
ran concurrently in this checkout. `git status --porcelain` at close is byte-identical to the
gate check: ` M .archgraph/agent-operating-policy.md`, `?? .archgraph/contexts/`.
