---
plan: phase 8B (inline item prices at task creation — round 18)
role: review
round: 2
verdict: APPROVED
date: 2026-08-15
actor: Claude (plan-reviewer, re-review)
---

# Phase 8B re-review r2 — handoff

**Verdict: APPROVED.** 0 blocking · 0 should-fix · 0 new notes.

Both round-1 should-fixes are dead at the seam, verified by re-running the
exact mutations that exposed them. The fix cycle changed one file, added one
test node, and touched no production code — the perimeter matches the fence
byte for byte. Phase 8B is done; phase 9's HOLD can lift.

⚠ OWNER DECISIONS REQUIRED (0)

## Review history (what earlier rounds settled)

- **Projection r0** — 18 rows, owner card → R18-3 branch B; produced the
  GOVERNING B1–B10 block.
- **Implement r1** — mechanism shipped; reviewed at full depth in r1 and found
  **correct on every branch**, including two shapes no test reached. §7B.5's
  survival property verified LIVE, effect set diffed exact against the PUT
  path, bridge unsoftened, C5.3 non-vacuous, `maybe_begin` confirmed OWNER in
  production. **None of that is re-verified here** — it is settled ground.
- **Review r1** — 0 blocking / 2 should-fix (both test-side, one file) / 3
  notes → CHANGES_REQUESTED.
- **Fix r2** — F1 + F2 (+ F3 record discipline), this review's only subject.

## Perimeter verification (charter re-review clause 1)

`git diff 2719941..4369a27` touches exactly one path under `app/`:

```
app/tests/.../test_phase8b_inline_task_prices.py   | 117 +++++-
```

