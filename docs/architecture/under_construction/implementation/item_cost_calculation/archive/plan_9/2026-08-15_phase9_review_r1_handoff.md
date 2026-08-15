---
plan: phase 9 (living docs & drift routing — the LAST phase of v1)
role: review
round: 1
verdict: APPROVED
date: 2026-08-15
actor: Claude Opus 5 / plan-reviewer
---

# Phase 9 review r1 — handoff

## Verdict: **APPROVED**

**0 blocking / 4 should-fix / 7 notes.** The prose holds. I read all four
`docs/domains/item_economics/` files and both frontend handoffs sentence by sentence
against the shipped code, and every load-bearing claim I could check is true: the
twelve-value vocabulary and its branch structure, the ten-row readiness precedence, the
handler's admission table over all eight task states, the four emission points, the
event payload and the audit vocabulary, every payload key catalog in `api.md` and both
handoffs, the exact `ITEM_MONEY_MOVED` and `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`
messages, the six auto-commit outcomes, the two-call create→budget-status flow, the
`quantity`-does-not-participate claim, the eight-endpoint `total_cost_minor` census, the
nine read surfaces, both contract divergences, the deploy-ordering hazard.

The four should-fix findings are all **outside** the six documents P9R-1 fences as
blocking. Three are one-line corrections; the fourth is the implementer's own filed
drift item, verified real. **S1 lands in the frontend repo's two UNCOMMITTED files** —
so it can be fixed at zero cost during the same closeout step that decides whether those
files get committed at all. That is why this is an approval and not a fix cycle.

Suite re-run independently: **2249 passed / 23 failed / 1 deselected = 2272 selected**,
and the 23-failure set is **set-identical** to the phase-1 recorded baseline
(`plans/phase_1_worker_money_redaction.md:270-282`), verified by sorted `diff` — empty.
+65 reconciled exactly (8 + 50 + 4 + 3, counted per file). `ruff check` clean on all
fifteen touched Python files. `alembic check` reports **exactly** the three pre-existing
drifts — no fourth entry, so the eleven annotations are proven INERT. DB left at head
`c1d2e3f4a5b6`; no migration ran.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Should the frontend's copy of the API tables be fixed before it is committed?

**Question:** Fix four rows in the frontend repo's mirrored API tables before deciding
whether to commit those two files — yes, or commit as-is and fix later?

**Story:** A frontend developer opens the task-creation section of the mirrored API docs
next week to remove the old money fields. The `item_currency` row tells them the field is
**required** *and* that sending it always fails with a 422. Both cannot be true, so they
either stop and ask, or they guess. If they guess that the field is genuinely required,
they keep sending it and every task creation from the new form fails the moment a user
picks a currency — the exact live risk the operational handoff warns about on its first
page.

**Branches:**
- **Fix first, then commit** — four cells change `Yes` → `No`, one clarifying sentence per
  table; the developer reads one consistent story.
- **Commit as-is** — the contradiction ships into the frontend's history and the fix
  becomes a second change someone has to remember.

**Recommendation:** Fix first — the files are still uncommitted, so the correction costs
one edit and no history, and the row it corrects is the one a developer acts on.

**On silence:** The gate holds on this card only; phase 9 is approved regardless. The two
frontend files simply stay uncommitted, which is where the implementer left them.

**Trace:** finding S1; plan P12; implementer handoff "Frontend — uncommitted".

---

## Findings

### Blocking (0)

None.

### Should-fix (4)

#### S1 — the frontend mirror's `item_currency` rows say "required" and "always rejected" in the same row, and the twelve annotations carry no clarifier

`frontend/docs/architecture/backend/routers_endpoints/README.md:1920`, `:1978`, `:2080`,
`:2477`.

Two defects on rows this phase deliberately rewrote:

1. **Requiredness is wrong.** All four `item_currency` rows read Required=**Yes**. The
   request models declare `item_currency: ItemCurrencyEnum | None = None`
   (`services/commands/items/requests/__init__.py:207,264,484`;
   `services/commands/tasks/requests/__init__.py:39`). Combined with the new "always
   rejected" annotation the row describes an unusable endpoint. The backend's own
   equivalent row was corrected to `No` in this same change
   (`app/beyo_manager/routers/README.md:2670`), so the two artifacts now disagree with
   each other.
2. **"present, always rejected" is imprecise and, in the mirror, unaccompanied.**
   `reject_legacy_item_money_values` (`services/commands/items/requests/__init__.py:14-17`)
   refuses only **non-null** values; present-with-null passes and is ignored. The backend
   README states this precisely one line below its table (`:2722`) and the operational
   handoff states it precisely at §1.2 (`:54`). The mirror carries the terse annotation
   alone across all twelve rows.

