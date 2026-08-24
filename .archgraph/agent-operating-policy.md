# Architecture Graph Agent Operating Policy

This is the canonical, client-neutral guide for using Architecture Graph MCP.
Client adapters may point to this document and add entry-point ergonomics, but
they must not replace, weaken or reinterpret it.

## What this policy governs

Architecture Graph has three layers:

1. Protocol guarantees: MCP tool contracts, structured outputs, permission
   modes, path containment, bounded responses and lifecycle behavior.
2. Operating policy: the judgment an agent uses to explore, interpret and
   record architecture.
3. Client adapters: packaging for a particular agent host.

This document governs the second layer. It does not redefine schemas or server
invariants. If an agent ignores this policy, the server must still enforce its
protocol, permission, evidence, revision, duplicate, path and atomicity
guarantees.

## Currently available capabilities

M0–M3 capabilities are always available through MCP; M5 review capabilities
are available with `--allow-review`, and M6.5 maintenance capabilities with
`--allow-maintenance`. The full set is:

- `archgraph_status`
- `archgraph_describe_schema`
- `archgraph_search_nodes`
- `archgraph_get_node`
- `archgraph_get_neighbors`
- `archgraph_compute_impact`
- `archgraph_read_current_context`
- `archgraph_build_context` when started with `--allow-context-write`
- `archgraph_check_duplicates` and `archgraph_apply_changes` when started with
  `--allow-graph-write`
- `archgraph_list_pending_reviews`, `archgraph_get_review_item`,
  `archgraph_preview_review_decisions` and `archgraph_apply_review_decisions`
  when started with `--allow-review`
- `archgraph_preview_maintenance_changes` and
  `archgraph_apply_maintenance_changes` when started with
  `--allow-maintenance`

The default mode is read-only. Architecture Graph MCP never initializes a
workspace. A human must create and initialize `.archgraph` first. If status
reports an uninitialized or invalid workspace, stop and report that condition;
do not try to create files or work around the diagnostics.

Review capabilities (`--allow-review`) let an agent inspect
inferred architecture, explain a review case, compare it against the
implementation, identify contradictions and uncertainties, and **recommend**
a decision — entirely on its own. An agent must never enact a promotion,
rejection, edit, deprecation or removal on its own judgment: every
`archgraph_apply_review_decisions` call requires human authorization through
a channel the model does not control (the MCP client's own approval prompt in
`client-approval` mode, or the VS Code extension's confirmation modal in
`vscode-confirm` mode). A `humanInstruction` string typed into a tool call is
never itself authorization.

Maintenance capabilities (`--allow-maintenance`) carry the same rule and a
sharper edge: review adjudicates what a machine proposed, maintenance corrects
— and can delete — what a human asserted. The flag is deliberately orthogonal
to the read-only → context → write → review ladder rather than the top of it:
authority to adjudicate agent proposals does not imply authority to destroy
human-authored architecture, and neither implies the other. `--allow-maintenance`
requires at least `--allow-graph-write`; supplied without it, the server
refuses to start rather than quietly offering a smaller tool surface.

The VS Code canvas and tree offer the same delete and edit affordances
directly. There the modal confirmation *is* the authorization — no agent sits
between the human and the write, so there is no token to bind one to — but the
mutation runs through the identical shared resolution, discloses the identical
cascade, and writes the identical audit record. An agent must never treat the
existence of that UI as permission to skip its own authorization step.

## Operating rules

### Decide whether the graph applies at all

The graph is a map of meaning: what the architecture is for, where its
boundaries lie, and what a change would touch. Reach for it when the task
concerns this workspace's architecture — explaining a capability, policy or
boundary, understanding relationships and impact, planning or implementing a
change whose consequences cross a boundary, or recording architecture the work
created.

Do not reach for it when it cannot help:

- A general programming question, or work in a repository without an
  initialized `.archgraph`, is not a graph task. The presence of the tools is
  not a reason to use them.
