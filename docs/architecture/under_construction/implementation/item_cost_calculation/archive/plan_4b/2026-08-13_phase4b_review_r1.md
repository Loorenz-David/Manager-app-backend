---
plan: phase 4B (category-driven group selection, §7C)
role: reviewer
round: 1
date: 2026-08-13
---

# Session prompt — review phase 4B implementation r1

You are the **reviewing agent** for phase 4B, round 1. Re-derive independently;
never accept a declaration you can re-run.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Ground

- Plan: `plans/phase_4b_category_selection.md` — read ALL THREE layers (base
  tasks/criteria; the GOVERNING "Round-0 projection amendments"; the GOVERNING
  "Prompt-time dependency re-verification" T8-7…T8-10).
- Checkpoint `cfec9df` (final; the handoff cites it), deposit:
  `handoffs/implementer/2026-08-13_phase4b_implement_r1_handoff.md`.
- Coordinator consumption (already verified — don't re-derive): perimeter =
  the plan's file list + L-12 README + task-8 edits + tracker/Review log +
  graph delta + the DECLARED env.py exception; arithmetic exact (selected
  1915→1949 = +34 = passed delta; failures constant 23); `_common.py`'s
  revert-mutant hash equals phase-4's original file hash (corroborates).
- Master plan §9 rules P-A…P-W all bind — esp. P-V (ids name the authority
  row), P-I (observed node ids; every enumerated mutation EXECUTED), P-W
  (filter rows compete), P-Q (implication pins), P-O (no disjunctions).
- Environment: §10. Suite baseline: 23 failures byte-identical to the phase-1
  list (N14 flake caveat). Expect 1926/23/1.

## Owner decision already taken — fold it in

**OD-1 (env.py, ANSWERED 2026-08-13, `planning/owner_decisions.md`): RETAIN;
you verify.** Two mandatory probes:

- **P4B-0a (reproduce the rationale):** on a DISPOSABLE database, revert the
  four env.py lines and run the 4B migration path; the claim is that
  `alembic upgrade` reports success but persists neither the revision nor the
  DDL. Reproduce it. Context that makes this non-obvious: the maintenance
  session's from-scratch upgrades succeeded BEFORE this rollback existed —
  determine what changed (first migration whose upgrade() opens its own
  SELECT via the preflight? autobegin state?). If it does NOT reproduce,
  that is a FINDING (unnecessary infra change, candidate reversion), never a
  silent pass. Restore the lines; hash-verify.
- **P4B-0b (no collateral):** with the rollback in place, re-run §10's
  from-scratch recipe (empty disposable DB → `5caae620088c`): cold-build
  workspace machinery still creates/cleans its transient rows; configured DB
  untouched at head.

## Step 1 — perimeter & hygiene (fast)

`git show cfec9df --stat` vs the plan's list; `git status --porcelain` clean;
handoff-only deposit after the checkpoint. One known declaration defect to
confirm-and-record (not a finding hunt): the router-file mutant SHA in the
ledger is 63 hex chars — recompute both hashes for that row when you re-run it.

## Step 2 — the criteria, re-derived

- **C1 (migration):** live-schema rows on the dev DB at head (`atttypid` →
  `item_major_category_enum`; exactly ONE pg_type row; the partial unique
  with `is_deleted = false`; `compare_metadata` FILTERED to
  `production_cost_groups` — L-13). Static proxies: pre-flight raise before
  any `op.` call, report carries ids + dependent counts (L-15), downgrade has
  no enum drop, `create_type=False` at the migration site. Disposable
  round-trip + seeded-row refusal (the implementer records theirs; run your
  own).
- **C2 (INV-G3, P-M/P-K):** the four rows are direct-insert+flush with the
  INDEX as sole arbiter; re-run the two DDL-site mutations (widen key with
  `name`; drop the predicate) on disposable state.
- **C3 (dual-path identity):** pre-check rows both commands; the
  `INDEX_IDENTITIES` mutation; the L-4 recorded reachability judgment stands
  in for a live DB-conflict race (P-S — confirm the judgment is recorded, do
  not demand the harness).
- **C4 (immutability, P-Q):** all five rows incl. the deleted-basis breadth
  row (L1 pin) and the equal-value no-op (L3 pin); the guard-deletion
  mutation reddens (a)+(b) only; the L-5 router-level name-only PATCH row
  (P-R: through `TestClient`, a rename of a versioned group must succeed over
  HTTP — this is the row that catches the `model_dump()` None-vs-absent trap).
- **C5 (classifier):** V0–V6 + V2b + P1/P3/P4 on unsaved ORM instances with
  EXPLICIT distinct client_ids (L-6 — check a fixture actually sets them;
  `None == None` joins are the failure mode); M1/M2 re-run; M3's
  enum-permutation structural probe (verify the run evidence, or re-run in a
  disposable worktree).
- **C6 (status shape):** exact-dict equality incl. the per-category basis
  scoping row (d) and its named mutation; keys exactly
  `{"categories","has_open_cost_model_version"}` / blocks exactly the five
  keys / categories exactly `{"wood","seat"}`.
- **C7 (surfaces):** parse rows incl. wrong-case `"WOOD"`; the body-model
  structural row (its mutation is the one with the 63-char SHA — re-run);
  serializer row.
- **C8 (regression):** phase-4 C11 role rows green over the reworked routes;
  grep `audit(` call sites in the two reworked commands against §6.4's
  registered vocabulary (no new event strings).
- **Vacuous-mutation note in the handoff:** the status query's deleted-basis
  filter edit was reported vacuous (loader already excludes deleted rows).
  Verify the reasoning at the loader, and judge whether a criterion row is
  OWED there or the per-category scope mutation genuinely covers it.
- **Ledger discipline:** sample at least a third of the 17 rows (must include
  the migration DDL-site pair, the guard deletion, M1/M2, the body-model
  row); apply/run/revert with sha256 pairs against the REAL paths; observed
  node ids must match the declaration (P-I: a mis-attributed node id is a
  finding even when something reds).

## Step 3 — graph (read-only)

`archgraph_status` — expect revision `5e4f368d…`, 148 nodes / 188 edges,
2 pending (the N7 cost-model-term edges — NOT yours to adjudicate). The
implementer recorded six source links in the checkpoint; spot-check two spans
against the code. Anything contradicting the code → the
`archgraph-discrepancies` skill (file, don't fix).

## Closing protocol

1. Verdict in the plan's Review log + tracker row (stamps preserved): APPROVED
   or CHANGES_REQUESTED with per-finding corrections verified by a mutation
   that stays green (the phase-4 bar).
2. Suite re-run yourself: 1926/23/1, failure set byte-identical; any
   committing subset twice with the residue-check SCOPE stated (§9 rule-11½
   record); ruff; dev DB at head `5caae620088c`.
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-13_phase4b_review_r1_handoff.md`
   (full path, AFTER your writes): summary; `⚠ OWNER DECISIONS REQUIRED (n)`;
   P4B-0a/0b outcomes stated explicitly; full write perimeter + probe
   declaration with sha256 pairs.
