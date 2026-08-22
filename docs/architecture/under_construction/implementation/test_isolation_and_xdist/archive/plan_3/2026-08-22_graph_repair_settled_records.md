---
plan: 3
role: maintenance
round: 1
date: 2026-08-22
project: test_isolation_and_xdist
---

# Session prompt — architecture-graph repair of three settled records

## 1. Role and authority

You repair three `human_confirmed` architecture-graph records that phase 3 invalidated. You are
**not** reviewing phase 3's code and you write **no** project document except your handoff.

**The charter's default is that agents never promote, reject or edit review items — the human
adjudicates. The owner has authorised this session to do so.** Review r4 raised it as a decision
card; the owner answered **yes** on 2026-08-22, accepting the recommendation:

> *"a maintenance session repairs the addresses and the one stale sentence; the graph matches the
> code again."*

That authority covers **exactly the three records named in §3** and nothing else. Every other node,
edge and pending item in the graph is out of bounds.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Branch `feat/test-isolation-xdist`. **This prompt names no HEAD and no line numbers, on purpose.**
Two earlier attempts at this session were blocked by gates that named a moving value: one pinned a
bare `HEAD` that the commit adding this prompt falsified, and one carried a drift table that fix r5
invalidated by adding rows to the file being repaired. Master plan standing rule 8 — write the
check against what the gate protects, in a form another session cannot falsify. **Record the SHA
you observe at the start of your run and derive every span from that working tree.**

**Read first, by absolute path:** `/Users/davidloorenz/agent-skills/pipeline-charter.md`
(its **project-affordance** section on the architecture graph, and **"The owner layer"**).
Then `handoffs/reviewer/2026-08-22_phase3_review_r4_handoff.md` **§6 and N3** — N3 carries the
measured drift table you are repairing, and §6 records how the four pending items were adjudicated
hours ago, including the one override and its reasoning.

## 2. Gate check — stop and report if any is false

- `archgraph_status` reports **194 nodes, 291 edges, 0 pending, 0 diagnostics**, `staleNodeCount` 0,
  revision `0dd6785a…`.
- `git status --porcelain` is empty.
- `permissionMode` is `review`; `allowMaintenance` and `allowAnchorRepair` are both true.
  **`allowAnchorRepair` is a launch-time server flag, not graph state** — if it reads `false`, this
  session's MCP server was started without `--auto-anchor-repair` and no amount of graph inspection
  will change it. Stop and report that specifically; it is a configuration fix on the operator's
  side, not something to work around. *(This happened on 2026-08-22: the Codex server's argument
  list carried `--uto-anchor-repair`, a typo the server accepted silently instead of rejecting, so
  the flag was simply absent. The session stopped at this gate, correctly.)*
- **No implement, fix or review round is in flight.** This session repairs anchors that point into
  `app/tests/database_isolation.py` and `app/tests/integration/infrastructure/test_database_isolation.py`
  — the exact files a fix round edits. A concurrent round both dirties the worktree and moves the
  targets, so a repair applied during one is stale before it lands. *(Measured 2026-08-22: fix r5
  ran concurrently, dirtied two documents, and moved one recorded symbol from line 537 to 614 while
  this session was checking its gate.)* If `handoffs/implementer/` holds a handoff the coordinator
  has not yet consumed, that is not by itself a blocker — but an uncommitted worktree is.

If the revision has moved, someone has written to the graph since review r4 — stop and report
rather than repairing on top of an unknown change.

## 3. What is wrong, measured

The three records were confirmed at revision `f5bf3a7` on 2026-08-21 at 19:07, against the
**pre-phase-3** tree. Phase 3 then added roughly seventy lines to `app/tests/database_isolation.py`
and every address below moved. Review r4 measured the drift; **verify each against the file
yourself before repairing it** — a stale table repaired blindly is a second wrong answer.

| record | evidence entry — the symbol to locate |
|---|---|
| `node:infrastructure-test-database-isolation` | `DatabaseIsolation.start` |
| — | `_drop_database_if_exists` |
| — | inline `assert_disposable_database` |
| — | `isolated_database` (in `app/tests/conftest.py` — review r4 found this one **unchanged**; confirm before touching it) |
| `node:test-database-isolation-contract` | `resolve_worker_database_name` |
| — | `_migrate_and_assert` |
| — | `test_dev_database_counts_are_untouched` |
| `edge:…--configured_by-->test-database-isolation-contract` | `_ensure_template` |

