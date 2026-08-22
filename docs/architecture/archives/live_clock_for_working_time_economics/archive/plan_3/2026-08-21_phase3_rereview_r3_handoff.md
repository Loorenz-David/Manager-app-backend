---
plan: 3
role: review
round: 3
verdict: APPROVED
date: 2026-08-21
actor: Opus 5 (re-review r3)
---

# Re-review r3 handoff — plan 3, `live_clock_for_working_time_economics`

**Verdict: APPROVED — 0 blocking, 0 should-fix, 3 notes.** Fix r2 closes both should-fix
findings from review r1, and it closes them on the merits rather than by restating them.
C6c is real, non-vacuous and non-redundant; C6b's re-specification gives its `null`
exactly one sufficient cause and its comment now claims only what the fixture shows. The
production code was untouched across the whole cycle and is byte-identical to what
review r1 confirmed correct. All three notes are documentation drift in coordination
artifacts, correctable in the coordinator's fold without a fix cycle.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing on this round needs the owner. P5's database question resolves inside an owner
decision already taken (master §6's ⛔ GATE, step 1: "phase 3 runs to APPROVED on the
current serial runner") — re-asking it would relitigate a settled call. The recommendation
it produces is a coordinator-level correction to how the approval baseline is *stated*,
recorded under Lessons below.

## 1. Gate check

| Condition | Result |
|---|---|
| `master_plan.md` §3 shows phase 3 at REVIEWING (re-review r3) | ✅ holds |
| HEAD is `874f02d` | ⚠ **HEAD is `808eead`** — four coordinator document commits sit on top of the checkpoint (`766bdec`, `a8371cb`, `9a12b9b`, `808eead`). `git diff 874f02d HEAD` touches exactly three files, all under the implementation folder; `git diff 874f02d HEAD -- app/` is **empty**. The gate's substance holds; the prompt's SHA was stale by four doc commits. Recorded, not a finding. |
| `git diff 5b8329b 874f02d -- app/beyo_manager/` is empty | ✅ empty — no production change across the fix cycle |
| Foreign stream present and not mine to touch | ✅ handled per §3 of the prompt; see N9 for one item the stream's recorded perimeter does not cover |

**Tree identity for every evidence record below:** HEAD `808eead`, tree **dirty** (foreign
stream), `git diff HEAD -- app/` digest
`f0722645dc56c12da5b7147482ff8283b9566521d72dd8004ba3e0ea18d079c6` — **unchanged across
every probe and every measurement in this round**.

⚠ **That digest was valid for the whole measuring window and then moved, without my
touching anything.** After the last probe was reverted and while these artifacts were being
written, the shopify stream modified a further file —
`app/tests/unit/services/infra/shopify/test_product_sync_client.py` — taking the `app/`
digest to `020e77c9f83027258aef20c53665b9d9fa87042befde6a3eddf5f5c858d61730`. **No phase-3
file moved with it**, which is the claim that actually matters and is proven per-file rather
than by the aggregate digest:

```
d9160f92…  division_serializers.py       (also the coordinator's fix-r2 digest — revert corroborated from a second session)
65558c51…  serializers.py
16cb98a9…  calculator.py
90da6486…  test_phase2_live_surfaces.py
```

This is the dirty-tree identity scheme doing exactly its job, and it is the concrete reason
an aggregate `app/`-scoped digest is the wrong instrument while an uncommitted foreign
stream is live: it conflates "my probe leaked" with "the owner saved a file". **Per-file
digests over the reviewed perimeter are what a round in this state should record.**

The round spent no L4 run. Every hypothesis was L1-scoped over the two phase files, which
also kept the round clear of the foreign surface entirely (the +17 shopify tests never
entered a measurement).

## 2. Findings

### Blocking (0)

None.

### Should-fix (0)

None.

### Notes (3)

**N7 — `planning/intention.md` §5.3A's S1 correction rests on a premise fix r2 deleted.**
The block reads: *"Row (b) does not redden on that edit and never could: **its fixture sets
the current evaluation's `allowed_worker_minutes = 0.00`**, so its payload's `status` is
itself `infeasible`…"*. After fix r2, C6b sets that allowance to `20.00` and asserts
`status == "ok"` on both faces. The **conclusion is still correct** — row (a) is the
status-blanking guard, and C6b still does not redden on that edit — but for the opposite
reason: status-blanking never fires on C6b now, rather than firing and coincidentally
matching. The live risk is concrete: a reader reconciling the intention against the tree
finds the sentence false and may "restore" the `0.00`, which would undo exactly what S1
bought. `plans/plan_3.md` §5 C6 carries the same premise but is safe, because that block
ends with the order *"C6b's fixture must be re-specified with a positive current
allowance"* and therefore reads as history; §5.3A carries no such clause and reads as
standing contract text. **Correction:** one clause in §5.3A — note that the fixture was
subsequently re-specified and that row (b)'s immunity now follows from its `ok` status.
Authority: charter §5 (a comment asserting a property is a claim) and the shelf-life rule
the coordinator added to C5 at this same consumption.

**N8 — the "live `120.00`" figure attached to C6c's non-vacuity is wrong; the measured
value is `170.00`.** Both `master_plan.md` §3's current row and `plans/plan_3.md` §7's
fix-r2 consumption entry justify C6c as *"non-vacuous against a live `120.00`"*. C6c
serves at `now`, i.e. the **open** state, so the live percent is `34.00 / 20.00 = 170.00`
on both surfaces — `120.00` is the **pre-open** value, which C6c never serves. Measured
directly (probe D below): `('170.00', '170.00')`. **Non-vacuity is unaffected** —
`150.00 ≠ 170.00` either way — but the number is the kind a later round cites without
re-deriving, and the pipeline has been bitten four times by exactly that. **Correction:**
`170.00` in both places.

**N9 — the foreign stream is writing the architecture graph, and stream 3's recorded
perimeter does not cover it.** `master_plan.md` §7 lists stream 3 as two `app/beyo_manager`
files plus two untracked paths, and states that anything outside the lists is a finding.
At **10:16:07 local today** — about one minute into this session and one minute after the
last coordinator doc commit — `.archgraph/architecture.yml` gained an uncommitted delta:
node `command-shopify-backfill-expected-sold-price` (`origin: ai_inferred`, confidence
`0.9`) plus one `calls` edge to `command-item-economics-set-item-valuation`, with evidence
spans pointing at `app/scripts/shopify/backfill_from_shopify.py` and
`app/scripts/shopify/fields.py`. `.archgraph/.internal/` moved with it. It is
unambiguously the shopify stream's own work, **not this pipeline's and not a probe of
mine** — this session made no `archgraph_*` call of any kind, and my probes are declared
in §4 below.

**A second omission surfaced an hour later, and it is the more consequential of the two.**
While these artifacts were being written the same stream modified
`app/tests/unit/services/infra/shopify/test_product_sync_client.py` — a **tracked, existing
test file**, also absent from stream 3's perimeter. §7 currently reasons about this stream
as *additive*: "the failing-ID set is the stable instrument here; additions that pass do not
touch it." That reasoning holds for the untracked `test_backfill_from_shopify_fields.py`
and its 17 new tests. It does **not** hold for edits to an existing test file, which can
move the failing-ID set in either direction — and the enumerated 26-ID baseline already
contains a shopify row (`test_create_shopify_metafield_preferences.py`) with a shopify flake
beside it. So the instrument §7 declares stable is only stable against the half of this
stream §7 happened to see.

Three consequences: (1) stream 3's perimeter in §7 should name `.archgraph/architecture.yml`,
`.archgraph/.internal/` and `app/tests/unit/services/infra/shopify/`, or the next perimeter
check raises them as automatic findings; (2) the "additions only" claim must be narrowed —
**this stream can move the failing-ID set**, so the phase-4 gate cannot treat an unchanged
ID set as self-evident while the stream is uncommitted; (3) the graph delta adds to the
owner-adjudication backlog master §6 already flags as having grown silently, so **phase 4's
delta will land on a dirtier graph than the 9-pending/2-stale reading** — re-measure at that
point, never cite. Nothing here was touched, per the standing rule that agents never
promote, reject or edit review items.

## 3. Probes — what was asked, what was measured

### P1 — is C6c real?

**Non-vacuous: yes, measured.** Frozen `150.00` against a live `170.00` on the same
payload (probe D). The row's two assertions cross **two distinct producers**, not one —
`division_serializers.py:serialize_task_production_time` → `_serialize_production_time_final`
for E-P, and `serializers.py:serialize_task_budget_status` → `_serialize_result` for E-B —
and the fix-r2 ledger already shows each site's clamp mutation reddening it independently.

**Non-redundant: yes, and this is the sharper answer.** Probe B applied an implementation
nobody has run — *blank the frozen percent whenever the stored `variance` is negative* —
at the E-P site. Result: **1 failed / 34 passed**, the single red being **C6c**. C6b stays
green, because that implementation returns exactly the `null` C6b asserts. So C6b cannot
substitute for C6c at any distance: the two rows partition the negative-variance space at
the zero-allowance boundary, and only C6c holds the half where a percentage still exists.
That is precisely the wrong implementation review r1's S2 said the repository could not
see, and it is now visible.

**Could one wrong implementation satisfy C6c and its neighbours?** Not among the shapes
tried: the clamp (fix r2, both sites), the positive-fallback denominator (fix r2, both
sites), status-blanking (fix r2, both sites), the `actual`-alone denominator (C5, both
sites), variance-sign blanking (probe B) and argument transposition (probes A1/A2) each
leave at least one row red, and no two of them are killed by the same single row.

### P2 — the region enumeration closes

Walking the frozen percent's full output space under N-4 (`allowed_recon = actual +
variance`, `percent = actual / allowed_recon × 100`):

| region | reachable? | guarded by |
|---|---|---|
| `allowed_recon ≤ 0` → `null` | yes (zero **and** negative; both take the same branch) | **C6b** at exactly `0.00` |
| `0 < percent < 100` | yes | **C3** (`80.00`), **C6a** (`15.00`), goldens (`15.00`), `test_c17` (`20.00`) |
| `percent == 100.00` exactly | yes | **C1**, **C2**, **C4b**, **C4c** — four exact literals pin the boundary |
| `percent > 100` (OD-10's over-budget premise row) | yes | **C6c** (`150.00`) — the region review r1 found at ∅/∅ |
| `percent < 0` | **unreachable** | `actual_worker_minutes` is `calculate_actual_worker_minutes(actual_worker_seconds)` — a non-negative seconds count divided by 60 — and its single writer is `process_item_cost_result.py`. With a positive denominator the output range is `[0, ∞)`. |

**The `≤ 0` boundary is discriminated at exactly zero, not merely by sign — measured.**
Probe C weakened `calculate_percent_consumed`'s guard from `allowed <= 0` to `allowed < 0`:
**2 failed / 33 passed**, reddening **C6b** (the frozen side, `allowed_recon` exactly
`0.00`) and **C6a** (the live side, current allowance `0.00`). So the enumeration does not
merely cover the regions, it pins the inequality that separates two of them.

**The enumeration closes.** OD-10's premise table names three regions; all three are now
guarded by an exact literal, the `100.00` boundary between two of them is pinned four
times over, and the fourth conceivable region is unreachable by construction rather than
untested. §5B's new corollary is satisfied.

### P3 — C6b proves what its comment claims

The comment says the `null` is undefined *"solely because the frozen basis is
non-positive"*. Every competing cause is closed on the fixture as built:

- **status** — `production["status"] == "ok"` and `worker_payload["status"] == "ok"` are
  asserted on both faces, so a status-blanking implementation cannot produce this `null`;
- **absent result** — `assert result is not None` precedes the mutation;
- **a fallback denominator** — produces a number, not `null` (fix r2 measured it red at
  both sites);
- **the frozen basis itself** — `15.00 + (−15.00) = 0.00`, and probe C shows the row bites
  on the exact-zero boundary rather than on sign.

The claim holds. The S1 inversion is gone from all three documents that carried it —
`planning/intention.md` §5.3A, `plans/plan_3.md` §5 C6, `master_plan.md` §3 (inline in the
PROMPT_READY row, plus a correct restatement in the current row) — subject to **N7** on
§5.3A's now-stale premise.

### P4 — the fix cycle's blast radius is empty

C6b's re-specification changes two values inside its own test body. Both live on
`db_session`-scoped objects, so nothing leaks to another row. The line
`values[10].allowed_worker_minutes = Decimal("20.00")` restates the value
`_make_live_fixture` already sets — not dead scaffolding but a defensive pin: if the shared
fixture's allowance moves later, C6b and C6c hold their meaning instead of silently
changing region.

No row's expected value now coincides with a value it exists to tell apart:

| row | frozen (asserted) | live on the same payload | distinct? |
|---|---|---|---|
| C6b | `null` | `170.00` | ✅ |
| C6c | `150.00` | `170.00` | ✅ |
| C6a | `15.00` | `null` (current allowance `0.00`) | ✅ |
| C3 | `80.00` (`before` and `after`) | `120.00` → `80.00` | ✅ via `before`; N1's added assertion is what makes the live percent visibly *move* rather than merely land |

A regression run over both phase files at the reviewed tree is **35 passed / 1 deselected**.

### P5 — is a development-database baseline acceptable evidence to approve on?

**Yes for this phase, with one correction to how the baseline is published. No owner card.**

1. **The owner has already ruled on the sequencing half.** Master §6's ⛔ GATE, step 1:
   *"Phase 3 runs to APPROVED on the current serial runner — never change the runner
   mid-phase."* Holding phase 3's gate for the test-database work would invert a decision
   taken five days into this pipeline for stated reasons.
2. **The development database is currently the *more* faithful environment, not the less.**
   It is at head with the full schema; `app_test` is stamped `67cfba8fcb2d` with 96 tables
   and lacks `cost_model_versions` and `item_cost_results` outright — the phase's own tests
   cannot run there at all. Measuring on `app_test` today would produce collection errors,
   not better evidence.
3. **What actually carries this phase is DB-independent in substance.** The approval rests
   on per-row mutation bites over serializer arithmetic against ORM objects. Those bites
   would be identical on any database carrying the schema; the database identity determines
   only *which inherited tests fail*, and the enumerated 26 contains nothing in
   `item_economics`.
4. **The real exposure is provenance, and it is one line wide.** `26 / 2487 / 1` is a
   *count* taken against a mutable development database that accumulates residue and is
   shared with manual work — and, as of today, against a working tree carrying an
   uncommitted foreign stream worth +17 collected tests. The durable half is the
   **enumerated failure-ID set**, stable across 12+ runs and `comm`-diffed empty in both
   directions at every stamp of this phase.

**Recommendation:** approve now; and at the approval gate, publish the baseline as
*failure-ID set + tree identity (SHA + dirty-diff digest) + **database identity***, with
the count explicitly subordinate. Master §7's "Published approval baselines" table records
neither the database nor a dirty-tree digest today, and phases 1 and 2 are already
published without them. The re-enumeration on a correctly migrated test database is
already owned by the phase-4 gate (§6), where charter rule 7's Alembic transaction trap
must be checked by asserting DDL rather than the exit code.

## 4. Mutation-probe declaration

Five probes, each applied and reverted, each verified byte-identical by SHA-256 against
the digest taken before the round began.

| # | File touched | Mutation | Result over both phase files |
|---|---|---|---|
| A1 | `app/beyo_manager/domain/item_economics/division_serializers.py` | **argument transposition** — swap the two arguments to `calculate_percent_consumed` at the E-P reconstruction site | **5 failed / 30 passed / 1 deselected** — `test_c3`, `test_c6a`, `test_c6b`, `test_c6c`, `test_c17` |
| A2 | `app/beyo_manager/domain/item_economics/serializers.py` | same transposition at the E-B reconstruction site | **4 failed / 31 passed / 1 deselected** — the same four minus `test_c17` |
| B | `app/beyo_manager/domain/item_economics/division_serializers.py` | **variance-sign blanking** — return `None` whenever `result.variance_worker_minutes < 0`, E-P site | **1 failed / 34 passed / 1 deselected** — `test_c6c` alone; `test_c6b` green |
| C | `app/beyo_manager/domain/item_economics/calculator.py` | **zero-boundary weakening** — `calculate_percent_consumed`'s guard from `allowed <= 0` to `allowed < 0` | **2 failed / 33 passed / 1 deselected** — `test_c6b` (frozen side), `test_c6a` (live side) |
| D | `app/tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py` | **read-out probe** — one temporary assertion in `test_c6c` printing the live percents | read `('170.00', '170.00')`; grounds **N8** |

Byte-identity after revert:

```
d9160f92fad81991729d67e1714b9492f4215a75bbffb7f9684b69384ef48979  division_serializers.py
65558c5179bc8596bf10c27b16215baabc9875cfadc66459e550fcab52b0ee46  serializers.py
16cb98a97a6e1cefa25bd59928416ddbd702b8d5d4220e2c921b99d0439c7a11  calculator.py
90da6486bef4fd73a94fd61ebc3ea18f866aa79d2903e07add24315a68111555  test_phase2_live_surfaces.py
```

All four match their pre-round values exactly. The aggregate `app/` digest was
`f0722645…` throughout the measuring window and is `020e77c9…` now — the delta is the
shopify stream's own later edit, not a probe residue; see the tree-identity note in §1 and
N9.

**State side effects: none.** Every run used the suite's rollback-scoped `db_session`
fixture; no schema change, no committed rows, no migration. **No `archgraph_*` call was
made in this session** — the `.archgraph/architecture.yml` modification in `git status` is
foreign and is reported as N9.

**Evidence records** (all L1, hypothesis-scoped; tree identity as stated in §1 above,
constant across every row):

| Hypothesis | Scope / command | Result | ID delta |
|---|---|---|---|
| The two phase files are green at the reviewed tree | L1, `pytest -q -m integration <both phase files>` | 35 passed / 1 deselected | ∅ / ∅ |
| N-4's argument order is guarded at the E-P site | L1, probe A1 | 5 failed / 30 passed | +C3, +C6a, +C6b, +C6c, +`test_c17`; ∅ removed |
| …and at the E-B site | L1, probe A2 | 4 failed / 31 passed | +C3, +C6a, +C6b, +C6c; ∅ removed |
| C6c, not C6b, guards the negative-variance-with-positive-allowance region | L1, probe B | 1 failed / 34 passed | +C6c only; ∅ removed |
| The `allowed ≤ 0` boundary is pinned at exactly zero | L1, probe C | 2 failed / 33 passed | +C6a, +C6b; ∅ removed |
| C6c's live comparator | L1, probe D, `-k test_c6c` | read-out | `('170.00', '170.00')` |

Why no L4: every hypothesis this round was a named-row bite question, which the charter
scopes at L1. No absence claim was made and no coupling set needed bounding — the one
coupling question in the phase (C5's bite set) was re-measured by the coordinator at
`874f02d` and is cited, not reproduced. Staying at L1 also kept the round clear of the
foreign stream's +17 tests, so no measurement here needs attributing.

## 5. Verified correct (specifically)

- **Perimeter, both directions.** `5b8329b → 874f02d` touches nothing under
  `app/beyo_manager/`; `874f02d → HEAD` touches nothing under `app/`. The five files in the
  checkpoint are exactly the five declared.
- **Revert claims corroborated independently.** `division_serializers.py` hashes
  `d9160f92…`, the digest the coordinator recorded after the C5 probe — so that probe's
  revert is proven from a second session, not accepted.
- **The production code.** Both reconstruction sites pass
  `calculate_percent_consumed(actual + variance, actual)` — the N-4 order — inside the
  existing `result is not None` branch, and probes A1/A2 show the order is now
  *mutation-guarded* at both sites rather than merely correct on reading, which is what
  review r1 could say.
- **C6b's re-specification** (S1): frozen `15.00 / −15.00`, current allowance `20.00`,
  `status == "ok"` asserted on both faces, comment rewritten to claim only what the fixture
  shows.
- **C6c** (S2): `"150.00"` on both faces from frozen `15.00 / −5.00`, `status == "ok"` on
  both faces, non-vacuous against a live `170.00`, and the sole guard of its region.
- **N1** (`before["budget"]["percent_consumed"] == "120.00"` in C3) and **N4** (the comment
  above `test_c17`) are present and correct; N1 turns C3's live percent from *landing* into
  *moving* (`120.00 → 80.00`).
- **The S1 attribution swap** is present in all three documents (see P3, with N7's caveat).
- **Region enumeration** closes across OD-10's three named regions plus the `100.00`
  boundary and the `≤ 0` inequality (see P2).
- **No blast radius** from the fix cycle (see P4).

## 6. Carry-forward dispositions

| # | Item | Severity | Destination |
|---|---|---|---|
| N7 | `intention.md` §5.3A's stale C6b premise | note | **Coordinator fold, before the phase-4 prompt is compiled.** One clause; the section is a standing authority and phase 4 cites it. |
| N8 | `120.00` → `170.00` in two consumption records | note | **Coordinator fold** — `master_plan.md` §3 current row and `plans/plan_3.md` §7. |
| N9 | Stream 3's perimeter omits `.archgraph/` **and** an existing shopify test file; the "additions only" claim about the failing-ID set is too strong | note | **`master_plan.md` §7** — widen stream 3's perimeter to `.archgraph/architecture.yml`, `.archgraph/.internal/` and `app/tests/unit/services/infra/shopify/`, and narrow the "additions that pass do not touch the ID set" clause. **+ the owner graph backlog at `plans/plan_4.md` C6**; re-measure `archgraph_status` at phase 4 rather than citing §6's 9/2. |
| P5 | Approval baselines are published without database or dirty-tree identity | lesson | **`master_plan.md` §7, "Published approval baselines"** — add database identity and a dirty-diff digest column; state the count as subordinate to the failure-ID set. |

## 7. Lessons for the plans

1. **A correction inherits the shelf life of the thing it corrects.** N7 is the same shape
   as the C5 class-list finding the coordinator raised one round ago: a measured, dated,
   correct statement whose *premise* the very next fix cycle invalidated. The two blocks
   that carried it diverged only because one ended with the order that changed the tree
   ("C6b's fixture must be re-specified…") and the other did not. **Rule worth standing:
   when a correction both diagnoses a fixture and orders it changed, the diagnosis is
   written in the past tense and the order is written beside it — in every document that
   receives the fold, not only the one where the fix is executed.**
2. **A justifying number is a claim.** N8's `120.00` was asserted to establish
   non-vacuity, was never measured, and was wrong by one payload state (pre-open vs open on
   a fixture whose whole purpose is that the two differ). The conclusion survived by luck:
   both candidate values differ from `150.00`. §5B already requires computing both sides
   before choosing a fixture — the same discipline should apply to the *justification*
   written afterwards, which is currently done by inspection.
3. **The uncommitted foreign stream reaches further than its perimeter records, and it
   moved twice during one review round.** N9 caught it writing tool-recorded state (the
   graph) and then editing an existing tracked test file, neither listed in §7. Two rules
   fall out. (a) The charter's handoff rule already says a write perimeter covers
   "documents, code, and tool-recorded state (archgraph deltas)" — **§7's stream perimeters
   must follow the same schema, or they under-declare by construction.** (b) **A stream
   perimeter is a live claim, not a one-time note:** §7's "additions that pass do not touch
   the failing-ID set" was true of the stream as observed yesterday and is not true of the
   stream as it stands today. Same shelf-life shape as N7 and as the C5 class list — three
   instances in three consecutive rounds, now in three different artifact types (an
   intention section, a criterion's expected set, a stream perimeter). It is worth promoting
   to a standing rule that **any enumerated set describing something still in motion carries
   the date and the tree it was measured at**, so a later reader can tell "still true" from
   "was true".
4. **While an uncommitted foreign stream is live, an aggregate-diff digest is the wrong
   revert instrument.** Mine went stale between the last probe and the last artifact write,
   through no action of this session. Per-file digests over the reviewed perimeter prove
   what the aggregate cannot, and they were what actually carried the claim here.
5. **The round confirms the evidence policy is paying.** Five probes, five new mutant
   shapes, zero L4 runs, ~25 seconds of pytest total, and it produced one genuinely new
   structural fact (C6b and C6c partition the negative-variance space and neither covers the
   other). Under the retired policy the same five observations would have cost roughly
   twelve minutes and told us less, because the foreign stream would have needed attributing
   in every one of them.

## 8. Human-authorization backlog

- The architecture-graph review queue — master §6's 9 pending / 2 stale, **plus the
  uncommitted node and edge from N9**. Owner adjudication only; no session in this pipeline
  has written to it, and this one did not call the graph at all. Tracked at
  `plans/plan_4.md` C6.