- Symbol-level lookups — where a function is defined, which files match a
  pattern, what a line of code says — belong to the host's own file and text
  search tools. The graph answers "what does this mean and what does it
  affect", not "where is this string"; it is a complement to text search, not
  a replacement for it.
- If reading one known file answers the question, read the file.

When the graph does apply, prefer it as the first step rather than the last:
one search plus one impact computation often replaces many exploratory file
reads, and the node's evidence links point directly at the files worth
opening.

### Inspect status first

Begin every graph-dependent task with `archgraph_status`. Confirm:

- the workspace is initialized and valid;
- node and relationship counts are plausible for the task;
- diagnostics, stale links and the current revision are understood;
- the permission mode is sufficient for the requested action.

Do not rely on an earlier session's status or revision. Re-check before a write
and use the revision returned by the current status call.

### Search before creating

Before proposing a new concept, use `archgraph_search_nodes` with the concept's
name, synonyms and domain terms. Search is required even if a concept appears
obvious. Inspect matching nodes with `archgraph_get_node`; use
`archgraph_get_neighbors` to understand the local branch and avoid creating a
second representation of an existing concept.

When graph-write permission is available, use `archgraph_check_duplicates` as
an additional preflight. It is not a substitute for search, and the server
re-checks duplicates during `archgraph_apply_changes`.

Prefer reusing a matching node or relationship. Record a new item only when no
existing item represents the same architectural concept and the evidence
justifies the distinction.

### Use the registered vocabulary

Before writing, use `archgraph_describe_schema` when the appropriate node type,
relationship type or traversal rule is not already known. Use registered node
and relationship types only.

Relationships have one canonical direction. Record an edge in that direction.
For explanation, use the registry's inverse label; do not invent a second
inverse relationship type such as `called_by` when the registered type is
`calls`.

### Choose architectural granularity

Create nodes for independently named architecture that another engineer or
team could discuss, own, test or change independently. Typical useful nodes
include:

- applications and external systems;
- capabilities and domain entities;
- commands, events and endpoints;
- tables and projections;
- architectural decisions and test boundaries;
- source files used as implementation anchors.

Do not create a node for every function, local variable, helper, DTO field,
internal branch or other incidental implementation detail. A function may be
evidence for a command, handler, consumer or persistence boundary without
becoming a node itself. When uncertain, keep the detail in the evidence or
final report and record the smallest independently named architectural unit.

### Write descriptions that stand alone

A description is the only part of a node that explains it. Everything else —
edges, impact, source links — says how it connects, never what it is for. Write
it for a reader who has the graph open and the codebase closed.

Three obligations, in this order, because the order is load-bearing:

1. **Identity.** One sentence saying what this is, in the language of the
   domain rather than of the code. Only this sentence survives into neighbour
   and impact listings, so it has to identify the node on its own, without the
   sentences after it and without the node's own name propping it up.
2. **Responsibility and boundary.** What this owns, and — where confusion is
   plausible — what it explicitly does not. A boundary stated once here is
   worth more than any number of correctly drawn edges, because it is the only
   place a *wrong* edge can be recognised as wrong.
3. **What must stay true.** The guarantee, invariant or ordering rule that a
   change to this node must not break. This is what a later agent needs before
   editing the code behind it, and it is the sentence most often missing.

Four to six sentences is typical and ample; the write path accepts up to 2000
characters and terseness is a habit, not a constraint. Do not restate the name,
and do not restate the graph — "depends on the item service" is what the edge is
for. Spend the words on what the structure cannot say.

Two limits on what belongs here. A description carries **no evidence, no hash
and no review item** — nothing anchors it the way evidence anchors a node's
existence, and once the node is promoted it reads as settled fact everywhere it
appears. So state what the code shows, mark what you concluded as a conclusion,
and leave out what you would not defend line by line. And keep rationale out:
"why we chose this" belongs on a `decision` node, which is declared by a human
and can be governed by an edge — not buried in prose that nothing reviews.

What each family of node types owes its reader, beyond the three obligations:

