# Phase 9 — Living docs & drift routing

```
plan: phase 9
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Write the domain's living-docs page and land the documentation-drift fixes routed by
the intention (§2.6) and the gate handoff (D-1…D-4). **NOT in this phase:** any code
or schema change; the dead-code cleanup candidates (§2.6 item 5 — recorded
out-of-scope); the archgraph D-3 anchor repair (human-authorized maintenance
channel, master plan §8). This phase is deliberately thin — **refine at prompt
time** (planner doctrine): the coordinator finalizes the exact wording tasks from
what phases 1–8 actually shipped.

## Read first

1. `master_plan.md` §§2, 6.5, 7, 9 (P-A…P-D), 11.
2. Intention §2.6 (drift list), §8.1/§8A.2 (two-cost divergence statement — rule 5),
   §6A.4 + R4-2 (presentation rule + 25→20 guidance), §11A.4 (vocabulary), §13,
   §10.2 breakage list (docs entries); gate handoff D-1…D-4.
3. Contracts: `23_documentation`, `29_feature_workflow` (+ core).

## Dependencies

Phase 8 APPROVED.

## Files expected to change

- `docs/domains/item_economics.md` (new — the living-docs page; if `docs/domains/`
  does not exist yet, create it per `23_documentation`'s placement rules and record
  the decision in the Review log)
- `app/beyo_manager/models/tables/items/README.md` (§2.6-1 `STALL`→`STALLED`;
  §2.6-2 remove the dropped `item_issues` columns section; plus the phase-6 column
  removal reflected)
- `app/beyo_manager/models/tables/tasks/README.md` (§2.6-3 stale
  `task_history_record.py` / `latest_history_record_id` references; plus a D-4 line:
  step transitions are not guarded on task terminality and terminal commands leave
  open step records open — with the §8A.5 re-emit as the consequence-handler)
- `routers/README.md` (verify every phase's OpenAPI mirror rows landed; fix gaps)
- `/Users/davidloorenz/Desktop/Developer/Application_contracts/planning/task/task_step_models.md`
  (§2.6-4: the step time/cost aggregates gap) and
  `/planning/item/item_models.md` §"Value and cost semantics" (§10.2 breakage list)
  — **separate working directory**; the coordinator confirms it is in the session's
  scope before compiling the prompt, or reroutes these two as an explicit
  maintenance item.

## Implementation tasks (ordered)

1. Living-docs page with pinned content: the §1 economic contract chain; the
   **two-cost-numbers side-by-side definitions with the divergence and its reason**
   (§8A.2 rule 5 — `total_cost_minor` = salary-priced working+paused;
   `consumed_cost_minor` = allowance-priced working-only); the **R4-2 presentation
   rule** (percentage terms are planning allocations; never presented as legally
   payable tax; VMB out of scope; the 25→20 gross-base example) — master plan P-D;
   the §11A.4 status vocabulary; snapshot/replay semantics (HC-1/HC-7, §8A.4);
   unvalued-is-never-zero (R-9); worker-minutes vocabulary (P-C); the §10A.3 bridge
   and its planned one-release lifetime (master plan §7 note).
2. README drift fixes per the file list above.
3. Application_contracts gap entries (or the rerouted maintenance item — coordinator
   decision recorded here).
4. Confirm the master plan's follow-up ledger still records: bridge-validator
   removal (release after frontend stops sending keys); D-3 anchor repair
   (maintenance channel); §2.6-5 dead-code list (out of scope).

## Acceptance criteria

Documentation deliverables; where a criterion is not automatable it is
reviewer-verified content (recorded — this is a deliberate, justified exception to
charter rule 1's test-backed norm, which targets code behavior).

**C1 (automated proxy):** a test asserting `docs/domains/item_economics.md` exists
and contains the pinned phrases: "planning allocation", the never-legally-payable-tax
sentence, "worker-minutes", and both cost-number definitions (string containment —
cheap drift alarm, not a substitute for review).

**C2 (reviewer-verified):** the living-docs page states both cost definitions side
by side with the R-5 reason; the presentation rule appears verbatim in spirit; no
sentence presents a percentage term as computing tax; "minutes per worker" appears
nowhere (P-C).

**C3 (reviewer-verified):** the three README fixes match the code as shipped
(STALLED; no dropped-column docs; no `task_history_record` references; D-4 line
present and accurate against `transition_step_state`'s actual guard).

**C4 (reviewer-verified):** `routers/README.md` mirrors every route the registry
§6.5 shipped; Application_contracts entries landed or the reroute decision is
recorded in the Review log.

## Notes

- Evidence documents (`research_context.md`, `raw_intention.md`) are records — never
  edited (charter artifact map); drift found in them was routed, not patched.
- Projection gate: **waived by plan** (no S1/S2 mechanism; documentation only) —
  the waiver justification the charter requires is this line; the coordinator may
  still order a projection if phase-8 lessons suggest it.
- Archgraph: expected delta ≈ zero (docs); state it explicitly at close.
- **Phase-1 review r1 additions to the drift batch (2026-08-12):**
  (N1) `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`
  publishes `total_cost_minor` as always-present on a worker-app endpoint — false
  since phase 1; correct it here and note it for the frontend team alongside the
  `LastActiveStepCard.tsx` smoke note.
  (N2) the ADMIN/MANAGER-only step-money audience is a real architectural policy no
  archgraph node carries — candidate node/description in this phase's graph delta.
- **Phase-2/3 additions to the drift batch (2026-08-12):** phase-2 review N4
  (`checkfirst=True` on the five new enum types), N5 (prefix-map row ordering),
  re-review N8 (downgrade proxy misses raw-SQL `DROP TYPE`), r3 N14 (order-dependent
  Shopify assertion — flaky under load, threatens byte-identical baseline gates);
  phase-3 projection S7 (**eleven `Mapped[float]` annotations on `Numeric` columns**
  in the item_economics models → `Mapped[Decimal]`/`| None` per
  `user_work_profile.py:33` precedent — annotation-only, no runtime change).

- **Forward note (phase-6 projection r0, D22):** the frontend doc mirrors
  carrying the legacy money keys
  (`frontend/docs/architecture/backend/routers_endpoints/README.md:1918-1920,
  1976-1978, 2078-2080, 2475-2477`;
  `frontend/docs/architecture/backend/tables/README.md:437,467,469` — :469
  also mirrors the `create_type=True` flag phase 6 flips) are OUTSIDE phase
  6's perimeter by decision, not oversight — this drift batch owns them.

- **Forward notes (phase-6 reviews):** (r1 N9) deploy ordering for the column
  drop is unstated — an old ORM selecting the dropped columns during a rolling
  deploy errors; document the required order (deploy code first, migrate
  second) in the living-docs page. (r2 N1) the drop migration's docstring
  still reads `Revises: 5caae620088c` while `down_revision = "5420acc6a7b3"`
  — one-line correction + the fix-r1 record correction is already in the r2
  Review log entry.

- **Forward note (phase-8 projection r0, L17 — deferred 4B N3):**
  `get_economics_configuration_status.py:39,:49` carry a redundant
  `and not version.is_deleted` (the loader already filters deleted rows) —
  two sufficient causes, verified not-a-gap; simplify or keep KNOWINGLY with
  a comment. Phase 8 took only N4 (the `status is EconomicsStatusEnum.OK`
  swap) with a declared one-file extension; the N3 clause is this phase's.

- **Forward notes (phase-8 re-review r3, routed at approval):**
  (N1) the three C1 filter-deletion mutations' bite is order-CONTINGENT
  (62/62 empirically, but the alternate heap order was observed on clean
  trees in r2) — this phase, as the first to touch the status queries, adds
  the STRUCTURAL arbiter: assert each of the three services' compiled
  evaluation `SELECT` carries the three literal filter clauses
  (`kind='committed'`, `superseded_at IS NULL`, `is_deleted = false`),
  which no heap order affects (§9 structural-filter rule). (N2) the C5
  supersession row never closes its task, so "after close" is untested and
  2 of 10 compared columns are vacuous — resolve the task before the
  second handler run, or rename the row (§9 scenario-fixture rule). (N4)
  `test_phase8_serializers.py` carries a stray re-indented `)` and a
  dropped blank line from the fix-r2 row deletion — cosmetic, ruff-silent,
  fold into this phase's formatting sweep.

## Scope addition (round 18, R18-2, 2026-08-15) — GOVERNING

**Frontend handoff deliverable (owner request, verbatim in
`planning/owner_decisions.md`):** this phase authors
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_<date>.md`
covering, for the frontend team to build the capability from the handoff
alone:

