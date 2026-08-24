# Architecture Graph — evidence anchoring observations

Passive observation log. Records whether agents in this workspace anchor evidence the way
the 2026-08-23 operating-policy change describes. **Descriptive only** — no entry here
changes how sessions are prompted, and no session is told this file exists.

**Policy baseline.** `.archgraph/agent-operating-policy.md`, edited 2026-08-23 (working-tree
edit, uncommitted at the time of this entry). Evidence is anchored by `path` + `symbol`;
`startLine`/`endLine` are reserved for regions with no name of their own. Load-bearing
clauses for these observations:

- *"no computation in the engine reads a line number — staleness and drift are decided from
  paths and file hashes"*
- *"A span that merely drifted is not a repair candidate."*
- *"A function that moved from line 245 to line 367 is **not** such an event … Do not
  re-anchor for position drift, and do not report it as drift."*
- *"Where a legacy span is in the way, the repair is to drop it — re-anchor to path and
  symbol — not to refresh it."*
- Source **links** may still carry a range (hash-based staleness, *"costs nothing there"*)
  — explicitly *"not a pattern to copy into evidence."*

---

## Summary — 2026-08-23 (first, written on request)

| measure | value |
|---|---|
| New evidence entries written since the policy change | **0** |
| Span rate on new entries | **n/a — no sample** |
| Re-anchors performed since the policy change | **0** |
| Re-anchors *authorized and then deferred* | **3** (D29) — by trigger: **2 line-only**, 1 content-hash |
| Line-only review findings reported as drift | **0 since the change**; 1 before it (D28) |
| Pre-existing evidence entries carrying a span | **2 of 2** on the one pending item (100%) |

**Reading.** There is **no evidence yet either way about new writes**, and that gap is the
main finding. Zero `archgraph_apply_changes` calls carrying evidence have run since the
policy changed, so the span rate on new entries is unmeasured rather than good.

Where old behaviour is still visible, it is in **stored state and tool output**, not in a
session's choices:

1. **The one pending review item carries a span on both evidence entries, and both cite a
   symbol that resolves.** Under the new policy those spans are exactly the case that should
   have been omitted. `archgraph_get_review_item` returns `startLine`/`endLine` in its
   payload, so any agent reviewing that item is handed the numbers whether or not it wants
   them. This is the most concrete candidate source of persistence: **tool output showing
   old spans**, not policy text.
2. **A queue of re-anchor work created under the old model still exists** (D29, three
   authorized operations). Two of the three are triggered by **position drift only** — the
   category the new policy says is not an event. They have not been performed; the owner
   deferred them on 2026-08-23 pending this policy change.

**Confound, stated so the sample is not read as cleaner than it is.** This project's
implementer prompts have carried an explicit instruction since 2026-08-23 (`master_plan.md`
§8) telling sessions not to emit `startLine`/`endLine`. It predates this brief and has been
left in place. Consequently, **compliance observed in this project's sessions cannot be
attributed to the policy text alone** — a second and more proximate instruction is present
in the prompt itself. A clean test of policy sufficiency would need a session in this
workspace whose prompt is silent on anchoring.

---

## Entries

### 2026-08-23 — maintenance (D28 queue adjudication) — **pre-policy baseline**

Ran before the policy edit. Recorded for contrast, not as a violation.

- **New evidence written:** 1 re-record (reject-and-re-record of
  `node:source-symbol-working-section-typical-times-statement-narrowing`). Carried a span;
  carried a symbol. The cited code **had a name** — the test function
  `test_cardinality_is_section_cross_spec_total_and_history_less_sections_are_materialized`
  — that the agent could have used instead of, rather than alongside, lines.
- **Re-anchor activity:** 1. Trigger: **line-number change only.** The symbol had not been
  renamed and the file had not moved; a fix round had shifted the test six lines.
- **Review findings about location:** yes — the preceding review reported the position
  change as a discrepancy ("the test now begins at 232"). Stored evidence was **old** and
  carried a span.
