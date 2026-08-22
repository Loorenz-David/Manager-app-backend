---
plan: 4
role: review
round: 3
date: 2026-08-22
verdict: CHANGES_REQUESTED
actor: Claude Opus 5 (1M context) — independent reviewer
---

# Phase 4 — review r3 handoff (first external review, full checklist)

## Summary

Full checklist against C1–C9 and the semantic authorities. **The document is strong and
substantially correct**: every criterion is discharged, every numeric claim I traced
lands on the intention section that derives it, and the two most falsifiable graph
claims — the ones nobody had checked — hold **exactly** at source. The fix cycle's
perimeter is exactly as declared.

**Verdict: CHANGES_REQUESTED — 0 blocking, 2 should-fix, 3 notes.** Both should-fix
findings are in the published deliverable, both are one-to-three-sentence edits, and
neither is a mechanism defect. They are raised because this document ships to another
codebase and to a successor pipeline, where a wrong sentence is expensive to retract.

The reserved judgment call (P1) is **decided against the sentence** — but on the
authority's literal text, not on the rationale the coordinator flagged, and at
should-fix rather than blocking because I established at source that no behavioural
harm follows. The §5-internal "snap" tension (P3) is **decided the other way**: the
client can obey both, the document is faithful to its authorities, and the ambiguity
is in the intention, so it is routed as a lesson and not as a finding against the
implementer.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — the graph now records one dependency at two granularities

**Question.** When you adjudicate phase 4's five pending graph items, keep the four new
`reads_from` edges to the step-state-record table as they are, or reject them because
the two-hop path through the live-worked-seconds node already records the same fact?

**Story.** Six months from now someone changes the shape of the open-interval table and
asks the graph who is affected. Today the graph would answer with the four
item-economics screens directly — the budget screen, the worker card, the batched
allocation cards, the production-time widget — which is the answer you actually want,
because all four would visibly change. If the four edges are rejected, that same
question returns only the internal loader, and whoever is doing the impact review has
to know to take a second hop to reach the screens people look at.

**Branches.**
- *Keep them:* impact analysis reaches the screens in one hop; the same dependency is
  recorded twice, so a future refactor has four extra edges to remember.
- *Reject them:* the graph stays minimal, and the dependency lives only in the two-hop
  path recorded in phase 2.

**Recommendation.** Keep them — a missing impact edge costs a missed review, and
duplicate edges cost only tidiness; the edges' own descriptions already say the read is
"through the shared live-worked-seconds loader", so they do not misrepresent themselves.

**On silence.** The five items stay pending; nothing breaks and no gate holds on this.

**Trace.** `.archgraph` relationships from the four `projection-item-economics-*` nodes
to `table-step-state-record`; intention §8; plan 4 C6.

---

## Verified perimeter (step 1)

`git show --stat 3df02ae` — **exactly the allowed set, 10 files**: `.archgraph/`
(`architecture.yml` + 5 change records), `handoffs/implementer/2026-08-22_phase4_fix_r2_handoff.md`,
`master_plan.md` (**1 insertion**, its own tracker row — verified by reading the diff,
not the count), `plans/plan_4.md`, and the new frontend handoff.

`git diff 80b8cca 3df02ae --name-only` additionally lists
`handoffs/implementer/2026-08-22_phase4_implement_r1_handoff.md` and
`prompts/implementer/2026-08-22_phase4_fix_r2.md`. **These are not perimeter
violations**: the coordinator commit `e13923f` sits between the two checkpoints, and
`git show --stat e13923f` shows both files as its own writes (consumption marking + the
fix prompt it compiled). No file needed attribution to master §7's three recognized
external streams. **No automatic finding.**

## Findings

### S1 — should-fix — record deletion is named to the client, against two authorities

**Where.** New handoff §5, decrease mode 2: *"Record deletion is not a shipped client
event and is not a cause to handle."*

**Violated authority.** Intention **§5.4**: *"record deletion is **not** a shipped
capability and **is not named to the client**"*. Master plan **§7, obligation 5**, same
words: *"record deletion is NOT a shipped capability and is not named to the client"*.
Both say the event is not **named**; neither says only that it is not named *as a
cause*. Plan C5's narrower literal ("record deletion NOT named as a cause") **is** met —
the document names it as a non-cause — which is why the coordinator's reading of C5 was
correct and why this is a finding against the document, not against that reading.

**Why should-fix and not blocking.** I established at source that no behavioural harm
follows. E5's only writer is the workspace reset, and
`services/commands/reset/reset_app.py` deletes task steps, tasks and the workspace in
the same run as `phases/delete_step_state_records.py` — so there is no surviving surface
on which a client could observe a decrease from record deletion. The sentence is
therefore inert in the payload sense; the defect is editorial and contractual.

