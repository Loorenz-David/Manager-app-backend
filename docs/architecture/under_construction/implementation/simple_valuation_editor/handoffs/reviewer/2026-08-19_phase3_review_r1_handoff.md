---
plan: 3
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-19
actor: Opus 5 (review r1)
---

# Phase 3 review r1 — the carried repairs from phase 2's review

**Verdict: CHANGES_REQUESTED.** 0 blocking, 3 should-fix, 6 notes.

**The endpoint is correct and every one of the seven repairs does what it was asked to do.**
All four named mutations discriminate; I re-derived three of them myself and found no
disagreement with the ledger. Nothing here is a behaviour defect and nothing here changes a
payload.

What CHANGES_REQUESTED is for: **all three should-fixes are the same shape — a record that
does not survive the reader it was written for.** F8's decision is recorded in code but points
at a label that archives; F9's decision is recorded only in a document that archives; and the
C1 fixture's one comment credits the half of the fixture that my measurements show does
nothing, while the half that does everything reads as incidental sequencing. Plan 3 §3 asked
for decisions *recorded*, and the handoff answered the narrower question of whether they were
*made*. Each fix is a comment; none touches an executable line except deleting two inert
statements and one now-unused import.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required. Every finding is a coordinator/implementer matter with verbatim
replacement text supplied.

## 1. Perimeter — verified

`git show --stat ef55f6d` and `git status --porcelain --untracked-files=all` at review time:

| Path | Status |
|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | in perimeter, +3/−2 |
| `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` | in perimeter, +183/−13 |
| `handoffs/implementer/2026-08-19_phase3_implement_r1b_handoff.md` | declared, expected |

**Nothing outside the two-file application perimeter changed.** No third file, no mirror
artifact, no `price_scenario.py`, no serializer, no router. The working tree carries only the
concurrent owner change (`purchase_api.py`, its unit test, `.archgraph/architecture.yml`) —
not reviewed, not touched, not counted against phase 3.

## 2. Criteria — C1 through C7

**All seven are met.** C5's F8 half is met as to *deciding and recording*; the recorded text
is F-1.

| C | Verdict | What I verified, and how |
|---|---|---|
| C1 | **MET** (see N-3) | Row asserts `saved.valuation_id == current` and `expected_sale_price_minor == 855_000`. I applied the named mutation at `_current_valuation`'s definition myself: **red 2/2**, and **red again after `VACUUM (ANALYZE, FULL) item_valuations`**. Second clause — "record that it reddened nothing before this row existed" — not in the handoff (N-3). |
| C2 | **MET** | Deleted purchase term → `can_commit: true`, model collapses. Coordinator measured the unfiltered-`any` mutation suite-wide as exactly this row. I additionally proved the row's **second** assertion carries weight — see N-2, and it is a better result than the handoff claims. |
| C3 | **MET** | `{11, 12, None}` row. **Re-derived from the intention's rule, not from the code:** usable `{11,12}` → `_median` = `23/2`; `round_half_even(23,2)` → `quotient 11, 2·remainder = 2 = b, 11 % 2 ≠ 0` → **12**; total `11 + 12 + 12 = 35`. Truncation → `11 + 12 + 11 = 34`. Named mutation reddens exactly this row. Half-up caveat in N-1. |
| C4 | **MET** | `test_c16_discriminating_literal_is_exact` absent (grep, repo root). The literal's owner survives: `tests/unit/domain/item_economics/test_price_scenario.py::test_quantity_zero_falls_back_to_a_divisor_of_one:382-386` asserts `slider_domain(8_919, 0, 0) == SliderDomain(110, 3_080, 12_100)` verbatim. The `max(6, quantity)` suite-wide one-test result is the coordinator's measurement; **I did not re-run it** and record that. |
| C5 | **MET**, with F-1 | **F6 removed.** I verified the deadness structurally, not behaviourally: `binding = "detached" if item is None` (`get_task_budget_status.py:111`) and `can_commit`'s conjunction opens with `item is not None` (`:188`). Same fact, so the block could never fire. **F8 decided and recorded** — the decision is right, the text is F-1. |
| C6 | **MET** | F9 accepted with a reason I verified true: `TaskBudgetStatus` (`get_task_budget_status.py:33-48`) carries `item_id: str \| None` and `result: ItemCostResult \| None` — no `Task`, `Item`, selection, terms or valuation. Collapsing genuinely requires changing that dataclass. Phase-2 C1/C2/C9/C10 rows all green. **Where the acceptance lives is F-3.** |
| C7 | **MET** | My own full run: **26 failed / 2430 passed / 1 deselected** in 128.94 s. Arithmetic reconciles exactly: `2425 − 1 duplicate + 3 new + 3 owner = 2430`. All 26 IDs are pre-existing failures; **none is in `services/queries/item_economics/` or `domain/item_economics/`**, and all 8 of the unit failures documented at `docs/debugging/test_suite_runs_against_the_development_database_20260801.md:143-151` are present. |

