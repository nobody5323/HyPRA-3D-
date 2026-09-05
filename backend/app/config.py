"""应用配置：从 backend/.env 读取运行参数与云端密钥。

红线：云端密钥（百炼 / 硅基流动 / 魔珐星云 / Qdrant Cloud）一律只放
backend/.env（已被 .gitignore 排除），不入库。格式参考 backend/.env.example。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 本文件位于 backend/app/config.py，.env 约定在 backend/.env
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """全局配置。新增配置项时在此声明字段，并在 .env / .env.example 同步。"""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 基础 ----
    app_name: str = "HyPRA Backend"
    app_version: str = "0.1.0"
    debug: bool = False

    # ---- 外部服务密钥占位（真实值放 backend/.env）----
    # 示例：
    # qdrant_url: str = ""
    # qdrant_api_key: str = ""
    # dashscope_api_key: str = ""
    # siliconflow_api_key: str = ""
    # moya_app_id: str = ""


def get_settings() -> Settings:
    """返回单例配置（FastAPI 依赖注入用）。"""
    return Settings()
