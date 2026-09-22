---
batch: D1
plan: [12, 13]
role: review
round: 1
verdict: CHANGES_REQUESTED
state: OWNER_DECISIONS_PENDING
date: 2026-09-21
actor: Opus reviewer (orchestrated subagent, slot `dr`)
tree: HEAD `06ad124`, `git status --porcelain` empty at entry and at exit
---

# Batch D1 review 1 — plans 12 and 13

**Verdict: `CHANGES_REQUESTED`.** Not because the production code is broadly wrong — it is not.
One blocking production defect is already confirmed and parked (owner card **D-5**), and I add
**one should-fix against the verification** and **one should-fix against the plan**, both measured
by probes nobody had run.

**Per-row tally, 64 rows: 58 PASS / 2 FAIL / 4 NOT_VERIFIED.**
Plan 12 (45): 42 PASS / 1 FAIL / 2 NOT_VERIFIED. Plan 13 (19): 16 PASS / 1 FAIL / 2 NOT_VERIFIED.

**New findings this round (3 + 5 notes).** One should-fix routed `verification` (plan 13 C4(a)'s
ordering clause cannot fail — three different order keys satisfy its fixture), one should-fix
routed `plan` (§9 rule 18: the event builder this batch registered is pinned by no row — I
violated its `extra {}` contract and the whole delete file stayed green), and one should-fix
routed `plan` for the eight untraced/uncredited router test ids. Everything else I looked at held.

**One more absorbed-additive mutant found**, the mechanism the D1 gate named: duplicating the
cascade's neighbour `:updated` events changes nothing observable, because
`coalesce_stock_report_events` de-duplicates. That makes **seven** in this batch. In these two
phases *no additive mutant on an event or a write has ever been observed to bite*; only
subtractive and re-ordering ones do.

I did **not** re-run the tester's campaign. Its 78 mutation rows are tree-matched (`app/` is
byte-identical from `b6cbbb9` through `HEAD`) and are consumed by citation. My budget went to
§13 of its handoff — the variation it declared it did not spend — and bought ten probes at seven
clauses no named mutation covers.

---

## ⚠ OWNER DECISIONS REQUIRED (3)

Cards **D-1, D-4, D-5, D-6, D-7** in `OWNER_CARDS_batch_D.md` are already parked and are **not**
re-raised here. These three are new.

### Card R-1 — the board's "row deleted" announcement is not pinned by anything

**Question.** Do you want a criterion row that pins the shape of the row-deleted announcement
(name, row id, and an empty detail block), yes or no?

**Story.** When someone deletes a board row, the backend announces it to every open screen so the
row disappears everywhere at once. This batch introduced the little function that builds that
announcement and wrote it into the project's registry of public shapes. I changed its detail block
from empty to carrying junk and ran the entire deletion test file: every test passed. So the
announcement's agreed shape is held by nothing — a later change could start shipping fields the
frontend never agreed to, or drop the empty block a renderer relies on, and no test anywhere would
notice.

**Branches.**
- *Yes, add a row:* one assertion in a test file that already captures these announcements; near
  zero cost, and the project's own standing rule 18 asks for it.
- *No, record it as knowingly unpinned:* costs nothing tonight; the next person to touch that
  builder has no guard.

**Recommendation.** Yes — the rule exists because a registered shape that nothing pins is how a
contract ships that never shipped, and here the guard is one line.

**On silence.** The gate holds: the row stays unpinned and I record it as a finding, not as
coverage.

**Trace.** Master plan §6.5 (`build_stock_report_item_deleted_event`, registered at the D1 gate),
§9 rule 18; plan 13 C3(a); my probe RP-10.

### Card R-2 — four statements in the deletion cascade name no workspace

**Question.** Add the workspace term to the statements that address a row by id alone — in the
cascade and in the two priority commands — yes or no?

**Story.** Every row on the board carries a globally unique id, and the code has already locked
the right workspace before these statements run, so nothing is wrong today and no customer can
see another customer's data through them. What is wrong is the reading: the same function that
carefully passes the workspace into three of its statements leaves it out of four others, and the
two priority commands do the same on the statement that actually writes the moved row. A future
reader cannot tell which omissions were deliberate, and that is exactly the shape that was
repaired once already in this project.

**Branches.**
- *Yes:* seven one-line additions, no behaviour change, and the tests prove inertness by staying
  green.
- *No:* safe today, and the asymmetry stays as a trap for the next reader.

**Recommendation.** Yes, but as a follow-up item rather than inside this batch — it touches code
whose review is otherwise settled, and it changes no outcome.