Authority: intention §10A.3 / master plan §6.4 (the bridge's exact contract); plan P12.

**Correction:** set the four `item_currency` Required cells to `No`; add the one-sentence
clarifier beneath each of the four mirror tables (or reword the annotation to "non-null
value rejected with 422 `ITEM_MONEY_MOVED`"). See owner card 1 for the sequencing.

#### S2 — the lifetime endpoint returns `terms: []` on every episode, and no document says so

`get_item_lifetime_economics.py:88` calls `serialize_item_cost_evaluation(evaluation, [])`,
so every episode's `evaluation.terms` is an empty array. Meanwhile `api.md:414` publishes
`terms` as an evaluation field, `api.md:461` states "Each row carries its `terms`" for
`GET /tasks/{id}/evaluations`, and the operational handoff §4.1 (`:284-286`) instructs the
frontend to "render them as the 'how this number was reached' drill-down". Neither
`api.md`'s `GET /items/{item_client_id}/economics` section (`:601-634`) nor the handoff's
§5.2 (`:465-494`) mentions the difference. A lifetime drill-down built on the §4.1
instruction shows an empty breakdown and no error.

Authority: plan P1 ("payload catalogs → `api.md`"); plan P6 (response envelope, verbatim
keys, per route).

**Correction:** one sentence in each place — "each episode's `evaluation` carries
`terms: []`; fetch `GET /tasks/{task_id}/evaluations` for the term breakdown."

#### S3 — `05_errors_local.md`'s pydantic rule is unqualified and contradicts the shipped tree

`architecture/05_errors_local.md:114`: "**Pydantic-side validators raise the repo's
`DomainError`, not `ValueError`.**"

`raise ValueError` inside pydantic validators is pervasive and correct across at least
twenty request modules, including this project's own —
`services/commands/item_economics/requests/__init__.py` (5 sites, e.g. "name must not be
blank") and `services/commands/tasks/requests/__init__.py:61` ("item.currency is required
when an inline item price is provided", which the operational handoff §9 publishes as a
plain schema 422 with no identity). None of these is a defect.

The rule's own rationale names what is actually at stake ("destroys the leading-token
contract"), and the file's own §"When an identity is required" (`:77-86`) already supplies
the missing qualifier — "A plain sentence with no identity is correct for a one-of-a-kind
failure the client can only surface verbatim." The bolded headline drops it. This is the
file P20 called "what future agents read BEFORE writing code"; as written it licenses a
sweep that would change 422 payload shapes across the app.

Authority: charter project-affordance rule (contracts are authoritative for how to write
code); the file's own `:77-86`.

**Correction:** qualify the sentence — "An error a client must **branch on** — i.e. one
carrying an IDENTITY — is raised as the repo's `DomainError`, never as a `ValueError`,
because pydantic's field-locator prefix destroys the leading token. A plain schema
`ValueError` remains correct for a non-branchable field error."

#### S4 — `Application_contracts/planning/item/item_models.md` is now internally self-contradictory

The implementer's filed drift item 5, **independently verified and confirmed real**:
`:29-31` still lists `item_value_minor` / `item_cost_minor` / `item_currency` as live
columns; `:58-63` still documents `item_currency_enum` "for current operational scope";
`:203` still asks "Should item_currency default from workspace settings when value/cost is
provided?"; `:54` and `:97` still say `STALL` where the enum says `STALLED`. P13's new
block at `:104-107` states the columns are dropped. Before this phase the document was
uniformly stale; it is now stale **and** self-contradicting, which is harder for a reader
to resolve than either end state.

The implementer was **right** not to widen the fence — P13 enumerated `:104-107` and
filing beat silently expanding scope. The residue is nonetheless a real defect in a live
cross-repo contract and needs a named destination rather than a drift line.

Authority: charter artifact map (a needed change is made in its home artifact and flows
down); plan P13. See lesson L1.

**Correction:** a follow-up pass over the four sibling sites in the same file.

### Notes (7)

- **N1 — P-d's declared red set is incomplete.** Re-running the probe (re-adding
  `consumed_cost_minor` to `_serialize_result`'s worker branch) reddens **three** nodes,
  not the two declared: the third is
  `tests/unit/services/queries/item_economics/test_phase8_serializers.py::test_worker_result_serializer_has_no_monetary_fields`.
  Charter L8 — a mutation declaration is checked against the run that produced it. The
  omission is in the safe direction (a pre-existing arbiter also bites, which is good
  news), but the declaration is not what the run shows.
- **N2 —** `05_errors_local.md:11` cites `errors/base.py:3-10` for a block that begins at
  `:1`. Inherited from master plan §6.4's own wording; cosmetic.
- **N3 —** `05_errors_local.md:30-32` enumerates the class → `http_status` map and omits
  `ShopifyProductLookupAmbiguousError` (`errors/external_service.py:57`, 409). Outside this
  domain, but the enumeration reads as complete.
- **N4 —** Drift item 7's citation `models/tables/README.md:24` has shifted to `:26`
  because P5's own nine index rows were inserted above it. Re-anchor when picked up.
- **N5 — judgment call 10 assessed: acceptable.** The `//` in the JSON example at
  `HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md:166` sits in a **response**
  example — nobody transmits it — and a copy-paste produces a loud parse error, not a wrong
  belief. The field table at `:393` carries the full statement. No change needed.
- **N6 — the identity arbiter is one-way by design; record it as such.**
  `test_no_document_names_an_unregistered_error_identity` catches invented identities but
  not omitted ones, and `_IDENTITY_TOKEN` cannot see the abbreviated `` `_REQUIRED` ``
  form the docs use for the composed-identity families. Both are within P15's stated
  criterion ("every identity **in the handoff** greps to the shipped artifact"); recorded so
  a later phase does not read this as coverage in the other direction.
- **N7 — the squash seed has no single home.** P22 item 2 speaks of "the squash seed
  (Findings 1–8)", but those entries are distributed across `planning/owner_decisions.md`,
  phase plans and Review logs; no consolidated ledger exists. The implementer correctly
  flagged placement as the coordinator's at closeout; confirming it is genuinely
  unconsolidated, not merely unlocated by me.

---

## Prose-verification record — documents read in full, sentence by sentence

| Document | Read | Outcome |
|---|---|---|
| `docs/domains/item_economics/README.md` (339 ll.) | full | accurate |
| `docs/domains/item_economics/api.md` (634 ll.) | full | accurate except S2 |
| `docs/domains/item_economics/events.md` (84 ll.) | full | accurate |
| `docs/domains/item_economics/states.md` (178 ll.) | full | accurate |
| `HANDOFF_..._operational_20260815.md` (730 ll.) | full | accurate except S2 |
| `HANDOFF_..._configuration_20260815.md` (485 ll.) | full | accurate |
| `docs/deploy/RUNBOOK_20260815_item_money_column_drop_ordering.md` (47 ll.) | full | accurate |
| `architecture/05_errors_local.md` (118 ll.) | full | S3, N2, N3 |
| `architecture/46_serialization_local.md` (65 ll.) | full | accurate |

### What I re-derived against the code, by claim

**`states.md` / operational handoff §6 — the vocabulary and its order (P16, judgment call 1).**
`enums.py:15-27` carries exactly twelve members and the published **values** are verbatim.
`configuration.py:14-20` (`CONFIGURATION_FAILURE_PRECEDENCE`) and `:33-39`
(`ITEM_READINESS_PRECEDENCE`) are the two ordered sequences, and branch B's ten rows are
their concatenation in order. Intention §11A.4 as amended by §7C.3 defines group 1 as *"A
current committed evaluation exists"* — a **branch condition**, not a precedence step.
Judgment call 1 is **correct**, and P16 and F20 genuinely do not conflict: publishing the
evaluated branch separately satisfies both. The null-numerics rule and the
`percent_consumed`-for-`infeasible` clause match §11A.4's closing rule; the `preview`
carve-out matches §11A.5 R13-1(b).

**`states.md` — the result row's lifecycle.** `_ADMITTED_STATES` in
`process_item_cost_result.py:28-36` is exactly `{WORKING, READY, RESOLVED, FAILED,
CANCELLED}`; `TaskStateEnum` has exactly eight members, so the admission table is total.
Soft-deleted task and no-current-committed-evaluation both return without writing
(`:52-56`, `:70-75`). The four emission points are real and their conditions exact:
`_task_state_transitions.py:55-59` (READY), `:113-117` (reopen), `resolve_task.py:104` /
`fail_task.py:104` / `cancel_task.py:104`, and `process_step_transition.py:87-97` gated on
`task.state == READY or in TERMINAL_TASK_STATES`. The `ON CONFLICT (task_id) DO UPDATE` and
the `computed_at`-excluded replay identity match `:126-129` and the `update_columns` set.

**`events.md`.** One event, built at `commit_item_cost_evaluation.py:387-392` via
`build_workspace_event(task, …, extra={"evaluation_id": …})` — so `client_id` is the
**task's**, as documented. Projections never emit (guarded on
`kind is ItemCostEvaluationKindEnum.COMMITTED`). The audit vocabulary table is exact: all
twelve `<entity>.<action>` names grep to their commands, and
`item_economics:evaluation-committed` is absent from the audited-event registry. The
consumed-event payload is the frozen `ItemCostResultPayload` and nothing else.

**`api.md` + both handoffs — the payload catalogs.** Every published key list checked
field-by-field against `domain/item_economics/serializers.py`: cost group (8 keys),
section (8), basis version (15), cost-model version (10 + terms), cost-model term (11),
valuation (10), preview (3), evaluation (25 incl. `error`), evaluation term (9),
budget-status manager (14) and worker (9), the two `result` shapes (9 / 5), lifetime
(`episodes` / `totals` / `episodes_pagination`). All exact. The manager/worker absence
list at `api.md:584-587` and handoff `:440-443` is exact.

**Role gates and the route census.** The router carries exactly 23 endpoints; exactly one
(`GET /tasks/{task_client_id}/budget-status`) admits `[ADMIN, MANAGER, WORKER, SELLER]`
and the other 22 are `[ADMIN, MANAGER]`. 13 + 10 = 23, and each hand-written tuple matches
a real `@router.<verb>` path.

**The `total_cost_minor` census (`api.md:40-58`).** Matches intention §11A.2's round-5
eight-endpoint correction row for row, including the SELLER column (rows 3, 4, 6, 7 admit
ADMIN/MANAGER/WORKER only) and rows 5 and 8 keeping money deliberately.

**Configuration-status shape.** `get_economics_configuration_status.py:39-62` produces
exactly the documented JSON, keyed by `ItemMajorCategoryEnum` (`wood`, `seat`), with
`first_failure` null iff `evaluable`. P4 item 4's removal of `and not version.is_deleted`
at `:39`/`:49` is safe: all three loaders already filter `is_deleted.is_(False)` at
`:15-36`.

**Request-shape claims in the configuration handoff.** Every constraint checked against
`services/commands/item_economics/requests/__init__.py`: `fixed_monthly_cost_minor` `gt=0`;
`monthly_paid_hours` `gt=0`; `planning_utilization_percent` `gt=0, le=100`; `percent_value`
`ge=0, le=999.999`; `fixed_amount_minor` `ge=0`; `label` `max_length=255`; `major_category`
required on create and optional on update; `source` a three-value `Literal`;
`cost_per_worker_minute_minor` accepted nowhere. **A frontend developer could build the
settings screen from this document alone** — it carries the build order, the per-category
readiness model, both dual-path conflict identities with the token-not-status rule, the
three term shapes as a decision table, and the currency trap.

**Operational-handoff behaviour claims.** `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`'s message
is verbatim (`create_task.py:339-341`) and is raised **outside** the `begin_nested()`
savepoint, so §9.1's "the whole task creation is rolled back" is right. The auto-commit sits
inside the savepoint under a broad `except Exception` that only logs (`:353-368`), so §9.2's
"best effort… silent from the response's point of view" is right. `quantity` appears nowhere
in the domain. The task history entry is `field_name="item_cost_evaluation"` with
`_figures()`'s four headline values and a `None` `from` on first commit
(`:71-79`, `:364-379`). The §1.2 bridge sentence is precise where the mirror's is not (S1).

**`README.md`'s structural claims.** The two-payload-families disjointness test exists with
non-vacuity guards on **both** sides (`test_phase8_reviewer_r1_probe.py:700-714`). Nine
tables in `models/tables/item_economics/`. `_common.py` holds exactly the valuation-chain
writer and the preview-input loader. INV-G3's index
(`uix_production_cost_groups_major_category_active`) exists, so "structurally unreachable"
is accurate.

**The README/contract batch.** `ItemStateEnum` is `PENDING/STALLED/FIXING/READY`;
`item_issue.py:42-44` carries exactly the three snapshot columns the replaced section names;
`item_upholstery_requirement.py:44` is `create_type=True` and `item.py:25` has
`item_state_enum` as its only `create_type=True` — so both corrected claims are right in
both the backend README and the frontend mirror. The tables index is 71 rows. The nine
prefix-map rows are correctly sorted in and the file is not resorted (a full alphabetical
sweep finds only the pre-existing AppUpdate\*, StaticCost/SkuTemplate/Shopify\* and
WorkingSection\* blocks, none touched). The D-4 line is exact:
`transition_step_state.py:150` guards on `step.state in TERMINAL_STEP_STATES` only, the
three terminal task commands do not touch steps, and the re-emit is the stated
consequence-handler. All `task_history_record` references are gone. `05_errors.md:17,76`
really do define `code: str` and `STATUS_MAP`, and `46_serialization.md:5-20` really does
mandate router-owned serialization — both divergences are stated against the real canonical
text, not a strawman. Both `_local` files follow the repo's `> Extends:` convention. The
`docs/README.md` domain-map row is exactly what `23_documentation.md:410` mandates, and the
README follows the `:132` template.

**P4's fence.** The checkpoint contains 34 paths: the 33 declared documents/code files plus
`.archgraph/architecture.yml` (declared under tool-recorded state). **Nothing outside the
allow-list.** Each of the nine items landed as specified, including the docstring
(`Revises: 5420acc6a7b3` now equals `down_revision`), N14 at `:179` as a set comparison, and
P7's C5 repair closing the task **before** the first run so both lifecycle columns carry
real closed values and the ten-column equality still holds — with a live sole-cause guard
(`calculate_consumed_cost_minor(…, new_rate) != first.consumed_cost_minor`).

**P14's node.** All four evidence spans re-read and accurate:
`domain/tasks/serializers.py:150-155` is exactly the predicate, `:158-160` covers the
keyword-only signature, `routers/api_v1/item_economics.py:133-144` is exactly
`_run_budget_status`, `domain/item_economics/serializers.py:197-207` is exactly the
money-free branch. Type `decision` is the right call (judgment call 8): it records a
rejected alternative and a contested scope, which `infrastructure` does not describe.

**Judgment call 3 (frontend mirrors) is correct on its own terms.** All four cited ranges
are **request-body** tables (`PUT /api/v1/items`, `POST /api/v1/items/find-or-create`,
`PATCH /api/v1/items/{client_id}`, `PUT /api/v1/tasks`), so the keys are still accepted and
still refused; deleting the rows would have been wrong. The defect is in the annotation's
wording and the untouched Required column, not the annotate-not-delete decision — see S1.

**Judgment calls 2, 4, 5, 6, 7, 9 verified correct.** The nine index rows link to a real
`item_economics/README.md` (25 lines, exists), so no anchor resolves to nothing. `:179` needed
the pop-and-compare-as-set idiom. Deleting `### Timing fields` with its paragraph is right.
`shopify_preorder` as nested leaf rows follows the table's own `item_upholstery.*` idiom.
The revision-naming line is in `docs/deploy/` and `api.md:82-85` states the generic rule
with no revision named. The five `from decimal import Decimal` imports are genuinely
required — none of the five modules carries `from __future__ import annotations`, so
`Mapped[Decimal]` is evaluated at class creation.

**The 65-node arbiter suite, read hard (P9R-2).**

- The **identity census is exactly right**, counted by hand against master plan §6.4:
  4 selection + 7 inputs + 1 rate + 4 chain races + 3 guarded deletes + 2 valuation +
  1 membership + 3 config uniqueness + 2 category + 1 commit-path
  (`ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY`) + 1 inline birth + `ITEM_MONEY_MOVED` =
  **30 literal**; the two admission families × three suffixes = **6 composed**. The audit
  vocabulary and the migration pre-flight `RuntimeError` are correctly excluded.
- The **13 + 10 route sets are the real 23**, each verified against a live decorator.
- **Heading-level equality** (`_heading_routes` matches only lines starting `#`) is exact-set,
  not containment, in both directions — a missing heading and an invented one both bite.
- **Path normalisation** collapses `{param}` and worked-example ids (`_CONCRETE_ID`) so the
  check is on route shape; the known-set includes `""` and `"/"` for bare-prefix mentions.
- **C1's `parents[4]` anchor resolves correctly** from the test's real location:
  `backend/app/tests/unit/docs/` → `[0]`=docs, `[1]`=unit, `[2]`=tests, `[3]`=app,
  `[4]`=backend → `backend/docs/domains/item_economics`. Confirmed by running it.
- **The whitespace normalisation does not let a reword pass** — proven, not assumed: probe
  R-g1 below.
- The **filter arbiter carries a non-vacuity guard** (`len(evaluation_statements) == 1`), so
  the clause assertions cannot be satisfied by some other statement, and selection is by
  compiled text rather than call ordinal as P3 required.
- The **route mirror is genuinely hand-written** and never derived from `router.routes`
  (phase-8 L5), with the count asserted off the table rather than independently.

---

## Mutation ledger — all re-run from the declared mutant bytes

Scope: `tests/unit -m 'not e2e' -p no:randomly` (1366 passed / 8 pre-existing failures),
diffed both ways against a baseline capture of that same scope — reproducing the
implementer's declared method.

### The three named mutations (P3) — **all three reproduce exactly**

| # | Site | Mutant sha256 (mine) | Declared | Observed red | Restored |
|---|---|---|---|---|---|
| M1 | `get_task_budget_status.py` delete `:107` | `b66a7fce09a60b0d…` | `b66a7fce09a6…` **match** | exactly `…::test_committed_current_filter_is_present_in_the_compiled_select[get_task_budget_status.py:106-108]`; zero collateral; zero baseline failures disappeared | `5f89e29b695ea13f` **match** |
| M2 | `get_task_budget_status_worker.py` delete `:31` | `258873a603b10530…` | `258873a603b1…` **match** | exactly `…[get_task_budget_status_worker.py:30-32]`; zero collateral | `011cf2ae76dde81f` **match** |
| M3 | `get_item_lifetime_economics.py` delete `:47` | `89a4d32613b1699f…` | `89a4d32613b1…` **match** | exactly `…[get_item_lifetime_economics.py:46-48]`; zero collateral | `1f26eecaaeeb6df1` **match** |

Per-site red only, exactly as P3 predicted: the worker service carries its own copy of the
filter, so M1 cannot reach it.

### Self-chosen probes re-run (P9R-3 asked for two; I ran both recommended)

| # | Probe | Result |
|---|---|---|
| P-c | rename `ITEM_COST_TASK_TERMINAL` → `ITEM_COST_TASK_ALREADY_CLOSED` in the operational handoff | reddens exactly `test_no_document_names_an_unregistered_error_identity[operational]`; mutant `98c52885957f97eb…` **matches** the declared value; restored `f3b036ba7dccb871` **match** |
| P-d | re-add `consumed_cost_minor` to `_serialize_result`'s worker branch | reddens **three** nodes: the two declared plus `test_phase8_serializers.py::test_worker_result_serializer_has_no_monetary_fields` (see N1). My mutant hash differs from the declared one because I chose my own insertion point within the same dict; restored `12d6e36a7a04074c` **match** |

### Reviewer-added probes — the arbiters nobody had falsified

| # | Probe | Expected | Observed |
|---|---|---|---|
| R-e | corrupt one route path in a configuration-handoff heading (`:196`) | exact-set equality must bite | reddens `…exactly_its_half_of_the_surface[configuration-13-routes]` **and** `…covers_all_twenty_three_routes`; restored `37f351fdd28d1565` |
| R-f | rename `currency_mismatch` → `currency_conflict` inside the operational handoff's §6 only | vocabulary equality must bite | reddens exactly `test_the_published_status_vocabulary_is_exactly_the_enum`; restored `f3b036ba7dccb871` |
| R-g1 | **reword** one word of the presentation rule ("computing" → "calculating") in `docs/domains/item_economics/README.md` | must bite | reddens exactly `…[intention-6A.4-presentation-rule]` |
| R-g2 | **rewrap** the same paragraph onto one long line | must **stay green** | 8 passed — the alarm distinguishes a rewrap from a reword, exactly as declared; restored `4790f91842be00ee` |
| R-h | inject `op.execute("DROP TYPE IF EXISTS business_task_type_enum")` into `90cdd23a828e`'s `downgrade` | P4 item 6's regex must bite | reddens `test_downgrade_static_proxy_is_exact` at the reuse assertion (`:210`) — phase-2 N8's fix is live, not decoration; restored `3fc5cd88367b8a7b` |

R-h is the one item in P4's allow-list whose bite the implementer did not demonstrate; it
holds.

---

## Numbers, independently measured

| Claim | Method | Result |
|---|---|---|
| 2249 / 23 / 1 = 2272 selected | one foreground `PYTHONPATH=. python3 -m pytest -m 'not e2e' -q` from `backend/app/` | **reproduced**, 147.37s |
| failure set byte-identical to the phase-1 baseline | extracted and sorted my 23 `FAILED` node ids; sorted the 23-item list recorded at `plans/phase_1_worker_money_redaction.md:270-282`; `diff` | **empty diff** |
| +65 reconciled 8 + 3 + 4 + 50 | `--collect-only` node count per file | docs 8, handoff-accuracy 50, route-mirror 4, filter-structure 3 = **65**; the four files together run 65 passed |
| eleven annotations INERT | `alembic check` | **exactly three** pre-existing drifts (`email_sync_states_connection_id_key`, `ix_step_state_records_ws_credited_entered`, `ix_step_state_records_ws_flagged_entered`). No fourth entry ⇒ metadata unchanged |
| eleven sites carry an explicit column type | read all eleven | every one is `mapped_column(Numeric(p, s), …)`; no `from __future__ import annotations` in any of the five modules |
| ruff clean on fifteen files | `ruff check` over the commit's 15 `.py` paths | **All checks passed!** |
| DB at head, no migration ran | `alembic current` before and after | `c1d2e3f4a5b6 (head)` |
| item-economics scope green | the whole domain scope (431 nodes) + subsumed by the full run | 431 passed; no item-economics test appears in the 23 |
| perimeter exact | `git show --numstat 4b648c0` | 34 paths = 33 declared + `.archgraph/architecture.yml` (declared as tool-recorded state). Nothing outside P4's allow-list |
| frontend repo untouched beyond the two files | `git status` + sha256 | exactly `7ace7e17284a1e99…` and `306694cca5d66b4c…`, still uncommitted |
| Application_contracts hashes | sha256 | `30c0fc7f071a239d…`, `e60d2e3dc82052a0…` — match; the repo's only tracked change is the pre-existing deleted PNG |
| graph | `archgraph_status` | 175 nodes / 260 edges, rev `7dcdb9b01f03…`, 1 pending, 1 stale, 0 diagnostics |

### The 8 filed drift items — each verified as a claim in its own right (P9R-7)

| # | Claim | Verified |
|---|---|---|
| 1 | `endpoint-item-economics-status` link stale, content drift inside a still-correct span | **real** — `staleNodeCount: 1`; the function is `:13-64` and the edit hit `:39`/`:49` |
| 2 | pre-existing ruff `F401` in `test_phase8_reviewer_r1_probe.py:22` | **real** — `ruff check` on that file: 1 error; file absent from the commit |
| 3 | five Required=Yes over-states + `notes[].content` typed `object` | **real** — `priority` has a default, the other four are `\| None = None` (`requests/__init__.py:221,225-228`); `content: list` at `:98` |
| 4 | the three items endpoints' request tables omit the money rows | **real** — 0 money rows in all three sections |
| 5 | `item_models.md` internally inconsistent after P13 | **real** — see S4 |
| 6 | `tasks/README.md` file table omits three tables | **real** — 0 mentions of all three |
| 7 | `models/tables/README.md` still indexes `issue_category_configs` | **real** — now at `:26`, not `:24` (see N4) |
| 8 | prefix-map ordering violation retained | **real** — StaticCost/SkuTemplate/Shopify\* out of order, item-economics rows all correct |

### P22 ticks — each claim checked

(1) §13's living-docs row ships as the contract-mandated folder **and** the archgraph clause
is discharged by the P14 node in the same change — **holds**. (2) The post-v1 handoffs: §11
carries F14's four uncovered filter sites **and** the N11 residue research — **holds**; the
bridge-validator removal is in §7's §10A.3 sequencing note (at `:567`, not the cited
`:560-564` — immaterial) — **holds**; the phase-7 ival residue row stands — **holds**;
**the squash seed's Findings 1–8 have no consolidated home** — see N7, which the implementer
had already routed to the coordinator. (3) All five formerly-UNROUTED census rows ended in a
task or a recorded disposition — **holds**. (4) The projection gate did not demote, moot on
the last phase — **holds**.

