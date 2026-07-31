# Implementer prompt — System Transition Reasons, Phase 3: historical backfill

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

**This is the one irreversible phase in the set.** Phases 1 and 2 were additive and reversible;
this one rewrites historical rows. Everything below is shaped by that.

The good news is that it is now much smaller than the plan was originally written for. Two of its
three row populations were removed by operator ruling. **You are migrating one population: rows
whose `pause_reason_id` points at `pause_other_task_priority`.**

## Protocol

1. Load and follow `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process as: implement → validate → review-log entry → **STOP for independent review.**
   Summary/archive only after the reviewer approves.
2. Read, in order:
   - `docs/domains/worker_shifts/` — all three files. The living map of the domain you are
     touching, and one of them becomes false in this phase (see "Domain documentation").
   - `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md` — decisions
     **T1–T9**, the **"Phase 1 inventory"** section, and the items phase 2's close-out recorded as
     binding on you.
   - Your plan: `.../system_transition_reasons/PLAN_system_transition_reasons_phase3_backfill_20260731.md`
3. **Clarifications.** Two of three are resolved and recorded in the plan. Only "batched or
   single-statement" is open, and it is decided by the volume figure, not by preference — record the
   figure you decided from.

## What you must NOT touch — three populations, two of them off-limits

| Rows pointing at | Action | Why |
|---|---|---|
| `pause_other_task_priority` | **Migrate** → `OTHER_TASK_PRIORITY`, `pause_reason_id = NULL` | The only system population left |
| `pause_ended_shift` | **Leave alone** | A worker's pick and a clock-out write are historically indistinguishable — same state, same id, `transition_reason` null on both. Migrating would relabel real worker choices as system transitions, irreversibly. |
| `pause_case_created` | **Leave alone** | Stale value, no member minted. 7 rows keep resolving through the soft-deleted anchor, which is what satisfies success criterion 5 by construction. |

**Select by `pause_other_task_priority` alone — never by `is_system_managed`, never by a set of
"system" rows.** One mislabelled row would widen the blast radius to real worker choices with no way
back. This is the single most important line in this prompt.

"Leave alone" is an assertion, not a note: prove both untouched populations have identical counts
before and after.

## The rehearsal is a deliverable, not preparation

The `.env` database (`postgresql+asyncpg://postgres:postgres@localhost:5433/beyo_manager`) is a
**dockerised exact copy of the current server database**, re-downloadable and replaceable. Use that
property:

1. Restore a fresh copy. **Record the restore point.**
2. Capture "before" labels **through the real read paths** for a sample of every row shape.
3. Run the migration.
4. Capture "after" labels the same way and diff them.
5. Run the zero-remaining-references query.
6. **Restore again and confirm the restored state matches the recorded restore point.**

Step 6 is what makes steps 2–5 mean anything. A rehearsal that cannot be repeated from a known state
is an anecdote. Record which restore each figure came from.

**Label parity must be captured through the real read paths, not from the migration's own mapping.**
Otherwise the test proves only that the migration agrees with itself.

**One qualification on every count:** the suite also runs against this database, so **globals carry
accumulated test residue while workspace-scoped figures reproduce.** Scope every count. Never size
the migration from a global.

## Carried forward from phase 2's close-out — these are yours

- **Criterion 11**: the `startswith(f"{PauseReason.CLIENT_ID_PREFIX}_")` branch in
  `domain/users/serializers.py` — remove it, or prove it dead with a test showing no input reaches
  it. This also closes the intention's success criterion 4, which phase 2 correctly recorded as
  *not yet met* rather than quietly counting itself against it.
- **`backfill_worker_shift_state_records.py`** shares the R14 mechanism and sat outside phase 2's
  named scope. Pick it up.
- **Phase 1's `image_url` premise is struck** as wrong — the icon is preserved in code. You do not
  own that consequence; do not re-derive it.

## Domain documentation

`docs/domains/worker_shifts/README.md` currently warns that `reason` is overloaded and that
**readers distinguish the two meanings by inspecting the id prefix**. If you discharge criterion 11,
that warning becomes **false** and must be rewritten or removed in this same change.

Domain docs state what is true now. No plan references, no phase numbers, no "previously", and
nothing about phase 4, which has not shipped.

## Hard constraints

- **`user_declared_state_records` is out of scope entirely.** Every row is a genuine worker choice
  with a `NOT NULL` catalog reference. Touching it is a defect, not a scope question.
- **`downgrade` restores the previous state, or the migration documents that it is irreversible and
  why.** An undocumented one-way migration is a finding. Precedent: an earlier feature set shipped
  migrations whose downgrades did not restore data, and that later blocked testing entirely.
- **Idempotent** — running it twice changes nothing the second time. Prove it.
- **Do not touch `manually_recorded` or the `changed_by_id` heuristic** (T7 — deferred).
- **Do not edit `docs/handoff/to_frontend/`.** Operator-owned; propose in the Review log.
- **Do not edit the archived declared_worker_states or phase 1/2 plans.**
- **T9 — commits.** Stage explicit paths; never `git add -A`. A parallel feature set
  (reassigned-steps endpoints) is live in this same tree and a broad add will capture it.

## Validation — three corrections learned the hard way

- **Run `git` from `backend/`, not from `ManagerBeyo-app/`.** The parent is not a repository;
  `backend/` and `frontend/` are separate ones. Two agents in this feature set concluded there was
  no repository at all and silently downgraded their verification. If `git rev-parse` fails, you are
  one level too high.
- **A baseline worktree needs all of `app/.env*` copied in.** `.gitignore` excludes them, and
  `.env.testing` alone cannot start the app — it defines no `JWT_SECRET_KEY`, and the suite reads
  `.env`. Smoke-test config parity in both trees before trusting any number.
- **Compare failure node sets at the same run index, and expect one latching node.** The DB and Redis
  are shared and not reset. Round 3 of phase 2 measured 26/1396 on run 1 and 27/1395 on runs 2 and
  3 — the extra being a shopify node that passes in isolation and sits outside the diff. A node that
  passes in isolation and lives outside your change is a measurement artefact: verify it, do not
  absorb it (T8).

## Definition of done

- All 10 acceptance criteria met with evidence.
- The rehearsal run end to end, including the final restore, with figures attributed to restores.
- Label parity proven through real read paths for every row shape.
- Both untouched populations proven unchanged by count.
- Idempotence proven; `upgrade`/`downgrade`/`upgrade` cycled, or irreversibility documented with
  reasoning.
- Zero rows referencing `pause_other_task_priority` afterwards; query recorded verbatim.
- Criterion 11 discharged; `backfill_worker_shift_state_records.py` handled;
  `docs/domains/worker_shifts/` true again.
- Full suite per the rules above; `ruff check` clean on touched files.
- Review log entry with volumes and the figure the batching decision came from. Then **STOP** — no
  summary, no archive, no phase-table flip, no handoff edit.
