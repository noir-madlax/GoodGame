from typing import List

from tikhub_api.orm.enums import Channel
from jobs.logger import get_logger
from jobs.config import Settings
from tikhub_api.orm import (
    SearchKeywordRepository,
    SearchKeyword,
)
from tikhub_api.workflow import run_channel_search_and_upsert
from common.request_context import set_project_id

log = get_logger(__name__)


def run_search_once(settings) -> None:
    """
    定时任务：查询所有关键词，固定渠道 douyin，直接使用 SearchKeywordRepository 返回的 keyword，
    逐一调用 run_video_workflow_channel 执行业务（不再与品牌名组合）。
    """
    log.info("[Scheduler] run_search_once: start")

    # 临时设置固定的 project_id
    set_project_id("67f480b5-3691-447c-af85-37f6227c9365")

    # 1) 查询所有关键词（search_keywords 全量）
    keywords: List[SearchKeyword] = SearchKeywordRepository.list_all(limit=2000, offset=0)
    log.info("关键词数量: %d", len(keywords))

    # 2) 逐一执行业务（不额外打印结果）
    channel = Channel.DOUYIN
    total = 0
    for k in keywords:
        kw = (k.keyword or "").strip()
        if not kw:
            continue
        try:
            run_channel_search_and_upsert(channel, kw)
        except Exception as e:
            log.error("运行搜索落库失败: channel=%s, keyword=%s, err=%s", channel, kw, e)
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

