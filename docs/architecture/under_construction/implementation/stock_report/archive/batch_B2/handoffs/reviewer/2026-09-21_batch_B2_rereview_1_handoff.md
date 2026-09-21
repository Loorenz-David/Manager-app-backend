---
plan: batch B2 (6, 7)
role: review
round: batch_B2-rereview-1
state: APPROVED
date: 2026-09-21
actor: pipeline-reviewer (Claude Opus 5, skill `plan-reviewer`)
tree: 29b4395
---

# Batch B2 re-review 1 — after fix round 1 (phases 6 and 7, `stock_report`)

**Gate check.** `planning/intention.md` begins `status: RATIFIED — by the owner (David): ratified
2026-09-18, re-ratified 2026-09-18 incl. §14B, and 2026-09-19 incl. round 7 (§14D), round 8 (§14E)
and round 9 (§14F, card 14, P42–P45)` — **PASS**.

**Tree identity.** My `git status --porcelain` is empty; HEAD is `ca7a746`; `git diff
29b4395..ca7a746 -- app/` is **empty** (the two commits after the fix are docs/prompt only), so my
tree is byte-identical to the stamped `29b4395` over all code and tests. Every stamp below that is
cited rather than re-run is therefore tree-matched.

**Evidence consumed by citation, not re-run** (charter "over-evidence is a defect"):
- `git diff ff39a96..29b4395 -- app/beyo_manager/` is **empty** — I re-confirmed it myself; the
  round was tests only.
- **L4 on `29b4395`: 21 failed / 3445 passed / 2 skipped**, failing-ID set identical to the
  published 21-ID baseline **in both directions** (orchestrator's run, 02:58 UTC; implementer's
  independent run agrees). 3445 = 3436 + 9 net new tests. **No L4 run by me**, per prompt.
- L1 control `test_receive_stock_demand_webhook.py` → **23 passed** on `29b4395` (implementer §6).
  Not re-run as a bare control; every run I made carried a mutation.
- Review 1's seven `criteria_normalization.py` closures (`declared 29 = executed 29`). Not re-run
  **as parser-scope runs**; see §3 for why three of them had to be re-sited to the endpoint.

## 1. Verdict

**APPROVED.** Batch B2 closes, and with it batch B. No blocking finding, no should-fix finding,
no production defect. The fix round did exactly what it was scoped to do and nothing else.

| | rows | PASS | FAIL | delta vs review 1 |
|---|---|---|---|---|
| Phase 6 (`plan_6.md`) | 36 | **36** | 0 | unchanged (untouched, not re-verdicted) |
| Phase 7 (`plan_7.md`) | 52 | **52** | 0 | **+8** (C4(a)–(h): FAIL → PASS) |
| **Total** | **88** | **88** | **0** | **80/8 → 88/0** |

Three rows that review 1 passed *with a recorded gap* — C2(a), C2(x), C2(y), whose outcome cells
name persisted state — are now discharged at the scope their cells name. Their verdict does not
move (they were PASS), but finding S1 is closed.

## ⚠ OWNER DECISIONS REQUIRED (1)

One card, **carried verbatim from review 1 and not re-litigated** (the prompt reserves criterion
authorship to you). It does not gate this approval; it is repeated here because batch B is closing
and the card would otherwise sit in a consumed handoff.

**Card 1 — Should three uncovered invariants become criterion rows?**

*Story.* Three guarantees this build relies on have no test that could ever catch them breaking.
Scanner's webhook must never stamp itself as the editor of a stock row — today it correctly leaves
the "last edited by / at" fields empty, but if a later phase starts stamping them, nothing goes
red and your audit trail quietly starts crediting a robot. Two concurrent Scanner deliveries must
take their row locks in the same order or they deadlock; the code sorts correctly, and I measured
that deleting *both* sorting rules leaves every test in the batch green. And the shared webhook
key-check refuses an unconfigured workspace setting; I measured that deleting that refusal also
leaves everything green, because the demand command happens to refuse it a moment later — which
stops being true the day the second Scanner webhook (phase 9) ships without its own check.

*Branches.*
- **Author all three** — three small rows, roughly four tests, spread over phases 7, 9 and a later
  concurrency phase. Each closes a guard that currently cannot fail.
