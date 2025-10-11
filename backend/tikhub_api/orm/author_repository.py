from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from .supabase_client import get_client
from .models import Author

TABLE = "gg_authors"


class AuthorRepository:
    """CRUD helpers for gg_authors table.
    
    Constraints:
    - Primary key: id
    - Unique: (platform, platform_author_id)
    - Index: sec_uid (where sec_uid is not null)
    """

    # ------------------------ Reads ------------------------
    @staticmethod
    def get_by_id(author_id: int) -> Optional[Author]:
        """根据主键 id 查询作者"""
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("id", author_id)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return AuthorRepository._row_to_model(row) if row else None

    @staticmethod
    def get_by_platform_author(platform: str, platform_author_id: str) -> Optional[Author]:
        """根据平台和平台作者ID查询作者（唯一索引）"""
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("platform", platform)
            .eq("platform_author_id", platform_author_id)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return AuthorRepository._row_to_model(row) if row else None

    @staticmethod
    def get_by_sec_uid(sec_uid: str) -> Optional[Author]:
        """根据 sec_uid 查询作者"""
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("sec_uid", sec_uid)
            .limit(1)
            .execute()
        )
        row = (resp.data or [None])[0]
        return AuthorRepository._row_to_model(row) if row else None

    @staticmethod
    def list_by_platform(
        platform: str,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "follower_count",
        desc: bool = True
    ) -> List[Author]:
        """根据平台查询作者列表，默认按粉丝数降序"""
        client = get_client()
        query = (
            client.table(TABLE)
            .select("*")
            .eq("platform", platform)
        )
        query = query.order(order_by, desc=desc)
        resp = query.range(offset, offset + max(limit - 1, 0)).execute()
        return [AuthorRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def list_all(
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        desc: bool = True
    ) -> List[Author]:
        """查询所有作者列表"""
        client = get_client()
        query = client.table(TABLE).select("*")
        query = query.order(order_by, desc=desc)
        resp = query.range(offset, offset + max(limit - 1, 0)).execute()
        return [AuthorRepository._row_to_model(r) for r in (resp.data or [])]

    # ------------------------ Writes ------------------------
    @staticmethod
    def upsert_author(author: Union[Author, Dict[str, Any]]) -> Author:
        """Upsert 作者信息，基于 (platform, platform_author_id) 唯一约束
        
        支持两种输入：
        - Author 实例：严格校验、完整 upsert
        - dict（部分字段补丁）：仅更新提供的字段
        
        Returns:
            插入或更新后的 Author 对象
        """
        client = get_client()

        # dict patch path: no strict pydantic validation
        if isinstance(author, dict):
            payload: Dict[str, Any] = {k: v for k, v in author.items() if v is not None}
            # 处理 datetime 序列化
            for dt_field in ["created_at", "updated_at"]:
                if isinstance(payload.get(dt_field), datetime):
                    payload[dt_field] = payload[dt_field].isoformat()
            if payload.get("id") is None:
                payload.pop("id", None)
            resp = client.table(TABLE).upsert(
                payload,
                on_conflict="platform,platform_author_id"
            ).execute()
            data = resp.data[0] if resp.data else None
            return AuthorRepository._row_to_model(data) if data else Author()

        # pydantic model path
        model = author
        if hasattr(model, "model_dump"):
            payload: Dict[str, Any] = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        else:
            payload = model.dict()  # type: ignore[attr-defined]
            # 处理 datetime 序列化
            for dt_field in ["created_at", "updated_at"]:
                if isinstance(payload.get(dt_field), datetime):
                    payload[dt_field] = payload[dt_field].isoformat()

        if payload.get("id") is None:
            payload.pop("id", None)

        resp = client.table(TABLE).upsert(
            payload,
            on_conflict="platform,platform_author_id"
        ).execute()
        data = resp.data[0] if resp.data else None
        return AuthorRepository._row_to_model(data) if data else model  # type: ignore[return-value]

    @staticmethod
    def upsert_authors(authors: List[Union[Author, Dict[str, Any]]]) -> List[Author]:
        """批量 upsert 作者信息
        
        Args:
            authors: Author 对象或字典列表
            
        Returns:
            插入或更新后的 Author 对象列表
        """
        if not authors:
            return []

        client = get_client()
        payload = []
        seen = set()

        for author in authors:
            if isinstance(author, dict):
                row = {k: v for k, v in author.items() if v is not None}
            else:
                if hasattr(author, "model_dump"):
                    row = author.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
                else:
                    row = author.dict()  # type: ignore[attr-defined]

            # 处理 datetime 序列化
            for dt_field in ["created_at", "updated_at"]:
                if isinstance(row.get(dt_field), datetime):
                    row[dt_field] = row[dt_field].isoformat()

            # 去重：基于 (platform, platform_author_id)
            key = (row.get("platform"), row.get("platform_author_id"))
            if key in seen:
                continue
            seen.add(key)

            if row.get("id") is None:
                row.pop("id", None)
            payload.append(row)

        if not payload:
            return []

        resp = client.table(TABLE).upsert(
            payload,
            on_conflict="platform,platform_author_id"
        ).execute()
        data = resp.data or []
        return [AuthorRepository._row_to_model(r) for r in data]

    @staticmethod
    def update_author(
        author_id: int,
        updates: Dict[str, Any]
    ) -> Optional[Author]:
        """更新作者信息
        
        Args:
            author_id: 作者 ID
            updates: 要更新的字段字典
            
        Returns:
            更新后的 Author 对象，若失败返回 None
        """
        if not updates:
            return None

        client = get_client()
        payload = {k: v for k, v in updates.items() if v is not None}
        
        # 处理 datetime 序列化
        for dt_field in ["created_at", "updated_at"]:
            if isinstance(payload.get(dt_field), datetime):
                payload[dt_field] = payload[dt_field].isoformat()

        resp = (
            client.table(TABLE)
            .update(payload)
            .eq("id", author_id)
            .execute()
        )
        row = resp.data[0] if getattr(resp, "data", None) else None
        return AuthorRepository._row_to_model(row) if row else None

    @staticmethod
    def mark_user_deleted(author_id: int, deleted: bool = True) -> Optional[Author]:
        """标记用户已删除状态
        
        Args:
            author_id: 作者 ID
            deleted: 是否已删除
            
        Returns:
            更新后的 Author 对象
        """
        return AuthorRepository.update_author(author_id, {"user_deleted": deleted})

    # -------------------- Mappers/Utils --------------------
    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> Author:
        """将数据库行转换为 Author 模型"""
        if not row:
            return Author()
        return Author(
            id=row.get("id"),
            platform=row.get("platform", "douyin"),
            platform_author_id=row.get("platform_author_id", ""),
            sec_uid=row.get("sec_uid"),
            nickname=row.get("nickname"),
            avatar_url=row.get("avatar_url"),
            share_url=row.get("share_url"),
            follower_count=row.get("follower_count", 0),
            signature=row.get("signature"),
            location=row.get("location"),
            account_cert_info=row.get("account_cert_info"),
            verification_type=row.get("verification_type"),
            raw_response=row.get("raw_response"),
            user_deleted=row.get("user_deleted"),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
        )


def _parse_dt(val: Any) -> Optional[datetime]:
    """解析日期时间字符串"""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None