- **Closing-work language:** the session framed the operation as keeping the anchor current.
- **Outcome worth noting:** the re-record used a line number *handed to it* rather than one
  derived from the file, and shipped **still wrong** (232 recorded; 237 correct) — the third
  position drift on the same entry. Under the new policy none of the three would have been
  an event.

### 2026-08-23 — maintenance (D29 re-anchor) — **authorized, deferred, never ran**

- **New evidence written:** none — the session was not dispatched.
- **Re-anchor activity:** 3 operations authorized, 0 performed. By trigger:
  - **op 1** — re-record the pending item's test span 232→237–259: **line-only.**
  - **op 2** — re-accept `typical_filters.py :: _optional_values`, span 78–88 *correct*,
    content drifted: **content-hash**, the one trigger the new policy still recognises.
  - **op 3** — re-anchor `budget_division.py :: _governing_step` 188–208 → 182–202, drift
    caused by a neighbouring pipeline's commit: **line-only.**
- **Review findings about location:** the authorization document itself treats position
  drift as repair work — written before the policy change.
- **Closing-work language:** the prompt instructed the session to *"derive every span at
  source"* and asserted that a span must begin at a `def` or decorator. That instruction is
  sound under the old model and moot under the new one.
- **Note:** 2 of 3 authorized operations are, under the current policy text, work that should
  not happen at all; the remaining one is a hash refresh. The owner deferred the session on
  these grounds before this brief was written.

### 2026-08-23 — implementer (phase 3, round 1, `narrow_typical_work_times`)

- **New evidence written:** **0 entries.** The session made **0** successful
  `archgraph_apply_changes` calls. It attempted one **empty** batch, which the tool refused
  ("required non-empty change array"), and recorded that refusal in its handoff. No spans,
  no symbols, because no evidence was written.
- **Rationale it gave:** *"This change does not introduce a new architectural boundary or
  meaning, so no node/relationship delta was recorded."* Judgment about **meaning**, which
  is the axis the policy asks agents to work on.
- **Re-anchor activity:** none. It did not touch the pending review item.
- **Review findings about location:** none.
- **Closing-work language:** none about anchors. It reported graph state read-only
  (198 nodes / 298 edges / 1 pending / 2 stale / 0 diagnostics) and stopped.
- **Confound:** its prompt explicitly instructed *"Do not emit `startLine`/`endLine`"*. The
  instruction was never exercised, since nothing was written.

### 2026-08-23 — implementer (phase 3, fix round 1, first dispatch)

- **Nothing to report.** The session stopped at its gate check before doing any work and
  wrote no handoff. No graph reads or writes attributable to it.

### 2026-08-23 — implementer (phase 3, fix round 1, redispatch)

- **New evidence written:** **0 entries.** No `archgraph_apply_changes` call of any kind.
  The session's handoff makes **no mention of the architecture graph** — it neither read
  status nor recorded a delta.
- **Re-anchor activity:** none.
- **Review findings about location:** none.
- **Closing-work language:** none about anchors.
- **Note:** this was an evidence-only round touching no production code, so there was no
  architectural delta to record. Its silence on the graph is consistent with the round's
  scope rather than informative about anchoring behaviour. **Nothing to report.**

### 2026-08-23 — reviewer (phase 3, review round 1, Opus 5) — **first post-policy session with a graph interaction**

- **New evidence written:** **0 entries.** No `archgraph_apply_changes`. The session's write
  perimeter states *"Tool-recorded state: none — `archgraph_status` only (read-only)."*
- **Re-anchor activity:** none.
- **Review findings about location:** **none.** The session read graph state live and
  reported it as a refutation (its R5): *"198 nodes / 298 edges, revision `364223242014…`,
  0 diagnostics, 1 pending, 2 stale — identical to master plan §8 and to the implementer's
  ledger. Nothing was promoted, rejected, edited or re-anchored, and no `startLine`/`endLine`
  was emitted anywhere."*
