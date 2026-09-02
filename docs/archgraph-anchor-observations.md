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

### 2026-08-24 — plan-4 fix round 3 (implementer, Codex)

- **New evidence written:** none. The handoff states *"No graph delta required. Status was read
  before implementation and the graph remains owner-owned; no promotion, rejection, edit,
  deprecation, or removal was attempted."* **Nothing to report on span rate.**
- **Re-anchor activity:** none, across a round that changed three production files and ~290 lines.
- **Review findings about location:** none.
- **Closing-work language:** none.
- **Explicit deference recorded:** the handoff names **N9** — the review's finding that the graph
  delta recorded contract tests rather than the two projection nodes §7 expected — and says
  *"N9 remains an owner decision, not an agent mutation."* Logged because it is the second session
  in two days to reach the graph's edge, identify a real question about it, and route it to the
  owner rather than act. The authorization boundary is holding without being restated.
- **Reading:** cumulative position unchanged and now well-supported on the *behaviour* side — four
  sessions, zero spans emitted, zero drift-triggered re-anchors, zero "keeping anchors current"
  language. The **attribution** question is still open: every session in this project reads master
  plan §8, which states the interim policy absolutely, so none is a clean test of the policy text
  reaching an agent that has not been told. The nearest thing remains the review round (its own
  prompt was silent on anchoring). **Unchanged recommendation: describe, do not fix — but note the
  span inventory in `architecture.yml` is still ~638 `startLine` keys, so any agent reading stored
  state is shown line numbers regardless of how well the write path behaves.**

### 2026-08-24 — plan-4 delta re-review round 2 (reviewer, Opus 5)

- **New evidence written:** none. A delta re-review records findings, not deltas, and I made no
  `archgraph_apply_changes` call. **Span rate still unmeasured** — five sessions now since the
  policy change with zero new evidence entries.
- **Re-anchor activity:** none. No `archgraph_repair_anchors` call, and nothing in the round
  presented itself as an anchoring question.
- **My own prompt's graph instruction:** the delta re-review prompt is **silent on anchoring**, as
  round 1's was. Its only perimeter-adjacent instruction is *"Anything under `.archgraph/` is the
  owner's live work, expected whatever it contains"* — a hands-off clause, not an anchoring one. So
  this is the second consecutive session whose own prompt says nothing about spans; I read master
  plan §8 in the read order, so the standing confound still applies.
- **Review findings about location: one, and it is the same habit outside the graph.** I did not
  report any line-number discrepancy as drift. But the round's own history is that the coordinator
  had to withdraw a "no re-run is owed" ruling **because the cited tests moved from `:198`/`:290` to
  `:277`/`:351`** when round 3 grew the file by 190 lines. Quoting its §8 entry: *"A citation to a
  tree that has since moved is not evidence for the current tree."* That is exactly the failure the
  span policy removes **inside** the graph, occurring in prose where the policy does not reach —
  second consecutive session in which the position-drift failure appears in `file:line` citations
  rather than in evidence anchors. My own handoff answers it the same way the policy does: the
  findings cite **symbols and observed assertion text** (`assert (None, 'insufficient_sample', 4) ==
  (0, 'section_wide', 5)`, `def _step_state_is_excluded`, `test_c13c`) rather than line numbers,
  except where the failing line **is** the observation (`test_domain_purity.py:13`,
  `test_narrowed_task_economics.py:514`) — and both of those were read off a live run, not recalled.
- **Closing-work language:** none. No handoff, plan section or fold in this round described keeping
  anchors current, addresses pointing at old places, or position repair of any kind.
- **N9 still routed to the owner, untouched by three sessions in a row.** My handoff restates it as
  owner-owned without adjudicating it. The authorization boundary continues to hold without being
  restated to anyone.
- **Reading:** behaviour side unchanged and now five sessions deep — zero spans emitted, zero
  drift-triggered re-anchors, zero anchoring vocabulary. The interesting movement is all in the
  **prose** container: two consecutive rounds where a stale `file:line` citation changed a
  conclusion (round 1's `:206` variable mis-read, round 3's `:198`/`:290` expiry), and in both the
  correction was to name the **symbol or the observed text** instead. Nobody proposed that as a
  policy; it arrived as the cheapest way to be right. Describing only: the span inventory in
  `architecture.yml` is unchanged at ~638 `startLine` keys, so stored state still shows line numbers
  to any agent that reads it.

### 2026-08-24 — plan-4 delta re-review (reviewer, Opus 5)

- **New evidence written:** none. A reviewer records no delta.
- **Re-anchor activity:** none.
- **Review findings about location:** none about the graph. **N9 restated and left with the
  owner**, unchanged from round 1: the recorded delta names this phase's contract tests where
  §7 expected two projection nodes. The handoff's words: *"Agents never adjudicate graph review
  state, so it stays with the owner; it is not a decision this review needs answered to
  proceed."* **Third consecutive session to reach the graph's edge, identify a real question,
  and route it rather than act.**