**On silence.** Nothing changes; the code stays correct and the note stays recorded.

**Trace.** `_delete_stock_report_item_cascade.py` (assignment `SELECT`, counters `SELECT`,
position `SELECT`, row soft-delete, history soft-delete), `set_stock_report_item_priority.py`
and `set_stock_report_item_priority_order.py` (mover `UPDATE`, `_serialize` re-read); tester
handoff §7.

### Card R-3 — eight tests in this batch answer to no rule

**Question.** For the five tests declared as candidates and the three that duplicate an existing
rule at the HTTP layer: fold them in as rules, or delete them — one answer for each group is
enough.

**Story.** Every test in this project is supposed to exist because a written rule asked for it.
Eight of the tests added in this batch do not: five were flagged by the people who wrote them as
"this looks worth keeping, but you decide", and three re-check at the web layer something two
existing rules already prove one layer down. They pass, they cost a little time on every future
run, and they are surface nobody is assigned to keep honest. They are not defects; they are eight
small decisions that have been deferred twice.

**Branches.**
- *Fold them in:* each becomes a real rule with an owner and a guard; a few minutes each.
- *Delete them:* the suite gets smaller and the rule book stays exact.
- *Keep them undecided:* the same question comes back at the next batch, bigger.

**Recommendation.** Fold the four that guard the request bodies (unknown fields, an explicit
"no priority", an absent filter) and drop the three duplicates — the underlying rules are already
proven one layer down.

**On silence.** The gate holds on the fold; I credit none of them against any rule.

**Trace.** Charter trace chain links 3–4 and §9 rule 16; implementer handoff §4/§6; tester
handoff §9 and its reverse map.

---

## 1. Gate check

| Check | Command / source | Result |
|---|---|---|
| Intention status | `head -30 SR/planning/intention.md` | `RATIFIED` (round 9, 2026-09-19; round 10 additive by owner ruling) — gate passes |
| Tree at entry | `git status --porcelain` | empty; HEAD `06ad124` |
| Checkpoints in HEAD | `git log --oneline` | `568a1cb`, `b6cbbb9` (implementer), `a0bb9b4`, `a7c9af1` (tester) all ancestors |
| Production diff, implementer → tester | `git diff --name-only b6cbbb9 a0bb9b4 -- app/beyo_manager/ \| wc -l` | **0** — the tester left no production change |
| Production diff, implementer → HEAD | `git diff --name-only b6cbbb9 HEAD -- app/beyo_manager/ \| wc -l` | **0** — my tree matches the stamped tree, so the tester's ledger is citable |
| Criterion counts | `python3 SR/count_criteria.py` | plan 12 **45 rows / 7 criteria**, plan 13 **19 / 6** → **64 rows** |
| Declared-mutation arithmetic | re-derived by hand from both §6 tables | 12: 18+1+5+11+2+2+12 = **51**; 13: 7+2+1+8+8+1 = **27**; **78**, and table 1 carries 79 numbered runs of which `M-69` is C2(b)'s re-siting → **78 declared = 78 executed**, closed |
| Batch-D unattended-run authority | `SR/FINALIZATION_STEPS.md` frontmatter | "owner, stated 2026-09-21 before an unattended overnight run of batch D" — the §3B launch exception's expiry at C APPROVED is covered for D |

**On §3B's "a `BLOCKED-PRODUCTION` row returns to the implementer before any review is compiled":**
I agree with the prompt's reading. The return step is *deferred, not skipped* — its destination is
a fix the owner has not authorised, because it reopens APPROVED phase 3. Running the review now
costs nothing and buys the morning both answers. The gate is unaffected: D1 cannot be approved by
me under any reading.

## 2. Perimeter check — clean

| Perimeter | Command | Result |
|---|---|---|
| Implementer | `git diff --name-only 6aed93f b6cbbb9 -- app/` | 14 production files + 6 test files. Every production file is in plan 12 §4, plan 13 §4, or the registry-authorised `_row_values` consolidation (`_row_values.py` + the three donors). **No file outside those lists.** |
| Tester | `git diff --name-only b6cbbb9 HEAD -- app/` | exactly the four test files it declares; **zero** under `app/beyo_manager/` |
| Docs/tooling since `b6cbbb9` | `git diff --name-only b6cbbb9 HEAD` | `.archgraph/architecture.yml`, both plan files, the master plan, the owner-cards file, the two handoffs and two prompts — all declared |
| Phase-13 §4 exclusions honoured | same diff | `requests/__init__.py` carries **no** delete request model (owner card 5 ✓); `serializers.py` gained only `serialize_stock_report_item` — the three compact serializers are byte-unchanged from phase 8 (`git diff 6aed93f b6cbbb9` on that file shows one added function) ✓ |

