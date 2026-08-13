---
plan: phase 4B (category-driven group selection)
role: reviewer
round: 2 (re-review, delta-scoped — B1/S1/S2 + the N5 ride-along)
date: 2026-08-13
---

# Session prompt — re-review phase 4B after fix cycle r1

You are the **re-reviewing agent** for phase 4B, round 2. Delta-scoped;
everything in review r1's "Verified correct" list is settled ground.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (settled)

- r1 (your predecessor): the category contract itself verified built correctly;
  CHANGES_REQUESTED on B1 (cold-build cleanup DELETEs never committed — fresh
  builds shipped a ghost workspace + 7 pause reasons), S1 (model-side
  partial-index predicate had no arbiter — deleting AND inverting it both
  stayed green), S2 (the shared-model status row asserted partially; the
  `has_open_basis and evaluable` collapse stayed green). Owner card 1 OPTION
  ONE authorized ONE more `env.py` edit, this cycle only.
- Fix r1 (Codex, checkpoint `8285cf1`, final): B1 `connection.commit()` as the
  last statement of `_do_run_migrations()`'s `finally` (env.py +1 line — the
  whole production diff); S1 the model-predicate structural row; S2 the
  exact-dict rewrite. Handoff:
  `handoffs/implementer/2026-08-13_phase4b_fix_r1_handoff.md`.
- N5 was performed by the COORDINATOR (graph revision `5c60534d…`, commit
  `5d8b6a6`): the `domain-item-economics` source link re-recorded at
  `configuration.py:44-82` via maintenance unlink+link, two audit records.
- Coordinator consumption (settled, don't re-derive): perimeter exact (5
  files; handoff-only deposit); arithmetic exact (1926 → 1927 = S1's one new
  row; focused selector named, 200×2); current hashes of env.py / model /
  query all byte-identical to the declared mains; B1's mutant hash equals YOUR
  predecessor's recorded pre-fix env.py hash (`db98e1ee…`) — independent
  cross-corroboration. **Known transcription defect (recorded, don't re-file):
  the S1 rows' "Restored SHA" strings are missing characters** — recompute
  when you re-run those probes; the real file is verified byte-identical.

## Step 1 — perimeter (fast)

`git show 8285cf1 --stat` = exactly env.py + the two named test files +
master_plan + the 4B plan. `git diff 8285cf1..HEAD -- app/` empty (the only
post-checkpoint commits are the coordinator's `.archgraph` and docs commits).

## Step 2 — delta probes

- **R2-P1 (B1/C9, the heart of it):** re-run §10's from-scratch recipe on
  your own disposable DB — end state asserted by QUERIES (review L5): head
  `5caae620088c`, zero `workspaces`, zero `pause_reasons`, zero
  `mig_cold_build_workspace` rows. Then the named mutation: revert the one
  commit line, rebuild on a second disposable, the ghost must return
  (1 workspace / 7 pause reasons); restore, hash-verify (`09261d91…`). Drop
  both databases; configured DB stays at head.
- **R2-P2 (S1):** both r1-green probes must now bite: delete
  `postgresql_where` from the model index → the new structural row reds;
  flip to `is_deleted = true` → same row reds. Recompute the restored hash
  (the ledger's is truncated); expect `27d99ecb8b3a0e5e…`.
- **R2-P3 (S2):** your predecessor's Probe B (`has_open_basis_version` →
  `has_open_basis and evaluable` in the status query) must now redden
  `test_status_shared_model_failure_is_repeated_in_each_category_block`;
  confirm the row is a whole-payload exact-dict assertion and that C6(b)'s
  collapse is stated in the plan's fix-r1 amendments block.
- **R2-P4 (N5 spot-check):** `archgraph_get_node domain-item-economics` — the
  configuration.py source link now reads symbol
  `resolve_economics_configuration`, span 44-82; re-read :44 (`def`) and :82
  (final `return`) in the code. Graph revision `5c60534d…`, 2 pending items
  (N7 edges) untouched.
- **Suite:** 1927 / 23 / 1; failure set byte-identical to the phase-1
  baseline; the 7-file focused selector (named in the handoff) 200×2; ruff on
  the changed files; residue check with SCOPE stated.

## Closing protocol

1. Review log entry; tracker verdict (**APPROVED** expected if the delta
   verifies); stamps preserved.
2. Archgraph read-only beyond R2-P4; state revision; zero delta of your own.
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-13_phase4b_rereview_r2_handoff.md`
   (full path, AFTER your writes): summary; `⚠ OWNER DECISIONS REQUIRED (n)`;
   probe results with sha256 pairs; full write perimeter + probe declaration;
   disposable DBs listed and dropped.
