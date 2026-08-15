---
plan: phase 8B (inline item prices at task creation — round 18)
role: reviewer
round: 1
date: 2026-08-15
---

# Session prompt — review phase 8B implementation r1

You are the **reviewing agent** for phase 8B — the smallest mechanism phase
of the project, and the first whose implementer met the full endgame bar
unprompted: expected-red ids declared before the runs, per-row mutant AND
restored hashes, zero deferrals. Re-derive independently; the small surface
means you can afford FULL depth on every row.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Ground

- Plan: `plans/phase_8b_inline_task_prices.md` — base + the **GOVERNING
  "Amendments (projection r0)" block B1–B10**. Intention **§7B.6 with
  lettered (a)/(b)** (the trio's real shape; branch B — refuse IFF a
  CURRENT valuation exists, INV-V1 predicate; never-valued → v1;
  deleted/superseded-only → NEXT version); §4.7A (create_task = the fourth
  registered writer); §11A.5(c) as corrected; §7B.5 (the birth write sits
  OUTSIDE the savepoint — deliberately; a price that survives a failed
  auto-commit is CORRECT). §6.4:
  **`ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`** (message names the item's
  client_id + points at the valuation endpoint; single-path, P-S note) and
  `ITEM_MONEY_MOVED` must keep biting. §9 ALL rules.
- Checkpoint **`513856d`** (9 files; handoff `68d925a` deposited after).
  Handoff: `handoffs/implementer/2026-08-15_phase8b_implement_r1_handoff.md`.
- Coordinator consumption (verified, do not re-litigate): all SEVEN final
  hashes recomputed byte-identical; perimeter = the declared 9 files
  exactly; `git diff 513856d..HEAD -- app/ .archgraph/` empty; graph
  174/260, 5 pending (the new `command-task-create` node + 4 edges — HELD
  for the post-approval pass), rev `53fdbc78…`; the write site, refusal,
  audit call, and validator definition order confirmed present by
  inspection (`create_task.py:317-353`, `requests/__init__.py:56` after
  the bridge validator at :48-50).

## Environment facts

- Head `c1d2e3f4a5b6` (no migration). Declared suite: **2183 / 23 / 1
  deselected, 2207 collected** (+45 over 2162 = 24 extended bridge nodes +
  21 phase nodes — reconcile via `--collect-only`); focused 66; sorted
  failure IDs declared byte-identical to the phase-1 list — the diff is
  YOURS. Ruff clean declared.
- The C4 rows use the committing OWNER harness (`maybe_begin` owns) — any
  subset you run twice needs its residue scope named (rule 11½); the
  handoff notes the inverted-predicate mutant left 4 `phase8b` workspaces
  that the teardown removed — verify zero residue by state query.

## Probes (minimum — the ledger is yours)

- **P8B-1 — the five-mutation ledger, re-run from the declared mutant
  hashes** (all five phrased for byte-reproducibility — report
  reproduces/differs per row, P-I 9th): valuation-write deletion;
  refusal-predicate inversion (all three C4 rows red); validator-order
  swap (row C3-2 red); `reject_legacy_money` deletion (the three shipped
  retention nodes red); `_TaskItemInputBody` trio deletion (the survival
  row red). Reversion proven, tree == `513856d` blobs.
- **P8B-2 — row-coverage map** over B1–B10's amended criteria: C1's six
  rows (each valuation-EXISTS + the exact skip literals; rows 2 vs 3
  differ only in model terms; no disjunctions), C2 regression, C3's three
  rows (case (c): the `ge=0` field error ALWAYS beats the bridge —
  documented precedence), C4's three rows ON THE OWNING HARNESS (the
  refusal row asserts NO task, NO TaskItem, AND the matched item
  byte-unchanged — the `designer` trick; the deleted-only row asserts the
  chain GREW, not resurrected), C5's five rows (C5.3: ZERO rows in
  item_valuations — the sole-predicate form), C6's two harnesses, B8's
  non-vacuity mirror companion. Observed ids, P-V mapping.
- **P8B-3 — the refusal predicate read hard:** the select at
  `create_task.py:326-ff` must carry the FULL INV-V1 predicate
  (`superseded_at IS NULL AND is_deleted = false`, workspace-scoped) — a
  missing conjunct silently turns branch B into branch A for
  deleted-only items (the exact R15-1-adjacent hazard). Probe it: an item
  with ONLY a deleted valuation must accept; with ONLY a superseded one
  must accept (if no test row covers the superseded-only shape, that is a
  finding — §7B.6(b) names it).
- **P8B-4 — the effect set (P-AB discipline):** the birth write does
  EXACTLY the PUT path's effects (chain write + `item_valuation.created`
  audit) — no history record, no workspace event, no preview; and the
  §7B.5 interaction holds live (savepoint rollback keeps the valuation —
  the overflow fixture from phase 8 is the precedent harness if you want
  it live; L9's by-construction reading is in the projection).
- **P8B-5 — the bridge unsoftened:** the three legacy keys still 422 with
  the exact `ITEM_MONEY_MOVED` message on the nested item; the phase-6
  structural guard (`test_phase6_api_bridge.py:87-97`) still green (no
  legacy token in `create_task.py` source); mixed rows per B5.
- **P8B-6 — numbers:** full suite foreground yourself; sorted byte-diff
  vs the phase-1 list; +45 reconciled per file; focused set on a stated
  scope; ruff; DB at head `c1d2e3f4a5b6` after your passes; zero
  `phase8b` residue by state query.
- **P8B-7 — graph:** READ-ONLY, zero delta; the 5 pending are HELD (state
  exit revision/counts). Spot-check the new node's evidence spans against
  the shipped file (it was recorded by the implementer — nobody has
  verified its anchors).

## Closing protocol

1. Verdict, counts from the ledger table (P-L); story-shaped owner cards
   only for semantic decisions.
2. Mutations: per-row sha256 pairs COPY-PASTED (before AND mutant),
   observed red ids, reversion proven.
3. If APPROVED: carry-forward dispositions (the 5 pending graph items →
   the coordinator's post-approval pass; anything new → named landing
   spot); anchor spans service if anything you find moves them.
4. Deposit AFTER your writes, citing final hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-15_phase8b_review_r1_handoff.md`
   (full path): findings ledger; row-coverage map; mutation ledger; full
   write perimeter + probe declaration; lessons.
