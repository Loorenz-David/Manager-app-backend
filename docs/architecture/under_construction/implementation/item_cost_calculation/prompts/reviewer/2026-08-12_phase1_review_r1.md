---
plan: phase 1 (worker money redaction)
role: reviewer
round: 1
date: 2026-08-12
---

# Session prompt — review phase 1 (first review, full checklist)

You are the **reviewing agent** for phase 1 of the item-cost-calculation pipeline.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path, in this order)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` — shared charter.
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — your session doctrine.
   This is a FIRST review: full checklist against plan criteria and semantic
   authorities; adversarial re-derivation; mutation-tested tests.

## Gate check (verify before working; on any failure, stop and report)

- `master_plan.md` §4 tracker shows phase 1 **IMPLEMENTED** (actor Codex).
- Implementer handoff exists:
  `handoffs/implementer/2026-08-12_phase1_implement_r1_handoff.md`
  (checkpoint commit `4416570`).
- The phase-1 plan's Review log carries the implementer's entry.

## Read order (after doctrine)

1. `plans/phase_1_worker_money_redaction.md` — criteria (rows 1–16, 15b, 17–25),
   named mutations M1–M6 + the two blanket-False probes, Notes (pinned handling of
   the two pre-existing tests; scope fences).
2. Intention §11A.1–§11A.3 **including the §11A.2 round-5 correction** (the
   eight-endpoint census — re-derive it yourself; do not trust any census).
3. `master_plan.md` §§5 (both contract-gap records), 9, 10.
4. The implementer handoff — their judgment calls are your probe list.
5. The diff under review: `git diff 545e504..4416570`.

## Coordinator probes (from adversarial consumption of the handoff — verify, don't trust)

- **P-R1 (baseline validity — the sharpest probe):** the recorded pre-change
  baseline ran in a sandbox with PostgreSQL/Redis denied (1092 passed / 473 failed /
  38 errors — meaningless), so the claim "22 failures are pre-existing and outside
  this phase" was made post-hoc. Verify it: run the suite at the pre-phase commit
  (`git worktree` or stash-checkout `545e504`; disposable state only; restore
  exactly) and confirm the same 22 fail there; or, failing that, establish from each
  failure's content that it cannot touch this phase's perimeter. If any of the 22 is
  attributable to this phase, that is a finding.
- **P-R2 (criteria mapping):** map each of the 26 criteria rows to one specific
  asserting test on the pinned harness (query-service-level integration;
  `ServiceContext` identity; real ORM `TaskStep`; present rows assert equality with
  seeded `4321`; absent rows assert key ∉ dict). Any row satisfied by a router-idiom
  test (stubbed `run_service`) violates the plan's harness pin.
- **P-R3 (mutations):** the handoff claims M1–M6 + two blanket-False probes were run
  and reverted. Confirm the committed tree contains no probe remnant (the diff is
  your evidence), then independently re-run at least M4, M5 (the shared-builder
  mutations — highest value: they must also turn the round-5 endpoint rows 19/22
  red) and M6 (deny-list flip → row 25). Revert your probes; declare them.
- **P-R4 (characterization authority):** the working-section characterization test
  was re-parametrized by role — verify it asserts worker → key absent AND
  manager → key present-with-value (not a deleted key), and that the key-set change
  is recorded in the Review log. The ended-shift test must show exactly a one-token
  keyword addition, no assertion change.
- **P-R5 (fixture sole-predicate):** the implementer reused an existing
  working-section seed helper — check each redacted row's fixture makes redaction
  the ONLY reason for absence (non-NULL seeded money), and no fixture satisfies two
  sufficient causes (charter rule 2 companion).

## Scope-fence verification

`serialize_item` untouched; the three round-5 endpoint query services untouched;
serialization not relocated to routers (master plan contract-gap 2); ADMIN/MANAGER
money retained everywhere including both worker-stats endpoints. The diff is the
perimeter evidence — anything outside the handoff's declared write perimeter is an
automatic finding.

## Constraints

- Full suite run per master plan §10 (`PYTHONPATH=. pytest -m 'not e2e'` from
  `backend/app/`, healthy containers via `make dev-up`).
- **Execution environment:** run all test/baseline commands **with elevated
  permissions** — PostgreSQL and Redis are local Docker services on
  `127.0.0.1:5433` and `127.0.0.1:6380` and are inaccessible from the normal Codex
  sandbox (master plan §10 caveat; this is what invalidated the implementer's
  baseline). If elevation is unavailable, stop and report — never record a
  sandboxed run as evidence.
- Findings go to the phase plan's **Review log** (append-only) with severity
  (B/blocking, S/should-fix, N/note); your tracker row update only
  (IMPLEMENTED → REVIEWING → your verdict: APPROVED or CHANGES_REQUESTED).
- Archgraph: status + orientation read-only; the implementer recorded an explicit
  zero delta — verify that judgment (this phase changed payload behavior of an
  existing surface; a zero delta is plausible, confirm or file).
- Anything seen wrong in passing outside settled areas: report it (charter re-review
  clause applies to first reviews too).
- Do not fix anything — findings, not patches. Mutation probes are run-and-reverted.

## Closing protocol

1. Review log entries in `plans/phase_1_worker_money_redaction.md` (append-only).
2. Tracker row (yours only): verdict state + one-line note.
3. Deposit the handoff at
   `handoffs/reviewer/2026-08-12_phase1_review_r1_handoff.md` with frontmatter
   (`plan`, `role`, `round: 1`, `date`, `state`, `verdict`, `actor`) and body:
   summary; `⚠ OWNER DECISIONS REQUIRED (n)` (one line if zero); findings by
   severity with file:line and the exact correction clause per finding (fix prompts
   quote these verbatim); probe results P-R1…P-R5; lessons for the plans; your full
   write perimeter (expected: Review log, tracker row, your handoff, reverted
   probes — declared).
