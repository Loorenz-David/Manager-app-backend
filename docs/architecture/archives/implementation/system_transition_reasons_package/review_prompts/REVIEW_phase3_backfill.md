# Review prompt — System Transition Reasons, Phase 3: historical backfill

Independent adversarial review. Work from the repo files; assume no prior conversation.
Do not fix anything — report.

**This is the one irreversible phase in the set.** Phases 1, 2 and 4 can be reverted; this one
rewrites historical rows. Review it accordingly: the question is not only "does it work" but
"**what does it destroy if it is wrong, and would we know**".

## Before anything else

**Run `git` from `backend/`.** `ManagerBeyo-app/` is not a repository — `backend/` and `frontend/`
are separate ones. Two agents in this feature set ran it from the parent, concluded there was no
repository, and silently substituted weaker verification. If `git rev-parse` fails you are one level
too high. State in your entry whether you had history access.

## Inputs

- Plan: `.../system_transition_reasons/PLAN_system_transition_reasons_phase3_backfill_20260731.md`
- Implementer prompt: `.../codex_prompts/PROMPT_phase3_backfill.md`
- Master plan: decisions **T1–T9**, the **"Phase 1 inventory"**, and phase 2's carried-forward items
- Living domain docs: `docs/domains/worker_shifts/`

## The three populations — check the two that must NOT have moved first

| Rows pointing at | Expected |
|---|---|
| `pause_other_task_priority` | Migrated → `OTHER_TASK_PRIORITY`, `pause_reason_id = NULL` |
| `pause_ended_shift` | **Untouched** |
| `pause_case_created` | **Untouched** |

- [ ] **Verify the two untouched populations by count, before and after, yourself.** Do not accept
      the implementer's figures. This is the single highest-consequence check in the review: a
      migrated `pause_ended_shift` row is a real worker choice relabelled as a system transition,
      irreversibly and undetectably after the fact.
- [ ] **Read the migration's WHERE clause.** It must select `pause_other_task_priority` by identity —
      not by `is_system_managed`, not by a "system rows" set, not by slug pattern. Any predicate
      that could match a row someone later mislabels is a finding even if it happens to be correct
      today.
- [ ] `user_declared_state_records` is untouched. Every row there is a worker choice with a
      `NOT NULL` catalog reference.

## The rehearsal

- [ ] It was actually **run**, on a restored copy, with the **final restore performed** and the
      restored state confirmed against the recorded restore point. Without step 6 the rest is an
      anecdote — a rehearsal you cannot repeat from a known state proves nothing about the second
      run, which is the one that happens in production.
- [ ] Figures are attributed to which restore they came from.
- [ ] **Label parity was captured through the real read paths**, not from the migration's own
      mapping. If parity was computed from the same dict the migration applies, it proves only
      self-consistency. Re-derive parity for at least two row shapes yourself.
- [ ] Counts are **workspace-scoped**. The suite runs against this database, so globals carry test
      residue. A global count used to size the migration is a finding.

## The migration itself

- [ ] **Idempotent** — run it twice yourself; the second run changes nothing.
- [ ] `downgrade` restores the previous state, **or** irreversibility is documented with reasoning.
      An undocumented one-way migration is a finding.
- [ ] Zero rows reference `pause_other_task_priority` afterwards; the query is recorded verbatim and
      you can re-run it.
- [ ] Batching decision is justified by a recorded volume figure, not by preference.

## Carried forward from phase 2 — verify these were discharged, not dropped

- [ ] **Criterion 11**: the `startswith(CLIENT_ID_PREFIX)` branch in `domain/users/serializers.py`
      is gone, or provably dead with a test proving no input reaches it. This also closes the
      intention's success criterion 4 — confirm the intention was updated rather than left stale.
- [ ] **`backfill_worker_shift_state_records.py`** was picked up.
- [ ] Phase 1's `image_url` premise was **not** re-derived — it is struck as wrong and the icon lives
      in code.

## Domain documentation

- [ ] If criterion 11 was discharged, `docs/domains/worker_shifts/README.md`'s warning that readers
      distinguish `reason`'s meanings **by inspecting the id prefix** is now false and must have been
      rewritten or removed **in this same change**.
- [ ] Docs are *accurate*, not merely *edited* — spot-check two claims against code.
- [ ] No plan references, no phase numbers, no "previously", nothing about phase 4.

## Suite

- [ ] Failure **node sets** compared at the **same run index**, baseline worktree with all of
      `app/.env*` copied in (`.env.testing` alone cannot start the app — no `JWT_SECRET_KEY`).
- [ ] **Expect one latching node.** Phase 2 round 3 measured 26/1396 on run 1 and 27/1395 on runs 2
      and 3 — a shopify node that passes in isolation, outside the diff, and does not clear. A node
      matching that description is a measurement artefact, not a regression, and not the
      implementer's to absorb (T8). Do not raise it as a finding; do confirm it still matches that
      description.

## Adversarial probes

- Take a `pause_ended_shift` row and a `pause_case_created` row and prove each is byte-identical
  before and after.
- Construct a row that *would* match a sloppier predicate — e.g. another `is_system_managed` row, or
  a row in a second workspace — and confirm the migration leaves it alone.
- Run the migration against a restored copy, then run it again, then diff.
- **Do not probe "a reason hard-deleted since"** — it is unreachable. The FK is `ON DELETE RESTRICT`
  and raises. That probe was carried across earlier rounds as though it were reachable; it is not.

## Verdict

`APPROVED` or `NEEDS_CHANGES`, findings with file:line, violated criterion, severity. Record in the
plan's Review log — the only file you modify.

Two notes specific to this phase. First: **"the migration is correct" is not sufficient here — you
must also be satisfied that a mistake would have been caught.** If parity was self-referential, or
the untouched populations were verified only by the implementer's own query, say so even if the
outcome looks right. Second: a process lesson from phase 2 cost two rounds — a decision deferred
without an owner and a default gets skipped rather than decided. If this phase defers anything to
phase 4, check it names both.
