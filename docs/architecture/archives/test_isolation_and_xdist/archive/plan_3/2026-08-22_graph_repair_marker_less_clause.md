---
plan: 3
role: maintenance
round: 2
date: 2026-08-22
project: test_isolation_and_xdist
---

# Session prompt — one graph record, one clause

## 1. Role and authority

**One record. One corrected summary. Nothing else.**

The owner authorised correction of the three settled records phase 3 invalidated (review r4's
decision card 1, answered **yes** on 2026-08-22):

> *"a maintenance session repairs the addresses and the one stale sentence; the graph matches the
> code again."*

Round 1 did that. **This is a second correction to the same record, because the coordinator drafted
the replacement wording and it dropped a clause.** Same authority, same record, one operation.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`

**Read first, by absolute path:** `/Users/davidloorenz/agent-skills/pipeline-charter.md` — its
architecture-graph affordance section and **"The owner layer"**.

## 2. Gate check — stop and report if any is false

- `archgraph_status`: **194 nodes, 291 edges, 0 pending, 0 diagnostics**, `staleNodeCount` 0.
- `permissionMode` is `review`; `allowMaintenance` and `allowGraphWrite` are true.
  *(`allowAnchorRepair` is not needed this round — no address moves.)*
- `git status --porcelain` is empty, and no implement/fix/review round is in flight. This session
  writes only `.archgraph/` and its handoff, but a round in flight moves the code the record
  describes.

*(Gates here name no HEAD and no line numbers — standing rule 8, earned five times in this project.
Derive spans from the tree you observe and record the SHA you observed.)*

## 3. The record and what is wrong with it

`edge:infrastructure-test-database-isolation--configured_by-->test-database-isolation-contract`,
`human_confirmed`, evidence pointing at `DatabaseIsolation._ensure_template`.

Its evidence summary currently reads:

> An existing template is reused only when it carries the disposable marker, its Alembic head equals
> the head derived at runtime from the migration scripts, it contains every required public table,
> and it does not carry the legacy baseline column; **otherwise it is dropped and rebuilt.**

**The bolded clause is false for the marker-less branch, and false in the dangerous direction — it
describes the destructive guard as more destructive than it is.** Read `_ensure_template` and
confirm before you act. What it does when the marker is absent:

- **public table count is 0** → the shell is absorbed: dropped, recreated, marked, migrated.
- **any public tables present** → **`UnsafeDatabaseError`, refused outright.** Not dropped. Not
  rebuilt.

That refusal is the protection that stops the machinery replacing a real database whose name merely
matches the template pattern. A record telling a future session it gets dropped and rebuilt is
worse than a record that says nothing.

**Provenance, so the record is honest about how this happened:** the original summary was wrong in
a different way — it required a *public-table count matching expected constants*, a mechanism
phase 3 deliberately removed. Round 1 replaced it with wording the coordinator drafted in the
round-1 prompt, and that draft covered the reuse conditions while omitting the marker-less branch
entirely. The session was told the sentence was "a reading, and yours is the authority"; it
verified the clauses it was given rather than auditing for the one that was missing.

## 4. The operation

**Evidence summaries are immutable** — `archgraph_apply_maintenance_changes` cannot touch a summary
or an inferenceReason. So:

1. **Delete** the edge (maintenance change, previewed then applied).
2. **Re-record** it with `archgraph_apply_changes` — same edge id, same `configured_by` type, same
   source and target, same evidence path and symbol, **corrected summary**. It lands as
   `ai_inferred` and re-enters the review queue.
3. **Confirm it** on a second pass via `archgraph_preview_review_decisions` /
   `archgraph_apply_review_decisions`, reading it back with `archgraph_get_review_item` first.

**Do not report it as confirmed until the re-recorded version is actually confirmed.** Preview
before every apply.

Preserve the edge's `description` as it stands — *"The lifecycle's database names, template-reuse
rules and destructive-operation guard are all decided by the isolation contract; changing the
contract changes what this lifecycle may create, reuse or drop."* Only the evidence summary is at
fault.

**Expect the `conflicting-canonical-relationship` warning** on the re-record: a second
`configured_by` edge from the same source targets `configuration-shipped-pytest-parallel-default`.
Review r4 evaluated and overrode it — `configured_by` declares a direction, not a cardinality, and
two configuration nodes legitimately configure one infrastructure node. Record that you evaluated
it; do not treat it as new.

## 5. Suggested summary — a reading, not the authority

Write it from `_ensure_template`, and **audit it for branches this draft omits** — that omission is
the entire reason this round exists:

> An existing template is reused only when it carries the disposable marker, its Alembic head
> equals the head derived at runtime from the migration scripts, it contains every required public
> table, and it lacks the legacy baseline column; a *marked* template failing any of those is
> dropped and rebuilt. A marker-less template is not rebuilt by default — it is refused outright
> with `UnsafeDatabaseError` if it still has public tables, and absorbed only if it is an empty
> shell.

Keep it at its neighbours' granularity: the rule, not a line-by-line trace.

## 6. Scope fences

- **This one edge.** Every other node, edge and record is out of bounds, including the two nodes
  round 1 repaired and the four items review r4 promoted.
- **No source file is edited.** You read `app/tests/database_isolation.py`; you write nothing under
  `app/`.
- **No project document** — no plan, no master plan, no intention. The Review-log line is the
  coordinator's.
- **No new nodes or edges** beyond re-recording this one under its existing id.

## 7. One thing to report but not fix

Round 1 recorded, and the coordinator confirmed, that a **different** record carries a stale
reference *inside* an immutable summary: `node:infrastructure-test-database-isolation`'s
`_drop_database_if_exists` evidence says *"passes the result to assert_disposable_database (lines
81-107)"*, and that function now sits at **148-175**. It is a line reference embedded in prose, so
anchor repair cannot reach it and only a reject-and-re-record would.

**Do not fix it.** Confirm the current span, state it in your handoff, and say plainly whether you
judge it worth a third re-record or worth leaving — the coordinator will route it. Two re-records
of settled records in one day is already more churn than this graph should see.

## 8. Evidence budget

**L4 budget: 0.** No test run answers any question here. Verification is reading
`_ensure_template` and comparing it to the record.

## 9. Closing protocol

Handoff at `handoffs/maintenance/2026-08-22_graph_repair_marker_less_clause_handoff.md`,
frontmatter `plan: 3`, `role: maintenance`, `round: 2`, `state`, `date`, `actor`.

1. **Owner-readable opening**, 3–5 sentences, no jargon.
2. **`⚠ OWNER DECISIONS REQUIRED (n)`**, charter card format, or one line saying nothing does.
3. **What you read in `_ensure_template`**, including the branches, so the correction is traceable
   to code rather than to this prompt.
4. **The delete, the re-record, and the confirmation — as three separate steps**, each stated.
5. **The corrected summary quoted in full**, beside the one it replaces.
6. **§7's stale inline reference**: the span you measured and your recommendation.
7. **Final `archgraph_status`** — counts, pending, diagnostics, `staleNodeCount`, revision.
   Expected **194 / 291 / 0 / 0**; a change in counts means something went wrong.
8. **Your full write perimeter** — every `.archgraph` path including audit records.
9. Your final chat message follows the charter's **owner layer**. Not a paste of the handoff.
