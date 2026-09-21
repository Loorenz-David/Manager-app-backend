```
batch: C2
phases: [9, 10]
role: review
round: 2 (re-review)
verdict: APPROVED
state: OWNER_DECISIONS_PENDING
date: 2026-09-21
actor: Opus (plan-reviewer)
```

# Batch C2 re-review — plans 9 and 10, fix round 1

## 0. Summary

**Verdict: APPROVED.** 84 criterion rows in scope (plan 9: 45, plan 10: 39). **84 PASS · 0 FAIL ·
0 NOT_VERIFIED.** Round 1's two OWED rows and the three rows the owner authored from its cards are
all built, and — the part the round could not establish about itself — **all five are armed, not
merely green.** I measured the arming that the fix round did not: C4(i)'s two unexecuted plants,
C4(j)'s five collected constructs, and C8(d)'s second sub-check.

Every round-1 finding is closed at its site:

| Round 1 | Status now | How I checked |
|---|---|---|
| **F-1** blocking — the sync read *any* assignment, not the **active** one | **CLOSED** | Both halves of MC-2 step 3 restored; every other reader of that assignment in the command audited (§6.4); no second stale read anywhere in the corpus |
| **F-2** the collector missed five forms | **CLOSED for those five**; **four new in-class forms found — R-1** | Re-planted all five myself: the guard names each of the five lines individually |
| **F-3** C2(a)'s delegated evidence did not exist | **CLOSED** | `test_c4i_…` is the negative assertion; I planted the forbidden call in the two helpers nobody had tried and it fires on both |
| **F-4** C8(d)'s fixture was unproducible | **CLOSED** | Row restated by the owner to a terminal assignment; the test matches the restated cell, not the original |
| **F-5** no row covered a two-assignment task | **CLOSED** | Plan 10 C1(m) authored and built |
| **F-6** raw SQL was not a collected class | **CLOSED** | Class (f) shipped and collects |

**The production behaviour change the prompt flagged — `resolve_processed_group`'s three N-5/C8(d)
additions — is sound, and I judged it explicitly (§6.1).** One of the three is armed; the other two
are **individually equivalent mutants and jointly load-bearing**, which I established by running
all three mutant combinations. Suppressing the zero-delta `:updated` event is not a deviation: it is
what MC-19's own net-change rule does to that event anyway. No consumer depends on it arriving
unconditionally.

**One finding, one owner card, seven notes.** The finding (R-1) is `plan`-routed and blocks nothing
that shipped: the collector under-implements the owner's own "by construct, not by spelling"
clause for four more constructs, one of which is an idiom **this repository's own test suite already
uses three times to write `Task.state`**. Zero live instances in the scanned corpus.

**Tracker rows are not written by me** — master plan §3A reserves them to the orchestrator.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Should the write-site guard also see a job-state write made through `Task.__table__.update()`?

**Question.** Extend MC-2's guard to four more constructs — yes or no?

**Story.** The guard's job is that nobody can change a job's state without the board being told, and
you already ruled it must catch the *construct*, however it is spelled. I wrote a job-state update
into a live file the way this project's own test files already write it three times, through the
table object rather than the model, and the guard passed without a word. Three more shapes passed
too. Nothing in the shipped code writes state this way today, so this is a door left open, not a
leak.

**Branches.**
- *Extend*: four more shapes become watched sites; nothing in the codebase needs registering today.
- *Do not*: the shapes stay invisible, and this handoff is the only record of which ones.

**Recommendation.** Extend — it is your own card-4 reasoning (cheap today, expensive later), and the
strongest missed shape is one the team already writes by habit.

**On silence.** Nothing changes; the four shapes stay uncollected and recorded here only. No row is
authored. The gate holds.

**Trace.** intention §5B "The guard" (a)–(f) and the by-construct clause; plan 10 C4(j); finding R-1.

---

## 1. Gate check

| Check | Result |
|---|---|
| Intention `status: RATIFIED` (round 9; round 10 additive) | PASS |
| Plans 9 and 10 present, criteria tables addressable | PASS |
| Master plan §4A batch C2 = `FIX-VERIFIED — re-review owed` at dispatch | PASS |
| `git status --porcelain` empty at session start and at close | PASS |
| `BEYO_TEST_SLOT=rv2` on **every** pytest invocation (6 runs) | PASS |
| Gate condition = **23** failures (21 published + the two `test_database_isolation` slot IDs) | PASS — see §2, not re-run |
| Batch C2's eight files byte-identical to fix checkpoint `d3c93a3` | PASS — `git diff d3c93a3..HEAD --` over the eight paths is empty |

