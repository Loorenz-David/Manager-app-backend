# Plan 6 — Closeout: the frontend handoff, the living docs, the graph

```
plan: plan_6
project: narrow_typical_work_times
state: NOT_STARTED
projection_gate: WAIVABLE — no rule-6 code surface. The coordinator records a one-line
                 justification if it waives.
```

## 1. Goal

Publish what the frontend must do differently, correct the one **published** instruction this
pipeline supersedes, bring the living docs back into agreement with the code, and leave the
architecture graph accurate.

**Explicitly NOT in this phase:** no production code change, no test-behaviour change, no
golden regeneration, and — the standing rule — **no edit to any published handoff**. If a
production defect is found here, it goes back to the phase that owns it as a fix cycle; it is
not patched from a closeout phase.

## 2. Read first

- Master plan §§4, 5, 6.5, 6.7, 8, 9, 10.
- Intention **header**, then §5 (the two pathways and the statistics-vs-task numeric
  difference), §6.3 (**the exact eligibility phrasing — normative, do not paraphrase**), §6B
  (what the `is_estimated` message actually is), §7 (the always-present rule), §7.1 (D24),
  §7.2, §7.3, §7.4, §9 (what is deferred, with its return paths), **§11.3** in full, §4C
  (what is now unreachable on the wire).
- `planning/owner_decisions.md` — D18, D19, D20, D23, D24, **D25**.
- Gate handoff §5 item 2 (the `is_estimated` message is materially different from the one §6.4
  was going to send).
- The Review logs of plans 1–5 — **including the projection handoffs' ledgers**, not only the
  intention's sections. A read order built from section numbers misses lettered sections a
  projection added.
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`
  §Worker task-step cards — **read it, do not edit it.**
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` — the
  shape a published handoff takes in this lineage.
- `app/tests/unit/docs/test_item_economics_docs.py` and `test_item_economics_handoff_accuracy.py`
  — **the guard decides which living docs must move, not judgement.**

## 3. Dependencies

**Gate: plan 5 `APPROVED`.**

## 4. Files expected to change

