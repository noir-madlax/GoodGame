import time
from jobs.logger import get_logger
from jobs.config import Settings
from jobs.worker.pools import WorkerPools
from jobs.worker.lanes.evaluate import EvaluateLane
from jobs.worker.lanes.comments import CommentsLane
from jobs.worker.lanes.analyze import AnalyzeLane

log = get_logger(__name__)


class WorkerDispatcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pools = WorkerPools(settings)
        self.lanes = [
            EvaluateLane(settings, self.pools.eval_pool),
            CommentsLane(settings, self.pools.comments_pool),
            AnalyzeLane(settings, self.pools.analyze_pool),
        ]
        self._stopping = False

    def run_forever(self) -> None:
        log.info("Worker dispatcher starting")
        try:
            while not self._stopping:
                did_work = False
                for lane in self.lanes:
                    try:
                        claimed = lane.claim_and_submit_batch()
                        if claimed:
                            did_work = True
                    except Exception as e:
                        log.exception("Lane %s failed in claim/submit: %s", lane.name, e)
                time.sleep(0 if did_work else self.settings.WORKER_POLL_INTERVAL_SEC)
        finally:
            self.stop()

    def stop(self) -> None:
        self._stopping = True
        try:
            self.pools.shutdown()
        except Exception:
            pass
        log.info("Worker dispatcher stopped")

