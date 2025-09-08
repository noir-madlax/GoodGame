from jobs.logger import get_logger
from jobs.config import Settings

log = get_logger(__name__)

# 使用 APScheduler 基于 Cron 表达式的调度
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _HAS_APSCHEDULER = True
except Exception:
    _HAS_APSCHEDULER = False

from jobs.scheduler.search_job import run_search_once


class SchedulerRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._stopping = False
        self._scheduler = None

    def run_forever(self) -> None:
        if not _HAS_APSCHEDULER:
            log.warning("APScheduler 未安装，Scheduler 不会运行。请在 requirements 中加入 apscheduler。")
            return
        log.info("Scheduler starting with cron: %s", self.settings.SCHED_SEARCH_CRON)
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(
            func=lambda: run_search_once(self.settings),
            trigger=CronTrigger.from_crontab(self.settings.SCHED_SEARCH_CRON),
            id="search_job",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
            replace_existing=True,
        )
        self._scheduler.start()
        try:
            while not self._stopping:
                # BackgroundScheduler 在后台线程运行，此处保持主线程存活
                import time
                time.sleep(1)
        finally:
            self.stop()

    def stop(self) -> None:
        self._stopping = True
        if self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
                log.info("Scheduler stopped")
            except Exception:
                pass

