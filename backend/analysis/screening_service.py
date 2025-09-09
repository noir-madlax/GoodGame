from __future__ import annotations
from typing import List, Dict, Any, Optional

from ..tikhub_api.orm.post_repository import PostRepository
from ..tikhub_api.orm.enums import RelevantStatus
from .openrouter_client import OpenRouterClient
from .text_builder import build_user_msg, SYSTEM_PROMPT
from .heuristics import obviously_no_value

ALLOWED_STATUSES = {"init", "pending", "no_value", "analyzed"}

class ScreeningService:
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self.client = OpenRouterClient(model=model, api_key=api_key)

    def fetch_candidates(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        # 仅挑选 relevant_status='unknown' 的内容；当前需求固定只取 1 条（硬编码）
        posts = PostRepository.list_by_relevant_status(RelevantStatus.UNKNOWN.value, limit=1, offset=offset)
        # 转字典便于模板格式化
        return [p.model_dump(mode="json", exclude_none=True) for p in posts]  # type: ignore

    def decide_status(self, row: Dict[str, Any]) -> str:
        # 先走本地明显无价值规则
        if obviously_no_value(row):
            print({"post_id": row.get("id"), "decision": "heuristics:no_value", "reason": "低互动或低价值关键词"})
            return "no"
        # 调用 LLM：现约定模型直接返回英文相关性枚举（yes/no/maybe），不再做本地映射
        user_msg = build_user_msg(row)
        result = self.client.classify_value(SYSTEM_PROMPT, user_msg)
        print({"post_id": row.get("id"), "llm_result": result})

        # 解析返回：直接读取 brand_relevance（yes | maybe | no）；若是字符串则直接使用
        status = ""
        if isinstance(result, dict):
            status = str(result.get("brand_relevance") or "").strip().lower()
        elif isinstance(result, str):
            status = result.strip().lower()
        # 只接受 yes/no/maybe，其它一律拒绝为 no
        return status if status in RelevantStatus.__members__.values() else RelevantStatus.UNKNOWN.value

    def process_batch(self, limit: int = 50, offset: int = 0) -> Dict[str, int]:
        rows = self.fetch_candidates(limit=limit, offset=offset)
        counters = {"yes": 0, "maybe": 0, "no": 0, "skipped": 0}
        for row in rows:
            post_id = int(row.get("id") or 0)
            if not post_id:
                counters["skipped"] += 1
                continue
            relevant_status = self.decide_status(row)  # "yes" | "maybe" | "no"
            # 回写 relevant_status
            PostRepository.update_relevant_status(post_id, relevant_status)
            counters[relevant_status] += 1
            print({"post_id": post_id, "updated_relevant_status": relevant_status})
        return counters

