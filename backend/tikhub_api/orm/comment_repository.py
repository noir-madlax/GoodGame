from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime

from .supabase_client import get_client
from .models import PlatformComment

TABLE = "gg_platform_post_comments"


class CommentRepository:
    """CRUD(light) for gg_platform_post_comments: add and query only."""

    @staticmethod
    def upsert_comment(comment: PlatformComment) -> PlatformComment:
        """Upsert a comment by (platform, platform_comment_id) unique constraint.
        Returns the stored row.
        支持两种输入：
        - PlatformComment 实例：严格校验、完整 upsert
        - dict（部分字段补丁）：用于二次修正 parent_comment_id 等，仅更新提供的字段
        """
        client = get_client()

        # 如果传入的是补丁 dict，直接 upsert（不经 Pydantic 强校验）
        if isinstance(comment, dict):  # type: ignore
            payload: Dict[str, Any] = {k: v for k, v in comment.items() if v is not None}
            # 规范化时间字段
            if isinstance(payload.get("published_at"), datetime):
                payload["published_at"] = payload["published_at"].isoformat()
            # id=None 移除，避免插入路径冲突
            if payload.get("id") is None:
                payload.pop("id", None)
            resp = client.table(TABLE).upsert(payload, on_conflict="platform,platform_comment_id").execute()
            data = resp.data[0] if resp.data else None
            return CommentRepository._row_to_model(data) if data else PlatformComment()

        # 否则按完整对象处理
        model = comment  # type: ignore[assignment]

        # Pydantic v2 preferred
        if hasattr(model, "model_dump"):
            payload: Dict[str, Any] = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        else:
            payload = model.dict()
            if isinstance(payload.get("published_at"), datetime):
                payload["published_at"] = payload["published_at"].isoformat()

        if payload.get("id") is None:
            payload.pop("id", None)
        resp = client.table(TABLE).upsert(payload, on_conflict="platform,platform_comment_id").execute()
        data = resp.data[0] if resp.data else None
        return CommentRepository._row_to_model(data) if data else model

    @staticmethod
    def get_by_platform_comment(platform: str, platform_comment_id: str) -> Optional[PlatformComment]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("platform", platform)
            .eq("platform_comment_id", platform_comment_id)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return CommentRepository._row_to_model(row) if row else None

    @staticmethod
    def list_by_post(post_id: int, limit: int = 100, offset: int = 0) -> List[PlatformComment]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("post_id", post_id)
            .order("published_at", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [CommentRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def list_replies(parent_comment_id: int, limit: int = 100, offset: int = 0) -> List[PlatformComment]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("parent_comment_id", parent_comment_id)
            .order("published_at", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [CommentRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def update_parent_link(platform: str, platform_comment_id: str, parent_comment_id: int,
                           parent_platform_comment_id: str, post_id: int) -> Optional[PlatformComment]:
        """仅更新父子关联字段，避免触碰 content 等非空字段。"""
        client = get_client()
        payload: Dict[str, Any] = {
            "parent_comment_id": parent_comment_id,
            "parent_platform_comment_id": parent_platform_comment_id,
        }
        resp = (
            client.table(TABLE)
            .update(payload)
            .eq("platform", platform)
            .eq("platform_comment_id", platform_comment_id)
            .eq("post_id", post_id)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return CommentRepository._row_to_model(row) if row else None

    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> PlatformComment:
        if not row:
            return PlatformComment()
        return PlatformComment(
            id=row.get("id"),
            post_id=row.get("post_id"),
            platform=row.get("platform", ""),
            platform_comment_id=row.get("platform_comment_id", ""),
            parent_comment_id=row.get("parent_comment_id"),
            parent_platform_comment_id=row.get("parent_platform_comment_id"),
            author_id=row.get("author_id"),
            author_name=row.get("author_name"),
            author_avatar_url=row.get("author_avatar_url"),
            content=row.get("content", ""),
            like_count=row.get("like_count", 0),
            reply_count=row.get("reply_count", 0),
            published_at=_parse_dt(row.get("published_at")),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
        )


def _parse_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        return None

