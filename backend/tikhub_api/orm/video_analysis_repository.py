from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from .supabase_client import get_client
from .models import VideoAnalysis

TABLE = "gg_video_analysis"


class VideoAnalysisRepository:
    """CRUD helpers for gg_video_analysis.

    主键: id
    唯一键: source_path
    """

    @staticmethod
    def upsert(va: Union[VideoAnalysis, Dict[str, Any]]) -> VideoAnalysis:
        """Upsert by unique constraint on source_path. 返回插入/更新后的行（若 supabase 返回 data）。

        支持两种输入：
        - VideoAnalysis 实例：严格校验、完整 upsert
        - dict（部分字段补丁）：仅更新提供的字段
        """
        client = get_client()

        # dict patch path: 不做 Pydantic 强校验
        if isinstance(va, dict):
            payload: Dict[str, Any] = {k: v for k, v in va.items() if v is not None}
            # 规范化时间字段
            if isinstance(payload.get("created_at"), datetime):
                payload["created_at"] = payload["created_at"].isoformat()
            # id=None 移除，避免与主键冲突
            if payload.get("id") is None:
                payload.pop("id", None)
            resp = client.table(TABLE).upsert(payload, on_conflict="project_id,source_path").execute()
            data = getattr(resp, "data", None)
            row = data[0] if data else None
            return VideoAnalysisRepository._row_to_model(row) if row else VideoAnalysis(
                **{k: v for k, v in payload.items() if k in VideoAnalysis.model_fields}  # type: ignore[attr-defined]
            )

        # Pydantic model path
        model = va
        if hasattr(model, "model_dump"):
            payload = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        else:  # pragma: no cover - 兼容 pydantic v1
            payload = model.dict()  # type: ignore[attr-defined]
            if isinstance(payload.get("created_at"), datetime):
                payload["created_at"] = payload["created_at"].isoformat()
        if payload.get("id") is None:
            payload.pop("id", None)
        resp = client.table(TABLE).upsert(payload, on_conflict="project_id,source_path").execute()
        data = getattr(resp, "data", None)
        row = data[0] if data else None
        return VideoAnalysisRepository._row_to_model(row) if row else model  # type: ignore[return-value]

    @staticmethod
    def get_by_id(analysis_id: int) -> Optional[VideoAnalysis]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("id", analysis_id)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return VideoAnalysisRepository._row_to_model(row) if row else None

    @staticmethod
    def get_by_source_path(source_path: str) -> Optional[VideoAnalysis]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("source_path", source_path)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return VideoAnalysisRepository._row_to_model(row) if row else None

    @staticmethod
    def list_by_post(post_id: int, limit: int = 50, offset: int = 0) -> List[VideoAnalysis]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("post_id", post_id)
            .order("id", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [VideoAnalysisRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def list_recent(limit: int = 50, offset: int = 0) -> List[VideoAnalysis]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .order("id", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [VideoAnalysisRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> VideoAnalysis:
        if not row:
            return VideoAnalysis(
                source_path="",  # satisfy NonEmptyStr at runtime when needed
                summary="",
                sentiment="",
                timeline=[],
                key_points=[],
                risk_types=[],
            )
        return VideoAnalysis(
            id=row.get("id"),
            project_id=row.get("project_id", ""),
            source_path=row.get("source_path", ""),
            source_platform=row.get("source_platform", "douyin"),
            summary=row.get("summary", ""),
            sentiment=row.get("sentiment", ""),
            brand=row.get("brand"),
            timeline=row.get("timeline"),
            key_points=row.get("key_points"),
            risk_types=row.get("risk_types"),
            total_risk=row.get("total_risk"),
            total_risk_reason=row.get("total_risk_reason"),
            created_at=_parse_dt(row.get("created_at")),
            platform_item_id=row.get("platform_item_id"),
            analysis_detail=row.get("analysis_detail"),
            post_id=row.get("post_id"),
            brand_relevance=row.get("brand_relevance"),
            relevance_evidence=row.get("relevance_evidence"),
            transcript_json=row.get("transcript_json"),
            handling_suggestions=row.get("handling_suggestions"),
        )


def _parse_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None

