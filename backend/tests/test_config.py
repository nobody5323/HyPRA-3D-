"""配置层测试。"""

from app.config import Settings


def test_defaults_zero_dependency() -> None:
    """默认配置应零依赖可跑：mock LLM + 本地确定性 embedding + memory 向量后端。"""
    settings = Settings()
    assert settings.llm_provider == "mock"
    assert settings.embedding_provider == "deterministic"
    assert settings.warm_backend == "memory"
    assert settings.qdrant_api_key == ""  # 无 key 默认


def test_env_override(tmp_path, monkeypatch) -> None:
    """环境变量应能覆盖默认值。"""
    import os

    os.environ["LLM_PROVIDER"] = "dashscope"
    os.environ["QDRANT_URL"] = "https://cloud.example.com:6333"
    settings = Settings()
    assert settings.llm_provider == "dashscope"
    assert settings.qdrant_url == "https://cloud.example.com:6333"
    # 清理环境变量避免影响其他测试
    os.environ.pop("LLM_PROVIDER", None)
    os.environ.pop("QDRANT_URL", None)
