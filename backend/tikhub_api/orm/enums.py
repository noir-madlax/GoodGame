from __future__ import annotations
from enum import Enum


class AnalysisStatus(str, Enum):
    INIT = "init"
    NO_VALUE = "no_value"
    PENDING = "pending"
    ANALYZED = "analyzed"


class RelevantStatus(str, Enum):
    UNKNOWN = "unknown"
    NO = "no"
    YES = "yes"
    MAYBE = "maybe"


__all__ = [
    "AnalysisStatus",
    "RelevantStatus",
]

