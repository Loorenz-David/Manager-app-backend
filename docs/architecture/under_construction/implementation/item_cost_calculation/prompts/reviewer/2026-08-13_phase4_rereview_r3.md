---
plan: phase 4 (configuration services)
role: reviewer
round: 3 (re-review, delta-scoped — B1/B2/S1–S4 only)
date: 2026-08-13
---

# Session prompt — re-review phase 4 after fix cycle r3

You are the **re-reviewing agent** for phase 4, round 3. Delta-scoped; settled
ground is not re-derived; anything seen wrong in passing is reported.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(project folder: `docs/architecture/under_construction/implementation/item_cost_calculation/`).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (settled)

- r1: mechanisms verified correct. r2: coverage substantially closed; six
  test-side gaps remained (B1/B2/S1–S4), each proven by a green mutation; the
  r2 Review-log entry carries the settled ground and the verified corrections.
- **Fix r3 (Codex, checkpoint `74b280b`, final; handoff after, citing it):**
  test-side only (2 test files + 2 docs, verified); B1 table-mapped rows incl.
  live NULL-open fixtures; B2 four sole-cause filter fixtures + both rename
  paths; S1 identity tokens on the real races; S2 the `2.675` straddling
  fixture; S3 adjacent pairs per bound; S4 bounded waits. Ledger: 9 mutations
  with observed pytest ids + sha256 pairs. N4/N5/N6 not taken (optional).
  Handoff: `handoffs/implementer/2026-08-13_phase4_fix_r3_handoff.md`.
- **Pre-resolved consumption notes (do not re-file):** (1) the handoff's
  probe-file PATHS are garbled (`services/commands/item_economics/queries/…`
  does not exist) — the declared sha256s match the real files
  (`services/queries/item_economics/list_production_cost_groups.py` =
  `75d81316…`), so the probes were real and the transcription is the defect;
  recorded. (2) Focused +13 vs suite +17 — reconcile the 4-test difference.

## Step 1 — verified perimeter

`git show 74b280b` = exactly `test_phase4_fix_coverage.py`,
`test_item_economics_requests.py`, tracker row, Review log (+405/−27). The
deposit `c89354c` carries only the handoff. **Zero production changes** — verify
`git diff 2567fc7..HEAD -- app/beyo_manager/` is empty.

## Step 2 — delta probes

- **R3-P1 (the r2 green-mutations now bite):** re-run at least: B1's
  `open_from is not None` drop (→ the table-row-5 nodes, both chains); S1's
  basis-index→model-identity swap (→ the REAL race row, not the proxy — this
  was r2's S1 exactly); one B2 filter drop; S3's `gt→ge`
  (→ the fixed-zero row). Observed ids; sha256 reverts.
- **R3-P2 (table mapping, P-V):** the C1 parametrize ids map one-for-one onto
  §7A.4's ten table rows × 2 chains — no duplicates, no omissions (r2's B1 was
  precisely a count-without-table match; verify the mapping, not the count).
- **R3-P3 (the two legacy-arbiter filters):** model-workspace and
  basis-`is_deleted` stayed on the combined C10 arbiter (they reddened in r2 —
  confirm they still do under their respective filter drops).
- **R3-P4 (S4):** both C3 waits are bounded; kill-resilience improved — run the
  concurrency subset twice; confirm zero residue (rule 11½), and note the
  arithmetic reconciliation (focused 139 vs suite 1892 = +17 over r2's 1875).
- **Suite:** 1892 / 23 / 1 expected; failure set byte-identical (N14 caveat).

## Step 3 — closing notes

The 47 graph items + N7's 2 missing edges stay held (your r2 predecessor
supplied final spans; this fix touched NO production file, so those spans
remain valid — confirm by spot-checking two).

## Closing protocol

1. Review log entry; tracker verdict (**APPROVED** expected if the delta
   verifies); stamps preserved.
2. Archgraph read-only: revision `bf6dad5b…`, 47 pending, zero delta — state it.
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-13_phase4_rereview_r3_handoff.md`
   (full path, AFTER your writes): summary; `⚠ OWNER DECISIONS REQUIRED (n)`;
   probe results; full write perimeter + probe declaration.
