"""温层存储工厂：按配置创建 WarmMemoryStore 实现。

双模式（配置驱动）：
- backend="memory"  → InMemoryWarmStore（零依赖，默认，开发/测试/演示）
- backend="qdrant"  → QdrantWarmStore
    · local_path=":memory:" / "<目录>"（本地嵌入式，无 Docker）
    · url=...（评审 docker 内网 http://qdrant:6333 / 开发云 Qdrant）

上层（chat / 记忆门面）只依赖 WarmMemoryStore 接口。
"""

from app.memory.warm.base import WarmMemoryStore
from app.memory.warm.embedding import EmbeddingProvider
from app.memory.warm.inmemory_store import InMemoryWarmStore
from app.memory.warm.qdrant_store import QdrantWarmStore


def create_warm_store(
    backend: str = "memory",
    *,
    provider: EmbeddingProvider | None = None,
    url: str | None = None,
    api_key: str | None = None,
    local_path: str | None = None,
) -> WarmMemoryStore:
    """按 backend 创建温层存储。

    参数:
        backend: memory（默认，零依赖）| qdrant；
        provider: embedding 提供者（缺省用确定性本地实现）；
        url / api_key / local_path: qdrant 后端的连接参数。
    """
    name = (backend or "memory").strip().lower()
    if name in {"memory", "inmemory", "in-memory"}:
        return InMemoryWarmStore(provider)
    if name in {"qdrant", "qdrant-local"}:
        # qdrant-local 便捷别名：未给 url 时走本地嵌入式内存模式
        if name == "qdrant-local" and not url and not local_path:
            local_path = ":memory:"
        return QdrantWarmStore(
            provider,
            url=url,
            api_key=api_key,
            local_path=local_path,
        )
    raise ValueError(f"未知温层后端：{backend!r}（可选 memory | qdrant）")
