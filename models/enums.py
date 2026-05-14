from enum import Enum


class SwipeEnum(str, Enum):
    RIGHT = "RIGHT"
    LEFT = "LEFT"
    UP = "UP"


class TierEnum(str, Enum):
    STRANGER = "STRANGER"
    ACQUAINTANCE = "ACQUAINTANCE"
    COLLEAGUE = "COLLEAGUE"
    TRUSTED_PARTNER = "TRUSTED_PARTNER"


class VisibilityEnum(str, Enum):
    PUBLIC = "PUBLIC"
    RESTRICTED = "RESTRICTED"
    HIDDEN = "HIDDEN"


class PlanEnum(str, Enum):
    FREE = "FREE"
    PREMIUM = "PREMIUM"


class IssueEnum(str, Enum):
    HALLUCINATION = "HALLUCINATION"
    LATENCY = "LATENCY"
    UNRESPONSIVE = "UNRESPONSIVE"
    UNAUTHORIZED = "UNAUTHORIZED"
