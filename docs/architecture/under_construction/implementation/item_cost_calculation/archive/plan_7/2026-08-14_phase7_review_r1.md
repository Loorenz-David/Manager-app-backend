---
plan: phase 7 (evaluations — commit/supersede, projections, auto-commit)
role: reviewer
round: 1
date: 2026-08-14
---

# Session prompt — review phase 7 implementation r1

You are the **reviewing agent** for phase 7 — the heart of the domain: the
commit transaction, mirror rule, projections/promotion, the `create_task`
auto path, and the evaluations read. Re-derive independently; never accept a
declaration you can re-run. **This phase's concurrency mutations were
explicitly left to you** (see P7-1) — they are not optional garnish; the
projection proved one silent-clobber race on paper and phase 4 proved the
delete-guard hazard live.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Ground

- Plan: `plans/phase_7_evaluations.md` — base + forward notes + the
  **GOVERNING "Amendments (projection r0)" block A1–A5** (restated C1–C10,
  new C11–C14). Intention **round 16 as folded**: §7B.1 (step-4 valuation
  `FOR UPDATE`, step-9 TASK-linked history record), §7B.4's two-ordering race
  clause, §7B.5 as restated (resolver-total pre-check, verbatim log lines,
  `pending_events` discipline), §7B.2/§7B.3, §7A, §7C, §7.3, §6A.9, §6A.11.
  Master plan §6.4 (the status→identity mapping table;
  `ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY`; `item_cost_evaluation.*` audit
  rows; the `_common.py` evaluations-index row, uniform conflict sentence
  standing) and §6.5 (Phase-7 additions incl. the four evaluations-read pins,
  the RECOMPUTE decision, the rederive-marker ERROR escalation, and the
  post-hoc-registered `auto_commit_item_cost_evaluation_in_session`).
  §9 P-A…P-AA and ALL extensions bind.
- Checkpoint **`a7f421f`** (17 files; deposits `38a44a9` + `a255147` are
  handoff-only):
  `handoffs/implementer/2026-08-14_phase7_implement_r1_handoff.md`; the
  mutation ledger lives in the plan's Review log.
- Coordinator consumption (already verified, do not re-litigate): both
  declared final hashes match the working tree
  (`create_task.py` = `f1daef7f…e4c8`, `item_economics.py` = `87fcb318…40ae`);
  `git diff a7f421f..HEAD -- app/` is empty; perimeter = exactly the 17
  declared files; tracker + plan state flipped to IMPLEMENTED; graph state
  matches the declaration (166 nodes / 239 edges, 52 pending, revision
  `0a71061554fa2123d7e2fba7ff853c328fb1405676194dd0d2cc7f067938266c`).

## Environment facts

- git HEAD is at or after `a255147`; alembic head `be9dfe42a035` — **this
  phase adds NO migration**; a DB not at that head is a finding.
- Declared suite: full **2037 / 23 / 1 deselected** (baseline was 2012/23/1 =
  2035 selected → +25); failure set claimed = the established phase-1 list.
  Four `create_task` integration files: 29 passed after the final savepoint
  relocation.
- Live DB: all seven economics tables were 0 rows at projection time; suite
  runs add residue (~116 non-economics workspaces/run is the known class —
  rule 11½: name the residue scope of anything you run twice).

## Probes (minimum — the findings ledger is yours)

- **P7-1 — the deferred concurrency mutations are YOURS to run** (deferral
  has phase-4 P4-3 precedent; the declaration is honest). Bounded waits
  (P-T r2-L3 — an unbounded wait once hung the suite 120 s); each in a
  disposable or with hashes proving reversion; observed pytest ids per row
  (P-I): (a) **C11** — delete `.with_for_update()` at
  `commit_item_cost_evaluation.py:111` (task lock) → the block observable
  reddens; promotion row shares the lock; (b) **C5 row 6** — delete
  `.with_for_update()` at `:183` (valuation lock) → the committed-mid-flight
  row reddens: without it the manager's price is silently clobbered (the
  projection's D4 trace — verify the test actually stages the commit BETWEEN
  step 4 and step 9, not merely "concurrently"); (c) **C12** — delete
  `read=True` at `:149` and `:155` separately (basis chain / model chain) →
  **row 1 only** per chain reddens; a run where row 2 also reddens
  contradicts the plan's declaration and is itself a finding (P-I fifth
  ext); (d) **C2** — the direct-INSERT conflict row: verify the translated
  `ITEM_COST_CONCURRENT_COMMIT` surfaces (not a raw IntegrityError), and
  that no test drives it "two sessions past S1" through the command — that
  deleted row rewarded removing the task lock.
- **P7-2 — C1 row 1b's mutation is MISSING from both ledger lists** (run
  list AND deferral list). Verify the row exists (hand-written basis where
  persisted rate ≠ derived), then run its named mutation: swap the snapshot
  source to `basis.cost_per_worker_minute_minor` → exactly that row reddens.
  If the row itself is absent, that is a blocking coverage gap (the
  RECOMPUTE decision has no arbiter without it).
