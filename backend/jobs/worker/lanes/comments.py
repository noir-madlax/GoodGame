import threading
from jobs.worker.lanes.base import BaseLane
from jobs.logger import get_logger

log = get_logger(__name__)

class CommentsLane(BaseLane):
    name = "comments"

    def __init__(self, settings, executor):
        super().__init__(settings, executor)
        self._busy = False
        self._lock = threading.Lock()

    def claim_and_submit_batch(self) -> int:
        log.info("[CommentsLane] claim_and_submit_batch: start")
        with self._lock:
            if self._busy:
                log.debug("[CommentsLane] busy, skipping this round")
                return 0
            # TODO: 从 posts 中占坑 analysis_status='pending' 的记录为 'running_comments'，提交线程池
            candidates = []  # TODO: 实际查询候选
            if not candidates:
                return 0
            self._busy = True
            self.executor.submit(self._run_one_wrapper, candidates)
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
            # TODO: 复用 tikhub_api.workflow 的 _step_sync_comments / run_video_workflow 进行评论抓取
            # 成功则置为 'ready_to_analyze'，失败回滚并重试
            log.info("[CommentsLane] processing item: %s", item)
        except Exception as e:
            log.exception("[CommentsLane] run_one failed: %s", e)
