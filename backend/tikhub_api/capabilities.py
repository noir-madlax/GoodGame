from __future__ import annotations
from typing import Protocol, Optional, Dict, Any, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from .orm.models import PlatformPost


@runtime_checkable
class DanmakuProvider(Protocol):
    """提供弹幕获取能力的协议接口。由支持弹幕的平台实现。"""

    def fetch_video_danmaku(self, video_id: str, duration: int, start_time: int = 0,
                             end_time: Optional[int] = None) -> Dict[str, Any]:
        """获取弹幕的原始 API 响应。"""
        ...

    def get_video_danmaku(self, video_id: str, duration: int, start_time: int = 0,
                           end_time: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """获取弹幕数据（便捷方法，返回 data 字段）。"""
        ...


@runtime_checkable
class VideoPostProvider(Protocol):
    """提供标准化视频贴子领域模型的能力（便于落库）。"""

    def get_video_post(self, video_id: str) -> Optional[PlatformPost]:
        ...


@runtime_checkable
class VideoDurationProvider(Protocol):
    """提供获取视频时长（毫秒）的能力。"""

    def get_video_duration_ms(self, video_id: str) -> Optional[int]:
        ...


@runtime_checkable
class CommentsProvider(Protocol):
    """提供评论分页获取能力的协议接口。"""

    def fetch_video_comments_page(self, video_id: str, cursor: int = 0, count: int = 20) -> Dict[str, Any]:
        """获取评论分页原始响应（顶层评论）。"""
        ...

    def get_video_comments(self, video_id: str, cursor: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """便捷方法，返回 data 字段（含 comments, cursor, has_more）。"""
        ...

    # 评论回复（楼中楼）
    def fetch_video_comment_replies_page(self, item_id: str, comment_id: str, cursor: int = 0, count: int = 20) -> Dict[str, Any]:
        """获取某个顶层评论的回复分页原始响应。"""
        ...

    def get_video_comment_replies(self, item_id: str, comment_id: str, cursor: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """便捷方法，返回 data 字段（含 comments, cursor, has_more, total）。"""
        ...

