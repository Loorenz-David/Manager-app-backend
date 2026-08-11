---
name: architecture-graph
description: Use the Architecture Graph MCP tools (archgraph_*) when working in a workspace with an initialized .archgraph — to answer questions about the architecture's meaning, boundaries or impact, to build context before implementing, to record the architectural delta after implementing a change, and to review or maintain the graph. Read this skill before the first archgraph_* call of a session.
---

# Architecture Graph

Follow the canonical operating policy. Read the first of these that exists:
`.archgraph/agent-operating-policy.md` at the workspace root (the installed
copy every host shares), `agent-operating-policy.md` beside this file, or
[docs/agent-operating-policy.md](../../../docs/agent-operating-policy.md) in
the Architecture Graph repo itself.
This file is the Claude Code entry point, not a second policy — the policy is
the source of truth for judgment, workflows and reporting.

Route the task to a policy workflow:

| Task looks like | Workflow |
|---|---|
| "What does capability X do?" / bounded end-to-end map | `map-capability` |
| "Expand what we know around node Y" | `expand-architecture-branch` |
| "Plan this change" — context and impact before coding | `build-implementation-plan-context` |
| "Implement this" in an initialized workspace | `implement-and-record` |
| Inspect or decide on pending AI-inferred items | `review-inferred-architecture` |
| Correct or delete settled architecture | `maintain-graph` |

Claude Code ergonomics (the policy's batching rule, applied here):

- Issue independent `archgraph_*` reads as parallel tool calls in a single
  block; don't serialize `archgraph_get_node` calls one per turn.
- Accumulate a task's whole change set and record it with one
  `archgraph_apply_changes` batch, not one call per node.
- The graph answers meaning, boundaries and impact; Grep/Glob/Read answer
  symbol-level questions. Use each for what it is best at.

Review and maintenance mutations require explicit human authorization through
the client's own approval channel (or the VS Code confirmation modal in
`vscode-confirm` mode) — never enact a promotion, rejection, edit,
deprecation or removal on your own judgment, and never treat a
`humanInstruction` string as authorization. MCP never initializes a
workspace.
