from __future__ import annotations
from enum import Enum


class AnalysisStatus(str, Enum):
    INIT = "init"
    PENDING = "pending"
    ANALYZED = "analyzed"
    SCREENING_FAILED = "screening_failed"
    COMMENTS_FAILED = "comments_failed"
    ANALYSIS_FAILED = "analysis_failed"


class RelevantStatus(str, Enum):
    UNKNOWN = "unknown"
    NO = "no"
    YES = "yes"
    MAYBE = "maybe"




class Channel(str, Enum):
    DOUYIN = "douyin"
    XIAOHONGSHU = "xiaohongshu"



class PromptName(str, Enum):
    PRELIMINARY_SCREENING = "PRELIMINARY_SCREENING"
    ANALYZE_VIDEO = "ANALYZE_VIDEO"
    ANALYZE_PICTURE = "ANALYZE_PICTURE"


class PostType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"


__all__ = [
    "AnalysisStatus",
    "RelevantStatus",
    "Channel",
    "PromptName",
    "PostType",
]

