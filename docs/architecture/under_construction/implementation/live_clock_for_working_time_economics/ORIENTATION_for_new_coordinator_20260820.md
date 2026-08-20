# Orientation — incoming pipeline coordinator, `live_clock_for_working_time_economics`

```
written: 2026-08-20 by the outgoing coordinator (Opus 5), at the owner's request
for: the session that will orchestrate this pipeline
repo head at writing: ee253cd, working tree clean
```

Read this once, then read the two documents in §2. Everything else here exists so you do
not re-derive it or re-learn it the expensive way.

---

## 1. Your role

You are the **pipeline coordinator / orchestrator**. Doctrine, in reading order:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/pipeline-coordinator.md`

The shape: **the owner mediates.** You author prompts into `prompts/<role>/`; external agents
(Codex or another Claude session — the owner picks, and it changes) execute and deposit
handoffs into `handoffs/<role>/`; you consume them **adversarially** and route what you find.

"Adversarially" is not a posture, it is a checklist, and it is the single highest-value thing
the last pipeline established:

- **Verify the perimeter against `git`**, not against the handoff's own claim.
- **Re-run the suite yourself.** Never accept a reported count.
- **Re-apply the named mutations yourself** at their definition sites, whole-suite, and check
  the observed-red set matches. In the last pipeline this caught a wrong ledger row in three
  separate rounds.
- **Relay owner cards verbatim**, in one `⚠ OWNER DECISIONS REQUIRED (n)` section.

Track record worth knowing: across the last pipeline, **every blocking review finding was in
a coordinator artifact** — my prompts, my plans, my handoff prose. Not the implementers'.
Assume the same about yours.

---

## 2. The task, and where it lives

`docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

| File | |
|---|---|
| `planning/intention.md` | **RESOLVED, round 2.** D1–D6 ratified, ledger empty. The owner's own document. |
| `planning/owner_decisions.md` | D1–D6 with the owner's verbatim words |
| `planning/coordinator_review_of_intention_20260819.md` | **My review of that intention — six findings. Read it with the intention, not after.** |

**In one sentence:** make the worked-seconds basis *live* — settled work plus the
concurrency-averaged share of any open `working` interval — computed once in the backend and
consumed by every present-tense surface, so `share_state`, `worked_seconds` and `left_seconds`
stop disagreeing on the same card.

**Next gate: mechanism-inventory. It has NOT run.** Do not waive it. Charter rule 6 triggers
on time arithmetic with a concurrency-averaging rule and a windowing rule, and this feature is
made of exactly that — every mechanism produces a number that looks plausible when it is
wrong. The previous pipeline ran this gate and it paid: it found a break-even literal off by
29, an undefined function, and a status matrix that could not produce two of its own values.

---

## 3. What I verified about this intention — do not re-spend the pass

**The keystone claim holds.** `_section_step_allowances` reads worked seconds **only for
completed steps**, so live figures cannot move `allowance_seconds`. The intention's central
safety argument is sound. I checked this at the source, not by reading the document.

**The six findings, in one line each.** Details in the review; the numbers below are its
section numbers.

1. **§2.6's "no shared files" is now false.** It was written before the price-scenario
   pipeline landed. Re-derive the overlap set yourself against the current tree.
2. **Two promises to the frontend that the mechanism contradicts.** Reconcile before planning.
3. **The window rule is under-specified for the multi-open case.** More than one open interval
   at once is the ordinary state on a busy floor, not an edge case.
4. **E-B's SQL aggregate must be dismantled and the document doesn't say so.**
5. **T5 is not writable as stated.**
6. **E-A's cost is proportional to something unbounded.**

The review also carries a process note for whoever runs the gate. Honour it.

---

## 4. ⚠ A binding obligation to another codebase. Do not discover this late.

`backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md`
is **shipped and approved**. It tells the frontend that `share_state` is settled-only, tells
them to suppress the verdict while `state == "working"`, and then §4 says this:

> A backend pipeline is already shaped that reverses §1 on this very endpoint … Its removal is
> signalled by **that pipeline's own dated handoff**, not by this one. That document is already
> obliged to carry the go-live statement that retires your interim gate.

**That pipeline is yours.** Its closeout handoff **must** carry the statement that retires the
frontend's interim suppression flag. This is not a nicety — the frontend was told to build the
suppression behind one removable flag *specifically because* we promised to signal its removal.

Two related rules the frontend asked for and we adopted:

- **Never rewrite a published handoff in place.** Issue a new dated one and amend by reference.
  An in-place edit on 2026-08-15 cost the frontend four days and a feature built on a refusal
  that no longer existed.
- **§2's correction and §3's warning in that document do not expire.** Only §1 does.

---

## 5. Load-bearing facts about the code you will touch

Verified at source during the last pipeline. Re-confirm anything you plan to cite — but these
are true as of `ee253cd` and will save you the discovery.

- **`worked_seconds` on `production-time` is `TaskStep.total_working_seconds` and nothing
  else** (`budget_division.py:134`, `:266`) — a stored column, never a clock difference. That
  is *why* two calls a minute apart agree today, and it is the property your pipeline changes.
- **`share_state` compares that settled column against `allowance_seconds`**
  (`budget_division.py:364`). This is **D16** of the budget-division pipeline, ratified so that
  `share_state`, `worked_seconds` and `left_seconds` can never contradict each other on one
  card. An earlier implementation built two of them on different bases and shipped
  `left_seconds: -100` beside `share_state: "on_track"`. **If you change the basis, change it
  for all three or you re-create that bug.**
