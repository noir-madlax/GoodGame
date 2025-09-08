from __future__ import annotations
from typing import Optional, Dict, Any, Literal
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, constr
from pydantic import field_validator


# Pydantic models with validation constraints

NonEmptyStr = constr(strip_whitespace=True, min_length=1)


class PlatformPost(BaseModel):
    id: Optional[int] = Field(default=None, ge=1)

    platform: NonEmptyStr
    platform_item_id: NonEmptyStr

    title: NonEmptyStr
    content: Optional[str] = None

    # 新增：帖子类型/原始链接/作者信息/转发数/时长（毫秒）
    post_type: str = Field(default="video")
    original_url: Optional[HttpUrl] = None
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    share_count: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)

    play_count: int = Field(default=0, ge=0)
    like_count: int = Field(default=0, ge=0)
    comment_count: int = Field(default=0, ge=0)

    cover_url: Optional[HttpUrl] = None
    video_url: Optional[HttpUrl] = None

    # 分析状态（方案二：TEXT + CHECK）。DB 默认 'init'。
    analysis_status: Literal['init', 'no_value', 'pending', 'analyzed'] = Field(
        default="init",
        description="分析状态：init=初始化, no_value=没有分析价值, pending=待分析, analyzed=已分析",
    )

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
