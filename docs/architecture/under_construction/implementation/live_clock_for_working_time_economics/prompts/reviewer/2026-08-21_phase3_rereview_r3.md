---
plan: 3
role: reviewer
round: 3
date: 2026-08-21
project: live_clock_for_working_time_economics
---

# Session prompt — plan 3 re-review r3, `live_clock_for_working_time_economics`

## 1. Role and mode

**Re-review of a fix cycle — delta-scoped**, per the charter's review protocol. You are
not re-reviewing the phase; you are reviewing what fix r2 changed, plus anything you see
wrong in passing (that clause has caught real bugs here and is not decorative).

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (suite: `PYTHONPATH=. pytest -m 'not e2e'`)

**Read first, by absolute path, as doctrine:**
1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` — including
   **"Test-evidence scope and reuse"**, which governs §4 below.
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## 2. Review history — what is settled, and by whom

- **Implement r1** (checkpoint `5b8329b`): D9 built at the two serializer feed sites.
  Review r1 found **0 blocking** and confirmed the production code correct; N-4 is applied
  with the right argument order, guarded by `result is not None`, HC-4 holds.
- **Review r1** (`184f48a`): CHANGES_REQUESTED — 2 should-fix, 6 notes, **all in the proof
  and the documents, none in the code**. S1: the plan/intention/tracker attributed the
  status-blanking guard to C6 row (b), which measurably passes under that edit. S2: the
  frozen percent's over-budget region was guarded by nothing in the repository (∅/∅ at L4
  under a clamp-at-100 mutant).
- **Coordinator fold**: S1's document half corrected in three places (intention §5.3A,
  plan §5 C6, master tracker); C6b's re-specification made **required**; **C6c** added to
  the plan; §5B gained the output-range corollary.
- **Fix r2** (checkpoint `874f02d`): test-only. C6b re-specified, C6c built, N1 and N4
  applied. **No production file changed** — verified.

## 3. Gate check — stop and report if any is false

- `master_plan.md` §3 shows phase 3 at **REVIEWING (re-review r3)**.
- HEAD is **`874f02d`** (`CHECKPOINT (not approved): phase 3 fix r2`).
- `git diff 5b8329b 874f02d -- app/beyo_manager/` is **empty** (no production change
  across the fix cycle). *This* is the perimeter condition, not a clean `git status`.

**⚠ A foreign, uncommitted change stream is in the working tree — read before you run
anything.** `app/beyo_manager/services/infra/shopify/product_sync_client.py` (+47),
`…/shop_client.py` (+27) and an untracked `app/scripts/shopify/` are modified by work
outside this pipeline. **They are not yours: do not commit, revert, stash or review
them**, and their presence is not a perimeter finding against fix r2 — the coordinator
dated them by digest and they appeared **after** fix r2's stamp (the `app/`-scoped diff
including them hashes `2d7604fe…`, while the declared stamp digest `b50bda39…` matches
the committed-only diff exactly).

Two consequences you must handle rather than absorb:
1. **Any L4 run you perform includes them**, because they are uncommitted. The 26-ID
   baseline contains Shopify rows (`test_create_shopify_metafield_preferences.py`), and
   one of the two named flaky tests is
   `test_process_shopify_products_integration.py`. If your counts differ from the cited
   `26 / 2487 / 1`, **capture the failing-ID set first, then attribute** — foreign-stream
   effect, flake, or real regression are three different answers and a bare count cannot
   tell them apart.
2. Prefer L1/L2 scopes for this delta-scoped round, which keeps you clear of the foreign
   surface entirely. Escalate to L4 only for a hypothesis that genuinely needs it, and
   record the foreign state in that evidence record's tree-identity field (SHA + a
   `git diff` digest, since the tree is dirty).

## 4. Evidence — what NOT to re-run

The coordinator verified all of the following independently at consumption. Re-deriving
them wastes the round; **contradicting** one is a finding worth reporting loudly.

- **Tree identity**: fix r2's declared dirty-diff digest
  `b50bda39cf505b208897233ed3e90121ec2e9c41c12f96e354cbc77b76d14d2f` reproduces exactly as
  `git diff ac953a0 874f02d -- app/`. Its L4 stamp — **26 failed / 2487 passed / 1
  deselected**, baseline IDs unchanged both directions — is tree-valid and **citable, not
  reproducible**. The `+1` (not the prompt's forecast `+2`) is correct: C6c adds one test
  function, C6b was re-specified rather than added. The forecast was the coordinator's
  error and the implementer flagged it.
- **Perimeter**: five files in `874f02d`, exactly the declared five; nothing under
  `app/beyo_manager/`.
- **S1 closure**, verified at source: C6b now sets frozen `15.00 / −15.00` with the
  **current** evaluation at `20.00`, asserts `status == "ok"` on **both** faces, and its
  comment was rewritten to claim only what the fixture shows.
- **S2 closure**, verified at source: C6c asserts `"150.00"` on both faces with `status ==
  "ok"`, from frozen `15.00 / −5.00` → reconstructed `10.00`.
- **N1** (`before["budget"]["percent_consumed"] == "120.00"`) and **N4** (the comment above
  `test_c17`) are present.
- **Coordinator probe, new evidence for you**: the C5 mutant (unconditional
  `actual`-alone denominator) at the E-P site now reddens `test_c3`, `test_c6a`,
  `test_c6b`, **`test_c6c`** and `test_c17` — 5 failed / 31 passed over the two phase
  files at `874f02d`, probe reverted and `division_serializers.py` verified byte-identical
  at `d9160f92…`. **C6c has been added to C5's expected class 2 in `plans/plan_3.md`.**

Spend your budget on **variation**: sites, conditions, fixture shapes and mutant shapes
nobody has run. Scope each probe to its hypothesis (§5B assigns scopes); an absence claim
is L4 by construction, a named-row bite is not.

## 5. Probes

- **P1 — C6c is new text with exactly one author and one reader.** It guards the most
  consequential number the frozen block serves. Attack it: is `"150.00"` non-vacuous on
  that fixture (what is the *live* percent there, and do they differ)? Does the both-faces
  assertion genuinely exercise two branches? Could any single wrong implementation satisfy
  C6c *and* the rows it sits beside?
- **P2 — is the region enumeration now complete?** §5B's new corollary binds criteria to
  enumerate the regions the authority names. OD-10's premise table names three. Walk the
  frozen percent's full output space — including the exact `100.00` boundary and whether
  anything below `0` is reachable — and say whether a region is still unguarded, or state
  plainly that the enumeration closes.
- **P3 — does C6b now prove what its new comment claims?** It says the `null` is undefined
  *"solely because the frozen basis is non-positive"*. That is a prose claim and inherits
  the mutation rule. Verify the fixture can actually demonstrate "solely" — and confirm
  the S1 inversion is gone from every document that carried it (three were corrected).
- **P4 — the fix cycle's own blast radius.** C6b changed fixture values that other rows
  may share. Did re-specifying it weaken any *existing* row's discrimination? Check
  whether any row's expected value now coincides with a value it is meant to tell apart.
- **P5 — the database the evidence was measured on (raised by fix r2, measured by the
  coordinator; now in master §6).** Every stamp in this pipeline was taken against the
  **development** database (`app/.env` → `…:5433/beyo_manager`), while `app/.env.testing`
  designates `…:5432/app_test`, which is stamped at `67cfba8fcb2d` with 96 tables and
  **lacks `cost_model_versions` and `item_cost_results`**. Your question is narrow and it
  matters for the approval gate: **is a baseline measured on the development database
  acceptable evidence for approving this phase**, given phase 4 publishes that baseline
  for the next pipeline? Recommend; the owner decides if you think it needs them.

## 6. Closing protocol

Mutation-probe declaration (files touched, reverted, byte-identity verified) and every
state side effect restored; a carry-forward dispositions table if you approve with open
notes; tracker row (**your row only**) → APPROVED or CHANGES_REQUESTED; technical findings
appended to `plans/plan_3.md`'s Review log; handoff at
`handoffs/reviewer/2026-08-21_phase3_rereview_r3_handoff.md` (frontmatter `plan`,
`role: review`, `verdict`, `date`, `actor`) with verdict, findings by severity, lessons for
the plans, and any owner item as a **decision card** (one line if none).

Your final message carries the layer-2 human briefing: 2–4 sentences of plain-language
state of the build, then a faithful narrative per blocking/should-fix finding in the
owner's own domain — this phase decides what percentage a *finished* job displays, so make
the consequence felt in kronor and minutes.

If the work holds, **approve plainly**. Do not invent findings for completeness.
