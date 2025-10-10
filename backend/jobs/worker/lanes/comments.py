import threading
from jobs.worker.lanes.base import BaseLane
from jobs.logger import get_logger
from tikhub_api.orm.post_repository import PostRepository
from tikhub_api.orm.enums import AnalysisStatus, RelevantStatus
from tikhub_api.workflow import sync_comments_for_post_id

log = get_logger(__name__)

class CommentsLane(BaseLane):
    name = "comments"

    def __init__(self, settings, executor):
        super().__init__(settings, executor)
        self._busy = False
        self._lock = threading.Lock()

    def claim_and_submit_batch(self) -> int:
        with self._lock:
            if self._busy:
                log.debug("[CommentsLane] busy, skipping this round")
                return 0
            # 获取一条 analysis_status=init 且 relevant_status in (yes, maybe) 的帖子
            candidates = PostRepository.list_by_analysis_and_relevance(
                [AnalysisStatus.INIT.value],
                [RelevantStatus.YES.value, RelevantStatus.MAYBE.value],
                limit=1,
                offset=0
            )
            if not candidates:
                log.debug("[CommentsLane] no candidate found (analysis=init, relevant in [yes, maybe])")
                return 0
            candidate = candidates[0]
            self._busy = True
            self.executor.submit(self._run_one_wrapper, candidate)
            log.info("[CommentsLane] submitted 1 task, marked as busy")
            return 1

    def _run_one_wrapper(self, item) -> None:
        try:
            self._run_one(item)
        finally:
            with self._lock:
                self._busy = False
                log.info("[CommentsLane] task completed, marked as not busy")

    def _run_one(self, item) -> None:
        try:
            # item 期望为 PlatformPost
            post_id = getattr(item, "id", None)
            if not post_id:
                log.warning("[CommentsLane] invalid item: missing id")
                return

            # 调用工作流公开方法封装的评论同步逻辑
            res = sync_comments_for_post_id(int(post_id), page_size=20)
            log.info(
                "[CommentsLane] comments step finished: ok=%s skipped=%s err=%s",
                getattr(res, "ok", False), getattr(res, "skipped", False), getattr(res, "error", None)
            )
        except Exception as e:
            log.exception("[CommentsLane] run_one failed: %s", e)



def run_once_by_id(post_id: int, page_size: int = 20) -> None:
    """单次执行：按 post_id 抓取评论并更新状态（封装工作流公开方法）。"""
    res = sync_comments_for_post_id(int(post_id), page_size=page_size)
    if getattr(res, "ok", False) and not getattr(res, "skipped", False):
        log.info("[CommentsLane] run_once_by_id ok: post_id=%s", post_id)
    else:
        log.info(
            "[CommentsLane] run_once_by_id finished with err: ok=%s skipped=%s err=%s",
            getattr(res, "ok", False), getattr(res, "skipped", False), getattr(res, "error", None)
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run comments sync once by post id")
    parser.add_argument("--id", type=int, required=True, help="post id")
    parser.add_argument("--page-size", type=int, default=20, help="comments page size")
    args = parser.parse_args()

    run_once_by_id(args.id, page_size=args.page_size)
