from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from .supabase_client import get_client
from .models import SearchKeyword

TABLE = "search_keywords"


class SearchKeywordRepository:
    """CRUD(light) for search_keywords: upsert and query helpers."""

    @staticmethod
    def upsert_keyword(kw: Union[SearchKeyword, Dict[str, Any]]) -> SearchKeyword:
        """Upsert a keyword by unique constraint on keyword. Returns the stored row if available.
        支持两种输入：
        - SearchKeyword 实例：严格校验、完整 upsert
        - dict（部分字段补丁）：仅更新提供的字段
        """
        client = get_client()

        if isinstance(kw, dict):
            payload: Dict[str, Any] = {k: v for k, v in kw.items() if v is not None}
            if isinstance(payload.get("created_at"), datetime):
                payload["created_at"] = payload["created_at"].isoformat()
            if payload.get("id") is None:
                payload.pop("id", None)
            resp = client.table(TABLE).upsert(payload, on_conflict="keyword").execute()
            data = resp.data[0] if resp.data else None
            return SearchKeywordRepository._row_to_model(data) if data else SearchKeyword()

        model = kw
        if hasattr(model, "model_dump"):
            payload: Dict[str, Any] = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        else:
            payload = model.dict()  # type: ignore[attr-defined]
            if isinstance(payload.get("created_at"), datetime):
                payload["created_at"] = payload["created_at"].isoformat()

        if payload.get("id") is None:
            payload.pop("id", None)

        resp = client.table(TABLE).upsert(payload, on_conflict="keyword").execute()
        data = resp.data[0] if resp.data else None
        return SearchKeywordRepository._row_to_model(data) if data else model  # type: ignore[return-value]

    @staticmethod
    def get_by_id(keyword_id: int) -> Optional[SearchKeyword]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("id", keyword_id)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return SearchKeywordRepository._row_to_model(row) if row else None

    @staticmethod
    def get_by_keyword(keyword: str) -> Optional[SearchKeyword]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("keyword", keyword)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return SearchKeywordRepository._row_to_model(row) if row else None

    @staticmethod
    def list_all(limit: int = 200, offset: int = 0) -> List[SearchKeyword]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .order("id", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [SearchKeywordRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> SearchKeyword:
        if not row:
            return SearchKeyword()
        return SearchKeyword(
            id=row.get("id"),
            keyword=row.get("keyword", ""),
            created_at=_parse_dt(row.get("created_at")),
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

