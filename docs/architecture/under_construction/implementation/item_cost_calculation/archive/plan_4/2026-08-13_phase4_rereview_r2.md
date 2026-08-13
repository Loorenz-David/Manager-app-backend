---
plan: phase 4 (configuration services)
role: reviewer
round: 2 (re-review, delta-scoped)
date: 2026-08-13
---

# Session prompt — re-review phase 4 after fix cycle r2

You are the **re-reviewing agent** for phase 4. Delta-scoped per the charter —
settled ground is not re-derived; anything seen wrong in passing is reported.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(project folder: `docs/architecture/under_construction/implementation/item_cost_calculation/`).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` (re-review protocol).
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (settled — do not re-derive)

- **r1 (Claude, CHANGES_REQUESTED):** the MECHANISMS were verified correct and are
  settled ground (Review log "verified independently" section: 20/20 admission in
  code, both chain races on the real DB path proven by the reviewer, 12 term
  cells, classifier precedence, canonicalize-then-derive, audit vocabulary, no
  term routes, no events). Open: B1 coverage ~6/60; B2 out-of-range → 500s; S1
  router advertised the derived rate; S2 dead scaffolding; N2 `.value`
  comparison; S3 was PLAN text (amended by the coordinator: C6 observable, C5
  reachability, B2 bounds block).
- **Fix r2 (Codex, checkpoint `4e19506`, final; handoff after, citing it):**
  +119 tests exactly (focused 126 = 7 + 119; full 1875/23/1); production delta
  small and scoped (−1 router field, `_common` trims, bounds in requests, enum
  member comparison); twelve mutations declared with observed pytest ids AND
  per-mutation sha256 pairs. Handoff:
  `handoffs/implementer/2026-08-12_phase4_fix_r2_handoff.md`.
- **Deviation to verify, not auto-file:** mutations ran in **disposable local
  clones** (the managed workspace's `.git` cannot create worktrees). Verify the
  current files hash to the declared "main" sha256 values and match `4e19506`'s
  blobs; if they do, the deviation is procedural (note it).

## Step 1 — verified perimeter

`git show 4e19506` = 5 production files + 3 test files + tracker row + Review
log (10 files, ~923 insertions). The handoff deposit `187efb9` carries only the
handoff. Anything else is a finding.

## Step 2 — delta probes

- **R2-P1 (coverage closure):** map the amended C1–C11 to the shipped rows —
  the r1 inventory demanded ~54; confirm each criterion family is now enumerated
  (C1's 20 parametrized outcomes against §7A.4's table row-for-row; C5's 12
  cells; C8's six through the STATUS QUERY; C10's 14; C11's per-route rows on a
  NAMED harness per P-R — which harness did they use?). Any still-missing row is
  a finding with its clause.
- **R2-P2 (mutations, sampled):** re-run at least C6(b) (the corrected
  `reference_blocked_while_locked` observable), C8 (precedence swap), C11
  (MANAGER removal — this reddened NOTHING in r1; confirm it now reds the
  retention row), and B2 (the `gt=0` drop). Observed pytest ids; sha256-verified
  reverts.
- **R2-P3 (the races are genuine):** the C3/C6 concurrency tests use committed
  sessions from `_session_factory()`, lock timeouts, and `try/finally` teardown
  per the harness block — NOT monkeypatched flushes; run them twice in a row to
  prove teardown leaves no residue (r1's killed-run lesson).
- **R2-P4 (B2 totality):** all eight r1-proven 500 cases now 422/ValidationError
  naming the field; adjacent-pair boundary rows exist per bound; canonicalization
  rows (R11-1) still green — P-U says these are separate criteria, verify both
  sets independently.
- **R2-P5 (production trims):** S1 field absent from the router model (and the
  OpenAPI schema); S2 dead helpers gone or wired; N2 member comparison (no
  `.value`); N10 vestigial assignment gone.
- **Suite:** 1875 / 23 / 1 expected; failure set byte-identical (N14 caveat).
  Focused 126.

## Step 3 — anchors service for the held graph adjudication

The 47 pending graph items (r1: 17 promote / 30 edit-then-promote) are STILL not
yours to adjudicate. But the fix moved lines in 4 of the anchored files. As a
closing service (like phase-3 card 3): for the r1 "edit" recommendations whose
files this fix touched (`item_economics.py` router endpoints, the 5 imprecise
command nodes, the 25 blanket-anchored edges), supply CURRENT corrected spans in
your handoff so the coordinator's single post-approval adjudication uses final
line numbers.

## Closing protocol

1. Review log entry (append-only); tracker verdict (**APPROVED** expected if the
   delta verifies); stamps preserved.
2. Archgraph read-only: revision `bf6dad5b…`, 47 pending, zero delta from the
   fix — verify and state.
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-13_phase4_rereview_r2_handoff.md`
   (full path, AFTER your Review-log/tracker writes): summary; `⚠ OWNER
   DECISIONS REQUIRED (n)`; probe results; the anchor-spans table; findings if
   any; full write perimeter + probe declaration.
