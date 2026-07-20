import enum


class ConnecteamEventTypeEnum(str, enum.Enum):
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"
    AUTO_CLOCK_OUT = "auto_clock_out"


class ConnecteamActivityTypeEnum(str, enum.Enum):
    SHIFT = "shift"
    MANUAL_BREAK = "manual_break"
    UNKNOWN = "unknown"


class ConnecteamIntakeOutcomeEnum(str, enum.Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    IGNORED_ACTIVITY_TYPE = "ignored_activity_type"
    UNSUPPORTED_EVENT_TYPE = "unsupported_event_type"


class ConnecteamProcessingOutcomeEnum(str, enum.Enum):
    PROCESSED = "processed"
    CLOCK_IN_APPLIED = "clock_in_applied"
    CLOCK_OUT_APPLIED = "clock_out_applied"
    ALREADY_CLOCKED_IN = "already_clocked_in"
    NO_OPEN_SHIFT = "no_open_shift"
    WORKER_NOT_MAPPED = "worker_not_mapped"
    AMBIGUOUS_MAPPING = "ambiguous_mapping"
    IGNORED_ACTIVITY_TYPE = "ignored_activity_type"


class ConnecteamUserMappingStatusEnum(str, enum.Enum):
    PROPOSED = "proposed"
    UPDATED = "updated"
    ALREADY_MAPPED_SAME_ID = "already_mapped_same_id"
    EXISTING_DIFFERENT_CONNECTEAM_ID = "existing_different_connecteam_id"
    EXTERNAL_USER_UNMATCHED = "external_user_unmatched"
    WORK_PROFILE_NOT_FOUND = "work_profile_not_found"
    WORK_PROFILE_AMBIGUOUS = "work_profile_ambiguous"
    DUPLICATE_EXTERNAL_FULL_NAME = "duplicate_external_full_name"
    CONNECTEAM_ID_ALREADY_ASSIGNED = "connecteam_id_already_assigned"
    INVALID_EXTERNAL_NAME = "invalid_external_name"