---

## Full write perimeter (this review session)

**Documents written (3):**

| Path | Nature |
|---|---|
| `handoffs/reviewer/2026-08-15_phase9_review_r1_handoff.md` | this file |
| `plans/phase_9_docs_and_drift.md` | Review log entry appended (layer 1 only) |
| `master_plan.md` | tracker row 9 only: REVIEWING → APPROVED |

**Code changed: none.** **Tool-recorded state: none** — `archgraph_status` and
`archgraph_get_node` are read-only; no `apply_changes`, no promotion, no adjudication. The
1 pending node and 1 stale link are left exactly as found for the human-adjudicated
closeout pass.

## Mutation-probe declaration

Every file below was mutated and restored **byte-identical**, verified by sha256 against the
pre-probe value; `git status` in `backend/` is clean at deposit time.

| File | Probes | Restored sha256 (prefix) |
|---|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py` | M1 | `5f89e29b695ea13f` |
| `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py` | M2 | `011cf2ae76dde81f` |
| `app/beyo_manager/services/queries/item_economics/get_item_lifetime_economics.py` | M3 | `1f26eecaaeeb6df1` |
| `app/beyo_manager/domain/item_economics/serializers.py` | P-d | `12d6e36a7a04074c` |
| `app/migrations/versions/90cdd23a828e_item_economics_schema.py` | R-h | `3fc5cd88367b8a7b` |
| `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` | P-c, R-f | `f3b036ba7dccb871` |
| `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_configuration_20260815.md` | R-e | `37f351fdd28d1565` |
| `docs/domains/item_economics/README.md` | R-g1, R-g2 | `4790f91842be00ee` |

**Database side effects:** the configured development database was read/written by the
integration suite in the ordinary way and left at head `c1d2e3f4a5b6`, verified by
`alembic current` after the last run. No disposable database was created, no migration was
executed (`alembic check` is read-only), no destructive verification was performed. **The
R-h probe mutated a migration's source text only** — it was never executed, and the test it
falsifies reads the source with `inspect.getsource`.

**Other repositories:** `frontend/` and `Application_contracts/` were read only; both are in
exactly the state the implementer declared.

---

## Carry-forward dispositions (v1 closure — P22)

| Item | Destination |
|---|---|
| **S1** four `item_currency` Required cells + the twelve-annotation clarifier | **coordinator's closeout, before the frontend-commit decision** — owner card 1 |
| **S2** lifetime `terms: []` undocumented | closeout doc pass (`api.md` §lifetime + operational handoff §5.2) — two sentences |
| **S3** `05_errors_local.md:114` qualifier | closeout doc pass — one sentence, same file |
| **S4** `item_models.md` sibling sites (`:29-31`, `:58-63`, `:203`, `:54`/`:97`) | post-v1 Application_contracts follow-up pass, together with drift item 5 |
| **N1** P-d declaration | recorded; no action (charter L8 lesson folded below) |
| **N2, N3, N4** citation/enumeration nits | next touch of each file |
| **N5** the `//` in the old handoff | **no action** — assessed and accepted |
| **N6** one-way identity arbiter | recorded in §11's only-if-cheap ledger, if the coordinator wants the reverse direction later |
| **N7** squash seed has no consolidated home | **coordinator's closeout** — create the ledger or name its home before v1 closes |
| 1 pending graph node (`decision-money-audience-admin-manager-only`) | **human adjudication**, coordinator's post-approval pass — I did not promote it |
| 1 stale source link (`endpoint-item-economics-status`) | human-authorized maintenance channel (link re-accept) — drift item 1 |
| The two uncommitted frontend files | **owner**, via card 1 |
| Drift items 2, 6, 7, 8 | next touch of each file |
| Drift items 3, 4 | single follow-up documentation pass over `routers/README.md` |
| Post-v1 handoffs: squash seed (Findings 1–8), N11 residue research prompt, bridge-validator removal (§7 §10A.3 note), §11's F14 entry, the phase-7 ival residue row | recorded and standing; the squash seed needs a home (N7) |

