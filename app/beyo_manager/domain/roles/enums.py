from enum import StrEnum


class RoleNameEnum(StrEnum):
    ADMIN = "admin"
    WORKER = "worker"
    MANAGER = "manager"
    SELLER = "seller"
