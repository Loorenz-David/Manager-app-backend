---
plan: phase 9 (living docs & drift routing — the LAST phase of v1)
role: reviewer
round: 1
date: 2026-08-15
---

# Session prompt — review phase 9 implementation r1 (the last review of v1)

You are the **reviewing agent** for phase 9 — the final phase. The
implementation is mostly PROSE, so this review is mostly READING: the
accuracy arbiters check that names, routes, keys, and identities grep to
shipped artifacts, but only you can verify that the SENTENCES are true —
the flow narratives, the request/response semantics, the setup story, the
two-cost explanation. A handoff sentence that misleads the frontend is
this phase's silent-money-loss equivalent. Approve only what you have
read.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10). You ALSO need read
access to `ManagerBeyo-app/frontend/` and
`/Users/davidloorenz/Desktop/Developer/Application_contracts` — stop and
report if absent.

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Ground

- Plan: `plans/phase_9_docs_and_drift.md` — base + Scope addition +
  forward notes + **P1–P22 GOVERNING**. R19-1
  (`planning/owner_decisions.md`): TWO handoffs, all 23 endpoints, split
  for the owner's two-stage frontend build — each buildable-from ALONE
  for its half. Intention §6A.4/§8A.2 (the quoted literals), §11A.2,
  §11A.4/§7C.3 (values vs ORDER — P16). Master plan §6.4/§6.5, §9 ALL.
- Checkpoint: **`4b648c0`** (effective; the handoff's perimeter table
  cites `71616af`, a pre-amend object — coordinator verified the two
  trees differ only in 2 planning-doc lines, `app/` identical; the
  phase-2 amend class, recorded not re-filed). Handoff:
  `handoffs/implementer/2026-08-15_phase9_implement_r1_handoff.md`.
- Coordinator consumption (verified, do not re-litigate): 10 sampled
  hashes byte-identical ACROSS ALL THREE REPOS (backend docs/models/
  migration; the frontend's exactly-two modified files `7ace7e17…` /
  `306694cc…`; both Application_contracts files); graph 175/260,
  1 pending (`decision-money-audience-admin-manager-only`, type decision
  — HELD for the closeout pass), 1 stale (the config-status source link,
  CONTENT drift from the N3 edit inside its span — the known
  link-re-accept repair, closeout pass), rev `7dcdb9b0…`.

## Environment facts

- Head `c1d2e3f4a5b6` (the only migration touch is P10's docstring).
  Declared suite: **2249 / 23 / 1 = 2272 selected (2273 collected)**,
  +65 reconciled (8 C1 + 3 P3 + 4 C4 + 50 accuracy); failure set declared
  byte-identical — the sorted diff is YOURS. Fifteen touched Python files
  ruff-clean declared.
- The frontend repo's two files are UNCOMMITTED by design (the
  implementer correctly declined to commit another repo's history) — the
  owner decides at closeout; verify the hashes still match and nothing
  else moved there.

## Probes (minimum — the ledger is yours)

- **P9R-1 — READ the prose.** All four `docs/domains/item_economics/`
  files and BOTH handoffs, sentence by sentence, against shipped
  behavior. Priority checks: the operational handoff's flow narratives
  (the 8B one-call flow incl. branch-B's exact refusal semantics; the
  two-call create→budget-status flow; R17-1's boundary label; the
  removals framed as "present, always rejected" where the keys are
  retained); the configuration handoff's setup narrative (category
  contract, dual-path identities, term types — could a frontend dev
  build the settings screen from it ALONE?); `states.md`'s chain +
  binding semantics; `api.md`'s payload catalogs vs the serializers.
  Wrong sentences are BLOCKING here.
- **P9R-2 — the 65-node arbiter suite read hard** (nobody but its author
  has read it): the hand-written sets verified against §6.4/§6.5 BY HAND
  (is "30 literal + 6 composed identities" the real census of §6.4? are
  the 13+10 route sets the real 23?); the heading-level equality and
  path-normalisation mechanics; C1's `parents[4]` anchor arithmetic
  (verify it resolves from the test's real location); the
  whitespace-normalisation doesn't make a reword pass.
- **P9R-3 — mutations:** re-run M1/M2/M3 from their declared mutant
  bytes (reproduces/differs per row) and at least two of the four
  self-chosen probes (P-c and P-d recommended — they guard the handoff
  arbiters). Reversion proven, tree == `4b648c0` blobs.
- **P9R-4 — the eleven annotations are INERT:** verify each of the
  eleven sites carries an EXPLICIT column type (`Numeric(...)`) so
  `Mapped[Decimal]` changes typing only; run `alembic check` and confirm
  the diff set is EXACTLY the three pre-existing drifts (a fourth entry
  = the annotations changed metadata = blocking); the five new
  `from decimal import Decimal` imports are judgment call 9 — confirm
  no `__future__` interaction. Run the item-economics integration scope
  once (the 519-node claim).
- **P9R-5 — the judgment calls (ten declared):** each against its
  authority — esp. #1 (the published ORDER: branch condition vs
  precedence — does `states.md`/§6 read correctly per §11A.4/§7C.3?),
  #3 (annotate-not-delete on the frontend request-body rows — verified
  right call?), #10 (the `//` in a JSON example — acceptable or does it
  mislead a copy-paster?).
- **P9R-6 — the README batch vs the P-enumerations:** spot-verify P5/P9/
  P11/P15/P18/P19 landed exactly (the tables index 71 rows; the six
  tasks-README sites; the prefix map's nine rows sorted in, file NOT
  resorted; the PUT-table repair per F16 incl. the banner; the old
  handoff's :166/:393; the runbook + api.md split).
- **P9R-7 — numbers + the drift-filed list:** full suite foreground;
  sorted byte-diff; +65 reconcile per file; ruff; DB at head; committing
  subsets twice if you run any (residue named). VERIFY each of the 8
  filed drift items is real (they are claims like any other) and that
  each P22 tick the implementer claimed holds.

## Closing protocol

1. Verdict, counts from the ledger (P-L); story-shaped owner cards only
   for semantic decisions.
2. Your mutation rows: hashes copy-pasted, observed reds, reversion
   proven.
3. If APPROVED: the full v1-closure carry-forward table (P22): the 1
   pending node + 1 stale link → the coordinator's closeout pass; the
   frontend commit decision → the owner; the 8 drift items → named
   destinations; the post-v1 handoffs enumerated (squash seed Findings
   1–8, N11 residue prompt, bridge-validator removal, §11 entries, the
   phase-7 ival row).
4. Deposit AFTER your writes, citing final hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-15_phase9_review_r1_handoff.md`
   (full path): findings ledger; the prose-verification record (which
   documents you read fully); mutation ledger; full write perimeter +
   probe declaration; lessons.