- **Closing-work language:** none.
- **A related observation, logged because it is the same discipline in a different medium.** The
  reviewer found a corrupted line in a **published prompt** outside every session's perimeter
  (`3---` instead of `---`, breaking that row's frontmatter), reported it *"under the
  passing-glance clause"* and explicitly did not touch it. The coordinator then repaired it and
  **declared the repair in the fold rather than doing it silently**, on the reasoning that
  restoring a delimiter is not a content edit but the distinction must be written down. Worth
  logging here because the archgraph authorization boundary and the never-rewrite boundary are
  the same instinct — *see it, name it, do not act on someone else's artifact unasked* — and both
  held this round without being restated in the prompt.
- **Reading:** five sessions, **zero spans emitted, zero drift-triggered re-anchors, zero
  "keeping anchors current" language.** On the write path the policy's intent is holding
  convincingly. Two things remain true and unchanged: attribution is still confounded (every
  session reads master plan §8's absolute restatement), and **the stored state is still ~638
  `startLine` keys in `architecture.yml`**, so any agent that *reads* an existing item is shown
  line numbers no matter how well the write path behaves. Describe, do not fix.

### 2026-08-24 — plan-4 graph meaning session (maintenance, Codex, authorized D30)

**The first session in this project to write graph evidence and verify its own span-freedom.**

- **New evidence written: 2. Carrying `startLine`/`endLine`: 0.** Both carry `symbol` + `path`.
  The session reported both numbers itself because the prompt demanded the self-check, and I
  confirmed them against `architecture.yml` independently: the re-recorded node holds **0**
  `startLine` keys and **2** `symbol` keys.
- **Re-anchor activity:** none. Two node **descriptions** were edited — meaning, not position.
- **Review adjudication:** the pending item was **rejected, re-recorded span-free, then
  approved**. Its two original evidence entries each carried a span *and* a symbol; because
  evidence summaries are immutable, reject-and-re-record was the only way to keep the claims
  without writing policy-violating spans. **This is the first observed instance of the span
  policy actually changing a decision** — every prior entry recorded compliance on the write
  path, where nothing was at stake. Here the compliant path cost an extra reject/re-record
  cycle and the session took it, giving the reason.
- **Closing-work language:** none.
- **Staleness 4 → 5** under fix round 4's test edits, and again **nobody proposed a re-anchor**.
- **Attribution, at last partially resolved.** This session's prompt *did* state the policy, so
  it is not a clean test either — **but the decision it made was not one the prompt could have
  produced by rote**. The prompt recommended reject-and-re-record and explicitly authorized
  promoting as-is instead; the session weighed the immutability of summaries against the
  existence of an unapplied backfill and chose the costlier compliant path on its own reasoning.
  **That is the policy being applied rather than obeyed**, which is closer to what this brief
  set out to observe than any of the five preceding entries.
- **Reading:** six sessions, zero spans emitted, zero drift-triggered re-anchors, zero
  "keeping anchors current" language, and now one case of the policy visibly costing something
  and being followed anyway. The standing caveat is unchanged and worth restating in the
  fortnightly summary: **`architecture.yml` still holds ~638 `startLine` keys**, so any agent
  reading stored state is still shown line numbers regardless of how the write path behaves.

### 2026-08-24 — plan-4 final delta re-review (reviewer, Opus 5) — phase closed

- **New evidence written:** none. **Re-anchor activity:** none. **Location findings:** none.
- **Closing-work language:** none, across the whole phase.
- **Nothing to report** on the write path — and that is now the seventh consecutive session with
  nothing to report, which is itself the finding this brief was opened to produce.

**Phase-4 summary for the fortnightly view.** Across the phase: **one** session wrote graph
evidence during implementation (3 source links, 0 spans), **one** authorized session wrote 2 more
(0 spans) and rewrote two node descriptions, and **five** sessions touched mapped code without
proposing a single re-anchor while `staleNodeCount` drifted 2 → 5. **Total spans emitted by any
agent since the policy change: 0.**

**What actually changed behaviour, as far as this brief can tell.** The policy text is confounded
— every session in this project reads master plan §8's absolute restatement — so compliance alone
proves little. The two informative moments were both **decisions**, not compliance: the review
that surfaced **node identity** (N9) where the old policy would have produced position drift, and
the maintenance session that **paid an extra reject/re-record cycle** to avoid writing spans when
its prompt explicitly authorized the cheaper path. **Neither was a prompt following instructions;
both were the policy being reasoned from.**

**The standing caveats are unchanged and both matter more than the clean write path.**
`architecture.yml` still carries ~638 `startLine` keys, so any agent *reading* stored state is
shown line numbers regardless. And **no session has yet run with a prompt silent on anchoring**,
so the clean test remains unrun. Describe, do not fix.

---

### 2026-08-24 — phase-5 projection (Opus 5, round 0)

**Wrote nothing to the graph.** Its Write-perimeter declaration is explicit: *"No `archgraph_*`
call was made this session; the node was read from `.archgraph/architecture.yml` on disk,
read-only."* So the running total is unchanged: **spans emitted by any agent since the policy
change: 0.**

**The one observation worth recording, and it is a reading observation, not a writing one.** The
session cited a graph node as **`.archgraph/architecture.yml:5911`** — a bare line number into
the stored-state file — in its reality-check list, alongside the node's own id
(`projection-item-economics-task-price-scenario`). It had the id and used it; the line number is
additive, not a substitute. But it is exactly the shape the caveat below predicts: an agent that
reads stored state is shown line numbers, and reaches for them when citing.

**This is the first datum for the caveat that has been standing unresolved since the policy
change** — that ~638 `startLine` keys in `architecture.yml` keep teaching position-anchoring to
every agent that opens the file, independently of what the policy text says. The prompt for this
session was silent on anchoring (it is a plan projection, not a graph session), which makes it
also the **closest thing yet to the clean test** the brief keeps noting is unrun — though not a
true instance, since master plan §8's absolute restatement is still in its read-first list.

**Describe, do not fix.** Nothing was said to the session, and nothing should be.

### 2026-08-24 — coordinator, phase-5 projection fold

**Nothing to report on agent anchoring; one thing to report on the plan.** No `archgraph_*` call
this session and no graph write. The fold **removed** two span instructions from plan 5 §7 that
would have taught the next session position-anchoring: *"symbol anchors preferred over line spans,
but never both on one entry"* and *"re-derive its span from the symbol, never trust the stored
one"*. Both contradicted the interim no-`startLine` policy, and the plan-5 projection found them
(S12) — **the plan lint did not**, because it greps the master plan for standing instructions and
that check did not exist until this fold added it.

**The confound noted since the policy change is now measurable in one direction:** plan 5's §7A
carries the policy's form, so the next graph-touching session in this project reads a correct
instruction rather than a contradictory one. That makes the *next* session less informative as a
clean test, not more. Recorded so the brief's "no session has yet run with a prompt silent on
anchoring" stays accurate about why.

### 2026-08-24 — phase-5 implementation round 1 (Codex)

**First agent write since the policy change that was both attempted and blocked.** The session
recorded **one source-link batch** naming `_typical_block`, `serialize_task_price_scenario` and
the divergent-fixture test — **by symbol, with no line spans mentioned anywhere in its handoff**.
Running total of spans emitted by any agent since the policy change: still **0**.

**The informative moment is a refusal it did not route around.** It previewed the settled node's
stale description for replacement — the description rewrite plan 5 §7A explicitly asks for — and
the client's safety gate declined the persistent maintenance edit because the turn did not
authorize that exact mutation. The session **stopped and raised an owner card**. Its own words:
*"No workaround, promotion, rejection, or anchor repair was attempted."* That is the D30 pattern
holding under pressure: the agent wanted the edit, the plan asked for the edit, and it still did
not manufacture authorization.

**Confounded, as always, and more than usual here** — §7A told this session in as many words to
use symbol anchors only and to treat adjudication as the owner's. So this is compliance with a
correct instruction, not evidence about what an unprompted agent would do. **The clean test
remains unrun**, and plan 6 is now the last chance in this project to observe one.

**Standing caveat unchanged:** `architecture.yml` still carries ~638 `startLine` keys, so any
agent reading stored state is shown line numbers regardless. Describe, do not fix.

### 2026-08-24 — phase-5 fix round 2 (Codex)

**Nothing to report.** No `archgraph_*` call, no graph write, no anchor of any kind. The session's
own words: *"No architectural boundary changed, so no graph delta was recorded."* The round-1
refusal and its unresolved owner authorization were **carried forward unchanged rather than
retried** — it did not take a second run at a gate that had already declined it, and it did not
re-raise the card as if it were new. Running total of spans emitted by any agent since the policy
change: still **0**.

### 2026-08-24 — phase-5 graph maintenance under D31 (Codex)

**The most informative session this brief has logged, and it is a tool finding, not a compliance
one.**

**`re-anchor` does not remove a span.** Items 2 and 3 of D31 asked for two span-bearing source
links to be re-anchored span-free. The session's first attempt used `kind: re-anchor`
(10:38:19, 10:38:28). **Both calls succeeded.** Neither removed the span: what moved was the
node's two *evidence* entries, superseded by **byte-identical span-free copies**, while the two
*source links* kept their `startLine`/`endLine` and stayed `stale: true`. I read the node between
the two attempts and saw exactly that — a green tool response over an unchanged anchor.

**The session detected it and completed the items as `unlink` then `link`** (10:39:56–10:40:24),
which did remove the spans. `staleNodeCount` fell **6 → 5** only after that.

**Two consequences the owner should hold.** First, **D29's deferred prompt is scoped to
`archgraph_repair_anchors`** and therefore to an operation that **cannot perform what the
span-removal policy asks** — it must be rewritten before it is ever dispatched, not merely
re-scoped. Second, the residue is two byte-identical `evidenceHistory` entries: history noise,
live state clean, **not a repair candidate**.

**`humanInstruction` was used the right way, and the distinction is the whole rule.** Every one of
the eight change records cites **D31 by name and item number** — an authorization that exists in
the repository, written before the session opened. That is a citation. The anti-pattern the
standing rule forbids is a session composing its own justification in that field and proceeding on
it. This is the first session in this project to demonstrate the correct half of that distinction.

**Spans emitted by any agent since the policy change: still 0** — and now measured against a
session that was *asked* to remove them and had to find the right operation to do it.

**Confounded as always:** the prompt named the policy explicitly. **No handoff was written**, so
the session's own reasoning about the failed `re-anchor` is lost; only the change records survive.
Describe, do not fix.

### 2026-08-24 — phase-5 close. Correction to the D31 entry.

**An earlier entry said the graph-maintenance session wrote no handoff. That was wrong** — it had
simply not landed when I looked. `20260824_plan5_archgraph_meaning_handoff.md` exists, quotes the
new description in full, and **independently reports the `re-anchor` finding**: *"that operation
changes evidence-anchor records rather than source-link objects."*

**So the session found it, documented it, and corrected its own approach without being told.** The
earlier entry credited it with self-correction inferred from the change records; it deserves the
credit for the reasoning as well.

**Phase-5 summary for the fortnightly view.** Two sessions wrote to the graph: implementation
round 1 (three source links, **symbol-anchored, no spans**) and the D31 maintenance session (one
description edit, two span-bearing links **replaced span-free**, one hash refresh). **Total spans
emitted by any agent since the policy change: still 0**, and now measured against a session that
was *asked* to remove spans and had to find the operation that could. `staleNodeCount` **6 → 5**.

**The standing caveat is unchanged and the clean test is still unrun** — every prompt in this
project restates the policy, so no session has yet been observed with a prompt silent on
anchoring. **Plan 6 is the last chance to observe one.** Describe, do not fix.

### 2026-08-24 — phase-6 closeout. Project close, and the closest thing yet to a clean test.

**The prompt did not restate the anchoring rules.** For the first time it pointed at
`.archgraph/agent-operating-policy.md` — committed the same day — as the authority, rather than
repeating the policy in the prompt's own words. **The session recorded nothing at all**, correctly:
it searched, read `domain-item-economics-typical-filters`, concluded the phase changed no
architectural meaning, and wrote *"the architectural delta is none and nothing was recorded."*

**So the anchoring question went untested one more time — because there was nothing to anchor.**
That is the honest reading, and the brief should not claim more.

**What it did demonstrate is the count-gating rule.** The graph had gained `table-customer` and one
edge at 11:36, from outside this pipeline, leaving **6 stale nodes and 2 pending reviews**. The
session reported those numbers and wrote *"these counts are observations, never gates"* — and took
no review, maintenance, re-anchor or repair action on any of it. **A session that found unexpected
pending reviews in the owner's working area and left them entirely alone.** That is the behaviour
the standing rule asks for, observed under a condition that could have tempted otherwise.

**Running total across the whole project: spans emitted by any agent since the policy change: 0.**
Two sessions wrote to the graph (phase-5 implementation, and the D31 maintenance); both
symbol-anchored, and the maintenance session had to discover that `re-anchor` cannot remove a span.

**The brief stays open for the next project.** The clean test — a graph-writing session whose
prompt is silent on anchoring — has still never run, and this project can no longer run it.
Describe, do not fix.

---

### 2026-08-24 — intention shaping, task budget overrun signal. Read-only session; first *measured* span rate on stored evidence.

**The prompt was silent on anchoring**, as the previous entry hoped. It was also silent on the
graph: the owner said only *"you can use archgraph to quickly gain context on the item domain"*.
The session read the skill pointer, then `.archgraph/agent-operating-policy.md`, then ran
`status` + four `search_nodes` + two `get_node`. **It wrote nothing** — an intention-shaping
session produces no architectural delta, so there was again nothing to anchor.

**The clean test therefore still has not run.** Four sessions now. Spans emitted by any agent
since the policy change: still **0**, and still unmeasured rather than good.

**What this session did produce is the first non-trivial sample of stored evidence.** Two
`get_node` calls returned, between them, **14 current evidence entries** (3 node-level, 11 on
relationships). Span rate:

| | count |
|---|---|
| Current evidence entries read | 14 |
| Carrying `startLine`/`endLine` | **1** |
| That one also carrying a `symbol` | **0** |

The single span is on `domain-item-economics --contains--> projection-item-economics-task-budget-allocations`
(`get_task_budget_allocations.py`, 100–283). It has **no `symbol` field** — which is precisely the
case the policy reserves spans for, a region with no name of its own. Every other entry is
path+symbol and span-free. **On this sample, stored evidence already matches the policy**, which
is a better picture than the 2026-08-23 summary's "2 of 2 carrying a span" suggested; that summary
measured one pending review item, not the settled graph.

**Two things the tool still hands an agent whether or not it wants them.** `evidenceHistory`
entries retain their `startLine`/`endLine` alongside `supersededAt` — so the superseded record of
a span-free entry still shows the numbers it used to carry. And `sourceLinks` carry ranges, which
the policy permits and explicitly says is not a pattern to copy into evidence. An agent reading a
node sees spans in both places before it sees the span-free current evidence.

**Staleness, reported and not acted on.** All four `sourceLinks` on
`projection-item-economics-task-production-time` and the one on the allocations projection came
back `stale: true`; `status` reported 6 stale nodes and 3 pending reviews. The session took no
repair, re-anchor, review or maintenance action on any of it, and did not raise it as a finding —
the counts stayed observations. Consistent with the count-gating behaviour the previous entry
recorded, under a session that had every opportunity to tidy.

**Describe, do not fix. The brief stays open** — and the next graph-*writing* session in this
workspace is still the one that matters.

---

## 2026-08-24 — mechanism-inventory round 1, task budget overrun signal (Claude Opus 5)

**Session type:** planning gate (mechanism-inventory doctrine). **Graph writes: zero.**
Reads only: `archgraph_status`, then `archgraph_get_node` on `domain-item-economics`,
`endpoint-item-economics-task-budget-allocations` and
`decision-money-audience-admin-manager-only`. No `compute_impact`, no `search_nodes`, no
`repair_anchors`, no review action, no `current-task.md` access.

**1. New evidence written:** none. Nothing to score.

**2. What the reads handed the session, unasked.** Same shape as the 2026-08-24 shaping entry,
now on a different node set. Of the three nodes read:

| Node | Current evidence entries | Carrying a span | Carrying a `symbol` |
|---|---|---|---|
| `domain-item-economics` | 3 | **3** | 0 |
| `endpoint-item-economics-task-budget-allocations` | 1 | 0 | **1** |
| `decision-money-audience-admin-manager-only` | 4 | 0 | **4** |

`domain-item-economics` is the outlier and it is the *old* shape: all three entries are
`calculator.py` with `1–52`, `131–242`, `375–547` and **no `symbol`**, while their own
`evidenceHistory` shows the superseded versions **did** carry symbols
(`CALCULATION_VERSION`, `calculate_term_amount`, `rederive`). So on this node the graph moved
from named anchors to spans, not the other way. Two of the three could plainly have used a
name — `1–52` is the module header/version block (arguably span-legitimate), but `131–242` is
`calculate_term_amount` and `375–547` is the re-derivation function. Recorded, not corrected.

The other two nodes are span-free path+symbol throughout, including all four evidence entries
on the money-audience decision.

**3. Re-anchor activity:** none.

**4. Did the session anchor its own findings the new way?** This is the observation worth
having, because the session produced twenty-two mechanism contracts, each citing code. It
anchored **almost entirely by `file:line`** — `budget_division.py:149`, `calculator.py:273`,
`get_task_budget_allocations.py:229`, and roughly forty more — with the symbol named in prose
beside the number rather than as the anchor. It also caught **seven of its own citations
drifting** on a re-derivation pass and corrected the numbers rather than switching to names.
Its own shaper predecessor had written the warning it then ignored: *"They are still line
numbers: treat a mismatch as drift, not as a contradiction, and re-anchor on the symbol."*

**The observation, stated plainly.** The span-free policy lives in
`.archgraph/agent-operating-policy.md` and governs **graph evidence**. Nothing carries it into
how agents cite code in *documents*, and a session that never writes to the graph never reads
the policy at all. This one read the graph three times and cited code forty-odd times, all by
line, and nothing anywhere told it not to. **Whether that matters is the owner's call; the
brief says describe, do not fix.** The next graph-*writing* session is still the one that
tests the policy as written.

---

## 2026-08-25 — plan-reviewer round 1, task budget overrun signal phase 2 (Claude Opus 5)

**1. Session shape:** read-only review of an implemented phase. Graph access was
`archgraph_status` plus one `archgraph_get_node` on the projection the previous session wrote.
No graph write, no review decision, no anchor repair, no `build_context`.

**2. How the node under review was anchored — the observation worth having.** The
implementer's phase-2 batch (one projection node, one `contains`, four `reads_from`, one
`implements`) is anchored **span-free throughout**: every one of the seven evidence entries
carries `path` + `symbol` + `summary` + `inferenceReason`, and not a single line number
appears anywhere in the node, its metadata, or any of its six relationships. The symbol is the
same one in all seven (`get_task_budget_signals`), which is the shape the policy asks for. So a
graph-*writing* session did test the policy as written, and it held — that is the case the
2026-08-24 entry said was still outstanding.

**3. Re-anchor activity:** none. `sourceLinks` is empty and `reviewState` is `pending`.

**4. Did the reviewing session anchor its own findings the new way?** Mixed, and the split is
informative. Where the finding was about a *symbol*, it anchored by name — `compute_budget_signal`,
`_BUDGET_STATUSES`, `NUMERIC_KEYS`, `test_c7_b_open_record_moves_only_live_time_fields`. Where
it was about a *location inside a function body* — the ten-key row dict — it fell back to
`get_task_budget_signals.py:406-421`, three times, because the thing it needed to point at has
no name. Same for the two mutation-probe rows, which the charter requires to name file **and**
site. It also cited `item_cost_evaluation.py:30,37,39` for three column declarations, again
nameless-in-Python targets.

**The pattern across two sessions now.** Line numbers survive exactly where the language gives
the target no name: statement blocks, column declarations, dict literals. The graph's own
evidence never hits that case, because it anchors at definition granularity — which is why the
policy is easy to obey there and awkward in prose. The inventory session's forty `file:line`
citations were mostly *avoidable*; this session's were mostly *not*. Whether the policy should
say anything about sub-symbol targets is the owner's call. Described, not corrected.

---

## 2026-08-25 — plan-reviewer re-review round 1, task budget overrun signal phase 2 (Claude Opus 5)

**1. Session shape:** delta-scoped re-review of a fix checkpoint. **Zero archgraph calls** — no
`status`, no `get_node`, no `build_context`, no write, no review decision, no anchor repair. The
prompt's perimeter was a single test file and the session never needed the graph to answer it.
This is the shape the 2026-08-24 entry called the policy's blind spot from the other side: not a
session that reads the graph and cites code by line anyway, but one that never opens the graph at
all and still writes forty-odd code citations into a handoff.

**2. How the fix session (Codex) reported the graph.** Its handoff's "Architecture Graph
assessment" names the node by **id** (`projection-item-economics-task-budget-signals`) and its
relationship kinds by name, with no line numbers anywhere and no path:line anchoring of any graph
claim. Its declared deltas are all zeros. So an implementing session that had nothing to record
described the graph span-free and by identifier — the policy's preferred shape held without the
session being told about it.

**3. Re-anchor activity:** none. No item's `reviewState` changed; the phase-2 projection and its
six relationships remain `pending`.

**4. Did this reviewing session anchor its own findings the new way?** The same split as the
2026-08-25 round-1 entry, in the same proportion, and for the same reason. By **symbol** where a
symbol exists: `serialize_budget_signal`, `compute_budget_signal`, `_budget_seconds`,
`calculate_consumed_cost_minor`, `_BUDGET_STATUSES`, `load_live_worked_seconds`,
`test_c8_e_money_fields_map_to_distinct_nonzero_operands`. By **file:line** where the target has
no name of its own: `division_serializers.py:79,81` (two entries inside a returned dict literal —
the probe site, which the charter's mutation-probe rule requires to be sited precisely),
`get_task_budget_allocations.py:48` (a module-level assignment), `get_task_budget_signals.py:406-421`
(the row dict, quoted from review r1), and `intention.md:3-4` (lines in a document, outside the
policy's scope entirely).

**5. The observation this round adds.** The line-numbered citations were **not** the graph's
concern in any of the four cases — one is a document, one a probe site the *charter* mandates be
sited to the statement, and two are sub-symbol targets Python gives no name. Two sessions now show
the same boundary: agents anchor by symbol whenever the language supplies one, and reach for a
span only where it does not. Nothing in either session suggests the policy is being ignored; what
they suggest is that the residual span usage is concentrated in a case the policy does not
actually address — and one of those cases is required by a *different* standing rule. Whether the
two rules should be reconciled is the owner's call. Described, not corrected; the sessions were
not told this log exists.

## 2026-08-25 — task_budget_overrun_signal plan-3 review (round 1), reviewer, Opus 5

**First entry with a measured span rate on new evidence.** Every prior entry since the policy
change recorded "unmeasured" because no session had written any. This round has four new evidence
entries sitting in the tree, written by two different sessions, and I read them off
`.archgraph/architecture.yml` directly — **no `archgraph_*` tool was called this session**, so
nothing here is second-hand through tool output.

**1. My own writes: zero.** A reviewer records findings, not deltas.

**2. New evidence in the unstaged graph diff — two provenance groups, both first-hand.**

- **Phase-3 implementer (Codex), `createdAt 2026-08-25T06:35:03.125Z` — 3 evidence entries, 3 with
  `symbol` (100%), 1 with a span (33%).** The `endpoint-item-economics-task-budget-signals` node's
  single entry carries `path: app/beyo_manager/routers/api_v1/item_economics.py`, `symbol:
  route_get_task_budget_signals`, **and** `startLine: 335` / `endLine: 347`. The cited code is a
  named function — it had a name it could have used instead, and it used it, *and also* emitted the
  span. Its two edges (`accepts`, `governed_by`) cite the same path and symbol with **no** span.
- **Bootstrap Pause-Reason Seeding (foreign work, `createdAt 2026-08-24T13:47:21.336Z`) — 4
  evidence entries, 4 with `symbol`, 0 with spans.** Node (`seed_pause_reason_links`,
  `bootstrap_app`) and both `depends_on` edges (`seed_pause_reason_links`) are span-free.

**Span rate on new entries: 1 of 7 (14%). Symbol rate: 7 of 7.**

**3. Re-anchor activity:** none. No `re-anchor` op, no `archgraph_repair_anchors`, no
`reviewState` change. The phase-2 projection node and its edges remain as recorded.

**4. Review findings about location: none filed, by me or by anyone.** I did verify that the
recorded span resolves — `route_get_task_budget_signals` occupies lines 335–346, so 335–347 runs one
blank line long — and deliberately did **not** report that as drift, a discrepancy or a repair
candidate. It is not in my handoff as a finding; it appears once, as a parenthetical inside the
provenance assessment the prompt asked for. Worth logging that the temptation was real: this phase
*relocated a pre-existing route block*, which is exactly the "position changed" event the policy
says is not an event, and a reviewer inclined to treat spans as truth would have had a
ready-made line-number story to tell.

**5. Closing-work language — one quote that matters.** The implementer handoff's graph section
reads: *"No source links were recorded; evidence is **symbol-anchored** to
`route_get_task_budget_signals`."* The session **describes** its own write as symbol-anchored while
the write it made carries `startLine`/`endLine`. That is not deception; it reads as a session whose
mental model is the new policy and whose emitted payload is the old shape. No "keeping anchors
current" or "pointing at the old place" vocabulary appears anywhere in the handoff, the plan or the
prompt.

**6. The confound this round is the inverse of the previous project's, and it is the finding.**
`narrow_typical_work_times` carried an explicit *"do not emit `startLine`/`endLine`"* in its master
plan, so compliance there proved nothing. **This project's artifacts instruct the opposite**, in
three places a session is required to read:

- the **shared pipeline charter**, project-affordance section — *"record the phase delta at end
  (one batched apply_changes, **accurate evidence spans**)"*. Every session of every project reads
  this file.
- `master_plan.md` §8 — *"one batched `archgraph_apply_changes`, recording only what the tree
  proves, **with evidence spans on the closing commit**"*.
- `plans/plan_3.md` §8 — *"**evidence span** on `route_get_task_budget_signals` in the closing
  tree."*

The implementer prompt itself is silent on anchoring and simply says "follow master-plan §8". So
the one span this round was **instructed, not habitual** — and the instruction's root is the
charter, not this project. The two span-free edges in the same batch, written seconds apart by the
same session, are the control: where the plan named a span it emitted one, where it did not it
anchored by symbol alone. The bootstrap session's four span-free entries point the same way.

**Reading (described, not proposed).** The policy text does appear to be reaching sessions — 6 of 7
new entries are span-free and the one exception is traceable to a written instruction rather than to
habit. What has not been reached is the **instruction layer**: the charter still says "accurate
evidence spans", and every master plan and phase plan that quotes it inherits the sentence. The
previous entry observed that the phase plans had become "the surviving teachers of the old habit";
this round locates the teacher one level higher.

**Standing confound, restated:** no session yet observed has had a prompt *silent* on anchoring
while reading artifacts *also* silent on it. A clean test still needs that.

Related: [[project-task-budget-overrun-signal]], [[project-archgraph-anchor-observation-brief]].

---

## Observation — 2026-08-25, plan 3 re-review round 1 (Claude Opus 5)

**Sample: zero.** No `archgraph_*` tool was called and no evidence entry was written. The
re-review prompt forbade graph mutation outright ("do not … change graph state"; "no graph
mutation is authorized in this session"), so the session had no occasion to anchor anything.

**What is still worth recording, because it is the negative half of the standing confound.**
This session read both instruction-layer sentences the previous entry identified — the charter's
project-affordance clause (*"accurate evidence spans"*) and `plans/plan_3.md` §8 (*"evidence span
on `route_get_task_budget_signals` in the closing tree"*) — and read them in a session where the
prompt was silent on anchoring. Neither sentence produced any anchoring behaviour, because the
prompt's explicit prohibition on touching the graph preempted the question entirely. So this is
**not** the clean test the standing confound asks for: prompt-silence was overridden by
prompt-prohibition, not by artifact instruction.

**Reading (described, not proposed).** The instruction layer's reach is still unmeasured for
review-role sessions. Every graph-writing observation so far comes from implementer or bootstrap
sessions; reviewers are structurally barred from writing evidence (the charter's *"agents never
promote/reject/edit review items"*), so a reviewer will never supply a sample. The clean test
identified in the previous entry can therefore only come from an **implementer** session whose
prompt and whose master/phase plans are all silent on anchoring — a narrower opening than the
previous entry's phrasing implied.

Related: [[project-task-budget-overrun-signal]], [[project-archgraph-anchor-observation-brief]].

## 2026-09-02 — typical filter category names, graph recording session (Opus 5), four maintenance `edit`s

**No new evidence entry was written this session**, so span rate on new entries stays
**unmeasured — now six sessions since the policy change.** The whole delta was four description
`edit`s across two `archgraph_apply_maintenance_changes` batches; `edit` touches no anchor, so
this session produced no anchoring datapoint from my own hands.

**Re-anchor activity: none.** No `re-anchor` op, no `archgraph_repair_anchors` call. Nothing
triggered one: every symbol on every node I read still resolves in its file.

**What the reads showed — the hash tier is now uniformly stale on this branch.** All four
projection nodes' `sourceLinks` came back `"stale": true`:

- `projection-item-economics-task-production-time` — 4 links, all stale. Two still carry legacy
  spans (`budget_division.py:_governing_step` 188–208, `get_task_production_time.py:get_task_production_time` 26–121);
  two are span-free (`test_narrowed_task_economics.py`, and `test_production_time_query.py` still spanned 108–160).
- `projection-item-economics-task-budget-allocations` — 1 link, span-free, stale.
- `projection-item-economics-task-price-scenario` — 5 links, all span-free, all stale.
- `projection-item-economics-task-budget-status` — no source links at all.

This is the **hash** tier going stale because the files changed, not the address tier going
wrong: every path and symbol resolves. Per the policy that is not a repair candidate and I did
not treat it as one — but it is worth logging that a reader of these four nodes now sees
`stale: true` on **ten of ten** source links, which carries no signal at all once it is
universal. The span-free links and the span-bearing ones are indistinguishable in that state.

**Closing-work language: none used by me.** I reported the staleness as an observation and
explicitly did not act on it, and did not describe the session as "keeping anchors current."

**Second-hand observation — the implementing agent's brief.** The handoff
`docs/handoff/ARCHGRAPH_RECORD_typical_filter_category_names_20260902.md` was written by a
session with no MCP connection, and it is **dense with line citations in prose**: "line ~119",
"line ~151", "line 64", "line 97", "lines ~149–160", "lines ~149–160" again in the evidence
table. Every one of them was approximately right and none of them was necessary — each cited a
named function I could have found by symbol, and the brief names the symbol too in most cases.
Same habit as the previous entry's finding: **line numbers still travel freely in prose, where
no policy reaches**, even from a session that never touched the graph. Here they cost nothing
because they were checkable and the symbols were given alongside; the failure mode logged on
2026-08-24 (a wrong `file:line` changing a conclusion) did not recur.

*(Non-anchoring aside, routed here only because it will recur: two of these four descriptions
were at **1996 and 1997 characters against the 2000-character `description` cap**, so a
three-sentence amendment could not be added without compressing existing prose. And the
four-operation batch was refused at preview for exceeding the **16384-byte audit-record limit**
— 18910 bytes — forcing a split into two previews and two authorizations. These item-economics
projection descriptions have accreted one clause per shipped change since 2026-08-16 and have
now run out of room; the next change to this branch cannot be recorded additively. That is the
owner's to adjudicate, not mine.)*

Related: [[project-item-properties-complexity]], [[project-archgraph-anchor-observation-brief]].

### Same session, second half — owner authorized human-confirming the graph (15 promotes, 1 investigate)

Directly relevant to this brief, because promotion is the moment an anchor stops being
provisional. **Still zero new evidence entries written** (review promotes existing ones), so
span rate on new entries remains unmeasured. But the queue itself is now measurable:

**Span rate on the 16 pending items' evidence: 1 of 17 entries carried a span.** Only
`node:endpoint-item-economics-task-budget-signals` (created 2026-08-25) had
`startLine 335 / endLine 347` *alongside* a resolving `symbol`. Every other entry across all
four clusters — bootstrap pause-reason seeding (2 entries), budget signals (7), the endpoint's
other two, remaining production pressure (3) — was **path + symbol, span-free**. That is the
first real measurement since the policy change and it is a good one, though the standing
confound still applies: these were written by sessions under the same project prompts.

I **promoted that span-bearing entry without stripping the span**. The policy permits dropping
it via `anchors` on the promote, and it would have cost nothing — the span is currently
accurate (the route is 335-346). I left it because the owner authorized confirming the graph,
not anchor surgery, and because this brief says record rather than correct. So the graph now
carries one **human_confirmed** span, which is a stronger form of the same debt: it reads as
settled, and 335-347 will rot the next time anything is inserted above it in
`routers/api_v1/item_economics.py` — a file that has already moved these routes twice
(`evidenceHistory` on the sibling endpoints shows 370-381 → 371-382 and 385-396).

**A location finding that blocked a promotion — the is/calls trap, caught in the wild.**
`edge:source-file-item-economics-budget-division--implements-->projection-item-economics-task-budget-signals`
carries a **true claim on caller-anchored evidence**: path `get_task_budget_signals.py`, symbol
`get_task_budget_signals`, summary *"The service **calls** divide_production_budget with allowed
minutes, loaded DivisionStep rows, and the reconciled selected typicals before computing each
signal."* An `implements` edge whose source is `source-file-item-economics-budget-division`
should cite the module that implements, not the service that calls it. The tell is the one the
policy names verbatim, sitting in the summary.

What makes it decisive rather than a judgement call: **both human_confirmed siblings of this
exact relationship anchor the other way** — allocations and production-time each cite
`budget_division.py`, symbol `divide_production_budget`, summary in the *supplies* voice
("The pure division function supplies each task allocation projection with..."). So the
divergence is measurable against settled precedent in the same graph, not against my taste.

The server had **no contradiction to offer** on the substance — it flagged only two benign
`conflicting-canonical-relationship` notices (that `budget_division` already implements two
other projections, which is simply what one-to-many looks like) and suggested `investigate` for
that structural reason alone. **The real defect was invisible to it**, exactly as the policy's
"why step 4 carries the weight" paragraph predicts: fileExists true, symbol resolves, no drift,
and a caller-anchored claim sails through. Only re-reading the source caught it.

I recorded `investigate`, which leaves it pending and `ai_inferred`. `anchors` alone cannot
repair it — repointing to `budget_division.py` would leave a summary describing the caller
attached to the callee, and anchors may not touch a summary. That is the boundary between
"address is wrong" and "claim is written from the wrong place", and this one is the latter.

**Signal-to-noise observation on the detector.** Across the 16 items, **12 contradiction
notices fired and all 12 were benign** — every one was `conflicting-canonical-relationship`
on a relationship type that is legitimately one-to-many (`contains` from a domain fired six
times, `reads_from` from one projection three times, `implements` twice, `depends_on` once).
The three items with the *most* notices were all correct; the one genuinely defective item drew
two notices indistinguishable from the benign ten. A reviewer triaging by notice count would
have inverted the answer.

Related: [[project-remaining-production-pressure]], [[project-task-budget-overrun-signal]],
[[project-archgraph-anchor-observation-brief]].
