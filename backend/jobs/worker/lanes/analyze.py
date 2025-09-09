import threading
from jobs.worker.lanes.base import BaseLane
from jobs.logger import get_logger

log = get_logger(__name__)


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
            # TODO: 从 posts 中占坑 analysis_status='ready_to_analyze' 的记录为 'running_analyze'，提交线程池
            candidates = []  # TODO: 实际查询候选
            if not candidates:
                return 0
            self._busy = True
            self.executor.submit(self._run_one_wrapper, candidates)
            log.info("[AnalyzeLane] submitted 1 task, marked as busy")
            return 1

    def _run_one_wrapper(self, item) -> None:
        try:
            self._run_one(item)
        finally:
            with self._lock:
                self._busy = False
                log.info("[AnalyzeLane] task completed, marked as not busy")

    def _run_one(self, item) -> None:
        try:
            # TODO: 执行视频+评论分析，写入 analysis_results；成功置为 'analyzed'
            log.info("[AnalyzeLane] processing item: %s", item)
        except Exception as e:
            log.exception("[AnalyzeLane] run_one failed: %s", e)
