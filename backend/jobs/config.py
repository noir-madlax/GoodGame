import os
from dataclasses import dataclass


def _getenv_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "y", "on"}


def _getenv_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _getenv_str(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass
class Settings:
    # Switches (global)
    ENABLE_SCHEDULER: bool = True
    ENABLE_WORKER: bool = True
    ENABLE_API: bool = True

    # Switches (per-lane)
    ENABLE_LANE_EVALUATE: bool = True
    ENABLE_LANE_COMMENTS: bool = True
    ENABLE_LANE_ANALYZE: bool = True
    ENABLE_LANE_AUTHOR: bool = True

    # Scheduler
    # Cron 表达式，默认每5分钟执行一次关键词搜索
    SCHED_SEARCH_CRON: str = "*/5 * * * *"

    # Worker
    WORKER_POLL_INTERVAL_SEC: int = 2
    WORKER_EVAL_CONCURRENCY: int = 1
    WORKER_COMMENTS_CONCURRENCY: int = 1
    WORKER_ANALYZE_CONCURRENCY: int = 1
    WORKER_AUTHOR_CONCURRENCY: int = 1
    MAX_ATTEMPTS: int = 5
    RUNNING_TIMEOUT_MIN: int = 15

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    API_RELOAD: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    # Gemini
    GEMINI_API_KEY_ANALYZE: str = ""
    GEMINI_API_KEY_SCREENING: str = ""

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            ENABLE_SCHEDULER=_getenv_bool("ENABLE_SCHEDULER", True),
            ENABLE_WORKER=_getenv_bool("ENABLE_WORKER", True),
            ENABLE_API=_getenv_bool("ENABLE_API", True),
            ENABLE_LANE_EVALUATE=_getenv_bool("ENABLE_LANE_EVALUATE", True),
            ENABLE_LANE_COMMENTS=_getenv_bool("ENABLE_LANE_COMMENTS", True),
            ENABLE_LANE_ANALYZE=_getenv_bool("ENABLE_LANE_ANALYZE", True),
            ENABLE_LANE_AUTHOR=_getenv_bool("ENABLE_LANE_AUTHOR", True),
            SCHED_SEARCH_CRON=_getenv_str("SCHED_SEARCH_CRON", "*/5 * * * *"),
            WORKER_POLL_INTERVAL_SEC=_getenv_int("WORKER_POLL_INTERVAL_SEC", 2),
            WORKER_EVAL_CONCURRENCY=_getenv_int("WORKER_EVAL_CONCURRENCY",1),
            WORKER_COMMENTS_CONCURRENCY=_getenv_int("WORKER_COMMENTS_CONCURRENCY",1),
            WORKER_ANALYZE_CONCURRENCY=_getenv_int("WORKER_ANALYZE_CONCURRENCY",1),
            WORKER_AUTHOR_CONCURRENCY=_getenv_int("WORKER_AUTHOR_CONCURRENCY",1),
            MAX_ATTEMPTS=_getenv_int("MAX_ATTEMPTS", 5),
            RUNNING_TIMEOUT_MIN=_getenv_int("RUNNING_TIMEOUT_MIN", 15),
            API_HOST=_getenv_str("API_HOST", "0.0.0.0"),
            API_PORT=_getenv_int("API_PORT", 8000),
            API_WORKERS=_getenv_int("API_WORKERS", 1),
            API_RELOAD=_getenv_bool("API_RELOAD", False),
            LOG_LEVEL=_getenv_str("LOG_LEVEL", "INFO"),
            GEMINI_API_KEY_ANALYZE=_getenv_str("GEMINI_API_KEY_ANALYZE", ""),
            GEMINI_API_KEY_SCREENING=_getenv_str("GEMINI_API_KEY_SCREENING", ""),
        )

