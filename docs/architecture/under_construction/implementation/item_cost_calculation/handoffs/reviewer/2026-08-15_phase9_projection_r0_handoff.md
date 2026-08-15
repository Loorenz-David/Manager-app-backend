---
plan: phase 9 (living docs & drift routing — the LAST phase of v1)
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
state: OWNER_DECISIONS_PENDING
date: 2026-08-15
actor: reviewer / projectionist (Claude Opus 5)
---

# Phase 9 projection, round 0 — decision ledger

## Opening (owner-readable)

The last phase's plan is not yet buildable as written, but nothing is wrong with
the software — every problem is in the paperwork that tells the builder what to
write. The biggest one: the plan says to write a single page of documentation,
while this repository's own documentation rulebook says a new area of the system
gets a small folder of pages and a link added to the main index. There are also
several pieces of clean-up that were promised to this final phase over the last
eight phases and then never made it onto the plan's own list — most notably a
table index inside the backend that still describes three item price columns that
were deleted weeks ago. I found one thing that genuinely needs you: the frontend
handoff you asked for covers ten endpoints, but the team also needs the thirteen
setup endpoints (creating cost groups, cost bases, cost models) or they cannot
build the manager's configuration screen from the handoff alone. Everything else
is a wording fix the coordinator can route without you.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Should the frontend handoff also cover the thirteen setup endpoints?

**Question:** Does the frontend handoff document only the ten endpoints you
listed, or all twenty-three the project shipped?

**Story:** A frontend developer opens the handoff to build the new screens. They
can build the price form, the budget screen, the what-if projections — all ten
endpoints are there. Then they reach the first screen a manager actually has to
use, before any of that works: the settings page where you create a cost group
for wood, type in the monthly workshop cost and the paid hours, and add the
percentage terms. Nothing in the handoff describes those endpoints. The developer
either stops and asks, or guesses the request shapes and gets 422s for a day.
Meanwhile every price screen they did build shows "no cost group set up" for
every item, because the setup was never done.

**Branches:**
- **Ten endpoints only** — the handoff ships smaller and sooner; the configuration
  screen needs a second handoff round before a manager can use anything.
- **All twenty-three** — one document, the whole capability buildable from it;
  roughly half again as much writing in this phase.

**Recommendation:** all twenty-three. The ten endpoints are unusable until the
thirteen setup ones have been called once, so a handoff without them cannot meet
your own stated goal of building the capability from the handoff alone.

**On silence:** the gate holds. The implementer prompt is not compiled until this
is answered; nothing is guessed.

**Trace:** intention R18-2; `plans/phase_9_docs_and_drift.md` "Scope addition"
item 1; master plan §6.5 router block (23 routes shipped, verified in
`routers/api_v1/item_economics.py`).

---

## Decision ledger

Severity: **B** = blocking (implementer prompt cannot compile), **S** = should-fix,
**L** = low / recorded. "Verified" means I checked the artifact in the tree this
session.

