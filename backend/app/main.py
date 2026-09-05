"""HyPRA 后端入口：FastAPI 应用工厂 + 健康检查。

后续按模块拆分路由（chat / memory / media），在此统一注册到 app。
"""

from fastapi import FastAPI

from app.config import get_settings


def create_app() -> FastAPI:
    """应用工厂：创建 FastAPI 实例并注册路由。"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """健康检查：确认服务与配置加载正常。"""
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
