from jobs.logger import get_logger

log = get_logger(__name__)


def run_search_once(settings) -> None:
    """
    定时任务：关键词搜索 + upsert 入库（analysis_status=init）
    TODO: 读取关键词列表、按平台调用 fetcher.get_search_posts(keyword)
          使用 PostRepository.upsert_post 写入
    """
    log.info("[Scheduler] run_search_once: start")
    # TODO: 实现业务逻辑
    log.info("[Scheduler] run_search_once: done")

