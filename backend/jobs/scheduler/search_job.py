from typing import List

from jobs.logger import get_logger
from jobs.config import Settings
from tikhub_api.orm import (
    MerchantBrandRepository,
    SearchKeywordRepository,
    MerchantBrand,
    SearchKeyword,
)
from tikhub_api.workflow import run_video_workflow_channel

log = get_logger(__name__)


def run_search_once(settings) -> None:
    """
    定时任务：查询有效品牌与关键词，按 brand_name+keyword 组合，固定渠道 douyin，
    循环调用 run_video_workflow_channel 执行业务。
    """
    log.info("[Scheduler] run_search_once: start")

    # 1) 查询有效品牌（merchant_brands.is_valid = true）
    brands: List[MerchantBrand] = MerchantBrandRepository.list_valid(limit=1000, offset=0)
    log.info("有效品牌数量: %d", len(brands))

    # 2) 查询所有关键词（search_keywords 全量）
    keywords: List[SearchKeyword] = SearchKeywordRepository.list_all(limit=2000, offset=0)
    log.info("关键词数量: %d", len(keywords))

    # 3) 逐一组合并执行业务（不额外打印结果）
    channel = "douyin"
    total = 0
    for b in brands:
        brand_name = (b.name or "").strip()
        for k in keywords:
            kw = f"{brand_name}{k.keyword}"
            try:
                run_video_workflow_channel(channel, kw)
            except Exception as e:
                log.error("运行工作流失败: channel=%s, brand=%s, keyword=%s, err=%s", channel, brand_name, k.keyword, e)
            total += 1

    log.info("已触发工作流次数: %d", total)
    log.info("[Scheduler] run_search_once: done")


def main():
    """手动执行一次搜索任务的入口"""
    print("手动执行搜索任务...")
    settings = Settings.from_env()
    run_search_once(settings)
    print("搜索任务执行完成")


if __name__ == "__main__":
    main()