No perimeter violation by either role.

## 3. What I verified by execution — my ten probes

Protocol for every probe: apply with a scripted, asserted-unique string replacement · run the
**whole** test file (never `-k`) with `BEYO_TEST_SLOT=dr` · `git checkout --` · `git diff --quiet`
exit 0. Every command below was run by me on `06ad124`.

| Probe | Site (file:symbol, def.) | Edit | Command | Result |
|---|---|---|---|---|
| **RP-1** | `list_stock_task_assignments.py` order clause | drop `created_at` from `.order_by(created_at, client_id)` | L1 `test_list_stock_task_assignments.py` | **GREEN — 5 passed** (and green on 4 further repeats, so it is not a flake) |
| **RP-1b** | same | drop `client_id`, keep `created_at` | L1 same file | **GREEN — 5 passed** |
| **RP-2** | same | reverse both terms (`.desc()`) | L1 same file | RED — `test_every_non_deleted_state_is_listed_in_created_at_client_id_order` |
| **RP-3** | `set_stock_report_item_priority_order.py`, the `t == p` branch | insert an *idempotent* write (`SET priority_order = priority_order`) before the early return — no record, no event, no stamp | L1 `test_stock_report_priority_and_ordering.py` | RED — `test_move_to_the_held_position_writes_nothing` (the `count_writes == 0` clause bites on a mutant shape nobody ran) |
| **RP-4** | `set_stock_report_item_priority.py`, mover `UPDATE` | drop `updated_by_id` / `updated_at` (the **subtractive** direction of C5(a)) | L1 ordering file | RED — `test_priority_change_closes_the_source_gap_and_appends:571` `assert None == 'usr_sm_281a50c995'` |
| **RP-5** | `list_stock_report_items.py` read order | `priority_order.desc()` inside the rank | L1 `test_list_stock_report_items.py` | RED — `test_read_order_is_high_medium_low_then_priority_order:152` |
| **RP-6** | `_delete_stock_report_item_cascade.py` | delete the history soft-delete `UPDATE` | L1 `test_delete_stock_report_item.py` | RED ×2 — `…soft_deletes_the_row:333` and `…creates_a_new_row:633` |
| **RP-7** | same | drop `updated_at` / `updated_by_id` from the row soft-delete | L1 delete file | RED — `…soft_deletes_the_row:319` `assert None == datetime(...)` |
| **RP-8** | `serializers.py:serialize_item_compact` (APPROVED phase 8) | `item_images` elements become `{client_id}` instead of `serialize_image_light` | L1 `test_list_stock_task_assignments.py` | RED — `…fourteen_key_shape…:295` `assert [{'client_id'}] == [{'client_id'…,'width_px'}]` |
| **RP-9** | `_delete_stock_report_item_cascade.py` | emit each shifted neighbour's `:updated` **twice** | L1 delete file | **GREEN — 6 passed** (absorbed by the coalescer) |
| **RP-10** | `_delete_stock_report_item_cascade.py:build_stock_report_item_deleted_event` | `extra={}` → `extra={"rp10_probe": …}` | L1 delete file | **GREEN — 6 passed** |

Scope note for RP-10's absence half: `grep -rn "stock_report_item:deleted" app/tests` returns
**two** lines, both in `test_delete_stock_report_item.py` (`names.count(...) == 1` and the exact
ordered event list) — neither reads `extra`. The grep bounds the claim, so the whole-file green is
sufficient and no L4 was spent on it.

### The structural check the plan asks the reviewer for — plan 12 C2(a)/C2(b)

The cells are class-3 (unforced interleaving) and state the post-condition I am to derive. I
derived it structurally rather than behaviourally:

- Every statement in the tree that writes `stock_report_items.priority_order` is one of five —
  `_ordering.py:_shift`, the two commands' mover `UPDATE`s, and `repair_stock_report.py:69,125`
  (`grep -rn "priority_order" app/beyo_manager --include="*.py"`, filtered to write sites).
  `apply_stock_demand.py:237` is a `RETURNING` column declaration, not a write;
  `create_upholstery.py:285` is a different table.
- Every command that reaches those five takes `pg_advisory_xact_lock(hashtext('stock_report_order:'
  || ws))` **before reading any position** — `grep -rn "acquire_stock_report_order_lock"` gives
  exactly four callers: the two ordering commands, `delete_stock_report_item`, and
  `repair_stock_report`. It is an **xact** lock (`_locks.py:13-19`), so it is held to commit.
