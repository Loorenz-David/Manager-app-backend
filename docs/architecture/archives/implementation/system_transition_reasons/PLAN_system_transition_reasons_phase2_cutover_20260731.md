# PLAN_system_transition_reasons_phase2_cutover_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase2_cutover_20260731`
- Status: `archived`
- Owner agent: `claude-opus-5` (implementer)
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T17:40:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: every writer stops resolving system reasons from the catalog. Clock-out, both task-switch
  sites, the derivation rebuild, and the serializer all move to `transition_reason`.
- Business/user intent: **this phase ends the outage.** In the 3131 workspaces with no
  `pause_ended_shift` row, clock-out with an open WORKING step currently fails, and starting a task
  while another is active fails too. After this phase both succeed — **without any backfill**,
  because new rows do not need the row that is missing.
- Non-goals: historical data (phase 3); the catalog itself (phase 4); `manually_recorded` and the
  `changed_by_id` heuristic (T7 — deferred; touching either is a scope violation).

## Scope

- In scope: `services/commands/users/_clock_worker_shift.py` (~line 200);
  `services/commands/task_steps/transition_step_state.py` (~line 274) and
  `_step_transition_core.py` (~line 114); the rebuild
  (`_reconstruct_shift_middle.py`, `reconcile_worker_shift_state.py`, `heal_open_shifts_today.py`);
  `domain/users/serializers.py`.
- Out of scope: the command wrappers, routes, and analytics composers — the Connecteam handler and
  the midnight safeguard call `clock_out_shift_for_user` **directly** and must inherit this change
  by design. Verify they do; do not special-case them. Every `docs/handoff/to_frontend/` file is
  operator-owned: **propose, never edit**.
- Assumptions: phase 1 archived. Readers already tolerate `transition_reason`.

## What phase 1 established (do not re-decide)

- **No `WORKER_PAUSED` member.** `transition_reason` means "a system transition happened, and which
  one". A worker-chosen pause is identified by its catalog reference alone, and leaves
  `transition_reason` null.
- **The vocabulary lives in `domain/transitions/`** — `enums.py` holds the enum only (it is the
  models-importable surface); `labels.py` holds the label map and is imported by read paths only.
- **The read-path audit (R1–R24) is in the master plan's "Phase 1 inventory".** It is **this phase's
  checklist too** — every path you change must already be on it, and if you find yourself editing a
  path that is not, stop and ask why the audit missed it.
- **R23/R24 (`domain/analytics/linear_timeline.py:220,264`) are yours.** Phase 1 classified them as
  emitting opaque keys with no resolution and listed them precisely because this phase rewrites
  both.
- **Mutual exclusion has one documented exception.** `transition_reason` non-null ⟺
  `pause_reason_id` null holds for `step_state_records`. It does **not** hold for the derived
  declared-state row, which carries `WORKER_DECLARED_STATE` *and* its catalog reference by design
  (criterion 6 below). Phase 4's check constraint depends on this being stated, so do not
  "correct" it.

## The failure shape this phase must avoid

Phase 1's single blocking finding was a guard that looked incidental and was load-bearing: a
truthiness check on a serialized object (`details[0]["pause_reason"]`) that was in fact a
**workspace-resolution check**. Removing it leaked another workspace's id into a workspace-scoped
response.

**This phase rewrites the very paths that guard lived in.** Before changing any conditional in the
timeline or breakdown modules, ask what it is *actually* testing — not what it appears to test. A
`None` check standing in for a resolution check, or a fallback chain whose first element can now be
non-null where it previously could not, is the same bug.

The fix that phase 1 landed is the pattern to follow: make the guard **structural** — pass the
resolved set as a required argument so a caller cannot obtain a key without proving resolution —
rather than relying on a side-effect being falsy.

## Clarifications required

All three resolved before implementation began; rulings and reasoning in the Review log.