## 2. Tree identity and evidence policy

- Session start tree: **`f8f7dd8`**, clean. **Close tree: `df09143`, clean** — see the drift note
  below. All six of my pytest runs were taken at `f8f7dd8`.
- **I did not take an L4, and I did not re-run the orchestrator's hand-verification.**
  Authorization line, written before the first run: *narrower evidence is sufficient because all
  eight batch-C2 files are byte-identical to `d3c93a3`, the tree whose L4 the orchestrator took on a
  clean tree (`23 failed / 3669 passed / 1 skipped`, both ID diffs empty); the only `app/` delta
  between that tree and mine is phase 8A's, which touches three files disjoint from C2's perimeter
  and from every import radius my hypotheses reach. An L4 of my own would purchase no variation on
  any C2 hypothesis.*
- Consumed by citation, tree-matched, **not re-run**: the orchestrator's C2 surface (124 passed),
  its F-1 revert-at-the-site run, its `maybe_advance_task_to_working` plant, its class-(f) raw-SQL
  plant, and its gate L4. The implementer's C8(d), C1(m), C8(a) and N-5 mutation rows are
  tree-matched and consumed; where a claim was checkable by reading I corroborated it analytically
  rather than re-running (§6.2).
- My whole budget went to **variation**: six probe runs, every one on a site, mutant shape or
  sub-check that no prior round had touched.

**⚠ Foreign commit during this session, reported not acted on.** `df09143`
("owner ruling round 3 — withdraw the `item_category_id` widening") landed on `main` while I
worked. It is **phase 8A** and touches three `app/` files (`routers/api_v1/stock_report.py`,
`preview_stock_task_assignment_match.py`, `test_preview_stock_task_assignment_match.py`) plus
`master_plan.md`, `plan_8A.md`, and it deletes the draft v3 frontend addendum. **None of C2's eight
files is touched** (verified path-by-path), so none of my evidence is affected. **Consequence for
the orchestrator, not for this verdict:** the commit withdraws one parametrized case, so the gate
stamp `3669` no longer describes the tree — the approval-gate L4 must be re-taken on whatever tree
is gated, and **3668** is the count to expect if nothing else lands. The 23-ID failure set is
unchanged. I did not review, revert or act on any of it.

## 3. Perimeter — verified, not reconstructed

The fix round's declared perimeter is **8 code/test files**. Reconstructed from the five checkpoint
commits (`7d33c9a`, `ba3166e`, `b15f6e3`, `046d8dc`, plus the docs-only `d72f2e9`/`d3c93a3`):

| File | Declared | In the commits |
|---|---|---|
| `bm/services/commands/stock_report/sync_task_stock_assignments.py` | ✓ production | ✓ |
| `bm/services/commands/stock_report/_move_assignment.py` | ✓ production | ✓ |
| `tests/unit/.../stock_report/_task_state_write_scanner.py` | ✓ test-support | ✓ |
| `tests/unit/.../stock_report/task_state_write_site_registry.py` | ✓ test-support | ✓ |
| `tests/unit/.../stock_report/test_task_state_write_sites_are_registered.py` | ✓ test | ✓ |
| `tests/integration/.../stock_report/test_task_state_sync.py` | ✓ test | ✓ |
| `tests/integration/.../stock_report/test_process_items_processed.py` | ✓ test | ✓ |
| `tests/unit/.../stock_report/test_items_processed_request.py` | ✓ test | ✓ |

**Exact match, both directions. No file outside the declared perimeter changed.** Plan documents:
Review log entries only in plan 9 and plan 10 (no criterion cell touched — confirmed by reading
`d72f2e9`'s diff: 180 insertions, **zero deletions**). No `master_plan.md` edit, no intention edit,
no tracker row, no push.

## 4. Review history — what is already settled, so nothing is re-spent

Round 1 dispositioned **79 PASS / 0 FAIL / 2 NOT_VERIFIED** over 81 rows, consuming the tester's
ledger where tree-matched and spending its own budget on three measured defects past the rows. Those
79 rows are **settled and not re-verified here**; their evidence is unchanged because none of their
files moved except the two the fix touched, and on those two I re-derived the affected seam in full.
This round's scope is therefore: the changed seam (`resolve_processed_group`, the sync's discovery
query, the collector), the five rows that were owed or newly authored, the six notes, the four
judgment calls, and the perimeter.

