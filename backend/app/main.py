"""HyPRA 后端入口：FastAPI 应用工厂 + 健康检查。

路由按模块拆分（chat / media），在此统一注册到 app。
跨域：前端（Next.js，默认 3000）与后端（8000）不同源，必须配置 CORS，
否则浏览器会拦截请求（表现为前端一直显示「后端未连接」）。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat_router, media_router
from app.config import cors_origin_list, get_settings


def create_app() -> FastAPI:
    """应用工厂：创建 FastAPI 实例并注册中间件与路由。"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # 跨域配置（来源可用 CORS_ORIGINS 覆盖；"*" 表示允许全部）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origin_list(settings),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """健康检查：确认服务与配置加载正常。"""
        return {"status": "ok", "app": settings.app_name}

    app.include_router(chat_router)
    app.include_router(media_router)
    return app


app = create_app()