- **`intention`, `application`, `domain`** — the boundary. What falls inside,
  what deliberately falls outside, and who depends on it from beyond that line.
- **`entity`, `property`** — identity and validity. What makes two of these the
  same thing, what states are legal, and who is allowed to change it.
- **`table`, `projection`** — what is authoritative versus derived. For a
  projection, what it is derived *from* and how stale it is allowed to be.
- **`command`, `event`, `endpoint`** — these are contracts, so describe them as
  ones: what triggers it, what it changes, and what a caller or consumer may
  rely on. For an event, whether ordering or delivery is guaranteed. For an
  endpoint, what it refuses.
- **`decision`** — what was decided, what was rejected, and what forced the
  choice. A decision whose alternatives are unrecorded cannot be revisited
  later, only re-argued.
- **`test`** — what property it protects, not which cases it runs.
- **`source_file`, `source_symbol`** — the architectural role it plays. Do not
  restate the path; the source link already carries it.
- **`infrastructure`, `configuration`** — what it provides, and what breaks or
  changes behaviour when it changes.

Projects that register additional node types in `.archgraph/config.json` should
extend this list in the same shape: name the one question a description of that
type must answer that the graph cannot answer structurally.

### Inspect exact nodes and evidence before writing

Use `archgraph_get_node` on every reused or proposed anchor before recording a
relationship. Inspect outgoing and incoming relationships, source links,
staleness, existing evidence and confidence. Use `archgraph_compute_impact`
when the change could affect a broader branch.

Architecture recorded by an agent is inferred. For every new inferred node or
relationship, provide explicit confidence and at least one evidence entry with
a workspace-relative path, what the source shows and why that observation
implies the architectural concept. Do not copy source bodies or secrets into
the graph.

Anchor evidence with a path and, where the code has one, a `symbol`. A symbol
survives the edits above it; a line range does not. The graph is a map of what
the code means, not an index of where it sits today, and no computation in the
engine reads a line number — staleness and drift are decided from paths and
file hashes. Record `startLine` / `endLine` only when the claim is about a
region that has no name of its own — a configuration block, a migration body,
one branch inside a long function — and accept that such a span is a
maintenance debt you have chosen. Omitting a span is the default, not a loss
of precision. Navigation does not suffer: the VS Code extension opens an
evidence entry by its symbol first and falls back to lines only when no symbol
resolves.

Anchor evidence to code that **is** the thing, not to code that calls, imports,
configures or names it. A route handler that invokes an order service is
evidence of the handler, not of the service. The tell is inside your own
writing: if the summary says the code *calls*, *delegates to*, *imports* or
*references* something, then the location is a caller and the claim cannot be
that the location *is* that something. Follow the call to where the behaviour
actually lives and cite that, or record the node without a location and say the
anchor is unresolved. A confidently wrong anchor costs more than a missing one,
because everything downstream — impact, generated context, staleness — is
computed from it, and nothing later re-checks it.

Source links are implementation anchors: use their path and symbol when
available. A line range on a source link is a human-accepted address whose
staleness is hash-based, so it costs nothing there — but it is not a pattern
to copy into evidence. The server computes their content hash. Do not fabricate a
confidence field for a source link, whose schema uses its path and location as
the record of evidence.

A source link is the human-accepted tier, and recording one is an act of
acceptance, not of observation. Its stored content hash is what every later
staleness check compares against, so writing one asserts "this mapping is
correct as of now" — a claim about correctness that no hash can verify.

What that requires is a **human authorization of that specific mapping**, not a
particular application. Which surface a person authorizes from is provenance,
never authority (D-42), so an approval in an MCP client and a click in the VS
Code modal are the same act. The distinction that matters is between the two
write paths:

- **`archgraph_apply_changes` writes without a per-item human gate.** It is
  additive, it issues no preview and no token, and the human sees the result
  afterwards. **Do not record `source_link` changes there on your own
  inference.** Record your evidence and propose the mapping instead. The one
  exception is a link the human has explicitly asked for in the current turn;
  then it is their act carried out through you, and the report says so.
