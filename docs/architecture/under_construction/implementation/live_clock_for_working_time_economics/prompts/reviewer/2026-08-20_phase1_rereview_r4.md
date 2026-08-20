---
plan: 1
role: reviewer
round: 4 (re-review)
date: 2026-08-20
project: live_clock_for_working_time_economics
---

# Session prompt — plan 1 re-review (round 4), `live_clock_for_working_time_economics`

## 1. Review history — what is settled, and by whom

- **r1 (full review, Opus 5):** CHANGES_REQUESTED — 2 blocking, 2 should-fix, 7
  notes. Its §4 *"Verified correct (so the re-review can skip these)"* list is
  authoritative: **C1–C10, HC-1A structurally, HC-2, N-1/N-3 conformance, the
  window-anchor derivation, and the goldens' composition and liveness are
  settled.** Do not re-verify them. Its own four production mutations (guard,
  attribution, settled-term, `int(round)`) are settled too.
- **r2 (fix, Codex):** closed B1, B2, S1, S2 and notes N1, N3, N7. Coordinator
  re-applied all four named mutations whole-suite; every observed-red set matched
  ID-for-ID. **Zero production lines changed.**
- **r3 (fix, Codex):** added the one C12 locus row from the coordinator's own
  finding F-C1. Coordinator re-applied M-locus and M-mode whole-suite: each added
  exactly its one intended ID and removed none, proving the three C12 rows are
  orthogonal. **Zero production lines changed.**
- **The production loader has not changed since checkpoint `a7659bc`.** Every
  round since has been about whether the tests prove what they claim.

Your scope is the **delta**: what r2 and r3 added, and anything you see wrong in
passing anywhere (that clause has caught real bugs on this project; it is not
decorative).

## 2. Role, workspace, doctrine

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (tests: `PYTHONPATH=. pytest -m 'not e2e'`)
Project folder:
`backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

Doctrine, read first by absolute path:
1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## 3. Step 1 — the verified perimeter (charter re-review protocol)

Before anything else, confirm from `git` — not from the handoffs — that r2 and r3
touched **only** their allowed files:

- `git diff --name-only ae7d723..HEAD` must be the union of: the phase test file,
  `plans/plan_1.md`, the two fix handoffs, and (from the coordinator's own commits)
  documents under the project folder.
- **`git diff ae7d723..HEAD -- app/beyo_manager/` must be empty.** Any production
  change in these two cycles is an automatic finding.
- `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py` must
  hash to `6d11b922fbec3031be49adf1313b6d1685bef95659caf81f2b6cb7e918fa82ca`.

Anything outside that perimeter is a finding regardless of merit.

## 4. Read order

1. `plans/plan_1.md` §5 (**C9 as amended, C11, C12's three rows** — the criteria
   this round is judged against) and §7 (the full round history including the
   coordinator's consumption records and F-C1).
2. The two fix handoffs in `handoffs/implementer/` (r2, r3) — claims to verify.
3. Intention §1A HC-3A (**as amended round 4c** — the fails-closed contract) and
   §3.1A A–B (type, mode, locus).
4. `master_plan.md` §5's rules earned this phase (identity-element, isinstance,
   failure-site-claims, the where-two-forms-differ rule) and §6 (baseline
   **26 / 2459 / 1**, ID set enumerated).
5. The delta itself: `git diff ae7d723..HEAD -- app/tests/`.

## 5. Full adversarial depth on the changed seam

- **C11's two rows.** Does each make its own predicate the only reason its value
  holds? Row (a) is `settled=100` + a 600 s share ⇒ 700; row (b) is `settled=250`
  with **no** record ⇒ 250. Check row (b)'s `create_record=False` helper branch
  actually produces a step with no state record at all (not a record in another
  state), and that the helper parameter has a caller (charter rule 4).
- **C12's three rows and their orthogonality.** The coordinator measured
  M-locus ⇒ only the locus row, M-mode ⇒ only the mode row. **Verify the third
  leg yourself:** does M-float (`+= contribution.seconds` alone) redden (a), (b)
  and (c) as r3's ledger claims? And is there a **fourth** property hiding in
  this seam that no row pins — e.g. the per-step accumulation form (`+=` vs `=`),
  which the one-open-record-per-step unique index may make untestable; if so, say
  so explicitly rather than leaving it unremarked.
- **The docstrings and comments added by r2/r3 are claims and inherit the
  mutation rule** (master plan §5). Four to check, each for *truth*, not
  presence: S1's ("the configured driver normalizes a naive bind before the
  sweep, so the sweep cannot raise — 0 rows observed"); S2's (`reset/phases/
  delete_step_state_records.py` is the **only** writer — sweep the class, verify
  no other writer exists); N1's (which mutation answers which half of the
  zero-cases row); N7's D1 comment (two overlapping 30-minute cross-task records
  ⇒ 900). A false sentence in the tree is a finding even where the test passes.
- **N3's added assertion** on C7 (`result[second.client_id] == 1800`) — does it
  hold for the right reason, and does it survive the C7 anchor mutation as
  expected?
- **The r3 count anomaly.** r3's ledger records that M-locus's first run read
  26 failed **with the new ID present** — i.e. a baseline ID vanished — and the
  repeat read 27 with the correct set. The coordinator's own M-locus run read 27
  cleanly. The repeat rule was applied correctly; the question for you is whether
  the vanishing ID is one of §6's two named flaky tests or a **third** one, which
  would be a new environment fact worth recording in §6.

## 6. Suite and mutation discipline

Full runs only; a count disagreeing with §6's baseline is repeated and its **ID
set** diffed before any conclusion. Every mutation you apply: both sides computed
for the named fixture, site named (file, definition-vs-call-site), whole suite,
reverted, revert hash verified. Declare every probe and its revert in your handoff.

## 7. Closing protocol

Deposit at `handoffs/reviewer/2026-08-20_phase1_rereview_r4_handoff.md`, charter
frontmatter (`plan: 1`, `role: reviewer`, `round: 4`, `verdict`, `date`, `actor`).

- Verdict **APPROVED** (0 blocking) or **CHANGES_REQUESTED** with findings routed
  by severity, each with exact artifact and `path:symbol` citation.
- Owner cards, if any, in ONE `⚠ OWNER DECISIONS REQUIRED (n)` section directly
  after the opening summary; one line saying "none" if none.
- **Carry-forward dispositions**: for any note you leave open, name the phase that
  inherits it. (r1's N2 is already folded upstream; its N6 — the graph evidence
  summary carrying a count — is already routed to `plans/plan_4.md` C6 for owner
  adjudication. Do not re-route those two; add only what is new.)
- Lessons for the plans, for the coordinator to fold.
- Your full write perimeter from `git status` / `git diff --name-only` — which for
  this session should be exactly the one handoff file.
