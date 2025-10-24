from __future__ import annotations
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, constr
from pydantic import field_validator
from .enums import AnalysisStatus, RelevantStatus, PostType, Channel, AuthorFetchStatus


# Pydantic models with validation constraints

NonEmptyStr = constr(strip_whitespace=True, min_length=1)


class PlatformPost(BaseModel):
    id: Optional[int] = Field(default=None, ge=1)
    project_id: Optional[str] = None

    platform: NonEmptyStr
    platform_item_id: NonEmptyStr

    title: NonEmptyStr
    content: Optional[str] = None

    # 新增：帖子类型/原始链接/作者信息/转发数/时长（毫秒）
    post_type: PostType = Field(default=PostType.VIDEO)
    original_url: Optional[HttpUrl] = None
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    share_count: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)

    play_count: int = Field(default=0, ge=0)
    like_count: int = Field(default=0, ge=0)
    comment_count: int = Field(default=0, ge=0)

    cover_url: Optional[HttpUrl] = None
    video_url: Optional[List[HttpUrl]] = None
    image_urls: Optional[List[HttpUrl]] = None  # 图文笔记的图片地址列表

    # 分析状态（TEXT + CHECK）。DB 默认 'init'。建议使用枚举 AnalysisStatus 来引用。
    analysis_status: AnalysisStatus = Field(
        default=AnalysisStatus.INIT,
        description="分析状态：init=初始化, pending=待分析, analyzed=已分析",
    )

    # 相关性状态（TEXT + CHECK）。DB 默认 'unknown'。建议使用枚举 RelevantStatus 来引用。
    relevant_status: RelevantStatus = Field(
        default=RelevantStatus.UNKNOWN,
        description="相关性状态：unknown=未知, no=不相关, yes=相关, maybe=可能相关",
    )

    # 作者信息获取状态（TEXT + CHECK）。DB 默认 'not_fetched'。
    author_fetch_status: AuthorFetchStatus = Field(
        default=AuthorFetchStatus.NOT_FETCHED,
        description="作者信息获取状态：not_fetched=未获取, success=获取成功, failed=获取失败",
    )

    # LLM/规则判定的详细结果（JSON 存档，形态不固定：可能为 dict/list/str），使用 Any 以兼容
    relevant_result: Optional[Any] = None
    is_marked: bool = False

    # 存储 get_video_details 返回的原始报文，便于排查
    raw_details: Optional[Dict[str, Any]] = None


    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("title", mode="before")
    def title_trim(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class PlatformComment(BaseModel):
    id: Optional[int] = Field(default=None, ge=1)

    post_id: int = Field(..., ge=1)

    platform: NonEmptyStr
    platform_comment_id: NonEmptyStr

    parent_comment_id: Optional[int] = Field(default=None, ge=1)
    parent_platform_comment_id: Optional[str] = None

    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_avatar_url: Optional[HttpUrl] = None

    content: NonEmptyStr

    like_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)

    floor: int = Field(default=0, ge=0)

    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None




class MerchantBrand(BaseModel):
    id: Optional[int] = Field(default=None, ge=1)
    name: NonEmptyStr
    created_at: Optional[datetime] = None
    is_valid: bool = True



class SearchKeyword(BaseModel):
    id: Optional[int] = Field(default=None, ge=1)
    keyword: NonEmptyStr
    created_at: Optional[datetime] = None



class VideoAnalysis(BaseModel):
    id: Optional[int] = Field(default=None, ge=1)

    project_id: NonEmptyStr
    source_path: NonEmptyStr
    source_platform: str = Field(default="douyin")

    summary: NonEmptyStr
    sentiment: NonEmptyStr
    brand: Optional[str] = None

    # JSONB 列：形态未固定，使用 Any 以兼容 dict/list 等
    timeline: Any
    key_points: Any
    risk_types: Any

    # 总体风险等级：high/medium/low
    total_risk: Optional[Literal["high", "medium", "low","低","中","高"]] = Field(
        default=None,
        description="整篇内容的严重性：high/medium/low",
    )
    # 风险等级判定理由（简洁、可复核）
    total_risk_reason: Optional[str] = None

    created_at: Optional[datetime] = None

    platform_item_id: Optional[str] = None
    analysis_detail: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None

    post_id: Optional[int] = Field(default=None, ge=1)
    brand_relevance: Optional[str] = None
    relevance_evidence: Optional[str] = None
    transcript_json: Optional[Dict[str, Any]] = None
    handling_suggestions: Optional[Dict[str, Any]] = None



class PromptTemplate(BaseModel):
    id: Optional[str] = None
    name: NonEmptyStr
    description: Optional[str] = None
    notes: Optional[str] = None
    version: Optional[str] = None
    method_name: Optional[str] = None
    is_active: bool = False
    content: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None



class PromptVariable(BaseModel):
    id: Optional[int] = Field(default=None, ge=1)
    project_id: NonEmptyStr
    variable_name: NonEmptyStr
    variable_description: Optional[str] = None
    variable_value: Optional[Any] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None



class ProjectSettings(BaseModel):
    id: Optional[str] = None  # uuid
    project_name: NonEmptyStr
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: Optional[str] = None
    nav_overview_enabled: bool = False
    nav_mark_process_enabled: bool = False
    nav_search_settings_enabled: bool = False
    nav_analysis_rules_enabled: bool = False
    nav_alert_push_enabled: bool = False


class Author(BaseModel):
    """作者信息模型，对应 gg_authors 表"""
    id: Optional[int] = Field(default=None, ge=1)
    platform: Channel
    platform_author_id: NonEmptyStr
    sec_uid: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    share_url: Optional[HttpUrl] = None
    follower_count: int = Field(default=0, ge=0)
    signature: Optional[str] = None
    location: Optional[str] = None
    account_cert_info: Optional[str] = None
    verification_type: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None
    user_deleted: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SearchResponseLog(BaseModel):
    """搜索响应日志模型，对应 gg_search_response_logs 表"""
    id: Optional[int] = Field(default=None, ge=1)
    project_id: NonEmptyStr
    keyword: NonEmptyStr
    platform: str = Field(default="douyin")
    page_number: int = Field(default=1, ge=1)
    batch_id: Optional[str] = None  # 批次号，标识一次定时任务执行

    # JSONB 字段
    request_params: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None

    # 元数据
    request_timestamp: Optional[datetime] = None
    response_status: Optional[str] = None
    error_message: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
