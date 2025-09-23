from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from .base import BaseRequest, BaseResponse  # re-exported by package for typing in router
from tikhub_api.orm.enums import Channel


class ImportAnalyzeRequest(BaseRequest):
    """/api/import/analyze 入参"""

    # 为 Swagger 文档提供默认示例
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "project_id": "657ec0d1-ad78-4610-aa4e-34123714800a",
                "url": "https://www.douyin.com/video/7550247003771473152",
                "trace_id": "2c3b0c7d-d1a0-4b68-9e31-4a9b60b75977",
                "user_id": "",
                "client_ip": "",
                "meta": {}
            }
        },
    )

    project_id: str = Field(..., min_length=1, description="项目ID (UUID)")
    url: str = Field(..., min_length=1, description="待分析 URL")


class ImportAnalyzeResult(BaseModel):
    """/api/import/analyze 出参数据体（包在 BaseResponse.data 中）"""

    recognized: bool = Field(False, description="是否成功识别平台与帖子ID")
    platform: Optional[Channel] = Field(None, description="平台：Channel 枚举")
    platform_item_id: Optional[str] = Field(None, description="平台帖子/视频ID：aweme_id/note_id")
    post_id: Optional[int] = Field(None, description="数据库ID（upsert 后）")

    # 便于前端展示的部分字段（存在则返回）
    title: Optional[str] = None
    post_type: Optional[str] = None
    original_url: Optional[str] = None
    cover_url: Optional[str] = None
    video_url: Optional[str] = None

    # 失败时的人类可读原因
    raw_reason: Optional[str] = None

