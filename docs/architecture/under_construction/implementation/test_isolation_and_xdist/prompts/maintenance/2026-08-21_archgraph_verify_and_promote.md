---
plan: 1
role: maintenance
round: 1
date: 2026-08-21
project: test_isolation_and_xdist
authority: OWNER-DELEGATED PROMOTION — see §1
---

# Session prompt — verify and promote the three `ai_inferred` archgraph items

## 1. Role, and the authority you have been given

Three items have been sitting `ai_inferred` since phase 1. They were **deliberately not
confirmed** because phase 2 was about to change the code they describe. Phase 2 is now APPROVED
and it did change that code, substantially.

**The owner has explicitly delegated promotion to this session.** Normally the pipeline charter
reserves graph adjudication to a human and forbids agents from promoting — that rule is suspended
here, for these three items only, by the owner's decision. Treat it as real authority and real
responsibility: **what you promote becomes the architecture record, and nobody is going to check
it behind you.**

The one rule that replaces the one being suspended:

> **Never promote content you have not confirmed against the current source. Correct it first, or
> leave it pending and say why. A wrong record promoted is worse than a right one left waiting.**

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Branch `feat/test-isolation-xdist`, HEAD `49ea918`, tree clean.

**Read first, by absolute path, as doctrine:**
`/Users/davidloorenz/agent-skills/pipeline-charter.md`. Then the project's
`docs/architecture/under_construction/implementation/test_isolation_and_xdist/master_plan.md`
— **§6 is the authority on what the code now does**; it is current as of phase 2's approval and
will save you re-deriving the topology.

## 2. The three items

```
node:infrastructure-test-database-isolation   "Serial test database isolation"   (infrastructure, conf 0.96)
node:test-database-isolation-contract         "Test database isolation contract" (configuration,  conf 0.95)
edge:infrastructure-test-database-isolation --configured_by--> test-database-isolation-contract
```

Graph state: 192 nodes, 289 edges, **0 diagnostics, 0 stale, 3 pending**, revision
`4caa1afe361b7906bd6aed854d0ded5897a6927d3e5e9f13f29e81e7177508fc`, permission mode `review`.

## 3. What the coordinator already measured — verify it, do not trust it

Both nodes carry three evidence anchors each. **All six have drifted, and the graph cannot see
it**: every anchor reports `contentChangedSinceInference: "unknown"`, and `staleNodeCount` is 0
because these are *pending* items, not promoted ones. Answering "is it stale?" from that counter
is answering from the wrong instrument.

| node | recorded anchor | actual now |
|---|---|---|
| infrastructure | `DatabaseIsolation.start` @ 127–136 | @ 167 |
| infrastructure | `_drop_database_if_exists` @ 502–534 | @ 463 — **and the file is 496 lines, so the recorded end is past EOF** |
| infrastructure | `conftest.isolated_database` @ 18–30 | @ 23 |
| contract | `resolve_worker_database_name` @ 26–35 | @ 46 |
| contract | `_migrate_and_assert` @ 395–439 | @ 364 |
| contract | `test_dev_database_counts_are_untouched` @ 97–105 | @ 278 |

Phase 2 changed these files by **+184 / −74**.

**Worse than moved lines — three summaries are factually false against current code:**

1. *"Destructive database operations require a strict disposable-name pattern, a non-configured
   database URL, and a marker"* — that is phase 1's **three**-check invariant. It is now **five**:
   name pattern, endpoint confinement, configured-`(host, port, database)` identity,
   marker-or-empty-shell, and URL validity. See master plan §6.3.
2. *"Worker IDs resolve to the bounded names `beyo_test_main` or `beyo_test_gwN`"* — falsified by
   phase 2's slot discriminator. Names are `beyo_test_<slot>_<worker>`; the serial default is
   `beyo_test_main_main`. See §6.2.
3. *"The infrastructure tests assert fixed development row counts"* — **this describes a defect
   that was found and repaired.** Phase 1's review called it out (an absolute count "cannot
   distinguish 'isolation broke' from 'the owner added a workspace'"), and fix r2 replaced it with
   a before/after snapshot within the run. Promoting this summary would re-enshrine the corrected
   defect as the documented contract.

Verify each of these yourself at source. If you find the coordinator wrong about any of them,
**say so** — that is worth more than agreement.

## 4. Procedure

1. **Pull each item** with `archgraph_get_review_item` and read its evidence, inference reason,
   contradictions and uncertainties.
2. **Read the actual code** each anchor points at — `app/tests/database_isolation.py`,
   `app/tests/conftest.py`, `app/tests/integration/infrastructure/test_database_isolation.py` —
   and decide, per anchor, whether the recorded summary is *true of the code as it stands today*.
3. **Correct before promoting.** Anchors get current line spans; summaries get rewritten to what
   the code actually does. The record you leave should be one a reader trusts a year from now
   without re-deriving it.
4. **Judgment call worth making deliberately — the node's name.** It is *"Serial* test database
   isolation", and phase 3 installs `pytest-xdist`. A name falsified by the next phase is a name
   that will need re-reviewing in a week. The mechanism is genuinely per-**process** and always
   was — the worker id has been in the naming scheme since phase 1. Decide whether to rename, and
   record your reason either way.
5. **Check the edge on its own merits.** `configured_by` — confirm the direction is right
   (infrastructure is configured *by* the contract, not the reverse) and that both endpoints still
   describe distinct things rather than one concept split in two.
6. **Preview, then apply.** Use `archgraph_preview_review_decisions` before
   `archgraph_apply_review_decisions`.

## 5. Tooling notes — earned, will save you time

- **The review path batches correctly.** A prior session applied **13 decisions in a single
  call** with no trouble. Do not loop one item per call here.
- **`archgraph_repair_anchors` does NOT batch** — it has a measured one-operation-per-call defect.
  If you use it, one call per anchor. Prefer expressing corrections through the review-decision
  path where you can.
- **Never invent nodes.** Your perimeter is these three items. The other 189 nodes and 289 edges
  are out of scope, including anything you notice in passing — report it, do not touch it.

## 6. Scope fences

- **No code changes.** Not one line, not a comment. This is a records task.
- **No test runs.** Your **L4 budget is 0** and you do not need L1/L2 either — reading source is
  the work. If you think you need to execute something to decide an anchor, that is a signal the
  anchor is describing behaviour rather than structure; say so in your report.
- **Only these three items** may be promoted, rejected or edited.

## 7. Report back

In your final message (no file needs writing):

1. **Per item:** promoted / corrected-then-promoted / left pending — with the reason.
2. **Every correction you made**, old value → new value, so the owner can see what the record
   would have said if it had been promoted unchecked.
3. **Anything you found that contradicts §3** — the coordinator's measurements are claims, not
   authority.
4. **The final graph revision hash**, plus node/edge/pending/stale counts, so the state is
   verifiable afterwards.
5. **Anything you noticed outside the perimeter** and deliberately did not touch.

If any item cannot be made accurate from the current source, **leave it pending and say what is
missing.** Three correct records and a clear explanation beats three promotions and a silent
error.
