---
plan: phase 9 (living docs & drift routing — the LAST phase of v1)
role: implement
round: 1
state: IMPLEMENTED
date: 2026-08-15
actor: Claude Opus 5 / implementation-executor
---

# Phase 9 implement r1 — handoff

## Summary

The GOVERNING amendment block P1–P22 is discharged in full. Phase 9 shipped the
`docs/domains/item_economics/` folder and its `docs/README.md` row, the TWO frontend
handoffs covering all twenty-three endpoints, four new arbiter test files, the nine-item
code allow-list, the README / prefix-map / mirror / contract-amendment batch, and one
additive archgraph node.

**Suite: 2249 passed / 23 failed / 1 deselected = 2272 selected**, from one foreground
run of `PYTHONPATH=. python3 -m pytest -m 'not e2e' -q` in `backend/app/`. The
twenty-three failures are **byte-identical** to the phase-1 baseline list — both sets
sorted and `diff`ed, output empty. The +65 over the 2184 baseline reconciles exactly:
8 (C1) + 3 (P3) + 4 (C4) + 50 (handoff/docs accuracy) = 65.

`ruff check` clean on all fifteen touched Python files. DB left at head `c1d2e3f4a5b6`;
**no migration ran** — the only migration touch is P10's docstring line. Archgraph:
one additive node, **175 nodes / 260 edges**, revision
`7dcdb9b01f03611f0605b77622963e205e9073ecf0cca7f3d988e31a2fb3c36f`, 1 pending (that
node), 1 stale (declared under Drift below).

Checkpoint commit: `4b648c0`.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing on this phase needs the owner. Every open question the projection raised was
routed by the coordinator before the prompt compiled, and no new semantic hole appeared
during implementation.

---

## Criteria

| Criterion | State | Evidence |
|---|---|---|
| **C1** (automated, per P2) | **green** | `tests/unit/docs/test_item_economics_docs.py` — 8 nodes: four file-existence rows + four literal-containment rows (`intention-6A.4-presentation-rule`, `intention-8A.2-two-cost-numbers`, `P-D-planning-allocation`, `P-C-worker-minutes`). Anchored `Path(__file__).resolve().parents[4] / "docs" / "domains" / "item_economics"`; whitespace is normalised on both sides so a markdown rewrap cannot break the alarm while a reword still does. |
| **C2** (reviewer-verified) | **content shipped; self-check below** | Both cost definitions sit side by side in `docs/domains/item_economics/README.md` under "The two cost numbers — they are different numbers on purpose", carrying the §8A.2 sentence verbatim plus a four-row table and the reason (paused seconds are wage cost, not purchased capacity). The presentation rule appears verbatim under "Percentage terms are planning allocations, never tax". Self-check run: `grep -rn "minutes per worker" docs/domains/item_economics/ docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_*` → **zero hits** (P-C). No sentence in the folder or either handoff presents a percentage term as computing tax; the configuration handoff additionally instructs the frontend not to label the field "tax", "VAT" or "moms". |
| **C3** (reviewer-verified) | **content shipped** | `items/README.md`: `STALLED` at the state line; the money block gone; the snapshot section replaced with the three live columns (`issue_type_snapshot` / `issue_mode_snapshot` / `placement_of_issue_snapshot`, verified against `item_issue.py:43-45`); the timing paragraph deleted; the `create_type` / import-order claims corrected against `item_upholstery_requirement.py:44` and `item.py:25`. `tasks/README.md`: all six stale `task_history_record` sites gone, and the D-4 line checked against `transition_step_state.py:150`'s actual guard (step terminality only) and the re-emit that handles the consequence. |
| **C4** (reviewer-verified, arbiter per P15) | **green + arbiter** | `tests/unit/routers/test_phase9_item_economics_route_mirror.py` — a **hand-written** 23-row literal set of (method, path, role gate), asserted (a) against `routers/README.md`'s Quick Index rows for `/api/v1/item-economics/` and (b) against the router source's decorators and their `require_roles([...])` dependencies, plus a prefix-registration row. Never derived from `router.routes` (phase-8 L5). Application_contracts landed — see P13 below. |

