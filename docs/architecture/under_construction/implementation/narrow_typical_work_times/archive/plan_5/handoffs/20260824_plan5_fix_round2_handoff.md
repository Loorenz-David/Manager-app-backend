---
plan: plan_5
role: fix
state: IMPLEMENTED
date: 2026-08-24
actor: Codex
---

# Plan 5 fix round 2 handoff

## Summary

Resolved all five coordinator findings from round-1 consumption. The fix's code perimeter is
empty: production remains byte-identical to checkpoint `8a4a1cb`. The only `app/` change is the
phase test file: one inert C8 test was deleted and C1(c)'s brittle source scan was replaced by a
delegating spy. The plan now states C5(i)'s exact literal and the round-1 handoff's baseline
description is corrected.

⚠ OWNER DECISIONS REQUIRED (0)

No new owner decision is required in this fix round. The round-1 settled graph-description
authorization remains carried as an earlier handoff item; this fix made no graph change.

## F1–F5 disposition

- **F1 — fixed.** Deleted `test_c8_narrowing_changes_the_published_number_and_basis`. It drove
  `_TypicalSession`, whose `execute()` discards SQL and supplies both populations by hand, and
  passed under total loss of narrowing. The SQL-backed
  `test_c8_divergent_fixture_measures_narrowed_600_against_section_375` is the sole C8 proof.
- **F2 — verified at the corrected site.** Temporarily changed the production derivation line
  `specs = (spec,) if spec is not None and spec.is_narrowing else ()` to `specs = ()`. The exact
  C8 test reddened at `assert 375 == 600`, as required. The production mutation was reverted.
- **F3 — fixed by derivation.** Under C5(i), using all task sections makes `narrowed_uniform`
  false. The real section contributes its section-wide median `375`; the excluded section has
  zero evidence and receives the usable-value fallback `375`; therefore the mutated two-section
  total is `375 + 375 = 750`. The plan now states `750` explicitly.
- **F4 — fixed and probed.** Replaced the `inspect.getsource` substring scan with a delegating
  spy on `working_sections.get_working_section_typical_times`'s imported
  `typical_times_statement`. The contract asserts that the call has no `now` kwarg. Temporarily
  adding `now=ctx.now` produced the exact red `assert "now" not in {"now": datetime(...)}`;
  the read-only production file was reverted.
- **F5 — fixed in documentation.** The round-1 67-case slice was post-test-authoring and
  post-production-edit: the old query file contributed 52 and the new file contributed 16. No
  pre-edit baseline was captured for these two phase files. The honest comparator is the stable
  21-ID full-suite failure set.

## Coverage and retained evidence

The deleted test was the only orphan; it had claimed C8(a) while failing to issue SQL. The
remaining changed test still maps to C1(c), and the divergent integration test maps to C8(a)/(b).
No new test was added. Round-1 mutation evidence is retained for unchanged assertions; the test
file edit changed only the deleted inert test and the C1(c) instrument. The corrected C8 mutation
and C1(ii) mutation were rerun in this round at their corrected sites.

## Cycle-scoped perimeter

Intended fix writes:

- `app/tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_5.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- this handoff

`git diff` confirms no production change and no other `app/` change. Mutation-probe files are
listed separately from the fix perimeter:

- `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` — C8 definition-site probe, reverted; final md5 `213a38a03f7ffaafe954bae68d4da16a`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` — C1(ii) probe, reverted; final md5 `48833e4438348f2d01bcf2d00f64bb20`
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py` — round-1 probe file, not touched this round; cited final md5 `aff094ded01e15235865bf06c378d8bd`

## Mutation evidence

| mutation | scope and command | observed result |
|---|---|---|
| C8 corrected definition-site `specs = ()` | L1: `test_narrowed_price_scenario.py::test_c8_divergent_fixture_measures_narrowed_600_against_section_375` | failed exactly at `assert 375 == 600` |
| C1(ii) read-only call-site `now=ctx.now` | L1: `test_narrowed_price_scenario.py::test_c1c_working_section_typicals_keep_the_default_statement_clock` | failed exactly because captured kwargs contained `now` |

The 14 unchanged round-1 named mutations and two planted probes remain valid by citation from
`8a4a1cb`; their assertion bodies and production sites were not changed by this round. The two
round-1 probe md5s are preserved above, and the two corrected probes are fresh.

## Verification

- Gate: intention `RATIFIED`, Redis `PONG`, and `git status --porcelain -- app/` was empty before
  the fix.
- Fix slice: **83 passed** across the narrowed price-scenario, price-scenario query, and
  narrowed-task-economics tests.
- Focused Ruff: **all checks passed** for the changed test file.
- Authoritative L4: `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'` → **2707 passed / 21
  failed / 1 skipped / 2 warnings**. The 21 failure IDs are unchanged from round 1; only the
  deleted inert test reduces the pass total by one. No failure-ID delta was introduced.

## Architecture graph and state

No architectural boundary changed, so no graph delta was recorded. The round-1 graph source-link
batch and unresolved settled-description authorization remain unchanged.

State: `IMPLEMENTED`. No candidate criterion was added.
