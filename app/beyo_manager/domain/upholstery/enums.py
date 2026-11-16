import enum


class UpholsteryCurrencyEnum(enum.Enum):
    SWEDISH_KRONA = "swedish_krona"
    DANISH_KRONA = "danish_krona"
    EURO = "euro"


class UpholsteryInventoryConditionEnum(enum.Enum):
    AVAILABLE = "available"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"


class UpholsteryOrderStateEnum(enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    ORDERED = "ordered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"


class UpholsteryExternalProviderEnum(enum.Enum):
    NEVOTEX = "nevotex"
    OHLSSONS_TYGER = "ohlssons_tyger"
    FARGOTEX = "fargotex"
    SELFMADE = "selfmade"


class InventoryMovementTypeEnum(enum.Enum):
    """What happened to an upholstery inventory — one value per ledger row kind.

    Persisted as the Postgres enum ``upholstery_inventory_movement_type_enum``; adding a
    value needs ``ALTER TYPE ... ADD VALUE``. Reconstructed (backfilled) rows reuse these
    values and are told apart by ``is_reconstructed``.
    """

    OPENING_BALANCE = "opening_balance"
    INVENTORY_CREATED = "inventory_created"
    NEED_ADDED = "need_added"
    NEED_ADJUSTED = "need_adjusted"
    RESERVED_FOR_USE = "reserved_for_use"
    USE_FINISHED = "use_finished"
    USED_DIRECT = "used_direct"
    USE_ROLLED_BACK = "use_rolled_back"
    ORDER_PLACED = "order_placed"
    ORDER_RECEIVED = "order_received"
    ORDER_AMOUNT_CHANGED = "order_amount_changed"
    SURPLUS_ADDED = "surplus_added"
    STORED_SET = "stored_set"
    ALLOCATION_RUN = "allocation_run"
    REQUIREMENT_STATE_CHANGED = "requirement_state_changed"


class InventoryMovementTriggerEnum(enum.Enum):
    """Which command / origin caused a ledger row.

    Stored as a plain string column (not a Postgres enum) so a new origin never needs a
    migration. ``movement_type`` says *what* moved; ``trigger`` says *why*.
    """

    # item upholstery / requirement commands
    ITEM_UPHOLSTERY_SET = "item_upholstery_set"
    REQUIREMENT_QUANTITY_CHANGED = "requirement_quantity_changed"
    UPHOLSTERY_SWAPPED = "upholstery_swapped"
    ITEM_UPHOLSTERY_DELETED = "item_upholstery_deleted"
    REQUIREMENT_MARKED_IN_USE = "requirement_marked_in_use"
    REQUIREMENT_MARKED_COMPLETED = "requirement_marked_completed"
    REQUIREMENT_COMPLETED_SINGLE = "requirement_completed_single"
    SURPLUS_APPLIED = "surplus_applied"
    # task / step lifecycle
    TASK_CREATED = "task_created"
    TASK_RESTORED = "task_restored"
    TASK_DELETED = "task_deleted"
    STEP_TRANSITION = "step_transition"
    TASK_FORCED_READY = "task_forced_ready"
    TASK_FINISHED = "task_finished"
    # ordering / manual inventory edits
    ORDER_CREATED = "order_created"
    ORDER_RECEIVED = "order_received"
    ORDER_AMOUNT_CHANGED = "order_amount_changed"
    MANUAL_ADD_ORDERED = "manual_add_ordered"
    MANUAL_CONFIRM_ORDERED = "manual_confirm_ordered"
    MANUAL_STORED_SET = "manual_stored_set"
    # state-only allocation commands
    REQUIREMENTS_MARKED_ORDERED = "requirements_marked_ordered"
    REQUIREMENTS_RESOLVED_AFTER_STOCK = "requirements_resolved_after_stock"
    STOCK_REALLOCATED = "stock_reallocated"
    # creation / system
    INVENTORY_CREATED = "inventory_created"
    UPHOLSTERY_CREATED = "upholstery_created"
    MIGRATION_BASELINE = "migration_baseline"
    RECONSTRUCTED = "reconstructed"
    MAINTENANCE_SCRIPT = "maintenance_script"