### The question plan 3 §3 actually asked — does each decision survive closeout?

| | Recorded where | Survives closeout? |
|---|---|---|
| **F6** | Nowhere — the block is simply absent | **Yes, by construction.** An absent dead branch needs no record; `can_commit`'s conjunction now reads as its own explanation. No action. |
| **F8** | Two code comments — **the right medium** | **The record survives; its justification pointer does not.** `C10` resolves only inside `plans/plan_2.md`, which moves to `archive/plan_2/`. → **F-1** |
| **F9** | The implementer handoff only | **No.** It moves to `archive/plan_3/` and becomes invisible to the next person who profiles this endpoint. → **F-3** |

## 3. Findings

### F-1 — should-fix — the F8 comments dangle, *and* they sit above predicates that are load-bearing

`get_task_price_scenario.py:75` and `:89`, both reading:

```python
# Redundant defence-in-depth: _load_task_and_item owns the tenant boundary (C10).
```

**Confirmed, from the repository root.** `grep -rnE '#.*\b(C[0-9]{1,2})\b' app/beyo_manager/`
returns these two lines and nothing else. The house convention is `path:symbol` — four
instances, all in `item_economics` (`price_scenario.py:54`, `calculator.py:125`,
`serializers.py:299`, `cases/serializers.py:104`). `C10` matches none of it and resolves
only inside a document that archives.

**The extension P1 asked for, and it is the sharper half.** Both comments are placed as the
**first line inside a multi-predicate `.where(...)`**, and in both cases the predicates below
them are load-bearing:

- `_current_valuation`: `superseded_at.is_(None)` is the filter **phase 3's own C1 row exists
  to protect** — F4 was raised precisely because deleting it left the file green. A comment
  reading "Redundant defence-in-depth" one line above it is the exact invitation F4 was
  written to remove.
- `_typical_block`: `TaskStep.is_deleted.is_(False)` is load-bearing —
  `test_c5_deleted_steps_do_not_create_a_participating_section` and C10's own hides-deleted row
  both depend on it.

Plan 3 §3 F8 said *"do not silently leave a reader thinking they are load-bearing."* The
converse error is worse here, and it is the one now in the tree.

**Verbatim replacement — `get_task_price_scenario.py:72-81`:**

```python
async def _current_valuation(ctx: ServiceContext, item_id: str) -> ItemValuation | None:
    return await ctx.session.scalar(
        select(ItemValuation).where(
            # This line only — workspace_id is redundant defence-in-depth: item_id is
            # already resolved workspace-scoped by
            # get_task_budget_status.py:_load_task_and_item, proven by
            # test_price_scenario_query.py:test_c10_task_resolution_is_workspace_scoped_and_hides_deleted.
            # The three predicates below are load-bearing.
            ItemValuation.workspace_id == ctx.workspace_id,
            ItemValuation.item_id == item_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
    )
```

**Verbatim replacement — `get_task_price_scenario.py:88-93`:**

```python
                select(TaskStep).where(
                    # This line only — workspace_id is redundant defence-in-depth:
                    # task_id is already resolved workspace-scoped by
                    # get_task_budget_status.py:_load_task_and_item, proven by
                    # test_price_scenario_query.py:test_c10_task_resolution_is_workspace_scoped_and_hides_deleted.
                    # The two predicates below are load-bearing.
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.task_id == task_id,
                    TaskStep.is_deleted.is_(False),
                )
```

Both replacements are comment-only. Ruff has no `E501` enabled in this project (the existing
101-char comment at `:75` passes `ruff check`), so the long test-path lines are fine; I ran
`ruff check` and `ruff format --check` on the current file and both pass, and the replacements
change no code line.

---

### F-2 — should-fix — the C1 fixture's two `SET LOCAL` statements are inert, and the only comment in the file credits them

