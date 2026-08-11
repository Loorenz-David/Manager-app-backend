---
name: archgraph-discrepancies
description: Report and fix discrepancies between the architecture graph (.archgraph) and the actual code. Use when any agent in the build flow (intention-shaper, mechanism-inventory, implementation-planner, implementation-executor, plan-reviewer) finds a graph node that disagrees with what the code says — file the finding, do not work around it silently. Also use when a session's job IS to fix filed discrepancies and drive a capability's nodes to human_confirmed.
---

# Architecture Graph — discrepancy reporting and repair

Two roles. Read the one that applies, then the shared context.

**Ledger:** `docs/architecture/under_construction/implementation/archGraph_mapping_mantainance/`

---

## Shared context — read first

Most of this graph is **unverified**. Records carry an `origin`:

- `human_confirmed` — independently re-derived from source and promoted. Trustworthy.
- `ai_inferred` — one AI session asserted it and nobody checked. A lead, not a fact.

As of the last count: 29 confirmed, 244 pending. Check `origin` on any node before
relying on it — `archgraph_search_nodes` returns it, `archgraph_get_node` shows it
with review state.

### Where the errors actually are

From an independent review of 43 records, errors clustered in exactly two places:

- **Rationale** — any sentence explaining *why*. The worst case invented a reason for
  a column having no foreign key while the real reason sat two lines away in that
  column's own comment. An invented "why" sitting next to a documented one is the
  strongest signal in the graph.
- **Enumeration** — any count. "The four analytics tables", "three copies",
  "five drivers". Several were faithful transcriptions of *stale code comments*.

Descriptions of **mechanism** — what the code does, what calls what, which table a
command writes — held up well.

So: be efficient on mechanism claims, and spend your attention on any description
that supplies a reason or a number.

### The anti-pattern

Reading a node's stored `inferenceReason`, finding it plausible, and treating that as
confirmation. That is not verification — it re-reads the assertion under examination
and manufactures confidence without adding information.

**Open the cited lines and say what the code does in your own words BEFORE reading the
stored claim.** This is step 4 of `.archgraph/agent-operating-policy.md` and it is the
single rule that catches what structural validation cannot: the server checks that a
file exists and a hash matches, never that the cited code *means* what the claim says.

---

## Role A — Reporter (any agent in the build flow)

You are not here to fix the graph. You are here so the finding is not lost.

**When you hit a discrepancy: file it, then carry on with your actual task.** Do not
detour into a review workflow, do not attempt maintenance mutations, and do not
silently work around the wrong node.

File one when a node's claim disagrees with the code, when its evidence points at a
moved or deleted address, when a description supplies a rationale the cited lines do
not support, when a count is wrong, or when something load-bearing is missing from the
graph entirely.

### How to file

One file per graph item, in the ledger's `open/` directory. Name it after the item id
with `:` and `/` replaced by `-`, e.g.:

    open/node-analytics-reconcile-user-day-time.md
    open/edge-command-transition-step-state--writes_to--table-task.md

If the file already exists, **append a new finding block** rather than overwriting —
two agents finding the same node is signal, not conflict.

Use `TEMPLATE.md` in the ledger root. The essential discipline: record **what you
observed in the code, with `path:line`**, separately from **what you concluded**. An
observation is checkable; a conclusion is another inference. The fixer re-derives
independently, so give them addresses to check rather than a verdict to agree with.

Keep it short. Five minutes, not fifty. If a finding is turning into an investigation,
file what you have with `confidence: low` and move on.

---

## Role B — Fixer (a session dedicated to graph repair)

Requires the MCP server started with `--allow-review`. Check
`archgraph_status.permissionMode` includes `review` before starting; if it does not,
stop and say so rather than working around it.

Follow `review-inferred-architecture` in `.archgraph/agent-operating-policy.md`. What
follows is what that workflow does not tell you, learned by getting it wrong.

### Order of work

1. Read the filed finding's **cited addresses only** — not its conclusion.
2. Open those lines and state what the code does, in your own words.
3. *Then* read the stored graph claim and the reporter's conclusion. Where your reading
   and either of them disagree, that disagreement is the finding.
4. Recommend a decision. **Never enact one on your own judgment.**

### Choosing the decision

| Situation | Decision |
|---|---|
| Claim is wrong, and was always wrong | `reject` |
| Claim was true; the code deliberately removed what it described | `deprecate` — preserves the provenance of a property the codebase genuinely had |
| Claim holds; only its address moved | `promote` **with** `anchors` — same claim, corrected location, one authorization |
| Claim holds; wording is incomplete or invented | `edit` |
| Cannot settle it from source | `investigate` — say what evidence would settle it |

Prefer `deprecate` over `reject` for superseded-but-once-true records. Rejecting a
correct-at-the-time item destroys its provenance and sends a rebuilt copy to the back
of the queue.

### Five things that will bite you

1. **`decisionSetHash` does NOT cover anchors or rationales.** Two previews — one
   applying a re-anchor, one silently dropping it — produce identical hashes. Verify a
   preview by reading its `anchors` blocks, never by comparing hashes. (Unconfirmed:
   whether `edit` payloads are also excluded. Assume they are.)

2. **Do not re-anchor an evidence entry onto a different target.** If a summary
   accurately describes file A, repointing it at file B severs summary from target.
   Anchors carry location only. If you want to reword the summary, the *claim* is what
   is wrong and re-anchoring is not the tool — and summary text is immutable through
   both review and maintenance, so that means `reject` and re-record.

3. **Adding a citation is additive, not a re-anchor.** To attach a new supporting
   document to a node: `promote` as-is, then record a `source_link` through
   `archgraph_apply_changes` as a separate act.

4. **Review records are size-capped** (16384 bytes) and rationale text counts toward
   the cap. Batch size is bounded by prose, not item count — roughly 12-15 decisions
   with short rationales. If one item's reasoning breaks the cap, split that item out
   rather than trimming the reasoning. The reasoning is the product.

5. **`deprecate` and `edit` do not retire an item** from the pending count — only
   `promote` and `reject` do. A deprecated node still needs a decision eventually.

### Closing a finding

Move its file from `open/` to `resolved/`, and append the outcome: the decision
applied, the audit record filename under `.archgraph/reviews/`, and — if your reading
disagreed with the reporter's conclusion — what the disagreement was. That last part is
how the flow learns.

**Applied review decisions modify `.archgraph/architecture.yml`, which is tracked.**
Say so in your report; it needs a commit.

---

## The gate

The objective: **by the time a capability reaches implementation planning, every graph
node its plans will cite is `human_confirmed`.**

Check it before compiling implementation prompts:

1. `archgraph_get_neighbors` (or `archgraph_compute_impact`) from the capability's
   entry nodes to enumerate what its plans will actually reference.
2. For each, read `origin`.
3. Any `ai_inferred` in that set is a gate failure — either fix it or drop it from the
   plan's citations. A plan citing an unverified node inherits its error silently.

Report the gate as a count, not a feeling: *"14 of 14 cited nodes human_confirmed"*.

Nodes outside that set stay pending. That is deliberate — bulk review is not
proportionate, and pending is an honest state that blocks nothing.
