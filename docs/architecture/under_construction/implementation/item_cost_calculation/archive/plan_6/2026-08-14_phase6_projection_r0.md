---
plan: phase 6 (legacy migration & API bridge)
role: reviewer (projection)
round: 0 (pre-implementation projection gate)
date: 2026-08-14
---

# Session prompt — phase 6 projection, round 0

You are the **projectionist** for phase 6. The plan was written 2026-08-11,
BEFORE rounds 11–13 and phases 4/4B/5 shipped — find where it no longer
survives contact with the code and semantics as they exist NOW, and deposit an
amendment ledger. This phase is the project's most DESTRUCTIVE (a data
migration moving legacy item money into `item_valuations`, then dropping
columns) — the projection's bar rises accordingly.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

## Ground

- Plan under projection: `plans/phase_6_legacy_migration_api_bridge.md`
  (incl. its forward note — the r2-N2 `client_id DESC` tie-breaker criterion:
  bulk-created valuation rows CAN share a `created_at`; the reviewer-verified
  correction is in the note).
- Semantic authority: intention §10.2 ENTIRE (three-step ladder: journaled
  data migration → API bridge → column drop; pre-flight refusal of rows
  carrying an amount with NULL `item_currency` — currency is NEVER guessed),
  §10A.3 (`ITEM_MONEY_MOVED` bridge identity), §4.7A (INV-V1/V2), R1-3/R2-1
  (money leaves item CRUD entirely; `item_currency_enum` type ownership moves
  — the type survives for `item_upholstery_requirements`), R13-1/R13-2
  (§11A.5 lettered clauses), §7A.1 (the chain the migration's rows must
  respect).
- Registry: master plan §6 as amended through 2026-08-13; §9 P-A…P-Z + P-AA
  and every extension through the phase-5 rounds ALL bind (esp. P-Z scope
  exceptions carry before/after property tests; the §10 from-scratch history
  — this phase writes a data migration ON TOP of the env.py transaction
  regime the 4B review mapped; L5 state assertions, never exit codes).
- Shipped reality to project against: phase 5's valuation surface (the
  migration's target table has a live command surface now — INV-V1 races,
  audit events, serializers); 4B's category contract; the migration exemplars
  (`97b60e06d42a` journaled; `5caae620088c` report-first pre-flight with
  dependent counts).

## Environment facts (verified at prompt time)

- Head `5caae620088c`; suite baseline 1968/23/1 (collection 1991+1); dev DB
  at head; economics tables at ZERO rows (post-closeout purge).
- Live legacy data is THE subject here — measure it, don't trust prose:
  count items with non-NULL `item_value_minor` / `item_cost_minor` /
  `item_currency`; count the §10.2 refusal class (an amount present with
  NULL currency); state the numbers per workspace. The projection's pre-count
  becomes the migration criterion's expected arithmetic.
- Disposable-DB work is MANDATORY here (charter rule 7): the migration
  round-trip, the refusal path, and the journal shape all rehearse on
  disposables per §10's recipe.

## Projection axes (minimum — the ledger is yours)

1. **Rounds 11–13 drift:** every plan claim about the valuation table,
   endpoint, serializers, or status vocabulary against what actually shipped
   (R13-1 preview envelope; R13-2 history pins; the §6.5 registry as amended).
2. **The migration's interaction with INV-V1 and the §7A.1 chain:** migrated
   rows must land as valid current rows (one per item, both predicate
   clauses); what happens for items with BOTH legacy value and cost vs one;
   `created_at` bulk-timestamp behaviour (the tie-breaker criterion);
   audit/journal rows; whether migrated rows carry `created_by_id` and what
   §10.2 says about attribution.
3. **The API bridge:** grep the ACTUAL request schemas/serializers for the
   money fields today (`item_value_minor`, `item_cost_minor`,
   `item_currency` across `items` create/patch/find-or-create,
   `create_task`'s nested body, both item serializers) — the plan's file list
   was written three days and three phases ago; re-run every Dependencies
   grep (the N-f lesson) including payload KEYS across the test tree.
4. **The column drop's ladder position:** never a rewrite of an applied
   migration (rule 7); enum-type ownership movement verified at the MIGRATION
   site (the phase-2/4B lesson — model flags are inert); what
   `compare_metadata` can and cannot see here (P-X).
5. **Criteria quality under §9 as it stands:** P-V ids naming CURRENT
   authority numbering; P-W competing fixtures; P-Q implication pins checked
   against the implementation they meet; P-J structural rows quantifying over
   their sets with non-vacuity arbiters; P-AA for any transitive relation;
   the ledger rule (N named mutations = N rows).
6. **Rollback/downgrade semantics for a DATA migration:** what §10.2's
   journal makes reversible, what it explicitly does not, and what the
   criterion asserts about each (state queries, never exit codes — L5).

## Closing protocol

1. Deposit an amendment LEDGER (numbered rows, severity, the plan section
   amended, verified corrections — executed where cheap, never reasoned).
   `⚠ OWNER DECISIONS REQUIRED (n)` for anything semantic (story-shaped
   cards, branches + recommendation + on-silence).
2. No code, no plan edits, archgraph READ-ONLY (state revision `bd72c36d…`,
   154 nodes / 200 edges, 6 pending — zero delta).
3. Deposit at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase6_projection_r0_handoff.md`
   (full path, AFTER your writes): ledger; the live-data measurements; full
   write perimeter + probe declaration.