**The handoffs' accuracy arbiter** (P6's "same harness", hardened): 50 nodes in
`tests/unit/docs/test_item_economics_handoff_accuracy.py`. Hand-written sets for the 13
configuration routes, the 10 operational routes, the 30 literal error identities and the
6 composed admission identities. It asserts: each handoff documents **exactly** its half
of the surface (heading-level method+path equality, not containment); the two together
cover all 23; no document invents a fully-qualified item-economics path (route shape
compared after normalising both `{param}` and a worked example's `itm_01H…`); no document
names an unregistered identity; every literal identity is greppable in `beyo_manager/`;
both halves of each composed identity are greppable (the full token is built at raise
time by `admission_error`, so only the halves can be); the operational handoff's §6 names
exactly the twelve `EconomicsStatusEnum` values and nothing status-shaped outside them;
and the documented budget-status key sets — manager and worker, top level and `result` —
equal what `serialize_task_budget_status` actually emits.

---

## Mutation ledger

**Named by the plan: 3. Executed: 3.** Expected-red node ids were written down before
each run. Every red set was observed over `tests/unit` (`-m 'not e2e' -p no:randomly`;
1366 passed / 8 pre-existing failures), diffed both ways against a baseline capture of
that same scope.

| # | Mutation (line-pinned) | Mutant sha256 | Restored sha256 | Expected red | Observed red |
|---|---|---|---|---|---|
| M1 | `services/queries/item_economics/get_task_budget_status.py` — delete `:107`, `            ItemCostEvaluation.superseded_at.is_(None),` (definition site inside `get_task_budget_status`) | `b66a7fce09a60b0dc8edda91f25ee107b9a03642220afed519337d34dd63392b` | `5f89e29b695ea13f13666ecb5ff9e315fdf61e2e745f61ca8cba48a90a68bde8` | `tests/unit/services/queries/item_economics/test_phase9_committed_filter_structure.py::test_committed_current_filter_is_present_in_the_compiled_select[get_task_budget_status.py:106-108]` | **exactly that node.** Zero collateral; zero baseline failures disappeared. |
| M2 | `…/get_task_budget_status_worker.py` — delete `:31`, same clause | `258873a603b105302348f2e72c783746e35e85e68f50b9c1bd3bda9b30b7150a` | `011cf2ae76dde81fe837a1f7b5f8a869230621001c64af06feb7718951970f00` | `…[get_task_budget_status_worker.py:30-32]` | **exactly that node.** Zero collateral. |
| M3 | `…/get_item_lifetime_economics.py` — delete `:47`, same clause | `89a4d32613b1699f82e1a0a32d19c5bd1290cb06588a215ff867d99af953d6e1` | `1f26eecaaeeb6df153316640d99e1d067aed69844e418d13c93efbd0e7cf315e` | `…[get_item_lifetime_economics.py:46-48]` | **exactly that node.** Zero collateral. |

Per-site red only, as P3 predicted. M1 cannot reach the worker row because the worker
service carries its own copy of the filter — a deliberate phase-8 decision, and the
reason the three rows are three rows.

**Self-chosen probes (4).** Declared because the four new arbiters would otherwise reach
the reviewer unfalsified. All applied and reverted; restored hash equals pre hash in
every case.

| # | Probe | Mutant sha256 | Restored sha256 | Observed red |
|---|---|---|---|---|
| P-a | delete `app/beyo_manager/routers/README.md:70` (one Quick Index row) | `cd7bf852cfb4ba98650782156ec4b5f71b73c444498cf07d3187862db743f757` | `fc67aabfe64b05f2096a4950702fb5e0f0567dd4f30662e8e1bc57266ce562be` | `test_phase9_item_economics_route_mirror.py::test_readme_quick_index_mirrors_every_shipped_route` |
| P-b | drop `WORKER` from the budget-status gate, `routers/api_v1/item_economics.py:347` | `f9bfed7067897d0392807cb2873f8ea109fb700ca15ccc2e105f3eaf7a324e89` | `799d205d432435ffb6a88eead011803a698e157df44a0ab43c3e8a31739dc15a` | `…::test_router_source_matches_the_hand_written_route_and_role_set` |
| P-c | rename one identity in the operational handoff (`ITEM_COST_TASK_TERMINAL` → `ITEM_COST_TASK_ALREADY_CLOSED`) | `98c52885957f97ebd627a3d4a1812d65a7c6d5db1c346047822e3776e7fb413b` | `f3b036ba7dccb8710e75717688b510a914e017b19ecca1faff81dc3711c9188d` | `test_item_economics_handoff_accuracy.py::test_no_document_names_an_unregistered_error_identity[operational]` |
| P-d | re-add `consumed_cost_minor` to the worker branch of `_serialize_result` (definition site) | `881b5ea368dec47068c1e0e016625881a75b8d8d4a0a2586d870fcdf368f0964` | `12d6e36a7a04074c03c277704d66744d8da7adade3469edd0c9de27ce2a53f88` | **two** nodes: `…::test_the_documented_budget_status_keys_are_the_shipped_keys[budget-status-worker-shape]` and `…::test_the_worker_budget_status_carries_no_monetary_key` |

**Files a mutation probe touched (applied-and-reverted), listed separately from the
phase's own changes** — every one restored byte-identical to its pre-probe hash:

- `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py` (M1)
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py` (M2)
- `app/beyo_manager/services/queries/item_economics/get_item_lifetime_economics.py` (M3)
- `app/beyo_manager/routers/README.md` (P-a) — **also a phase change**; the probe was run
  before the final hash was taken, and the restored hash equals the committed hash
- `app/beyo_manager/routers/api_v1/item_economics.py` (P-b) — **not otherwise touched by
  this phase**; it is unmodified in the commit, which the tree confirms
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` (P-c) — also a phase change; restored hash equals the committed hash
- `app/beyo_manager/domain/item_economics/serializers.py` (P-d) — **not otherwise touched
  by this phase**; unmodified in the commit

---

## Write perimeter (full)

### Backend — `ManagerBeyo-app/backend`, all in commit `71616af`

New (13):

| sha256 | file |
|---|---|
| `4790f91842be00ee35f8027909598a37e10f03e877c7461c59417007263bf501` | `docs/domains/item_economics/README.md` |
| `3bc334caed3b9bcdfd6ac763032ea782985f780d4bbe5526d408e9fe44b9eff4` | `docs/domains/item_economics/api.md` |
| `8463cc2e69bb00f7d502b7496e4a6ac8c894651c18d993532135602abb385664` | `docs/domains/item_economics/events.md` |
| `f48c1e06b04837d893d2a147e79f1441b55da20dd9f8152545a77bc13e126f8a` | `docs/domains/item_economics/states.md` |
| `f3b036ba7dccb8710e75717688b510a914e017b19ecca1faff81dc3711c9188d` | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` |
| `37f351fdd28d156555f4cdc64773a7fce165b951061c886736ae85687477e4c3` | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_configuration_20260815.md` |
| `beba00150d7df471c5fc69a007294e0a1e45f67e163f60670652184c87d5c0a3` | `docs/deploy/RUNBOOK_20260815_item_money_column_drop_ordering.md` |
| `38c24eb3fd973ca96568d52bd414fbef9d482b472de08cc20644fc354712c693` | `architecture/05_errors_local.md` |
| `c0322117f26ffa8b635fc19e355341072605f2031e3a9f04ccacb2ceeebba4fc` | `app/tests/unit/docs/test_item_economics_docs.py` |
| `ac34d9717c4056d6ccbbf85ec8db8b12ed16c1fd96976cee24a0bf8d8e15c6aa` | `app/tests/unit/docs/test_item_economics_handoff_accuracy.py` |
| `c7f598bdae45bde1c15d500a106b852e2b9c6c9d81e4bd02cfb5390f1d01545f` | `app/tests/unit/services/queries/item_economics/test_phase9_committed_filter_structure.py` |
| `8e1720b88f5ab2a112d8ee7f78a54f7fd5a034d483891be7f20fc62555eb5d58` | `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` |
| *(this file)* | `docs/architecture/.../handoffs/implementer/2026-08-15_phase9_implement_r1_handoff.md` — written **after** the checkpoint, per protocol |

Modified (21):

| sha256 | file |
|---|---|
| `cc53390b4a973a40abe00c45d1e6f61f33ee4e492ae21217306e8dccef4c1333` | `docs/README.md` |
| `17620cb814ea9dff6640e5e32c843e6addf56adc02e7350b9e5e97ef277cb75e` | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md` |
| `121820edf8d8e8216d90fce9737e25b5b68edc3680f492b1e7e0b81c0e7d5d67` | `architecture/46_serialization_local.md` |
| `fc67aabfe64b05f2096a4950702fb5e0f0567dd4f30662e8e1bc57266ce562be` | `app/beyo_manager/routers/README.md` |
| `ec4df9132c00370b7ee99423db4f61f06a38000f46d8d3d75c55a7c544e0e3e6` | `app/beyo_manager/models/tables/README.md` |
| `1c3803663f5c91b6a6bbdc1c1411581fdf04c90093e6df7301dd2164c409e85a` | `app/beyo_manager/models/tables/client_id_prefix_map.md` |
| `fd7ce416c65a49af5fdcefcc314e07e9c44fc1a8ee6bcdf92b533d9fe5cfc2d2` | `app/beyo_manager/models/tables/items/README.md` |
| `11a606c71fb231a4740dff73d3f05820813046a676718a9f530d514d13534dc8` | `app/beyo_manager/models/tables/tasks/README.md` |
| `22a87e61138a701be35cb86a9fbb5fbd5c40dd67a9ca6fe5296edf0549a03d6c` | `app/beyo_manager/models/tables/item_economics/production_cost_basis_version.py` |
| `529180bb2cd22d1a24294c89bd16d327cbe940ca5932d334b013bc2a67eab320` | `app/beyo_manager/models/tables/item_economics/item_cost_evaluation.py` |
| `8acceac6bc6c9ecbe7f5257c582d2255568e72c6f1bf2fe641d35c6515805407` | `app/beyo_manager/models/tables/item_economics/item_cost_evaluation_term.py` |
| `02636b7a6981943b6e690a94f0d01d04f6fdb775585fff9ea0e03a63c8129c4d` | `app/beyo_manager/models/tables/item_economics/cost_model_term.py` |
| `f2a2b742068d4a6764179d7f978fa03cdc427af69114962a9935a442bfd9b258` | `app/beyo_manager/models/tables/item_economics/item_cost_result.py` |
| `d81cb4938c3d80415b6111bfa6860350a171398f6b03a095d068fe23e88efdcd` | `app/beyo_manager/services/queries/item_economics/get_economics_configuration_status.py` |
| `038f609de3751ba1706eb36519e25ef4ef2ee6c5714b62f4ce4e2219203d11c1` | `app/migrations/versions/be9dfe42a035_drop_legacy_item_money_columns.py` |
| `af953a9251938d8480d089aeb390adac7e7fb860e9061d831dc40e157d58c91b` | `app/tests/unit/services/queries/item_economics/test_phase8_serializers.py` |
| `d9311a6e9951a447d607706b665851c5b8094f4bea64ade741df3b665ed069c1` | `app/tests/integration/models/item_economics/test_item_economics_schema.py` |
| `e6de1f0dc3ed3dbedf2061c149085f79218a2d33928e12e158d0f2c8b2a733ef` | `app/tests/integration/services/commands/item_economics/test_phase8_status_results.py` |
| `9b45bc20459e7a88ca79127c5213b986f54fedb140d2f4a616aab8935fd64055` | `app/tests/integration/services/commands/shopify/test_process_shopify_products_integration.py` |
| `d86260ffd0828fc549bba649a496feaa1a59a9247ed56dc14233347ef995d086` | `docs/architecture/.../plans/phase_9_docs_and_drift.md` (Review log entry) |
| `23eb666119478253acd5fa33d79e854e5f3fed4c7adf40f5ec0947ffaad70ee1` | `docs/architecture/.../master_plan.md` (row 9 only) |

### Frontend — `ManagerBeyo-app/frontend` (separate repo, **uncommitted**)

| sha256 | file | edit |
|---|---|---|
| `7ace7e17284a1e9914df10b749d331047627c9c15c5e9936e8d32e5ff19d5eaf` | `docs/architecture/backend/routers_endpoints/README.md` | twelve rows annotated at `:1918-1920`, `:1976-1978`, `:2078-2080`, `:2475-2477` |
| `306694cca5d66b4ca1d971b3aa484aae73e0224f426fe45323c3f9ae8d56a0b6` | `docs/architecture/backend/tables/README.md` | `:437` `create_type=False` → `True`; `:467-469` deleted |

`git status` in that repo shows exactly these two files modified and nothing else.
**Left uncommitted deliberately** — the standing checkpoint authorisation is worded for
this project's repo, and a phase-9 commit message in the frontend's history is the
coordinator's call, not mine. Flagging it so the closeout does not lose them.

### Application_contracts — `/Users/davidloorenz/Desktop/Developer/Application_contracts`

| sha256 | file | edit |
|---|---|---|
| `30c0fc7f071a239dd5e4eafa15774eb125c0f2e8f092f684fa24fc1f3f0e9d6b` | `planning/task/task_step_models.md` | `total_working_seconds` + `total_cost_minor` added to the column list; the mixin lines now name what each supplies; a new "Time and cost aggregate semantics" block carrying the two-cost divergence and the ADMIN/MANAGER audience |
| `e60d2e3dc82052a0ff45e6f1d507bffea8666e3fbf361ceb9e4269b2c4b6282a` | `planning/item/item_models.md` | `:104-107`'s "Value and cost semantics" block rewritten for the valuation model |

**`planning/` is gitignored in that repository** (`.gitignore:8`), so `git status` there
shows nothing and the perimeter is verifiable by hash and mtime only. Its one tracked
modification (a deleted PNG under `backend/tests/bootstrap_tests/`) is pre-existing and
not mine.

### Tool-recorded state

One `archgraph_apply_changes`, one node, no relationships, no source links:

- `decision-money-audience-admin-manager-only` (type `decision`, confidence 0.90, tags
  `security-boundary` / `roles` / `money`), four evidence entries:
  `domain/tasks/serializers.py:150-155` (`include_monetary_step_fields`) and `:158-160`
  (the keyword-only, no-default parameter); `routers/api_v1/item_economics.py:133-144`
  (`_run_budget_status` selecting an entirely different service by role);
  `domain/item_economics/serializers.py:197-207` (the enumerated money-free worker
  result).
- Graph before `452befdb…` → after `7dcdb9b01f03611f0605b77622963e205e9073ecf0cca7f3d988e31a2fb3c36f`;
  174/260 → **175/260**; pending 0 → 1 (this node, awaiting the coordinator's
  post-approval pass); `.archgraph/architecture.yml` sha256 equals the revision string.

### Databases touched

The configured development database only, read/write by the integration suite as usual;
left at head `c1d2e3f4a5b6`, verified by querying `alembic_version` after the full run.
No disposable database was created, no migration was executed, no destructive
verification was performed.

---

## Judgment calls

1. **P16's publication order.** P16 and F20 read slightly differently about where
   `infeasible`/`ok` belong. Followed P16 (the GOVERNING block): the twelve **values**
   are verbatim from `enums.py:15-27`; the **evaluated branch** is published separately
   (branch A — a current committed evaluation exists → `infeasible` if the allowance ≤ 0
   else `ok`) from the ten-row readiness precedence (branch B —
   `item_missing_major_category` → … → `not_evaluated`). This is what §11A.4/§7C.3
   actually define: group 1 is a branch condition, not a precedence step. It satisfies
   F20's "group 1 evaluated first" too, so the two amendments do not in fact conflict.
   Published identically in `states.md` and the operational handoff's §6, and the
   accuracy arbiter asserts §6 names exactly the twelve values and nothing else.
2. **P5(a)'s nine index rows link to the folder guide**, not to a `#anchor`. P5 records
   that the per-table column sections are not added this phase, so an anchor link would
   resolve to nothing. `- [cost_model_terms](item_economics/README.md)` and so on. Index
   is now 71 rows (62 + 9).
3. **P12's four mirror ranges are request-body rows, not response rows.** Verified
   against the headings: `PUT /api/v1/items`, `POST /api/v1/items/find-or-create`,
   `PATCH /api/v1/items/{client_id}`, `PUT /api/v1/tasks`. The three keys are therefore
   still accepted and still rejected, so deleting the rows would have been wrong.
   Annotated all twelve "present, always rejected with 422 `ITEM_MONEY_MOVED`", matching
   the treatment P15 mandates for the backend's own PUT `/api/v1/tasks` table.
4. **P4 item 7 (N14) is one assertion converted, not literally one line.** The ordered
   comparison at `:179` sits inside a dict-equality assertion, so repairing it needs the
   `pop`-and-compare-as-set idiom the file already uses one line above for the event ids.
   Net +2/−1 lines in one contiguous region.
5. **P9's `:61` deletion took its heading with it.** Deleting only the paragraph leaves
   `### Timing fields` with no body.
6. **P15's `shopify_preorder` is documented as nested leaf rows**
   (`shopify_preorder.product.*`, `shopify_preorder.inventory[].*`), following the
   table's own `item_upholstery.*` convention for a nested model rather than a bare
   `object` row.
7. **P19's generic ordering sentence lives in `api.md`.** The revision-naming operations
   line is in `docs/deploy/RUNBOOK_20260815_item_money_column_drop_ordering.md`; the
   domain doc's generic rule (no revision named) sits in the `api.md` section that
   already discusses the removed money keys, which is the only place in the folder a
   reader meets the topic.
8. **P14's node type is `decision`.** The money audience is an architectural policy with
   a rejected alternative (a defaulted include-money flag on one shared serializer) and a
   contested scope (SELLER excluded alongside WORKER); `infrastructure` describes
   something that provides a runtime capability, which this does not.
9. **The eleven annotations required an import.** Each of the five model modules gained
   `from decimal import Decimal` on line 2, matching the `user_work_profile.py:2`
   precedent — none of them carries `from __future__ import annotations`, so
   `Mapped[Decimal]` is evaluated at class creation. Nothing else changed: `ruff check`
   clean on all five, `import beyo_manager.models` succeeds, and the whole item-economics
   test scope (519 nodes) passes.
10. **P18's `:166` carries a `//` comment.** The example is a JSON block with no comment
    idiom in that file, and pure JSON cannot express "this key is absent for some roles".
    A trailing `//` note on the value line is unambiguous in an API-doc example; the
    field table at `:393` carries the full statement.

---

## Drift found and FILED, not fixed

Every P-enumeration is a line-range fence. These are real and outside it.

1. **`endpoint-item-economics-status`'s archgraph source link is now stale.** Its anchor
   spans `get_economics_configuration_status.py:12-64`, and P4 item 4 (4B N3) edited
   lines 39 and 49 inside that span. The span is still correct — the function is
   `:13-64` — so this is content drift, not span drift, and acknowledging it belongs to
   the human-authorized maintenance channel. This is the whole of the graph's
   `staleNodeCount: 1`.
2. **`tests/integration/services/commands/item_economics/test_phase8_reviewer_r1_probe.py:22`
   carries a pre-existing ruff `F401`** (`ItemMajorCategoryEnum` imported but unused). It
   is the only ruff error anywhere in the item-economics tree and the file is untouched
   by this phase (absent from `git diff --name-only`). One-line fix for whoever next
   opens that file.
3. **`routers/README.md`'s PUT `/api/v1/tasks` table over-states five Required flags.**
   `return_source`, `item_location`, `return_method`, `fulfillment_method` are all
   `| None = None` and `priority` has a default (`tasks.py:182-189`), yet all five read
   Required=**Yes**. Also `notes[].content` is typed `object` where the model declares
   `list`. Outside F16's enumeration.
4. **The same README omits the three legacy money rows from the *items* endpoints'
   request tables** (`PUT /api/v1/items`, `POST /api/v1/items/find-or-create`,
   `PATCH /api/v1/items/{client_id}`) — the identical drift F16 enumerated for the tasks
   endpoint, which P15 scoped to tasks only. A frontend reader of those three sections
   still concludes the keys are simply unknown.
5. **`Application_contracts/planning/item/item_models.md` is internally inconsistent
   after P13's rewrite.** `:29-31` still lists `item_value_minor` / `item_cost_minor` /
   `item_currency` as live columns, `:58-63` still documents `item_currency_enum` for
   them, `:203` still asks "should item_currency default from workspace settings", and
   `:54`/`:97` still say `STALL`. P13 enumerated `:104-107` only, so the rewritten block
   now contradicts the column list four sections above it. Worth a follow-up.
6. **`models/tables/tasks/README.md`'s file table omits three tables in the folder** —
   `task_customer_coordination.py`, `task_post_handling.py`,
   `task_step_acknowledgment.py`. Pre-existing.
7. **`models/tables/README.md:24` still indexes `issue_category_configs`**, dropped by
   `99accdeba8b9`. Recorded as out of scope by P5 and untouched.
8. **`client_id_prefix_map.md:56-62` keeps the pre-existing StaticCost / SkuTemplate /
   Shopify\* ordering violation.** Recorded by P11 and untouched — the nine new rows were
   sorted in without resorting the file.

---

## For the coordinator to fold upstream

- **§10's suite baseline** is now 2249 / 23 / 1 = 2272 selected (2273 collected). Left
  unedited: §10 records baselines at closeout, and phase 9 is not approved yet.
- **The frontend repo's two files are uncommitted** (see perimeter). They need either a
  commit in that repo or an explicit record that they ship with the frontend team's next
  change.
- **P22 items this session could already tick**, recorded in the Review log: §13's
  living-docs and archgraph-delta clauses are both discharged in this one change; the
  post-v1 handoffs are recorded (squash seed now carries Finding 8's `checkfirst`
  posture with its rationale, §11 carries F14's four uncovered filter sites and the N11
  residue research, §7:560-564 carries the bridge-validator removal, the phase-7 ival
  residue row stands); all five formerly-UNROUTED census rows ended in a task (7 → P5,
  8 → P4 item 8, 30 → P20) or a recorded disposition (10 → P21, 11 → P1); and the
  projection gate did not demote (the r0 ledger was not empty), moot on the last phase.
- **Drift items 1–8 above** each need a destination: item 1 to the maintenance channel,
  items 3–5 plausibly to a single follow-up documentation pass, items 2 and 6–8 to
  whoever next touches those files.

## Reproducing the numbers

```
cd /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app
PYTHONPATH=. python3 -m pytest -m 'not e2e' -q          # 2249 / 23 / 1
PYTHONPATH=. python3 -m pytest tests/unit/docs tests/unit/routers/test_phase9_item_economics_route_mirror.py \
    tests/unit/services/queries/item_economics/test_phase9_committed_filter_structure.py -q   # 65
python3 -m ruff check <the fifteen touched .py files>   # All checks passed!
```