- **The `link` maintenance operation is previewed and authorized before
  anything is written.** Propose mappings there: the preview states the path,
  symbol and span, and applying hashes the file at that instant. An exact
  re-record of an existing link re-hashes it in place — the re-accept of a
  file that changed without the mapping changing. Proposing one obliges you to
  have read the file first; an approval the human cannot judge from is not
  authorization, and a mapping accepted on your say-so is exactly the
  confidently wrong anchor this section exists to prevent.

A link that turns out to be wrong is removed with `unlink` — not by deleting
the node it hangs off, and not by recording a second link to the same file and
hoping the first is ignored. Storage can only append, so an overlapping
re-record is refused rather than applied: `unlink` first, then `link` the
corrected mapping.

Treat inferred architecture as provisional. Do not describe it as human-
confirmed or authoritative merely because confidence is high. Keep confidence
explicit and distinguish observed facts from inferences in descriptions and
reports.

### Respect budgets and stop conditions

Set an exploration budget before traversing. For bounded capability mapping,
the recommended acceptance budget is maximum depth 3 and maximum 15 new
architecture nodes. Use smaller budgets when they are sufficient. Also respect
the limits in the active tool schemas, context character budget and graph-write
batch limit.

Stop when any budget is reached, when the graph boundary becomes ambiguous, or
when further exploration would require unsupported assumptions. Do not silently
increase a budget. Record the boundary and the unresolved question instead.

### Work in batches, not round trips

Budgets bound how much is explored; this rule bounds how many calls it takes.

- Prefer one well-chosen search over iterative narrowing: query with the
  concept's strongest name and use the type and origin filters, rather than
  re-searching several times with small variations. Search when the target
  node is unknown; go straight to `archgraph_get_node` when it is known.
- Independent reads need not be sequential. When the client can issue several
  tool calls in one turn, inspect multiple candidate nodes together, or pair
  `archgraph_get_neighbors` with `archgraph_compute_impact` on the same
  anchor, instead of one call per turn.
- Writes are batches by design. `archgraph_apply_changes` records up to its
  batch limit of changes — nodes, relationships and source links together —
  in one atomic call, and `archgraph_check_duplicates` accepts the whole
  candidate set. Accumulate the full evidence-backed change set for the task
  and record it in one call (splitting only when the batch limit requires it),
  never one item per call. Use `dryRun` to validate a large batch before
  writing it.
- Use the identifiers the tools return. Search and node results carry the
  `itemId` that review tools expect; do not re-derive or guess identifier
  formats.

### Use impact and generated context before implementation planning

Before proposing implementation work, inspect the exact starting node, compute
impact and, when context permission is available, use `archgraph_build_context`.
Read the resulting context with `archgraph_read_current_context` when useful.
Treat stale warnings, exclusions and over-budget blocks as part of the result;
do not present an incomplete context package as dependency-complete.

## Workflow entry points

These workflows are reusable operating sequences, not new MCP tools. A client
may expose them as a convenience prompt, but the same sequence must remain
available through the tools and this policy.

### `map-capability`

Use when the task asks what a capability does or asks for a bounded end-to-end
map before implementation.

Recommended sequence:

1. `archgraph_status`.
2. `archgraph_describe_schema` for node and relationship vocabulary if needed.
3. `archgraph_search_nodes` for the capability, synonyms and likely entry
   points.
4. `archgraph_get_node` for matching anchors; then bounded
   `archgraph_get_neighbors` and `archgraph_compute_impact`.
5. Inspect exact source links and evidence. Search before proposing each
   missing concept.
6. If recording is authorized, run `archgraph_check_duplicates`, prepare only
   evidence-backed additive changes, and call `archgraph_apply_changes` with
   the current revision.
7. Re-read status and relevant nodes after a successful write.

Stop at the declared depth and new-node budget. If the capability crosses an
unresolved boundary, stop there rather than guessing.

