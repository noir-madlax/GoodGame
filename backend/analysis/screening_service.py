from __future__ import annotations
from typing import List, Dict, Any, Optional

from ..tikhub_api.orm.post_repository import PostRepository
from .openrouter_client import OpenRouterClient
from .text_builder import build_user_msg, SYSTEM_PROMPT
from .heuristics import obviously_no_value

ALLOWED_STATUSES = {"init", "pending", "no_value", "analyzed"}

class ScreeningService:
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self.client = OpenRouterClient(model=model, api_key=api_key)

    def fetch_candidates(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        # 仅挑选 init 的内容，避免重复消耗
        posts = PostRepository.list_by_status("init", limit=limit, offset=offset)
        # 转字典便于模板格式化
        return [p.model_dump(mode="json", exclude_none=True) for p in posts]  # type: ignore

    def decide_status(self, row: Dict[str, Any]) -> str:
        # 先走本地明显无价值规则
        if obviously_no_value(row):
            print({"post_id": row.get("id"), "decision": "heuristics:no_value", "reason": "低互动或低价值关键词"})
            return "no_value"
        # 调用 LLM 做二分类
        user_msg = build_user_msg(row)
        result = self.client.classify_value(SYSTEM_PROMPT, user_msg)
        # 打印 LLM 原始结果
        print({
            "post_id": row.get("id"),
            "llm_result": result,
        })
        suggested = str(result.get("suggested_status") or "no_value").strip()
        return suggested if suggested in ("pending", "no_value") else "no_value"

    def process_batch(self, limit: int = 50, offset: int = 0) -> Dict[str, int]:
        rows = self.fetch_candidates(limit=limit, offset=offset)
        counters = {"pending": 0, "no_value": 0, "skipped": 0}
        for row in rows:
            post_id = int(row.get("id") or 0)
            if not post_id:
                counters["skipped"] += 1
                continue
            new_status = self.decide_status(row)
            PostRepository.update_analysis_status(post_id, new_status)
            counters[new_status] += 1
            # 打印更新日志
            print({"post_id": post_id, "updated_status": new_status})
        return counters