## 5. Per-row dispositions — 84 rows

### Plan 9 — 45 rows: 45 PASS

| Rows | Disposition |
|---|---|
| C1(a)–(e), C2(a)–(h), C3(a)–(l), C4(a)–(g), C5(a)–(b), C6(a)–(b), C7(a)–(e), C8(a)–(c) | PASS (44). **Settled in round 1, not re-verified** (§4). None of their files changed except `test_process_items_processed.py`, whose delta is purely additive (+93 lines, two new tests, zero deletions) — no existing row's evidence is touched. Re-confirmed green as a by-product: three of my probe runs show `43 passed` on that file's clean-at-that-point baseline. |
| **C8(d)** | **PASS — was NOT_VERIFIED.** Built to the **owner's restated cell**, not the original: the fixture is a **terminal** (`resolved`) assignment walked there by `_create_at([AWAITING, RESOLVED])`, which is exactly what card 3 restated; the unproducible `in_progress` example is gone. Both sub-checks measured to discriminate — the declared mutation (remove `_assert_allowed_move`) and a **second mutation I added** for the "nothing is written" clause (§8, R-probe 5). |

### Plan 10 — 39 rows: 39 PASS

| Rows | Disposition |
|---|---|
| C1(a)–(l), C2(a), C3(a)–(f), C4(a)–(h), C5(a)–(c), C6(a)–(b), C7(a)–(c) | PASS (35). **Settled in round 1, not re-verified**, with one upgrade: **C2(a)'s delegated evidence now exists.** Round 1's F-3 recorded that the row's declared substitute — "the C4 registry guard refuses a sync call inside the three helpers" — performed no such check. `test_c4i_…` is now that check, and I verified at the site that it is the *same* check the ruling delegated to (the four named helpers, the shared core included). C2(a) is no longer an `UNFORCEABLE` row with no evidence of any kind. |
| **C1(m)** | **PASS — new.** The fixture genuinely carries two non-deleted assignments on one task (A1 `failed`, A2 `in_queue`), both asserted as preconditions, and the task is driven through S1 by the **real** `transition_step_state` command, not a direct call. Outcome cell discharged line by line: A2 → `in_progress`, counters `(0, 4, 0)`, A1 untouched, exactly one `state-changed` for A2 and one `:updated` for R. Armed — the orchestrator reverted the fix at the site and this test alone went red. |
| **C4(i)** | **PASS — new, and now fully discharged.** The row's input cell names **four** plants; the round executed one and the orchestrator a second. **I executed the remaining two** (§8): `_apply_step_transition` (a different file, which also proves `function_contains_call`'s cross-file reach) and `maybe_reopen_task_to_working`. All four bite, each naming its own helper. All four functions exist in the corpus, so no element of the guard's loop is vacuous. |
| **C4(j)** | **PASS — new.** I re-planted all five constructs myself at EOF of `update_task.py`: the guard reddens and names **all five lines individually** (`121`–`125`), which is per-construct discrimination, not an aggregate. No construct is double-collected, so this is informationally equivalent to the cell's "revert each extension in turn" — recorded as such in note N-9 rather than left as an unrun mutation. |
| **C8(a)** | **PASS — was NOT_VERIFIED.** Calls the sync directly, pins the argument shape and the returned event-kind set (`state-changed` ×1, `:updated` ×1, `len == 2`) and deliberately does not re-assert the nine call sites — which is what the cell asks for and what round 1 found the two pre-existing direct-call tests could not do (both assert `events == []`). Mutation tree-matched and consumed; its multi-test bite set is correctly recorded per §9 rule 8. |

## 6. Judgment and adversarial depth on the changed seam

### 6.1 `resolve_processed_group`'s three behaviour changes — judged explicitly

The prompt's first ask. All three are **faithful mirrors of `move_assignment`, not invented
asymmetries**, and none reaches a published contract.

**(i) The `from_state == target` short-circuit.** Placed **before** `_assert_allowed_move`, exactly
as `move_assignment:195-200` places its own. Reachability enumerated: because the target is computed
as `RESOLVED` from `AWAITING` and `RESOLVED_EARLY` otherwise, `from_state == target` is true for
**exactly one** state, `resolved_early`. Every other terminal state (`resolved`, `failed`) falls
through to `_assert_allowed_move` and raises. So the short-circuit is the `'='` cell and nothing
else. **Unreachable from the webhook**: `process_items_processed:139` filters to
`ACTIVE_ASSIGNMENT_STATES` before an assignment can enter the group. **Armed** — the implementer's
mutation is tree-matched, and I corroborated its reported `KeyError` shape by reading
(`_assert_allowed_move` returns on the `'='` cell at `:64`, so the write proceeds and
`_COUNTER_COLUMN[RESOLVED_EARLY]` raises).

