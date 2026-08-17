# Owner decisions — simple_production_budget_division

Verbatim register. Cards are relayed exactly as authored; answers are recorded with
date and the owner's own words where they carry nuance.

---

## Settled during intention shaping (owner conversation, 2026-08-16)

**D1 — typical statistic.** Median of `total_working_seconds` over completed steps,
90-day window, minimum 5 samples, `null` below minimum. Owner: "sounds greate" to the
recommendation triple (median / 90d / min-5), with the explicit framing that window and
minimum are tunable numbers he may revisit.

**D2 — granularity.** Per working section only in v1. Per-item-category refinement
("upholstery on a sofa vs on a chair") deferred to a future `method` value.

**D3 — audience.** Both endpoints serve ADMIN, MANAGER, WORKER, SELLER. Time only —
no monetary field may ever appear on these surfaces.

**D4 — no serializer embedding.** Owner initially asked whether the typical could be
"hooked on the task steps serialization themselves" so every step surface carries it;
after the coordinator laid out the coupling/contract-churn/granularity costs and the
client-side-join alternative (every step payload already carries
`working_section_id`), owner: "got it." Standalone endpoints only.

**D5 — section filter.** E1 takes optional `working_section_ids`. Owner: "a worker
working only on upholstery shouldn't have to fetch all the other tipical working
sections average / median."

**D6 — allocation semantics.** Owner identified the conflict himself: the worker card's
"left" must come from the budget, not the typical, "and not only that but we can't use
all the budget because that will give too much time when there is working sections
after this that also need time." Accepted the budget-scaled typical-shares design
(typicals as proportions, budget as total, allowances summing exactly to budget) and
the **static** v1 variant. Owner: "perfect, i like it."

**D7 — server-side `share_state`.** On-track/over-share computed once in the backend so
the production-time widget and the worker cards can never disagree. Part of the D6
acceptance.

**Context decision (scheduling):** the frontend build of both components waits on this
phase — owner: "before i ship this to the frontend i want to tackle this 'tipicall'
value." The production-time component handoff's §6.1 omission is temporary and gets
un-omitted at this pipeline's closeout.

**D8 — live-step-set allocation (answers card 1, 2026-08-16).** Owner chose option B,
generalized, against the coordinator's A recommendation. Verbatim: "about the card 1:
I will actually prefere that the division and allocation of time changes, because a
manager not only can unasigned but also assigned, which should bring the allowed time
for that re-assignement also." Recorded consequence (coordinator, folded as intention
round 1): skipped/cancelled/failed steps leave the allocated set; manager-added steps
join it on the next read; worked seconds already consumed by excluded steps stay
charged against the budget before division (`D = max(0, B − C)`), so surviving
allowances never promise time a failed step already spent. Consumption-based
reallocation inside an unchanged step set remains out — D6 stands.

**D9 — (task, section) group totals as the typical's sample unit (2026-08-16).**
Owner spotted the re-assignment skew before implementation: "when a person
re-assignes to a working sectin a step … in real life that re-assignment will
techinally take less time than the real production time, so won't that pull down the
average?" Coordinator offered exclude-rework (first-pass-only); owner proposed the
better definition instead, verbatim: "a re-assignment technically counts as work that
was missed by the working section. then why can't we keep the query to add the
working time of the task steps that have the same working section, so a task with two
task steps on the same working section will add both working times to obtain that
'total' working time." Adopted as M1's sample unit (intention round 4) with two
coordinator-pinned corollaries: group-level window admission on MAX(closed_at), and
the accepted MVP over-allocation note for tasks holding two live same-section steps.

**D10 — E2 mounts inside the item-cost surface (answers projection card 1,
2026-08-16).** Owner: "about card 1: i go for A" (= the projectionist's *inside
item-cost* branch, also its recommendation). Consequence: HC-1 gains a narrow,
enumerated exception — exactly three v1 artifacts may change, each by the addition
the v1 authors designed for ("that friction is the point",
`test_phase9_item_economics_route_mirror.py:6-8`): (1) one route row added to the
hand-written `_EXPECTED_ROUTES` literal, (2) the count assertion 23 → 24, (3) one
Quick Index row + detail section in `routers/README.md`. Nothing else in v1 may be
touched; deleting the feature reverts all three in one edit each.