1. **The ten new routes** (valuation set/history/delete ×3; evaluations
   commit/list/projections/delete/promote ×5; budget-status; lifetime) —
   method, path, role gate, request body, response envelope (verbatim
   keys), pagination where present, and the error identities each can
   return (leading-token contract, §6.4).
2. **The phase-8B inline flow** (this phase is BLOCKED on 8B): the
   task-creation item block's valuation trio, the one-call
   born-with-prices path, the existing-item refusal.
3. **The changed existing endpoints — prominently the REMOVALS:** item and
   task payloads REJECT the legacy money keys (422 `ITEM_MONEY_MOVED`,
   exact message); the nine read surfaces that no longer carry the three
   keys (phase-6 census); worker/seller payloads carry NO monetary keys
   anywhere (the budget-status role split); the twelve-member status
   vocabulary verbatim with the null-numerics rule.
4. **Flow narratives** (frontend-facing): pricing an item, committing a
   budget, what-if projections + promotion, the team task-flow history
   entry, the budget screen from READY (R17-1's boundary label).

**8B-routed handoff sentences (projection L14/L15/L18, 2026-08-15):** the
`PUT /api/v1/tasks` body table's PRE-EXISTING drift (missing
item_zone/can_have_upholstery/notes/steps/shopify_preorder rows; six
phantom `item_issues[]` fields; NO generator exists in-tree despite the
"autogenerated" banner — hand edits only); `quantity` does NOT participate
in economics (a valuation is per-item — 1000 stays 1000 at quantity 5);
the create-task response carries no priced-or-not signal — document the
two-call flow (create, then `GET /tasks/<id>/budget-status`).