**The recorded spans are in the graph itself — read them with `archgraph_get_review_item` or
`archgraph_get_node`, do not take them from any prompt.** Locate each symbol in the working tree
and derive its current span there. Review r4's N3 table measured these on 2026-08-21; **fix r5 has
since moved at least one of them** (`test_dev_database_counts_are_untouched`, 537 → 614), which is
why this prompt carries symbol names and not numbers. Treat r4's numbers as evidence that drift
exists, never as the drift's current value.

**The substantive one, and the only one needing judgment.** That last edge's evidence *summary*
reads:

> *"An existing template is reused only when it carries the marker, its Alembic head and
> **public-table count match the expected constants**…"*

`_ensure_template` today checks the marker, the **derived** head, `REQUIRED_PUBLIC_TABLES ⊆
public_table_names(template)`, and the absence of the legacy baseline column. **There is no count
and there are no constants** — task 6 deleted that mechanism deliberately, and removing it was one
of phase 3's objectives (the carried "N4 time bomb"). The record now describes the brittle rule the
phase existed to remove.

## 4. The mechanism that decides your sequence

**An evidence summary is immutable.** No write path can edit one — measured 2026-08-21. So the two
repairs are different operations and must not be conflated:

- **Addresses** → `archgraph_repair_anchors`. Mechanical and audited; prior addresses are preserved
  under `metadata.evidenceHistory`, as review r4's two corrections were.
- **The wrong summary** → **reject and re-record.** A re-record under the same id **re-enters the
  review queue**, so the corrected record needs a **second pass** to reach `human_confirmed` again.
  Plan for two passes, and **do not report it as confirmed until you have actually confirmed the
  re-recorded version.**

Preview before applying, every time: `archgraph_preview_maintenance_changes` /
`archgraph_preview_review_decisions` before their apply counterparts.

## 5. What the corrected summary must say

Write it from the code, not from the old sentence with the wrong clause struck out. The rule
`_ensure_template` actually implements today is: **an existing template is reused only when it
carries the disposable marker, its Alembic head equals the head derived at runtime from the
migration scripts, it contains every required public table, and it does not carry the legacy
baseline column; otherwise it is dropped and rebuilt.** Check that against
`app/tests/database_isolation.py` before you write it — that sentence is a reading, and yours is
the authority.

Keep the summary at the same architectural granularity as its neighbours: the rule, not the
function's line-by-line behaviour.

## 6. Scope fences

- **Only the three records in §3.** The four items promoted by review r4 at revision `0dd6785a…`
  are freshly correct — do not touch them.
- **No source file is edited.** You read `app/tests/database_isolation.py` and
  `app/tests/conftest.py`; you write nothing under `app/`.
- **No project document** — no plan, no master plan, no intention. The Review-log line is the
  coordinator's.
- **No new nodes or edges.** If you find something the graph is missing, report it in the handoff;
  recording it is a separate authorization.
- If a repair turns out to need rejecting a record you were not authorised to reject, **stop and
  raise a decision card** rather than widening your own mandate.

## 7. Evidence budget

**L4 budget: 0.** You ship no code and hand over no tree. Verification is reading the named symbols
in the two files and comparing them to the records — no test run answers any question here.

## 8. Closing protocol

Deposit **one handoff** at
`handoffs/maintenance/2026-08-22_graph_repair_settled_records_handoff.md` with charter frontmatter
(`plan: 3`, `role: maintenance`, `round: 1`, `state`, `date`, `actor`).

Contents, in order:

1. **Owner-readable opening**, 3–5 sentences, no jargon: what was wrong, what you fixed, whether
   anything still needs the owner.
2. **`⚠ OWNER DECISIONS REQUIRED (n)`** in the charter's card format, or one line saying nothing
   needs them.
3. **Per record**: what it claimed, what you verified in the source, the operation you applied
   (anchor repair vs reject-and-re-record), and for the re-recorded one **both passes**, stated
   separately — the re-record, then the confirmation.
4. **The corrected summary, quoted in full**, beside the one it replaces.
5. **Final `archgraph_status`** — node count, edge count, pending count, diagnostics,
   `staleNodeCount` — and the **revision hash**. Node and edge counts should be unchanged at
   194/291: this is a correction, not a topology change. If they moved, explain why.
6. **Your full write perimeter** — every `.archgraph` path touched, including the audit record.
   `git status --porcelain` should show `.archgraph` paths and your handoff, nothing else.
7. Your final chat message follows the charter's **owner layer** — what you did, what it means in
   plain words, what happens next, what needs them. Not a paste of the handoff.

The handoff file, not your chat message, is what the coordinator consumes.
