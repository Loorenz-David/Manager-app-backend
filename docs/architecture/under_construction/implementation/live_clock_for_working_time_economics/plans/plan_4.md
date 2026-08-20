# Plan 4 — the closeout handoff and the graph delta

```
state: NOT_STARTED
phase: 4
date: 2026-08-20
depends_on: plan 3 APPROVED (the handoff documents shipped behaviour, including D9)
```

## 1. Goal

Discharge the pipeline's shipped promise: a **new dated** frontend handoff carrying the
go-live statement that retires their interim verdict-suppression flag, plus the five
other obligations in master plan §7's closeout table; and record the architecture-graph
delta (five projection nodes + `reads_from` edges).

**NOT in this phase:** no code. No edit to any published handoff — amendment is by
reference from the new document only. No graph review adjudication (human-owned).

## 2. Read first

1. `master_plan.md` §7 (the obligations table — the task list), §5, §6 (graph tooling
   findings pointer).
2. Intention §5.4, §6A C (the per-event client rules — carried **verbatim in
   substance**, three decrease modes), §2.5A (the corrected consumer list ships, not
   the list of four), §3.4 (cost answer), §1A HC-3A / §9 T1 (the determinism answer),
   §8 (the graph delta, five nodes).
3. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md`
   — the document whose §1 this handoff retires (§2 and §3 do not expire and are
   restated as surviving, by reference).
4. The frontend's four open questions as the intention answers them (§5.4).
5. `implementation/archGraph_mapping_mantainance/open/` — both tooling findings,
   **before** any `archgraph_repair_anchors` call (one operation per call).

## 3. Files expected to change

- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_<date>.md` —
  **new** (date stamped at authoring time).
- `.archgraph/` — the closeout delta, one batched `apply_changes`: the four projection
  node descriptions (`…-task-budget-status`, `…-worker`, `…-task-budget-allocations`,
  `…-task-production-time`) plus `projection-item-economics-task-price-scenario`'s
  transitive dependency, `reads_from` edges to the step-state-record table node as the
  vocabulary allows; keep (never restate) the budget-allocations node's existing HC-5
  invariant (§8).
- Nothing under `app/`.

## 4. Ordered tasks

1. **Run the docs guard before writing**: `PYTHONPATH=. pytest tests/unit/docs/` —
   the tripwire's roots cover all of `docs/handoff/` (master plan §5; it broke a
   running session once). Run it again after writing.
2. Author the handoff. One section per obligation, in the §7 table's order; every
   numeric claim (bounds, modes, windows) cited to the intention section that derives
   it; every code reference `path:symbol`.
3. The graph delta (orient with `archgraph_status` first; evidence summaries carry no
   counts; symbol anchors preferred, never symbol+span on one entry).

## 5. Acceptance criteria

Charter rule 1's exemption applies to none of these — the docs guard is automated, and
the content criteria are review-checklist rows for the phase reviewer (each obligation
gets one row, per the blanket-claim rule: a grouped claim needs one probe per member):

- **C1** — obligation 1: the go-live statement names the interim verdict-suppression
  flag as retired and cites the 2026-08-19 document's §4 as the promise being kept.
- **C2** — obligation 2: the new document edits nothing in place; it states explicitly
  that the 2026-08-19 document's §2 correction and §3 warning survive.
- **C3** — obligation 3: the 2026-08-18 "Live time" correction (client ticking
  superseded; smoothing from time-of-receipt legitimate).
- **C4** — obligation 4: all four open questions answered, each citing its intention
  section (§3.4 cost; §4.1 all-fields; §2.5A the **eight-row** consumer list; HC-3/T1).
- **C5** — obligation 5: the three decrease modes with the per-event client rules of
  §6A C in full (≤ 1 s rounding; disowning drops — record deletion NOT named as a
  cause; D8 settlement window dip-and-recover); snap down, never clamp; no `as_of`
  field exists by their own request (D4).
- **C6** — obligation 6 / graph: five nodes updated, edges recorded, `archgraph_status`
  returns 0 stale / 0 diagnostics after the batch; evidence spans verified by reading
  the `anchors` block (the hash does not cover anchors — master plan §5 lineage).
  **Carried from phase 1 review r1, N6 (its stated carry-forward target):** phase 1's
  `reads_from` edge summary reads *"issues **one** batched probe"* — a count inside
  an evidence summary, which is immutable through both review and maintenance
  (master plan §5: describe what the evidence shows, never how many). It cannot be
  edited in place; closing it means rejecting and re-recording that item, which is
  the owner's adjudication to make. This criterion carries the item to the owner
  with that framing — it is not a licence to re-record unilaterally.
- **C7** — `pytest tests/unit/docs/` green before and after; suite baseline unchanged.

## 6. Notes

- Projection gate: **WAIVED for this phase** — documentation only, no mechanism; the
  waiver line lives in the master plan tracker note per charter.
- Review: full round regardless — the valuation pipeline's doc phase drew 24 findings
  across three rounds, and every blocking one was in coordinator-authored prose.
- The frontend reads this document with no access to our tree: every instruction must
  execute from their side alone (no internal symbol soup in client-facing sections;
  `path:symbol` only in the provenance appendix).

## 6A. Carried notes from phase 2 (closeout record, not criteria)

- **The section-weight input is unguarded for *any* wrong value, not only a live one**
  (re-review r5 N3). Phase 2's B1 row pins the live direction, which was this phase family's
  to owe; the wider gap — nothing in the budget-division family observes what
  `typicals_by_section` carries — is **pre-existing coverage debt that phase 2 did not
  create**. Recorded here so the closeout handoff can name it honestly rather than implying
  the weights are fully guarded.
- **What phase 2's two-serve byte-identity rows actually guard** (re-review r5 F-R4): the
  loader-invocation total across two serves, and payload determinism at whole-second
  granularity under a frozen clock. They are **not** an open-record determinism guard — no
  mutation exists that they alone catch, established structurally, not by exhaustion. Any
  future reader tempted to lean on them should read plan 2 §7's r5 entry first.
- **The published approval baseline** (master plan §7, closeout obligation 7) is the
  reference point `narrow_typical_work_times` D23 builds on: phase 2 approved at `efd6b99`,
  suite 26 / 2479 / 1, failure-ID set unchanged from master §6. The closeout handoff states
  the tree **and** the ID set, never a bare count.

## 7. Review log

(empty — append-only)
