import os
import signal
import threading
import time
from pathlib import Path

# 提前加载 backend/.env，确保后续 Settings/Logger 都能读取到
try:
    from dotenv import load_dotenv
    _DOTENV_LOADED = True
except Exception:
    _DOTENV_LOADED = False

if _DOTENV_LOADED:
    dotenv_path = Path(__file__).with_name(".env")
    # 若文件存在则加载（不抛错），不存在则忽略
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)

from jobs.config import Settings
from jobs.logger import get_logger
from jobs.scheduler.runner import SchedulerRunner
from jobs.worker.dispatcher import WorkerDispatcher
from api.server import APIServer


log = get_logger(__name__)


def main():
    settings = Settings.from_env()
    log.info("Starting backend with settings: SCHEDULER=%s, WORKER=%s, API=%s",
             settings.ENABLE_SCHEDULER, settings.ENABLE_WORKER, settings.ENABLE_API)

    threads: list[threading.Thread] = []
    components: list[object] = []

    # API Server
    if settings.ENABLE_API:
        api_server = APIServer(settings)
        components.append(api_server)
        t_api = threading.Thread(target=api_server.run_forever, name="API", daemon=True)
        t_api.start()
        threads.append(t_api)
        log.info("API server thread started on %s:%s", settings.API_HOST, settings.API_PORT)

    # Scheduler
    if settings.ENABLE_SCHEDULER:
        scheduler_runner = SchedulerRunner(settings)
        components.append(scheduler_runner)
        t_sched = threading.Thread(target=scheduler_runner.run_forever, name="Scheduler", daemon=True)
        t_sched.start()
        threads.append(t_sched)
        log.info("Scheduler thread started")

    # Worker
    if settings.ENABLE_WORKER:
        worker = WorkerDispatcher(settings)
        components.append(worker)
        t_worker = threading.Thread(target=worker.run_forever, name="Worker", daemon=True)
        t_worker.start()
        threads.append(t_worker)
        log.info("Worker thread started")

    # Graceful shutdown
    stop_event = threading.Event()

    def _graceful_shutdown(signum, frame):
        log.info("Received signal %s, shutting down...", signum)
        stop_event.set()
        for comp in components:
            try:
                if hasattr(comp, "stop"):
                    comp.stop()  # type: ignore[attr-defined]
            except Exception as e:
                log.exception("Error stopping component %s: %s", comp, e)

    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)

    try:
        while not stop_event.is_set():
            time.sleep(1)
    finally:
        log.info("Exit main loop")


if __name__ == "__main__":
    main()

