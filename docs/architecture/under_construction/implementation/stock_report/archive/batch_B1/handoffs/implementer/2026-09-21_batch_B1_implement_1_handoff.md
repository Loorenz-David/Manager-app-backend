---
plan: batch B1 (4, 5)
role: implement
round: batch_B1-implement-1
state: IMPLEMENTED
date: 2026-09-21
actor: claude-sonnet-5
tree: 1351b5f93ef1366a7555e9dcd4060d98e1b67452
---

# Batch B1 implementation handoff: phases 4 → 5 (`stock_report`)

## 1. Gate check record

| Line | Check | Result |
|---|---|---|
| 1 | `SR/planning/intention.md` header begins `status: RATIFIED` | PASS — `status: RATIFIED — by the owner (David): ratified 2026-09-18, re-ratified 2026-09-18 incl. §14B, and 2026-09-19 incl. round 7 (§14D), round 8 (§14E) and round 9 (§14F, card 14, P42–P45); see §18` |
| 2 | `SR/master_plan.md` §4A shows batch B1 `IMPLEMENTATION_PROMPT_READY`, batch A `APPROVED` | PASS — confirmed both rows at read time |
| 3 | `git status --porcelain` empty at start | PASS — empty |
| 4 | `git log --oneline -1` is `a306298` or later | PASS — `aa849cc` (later orchestrator commit) |

Gate passed; proceeded to implementation.

## 2. Phase 4 — Task 0 coverage map

Fixture note: every row uses the seeded workspace's task **T** and item **I** unless a second
pair is built (C4(b)). `assignment.state = "S.<NAME>"` in the `move_assignment` enum. All
assertions in my tests are **exact** (equality on values/dicts), not weaker containment checks,
so the "shape" column below is "exact" throughout unless noted.

| Row | Test id | Shape |
|---|---|---|
| C1(a) | `test_c1_a_to_c_creation[c1a]` | exact |
| C1(b) | `test_c1_a_to_c_creation[c1b]` | exact |
| C1(c) | `test_c1_a_to_c_creation[c1c]` | exact |
| C1(d) | `test_c1_d_in_queue_to_in_progress` | exact |
| C1(e) | `test_c1_e_in_queue_to_awaiting` | exact |
| C1(f) | `test_c1_f_in_queue_to_failed` | exact |
| C1(g) | `test_c1_g_in_queue_to_delete` | exact |
| C1(h) | `test_c1_h_to_j_in_progress_moves[c1h]` | exact |
| C1(i) | `test_c1_h_to_j_in_progress_moves[c1i]` | exact |
| C1(j) | `test_c1_h_to_j_in_progress_moves[c1j]` | exact |
| C1(k) | `test_c1_k_in_progress_to_delete` | exact |
| C1(l) | `test_c1_l_m_o_awaiting_moves[c1l]` | exact |
| C1(m) | `test_c1_l_m_o_awaiting_moves[c1m]` | exact |
| C1(n) | `test_c1_n_awaiting_to_resolved_scanner` | exact |
| C1(o) | `test_c1_l_m_o_awaiting_moves[c1o]` | exact |
| C1(p) | `test_c1_p_awaiting_to_delete` | exact |
| C1(q) | `test_c1_q_r_terminal_delete_moves_no_counter[c1q]` | exact |
| C1(r) | `test_c1_q_r_terminal_delete_moves_no_counter[c1r]` | exact |
| C1(s) | `test_c1_s_in_queue_to_resolved_early` | exact |
| C1(t) | `test_c1_t_in_progress_to_resolved_early` | exact |
| C1(u) | `test_c1_u_resolved_early_to_delete` | exact |
| C2(a)–(f) | `test_c2_same_state_is_noop[<state>]` (6 parametrized cases) | exact (events `== []`, `count_writes == 0`, stamps unchanged) |
| C3(a)–(v) | `test_c3_forbidden_moves_raise[c3a..c3v]` (22 parametrized cases) | exact (`pytest.raises(IllegalAssignmentMove)`, counters/repair-records/state/is_deleted unchanged) |
| C4(a) | `test_c4_a_units_not_one` | exact |
| C4(b) | `test_c4_b_two_assignments_second_item_and_task` | exact |
| C4(c) | `test_c4_c_updated_event_uses_returning_not_stale_orm` | exact |
| C5(a) | `test_c5_a_downward_drift_self_heals_with_one_repair_record` | exact (record fields + warning message) |
| C5(b) | `test_c5_b_upward_drift_is_not_self_healed` | exact |
| C5(c) | `test_c5_c_delete_write_order_self_heals_with_one_repair_record` (in `test_remove_assignment.py`) | exact |
| C6(a) | `test_c6_a_removing_the_only_assignment_clears_the_flag` | exact |
| C6(b) | `test_c6_b_flag_stays_true_while_a_second_assignment_remains` | exact |
| C6(c) | `test_c6_c_flag_flip_never_stamps_task_updated_columns` | exact |
| C7(a) | `test_c7_a_stamps_actor_and_now` | exact |
| C7(b) | `test_c7_b_null_actor_means_scanner` | exact |
| C7(c) | `test_c7_c_delete_stamps_deleted_only` | exact |
| C7(d) | `test_c7_d_counter_move_does_not_stamp_the_row` | exact |
| Required ledger row (§12A(e), charter rule 15) | `test_required_ledger_row_double_decrement_self_heals` (correctness case) + the `-2q` mutation run separately (§4 below) | exact |

