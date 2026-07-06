import enum


class EmailProviderTypeEnum(str, enum.Enum):
    SMTP_IMAP = "smtp_imap"


class EmailConnectionStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    AUTH_FAILED = "auth_failed"
    ERROR = "error"


class EmailSecurityEnum(str, enum.Enum):
    SSL = "ssl"
    STARTTLS = "starttls"
    NONE = "none"


class EmailMessageDirectionEnum(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class EmailThreadEntityTypeEnum(str, enum.Enum):
    TASK = "task"
    TASK_CUSTOMER_COORDINATION = "task_customer_coordination"
    CASE = "case"
    CUSTOMER = "customer"


class EmailTemplateTopicEnum(str, enum.Enum):
    TASK = "task"
    TASK_CUSTOMER_COORDINATION = "task_customer_coordination"
    CASE = "case"
    CUSTOMER = "customer"


class EmailTemplateTypeEnum(str, enum.Enum):
    TXT = "txt"
    HTML = "html"