**Why it is nonetheless worth removing.** Two measurements:
1. **There is no prior belief to retire.** I grepped all 18 published documents in
   `docs/handoff/to_frontend/` for deletion language: no published handoff has ever named
   step-state-record deletion as a worked-time decrease cause. The sentence retires
   nothing; it introduces the topic.
2. **It is the one sentence in §5 that describes our write surface rather than their
   behaviour** — and §6A C opens by excluding exactly that register: *"the closeout
   handoff tells the frontend what to do, not what we believe."* This is the same test by
   which §6A B's two-drops-from-one-action fact was correctly kept out of the document.
   Applying the test consistently removes this sentence too.

**Correction clause.** Delete the sentence *"Record deletion is not a shipped client
event and is not a cause to handle."* from §5 mode 2, changing nothing else in that
mode. **Source of truth: intention §5.4 and master_plan §7 obligation 5**, both of which
state that record deletion is not named to the client. Mode 2's surviving general rule —
*"A drop larger than 1 second is authoritative: snap down immediately to the served
value…"* — already covers a decrease from any cause, including one our API cannot emit,
so nothing is left uninstructed by the removal.

### S2 — should-fix — the published baseline omits the instability caveat its own authority marks binding

**Where.** New handoff §7, which publishes the 21-ID set as *"the durable comparator"*
for `narrow_typical_work_times` D23.