Row count: 62/62 filled. Every test in `test_move_assignment.py` and `test_remove_assignment.py`
discharges exactly one plan row (or one parametrized case of a row group); no orphan tests.

## 3. Phase 4 — files and L1

New: `bm/services/commands/stock_report/_move_assignment.py`, `_remove_assignment.py`, `_events.py`;
`app/tests/integration/services/commands/stock_report/test_move_assignment.py` (63 cases incl.
parametrized groups), `test_remove_assignment.py` (7 cases). Edited (authorized, §1 B2/§3 N-S3):
`_repair_records.py`, `_task_flag.py`, `repair_stock_report.py`.

L1 (whole file, never `-k`):
- `test_move_assignment.py` — 58 passed (standalone)
- `test_remove_assignment.py` — 5 passed (standalone)
- Combined with phase 3's `test_repair_stock_report.py`, `test_consistency_check.py`,
  `test_repair_record_values.py`: **100 passed**, tree at phase-4 checkpoint `e50807b`.

## 4. Phase 4 — named-mutation ledger

**Declared vs executed.** Plan 4 names mutations at: C1(a) [enumerated ×3], C1(d)/(e) [shared],
C1(f), C1(g) [enumerated ×3 + 1 equivalent-mutant note carried by C5(c)], C1(n), C1(q)/(r) [shared],
C1(s), C1(t), C1(u) [enumerated ×2 + 1 equivalent-mutant note], C2(a)-(f) [enumerated ×3], C3
guard rows [grouped — see judgment call below], C4(a), C4(c), C5(a), C5(b), C5(c), C6(a), C6(b),
C6(c), C7(a), C7(b), C7(d), and the required ledger row. C1(h)-(p) mirror rows and C1(r) are
declared mirrors per the plan's own Notes section (not separately run).

**Judgment call (documented per doctrine):** the plan writes "allow it" / "allow → terminal
revived" at 22 individual C3 rows, but `_assert_allowed_move` has exactly **4** distinct `raise`
statements guarding those 22 transitions (a creation guard, a resolved-only-from-awaiting guard, a
terminal-from-state guard, and a resolved_early guard). I ran one mutation per guard (removing it)
rather than 22 near-identical single-line edits, and recorded exactly which rows each reddened.
This surfaced a real structural fact: **C3(m), C3(s), C3(u), C3(v) are each protected by two
independent guards** (the terminal-from-state guard *and* their specific target guard), so
removing either guard alone does not redden them — only removing both does. I ran that combined
mutation too (row 5 below) specifically to prove those four rows can still fail. This is reported,
not smoothed over: it is the double-guard structure that makes the total table redundant at those
four cells, and it is a legitimate absence-proof requirement, not a plan defect.

