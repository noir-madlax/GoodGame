"""
FastAPI REST API 模块

提供对外的 REST API 接口，集成现有的后台任务系统。
支持帖子查询、分析状态管理、健康检查等功能。
"""

from .server import APIServer

__all__ = ["APIServer"]