## Lessons for the plans

**L1 — a line-range fence over a document whose neighbouring sections assert the opposite
of the rewrite produces a self-contradictory artifact.** P13 fenced `item_models.md:104-107`;
the rewritten block now contradicts the column list four sections above it, the enum
section, and an open clarification question. Before routing a rewrite-in-place task, grep the
target document for the terms the rewrite invalidates and either widen the fence to that
contradiction set or record "partial rewrite accepted, residue filed" as the *intended* end
state — so the implementer is not left choosing between scope creep and shipping a document
that argues with itself. (Earned: S4. The implementer's fence discipline was correct; the
fence was not.)

**L2 — when a phase edits one column of a table row, the criterion names the row, and the
mirror gets the arbiter too.** P12 named row ranges; the implementer edited the Notes column
and left the Required column of the same rows contradicting the new annotation. The backend's
own copy of that table is guarded by P15's arbiter and by C4's route mirror; the frontend
mirror has no arbiter at all, which is why the same class of defect survived in one artifact
and not the other. A criterion that repairs a mirrored table should say which columns are in
scope, and mirrors that carry a contract deserve at least a grep-level arbiter.
(Earned: S1.)

**L3 — a one-directional arbiter declares its direction.** The handoff-accuracy suite proves
"nothing in the document is invented"; it cannot prove "nothing shipped is missing from the
document". That is exactly what P15's criterion asked for, but the test names and the
handoff's summary read as coverage. A one-way arbiter should say so in its own docstring, so
the next phase does not inherit false confidence. (Earned: N6, and S2 is the defect that
slipped through the unguarded direction.)

**L4 — a newly authored contract file is checked against the tree it will govern.** P20
produced the highest-leverage document in the batch, and its one unqualified sentence
contradicts ~20 request modules of correct existing practice. A contract amendment's
acceptance criterion should include one grep per normative rule, confirming the rule
describes the tree or explicitly states what it supersedes. (Earned: S3.)
