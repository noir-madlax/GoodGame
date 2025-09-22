from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from .supabase_client import get_client
from .models import PromptVariable

TABLE = "prompt_variables"


class PromptVariableRepository:
    """CRUD helpers for prompt_variables table.

    Constraints expected in DB:
    - UNIQUE (project_id, variable_name)
    - INDEX (project_id)
    """

    # ------------------------ Reads ------------------------
    @staticmethod
    def get_by_id(var_id: int) -> Optional[PromptVariable]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("id", var_id)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return PromptVariableRepository._row_to_model(row) if row else None

    @staticmethod
    def get_by_project_and_name(project_id: str, variable_name: str) -> Optional[PromptVariable]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("project_id", project_id)
            .eq("variable_name", variable_name)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return PromptVariableRepository._row_to_model(row) if row else None

    @staticmethod
    def list_by_project(project_id: str, limit: int = 200, offset: int = 0) -> List[PromptVariable]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("project_id", project_id)
            .order("id", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [PromptVariableRepository._row_to_model(r) for r in (resp.data or [])]

    # ----------------------- Writes ------------------------
    @staticmethod
    def upsert_variable(v: Union[PromptVariable, Dict[str, Any]]) -> PromptVariable:
        """Upsert by unique (project_id, variable_name).
        - 支持传入 dict（仅更新提供的字段，None 字段忽略）或 PromptVariable 模型
        - 返回存储后的行（若 supabase 版本不返回行，则回退为输入对象）
        """
        client = get_client()

        if isinstance(v, dict):
            payload: Dict[str, Any] = {k: v for k, v in v.items() if v is not None}
            # 规范化时间字段
            for k in ("created_at", "updated_at"):
                if isinstance(payload.get(k), datetime):
                    payload[k] = payload[k].isoformat()
            # id=None 移除，避免插入路径冲突
            if payload.get("id") is None:
                payload.pop("id", None)
            resp = client.table(TABLE).upsert(payload, on_conflict="project_id,variable_name").execute()
            data = (resp.data or [None])[0]
            return PromptVariableRepository._row_to_model(data) if data else PromptVariable(**payload)

        model = v
        if hasattr(model, "model_dump"):
            payload: Dict[str, Any] = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        else:
            payload = model.dict()  # type: ignore[attr-defined]
            for k in ("created_at", "updated_at"):
                if isinstance(payload.get(k), datetime):
                    payload[k] = payload[k].isoformat()

        if payload.get("id") is None:
            payload.pop("id", None)

        resp = client.table(TABLE).upsert(payload, on_conflict="project_id,variable_name").execute()
        data = (resp.data or [None])[0]
        return PromptVariableRepository._row_to_model(data) if data else model  # type: ignore[return-value]

    @staticmethod
    def delete_by_project_and_name(project_id: str, variable_name: str) -> None:
        client = get_client()
        _ = (
            client.table(TABLE)
            .delete()
            .eq("project_id", project_id)
            .eq("variable_name", variable_name)
            .execute()
        )
        return None

    # -------------------- Mappers/Utils --------------------
    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> PromptVariable:
        if not row:
            return PromptVariable()
        return PromptVariable(
            id=row.get("id"),
            project_id=row.get("project_id", ""),
            variable_name=row.get("variable_name", ""),
            variable_description=row.get("variable_description"),
            variable_value=row.get("variable_value"),
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