**Accuracy arbiter:** same harness as the living-docs page — every route,
key, identity, and enum member in the handoff greps to the shipped
artifact; the projection hardens this criterion.

**Dependency change: phase 9 is BLOCKED on phase 8B** (the handoff and the
living-docs page document the post-8B flow).

## Review log

(append-only)

## Amendments (projection r0, 2026-08-15) — GOVERNING

Where this block contradicts anything above, THIS BLOCK WINS. Routed from
`handoffs/reviewer/2026-08-15_phase9_projection_r0_handoff.md` (5 B / 15 S /
8 L + the 32-row forward-note census; owner card 1 → **R19-1: TWO handoff
documents covering all twenty-three endpoints**).

### P1 (B1/F1) — the living-docs deliverable is a FOLDER

`docs/domains/item_economics/` with `README.md`, `api.md`, `events.md`
(required — the domain emits `item_economics:evaluation-committed`),
`states.md` (the twelve-status vocabulary + the evaluation chain), PLUS the
contract-mandatory domain-map row in `docs/README.md` (own task). Master
plan §6.5 corrected. Task 1's pinned content distributes: contract chain /
two-cost definitions / presentation rule / R-9 / worker-minutes →
`README.md`; payload catalogs (incl. phase-5 N5's valuation payload field
list and the §11A.2 eight-endpoint census — gate D-1's five call sites are
SUPERSEDED by the census, publish the census) → `api.md`; the event's shape
and after-commit semantics → `events.md`; vocabulary + chain + item_binding
→ `states.md`. Discipline: domain docs never reference migrations or
history — the §10A.3 bridge's one-release lifetime and the deploy-ordering
hazard do NOT go here (see P19).

### P2 (B2/F2) — C1 rewritten (automatable)

One test file `app/tests/unit/docs/test_item_economics_docs.py` (unit, no
marker needed beyond default), anchored
`Path(__file__).resolve().parents[N] / "docs" / "domains" /
"item_economics"` (NEVER cwd-relative — commands run from `backend/app/`,
docs live at `backend/docs/`; no repo test reads a .md today, this is the
first). Asserts: the four files exist; string containment of VERBATIM
literals quoted in the plan from intention §6A.4:718-720 (the
never-legally-payable-tax sentence) and §8A.2:1367-1369 (both cost-number
definitions), plus "planning allocation" and "worker-minutes". The
implementer copies the exact sentences into the test from the intention —
copy-paste, never paraphrase.

### P3 (B3/F3 + S10/F14) — the structural filter arbiter, fully pinned

