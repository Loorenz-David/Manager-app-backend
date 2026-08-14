---
plan: phase 5 (valuation surface)
role: reviewer
round: 1
date: 2026-08-13
---

# Session prompt — review phase 5 implementation r1

You are the **reviewing agent** for phase 5, round 1. Re-derive independently;
never accept a declaration you can re-run.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Ground

- Plan: `plans/phase_5_valuation_surface.md` — base + the GOVERNING
  "Round-0 projection amendments" block (L1–L16, notes, delegations). Intention
  §11A.4–§11A.5 **as amended by round 13** (R13-1 preview key + computable-state
  numerics + first-save-is-version-1; R13-2 hidden deleted history). Master
  plan §6 as amended 2026-08-13 (§6.5 resolver names + envelope; §6.4 the two
  audit events); §9 P-A…P-Z all bind; §10.
- Checkpoint `8b4ac06` (final), deposit `b52dbf8` (handoff only):
  `handoffs/implementer/2026-08-13_phase5_implement_r1_handoff.md`.
- Projection evidence to reuse: the r0 handoff (now the plan's amendments) —
  esp. the computed L12 fixture (persisted `13.0208` → allowance `76800.20` vs
  re-divided `76800.00`) and L18 (no self-FK teardown special-casing).

## Coordinator consumption findings (route these into your probes)

- **P5-A (arithmetic, off by one):** the handoff claims full suite "1951
  passed, 23 failed" with no deselected count; the tree at `8b4ac06` collects
  **1973 selected + 1 deselected**. 1951+23=1974 ≠ 1973. Expected truth:
  **1950 / 23 / 1** (+23 new tests over 1927). Re-run, pin the real numbers,
  and record the discrepancy class (transcription vs a run at a different
  tree state).
- **P5-B (the central probe — ledger under-declaration):** the ledger declares
  THREE mutations; the governing amendments name roughly TEN. Verified good:
  the three declared rows' restored hashes match the tree byte-identical.
  **Missing and owed** (P-I: every enumerated mutation EXECUTED, full observed
  red set, divergence from prediction flagged):
  1. L1 — force `resolve_economics_configuration` to diverge from
     `resolve_economics_selection(...).status` (must redden; if the
     reimplementation is genuine, the mutation site is the wrapper).
  2. L2(i) — permute `EconomicsStatusEnum` declaration order → ALL rows stay
     green (structural).
  3. L2(ii) — permute `ITEM_READINESS_PRECEDENCE` → must redden the ordered
     adjacent-pair rows.
  4. L15 — inline an `item_major_category_snapshot` read in the preview
     (bypassing `resolve_major_category`) → the structural row must redden.
     FIRST verify the structural row exists at all.
  5. L16 — drop ONE side of one currency comparison → exactly its row reds
     (three rows must exist: valuation≠basis, valuation≠model, basis≠model).
  6. L7 — verify `ITEM_COST_VALUATION_AMOUNT_REQUIRED` arrives as the exact
     LEADING token through the SHIPPED parser (the projection proved the
     naive implementation prefixes the field name); the assertion must be
     `startswith`, not substring.
  7. Audit (L9) — remove one `audit(...)` call → its C11-shaped retention row
     reds; both registered strings asserted exactly.
  Any of these that stays green, or any test that turns out not to exist, is
  a finding with the projection row as its authority.

## Step 1 — perimeter & hygiene (fast)

`git show 8b4ac06 --stat` = the 16 declared files; `git status --porcelain`
clean; `git diff 8b4ac06..HEAD -- app/` empty. Ruff on changed files.

## Step 2 — the criteria, re-derived

- **C1/C2 (chain + race):** close-before-insert order (S1→S2→S3); BOTH race
  paths (pre-existing current: loser blocks then conflicts; first valuation:
  index alone arbitrates) on genuine two-session fixtures; all waits bounded;
  run the race subset TWICE; residue check names the five tables
  (`item_valuations, audit_logs, items, users, workspaces`).
- **C3 (request layer only, L10):** rows cite phase-2's six DB-CHECK ids;
  no duplicate DB rows built.
- **C4 (delete/immutability, L5 option (a)):** superseded-row refusal proven
  by direct command call with the recorded reachability judgment; DELETE
  returns the status-only `item_unvalued` preview (§11A.5(d)); re-set starts
  a fresh current row.
- **C5 (the 12-value enumeration, P-V):** parametrize ids map one-for-one
  onto §11A.4's values — no duplicates, no omissions; recorded judgments for
  `ok`/`infeasible` (task-scoped) and ambiguous (INV-G3 defence); the
  `item_missing_major_category` row live; every non-computable row asserts
  `null` numerics AND `item_cost_evaluations` count unchanged; the
  `not_evaluated` row asserts the L12 fixture's exact `76800.20`.
- **R13-1 envelope exactness:** `{"item_valuation": …, "preview": …}` asserted
  by exact-dict (P-Y — partial assertions on shaped criteria are findings);
  preview carries no `client_id`; nothing merges preview numerics into
  committed fields.
- **C6 (history, R13-2/L13):** deleted rows excluded; order
  `created_at DESC, client_id DESC`; "exactly one current" via INV-V1's
  predicate with the delete-then-reset fixture (two `superseded_at IS NULL`
  rows) as the prover; byte-identical re-read.
- **Routes (P-R):** exactly three new routes, ADMIN/MANAGER, in the shipped
  `_ROUTES` harness; the L20 rename (or second list) applied so names don't
  overclaim; POST body row for valuation carries a valid payload.
- **Regression:** the 4B suite untouched-and-green (the classifier rework is
  behavioral-identity — `resolve_economics_configuration` results unchanged);
  the status query still passes with zero changes to its file.

## Step 3 — architecture graph (read-only + service)

The checkpoint recorded 5 nodes + 7 edges (revision `b5e6fe09…`, now pending
review). Do NOT adjudicate. Verify each claim against code (the phase-4
lesson: write-site evidence lives in command files, never a blanket router
span) and deliver an anchor-spans table for the coordinator's post-approval
pass — final line spans per item, corrected where imprecise.

## Closing protocol

1. Review log entry; tracker verdict (stamps preserved); per-finding verified
   corrections (mutation-proven) if CHANGES_REQUESTED.
2. Suite re-run yourself (expect 1950/23/1, failure set byte-identical to the
   phase-1 baseline); focused selector named; DB at head `5caae620088c`.
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-13_phase5_review_r1_handoff.md`
   (full path, AFTER your writes): summary; `⚠ OWNER DECISIONS REQUIRED (n)`;
   P5-A/P5-B outcomes stated explicitly; probe declaration with sha256 pairs
   (copy-pasted, never retyped); full write perimeter.
