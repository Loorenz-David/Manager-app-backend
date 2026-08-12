---
plan: phase 3
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-12
actor: Claude (plan-reviewer)
---

# Phase 3 reviewer handoff — canonical calculator (review r1, full checklist)

**Verdict: CHANGES_REQUESTED** — 2 blocking, 3 should-fix, 7 notes, 4 lessons.

The calculator itself is substantially correct and was independently re-derived, not
taken on the log's word. The perimeter is exact, the arithmetic is right at every one
of the ten seeded Q-site cells, and all nine declared mutations bite at their named
sites when re-run from a clean checkout. Two things do not hold: one contract
violation the phase's own C9 criterion is structurally unable to see (B1), and one
missing C6 cell whose absence lets the single most dangerous defect in a money domain
— an absent input silently becoming `0` — pass the entire 54-test suite (B2). Both
fixes are small; neither is a design problem.

## ⚠ OWNER DECISIONS REQUIRED (3)

### Card 1 — What should happen when a stored evaluation no longer re-derives?

**Question.** When re-derivation finds a stored evaluation disagreeing with its own
snapshot, should that surface to the user as a validation error, or be handled as an
internal integrity alarm?

**Story.** Six months from now a manager opens an item's economics from last March.
Behind the scenes the app recomputes that evaluation from its own snapshot and finds
the stored budget says 7 591 kr while the snapshot's own numbers say 7 592 kr —
something wrote a bad row. Today the manager would see a red validation message on a
page they were only reading, as if they had typed something wrong. Nobody is
notified, and the manager learns to click past it.

**Branches.** *User-facing validation error* — the manager is blamed for a data bug,
and nobody who can fix it hears about it. *Internal integrity alarm* — the read still
renders, the mismatch is logged/escalated for you, and the manager is not accused of
anything.

**Recommendation.** Internal integrity alarm — a snapshot disagreeing with itself is
never something the person reading the page did.

**On silence.** The gate holds; the identity stays unregistered and phase 3 cannot
approve. No guess is made.

**Trace.** Finding S2; intention §6A.11, §6A.10; master plan §6.4, §10 error surface.

### Card 2 — Should the calculator reject negative term values and zero rates?

**Question.** Keep the two extra guards the implementer added beyond the plan, or drop
them?

**Story.** A manager sets up a cost model and types `-5` into a percentage term,
meaning "give 5 % back". Today the calculator refuses the whole evaluation with an
invalid-shape error. That is almost certainly what you want — a negative allocation
has no meaning in this domain — but nobody ever decided it, and no test holds it, so
the next person to touch that file can delete it and every test stays green.

**Branches.** *Absorb into the intention* — the rule becomes real, gets test rows, and
survives. *Drop them* — the calculator stays exactly as narrow as the plan said, and
the schema alone guards ranges.

**Recommendation.** Absorb — §6A.4's table already says `≥ 0`, so this codifies an
existing rule rather than inventing one.

**On silence.** The gate holds; the guards stay in place but untested and unowned.

**Trace.** Notes N3, N4; intention §6A.4, §6A.6; plan phase-3 Notes.

### Card 3 — Adjudicate the pending architecture-graph node.

**Question.** Promote `domain-item-economics` now, or hold it until the phase-3 fix
cycle lands?

**Story.** The graph has one new inferred node describing item economics as its own
domain. Everything it *says* is true. But its evidence points at line ranges that are
slightly off — one range stops mid-function, another starts inside the wrong function
— and the coming fix will shift every line number in that file anyway. Promoting now
means confirming anchors you will have to correct again next week.

**Branches.** *Promote now* — the node is confirmed, then immediately drifts. *Hold* —
one adjudication instead of two, against final line numbers.

**Recommendation.** Hold — re-anchor to `1–26`, `137–219`, `371–426` after the fix and
adjudicate once.

**On silence.** The item stays pending; nothing is promoted, rejected or edited.

**Trace.** Probe P3-7; charter §8 standing flow; graph revision `671fd92a…`.

## Probe results

**P3-1 — mutations, sampled independently: PASS (exceeded).** Re-run in a disposable
git worktree at `2a860b2` (`git worktree add --detach`), each mutation applied in
isolation with `__pycache__` cleared, reverted and sha256-verified between runs. I ran
**all nine** declared mutations, not the four required. Every one reddens exactly its
named assertion set and nothing else:

| Mutation | Result | Reddened |
|---|---|---|
| M-Q1 Q1 call site → HALF_UP | 1 failed / 53 passed | `tie_table[Q1-25-24]` |
| M-Q2 Q2 call site → HALF_UP | 1 failed / 53 passed | `tie_table[Q2-actual1-expected1]` |
| M-Q3 Q3 call site → HALF_UP | 1 failed / 53 passed | `tie_table[Q3-actual2-expected2]` |
| M-Q4 delete Q4 `.quantize(…)` | 3 failed / 51 passed | both Q4 exactness rows + the variance triple |
| M-Q5 Q5 call site → HALF_UP | 1 failed / 53 passed | `tie_table[Q5-25-24]` |
| C6 delete shared `_guard_type` body | 14 failed / 40 passed | the 14 guard rows (matches the declaration) |
| C7 `rederive` reads `production_cost_basis_version_id` | 1 failed / 53 passed | the FK tripwire row |
| C9(a) drop explicit `rounding=` at Q1 | 1 failed / 53 passed | the ambient-context row |
| C9(b) remove Q3 `localcontext()` | 1 failed / 53 passed | the ambient-context row |

Declared hashes confirmed byte-identical before and after every probe: calculator
`088e6514…845e90`, tests `9096962c…733fd1`. Worktree removed; main tree clean.