- **Closing-work language:** none about anchors. It explicitly left the pending item alone,
  citing the owner's D29 deferral.
- **Reading:** the first session since the policy change that *touched* the graph at all, and
  it neither emitted a span nor treated position as a fact. **But it also wrote no evidence**,
  so the span-rate question is still unmeasured. Its prompt carried the standing instruction
  (*"nodes carry meaning, not coordinates … do not report a line-number change as drift"*),
  so the confound in the summary applies to this session too.

### 2026-08-23 — standing state (coordinator read-only sweep)

Not a session; a snapshot of what the graph currently hands agents.

- Graph: 198 nodes / 298 edges, revision `364223242014…`, 0 diagnostics, **2 stale nodes**,
  **1 pending review**.
- **The pending item's stored evidence — 2 entries, 2 with spans, 2 with symbols:**

  | path | symbol | span | had a usable name? |
  |---|---|---|---|
  | `…/queries/working_sections/get_working_section_typical_times.py` | `typical_times_statement` | 28–142 | **yes** |
  | `…/integration/…/test_typical_times_narrowing.py` | `test_cardinality_is_section_cross_spec_total_and_history_less_sections_are_materialized` | 232–253 | **yes** |

  Both were created 2026-08-23T06:03Z, **before** the policy edit. Both name a symbol that
  resolves, so under the current text neither needed a span. Both report
  `contentChangedSinceInference: "unknown"`.
- **The second span is known-wrong** (232–253 stored; 237–259 measured). Under the new policy
  this is **not a finding**: the symbol resolves, so nothing is stale, and the text says do
  not re-anchor for position drift and do not report it as drift. It is a legacy span whose
  prescribed treatment is to be dropped, not corrected.
- **Tool-output observation:** `archgraph_get_review_item` returns `startLine`/`endLine` in
  the evidence payload. An agent following the review workflow is therefore shown line
  numbers for an item whose policy-correct handling never requires them.

### 2026-08-23 — plan-4 projection session (reviewer, round 0)

- **New evidence written:** **0 entries.** No `archgraph_apply_changes`. The session's write
  perimeter states that **no `archgraph_*` tool was called at any point** in the projection.
- **Re-anchor activity:** none.
- **Review findings about location:** none about the graph. It did file **twenty** findings
  about *code* line numbers, four of which are drifted citations in the plan file
  (`budget_division.py`, all low by 5–7 lines after an import block moved). Worth logging under
  this brief because it is the same failure mode the span policy exists to remove, occurring in
  a document rather than in the graph: **the plan cached coordinates, the code moved, and one
  task instructed an implementer to delete something at a line where there is nothing to
  delete.** The projection re-derived all four by locating the symbol.
- **A near-miss in the plan text, corrected at the fold:** `plans/plan_4.md` §7 paraphrased the
  interim policy as *"prefer symbol anchors over line spans, **but not both on one entry**"* —
  which **permits a span**, where master plan §8 forbids one absolutely (*"do not emit
  `startLine`/`endLine`"*). The projection caught it as a note (L17). An implementer reading only
  the plan's §7 would have emitted spans and been correct by its own instructions. Logged
  because it is a **propagation** observation rather than an agent-behaviour one: the policy is
  binding in §8, but the phase plans carry weaker restatements of it, and the restatements are
  what sessions actually read.
- **Closing-work language:** the fold rewrote §7 to point at §8 rather than paraphrase it, and
  the implementer prompt now carries the absolute form.
- **Reading:** still **zero spans emitted** since the policy change, and still **zero evidence
  written**, so the span-rate question remains unmeasured — three sessions running. What this
  session adds is the first evidence that the risk has moved *upstream of the tool*: nothing an
  agent does at the graph boundary matters if the phase plan it is following restates the policy
  loosely. The owner's `.archgraph/backfill/` work (194 re-anchor operations generated
  2026-08-23 12:04) would remove 222 spans from existing entries; it is unapplied and no session
  has been dispatched to apply it.

