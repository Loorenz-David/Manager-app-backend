---
plan: phase 9 (living docs & drift routing — the LAST phase of v1)
role: implementer
round: 1
date: 2026-08-15
actor-intended: a Claude-model session (documentation-heavy; owner's choice)
---

# Session prompt — implement phase 9 (the last phase of v1)

You are the **implementing agent** for phase 9 — the final phase: the
living-docs folder, the TWO frontend handoffs, and the drift batch
accumulated across nine phases. Your output is mostly PROSE, and the bar
for prose here is the bar this project applies to code: every route, key,
identity, enum member, and line citation you write must be copied from the
shipped artifact, never paraphrased from memory. The projection verified
the current state of every file you will touch — its ledger is your map.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10). You ALSO need:
`/Users/davidloorenz/Desktop/Developer/Application_contracts` (P13) and the
frontend repo (`ManagerBeyo-app/frontend/` — P12). **If either is not
accessible in your session, STOP AND REPORT before writing anything.**

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## The plan — read BOTH layers as one document

`docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_9_docs_and_drift.md`:
base + Scope addition + forward notes + the **GOVERNING "Amendments
(projection r0)" block P1–P22** — it is your complete work list and its
enumerations are exhaustive. Key authorities: intention §6A.4/§8A.2 (quote
the literals verbatim into C1's test), §11A.2/§11A.4, R19-1
(`planning/owner_decisions.md` — the two-handoff split), master plan §6.4
(identities), §6.5 (the folder registration + the 23 routes), §9 ALL
rules (~65 — expected-red, P-I 10th line-pinning, hand-written-literal,
call-graph, pipeline-ends, set-assertion all apply to THIS phase's few
tests).

## Environment facts (projection-verified 2026-08-15)

- Head `c1d2e3f4a5b6` (no migration this phase — the ONLY migration touch
  is P10's docstring line, rule-7 exemption stated); suite baseline
  **2184 / 23 / 1 = 2207 selected (2208 collected)**; graph **174/260, all
  human_confirmed, 0 pending, 0 stale, rev `452befdb…`**.
- `docs/domains/` exists (precedent `worker_shifts/`); `docs/runbooks/`
  does NOT (P19 → `docs/deploy/`); `docs/handoff/to_frontend/` is the
  LIVE tier (its `archived/` is frozen — P18).
- No repo test reads a `.md` file — C1's harness is the first (P2's
  `parents[N]` anchor rule).

## The work (P-numbers are the plan block's; ordered)

1. **P1** the docs folder (four files + the `docs/README.md` row).
2. **P6** the TWO handoffs (operational + configuration) — the owner
   splits the frontend build on this boundary; each must be buildable-from
   alone for its half. **P18** the old reassigned-steps handoff
   correction.
3. **P15** the `routers/README.md` work (C4's hand-written 23-row
   arbiter; the PUT-table repair per F16's enumeration; the banner).
4. **P5/P9/P11** the backend README batch (tables index; items; tasks;
   prefix map — nine rows sorted in, file NOT resorted).
5. **P12/P13** the frontend mirrors + Application_contracts edits.
6. **P19** the deploy-ordering line in `docs/deploy/`. **P20** the two
   contract amendments (46_serialization_local rewrite;
   05_errors_local created).
7. **Code (P4's allow-list, NOTHING else):** P3's three structural rows +
   line-pinned mutations with expected-red ids stated BEFORE the runs;
   P7's C5 repair (close BEFORE the first run); P17's two-line hand edit
   (`ruff format` FORBIDDEN on that file); 4B N3's two clauses (:39/:49);
   P10's docstring line; phase-2 N8's proxy regex; N14's one line (:179,
   list→set); the ELEVEN annotations (P4 item 8, precedent
   `user_work_profile.py:33-34`).
8. **P14** the money-audience graph node — ONE additive delta at
   checkpoint (type declared; evidence at `serializers.py:150-155` +
   §11A.3), plus nothing else in the graph.
9. **P10** N4 WONTFIX rationale in the Review log (already seeded as
   squash Finding 8 by the coordinator).

## Discipline highlights

- **Copy, never paraphrase:** C1's literals from intention
  §6A.4:718-720/§8A.2:1367-1369; envelope keys from the serializers; the
  ITEM_MONEY_MOVED message from §6.4; identities' leading tokens; the
  twelve values from `enums.py:15-27` with §11A.4's ORDER (P16 — the
  declaration order is WRONG for publication).
- **Hand-written expected sets** for every accuracy arbiter (C4's 23
  rows; the handoffs' route/key/identity sets) — never derived from the
  surface audited (§9 hand-written-literal rule).
- **Mutations:** P3's three (line-pinned, expected-red ids first, mutant
  + restored hashes, per-site red only); regression = the phase-8/8B
  suites stay green; zero deferrals (the cap binds trivially here).
- The eleven annotations are ANNOTATION-ONLY — if any produces a runtime
  or ruff change beyond the annotation, stop and report.
- Every doc edit is enumerated in P5/P9/P11/P12/P13/P15/P18/P19 by line
  range — an edit outside those enumerations is out of fence (the drift
  you find but weren't assigned gets FILED in your handoff, not fixed).

## Closing protocol

1. All criteria green (C1 automatable per P2; C2/C3/C4 reviewer-verified
   content with your self-check recorded; the P3 mutation ledger).
2. Suite: expect 2184+N / 23 byte-identical (sorted diff, say so) / 1
   deselected — numbers READ off YOUR foreground run; ruff on touched
   Python files; DB at head `c1d2e3f4a5b6`; graph = your ONE P14 delta
   (state revision/counts).
3. Tracker → `IMPLEMENTED`; Review log per P-L (incl. the P10 WONTFIX
   and the P22 closure-checklist items you can already tick); FINAL
   sha256 for EVERY file touched — including every .md.
4. Checkpoint `CHECKPOINT (not approved): item-cost phase 9 implement r1
   — <summary>`; handoff AFTER (never inside), citing final hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-15_phase9_implement_r1_handoff.md`
   (full path). `⚠ OWNER DECISIONS REQUIRED (n)` if any arise; full
   write perimeter (backend + frontend + Application_contracts,
   separately listed) + probe declaration; every delegation stated
   (P14's node type; anything P-numbered you interpreted).
