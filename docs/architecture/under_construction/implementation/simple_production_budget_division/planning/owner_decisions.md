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

## Open

None. (Card 1 → D8; D9 owner-proposed; projection card 1 → D10.)
