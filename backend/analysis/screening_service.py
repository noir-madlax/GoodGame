from __future__ import annotations
from typing import List, Dict, Any, Optional

from tikhub_api.orm.post_repository import PostRepository
from tikhub_api.orm.enums import RelevantStatus
from .openrouter_client import OpenRouterClient
from .text_builder import build_user_msg, SYSTEM_PROMPT
from jobs.logger import get_logger

log = get_logger(__name__)

class ScreeningService:
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self.client = OpenRouterClient(model=model, api_key=api_key)

    def fetch_candidates(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        # 仅挑选 relevant_status='unknown' 的内容；当前需求固定只取 1 条（硬编码）
        posts = PostRepository.list_by_relevant_status(RelevantStatus.UNKNOWN.value, limit=limit, offset=offset)
        # 转字典便于模板格式化
        return [p.model_dump(mode="json", exclude_none=True) for p in posts]  # type: ignore

    def decide_status(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """返回包含状态与详细结果的 dict：{"status": str, "result": Any}
        - status 仅允许 yes/maybe/no，否则降级为 unknown
        - result 原样透传（可为 dict 或 str），用于记录到 relevant_result
        """
        # # 先走本地明显无价值规则
        # if obviously_no_value(row):
        #     log.info({"post_id": row.get("id"), "decision": "heuristics:no_value", "reason": "低互动或低价值关键词"})
        #     return {"status": "no", "result": {"source": "heuristics", "reason": "低互动或低价值关键词"}}
        # 调用 LLM：现约定模型直接返回英文相关性枚举（yes/no/maybe），不再做本地映射
        user_msg = build_user_msg(row)

        log.info({"post_id": row.get("id"), "event": "llm 请求参数如下",
                  "llm_system_prompt": SYSTEM_PROMPT,
                  "llm_user_msg": user_msg})
        result = self.client.classify_value(SYSTEM_PROMPT, user_msg)
        log.info({"post_id": row.get("id"),
                  "event":"llm 返回结果如下",
                  "llm_result": result})

        # 解析返回：直接读取 brand_relevance（yes | maybe | no）；若是字符串则直接使用
        status = ""
        if isinstance(result, dict):
            status = str(result.get("brand_relevance") or "").strip().lower()
        elif isinstance(result, str):
            status = result.strip().lower()
        # 只接受 yes/no/maybe，否则标记为 unknown
        allowed = {e.value for e in RelevantStatus}
        status = status if status in allowed else RelevantStatus.UNKNOWN.value
        return {"status": status, "result": result}

    def process_batch(self, rows: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        处理一批待判定的帖子，rows 由外部传入（不在此函数内做候选查询）。
        约定 row 至少包含 id、title 等用于判定的字段。
        返回计数器便于观测。
        """
        counters = {"yes": 0, "maybe": 0, "no": 0, "skipped": 0}
        for row in rows:
            post_id = int(row.get("id") or 0)
            if not post_id:
                counters["skipped"] += 1
                continue
            decision = self.decide_status(row)  # {status, result}
            relevant_status = decision.get("status", "unknown")
            relevant_result = decision.get("result")
            # 若模型未能给出明确结论，保守标记为 unknown
            allowed = {e.value for e in RelevantStatus}
            if relevant_status not in allowed:
                log.error({"post_id": post_id, "error": f"invalid relevant_status: {relevant_status}"})
                counters["skipped"] += 1
                continue
            # 回写 relevant_status + relevant_result
            PostRepository.update_relevant_status(post_id, relevant_status, relevant_result)
            counters[relevant_status] += 1
            log.info({"post_id": post_id, "updated_relevant_status": relevant_status})
        return counters

    def process_one_by_id(self, post_id: int) -> Dict[str, Any]:
        """按 ID 执行一次初筛：读取 DB→组装 row→复用 process_batch 处理一条
        返回与批处理一致的计数器摘要，以及该 id 的最终状态
        """
        post = PostRepository.get_by_id(post_id)
        if not post:
            raise ValueError(f"post not found: id={post_id}")
        row = post.model_dump(mode="json", exclude_none=True)  # type: ignore
        counters = self.process_batch([row])
        # 读取刚写回的状态（也可直接返回 process_batch 内部的决策）
        updated = PostRepository.get_by_id(post_id)
        final_status = getattr(updated, "relevant_status", None) or "unknown"
        return {"post_id": post_id, "relevant_status": final_status, "counters": counters}