**(ii) `if not moved: return []` before the flush — safe.** The caller never passes an empty group
(`moved_by_row` is built only from `moved_assignment_ids`), and no caller relied on the flush: the
flush had no side effect of its own, and `_apply_counter_delta`'s `session.execute` would autoflush
anything pending. Skipping it defers nothing past the command's own commit.

**(iii) The zero-delta guard on the row's `:updated` event — aligned with ratified semantics, and
dead code.** The prompt's sharpest question was whether any consumer depends on that event arriving
unconditionally. **No** — and better than no: **MC-19's own net-change rule already drops a
`:updated` event whose payload equals the row's initial values** (`_events.py:53-93`), so suppressing
a no-op `:updated` is what the ratified coalescer does to it anyway. The grouped webhook path does
not coalesce (it is one call per row by construction), so this guard is that rule's local form.
Separately: with `moved` non-empty the deltas can only be all-zero if every moved assignment has
`quantity == 0`, and `ck_stock_task_assignments_quantity_positive` (`quantity >= 1`) forbids that.
**The branch is unreachable-false on every path.** It is defensive mirroring, and I report it as a
note, not a defect (doctrine rule 2: an equivalent mutant is recorded, never test-demanded).

**Is there a row that would fail if these three were reverted?** Measured, not reasoned (§8):

| Mutant | Result |
|---|---|
| remove `if not moved: return []` alone | **43 passed** — individually equivalent |
| remove the zero-delta guard alone | **43 passed** — individually equivalent |
| remove **both** | **1 failed, 42 passed** — `test_resolve_processed_group_short_circuits_an_assignment_already_at_target` |

So (ii) and (iii) are **jointly load-bearing and individually equivalent** — the "guarded twice, so
no single-site mutant exists" shape the C1 tester named. They did **not** ship unguarded: one
declared test discriminates the pair, and it is declared in plan 9's Review log per rule 16. What is
missing is only the record of *which* mutant bites, which this handoff now supplies.

### 6.2 F-1 is complete, not merely present

