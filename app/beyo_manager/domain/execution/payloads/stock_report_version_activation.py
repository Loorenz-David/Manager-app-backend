from dataclasses import dataclass


@dataclass(frozen=True)
class StockReportVersionActivationPayload:
    """The delayed-scheduler payload of a scheduled draft activation (stock-report
    draft versions, plan §5.1). It is **not** a copy of the draft: the draft is
    read from the tables at fire time, so every edit made to a scheduled draft is
    what gets published. `scheduled_for` is the UTC ISO form of the draft's
    `scheduled_activation_at` when the row was created; the activation compares it,
    as a datetime, with the stored column to recognise a moved or cleared schedule
    (P-5, Q-5)."""

    workspace_id: str
    version_id: str
    scheduled_by_user_id: str | None
    scheduled_for: str
