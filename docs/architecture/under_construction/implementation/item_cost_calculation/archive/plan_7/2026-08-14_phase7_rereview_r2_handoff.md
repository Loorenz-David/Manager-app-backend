---
plan: phase 7 (evaluations — commit/supersede, projections, auto-commit)
role: review
round: 2 (re-review after fix r1)
verdict: APPROVED
date: 2026-08-14
actor: reviewer (Claude Opus 5)
---

# Phase 7 re-review r2 handoff

**Verdict: APPROVED** — 0 blocking, 1 should-fix (routed below), 3 notes.

All 13 round-1 findings are closed, and closed the way the charter asks: every
one was verified by re-running the arbiter that was green-or-absent in r1 and is
red-or-present now. Five of the seven declared mutant hashes **reproduce
byte-for-byte** from my own independent application of the named mutation — the
first time in this project's history that a fix cycle's mutation ledger has been
re-derivable rather than merely re-confirmable.

The one remaining should-fix is a two-word documentation error in the P-AB
effect enumeration. It changes no behaviour, and it is routed to the closeout
commit rather than a fix cycle.

⚠ OWNER DECISIONS REQUIRED (0) — nothing needs an owner answer.

## Review history (what earlier rounds settled)

- **projection r0** — 23 rows, all routed into A1–A5.
- **implement r1** — the procedure shipped; concurrency mutations deferred.
- **review r1** — 3 blocking / 5 should-fix / 8 notes. B1 (projection mirror)
  was the only behavioural defect; B2/B3 were proof gaps; S1/S2/S3 were plan
  defects the deferred mutation pass exposed.
- **fix r1** — this round's subject.

Settled and NOT re-verified here: the §7B.1 step order, the §6.4 translations,
C1/C3/C6/C7/C9/C13/C14 semantics, the P-Z extraction, §10 environment facts.
All were re-derived in r1 and their arbiters ran green in every suite pass this
session. Anything seen wrong in passing is reported below.

---

## Perimeter verification (charter re-review step 1)

`git show --stat bb233db` = **10 files**, matching the declaration exactly:

- 4 production: `commit_item_cost_evaluation.py`,
  `promote_item_cost_projection.py`, `requests/__init__.py`, `create_task.py`
- 4 verification: `test_phase7_criteria.py`, `test_phase7_concurrency.py`,
  `test_phase7_evaluations.py`, `test_item_economics_requests.py`
- 2 planning records

`git diff bb233db..HEAD -- app/` is **empty**. All five declared final hashes
match the working tree, including the router's unchanged baseline
`87fcb318…40ae`. **Nothing outside the fix fence changed.** The one declared
delegation (F4's translation row extending the existing unit file instead of a
new one) is present, is +1 line, and is the correct call — a duplicate file for
one parametrize row would have been worse.

Production diff read hunk by hunk: the F1 kind gate, the P-AB docstring, the N2
docstring correction, the F7 branch deletion, the N1 validator deletion, the N8
whitespace. Nothing else. No migration.

---

## Findings ledger

| id | sev | title | disposition |
|---|---|---|---|
| R2-S1 | should-fix | P-AB enumeration names an effect `kind` does not gate (the audit row) | routed to closeout commit |
| R2-N1 | note | Anchor drift: 13 held graph items need +4 in `commit_item_cost_evaluation.py` | routed to the held graph pass |
| R2-N2 | note | C10's visibility assertion is loop-guarded and could go vacuous | routed to phase 8 |
| R2-N3 | note | N8 over-applied — zero blank lines where one reads better | recorded only |

### R2-S1 (should-fix) — the P-AB enumeration lists an effect `kind` does not gate

The new docstring (`commit_item_cost_evaluation.py:202-206`) and plan **F1**
both enumerate the `kind`-gated effects as: *chain S1 close scope,
`committed_at`, the valuation mirror, the history record, **the audit row**, and
the pending event.*

