---
plan: 3
role: reviewer
round: 6
date: 2026-08-22
project: test_isolation_and_xdist
---

# Session prompt — plan 3 re-review r6, `test_isolation_and_xdist`

## 1. Role and mode

**Delta-scoped re-review** closing fix r5, per the charter's review protocol. Review r4 did the
full first review of this phase; you verify that its findings were resolved without collateral, and
you judge one new construction it has never seen.

**This is the last gate before approval.** Phase 3 is the final phase of this project, and the
baseline it publishes is consumed by `live_clock` phase 4 and `narrow_typical_work_times` D23. If
you approve, the coordinator takes the gate stamp and closes the project.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Branch `feat/test-isolation-xdist`.

**Read first, by absolute path, as this session's doctrine:**
`/Users/davidloorenz/agent-skills/pipeline-charter.md` (including **"Test-evidence scope and
reuse"**, the **review protocol**, and **"The owner layer"**) and
`/Users/davidloorenz/agent-skills/plan-reviewer.md`.

**You write files this session** — your handoff. The Review-log line is the coordinator's.

## 2. Gate check — stop and report if any is false

- `git status --porcelain` is empty.
- **`git diff 4b5719d HEAD -- app/` is empty** — the executable tree is byte-identical to the tree
  fix r5 took its closing stamp on. This is what sets your L4 budget to 0 (§6).
- **`git diff 8501a51 HEAD -- app/` touches exactly two files**: `app/.env.example` (1 line) and
  `app/tests/integration/infrastructure/test_database_isolation.py` (+86/−9). That is your entire
  code delta — everything review r4 has not seen.
- The architecture graph reports **194 nodes, 291 edges, 0 pending, 0 diagnostics**.

*(Gates in this project are written against diffs rather than against `HEAD` equalling a sha:
standing rule 8, earned five times. Do not check for a particular HEAD.)*

## 3. Read order

1. `handoffs/implementer/2026-08-22_phase3_fix_r5_handoff.md` — the round you are reviewing.
2. `handoffs/reviewer/2026-08-22_phase3_review_r4_handoff.md` — **your predecessor's findings, and
   its §9 "verified correct", which is settled ground you do not re-verify.**
3. `plans/plan_3.md` §7's **fix-r5 consumption entry** — it carries three named probes for you and
   discloses a coordinator defect you would otherwise waste time on (§4 below).
4. `master_plan.md` §5's thirteen standing rules — **10, 11, 12 and 13 were earned by review r4 and
   bind this round.** §6 is the environment authority; §8 the published baselines.
5. `planning/intention.md` **OD-10**, for what the shipped default is and why.

## 4. A coordinator defect that corrupts the commit record — disclosed so it does not confuse you

While fix r5 was mid-flight, the coordinator ran `git add -A && git commit` to correct two prompts.
**Commit `4b5719d`, whose subject reads *"fix the r5 and maintenance gate checks"*, therefore also
contains fix r5's code: `app/.env.example` and 93 lines of the criterion module.** Two sessions'
perimeters are merged under a subject describing one of them.

Do not try to reconstruct the boundary from history — it is not there. **Use `git diff 8501a51 HEAD
-- app/` as the round's perimeter**, which is exact regardless of how the commits were cut.

The coordinator already established that the damage is attribution rather than correctness, and
**you should not re-derive this**: fix r5's three closing checksums reproduce on today's tree, and
two of them — `app/tests/database_isolation.py` at `86434edf…` and `app/pytest.ini` at
`392e7102…` — are byte-identical to the values **you published in review r4 before applying
M4–M7**. Your own prior baseline proves the probes were reverted. Cite it; do not recompute it.

## 5. Depth allocation

### 5.1 The new construction — where all your adversarial effort belongs

B1's repair is **not** the correction review r4 wrote, and the divergence is the interesting part.

r4 proposed: hold a template connection across the copy and assert *"with the lock present the copy
waits behind it and passes."* **That does not work** — an advisory lock is cooperative between our
own processes and does nothing about an external session connected to the template, so
`CREATE DATABASE … TEMPLATE` refuses regardless and the row would redden in the correct
configuration too. The implementer found this and built something else without saying so.

What shipped (`test_concurrent_starts_survive_current_template`): it holds a template connection,
then monkeypatches **two** methods on each probe — `_maintenance_connection`, to tag the session
with a distinguishing `application_name`, and `_create_database_from_template`, to query `pg_locks`
for a granted advisory lock held by that probe before copying. **If the lock is observed, it closes
the held connection and copies; if not, the connection stays open and the copy raises
`ObjectInUseError`.**

Judge it hard. Specific things to decide:

- **What does the row actually prove?** It asserts *a lock is held at the moment of the copy* — the
  invariant task 3 states — not *concurrent copies survive*. Under the shipped code the obstruction
  is removed before the copy, so the lock's mutual exclusion is never exercised. Is that the right
  contract, mis-described, or a weaker one wearing the stronger one's name? The handoff says "M4
  and M5 expose PostgreSQL's `ObjectInUseError`", which reads as the real hazard reproducing when
  the error is produced by the test declining to close its own connection.
- **The two probes share one connection object.** The closure captures `connection` from the
  enclosing scope. The first probe to observe its lock closes it; the second then sees
  `is_closed()` and skips. Only one of the two concurrent probes is ever tested against a held
  connection. Does that halve the row's power, or does it not matter?
- **They run under `asyncio.gather`.** Two coroutines can both pass `not connection.is_closed()`
  and race into `close()`. Is that benign in asyncpg, or a flake waiting for a slower machine?
- **Does it still bite?** fix r5 reports M4 reddening rows (a)/(b)/(c) with
  `UniqueViolationError` / `InvalidCatalogNameError` / `ObjectInUseError`, and **M5 — the call-site
  narrowing plan task 3 warns about — reddening row (c)**, which was B1's whole point. Re-run both
  at L1; this is the one place reproduction is warranted, because it is the finding's closure.
- **Standing rule 2's companion:** does row (c)'s fixture now satisfy exactly one sufficient cause?

### 5.2 The C8 repair, and its three sub-checks

C8 now skips on any `-n`/`--numprocesses` override, then asserts `--dist loadfile`, a **positive
integer** worker count, and `PYTEST_XDIST_WORKER`. Standing rule 11 demands one mutation per
sub-check with which bites on which; fix r5 reports three plus both comparator spellings. Verify
the enumeration is complete against the code's branch points, not against that list — **standing
rule 4 is exactly this trap**, and both S1 and S2 were instances of it.

`-n 8` must now be **green** (S2's repair), and both `-n 0` and `--numprocesses 0` must **skip**
(S1's repair). §8's published comparator row depends on that skip; confirm the `1 skipped` it
publishes is still C8 and still fires under both spellings.

### 5.3 Collateral, and anything seen in passing

The charter's clause four is not decorative: settled areas are not re-verified, but **anything you
see wrong in passing is reported.** It has caught real defects in this project twice.

Cheap and worth a glance: N1's two new endpoint rows are covered by their own mutation; N2's
deletion removed an assertion and not a row (collection is 2599, `+2` over r3, which is the two
endpoint rows exactly); `app/.env.example` matches master plan §6.1's command character for
character.

## 6. Evidence budget

**L4 budget: 0.** `git diff 4b5719d HEAD -- app/` is empty, so fix r5's stamp — runs 2 and 3, at
`4b5719d` clean — is tree-bound to your tree and is **cited, not reproduced**. The published
numbers are `21 failed / 2578 passed` at the shipped default and
`21 failed / 2577 passed / 1 skipped / 1 deselected` under `-n 0`, all `comm`-empty in both
directions against the phase-2 21-ID set. Collection is 2599.

**One exception, and only one:** a repository-wide absence claim, which is L4 by construction.
Write the charter's authorization line **before** the run, stating what narrower evidence could not
answer.

Everything else is L1/L2 — and §5.1's mutations are the point of this round, so spend there. Revert
every mutation, declare every file you touched separately from your own writes, verify restoration
by checksum, and declare every probe database. Destructive verification on disposable databases
only; `beyo_manager` is never a target.

## 7. Out of scope

- **Everything in review r4 §9.** The advisory lock's own design, the five-step guard's nineteen
  boundaries, the N4 removal, the `0.0.0.0` narrowing, the Makefile targets.
- **The architecture graph.** It is at 194/291 with nothing pending; the three settled records were
  repaired by an owner-authorized maintenance session hours ago. **One known defect is already
  being handled and is not yours to report:** the re-recorded summary dropped a still-true clause
  (*a marker-less template with tables is refused outright; a marker-less empty shell is absorbed*
  — `_ensure_template:407-416`), because the coordinator's drafted wording omitted it. Do not write
  to `.archgraph/`.
- **Review r4's N4 and N5** — `app/run_pytest_suite.py` and the perturbation harness's retirement.
  Both are carried to the project's closeout with the owner.
- **The shipped worker count.** OD-10 settled it; six is the owner's decision.

## 8. Closing protocol

Deposit **one handoff** at `handoffs/reviewer/2026-08-22_phase3_rereview_r6_handoff.md` with
charter frontmatter (`plan: 3`, `role: review`, `round: 6`, `verdict`, `date`, `actor`).

Contents, in order:

1. **Verdict** — `APPROVED` or `CHANGES_REQUESTED`.
2. **Owner-readable opening**, 3–5 sentences, no citations and no jargon.
3. **`⚠ OWNER DECISIONS REQUIRED (n)`** in the charter's card format, or one line saying nothing
   needs them.
4. **The verified perimeter as step 1 of your findings** — what `git diff 8501a51 HEAD` shows,
   compared against fix r5's declared perimeter, with anything outside named as a finding.
5. **Each r4 finding — B1, S1–S5, N1, N2 — marked resolved / not resolved / resolved differently**,
   the last with the divergence stated. B1 is the one that diverged.
6. **Your judgment on §5.1**, item by item.
7. **Findings**, blocking / should-fix / note, each with artifact, line, the defect it would let
   through, and the mutation with both sides where you tested it.
8. **Your full write perimeter**, mutation-probe files listed separately with restoration verified,
   probe databases and their disposition, and **your L4 count as a number** (expected: 0).
9. Your final chat message follows the charter's **owner layer**. Not a paste of the handoff.

The handoff file, not your chat message, is what the coordinator consumes.
