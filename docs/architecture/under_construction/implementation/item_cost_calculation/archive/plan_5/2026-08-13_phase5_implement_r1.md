---
plan: phase 5 (valuation surface)
role: implementer
round: 1
date: 2026-08-13
---

# Session prompt — implement phase 5 (valuation surface)

You are the **implementing agent** for phase 5. Gate: 4B APPROVED (`377d0b9`);
the projection ledger is fully routed and owner cards R13-1/R13-2 are folded.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## The plan — read BOTH layers as one document

`docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_5_valuation_surface.md`:
the base plan (tasks 1–5, C1–C6, Notes/forward items) and the
**"Round-0 projection amendments" block — GOVERNING wherever they conflict**
(L1 selection resolver; L2 item-status resolver + both structural probes; L3
the `preview` envelope key with R13-1 numerics; L4 C5 as the 12-value
enumeration; L5 option (a); L6 DELETE returns the status-only preview; L7 the
leading-token exception; L8 corrected files list; L9 audit criterion; L10 C3
request-layer only; L11 the named race harness + BOTH race paths; L12 the
persisted-rate criterion with its computed fixture; L13 history pins; L15 the
snapshot-reader structural row; L16 three currency rows; the Notes and granted
delegations).

Also read: intention §4.7A, §7.5, §7A.1–7A.2, §7C, §11, **§11A.4–§11A.5 as
amended (R13-1 lettered clauses)**, §6A.9, R-9; master plan §6 (registry as
amended 2026-08-13 — `resolve_economics_selection` / `EconomicsSelection` /
`ITEM_READINESS_PRECEDENCE` / `resolve_item_economics_status` in §6.5, the two
audit names in §6.4, the response envelope); §9 P-A…P-Z ALL bind; §10.

## Environment facts (verified at prompt time)

- Head `5caae620088c`; dev DB at head; economics tables at ZERO rows.
- Suite baseline: **1927 passed / 23 known failures (byte-identical phase-1
  list) / 1 deselected**; collection 1951. No disposable DB needed this phase
  (no migration, no DDL) — every criterion is request/service-layer on the
  configured DB; only C2's races commit (teardown per L11).
- Live data: 471 items — 53 NULL category / 225 wood / 193 seat (L17).

## Discipline highlights (the bars phases 4/4B were held to)

- Every criterion row ships WITH its named mutation: run, **full observed red
  set** recorded (flag any divergence from the plan's prediction — P-I fifth
  ext), reverted, sha256 pair per row against REAL paths. **Copy-paste hashes
  and paths — never retype** (three transcription defects in three cycles).
- Parametrize ids name the authority row they discharge (P-V ext).
- All waits bounded (P-T ext); rule 11½ with the residue-check SCOPE stated
  (the five L11 tables).
- No disjunctions in message assertions (P-O); identities as exact leading
  tokens + class (§6.4; L7's carve-out is the ONE non-pydantic raise).
- The items domain is untouched; no new routes beyond §6.5's three; workers
  never see money (phase-1 redaction stands).

## Scope fence

Production: `domain/item_economics/configuration.py` (L1/L2 — additive rework;
`resolve_economics_configuration`'s behavior is settled by 4B's suite and must
stay green), `serializers.py`, `services/commands/item_economics/
set_item_valuation.py` + `delete_item_valuation.py` (new), `requests/__init__.py`,
`_common.py` (one INDEX_IDENTITIES entry), `services/queries/item_economics/
get_item_valuation_history.py` (new), `routers/api_v1/item_economics.py` (three
routes), `routers/README.md` mirror rows. Tests: new phase-5 files under the
item-economics test dirs + the L20 router-harness rename + the forward-items
touches (base-plan Notes block). Docs: master plan tracker row + plan Review
log + your handoff. **Nothing else** — if a correction seems to need another
file, stop and report.

## Archgraph

Orient read-only (`archgraph_status`; the item-economics domain/table/endpoint
nodes — all human_confirmed, revision `88e185f7…`, 0 pending). Delta at end:
ONE batched additive `apply_changes` — the two commands, the history query
endpoint(s), their accepts/writes_to/reads_from edges, accurate per-edge
evidence spans (the phase-4 lesson: write-site anchors live in the command
files, never a blanket router span). Never adjudicate anything.

## Closing protocol

1. All rows green; mutation ledger per-row (observed ids + sha256 pairs, real
   paths, divergences flagged).
2. Full suite: expect 1927+N / 23 byte-identical / 1 deselected; the
   committing race subset run TWICE with flat scoped row counts (name the five
   tables); ruff on changed files; DB at head.
3. Tracker → `IMPLEMENTED`; plan Review log per P-L (items, never counts).
4. Checkpoint `CHECKPOINT (not approved): item-cost phase 5 implement r1 —
   <summary>`; deposit the handoff AFTER, citing the FINAL hash, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-13_phase5_implement_r1_handoff.md`
   (full path). `⚠ OWNER DECISIONS REQUIRED (n)`; full write perimeter +
   probe declaration; state the L23 delegation choices you made.
