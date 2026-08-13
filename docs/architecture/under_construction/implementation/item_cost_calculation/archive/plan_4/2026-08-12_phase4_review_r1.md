---
plan: phase 4 (configuration services)
role: reviewer
round: 1
date: 2026-08-12
---

# Session prompt — review phase 4 (first review, full checklist)

You are the **reviewing agent** for phase 4 of the item-cost-calculation pipeline.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — FIRST review: full
   checklist, adversarial re-derivation, mutation-tested tests.

## Gate check

- Tracker: phase 4 **IMPLEMENTED** (Codex, checkpoint
  `98c75a8c6fa96d1e181f158721abb592bf9ff12a`, final; the handoff deposit
  `6aa908d` and the coordinator's round-12 commit `617e1d0` sit above it —
  attribute those correctly).
- Handoff: `handoffs/implementer/2026-08-12_phase4_implement_r1_handoff.md`.
- **Scope note:** phase 4 reviews against its plan as amended (the ONE-group
  §7A.5 rule). Intention §7C / round 12 (category selection) is phase 4B's —
  do not file its absence here.

## Read order (after doctrine)

1. `plans/phase_4_configuration_services.md` — the amended criteria C1–C11, the
   harness block, tasks 1–7, and the implementer's Review log entry.
2. Intention §7A entire, §6A.1 round 11 (canonicalize-then-derive), §6A.4 + R4-2,
   §6A.6, §11A.4; master plan §§5, 6 (identities incl. the three dual-path
   conflicts + audit vocabulary), 9, 10.
3. The handoff — its judgment calls and its framing are your probe list.
4. The diff: `git show 98c75a8` (28 files, ~2.3k insertions).

## Coordinator probes (verify, don't trust — the first two are pre-measured)

- **P4-1 (THE probe — criteria coverage arithmetic, coordinator-measured):** the
  three new test files collect to **7 test nodes** (verified:
  `test_configuration_commands.py` + `test_configuration.py` +
  `test_item_economics_requests.py`); the full suite grew 1749 → 1755 passed
  (+6). The handoff's "phase-focused suites: 72 passed" includes phase 3's 65
  calculator tests — a P-L framing violation (a declared figure must state what
  was built for THIS phase). Map every C1–C11 criterion row to a collected test
  node id; produce the uncovered-row inventory with exact counts (C1 alone
  enumerates 20 admission rows; C5 twelve cells; C10 four rows × three queries;
  C11 per-route). File the gap with verbatim correction clauses per criterion.
- **P4-2 (L8 partial compliance):** the mutation ledger's "observed node ID"
  column cites ARCHGRAPH anchors, not pytest node ids, and describes reddened
  tests in prose. Re-run every declared mutation yourself (C1's is_deleted drop,
  C4's canonicalization bypass, C5's blanket-conflict collapse, C11's MANAGER
  removal, C8's structural probe) and record the observed pytest ids; note that
  with only 7 tests, verify what each mutation ACTUALLY reddens.
- **P4-3 (C6 concurrency — declared deferred):** the implementer did not execute
  C6(a)/(b) (honest declaration). The production code claims `FOR UPDATE`, the
  in-lock re-check, and the `after_lock` seam — verify by reading AND by running
  the plan's harness block yourself for at least C6's interleaved row and one C3
  chain race (committed sessions, lock timeout, teardown). If the harness cannot
  be built as pinned, that is a plan finding, not silently absorbed.
- **P4-4 (production-code quality of the delivered surface):** independently
  verify the load-bearing mechanisms in code: canonicalize-then-derive order in
  the request models (R11-1 — the B1 fixture math), index-name discrimination
  with re-raise default (`_common.py` — P-K: audit this shared helper for
  constraints it pre-satisfies), admission table totality, classifier precedence
  from `CONFIGURATION_FAILURE_PRECEDENCE` (never enum iteration), `is_applicable`
  half-open predicate, `has_open_*` vs applicability divergence (the handoff
  flags it as a judgment call — is it §7A.3-consistent?), router-model
  `percent_value` docs (P-D wording), no term-mutation route, deliberate
  no-event absence, audit events match the registered vocabulary exactly.
- **P4-5 (smuggled field):** the `extra="ignore"` judgment call matches the plan's
  N4 pin (succeeds; persisted == derived) — verify with the C4 row.
- **P4-6 (graph delta — §8 standing flow):** 47 pending items (9 command nodes,
  13 endpoint nodes, 25 relationships; revision `bf6dad5b…`). Per item: read the
  cited code BEFORE the stored claim (anti-pattern rule); report claim/anchor
  verdicts and a recommended decision (promote/edit/reject) in a table. Do NOT
  adjudicate. Watch especially: route paths vs §6.5's registered surface, and
  whether endpoint nodes carry the ADMIN/MANAGER gate claims accurately.

## Constraints

- Full suite per master plan §10; baseline: 23 known failures (byte-identical
  set; N14 flake caveat). Findings → Review log (append-only), severity + verbatim
  correction clauses; tracker row yours only, stamps preserved. Findings, not
  patches. Mutations in disposable worktrees; revert, sha256, declare per row
  with observed pytest ids.

## Closing protocol

1. Review log entry; tracker verdict (APPROVED / CHANGES_REQUESTED).
2. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase4_review_r1_handoff.md`
   (full path, AFTER your Review-log/tracker writes): summary; `⚠ OWNER DECISIONS
   REQUIRED (n)`; probe results P4-1…P4-6 (P4-6 as a per-item table); findings by
   severity; lessons; full write perimeter + probe declaration.