- **P7-3 — number reconciliation (P-L; the recurring transcription class,
  now THREE-way):** the handoff says focused **97** / full **2037/23/1**;
  the plan's Review log says **88 router + 4 integration = 92**; the tracker
  row says focused **94** / full **2034/23/1**. Three documents, three
  number sets — none is trustworthy until re-run. Re-run the full suite and
  one consistent focused set and report YOUR numbers; reconcile the suite
  delta (baseline 2012/23/1 = 2035 selected) against the actual new
  test-node count; failure set byte-compared to the phase-1 list, not
  counted.
- **P7-4 — row-coverage mapping (phase-4 B1 precedent):** map every C1–C14
  row (as AMENDED — A3/A4 win) to an observed parametrize id (P-V: ids name
  the authority row in CURRENT numbering; expressions differ per row). ~60
  rows against 25 new tests means parametrization must carry the load —
  find the rows with no arbiter. Priority: C3's nine admission rows, C5's
  six mirror rows, C6 vs §7C.2 (ambiguous row = pure-resolver discharge,
  recorded, never a command fixture), C7's resolver-route identities, C9's
  TEN §11A.4 rows + both verbatim log lines, C14's four pins (incl. the
  equal-`created_at` tie-break fixture) + the rederive ERROR row.
- **P7-5 — independent re-derivation of the commit procedure** against
  §7B.1's order: calculator before ANY write; S1→S2→S3, never insert before
  S1, no `ON CONFLICT` on chain indexes; refusals via the §6.4 mapping table
  at the RESOLVER gate (the calculator's own identities are armor —
  something reaching them on an unevaluable item is a finding); mirror
  predicate as a Python tuple (`None == None`); snapshots = §6A.11's closed
  set from calculator outputs only; promotion re-runs §7B.2 admission +
  ownership + liveness and leaves the projection row equal on ALL columns
  including `updated_at`, read from a SECOND session (a stale identity-map
  comparison does not discharge C8).
- **P7-6 — the auto path:** `auto_commit_item_cost_evaluation_in_session`
  holds the §7B.5 pre-check (resolver `NOT_EVALUATED` + active PRIMARY) and
  NOTHING else (registered post-hoc — §6.5); the savepoint body; the
  overflow fixture is a genuine failed SQL statement (re-run the C9 mutation
  — `PendingRollbackError` was the observed red); `pending_events` append
  strictly after normal savepoint exit; NO dispatch from the subordinate
  path; no existing statement in `create_task` moved (read the diff hunk by
  hunk); both log lines byte-exact per §7B.5.
- **P7-7 — event & history (C10):** the seam is the DISPATCHING module's
  `event_bus.dispatch` (create_task's for the auto path); the after-commit
  observable reads the row from a second session; the TASK-linked history
  record appears in `get_task_flow_records`' response (the R16-1 mechanism —
  no flow-service change was needed; verify none was made); audit rows use
  the four registered names; nothing fires on a failed commit.
- **P7-8 — P-Z on the extraction:** `set_item_valuation.py` is refactor-only
  — re-run the phase-5 focused valuation suite yourself (the handoff's
  "green before and after" cites no numbers); the before/after property row
  exists (set+supersede+delete identical chain rows); the config loader and
  chain writer have exactly ONE definition each (grep for duplicates).
- **P7-9 — router surface (C13):** re-run the completeness-arbiter mutation
  (declared hashes `87fcb318…40ae` → `ce5d6486…8116`); five routes exactly
  per §6.5, ADMIN/MANAGER only, both role-gate tests parametrize over the
  new `_ROUTES` rows.
- **P7-10 — Architecture Graph: READ-ONLY, zero delta.** The 50 new inferred
  items are HELD for the post-approval pass — adjudicate NOTHING. Spot-check
  ≥5 sampled items' claims and anchors for accuracy (phase-4's P4-6 lesson:
  edges need write-site evidence, not blanket router anchors) and report
  what you find; deliver anchor corrections as a spans service in the
  handoff if needed. State revision/counts at exit (expect `0a71061…`,
  166/239, 52 pending).

## Closing protocol

1. Verdict `APPROVED` / `CHANGES_REQUESTED` with blocking / should-fix /
   notes, counted from the ledger table, not prose (P-L). Story-shaped owner
   cards ONLY for semantic decisions (branches + recommendation +
   on-silence).
2. Suite re-run yourself: report numbers READ off YOUR run; failure set
   byte-compared; ruff on changed files; DB at head after your passes; every
   disposable dropped and listed; any committing subset run twice with
   residue scope named (rule 11½).
3. All mutations you run: per-row sha256 pairs COPY-PASTED, observed red
   sets with pytest node ids, reversion proven (working tree == `a7f421f`
   blobs for touched files).
4. Deposit AFTER your writes, citing final hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase7_review_r1_handoff.md`
   (full path): findings ledger; row-coverage map; mutation ledger; full
   write perimeter + probe declaration; lessons.