**P3-2 — seeded fixtures verbatim: PASS.** Every C2 cell and C5's triple uses the
plan's seeded values with the plan's exact expected outputs; no test adjusted a seeded
value. I re-computed six by hand (more than the three required): Q1 `4000×15.000/100
= 600`; Q1 tie `4900×0.500/100 = 24.500 → 24` (HALF_UP would give 25); Q2 tie
`24 000 003 / 60 000 = 400.00005 → 400.0000`; Q3 tie `1/0.0128 = 78.125 → 78.12`;
Q5 drift `20/60 × 400.0000 = 133.33… → 133` (Q4's rounded 0.33 would give 132); and
C5's full triple — `100000/100.5 = 995.0248… → 995.02`, `12181/60 = 203.016… →
203.02`, `12181 × 100.5/60 = 20403.175 → 20403`, `var_min = 792.00`, `var_cost =
79597`, `792.00 × 100.5000 = 79596.000000`, difference **exactly 1**, both asserted
exactly and neither reconciled.

**P3-3 — C6 totality: FAIL (1 of 25 cells missing).** Counting rows against cells:
correct-type 4/4, `float` 3/3, `bool` 3/3, `Decimal` 3/3, `int` 3/3, `str` 4/4,
`None` user-supplied 1/1, `None` system-supplied **3 of 4** — the money cell has no
row. See B2. `bool` is explicitly rejected for all three int-spec classes ✓; enum
value-string → `TypeError` ✓; `None` user-supplied → named identity ✓.

**P3-4 — purity + localcontext coverage: purity PASS, localcontext FAIL.** No I/O
anywhere in `calculator.py`: imports are `decimal`, `typing`,
`domain.item_economics.enums`, `domain.items.enums`, `errors.validation` only — zero
matches for `sqlalchemy|session|requests|httpx|open(|os.|redis|await` (P-F,
`08_domain`). Reading every public function rather than trusting C9: thirteen of
fifteen are clean (Q1–Q5 wrapped; `calculate_production_budget` and
`calculate_variance_cost_minor` are pure `int`; `validate_currency_equality` and
`rederive` do comparisons only). **Two are not** — see B1.

**P3-5 — rederive: PASS.** Reads only the §6A.11 closed set; the tripwire covers all
five excluded fields and `mock.patch.object` with a raising `property` genuinely bites
(a data descriptor wins over the instance `__dict__` even on an already-constructed
ORM object — verified by the C7 mutation). D5 adopted: each term's `amount_minor` is
re-derived and compared, not summed. `REDERIVE_SKIPPED` is the single named constant
returned on version mismatch, before any other field is read; there is no second path
returning bare `None`.

**P3-6 — declared test change: PASS, verified positively.** The handoff says the C9
precision fixture "was strengthened". I tested the counterfactual rather than the
claim: substituting the plan's *other* seeded Q3 fixture (`budget=1, rate=0.0128`)
into the C9 test and then applying the C9(b) mutation gives **1 passed** — the weak
fixture would not have caught it — while the shipped fixture (`40 000 000, 400.0000`)
gives **1 failed**. The change strengthened the criterion; it did not weaken it.

**P3-7 — graph delta: reported, not adjudicated.** See card 3 and the Review log.
Status `671fd92a…` matches the handoff; 1 pending item; 126 nodes / 161 edges; zero
diagnostics; zero stale nodes. I read `calculator.py` at the cited spans **before**
opening the stored claim. All three claims are ACCURATE. Anchors: evidence 1
(`1–26`) exact; evidence 2 (`137–212`) starts at `calculate_percentage_term_amount`
not the named `calculate_term_amount`, and ends mid-body of `calculate_term_amounts`,
excluding the duplicate-purchase guard (`:215-218`) that S8 made load-bearing;
evidence 3 is stored as **`365–425`**, which is *not* the `371–425` the implementer
handoff and Review log declare — it opens inside `validate_currency_equality`'s list
comprehension and stops one line before `rederive`'s `return` (`:426`).
Recommendation: **hold**, re-anchor to `1–26` / `137–219` / `371–426` after the fix
cycle, adjudicate once. The declared-vs-stored span mismatch is worth one line back to
the implementer: the handoff's graph declaration was not accurate.

**P3-8 — API report: PASS with a note.** All 16 §6.5 names are present; nothing is
missing. Extra public names exist: `EvaluationSnapshot`, `TermSnapshot` (the
Protocols) and the re-exported `ROUND_HALF_EVEN`; with no `__all__`, `import *` also
re-exports `Decimal`, `Sequence`, `ValidationError` and friends. See N2.

## Scope fence and suite

Scope fence **clean**: the checkpoint touches exactly four files — `calculator.py`,
`test_calculator.py`, the master-plan tracker row, the plan's Review log. No service,
command, router, schema or persistence; no phase-2 model edits (the `Mapped[float]`
annotations correctly stay wrong until phase 9); no `EconomicsStatusEnum` logic; no
request-layer parse. Working tree clean at review start and end.

Suite re-run by me from `backend/app` with `PYTHONPATH=. pytest -m 'not e2e'`:
**1738 passed / 23 failed / 1 deselected** in 60s — matching the implementer exactly,
`+54` over the 1684 baseline, which is precisely the calculator suite. Zero
connectivity noise (0 matches for connection-refused / `OperationalError`), so the run
is admissible as evidence per §10. The 23 failure IDs `diff` **empty** against the
phase-1 Review log's routed 23-item list — byte-identical. N14's Shopify flake did not
fire; no re-run was needed. Focused suite: 54 passed. `ruff check` on both files: clean.

## Findings

### Blocking

**B1 — Decimal arithmetic outside `localcontext()` in two public functions.**
`calculate_remaining_worker_minutes` (`calculator.py:312`) computes `allowed - actual`
in the ambient context; `calculate_variance_worker_minutes` (`:335`) delegates to it.
Authority: intention **§6A.2 as amended round 8 (R8-2)** — the module "runs its
arithmetic inside a `decimal.localcontext()`", so that independence from the global
context is "realized by construction, not by hope"; and **§6A.8** ("exact 2 dp
subtraction"). Verified: under `getcontext().prec = 6`,
`calculate_remaining_worker_minutes(Decimal("100000.00"), Decimal("0.33"))` returns
`99999.7` instead of `99999.67`, and `calculate_variance_worker_minutes` returns the
same wrong value, while `calculate_percent_consumed` (wrapped) stays `20.40`. C9 is
structurally blind to this because it enumerates only Q1–Q5 — the precise hole P3-4
was written to catch. **Correction:** wrap both in
`with localcontext() as context: context.prec = 50`, as at the five Q sites; and
extend C9's baseline/hostile tuples to **every** public function performing Decimal
arithmetic (`calculate_remaining_worker_minutes`, `calculate_variance_worker_minutes`,
`calculate_percent_consumed`). Named mutation for the new row: "remove the
`localcontext()` wrapper from `calculate_remaining_worker_minutes`" must redden it.

**B2 — C6's `money × None (system-supplied)` cell is missing; the R-9 inferred zero
survives the whole suite.** C6 is declared TOTAL over input class × arriving type.
Every money guard row (`test_calculator.py:240-246`) drives `expected_sale_price_minor`
— a *user-supplied* field carrying `required_identity` — so its `None` row asserts
`ITEM_COST_EXPECTED_PRICE_REQUIRED`, and the system-supplied branch of `_require_money`
(`calculator.py:72-75`) is never exercised by any test. Authority: plan **C6**, master
plan §9 **P-B** (R-9: absent input ⇒ named error or `null` — **never 0**), charter
rule 2. **Verified by mutation:** replacing `raise _type_error(field, "an int in minor
units", value)` at `calculator.py:75` with `return 0` — exactly the inferred zero P-B
exists to forbid — leaves **54/54 green**. C6's own declared mutation does not reach
it: deleting `_guard_type`'s body reddens 14 rows, but both the money and rate `None`
paths return before `_guard_type` is ever called. The production code is *correct*
today; it simply has no arbiter. **Correction:** add the cell against a
system-supplied money parameter (e.g. `calculate_variance_cost_minor(None, 100)` or
`calculate_cost_per_worker_minute(None, …)`), and per charter rule 11 name the
mutation it must survive: "`_require_money`'s system-supplied `None` branch returns 0".

### Should-fix

**S1 — C8's message assertion is a disjunction; 2 of 3 rows never check the second
currency is named.** `test_calculator.py:303`:
`assert basis.value in message or model.value in message`. Plan C8 requires each row
to assert "the presence of **both** currency values". **Verified by mutation:**
dropping the right-hand value from the message
(`f"{left_name}={left.value} differs from {right_name}"`) reddens only **1 of 3**
rows — rows 2 and 3 pass because `basis.value` is `swedish_krona`, which the surviving
left-hand text still contains. The companion `assert pair in message` (`:301`) is
likewise trivially satisfied: every mismatch message enumerates a pair beginning with
`valuation`. Authority: plan C8; charter rule 2 (an assertion accepting a disjunction
hides mislabeling). **Correction:** per row, assert both distinct currency values by
name and the exact failing-pair label.

**S2 — `ITEM_COST_SNAPSHOT_MISMATCH` is not in the §6.4 registry.** Raised at
`calculator.py:397, 413, 418, 425`. Master plan §6.4's identity list is marked FINAL
and registry-authored; this identity appears in neither the intention nor the master
plan. §6A.11 specifies `rederive` only as returning `(rate, budget, allowed)`, and
C7/D5 mandate the comparison without pinning what a mismatch *does* — so the
implementer had to author an outcome, which is a plan gap (lesson L4) as much as a
code finding. Raising is a defensible reading, but an unregistered identity should not
ship, and a snapshot-integrity failure will travel the §10 `run_service` boundary as a
user-facing `ValidationError`. **Correction:** register the identity in §6.4
(coordinator, upstream) or change the carrier — see **owner card 1**.

**S3 — C9's version-constant row under-asserts its criterion.**
`test_calculator.py:388-391` asserts `CALCULATION_VERSION == 1`, `"§6A.10" in
calculator.__doc__` and `"rounding" in ….lower()`. C9 requires the docstring to name
§6A.10's **bump/never-bump lists**; no never-bump token (`renames`, `widening`, `API
shape`, `documentation`) is asserted at all, and the assertion reads the *module*
docstring while the constant carries its own (`calculator.py:21-23`). **Correction:**
assert a distinctive token from each list, against the docstring the criterion means.

### Notes

- **N1** — `test_purchase_term_missing_purchase_cost_varies_only_the_purchase_snapshot_field`
  (`:148-156`) and `test_purchase_cost_none_is_a_named_user_input_error` (`:261-269`)
  have **byte-identical bodies**; one of the 54 is dead weight. → next touch.
- **N2** — public surface exceeds §6.5's 16 names: `EvaluationSnapshot`,
  `TermSnapshot`, re-exported `ROUND_HALF_EVEN`; no `__all__`. The two Protocols are
  arguably contract surface phases 7/8 will type against. → coordinator: fold into
  §6.5 or add `__all__`.
- **N3** — `_term_shape` (`:131-134`) rejects negative `percent_value` /
  `fixed_amount_minor` with `ITEM_COST_TERM_SHAPE_INVALID`. Consistent with §6A.4's
  `≥ 0`, but beyond the plan's "re-validates presence/type, not range" note, and
  **both branches are untested** (verified live: both raise). → **owner card 2**.
- **N4** — `calculate_allowed_worker_minutes` (`:269-272`) raises
  `ITEM_COST_RATE_UNDERFLOW` on a zero rate; §6A.6 sites that identity at Q2 /
  basis-version creation. Sensible defence, unregistered at this site, untested. →
  **owner card 2**.
- **N5** — `_require_rate`'s `required=False` parameter (`:86-90`) has no caller and
  its `-> Decimal` annotation is false on that path (returns `None`). Charter rule 4.
  → next touch.
- **N6** — C2's fixtures are evaluated at **collection time** inside the `parametrize`
  argument lists (`:171-176, 186-189`). The mutations still bite, but a mutation that
  makes any of those calls raise becomes a whole-module collection error rather than a
  targeted failure, and the parametrize ids shift with the computed value
  (`[Q1-24-24]` → `[Q1-25-24]` under M-Q1) — which makes per-row mutation declarations
  hard to read across rounds. → next touch.
- **N7** (plan-level, passing glance) — C2's Q3 exactness cell claims it "asserts Q3
  consumes the persisted rate", but in phase 3 the rate arrives as a parameter, so
  nothing distinguishes a caller passing the persisted value from one passing the raw.
  The row is conformant to the letter and cannot bite. The real arbiter belongs where
  the call is wired. → **phase 4/5**.

## Lessons for the plans

- **L1** — C9 scoped a **module-wide** construction rule (§6A.2) to "every Q1–Q5
  output". A criterion proving a module-wide rule enumerates over the module's public
  surface, not over the mechanism list that motivated the rule. (Earned: B1.)
- **L2** — C6's cells name an input *class* and an arriving *type*, but not **which
  parameter** the row drives. Every money row happened to use a user-supplied
  parameter, so half a cell went untested while the matrix looked complete. Extends
  P-M's companion from "which field of the shared fixture" to "which parameter".
  (Earned: B2.)
- **L3** — charter rule 2's no-disjunction clause needs restating for criteria that
  assert **message content**, not only expected outcomes: "the presence of both
  values" was satisfiable by an `or`. (Earned: S1.)
- **L4** — a criterion mandating a comparison names the **outcome and its error
  identity**, or the implementer authors one and it lands unregistered. (Earned: S2.)

## Carry-forward dispositions

Not applicable — this is a CHANGES_REQUESTED verdict, so no notes are being carried
past an approval. Routing intent for the coordinator: N1, N5, N6 → next touch of these
files; N2 → §6.5 registry decision; N3, N4 → owner card 2 then intention; N7 →
phase 4/5 criteria; L1–L4 → plans and §9.

## Mutation-probe declaration

All probing was done in a **disposable git worktree** at `2a860b2`
(`git worktree add --detach`), never in the main tree.

- Files touched by probes, each applied and reverted, sha256-verified byte-identical
  after every single probe:
  - `app/beyo_manager/domain/item_economics/calculator.py` — 15 mutations total (the
    9 declared, re-run independently; plus 6 reviewer-authored: the S1 currency-message
    truncation, the B2 inferred-zero decider, and repeat isolation runs).
    Final sha256 `088e6514ee3552f433b5aa28f082932ff98273e6507a2bfd82bff67ee1845e90` ✓
  - `app/tests/unit/domain/item_economics/test_calculator.py` — 1 mutation (the P3-6
    counterfactual: C9's Q3 row swapped for the plan's other seeded fixture).
    Final sha256 `9096962c31e932fdda11491204c501ecf3b6edadcaae3128f97f098203733fd1` ✓
- One non-source file was created inside the worktree only: `app/.env`, copied from the
  main tree because it is gitignored and `conftest.py` cannot import settings without
  it. It never existed in the main tree's diff and went away with the worktree.
- Worktree removed (`git worktree remove --force`); `git worktree list` shows only the
  main tree. Main working tree verified clean at review end, both file hashes unchanged.
- **Database/state side effects: none.** Every probe ran the pure unit module only; no
  migrations, no DDL, no writes. The configured development database was never written
  to and remains at head. Architecture graph: **read-only** — `archgraph_status`,
  `archgraph_list_pending_reviews`, `archgraph_get_review_item` only. Nothing was
  promoted, rejected, edited, deprecated or removed; revision unchanged at
  `671fd92a560fbaffda67e74f21eff8128c55cacfae807d98ab27fdf6e586319b`.

## Full write perimeter

- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_3_canonical_calculator.md`
  — appended the reviewer r1 Review log entry (append-only; implementer entry untouched).
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
  — phase-3 tracker row only: state `IMPLEMENTED` → `CHANGES_REQUESTED`, actor extended
  to `Codex; reviewer r1 (Claude)`, verdict summary appended. Prior actor stamps and all
  other rows preserved verbatim.
- This handoff file.
- **No production or test code was modified.** All probe edits were made in the
  disposable worktree and reverted there before it was removed.
