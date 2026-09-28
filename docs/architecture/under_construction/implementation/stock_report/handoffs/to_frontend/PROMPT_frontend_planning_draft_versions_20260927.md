# Prompt — frontend implementation plan for stock report draft versions

> Pass this file, together with `HANDOFF_TO_FRONTEND_stock_report_snapshots_v7_20260927.md` and the
> owner's frontend intention, to the frontend agent. Date: 2026-09-27.

## Your job

Write the **frontend implementation plan** for the stock report's draft-versions capability. Use two inputs:

1. **The owner's frontend intention.** It is the authority on *what the app should let people do and see*.
2. **The v7 handoff.** It is the authority on *what the backend offers*: routes, shapes, roles, errors, events.

**Plan only. Do not implement anything yet.** The backend has not been built either. Both sides wait until
your plan is ready, because any gap you find is still cheap to fix now, in both plans and the contract.

## How to treat v7

- **Treat v7 as already implemented.** Plan against it exactly as written: paths, field names, nullability,
  error identities, event names and `extra` keys. Do not assume behaviour v7 does not state.
- **Do not edit v7.** If something in it is wrong, missing or unclear, report it (below). Corrections come
  back as a new dated handoff.
- v6 describes what the server does **today**. v7 describes what it will do. Where they differ, plan for v7.

## Must be in your plan (v7 §0.1)

These fix real defects. Today's `packages/stock-report/src/socket-events.ts` (`applySnapshotUpdate`) applies
`stock_report_item_snapshot:updated` to the board by row id and ignores `version_id`, so draft edits would
repaint the live board.

1. Apply `stock_report_item_snapshot:updated` only to views of `extra.version_id`.
2. On `stock_report_snapshot_version:activated`, refetch the board, the active version, the versions list and
   the missing summary. On `:refreshed`, refetch that version's views. On `:updated` and `:deleted`, refetch
   the versions list.
3. Handle `active_at: null` (drafts) everywhere a version or snapshot is rendered. Read `state` rather than
   deriving it from the two dates.
4. `GET …/snapshots/versions` now returns drafts first. Use `state=` wherever a screen wants only history.
5. Manual activation ignores the draft's stored refresh choice. Send `refresh_quantity_requested` explicitly.
6. Show a draft whose `scheduled_activation_at` is in the past as **overdue** (v7 §5.21).

Gate the UI by role exactly as v7 states:
- admin and manager: create, activate, refresh, edit title and schedule, delete drafts;
- admin, manager and seller: reorder, inside any open version;
- admin, manager and worker: mark missing, inside any open version;
- every role: read drafts.

## When the intention needs something v7 does not offer

This is expected. Owner intentions often reach past what the backend supports.

- **Do not work around it silently.** No client-side emulation of missing backend behaviour, no chaining of
  calls to fake a missing route, no guessed fields. Any of these becomes a hidden contract the backend does
  not know about.
- **Record it as a backend gap** (format below), plan everything else, and mark the plan steps that depend on
  the gap as **blocked on gap G-n**.
- If v7 can already cover the need, perhaps less conveniently, say so in the gap entry. The owner may prefer
  that to a backend change.

## Output

Two files, both in the frontend repo's docs folder for this work:

1. **The implementation plan**, which must cite the v7 section (for example "v7 §5.17") for every backend
   interaction it relies on. When a corrected handoff arrives later, it then shows exactly which steps are
   affected.
2. **`BACKEND_GAPS_draft_versions_<date>.md`**, which the owner carries back to the backend. Use one entry per
   gap, in this exact shape:

```markdown
### G-1 — <short name>

- **What the user needs:** <the screen, the action, the lived scenario, from the intention>
- **Why v7 does not cover it:** <the v7 section, and what is missing, wrong or ambiguous>
- **Proposed backend shape:** <route + method, query params, request body, response JSON, event(s), roles,
  error identities; be concrete, it is a proposal the backend will check against its code>
- **Can v7 do it another way?** <yes: how, and the cost to the user | no>
- **Blocks:** <which plan steps; can the rest of the frontend proceed without it?>
```

Keep **questions** (v7 is unclear, or two sections seem to disagree) in a separate section of the same file,
headed `## Questions about v7`. They are not gaps: the answer may be "v7 already says X".

If you find no gaps, the file still exists and says so in one line. That is a claim the owner will check
against the intention, so keep the file.

## Known open item (does not change any shape)

The backend has one owner decision still open: which scheduled draft wins when several are due at the same
time, or when a manager already activated a board by hand. Either way the frontend sees the same events and
fields. Refetching the versions list on `stock_report_snapshot_version:updated` renders both outcomes
correctly. Do not plan around it further.
