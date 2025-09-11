import threading
from jobs.worker.lanes.base import BaseLane
from jobs.logger import get_logger

log = get_logger(__name__)
from tikhub_api.orm import PostRepository, AnalysisStatus
from analysis.analysis_service import AnalysisService



class AnalyzeLane(BaseLane):
    name = "analyze"

    def __init__(self, settings, executor):
        super().__init__(settings, executor)
        self._busy = False
        self._lock = threading.Lock()

    def claim_and_submit_batch(self) -> int:
        with self._lock:
            if self._busy:
                log.debug("[AnalyzeLane] busy, skipping this round")
                return 0
            # 查询一条待分析的帖子（analysis_status='pending'）
            posts = PostRepository.list_by_analysis_status(AnalysisStatus.PENDING.value, limit=1)
            if not posts:
                return 0
            post = posts[0]
            if not getattr(post, "id", None):
                return 0
            self._busy = True
            self.executor.submit(self._run_one_wrapper, int(post.id))
            log.info("[AnalyzeLane] submitted 1 task, marked as busy: post_id=%s", post.id)
            return 1

    def _run_one_wrapper(self, item) -> None:
        try:
            self._run_one(item)
        finally:
            with self._lock:
                self._busy = False
                log.info("[AnalyzeLane] task completed, marked as not busy")

    def _run_one(self, post_id: int) -> None:
        try:
            log.info("[AnalyzeLane] processing post_id: %s", post_id)
            svc = AnalysisService()
            svc.analyze_post(int(post_id))
        except Exception as e:
            log.exception("[AnalyzeLane] run_one failed: %s", e)
