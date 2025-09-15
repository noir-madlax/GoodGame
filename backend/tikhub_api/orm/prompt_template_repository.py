from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from .supabase_client import get_client
from .models import PromptTemplate

TABLE = "prompt_templates"


class PromptTemplateRepository:
    """CRUD helpers for prompt_templates table.

    Notes on constraints:
    - Unique (name, version)
    - Partial unique on (name) where is_active = true (只能有一个同名激活版本)
    """

    # ------------------------ Reads ------------------------
    @staticmethod
    def get_by_id(template_id: str) -> Optional[PromptTemplate]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("id", template_id)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return PromptTemplateRepository._row_to_model(row) if row else None

    @staticmethod
    def get_by_name_and_version(name: str, version: str) -> Optional[PromptTemplate]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("name", name)
            .eq("version", version)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return PromptTemplateRepository._row_to_model(row) if row else None

    @staticmethod
    def get_active_by_name(name: str) -> Optional[PromptTemplate]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("name", name)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return PromptTemplateRepository._row_to_model(row) if row else None

    @staticmethod
    def list_by_method(method_name: str, is_active: Optional[bool] = None, limit: int = 100, offset: int = 0) -> List[PromptTemplate]:
        client = get_client()
        query = (
            client.table(TABLE)
            .select("*")
            .eq("method_name", method_name)
            .order("updated_at", desc=True)
        )
        if is_active is not None:
            query = query.eq("is_active", is_active)
        resp = query.range(offset, offset + max(limit - 1, 0)).execute()
        return [PromptTemplateRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def list_versions(name: str, limit: int = 50, offset: int = 0) -> List[PromptTemplate]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("name", name)
            .order("created_at", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [PromptTemplateRepository._row_to_model(r) for r in (resp.data or [])]

    # ----------------------- Writes ------------------------
    @staticmethod
    def upsert_template(t: Union[PromptTemplate, Dict[str, Any]]) -> PromptTemplate:
        """Upsert by unique (name, version). Returns stored row if available.
        - 若传入 dict：仅使用非 None 字段
        - 若传入 PromptTemplate：使用其序列化值
        注意：若希望该条记录为激活版本，请先调用 set_active() 确保唯一性。
        """
        client = get_client()

        if isinstance(t, dict):
            payload: Dict[str, Any] = {k: v for k, v in t.items() if v is not None}
        else:
            # Pydantic v2: model_dump; v1 回落到 dict()
            if hasattr(t, "model_dump"):
                payload = t.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
            else:
                payload = t.dict(exclude_none=True)  # type: ignore[attr-defined]

        # id=None 时删除，以避免主键冲突
        if payload.get("id") is None:
            payload.pop("id", None)

        resp = client.table(TABLE).upsert(payload, on_conflict="name,version").execute()
        data = (resp.data or [None])[0]
        return PromptTemplateRepository._row_to_model(data) if data else (
            t if isinstance(t, PromptTemplate) else PromptTemplate(**payload)
        )

    @staticmethod
    def set_active(name: str, version: str) -> None:
        """将同名的其它版本置为非激活，并将指定版本置为激活。
        注：不是事务操作，若需要更强一致性，可迁移到 RPC/存储过程中处理。
        """
        client = get_client()
        _ = (
            client.table(TABLE)
            .update({"is_active": False})
            .eq("name", name)
            .eq("is_active", True)
            .execute()
        )
        _ = (
            client.table(TABLE)
            .update({"is_active": True})
            .eq("name", name)
            .eq("version", version)
            .execute()
        )
        return None

    # -------------------- Mappers/Utils --------------------
    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> PromptTemplate:
        if not row:
            return PromptTemplate()
        return PromptTemplate(
            id=row.get("id"),
            name=row.get("name", ""),
            description=row.get("description"),
            notes=row.get("notes"),
            version=row.get("version", ""),
            method_name=row.get("method_name", ""),
            is_active=bool(row.get("is_active", False)),
            content=row.get("content", ""),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
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