**New**
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_narrow_typical_work_times_<YYYYMMDD>.md`

**Modified — only if the guard names them**
- `docs/domains/item_economics/README.md` · `api.md` · `events.md` · `states.md`
- `app/tests/unit/docs/test_item_economics_docs.py` /
  `test_item_economics_handoff_accuracy.py` (new pinned assertions for the new document)

**Modified — closeout bookkeeping**
- `master_plan.md` (tracker rows to `APPROVED`)
- `plans/plan_<n>.md` Review logs

**Read-only, and a change is a finding**
- Every file under `app/beyo_manager/`, every golden, and
  `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`.

## 5. Ordered tasks

1. **Run the docs guard FIRST**: `PYTHONPATH=. pytest tests/unit/docs/` (59 tests, ~3 s). It
   costs nothing and it is what tells you which living docs are pinned to which semantic
   authorities. A tripwire in this suite has broken a running implementer session's baseline
   from a file in a different phase's perimeter once already.
2. **Write the new dated handoff.** §11.3's obligations, each as its own section:
   - **`ALLOCATION_METHOD` v2**, with §6.3's exact eligibility phrasing quoted, not
     paraphrased: every task is now evaluated under the new rule; allowances are **eligible**
     to change wherever item-category narrowing changes the relative section weights; many
     tasks remain numerically identical (primary items with no category; tasks reconciling to
     `section_wide_uniform`; categories whose narrowed ratios coincide with the section-wide
     ratios); **the contract changes even where an individual numeric result does not.**
   - **Every new field, with its nullability and the reachable state that produces each null.**
     Not a key list — a key list passes while getting the harder half wrong. `applied_filter`
     is the one deliberate `null`, and the state that produces it is "the task's primary item
     has no category, or there is no primary item".
   - **The `is_estimated` clarification — and it carries NO value change.** This is materially
     different from the message §6.4 was going to send. Read literally, §6.4 would have flipped
     the flag to `false` for a task with zero participating sections; §6B keeps that disjunct
     verbatim, so every existing value is preserved. Say plainly: *nothing to change; the
     definition is now written down.* Also state §6.4's genuine content — reconciling to
     `section_wide_uniform` alone does **not** set the flag — and the `sections_without_sample`
     scope (participating sections whose **selected** typical is null or ≤ 0, **not** sections
     without a narrowed sample).
   - **D25's unreachability, so nobody codes a branch for it**: `typical_worker_seconds: 0`
     beside `typical_basis: "item_narrowed"` is **unreachable on every task surface**. The
     reachable zero-statistic form is `section_wide` + `0`, and a zero **is** a statistic — it
     is never published as `insufficient_sample`.
   - **`/working-sections/typical-times` is unchanged** (D24) — no params, no response change.
   - **The statistics-vs-task numeric difference (§5)** stated as *deferred*: the same evidence
     can legitimately produce `540` for task economics and `null` for analytics, and this
     becomes visible only when `/statistics/typical-times` ships (§9). Do not describe an
     endpoint that does not exist.
   - **The worker-card re-pointing, as a supersession.** Name
     `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md` §Worker task-step cards
     and supersede **one instruction** of it: the cards' fallback typical comes from
     `budget-allocations` `steps[].typical_worker_seconds` (already present in the `no_budget`
     state, and item-aware after this pipeline); **the bootstrap `typical-times` fetch, cache
     and join are deleted from the card path.** One batched call per feed page (≤50 task ids)
     remains the cards' single economics source; `typical-times` stays a task-free benchmark
     surface.
     *Why*, in one line the frontend can act on: a client-side cached generic typical beside
     item-aware card figures would contradict production-time's degraded state for the same
     task and section — the last place cross-surface disagreement could survive.
   - **A cost line** for any instruction that changes *when* an endpoint is called. A
     correctness fix to a client instruction needs one: the reviewer who corrects the timing has
     no reason to look at what the call runs, and the frontend has no way to.
3. **Never edit the 2026-08-18 handoff.** Supersession is a new dated document naming the old
   one. An in-place edit of a published handoff cost the frontend four days in this lineage,
   building a feature on a refusal that no longer existed.
4. **Update the living docs the guard names**, and extend the guard with pinned assertions for
   the new document if the existing tests' pattern calls for it (they pin semantic authorities
   by literal). If a document must *describe* a retired identity, describe the behaviour and
   tell the reader to search their own codebase — **do not spell the token**; the retired-identity
   guard's roots cover all of `docs/handoff/`.
   Widen an allowlist rather than removing a filter: removing the guard's extension filter makes
   it crash on a binary file in its own root and go red forever for the wrong reason.
5. **Architecture graph.** One batched `apply_changes` for whatever this session actually
   changes (likely: none, if only documents moved — check, do not assert). Then verify the whole
   project's graph state: `archgraph_status` shows 0 pending / 0 stale / 0 diagnostics, and the
   nodes plans 2, 4 and 5 touched carry accurate spans. **Re-derive every span from its symbol;
   never trust a stored one** — all four stored spans were wrong the last time this was checked
   in this lineage. Agents never promote, reject or edit review items.
6. **Close the tracker.** All six rows `APPROVED`. Move closed prompts and handoffs into
   `archive/plan_<n>/` at the coordinator's closeout ritual, together with the gate commit.
   Historical path references are **not** rewritten — they resolve under `archive/` by
   convention.
7. **Read every document in the phase end to end, regardless of delta.** A final round does
   this because the finding that survives is the one in a file nothing changed.

## 6. Tests / acceptance criteria

**C1 — the docs guard is green.** `PYTHONPATH=. pytest tests/unit/docs/` passes, before and
after every write under a guarded root.
*Mutation* — name the retired inline-refusal identity verbatim in the new handoff →
`test_retired_inline_refusal_identity_is_absent_from_live_sources` goes red (its roots cover
all of `docs/handoff/`).
*Both sides* — contract: 59 passed; mutation: 1 failed, naming the new file's path.

**C2 — every new payload field in the handoff is annotated nullable-or-not, and every
annotation names a reachable state that produces the null.** Asserted by a pinned docs test
over the new document: for each of `typical_basis`, `sample_count`, `narrowed_sample_count`,
`section_sample_count`, `typical_resolution`, `applied_filter`, the document contains the
field's name **and** an explicit non-nullable / nullable statement; and `applied_filter`'s
nullable statement names the producing state.
*Mutation* — the docs test (definition): drop `applied_filter` from the checked set → the
document could ship with a key list and no nullability, which is exactly how a previous
closeout in this lineage passed the check it was given while getting the harder half wrong.
Contract: six fields checked; mutation: five, and a document missing the one deliberate null
passes.
*Both sides*: with the field absent from the document, contract → red, mutation → green.

**C3 — the handoff states D25's unreachability.** The document contains the claim that
`typical_basis: "item_narrowed"` beside `typical_worker_seconds: 0` does not occur on task
surfaces, and that a zero is published as a statistic (`section_wide` + `0`), never as
`insufficient_sample`. Pinned by literal in the docs test.
*Defect caught*: a frontend branch written for a payload shape that cannot occur, and — worse —
a null-check that treats a legitimate `0` as "no data".

**C4 — the supersession is a supersession.**
(a) The 2026-08-18 handoff is **unchanged** — verified from `git diff` in the session's
perimeter, not from memory.
(b) The new document names that file and the section it supersedes, and supersedes **exactly
one** instruction of it.
(c) It states both halves of the re-pointing: where the fallback typical now comes from, **and**
that the bootstrap `typical-times` fetch/cache/join is deleted from the card path. A blanket
"the cards change" claim needs one statement per member.
*Mutation* — the docs test (definition): check only the "fallback comes from
budget-allocations" half → a document that adds the new source without deleting the old join
passes, and the frontend keeps a cache that is the last source of cross-surface disagreement.
Contract: both halves required; mutation: one.

**C5 — the pipeline's own record is consistent.** All six tracker rows read `APPROVED`; every
plan's Review log is non-empty; the master plan's environment section still matches
`app/pytest.ini` and the published baseline, or has been updated with what changed.
*Not automatable — stated as a reviewer check, not dressed up as a test.*

## 7. Notes

- **The owner-facing message of this pipeline, in product words** (for the closing chat
  message, not for the handoff): the time a task is *expected* to take in each working section
  is now drawn from past work on **the same kind of item**, everywhere the number appears — the
  worker's card, the manager's production-time view, the price scenario and the budget split —
  and when there is not enough same-item history, every surface falls back to the general figure
  **together**, never one at a time.
- **A "record the decision" instruction needs a named medium, or it defaults to the handoff —
  which archives.** Anything decided in this phase that the next reader of the *code* will
  question belongs in a code comment or the master plan, not only here.
- **A comment that asserts a property is a claim.** If this phase writes one ("the three
  predicates below are load-bearing"), drop each and see what goes red **before** the comment
  ships — and sweep the class, not the instance.
- **Verbatim replacement text is unreviewed on arrival.** A re-review's scope is the corrections
  **and** the correcting sentences; four findings in one lineage phase were defects in a
  reviewer's own proposed wording.
- The `/statistics/typical-times` route stays deferred with its contract pre-locked (§7.5,
  §9): `ANSWER_AS_ASKED`, no route override, counts-only diagnostics. Its parser and its policy
  branch shipped in plan 1 — **do not announce the endpoint**, and do not let the handoff imply
  it exists.

## 8. Review log

*(empty — append-only; shared by implementer and reviewer)*
