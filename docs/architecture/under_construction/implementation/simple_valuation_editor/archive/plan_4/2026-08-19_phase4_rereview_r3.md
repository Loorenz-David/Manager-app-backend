---
plan: 4
role: reviewer
round: 3
date: 2026-08-19
project: simple_valuation_editor
kind: re-review — delta-scoped, narrow
---

# Session prompt — re-review r3, phase 4 (`simple_valuation_editor`)

## 1. Review history

**r1**: `CHANGES_REQUESTED`, 3 blocking / 4 should-fix / 3 notes. All applied verbatim.
**r2**: `CHANGES_REQUESTED`, 1 blocking / 4 should-fix / 3 notes. **All eight applied.**

r2 closed S1, S2, S3, S4, N2, N3 outright and confirmed B1's substance, B3's boundary
statement, §7.4's table row for row, and §7 amendment 3's five factual claims. **None of that
is re-opened.** In particular:

- **S1 is closed by the strongest probe either round ran** — a wrapper-aware transitive import
  walk over all 82 modules reachable from `services/queries/item_economics/`, seven clock
  primitives, 41 hits, exactly two on a read path, and the correction names exactly those two.
- **§4's BigInt block and the worked example** were executed independently at r1 (612 cases,
  0 mismatches) and are settled.
- **The `can_commit` prose** matched the code condition for condition at r1.

## 2. The delta — eight corrections, and the one thing they have in common

r2's three unclosed findings all failed the same way: **the r1 fix landed where the finding
pointed and not where the same defect also lived.** This round's corrections were made with a
`grep` for each affected field first, and the fix perimeter was confirmed before editing. **Test
whether that worked.**

| # | What changed |
|---|---|
| **R1** (blocking) | §3's render table rebuilt: ⚠ markers per row, a gating sentence above it, `max(1, quantity)` in four rows, `2 750` replacing `2 700`, and a two-check warning on the byline row. Action item 6 rewritten to name both absences. |
| **R2** | `profile_picture` annotated; the closed-set summary line replaced with a full two-direction enumeration. |
| **R3** | "the two always move together" replaced at **both** sites (§5.2 item 3 and §6.1). |
| **R4** | The refetch instruction: both events named, scope corrected to workspace-wide, and the fact that `item:updated` has never been published to the frontend stated plainly. |
| **R5** | §7.4 moved out of the amendments section to **§5.5**; the apology restored beneath amendment 3; three cross-references retargeted. |
| **R6, R7** | The guard sentence now describes the sweep that actually fired; the dangling "collapsibility qualification" reference retargeted to §5.2 item 4. |
| **R8** | Routed to **plan 5** — not fixed here. |

## 3. Probes

### P1 — did the grep-first discipline actually work?

r2's lesson 1 is that a field-level finding's perimeter is *every section naming that field*.
This round the coordinator grepped for `saved.`/`created_by`, for every division by `quantity`,
and for `2 700`/`2 750` before editing, and confirmed all three defects lived only in §3.

**Verify that independently.** Grep the document yourself for each corrected field and check
that no site was missed a second time. Specifically: is there anywhere else that dereferences a
nullable through a chain, divides by a bare `quantity`, or prints a superseded literal?

### P2 — attack r2's replacement text as adversarially as r1's

**This is the round's central instruction, and it comes from r2's own lesson 4.** Three of r2's
five findings were defects *in r1's proposed wording* — "the two always move together" was
false, and the refetch instruction under-covered a mechanism r1 itself had described one
paragraph earlier. Verbatim application is the right protocol and it means **reviewer prose
enters the document with no second reader.**

So: r2's replacement text is now in the document, unreviewed. Read it as if the coordinator had
written it. In particular —

- **§3's new ⚠ table.** Does every marker point at a real nullability, and is any row missing
  one? The `AT PRICE` row says "gate on `model !== null`" — is that the correct gate for that
  row, given `anchors` and `domain` are separately null-able within a present `model`?
- **§2's new enumeration.** It is a closed set, written by a fix, which is exactly the shape R2
  faulted. Walk it against the serializer once more. Is `config_fingerprint` correctly in the
  nullable list? Is `anchors.is_fundable` correctly in the non-null list *conditioned on
  `anchors` being present*?
- **§6.3's new refetch paragraph.** It now tells the frontend to refetch on **any** task's step
  transition in the workspace. Is that operationally sane for a screen that may be open while a
  busy floor transitions steps every few seconds — or has the correction traded a stale screen
  for a refetch storm? If so, that is a finding, and the honest answer may be a debounce
  sentence.

### P3 — §5.5's new home

The block moved from §7 to §5.5. Check: the three cross-references now point at §5.5; §5.5 sits
where §5.2 item 1's reader is standing; the apology reads as attached to amendment 3 again; and
§7's opening still says "these three amendments" and is now true.

### P4 — the production-time reply

Only §1 and §6 changed there, both at r1, and r2 verified both. **Read it once end to end
anyway** — it has had no structural review since, and the passing-glance clause applies.

## 4. What a finding looks like

Same as r2. **"True, but I had to read it three times" is a should-fix**, not a note — the
audience implements from a skim.

If the verdict is `APPROVED`, say so plainly and state what the frontend now has. This document
has been through three rounds; the bar is that it is correct and usable, not that it is
perfect.

## 5. Closing protocol

Deposit at `handoffs/reviewer/2026-08-19_phase4_rereview_r3_handoff.md`, charter frontmatter.
State **explicitly whether each of R1–R7 is closed** (R8 is plan 5's). Findings by severity with
verbatim replacement text. Carry-forward table if approving with notes. Full write perimeter —
**you write no handoff.**

Do not update the master plan tracker or plan 4's Review log.

## 6. Environment

- No code changed in any phase-4 round. `tests/unit/docs/` re-verified green after every
  correction (59 passed).
- Plan 3 is in flight under `app/` and plan 5 is now planned against
  `tests/unit/docs/test_item_economics_handoff_accuracy.py`. Neither is yours.
- If you run the full suite, expect **2425 / 26 / 1** unless plan 3 has landed; a disagreement
  in the count is repeated and **ID-diffed** before any conclusion.