| # | Sev | Decision point | Classification | Proposed routing |
|---|---|---|---|---|
| B1 | B | The living-docs deliverable is pinned as a flat file `docs/domains/item_economics.md`; the cited contract mandates a per-domain **folder** plus a `docs/README.md` row | plan gap + skeleton gap | amend master plan §6.5:538 and plan task 1 / Files list / C1 / C2 (detail F1) |
| B2 | B | C1 names no verbatim strings, no test path, no harness; no test in the repo reads a `.md` file | plan gap (charter rule 2, P-R) | rewrite C1 with pinned literals + harness (detail F2) |
| B3 | B | r3-N1 (the phase's one weighty code item) names neither the three files, nor the inspection mechanism, nor a per-site expected-red node id | plan gap (§9 structural-filter + expected-red rules) | rewrite the r3-N1 note into a task + criterion (detail F3) |
| B4 | B | The Goal fences out "any code or schema change" while at least eight routed items ARE code | plan gap (self-contradiction) | replace the fence with the enumerated allow-list (detail F4) |
| B5 | B | `app/beyo_manager/models/tables/README.md` is absent from the Files list and carries three live drifts | census hole | add to Files list; three enumerated edits (detail F5) |
| S1 | S | The routed C5 repair ("resolve the task before the second handler run") makes the test **red** | upstream note is wrong | correct the repair: close the task before the FIRST run (detail F6) |
| S2 | S | 4B N3's citations are stale — the redundant clause is at `:39` and `:49`, not `:38`/`:47` | reality check | correct the plan note; **executed below** |
| S3 | S | `items/README.md` drift is wider than §2.6 records (two further sites, both created by phase 6) | census hole | extend the plan's items-README task (detail F7) |
| S4 | S | §2.6-2 says "remove" a section documenting three columns that **do** exist under different names | decidability | instruction is *replace*, not remove (detail F8) |
| S5 | S | §2.6-3 names `tasks/README.md:8,42`; six sites are stale | reality check | enumerate all six (detail F9) |
| S6 | S | N5's prefix-map scope undercounts (nine rows, not five) and the file already violates alphabetical order elsewhere | decidability | name the target ordering explicitly (detail F10) |
| S7 | S | Phase-2 N4 (`checkfirst=True`) is undischargeable — the only fix edits an applied migration | upstream routing | close as WONTFIX with rationale, or move to the squash seed (detail F11) |
| S8 | S | The phase-6 r2 N1 docstring fix also edits an applied migration; rule 7's scope is unstated | decidability | state the docstring exemption in the plan (detail F12) |
| S9 | S | N14 is live but at `:179`, not the filed `:176`, and on a different assertion | reality check | correct the note; decide take-or-reroute (detail F13) |
| S10 | S | The same three-clause filter lives at **four more** production sites than the three r3-N1 covers | scope fence | extend or record the boundary (detail F14) |
| S11 | S | Plan Notes say "archgraph delta ≈ zero"; phase-1 N2 routes a **new node** here | plan self-contradiction | decide build-or-reroute (detail F15) |
| S12 | S | C4 (`routers/README.md`) has no arbiter and the file's PUT `/api/v1/tasks` table is materially wrong | plan gap + census | give C4 an arbiter; enumerate the row set (detail F16) |
| S13 | S | The frontend doc mirrors (D22) are in Notes but not in the Files list, and D22 undercounts by one row | census hole + scope | add to Files list; confirm write scope (detail F17) |
| S14 | S | The Application_contracts scope decision is still open — the plan defers it to the coordinator | open decision | decide before the prompt compiles (detail F18) |
| S15 | S | `46_serialization_local.md` and the `05_errors` gap are routed here by master plan §5 and appear nowhere in the plan | census hole | add as a task (detail F19) |
| L1 | L | The enum's declaration order ≠ the published evaluation order | accuracy trap | criterion names which order is published (detail F20) |
| L2 | L | D-3 discharged: 0 pending / 0 stale — but counts prove adjudication, not span accuracy | reality check | mark resolved in the plan, with that caveat |
| L3 | L | N4's "formatting sweep" must be a two-line hand edit; `ruff format` rewrites ~90 lines | decidability | pin the exact edit; forbid a blanket format (detail F21) |
| L4 | L | Phase-4 r3 N10 is conditional ("only if flakiness appears") | census row | record as no-action, do not silently drop |
| L5 | L | Phase-4 projection S5 made C4 the OpenAPI backstop; C4 has no arbiter (see S12) | cross-reference | fold into S12's fix |
| L6 | L | The ten routes' role gates have a greppable arbiter | supports the accuracy harness | cite in the handoff criterion (detail F22) |
| L7 | L | Plan Read-first cites the 2138/23/1 baseline; §10 now records 2184/23/1 | stale citation | refresh at prompt time |
| L8 | L | Plan Ground and the projection prompt's closing protocol both cite graph `45b72196…` / 173-256 | stale citation | live state is 174/260, `452befdb…` (verified) |

---

## Findings in detail

### F1 (B1) — the living-docs page is specified in a shape the cited contract forbids

The plan's Read-first list names `23_documentation`. That contract says:

- `architecture/23_documentation.md:36-41` — `docs/domains/<domain>/` is a
  **folder** containing `README.md`, `api.md`, `events.md`, `states.md`.
- `architecture/23_documentation.md:410` (maintenance discipline, mandatory row) —
  "**New domain created** → Create full `domains/<domain>/` folder with all 3–4
  files, **add row to `docs/README.md`**".

The repo's applied form agrees: `docs/README.md`'s "Where to go" table routes
readers to `docs/domains/<domain>/`, its domain map links
`[domains/worker_shifts/](domains/worker_shifts/)`, and the only in-tree
precedent is a folder — `docs/domains/worker_shifts/{README.md, api.md,
states.md}` (verified).

Against that, three artifacts pin a flat file: master plan §6.5:538
(`docs/domains/item_economics.md (phase 9)`), the plan's Files-expected-to-change
list, and C1's assertion target. An implementer following the plan ships a
contract violation; one following the contract fails C1.

Three consequences the plan does not currently carry:

1. **`docs/README.md` gains a domain-map row** — contract-mandatory, and without
   it the new page is unreachable from the single documented entry point. The map
   currently lists Item economics nowhere (its "Items" row reads *not yet
   documented*).
2. **`events.md` is required, not optional** — this domain emits
   `item_economics:evaluation-committed` (master plan §6.5; graph node
   `event-item-economics-evaluation-committed`, verified `human_confirmed`).
3. **`states.md` is "if applicable"** and it is: the twelve-member ordered status
   vocabulary and the committed/superseded evaluation chain are exactly what the
   contract's states template exists for.

The plan's own hedge — "if `docs/domains/` does not exist yet, create it … and
record the decision" — is moot: `docs/domains/` **exists**. The open question is
file-vs-folder, and the contract answers it.

**Routing:** amend master plan §6.5:538 to the folder; rewrite plan task 1 to
distribute the pinned content across `README.md` / `api.md` / `events.md` /
`states.md`; add the `docs/README.md` row as its own task; re-target C1 and C2.

**Note for whoever writes task 1:** `docs/README.md`'s documentation-discipline
section says domain docs "must **not** reference implementation plans, summaries,
**migrations**, or the history of how something came to be." Two pinned content
items collide with that — the §10A.3 bridge's one-release lifetime, and the
phase-6 N9 deploy-ordering hazard (a column-drop concern). See F23.

### F2 (B1/B2) — C1 is not decidable and its harness does not exist

C1 as written: "a test asserting `docs/domains/item_economics.md` exists and
contains the pinned phrases: 'planning allocation', the
never-legally-payable-tax sentence, 'worker-minutes', and both cost-number
definitions (string containment)".

Four gaps, each of which the implementer would have to close by inventing:

1. **Two of the four "pinned phrases" are not literals.** "the
   never-legally-payable-tax sentence" and "both cost-number definitions" are
   descriptions. Charter rule 2 wants one exact expected outcome per case. The
   source strings exist and should be quoted into the criterion: intention
   §6A.4:718-720 for the presentation rule, §8A.2:1367-1369 for the two
   definitions.
2. **No test path, no marker.** Nothing says where the test lives or whether it
   is `unit` or `integration`.
3. **No harness, and no precedent to copy.** I grepped the whole test tree:
   **zero** tests read a `.md` file from disk. This is a new pattern, and its
   path resolution is non-obvious — commands run from `backend/app/` (master plan
   §10) while the docs live at `backend/docs/`. The criterion needs the anchor
   spelled out (`Path(__file__).resolve().parents[N] / "docs" / "domains" / …`)
   because a cwd-relative path silently passes or fails depending on where pytest
   was invoked.
4. **B1 changes the target.** If the page becomes a folder, C1 asserts over the
   folder's files — the criterion cannot be written before B1 is settled.

**Routing:** rewrite C1 after B1, with verbatim literals, a named test file, a
marker, and the `parents[N]` anchor. Charter rule 1's exemption already covers
the reviewer-verified criteria; C1 is the automated proxy and must actually be
automatable.

### F3 (B3) — the structural filter arbiter: everything the implementer needs is missing

The plan's r3-N1 note says "assert each of the three services' compiled
evaluation `SELECT` carries the three literal filter clauses". It names no file,
no mechanism, and no expected-red test node. Here is what I verified, so the plan
can pin it:

**The three sites** (each carries all three clauses):

| Service | Lines | Session method |
|---|---|---|
| `services/queries/item_economics/get_task_budget_status.py` | `:106-108` | `session.scalar` |
| `services/queries/item_economics/get_task_budget_status_worker.py` | `:30-32` | `session.scalar` |
| `services/queries/item_economics/get_item_lifetime_economics.py` | `:46-48` | `session.**scalars**` |

`list_task_evaluations.py:50-51` deliberately carries only two of the three (it
returns the whole committed chain, current row first — phase-7 D15); it is **not**
a fourth site and a criterion that swept it in would be wrong.

**The mechanism.** There is a repo precedent and the plan should name it:
`tests/unit/services/queries/upholstery/test_list_upholstery_inventories.py:34-46,
63-64` — a fake `_Session` capturing the statement, then
`str(query.compile(compile_kwargs={"literal_binds": True})).lower()`. Two
adaptations the plan must state, because both are places an implementer would
guess:

- the three sites use `scalar` / `scalars`, **not** `execute` — the fake must
  implement the methods actually called;
- the evaluation SELECT is not the first statement. In the two budget-status
  services it is the 4th `scalar` call when the task has a PRIMARY item and the
  3rd when it does not (`_load_task_and_item`, `get_task_budget_status.py:51-78`,
  issues one, two, or three of its own). **Selecting by call ordinal is fragile
  and fixture-dependent**; select the captured statement whose compiled text
  names `item_cost_evaluations` instead.

**The mutations.** §9's expected-red rule requires mutation site → expected red
node id, one row per site. Three deletion-shaped mutations (per §9's P-I tenth
extension, each with its line range): delete `:107` / delete `:31` / delete `:47`
— each must redden its own site's structural row and nothing else. The plan owes
the node ids; the implementer runs and reports them per row (P-I fourth
extension: executed, never reasoned about).

### F4 (B4) — the scope fence contradicts the batch it fences

The Goal says "**NOT in this phase:** any code or schema change". The items
routed here that *are* code:

| Item | File(s) | Kind |
|---|---|---|
| r3-N1 structural rows | new/edited test file | test |
| r3-N2 C5 fixture | `test_phase8_status_results.py` | test |
| r3-N4 formatting | `test_phase8_serializers.py` | test |
| 4B N3 redundant clause | `get_economics_configuration_status.py:39,:49` | **production** |
| phase-6 r2 N1 docstring | `be9dfe42a035_…py:4` | **applied migration** |
| phase-2 N8 proxy regex | `test_phase2_*` downgrade proxy | test |
| phase-2 r3 N14 | `test_process_shopify_products_integration.py:179` | test (non-domain) |
| phase-3 S7 annotations | eleven `Mapped[float]` sites | **production** |

The eleven annotations are the sharpest case: master plan §6.1:187 says
"Annotation fix queued in the phase-9 drift batch", the phase-3 plan and its
implementer prompt both say "the annotation fix is phase 9's", and the phase-9
plan's own Goal forbids it. I verified all eleven are still live
(`production_cost_basis_version.py:24,25,26`; `item_cost_evaluation.py:33,34,36,38`;
`item_cost_evaluation_term.py:22`; `cost_model_term.py:22`;
`item_cost_result.py:23,25`), and the target precedent is
`user_work_profile.py:33-34` (`Mapped[Decimal | None]`).

Note that the projection prompt's own axis-5 list also omits the annotations —
so the omission is currently in three places at once.

**Routing:** replace "any code or schema change" with the enumerated allow-list
above (whatever subset survives S7/S9/S11's decisions), so the implementer prompt
can forbid everything else by name. A fence that contradicts the batch is a fence
the implementer will resolve silently — which is the exact failure this gate
exists to prevent.

### F5 (B5) — the backend table index was never routed, only its frontend mirror

`app/beyo_manager/models/tables/README.md` appears in no phase plan's file list.
It carries three live drifts:

1. **The nine item_economics tables are absent** from its 62-row index
   (`:5-66`) and have no sections. This was deferred here explicitly —
   `plans/phase_2_schema_models.md:222`: "`models/tables/README.md` (the tables
   index) is **deferred to phase 9's drift batch**" (phase-2 projection D16).
2. **`:468-470` still documents `item_value_minor`, `item_cost_minor`,
   `item_currency`** on `items` — dropped by `be9dfe42a035`.
3. **`:438` documents `item_upholstery_requirements.currency` as
   `create_type=False`** — false since phase 6 moved type-creation ownership;
   `item_upholstery_requirement.py:44` now carries `create_type=True`.

Drifts 2 and 3 are the *same* drift D22 routed for the **frontend mirror**
(`frontend/docs/architecture/backend/tables/README.md:437,467-469`). The mirror
was routed; the original was not. Both need the same edit, and doing only the
mirror would leave the backend's own index wrong.

*(Passing observation, pre-existing and out of scope: `:24` still indexes
`issue_category_configs`, dropped by `99accdeba8b9` per master plan §6.1:198.
Recorded, not routed.)*

### F6 (S1) — the C5 repair as routed turns the test red

Phase-8 r3-N2 says: "resolve the task before the second handler run, or rename
the row". The first half does not work. Verified:

- `test_phase8_status_results.py:493-544` asserts **ten** columns are identical
  across two handler runs (`:542`), including `task_closed_at` and
  `task_state_snapshot`.
- The handler **refreshes both every run** from the live task —
  `process_item_cost_result.py:110-111` (`"task_closed_at": task.closed_at`,
  `"task_state_snapshot": task.state`), and both are in `update_columns`
  (`:125-126`).
- `_prepared` leaves the task at `WORKING` (`:82`), so today both columns are
  vacuous — which is r3-N2's correct half.

Resolving the task *between* the runs flips `task_state_snapshot`
`working → resolved` and `task_closed_at` `NULL → timestamp`, and the equality at
`:542` fails.

**The repair that works:** close the task (state + `closed_at`) **before the
first** handler run. Both lifecycle columns then carry real closed values, the
"after close" scenario the row's name claims is genuinely reached, and the
equality still holds because the config supersession between the runs does not
touch them. `RESOLVED` is admitted (`process_item_cost_result.py:30-35`), so the
first run still writes.

Worth recording alongside: `task_state_snapshot` is **not** in §8A.4's
replay-identity set (`intention:1409-1412`), so C5 compares one column more than
the invariant names. That is stricter, not wrong — but the plan should say it is
deliberate.

### F7 (S3) — `items/README.md` carries two further drifts, both created by phase 6

Beyond §2.6-1 (`:34` `STALL`, verified live) and §2.6-2:

- **`:29-31` "Monetary fields"** documents `item_value_minor`,
  `item_cost_minor`, `item_currency` — dropped by phase 6. The plan's file list
  says "plus the phase-6 column removal reflected", which covers this if the
  implementer finds it; naming the line range removes the guess.
- **`:110-111`** states "This file uses `create_type=False` for
  `item_currency_enum` — the type is created by `item.py`. Import order in
  `models/__init__.py` must keep `item.py` before `item_upholstery_requirement.py`."
  Both sentences are now false: `item.py` has no currency column at all
  (verified — its only `create_type=True` is `item_state_enum` at `:25`), and
  `item_upholstery_requirement.py:44` owns the type. The import-order instruction
  is actively misleading to the next person who touches `models/__init__.py`.

Neither is in §2.6 (which predates phase 6) nor in the plan's task list.

### F8 (S4) — §2.6-2's instruction would delete live documentation

§2.6-2 says to remove the section documenting `base_time_seconds` /
`time_multiplier` / name-snapshot columns "that no longer exist". Verified:
`item_issue.py` has none of the four names the README lists at `:53-56`. But it
**does** carry three snapshot columns under different names —
`issue_type_snapshot`, `issue_mode_snapshot`, `placement_of_issue_snapshot`
(`item_issue.py:43-45`). Deleting the whole "Snapshot on creation" block would
leave three live columns undocumented and the "snapshot immediately" rule
unstated.

**The instruction is replace, not remove.** The "Timing fields" paragraph at
`:61` has no live referent and is a straight deletion.

### F9 (S5) — the `tasks/README.md` stale-reference set is six sites, not two

§2.6-3 names `:8,42`. Verified stale sites: `:8` (file/table/prefix row for
`task_history_record.py` / `thr`), `:24`, `:35`, `:42`, `:146`, `:150`. Verified
non-existence: no `task_history_record.py` in `models/tables/tasks/`, and
`grep -rn "latest_history_record_id\|task_history_record" --include="*.py"`
returns **zero** hits repo-wide.

`:146` and `:150` are a whole "`task_events` and `task_history_records` — key
rules for commands" section, i.e. a heading and rules for a table that does not
exist — a larger edit than a two-line fix, and it should be sized as such.

The D-4 line the plan adds to this same file is separately fine: I verified
`transition_step_state.py` guards step terminality only, and the plan's wording
("step transitions are not guarded on task terminality and terminal commands
leave open step records open") matches intention §8A.5:1419-1423.

### F10 (S6) — the prefix-map ordering criterion has no stated target

N5 says "the five `ProductionCost*`/`CostModel*` rows land after `StaticCost`".
Verified `client_id_prefix_map.md`: those five are at `:52-56` — but **four more**
new rows are also out of order, `ItemCostEvaluation` / `ItemCostEvaluationTerm` /
`ItemCostResult` at `:41-43` (after `ItemValuation` at `:40`, where
alphabetically they precede `ItemUpholstery`). Nine rows, not five.

And the file is not alphabetical to begin with: `ShopifyIntegrationEvent` /
`ShopifyOAuthState` / `ShopifyShopIntegration` (`:58-60`) follow `SkuTemplate`
(`:57`). So "restore alphabetical order" is ambiguous between "sort the nine new
rows into place" and "sort the file". **Recommend the former**, stated explicitly,
with the pre-existing Shopify violation recorded as untouched — otherwise the
diff balloons and the reviewer cannot tell intent from accident.

### F11 (S7) — phase-2 N4 cannot be discharged as a drift-batch item

N4 wants `checkfirst=True` removed from the five new enum creations so a
pre-existing type fails loudly instead of being adopted. The only site is
`90cdd23a828e_item_economics_schema.py:53-57` — an **applied** migration (head is
`c1d2e3f4a5b6`, four revisions later). Charter rule 7 forbids rewriting it, and a
follow-up revision is meaningless: the five types already exist, so the posture
N4 wants can never fire again on this chain.

**Recommend:** close as WONTFIX in the Review log with that rationale, and carry
the posture as a note in the migration-squash seed (which master plan §11 /
the owner's post-v1 items already hold). Leaving it listed as an open drift item
into v1 closure is the failure mode the census axis exists to catch — it would
silently evaporate.

### F12 (S8) — the docstring fix needs its rule-7 exemption stated

Verified live: `be9dfe42a035_drop_legacy_item_money_columns.py:4` reads
`Revises: 5caae620088c` while `:15` reads `down_revision = "5420acc6a7b3"`.
`5420acc6a7b3` is the journaled money migration — the docstring names the wrong
parent inside a destructive migration.

This is an applied migration, so F11's rule-7 question arises again — but here
the answer is different: the edit changes a docstring, not an operation, and
Alembic derives the chain from `down_revision`, never from prose. **The plan
should say so explicitly.** Without it, a careful implementer refuses the edit on
rule 7, or a careful reviewer flags it — the phase-6 r2 record already shows this
item surviving one round on a claim that it was closed when it was not
(`plans/phase_6_…:766-772`).

### F13 (S9) — N14 has moved and was filed against the wrong assertion

Filed as "`test_process_shopify_products_…` compares an unordered `SELECT` as an
ordered list (`:176`)". Verified today in
`tests/integration/services/commands/shopify/test_process_shopify_products_integration.py`:

- `:175` — the **events** assertion is already a set comparison, with a comment
  explaining why. Not the defect.
- `:179` — `"sync_item_client_ids": [row.client_id for row in rows]` still
  compares an **ordered list** against `rows`, whose query (`:158-162`) has no
  `ORDER BY`. This is the live half.

The file's last commits are pre-project (`e795aa4`), so the set-comparison at
`:175` predates the filing — N14 named the wrong line from the start.

Second question the plan must answer: this is a **non-economics** test file. The
routing was "next touch of that file / phase 9". Phase 9 touches no Shopify code.
Take it (a one-line change, and the flake threatens the byte-identical baseline
gate every phase depends on) or re-route to the maintenance channel — but decide.
**Recommend take**, with the corrected line cited.

### F14 (S10) — the structural arbiter's boundary is unstated

The three-clause committed-current filter appears at **seven** production sites,
not three (verified by grepping `ItemCostEvaluation.superseded_at.is_(None)`):

| Site | Covered by r3-N1? |
|---|---|
| `get_task_budget_status.py:106-108` | yes |
| `get_task_budget_status_worker.py:30-32` | yes |
| `get_item_lifetime_economics.py:46-48` | yes |
| `services/tasks/analytics/process_item_cost_result.py:66-68` | **no** |
| `commit_item_cost_evaluation.py:277-280` | **no** |
| `commit_item_cost_evaluation.py:288-290` | **no** |
| `create_item_cost_projection.py:32-34` | **no** |

Intention §8A.6:1451-1453 says "**every** operational read carries the literal
filter". The handler site is the one whose silent failure is worst — it resolves
the evaluation that gets **persisted** into `item_cost_results`, and §8A.3 names
that resolution explicitly.

r3-N1's own wording ("the first phase touching the status queries") is a faithful
reason for stopping at three. But the plan should say that is the reason, so the
boundary is a recorded decision rather than an oversight a later reader has to
reconstruct. **Recommend:** hold the three, record the four, and file the handler
site as an only-if-cheap ledger entry (master plan §11).

### F15 (S11) — the plan promises a zero graph delta and a new node at once

Plan Notes: "Archgraph: expected delta ≈ zero (docs); state it explicitly at
close." Plan Notes, four lines earlier: phase-1 N2 — "the ADMIN/MANAGER-only
step-money audience is a real architectural policy no archgraph node carries —
candidate node/description in this phase's graph delta."

Verified: `archgraph_search_nodes("money exposure boundary worker redaction
audience")` returns **0 of 174** nodes. The policy is still uncarried.

**Recommend:** build the node. It is the one architectural fact of this project
that lives only in prose (§11A.1/§11A.3), it is exactly what the graph is for,
and phase 9 is the last chance inside v1. If it is instead re-routed, the Notes'
"delta ≈ zero" line stands and N2 needs a named destination — not silence.

### F16 (S12) — C4 has no arbiter, and the file it audits misdescribes itself

**The arbiter gap.** C4 says `routers/README.md` "mirrors every route the registry
§6.5 shipped". Per P-R, a criterion only a harness can satisfy names its harness.
There is one available and it is cheap: 23 rows exist at `routers/README.md:58-80`
and every route's role gate is greppable in `routers/api_v1/item_economics.py`
(`require_roles([...])`, verified at `:150 … :389`). Phase-8 L5's
hand-written-literal rule binds: the expected row set is written by hand, never
derived from `router.routes`, or it cannot disagree with the router.

**The file lies about its provenance.** `routers/README.md:3` reads
"*Autogenerated from FastAPI OpenAPI.*" and **no generator exists in-tree**
(verified: nothing under `scripts/` or anywhere in `*.py` references it). This is
8B projection L14, and it matters for the frontend handoff: everything in that
file is hand-maintained and can silently rot.

**The PUT `/api/v1/tasks` body table is materially wrong.** Verified against
`routers/api_v1/tasks.py:95-204`, the table at `:2645-2694` is missing
`assortment` (`tasks.py:190`), `item.item_zone` (`:112`),
`item.can_have_upholstery` (`:117`), `item.item_value_minor` / `item.item_cost_minor`
/ `item.item_currency` (`:105-107` — **retained deliberately** per R14/D6 so the
bridge can 422), `shopify_preorder` (`:204`), `notes[].plain_text` /
`notes[].users_read_list` (`:145-146`), and `steps[].ready_by_at` /
`steps[].reason` (`:282-285`). Five of its six `item_issues[]` rows are phantom
against `_TaskItemIssueBody` (`:120-128`): only `issue_type_id` is real;
`issue_severity_id`, `base_time_seconds`, `time_multiplier`,
`issue_name_snapshot`, `severity_name_snapshot` do not exist, and seven real
fields are undocumented.

The three legacy money rows deserve emphasis for the frontend handoff: their
**absence** from the table is the drift that bites hardest, because a frontend
reader concludes those keys are merely unknown when in fact sending one non-null
returns 422 `ITEM_MONEY_MOVED`.

*(Verified correct: 8B's own three rows landed —
`item.expected_sale_price_minor` / `purchase_cost_minor` / `currency` at
`:2667-2669`.)*

### F17 (S13) — the frontend mirrors are routed in prose only, and undercount by one

D22's four cited ranges are all live and exact:
`frontend/docs/architecture/backend/routers_endpoints/README.md:1918-1920,
1976-1978, 2078-2080, 2475-2477` (verified).

`frontend/docs/architecture/backend/tables/README.md`: D22 names `:437,467,469`
and says ":469 also mirrors the `create_type=True` flag phase 6 flips". Verified,
with a correction — `:467-469` are the three dropped item money columns (all
three go), and the `create_type` flip is at **`:437`**
(`item_upholstery_requirements.currency`, documented `create_type=False`, now
`True`). D22 attributes the flag to the wrong line; both `:437` and `:467-469`
need edits, for two different reasons.

These files sit outside `backend/`, so they need the same explicit scope
confirmation the plan already demands for Application_contracts (F18). They are
currently in Notes only, not in "Files expected to change".

### F18 (S14) — the Application_contracts decision is still open

The plan's Files list defers it: "the coordinator confirms it is in the session's
scope before compiling the prompt, or reroutes these two as an explicit
maintenance item." That decision has not been recorded, and the prompt cannot
compile without it.

Both drifts verified live:

- `Application_contracts/planning/task/task_step_models.md` — zero occurrences of
  `total_working_seconds` or `total_cost_minor` (§2.6-4's gap).
- `Application_contracts/planning/item/item_models.md:104-107` — a "Value and cost
  semantics" block describing `item_value_minor` and `item_cost_minor` as live
  fields (§10.2's breakage list).

`/Users/davidloorenz/Desktop/Developer/Application_contracts` **is** among this
session's additional working directories, so the mechanical obstacle is absent;
the decision is whether phase 9 owns the edit.

### F19 (S15) — two contract-gap amendments are routed here and appear in no task

Master plan §5:143-150 records a standing divergence and says: "The local contract
file's actual amendment lands with the phase-9 drift batch, **alongside the
`05_errors` gap**." Neither is in the phase-9 plan.

Verified:

- `architecture/46_serialization_local.md` is an **unmodified template** — every
  section still holds its placeholder comment. The standing divergence (router-owned
  serialization mandated; the query layer does the opposite; phases keep
  serialization where the code they modify has it) is recorded nowhere a future
  implementer would look.
- `architecture/05_errors_local.md` **does not exist**, and
  `app/beyo_manager/errors/base.py:3-10` confirms the divergence: `http_status` and
  `message`, no `code` field. §6.4's entire leading-token carrier decision rests on
  this and it is unrecorded in the contract set.

These are the highest-leverage documentation items in the batch — they are what a
future agent reads *before* writing code — and they are the two the plan does not
mention.

### F20 (L1) — declaration order is not evaluation order

`domain/item_economics/enums.py:15-27` declares `EconomicsStatusEnum` with
`INFEASIBLE` and `OK` **last**; §11A.4/§7C.3 evaluate them **first** (group 1).
Master plan §6.3:269 records that declaration order carries no precedence.

A docs page or handoff that lists the twelve members "verbatim from the enum"
therefore publishes the *wrong* order for a reader trying to understand which
status wins. The criterion should say: the twelve **values** are verbatim from the
enum; the **order** is §11A.4's evaluation order (`item_missing_major_category` →
… → `not_evaluated`, with group 1 evaluated first). Verified: twelve members,
values match §7C.3.

### F21 (L3) — the formatting item is a hand edit, not a sweep

Verified: `ruff check` on `test_phase8_serializers.py` passes ("All checks
passed!") — consistent with r3-N4's "cosmetic, ruff-silent". The defect is at
`:14`, an over-indented `)` closing the import block, plus a missing blank line
before `def _result()`.

But `ruff format --diff` on that file wants ~90 lines changed, including
reflowing the `@pytest.mark.parametrize` rows that carry the P-V authority-row
ids. **A blanket `ruff format` is not the repair** — it would blow the perimeter
and churn exactly the ids phase-8's P-V criterion depends on. The plan should name
the two-line hand edit and forbid the sweep. ("Fold into this phase's formatting
sweep" currently invites the wrong action.)

### F22 (L6) — the accuracy harness the plan asks for is buildable

Axis 2 asked what arbitrates a docs page. Everything needed exists:

- **Routes** — 23 rows at `routers/README.md:58-80`, matching
  `routers/api_v1/item_economics.py`.
- **Role gates** — `require_roles([...])` per route; all ADMIN/MANAGER except
  budget-status (`:347`, ADMIN/MANAGER/WORKER/SELLER), exactly as §6.5 registers.
- **Error identities** — §6.4's list; each is a leading token greppable in
  `services/commands/item_economics/`.
- **Status vocabulary** — `enums.py:15-27` (values) + §11A.4/§7C.3 (order).
- **Nine no-longer-carrying read surfaces** — enumerated in
  `plans/phase_6_…:195-204` (D4): 6 via `domain/tasks/serializers.py::serialize_item`,
  3 via `domain/items/serializers.py::_serialize_item_base`.
- **The graph** — 174 nodes / 260 edges, all `human_confirmed`, 0 pending, 0 stale
  (verified), including one node per item-economics endpoint and command.

**Recommended criterion shape:** every route path, payload key, error identity and
enum member appearing in the page or the handoff greps to a shipped artifact, and
the expected sets are **hand-written literals** (phase-8 L5), never derived from
the surface being audited.

### F23 — placement of the deploy-ordering line (axis 4), unresolved

Phase-6 r1 N9 routes "one operations line" to the living-docs page: `be9dfe42a035`
drops columns the previous release's ORM still selects, so an old process
surviving the migration 500s on every item read; the required order is deploy code
first, migrate second.

Two problems with the routed destination:

1. `docs/README.md`'s discipline section forbids domain docs from referencing
   migrations. A rolling-deploy hazard about a specific revision is exactly that.
2. `23_documentation.md:60-63` places operational procedure in `docs/runbooks/`
   — and **`docs/runbooks/` does not exist** in this repo (verified: `docs/` holds
   `architecture`, `debugging`, `deploy`, `domains`, `handoff`).

`docs/deploy/` **does** exist and is the nearest live home. **Recommend:** the
operations line lands in `docs/deploy/`, and the domain doc — if it mentions the
hazard at all — states the ordering rule without naming a revision. The plan
currently says "the living-docs page" and the implementer will otherwise write a
migration reference into a document whose own rules forbid one.

---

## Forward-note census

Every note routed to phase 9 across all eight phases, from the plan's own Notes
plus a grep of `plans/`, `archive/`, `handoffs/`, `planning/` and the master plan
for "phase 9" / "phase-9". **Landed** = named in a plan task or the Files list.
**Notes-only** = present in the plan's Notes but absent from tasks/Files.
**UNROUTED** = routed to phase 9 by an upstream artifact and absent from the
phase-9 plan entirely.

| # | Source | Note | In plan? | Verified state | Ledger |
|---|---|---|---|---|---|
| 1 | phase-1 r1 N1 | frontend handoff publishes `total_cost_minor` for the worker reassigned-steps page | Notes-only | LIVE — `HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md:166` (example payload) and `:393` (field table: always-present "yes"); the only live handoff carrying the key | F24 |
| 2 | phase-1 r1 N2 | money-audience policy has no graph node | Notes-only | LIVE — 0 of 174 nodes match | S11 / F15 |
| 3 | phase-2 r1 N4 | `checkfirst=True` on the five new enum types | Notes-only | LIVE at `90cdd23a828e:53-57`, **undischargeable** (applied migration) | S7 / F11 |
| 4 | phase-2 r1 N5 | `client_id_prefix_map.md` row ordering | Notes-only | LIVE — nine rows misordered (`:41-43`, `:52-56`), not five | S6 / F10 |
| 5 | phase-2 r2 N8 | downgrade proxy misses raw-SQL `DROP TYPE` | Notes-only | test-side, actionable; no task | — (fold into F4's allow-list) |
| 6 | phase-2 r3 N14 | order-dependent Shopify assertion | Notes-only | LIVE at `:179`, **not** the filed `:176` | S9 / F13 |
| 7 | phase-2 projection D16 (`plans/phase_2_…:222`) | `models/tables/README.md` gains the nine tables | **UNROUTED** | LIVE — absent from the 62-row index | B5 / F5 |
| 8 | phase-3 projection S7 | eleven `Mapped[float]` annotations | **UNROUTED** (master plan §6.1:187 routes it here; plan Notes mention it under "phase-2/3 additions" but no task, and the Goal forbids it) | LIVE — all eleven verified | B4 / F4 |
| 9 | phase-4 projection S5 | OpenAPI-mirror manual criterion; "phase 9 C4 backstops" | implied by C4 | C4 has no arbiter | S12 / L5 |
| 10 | phase-4 r3 N10 | wall-clock timeout bounds, "only if flakiness appears" | **UNROUTED** | conditional; no flakiness observed this session | L4 — record as no-action |
| 11 | phase-5 r1 N5 | valuation payload field list → phase 9 docs pass | **UNROUTED** (in the projection prompt's Ground, not in the plan) | discharged by the `api.md` payload catalog once B1 lands | fold into F1 |
| 12 | phase-6 projection D22 | frontend doc mirrors | Notes-only | LIVE — all four ranges exact; `tables/README.md` needs `:437` **and** `:467-469` | S13 / F17 |
| 13 | phase-6 r1 N9 | deploy ordering for the column drop | Notes-only | destination conflicts with the docs discipline; `docs/runbooks/` does not exist | F23 |
| 14 | phase-6 r2 N1 | drop-migration docstring parent | Notes-only | LIVE — `be9dfe42a035:4` vs `:15` | S8 / F12 |
| 15 | phase-8 projection L17 (4B N3) | redundant `and not version.is_deleted` | Notes-only | LIVE at `:39` and `:49` (plan says `:38`/`:47`) | S2 — corrected below |
| 16 | phase-8 r3 N1 | structural compiled-statement filter arbiter | Notes-only | three sites verified; four more uncovered | B3 / S10 |
| 17 | phase-8 r3 N2 | C5 closed-task premise | Notes-only | LIVE; **the routed repair reddens the test** | S1 / F6 |
| 18 | phase-8 r3 N4 | serializer test formatting | Notes-only | LIVE at `:14`; sweep is the wrong instrument | L3 / F21 |
| 19 | phase-8B projection L14 | `routers/README.md` PUT `/tasks` pre-drift | Scope addition | LIVE and wider than filed | S12 / F16 |
| 20 | phase-8B projection L15/L18 | quantity-is-per-item; the two-call flow; no priced-or-not signal | Scope addition | governing; no artifact check needed | — |
| 21 | intention §2.6-1 | `items/README.md:34` `STALL` | Files list | LIVE | — |
| 22 | intention §2.6-2 | dropped `item_issues` columns | Files list | LIVE, but the instruction is *replace* | S4 / F8 |
| 23 | intention §2.6-3 | `tasks/README.md` history-record references | Files list | LIVE at six sites, not two | S5 / F9 |
| 24 | intention §2.6-4 | Application_contracts step aggregates gap | Files list (deferred) | LIVE; scope undecided | S14 / F18 |
| 25 | intention §2.6-5 | dead code/columns | out of scope by plan | — | — |
| 26 | gate D-1 | five `serialize_step` call sites | Read-first | superseded by §11A.2's eight-endpoint census; the docs must publish the census, not the five | fold into F1 |
| 27 | gate D-3 | archgraph anchor drift | Notes ("verify and mark") | RESOLVED — 0 pending, 0 stale, rev `452befdb…` | L2 |
| 28 | gate D-4 | step-transition / task-terminality behaviour | Files list | LIVE and accurately worded in the plan | — |
| 29 | intention D22/§10.2 breakage | `item_models.md` "Value and cost semantics" | Files list (deferred) | LIVE at `:104-107` | S14 / F18 |
| 30 | master plan §5:143-150 | `46_serialization_local.md` amendment + the `05_errors` gap | **UNROUTED** | LIVE — template unmodified; `05_errors_local.md` absent | S15 / F19 |
| 31 | master plan §7:560-564 | bridge-validator removal recorded as a follow-up | task 4 | verify at closeout | — |
| 32 | phase-9 plan task 4 | D-3 + §2.6-5 ledger confirmations | task 4 | D-3 now resolved (row 27) | L2 |

**Census result: 32 rows. 5 UNROUTED (rows 7, 8, 10, 11, 30), 14 Notes-only,
2 upstream notes factually wrong (rows 6 and 17), 1 undischargeable (row 3).**

### F24 — a note on row 1's editability

`docs/handoff/to_frontend/` is the live frontend contract per `docs/README.md`
("See the contract with the frontend"), and it carries its own `archived/`
subfolder for frozen documents. The file to correct is in the **live** tier, so
editing it is legitimate — but the charter's artifact map ("evidence documents are
records — never edited") plus the plan's own Notes reminder could easily be read
the other way. The plan should state the tier rule in one line so the implementer
neither refuses the edit nor edits something under `archived/`.

---

## v1 closure shape (axis 6)

What the closeout must verify, beyond the phase's own criteria:

1. **Every §13 must-ship row discharged.** Note that §13's list names
   "living-docs page (`docs/domains/`) + archgraph delta in the same change" and
   "contract-gap routing (§2.6)". The archgraph clause interacts with F15 — a
   literal reading of §13 expects a delta, which is one more reason to build the
   money-audience node.
2. **The post-v1 items handed off, not dropped:** the migration-squash seed
   (Findings 1–7, plus F11's `checkfirst` posture), the N11 residue research
   (~116 non-economics workspaces per full run, master plan §10), the
   bridge-validator removal (master plan §7:560-564), and F14's four uncovered
   filter sites if they are not taken here.
3. **The five UNROUTED census rows** each end in a task or an explicitly recorded
   re-route. A note that evaporates at v1 closure never gets another gate.
4. **The projection gate's own status.** Per charter self-retirement, this
   projection is not empty, so the gate does not demote — moot, as this is the
   last phase, but the master plan should record it rather than leave it implied.

---

## Verified corrections executed

Per the closing protocol, cheap verified corrections are executed. **One** was
in scope (a citation inside the plan's own Notes; no semantic change, no task or
criterion touched):

- `plans/phase_9_docs_and_drift.md`, the phase-8-projection-L17 note:
  `get_economics_configuration_status.py:38,:47` → `:39,:49`, verified against
  the file this session.

Everything else in the ledger requires a task, criterion, or scope decision and is
routed to the coordinator, not executed. **No other plan text, no intention text,
no code, and no criteria were modified.**

---

## Write perimeter (full)

**Documents written (2):**

1. `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-15_phase9_projection_r0_handoff.md` (this file — new)
2. `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_9_docs_and_drift.md` — **one-line citation correction only** (`:38,:47` → `:39,:49` in the phase-8 L17 note). Diff is one line.

**Code written:** none.

**Tests written or run:** none. No suite run this session — a projection proves
implementability on paper; the §10 baseline (2184 / 23 / 1 = 2207 selected) is
carried from the phase-8B closeout, unverified by me and not relied on for any
finding.

**Tool-recorded state:** none. Archgraph was **read-only** — two calls,
`archgraph_status` and `archgraph_search_nodes`. Zero delta. Live state recorded:
**174 nodes / 260 edges, revision `452befdba995e4d01bb88223b0adbaa63214151d8d038b27ec7db152841713dd`,
0 pending, 0 stale, 0 diagnostics** — which supersedes both the plan's Ground
(173/256, `45b72196…`) and the projection prompt's closing-protocol restatement of
`45b72196…`.

**Mutation probes:** none run. No file was mutated and reverted; every finding is
from reading the tree as committed.

**Databases touched:** none. No pytest, no alembic, no psql — head
(`c1d2e3f4a5b6`) was confirmed statically, by verifying no migration under
`app/migrations/versions/` carries it as `down_revision`.

**Git state:** working tree carries exactly the two documents above.

---

## Exit condition

Every ledger row must be routed — amendment applied, upstream change made, or
delegation recorded — and **owner card 1 answered** before the implementer prompt
compiles. B1 is the ordering constraint: C1 and C2 cannot be rewritten until the
page's shape is settled, and F1's folder decision changes what the phase's
central task even produces.