- Therefore every `priority_order` writer in a workspace is totally ordered, each re-reads
  positions under the lock, and the end state after either serialisation is one of the two
  sequential compositions with the group dense `1..n`. **The post-condition holds.**

That is a structural derivation, not evidence. **The density-under-a-real-race half of MC-7 is
proven by no test in this project, and C2(c) proves only that the lock is taken.** I confirm the
prompt's statement of the true coverage state, and I record both rows `NOT_VERIFIED` rather than
letting a structural argument read as coverage.

### Claims I consumed rather than re-bought

Per the charter's test-evidence section (tree identity matches: `app/` byte-identical from
`b6cbbb9` to `06ad124`): the orchestrator's six hand verifications (its own L4 on the implementer
tree, C4(e)'s two mutants including the sharper "emit only when non-`None`", `_row_values`
inertness, the cascade's two fresh `SELECT`s and the no-`ctx` AST result, card D-5's both halves,
and card D-6's measured ORM asymmetry), and all 78 rows of the tester's table 1 including the
three replacement probes P-1/P-2/P-3 that the D1 folds now name as the declared mutants for
plan 12 C1(a), C1(b) and C6(a). I re-ran none of them; the one thing I re-derived by hand was the
declared-mutation arithmetic, because it is cheap and it gates `executed == declared`.

## 4. Findings

### B-1 · blocking · route `production` · plan 12 C3(d) — the consumed blocker (owner card D-5)

Consumed, not re-bought: the orchestrator confirmed both halves against ratified text
(`consistency.py:200-222` applies the `goal_total` rule to every history record though intention
§14C line 1594 scopes it to goal records and §6.2 line 794 defines those as
`quantity_requested_change`; `repair_stock_report.py:248-255` zeroes by `client_id` with no type
filter). Phase 12's own code is right; it is the first writer of `priority_change` records and
therefore the thing that makes a latent phase-3 defect live.

What I add is the review's own position: **the witness test must stay red.** Deleting or weakening
`assert_stock_report_clean` in
`test_the_priority_record_snapshots_the_live_awaiting_counter` would satisfy §9 rule 2's letter
while destroying the only record of the defect, and it would make C3(d) a row that passes over a
product that corrupts history. The tester's judgement is **confirmed**. Row verdict: **FAIL**,
fix routed to the implementer *after* the owner rules card D-5.

Secondary observation, recorded so the next round does not trip on it: C3(d)'s named mutant
(M-24) was run against a test that is **already red**. The tester's reading — the failure point
moves forward to the record clause — is correct and is the only reading available, but a mutation
run against a baseline-red test can never show "green → red", so C3(d) will need its mutation
re-run once the blocker is fixed.

### S-1 · should-fix · route `verification` · plan 13 C4(a) — the ordering clause cannot fail

The row's outcome names the key: *"ordered by `created_at, client_id`"*. Its test computes the
expected list with a second query that uses the same two keys, and its four assignments are
created in one tight loop with nothing pinning the two orderings apart.

Measured: **RP-1** (production ordered by `client_id` alone) → green, five runs;
**RP-1b** (production ordered by `created_at` alone) → green; only **RP-2** (full reversal) bites.
Three different order keys satisfy the fixture, so the row's stated key is not discriminated —
the defect family the project calls L-14, and the *exact twin* of the one the tester repaired in
plan 12 C4(b) the same evening. C4(b)'s test now back-dates a null row **chosen from the sorted
real ids** and asserts `N1 > N2`; C4(a) has no equivalent.