This is P2, answered by measurement rather than argument. Four probes, all on the C1 mutant
(`_current_valuation` with `superseded_at.is_(None)` dropped), focused file, 49 tests:

| Probe | Result |
|---|---|
| As shipped | C1 **red** 2/2 |
| As shipped, after `VACUUM (ANALYZE, FULL) item_valuations` | C1 **red** 1/1 |
| **Both `SET LOCAL` statements deleted**, update order kept | C1 **red 3/3** |
| **Both `SET LOCAL` kept**, the two UPDATEs swapped | C1 **GREEN 3/3** |

**The determinism comes entirely from the UPDATE ordering. The planner GUCs contribute
nothing.** The table holds one live row and never exceeds a handful during the test; PostgreSQL
seq-scans it regardless of what `enable_indexscan` says.

The file's one comment (`:824-825`) reads:

```python
# Update old, then current so the forced heap scan makes the no-filter mutant
# deterministically encounter the older live tuple first.
```

It presents a two-part mechanism — *forced heap scan* **and** *tuple order*. My third and
fourth probes show only the second part exists. **The failure this sets up:** the next person
editing this test sees two conspicuous, unusual `SET LOCAL` statements (the only planner GUCs
in the entire suite — `grep -rn "SET LOCAL\|enable_indexscan\|enable_bitmapscan\|enable_seqscan"
tests/` returns nothing else) and preserves them, while the two adjacent `flush()` calls read as
incidental sequencing and get reordered. C1 then passes forever without being able to fail —
the same class this project has now recorded four times (*"a fixture whose expected value is the
same under the defect proves nothing, even when the assertion beside it bites"*), and charter
rule 4's no-dead-scaffolding.

`"the no-filter mutant"` is also a second P1-class reference: it names a mutation that exists
only in an archived ledger. Replaced below.

**On P2's other two questions, both answered and both clean:**

- **Does the GUC leak?** **No — confirmed empirically, not only by reading.** I added a
  temporary `assert (await db_session.scalar(text("SHOW enable_indexscan"))) == "PROBE_LEAKED"`
  after the residue block; it read **`'on'`**. `SET LOCAL` is transaction-scoped, the `finally`
  rolls back, and `tests/conftest.py:47-50` rolls back again at teardown. **No suite-wide
  hazard.** This becomes moot under the fix below, which deletes them.
- **Is a plan-dependent ledger row acceptable evidence?** The question dissolves: the row is
  not plan-dependent. It is **heap-order**-dependent, which is a weaker guarantee than an index
  and should be stated as such at the fixture — which the replacement does.

**Verbatim replacement — delete `test_price_scenario_query.py:830-831` entirely** (the two
`await db_session.execute(text(...))` lines), and replace `:824-825` with:

```python
        # The mutant this row exists to catch (dropping superseded_at IS NULL) returns
        # whichever live row the scan reaches first. Updating `older` BEFORE `current`
        # puts the older row's newer tuple earlier in the heap, so the mutant returns
        # the older row and this test goes red. Measured at review r1: swap these two
        # updates and the mutant passes 3/3. Heap order is not a guarantee — if this
        # ever stops discriminating, that is what changed.
        # The assertions below do not depend on any of it: the unmutated query is
        # deterministic by uix_item_valuations_current, a partial unique index on
        # item_id (models/tables/item_economics/item_valuation.py:35).
        older.superseded_by_id = current.client_id
        await db_session.flush()
        current.expected_sale_price_minor = current_price
        await db_session.commit()
```

**Do not miss the import.** `text` is used at `:830-831` and nowhere else in the file
(`grep -n "text(" …` returns only those two). Deleting them leaves `text` unused and
`ruff check` will fail `F401`. Line 11 must become:

```python
from sqlalchemy import delete, func, select
```

*(If the implementer prefers to keep the GUCs as insurance for a larger table, that is
defensible — but then the comment must say they are insurance and that they are currently
inert, because the measurement above is now on the record either way.)*

---

### F-3 — should-fix — F9's latency acceptance survives closeout nowhere

This is P4, and the answer is: **a comment at the call site.** Not the master plan, not a graph
node.

- **Master plan** — lives under `docs/architecture/under_construction/implementation/` and moves
  with the project. It reaches the *next pipeline*; it does not reach the person who opens a
  profiler on a slow price-scenario screen.
- **Graph node** — the right medium in principle, but unavailable: the projection's items are
  pending `ai_inferred`, `repair_anchors` returns `INTERNAL_ERROR` on them, maintenance refuses
  them by design, and the review path is coordinator-and-human-owned. And a local latency
  trade-off is not an architectural fact about behaviour.
- **Call site** — the only one of the three that is in the same file as the cost, is read by
  exactly the person who will question it, and cannot be archived away.

The cost is real and on the **common** branch: `get_task_budget_status(ctx)` at `:155` runs
`_load_task_and_item`, `_load_preview_inputs` and the current-valuation select, and `:156`,
`:164` and `:169` then repeat all three — roughly eight redundant round trips on every open of
a task with no committed evaluation, which is the state this screen exists to resolve.

**Verbatim replacement — `get_task_price_scenario.py:155`:**

```python
    # Accepted duplication (measured at phase 3): this re-reads task, item, the current
    # valuation and the preview inputs that get_task_budget_status has already loaded —
    # roughly eight redundant round trips on the common no-evaluation branch. Collapsing
    # it means returning those objects from get_task_budget_status, whose TaskBudgetStatus
    # carries item_id and no objects and is a contract other screens consume. Reusing this
    # service is also what keeps status, binding and the tenant boundary identical to them.
    budget_status = await get_task_budget_status(ctx)
```

## 4. Notes

**N-1 — C3 separates half-even from truncation, not from half-up. Say it out loud.**
P5 asked me to check rather than assume, so I mutated `round_half_even`'s tie branch to half-up
(`if twice_remainder >= b`). Result on the focused file: **C4 red, the new C3 row green.**
`11.5` rounds to `12` under both modes, so C3 cannot tell them apart. This is not a defect —
the test's own name says `differs_from_truncation`, and C4 carries the half-up half (its `10.5`
→ `10` half-even vs `11` half-up). **The pair pins the mode; neither row does alone.** That
sentence belongs in plan 3's Review log, because the master plan's own lesson
(*"a criterion naming a rounding MODE needs a fixture where the modes disagree"*) reads as
though one fixture settles it.

