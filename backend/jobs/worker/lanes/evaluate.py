from typing import List, Dict, Any
import threading
from jobs.worker.lanes.base import BaseLane
from jobs.logger import get_logger
from analysis import ScreeningService

log = get_logger(__name__)


class EvaluateLane(BaseLane):
    name = "evaluate"

    def __init__(self, settings, executor):
        super().__init__(settings, executor)
        self._busy = False
        self._lock = threading.Lock()

    def claim_and_submit_batch(self) -> int:
        """
        通过 ScreeningService.fetch_candidates() 拉取候选（当前约定为1条），
        有则提交到线程池由 _run_one 调用 process_batch(rows=...) 执行。
        添加 busy 标记避免重复提交。
        """
        with self._lock:
            if self._busy:
                log.debug("[EvaluateLane] busy, skipping this round")
                return 0

            svc = ScreeningService()
            rows: List[Dict[str, Any]] = svc.fetch_candidates(limit=1, offset=0)
            if not rows:
                return 0

            # 标记为忙碌，提交到线程池
            self._busy = True
            self.executor.submit(self._run_one_wrapper, rows)
            log.info("[EvaluateLane] submitted 1 task, marked as busy")
            return 1

    def _run_one_wrapper(self, rows: List[Dict[str, Any]]) -> None:
        """包装器，确保执行完成后清除 busy 标记"""
        try:
            self._run_one(rows)
        finally:
            with self._lock:
                self._busy = False
                log.info("[EvaluateLane] task completed, marked as not busy")

    def _run_one(self, rows: List[Dict[str, Any]]) -> None:
        try:
            svc = ScreeningService()
            counters = svc.process_batch(rows=rows)
            log.info("[EvaluateLane] processed counters=%s", counters)
        except Exception as e:
            log.exception("[EvaluateLane] run_one failed: %s", e)
