---
subject: stock_report — the ordered execution list from the D1 production fix to project close
date: 2026-09-22
actor: orchestrator
authority: owner, 2026-09-22 — "apply after D1 approves, then continue with D2. you should complete all the remaning task by your self"
status: IN PROGRESS
---

# Remaining work, in order

**This is the single ordered list.** It supersedes `D1_GATE_CHECKLIST.md` (whose six gate items
are all discharged). `OWNER_CARDS_batch_D.md` holds the rulings; `FINALIZATION_STEPS.md` holds the
owner's original ordering, which this expands.

**Every owner card is now ruled.** Nothing below waits on a person. The two authority lines still
hold absolutely: **rule only what the intention settles and cite the clause**, and **park anything
that turns on a domain invariant or a published contract that the owner has not already ruled on.**

---

## STATUS, 2026-09-22 — steps 1 through 4 are DONE

Steps 1, 2, 3 and 4 are complete. **D1 is APPROVED at `d800e73`; phases 12 and 13 are VERIFIED;
14 of 16 phases are done.** All four ruled card additions are authored **and armed**, every mutant
re-measured by the orchestrator rather than consumed from an agent's stamp. Totals **660 criterion
rows in 108 criteria across 16 plans**.

**What remains is steps 5 through 8**, and step 5 (D2's projection) is **in flight**.

**Two things are carried to the owner and must not be quietly closed:**
- **Card D-13** (new) — the deleted event's `workspace_id` comes from `ctx`, which contradicts
  ratified intention line 1495 and master plan §6.7. Unobservable today; routed to D2's projection
  for measurement; **parked** because it turns on ratified text.
- **The eighth D-10 id** (`test_a_row_with_no_assignments_answers_an_empty_list`) was outside the
  arming round's scope and is still **undecided**. Carried to closeout.

---

## 1. D1 production fix — DONE (`2fb7acb`)

Card D-5, owner-approved and scoped to goal records. One type predicate in `consistency.py`.

**Verify by hand, never from the stamp:**
- the witness `test_the_priority_record_snapshots_the_live_awaiting_counter` green **unedited**;
- phase 3's suite green with **no test file touched** (the inertness proof);
- revert the filter → witness red again → restore, `git diff --quiet` exit 0;
- **gate L4 back at 23 / 3739 / 1**, ID diff empty both ways against the checked-in baseline.

## 2. D1 narrow re-review — DONE (`30d7193`, APPROVED)

Delta-scoped: the fix, plus the rows the fix and the verification fix round touched
(12 C3(d), 13 C4(a), 13 C2(a)). Everything else was settled at 58/64 in round 1 and is **not**
re-opened. **Carry L-45:** every mutation observed during round 1 ran against a suite that was
already red by one test; the re-review confirms the ones that matter now that it is green.

**Never approve a batch a review failed.** If this one fails, it is a second CHANGES_REQUESTED on
one batch — §3A says that is not automatic and the coordinator stops and relays. **That would go
back to the owner**, ruled or not.

## 3. D1 gate — DONE (`d800e73`)

Approval-gate commit · phases 12 and 13 → **VERIFIED** · batch tracker D1 → **APPROVED** ·
graph delta (one batched `apply_changes`) · archive D1's spent prompts and consumed handoffs to
`archive/batch_D1/`.

## 4. Apply the ruled card additions — DONE (`96e5e33`, `1084791`, and this commit)

Order by value, all authored against the drafted text in `OWNER_CARDS_batch_D.md`:

1. **D-8** — the row pinning `stock_report_item:deleted` (`extra {}`). Highest value: it is a
   promise in the **published** frontend contract that nothing currently guards, and §9 rule 18's
   first violation since that rule was written. Arm it and **measure it red** before recording it.
2. **D-1** — plan 12 **C1(p)**, the priority-order tenancy row, from the drafted cell text.
3. **D-7 (1)** — plan 13 C3(a): three → **four** assignment-deletion events.
4. **D-7 (2)** — plan 13 C1(c) reworded to *"a new live row whose history contains only its own
   new goal record"*; "empty history" is unachievable and verified so.
5. **D-10** — **per test, not as a block**: fold the two `refuse_unknown_fields` guards; re-check
   `test_priority_route_accepts_an_explicit_null` and
   `test_list_items_route_passes_no_priority_when_the_param_is_absent` against existing rows
   before authoring anything (they may already be covered); **delete** the three HTTP-layer
   duplicates.
6. **D-6 / D-11 / D-7 (3)** — records, not rows. Each says **"unobservable, not unnecessary"**
   and carries its measurement *and its conditions* (D-6: the installed SQLAlchemy version;
   D-11: the query plan and table size). D-7(3) is a structural check and **no row is authored.**
7. **D-4** — amend intention §9 to the four-key `item_category`, **and sweep §9's other response
   shapes for the same drift** rather than patching one key.

Each addition is a test plus a measured-red mutation, then the row. **A row recorded before its
mutation is observed red is the failure this project has closed four times.**

## 5. D2 — projection **DONE (BLOCKED → resolved → folded)**; implementation is next

**Projection r0 returned BLOCKED**, on the one thing the batch was split to protect: 13A **C5(b)**'s
ORM-staleness premise. The orchestrator re-measured on the production shape and **the projection was
right** — the premise is false, the earlier contrary measurement had passed a string where the code
passes an enum member. See master plan **L-40 (corrected)** and **L-49**.

**Resolved and folded:** all **20 findings** applied to plans 13A and 14; C5(b) mutant (i) retired
and replaced by **(i-r)** (each cascade closes its own gap against the positions the previous one
left — observable, and invisible to plan 13 because plan 13 deletes one row); §7 Q2's armedness
restated; the batch-D split rationale corrected in §4; the cascade's own comment, which asserted the
staleness, corrected in place (comment only, suite green). Owner card **D-3 closed as "no change"** —
phase 7 is not touched. Plan 14 **C2(a)** is now met by a **test**, per the owner's ruling.

**Next: implement.** Prompt ready at `prompts/implementer/2026-09-22_batch_D2_implement_1.md`.
Then tester → review → fix rounds → gate.

Plans **13A** and **14**. 13A's projection is mandatory per the master plan.

**Carry into the projection prompt:**
- **L-41** — in this codebase's idempotent, de-duplicating code an **additive** mutant is absorbed
  (seven for seven in D1). Prefer **subtractive** and **reordering** mutants. This is the single
  most valuable thing D1 learned.
- **L-42** — fixture discrimination is **per row**, not per batch. Audit every ordered assertion
  in 13A and 14 individually; the same defect was fixed in plan 12 C4(b) and found untouched in
  plan 13 C4(a) hours later.
- **L-40** — §9 rule 3 is too coarse. **13A C5(b) IS armable** (measured: the shift statement
  leaves the ORM stale, 3 vs 2); do not let anyone retire it on the strength of C2(b)'s inertness.
- **L-43** — every signature registered in §6.5 must emit a pin obligation in the same act.
- **Card D-3** — the projection **establishes whether 13A needs the per-field validators exposed
  at all.** If it does not, **phase 7 is not touched.** Do not pre-authorise the extraction.
- **Plan 14 C1(b)'s guard must root in §6.7 plus every `event_name=` site**, not in `_events.py`
  alone — otherwise it cannot see `build_stock_report_item_deleted_event`, which now lives in
  `_delete_stock_report_item_cascade.py`.

Then: implement → tester → review → fix rounds → gate. Same slots discipline
(`BEYO_TEST_SLOT` on **every** pytest command).

## 6. Phase 14's own deliverable — re-verify, do not re-author

Plan 14 task 3 was changed at the D1 planning stage from *author* to **re-verify**: read the
published `HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` against the shipped code, flip
each **SPECIFIED** line to **VERIFIED**, and **re-issue only if something moved** — a new dated
file with a `supersedes:` key, the old one **moved** to `archived/`, never edited in place.

**`…match_preview_v2…` is not superseded and not archived.** Owner card 7.

## 7. The frontend wiring guide — the owner's actual goal

Read `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/frontend/docs/architecture/under_construction/implementation/stock_report`
and write **what the frontend must change to use this backend**. Concrete and actionable, not a
restatement of the API. This is the wiring stage — the last step before live testing, and the
thing the whole pipeline was for.

## 8. Closeout

1. Final **L4 + baseline comparison** (§3B defers these to closeout explicitly; batch gates do
   not satisfy them).
2. **D-9** — the seven missing `workspace_id` terms, as its own post-D change. Behaviour-preserving;
   the suite staying green is the proof.
3. **The five "adjacent" baseline failures** (§10.1) — **DONE 2026-09-22, recommendation: fix
   none.** Both causes named by execution: two are a stale reference to `_DeleteIssuesBody`,
   renamed by foreign commit `3f19249` (and this project never touched `items.py` — 0 commits
   since `cce4b1b`); three are `A transaction is already begun on this Session`, a fixture defect
   in their own files. Full evaluation in master plan §10.1. **Relay to the owner at closeout** —
   the two stale ones are worth a small change *in the project that owns them*, not here.
4. Graph delta · archive to `archive/batch_D2/` · approval-gate commits · update
   `project_stock_report_pipeline.md`.

## Carried OUT of this pipeline — still not absorbed

- **The mandatory-category enforcement gap** — needs its own intention, a migration and a backfill
  audit.
- **`test_database_isolation.py` slot-sensitivity** — a foreign APPROVED project's file.
- **The `migrations` exclusion** from the MC-2 write-site guard — a migration can change task
  state invisibly in any form. Noticed 2026-09-21, never ruled.
