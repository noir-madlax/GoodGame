import uvicorn
import threading
from fastapi import FastAPI, Depends
from jobs.config import Settings
from jobs.logger import get_logger
from .routers import health, import_analyze
from .middleware import setup_middleware
from .dependencies import get_settings
from .schemas import BaseResponse


log = get_logger(__name__)


class APIServer:
    """FastAPI 服务器组件，集成到现有的多线程架构中"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.app = self._create_app()
        self._stop_event = threading.Event()

    def _create_app(self) -> FastAPI:
        """创建 FastAPI 应用实例"""
        app = FastAPI(
            title="Backend API",
            description="后台任务系统 REST API",
            version="1.0.0",
            dependencies=[Depends(get_settings)]
        )

        # 设置中间件
        setup_middleware(app)

        # 注册路由
        app.include_router(health.router, prefix="/health", tags=["health"])
        app.include_router(import_analyze.router, tags=["import"])

        # 根路径
        @app.get("/", response_model=BaseResponse[dict])
        async def root():
            return BaseResponse.ok({
                "message": "Backend API is running",
                "version": "1.0.0",
                "docs": "/docs",
            })

        return app

    def run_forever(self) -> None:
        """在当前线程中运行 API 服务器"""
        try:
            log.info("Starting API server on %s:%s", self.settings.API_HOST, self.settings.API_PORT)

            # 配置 uvicorn
            config = uvicorn.Config(
                app=self.app,
                host=self.settings.API_HOST,
                port=self.settings.API_PORT,
                log_config=None,  # 使用我们自己的日志配置
                access_log=False,  # 通过中间件记录访问日志
                reload=self.settings.API_RELOAD,
                workers=1  # 多线程模式下只能用 1 个 worker
            )

            server = uvicorn.Server(config)

            # 在当前线程中运行
            server.run()

        except Exception as e:
            log.exception("API server error: %s", e)
        finally:
            log.info("API server stopped")

    def stop(self) -> None:
        """停止 API 服务器"""
        log.info("Stopping API server...")
        self._stop_event.set()
        # 注意：uvicorn.Server 的优雅停止需要在实际部署中进一步完善