The audit row is **not** gated on `kind`. `await audit(...)` at line 379 runs on
every path; what varies is the `audit_event` **parameter** the caller supplies —
`create_item_cost_projection.py:74` passes `item_cost_evaluation.projected` and
`promote_item_cost_projection.py:46` passes `.promoted`. §6.4's registered audit
vocabulary requires exactly this: `.committed` / `.projected` / `.promoted` /
`.deleted` are four distinct registered events, so a projection **must** write an
audit row.

The error points the wrong way: a reader consulting the enumeration to answer
"do projections write an audit row?" would conclude *no*, and be wrong.

**Verified gated set** (exhaustive — every `kind` reference in the file):

| line | effect |
|---|---|
| 272–292 | chain S1 close scope (previous-row read + supersede UPDATE) |
| 319 | `committed_at` |
| 346 | the valuation mirror (F1's new gate) |
| 361 | the history record |
| 386 | the pending event |

Five effects. Line 298 (`kind=kind`) is the stored column value, not a gated
effect.

**Correction (two places, no code change):** drop "the audit row" from the
docstring at `commit_item_cost_evaluation.py:204-205` and from plan F1's
sentence, and add one clause: *the audit row is written on every path under a
caller-supplied `audit_event`.*

Authority: **P-AB** (the rule review r1 earned) — "when a helper is
parameterised by kind, the plan enumerates which effects that parameter gates,
one line per effect; anything unlisted is a finding." The converse binds too: an
enumeration that lists an effect the parameter does *not* gate is the same
defect wearing the other sign. This shipped in the very cycle that created the
rule, which is worth recording as a lesson (L1 below).

### R2-N1 (note) — anchor drift for 13 held graph items

The F1 docstring grew from 1 line to 5, shifting everything at or below line 203
in `commit_item_cost_evaluation.py` by **+4**. The 13 pending graph items
anchored in that file now carry stale spans:

| items | recorded | corrected |
|---|---|---|
| the 12 edges on `_commit_item_cost_evaluation_in_session` (8 `reads_from`, 3 `writes_to`, 1 `produces`) | `203–355` | **`207–359`** |
| `node:command-item-economics-commit-item-cost-evaluation` | `187–388` | **`187–392`** (start unchanged; `def` is still at 187) |

Rule: **any recorded line ≥ 203 in this file gains +4.**

Not a blocker: `staleNodeCount` is 0, the tool reports no diagnostics, every
claim remains true, and the recorded spans still overlap their evidence. The
graph is READ-ONLY until the post-approval pass, which re-anchors anyway — this
table is the spans service for that pass.

### R2-N2 (note) — C10's visibility assertion could go vacuous

In `test_phase7_evaluations.py`, the fake dispatch asserts second-session
visibility inside a guard:

```python
for event in events:
    if "evaluation_id" in event.extra:
        assert await verify_session.scalar(...) is not None
```

If the `extra` key were ever renamed, the guard would stop matching, the
assertion would silently stop running, and the sibling
`count("item_economics:evaluation-committed") == 1` would still pass — the event
*name* is unchanged. Charter rule 2's non-vacuity question (and **P-J third
extension**: a property over a discovered set owes a non-vacuity row).

Non-vacuous today; hardening is one line (`assert checked == 1` after the loop).
Routed to **phase 8**, which inherits this seam.

### R2-N3 (note) — N8 over-applied

The fix removed **both** blank lines at `create_task.py:307-308`, so
`await ctx.session.flush()` now abuts `auto_events: list = []` with no
separation. N8 asked for the *double* blank line. Ruff-clean, purely cosmetic,
recorded only — not worth a cycle.

---

## r1 finding closure — verified one by one