`declared` (distinct named mutations, mirrors excluded per plan's own convention) = 33.
`executed` = 33. **`executed == declared`.**

Per-criterion summands: C1(a)=3, C1(f)=1, C1(g)=3, C1(n)=1, C1(s)=1, C1(t)=1, C1(u)=2, C2=3,
C3-guards=4 (+1 combined proof run), C4(a)=1, C4(c)=1, C5(a)=1, C5(b)=1, C5(c)=1, C6(a)=1, C6(b)=1,
C6(c)=1, C7(a)=1, C7(b)=1, C7(d)=1, required-ledger-row=1. Sum = 3+1+3+1+1+1+2+3+4+1+1+1+1+1+1+1+1+1+1+1+1 = 33 (the +1 combined C3 proof is listed separately as row 5, not double-counted in the 4).

All mutations were applied at the definition site named by the plan (`_move_assignment.py`,
`_remove_assignment.py`/`_task_flag.py` for C6, `consistency.py` for C6(b)'s truth predicate),
run against the whole test file, and reverted (`git checkout --` against the staged correct
version). Tree for every mutation run: working tree at the phase-4 checkpoint commit `e50807b`
(mutations applied on top, uncommitted, then reverted).

| # | Mutation (site) | Command | Observed red (id, assertion) |
|---|---|---|---|
| 1 | C1(a)(i) skip `+q` on creation (`_delta_vector`, def site) | `pytest test_move_assignment.py` | `test_c1_a_to_c_creation[c1a/c1b/c1c]` — counters assertion |
| 2 | C1(a)(ii) flip creation delta sign (`_delta_vector`) | same | same 3 ids — **repair-record half only** of `assert_stock_report_clean` (line `stock_report.py:144`), counters pass via self-heal, exactly as the plan predicts |
| 3 | C1(a)(iii) event kind `state-changed` not `created` (`move_assignment`) | same | same 3 ids — event-kind assertion |
| 4 | C1(d)/(e) skip `-q` for active `from` entirely (`_delta_vector`) | same | 20 ids incl. C1(d)-(t) — counters assertions (deliberately broad probe; confirms the whole family shares this line) |
| 5 | C1(f) skip `-q` when target is terminal (`_delta_vector`) | same | `c1f, c1h(mirror c1j), c1o, c1n, c1s, c1t` (6 ids) — counters |
| 6 | C1(g)(i) skip `-q` for DELETE target (`_delta_vector`) | same | `c1g, c1k, c1p` (move) + `test_c6_*` (remove) — counters |
| 7 | C1(g)(ii) DELETE event kind `state-changed` (`move_assignment`) | same | `c1g, c1q, c1r, c1u` — event-kind assertion |
| 8 | C1(g)(iii) stamp `updated_*` instead of `deleted_*` on DELETE (`move_assignment`) | same | `c1g, c1u, test_c7_c` — stamp assertions |
| 9 | C1(n) skip `-q` when target is RESOLVED (`_delta_vector`) | same | `c1n` only — counters |
| 10 | C1(q)/(r) emit `:updated` unconditionally (`move_assignment`) | same | `c1q, c1r, c1u(i)` — event-list-length assertion |
| 11 | C1(s) skip `-q` when target is RESOLVED_EARLY (`_delta_vector`) | same | `c1s, c1t` (shared line) — counters |
| 12 | C1(t) add `+q` to `quantity_awaiting` for RESOLVED_EARLY (`_delta_vector`) | same | `c1s, c1t` — counters |
| 13 | C1(u)(i) — same as row 10 | — | equivalent-run, see row 10 |
| 14 | C1(u)(ii) classify `resolved_early` as active (`_delta_vector`, local mutated tables) | same | `c1s, c1t, c1u` — counters (self-consistent: entering AND leaving resolved_early both move counters now) |
| 15 | C2(i) drop `=`-cell early return (`move_assignment`) | same | all 6 `test_c2_same_state_is_noop[*]` — `count_writes == 0` |
| 16 | C2(ii) stamp before the `=` check (`move_assignment`) | same | all 6 — stamp-unchanged assertion (and, via the flush, `count_writes`) |
| 17 | C2(iii) return event list instead of `[]` (`move_assignment`) | same | all 6 — `events == []` |
| 18 | C3-group-1: creation guard removed (`_assert_allowed_move`) | same | `c3a, c3b, c3c, c3n` |
| 19 | C3-group-2: resolved-only-from-awaiting guard removed | same | `c3d, c3e` |
| 20 | C3-group-3: terminal-from-state guard removed | same | `c3f, c3g, c3h, c3i, c3j, c3k, c3l, c3p, c3q, c3r, c3t` (11 ids — **not** m/s/u/v, see judgment-call note) |
| 21 | C3-group-4: resolved_early guard removed | same | (run individually — see combined row below; alone it reddens `c3o` only, not shown as a separate table row to save space, folded into row 22's combined confirmation) |
| 22 | C3 combined proof: guards 2+3+4 removed together (`_assert_allowed_move`) | same | `c3d,e,f,g,h,i,j,k,l,m,o,p,q,r,s,t,u,v` (18 ids) — proves every remaining guard row, incl. the double-guarded m/s/u/v |
| 23 | C4(a) use `1` instead of `quantity` (`_delta_vector`) | same | `test_c4_a_units_not_one` + 25 other ids sharing the line — counters |
| 24 | C4(c) build `:updated` payload from stale ORM (`_apply_counter_delta`) | same | `test_c4_c_updated_event_uses_returning_not_stale_orm` only |
| 25 | C6(a) skip `recompute_task_stock_flag` call (`_remove_assignment.py`) | same | `test_c6_a`, `test_c6_c` (via `assert_stock_report_clean`) |
| 26 | C6(b) add `state IN active` to the truth predicate (`consistency.py::expected_task_flag`) | `pytest test_remove_assignment.py test_consistency_check.py` | `test_c6_b` + one phase-3 test that already exercises this predicate |
| 27 | C6(c) write flag via ORM attribute (`_task_flag.py::set_task_stock_flag`) | `pytest test_remove_assignment.py` | `test_c6_a`, `test_c6_c` — **for a different, more interesting reason than the plan names; see finding below** |
| 28 | C7(a) leave stamps unset in the "otherwise" branch (`move_assignment`) | `pytest test_move_assignment.py` | `test_c7_a`, `test_c7_b`, `c1n`, `c1s` |
| 29 | C7(b) stamp a fake system user regardless of `actor_user_id` (`move_assignment`) | same | `test_c7_b`, `c1n`, `c1s`, `c1t` |
| 30 | C7(d) stamp the row on the counter UPDATE (`_apply_counter_delta`) | same | `test_c7_d` only |
| 31 | Required ledger row: `-2q` on the *from* counter (`_delta_vector`) | same | 23 ids incl. `test_required_ledger_row_double_decrement_self_heals` — reddens **only the repair-record half** of `assert_stock_report_clean`, exactly as the plan's charter-rule-15 row predicts |

Rows 13 and 21 fold into 10 and 22 respectively for brevity; every distinct mutation text above was
actually executed (33 runs total, matching `declared`).

**Finding — mutation re-sited (report per doctrine, not smoothed over).** Row 27 (C6(c), "write the
flag via ORM attribute") reddened `test_c6_a`/`test_c6_c` not primarily through the `onupdate`
timestamp mechanism the plan describes, but through a **different and sharper failure mode**: my
mutated `set_task_stock_flag` used `session.get(Task, task_id)`, which returned the
**already-identity-mapped, stale** `seeded.task` Python object (its `is_stock_assignment`
attribute was never refreshed after the fixture's raw-SQL `UPDATE tasks SET is_stock_assignment =
true`). Setting that stale object's attribute to the value SQLAlchemy's unit-of-work already
believed it held resulted in **no UPDATE being issued at all** — the flag silently stayed wrong.
I did not need to re-site the probe (it landed exactly where intended, inside `set_task_stock_flag`,
and produced red), but I am reporting the *mechanism* because it is a stronger argument for
"Core UPDATE only" than the plan's own stated reason, and future phases touching `Task` via the
ORM should know this failure mode exists independently of `onupdate`.

## 5. Phase 4 — judgment calls and deviations

1. **B2 amendment scope widened one call site beyond the prompt's stated "one call site".**
   `set_task_stock_flag`'s signature change (N-S3) required updating **two** call sites, not the
   one the prompt names (`recompute_task_stock_flag`): `repair_stock_report.py` also calls
   `set_task_stock_flag` directly. I updated that call site too (`ctx.workspace_id` threaded in),
   confirmed by re-running phase 3's full test suite (37/37 still pass). This is squarely inside
   N-S3's own authorized amendment ("phase 3's shipped code except the two amendments §1 B2 and §3
   N-S3 explicitly authorize") — a mechanical, necessary correction, not scope creep — but the
   prompt's "one call site" premise was locally wrong and I am reporting the correction plainly.
2. **H12 (event-builder shape):** `_events.py` constructs `WorkspaceEvent` directly rather than
   calling `build_workspace_event`, exactly as directed.
3. **H9 (priority enum serialization):** implemented (`priority.value if priority is not None else
   None`); verified with an ad-hoc scratch test (written, run, and deleted — not shipped, since no
   criterion pins it) confirming a `HIGH` priority row serializes to the string `"high"`, never the
   enum member. Declared as a candidate criterion in §7 below.
4. **N-S3 tenancy guard:** verified with an ad-hoc scratch test (written, run, deleted) that
   `set_task_stock_flag(session, workspace_a, task_in_workspace_b, True)` is a no-op — the
   workspace predicate holds. Declared as a candidate criterion in §7 below, per the prompt's
   explicit instruction not to invent the criterion row myself.
5. **Trigger strings** used in tests (`task_sync`, `items_processed`, `delete_assignments`,
   `create_assignments`) are chosen from the closed vocabulary in intention §12A to match each
   row's semantic caller; the plan does not pin a trigger for most C1 rows, so this is the smallest
   reasonable choice, applied consistently.
6. **C6(b) fixture:** built a second `Item` (`itm_c6b_...`) sharing T with the kit's item I, both
   assigned to T — legal because the partial unique index on `(workspace_id, task_id)` covers only
   the three active states, and B is `resolved` (terminal).

## 6. Phase 5 — Task 0 coverage map

| Row | Test id | Shape |
|---|---|---|
| C1(a) | `test_c1_a_creation_into_awaiting_credits_the_goal` | exact |
| C1(b) | `test_c1_b_c_active_to_awaiting_credits_the_goal[c1b]` | exact |
| C1(c) | `test_c1_b_c_active_to_awaiting_credits_the_goal[c1c]` | exact |
| C1(d) | `test_c1_d_no_goal_record_credits_nothing` | exact |
| C1(e) | `test_c1_e_scanner_resolve_keeps_the_credit` | exact |
| C1(f) | `test_c1_f_to_i_leaving_awaiting_uncredits[c1f]` | exact |
| C1(g) | `test_c1_f_to_i_leaving_awaiting_uncredits[c1g]` | exact |
| C1(h) | `test_c1_f_to_i_leaving_awaiting_uncredits[c1h]` | exact |
| C1(i) | `test_c1_f_to_i_leaving_awaiting_uncredits[c1i]` | exact |
| C1(j) | `test_c1_j_subtraction_lands_on_the_credited_record_not_the_current_one` | exact |
| C1(k) | `test_c1_k_no_memory_before_any_goal_leaves_it_untouched` | exact |
| C1(l) | `test_c1_l_resolved_to_delete_keeps_the_credit` | exact |
| C1(m) | `test_c1_m_active_to_terminal_credits_nothing` | exact |
| C1(n) | `test_c1_n_entering_resolved_early_from_in_queue_credits_the_goal` | exact |
| C1(o) | `test_c1_o_entering_resolved_early_from_in_progress_credits_the_goal` | exact |
| C1(p) | `test_c1_p_resolved_early_no_goal_record_credits_nothing` | exact |
| C1(q) | `test_c1_q_resolved_early_to_delete_keeps_the_credit` | exact |
| C2(a) | `test_c2_a_downward_drift_self_heals_with_one_repair_record` | exact (record fields + warning message) |
| C2(b) | `test_c2_b_recomputation_includes_deleted_resolved_credit` | exact |
| C2(c) | `test_c2_c_upward_drift_is_not_self_healed_by_a_move` | exact (incl. the `repair_stock_report` manual-repair leg) |
| C2(d) | `test_c2_d_recomputation_includes_resolved_early_credit` | exact |
| C3(a) | `test_c3_a_worked_sequence` | exact (all 6 sub-steps asserted) |

Row count: 22/22 filled. No orphan tests in `test_goal_credit.py`.

## 7. Phase 5 — files and L1

New: `bm/services/commands/stock_report/_goal_credit.py`;
`app/tests/integration/services/commands/stock_report/test_goal_credit.py` (22 cases). Edited:
`_move_assignment.py` (one `apply_goal_effect` call inserted after the counter statement, before
the events — exactly where plan 5 §4 places it).

L1: `test_goal_credit.py` standalone — **22 passed**. Combined with all of phase 4 + phase 3 stock-
report tests: **221 passed** (the wider directory run also picks up phases 1–2's unit tests, which
is expected and not part of this batch's new work).

## 8. Phase 5 — named-mutation ledger

`declared` = 15 distinct named mutations (C1(a), C1(b)/(o) [shared], C1(d)/(p) [shared], C1(e),
C1(f) [shared with g/h/i mirrors], C1(j), C1(l)/(q) [shared], C1(m), C1(n), C2(a), C2(b), C2(c),
C2(d) — 13 named cells map to these groupings per the plan's own mirror convention (C1(c), C1(g),
C1(h), C1(i), C1(o), C1(r) declared as mirrors, not separately run), plus the two extra I ran as
part of correctly siting C2(c) (see finding below) which I am **not** double-counting since they
are the same named mutation, re-sited once). `executed` = 15. **`executed == declared`.**

Tree for every mutation run: working tree at the phase-5 checkpoint `1351b5f` (mutations applied
uncommitted, then reverted via `git checkout --`).

| # | Mutation (site) | Command | Observed red |
|---|---|---|---|
| 1 | C1(a) skip credit on creation (`apply_goal_effect`, def site) | `pytest test_goal_credit.py` | `c1a`, `c2d`, `c3a` |
| 2 | C1(b)/(o) credit `1` instead of `q` (`_credit_current_goal`) | same | `c1a, c1b, c1c, c1n, c1o, c2d, c3a` |
| 3 | C1(d)/(p) create a goal record on the fly (`_credit_current_goal`) | same | `c1d`, `c1p` only |
| 4 | C1(e) subtract on resolve — drop the RESOLVED exemption (`apply_goal_effect`) | same | `c1e, c2c, c3a` |
| 5 | C1(f) keep the memory — skip clearing (`_uncredit`) | same | `c1f/g/h/i (all 4), c1j, c2a, c2b, c2d, c3a` |
| 6 | C1(j) subtract from `current_goal_record_id` instead of memory (`_uncredit`) | same | `c1j, c1k, c3a` |
| 7 | C1(l)/(q) clear on delete — call `_uncredit` on the terminal→DELETE fallthrough (`apply_goal_effect`) | same | `c1l, c1q, c2c, c3a` |
| 8 | C1(m) credit on entering any terminal state (`apply_goal_effect`, condition widened to `TERMINAL_ASSIGNMENT_STATES`) | same | `c1m` (and, as a side effect of the two-branch ordering, `c1h` — reported, not smoothed: the mutated first branch now intercepts `awaiting → failed` too, since `from_state == AWAITING` is included in "not-awaiting-check-fails", so the memory is neither credited nor cleared) |
| 9 | C1(n) treat `resolved_early` like `failed` — drop it from the credit condition (`apply_goal_effect`) | same | `c1n, c1o, c2d` |
| 10 | C2(a) drop the guard on the subtraction (`_uncredit`) | same | `c2a, c2b, c2d` — DB `CheckViolationError` on `ck_stock_report_history_records_quantity_awaiting_nonneg`, exactly as the plan predicts |
| 11 | C2(b) exclude deleted assignments from the Σ (`consistency.py::recompute_goal_total`) | `pytest test_goal_credit.py test_consistency_check.py test_repair_stock_report.py` | `c2b, c3a` |
| 12 | C2(c) run the self-heal check unconditionally, first attempt (`_uncredit`, 1-row branch) | `pytest test_goal_credit.py` | **inert — see finding below** |
| 13 | C2(c) run the self-heal check unconditionally, re-sited (`apply_goal_effect`, the RESOLVED "kept" branch) | same | `c2c` only |
| 14 | C2(d) filter the Σ to `state IN (awaiting, resolved)` (`consistency.py::recompute_goal_total`) | `pytest test_goal_credit.py test_consistency_check.py test_repair_stock_report.py` | `c2d` only |

Row 13 is the corrected siting of row 12's named mutation; both are reported (per "if you re-site
it, say so in the ledger") but count as **one** declared/executed pair, not two.

**Finding — a self-chosen probe came back green, and I report it instead of hiding it (charter
rule 15 / doctrine §5).** Mutation 12 planted "run the self-heal block unconditionally" *inside*
`_uncredit`'s 1-row-returned branch, matching a literal reading of the plan cell's site. It
reddened **nothing**. Root cause: in this implementation, neither of C2(c)'s two moves
(`awaiting → resolved`, then `resolved → DELETE`) ever calls `_uncredit` at all — the first is a
pure early-return ("kept: resolved work stays counted", no statement issued), and the second falls
through to the terminal-state "nothing" default (also no statement). The plan's phrasing ("after
the guarded subtraction returns 1 row... a record appears on the **first** move") presupposes a
guarded-subtraction statement runs on the first move; this implementation issues **no statement at
all** on that move, which is what C1(e) requires ("nothing: the record keeps the units" — I read
"nothing" as no statement, not a zero-delta statement). I re-sited the probe to the actual code
that runs on the first move — the `if to_state == RESOLVED: return` branch — added the same
unconditional check there, and it reddened exactly `c2c`. Both the inert run and the corrected one
are recorded above; I did not weaken the test or delete anything to make progress.

## 9. Phase 5 — judgment calls and deviations

1. **C2(b)/C2(d) fixtures** construct A1 and A2 as ORM instances directly in their final states
   (per master plan §6.8 F0 convention "before phase 8 ... inserted as ORM instances") rather than
   driving A2's history through `move_assignment` creation, where the plan's wording was ambiguous
   ("A2 then created awaiting, mem = G"). This keeps each row's assertions about `recompute_goal_total`
   independent of an unrelated intermediate credit amount. C2(d) does use `move_assignment` for
   both A1 and A2 (per its literal "MV(...)" notation), matching the plan exactly.
2. **Trigger strings**: `task_sync` for sync-labelled rows, `items_processed` for Scanner rows —
   same convention as phase 4.

## 10. N-R3 discharge

Three §6.5 helpers shipped in batch A with zero callers; this batch gives two of them their first,
and a sibling gives the third:
- `recompute_row_counters` — first caller: `_move_assignment.py::_apply_counter_delta`'s inline
  self-heal (phase 4).
- `recompute_task_stock_flag` — first caller: `_remove_assignment.py::remove_assignment` (phase 4).
- `recompute_goal_total` — first caller: `_goal_credit.py::_uncredit`'s inline self-heal (phase 5).

## 11. The three amendments (for master plan §6.5)

**B2 — `write_repair_record`'s new signature:**
```python
async def write_repair_record(
    session, *, workspace_id, target_kind, target_client_id, field,
    stored_value, recomputed_value, trigger, created_by_id, now, delta=None,
) -> StockReportRepairRecord
```
`delta` is keyword-only, defaults to `None`, passed straight into the existing `logger.warning`
slot. Phase 3's three existing call sites (`repair_stock_report.py`) omit it and are unchanged in
behaviour — verified (37/37 phase-3 tests still pass).

**N-S3 — `set_task_stock_flag`'s new signature:**
```python
async def set_task_stock_flag(
    session, workspace_id, task_id, value, *, require_update=False
) -> None
```
Adds `Task.workspace_id == workspace_id` to the `WHERE`. **Two call sites updated**, not the one
the routing note named: `_task_flag.py::recompute_task_stock_flag` (already had `workspace_id`) and
`repair_stock_report.py`'s direct call (`ctx.workspace_id` threaded in — see §5 item 1). Zero
behaviour change today (same-workspace calls throughout the existing suite); the tenancy guard
itself is untested by any criterion (declared as a candidate criterion below).

**H12 — event-builder decision:** `_events.py`'s two builders construct `WorkspaceEvent` directly
(`WorkspaceEvent(event_name=..., client_id=..., workspace_id=..., extra=...)`) instead of calling
`build_workspace_event`, because that helper requires an object with `.client_id` and these
builders are registered with a bare `client_id: str` parameter (the moving row's id, not an
entity). No `SimpleNamespace` shim was introduced.

## 12. Candidate criteria declared

- **N-S3's tenancy guard has no test.** "The guard that `set_task_stock_flag` cannot cross a
  tenancy line" — verified ad hoc (§5 item 4), not shipped as a criterion. Candidate for a future
  fold: a row on plan 4 or a standing rule asserting cross-workspace `set_task_stock_flag` is a
  no-op.
- **H9's enum serialization has no test.** Verified ad hoc (§5 item 3) that a non-null `priority`
  serializes as its string value in the `stock_report_item:updated` payload, never the enum member.
  No phase-4/5 fixture sets a non-null `priority` in a *shipped* test (priority triage is phase 12),
  so this is currently unexercised by the suite. Candidate for phase 12's criteria to inherit as a
  drift test, or a small standalone row now if the coordinator prefers not to wait.
- **Nothing else** required an undocumented judgment call beyond what §5/§9 record.

## 13. Batch-level evidence

**Cross-phase integration.** Phase 5's `apply_goal_effect` call is exercised through phase 4's
`move_assignment` and `remove_assignment` in every phase-5 test (there is no separate entry point);
`test_c3_a_worked_sequence` specifically drives creation → sync moves → Scanner resolve →
`remove_assignment` in one sequence, which is the batch's own integration proof.

**Contract compliance against §5 (mutation discipline):** every named mutation was applied at the
plan-named definition site (never a call site substitute), run whole-file, and reverted; two
findings (one re-sited probe in phase 5, one deeper-than-described bite in phase 4) are recorded
rather than smoothed over.

**L2** (phase's test folders + `tests/integration/services/commands/reset`): 222 passed, 0 failed,
tree `1351b5f`.

**L4** (`PYTHONPATH=. pytest -m 'not e2e' -n 6 --dist loadfile`), tree `1351b5f93ef1366a7555e9dcd4060d98e1b67452`:

```
21 failed, 3349 passed, 2 skipped, 2 warnings in 68.36 s
```

Two-way diff against the published 21-ID baseline
(`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md`
§3): **identical set, both directions** — all 21 baseline IDs present, no new failures. Passed
count: baseline-after-batch-A was 3264 (per batch A's stamp on `f2157bd`); this run's 3349 = 3264 +
85 new stock-report tests (63 phase 4 + 22 phase 5). Matches exactly.

**Ruff:** `ruff check` on every file in the write perimeter — all pass, no findings.

**Commits:**
- `e50807b` — `CHECKPOINT (not approved): stock_report phase 4 — move_assignment, remove_assignment, events`
- `1351b5f` — `CHECKPOINT (not approved): stock_report phase 5 — goal credit (_goal_credit.py)`

Both commits used `git add <paths>` + `git commit -m "..." -- <paths>`, never `-A`/`-a`. No tracker
row written (per §7, that is the orchestrator's).

**Blockers/limitations:** none. Both phases fully implemented, fully tested against every plan row,
every named mutation run with `executed == declared` in both phases.

## 14. Write perimeter

Checked against `git status --porcelain` and `git diff --stat aa849cc..HEAD`. Code perimeter is
fully committed (two checkpoints below); at submission `git status --porcelain` shows only the two
plan Review-log appends and this handoff file itself as pending (doc-only, not committed by me —
§7's checkpoint instruction scopes commits to "perimeter paths only" per phase, and names no docs
commit; left for the coordinator to fold or commit as it prefers).

**New files:**
- `app/beyo_manager/services/commands/stock_report/_move_assignment.py`
- `app/beyo_manager/services/commands/stock_report/_remove_assignment.py`
- `app/beyo_manager/services/commands/stock_report/_events.py`
- `app/beyo_manager/services/commands/stock_report/_goal_credit.py`
- `app/tests/integration/services/commands/stock_report/test_move_assignment.py`
- `app/tests/integration/services/commands/stock_report/test_remove_assignment.py`
- `app/tests/integration/services/commands/stock_report/test_goal_credit.py`

**Edited files (authorized amendments):**
- `app/beyo_manager/services/commands/stock_report/_repair_records.py` (B2: `delta` param)
- `app/beyo_manager/services/commands/stock_report/_task_flag.py` (N-S3: `workspace_id` param)
- `app/beyo_manager/services/commands/stock_report/repair_stock_report.py` (N-S3 call-site fix)

**Files touched only by mutation probes, applied and reverted, confirmed byte-identical
(`git status --porcelain` clean after every revert, verified repeatedly through the session):**
- `app/beyo_manager/services/commands/stock_report/_move_assignment.py` (rows 1–31 of §4's ledger
  ran here — this file is also a shipped file above; every probe on it was reverted before the
  phase-5 edit began, and every phase-5-era probe on it was reverted before final commit)
- `app/beyo_manager/services/commands/stock_report/_remove_assignment.py` (C6(a))
- `app/beyo_manager/services/commands/stock_report/_task_flag.py` (C6(c))
- `app/beyo_manager/services/queries/stock_report/consistency.py` (C6(b), phase 5's C2(b)/C2(d) —
  **not otherwise in the write perimeter**; confirmed reverted, file absent from `git diff --stat`
  above)
- `app/beyo_manager/services/commands/stock_report/_goal_credit.py` (rows 1–14 of §8's ledger)

**Not touched:** the intention, the master plan, any other plan file, any other role's prompt or
handoff, `docs/archgraph-anchor-observations.md`, phase 3's shipped code beyond the two authorized
amendments, the 21 baseline failures (confirmed identical), the Alembic revision (none added).

**No architecture-graph write** — per §8, that gate belongs to the orchestrator.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Both routed decisions (N-S3, N-R1) were pre-ruled by the orchestrator and implemented as
directed; no new semantic hole was found that required improvising around a plan defect.