**Violated authority.** Master plan **§6**, two bullets that the 2026-08-22 gate block
does **not** supersede (that block supersedes "both baselines recorded further down" and
the "which database" block — the instability bullets are neither):
- *"**⚠ Suite instability — at least TWO named flaky tests**"*
  (`test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
  and `test_process_shopify_products_integration.py::test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task`),
  with the consequence stated as **binding**: *"a single run is not evidence — repeat and
  ID-diff."*
- *"**⚠ A THIRD intermittent test exists, and its identity is unrecoverable**"* — the run
  in which one enumerated baseline ID *passed*.

**Measured.** Neither named flaky test is a member of the published 21 (`grep` over the
handoff: 0 hits each; 21 IDs published, count verified). **So a flake cannot present as a
missing ID — it presents as a NEW failing ID in D23's diff, which reads as a regression
introduced by their own work.** That is precisely the misreading C9's own subset bullet
exists to prevent for the 26→21 transition ("so a successor holding an old citation can
reconcile the two rather than reading a regression into the difference"), reproduced by
omission one bullet later. The third intermittent test makes the error symmetric: the set
can also shrink.

**Correction clause.** Add to §7's baseline block that **at least two named tests in this
suite are intermittent and are not members of the 21**, that a third intermittent test's
identity is unrecoverable, and that **a single run is therefore not evidence — repeat and
ID-diff before concluding the set has changed**. **Source of truth: master_plan §6**, the
"⚠ Suite instability" and "⚠ A THIRD intermittent test" bullets. If the isolation work is
believed to have retired that instability (plausible — its causes were dev-database and
collection-order coupling), that must be **measured and stated as re-measured**, not
assumed by silence; the bullets stand unamended in §6 today.

### N1 — note — the Redis precondition ships without its diagnostic number

C9's bullet reads *"Redis at `settings.redis_url`, **without which the same tree measures
23 failed / 2 errors, not 21**"*; §7 states the requirement and omits the consequence.
Master §6's own published-baseline standard (*"failing-ID set, tree identity, database
identity **and the services that must be reachable**"*) **is** met, which is why this is a
note and not a should-fix. **Correction:** add "a machine without Redis measures 23 failed
/ 2 errors, not 21" so a mismatched count is diagnosable rather than mysterious. Source of
truth: master_plan §6, the Redis precondition bullet.

### N2 — note — "snap down" carries two referents across the authorities; the document inherits the ambiguity (P3's reserved tension)

**Not a finding against the implementer.** The document's closing rule — *"smoothing may
add elapsed time after receipt, but it must snap down to the served value rather than
clamp"* — is a near-verbatim lift of **intention §5.4** (*"Client smoothing must snap down
to the served value, never clamp"*) and of **master §7 obligation 5** (same sentence). The
implementer carried its authority faithfully.

**The tension is between authority sections.** §5.4 states "must snap down" over every
mode; §6A C's second bullet says that on a ≤ 1 s drop *"no visible snap is required"*, and
§3.3 is titled *"The no-snap invariant"*, where "snap" is the thing to avoid.

**Decision: a client can obey both.** The only reading in which both sentences are
simultaneously satisfiable is that "snap down" governs the **smoothing baseline** (never
hold a floor above the served value) while "no visible snap is required" governs the
**rendered value** — a client displaying `served + elapsed-since-receipt` lowers its
baseline by 1 s while the display continues to rise, so nothing visibly snaps. Mode 2 uses
"snap down" compatibly, pairing it with "reset the smoothing baseline". So this is a
lesson, not a defect.

**Lesson home: `planning/intention.md` §5.4 and §6A C** — name the referent of "snap"
(baseline vs rendered value) so the frontend does not have to derive the reconciliation
from three sections. If the coordinator wants belt-and-braces, the handoff's closing
paragraph could say "snap its smoothing baseline down to the served value", which is a
strict improvement and contradicts nothing.

### N3 — note (owner-adjudicated; see Card 1) — the double dependency is on all four projections, not one

P7 framed this as one node; **measured over the graph, it is four**. Each of
`projection-item-economics-task-budget-status`, `…-worker`, `…-task-budget-allocations`
and `…-task-production-time` now carries **both** `reads_from → projection-live-worked-seconds`
(phase 2, `human_confirmed`) and `reads_from → table-step-state-record` (phase 4 r1,
`ai_inferred`, pending), while `projection-live-worked-seconds → table-step-state-record`
already exists. The four new edges are transitive shortcuts across an already-modelled
two-hop path.

**Not filed on the `archgraph-discrepancies` route**: the graph does not contradict the
code — the dependency is real, and diagnostics are 0. It is a modelling-granularity
question, which is the owner's, and the five items are pending adjudication anyway.

**One falsifiable cost, recorded for the adjudication:** each new edge's evidence anchor
points at a symbol that does not touch the table —
`get_task_budget_status.py:_build_evaluated_status` contains no `StepStateRecord`
reference; the read lives in `live_worked_seconds.py`. Mitigating, and why I still
recommend promotion: the edge descriptions and `inferenceReason` fields say so themselves
("through the shared live-worked-seconds loader", "ultimately sourced from"), so the edges
are self-documenting rather than misleading.

**I promoted, rejected and edited nothing.** Five pending, unchanged.

## Verified correct — specifically (so the next round is cheap)

**Criteria.** C1 ✓ (§1 names the flag as retired and cites the 2026-08-19 §4 promise).
C2 ✓ (states §2's correction and §3's warning survive; perimeter confirms no published
handoff edited). C3 ✓ (client ticking superseded, smoothing-from-receipt preserved).
**C4 ✓ in all four parts**, including both amendments: **4.1 cites §§2.3A *and* 3.4A** —
the pre-prompt amendment survived the fix cycle — and **4.3 carries the eight-row list**,
which I checked **row by row** against §2.5A: item-cost results (1), daily analytics (2),
settlement-time step cost and rollups (3), production-time `final` partly-live (4),
typical-times aggregate (5), worker clock-out analytics (6), task/step serializer (7),
inert metrics helper with no callers (8). All eight present, each characterised as §2.5A
characterises it. C5 ✓ except S1. C6 ✓ (below). **C7 ✓ measured at my tree.** C8 ✓ (the
live/frozen `percent_consumed` distinction is stated in both directions and delivered
without editing the 2026-08-15 handoff). C9 ✓ except S2/N1.

**P2 — the price-scenario node's three clauses, all CONFIRMED at source**
(`get_task_price_scenario.py`, read in full, not via the handoff's account):
1. *"composes task budget status"* — line 195, `await get_task_budget_status(ctx)` with no
   `live_seconds`, so the loader does run inside a price-scenario request. The
   transitive dependency is real, not nominal.
2. *"publishes no live worked-time field of its own"* — **the load-bearing check.** It
   consumes exactly two fields off the composed status: `budget_status.status` and
   `budget_status.item_binding` (lines 239, 242, 298–299). `status` is
   `INFEASIBLE if allowed <= 0 else OK` where `allowed = evaluation.allowed_worker_minutes`
   (`get_task_budget_status.py:172–173`) — an **evaluation snapshot, not a worked-time
   derivation** — and on the non-evaluated branch it comes from
   `resolve_item_economics_status(valuation, selection, terms)`. `item_binding` is
   item/evaluation-derived. Its own `_typical_block` uses `typical_times_statement`, a
   settled consumer (§2.5A row 5). **So no live worked-time value reaches its payload,
   and the clause holds.**
3. *"reads no open interval record directly"* — the module imports neither
   `StepStateRecord` nor `live_worked_seconds`. ✓

**P5 — the two most falsifiable node claims, both CONFIRMED exactly:**
- **Batched allocations, *"one shared live worked-seconds map loaded once per request"*** —
  `get_task_budget_allocations.py`: steps for **all** visible tasks are loaded once
  (111–119), **one** `load_live_worked_seconds` call (124), then every per-task row indexes
  into that single map (222 `DivisionStep.total_working_seconds`, 238 `actual_seconds`).
  One map, one load, shared across the whole batch. ✓
- **Production time, *"passed both to budget status and into the allocator's response-only
  step rows"*** — `get_task_production_time.py`: loaded once (42), injected into budget
  status as `live_seconds=live_seconds` (48), and substituted into `DivisionStep` rows
  (55) that feed `divide_production_budget`. **Both halves, exactly as described.** ✓
- The remaining two: budget-status resolves its own map over `is_deleted.is_(False)` steps
  when none is injected (154–169) ✓; the worker face delegates to `_build_evaluated_status`
  without a map and so resolves one per request (`get_task_budget_status_worker.py:53`) ✓.
- **The mechanism sentence itself** is accurate: `live_worked_seconds.py` returns
  `settled + concurrency-averaged open share`, filters `exited_at IS NULL`,
  `state = WORKING`, `is_deleted = False`, and its docstring states *"no ORM step is
  mutated"* — "persisted nowhere" ✓.

**P4 — baseline block, element by element, judged as the D23 reader:**
- **Runner — verified at source, not from the master plan.** `app/pytest.ini`:
  `addopts = -ra --strict-markers --strict-config -n 6 --dist loadfile`. Six workers and
  `--dist loadfile` are literally there, as §7 states. ✓
- **Redis** — `settings.redis_url` exists (`beyo_manager/config.py:29`) ✓ (see N1).
- **Disposable database** — `beyo_test_main_template` is the name
  `resolve_template_database_name("main")` returns
  (`tests/integration/infrastructure/test_database_isolation.py:95`) ✓.
- **Tree identity** — settled by the coordinator, and **sound for this obligation for a
  reason worth recording**: master §7 obligation 7 wants *this pipeline's post-approval
  tree*, and `dc76db8` is the isolation project's stamp — but phase 4 changes nothing
  under `app/`, so the post-approval `app/` tree **is** `dc76db8`'s, and the block says so
  explicitly with a check-out instruction. Correct as published.
- **Counts** — 21 + 2576 = 2597 = the published collection ✓; matches master §6's first
  block verbatim, including 50.61 s. The deselected count is omitted, exactly as §6's own
  parallel line omits it — faithful, not raised.
- **21 IDs written out**, count verified = 21 ✓ (`comm` equality settled by the
  coordinator; not re-spent).

**Other structural checks (P8, passing glance):**
- §1 instructs the client to render `worked_seconds`, `left_seconds` and `share_state`.
  **These are real payload keys** — `division_serializers.py:43–45, 97–101`. The
  instruction executes from their side. ✓
- The §5 claim *"There is no `as_of` field by design"* is **structurally true**:
  `grep -rn 'as_of'` over `domain/item_economics/` and `services/queries/item_economics/`
  returns nothing. ✓
- §4.1's cost sentences match §3.4A **term for term**, including the corrected
  denominator — *"bounded by the smaller of the open records among the batch's non-deleted
  steps and the number of distinct credited users in the workspace"* is §3.4A B's `min(...)`,
  **not** §3.4's superseded 50-task cap — and the window is stated as *"a cost condition,
  not a correctness dependency"*, which is §3.4A C's exact instruction. This is the single
  most carefully-carried passage in the document.
- §6's prose matches the graph delta it describes (four direct, price-scenario transitive
  and explicitly denied a direct read). ✓

## Evidence

| # | Hypothesis | Scope | Command | Tree identity | Result |
|---|---|---|---|---|---|
| E1 | C7's docs guard is green on the tree under review | L1 | `PYTHONPATH=. pytest tests/unit/docs/ -q` (from `app/`) | `31e6634`, `git status --porcelain` **empty** | **59 passed** in 2.89 s |
| E2 | Fix-cycle perimeter is exactly as declared | — | `git show --stat 3df02ae`; `git show --stat e13923f` | `31e6634`, clean | 10 files, exactly the allowed set; the 2 extras in the checkpoint-to-checkpoint diff belong to `e13923f` |
| E3 | Runner claim is true at source | — | `cat app/pytest.ini` | `31e6634`, clean | `-n 6 --dist loadfile` present in `addopts` |
| E4 | Neither named flaky test is a member of the published 21 | — | `grep -c` per ID over the handoff | `31e6634`, clean | 0 and 0; 21 IDs published |
| E5 | Graph edge inventory around the live-worked-seconds boundary | — | parse of `.archgraph/architecture.yml` (296 relationships) | `31e6634`, clean | 4 projections × 2 edges each + the loader's own edge |

**L4 runs this session: 0.** The budget was 0 and the derivation held — my `app/` tree is
identical to the gate stamp's (`git diff 0aae85e HEAD -- app/` empty, coordinator-settled),
so master §6's **21 failed / 2576 passed** is cited by tree identity, never re-measured.
E1 is not over-evidence: my tree (`31e6634`) differs from the last docs-guard stamp's tree
(`3df02ae` + session edits) **in `docs/`**, which is the surface that guard reads.

**Settled items I deliberately did not re-spend**, per the prompt: the 21-ID `comm`
equality and the five removed IDs; `dc76db8`'s resolution and its empty `app/` diff; the
untouched `summary`/`inferenceReason` fields and the byte-identical HC-5 invariant;
`archgraph_status`'s 194/296/5/0/0; **C7's non-vacuity probe**; and §6A B's correct
absence.

## Mutation-probe declaration

**No mutation probe was applied this session.** No file was written, moved or reverted
outside my declared write perimeter; no database or tool-recorded state was mutated. The
one command executed (E1) is read-only with respect to the repository, and
`git status --porcelain` is empty at close. Nothing to restore.

## Write perimeter (this session)

**Documents:** this handoff; `plans/plan_4.md` (state line + §7 Review log append);
`master_plan.md` (my own tracker row only).
**Code:** none. **Tool-recorded state:** none — no `archgraph_*` write of any kind, and no
review item promoted, rejected or edited.

## Lessons for the plans

1. **"Not named as a cause" and "not named" are different criteria, and the plan carried
   the weaker one.** Plan 4's C5 paraphrased intention §5.4 and master §7 obligation 5
   into a narrower rule, and the paraphrase was met while both authorities were not — the
   fix round then preserved the sentence on instruction. **Home: `plans/plan_4.md` C5** —
   quote the authority's clause rather than paraphrasing it. Generalisable: when a
   criterion compresses an authority sentence, it should quote the operative words.
2. **A published baseline needs its instability caveat, not only its identity.** Master
   §7's baseline schema was amended once already (2026-08-21, re-review r3 P5) to require
   `failure-ID set + tree identity + database identity`; this round shows the schema is
   still one field short. **Home: `master_plan.md` §7, "Published approval baselines"** —
   add *known instability* to the schema, so every future published baseline carries "a
   single run is not evidence" with its named flaky members. This is the same lesson the
   inline-valuation project earned independently ("the suite drifts, so a single run is not
   evidence"); it is now earned twice and belongs in the schema rather than in a §6 bullet
   a publisher may not read.
3. **The gate block should say what it supersedes *and* what it does not.** Master §6's
   2026-08-22 gate block opens "READ THIS BEFORE CITING ANY BASELINE BELOW" and supersedes
   the baselines and the "which database" block. The instability, `TZ` and residue bullets
   below it survive — but a reader who takes the banner literally will not carry them
   forward, which is exactly how S2 happened. **Home: `master_plan.md` §6, the gate block**
   — one line enumerating the bullets that survive it.
4. **Name the referent of "snap".** See N2. **Home: `planning/intention.md` §5.4 and
   §6A C.**
5. **A phase whose deliverable is prose should get a source-verification criterion for
   claims it makes *about code*.** C6 required "five nodes updated" and the fix round
   updated five; nothing in C1–C9 required that the new descriptions be *true*. They are —
   I verified all five at source and every clause held — but that was a probe the review
   prompt had to invent, not a criterion the plan carried. **Home: the next
   documentation-phase plan's criteria** (and `master_plan.md` §5 as a standing rule):
   when a phase writes descriptions asserting a mechanism, one criterion requires each
   asserted mechanism to be verified at its own source, per node.

## Carry-forward dispositions

Not applicable at this verdict (CHANGES_REQUESTED). If the fix round closes S1 and S2, the
open notes route as: **N1** → fold into the same fix (one clause, same block as S2);
**N2** → intention §5.4 / §6A C at the coordinator's next upstream fold, not a phase-4 fix;
**N3** → the owner's graph adjudication of the five pending items, Card 1 above, which is
independent of this phase's gate.
