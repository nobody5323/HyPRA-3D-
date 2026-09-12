"""应用配置：从 backend/.env 读取运行参数与云端密钥。

红线：云端密钥（百炼 / 硅基流动 / 魔珐星云 / Qdrant）一律只放
backend/.env（已被 .gitignore 排除），不入库。格式参考 backend/.env.example。

双模式（配置驱动，代码零硬编码）：
- 开发：向量库用云 Qdrant、模型用云 key；
- 评审：docker compose 本地 Qdrant（QDRANT_URL=http://qdrant:6333），
  embedding/LLM 由评审在 .env 自行填入（provider/key/model 均走配置）。
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

    # ---- 冷层（本地 SQLite）----
    # 数据库文件位置（相对 backend 运行目录；默认 backend/data/memory.db）
    cold_db_path: str = "data/memory.db"

    # ---- 记忆召回参数（三层聚合）----
    memory_fact_limit: int = 5      # 冷层事实召回条数
    memory_top_k: int = 3           # 温层语义召回条数
    memory_block_budget: int = 300  # 记忆块 token 预算
    memory_extractor: str = "rule"  # 回复后抽取器：rule（无 key）| llm（待接入）

    # ---- PromptManager 预算（M3 分层组装）----
    worldbook_budget: int = 400       # 世界书注入块预算
    prompt_history_budget: int = 800  # 滚动窗口预算
    prompt_total_budget: int = 2000   # 提示词总量预算（超出按优先级裁剪）

    # ---- 温层（向量库：memory 本地假实现 | qdrant）----
    # 评审用本地 docker：http://qdrant:6333（容器内互联）；开发用云 URL
    warm_backend: str = "memory"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # ---- LLM 提供商（评审自填：dashscope | siliconflow | openai-compatible | mock）----
    llm_provider: str = "mock"  # 默认 mock：无 key 也可跑通对话链路（占位回复）
    llm_api_key: str = ""
    llm_model: str = "qwen2.5-7b-instruct"
    llm_base_url: str = ""  # openai-compatible 时必填，如 https://api.example.com/v1

    # ---- Embedding（deterministic 本地假实现 | dashscope | siliconflow | openai-compatible）----
    embedding_provider: str = "deterministic"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-v3"
    embedding_base_url: str = ""


def get_settings() -> Settings:
    """返回单例配置（FastAPI 依赖注入用）。"""
    return Settings()