**N-2 — C2's second assertion is not decoration, and it turns out to guard something nobody
claimed.** P5 asked whether `model["constant_deduction_minor"] == 0` pulls weight. It does, on
a different mutation than C2's named one. I deleted `collapse_terms`'s `if term.is_deleted is
True: continue` (`price_scenario.py:71-72`) and ran the **whole suite**: **exactly one test
reddens in the entire codebase, and it is `test_phase3_c2_…`** (26 → 27 failed, ID-diffed, one
added, none removed). The domain owner file `tests/unit/domain/item_economics/test_price_scenario.py`
stays **53/53 green**.

So: `collapse_terms`'s deleted-term semantic — intention §3.1B / §9A.2, a phase-1/2 mechanism —
had **no guard anywhere in the suite** before this phase, and phase 3's F3 row is now its sole
one. That is a genuine bonus, and also a fragility: the only guard for a domain function now
lives in one assertion in an integration file two layers away. If that row is ever renamed,
narrowed or moved, the semantic silently loses its only test. Route to phase 5 (or the closeout
sweep): either add a direct row in the domain file, or note the dependency at
`price_scenario.py:71`.

**N-3 — C1's second clause is unrecorded.** C1 says *"Record that it reddened nothing before
this row existed."* The handoff's ledger records the mutation and its observed-red delta, but
never states the before-state. The fact survives in `plans/plan_3.md` §3 F4 (quoting phase 2's
review) — which archives to `archive/plan_3/`, the same medium F-3 is about. One sentence in the
fix handoff closes it.

**N-4 — P3: a third observation, and it disagrees with the implementer's.** The candidate ID
`tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
was **absent from my full run** (26 failed, 2430 passed). Standings on identical code, commit
`ef55f6d`:

| Observer | Failed | That ID |
|---|---|---|
| Implementer, run 1 | 27 | **present** |
| Implementer, run 2 | 27 | **present** |
| Coordinator | 26 | absent |
| **This review** | **26** | **absent** |

Four observations, two each way, same commit, ID sets otherwise byte-identical. **That is the
master plan §6 signature, and this test now satisfies it by name.** Note the tell that makes it
more than a coincidence: it passes 1/1 in isolation, it is a *real concurrency* test
(`test_c3_real_concurrent_open_insert_translates_the_loser`), and a concurrency test is exactly
the thing whose outcome depends on suite-wide load rather than on the code. I did not
investigate further and did not touch it — outside the perimeter, and the implementer was right
to stop at evidence. **Recommendation: master plan §6 stops saying "unidentified" and names this
ID as the leading candidate with four observations behind it.** Confirming it is a task for its
own session, not a phase-3 fix.

**N-5 — P1's absence claim is true for its form, not for its class.** `(C10)` is the only
`C<n>` criterion reference in `app/beyo_manager/`. But `domain/users/serializers.py:195` carries
`# PRECEDENCE (criterion 13), asserted rather than incidental:` — the same defect class, spelled
out, from an earlier pipeline. Out of this perimeter and not phase 3's to fix. Recording it
because it means F-1's fix should be read as **establishing the convention** (`path:symbol`,
already the house style in four places) rather than patching two lines — and because the
project's own standing lesson is that when a blocker reveals a pattern you search for every
instance before writing the correction.

