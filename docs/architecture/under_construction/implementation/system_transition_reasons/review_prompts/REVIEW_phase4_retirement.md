# Review prompt — System Transition Reasons, Phase 4: retirement & close-out

Independent adversarial review. Work from the repo files; assume no prior conversation.
Do not fix anything — report.

**Run `git` from `backend/`.** The parent is not a repository; `backend/` and `frontend/` are
separate ones. Two agents in this feature set ran it one level too high, concluded there was no
repository, and silently downgraded their verification.

This is the **final phase**, so the review has two jobs: the phase itself, and whether the feature
set actually closed. The second is the one most likely to be waved through.

## Inputs

- Plan: `.../system_transition_reasons/PLAN_system_transition_reasons_phase4_retirement_20260731.md`
- Implementer prompt: `.../codex_prompts/PROMPT_phase4_retirement.md`
- Master plan: **T1–T9**, "Phase 1 inventory", and phases 2–3 carried-forward items
- `architecture/30_migrations.md` — "Migration-owned bookkeeping tables"
- Living domain docs: `docs/domains/worker_shifts/`

## The two high-consequence checks — do these first

### 1. The check constraint

- [ ] **Compliance was proven by query BEFORE the constraint was added**, on real data, with the
      query and its result recorded. A constraint added first and validated by "the migration ran"
      is a failed deploy waiting for a workspace whose data differs.
- [ ] The constraint **actually constrains** — a deliberately violating row is rejected. Insert one
      yourself.
- [ ] **The documented exception is not rejected.** Mutual exclusion holds on `step_state_records`
      but **not** on the derived declared-state row, which carries `WORKER_DECLARED_STATE` *and* its
      catalog reference by design. Construct that row and confirm it inserts. A naive test seeds a
      step record and passes while this case is broken.

### 2. The journal

- [ ] Verified **intact before** the phase's other work, not after.
- [ ] Dropped **last**, after every other criterion passed.
- [ ] Row count recorded in the Review log.
- [ ] If it was missing and the phase proceeded anyway, that is **blocking** — the default was to
      keep it and stop.

Dropping the journal is what makes phase 3's backfill permanently irreversible. Treat a casual
account of it as a finding in itself.

## Retirement — verify what did NOT happen

| Row | Expected |
|---|---|
| `pause_other_task_priority` | Retired |
| `pause_ended_shift` | **Kept**, `is_system_managed` cleared, still visible and selectable |
| `pause_case_created` | **Untouched**, still soft-deleted |

- [ ] `pause_ended_shift` still appears in the worker-facing picker. **Assert against the actual
      endpoint response**, not a query — `list_pause_reasons` filters `is_deleted`, and that filter
      is the whole reason this row is kept.
- [ ] `pause_case_created` is byte-identical, and its 7 referencing rows are untouched.
- [ ] Entry condition was **re-run**, not inherited from phase 3's record.
- [ ] Non-zero references to the two kept rows were **not** treated as incomplete work.

## Subtraction

- [ ] `get_system_pause_reason_id` deleted, with its tests and its module if nothing else lives there.
- [ ] `is_system_managed` and every consumer removed — `guards.py`, the serializer field, the
      hardcoded `False` in `create_pause_reason.py`. **`can_delete_pause_reason` was delete
      protection**: confirm the implementer stated what replaces it rather than leaving it implied.
- [ ] `slug` and `uq_pause_reasons_slug` dropped. Phase 1's audit found a **frontend consumer** of
      `slug` and T6 was amended to keep the column — **verify which was actually agreed**, and that
      what shipped matches it. Getting this backwards breaks the worker app.
- [ ] Bootstrap seed phase and seed migration `49bd666da846` reconciled — both carry comments
      requiring the other to be updated in step. Inconsistency between them is a finding.
- [ ] **Second-workspace bootstrap succeeds** on a disposable database. Run it yourself.

## Close-out — the part most likely to be waved through

- [ ] **All six master-plan success criteria re-verified fresh**, not inherited. Spot-check two
      yourself, including criterion 1 (clock-out in a zero-catalog workspace).
- [ ] **Criterion 4 remains a PARTIAL completion** — closed on the provably-dead arm only, with
      clause (a) explicitly not satisfied. If this phase upgraded it to fully met, that is a finding:
      272 legacy strings still sit beside 58 `par_…` ids and nothing in this phase changed that.
- [ ] D3, D5, D14 carry their final amendment state in **this** master plan; the archived
      declared_worker_states plan is unedited.
- [ ] The intention is `achieved`, linked-plans table updated, open questions answered or explicitly
      closed.
- [ ] **Deferred items collected in one visible list** — T7's `manually_recorded` subsumption plus
      every T8 repo-health item across phases 1–4. Items living only in a phase Review log are lost
      once the phase archives. Check the list against the Review logs; anything missing is a finding.

## Scope and hygiene

- [ ] **`manually_recorded` and the `changed_by_id` heuristic untouched** (T7). This is the last
      phase and the temptation is highest here. Their improvement is a finding.
- [ ] Handoff unedited; any serializer contract change appears as a **proposal** in the Review log.
- [ ] `docs/domains/worker_shifts/` updated if anything became untrue — or an explicit statement that
      nothing did.
- [ ] T9: explicit paths, nothing from the parallel reassigned-steps workstream.

## Suite

- [ ] Node sets at the **same run index**, baseline worktree with all of `app/.env*`.
- [ ] **Expect one latching node** — a shopify test that passes in isolation, sits outside the diff,
      and does not clear. Confirm it still matches that description; do not raise it (T8).

## Probes

- Retire-then-read: is `pause_ended_shift` selectable through the real endpoint?
- A declared-state row against the new constraint.
- Two workspaces bootstrapped on a disposable database.
- Revert the constraint migration and confirm the compliance query still returns zero — if it does
  not, the data changed under it.
- **Do not probe "a reason hard-deleted since"** — unreachable, `ON DELETE RESTRICT` raises. That
  probe was carried across earlier rounds as though it were reachable.

## Verdict

`APPROVED` or `NEEDS_CHANGES`, findings with file:line, violated criterion, severity. Record in the
plan's Review log — the only file you modify.

Two notes. First: this phase was implemented by the operator, who also wrote the plan and this
prompt. **Weight that toward more scepticism, not less** — the usual independence between planning
and implementation is absent here, and the only remaining independent check is you. Second: if the
phase is clean, say so plainly. A feature set that ends with a manufactured finding is worse than
one that ends.
