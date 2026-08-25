---
plan: plan_2
role: review
round: 1
date: 2026-08-25
---

# Independent review — Plan 2 task budget-signal service and serializer

Review the implemented Plan 2 checkpoint in
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.
Invoke the `plan-reviewer` skill and follow its doctrine. You did not implement this phase;
derive the result independently. The plan is authoritative where this prompt differs.

## Gates

Confirm from source before reviewing:

- the intention header is `RATIFIED`;
- Plan 1 is `APPROVED` and Plan 2 is `IMPLEMENTED` in the master tracker;
- `HEAD` is checkpoint `8a63402` with subject `CHECKPOINT (not approved): task budget signal phase 2`;
- no uncommitted change touches a Plan 2 executable/test file.

If a gate fails, write a blocked review handoff and do not assess the phase as approved.

## Read order

1. Master plan §§1, 5–10, particularly the phase-2 file perimeter, graph protocol, and test
   baseline rules.
2. Ratified intention sections named in Plan 2 §2.
3. `plans/plan_2.md` in full, including every criterion, all 18 named mutations, and Review log.
4. Implementer handoffs rounds 1, 2, and checkpoint closeout; maintenance round 1 handoff.
5. The actual changed service, serializer, C19 contract test, Plan 2 integration test, and the
   two approved maintenance test files. Maintenance tests are a separately authorized baseline
   repair, not orphan Plan 2 tests.
6. Architecture graph: status and the new budget-signals projection node only. Do not write,
   build context, or adjudicate reviews.

## Review scope

Perform a first-review full checklist against C1(a)–C8(d), all mechanism contracts, the test
trace map, each mutation record, declared write perimeter, no-existing-output-change rule, C19
allocator-consumer contract, and the maintenance repair's order-independence claims. Reuse the
tree-bound implementation and maintenance evidence where it matches; spend new effort on
variation rather than repeating the identical 18 mutations.

Pay special attention to: evaluation-current/deletion predicates; the exact raw-list cap before
query; no-budget construction; fixed ten-key flat envelope; snapshot-vs-live-basis money;
strict live-seconds indexing and `ctx.now`; deterministic task order; statement-count scope; and
whether the C10 maintenance repair preserved category-to-result mapping rather than merely
weakening an ordering assertion. Check that serializer changes are additive-only.

This review's L4 budget is exactly **1** run: `PYTHONPATH=. pytest -m 'not e2e'` on the review
tree, with failing-ID delta against the durable 21-ID baseline. Use L1/L2 for all other checks.
Any mutation probe must be applied-and-reverted, checksum-verified, and declared in the handoff.

## Closeout

Do not fix code. Write
`handoffs/reviewer/20260825_plan_2_review_round_1.md` with verdict `APPROVED` or
`CHANGES_REQUESTED`, technical findings, owner cards if needed, verified-correct items,
mutation-probe declaration, evidence identity, carry-forward dispositions for any notes, and
owner-layer final response. Update only the Plan 2 tracker row and Review log after reaching
your verdict. Plan 3 remains blocked unless Plan 2 is `APPROVED`.