- **A section whose typical is `NULL` or `0` gets the median substituted as its weight**
  (`budget_division.py:327-335`).
- **`typical_times_statement`'s grouping subquery has NO date predicate.** The 90-day window is
  a `FILTER` on the outer aggregates only, so the subquery groups every completed step in the
  workspace for all time. **Any design that refetches per event runs an unbounded historical
  aggregate.** This already forced a debounce into a frontend handoff.
- **The read family is not clock-free.** `today_utc()` wraps `datetime.now` and is called in
  two files under `services/queries/item_economics/`. A grep for the literals `datetime.now`
  and `func.now` misses it — I published that false absence claim once and was corrected.

---

## 6. Standing rules earned the hard way

`docs/architecture/under_construction/implementation/simple_valuation_editor/master_plan.md`
**§5** is ~30 rules from five pipelines. Read it. The ones that bit most often:

- **Every named mutation: compute both sides, run the WHOLE SUITE, record every test that
  reddens.** A `-k` run is not an observation. Wrong three times before it stuck.
- **A fixture whose expected value is the same under the defect proves nothing, even when the
  assertion beside it bites.** Check the *assertion form*, not the fixture.
- **A comment that asserts a property is a claim, and it inherits the mutation rule.** Drop the
  thing it calls load-bearing and see what goes red *before* the comment ships.
- **Sweep the class, not the instance.** When a finding names one member of a set, probe every
  member. One round probed one of five predicates; three of the other four were hollow.
- **An absence claim is only as good as the scope it names** — earned three times, on a
  directory, a term set, and a suite.
- **A cross-reference from production code must resolve from a clean checkout with no pipeline
  documents present.** No criterion IDs, no round numbers, no bare line numbers.
- **"Record the decision" needs a named medium, or it defaults to the handoff — which
  archives.** A criterion asking for a recorded decision must say where the record lives after
  closeout.
- **A fake session makes a `WHERE` clause untestable, and the tests that look like they cover
  it do not.** Before citing a test as proof of a SQL predicate, check that it issues SQL.
- **Reviewer prose enters the tree with no second reader.** Verbatim application is correct
  protocol *and* it means replacement text arrives unreviewed. Read it as if you wrote it.

---

## 7. Environment

- Working directory `backend/app/`. Tests: `PYTHONPATH=. pytest -m 'not e2e'`. (The bare
  `make test` form fails collection with `ModuleNotFoundError: beyo_manager` in some shells.)
- **Baseline at `ee253cd`: 26 failed / 2433 passed / 1 deselected.** The 26 are inherited and
  pre-existing; none is in `item_economics`.
- **⚠ The suite has at least TWO flaky tests, named after 21 measured runs:**
  `test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
  and
  `test_process_shopify_products_integration.py::test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task`.
  **A single run is not evidence. A count that disagrees is repeated and its ID set diffed
  before any conclusion.** At the last closeout a mutation run read 27 and the repeat read 26 —
  a single run would have been read as the mutation biting.
- **Architecture graph: 0 pending, 0 stale, 0 diagnostics** — every node `human_confirmed` as
  of `0bab586`. You inherit it clean; keep it that way. Two open tooling findings sit in
  `implementation/archGraph_mapping_mantainance/open/` — read them before using
  `archgraph_repair_anchors` (batch calls fail; issue one operation per call) or before
  trusting a `conflicting-canonical-relationship` contradiction (it misfires on `contains` and
  `implements` both).
- Checkpoint commits at every `IMPLEMENTED`, prefixed `CHECKPOINT (not approved):`. Never
  squashed. The phase is committed again at its approval gate.

---

## 8. How the owner works

- **They mediate every round.** You never talk to the implementer or reviewer directly.
- **They answer owner cards decisively and briefly.** Card answers are often one line — take
  them at face value and move.
- **They will tell you when to narrow scope.** At the last closeout they chose the shortest
  path to done, and the line they drew was a good one: *fix what the tree is actively lying
  about; defer what is merely unguarded.* Offer that trade explicitly rather than assuming.
- **They run the reviews you compile.** Compile them.
- **The implementer session may change mid-pipeline** (Codex ran out of credit once and a
  Claude session took over). Prompts must be self-contained; assume no memory of prior rounds.

---

## 9. What is NOT yours

- **`set_aside/PLAN_item_economics_deferred_coverage_20260819.md`** — four deferred items from
  the last pipeline, each with its measured before-state. Do not fold them in.
- The `simple_valuation_editor` pipeline is **closed**: five phases APPROVED, all plans
  archived. Its files are not in any perimeter of yours unless your own mechanism-inventory
  says so — and finding 1 above says check, because §2.6 assumed otherwise.
- `domain/users/serializers.py:195` carries a dangling `criterion 13` reference. Owner backlog.

---

## 10. Suggested first move

1. Read `planning/intention.md` and `planning/coordinator_review_of_intention_20260819.md`
   together.
2. Re-derive finding 1's overlap set against the current tree — the answer changes the
   perimeter of everything downstream.
3. Build the charter folder structure (`plans/`, `prompts/<role>/`, `handoffs/<role>/`,
   `archive/`) and the `master_plan.md` hub.
4. Compile the **mechanism-inventory** prompt. Do not waive the gate.

One thing the last pipeline learned about that gate, worth carrying: **an intention's own
"what to attack" line is a hypothesis by its author, and the prompt must forbid it as a
scope.** Last time, the document nominated its two strongest sections; every defect worth a
round was in a mechanism nobody had flagged.
