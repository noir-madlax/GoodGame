"""
FastAPI 中间件配置

包含 CORS、请求日志、错误处理等中间件。
"""

import time
import traceback
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jobs.logger import get_logger

log = get_logger(__name__)


def setup_middleware(app: FastAPI):
    """设置所有中间件"""
    
    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境需要限制具体域名
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # 全局异常处理中间件
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.exception("Unhandled exception in API: %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": "An unexpected error occurred",
                "path": str(request.url.path)
            }
        )
    
    # 请求日志和性能监控中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        # 记录请求开始
        log.debug("API Request: %s %s", request.method, request.url)
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应
            log.info("API %s %s - %s (%.3fs)", 
                    request.method, 
                    request.url.path, 
                    response.status_code, 
                    process_time)
            
            # 添加性能头
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            log.error("API %s %s - ERROR (%.3fs): %s", 
                     request.method, 
                     request.url.path, 
                     process_time, 
                     str(e))
            raise
    
    # 健康检查路径的简化日志
    @app.middleware("http")
    async def health_check_filter(request: Request, call_next):
        # 对健康检查路径使用 DEBUG 级别日志
        if request.url.path.startswith("/health"):
            # 临时降低日志级别
            original_level = log.level
            try:
                response = await call_next(request)
                return response
            finally:
                pass  # 保持原有日志级别
        else:
            return await call_next(request)