| r1 id | closed by | how I verified it |
|---|---|---|
| **B1** blocking | F1 kind gate | `test_probe_c5_row_7_projection_override_must_not_touch_the_valuation` passes on the shipped tree (r1's exact scenario: scratch projection, override 2000 vs valuation 1000 → one valuation row, unchanged `client_id` **and** figures). F1 mutation reddens **exactly** that node, nothing else. Mutant hash reproduces the declaration byte-for-byte. |
| **B2** blocking | F2 adoption | Line-by-line `diff` of both adopted files against the preserved sources. **Zero assertions weakened or deleted.** The only removals: one function rename, one assertion line *split into three stronger ones*, one `])` replaced by an ids block, and the F4-authorised deletion of the C2 test with its now-unused imports. Integration nodes 4 → 42. |
| **B3** blocking | F3 two-session harness | `test_phase7_c8_promotion_projection_row_unchanged_across_sessions`: fixture committed, `before_session` and a **freshly created** `after_session` each read all columns; same-session assertion deleted from the monolith. Verified it *bites* (M10). |
| **S1** should-fix | F4 | Direct-INSERT test deleted wholesale. Translation unit row present — and verified **discriminating** (M8). |
| **S2** should-fix | F5 | Counterparty is now `FOR NO KEY UPDATE`. M1 reddens exactly the C11 node; hash reproduces. |
| **S3** should-fix | F6 | Blocking commit carries no override. M2 reddens exactly the C5r6 node; hash reproduces. |
| **S4** should-fix | F9 | My foreground numbers match the declaration exactly (below). Tracker corrected. |
| **S5** should-fix | F7 | Dead `task_client_id` branch gone from `promote_item_cost_projection.py`. Cross-**workspace** promote → `NotFound` row present in `test_probe_c8_promotion_rows`. |
| **N1** | F8 | Validator deleted; `field_validator` still used at 6 other sites, so no unused import. |
| **N2** | F8 | Docstring now says "it raises". Accurate. |
| **N3** | F8 | `test_phase7_c9_row_10_no_primary_item_logs_literal_status` asserts `status=no_primary_item`; registered in §6.5. |
| **N4** | F8 | Discrimination claim deleted; exactly-once + second-session visibility asserted (see R2-N2). |
| **N7** | F8 | Both back-links assert the **exact** successor id. Verified it bites (M9). |
| **N8** | F8 | Applied (see R2-N3). |
| **N5 / N6** | F9 | Correctly held / routed, not silently dropped. |

---

## Row-coverage map (C1–C14 as amended by A3/A4 + F1–F8)

Every row now has an observed node id. Ids name their authority row per P-V.

| row | arbiter |
|---|---|
| C1 immutability + rederive | `test_phase7_criteria.py::test_probe_c1_snapshot_immutability_after_superseding_everything` |
| C1 row 1b (persisted ≠ derived) | `test_phase7_evaluations.py::test_phase7_commit_projection_promotion_and_read` (M5) |
| C2 second commit / one current / back-link | `test_phase7_criteria.py::test_probe_c2_second_commit_leaves_one_current_and_backlinks` |
| C2 DB conflict path | discharged: P-S note + `INDEX_IDENTITIES` + `test_item_economics_requests.py::test_integrity_translation_preserves_each_registered_index_identity[uix_item_cost_evaluations_current-ITEM_COST_CONCURRENT_COMMIT]` (M8) |
| C3 rows 1–8 + deleted | `test_probe_c3_admitted_states[C3-row-1-PENDING … row-5-READY]`, `test_probe_c3_terminal_states[C3-row-6-RESOLVED … row-8-CANCELLED]`, `test_probe_c3_deleted_task` |
| C4 | `test_probe_c4_no_primary_item` |
| C5 rows 1–3 | `test_probe_c5_override_writes_mirror_on_explicit_commit`, `test_probe_c5_none_equals_none_writes_no_mirror` |
| C5 row 4 (auto path never mirrors) | by construction + `test_phase7_create_task_auto_commits_and_dispatches_after_task_transaction` |
| C5 row 6 (committed mid-flight) | `test_phase7_concurrency.py::test_probe_c5r6_commit_blocked_while_valuation_locked` (M2) |
| **C5 row 7 (projection must not mirror)** | `test_probe_c5_row_7_projection_override_must_not_touch_the_valuation` (F1) |
| C6/C7 rows 1–10 | `test_probe_c6_c7_refusal_rows[C6-C7-row-1-… … row-10-currency_mismatch_basis_vs_model]` |
| C8 byte-unchanged (2 sessions) | `test_phase7_c8_promotion_projection_row_unchanged_across_sessions` (M10) |
| C8 refusals + delete | `test_probe_c8_promotion_rows` (soft-deleted, terminal task, cross-workspace), `test_probe_c8_delete_projection_never_touches_committed` |
| C9 success | `test_phase7_create_task_auto_commits_and_dispatches_after_task_transaction` |
| C9 skip rows | `test_probe_c9_auto_commit_skipped_line_for_unvalued_item`, `test_phase7_c9_row_10_no_primary_item_logs_literal_status` |
| C9 savepoint | `test_phase7_auto_commit_overflow_rolls_back_savepoint_and_keeps_task` (M7) |
| C10 event/history/audit/nothing-on-failure | `test_probe_c10_history_reaches_task_flow_and_audit_row_exists`, `test_probe_c10_nothing_fires_on_a_failed_commit`, exactly-once + visibility in the auto-path test |
| C11 task lock | `test_probe_c11_second_commit_blocked_while_task_locked` (M1) + `test_probe_c11b_two_concurrent_commits_both_succeed_via_the_task_lock` |
| C12 row 1 × 2 chains | `test_probe_c12_row1_delete_first_commit_blocks_then_refuses[C12-row-1-BASIS \| C12-row-1-MODEL]` (M3/M4) |
| C12 row 2 | phase 4's `test_c6_serial_delete_guard_rechecks_all_evaluation_references` |
| C13 | 20 role-gate nodes + `test_router_route_pairs_match_the_authoritative_route_table` (M6) |
| C14 | `test_probe_c14_ordering_pins` + the marker row in the monolith |

**No row is without an arbiter.**

---

## Mutation ledger

Baseline (= `bb233db` blobs): `commit_item_cost_evaluation.py`
`4df51dcb…c596e` · `promote_item_cost_projection.py` `c65735e1…b12ab` ·
`requests/__init__.py` `a71379b7…12aad` · `create_task.py` `25cc3420…ca8e7` ·
`item_economics.py` `87fcb318…840ae` · `_common.py` `97662825…1a8e8`.

| # | row | mutant hash | vs declared | observed red set |
|---|---|---|---|---|
| F1 | mirror kind gate | `cea28666827471fc7e8e5b1d42c14a0522a4777e0c189e8681772e1cb11b9f24` | **exact match** | `test_phase7_criteria.py::test_probe_c5_row_7_projection_override_must_not_touch_the_valuation` — 1 node |
| M1 | task `FOR UPDATE` | `50e207f5be14b8fe1568065339973962a0158f18a409d58b0fc19c0a0215850f` | **exact match** | `test_phase7_concurrency.py::test_probe_c11_second_commit_blocked_while_task_locked` — 1 node |
| M2 | valuation `FOR UPDATE` | `893be91da0d81a0f12b8d1b8ad3a35adb44776f4d25d47a85c7de4231f47d188` | **exact match** | `test_phase7_concurrency.py::test_probe_c5r6_commit_blocked_while_valuation_locked` — 1 node |
| M3 | basis `read=True` | `a8e12a29ca62d8903655b17cece82f66c3d4e3b4e0b966d69725cbdc5d7664ba` | **exact match** | `…test_probe_c12_row1_delete_first_commit_blocks_then_refuses[C12-row-1-BASIS]` — **row 1 only**; `[C12-row-1-MODEL]` green |
| M4 | model `read=True` | `3b29a3c7c149aa7d90885e4ea2459b86c685661cd31a43be61554c22100d8b26` | **exact match** | `…[C12-row-1-MODEL]` — **row 1 only**; `[C12-row-1-BASIS]` green |
| M5 | snapshot source swap | `40f8718250d50a329fc35a458fb1d8b01e3e6f71877be6c4130ea3e7e9fa4007` | **exact match** | `test_probe_c1_snapshot_immutability_after_superseding_everything`, `test_phase7_commit_projection_promotion_and_read` |
| M6 | route without `_ROUTES` row | `28dc95698b1aa226b2102d129242842a36baf3e70c7e1d160c5d29ab3d903c9a` | differs (mutant text) — verified behaviourally | `test_router_route_pairs_match_the_authoritative_route_table` |
| M7 | savepoint → `if True:` | `999788369bcfe2aa961a4c376577e70139d6e04460d4c057f4dffe2d0cff7fec` | **exact match** | `test_phase7_auto_commit_overflow_rolls_back_savepoint_and_keeps_task` (SAWarning: non-active transaction) |

Three reviewer-authored mutations, to test the *new* rows rather than re-confirm
old ones:

| # | row | site | mutant hash | observed red set |
|---|---|---|---|---|
| M8 | F4 translation row | `_common.py` — `INDEX_IDENTITIES` key → `…_current_TYPO` | `037f92a051618304c660fc4060ed868c6c5037dd3ccf47d0329d2ac72c1929d0` | `test_integrity_translation_preserves_each_registered_index_identity[uix_item_cost_evaluations_current-ITEM_COST_CONCURRENT_COMMIT]` — 1 node; the other 4 index rows stayed green |
| M9 | N7 exact successor | `_common.py` — chain writer back-links to `old.client_id` | `95975c51a5effac804c422caf1a9ce442055d507d7466ffe93e5f3e8e31c73fe` | `test_phase7_extracted_valuation_chain_preserves_set_supersede_delete_invariants` **+** phase-5's `test_valuation_surface.py::test_valuation_chain_preview_delete_and_history` |
| M10 | B3 second-session check | `promote_item_cost_projection.py` — `projection.updated_by_id = ctx.user_id` | `9b78f61bb54c1ab4e71e99f2b0b2f41a9900517790a98f93fc884882cc56be88` | `test_phase7_c8_promotion_projection_row_unchanged_across_sessions` — 1 node |

M8/M9/M10 each redden the row the fix cycle *added*, which is the P-I question
("do the new rows bite?") answered rather than assumed.

**Reversion proven.** Every file restored and re-hashed to the baseline above;
`git diff -- app/` is **empty** and `git status --porcelain` shows only my
handoff deposit and the two planning-record edits.

---

## Numbers (R2-P6)

Read off my own foreground runs:

| set | mine | declared | verdict |
|---|---|---|---|
| full non-E2E | **2076 passed / 23 failed / 1 deselected** | 2076/23/1 | ✅ |
| committing concurrency subset (run 1 / run 2) | **5 / 5** | 5 twice | ✅ |
| phase-5 valuation + request surface | **55** | 55 | ✅ |
| phase-7 surface as I ran it (3 integration files + router + requests unit) | **170** | 82 | different **set**, not a discrepancy — the fix's 82 = 42 integration + 40 requests-unit; mine adds the 88 router nodes. Both reconcile. |

**Failure set byte-identical** to the phase-1 list: sorted diff over 23 entries,
zero differences.

**Delta reconciliation (+39), exact:** 2076 − 2037 = **+39** = phase-7
integration 4 → 42 (**+38**) + `test_item_economics_requests.py` **+1**. No
node is unaccounted for.

Ruff on the full perimeter: **All checks passed.**

---

## Write perimeter and probe declaration

**Documents written this session (the entire perimeter):**

- `docs/.../plans/phase_7_evaluations.md` — Review log entry appended; header
  `state:` → `APPROVED`
- `docs/.../master_plan.md` — §4 tracker row 7 only
- `docs/.../handoffs/reviewer/2026-08-14_phase7_rereview_r2_handoff.md` — this
  file

**No production or test file was left modified.** All ten mutations
(F1, M1–M7, M8–M10) were applied in the main worktree and reverted; the six
touched files re-hash to their `bb233db` blobs, listed above. I wrote no new
test files this round — the fix cycle adopted r1's probes, so the arbiters I
needed were already in the tree.

**Database side effects — restored exactly as found.** All eight economics
tables were 0 rows before my session and are **0 rows after**. `workspaces`
moved 8207 → 8323 = **+116 over one full non-E2E run**, exactly the known
non-economics class (§10; phase-4 r3 N11). **Residue scope: the eight economics
tables plus `workspaces`/`users`/`tasks`/`working_sections`** — the committing
concurrency subset was run twice and left zero economics rows both times.
Configured DB left at head `be9dfe42a035`; no migration added or run.

**Architecture Graph — READ-ONLY, zero delta.** Exit state: valid, **166 nodes /
239 edges**, 0 stale, **52 pending**, revision
`0a71061554fa2123d7e2fba7ff853c328fb1405676194dd0d2cc7f067938266c` — identical
to entry and to the fix's declaration. **Nothing adjudicated, promoted,
rejected, edited or removed.** The anchor-drift spans service for the 13 items
the fix moved is in R2-N1.

---

## Carry-forward dispositions

| item | destination | why |
|---|---|---|
| **R2-S1** — P-AB enumeration drops "the audit row" (docstring + plan F1) | **phase-7 closeout commit** (coordinator applies) | Two-word documentation correction in two artifacts; no code, no test, no re-review. Blocking the gate on it would cost a full cycle for a comment. |
| **R2-N1** — anchor spans +4 for 13 items | **the held post-approval graph pass** | Rides with N5; that pass re-anchors as a matter of course. |
| **R2-N2** — C10 seam non-vacuity guard | **phase 8** | Phase 8 inherits the seam; one-line hardening. |
| **R2-N3** — blank line | none (recorded) | Cosmetic. |
| **N5** (r1) — `list_task_evaluations` typed `command` | **the held post-approval graph pass** | Human adjudication; unchanged from r1. |
| **N6** (r1) — `_load_preview_inputs` vs `_load_live_inputs` structural pin | **phase 8** | Phase 8's status query consumes the same resolver. |

---

## Lessons for the plans

1. **L1 — a rule's first application is where it gets tested, and P-AB failed
   its own.** P-AB was created by review r1 to make `kind`-gated effect
   enumerations trustworthy; the very cycle that created it shipped an
   enumeration listing an effect `kind` does not gate (R2-S1). Proposed
   companion clause: **an effect enumeration is written by reading the
   parameter's occurrences, not the author's model of them** — the check is one
   `grep` of the parameter name in the file, and every hit is either an
   enumerated effect or explicitly excused. That grep is what found this.

2. **L2 — "adopt the reviewer's probes" worked, and the fidelity check is what
   made it safe.** Handing r1's probe files to the fix cycle collapsed a ~50-row
   coverage blocker into one cycle. The mechanism that made it trustworthy was
   preserving the sources with their sha256s so the re-reviewer could `diff`
   adoption against origin and prove no assertion was weakened. Proposed
   standing rule: **when a fix cycle adopts artifacts authored by a prior
   session, the originals are preserved with hashes at a named path and the
   adoption is verified by diff, not by claim.**

3. **L3 — reproducible mutant hashes are worth asking for.** Five of seven
   declared mutants reproduced byte-for-byte from the plan's named mutation
   alone. That is a much stronger ledger than r1's (where mutant text differed
   and only behaviour could be compared), and it came for free from the plan
   naming the mutation precisely enough ("delete `.with_for_update()` at the
   definition site in `_load_task_and_primary`"). Proposed: **P-I ninth
   extension — a named mutation is phrased so that two independent agents
   produce the same mutant text; the reviewer reports match/mismatch against the
   declared hash.**

4. **L4 — deleting an unbuildable criterion is a legitimate fix.** F4 removed
   C2's direct-INSERT direction rather than inventing a fixture around
   PostgreSQL's lock semantics, and replaced it with the one arbiter that *can*
   exist (the unit-level translation row). That is the right shape for the
   "unreachable path" class and should be the template when P-S applies.

## What made this round cheap

Round 1's probes became round 2's arbiters, so verifying closure was mostly
running things that already existed. The fix cycle's production diff was 4 files
and ~10 lines; everything else was test adoption. That ratio — tiny behavioural
change, large proof change — is what a healthy fix cycle looks like after a
review that found the proof missing rather than the code wrong.
