from concurrent.futures import Executor
from jobs.logger import get_logger
from jobs.config import Settings

log = get_logger(__name__)


class BaseLane:
    name: str = "base"

    def __init__(self, settings: Settings, executor: Executor) -> None:
        self.settings = settings
        self.executor = executor

    def claim_and_submit_batch(self) -> int:
        """
        占坑一小批记录并提交到线程池执行。
        返回：占到的数量。
        TODO: 不同 lane 实现各自的占坑与执行逻辑
        """
        # TODO: 占坑 SQL（update ... returning）或 select+条件 update
        claimed = []  # list of items
        for item in claimed:
            self.executor.submit(self._run_one, item)
        return len(claimed)

    def _run_one(self, item) -> None:
        try:
            # TODO: 业务实现
            pass
        except Exception as e:
            log.exception("%s run_one failed: %s", self.name, e)