---

**D10 scope note (coordinator, 2026-08-16, implement-r1 consumption):** a SECOND
hand-written route mirror exists at
`tests/unit/routers/api_v1/test_item_economics_router.py` (`_ROUTES`,
`_ALL_ROLE_ROUTES`, route-pair table) and turned red when E2 landed. Extended
HC-1a from three to four authorized artifacts under D10's existing rationale — it
is the same designed tripwire family the owner already accepted, not a new
decision. Recorded here for provenance; no new card raised.

## Settled — phase 2 (owner answers 2026-08-17)

**D11 — the working section is the allocation unit (answers C1).** Owner chose B.
Verbatim: *"i don't fully understand the issue, because if a task has two upholstery
task steps then the work for those two should be sum isn't becasuse two imply one is
completed the other is pending or working, the total time that working section has
taken to fix an item is the total worked time of those two task steps. i think this
which i discribe is what you are pointing as a soluction with the 'recommendation B'."*

**Coordinator correction, recorded because the reason differs from the owner's
reading:** what the owner described (summing the two steps' worked time) is the
*consumed* side, already settled by D9 and restated as M3.3 — both variants do it.
C1 was about the *allowance*. Measured consequence of variant A on a 180-minute
budget with typicals 60/30/60 and two Upholstery steps: Upholstery is allotted
**102.9 min** while Structural Repair drops to 51.4 and Sanding to 25.7, because the
second Upholstery step adds a second full Upholstery weight (total weight 150 → 210,
`budget_division.py:142-147`). The rework therefore *grants* Upholstery budget and
*takes* it from sections that did nothing wrong, and Upholstery can rework
indefinitely without ever reading late. Under B the slices are 72/36/72, both passes
count against Upholstery's 72, and the second pass surfaces as `over_share` — which
is the intent. The owner's answer stands as B on the corrected reasoning.

**D11a — per-step split inside a section (coordinator-specified, not carded).**
Variant B allocates to the section, but the worker card still needs one number per
step. Rule: **the section's open step is allowed the section's slice minus the worked
seconds of that section's closed steps.** Justification for not raising a card: the
database has **0 of 2782 (task, section) groups with two non-closed steps**, so "the
open step" is unambiguous in all real data, and the rule gives the card the honest
answer to "how long do I have for this second pass?" The theoretically-possible
multi-open case is pinned by fixture (§12.10 row 5), never by production reality.
Raised here for owner visibility under the MVP calibration rule.

**D12 — the live step governs the section's displayed state (answers C2).** Owner:
*"the recomendation is the correct approach"* → variant A. A section holding a
completed first pass and a pending reassignment renders **pending**, because the
section genuinely has work to do again and the row's time keeps climbing. The
furthest-state reading (showing *completed*) is the audit question, which this widget
is not for.

**D13 — E3 carries no per-step data, and a step row's `share_state` comes from its
section (answers projection card 1, 2026-08-17).** Owner: *"i don't understand the problem
of card 1 … if a working section has two task steps assigned, both task steps account for
the total worked time so if both working times additions overflow the allowed time it
should not render on track for independent steps … because this endpoint should not be
returning the individual task steps. only what is need it to read on the component which
is upholstery has worked a total of 2 h regardless of how many task steps was it
re-assigned to."*

Coordinator reading, recorded because the card was about a surface the owner had not
assumed was in play: card 1 concerned **E2's worker card**, which does render one card per
step — E3 never did. Two consequences. (a) E3's payload loses `step_ids`; `step_count`
stays as a fact about the section. (b) The owner's "should not render on track for
independent steps" is **stricter** than the projectionist's recommendation, under which an
earlier finished pass would read `on_track` while only the governing step showed the
overflow. Adopted per the owner: a step row's `share_state` is derived from its
**section's** total worked vs its slice, so no step of an overflowing section reads
on-track. `allowance_seconds` / `left_seconds` stay per-step — they answer "how long do I
have for *this* pass?" — and only the state is section-derived. Bonus: E2 and E3 now
report the same *state* for a section, not merely reconcilable numbers.

**D14 — allowances and time-left may go negative (answers projection card 2).** Owner:
*"that is a frontend concern, the frontend gets the values and sees the overflow and will
render the overflow, the backend just presents the data the frontend decides how to
visualize it."* No clamping: clamping would break P-AGREE's exact sum, the one guarantee
this phase exists to establish. The frontend handoff rewrite carries the rule that a
non-positive `allowance_seconds` draws a full over-share bar rather than a division.

**D15 — a failed step's time still comes off the whole budget (answers projection card
3).** Owner: *"we still show the ate [= eaten] time that section took."* Coordinator
reading: the consumed time stays visible in the section's `worked_seconds`, and "still"
keeps today's rule — charging remains at the task level, which is also the
projectionist's recommendation. So D11 changes the **weighting** unit only; `C` stays Σ
worked over non-deleted excluded steps, D8's promise holds, §4's consequence table stands,
and five phase-1 assertions keep their exact numbers. **Flagged for correction in one
line if that reading is wrong** — the alternative (each section absorbs its own failures)
would let a task promise time it has already spent.


