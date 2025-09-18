"""
FastAPI 依赖注入模块

提供全局依赖项，如配置、数据库连接等。
复用现有的配置和日志系统。
"""

from fastapi import Depends
from jobs.config import Settings
from jobs.logger import get_logger

# 全局设置实例，复用现有配置系统
_settings: Settings | None = None

log = get_logger(__name__)


def get_settings() -> Settings:
    """获取全局配置实例"""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
        log.debug("Loaded settings for API")
    return _settings


def get_logger_for_request():
    """为请求提供日志记录器"""
    return get_logger("api.request")