THREE sites (r3-N1's stated boundary — a RECORDED decision):
`get_task_budget_status.py:106-108`, `get_task_budget_status_worker.py:30-32`,
`get_item_lifetime_economics.py:46-48` (`scalars`, not `scalar`).
Mechanism: the fake-session capture precedent
(`test_list_upholstery_inventories.py:34-46,63-64`) —
`str(query.compile(compile_kwargs={"literal_binds": True})).lower()`; the
fake implements `scalar`/`scalars` (the methods actually called); select
the captured statement whose text names `item_cost_evaluations`, NEVER by
call ordinal (fixture-dependent: 3rd or 4th call). Three deletion mutations,
line-pinned (P-I 10th): delete `:107` / `:31` / `:47` → each reddens its
own site's row only; expected-red node ids stated in the ledger BEFORE the
runs. `list_task_evaluations.py:50-51` carries TWO clauses BY DESIGN
(returns the whole chain — phase-7 D15) and is NOT a site; the FOUR other
production sites are recorded in §11's only-if-cheap ledger (F14), not
here.

### P4 (B4/F4) — the Goal fence replaced by the enumerated allow-list

Code changes in this phase are EXACTLY: (1) P3's structural rows (test);
(2) r3-N2's C5 fixture with the CORRECTED repair (P8); (3) r3-N4's TWO-LINE
hand edit (P17); (4) 4B N3: drop the redundant `and not version.is_deleted`
at `get_economics_configuration_status.py:39` and `:49` (production, two
clauses); (5) the drop-migration DOCSTRING line (P10's rule-7 exemption);
(6) phase-2 N8: the downgrade-proxy regex gains raw-SQL `DROP TYPE`
matching (test); (7) phase-2 N14 TAKEN: `test_process_shopify_products_
integration.py:179` list→set comparison (ONE line, non-domain — taken
because the flake threatens the byte-identical baseline gate; the filed
:176 was the wrong line); (8) phase-3 S7: the ELEVEN `Mapped[float]` →
`Mapped[Decimal]`/`| None` annotations (production, annotation-only:
`production_cost_basis_version.py:24,25,26`;
`item_cost_evaluation.py:33,34,36,38`; `item_cost_evaluation_term.py:22`;
`cost_model_term.py:22`; `item_cost_result.py:23,25`; precedent
`user_work_profile.py:33-34`); (9) the money-audience graph node (P14).
NOTHING else — no schema change, no migration operation, no behavior
change; the phase-8/8B suites are the regression net.

### P5 (B5/F5) — `models/tables/README.md` joins the Files list

Three edits: (a) the nine item_economics tables added to the 62-row index
(INDEX ROWS ONLY — full per-table sections are NOT required this phase,
recorded); (b) `:468-470`'s three dropped money columns removed; (c)
`:438`'s `create_type=False` claim corrected (ownership moved phase 6).
The `:24` `issue_category_configs` ghost is PRE-EXISTING and out of scope
(recorded, untouched).

### P6 (R19-1) — the TWO frontend handoffs

`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`:
the ten routes (method/path/role gate/request/response envelope VERBATIM
keys/pagination/error identities per route), the 8B inline flow (trio
shape, branch-B refusal, the six auto-commit outcomes), the REMOVALS
prominently (legacy keys → 422 ITEM_MONEY_MOVED exact message; the nine
read surfaces; worker payloads carry no money), the twelve-value vocabulary
(VALUES verbatim from the enum, ORDER = §11A.4 evaluation order — P16),
the flow narratives (price→commit→projections→promotion; the two-call
create→budget-status flow; quantity-is-per-item; the team task-flow entry;
the budget screen from READY with the boundary label).
`…_configuration_20260815.md`: the thirteen setup routes (cost-groups CRUD
+ sections, basis-versions, cost-model-versions, configuration-status),
request shapes incl. the category contract (one active group per major
category; immutable category), the dual-path conflict identities, term
types, and the setup narrative (what a manager does before any price
screen works). BOTH: the grep-accuracy arbiter (P15) with HAND-WRITTEN
expected sets. Also P18's fix to the OLD reassigned-steps handoff.

### P7 (S1/F6) — the C5 repair that actually works

Close the task (state=RESOLVED + closed_at) BEFORE the FIRST handler run —
both lifecycle columns then carry real closed values, "after close" is
genuinely reached, and the ten-column equality still holds (RESOLVED is
admitted). NOT between the runs (that reddens `:542`). Record: C5 compares
`task_state_snapshot`, one column MORE than §8A.4's set — deliberate,
stricter.

### P8 — (folded into P4 item 2; the fixture change is P7's.)

### P9 (S3/S4/S5 — the README batch, enumerated)

`items/README.md`: `:34` STALL→STALLED; `:29-31` money block REMOVED;
`:53-56` snapshot section REPLACED (not removed — the live columns are
`issue_type_snapshot`/`issue_mode_snapshot`/`placement_of_issue_snapshot`,
`item_issue.py:43-45`); `:61` timing paragraph deleted; `:110-111`
create_type/import-order claims corrected. `tasks/README.md`: SIX stale
sites (`:8,:24,:35,:42` + the whole `:146-150` section for the nonexistent
table) + the D-4 line as planned.

### P10 (S7/S8 — the two applied-migration items)

Phase-2 N4 (`checkfirst=True`): **WONTFIX** — undischargeable (applied
migration, rule 7; the types exist so the posture can never fire);
rationale in the Review log; the posture recorded as squash-seed Finding 8.
Phase-6 r2 N1 (docstring): TAKEN with the rule-7 exemption STATED — the
edit changes prose only (`Revises:` line, `be9dfe42a035_…py:4`); Alembic
derives the chain from `down_revision`, never the docstring; no operation
changes.

### P11 (S6/F10) — the prefix map

Sort the NINE new rows into alphabetical place (`:41-43` the three
ItemCost* rows; `:52-56` the five ProductionCost*/CostModel* + StaticCost
context) — the FILE is not resorted; the pre-existing Shopify/SkuTemplate
violation (`:57-60`) is recorded and untouched.

### P12 (S13/F17) — the frontend mirrors, in the Files list with scope confirmed

`frontend/docs/architecture/backend/routers_endpoints/README.md:1918-1920,
1976-1978, 2078-2080, 2475-2477` (the four legacy-money route rows) and
`frontend/docs/architecture/backend/tables/README.md` — BOTH `:437` (the
create_type flip — D22 attributed it to the wrong line) AND `:467-469`
(the three dropped columns). SCOPE CONFIRMED: phase 9 owns these edits;
the implementer session's workspace must include the frontend repo — if it
does not, STOP AND REPORT rather than skip.

### P13 (S14/F18) — Application_contracts: phase 9 OWNS both edits

(decided — the directory is in the session's working set):
`task_step_models.md` gains the step time/cost aggregates
(`total_working_seconds` etc., §2.6-4); `item_models.md:104-107`'s "Value
and cost semantics" block rewritten for the valuation model (the legacy
fields are GONE; prices live on item_valuations; the §10A.3 bridge
rejects the old keys).

### P14 (S11/F15) — BUILD the money-audience node

One graph node (type `decision` or `infrastructure` — implementer's call,
declared): the ADMIN/MANAGER-only money audience — evidence at
`include_monetary_step_fields` (`domain/tasks/serializers.py:150-155`),
the §11A.3 separate-serializer rule, and the budget-status role split.
Recorded in the phase's ONE additive delta (this satisfies §13's literal
"archgraph delta in the same change"); promoted at the coordinator's
closeout pass. Phase-1 N2 thereby lands; the "delta ≈ zero" Notes line is
SUPERSEDED.

### P15 (S12/F16 + L6/F22) — C4's arbiter + the PUT-table repair

C4's arbiter: a HAND-WRITTEN 23-row literal set (path, method, role gate)
asserted against `routers/README.md:58-80`'s rows AND spot-grepped against
`require_roles` in the router (never derived from `router.routes` —
phase-8 L5). The PUT `/api/v1/tasks` body table REPAIRED per F16's
enumeration (missing: assortment, item.item_zone, item.can_have_upholstery,
the three RETAINED legacy money keys documented as "present, always
rejected with 422 ITEM_MONEY_MOVED", shopify_preorder, notes[].plain_text,
notes[].users_read_list, steps[].ready_by_at, steps[].reason; the five
phantom item_issues rows removed; the seven real _TaskItemIssueBody fields
documented). The `:3` "Autogenerated from FastAPI OpenAPI" banner REPLACED
with "Hand-maintained" (no generator exists — the lie is what lets it
rot).

### P16 (L1/F20) — vocabulary order rule

Everywhere the twelve members are published: VALUES verbatim from
`enums.py:15-27`; ORDER = §11A.4's evaluation order (group 1
`infeasible`/`ok` first is WRONG — the readiness precedence
`item_missing_major_category` → … → `not_evaluated` with the evaluated
branch stated separately, exactly as §11A.4/§7C.3 define). The criterion
names which order is published.