Evidence and budget: cite the source links and evidence inspected for each
created or reused concept. Use the declared maximum depth and new-node budget;
the M4 acceptance budget is depth 3 and 15 new nodes, with the active tool
schemas and graph-write batch limit also binding.

The final report lists the inspected nodes and evidence, reused concepts,
created nodes/relationships/source links, confidence, budget usage and
unresolved boundaries.

### `expand-architecture-branch`

Use when a known node or branch needs its neighboring architecture expanded.

Recommended sequence:

1. `archgraph_status` and `archgraph_describe_schema`.
2. `archgraph_search_nodes` for the branch terms and candidate neighbors.
3. `archgraph_get_node` for the branch root and each relevant existing node.
4. `archgraph_get_neighbors` with explicit direction, relationship filters and
   bounded depth; use `archgraph_compute_impact` when consequences matter.
5. Search before every new concept, then check duplicates and apply additive
   changes only when permission, evidence, confidence and revision are ready.

Stop when the branch is sufficiently explained, the budget is exhausted, or a
relationship cannot be justified from evidence. Report the boundary instead
of introducing a speculative edge or inverse type.

Evidence and budget: every new relationship must be traceable to inspected
source evidence and use the registered type and direction. Keep the explicit
depth and new-node limits; do not expand the branch merely because additional
neighbors are available.

The final report lists the branch root, inspected and reused items, created
items with evidence and confidence, traversal depth, new-node count and
unresolved relationships.

### `build-implementation-plan-context`

Use before implementation planning when a graph node and task are known.

Recommended sequence:

1. `archgraph_status`.
2. `archgraph_search_nodes` if the task's starting concept is not already
   identified.
3. `archgraph_get_node` for the exact starting node and any intention node.
4. `archgraph_compute_impact` to inspect direct and transitive consequences.
5. If context permission is enabled, call `archgraph_build_context` with an
   explicit task, bounded depth and character budget.
6. Use `archgraph_read_current_context` to verify the generated artifact when
   needed.

Do not modify the authoritative architecture graph as part of this workflow.
If context writing is unavailable, return the impact and explain that no
context file was generated.

Evidence and budget: keep implementation claims traceable to the exact node,
impact paths, source links and generated context. Respect the selected maximum
depth and context character budget; this workflow has no new-node budget
because it does not record architecture.

The final report includes the selected node, impact examined, context path and
budget cost, excluded or stale items, warnings and planning uncertainties.

### `implement-and-record`

Use when the task is to implement a change in a workspace whose graph is
initialized — a new feature, an endpoint added or cut, a boundary that moves.
This applies even when the request mentions only the implementation: in an
initialized workspace, keeping the graph current is part of finishing an
implementation task whose change touches independently named architecture.
The graph informs the implementation before, and records its delta after; it
never gates the implementation itself.

Recommended sequence:

1. `archgraph_status`.
2. Before implementing, gather context as in
   `build-implementation-plan-context`: `archgraph_search_nodes` for the
   starting concepts, `archgraph_get_node` on the exact anchors,
   `archgraph_compute_impact`, and `archgraph_build_context` when context
   permission is available. The recorded meaning and impact shape the plan.
3. Implement the change with the host's own tools.
4. After implementing, derive the architectural delta: which independently
   named architecture the change created, and which existing nodes gained
   relationships or source links. Apply the granularity rule — most code
   changes are evidence for existing nodes rather than new architecture, and
   a delta of zero items is a valid outcome worth stating explicitly. Every
   node the delta does create gets a description meeting all three
   obligations; a node worth recording is worth explaining.
5. If graph-write permission is available, run one
   `archgraph_check_duplicates` over the whole delta, then record it in a
   single `archgraph_apply_changes` batch with the current revision. This
   path is additive only: correcting an existing settled item belongs to
   `maintain-graph`, and adjudicating a pending inferred item belongs to
   `review-inferred-architecture`, each with its own authorization rules.
6. Re-read status after a successful write.