The corrected discovery query is the **only** reader of that assignment before the post-lock
re-read, and the re-read reads the same object under lock. Enumerated the whole corpus for the same
shape: the four other queries on `StockTaskAssignment.task_id` are `remove_item_from_task.py:60`,
`delete_task.py:111` (both **deliberately** any-state, MC-14 rows 1–2, and both `.scalars().all()`,
so the singular-selection bug has no analogue), `consistency.py:106` (`expected_task_flag`,
intentionally any-state — it answers "has any assignment", which is the flag's definition) and
`assignment_check_inputs.py:40` (a bulk `in_` projection). **No second stale read.** The post-lock
terminal skip is untouched, as C5(a)/C5(c) require. The full case table of MC-2 step 3 is legal:
`AWAITING → RESOLVED`, `IN_QUEUE → RESOLVED_EARLY`, `IN_PROGRESS → RESOLVED_EARLY` all pass
`_assert_allowed_move` — no false refusal was introduced by the new guard call.

### 6.3 The four judgment calls — checked, not agreed with

1. **C1(m)'s A1 built via `move_assignment` rather than a second Scanner report.** Within the row's
   text, which specifies the *state* and not the provenance. The half the row actually asks to be
   proven — driving T through S1 — **is** the real command. Accepted.
2. **C8(a) drives the sync directly.** The cell says "directly … The contract only". Accepted;
   building it through a call site would have duplicated C1/C4, which the cell forbids.
3. **The registry line fix `292 → 302`.** Verified at the site: line 302 is
   `assignment.state = target` inside `resolve_processed_group`, correctly classified
   `NOT_TASK / StockTaskAssignment`. A mechanical key correction, not a criterion change. Accepted.
4. **C4(j)'s probe sited in `update_task.py` at EOF.** Plan 10 §7 authorizes that file; the file's
   md5 is byte-identical to both the round-1 and this round's pre-probe hash
   (`a9d1d5242e6bf18d7ac35225c13064b9`), which is independent confirmation that no plant was left
   behind by either round. Accepted.

**None touches a published contract** — I checked the concrete question rather than the claim: no
request or response shape, error code, event name or event payload changes. The only externally
visible surface in the diff is the *set* of emitted events, and §6.1(iii) shows that set is
unchanged on every reachable path.

### 6.4 The six notes, checked at their sites (round 1 earned L-33 on exactly this)

| Note | Claimed disposition | True at the site? |
|---|---|---|
| N-1 | traced to C3(g) by docstring, not retired | **Yes.** The cited command-level test `test_c3g_outer_whitespace_matches_and_echoes_untouched` exists at `test_process_items_processed.py:698`. Not a paraphrase. |
| N-2 | no action, per the review's own ruling | **Yes.** No C2-row test surface changed. |
| N-3 | no action, closed by round 1's reading | **Yes.** Nothing built. |
| N-4 | left as is, with a reason | **Yes, and the reason is sound.** `test_c4a_no_sync_and_not_task_entries_carry_their_required_field:101` still asserts only `entry.get("model")` truthiness, and the collector genuinely holds no type information — `WriteSite.detail` is the *unparsed text* of the target expression, never a resolved type. The stated remedy (type inference or a curated allowlist) is correctly sized as out of perimeter. |
| N-5 | folded into C8(d)'s production change, armed | **Yes for the short-circuit; partly for the other two** — see §6.1. The disposition is honest; my measurement refines it. |
| N-6 | left as is, cosmetic | **Yes**, with one correction to my **own** round-1 text: the shared helper C5(b)/C5(c) use is `_run_referee_ordered` (`test_two_writers_on_one_assignment.py:384`), not `_run_forced_order`, which exists nowhere. `test_c5a_…` (`:118`) does still inline the choreography. N-6's substance stands; the citation in round 1's handoff was wrong and is corrected here rather than propagated. |

## 7. Findings

One finding. Severity · route · authority · correction.

### R-1 — SHOULD-FIX · route `plan` · the collector still misses four constructs inside MC-2's own class list, and one outside it

**Authority.** Intention §5B "The guard" (a)–(f) and the owner's card-4 clause, **"collection is by
construct, not by spelling"** (2026-09-21); charter rule 15; the collector's own module docstring
(`_task_state_write_scanner.py:7-17`).

**What is wrong.** I appended one function to `update_task.py` at EOF carrying eleven distinct
writers of `Task.state`: the five C4(j) named, plus six the round did not consider. Guard result —
one run, the assertion enumerates every collected line:

```
BEYO_TEST_SLOT=rv2 PYTHONPATH=. pytest tests/unit/.../test_task_state_write_sites_are_registered.py
→ 1 failed, 6 passed
E  AssertionError: unregistered site(s): [(…update_task.py, 121), (…, 122), (…, 123), (…, 124), (…, 125)]
```

Lines 121–125 are C4(j)'s five — **all collected, the row is genuinely armed**. Lines 126–131 are
absent from the message, i.e. **invisible to the collector**:

| Line | Planted construct | MC-2 class | Why missed |
|---|---|---|---|
| 128 | `Task.__table__.update().values(state=…)` | (c) | callee resolves to `update` but `node.args` is empty — the model is the *receiver*, not an argument |
| 129 | `update(Task.__table__).values(state=…)` | (c) | class (c) requires `isinstance(node.args[0], ast.Name)`; an `ast.Attribute` argument falls through |
| 126 | `for task.state in (…):` | (a) | no `visit_For`; an `ast.For` target is an assignment the collector never walks |
| 127 | `with nullcontext(…) as task.state:` | (a) | no `visit_With`; `withitem.optional_vars` is never walked |
| 131 | `builtins.setattr(task, "state", …)` | (b) | the `setattr` branch requires `isinstance(node.func, ast.Name)`, so a qualified `setattr` is not seen |
| 130 | `Task(**{"state": …})` | **not in (a)–(f)** | class (d) requires a literal `state=` keyword; a `**` splat carries `keyword.arg is None` |

**Why line 128 is the one that matters.** It is not exotic: **this repository's own test suite
already writes `Task.state` that way three times** — `test_create_stock_task_assignments.py:159`,
`test_process_items_processed.py:547` and `:845`, all
`Task.__table__.update()…values(state=…)`. Tests are outside the scanned corpus, so there is no
leak; but it is the form the next production writer is most likely to reach for, because it is the
one already in the team's hands.

**Live impact today: none.** Grepped the whole scanned corpus (`bm/**`, `scripts/**`): the only
`__table__` occurrences are `get_working_section_typical_times.py:71` and
`apply_stock_demand.py:50`, neither a `tasks` write; no `Task(**…)`; no qualified `setattr`; no
`for`/`with` target on `.state`. The 85 registered sites remain correct.

**Why this is `plan` and not a finding against the implementer.** The fix round built C4(j) exactly
as the owner authored it, and built it correctly — I proved that in the same run. Extending the
instrument further means extending the ratified class list, which is **the owner's to author**
(owner card 1). Four of the six sit inside classes (a)/(b)/(c) as already written, so they are a
by-construct shortfall; the fifth (`Task(**kwargs)`) would genuinely be a new clause.

**Correction (owner card 1).** In `_task_state_write_scanner.py`: add `visit_For` and `visit_With`
feeding `_iter_assign_targets`; relax the `setattr` branch to `_resolve_callee`; and for class (c),
accept a first argument that is an `ast.Attribute` whose `.attr` resolves to `Task`/`__table__`,
plus a zero-argument `.update()`/`.insert()` whose receiver resolves to `Task`. The `**kwargs`
constructor is a separate ruling. **Row authoring is the owner's; I propose and do not apply.**

## 8. What I planted, and what it proved

Six runs, all `BEYO_TEST_SLOT=rv2`, all whole-file (never `-k`).

| # | Probe | Site | Result | What it proves |
|---|---|---|---|---|
| 1 | Eleven `Task.state` writers appended at EOF | `bm/services/commands/tasks/update_task.py` | `1 failed, 6 passed`; lines **121–125 named**, 126–131 absent | C4(j) armed per-construct; **R-1**'s six blind spots |
| 2 | Remove `if not moved: return []` | `_move_assignment.py` `resolve_processed_group` | **43 passed** | individually equivalent mutant |
| 3 | Remove the zero-delta `:updated` guard | same | **43 passed** | individually equivalent mutant |
| 4 | Remove **both** (2 + 3) | same | **1 failed, 42 passed** — the N-5 short-circuit test | the pair is jointly load-bearing; one declared test discriminates it |
| 5 | Move `_assert_allowed_move` **after** `assignment.state = target` | same | **1 failed, 42 passed** — `test_c8d_…`, on `RESOLVED_EARLY != RESOLVED` | **C8(d)'s second sub-check ("nothing is written") is armed** — the round declared only the first mutation (rule 12) |
| 6a | Forbidden sync call inside `_apply_step_transition` | `bm/services/commands/task_steps/_step_transition_core.py` | `3 failed, 4 passed`; C4(i) names `_apply_step_transition` | C4(i)'s 4th plant, and cross-file reach of `function_contains_call` |
| 6b | Forbidden sync call inside `maybe_reopen_task_to_working` | `bm/services/commands/tasks/_task_state_transitions.py` | `3 failed, 4 passed`; C4(i) names `maybe_reopen_task_to_working` | C4(i)'s 2nd plant |

(6a/6b's two extra failures are registry line-drift from my mid-file insertion — expected, not a
defect; the C4(i) assertion is the one under test and it names the right helper each time.)

## 9. What I looked for and did NOT find — this is evidence too

- **A seventh *unreachable* form.** I looked for constructs that would let a real `Task.state` write
  escape the guard **and be plausible in this codebase**. Of the six the collector misses, only one
  (`Task.__table__.update()`) has a live idiom behind it; the other five are valid Python nobody here
  writes. I did **not** find a form that escapes the *scan roots* either: `bm/**` and `scripts/**`
  cover every production path, and the exclusions (`tests/`, `migrations/`) are deliberate.
- **A consumer of the unconditional `:updated` event.** I traced the event through
  `coalesce_stock_report_events` and the dispatch path and found no code consumer; MC-19 already
  drops the no-op form. Nothing depends on it.
- **A second stale read behind F-1.** Enumerated all five `StockTaskAssignment.task_id` queries in
  the corpus; none has F-1's shape (§6.2).
- **A false refusal introduced by C8(d)'s new `_assert_allowed_move` call.** All three active
  `from_state` values are legal; the full case table passes.
- **A vacuous element in C4(i)'s loop.** All four helper names exist as real definitions
  (`grep -rn "def <name>"`), so no element passes for want of a target.
- **An orphan test.** The five new tests all trace: four to lettered rows, one
  (`test_resolve_processed_group_short_circuits_an_assignment_already_at_target`) declared in plan 9's
  Review log per rule 16.
- **Over-verification.** C8(a) does not duplicate C1/C4; C8(d) and the N-5 test are one test each for
  one guard each; no same-sign duplicate mutants; no extra stages. Nothing to route as unnecessary
  verification.
- **A criterion-cell edit.** `d72f2e9` is 180 insertions and **zero deletions** across both plans —
  no cell was restated by the implementer.
- **What I did not check:** no L4 of my own (§2, with its authorization line); no condition variation
  (same `TZ`, locale, six xdist workers); no HTTP-layer coverage of either router; no independent
  re-derivation of the 85 registry classifications (N-4 remains the part the guard cannot close for
  itself); no re-verification of round 1's 79 settled rows; phase 8A's files are out of scope and I
  neither reviewed, reverted nor acted on `df09143`.

## 10. Notes — carry-forward dispositions

| Id | Note | Route | Destination |
|---|---|---|---|
| N-7 | The zero-delta `:updated` guard in `resolve_processed_group` is **unreachable-false**: with `moved` non-empty, `ck_stock_task_assignments_quantity_positive` (`quantity >= 1`) forbids an all-zero delta vector. Dead defensive code mirroring `move_assignment`. Correct to keep; recorded so no future round spends a mutation trying to arm it | `production` | closed here (equivalent mutant, doctrine rule 2) |
| N-8 | `test_resolve_processed_group_short_circuits_an_assignment_already_at_target`'s docstring says "the zero-delta guard … means an empty `moved` list returns `[]`". It is the `if not moved: return []` early return that does that, not the zero-delta guard. A one-line docstring paraphrase of a mechanism the same round wrote — the L-33 family at its smallest | `verification` | project cleanup (post-C2) |
| N-9 | C4(j)'s declared mutation is *"revert each of the five collector extensions in turn"*; the round ran the **plant** instead and recorded it in plan 10 §8 as "the row's own shape", without declaring the divergence (rule 14). The two are **informationally equivalent** — the assertion enumerates each line and no construct is double-collected, which I verified — so nothing is owed; the divergence should have been declared | `verification` | closed here, with the equivalence recorded |
| N-10 | C8(d) ships one named mutation for two sub-checks; the "nothing is written" clause — which F-4 specifically called load-bearing — had none. I measured one (§8 probe 5) and it bites on exactly that assertion. Charter rule 12's shape; the row discriminates, only the ledger was short | `verification` | closed here |
| N-11 | C4(i)'s cell names four plants; the round ran one, the orchestrator a second, I ran the remaining two. Row fully discharged, but a round should execute the plants its own row enumerates (rule 2 / manifest property 4) | `verification` | closed here |
| N-12 | `test_task_state_write_sites_are_registered.py`'s module docstring (`:4-8`) still lists **five** collected classes and omits class (f), and `:15` still says "C4(b)-(h), the six required probes" with C4(i)/C4(j) now beside them. The inverse of L-32: here the guard collects *more* than its docstring claims | `verification` | fold with R-1's fix, or a cleanup pass |
| N-13 | `process_items_processed` writes `outcomes[index] = "resolved"` **before** calling `resolve_processed_group`. If the short-circuit ever fired for a webhook entry, Scanner would be told "resolved" for an assignment nothing wrote. Unreachable today (the caller filters to active states, and only `resolved_early` can equal its own computed target). `move_assignment`'s callers read its `[]` return; this caller has already committed the answer. Worth a comment at the call site for the next caller | `production` | plan 13/next stock_report phase touching this command |

## 11. Write perimeter of this session (full)

**Documents written (3, all uncommitted — I made no commit):**
- `SR/handoffs/reviewer/2026-09-21_batch_C2_review_2_handoff.md` (new — this file)
- `SR/plans/plan_9.md` (§8 Review log entry appended only)
- `SR/plans/plan_10.md` (§8 Review log entry appended only)

**Code and tests written: none.** `git diff -- app/` is empty at close; every probe reverted (§12).
**Criterion cells: none touched. Tracker rows: none — §3A reserves them to the orchestrator.**
**`master_plan.md`, the intention: untouched. Architecture graph: no `archgraph_*` call of any kind
— no read, no write, no review decision. No commit, no push, no history rewrite.**

## 12. Mutation-probe declaration

Every probe applied and reverted inside this session; tree `git status --porcelain` empty at close.

| File | Probes | Revert proof |
|---|---|---|
| `bm/services/commands/tasks/update_task.py` | 1 appended EOF block carrying 11 constructs (R-1) — **out of perimeter; plan 10 §7 authorizes probes in this file** | `git checkout --`; md5 `a9d1d5242e6bf18d7ac35225c13064b9` before and after |
| `bm/services/commands/stock_report/_move_assignment.py` | 4 (remove `return []`; remove the zero-delta guard; remove both; reorder `_assert_allowed_move` after the write) — **in perimeter** | `git checkout --` / inverse edit; md5 `b5089815aa87550eaa2c56cfd204d0fa` before and after, matching the fix round's declared hash |
| `bm/services/commands/task_steps/_step_transition_core.py` | 1 (forbidden sync call inside `_apply_step_transition`) — **out of perimeter; not covered by either plan's §7, declared here** | `git checkout --`; `git status --porcelain` empty after |
| `bm/services/commands/tasks/_task_state_transitions.py` | 1 (forbidden sync call inside `maybe_reopen_task_to_working`) — **out of perimeter; not covered by either plan's §7, declared here** | `git checkout --`; `git status --porcelain` empty after |

**Files created and deleted: none.** No probe test file was written this round.

**Database / state side effects:** the four integration runs executed on slot **`rv2`**, whose six
xdist worker databases this session created. Each test seeds and purges its own workspace in
`finally` — including the two runs in which a test failed, whose `finally` purges were observed in
the run log. No row survives. **Standing item for the orchestrator:** slot `rv2`'s six worker
databases now exist, like every other slot's (this project already carries an orphaned-test-DB
cleanup item).

