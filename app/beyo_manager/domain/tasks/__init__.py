from beyo_manager.services.infra.audit.audited_events import register_audited_events


register_audited_events(
    {
        "task.customer_coordination.email_batch_enqueued",
    }
)
