from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from .supabase_client import get_client
from .models import SearchResponseLog

TABLE = "gg_search_response_logs"


class SearchResponseLogRepository:
    """CRUD helpers for gg_search_response_logs table."""

    # ------------------------ Create ------------------------
    @staticmethod
    def create(log: Union[SearchResponseLog, Dict[str, Any]]) -> SearchResponseLog:
        """创建一条搜索响应日志记录。
        
        Args:
            log: SearchResponseLog 实例或字典
            
        Returns:
            创建后的 SearchResponseLog 实例
        """
        client = get_client()

        if isinstance(log, dict):
            payload: Dict[str, Any] = {k: v for k, v in log.items() if v is not None}
            if isinstance(payload.get("created_at"), datetime):
                payload["created_at"] = payload["created_at"].isoformat()
            if isinstance(payload.get("updated_at"), datetime):
                payload["updated_at"] = payload["updated_at"].isoformat()
            if isinstance(payload.get("request_timestamp"), datetime):
                payload["request_timestamp"] = payload["request_timestamp"].isoformat()
            if payload.get("id") is None:
                payload.pop("id", None)
            
            resp = client.table(TABLE).insert(payload).execute()
            data = resp.data[0] if resp.data else None
            return SearchResponseLogRepository._row_to_model(data) if data else SearchResponseLog()

        model = log
        if hasattr(model, "model_dump"):
            payload: Dict[str, Any] = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        else:
            payload = model.dict()  # type: ignore[attr-defined]
            if isinstance(payload.get("created_at"), datetime):
                payload["created_at"] = payload["created_at"].isoformat()
            if isinstance(payload.get("updated_at"), datetime):
                payload["updated_at"] = payload["updated_at"].isoformat()
            if isinstance(payload.get("request_timestamp"), datetime):
                payload["request_timestamp"] = payload["request_timestamp"].isoformat()

        if payload.get("id") is None:
            payload.pop("id", None)

        resp = client.table(TABLE).insert(payload).execute()
        data = resp.data[0] if resp.data else None
        return SearchResponseLogRepository._row_to_model(data) if data else model  # type: ignore[return-value]

    # ------------------------ Reads ------------------------
    @staticmethod
    def get_by_id(log_id: int) -> Optional[SearchResponseLog]:
        """根据 ID 获取日志记录"""
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("id", log_id)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return SearchResponseLogRepository._row_to_model(row) if row else None

    @staticmethod
    def list_by_project(
        project_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[SearchResponseLog]:
        """获取指定项目的所有日志记录"""
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [SearchResponseLogRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def list_by_keyword(
        project_id: str,
        keyword: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[SearchResponseLog]:
        """获取指定项目和关键词的所有日志记录"""
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("project_id", project_id)
            .eq("keyword", keyword)
            .order("page_number", desc=False)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [SearchResponseLogRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def list_by_platform(
        project_id: str,
        platform: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[SearchResponseLog]:
        """获取指定项目和平台的所有日志记录"""
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("project_id", project_id)
            .eq("platform", platform)
            .order("created_at", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [SearchResponseLogRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def get_latest_by_keyword(
        project_id: str,
        keyword: str,
        platform: str = "douyin"
    ) -> Optional[SearchResponseLog]:
        """获取指定关键词的最新一条日志记录"""
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("project_id", project_id)
            .eq("keyword", keyword)
            .eq("platform", platform)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return SearchResponseLogRepository._row_to_model(row) if row else None

    @staticmethod
    def list_by_batch(batch_id: str, limit: int = 1000, offset: int = 0) -> List[SearchResponseLog]:
        """查询指定批次的所有日志记录（按页码排序）

        Args:
            batch_id: 批次号
            limit: 返回记录数上限
            offset: 偏移量

        Returns:
            SearchResponseLog 列表
        """
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("batch_id", batch_id)
            .order("page_number", desc=False)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        return [SearchResponseLogRepository._row_to_model(r) for r in (resp.data or [])]

    # ------------------------ Update ------------------------
    @staticmethod
    def update_by_id(log_id: int, patch: Dict[str, Any]) -> Optional[SearchResponseLog]:
        """部分字段更新：仅更新 patch 中提供的键值；自动规范化时间字段。"""
        client = get_client()
        payload: Dict[str, Any] = {k: v for k, v in patch.items() if v is not None}
        
        if "updated_at" not in payload:
            payload["updated_at"] = datetime.utcnow().isoformat() + "Z"
        else:
            if isinstance(payload["updated_at"], datetime):
                payload["updated_at"] = payload["updated_at"].isoformat()
        
        if isinstance(payload.get("request_timestamp"), datetime):
            payload["request_timestamp"] = payload["request_timestamp"].isoformat()
        
        resp = (
            client.table(TABLE)
            .update(payload)
            .eq("id", log_id)
            .execute()
        )
        row = (resp.data or [None])[0]
        return SearchResponseLogRepository._row_to_model(row) if row else None

    # ------------------------ Delete ------------------------
    @staticmethod
    def delete_by_id(log_id: int) -> bool:
        """删除指定 ID 的日志记录"""
        client = get_client()
        resp = client.table(TABLE).delete().eq("id", log_id).execute()
        return len(resp.data or []) > 0

    @staticmethod
    def delete_by_project(project_id: str) -> int:
        """删除指定项目的所有日志记录，返回删除的记录数"""
        client = get_client()
        resp = client.table(TABLE).delete().eq("project_id", project_id).execute()
        return len(resp.data or [])

    # ------------------------ Mappers/Utils ------------------------
    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> SearchResponseLog:
        """将数据库行转换为 SearchResponseLog 模型"""
        if not row:
            return SearchResponseLog()
        return SearchResponseLog(
            id=row.get("id"),
            project_id=row.get("project_id", ""),
            keyword=row.get("keyword", ""),
            platform=row.get("platform", "douyin"),
            page_number=row.get("page_number", 1),
            request_params=row.get("request_params"),
            response_data=row.get("response_data"),
            request_timestamp=_parse_dt(row.get("request_timestamp")),
            response_status=row.get("response_status"),
            error_message=row.get("error_message"),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
        )


def _parse_dt(val: Any) -> Optional[datetime]:
    """解析日期时间字符串为 datetime 对象"""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None

