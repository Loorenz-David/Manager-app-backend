# ARCHIVE_RECORD_PLAN_email_idle_watcher_20260706

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_email_idle_watcher_20260706`
- Archived at (UTC): `2026-07-06T08:25:48Z`
- Archive owner agent: `codex`

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_email_idle_watcher_20260706.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_email_idle_watcher_20260706.md`
- Debug chain (optional): none

## Outcome classification

- Result: `completed`
- Acceptance criteria met: `partially validated`

## Final notes

- The backend now has a dedicated IMAP IDLE watcher process that can own active email connections by deterministic shard, debounce mailbox-change signals, and enqueue the existing `EMAIL_INBOX_SYNC` task contract without frontend polling.
- Exact-new-message notification routing is now part of the inbox sync transaction: only newly-inserted inbound `EmailMessage` rows create `CREATE_NOTIFICATIONS` tasks, which preserves notification idempotency and keeps socket/VAPID delivery in the existing notification pipeline.
- The implementation plan’s linked intention file does not exist in the repo, so that lifecycle backlink could not be updated during archive.

## Follow-up links

- Next plan (optional): `backend/docs/architecture/under_construction/implementation/PLAN_offload_blocking_imap_smtp_20260706.md`
- Related handoff (optional): none