Evidence and budget: every recorded item cites the implementation itself —
the changed files are the evidence paths. The usual new-node budget applies;
an implementation that would justify more new nodes than the budget allows is
a signal to record the smallest independently named units and report the
rest as unresolved.

The final report summarizes the implementation, the delta recorded (or that
none was needed and why), reused anchors, confidence and evidence for each
new item, and unresolved architecture.

### `review-inferred-architecture`

Use when an agent needs to inspect inferred architecture that awaits human
review, and — with `--allow-review` — to preview and, after explicit human
authorization, apply a decision.

Recommended sequence:

1. `archgraph_status` — confirm `permissionMode` includes `review`, and check
   `pendingReviewCount`.
2. `archgraph_list_pending_reviews` (or `archgraph_search_nodes` filtered to
   `origin: ai_inferred` / pending review state, when `--allow-review` is not
   available).
3. `archgraph_get_review_item` to inspect evidence, drift, contradictions,
   uncertainties and the suggested decision for one item.
4. **Re-derive the claim from source, independently.** Open every cited path
   with the host's own file tools, locate the cited symbol (or the named
   region, where a span stands in for a name), and state what that code
   actually does, in your own words, *before* weighing the item's stored
   `summary` and `inferenceReason`. Then compare the two. Where your reading
   and the stored claim disagree, that disagreement is the finding — report
   it, and recommend `reject`, `edit` or `investigate` rather than `promote`.
   Skipping this step is not review: reading a stored `inferenceReason` and
   agreeing with it only re-reads the assertion under examination.
5. **If the claim holds but the address does not, correct the address rather
   than destroying the item.** A renamed or deleted file leaves a true claim
   anchored on nothing; `anchors` on a `promote` or `edit` decision repoints
   the evidence as part of the same authorization — same claim, correct path,
   confirmed in one act. Reserve reject-and-re-record for a claim that is
   actually wrong: rejecting a correct item costs its provenance and returns
   the rebuilt copy to the back of the queue. Anchors carry the location
   only; if you find yourself wanting to reword the `summary`, the claim is
   what is wrong and this is not the tool. Where the *source link* rather than
   the evidence is what points somewhere wrong, that is `unlink` + `link`
   through maintenance, once the item is no longer pending.
6. `archgraph_get_neighbors` and `archgraph_compute_impact` to understand
   consequences; use generated context if it clarifies implementation impact.
7. Explain the case and **recommend** a decision (`promote`, `reject`,
   `edit`, `deprecate`, or `investigate`) — an agent may never enact one on
   its own judgment.
8. If the human agrees, call `archgraph_preview_review_decisions` and show the
   exact diff — never paraphrase or summarize it away.
9. Only after the human explicitly authorizes the stated decision through the
   configured channel (the MCP client's own approval prompt in
   `client-approval` mode, or the VS Code confirmation modal in
   `vscode-confirm` mode), call `archgraph_apply_review_decisions` with the
   token from step 6. A `humanInstruction` string is audit metadata only —
   never authorization by itself.

Without `--allow-review`, this workflow is inspection-only: explain
uncertainties and recommend a decision, but do not attempt to preview or
apply one — those tools are absent from the tool list.

Why step 4 carries the weight: the server's contradiction detection is
deliberately structural only — a missing file, a stale hash, a duplicate name,
a dangling reference. It never judges whether the cited code means what the
claim says it means, because answering a fallible inference with a second
inference does not make either one true. So a claim whose own evidence does
not support it produces no contradiction, no uncertainty and a `promote`
suggestion. Only re-reading the source catches it. Watch in particular for the
is/calls/uses confusion described under "Inspect exact nodes and evidence
before writing": evidence whose summary says the code *calls* something, ending
in a claim that the code *is* that thing.

Evidence and budget: cite the evidence, source links, confidence and impact
paths bearing on each recommendation — both what supports it and what tells
against it. A recommendation that cites only supporting evidence has not been
reviewed. Keep search, neighborhood and context reads bounded; there is no
new-node budget because this workflow does not create architecture.

