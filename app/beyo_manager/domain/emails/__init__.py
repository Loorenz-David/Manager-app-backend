from beyo_manager.services.infra.audit.audited_events import register_audited_events


register_audited_events(
    {
        "email.send_enqueued",
        "email.batch_send_enqueued",
        "email.reply_enqueued",
        "email.delivery_completed",
        "email.threads.sync_targeted_enqueued",
        "email.threads.sync_targeted_batch",
    }
)
