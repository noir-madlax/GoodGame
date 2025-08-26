from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime

from .supabase_client import get_client
from .models import PlatformPost

TABLE = "gg_platform_post"


class PostRepository:
    """CRUD(light) for gg_platform_post: add and query only."""

    @staticmethod
    def upsert_post(post: PlatformPost) -> PlatformPost:
        """Upsert a post by (platform, platform_item_id) unique constraint.
        Returns the stored row.
        """
        client = get_client()
        # validate using Pydantic, and produce JSON-serializable dict for DB
        model = post if isinstance(post, PlatformPost) else PlatformPost(**post)  # type: ignore[arg-type]

        payload: Dict[str, Any] = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]

        # remove id if None to avoid conflict on upsert
        if payload.get("id") is None:
            payload.pop("id", None)

        # Upsert on the unique constraint (platform, platform_item_id)
        # 需要显式声明 on_conflict，才能命中该唯一索引而非按主键冲突
        resp = client.table(TABLE).upsert(payload, on_conflict="platform,platform_item_id").execute()
        data = resp.data[0] if resp.data else None
        return PostRepository._row_to_model(data) if data else model

    @staticmethod
    def get_by_platform_item(platform: str, platform_item_id: str) -> Optional[PlatformPost]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("platform", platform)
            .eq("platform_item_id", platform_item_id)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return PostRepository._row_to_model(row) if row else None

    @staticmethod
    def list_by_platform(platform: str, limit: int = 50, offset: int = 0) -> List[PlatformPost]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("platform", platform)
            .order("published_at", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [PostRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> PlatformPost:
        if not row:
            return PlatformPost()
        return PlatformPost(
            id=row.get("id"),
            platform=row.get("platform", ""),
            platform_item_id=row.get("platform_item_id", ""),
            title=row.get("title", ""),
            content=row.get("content"),
            # 新增字段映射（若列暂不存在，Pydantic 使用默认值）
            post_type=row.get("post_type", "video"),
            original_url=row.get("original_url"),
            author_id=row.get("author_id"),
            author_name=row.get("author_name"),
            share_count=row.get("share_count", 0),
            duration_ms=row.get("duration_ms", 0),
            play_count=row.get("play_count", 0),
            like_count=row.get("like_count", 0),
            comment_count=row.get("comment_count", 0),
            cover_url=row.get("cover_url"),
            video_url=row.get("video_url"),
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

