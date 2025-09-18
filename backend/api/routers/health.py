"""
健康检查 API 路由

提供系统状态检查、组件状态监控等功能。
"""

import time
from datetime import datetime
from fastapi import APIRouter, Depends
from jobs.config import Settings
from jobs.logger import get_logger
from ..dependencies import get_settings

router = APIRouter()
log = get_logger(__name__)


@router.get("/")
async def health_check(settings: Settings = Depends(get_settings)):
    """基础健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "scheduler": settings.ENABLE_SCHEDULER,
            "worker": settings.ENABLE_WORKER,
            "api": settings.ENABLE_API
        }
    }


@router.get("/detailed")
async def detailed_health_check(settings: Settings = Depends(get_settings)):
    """详细健康检查"""
    start_time = time.time()
    
    # 基础信息
    health_info = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_check_duration_ms": 0,
        "components": {
            "scheduler": {
                "enabled": settings.ENABLE_SCHEDULER,
                "cron": settings.SCHED_SEARCH_CRON if settings.ENABLE_SCHEDULER else None
            },
            "worker": {
                "enabled": settings.ENABLE_WORKER,
                "poll_interval": settings.WORKER_POLL_INTERVAL_SEC if settings.ENABLE_WORKER else None,
                "concurrency": {
                    "evaluate": settings.WORKER_EVAL_CONCURRENCY,
                    "comments": settings.WORKER_COMMENTS_CONCURRENCY,
                    "analyze": settings.WORKER_ANALYZE_CONCURRENCY
                } if settings.ENABLE_WORKER else None
            },
            "api": {
                "enabled": settings.ENABLE_API,
                "host": settings.API_HOST,
                "port": settings.API_PORT
            }
        },
        "lanes": {
            "evaluate": settings.ENABLE_LANE_EVALUATE,
            "comments": settings.ENABLE_LANE_COMMENTS,
            "analyze": settings.ENABLE_LANE_ANALYZE
        },
        "config": {
            "max_attempts": settings.MAX_ATTEMPTS,
            "timeout_minutes": settings.RUNNING_TIMEOUT_MIN,
            "log_level": settings.LOG_LEVEL
        }
    }
    
    # 计算检查耗时
    health_info["uptime_check_duration_ms"] = round((time.time() - start_time) * 1000, 2)
    
    log.debug("Health check completed in %.2fms", health_info["uptime_check_duration_ms"])
    
    return health_info


@router.get("/ready")
async def readiness_check(settings: Settings = Depends(get_settings)):
    """就绪状态检查（用于 K8s readiness probe）"""
    # 检查关键组件是否启用
    ready = True
    components = []
    
    if settings.ENABLE_SCHEDULER:
        components.append("scheduler")
    if settings.ENABLE_WORKER:
        components.append("worker")
    if settings.ENABLE_API:
        components.append("api")
    
    return {
        "ready": ready,
        "components": components,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check():
    """存活状态检查（用于 K8s liveness probe）"""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }
