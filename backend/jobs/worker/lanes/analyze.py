import threading
from jobs.worker.lanes.base import BaseLane
from jobs.logger import get_logger
from common.request_context import set_project_id, reset_project_id

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
        token = None
        try:
            log.info("[AnalyzeLane] processing post_id: %s", post_id)
            # 注入上下文：读取该帖的 project_id 作为本次任务生命周期内的固定值
            post = PostRepository.get_by_id(int(post_id))
            pid = getattr(post, "project_id", None) if post else None
            if pid:
                token = set_project_id(str(pid))
            else:
                raise ValueError(f"project_id missing for post_id={post_id}")

            svc = AnalysisService()
            svc.analyze_post(int(post_id))
        except Exception as e:
            log.exception("[AnalyzeLane] run_one failed: %s", e)
        finally:
            if token:
                reset_project_id(token)