- **Author only the third** (the shared key-check) — cheapest, and it is the one that becomes a real
  hole on a fixed date (phase 9).
- **Author none** — the code stays correct today and the debt is recorded in this handoff.

*Recommendation.* Author all three, because each is the "guard that cannot fail" shape the charter
calls the most expensive family in this project's history, and none of them is expensive to close.

*On silence.* Nothing gates on this: batch B2 is APPROVED without it, and the three items stay in
the carry-forward table below (CF-1, CF-2, CF-3). The gate holds; no row is authored by an agent.

*Trace.* intention §4B MC-17 (demand authorship cells); §4A MC-4 ("sorting the VALUES"); §8B MC-8
step 2 + plan 7 C1(c); carry-forward rows CF-1, CF-2, CF-3.

**Does the ratified intention settle it?** No. The intention states all three invariants (MC-17,
MC-4, MC-8 step 2) but does not oblige any phase to carry a criterion row for them, and only the
owner authors criterion rows. The intention settles *what is true*, not *what is measured*.

## 2. B1 — per-row confirmation of the eight

The requirement (intention §4A MC-3, final bullet): **"proven through the webhook endpoint with
real JSON bytes"**, each of (a)–(e) its own row, each "two rows" case its own row.

All eight live in
`app/tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py`, new
C4 section. Each is a separate test function; each seeds workspace W, configures both settings,
calls `receive_stock_demand_webhook(_ctx(db_session, raw_body=…))` **twice** with two raw bodies
produced by `_body()`/`_one_entry_body()` = `json.dumps(entries).encode("utf-8")` — real bytes
through the command, not pre-built `DemandEntry` objects — then counts live `stock_report_items`
rows for W via `_live_row_count`, then `assert_stock_report_clean`, then purges in `finally`.

| Row | Body 1 → Body 2 | Rows asserted | Real JSON bytes twice? | Live-row count? | Verdict |
|---|---|---|---|---|---|
| C4(a) key order | `{"a":["x"],"b":["y"]}` → `{"b":["y"],"a":["x"]}` | 1 | yes (L341–360) | yes, line 353 | **CONFIRMED** |
| C4(b) list element order | `["teak","dark"]` → `["dark","teak"]` | 1 | yes | yes, line 373 | **CONFIRMED** |
| C4(c) element case/whitespace | `["Teak"]` → `[" teak "]` | 1 | yes | yes, line 393 | **CONFIRMED** |
| C4(d) duplicate elements | `["teak","teak"]` → `["teak"]` | 1 | yes | yes, line 413 | **CONFIRMED** |
| C4(e) bare string vs 1-list | `"teak"` → `["teak"]` | 1 | yes | yes, line 433 | **CONFIRMED** |
| C4(f) key case | `{"Wood_Group":…}` → `{"wood_group":…}` | 2 | yes | yes, line 453 | **CONFIRMED** |
| C4(g) key whitespace | `{" wood_group":…}` → `{"wood_group":…}` | 2 | yes | yes, line 473 | **CONFIRMED** |
| C4(h) not-understood number | `{"n":1}` → `{"n":1.0}` | 2 | yes | yes, line 493 | **CONFIRMED** |

Three structural checks behind the table:
- **Real bytes, not objects.** `_one_entry_body` serialises with `json.dumps(...).encode("utf-8")`
  and the command's own first parsing step is `raw.decode("utf-8")` → `json.loads`. The two-key
  bodies for C4(a) rely on `json.dumps` preserving *insertion* order (it does; `sort_keys` is not
  passed), which is what makes the (a) fixture a genuine key-order difference on the wire.
- **The count is of live rows the flow can produce.** `_live_row_count` selects
  `StockReportItem.workspace_id == W` with **no** `is_deleted` filter, where review 1's suggested
  correction named one. Nothing in this flow soft-deletes, so the omission is strictly *stronger*
  (a spurious soft-deleted row would still be counted and would break the row). Note N-R2.
- **The fixture has one sufficient cause.** In (a)–(e) a miscount of 0 (category unresolved,
  nothing written) fails the row just as a miscount of 2 does, so "1" is not satisfiable by an
  inert path.

**Row-level ruling: B1 is CLOSED.** The invariant is now proven where MC-3 says it must be.

## 3. The arming question — measurement and ruling

