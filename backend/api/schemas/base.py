from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class BaseRequest(BaseModel):
    """
    统一的请求基础模型。
    - trace_id: 链路追踪ID（可从请求头 X-Request-Id / X-Trace-Id 注入）
    - user_id: 业务侧可选的用户标识
    - client_ip: 客户端 IP（可由依赖/中间件注入）
    - meta: 预留元信息扩展位
    """

    model_config = ConfigDict(extra="ignore")

    trace_id: Optional[str] = Field(default=None, description="链路追踪ID")
    user_id: Optional[str] = Field(default=None, description="用户标识")
    client_ip: Optional[str] = Field(default=None, description="客户端IP")
    meta: dict[str, Any] = Field(default_factory=dict, description="扩展元信息")


class Pagination(BaseModel):
    """通用分页入参"""

    model_config = ConfigDict(extra="ignore")

    page: int = Field(1, ge=1, description="页码，从1开始")
    size: int = Field(10, ge=1, le=200, description="每页大小")


class PageMeta(BaseModel):
    """分页元信息"""

    page: int
    size: int
    total: int


class BaseResponse(BaseModel, Generic[T]):
    """
    统一的响应基础模型。
    - code: 业务状态码；0 表示成功，非0表示失败
    - message: 人类可读的信息
    - success: 是否成功（由 code 推导但冗余存储，便于前端直读）
    - data: 数据载体（泛型）
    - trace_id: 链路ID
    - timestamp: ISO8601 时间戳（UTC）
    """

    code: int = Field(0, description="业务状态码；0 为成功")
    message: str = Field("OK", description="描述信息")
    success: bool = Field(True, description="是否成功")
    data: Optional[T] = Field(default=None, description="业务数据")
    trace_id: Optional[str] = Field(default=None, description="链路追踪ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="响应时间（UTC ISO8601）",
    )

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "OK", trace_id: Optional[str] = None) -> "BaseResponse[T]":
        return cls(code=0, message=message, success=True, data=data, trace_id=trace_id)

    @classmethod
    def fail(
        cls, code: int = 1, message: str = "ERROR", *, trace_id: Optional[str] = None, data: Optional[T] = None
    ) -> "BaseResponse[T]":
        if code == 0:
            code = 1
        return cls(code=code, message=message, success=False, data=data, trace_id=trace_id)


class PageResponse(BaseModel, Generic[T]):
    """统一的分页响应模型"""

    code: int = 0
    message: str = "OK"
    success: bool = True
    data: List[T] = Field(default_factory=list, description="数据列表")
    meta: PageMeta = Field(..., description="分页信息")
    trace_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def of(
        cls,
        items: List[T],
        *,
        page: int,
        size: int,
        total: int,
        message: str = "OK",
        trace_id: Optional[str] = None,
    ) -> "PageResponse[T]":
        return cls(
            code=0,
            message=message,
            success=True,
            data=items,
            meta=PageMeta(page=page, size=size, total=total),
            trace_id=trace_id,
        )