The final report identifies the inspected item(s), evidence supporting or
contradicting them, which cited locations were re-read from source and whether
each one bore out its claim, confidence, affected architecture, the recommended
decision, whether it was previewed and/or applied, and unresolved questions.
It explicitly states whether a review mutation was attempted, and if so,
under what authorization.

### `maintain-graph`

Use when architecture that has already settled needs correcting — a name that
no longer matches the code, a relationship typed wrongly, an endpoint that was
cut from scope. Requires `--allow-maintenance`.

**Which system owns the item is not a preference.** Review and maintenance
partition the graph exactly, and an item belongs to precisely one of them:

| Item state | Owner | Tools |
|---|---|---|
| `origin: ai_inferred` with no **terminal** review decision | **review** | `archgraph_preview_review_decisions` / `archgraph_apply_review_decisions` |
| everything else | **maintenance** | `archgraph_preview_maintenance_changes` / `archgraph_apply_maintenance_changes` |

Only `promote` and `reject` are terminal (D-50). `edit`, `deprecate` and
`investigate` write their audit entry and leave the item **pending** — still
`ai_inferred`, still in the queue, still owned by review, still decidable.
So `investigate` is a real "not yet", not a way to hand something to
maintenance: an item parked that way stays exactly where it was, with the
finding recorded against it.

Reaching for the wrong pair is not a silent mistake: the service refuses it
and names the other tool.

**Address repair may be pre-authorized.** When the server runs with
`--auto-anchor-repair`, `archgraph_repair_anchors` applies `re-anchor`,
`unlink` and `link` with no preview and no per-call approval, because an
operator authorized that class of change once at startup. It is not a way
around the gate: those operations move an address and assert nothing about the
architecture, their correctness is machine-checkable, and every new address
must resolve in the workspace or the batch is refused. Everything that changes
what the graph *says* is refused by that tool and still needs a human.

Use it where it belongs — keeping the map current when files and symbols are
renamed or removed, and retiring legacy line ranges — and reach for the
previewed tools for everything else. A span that merely drifted is not a
repair candidate. If a repair feels like it needs a
human to look at it, that is the signal it is not a repair.

Recommended sequence:

1. `archgraph_status` — confirm `permissionMode` and that maintenance tools are
   present. If they are absent the server was started without
   `--allow-maintenance`; say so rather than working around it.
2. `archgraph_get_node` / `archgraph_search_nodes` — confirm the item exists,
   read its `reviewState`, and check its evidence still describes the code.
3. `archgraph_get_neighbors` — understand what a deletion would take with it.
4. Explain what is wrong and **recommend** an operation. As with review, an
   agent may never enact one on its own judgment.
5. `archgraph_preview_maintenance_changes` — show the exact diff and, for a
   deletion, the **complete** incident-edge list. Never paraphrase the cascade;
   the point of disclosing it is that the human sees precisely what goes.
6. Only after the human authorizes through the configured channel, call
   `archgraph_apply_maintenance_changes` with the token from step 5.

A description that no longer explains its node is a correctness problem of the
same kind as a wrong name, and `edit` is how it gets fixed. Auditing them is
legitimate work to be asked for on its own: read a branch of the graph, name
which descriptions fail the three obligations — identity that does not identify,
no stated boundary, no invariant — and recommend replacements. Do it against the
code, not from the existing text, or you will polish the prose of a description
that was wrong to begin with. As everywhere else, recommend; the human decides.

Operations are `rename`, `edit`, `retype-node`, `delete`,
`retype-relationship`, `re-anchor`, `unlink` and `link`. Notes that matter in
practice:

- **`re-anchor` repairs an address, never a claim.** When the code moves, an
  item's evidence can cite a path that no longer exists while the claim it
  makes is still true. `re-anchor` moves where one evidence entry points —
  path, symbol, line range — and cannot touch its `summary` or
  `inferenceReason`. The address it replaces is preserved under
  `metadata.evidenceHistory` with the instant it was superseded, so nothing
  is lost and the original claim stays auditable. An anchor that omits a
  symbol or range clears the old one rather than leaving it. That is the
  intended way to retire a line range: re-anchor to path and symbol alone, and
  the span is gone. If the *claim* is what is wrong, this is the wrong
  operation — that is an `edit`, or a `delete`.