**Correction (tester's lane, no criterion change):** in
`test_every_non_deleted_state_is_listed_in_created_at_client_id_order`, after creating the four
assignments, back-date the one with the **larger** `client_id` (chosen from the sorted real ids,
master plan §10) and assert the disagreement, exactly as `test_no_filter_lists_only_null_priority_
rows_by_created_at` does; then re-run RP-1 as the arming proof. Row verdict: **FAIL** on the
ordering clause; its state-filter half (M-71, M-72) is genuinely armed.

### S-2 · should-fix · route `plan` · §9 rule 18 — the registered event builder is pinned by nothing

`build_stock_report_item_deleted_event(*, client_id, workspace_id) -> WorkspaceEvent` with
`extra {}` was **registered in master plan §6.5 at the D1 gate**. Rule 18: "a phase that adds a
name to §6.5 is complete only when some row in its own plan asserts that name's shape at its own
boundary — arity, the keys of what it returns, and the error it raises."

Measured: **RP-10** violates the `extra {}` half of that contract and the entire delete file stays
green (6 passed); the grep above shows no other test in the tree reads it. The nearest row,
C3(a), asserts the event's **name and row id** only — and C3(a) is itself `BLOCKED-PLAN`, so the
one row in the neighbourhood is not even countable. A signature registered by this batch ships
with no pin.

**Correction:** a criterion row (owner's authorship — card R-1) asserting the dispatched
`stock_report_item:deleted` element's `event_name`, `client_id`, `workspace_id` and `extra == {}`,
armed by exactly RP-10's mutant. Routed `plan`, not `verification`, because the tester may not
author the row.

### S-3 · should-fix · route `plan` · eight test ids trace to no criterion row

Derived by command (`pytest --collect-only` on the six files, counted by function):
`test_stock_report_router.py` collects **53** ids, **27** of them new this batch = 20 role cells
(C7(a)–(l), C5(a)–(h)) + 3 `test_ordering_routes_refuse_malformed_bodies` + 4 declared candidates;
the five integration files collect **34** ids, of which the tester's table 2 credits 33.

- **Five declared candidates** (`test_ordering_routes_refuse_unknown_fields` ×2,
  `test_list_items_route_passes_no_priority_when_the_param_is_absent`,
  `test_priority_route_accepts_an_explicit_null`,
  `test_a_row_with_no_assignments_answers_an_empty_list`) are correctly declared under the charter's
  link 3 — but a candidate is a *pending decision*, and it has now survived the implementer round
  and the tester round undecided.
- **Three `test_ordering_routes_refuse_malformed_bodies` ids** are the harder half: the implementer
  traced them to C1(m)/C1(n) "at the HTTP boundary", the tester explicitly credits them against
  **no** row (those cells site their mutation in `requests/__init__.py` and are armed at command
  scope). They exercise a *second, duplicate* copy of the 422 contract — the router carries its own
  `_SetStockReportItemPriorityBody` / `_SetStockReportItemPriorityOrderBody` beside the service's
  request models — so they are neither orphans nor credited coverage.

Owner card R-3. Not blocking; it is eight small decisions, and the rule that makes them a finding
(§9 rule 16 / charter link 4) is the same rule that makes an uncovered row one.

### N-1 · note · route `production` · the workspace term (owner card R-2)

I agree with the tester's §7 note and **widen** it by reading the code: the statements that address
a row by `client_id` alone are not four but seven — the cascade's assignment `SELECT`, counters
`SELECT`, position `SELECT`, row soft-delete and history soft-delete, **plus** both priority
commands' mover `UPDATE` and their `_serialize` re-read. All are safe today (the caller has locked
by workspace and `client_id` is a prefixed ULID), and all sit in functions that thread
`workspace_id` into their *other* statements. Not changed, no criterion touched.

### N-2 · note · route `verification` · a seventh absorbed-additive mutant (RP-9)

Duplicating every shifted neighbour's `:updated` in the cascade is invisible:
`coalesce_stock_report_events` de-duplicates, so the dispatched list is byte-identical. This is an
**equivalent mutant** — recorded and moved on, never a test demand (doctrine rule 2). Its value is
in the pattern: with C1(h)(i), 12 C1(a), 12 C1(b), 12 C6(a), 13 C1(a)(i) and 13 C2(b), that is
**seven** inert mutants in one batch, every one of them additive, and every subtractive or
re-ordering mutant in the same phases bit. For the D2 projection the rule is now mechanical:
*in these modules, do not name an additive mutant; name a subtraction or a re-order.*

### N-3 · note · route `plan` · §9 rule 3 is too coarse — I agree with card D-6

Consumed, not re-measured: the counter statement (PK equality + `RETURNING`) leaves the instance
synchronised, the shift statement (range criteria) leaves it stale. The rule as written — "an ORM
instance is stale after any Core UPDATE of the same row in the same transaction" — over-promises
evidence at PK-equality sites (which is exactly how plan 13 C2(b) came to be a tripwire that
cannot trip) and under-credits it at range-criteria sites. The finding is against the **rule's
wording**, not against the code; L-40 as drafted in card D-6 is the right replacement.

### N-4 · note · route `verification` · plan 13 C2(a) does not assert `target_kind`

The cell names the record as `{stock_report_item, R, field, stored, recomputed, inline:…}`. The
test asserts `target_client_id`, `field`, `stored_value`, `recomputed_value`, `trigger`,
`created_by_id` and `created_at` — but not `target_kind`. One line; the row is otherwise the
best-asserted record row in the batch.

### N-5 · note · route `plan` · two stale statements in the review prompt, recorded so they do not propagate

(a) The prompt's "Plan 13 C1(c) is NOT EXERCISED" is **stale**: the tester replaced that test in
place, and I read the replacement — it runs a real `apply_stock_demand` delivery after `DR(R)` and
asserts a new live row with its own fresh history at the surface the cell names. C1(c) is
exercised; only the wording of "empty history" is open (card D-7.2).
(b) The prompt routes the reviewer to `/Users/davidloorenz/agent-skills/independent-reviewer.md`,
which does not exist; the doctrine file is `plan-reviewer.md`. I followed the latter.

### N-6 · note · route `plan` · the declared-mutation count wording for role cells

Twelve role-cell rows say "both directions run and recorded" while each row is reddened by exactly
one edit. The tester's derivation (one run per row) is the right reading and its *set* of edits is
complete, but the cell wording will keep producing two different totals for the same work. Worth a
one-line clarification at the next fold: "both directions across the group, one edit per row".

## 5. Per-row verdicts — 64 rows

Legend: **PASS** = production satisfies the row *and* the evidence can fail · **FAIL** = the row
is not met, or a stated clause of it is proven by evidence that cannot fail · **NOT_VERIFIED** =
no evidence exists and none could be bought under this round's authority.

### Plan 12 — 45 rows: 42 PASS / 1 FAIL / 2 NOT_VERIFIED

| Row | Verdict | Basis |
|---|---|---|
| C1(a) | PASS | folded replacement mutant, tester P-1 red on the row's own state assertion |
| C1(b) | PASS | folded replacement, P-2 red on the row's own state assertion |
| C1(c) | PASS | M-03; **+ my RP-3**, a second mutant shape red on the `count_writes == 0` clause |
| C1(d) | PASS | M-04 |
| C1(e) | PASS | M-05 |
| C1(f) | PASS | M-06, and C1(d)/(e) stay green under it as the cell claims |
| C1(g) | PASS | M-07 |
| C1(h) | PASS | M-08 (the D1 gate's replacement) + M-09, both red |
| C1(i) | PASS | M-10 |
| C1(j) | PASS | M-11 |
| C1(k) | PASS | M-12 |
| C1(l) | PASS | M-13, the other branch of C1(k)'s site |
| C1(m) | PASS | M-14; rule-17 shapes measured on the installed pydantic 2.11.3 |
| C1(n) | PASS | M-15 (`StrictInt`; lax coercion confirmed) |
| C1(o) | PASS | M-16/17/18 re-sited to both lookups; both sitings recorded |
| C2(a) | **NOT_VERIFIED** | class-3, no test; my structural derivation holds (§3 above) but is not evidence |
| C2(b) | **NOT_VERIFIED** | same |
| C2(c) | PASS | M-19 — the move completes without the lock, so the wait is genuinely forced |
| C3(a) | PASS | M-20, M-21; I read the test: all eight record fields asserted |
| C3(b) | PASS | M-22, sited inside `shift_within_group` so it cannot leak into `close_priority_gap` |
| C3(c) | PASS | M-23 red on the record-count assertion of all four no-op cells |
| C3(d) | **FAIL** | blocking B-1 / owner card D-5; witness test red by design and correctly kept |
| C4(a) | PASS | M-25; **+ my RP-5** for the intra-group `priority_order ASC` sub-check |
| C4(b) | PASS | M-26, M-27; fixture now guarantees the two orderings disagree (`assert N1 > N2`) |
| C4(c) | PASS | M-28 |
| C4(d) | PASS | M-29, and measured both ways against C4(b) |
| C4(e) | PASS | M-30/31/32 + the orchestrator's sharper "emit only when non-`None`" probe; both rows' key sets compared in one assertion |
| C4(f) | PASS | M-33, M-34, one predicate per sub-check |
| C4(g) | PASS | M-35 |
| C5(a) | PASS | M-36 (additive) **+ my RP-4** (subtractive, mover clause) |
| C5(b) | PASS | M-37 |
| C6(a) | PASS | folded replacement, P-3 red on the row's own event-list assertion |
| C6(b) | PASS | M-39 (re-sited; the first siting's crash is recorded, not counted) |
| C7(a)–C7(d) | PASS ×4 | M-44/45/47/46 |
| C7(e)–C7(h) | PASS ×4 | M-48/49/51/50, a second route, separately recorded |
| C7(i)–C7(l) | PASS ×4 | M-40…M-43 |

### Plan 13 — 19 rows: 16 PASS / 1 FAIL / 2 NOT_VERIFIED

| Row | Verdict | Basis |
|---|---|---|
| C1(a) | PASS | M-61 at its real site (`_goal_credit.py`) for the credit clause; **+ my RP-6** (history soft-delete) and **RP-7** (`updated_*`), two clauses no named mutation covered. Mutant (i) is equivalent and MC-16's ordering clause stays knowingly unguarded (card D-7.3) |
| C1(b) | PASS | M-62 |
| C1(c) | PASS | M-63; test rewritten at the delivery surface the cell names — verified by reading it. Wording open (card D-7.2) |
| C1(d) | PASS | M-64/65/66, one per visibility cell |
| C2(a) | PASS | M-67; N-4 notes the one unasserted field |
| C2(b) | **NOT_VERIFIED** | `BLOCKED-PLAN`: green at the named site *and* the real site; the ORM instance is synchronised at a PK-equality statement, so the planted defect cannot occur. Production correct, proof empty (card D-6) |
| C3(a) | **NOT_VERIFIED** | `BLOCKED-PLAN`: the cell says three assignment-deleted events, its own fixture makes four (card D-7.1). Beyond that, **my RP-9** shows its "one `:updated` for C" clause is held by the coalescer, not by the cascade, and the composed outcome is still proven by two tests with different fixtures, never one |
| C4(a) | **FAIL** | S-1 — the ordering clause cannot fail (RP-1, RP-1b green); the state-filter half is armed (M-71, M-72) |
| C4(b) | PASS | M-73/74/75 with cross-suite red sets; **+ my RP-8** for the `item_images` element-shape clause |
| C4(d) | PASS | M-76/77/78 |
| C5(a)–C5(d) | PASS ×4 | M-52…M-55, both directions |
| C5(e)–C5(h) | PASS ×4 | M-56…M-59 |
| C6(a) | PASS | M-79 — and phase 8's two files stay green under it, which is the half the row exists for |

## 6. Mutation-probe declaration

Ten probe applications across **six** production files. Each was applied by an asserted-unique
string replacement, exercised by one whole-file L1 run on slot `dr`, then reverted with
`git checkout --` and confirmed byte-identical with `git diff --quiet` (exit 0) **immediately
after its run**. `git status --porcelain` is empty at the moment of writing, after the L4.

```
app/beyo_manager/services/queries/stock_report/list_stock_task_assignments.py   (RP-1, RP-1b, RP-2)
app/beyo_manager/services/commands/stock_report/set_stock_report_item_priority_order.py  (RP-3)
app/beyo_manager/services/commands/stock_report/set_stock_report_item_priority.py        (RP-4)
app/beyo_manager/services/queries/stock_report/list_stock_report_items.py                (RP-5)
app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py     (RP-6, RP-7, RP-9, RP-10)
app/beyo_manager/domain/stock_report/serializers.py   (RP-8 — APPROVED phase 8's serialize_item_compact)
```

**State side effects:** none outside the test-owned workspaces on slot `dr`. Every test in scope
seeds its own workspace and purges it (§9 rule 1, charter rule 11½); no probe wrote to a shared
table, no migration ran, and the configured database is untouched. No archgraph change was made
by this session — the phase delta recorded by the implementer stands as it is.

**Write perimeter of this session:** this handoff, the Review-log entry appended to
`plans/plan_12.md` and `plans/plan_13.md` (layer 1 only), and one checkpoint commit with explicit
paths. No tracker row (master plan §4/§4A reserves them to the orchestrator — please set batch D1
to `CHANGES_REQUESTED`), no criterion cell, no plan table, no other role's handoff, nothing pushed.

## 7. The one L4 stamp

**Authorization line, written before the run:** narrower evidence is insufficient because this
session applied and reverted ten production probes across six files, one of them in APPROVED
phase-8 code; the closing stamp has to be taken on the tree I hand back, and the prompt requires
both ID diffs at review entry.

**Hypothesis:** the tree I hand back moves the enumerated baseline by exactly one ID — the tester's
declared witness — and by nothing else.
**Scope:** L4. **Tree identity:** HEAD `06ad124`, `git status --porcelain` empty before and after.
**Command:** `cd app && BEYO_TEST_SLOT=dr PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q`
**Result:** **24 failed / 3739 passed / 1 skipped**, 74.7 s — identical to the tester's stamp.

Failure-ID diff against `handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt` (23 IDs,
comments stripped), both directions:

```
=== in mine, not in the baseline ===
tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py::test_the_priority_record_snapshots_the_live_awaiting_counter

=== in the baseline, not in mine ===
(empty)
```

24 = 23 + 1. The one new ID is the declared `BLOCKED-PRODUCTION` witness; all 23 baseline IDs are
present, including the two slot-sensitive `test_database_isolation.py` ids §10 requires under a
non-`main` slot. Passes reconcile as 3679 + 60 = 3739, unchanged by the tester and by me.

## 8. What I could have hidden and am reporting

1. **My L4 bought no variation.** It is the mandatory closing stamp on a tree I had probed, and I
   wrote the authorization line before running it — but on a byte-identical `app/` tree it
   reproduces the tester's number rather than discovering anything. Had I not probed production, I
   should have cited the tester's stamp instead of taking my own.
2. **I ran RP-1 five times.** The first green could have been the coin flip the project's §10 rule
   warns about, so I repeated it four times and added RP-1b to make the finding unambiguous. Four
   of those five runs bought nothing new and would have been over-evidence had the first result
   been red.
3. **RP-6, RP-7 and RP-8 all reddened** — three of my ten probes confirmed arming rather than
   finding a hole, and I chose them precisely because the clauses carried no named mutation. That
   is the honest hit rate: seven clauses probed, two holes.
4. **I did not probe the `actor_user_id=None` cascade path**, the lock-ordering matrix, any `TZ` or
   clock variation, or a second writer on the delete path — all of them still-unspent variation
   listed in the tester's §13.
5. **My structural check for C2(a)/C2(b) is a reading, not a measurement.** I could have presented
   it as though the rows were covered; they are not, and I recorded them `NOT_VERIFIED`.
6. **I did not independently re-verify card D-5's defect.** The prompt told me to consume it and I
   did; if the orchestrator's reading of §14C line 1594 is wrong, my blocking finding inherits the
   error.

## 9. Lessons for the plans (the coordinator folds these)

- **L-A (fixture discrimination is per row, not per batch).** The tester repaired plan 12 C4(b)'s
  ordering fixture the same evening it left plan 13 C4(a)'s twin unrepaired. When a round finds one
  "two orderings agree" defect, the fold should enumerate **every** row in the batch whose outcome
  names an order key, and check each — the defect class travels by shape, not by file.
- **L-B (rule 18 needs a mechanical hook).** A signature registered *during* a gate fold is exactly
  the one most likely to reach no criterion row, because the plan was written before the name
  existed. Registering a name should emit a pin obligation in the same act — "which row asserts
  this?" — or rule 18 is satisfied only by whoever remembers it.
- **L-C (additive mutants are the wrong shape in idempotent code).** Seven for seven this batch.
  For D2, a projection should reject any additive mutant cell in a module that de-duplicates
  (`coalesce_stock_report_events`) or overwrites (the mover's own `UPDATE … RETURNING`) and demand
  a subtraction or a re-order instead. This is now measured often enough to be a rule, not a note.
- **L-D (a mutation against a baseline-red test proves less).** C3(d)'s M-24 can only be read by
  where the failure lands, never as green → red. A row whose test is red at baseline should carry
  its mutation re-run in the fix round, and the ledger should mark it as such rather than as an
  ordinary bite.
- **L-E (candidates must die or be adopted in the round that creates them).** Five have now
  survived two sessions. A candidate that outlives its own batch is just an untraced test with a
  polite label.

## 10. Carry-forward dispositions

| Item | Route | Destination |
|---|---|---|
| B-1 / card D-5 (phase-3 type filter) | production | owner ruling → implementer fix inside D1, then re-run C3(d)'s mutation |
| S-1 plan 13 C4(a) fixture | verification | tester, D1 fix round; re-arm with RP-1 as the proof |
| S-2 / card R-1 (rule 18 pin) | plan | owner authors the row → tester arms it with RP-10's mutant |
| S-3 / card R-3 (8 untraced ids) | plan | owner/coordinator fold or refuse, recorded |
| N-1 / card R-2 (`workspace_id` term) | production | owner ruling; if yes, a follow-up phase after D1 — not inside this batch |
| N-2 (absorbed-additive rule) | plan | **D2 projection** — reject additive mutant cells in de-duplicating modules |
| N-3 (§9 rule 3 wording, L-40) | plan | master plan §9 rule 3 + §9A, at the next fold |
| N-4 (C2(a) `target_kind`) | verification | tester, D1 fix round, one line |
| N-5, N-6 (prompt/wording) | plan | coordinator, next prompt compilation |
| Cards D-1, D-4, D-6, D-7 | plan | already parked; untouched by this review |