**Commands run this session (6, all slotted):**
1. `pytest tests/unit/.../test_task_state_write_sites_are_registered.py` — R-1's 11-construct plant → `1 failed, 6 passed`
2. `pytest tests/integration/.../test_process_items_processed.py` — `return []` removed → `43 passed`
3. same file — zero-delta guard removed → `43 passed`
4. same file — both removed → `1 failed, 42 passed`
5. same file — `_assert_allowed_move` moved after the write → `1 failed, 42 passed`
6. `pytest tests/unit/.../test_task_state_write_sites_are_registered.py` ×2 — C4(i) plants in `_apply_step_transition` and in `maybe_reopen_task_to_working` → `3 failed, 4 passed` each

**No L4 was taken** (§2 carries the pre-run authorization line).

## 13. Lessons for the plans (the coordinator folds these upstream)

- **L-36 — a mirrored guard is two mutants, not one; measure the pair.** `resolve_processed_group`
  gained two safeguards copied from `move_assignment`. Each is individually an equivalent mutant and
  the pair is load-bearing, so a ledger with one named mutation per addition would have recorded two
  green runs and concluded nothing. **When a repair mirrors a sibling function, enumerate the mutant
  set over the *combination*, not over each added line** — and state which combination bites. (This
  is charter rule 12 read from the other end: rule 12 splits one mutation across sub-checks; this
  splits one sub-check across several mutations.)