**The question.** The implementer ran one arming mutation (`properties_signature=
json.dumps(properties_raw)` at `stock_demand_request.py`'s `DemandEntry` construction) and recorded
honestly that it reddened C4(a)–(e) on their own row-count assertion while C4(f)–(h) failed only at
the later `assert_stock_report_clean` call. Its disposition — "not a gap, because (f)–(h)'s own
named mutations were already run in review 1" — **substitutes one proposition for another**: review
1 ran those three mutations against the *parser* tests in `test_stock_demand_request.py`, which are
different tests. Nobody had shown that the three **endpoint** rows can fail on their own terms.
That is the same conflation review 1 named as lesson L-21, one level up.

**So I ran them.** Five mutations, each applied alone, run whole-file (never `-k`), reverted and
checksum-verified. Each result below is the *first* failing assertion, so no verdict rests on a
short-circuited sub-check (charter rule 12).

| Probe | Mutation | Site | Expected to arm | Measured |
|---|---|---|---|---|
| **P1** | `normalize_stock_criteria` → identity (`return dict(raw)`) | `criteria_normalization.py` | (b)–(e) | **C4(b) L373, (c) L393, (d) L413, (e) L433 all `assert 2 == 1`**; C5(a) also red (its own job); (a) and (f)–(h) green. 5 failed / 18 passed |
| **P2** | keys lower-cased (`key = key.lower()`) | `criteria_normalization.py` | (f) | **C4(f) L453 `assert 1 == 2`** — 1 failed / 22 passed |
| **P3** | keys stripped (`key = key.strip()`) | `criteria_normalization.py` | (g) | **C4(g) L473 `assert 1 == 2`** — 1 failed / 22 passed |
| **P4** | int/float (not bool) coerced to `float` | `criteria_normalization.py` | (h) | **C4(h) L493 `assert 1 == 2`** — 1 failed / 22 passed |
| **P5** | `sort_keys=False` in the signature serializer | `domain/items/properties_signature.py` | (a) | **C4(a) L353 `assert 2 == 1`** — 1 failed / 22 passed |

**Ruling: all eight endpoint rows genuinely discriminate, each on its own row-count assertion, and
each is now armed 1:1 by a measured mutation. No production change is needed; nothing here is a
finding against the fix round's tests.**

Two things the measurement taught that the round did not know:

1. **C4(a)'s arming site is not the normalizer.** P1 (normalization removed entirely) leaves C4(a)
   **green**, because key-order insensitivity comes from `compute_properties_signature`'s
   `sort_keys=True` (`domain/items/properties_signature.py:21`), not from
   `normalize_stock_criteria`. The row is armed — P5 proves it — but at a different site, in a
   file neither plan names. Recorded as note N-R3 so a later phase editing that serializer knows
   plan 7 C4(a) depends on it.
2. **The implementer's mutant was not merely "inert for (f)–(h)": it was the wrong family.** It
   removes normalization, which can only *split* identities, so it can never collapse two already
   distinct ones. The right instruments are the over-normalization mutants P2/P3/P4. Its
   conclusion was right; its *warrant* was not, and the warrant is what a mutation cell asserts.
   Lesson L-23.

## 4. S1 and S2 — confirmations

### S1 — the two write-path integration tests: **CONFIRMED, and armed**

`test_c2a_c2x_malformed_bodies_write_nothing_through_the_command` (L258) and
`test_c2y_extra_key_is_ignored_and_the_entry_is_applied` (L298).

**What they assert vs. what the cells name.**
- **C2(a)** "422; nothing written": raw body `b"\xff\xfe"` → `ValidationError` with
  `http_status == 422`, and `count_writes(statements, WRITE_TABLES) == 0` inside a
  `record_statements(db_session)` window that wraps the call. ✅
- **C2(x)** "422 naming entries 0 and 2, nothing written (entry 1 not applied)": three-entry body,
  entries 0 and 2 defective → 422, message contains `"entry 0"` and `"entry 2"` and **not**
  `"entry 1"`, `count_writes == 0`, **and** `_live_row_count(W) == 0` — the atomic-batch half. ✅
- **C2(y)** "200, `applied`": one entry carrying an extra `"location"` key → `response["results"][0]
  ["outcome"] == "applied"` and the created row's `quantity_requested == 3` read back with
  `scalar_one()` (which itself fails on 0 or 2 rows). ✅ The literal "200" is the router's status,
  which plan 7 C5(c) pins separately; at command scope the returned body is the right observable,
  consistent with how review 1 passed the other C5 rows.

**The instrument is real, not decorative.** `WRITE_TABLES` is restated in this file **byte-identical
to `test_apply_stock_demand.py`'s approved set**, and all four names are the real
`__tablename__`s (`stock_report_items`, `stock_task_assignments`, `stock_report_history_records`,
`tasks`) — I checked the models, not the prose. `count_writes` matches `tables` as substrings of
`INSERT/UPDATE/DELETE` text, so `"tasks"` over-matches (`task_items`, `task_steps`) — over-broad,
never under-broad, so `== 0` stays conservative.

**Arming, measured** (this matters: across the whole repository `count_writes` is asserted `== 0`
at every one of its twelve call sites and has *never* been observed positive — an absence
instrument nobody had ever seen fire):

| Probe | Mutation | Measured |
|---|---|---|
| **P6** | apply-then-reject: catch the parse error, apply a valid entry, re-raise (`receive_stock_demand_webhook.py`) | **C2(a) L270 `assert 3 == 0`** — the instrument observes three writes. 1 failed / 22 passed |
| **P7** | same, gated to UTF-8-decodable bodies so C2(a) stays green and C2(x)'s block executes | **C2(x) L289 `assert 3 == 0`** — 1 failed / 22 passed |
| **P8** | parser rejects unknown entry keys (`stock_demand_request.py`) | **C2(y) red** (`entry 0: unknown key`) — 1 failed / 22 passed |

P6/P7 plant exactly the defect M3 forbids — a rejected batch that leaves a trace — and both halves
of the combined test bite on their **own** sub-check, so the C2(a)/C2(x) merge into one function
costs nothing (charter rule 12 satisfied by construction, not by assertion order luck).

### S2 — the orphan: **CONFIRMED closed**

`test_raises_unauthorized_when_key_is_missing_or_wrong` is **deleted** from
`app/tests/unit/services/infra/test_location_tracker_webhook_verifier.py` (file now 1 test,
`1 passed`). The reason is recorded in the file's docstring and in plan 7's Review log. Nothing
lost coverage: the deleted test's two cases are plan 7 **C1(d)** (`test_c1d_missing_header_is_401`)
and **C1(e)** (`test_c1e_wrong_header_is_401`), both present and both PASS in review 1 at the wider
command scope. The surviving sibling
`test_returns_the_configured_workspace_id_on_success` is declared as candidate criterion **CF-4**
in plan 7's Review log, with the defect it catches and why C6(a) only proves it indirectly — the
declaration link-3 requires. The now-unused `LocationTrackerWebhookAuthError` import was removed
with it; `import pytest` correctly stays (`pytestmark`).

### Trace check on the nine net new tests

Every one maps to a criterion row: 8 → C4(a)–(h); 1 → C2(a)+C2(x); 1 → C2(y). **No orphan
introduced.** The C4 and C2 rows now each carry two tests (parser + endpoint); that is not
over-authorship — review 1's correction and the fix prompt both directed keeping the parser tests,
and they localise a mutation to the normalizer where the endpoint test localises it to the row
count.

## 5. Rows pulled in under the widening

No production code changed, so §3A's shared-foundation clause is not triggered. I checked the one
thing the prompt named — whether nine new tests in the same file perturb an instrument a row-1
verdict rested on — and pulled in **no row**.

- **`count_writes` / statement budget.** The four statement-budget rows (plan 6 C6(a)–(d)) and the
  bound-parameter row (C7(a)) live in `test_apply_stock_demand.py` / `_timing.py`, untouched files.
  Inside the changed file, `record_statements` is entered and exited per assertion block, and
  `event.remove` runs in its `finally`, so no listener outlives a test.
- **Event lists.** The new C4/C2(y) tests dispatch real events (they create rows), but none uses
  `capture_dispatch`; C6(a), the one row in this file that asserts a dispatched event, captures
  within its own scope and is green in all five of my runs.
- **Shared state.** Each new test seeds its own `ws_sr_*` workspace and purges it in `finally`;
  every assertion in them is workspace-scoped; `assert_stock_report_clean` runs before teardown.
  Across five mutated whole-file runs the only failures were the intended ones — strong negative
  evidence for cross-test coupling.
- **Counts reconcile**: file 13 → 23, verifier 2 → 1, L2 334 → 343, L4 3436 → 3445. Four
  independent arithmetic checks, all consistent with +10/−1.

## 6. Findings

### BLOCKING — none.

### SHOULD-FIX — none.

Review 1's **B1**, **S1** and **S2** are all closed, verified by measurement above.

### NOTES (backlog, this round)

- **N-R1 — the arming run used `-k`.** The fix handoff's §2 arming run was
  `pytest … -q -k "test_c4"`, against the owner's standing rule "run the whole test file, never
  `-k`" (memory rule, named-mutation both-sides). No harm here — the final L1 stamps are whole-file
  — but the `-k` run is the one whose output drove the "(f)–(h) not a gap" reasoning, and a
  whole-file run would have shown the same. Process note.
- **N-R2 — `_live_row_count` omits `is_deleted == False`** where review 1's suggested correction
  named it. Strictly stronger for this flow (nothing soft-deletes here), but a later phase that
  adds soft-delete to the demand path must revisit these eight rows or they will start counting
  tombstones. Destination: phase 13A.
- **N-R3 — plan 7 C4(a) is armed outside both plans' file lists.** Its only arming site is
  `sort_keys=True` in `app/beyo_manager/domain/items/properties_signature.py:21` (measured, P5);
  `criteria_normalization.py` does not touch key order. A phase editing that serializer changes the
  meaning of a batch-B criterion row. Destination: master plan §9 note.
- **N-R4 — `count_writes` is asserted `== 0` at all twelve of its call sites repo-wide** and, until
  P6/P7, had never been observed positive. It is now measured capable of firing on this path
  (3 writes seen). Recording the measurement so the next absence row on this instrument need not
  re-derive it. Destination: master plan §9 note.
- **N-R5 — a small record inconsistency.** Plan 7's Review log says the L4 was taken "on tree
  `2542a58` + this round's dirty diff"; the fix handoff §6 says `29b4395`, clean. They describe the
  same tree and the orchestrator's independent run agrees, so nothing is in doubt — but the
  charter's identity rule wants the SHA of the tree actually measured. Note only.

Review 1's notes **N1–N10** are unchanged and unre-litigated; none was in this round's perimeter.

### Carry-forward dispositions

| id | Item | Destination |
|---|---|---|
| CF-1 | MC-17's two demand-authorship cells have no row (review 1 N4) | candidate criterion → phase 8; **owner card 1** |
| CF-2 | MC-4's sorted-VALUES / `ORDER BY` lock order has no test that can fail (N5) | candidate criterion → phase 13A; **owner card 1** |
| CF-3 | The shared verifier's workspace-setting guard is an equivalent mutant today and stops being one at phase 9 (N1) | phase 9 (`items processed` webhook); **owner card 1** |
| CF-4 | `test_returns_the_configured_workspace_id_on_success` declared as a candidate criterion | coordinator: fold into a plan 7 row or refuse with a recorded reason — **now due, batch B is closing** |
| CF-5 | C6 / C7(a) are implementation-coupled by design and will redden on a statement-plan refactor (N7) | master plan §9 note (review 1 §8 item 3) |
| CF-6 | `app/tests/helpers/test_settings.py` is a test-named helper module (N-R9, inherited) | unchanged; outside any batch-B perimeter |
| CF-7 | N-R2 (`is_deleted` filter), N-R3 (C4(a)'s arming site), N-R4 (`count_writes` measured positive) | phase 13A / master plan §9 |
| CF-8 | Review 1 §8 amendments (plan 6 §5 task 2 step 1; master plan §6.5 `record_statement_calls`; §9 statement budget) | **owner**, still unapplied — a task cell is not a fold |

## 7. What I ran, and the mutation-probe declaration

**Commands** (all from `app/`, all **L1 whole-file, never `-k`**, one mutation live at a time):

```
PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py -q
```

Eight probe runs (P1 twice — once for pass/fail, once with `--tb=line` to identify the failing
assertion; P7 twice — the first attempt's re-raise was itself wrong and was corrected before the
measurement was taken). **No bare control run** (the tree-matched 23-passed stamp is cited
instead), **no L2**, **no L3**, **no L4**.

**Mutation-probe declaration.** Every probe was applied alone, run, and reverted with
`git checkout --` before the next. sha256 captured before the session and re-captured after the
final revert — **all four identical**, and `git status --porcelain` is **empty** at close:

| File | sha256 before **and** after | Probes | In batch perimeter? |
|---|---|---|---|
| `app/beyo_manager/domain/stock_report/criteria_normalization.py` | `5be822d6b3c90fd4b993866a066ca6061a40e833502116a1ef98e66bcabd3791` | P1, P2, P3, P4 | no — **phase 1, APPROVED** |
| `app/beyo_manager/domain/items/properties_signature.py` | `19494c504edde75c77ee516ccacc678f8decf3fcbbb0d31df979eac0994777a7` | P5 | no — **pre-existing items domain** |
| `app/beyo_manager/services/commands/stock_report/receive_stock_demand_webhook.py` | `a151ad89d0577488dd0089dc3dacd30e1b3aaff1d3b393b2d7bdfb1f1df6d487` | P6, P7 | yes (phase 7) |
| `app/beyo_manager/services/commands/stock_report/stock_demand_request.py` | `d8578ce3826a5e66d27b8dada075f26b481163941567e3146132be5b122c5d84` | P8 | yes (phase 7) |

The last two checksums match the values review 1 recorded for the same files, and the first matches
review 1's recorded value for `criteria_normalization.py` — three independent confirmations that
neither the fix round nor either review left a residue in production code.

**No test file, plan, prompt or other handoff was modified by a probe.** **Database/state side
effects:** none persisted — every test exercised carries
`finally: purge_stock_report_workspace + commit`, all runs ended green-or-expected-red with
teardown executing, and the xdist worker databases are dropped by `tests/database_isolation.py`.
The dev database (`beyo_manager`) was never a target.

**My full write perimeter for this session:** this handoff file; one appended Review-log entry in
`plans/plan_6.md` §8 and one in `plans/plan_7.md` §8. Nothing else. **No commit, no tracker row**
(the batch row is the orchestrator's), **no archgraph write**, no master-plan edit, no intention
edit, no change to `docs/archgraph-anchor-observations.md`, no touch of the Scanner repository.

## 8. Lessons for the plans

- **L-23 — "the same mutation already ran against a different test" never discharges a new row's
  arming.** This is L-21 one level up, and it recurred inside the round that L-21 was written for.
  Review 1 ran the lower-keys / strip-keys / normalize-numbers mutants against the *parser* tests;
  the fix round cited those runs to explain why the *endpoint* tests need not be armed. The
  propositions differ, and the correct instruments (P2–P4 here) cost four minutes. **Rule for the
  plans: when a row's test moves or is duplicated to a new surface, its named mutations are re-run
  at the new surface — a mutation ledger is scoped to a test id, never to a mutant.**
- **L-24 — a mutation that can only split identities cannot arm a "two rows" row.** The batch's
  identity rows come in two directions (collapse-to-one, stay-at-two), and they need mutants of
  opposite sign: under-normalization arms (a)–(e), over-normalization arms (f)–(h). A single shared
  arming mutation for a bidirectional invariant is a category error, not a shortfall. **Where a
  criterion family asserts both directions of an equivalence, the plan names one mutation per
  direction.**
- **L-25 — name the arming site, not the arming file.** Plan 7 C4(a) is armed only by
  `sort_keys=True` in `domain/items/properties_signature.py`, a file neither plan lists; every
  mutation cell in the family pointed at `criteria_normalization.py`, where C4(a) is provably inert
  (measured, P1). Charter rule 11's "a named mutation names where it is applied" needs its other
  half: **the plan verifies that the named site is the one the row actually depends on.**
- **L-26 — an absence instrument deserves one positive observation per project.** `count_writes` is
  used twelve times in this repository and asserted `== 0` every time; no test had ever shown it
  returning non-zero. It does (P6/P7, three writes seen). Cheap to establish once, and it converts
  a family of rows from "assumed armed" to "measured armed".

## 9. Review log entries appended

`plans/plan_6.md` §8 and `plans/plan_7.md` §8 each carry one appended entry, layer 1 only.