**N-6 — architecture graph: drift confirmed, counts moved, nothing repaired.** I confirmed both
drifted anchors by reading the files: the service symbol now spans **152–274**
(`async def get_task_price_scenario` at 152, closing `)` at 274) against the stored `149–273`,
and the phase-2 C1 table/test span is now **416–448** (`test_c1_status_matrix_has_twelve_exact_rows`)
against the stored `387–419`. Both match the implementer's report exactly.

`archgraph_status` at review time reads **187 nodes / 278 edges / 11 pending / staleNodeCount 1**,
revision `df61961d…` — where the implementer closed at 186 / 278 / 10 / 0, revision `2d76dab3…`.
The `+1 node` and `+1 pending` are attributable: `git diff .archgraph/architecture.yml` shows one
added node, `domain-purchase-api-sek-price-normalization`, which belongs to the **concurrent
owner change**, not to phase 3. Phase 3 recorded 0 graph mutations and that is correct. I make
**no claim** about the `staleNodeCount: 1`, only that it moved from 0; it is coordinator-owned
and I repaired nothing, reviewed nothing, promoted nothing.

**N-7 — verified correct in passing, so nobody re-raises it.** `can_commit` can be `true` while
`item_binding == "mismatched"`, because the F6 block only ever caught `"detached"` and the
nulling branch at `:241` does not touch `can_commit`. **This is deliberate and tested**:
`test_c9_non_bound_binding_governs_the_full_payload:629-632` asserts `can_commit is False` for
detached and `is True` for mismatched. F6's removal leaves both rows green and changes nothing
here. Not a finding.

**N-8 — the C1 teardown, confirmed on both halves P5 named.** The residue block sits **outside**
the `try/finally` and that is right: if the body fails, the `finally` still deletes everything,
and the test then fails on the body's own error rather than on a residue assertion that would
mask it. Charter rule 11½ is satisfied — cleanup is in the `finally`, not after the assertions.

**The four tables are the complete set this test writes.** Verified structurally rather than by
observation: the test adds only `Workspace`, `User`, `Item`, `ItemValuation`; `_scenario_objects()`
builds `Task`, `CostModelVersion`, `CostModelTerm`, `ProductionCostGroup` and
`ProductionCostBasisVersion` but **never adds them to the session** — they reach the code through
the monkeypatched `_load_task_and_item` / `_load_preview_inputs`, so no cascade can pull them in.
`get_task_price_scenario` is a pure read (every statement in it is a `select`). And
`grep -rn "listens_for\|event.listen" beyo_manager/models/` returns only two engine-level
`before/after_cursor_execute` logging hooks in `database.py:34,38` — **no ORM write listener, no
history or audit side-table, on any of the four**. Nothing else can have been written.

## 5. Carry-forward dispositions

| # | Item | Destination |
|---|---|---|
| N-1 | C3/C4 divide the rounding-mode duty; neither row pins it alone | Plan 3 Review log at fix-cycle fold; master plan lesson amended |
| N-2 | `collapse_terms`'s deleted-skip is guarded only by an integration row in another layer | **Phase 5** (or closeout sweep) — direct domain row, or a note at `price_scenario.py:71` |
| N-3 | C1's "reddened nothing before" is unrecorded | The phase 3 fix handoff, one sentence |
| N-4 | The drifting test has a name and four observations | **Master plan §6**, coordinator-owned. Confirmation is its own session |
| N-5 | `serializers.py:195` carries the same dangling-reference class | Owner backlog / next pipeline touching `domain/users/` |
| N-6 | Graph anchor drift on pending `ai_inferred` items; staleNodeCount 0 → 1 | **Coordinator**, existing pending-review queue |