- **L-37 — a defensive branch copied from a sibling can be dead at its new site; say so in the
  cell.** The zero-delta guard is unreachable in `resolve_processed_group` because a CHECK constraint
  forbids the only input that reaches it, while in `move_assignment` it is live. Mirroring is the
  right call; **recording the reachability difference is what stops the next round from trying to arm
  it**, and what stops a reviewer from filing it as an unguarded change.
- **L-38 — prove an instrument against the *class list*, then against the *idiom list*.** L-32 already
  said probe sets must come from the contract's classes, not the collector's code — this round did
  that and closed five holes. What it still missed is the form the repository's **own test suite
  already writes three times**. **Add one step to any guard's arming: grep the whole repo, tests
  included, for how the team actually writes the thing being guarded, and plant that spelling.** An
  instrument's real adversary is the codebase's habits, not the specification's taxonomy.
- **L-39 — when a criterion cell enumerates N plants, the round runs N.** C4(i) named four helper
  plants and the round ran one; C4(j) named five reverts and the round ran a differently-shaped
  equivalent without declaring the divergence (rule 14). Neither hid a defect — I ran the rest and
  everything bit — but both left the reviewer buying evidence the round was asked to buy. Manifest
  property 4 should be read as covering a cell's **input enumeration**, not only its mutation column.