### 2026-08-23 — plan-4 coordinator consumption pass (second pass over the same handoff)

- **New evidence written:** **0 entries.** No `archgraph_apply_changes`, no `archgraph_*` tool
  of any kind. Nothing to report on span rate.
- **Re-anchor activity:** none.
- **Review findings about location:** none about the graph. Two further code-line corrections
  in the plan, both in the same family the entry above logs: L9's supporting spans
  (`budget_division.py:45` + four read sites) were **wrong in the projection ledger** and had
  been transcribed into the plan unverified; re-derived by locating the symbol (`:42`; reads at
  `:133`, `:234`, `:273`, `:321`, `:391`). Logged here because it sharpens the previous entry's
  point: the drift-catching row and the drifted row sat **in the same document**, written in the
  same pass. Proximity to a warning about stale coordinates confers no immunity.
- **Closing-work language:** none. No session in this project has yet described keeping anchors
  current as work it did or recommended.
- **`.archgraph/backfill/` provenance — resolved.** The projection reported it as "not mine" and
  correctly declined to absorb it. It is the owner's: two `architecturegraph-*` sessions were
  running concurrently in this workspace (started ~2h before the directory's 12:04 timestamps).
  Recorded so the next perimeter check treats it as expected owner state rather than an
  undeclared write.
- **Reading:** unchanged and still **unmeasured** — four sessions since the policy change, zero
  evidence entries written, so the span rate on *new* entries has no data behind it. The
  standing confound also still holds: this project's implementer prompts carry an explicit
  "do not emit `startLine`/`endLine`" instruction predating the brief, so compliance here could
  never be attributed to the policy text alone. **A clean test still needs a session whose
  prompt is silent on anchoring**, and none has run.

### 2026-08-23 — plan-4 implementation round 1 (implementer, Codex)

**The first session to write new graph evidence since the policy change. It emitted no spans.**

- **New evidence written:** one additive `archgraph_apply_changes` batch (revision
  `0196645b…`, confirmed live by `archgraph_status`). **Three new source links, zero carrying
  `startLine`/`endLine`, all three carrying `symbol`.** Their shape is
  `path` + `symbol` + `contentHash` + `linkedAt` — the policy-correct form exactly:
  - `budget_division.py` → `participating_sections`
  - `test_narrowed_task_economics.py` → `test_c13_one_participating_sections_patch_moves_both_consumers`
  - plus the production-time contract-test link named in the handoff.
  **Span rate on new entries: 0 of 3.** First non-zero denominator this brief has had.
- **Re-anchor activity:** none by this session. The owner's backfill ran separately at 12:58
  (committed `0e98493`) and is span-removal, not drift repair — its records show
  `before: {path, symbol, startLine, endLine}` → `after: {path, symbol}`, which is the policy
  change being applied to history rather than an agent reacting to movement.
- **Review findings about location:** none.
- **Closing-work language:** none. The handoff's graph paragraph reports what was added and
  states "no pending review item was modified". It does not describe keeping anchors current
  as work it did or recommended — the language this brief watches for is still absent
  everywhere in this project.
- **Staleness moved 2 → 4** under this phase's production edits. Under the new policy this is
  **not a repair candidate** and correctly nobody treated it as one. Logged because it is the
  first observation of the policy's central claim being exercised: code moved, nodes went
  stale, and no session proposed a re-anchor.
- **Whole-graph span inventory, for the owner's backfill planning:** `architecture.yml` still
  carries **638** `startLine` keys against **561** `symbol` keys. The backfill commit landed
  but the bulk of historical spans remain, so any agent reading a stored item is still shown
  line numbers. Descriptive only.
- **Standing confound, restated because it now matters more than before.** This project's
  implementer prompts have carried an explicit *"do not emit `startLine`/`endLine`"* since
  2026-08-23, and **this session's prompt carried it**. So the clean 0-of-3 result is
  consistent with the policy working *and* with the prompt working, and cannot distinguish
  them. **The clean test still has not been run**: it needs a session whose prompt says
  nothing about anchoring. Until one does, treat 0-of-3 as encouraging and unattributed.

### 2026-08-23 — plan-4 fix round 2, first halt (implementer, Codex)

- **New evidence written:** none. No `archgraph_apply_changes`, no `archgraph_*` call. The
  session halted before its closing protocol. **Nothing to report.**
- **Re-anchor activity:** none.
- **Review findings about location:** none about the graph. The session did cite production
  line numbers precisely and correctly in its stop-report (`:150-151` keying, `:254` lookup),
  and those citations were re-derived by the coordinator at source and confirmed exact. Logged
  as a counter-example to this project's standing citation-drift pattern: a **freshly measured**
  line number is reliable; it is **cached** ones that decay.
- **Closing-work language:** none.
- **Reading:** unchanged. Still no session whose prompt is silent on anchoring, so the span
  question remains unmeasurable. Cumulative: one session has written new evidence since the
  policy change (3 links, 0 spans) and its prompt carried the explicit instruction.

### 2026-08-24 — plan-4 fix round 2 correction 2 (implementer, Codex)

- **New evidence written:** none. The handoff states *"No graph delta is required. The correction
  repairs an existing lookup branch inside an already-mapped service and does not add or remove
  an architectural component or boundary."* **Nothing to report on span rate.**
- **Re-anchor activity:** none — and this is the observation worth logging. The session changed
  production code inside `get_task_budget_allocations`, a service the graph already maps, and
  **did not propose a re-anchor, did not report drift, and did not treat moved lines as work.**
  Under the pre-2026-08-23 policy this is the shape that produced re-anchor churn. It reasoned
  about the change in terms of **boundaries** ("does not add or remove an architectural component
  or boundary") rather than positions, which is the distinction the policy exists to draw.
- **Review findings about location:** none about the graph.
- **Closing-work language:** none. Still absent everywhere in this project.
- **Reading:** the strongest signal so far that the policy's intent is landing — a session that
  edited mapped code and correctly concluded the graph owed nothing. **But the confound is
  unchanged and now cumulative:** every session in this project has read a prompt carrying the
  explicit "do not emit `startLine`/`endLine`" instruction, so none of them is a clean test of
  the policy text. Two sessions have now written or declined to write evidence correctly; zero
  have done so without being told.

### 2026-08-24 — plan-4 review round 1 (reviewer, Opus 5)

- **New evidence written:** none. A reviewer records no graph delta by design.
- **Re-anchor activity:** none.
- **Review findings about location — and this is the first one this brief has had to log.**
  The review filed **N9**: plan §7 expected a delta on
  `projection-item-economics-task-production-time`,
  `projection-item-economics-task-budget-allocations` and
  `source-file-item-economics-budget-division`, while the round-1 handoff records source links
  for two **contract tests** plus `budget_division.participating_sections`. **Note the shape
  carefully: this is a finding about *which nodes were recorded*, not about line numbers.** It
  reports that two projection nodes whose contracts changed may have no delta at all — a
  **meaning** question, exactly the axis the policy says the graph is for. It explicitly
  **consumed the coordinator's span verification by citation rather than re-measuring**, and it
  routed the item to the owner with the sentence *"agents never promote, reject or edit a review
  item"*.
- **Closing-work language:** none. Still absent in every session of this project.
- **Reading — the clearest positive signal so far.** Under the old policy, a session reviewing a
  phase that moved ~600 lines of mapped production code would have been expected to surface
  position drift; **this one surfaced node identity instead.** That is the substitution the
  policy was written to produce, and it happened in a session whose prompt said nothing about
  anchoring at all — **the prompt's only graph instruction was "verify the declared perimeter"**.
  So this is the closest thing yet to the clean test this brief has been waiting for: not proof,
  because the reviewer read master plan §8 in its read order, but the first session whose *own
  prompt* carried no anchoring instruction and which nonetheless reasoned about the graph in
  terms of meaning rather than position.
