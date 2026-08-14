---
plan: phase 6 (legacy money migration & API bridge)
role: implementer
round: 1
date: 2026-08-14
---

# Session prompt — implement phase 6 (legacy migration, API bridge, column drop)

You are the **implementing agent** for phase 6 — the project's one DESTRUCTIVE
phase (§10.2's three-rung ladder: journaled data migration → API bridge →
column drop). The projection did your first hour on paper; its 23 rows are
routed and GOVERNING.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## The plan — read BOTH layers as one document

`docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_6_legacy_migration_api_bridge.md`:
the base plan + its forward note + the **"Round-0 projection amendments"
block — GOVERNING wherever they conflict** (D1 carrier, D3 restatement, D4
nine-row census, D5 mutation pair, D6 router bodies RETAINED, D7/P3 owner
rules, D8–D13 pins and delegations, D14 synthetic tie fixture, D16 collapse,
D19 graph note, D22 scope, D23 ids).

Also read AS AMENDED (intention round 14): §10.2, **§10A.1 incl. lettered
clauses (a)–(c)**, **§10A.2 incl. P3**, **§10A.3 as corrected** (carrier
class, evidence correction, router-body retention); §4.7A; master plan §6.4
(the corrected ITEM_MONEY_MOVED row and P1/P2/P3 row), §6.1 (the journal
table), §9 P-A…P-Z + P-AA and ALL extensions, §10. Exemplars: `97b60e06d42a`
(journaled data migration) AND `5caae620088c` (report-first pre-flight,
`create_type=False` — previously uncited, closest precedent).

## Environment facts (verified at projection time, 2026-08-14)

- Head `5caae620088c`; suite baseline **1968/23/1** (collection 1991+1); dev
  DB at head; `item_valuations` at 0 rows.
- **Live census: 479 items, ALL legacy money columns 0 non-NULL, in all 61
  workspaces.** Every migration criterion is VACUOUS on the live DB —
  C1/C2/C3 run on seeded DISPOSABLE databases (§10 recipe, named per
  criterion) with non-vacuity rows proving the seeded eligible set is
  non-empty (P-J third ext). Zero test dependents exist for the three keys —
  a green suite proves nothing here; your mutations are the only arbiters.
- `item_currency_enum`: 2 column users today → exactly 1 after the drop
  (`item_upholstery_requirements.currency`; 204 rows, 0 non-NULL —
  dormancy re-verified).

## Discipline highlights

- **N named mutations = N ledger rows** (P-I sixth ext), full observed red
  sets, divergence from prediction flagged, per-row sha256 pairs COPY-PASTED,
  distinct hash per label (seventh ext).
- Every migration end-state asserted by STATE QUERIES, never exit codes (L5);
  refusal paths (P1/P2/P3) rehearsed on disposables — refusal leaves
  NOTHING persisted (D20's structural guarantee, still asserted).
- Charter rule 7: the configured DB is never the test bench for destructive
  work; every disposable dropped and listed.
- Parametrize ids name the authority row in its CURRENT numbering (D23).
- The items domain's non-money behavior is untouched; **the three keys are
  RETAINED in the four router body models** (D6 — deleting them there
  silently drops client money at the HTTP boundary).

## Scope fence

Production: the two migration files (data migration + column drop, on head at
implementation time — re-verify `alembic heads`); the four command request
schemas (validator added); the four router body files (keys retained — likely
zero diff, listed because D6 makes them load-bearing);
`domain/tasks/serializers.py` + `domain/items/serializers.py` (three keys
removed from both); `models/tables/items/item.py` (columns/type flag);
`app/beyo_manager/routers/README.md` mirror rows. Tests: new phase-6 files +
the D4 nine-row census file + the synthetic tie fixture (phase-5 history
test file gains it per D14). Docs: master plan tracker + plan Review log +
your handoff. **Frontend files: NONE** (D22 — phase 9 owns the doc mirrors).
If anything else seems needed, stop and report.

## Archgraph

Orient read-only (revision `bd72c36d…`, 154 nodes / 200 edges, 6 pending —
NOT yours to adjudicate; `node:table-item` is among them and its description
already anticipates this phase). Delta at end: ONE batched additive
`apply_changes` — the removal of the money surface is a semantic note on
existing nodes' evidence, plus any genuinely new architecture (the journal
table node); accurate spans; write-site evidence in the migration/command
files.

## Closing protocol

1. All criterion rows green (C1–C6 as amended); the full mutation ledger.
2. Suite: expect 1968±N / 23 byte-identical / 1 deselected (numbers READ off
   the run); any committing subset twice with residue scope named; ruff on
   changed files; configured DB at head (state the head — it moves to your
   drop migration's revision); all disposables dropped and listed.
3. Tracker → `IMPLEMENTED`; Review log per P-L; C6's manual disposable
   lifecycle evidence recorded in the Review log (state queries).
4. Checkpoint `CHECKPOINT (not approved): item-cost phase 6 implement r1 —
   <summary>`; handoff AFTER, citing the FINAL hash, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-14_phase6_implement_r1_handoff.md`
   (full path). `⚠ OWNER DECISIONS REQUIRED (n)`; full write perimeter +
   probe declaration; state every delegation choice (D8, D12) you exercised.
