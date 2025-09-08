from concurrent.futures import ThreadPoolExecutor
from jobs.config import Settings


class WorkerPools:
    def __init__(self, settings: Settings) -> None:
        # I/O 密集，先全部使用线程池；后续如需 CPU 密集可引入进程池
        self.eval_pool = ThreadPoolExecutor(max_workers=settings.WORKER_EVAL_CONCURRENCY, thread_name_prefix="eval")
        self.comments_pool = ThreadPoolExecutor(max_workers=settings.WORKER_COMMENTS_CONCURRENCY, thread_name_prefix="comments")
        self.analyze_pool = ThreadPoolExecutor(max_workers=settings.WORKER_ANALYZE_CONCURRENCY, thread_name_prefix="analyze")

    def shutdown(self) -> None:
        for pool in (self.eval_pool, self.comments_pool, self.analyze_pool):
            pool.shutdown(cancel_futures=True)

