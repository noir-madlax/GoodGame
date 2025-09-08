from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from .supabase_client import get_client
from .models import MerchantBrand

TABLE = "merchant_brands"


class MerchantBrandRepository:
    """CRUD(light) for merchant_brands: upsert and query helpers."""

    @staticmethod
    def upsert_brand(brand: Union[MerchantBrand, Dict[str, Any]]) -> MerchantBrand:
        """Upsert a brand by unique constraint on name. Returns the stored row if available.
        支持两种输入：
        - MerchantBrand 实例：严格校验、完整 upsert
        - dict（部分字段补丁）：仅更新提供的字段
        """
        client = get_client()

        # dict patch path: no strict pydantic validation
        if isinstance(brand, dict):
            payload: Dict[str, Any] = {k: v for k, v in brand.items() if v is not None}
            if isinstance(payload.get("created_at"), datetime):
                payload["created_at"] = payload["created_at"].isoformat()
            if payload.get("id") is None:
                payload.pop("id", None)
            resp = client.table(TABLE).upsert(payload, on_conflict="name").execute()
            data = resp.data[0] if resp.data else None
            return MerchantBrandRepository._row_to_model(data) if data else MerchantBrand()

        # pydantic model path
        model = brand
        if hasattr(model, "model_dump"):
            payload: Dict[str, Any] = model.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        else:
            payload = model.dict()  # type: ignore[attr-defined]
            if isinstance(payload.get("created_at"), datetime):
                payload["created_at"] = payload["created_at"].isoformat()

        if payload.get("id") is None:
            payload.pop("id", None)

        resp = client.table(TABLE).upsert(payload, on_conflict="name").execute()
        data = resp.data[0] if resp.data else None
        return MerchantBrandRepository._row_to_model(data) if data else model  # type: ignore[return-value]

    @staticmethod
    def get_by_id(brand_id: int) -> Optional[MerchantBrand]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("id", brand_id)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return MerchantBrandRepository._row_to_model(row) if row else None

    @staticmethod
    def get_by_name(name: str) -> Optional[MerchantBrand]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("name", name)
            .limit(1)
            .execute()
        )
        row = resp.data[0] if resp.data else None
        return MerchantBrandRepository._row_to_model(row) if row else None

    @staticmethod
    def list_valid(limit: int = 100, offset: int = 0) -> List[MerchantBrand]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("is_valid", True)
            .order("id", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [MerchantBrandRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def list_all(limit: int = 100, offset: int = 0) -> List[MerchantBrand]:
        client = get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .order("id", desc=True)
            .range(offset, offset + max(limit - 1, 0))
            .execute()
        )
        return [MerchantBrandRepository._row_to_model(r) for r in (resp.data or [])]

    @staticmethod
    def set_valid(brand_id: int, is_valid: bool) -> Optional[MerchantBrand]:
        """Update the is_valid flag for a brand. 若 supabase 版本不返回更新行，则返回 None。"""
        client = get_client()
        resp = (
            client.table(TABLE)
            .update({"is_valid": is_valid})
            .eq("id", brand_id)
            .execute()
        )
        row = resp.data[0] if getattr(resp, "data", None) else None
        return MerchantBrandRepository._row_to_model(row) if row else None

    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> MerchantBrand:
        if not row:
            return MerchantBrand()
        return MerchantBrand(
            id=row.get("id"),
            name=row.get("name", ""),
            created_at=_parse_dt(row.get("created_at")),
            is_valid=bool(row.get("is_valid", True)),
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