- [x] **Q4** — `auto_pause_description`. **Confirmed unchanged** (implementer, per "confirm or
      escalate"): it names *which item* took priority, a per-instance fact that typing the
      transition does not make redundant.
- [x] **Does `UserShiftStateRecord.reason` keep holding the catalog id for worker-chosen pauses**, or
      does the derived row gain its own `pause_reason_id` column? **Operator ruling: keep `reason`;
      no migration in this phase.** Consequence for criterion 11 recorded in the Review log.
- [x] **Does the API surface `transition_reason` to clients?** **Operator ruling: no — the invisible
      option.** The type is resolved server-side into the existing response shape; no handoff change.

## Acceptance criteria

### The outage fix

1. **Zero-catalog clock-out**: a workspace with **no `pause_reasons` rows at all**, a worker clocked
   in with an open WORKING step, clock-out succeeds, the step closes, and the record carries
   `transition_reason = SHIFT_ENDED` with `pause_reason_id = NULL`. **Must fail against pre-phase
   code** — verify that it does.
2. **Zero-catalog task switch**: same workspace, a worker starts a task while another is active, the
   conflicting step auto-pauses with `OTHER_TASK_PRIORITY` and `pause_reason_id = NULL`. Must fail
   against pre-phase code.
3. **Both task-switch sites changed.** `transition_step_state.py` and `_step_transition_core.py` are
   separate paths reached by different endpoints (single vs. batch). **A test per path.** One test
   hitting one path is the likely failure mode of this phase.
4. `get_system_pause_reason_id` has **zero runtime callers** — confirm by grep across `app/`
   excluding tests. The function is deleted in phase 4, not here; zero callers is this phase's proof
   of completion.
5. **The midnight safeguard and Connecteam inherit the fix**, tested explicitly. They are the paths
   most likely to run in a workspace nobody has curated.

### Derivation

6. Derived rows from the rebuild carry `transition_reason` reflecting their source: clock-out →
   `SHIFT_ENDED`; auto-pause → `OTHER_TASK_PRIORITY`; declaration → `WORKER_DECLARED_STATE`.
7. **The rebuild remains idempotent** — running it twice over the same source data produces
   identical derived rows. declared_worker_states Phase 2 burned four fix cycles here; treat this as
   the central invariant, not a nice-to-have.
8. **Declarations survive the rebuild.** The architectural spine of declared_worker_states is that
   declarations are a *source* table the rebuild cannot erase. Declare a state, clock out, assert it
   is represented in the derived timeline.
9. Ownership priority preserved: where a step-sourced segment and a declaration overlap, the same
   one wins as before. Assert against existing expected behaviour, not a fresh derivation of it.
10. The rebuild does not launder `changed_by_id`. It did once (H1), and `heal_open_shifts_today.py`
    then reopened the laundered row. Assert the original actor survives end-to-end.

### Serializer

11. The `startswith(f"{PauseReason.CLIENT_ID_PREFIX}_")` branch in `domain/users/serializers.py` is
    gone, or provably dead with a test showing no input reaches it (master-plan success criterion 4
    accepts either).
12. The published three-way `reason_text` contract — absent / string / null — behaves exactly as
    handoff §5.3 documents, for four cases: a system transition, a worker-chosen catalog pause, a
    declared state, and a legacy free-text row. Four cases, four tests, asserted against the handoff
    text.
13. **No published contract changes without an operator-approved handoff update.** If this phase
    concludes one is needed, write the proposal in the Review log and STOP. Do not edit the handoff,
    do not flip a liveness row.
14. The kiosk clock-out analytics contract is unaffected, or the effect is in the proposal. Re-run
    phase 1's compatibility tests.

### Whole-phase

15. Pre-phase rows still resolve to their existing labels via phase 1's fallback — prove with seeded
    rows of each legacy shape.
16. Existing behaviour otherwise identical: same steps transition, same timestamps, same
    `transitioned_steps` counts, same partial-unique-index invariants, same response shapes.
17. `_step_transition_core.py` has a documented pre-existing `NameError` (missing `select` import)
    on the auto-pause path. **Determine whether it is still present.** If so it is baseline debt
    (T8) — record it, do not fix it, and note that any test claiming to exercise that path before
    the fix was not actually reaching it.
18. The two clock-out tests in the recorded baseline failure set: state whether this phase fixes
    either. If one failed *because* of the missing catalog row, it should now pass — that is
    evidence, and it belongs in the Review log.
19. D3 and D5 amendments recorded in **this feature set's** master plan and in this Review log. The
    declared_worker_states plan is **archived and must not be edited**.

### Domain documentation — a deliverable, not a footnote

20. **`docs/domains/worker_shifts/` is updated in this change**, per the rule in its own README and
    in `docs/README.md`: any change altering a domain's logic updates that domain's docs in the same
    change. This phase alters three documented things, so the update is not optional:
    - **`states.md`** — what a transition records now. Its "Two derivations" and "The rebuild"
      sections describe what the rebuild carries; if `transition_reason` is now what identifies a
      segment's origin, that is a change to the documented machine.
    - **`README.md`** — the `UserShiftStateRecord.reason` entry currently carries an explicit
      warning that the field is overloaded and readers distinguish meanings by inspecting the id
      prefix. If this phase removes that prefix check, **the warning becomes false** and must go or
      be rewritten.
    - **`api.md`** — only if a request or response shape changes. If the third clarification
      resolves to the invisible option, this file may need no edit; say so explicitly rather than
      leaving it ambiguous.

    Constraints on the edit: domain docs describe **what is true now**. No references to this plan,
    to phases, to migrations, or to how the system used to behave. If you find yourself writing
    "previously" or "as of phase 2", you are writing history in a living document.

    Nothing about the *pending* phases 3 and 4 may appear there either — those describe a system
    that does not exist yet. Document only what ships in this change.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: command conventions.
- `backend/architecture/01_architecture.md`: layering.
- `backend/architecture/46_serialization.md`: output shapes.
- `backend/architecture/17_logging.md`: if any log line changes.

### File read intent — pattern vs. relational

- Permitted (relational): the five modules being changed; the Connecteam handler and
  `auto_clock_out_open_shifts.py` to confirm how they call in; `step_state_record.py` and
  `user_shift_state_record.py` for exact fields; handoff §5.1/§5.3 for the contract being preserved;
  the archived declared_worker_states Phase 2 Review log for why the provenance machinery exists.
- Prohibited (pattern): reading another command for flush/error-raising shape (`06_commands.md`),
  another serializer for output style (`46_serialization.md`).

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Escalate all three clarifications; wait for rulings before writing code they affect.
2. Clock-out first (criterion 1) — the highest-value change. Then both task-switch sites (2, 3).
3. Verify zero runtime callers of `get_system_pause_reason_id`.
4. Test Connecteam and the midnight safeguard explicitly.
5. Derivation: carry `transition_reason` through the rebuild; idempotence and declaration-survival
   tests; assert `changed_by_id` survives.
6. Serializer: remove the prefix branch; four contract-conformance tests.
7. Legacy-row resolution tests; the `NameError` check; the baseline-failure re-check.
8. Record the D3/D5 amendments. Review log entry. STOP for independent review.

## Risks and mitigations

- Risk: the change lands at the wrong level — in a wrapper rather than in `clock_out_shift_for_user`
  — leaving Connecteam and the midnight safeguard broken. This is exactly the shape of
  declared_worker_states Phase 7's F1: a fix applied one layer off, invisible to the tests written
  for it.
  Mitigation: criteria 5 and the zero-catalog tests exercise the real paths.
- Risk: only one of the two task-switch sites is changed.
  Mitigation: criteria 3 and 4 — a test per path plus a zero-caller grep.
- Risk: the rebuild erases declarations or changes ownership priority (F1/F2).
  Mitigation: criteria 8 and 9 assert against existing expected behaviour.
- Risk: a silent breaking change ships to a frontend already built against the contract. This
  happened once here — `pause_by_reason` keys went opaque with no lookup map, caught only in
  post-archive review.
  Mitigation: criteria 12, 13, 14 — assert against handoff text, propose rather than edit.
- Risk: the zero-catalog tests pass vacuously because a fixture seeds reasons anyway.
  Mitigation: criteria 1 and 2 require them to fail against pre-phase code.

## Validation plan

- Zero-catalog clock-out and task-switch tests: pass now, fail on pre-phase code.
- One test per task-switch path; `get_system_pause_reason_id` grep returns definition only.
- Connecteam + midnight-safeguard tests pass.
- Rebuild-twice idempotence: identical derived rows. Declaration survives clock-out.
- Four serializer contract-conformance tests against handoff §5.3.
- Legacy seeded rows resolve identically to pre-phase output.
- Full suite: no new failure nodes vs. baseline (**node sets**, not counts; baseline worktree needs
  `app/.env.testing` copied in). Note any baseline failure this phase legitimately fixes.
- `ruff check` clean on touched files.

## Review log

- `2026-07-31` `implementer`: **Phase 2 implemented; STOPPED for independent review.** No summary,
  no archive, no phase-table flip, no handoff edit.

  ### Clarifications — all three answered before any code was written

  **Q4 — `auto_pause_description`.** Provisional ruling **confirmed**, not escalated: the plan
  permits "confirm or escalate", and `f"started working with {identifier}"` names *which item* took
  priority. That is a per-instance fact; typing the transition records *that* a switch happened, not
  *what to*. It stays on `StepStateRecord.description`, untouched.

  **Q — derived row's catalog reference (operator decision).** Ruled: **keep `reason`; no
  migration.** New derived rows: worker-chosen pause → `reason = par_…`, `transition_reason = NULL`;
  system auto-pause → `reason = NULL`, `transition_reason = other_task_priority`; declaration →
  both. Consequence accepted and recorded under criterion 11 below.

  **Q — API surface (operator decision).** Ruled: **invisible; resolve server-side.** No response
  shape changes, no handoff proposal needed, criterion 13 satisfied without a STOP.

  **Q (raised by the implementer, not in the plan) — criterion 3 vs criterion 17.** Criterion 3
  demands a test per task-switch path; criterion 17 says record the `_step_transition_core.py`
  `NameError` and do not fix it. Verified the `NameError` is still present (`select` used at
  line 88, never imported), and verified by execution that it fires *before* the catalog lookup —
  so no test could ever have reached that branch. Escalated; **operator ruled: add the one-line
  import**, so criterion 3's test genuinely executes the path rather than asserting about it. See
  criterion 17.

  ### Guard-shape sweep

  Every conditional touched, and what it is actually testing:

  1. **`linear_timeline._sweep`, `owner.interval.reason or UNSPECIFIED_REASON`** — *this is the
     phase-1 failure shape, in its mirror image.* It reads as a null check; it is really "this
     pause explains nothing". Before this phase, `reason is None` on a step pause genuinely meant
     unattributed. After it, `reason is None` is the *normal* state of a system transition. Left
     alone, every auto-pause and every ended-shift segment would have silently bucketed as
     `unspecified` — R14's flagged risk, arriving through a line phase 1 classified as needing no
     change. Rewritten so `UNSPECIFIED_REASON` is reachable only when **both** channels are absent.
     Mutation-proved: restoring the naive form kills
     `test_rebuild_carries_the_transition_reason_onto_derived_rows`.
  2. **`compute_linear_segments` merge predicate** — `prev["reason"] == seg.reason` is an identity
     check, not a null check. Two adjacent pauses can now both carry `reason is None` and be
     different transitions, so `transition_reason` was added to the merge key or they would fuse
     into one run.
  3. **`reconcile_worker_shift_state`, `elif target is IN_PAUSE and open_paused[0].pause_reason_id
     is not None`** — the `is not None` conjunct was a pure null guard (the body only assigned
     `reason = open_paused[0].pause_reason_id`), but leaving it would have discarded the transition
     for exactly the rows that now depend on it. Dropped. **Not asserted as equivalent in a
     comment — proved by test:** `test_reconcile_pause_without_any_reason_leaves_both_fields_null`
     is the control (reasonless pause still projects both fields null, as before) and
     `test_reconcile_projects_a_system_auto_pause_by_its_transition_reason` is the case the guard
     would have broken.
  4. **`reconcile` no-op comparison** — added `current.transition_reason == transition_reason`.
     Deliberate strengthening: a row differing only in its transition is no longer treated as
     unchanged.
  5. **Structural fix, per phase 1's pattern.** `LinearInterval` / `_RawSegment` / `LinearSegment`
     carry `reason` and `transition_reason` as **separate fields** end to end, rather than one
     collapsed key. The rebuild writes them to different columns, and a collapsed key would force
     it to recover which kind of value it held by inspecting the string — reintroducing exactly the
     prefix-sniffing this feature set exists to delete. The separation makes that impossible rather
     than merely discouraged.
  6. **`domain/users/serializers.py` — not touched.** Its `startswith("par_")` branch and
     `pause_reason_reference_is_unresolved` are unchanged; see criterion 11.

  ### Acceptance criteria — evidence

  | # | Status | Evidence |
  |---|---|---|
  | 1 | ✅ | `test_zero_catalog_clock_out_closes_open_working_step`. **Verified failing pre-phase**, not assumed: reverting the call site reproduces `NotFound: System pause reason 'pause_ended_shift' is not configured.` |
  | 2 | ✅ | `test_zero_catalog_task_switch_via_single_step_endpoint`. **Verified failing pre-phase** with the `pause_other_task_priority` `NotFound`. |
  | 3 | ✅ | One test per path: `..._via_single_step_endpoint` and `..._via_shared_transition_core`. The core test **verified failing pre-phase** — with `NameError: name 'select' is not defined` at line 95, i.e. *before* the catalog lookup. |
  | 4 | ✅ | `grep -rn "get_system_pause_reason_id" app/beyo_manager` → the definition line only. |
  | 5 | ✅ | Connecteam: `tests/connecteam/test_clock_actions_integration.py` — the resolver patch was **deleted**, and it now asserts `transition_reason == shift_ended` / `pause_reason_id is None` on the real webhook path. Overnight safeguard: `test_overnight_safeguard_inherits_the_typed_clock_out` plus the pre-existing `test_midnight_safeguard_*` nodes, green. |
  | 6 | ✅ | `test_rebuild_carries_the_transition_reason_onto_derived_rows`; declaration case in criterion 8's test. |
  | 7 | ✅ | `test_rebuild_is_idempotent_over_the_same_source_data` — runs the rebuild twice and compares `(state, entered_at, exited_at, reason, transition_reason, changed_by_id, manually_recorded)` tuples. The rebuild re-reads its own derived rows, so `transition_reason` is selected in the manual-row query too; omitting it would make run 2 differ from run 1. |
  | 8 | ✅ | `test_declaration_survives_the_clock_out_rebuild` — declare, clock out, assert the source row is untouched *and* represented in the rebuilt timeline. |
  | 9 | ✅ | `test_declaration_still_outranks_an_overlapping_step_pause` — priority unchanged; asserted against the existing rule, not re-derived. |
  | 10 | ✅ | `test_rebuild_does_not_launder_changed_by_id`. |
  | 11 | ⚠️ **not met — recorded, not hidden** | The `startswith(CLIENT_ID_PREFIX)` branch is **neither gone nor dead**: it is provably *alive*. Under the operator's "keep `reason`" ruling, that field still holds `par_…` ids and legacy strings on pre-cutover rows (98 and 272 respectively per the phase 1 inventory), and this phase backfills nothing. The branch is what distinguishes a dangling catalog id (→ `reason_text: null`) from displayable text (→ `reason_text: "<raw>"`), and both inputs still exist. **This criterion is discharged by phase 3's backfill**, after which no non-`par_`-shaped legacy value remains and the branch can be shown dead. Master-plan success criterion 4 is a feature-set criterion and is unaffected. Flagged for the reviewer as a deliberate non-completion, not an oversight. |
  | 12 | ✅ | `tests/unit/domain/transitions/test_reason_text_contract_conformance.py` — four cases (system transition / worker-chosen catalog pause / declared state / legacy free text), each quoting the §5.3 and §4 arm it lands on, plus the `null` arm for completeness. |
  | 13 | ✅ | No published contract changed. The invisible option means a transition-typed row serialises into the existing `pause_reason` object shape with the transition value as `id`. No handoff file edited. |
  | 14 | ✅ | Phase 1's kiosk compatibility tests re-run green, including `test_clock_out_analytics_resolves_transition_and_unspecified_keys` and `test_pause_reasons_resolves_every_timeline_key_including_unspecified`. |
  | 15 | ✅ | `test_legacy_slug_shaped_reasons_still_render_as_text` (parametrized over the real measured distinct set) and `test_legacy_catalog_id_that_still_resolves_renders_the_catalog_object`. |
  | 16 | ✅ | Full-suite node set unchanged (below). `transitioned_steps` counts, timestamps and response shapes asserted in the pre-existing worker-shift suite, 42/42 green. |
  | 17 | ✅ (with the operator's ruling) | **The `NameError` was still present** — confirmed by AST check and by execution. Under the ruling above, `from sqlalchemy import select` was added. Recorded plainly: this is baseline debt repaired **solely** because criterion 3 is otherwise unmeetable, not absorbed scope. **And criterion 17's own warning is now proved rather than suspected:** the pre-phase branch raised `NameError` at line 95 before ever reaching the catalog lookup at line 117, so no test that claimed to cover that auto-pause path was reaching it. The branch is also unreachable in production — `transition_step_state_batch` rejects non-batch-capable steps up front, which is why the defect survived. |
  | 18 | ✅ | **This phase fixes one, and the "two" no longer both reproduce.** With clock-out reverted to pre-phase code, `test_worker_shift_commands.py` fails exactly one node — `test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`, through `NotFound: System pause reason 'pause_ended_shift' is not configured` — and with the phase applied all 42 pass. The declared_worker_states baseline note recorded *two* clock-out failures in this file; only one reproduces in this tree, so that note is now stale. Neither appears in the current failure node set. |
  | 19 | ✅ | D3 and D5 amended in **this** feature set's master plan ("Amendments to declared_worker_states decisions"), with the reasoning. The archived declared_worker_states plan was **not** opened for writing. |
  | 20 | ✅ | `docs/domains/worker_shifts/` — all three files. Detail below. |

  ### Domain documentation

  - **`README.md`** — `transition_reason` added to the `UserShiftStateRecord` table; a short "two
    explanation channels" block; a new "Transitions" row in the cross-domain table. **The
    overloaded-`reason` warning was kept, because it is still true** — the operator's ruling leaves
    `reason` holding catalog ids *and* legacy strings, and readers still inspect the prefix. It was
    rewritten to say what is now precise: `reason` is overloaded, `transition_reason` is not.
  - **`states.md`** — new "Why a segment is paused" section (the two channels, the three vocabulary
    members, the mutual exclusion and its one deliberate exception, and the resolution order); "The
    rebuild" now states what a rebuilt segment carries and that provenance survives.
  - **`api.md`** — **did need an edit, contrary to the plan's "may need none".** Two documented
    behaviours moved: `GET /current` now returns a reason object for a system pause as well as a
    catalog one, and the `analytics.pause_by_reason` key space is no longer "pause-reason id plus
    `unspecified`". Both corrected.
  - Checked for banned content: no "previously", no "as of phase 2", no plan/migration references,
    nothing about phases 3–4.

  ### Validation

  - **Full suite, node sets, run-2 vs run-2:** `26 failed / 1387 passed`, and the run-1 and run-2
    node sets are **identical** (`diff` empty) — this tree does not exhibit the second-run drift the
    baseline warns about, because the two `pause_reasons` seeding nodes that used to drift now fail
    on the first run too. **New failure nodes vs. phase 1's recorded set: zero.** Every one of the
    26 is pre-existing debt (shopify, auth, items/upholstery routers, audit, working sections,
    bootstrap, pause-reason seeding). **Zero worker-shift or clock-out nodes appear in the set at
    all.**
  - **Mutation checks (anti-vacuity).** Restoring the naive `reason or UNSPECIFIED_REASON` fallback
    kills `test_rebuild_carries_the_transition_reason_onto_derived_rows`; setting the declaration's
    `transition_reason` to `None` kills both declaration tests. The new branches are genuinely
    exercised.
  - **`ruff check` clean** on every touched file except `transition_step_state.py`, which carries
    **the same 5 pre-existing errors as before this phase** — all `F401` on imports serving a
    commented-out scheduler block, none related to this change, none introduced by it. Verified
    those five names appear nowhere in live code. Baseline debt, T8, not repaired.

  ### Scope notes for the reviewer

  - **`heal_open_shifts_today.py` needed no edit.** It calls `reconstruct_shift_middle` directly and
    inherits the change, which is the same inheritance property criterion 5 relies on for Connecteam
    and the overnight safeguard. Verified by reading, not assumed.
  - **Flagged, deliberately not changed: `app/scripts/backfill/backfill_worker_shift_state_records.py`.**
    It builds `LinearInterval`s without `transition_reason`, so if it were re-run it would write
    derived rows that lose a system transition's label — the same R14 mechanism, in a module this
    phase's scope list does not name. It is a one-time historical script and phase 3 owns historical
    data. Logged rather than folded in, per the intention's scope boundary. **Phase 3 should pick
    this up.**
  - `manually_recorded` and the `changed_by_id` heuristic untouched (T7). No
    `docs/handoff/to_frontend/` file opened. The archived declared_worker_states master plan not
    opened.

  **Files touched.** Source: `domain/analytics/linear_timeline.py`;
  `services/commands/users/{_clock_worker_shift,_reconstruct_shift_middle,reconcile_worker_shift_state}.py`;
  `services/commands/task_steps/{transition_step_state,_step_transition_core}.py`.
  Docs: `docs/domains/worker_shifts/{README,states,api}.md`; this plan; the master plan (D3/D5).
  Tests: `tests/integration/services/commands/test_system_transition_reasons_cutover.py` (new);
  `tests/unit/domain/transitions/test_reason_text_contract_conformance.py` (new);
  `tests/integration/services/commands/users/test_reconcile_worker_shift_state.py`;
  `tests/integration/services/commands/task_steps/test_batch_working_step_transition_integration.py`;
  `tests/connecteam/test_clock_actions_integration.py`.

- `2026-07-31` `independent-reviewer`: **NEEDS_CHANGES.** Four findings, two blocking (R2, finding 2).
  Full text in the operator's fix brief. Summary: step payloads serialize `pause_reason: null` for a
  transition-typed record, blanking a rendered label; the label map dropped the system transitions'
  `image_url`; a stale comment in `labels.py`; and `states.md` overclaims `changed_by_id`
  preservation.

- `2026-07-31` `implementer`: **Round 1 fixes applied; STOPPED for re-review.**

  ### R2 (blocking) — step payloads lost their explanation

  **Fixed.** New `serialize_step_pause_reason(record)` in `domain/tasks/serializers.py`, used at
  **both** sites (`:186` `serialize_step_latest_state_record`, `:377`
  `serialize_step_state_record_light`). A catalog row serializes exactly as before; a transition-typed
  record synthesizes the same object from the code-owned vocabulary.

  **The contract is stricter than "render a name", and that changed the fix.**
  `frontend/packages/tasks/src/types.ts:110` parses this field with the **full** `PauseReasonSchema`
  — all twelve fields required, `slug` a **non-nullable string**, `created_at` a required string. A
  partial object would fail Zod for the entire step payload, which is worse than the `null` being
  fixed. So `resolve_transition_reason_catalog_reference` emits all twelve, and
  `test_synthesized_object_matches_the_catalog_objects_key_set` pins the two channels to an identical
  key set.

  Two field choices worth the reviewer's attention:
  - **`slug` reproduces the replaced row's slug** (`pause_ended_shift`,
    `pause_other_task_priority`) rather than the transition value. Shipped frontend code branches on
    `reason.slug === "pause_ended_shift"` (`pause-reason-transition.ts:12`). Emitting the new
    vocabulary value there would change client behaviour — the opposite of clarification 3.
  - **`created_at`** echoes the owning record's timestamp. The published schema requires a
    non-nullable string and a code-owned vocabulary has no creation instant; nothing keys off it.

  **Failing-first, verified by execution.** Reverting both sites to round-1 behaviour fails **6 of
  the 8** new tests in `test_step_payload_pause_reason_render.py`; the 2 that still pass are the
  controls (a worker-chosen catalog pause, and a WORKING record that must stay `null`). Phase 1's R9
  test was left untouched — as the reviewer noted, it asserts `pause_reason: null` and passes
  identically either way, so it could not have caught this.

  ### The "phase 2 decides" sweep — R2 as a class

  Re-walked every audit entry that deferred a decision or claimed "no label logic", plus a
  repository-wide `grep` for consumers of the `pause_reason` **relationship** (not the FK). Result:

  - **The object channel has exactly two render sites**, both now fixed. The grep is exhaustive —
    every other hit is an import, a `selectinload`, or an FK reference.
  - **R16's four endpoints all route through those two serializers**: `tasks.py:699`,
    `list_task_steps.py:58`, `list_working_section_steps.py:574`, `step_record_payload.py:212`.
  - **Two surfaces the audit did not list as endpoints are also fixed by the same change**, and they
    are the ones that would have blanked *live*: the realtime event payloads at
    `transition_step_state.py:512` and `transition_step_state_batch.py:185`. So the blast radius was
    **six** surfaces, not four — worth recording, because the audit's endpoint framing undercounted
    it.
  - **R20** (`finalize_pending_step_completion.py:35,116`) confirmed a genuine passthrough: it moves
    a `pause_reason_id` value through a payload and renders nothing.
  - **R3/R4** confirmed safe for a different reason than R2 was: they take a `PauseReason` object
    directly, and `UserDeclaredStateRecord.pause_reason_id` is `NOT NULL`, so no declaration can
    reach them without one.
  - Incidental improvement: the auto-pause record now has `pause_reason_id = NULL`, so
    `record.pause_reason` short-circuits to `None` instead of risking a lazy load in an async
    session. The change reduces that exposure rather than adding to it.

  ### Finding 2 (blocking) — system transitions lost their image

  **Fixed, and the premise behind the original omission was wrong.** `labels.py` now carries the
  seeded URLs. They are hardcoded literals in exactly two places —
  `seed_pause_reasons.py::_PAUSE_REASONS` and migration `49bd666da846:50-51` — **byte-identical to
  each other and to every workspace**. The `ws_workspace_test` segment is part of the constant, not a
  per-workspace substitution. Phase 1 read the URL's shape as evidence of provenance and inferred
  wrongly; I carried that inference forward without checking it, which is how criterion 14 came to be
  asserted rather than verified.

  `WORKER_DECLARED_STATE` keeps `image_url: None` — no catalog row ever existed for it, so `None` is
  reproduction, not loss.

  **Criterion 14 re-verified by execution, not restated.** The kiosk analytics test now asserts a
  non-null `image_url` for **both** channels in the same payload — the transition bucket and a
  catalog bucket. The catalog fixture had been constructed without an `image_url`, so the first
  version of that assertion failed on the fixture rather than on the system; the fixture now carries
  one, which is what makes the comparison meaningful.

  **Master plan corrected in two places:** the "Label-resolution strings" note and phase-3 binding
  item 3, which owned an icon-loss consequence that no longer exists.

  ### Finding 3 (low) — stale comment

  **Deleted.** `labels.py`'s header no longer claims nothing writes the column. The reviewer's point
  that it was the comment that made the icon question look already-decided is taken: the replacement
  states *why* the URLs live in code, so the next reader inherits the reasoning rather than a
  conclusion.

  ### Finding 4 — docs overclaim, and the weak test behind it

  **Answered before editing either: the code is correct, the doc was wrong.**

  Evidence, from the archived declared_worker_states Phase 2 plan (not inferred):
  *"Reconcile-authored declaration projections have `changed_by_id IS NULL`, so declaration-involved
  transitions re-check the reason and manual marker only when no legacy manual row is open."*
  `changed_by_id IS NOT NULL` is the discriminator that holds an actor-authored legacy manual pause
  sticky against re-derivation. Giving a declaration projection the declaring worker would make it
  sticky too and suppress the re-derivation it depends on — reintroducing the H1 class of defect —
  and it would be a T7 violation, since the heuristic is explicitly out of bounds for this feature
  set. The declaring worker is not lost; it is on the declaration source row.

  `states.md` now states the narrow behaviour **and why the narrowness is load-bearing**, so the next
  reader does not "fix" it.

  **Criterion 10's test strengthened.** It asserted only the arm that passes trivially. Added
  `test_rebuild_leaves_a_declaration_projection_without_an_actor`, which pins `changed_by_id IS NULL`
  on a declaration projection and asserts the actor survives on the source row. The invariant is now
  defended in both directions.

  ### Validation

  - Full suite: `26 failed / 1396 passed`; **node set identical to round 1's** — no new failure
    nodes, and none of the 26 is in a touched area.
  - Two phase 1 tests and one phase 1 integration assertion updated from `image_url: None` to the
    restored URL. These are the intended consequence of finding 2, not collateral: each now asserts
    the icon is *present*, so a regression to `None` fails.
  - `ruff check` clean on all touched files.

  **Files touched this round.** Source: `domain/transitions/labels.py`; `domain/tasks/serializers.py`.
  Docs: `docs/domains/worker_shifts/states.md`; the master plan (R2 audit row, label-resolution note,
  phase-3 item 3); this plan. Tests:
  `tests/unit/domain/transitions/test_step_payload_pause_reason_render.py` (new);
  `tests/unit/domain/transitions/{test_transition_reason_domain,test_reason_text_contract_conformance}.py`;
  `tests/integration/services/queries/worker_stats/test_transition_reason_read_tolerance.py`;
  `tests/integration/services/commands/test_system_transition_reasons_cutover.py`.

  **Still open from round 1:** criterion 11 (the `startswith("par_")` branch is provably alive under
  the "keep `reason`" ruling; discharged by phase 3) and the flagged
  `backfill_worker_shift_state_records.py` carry-forward. Neither is affected by this round.

- `2026-07-31` `independent reviewer`: **NEEDS_CHANGES.** The outage fix itself is sound and its
  failing-first claims hold under re-execution. One blocking finding: a read path phase 1
  explicitly handed to this phase (R2) was never decided, and the resulting silent behaviour
  change reaches a shipped frontend.

  ### Verified independently (do not re-check)

  - **Failing-first, per file, not per claim.** Reverting `_clock_worker_shift.py` alone fails
    exactly `test_zero_catalog_clock_out_closes_open_working_step` and
    `test_overnight_safeguard_inherits_the_typed_clock_out`. Reverting `transition_step_state.py`
    alone fails exactly `..._via_single_step_endpoint`. Reverting `_step_transition_core.py` alone
    fails `..._via_shared_transition_core` with `NameError: name 'select' is not defined` at
    line 89. **The two task-switch tests therefore demonstrably reach different modules** — the
    failure mode criterion 3 was written to catch is absent.
  - **Criterion 17 confirmed by execution**, not inspection: the `NameError` was present, and the
    branch is unreachable in production (`transition_step_state_batch.py:130` rejects
    non-batch-capable steps; the guard fires only for them). The added import is inert in
    production.
  - **Criterion 4**: `grep -rn "get_system_pause_reason" app --include="*.py"` returns the
    definition line only.
  - **Adversarial probe — the derivation tests are not asserting on seeded data.** Deleting the
    `transition_reason=` argument from the `UserShiftStateRecord(...)` construction in
    `_reconstruct_shift_middle.py:244` kills four tests (carries / idempotence / both declaration
    tests).
  - **Guard-sweep item 1 binds.** Restoring the naive `reason or UNSPECIFIED_REASON` in `_sweep`
    kills exactly `test_rebuild_carries_the_transition_reason_onto_derived_rows`, as claimed —
    though that single node is the whole of its coverage.
  - **Phase 1's structural guard is intact.** `bucket_key(resolved_catalog_ids)` still takes the
    resolved set as a required argument; `test_breakdown_never_emits_a_catalog_id_that_did_not_resolve`
    is unmodified and green.
  - **Suite, node sets, run-2 vs run-2**, baseline `git worktree` at `0d9b049` with all `app/.env*`
    copied in: baseline **27 failed / 1338 passed** (matching phase 1's recorded baseline exactly),
    working **26 failed / 1387 passed**. Node-set diff: **zero added, exactly one removed** —
    `test_worker_shift_commands.py::test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`.
    That is criterion 18's claim, confirmed. Working-tree run-1 and run-2 node sets identical.
    `test_worker_shift_commands.py` 42/42.
  - Handoff untouched; the archived declared_worker_states plan untouched; `manually_recorded` and
    the `changed_by_id` heuristic absent from the production diff (T7); every modified production
    file attributable to phase 1 or phase 2 — **no out-of-scope production change in the diff**.
    Docs carry no history, no phase or plan references, nothing about phases 3–4. `ruff`: the same
    5 `F401` in `transition_step_state.py` as at baseline, verified against the baseline worktree.
  - The frontend Zod schemas tolerate the new key space (`worker-shifts/src/types.ts:4`
    `id: z.string()`; `:74` `pause_by_reason: z.record(z.string(), z.number())`), so the
    "invisible" ruling holds at the validation layer. The findings below are about rendered values,
    not parse failures.

  ### F1 — BLOCKING. R2 was assigned to this phase, never decided, and ships a silent regression

  `app/beyo_manager/domain/tasks/serializers.py:186,377` · criterion 16 ("existing behaviour
  otherwise identical") and the plan's rule that the R1–R24 audit "is this phase's checklist too".

  The master plan's Phase 1 inventory, R2, ends: "**Phase 2 decides whether step payloads need the
  transition surfaced.**" This Review log contains no R2 entry; `domain/tasks/serializers.py`
  appears in neither the guard-shape sweep, the file-read intent list, nor "Files touched". The
  decision was made by omission.

  Its consequence is live. `serialize_step_state_record_light` returns
  `"pause_reason": serialize_pause_reason(record.pause_reason) if record.pause_reason is not None
  else None`. This phase sets `pause_reason_id = NULL` on every `ENDED_SHIFT` record and every
  task-switch auto-pause, so that object is now `null` where it was a populated catalog object.
  Reproduced by execution in a workspace that **does** hold the catalog: after
  `transition_step_state`, the auto-paused record serialises to `pause_reason = None`,
  `pause_reason_id = None`, `transition_reason = other_task_priority`.

  It reaches `last_state_record.pause_reason` at `list_working_section_steps.py:574`,
  `step_record_payload.py:212`, `transition_step_state.py:512` and
  `transition_step_state_batch.py:185`. The shipped consumer is
  `frontend/packages/stats/src/lib/worker-stats-dto.ts:113` —
  `step.last_state_record?.pause_reason?.name?.trim() || null` — which now renders nothing for
  exactly the two transitions this phase retyped. `frontend/packages/stats/src/types.ts:60-63`
  documents the field as "populated for paused/ended-shift transitions".

  Phase 1's R9 coverage does not detect this: it asserts `pause_reason: null` for a typed row, which
  passes identically before and after the cutover.

  Required: make the R2 decision explicitly and record it. Either surface the transition in step
  payloads (a contract change → proposal + STOP per criterion 13), or accept the null and record it
  as a deliberate, user-visible consequence with the operator's ruling. It must not remain
  undecided.

  ### F2 — MEDIUM. System transitions lose their icon on live surfaces; criterion 14 says otherwise

  `app/beyo_manager/domain/transitions/labels.py:32,37` (`"image_url": None`) vs
  `services/commands/bootstrap/phases/seed_pause_reasons.py:26-27`, where both replaced catalog rows
  carry a real image URL · criterion 14.

  In the workspaces that hold the catalog — i.e. the one workspace that is **not** currently broken
  — `GET /worker-shifts/current` → `pause_reason.image_url`, the clock-out analytics
  `pause_reasons[key].image_url` (handoff §5.1), and the roster timeline lookup all go from a URL to
  `null` the moment this phase deploys. `image_url` is nullable in both the handoff and the frontend
  schema, so nothing breaks — but it is a rendered regression, criterion 14 claims the kiosk
  analytics contract is "unaffected", and this phase's own conformance test encodes the loss without
  flagging it (`test_reason_text_contract_conformance.py:76`, `"image_url": None`).

  Required: record it, with the operator's decision on whether a code-owned asset is chosen now or
  the icon is accepted as lost until phase 3.

  ### F3 — MEDIUM. A comment this phase falsified, and it is the comment that deferred F2

  `app/beyo_manager/domain/transitions/labels.py:16-20`: "**Nothing writes `transition_reason` in
  this phase, so no live row loses an icon here** — but phase 3's backfill DOES flip real rows onto
  this map… Flagged for phase 3, not decided here." Phase 2 is the phase that starts writing it; the
  deferral is wrong by one phase, and it is why F2 went unexamined. Same class:
  `models/tables/tasks/step_state_record.py:52` and
  `models/tables/users/user_shift_state_record.py:36` both still read "nothing writes it in phase 1".

  These are phase-1 files, but this is the change that made the statements false, and the plan's
  file-read intent already permitted opening both model files.

  ### F4 — LOW. `states.md` states a preservation guarantee the rebuild does not give

  `docs/domains/worker_shifts/states.md`, "The rebuild": "a rebuilt segment keeps the
  `changed_by_id` of the row it came from" · criterion 20 ("accurate, not merely edited").

  `_reconstruct_shift_middle.py:234` sources `changed_by_id` only from
  `manual_changed_by_id_by_id`, keyed on legacy manually-recorded derived rows. Step-sourced and
  declaration-sourced segments always receive `None`. Criterion 10's test seeds a manual row, so
  nothing binds the broader claim the doc makes.

  ### F5 — LOW. Guard-sweep item 4's evidence is broader than the code

  `reconcile_worker_shift_state.py:222-234`. The added `current.transition_reason ==
  transition_reason` conjunct sits behind `or not declared_projection_involved`, so it only takes
  effect when a declaration projection is on one side. A step-pause → step-pause change of
  transition is still treated as unchanged. That staleness is pre-existing and unchanged by this
  phase, so this is a correction to the claim ("a row differing only in its transition is no longer
  treated as unchanged"), not a defect.

  ### Noted, not findings

  - **Criterion 11 is unmet by design** and was disclosed rather than hidden — correct handling, and
    the reasoning holds. It does mean the phase ships one acceptance criterion open; that is the
    operator's call, not a defect.
  - `app/scripts/backfill/backfill_worker_shift_state_records.py` and the criterion-17 `select`
    import are both disclosed and correctly reasoned. `heal_open_shifts_today.py` does call
    `reconstruct_shift_middle` (line 169) and does inherit the change — the claim checks out.
  - Incidental confirmation of the intention's Finding 2: seeding a second workspace's
    `pause_other_task_priority` row during this review raised
    `UniqueViolationError: uq_pause_reasons_slug`.

  **Verdict: `NEEDS_CHANGES`** — F1 blocking; F2/F3 to be recorded and ruled on; F4/F5 corrections.

- `2026-07-31` `independent reviewer` (round 2): **NEEDS_CHANGES.** All four round-1 fixes verified
  correct by execution. One blocking finding, and it is the same class as R2 rather than a new one:
  the round-2 sweep concluded the `pause_reason` **object** channel has "exactly two render sites",
  and there are **three**. The third is `record_detail` in
  `get_worker_linear_timeline_breakdown.py` — the master plan's own audit row **R9** — and it still
  serialises `null` for a transition-typed record, into a field a shipped frontend renders.

  ### Verified independently — do not re-check

  - **R2's failing-first claim holds exactly.** Reverting both sites in
    `domain/tasks/serializers.py` to `serialize_pause_reason(record.pause_reason) if … else None`
    fails **6 of 8** nodes in `test_step_payload_pause_reason_render.py`; the 2 that survive are the
    two controls (`test_worker_chosen_catalog_pause_is_untouched`,
    `test_record_explaining_itself_neither_way_still_serializes_null`). Phase 1's R9 test was **not**
    quietly extended — the new file is new, and `test_transition_reason_read_tolerance.py:389` is
    untouched (see F1, where that is the problem).
  - **The six `serialize_step_*` surfaces are covered.** Re-derived from the four `selectinload`
    sites outward and from `serialize_step_state_record_light` / `serialize_step_latest_state_record`
    callers backward: `tasks.py:699`, `list_task_steps.py:58`, `list_working_section_steps.py:574`,
    `step_record_payload.py:212`, and the two realtime payloads `transition_step_state.py:512`,
    `transition_step_state_batch.py:185`. All route through the fixed serializer. No other event
    payload embeds a pause reason.
  - **`client_id = "shift_ended"` reaches no consumer that cares.** No frontend code reads
    `client_id` off an embedded `pause_reason`; the only two send-backs of `pause_reason_id`
    (`PauseReasonSheetPage.tsx:113,134`) take it from `usePauseReasonsQuery`, the catalog list, which
    the synthesized object never enters. `created_at` likewise: nothing renders, sorts or dedupes on
    it (`worker-daily-step-dto.ts:91` reads the *record's* `created_at`, not the reason's).
  - **The `slug` converse is clean, but the stated justification is not the real one.**
    `resolvePauseReasonTransition` (`pause-reason-transition.ts:12`) is fed **only** from
    `usePauseReasonsQuery` — a step record's embedded reason never reaches it, so the cited branch is
    not what the choice protects. The choice is nonetheless right for a different reason: the
    published schema requires a non-nullable `slug`, and reproducing the replaced row's keeps display
    parity. The converse is safe: selectability is gated on the catalog list endpoint, and
    `is_system_managed` has **no frontend consumer at all**. Recorded so the next reader does not
    inherit the wrong rationale.
  - **Criterion 14 was a fixture defect, correctly repaired.** The load-bearing assertion is
    `analytics["pause_reasons"][OTHER_TASK_PRIORITY]["image_url"] is not None`, which does not depend
    on the fixture. Giving the catalog `PauseReason` an `image_url` repaired a *control* that would
    otherwise have failed on the fixture rather than on the system. The assertion was not bent.
  - **The three restored `image_url` assertions still detect regression.** All three
    (`test_transition_reason_domain.py:106`, `test_reason_text_contract_conformance.py:74`,
    `test_transition_reason_read_tolerance.py:217`) assert **full-dict equality** including the exact
    URL; a regression to `None` fails each.
  - **Finding 4's direction is right, and load-bearing in live code, not just an archived plan.**
    The quote checks out in full context (`PLAN_declared_worker_states_phase2_derivation…:36`), and
    `reconcile_worker_shift_state.py:215-219` **depends** on it:
    `current_is_declared_projection = … and current.manually_recorded and current.changed_by_id is
    None`. An actor on a declaration projection would make that False and suppress the re-derivation.
    The doc was wrong; `_reconstruct_shift_middle.py` is not the defect.
    `test_rebuild_leaves_a_declaration_projection_without_an_actor` pins the other arm; neither
    `manually_recorded` nor the `changed_by_id` heuristic was touched (T7 clean).
  - **Master-plan edits did not overreach.** Binding item 3 and the "Label-resolution strings" note
    are struck through and marked `CLOSED` / `CORRECTED` with the round and finding — phase 1's text
    is visibly superseded, not overwritten. Same for the R2 audit row. Nothing else in phase 3's
    scope moved as a side effect of the closure. The archived declared_worker_states plan is
    unedited (`git status` on `docs/architecture/archives/implementation/declared_worker_states/`
    is empty).
  - **Suite, run-1 vs run-2 on the working tree**: `26 failed / 1396 passed` both runs, **node sets
    byte-identical**. Matches the implementer's report. `+9` passes over round 1's 1387 = the 8 new
    render nodes plus the new declaration-projection node. Spot-checked the one failure in a
    feature-adjacent path — `test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
    fails with `TypeError: empty_page() got an unexpected keyword argument 'roles'`, unrelated.
    `ruff check` clean on all touched files.
  - **Carried-over deferrals confirmed, not re-litigated.** Criterion 11: the
    `startswith(f"{PauseReason.CLIENT_ID_PREFIX}_")` branch is still present at
    `domain/users/serializers.py:170` and is alive under the "keep `reason`" ruling — discharged by
    phase 3. `backfill_worker_shift_state_records.py` still builds `LinearInterval`s without
    `transition_reason`; it is an offline script, not a runtime path, and phase 3 is the right owner.
    The 5 `F401`s in `transition_step_state.py` are baseline debt (T8), unchanged.

  ### F1 — BLOCKING. R9 is R2, in a third render site the sweep declared did not exist

  `app/beyo_manager/services/queries/worker_stats/get_worker_linear_timeline_breakdown.py:432` ·
  criterion 16 ("existing behaviour otherwise identical"), and the round-2 entry's own claim that
  "the object channel has exactly two render sites".

  `record_detail` renders a **full `PauseReason` object** by calling `serialize_pause_reason`
  directly on a separately-fetched row, not via `record.pause_reason`. That is why a grep for
  `.pause_reason` did not surface it — the review prompt's warning about "resting on one grep
  pattern" was the right one. Re-deriving from `serialize_pause_reason`'s callers instead finds it
  immediately; it is also listed in the master plan as **audit row R9**, "same file, `record_detail`
  nested `pause_reason`".

  The behaviour is the R2 defect verbatim. This phase sets `pause_reason_id = NULL` on every
  `SHIFT_ENDED` and `OTHER_TASK_PRIORITY` record, so `pause_reason_objects.get(record.reason)`
  resolves to nothing and the field serialises `null` where it previously carried a populated
  catalog object. The consumer is
  `frontend/packages/stats/src/lib/time-line-calendar/segment-adapter.ts:113` —
  `reasonLabel: record.pause_reason?.name ?? null` — rendered at `TimelineEventBlock.tsx:52,112-115`,
  `WorkerTimelineSlidePage.tsx:176-177` and `WorkerTimelineEventSheetPage.tsx:101-102`. Schema:
  `packages/stats/src/types.ts:304`, the same full `PauseReasonSchema` that drove the R2 fix.

  Two things make this worse than an oversight:

  1. **The phase's own tests pin the defect in both directions.**
     `test_transition_reason_read_tolerance.py:386-389` asserts
     `step_details[0]["pause_reason"] is None` under the comment *"the step payload gains no field in
     this phase"* — which is exactly the premise round 2 overturned for the other two sites. The
     sibling `test_breakdown_prefers_the_catalog_reason_when_a_row_carries_both:496` asserts
     `paused[0]["steps"][0]["pause_reason"]["client_id"] == reason.client_id` for a row that *does*
     carry a catalog id. The before/after asymmetry is proven by this phase's own two tests.
  2. **It is internally inconsistent inside one response.** This phase *did* fix the segment-level
     `reason` key in the same payload (`bucket_key` + the `pause_reasons` map top-up), so the same
     pause now reads "Other task priority" at the segment and blank at the step immediately below
     it. `test_breakdown_resolves_a_transition_reason_step_record` asserts both facts, four lines
     apart.

  Required: apply the R2 decision here. `record.transition_reason` is already on
  `_StepTimelineRecord`, and `resolve_transition_reason_catalog_reference` already exists — the fix
  is the same one-call substitution, plus reversing the assertion at :389 and its comment. If the
  operator instead rules the null acceptable on this surface, that must be recorded as a deliberate
  user-visible consequence, per the same standard applied to R2.

  **Class note, not a separate finding.** The remaining R-rows that phase 1 marked "no label logic"
  or "opaque passthrough" were re-derived and are genuinely clean: R1 (catalog leaf), R3/R4 (take a
  `PauseReason` directly; `UserDeclaredStateRecord.pause_reason_id` is `Mapped[str]`, NOT NULL),
  R16 (`selectinload` feeding the now-fixed R2), R19–R22. R9 is the only surviving instance.

  ### F2 — LOW. Round-1 F3 was reported fixed and is fixed in one of three places

  The round-1 finding named `labels.py` **and** explicitly added: *"Same class:
  `models/tables/tasks/step_state_record.py:52` and `models/tables/users/user_shift_state_record.py:36`
  both still read 'nothing writes it in phase 1'."* Only `labels.py` was edited. Both model comments
  are unchanged and now false:

  - `app/beyo_manager/models/tables/tasks/step_state_record.py:54` — "nothing writes it in phase 1"
  - `app/beyo_manager/models/tables/users/user_shift_state_record.py:36` — "Nothing writes it in
    phase 1."

  A third instance the round-1 review did not catch is worse than cosmetic:
  `app/beyo_manager/services/queries/worker_stats/list_workers_linear_timeline.py:59` — *"Nothing
  writes it yet, so this is inert today"* — sits directly above the
  `record.reason or record.transition_reason or UNSPECIFIED_REASON` fallback that this phase made
  live. A reader trusting that comment would delete the branch and silently re-break roster
  bucketing.

  ### F3 — LOW. The seed's drift guard now points at two of three copies

  `app/beyo_manager/services/commands/bootstrap/phases/seed_pause_reasons.py:10-14` warns: *"Duplicated
  (not imported) in migrations/versions/49bd666da846… If you change the values below, mirror the
  change into that migration's `_PAUSE_REASONS` tuple too."* There are now **three** copies of the
  image URLs. `labels.py` points at the other two, but the guard at the source does not point back at
  `labels.py`, so the one-directional warning will not stop the drift it exists to stop.

  ### The S3 URLs — assessed, and not a blocking finding

  The prompt asked what the risk actually is. Measured rather than asserted:

  - **The blast radius is at most one row per slug, database-wide.**
    `models/tables/pause_reasons/pause_reason.py:47` declares `Index("uq_pause_reasons_slug", "slug",
    unique=True)` — **globally** unique, not per workspace. Only one workspace in the entire database
    can hold `pause_ended_shift`; that is the same index that causes this outage. "Identical in every
    workspace" is therefore a claim about one row, not 3132.
  - **The host matches production configuration.** `.env.production.ec2` sets
    `STORAGE_BUCKET=test-bootstrap-local`, `STORAGE_REGION=eu-north-1` — the literal in `labels.py`
    is today's production bucket, however unfortunate its name reads in shipped code.
  - **The one falsifier in the repo is real but self-healing.** `update_pause_reason.py:43` writes
    `image_url` (and `name`) with **no `is_system_managed` guard** —
    `domain/pause_reasons/guards.py` guards `delete` only. So an admin *can* have changed that one
    row. But `seed_pause_reasons.py:39-46` repairs `image_url` back to the constant on any bootstrap
    rerun, which makes divergence transient for this field specifically — evidence the implementer's
    claim did not use and which supports it.
  - **The failure mode if it diverged is a stale icon, not a broken one** — the seeded asset, which
    that workspace was served until an admin replaced it. Note the same exposure already applies to
    `name`, which round 1 accepted under criterion 5; the round-2 `image_url` work is consistent with
    that, not a new class.

  Recorded as risk, not a finding: the residual is one editable row, one field, self-repairing, with
  a stale-icon worst case. Hardcoding a configurable bucket/region into *runtime domain* code (rather
  than seed data) is real debt and F3 is where it will bite — it is not worth blocking a phase that
  ends a live outage.

  ### Noted, not findings

  - `serialize_step_pause_reason` falls back to `created_at=""` when both `created_at` and
    `entered_at` are `None`. It satisfies `z.string()` and nothing reads the field, so it is inert —
    but `""` is not a datetime, and a stricter future schema would reject it.
  - **The tree was not quiet during this review.** Two commits landed mid-pass (`f344230`, `b0dd236`),
    committing the master plan, both plans and the intention, and amending **phase 3 and phase 4**
    scope. Docs only — no production or test file moved, and the suite figures above are unaffected.
    Flagged because the phase-3 amendment (`pause_ended_shift` references now left alone) postdates
    the round-2 entry and is the operator's own ruling, not part of what was under review here.

  **Verdict: `NEEDS_CHANGES`** — F1 blocking (R9, the third render site); F2/F3 low, comment-level.
  Everything the round-1 findings asked for was done correctly; what is missing is the generalisation
  the R2 fix implied.

- `2026-07-31` `implementer`: **Round 3 fixes applied; STOPPED for re-review.** Round 2's four fixes
  were not reopened; criterion 11, the `backfill_worker_shift_state_records.py` carry-forward and the
  S3-URL risk were not re-litigated.

  ### F1 (blocking) — R9 was R2 in a third render site

  **Fixed** at `get_worker_linear_timeline_breakdown.py:432` (`record_detail`). The nested object now
  takes the same two channels as the other two sites: `serialize_pause_reason` when the catalog row
  resolved, otherwise `resolve_transition_reason_catalog_reference` off `record.transition_reason`,
  with `created_at=record.entered_at.isoformat()` — that record's own timestamp, matching what
  `serialize_step_pause_reason` does.

  **The fix did not widen.** `bucket_key`, the segment-level `reason`, and the `pause_reasons` map
  top-up are untouched. The workspace-resolution guard is untouched and still upstream of the
  change: `pause_reason` is already `pause_reason_objects.get(...)`, so a catalog id that did not
  resolve in this workspace still falls through instead of being emitted. The synthesized branch is
  reached only when that resolution produced nothing, which is the same condition that previously
  produced `null`.

  **Failing-first, proven per node:**

  | Node | Before fix | After fix |
  |---|---|---|
  | `test_breakdown_resolves_a_transition_reason_step_record` | **FAILED** — `assert None is not None` at the reversed assertion | PASSED |
  | `test_breakdown_prefers_the_catalog_reason_when_a_row_carries_both` (control, unmodified) | PASSED | PASSED |

  The assertion was written and run **before** `record_detail` was touched. The old assertion and its
  comment (*"the step payload gains no field in this phase"*) are gone — that comment was the round-1
  premise round 2 overturned, and leaving it green is how this survived a round. The replacement
  asserts a populated object, its `name`, its `client_id` and a non-null `image_url`, and still
  asserts no new top-level key on the detail: the shape is unchanged, only populated.

  **Master plan audit row R9** corrected in the R2 row's format — struck through, marked decided,
  round named, with the reason it survived (the sweep grepped `.pause_reason`; `record_detail` calls
  `serialize_pause_reason` on a separately-fetched local).

  ### The sweep, re-derived by a route that finds F1

  Round 2's sweep was wrong in method, not just in result. Re-derived two ways: **every caller of
  `serialize_pause_reason`**, and **every construction of a twelve-field pause-reason-shaped dict**
  (probed on `requires_description` and `is_system_managed`, fields no other shape carries).

  Callers of `serialize_pause_reason` — the complete list:

  | file:line | Disposition |
  |---|---|
  | `domain/tasks/serializers.py:192` | Inside `serialize_step_pause_reason` — **fixed round 2**; both step render sites (`:207`, `:398`) delegate to it |
  | `services/queries/worker_stats/get_worker_linear_timeline_breakdown.py:444` | `record_detail` — **fixed this round (F1)** |
  | `services/queries/pause_reasons/list_pause_reasons.py:36` | Catalog leaf — iterates `PauseReason` rows from the catalog table; no transition can reach it |
  | `services/queries/pause_reasons/get_pause_reason.py:19` | Catalog leaf — same |
  | `services/commands/pause_reasons/create_pause_reason.py:47` | Returns the row just created — same |
  | `services/commands/pause_reasons/update_pause_reason.py:53` | Returns the row just updated — same |

  Twelve-field constructions: exactly two — `domain/pause_reasons/serializers.py` (the real one) and
  `domain/transitions/labels.py` (the synthesized one). **No third hand-rolled copy exists.**

  The other embedded shape is the three-field reference,
  `domain/users/serializers.py::_serialize_pause_reason_reference` (called at `:212`), whose
  transition counterpart `_serialize_transition_reason_reference` has existed since phase 1. Covered.

  **So: three render sites across two shapes, all three now handling both channels.** The four
  catalog-leaf endpoints are structurally unable to receive a transition — they read the catalog
  table.

  **R3/R4 confirmed independently rather than inherited:**
  `UserDeclaredStateRecord.pause_reason_id` is `Mapped[str]` (non-optional → NOT NULL) at
  `models/tables/users/user_declared_state_record.py:20`, so no declaration can reach those
  serializers without a catalog row. R1, R16, R19–R22 re-checked and clean.

  ### F2 (low) — three false comments, one dangerous

  All three rewritten to state what is true **and why**, per the standard round 2 applied to
  `labels.py`:

  - `models/tables/tasks/step_state_record.py` — now names which transitions write it, states that
    `pause_reason_id = NULL` accompanies them and why they are alternatives rather than companions,
    and explains that nullable encodes "a worker chose this instead".
  - `models/tables/users/user_shift_state_record.py` — now states that both derivations write it,
    why it is carried separately from `reason` through the sweep, and that this table is the
    documented exception where a row may carry both (which phase 4's constraint must allow).
  - `services/queries/worker_stats/list_workers_linear_timeline.py` — the one that mattered. Now says
    the fallback is **load-bearing**, that every clock-out and task-switch auto-pause reaches it, and
    that deleting the middle term buckets all of it as `unspecified` **with no error anywhere**.
    Stating the failure mode is what stops the next reader from "simplifying" it.

  ### F3 (low) — the drift guard now names all three copies

  `seed_pause_reasons.py` names `labels.py` as the third copy, says which fields it holds and for
  which slugs, and states the failure mode: a system transition rendering differently from the row it
  replaced, silently, because nothing joins the two.

  ### Also corrected: the `slug` justification round 2 got wrong

  The reviewer was right and I verified it independently rather than accepting it:
  `resolvePauseReasonTransition` is called only from `PauseReasonSheetPage.tsx:100,129`, fed from
  `usePauseReasonsQuery` → `pauseReasonsData.pause_reasons` — the catalog list endpoint. A step
  record's embedded object never reaches that branch. The comment in `labels.py` claimed it did.
  Corrected to the real reasons: the published schema's **non-nullable `slug`**, and display parity.
  The choice itself is unchanged.

  I fixed this even though the brief said "otherwise leave it", because F2's whole standard is that a
  false comment is a defect — leaving a known-false justification in the same file I was editing for
  F3 would contradict the finding I was closing.

  ### Optional item — taken

  The `created_at=""` fallback in `serialize_step_pause_reason` is **removed**. `entered_at` is
  `nullable=False`, so one of the two always exists on a persisted record; the expression is now
  `(record.created_at or record.entered_at).isoformat()`. Rationale recorded in the code: `""`
  satisfies `z.string()` while not being a datetime, so it ships an unparseable value to a client
  that has no reason to distrust it — a worse failure than raising at the boundary.

  ### Validation

  - Full suite: `26 failed / 1396 passed`; run-1 and run-2 node sets identical to each other **and
    byte-identical to the round-2 set**. No deviation to explain.
  - `ruff check` clean on all eight touched files.
  - **One thing I could not verify:** commits `f344230` / `b0dd236` are not visible from this
    working tree (`git rev-parse` reports no repository at or above
    `ManagerBeyo-app/`), so I could not rebase against `HEAD` or diff what they changed. I worked
    from the files on disk, which carry the phase-3/phase-4 amendments and T9 described in the brief.
    Flagged rather than assumed.

  **Files touched this round.** Source:
  `services/queries/worker_stats/get_worker_linear_timeline_breakdown.py`;
  `services/queries/worker_stats/list_workers_linear_timeline.py`;
  `domain/transitions/labels.py`; `domain/tasks/serializers.py`;
  `models/tables/tasks/step_state_record.py`; `models/tables/users/user_shift_state_record.py`;
  `services/commands/bootstrap/phases/seed_pause_reasons.py`. Tests:
  `tests/integration/services/queries/worker_stats/test_transition_reason_read_tolerance.py`. Docs:
  the master plan (audit row R9); this plan. **No domain-doc change** — F1 restores documented
  behaviour rather than altering it, and `docs/domains/worker_shifts/` describes the shift domain,
  not the breakdown payload's nested shape.

- `2026-07-31` `independent reviewer` (round 3): **APPROVED.** No findings. F1, F2 and F3 are fixed,
  both out-of-brief changes are correct and did not widen, and **the sweep is settled** — re-derived
  independently by four routes, matching the implementer's list exactly.

  ### The git environment problem — root cause found, it is not a repo problem

  Two prior sessions reported "no repository at or above `ManagerBeyo-app/`" and the operator
  reported `--is-inside-work-tree` → true. **Both are correct.** `ManagerBeyo-app/` is not a
  repository; `ManagerBeyo-app/backend/` and `ManagerBeyo-app/frontend/` are **two separate
  repositories**. `git rev-parse` run from the session's primary working directory fails exactly as
  reported; run from inside `backend/` it succeeds. Nothing is broken — the command was run one level
  too high. Recorded here so the third session does not rediscover it.

  This round therefore had full history access: hunk-level diffs, `git show` on the intervening
  commits, and node-set comparison against round 2's recorded set.

  ### F1 — fixed, and it did not widen

  `get_worker_linear_timeline_breakdown.py:443-450`. Verified structurally, not by reading the new
  code alone: the file's **hunk map is identical to round 2's** (`git diff -U0 … | grep '^@@'`) except
  for the import at `:18` and one new hunk replacing the single `record_detail` line with sixteen.
  `bucket_key` is **byte-identical** to round 2, as are the `resolved_catalog_ids` frozenset, the
  `detail_owners` block and the `segment_reason` expression. Nothing in the neighbourhood moved.

  **Failing-first, by execution.** Reverting the synthesized branch to
  `serialize_pause_reason(pause_reason) if pause_reason is not None else None` fails **exactly one
  node** — `test_breakdown_resolves_a_transition_reason_step_record` — with the other 43 in
  `test_transition_reason_read_tolerance.py` + `tests/unit/domain/transitions/` green, including the
  unmodified control at `:505`. Restored and re-confirmed green.

  ### The upstream guard — probed adversarially, holds

  Three throwaway probes run against the real query, then deleted (not part of the change set):

  | Probe | Result |
  |---|---|
  | Step carrying **another workspace's** `pause_reason_id` | Foreign id and foreign row name **absent from the entire response**; nested object is `null`, not fabricated |
  | Step whose catalog row was **soft-deleted** | No fabricated object |
  | Step carrying **neither** channel | `null` |

  Phase 1's blocking finding is not loosened. The guard is upstream by construction —
  `pause_reason` is already `pause_reason_objects.get(...)`, which is workspace-scoped, and
  `resolve_transition_reason_catalog_reference` returns `None` for anything outside the vocabulary,
  so a foreign id cannot reach either branch.

  **Correction to the brief's probe list:** "a reason hard-deleted since" is **not reachable**. The FK
  is `ON DELETE RESTRICT` (`fk_step_state_records_pause_reason_id_pause_reasons`) — attempting it
  raises `RestrictViolationError`. Soft delete is the only reachable variant and is what
  `delete_pause_reason` does. Worth recording: this probe has been carried forward across rounds as
  if it were reachable.

  ### The sweep — settled, by four routes

  Re-derived independently before reading the implementer's list, then compared. **Exact match.**

  | Route | Result |
  |---|---|
  | Callers of `serialize_pause_reason` | **6** — 2 render (`domain/tasks/serializers.py:192`, `get_worker_linear_timeline_breakdown.py:444`), 4 catalog leaf (`get_pause_reason.py:19`, `list_pause_reasons.py:36`, `create_pause_reason.py:47`, `update_pause_reason.py:53`) |
  | Twelve-field shape (`"is_system_managed"` / `"requires_description"` as output keys) | **2** constructions — `domain/pause_reasons/serializers.py`, `domain/transitions/labels.py`. No hand-rolled third |
  | **Every output key** `"pause_reason":` / `"pause_reasons":` in `beyo_manager/` | **13**, all accounted for. This is the route that would have caught round 2's miss most directly, because it does not depend on how the value was obtained |
  | Three-field reference shape | `serialize_declared_state:119` and `_serialize_pause_reason_reference:129`, both taking `PauseReason` directly; `_serialize_transition_reason_reference` is the counterpart. R3/R4 |

  R3/R4 re-confirmed at the model: `UserDeclaredStateRecord.pause_reason_id` is `Mapped[str]` at
  `user_declared_state_record.py:20`. Three render sites across two shapes, all three handling both
  channels. **Three rounds have turned on this sweep; it is now closed.**

  ### F2 / F3 — fixed, and the third comment does what was asked

  All three comments now state the failure mode rather than the conclusion.
  `list_workers_linear_timeline.py:57-64` is the one that mattered and now says the fallback is
  load-bearing, that every clock-out and auto-pause reaches it, and that deleting the middle term
  buckets all of it as `unspecified` **with no error anywhere**. F3's guard names `labels.py`, which
  fields it holds, for which slugs, and what silent divergence looks like.

  ### The two out-of-brief changes — both correct

  - **`slug` justification.** The *choice* is unchanged: the `_TRANSITION_REASONS` map is
    byte-identical to round 2, every value included. Only the comment block above it moved, and the
    replacement is right — `resolvePauseReasonTransition` is fed solely from `usePauseReasonsQuery`,
    so the frontend branch is not a consumer. Nothing else in the docstring drifted. Editing it while
    closing F3 in the same file was the consistent call, not scope creep.
  - **`created_at=""` removal.** The nullability claim checks out:
    `step_state_record.py:76` — `entered_at: Mapped[datetime] = mapped_column(..., nullable=False)`.
    Stronger than the implementer argued: both realtime construction sites set `entered_at=now`
    explicitly (`transition_step_state.py:280,346`), so the value is present before any flush and the
    old fallback was unreachable on every path, not merely on persisted rows. The change is confined
    to that expression.

  ### Suite — one correction to the claim, not a regression

  Measured four runs. Round-3 **run-1**: `26 failed / 1396 passed`, node set **byte-identical** to
  round 2's recorded set. Round-3 **run-2 and run-3**: `27 failed / 1395 passed`, identical to each
  other, differing from round 2 by exactly one node —
  `test_process_shopify_products_integration.py::test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task`.

  Not attributable to this change: it **passes in isolation**, shopify is untouched by the change set
  (`git status` has no shopify path), and it appeared between run-1 and run-2 of this session. It is
  the shared-DB/Redis accumulation the plan's own validation note documents — but it now **latches**
  rather than clearing, which the "run-2 vs run-2" rule does not account for. So the implementer's
  "byte-identical" is right for run-1 and overstated for run-2; the difference is measurement
  artefact, not regression. Flagged because a later round comparing run-2 sets could read this node
  as new.

  `ruff check` clean on all eight touched files, verified individually.

  ### Noted, not findings

  - `bucket_key`'s docstring still reads "`record_detail`'s nested `pause_reason` object … must not
    see a transition value". Strictly true — it constrains what `reason` may hold, and that
    constraint still binds — but now misparseable, since that object *does* carry a transition
    through a different door. Not raised as a finding: the sentence is literally correct and this
    round already closed three comment defects.
  - The R9 correction landed in commit `b86cb0e`, whose subject is T9 — the decision that commits
    stay single-purpose. Operator's commit, outside this review's scope; noted only because T9 exists
    to prevent exactly that shape.

  **Verdict: `APPROVED`.** Phase 2 is complete: the outage fix, its failing-first evidence, all three
  render sites, the derivation invariants, the docs, and the sweep. Criterion 11 remains open by
  design and disclosed, discharged by phase 3.

## Lifecycle transition

- Current state: `archived`
- Next state: `none` (terminal)
- Transition owner: `David`
- Approved at (UTC): `2026-07-31T17:40:00Z` — independent review, round 3.
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_system_transition_reasons_phase2_cutover_20260731.md`
- Archive record: `backend/docs/architecture/archives/implementation/system_transition_reasons/ARCHIVE_RECORD_PLAN_system_transition_reasons_phase2_cutover_20260731.md`
