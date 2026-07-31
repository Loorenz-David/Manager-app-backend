# Review prompt — System Transition Reasons, Phase 0: inventory & verification

You are performing an independent, adversarial review. Work from the repo files; assume no prior
conversation. Do not fix anything — report.

This phase produced **no production code**. So the usual review reflexes do not apply: there is no
diff to scrutinise for correctness. What you are reviewing is whether the **evidence is real,
reproducible, and complete** — because eleven phases are about to be built on it.

## Inputs

- Plan under review: `.../system_transition_reasons/PLAN_system_transition_reasons_phase0_inventory_20260731.md`
- Implementer prompt: `.../codex_prompts/PROMPT_phase0_inventory.md`
- Master plan (incl. the new "Phase 0 inventory" section and decisions T1–T8)
- Intention: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Checklist

- [ ] **Re-derive at least three figures yourself** from the recorded query text. If a number cannot
      be reproduced, or the query text is missing, that is a finding regardless of whether the
      number looks plausible.
- [ ] Every figure names the database it came from. An unattributed number is a finding — phase 8
      sizes a data migration from these.
- [ ] **Re-run the read-path audit independently**, from the model outward, and diff your list
      against theirs. This is the highest-value check in the review: the audit becomes phase 2's
      checklist, and a missed path ships broken in phase 3, in production, on the deploy that is
      supposed to *fix* an outage. Anything you find that they missed is a blocking finding.
- [ ] The audit contains the three runtime call sites named in the intention
      (`_clock_worker_shift.py:200`, `transition_step_state.py:274`, `_step_transition_core.py:114`).
      Absence proves the method was wrong.
- [ ] The audit covers **analytics and serializer** paths, not only command paths — the kiosk
      clock-out composite, the linear-timeline services, the breakdown endpoint, and
      `domain/users/serializers.py`.
- [ ] `IntegrityError` reproduction was **executed**, on a **disposable** database, and the outcome
      recorded either way. An inspection-only answer, or one run against the shared database, is a
      finding.
- [ ] Slug-consumer audit actually searched outside the backend source: handoff documents, exports,
      reports, webhooks, API response shapes. A one-line `grep app/` is not this audit.
- [ ] Label-resolution strings recorded for all three system rows, verbatim.
- [ ] **No production code changed.** `git status` / `git diff` shows only the master plan and the
      plan file. Read the diff yourself — do not take the Review log's word for it. (Phase 7 of the
      previous feature set shipped an out-of-scope production change that only a diff read caught.)

## Adversarial probes

- Pick the two least convenient figures — the ones that most constrain phases 8 and 9 — and
  reproduce them. Convenient numbers get less scrutiny from the person producing them.
- Look for a read path that resolves a pause reason **indirectly**: through a relationship, a
  serializer that reflects model fields, or a cached map built elsewhere. Direct `pause_reason_id`
  references are the easy half of the audit.
- Check whether anything resolves a pause reason in a **migration** — those are read paths too, and
  phase 8 will run alongside them.
- If the report claims the intention was correct on every point, be suspicious. The intention was
  written from static tracing by a single reader; a genuine measurement pass normally corrects
  something.

## Verdict

End with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line where applicable,
violated criterion, severity). Record findings in the plan's Review log; that should be the only
file you modify.

Note for `NEEDS_CHANGES`: "the evidence is incomplete" is a legitimate blocking verdict here even
though nothing is broken. Eleven phases inherit this. Incomplete evidence is a defect.
