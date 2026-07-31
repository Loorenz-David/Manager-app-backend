# Review prompt — System Transition Reasons, Phase 1: foundation

You are performing an independent, adversarial code review. Work from the repo files; assume no
prior conversation. Do not fix anything — report.

This phase is half investigation, half additive code. Both halves need a different kind of
scrutiny, and the investigation half is the one that matters more: **eleven acceptance criteria in
later phases inherit its read-path audit.** A missed path ships broken in phase 2 — in production,
on the deploy that is supposed to *fix* an outage.

## Inputs

- Plan under review: `.../system_transition_reasons/PLAN_system_transition_reasons_phase1_foundation_20260731.md`
- Implementer prompt: `.../codex_prompts/PROMPT_phase1_foundation.md`
- Master plan, incl. decisions T1–T8 and the new "Phase 1 inventory" section
- Intention: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Checklist — the investigation

- [ ] **Re-run the read-path audit independently**, model-outward, and diff your list against
      theirs. Anything you find that they missed is a **blocking** finding. This is the single
      highest-value check in this review.
- [ ] The audit covers **analytics and serializer** paths, not only commands — the kiosk clock-out
      composite, the linear-timeline services, the breakdown endpoint, `domain/users/serializers.py`
      — and any path resolving a reason **indirectly**: through a relationship, a serializer that
      reflects model fields, a cached map built elsewhere, or a **migration**.
- [ ] The three runtime call sites from the intention are present. Absence proves the method.
- [ ] **Re-derive at least three figures** from the recorded query text. Irreproducible or
      untexted figures are findings regardless of plausibility — phase 3 sizes a data migration
      from these.
- [ ] Every figure names its database.
- [ ] `IntegrityError` reproduction was **executed**, on a **disposable** database, outcome recorded
      either way. Inspection-only, or run against the shared DB, is a finding.
- [ ] Slug-consumer audit searched outside backend source (handoffs, exports, reports, webhooks,
      response shapes). A `grep app/` is not this audit.
- [ ] Label-resolution strings recorded verbatim for all three system rows.

## Checklist — the code

- [ ] **Zero behaviour change, verified by you**: no existing test modified, no endpoint response
      gains a field, no serializer surfaces `transition_reason`. Read the diff — do not take the
      Review log's word for it. (declared_worker_states Phase 7 shipped an out-of-scope production
      change that only a diff read caught.)
- [ ] `transition_reason` is nullable, indexed, no default, no constraint, on **exactly two** tables.
      **No column on `user_declared_state_records`** (T3).
- [ ] Migration is additive-only and reversible. Run `upgrade` → `downgrade` → `upgrade` yourself and
      confirm the schema is identical.
- [ ] Read tolerance covers **every** audit entry, each with a test that **seeds `transition_reason`
      directly** — the only way to exercise it before writers exist. **Mutate the resolution and
      confirm the tests fail**; nothing writes the column, so these tests can pass vacuously and
      look fine.
- [ ] Label resolution lives in one place and is imported. Duplicated maps are a finding. Its
      location respects `01_architecture.md:43` — `services/queries/` must not import
      `services/infra/`.
- [ ] Precedence when a row carries both representations is asserted, not incidental.
- [ ] The published kiosk `pause_by_reason` / `pause_reasons` contract is unchanged and every key
      still resolves, **including the literal `"unspecified"` key** — that is part of the published
      contract, not an edge case.
- [ ] Query counts unchanged (in-memory map). Verify the listener actually counts by mutating to a
      per-row lookup and confirming the test fails.
- [ ] **`manually_recorded`, the `changed_by_id` heuristic, and the `startswith("par_")` branch are
      all untouched** (T7 / phase 2 scope). Their modification is a finding even if the change looks
      like an improvement.
- [ ] Full suite compared by failure **node set** against a baseline worktree, with `app/.env.testing`
      copied into it. Reject count-only comparisons, and reject any baseline whose totals diverge
      wildly from the recorded canonical figures — that means the worktree was misconfigured, not
      that the tree regressed.

## Adversarial probes

- Pick the two figures that most constrain phases 3 and 4 and reproduce them. Convenient numbers get
  less scrutiny from whoever produced them.
- Delete a read path's `transition_reason` branch and confirm its test fails. If it passes, the test
  was seeding nothing.
- If the report claims the intention was correct on every point, treat that as a signal to look
  harder rather than as reassurance.

## Verdict

End with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated criterion,
severity). Record findings in the plan's Review log; that should be the only file you modify.

Note: "the inventory is incomplete" is a legitimate **blocking** verdict here even though nothing is
broken. Three later phases inherit it. Incomplete evidence is a defect.
