---
plan: 3
role: reviewer
round: 4
date: 2026-08-22
project: test_isolation_and_xdist
---

# Session prompt — plan 3 review r4, `test_isolation_and_xdist`

## 1. Role and mode

You are the **first review this phase has had.** Four implementation rounds have run — implement
r1, fix r2, fix r3 — and every verdict so far is either the implementer's own or the coordinator's.
Nobody outside that loop has read this code.

So this is a **full first review**, not a delta-scoped re-review: the complete checklist against
the plan's criteria and the semantic authorities. It is also the last gate before a baseline that
three other projects consume becomes authoritative.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Branch `feat/test-isolation-xdist`. HEAD `67821a4`, clean.

**Read first, by absolute path, as this session's doctrine:**
`/Users/davidloorenz/agent-skills/pipeline-charter.md` (including **"Test-evidence scope and
reuse"**, **"Owner decisions — the decision-card format"**, and **"The owner layer"**) and
`/Users/davidloorenz/agent-skills/plan-reviewer.md`.

**You write files this session** — your handoff, and the architecture-graph decisions in §8.
A previous round of this project was told to write nothing, produced its review in chat, and the
owner had to paste 400 lines by hand. Do not repeat that.

## 2. Gate check — stop and report if any is false

- `plans/plan_3.md` frontmatter reads `state: IMPLEMENTED` and its §7 carries entries for
  projection r0, implement r1, fix r2, fix r3, and three coordinator consumptions.
- `git status --porcelain` is empty.
- `app/pytest.ini` contains `-n 6 --dist loadfile`.
- `git diff b96802f HEAD -- app/` is **empty** — the executable tree is byte-identical to the tree
  every fix-r3 measurement was taken on. This is what lets you cite those measurements instead of
  re-running them, and it is the form this project uses for gate checks after a prompt that pinned
  a bare SHA went stale within a minute of being written.

## 3. Read order

1. `plans/plan_3.md` in full — §4 tasks 1–9, **§4A task 10 and §4B criterion C8** (added after fix
   r2 under an owner decision), §5 criteria C1–C7, §5A inherited traps, §6 budget, **§7's review
   log, which is the phase's whole history and the shortest path into it.**
2. `../master_plan.md` — **§5's nine standing rules bind this review**, §6 is the environment
   authority (do not re-derive it; if reality disagrees, that is a finding), §8 the published
   baselines.
3. `planning/intention.md` — §1 verbatim (the correctness gate and the mutation-testing
   consequence), then **OD-10, OD-9, OD-8, OD-6, OD-7**. OD-10 is the newest and changed what
   ships.
4. `handoffs/reviewer/2026-08-21_phase3_projection_r0_handoff.md` — the projection's 25 ledger
   rows and its three measured findings.
5. The three implementer handoffs in `handoffs/implementer/`, in order.

## 4. Settled ground — cite it, do not re-run it

Coordinator-measured, tree-bound, matching your tree. **Re-running any of it is over-evidence and
a finding against this round. Contradicting any of it is a finding worth reporting loudly.**

- **The shipped default is `21 failed / 2576 passed` in 52.62 s and 53.26 s; the `-n 0` comparator
  is `21 failed / 2575 passed / 1 skipped / 1 deselected` in 150.70 s.** All three on `b96802f`,
  clean, `comm` empty in both directions against the phase-2 21-ID set.
- **Collection is 2597 selected**, exactly one more than fix r2, and that one is C8.
- **The perturbation harness is collection-neutral**, measured by ID count: unset → 2594 / 0
  probes at r1's tree, each enabled position → +1. Gating keys off the environment variable, never
  worker identity.
- **Residue is `beyo_test_main_template` alone** on `localhost:5433`.
- **The requirements manifests are correct** — `app/requirements.txt` is byte-identical to
  `c73c017`; `pytest-xdist==3.6.1` is pinned only in `requirements-dev.txt`.
- **`planning/intention.md` is byte-identical to `c73c017`** plus the coordinator's OD-10 section.

## 5. Depth allocation — where this phase can still be wrong

Charter rule 6 allocates effort by silent-failure risk. Spend your deep passes here.

1. **The criteria, against the code, one at a time.** C1–C7 were amended after a projection that
   found four of phase 2's seven criteria could not fail. C8 is nine hours old. For each: could
   this row pass while the thing it names is broken? **Standing rule 2's companion is the sharp
   version — a row whose fixture satisfies two independent sufficient causes cannot fail when one
   breaks.** This project has recorded fifteen instances of that class.
2. **The five-step destructive guard, at its boundaries.** `assert_disposable_database` decides
   whether a `DROP DATABASE` proceeds. Phase 3 changed its endpoint normalisation twice — first
   widening it to treat `0.0.0.0` as this host, then narrowing it back. Read the final state
   against every input that reaches it, not against the description of it.
3. **Concurrency on the template.** A per-slot advisory lock protects the whole
   ensure/rebuild/drop/copy region. Six workers now serialise through it on every run. Look for
   what happens when a holder dies, when two slots collide, and whether the lock's key can
   collide across slots.
4. **What the parallel default changed that nobody listed.** Making `-n 6` the default silently
   re-pointed every inherited command and every developer habit. Fix r3 caught one instance — the
   legacy reclamation sweep, documented as serial-only, which now carries `-n 0`. **Assume there
   are more.** §6.1's reversed-collection row is a specific candidate: it was phase 2's serial
   order-independence probe and now runs under six workers, where it no longer isolates ordering.
5. **The published baseline itself.** Three projects consume it. Is `21 failed / 2576 passed` the
   number a fresh checkout gets, or does it depend on something local — Redis being up, a slot
   variable, a leftover template, the machine's core count?

## 6. Two named probes — confirm or refute, do not take them on trust

Both are the coordinator's, from consuming fix r3. They are **hypotheses, not findings.** If you
refute either, say so plainly; a refuted coordinator claim is a good outcome for this gate.

**Probe A — C8's behavioural sub-check may have no mutation.** C8
(`test_shipped_default_reaches_an_xdist_worker`) makes two assertions: the `addopts` token
sequence, then `PYTEST_XDIST_WORKER` matching `gw\d+`. The plan's named mutation removes `-n 6`
from `pytest.ini`, which reddens the **first** assertion and returns before the second runs. So
the recorded evidence may prove only that the string check works, leaving the half that actually
proves work was distributed unproven. Delete the `PYTEST_XDIST_WORKER` assertion and see whether
anything reddens — that is an L1 question. Project standing rule 4: enumerate sub-checks from the
code's branch points, not from the prose.

**Probe B — C8 hardcodes the worker count that OD-10 expects to change.** The assertion requires
the literal `["-n", "6", "--dist", "loadfile"]`. OD-10 states that raising the count is permitted
with a measurement. When someone raises it to eight, C8 reddens with *"shipped parallel default is
missing from pytest.ini"* — a false message about a legitimate change. That is the N4 time-bomb
shape, reintroduced by the criterion written to protect the default, in the phase that removed the
original N4. The contract C8 owns is *"the configuration, not the command line, produced
parallelism."* Judge whether the implementation expresses that contract or a narrower one, and if
narrower, say what the row should assert instead.

## 7. Evidence budget

**This session's L4 budget is 0 runs.** `git diff b96802f HEAD -- app/` is empty, so the fix-r3
stamp is tree-bound to your tree and is cited, not reproduced. You ship no code and hand over no
tree, so there is no closing stamp to take.

**One exception, and only one:** a **repository-wide absence claim** — "no test anywhere guards
X", expecting an empty result — is L4 by construction (charter L4(d)). If you need one, write the
charter's authorization line **before** the run, stating what narrower evidence could not answer.

Everything else runs at L1/L2: single test files, `--collect-only`, `pip show`, a database query,
and **every mutation you apply to test a criterion.** Mutations are where this gate earns its
keep — a criterion that survives the defect it exists to prevent is decoration, and reading it
cannot tell you which it is.

Revert every mutation. Declare every file you touched, separately from your findings, with the
verification that it was restored. Destructive verification on disposable databases only; the
configured `beyo_manager` database is never a target and is left at head.

## 8. Architecture graph — delegated authority, granted in writing

**The charter's default is that agents never promote, reject or edit review items; the human
adjudicates. The owner has delegated that authority to this session, verbatim:**

> *"the reviewer will also look at the archgraph and check those four new entries that are waiting
> for human approval, check them and approve them if correct, otherwise edit them accordingly and
> then approve them"*

The four pending items, all `ai_inferred`, all additive:

| itemId | what it claims |
|---|---|
| `node:infrastructure-template-copy-contention-lock` | "Per-slot template-copy advisory lock" (recorded by implement r1) |
| `edge:infrastructure-test-database-isolation--contains-->infrastructure-template-copy-contention-lock` | the lock is contained by the isolation infrastructure |
| `node:configuration-shipped-pytest-parallel-default` | "Shipped pytest parallel default" (recorded by fix r3) |
| `edge:infrastructure-test-database-isolation--configured_by-->configuration-shipped-pytest-parallel-default` | the isolation infrastructure is configured by that default |

**Verify each against the implementation before deciding.** Read the evidence span the item cites
and confirm it says what the item claims — the node names, the type, the edge direction, and
whether the evidence lines still contain the symbol. An item that is *approximately* right is not
right: this graph is read by future sessions as fact.

**One mechanism you need before you start, measured on 2026-08-21 and it will cost you a cycle if
you learn it the hard way: an evidence summary is immutable.** No write path can edit one.
"Editing" an item means **reject it and re-record it** with corrected content — and a re-record
under the same id **re-enters the review queue**, so a corrected item needs a second pass to
approve. Plan for two passes on anything you correct, and do not report a corrected item as
approved until you have actually approved the re-recorded version.

Sequence: `archgraph_status` → `archgraph_list_pending_reviews` → `archgraph_get_review_item` for
each → verify against the code → `archgraph_preview_review_decisions` → `archgraph_apply_review_decisions`.
Preview before applying, every time. Report the final `archgraph_status` — node count, edge count,
pending count, diagnostics — in your handoff, and state the revision hash.

**Still out of bounds:** the three items promoted to `human_confirmed` at revision `f5bf3a7` are
settled. Do not reopen, edit or re-record them. If phase 3 changed what they describe, record the
delta **additively** and leave it pending for the owner.

## 9. Closing protocol

Deposit **one handoff** at
`handoffs/reviewer/2026-08-22_phase3_review_r4_handoff.md` with charter frontmatter
(`plan: 3`, `role: review`, `round: 4`, `verdict`, `date`, `actor`). The Review-log line in
`plans/plan_3.md` is the coordinator's, not yours — your only document writes are this handoff and
the graph decisions.

Contents, in order:

1. **Verdict** — `APPROVED` or `CHANGES_REQUESTED`.
2. **Owner-readable opening**, 3–5 sentences, no citations and no jargon: what the review
   concluded, whether anything needs the owner personally, what happens next.
3. **`⚠ OWNER DECISIONS REQUIRED (n)`** immediately after it, in the charter's card format — story
   first, branches as consequences, exactly one recommendation, on-silence behaviour. Findings
   cite their card; they never contain it. If nothing needs the owner, one line saying so.
4. **Findings**, blocking / should-fix / note, each with the exact artifact and line, the defect it
   would let through, and — where you tested it — the mutation you applied and both sides of the
   result.
5. **Probes A and B**, answered explicitly by name, confirmed or refuted, with the evidence.
6. **Criteria table** — C1 through C8, each marked met / unmet / decoration, with the reason.
7. **The architecture-graph section** — per item: what it claimed, what you verified, the decision
   you applied, and for anything you corrected, both passes. Final status and revision hash.
8. **Your full write perimeter** — documents, code, tool-recorded state. Every mutation-probe file
   listed separately from your own writes, with its restoration verified. Every probe database and
   its disposition. **Your L4 count as a number** (expected: 0).
9. Your final chat message follows the charter's **owner layer** — what you did, what it means in
   plain words, what happens next, what needs the owner. Not a paste of the handoff.

The handoff file, not your chat message, is what the coordinator consumes.
