from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from .supabase_client import get_client
from .models import ProjectSettings

TABLE = "project_settings"


class ProjectSettingsRepository:
    """CRUD helpers for project_settings table.

    Constraints in DB:
    - PRIMARY KEY (id uuid)
    - UNIQUE (project_name)
    - INDEX (project_name)
    """

    # ------------------------ Reads ------------------------
    @staticmethod
    def get_by_id(project_id: str) -> Optional[ProjectSettings]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return ProjectSettingsRepository._row_to_model(row) if row else None

    @staticmethod
    def get_by_project_name(project_name: str) -> Optional[ProjectSettings]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("project_name", project_name)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return ProjectSettingsRepository._row_to_model(row) if row else None

    @staticmethod
    def list_all(limit: int = 200, offset: int = 0) -> List[ProjectSettings]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [ProjectSettingsRepository._row_to_model(r) for r in (resp.data or [])]

    # ----------------------- Writes ------------------------
    @staticmethod
    def upsert_settings(s: Union[ProjectSettings, Dict[str, Any]]) -> ProjectSettings:
        """Upsert by unique (project_name).
        - 支持传入 dict（仅更新提供的字段，None 字段忽略）或 ProjectSettings 模型
        - 返回存储后的行（若 supabase 版本不返回行，则回退为输入对象）
        """
        client = get_client()

        if isinstance(s, dict):
            payload: Dict[str, Any] = {k: v for k, v in s.items() if v is not None}
            for k in ("created_at", "updated_at"):
                if isinstance(payload.get(k), datetime):
                    payload[k] = payload[k].isoformat()
            # id=None 删除，避免插入冲突；uuid 由 DB 默认生成
            if payload.get("id") is None:
                payload.pop("id", None)
            resp = client.table(TABLE).upsert(payload, on_conflict="project_name").execute()
            data = (resp.data or [None])[0]
            return ProjectSettingsRepository._row_to_model(data) if data else ProjectSettings(**payload)

        model = s
        if hasattr(model, "model_dump"):
            payload: Dict[str, Any] = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        else:
            payload = model.dict()  # type: ignore[attr-defined]
            for k in ("created_at", "updated_at"):
                if isinstance(payload.get(k), datetime):
                    payload[k] = payload[k].isoformat()

        if payload.get("id") is None:
            payload.pop("id", None)

        resp = client.table(TABLE).upsert(payload, on_conflict="project_name").execute()
        data = (resp.data or [None])[0]
        return ProjectSettingsRepository._row_to_model(data) if data else model  # type: ignore[return-value]

    @staticmethod
    def update_by_id(project_id: str, patch: Dict[str, Any]) -> Optional[ProjectSettings]:
        """部分字段更新：仅更新 patch 中提供的键值；自动规范化时间字段。"""
        client = get_client()
        payload: Dict[str, Any] = {k: v for k, v in patch.items() if v is not None}
        if "updated_at" not in payload:
            payload["updated_at"] = datetime.utcnow().isoformat() + "Z"
        else:
            if isinstance(payload["updated_at"], datetime):
                payload["updated_at"] = payload["updated_at"].isoformat()
        resp = (
            client.table(TABLE)
            .update(payload)
            .eq("id", project_id)
            .execute()
        )
        row = (resp.data or [None])[0]
        return ProjectSettingsRepository._row_to_model(row) if row else None

    # -------------------- Mappers/Utils --------------------
    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> ProjectSettings:
        if not row:
            return ProjectSettings()
        return ProjectSettings(
            id=row.get("id"),
            project_name=row.get("project_name", ""),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
            status=row.get("status"),
            nav_overview_enabled=bool(row.get("nav_overview_enabled", False)),
            nav_mark_process_enabled=bool(row.get("nav_mark_process_enabled", False)),
            nav_search_settings_enabled=bool(row.get("nav_search_settings_enabled", False)),
            nav_analysis_rules_enabled=bool(row.get("nav_analysis_rules_enabled", False)),
            nav_alert_push_enabled=bool(row.get("nav_alert_push_enabled", False)),
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