- **`unlink` removes one source link.** Until it existed the only way to drop
  a link pointing at a deleted file was to delete the whole node it hung off.
  Nodes only: relationships carry no source links.
- **Keeping anchors current is closing work, not a separate errand — and an
  anchor is only stale when its path or symbol no longer resolves.** A phase
  that renames or deletes a file, or renames a symbol, leaves addresses
  pointing at a place that no longer exists, and the claims they support are
  usually still true. Repair those as part of finishing the work, in one
  batch, rather than reporting the drift and leaving it: an address that
  survives long enough stops reading as stale and starts reading as a
  contradiction — the next agent finds no such symbol in that file and has to
  guess whether the map is wrong or the code is. The dangerous guess is
  deleting a true relationship. A function that moved from line 245 to line
  367 is **not** such an event: nothing in the engine reacts to it, and a
  reviewer reading by symbol never sees it. Do not re-anchor for position
  drift, and do not report it as drift. Where a legacy span is in the way,
  the repair is to drop it — re-anchor to path and symbol — not to refresh it.
- **`link` accepts a mapping**, hashing the file at apply time. An exact
  re-record re-hashes in place (a re-accept); an overlapping-but-different one
  is refused, because storage appends and two mappings for the same code with
  no way to tell which is current is worse than the drift it was meant to fix;
  anything else is added. Nodes only. Correcting a span is therefore two
  operations, `unlink` then `link`, and that is deliberate — the removal and
  the acceptance are two different claims and each deserves to be seen.

- **Deleting a node with any incident edge requires `cascade: true`.** Without
  it the call fails with `CASCADE_NOT_ACKNOWLEDGED` and lists what blocks it.
  That is a prompt to show the human the list, not to retry with the flag set.
  A cascade removes edges only — never a second node.
- **`retype-relationship` is one operation, not a delete plus a create.**
  Relationship identity derives from source, type and target, so changing the
  type changes the id; the single operation carries description, confidence,
  evidence and history across, which two calls would silently drop.
- **`origin` cannot be changed.** Not by any operation, by any field, on any
  surface. Promotion to `human_confirmed` happens only through review.
- **`decision` and `intention` nodes are refused.** They live in
  `.archgraph/decisions/*.md` and `intentions/*.md`; edit those files directly.
  The refusal names the file.
- **Node ids cannot be renamed.** `rename` changes the display name. Changing
  an id means delete and recreate, with the cascade that implies.
- A large batch may be refused at preview for producing an oversized audit
  record. Split it and preview each part — the refusal says so.

Every applied change writes a committed record under `.archgraph/changes/`,
including a tombstone for anything removed. Those tombstones are what let a
deleted item be re-inferred and reviewed again rather than silently inheriting
its old review state, so a maintenance mutation is never "just" an edit.

Budget: maintenance counts against `--max-writes-per-session`. It creates
nothing, so node and relationship budgets are untouched.

The final report identifies each item changed, what was wrong with it, the
operation applied, everything a cascade removed, the record path, and whether
the human authorized it and through which channel.

## Final reporting contract

Every bounded exploration ends with a concise report containing:

- inspected: nodes, relationships, source links and evidence actually read;
- reused: existing concepts selected instead of recreated;
- created: new additive items, with type, relationship direction, confidence
  and evidence references;
- unresolved: missing architecture, ambiguous boundaries, stale evidence and
  questions requiring human or code inspection;
- budgets: maximums and actual depth, nodes and context cost;
- permissions and outcome: read-only, context or graph-write mode, including
  whether anything was written.

Do not claim that an automated test proves agent judgment. Behavioral
acceptance must observe the agent's sequence, granularity, evidence and report
in a real client session.