**D16 — a section reads `over_share` on its TOTAL worked, failed passes included
(answers review r1 card 1, 2026-08-17).** Owner: *"yes over share is the correct solution
( fail, cancell or deleted steps is not something that will happen often but the solution
that was provided as recommended is viable )."* So `share_state` compares M3.3's
`worked_seconds` — the section's total over all non-deleted steps, including excluded
ones — against `allowance_seconds`. `left_seconds` is unchanged and stays
`allowance_seconds − worked_seconds`, because §12.7's published example prints all three
on one row and the client must be able to reproduce the arithmetic. M3.5b's
exclusion rule continues to govern **only** the residual that splits a slice across a
section's steps: charging decides how much is allocated, `share_state` reports what the
section has spent. Owner's framing recorded: the excluded states are rare, and the
recommendation is viable rather than ideal.

**D12 reachability — owner challenge, adjudicated 2026-08-17.** Owner: *"about the D12 I
don't think this is possible to happen, because when the user manipulates a task step
( worker or manager ) it manipulates the active task step, once closed it never opens
again, a new one is created, or im i wrong ?"* **The owner is right about the
reassignment flow, and measured right about today's data.** Coordinator measurements:
**0** multi-step groups where the newest-created step is closed while a live step exists;
all 5 `{completed, pending}` groups have the pending step newest; `created_at` is NULL on
**0 of 3049** live steps; and — correcting review r1's supporting claim — **no multi-step
group shares an identical `created_at`** (49 two-step groups have 2 distinct timestamps,
19 three-step groups have 3). Two of B1's three deviating fixtures are therefore
unreachable through the database. Closed steps never reopen, confirmed in code
(`transition_step_state.py:150-152` raises on any transition out of terminality).

**The fix still lands, for the one case the reassignment argument does not cover:** a
manager adds a second step to a section that already holds a pending one, and the *newer*
step is completed first. Newest-created is then closed while older live work remains, and
the row would read `completed` beside outstanding work. Nothing in the write paths
prevents it; it simply has no instance today. The code currently agrees with D12 by the
coincidence that steps on one section are created in the order they go live — which is
enforced nowhere. Partitioning by liveness before sorting costs ~5 lines and makes the
code state the rule. **Reclassified BLOCKING → should-fix** on the corrected reachability;
it stays in the r2 work list.

---

## Settled — phase 1

None open. (Card 1 → D8; D9 owner-proposed; projection card 1 → D10.)