Everything else in that range is documents (my r1 handoff, the plan, the
master plan, the coordinator's fix prompt). Since the checkpoint, `git diff
4369a27..HEAD -- app/ .archgraph/` is **empty**.

Zero production change, independently confirmed by hash rather than by the
diff alone — all six untouched artifacts recomputed byte-identical to their
implement-r1 finals:

```
create_task.py            e9c2ccc1bfda4c133149195e530977860eaefba31508b30e492a42bd6e41d547
requests/__init__.py      2bc2b7bb018357d2e437096aac8e81263adddffae1e7a1c9c09fbe564b1e9da4
routers/api_v1/tasks.py   6a3654dd7aa602bc5f7435960f9bdce06e82d521c585e418a54962ef67061560
routers/README.md         291aae658bf026c9ad1f68e031c07e367c13b5fa36bd90e95b51efab6150fdec
test_phase6_api_bridge.py 68a34b62f37339434acfecbf1fd13ecd1130d8700669d810fd3799572b7e4a38
.archgraph/architecture.yml 53fdbc785621c38a295ae90ac09c67339ca654563d0b2f6480d034fc11868fd1
```

Fixed file: `test_phase8b_inline_task_prices.py` →
`12c6ad5bd81c03f668dbd9a8a2716c7eec2020e7fadaac748f99b5bf090daf39`, matching
the fix handoff. Nothing outside the fence.

## R2-P1 — S1 is dead

**The row.** `test_c4_row_4_superseded_only_existing_item_accepts_and_grows_chain`
seeds the state through the three production commands — `set_item_valuation`
(1100) → `set_item_valuation` (1200, supersedes) → `delete_item_valuation` —
never hand-built rows (charter rule 3). It asserts the pre-state explicitly:
v1 `superseded_at` set and not deleted, v2 deleted and not superseded, and — the
load-bearing one — a real `SELECT` on the INV-V1 predicate returning `None`,
i.e. DB truth that there is **no current valuation**. It then asserts
`create_task` ACCEPTS, the chain has grown to three rows, and v3 is current.

It is **stronger than the r1 probe it was built from**: it pins
`valuations[0].client_id` and `valuations[1].client_id` to the ORIGINAL rows,
so "grew rather than resurrected" is established by identity rather than by
arguing from the unique index.

**M6 re-run from its declared bytes.** Deleting
`ItemValuation.superseded_at.is_(None)` at `create_task.py:331` (that line
only):

| | |
|---|---|
| declared mutant | `98dc2c252e8f5bdac1ea7ecc5aeff0391fd6fd081f684d45dbf86ada718174bd` |
| reviewer-recomputed | `98dc2c252e8f5bdac1ea7ecc5aeff0391fd6fd081f684d45dbf86ada718174bd` — **byte-identical** |
| observed | **1 failed / 21 passed** over the full phase-file scope — the failure is exactly `test_c4_row_4_…` |
| restored | `e9c2ccc1bfda4c133149195e530977860eaefba31508b30e492a42bd6e41d547` ✅ |

The conjunct that survived the entire 66-node r1 suite now has a guard, and
the guard is the only thing that reddens.

## R2-P2 — S2 is dead

**The shape.** C4 rows 2 and 3 now capture `workspace_id`, `user_id`,
`item_id` and `item_article_number` into plain locals before the `try`, use
them throughout the body, and pass locals to
`_cleanup_committed_workspace`. Row 4 was written that way from the start. No
`finally` dereferences an ORM instance the rollback expires.

*(Row 4's assertion body does read `first_row.client_id` / `second_row.client_id`
after the commit — but those live inside the `try`, reached only when
`create_task` succeeded and the session is healthy. Cleanup itself is
instance-free. Correct.)*

**Direct regression proof.** I re-ran the same M2 inversion
(`create_task.py:337`) that produced the r1 leak — mutant hash reproduced
byte-identically again (`f0776418c7cdc77faf76907bc47545ce70d244106e35d6e88ba9f09940cb2f95`):

| | r1 | r2 |
|---|---|---|
| C4 rows red | 3 | **4** (rows 1–4; 4 failed / 18 passed) |
| `phase8b` workspaces left behind | 2 → 8 across probes, hand-cleaned | **0** |

State query after the red run — `workspaces 0 · users 0 · categories 0 ·
audits 0 · orphan items 0`. Cleanup runs on the path that matters. Charter
rule 11½ satisfied in both its modes.

## R2-P3 — numbers (all re-measured in foreground by this session)

| | measured | declared | |
|---|---|---|---|
| full non-E2E suite | **2184 passed / 23 failed / 1 deselected** (122.49s) | 2184 / 23 / 1 | ✅ |
| failure IDs | sorted `diff` vs the phase-1 S2 baseline: **empty**, 23/23 | byte-identical | ✅ |
| collection | **2208** (2207 selected + 1 deselected) | 2208 | ✅ |
| reconcile | +1 over r1's 2207 = the one new node; phase file 21 → **22** by `--collect-only` | +1 | ✅ |
| focused (phase + bridge) | **67 passed** | 22 phase-file | ✅ |
| ruff | **All checks passed** on the test file | clean | ✅ |
| DB | `c1d2e3f4a5b6 (head)`, no migration | head | ✅ |
| graph | 174 nodes / 260 edges, rev `53fdbc78…`, 0 stale, 5 pending, 0 diagnostics — **zero delta** | zero delta | ✅ |
| tree at close | byte-identical to `4369a27`; `git status` empty | — | ✅ |

## R2-P4 — F3 / P-I 10th ext: satisfied

Both fix mutations pin their site by line ("at `create_task.py:331` (line 331
only, definition site)"; "at `create_task.py:337` (line 337, definition
site)") and both state the scope behind "observed red". The payoff is
measurable: **both hashes reproduced byte-identically from their written
descriptions alone**, where r1's unpinned M1 did not. The extension works at
first use and should stay.

One observation, explicitly **not** a finding: M2's cell reports the one-row
scope, which is honest and compliant; over the full phase file the same
inversion reddens four rows. A full-scope figure carries strictly more
information at the same cost — worth preferring, not worth a fix cycle.

## Out of scope, not re-run (per the re-review's declared fence)

M1 / M3 / M4 / M5 (proven in r1 against production files that are byte-identical
today); the r1 row-coverage map's passing rows; the mechanism re-derivations;
my own M7 / M9 probes. **Passing-glance clause: nothing seen wrong.**

## Probe declaration

**Files touched by probes** — applied and reverted, restored hash
`e9c2ccc1bfda4c133149195e530977860eaefba31508b30e492a42bd6e41d547`:

- `app/beyo_manager/services/commands/tasks/create_task.py` (M6 at :331, M2 at
  :337 — nothing else).

No files created. No graph mutation (read-only `archgraph_status` /
`archgraph_get_node`); no promotion, rejection, edit or maintenance action.

**Database side effects: none retained.** Both probe runs self-cleaned via the
fixed teardown — the state query above returned zero, which is itself the S2
evidence. Database left at `c1d2e3f4a5b6 (head)`; no migration, no disposable
database.

**Pre-existing residue, NOT this phase's (unchanged from r1):** one
`item_valuations` row (`ival_01M012JEV…`, created 2026-08-14) under workspace
`phase7 1aa0f269…`. Left in place; routed below.

## Carry-forward dispositions

| item | destination | state |
|---|---|---|
| 5 pending graph items (`command-task-create` + 4 edges) | coordinator's post-approval human graph pass | HELD, unchanged |
| F4's corrected spans — node `:72-580`; `writes_to table-task` `:113-183`; `reads_from table-item` acceptable-loose (`:236-248` is the precise core); the two 8B-behaviour edges exact | same pass, as the correction payload | recorded in the plan (F4) |
| phase-7 `item_valuations` residue row | the existing rule-11½ maintenance record (§10, filed 2026-08-13) | not this phase's |
| `create_item_in_session` branch never exercised with the trio | no action — B7 made the write site shared and post-branch | observation only |

Nothing else is open. Phase 9's dependency on 8B is discharged.

## Lessons

None new. Two r1 lessons are now **validated in practice** and worth keeping
cited rather than restated:

1. **P-I 10th ext (pin the deletion boundary by line)** paid for itself
   immediately — two-for-two byte-reproduction where the unpinned mutation had
   failed. Recommend it stays a hard requirement, not a preference.
2. **Rule 11½'s second failure mode (capture identifiers into locals before the
   `try`)** now has a same-file before/after exemplar: row 1 always had the
   shape, rows 2/3 acquired it, and the M2-under-red state query is the check
   that distinguishes them. That check — *run the red path, then query state* —
   is the cheap generic verification for any test that commits, and is worth
   naming in §9 alongside the rule.