### P17 (L3/F21) — the formatting item

TWO-LINE hand edit in `test_phase8_serializers.py` (`:14` the over-indented
`)`; the missing blank line before `_result()`). `ruff format` is
FORBIDDEN on this file (~90-line churn incl. the P-V parametrize ids).

### P18 (census row 1/F24) — the old frontend handoff correction

`HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md:166` (example
payload) and `:393` (field table): `total_cost_minor` is NOT
always-present — ADMIN/MANAGER only since phase 1. TIER RULE stated: files
directly under `docs/handoff/to_frontend/` are the LIVE contract and
editable; anything under `archived/` is frozen (never edited).

### P19 (F23) — the deploy-ordering line lands in `docs/deploy/`

(decided — `docs/runbooks/` does not exist; `docs/deploy/` does): the
column-drop rolling-deploy hazard with the revision named, deploy-code-
first-migrate-second. The domain doc states the generic ordering rule
WITHOUT naming a revision (docs discipline).

### P20 (S15/F19) — the two contract amendments (own task)

(a) `architecture/46_serialization_local.md`: replace the template with
the recorded standing divergence (router-owned serialization mandated;
the query layer does the opposite; phases keep serialization where the
code they modify has it — master plan §5's wording). (b) CREATE
`architecture/05_errors_local.md`: the no-`code`-field divergence
(`errors/base.py:3-10`) and §6.4's leading-token carrier decision. The
highest-leverage documentation in the batch — what future agents read
BEFORE writing code.

### P21 (census) — dispositions for the remaining rows

Row 5 (phase-2 N8): in P4's allow-list. Row 10 (phase-4 N10): NO-ACTION
recorded (conditional on flakiness never observed). Row 26 (gate D-1):
superseded by the §11A.2 census, published in api.md (P1). Row 27 (gate
D-3): RESOLVED (0 pending / 0 stale) — marked in task 4 with the caveat
that counts prove adjudication, not span accuracy. L4/L7/L8: recorded;
the implementer prompt carries the CURRENT env facts (baseline 2184/23/1
= 2207 selected; graph 174/260 rev `452befdb…`).

### P22 — v1 closure checklist (the closeout's own criteria)

(1) every §13 must-ship row discharged (the P14 node satisfies the
archgraph clause); (2) post-v1 handoffs recorded, not dropped: the squash
seed (Findings 1–8), the N11 residue research prompt, the bridge-validator
removal follow-up (§7:560-564), §11's F14 entry, the phase-7 ival residue
row; (3) all five formerly-UNROUTED census rows end in a task (rows 7, 8,
30 → P5, P4-8, P20) or a recorded disposition (rows 10, 11 → P21, P1);
(4) the projection gate's non-retirement recorded (moot — last phase).

## Review log

(append-only)

- **2026-08-15 — projection r0 (Claude Opus 5): AMENDMENTS_REQUIRED** —
  5 B / 15 S / 8 L, 1 owner card, plus the 32-row forward-note census
  (5 UNROUTED caught; 2 upstream notes factually wrong — the C5 repair
  as routed reddens the test, N14 named the wrong line; 1 undischargeable).
  Standouts: the living-docs deliverable violated its own cited contract
  (folder, not flat file); C1 had no harness and no repo precedent reads
  a .md; the scope fence contradicted eight routed code items; the
  backend tables index was never routed while its frontend MIRROR was.
  One verified correction executed in-session (the :39/:49 citation).
  Coordinator routed ALL rows 2026-08-15: owner card → **R19-1 (TWO
  handoffs, all 23 endpoints, split for the two-stage frontend build)**;
  §6.5 folder correction; §11 += F14's four uncovered filter sites;
  squash seed += Finding 8 (N4 WONTFIX posture); this GOVERNING block
  P1–P22. Gate CLEARED; implementer prompt
  `prompts/implementer/2026-08-15_phase9_implement_r1.md` (intended for a
  Claude-model implementer per the owner's choice — documentation-heavy).