## 6. Lessons for the plans

1. **"Record the decision" needs a named medium, or it defaults to the handoff — which
   archives.** Three of this phase's seven repairs were decisions rather than code, and the
   plan asked for each to be "recorded in the handoff with its reason." The handoff complied
   exactly, and two of the three are now invisible to the reader they were written for. **A
   criterion asking for a recorded decision should name where it lives after closeout** — code
   comment, master plan, or graph node — the way plan 3 §3 asked and C5/C6 then did not.
2. **A test's determinism aid is a mechanism, and rule 5 applies to it.** "Forcing a heap scan
   and a deterministic live-tuple order" is two adjectives standing in for a contract. One of
   the two does nothing, and one probe each would have shown which — the master plan's own
   *"compute both sides"* rule applied to the fixture instead of to the mutation. **When a
   fixture has to be strengthened before its ledger row is accepted, the strengthening is
   itself a claim that needs its own both-sides check.**
3. **A cross-reference from production code must resolve from a clean checkout with no pipeline
   documents present.** That is the testable form of the rule `force_task_ready` earned, and it
   rules out criterion IDs, round numbers and mutation nicknames in one sentence. The house
   convention (`path:symbol`) already satisfies it in four places.
4. **A comment at the head of a multi-predicate `WHERE` annotates the whole block to a
   skimmer.** Two of this project's rounds were spent on filters nobody asserted; scoping
   language ("this line only", "the three below are load-bearing") costs six words.
5. **Suite drift is worth naming, not just tolerating.** §6 has said "unidentified and
   inherited" across three pipelines. Two rounds of ordinary discipline — repeat and ID-diff —
   produced a named candidate with four observations. The rule that got there is already in the
   master plan; what was missing was recording the *ID* rather than the *count* each time.

## 7. Mutation-probe declaration

Every probe applied and reverted; all three files confirmed **byte-identical** to `ef55f6d` by
SHA-256 after the final revert:

| File | SHA-256 after revert | Matches |
|---|---|---|
| `get_task_price_scenario.py` | `6900297d3b3617bf10f36f796e78dbee91a303e33eb021667c37350407acc775` | implementer's ledger ✓ |
| `test_price_scenario_query.py` | `c0df857d04df631400c43210fae66e0bdae6483a88baa0e6224be35f5f666eda` | pre-probe baseline ✓ |
| `price_scenario.py` | `948a7a0f990ad409f26ff97a173fc0eeb2211970d0c9d5e7e1059277aba04542` | implementer's ledger ✓ |

Probes run:

1. `_current_valuation` — drop `superseded_at.is_(None)` (definition site). Focused file ×3.
2. Test file — both `SET LOCAL` statements removed (F-2 probe 3). Focused file ×3.
3. Test file — the two UPDATEs swapped (F-2 probe 4). Focused file ×3.
4. Test file — temporary `SHOW enable_indexscan` assertion after the residue block (leak check).
5. `round_half_even` — tie branch to half-up (N-1). Focused file ×1.
6. `collapse_terms` — `is_deleted` skip deleted (N-2). Focused file ×1, domain file ×1, **whole
   suite ×1, ID-diffed**.

`git status --porcelain --untracked-files=all` after all reverts shows **only** the three
concurrent owner-change paths — no probe residue.

**State side effects, all restored or benign:**

- `VACUUM (ANALYZE)` then `VACUUM (ANALYZE, FULL)` on `item_valuations` in the configured
  development database (`localhost:5433/beyo_manager`). Non-destructive: no row was inserted,
  updated or deleted by me. It rewrote that table's physical layout and refreshed its planner
  statistics — deliberate, since it was the durability half of P2. **Declared because the next
  perimeter reconstruction should know the heap was rewritten.**
- Row state verified after: `item_valuations` back to **1 live row** (its pre-probe count), and
  `select count(*) from workspaces where client_id like 'ws_price_chain%'` → **0**. The C1
  test's `try/finally` cleans up correctly on both the pass and the mutated-fail path.
- No Redis, no queue, no external service touched.

## 8. Full write perimeter

This session wrote exactly one file:

1. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_phase3_review_r1_handoff.md`

No code, no plan file, no master-plan tracker row, no Review log, no architecture-graph mutation
of any kind (status read only — no review, promotion, rejection, edit, maintenance or context
write attempted).
