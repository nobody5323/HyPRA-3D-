"""温层（语义向量记忆）数据模型与存储接口。

隔离：每个陪伴对象独立 collection（参照⑧），由 companion_id 区分。
后端可替换：当前实现 InMemoryWarmStore（inmemory_store.py）用于离线开发与测试；
接入 Qdrant 时实现同一接口（qdrant_store.py，配置 URL 即可云/本地切换）。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryRecord:
    """一条已入库的向量记忆。"""

    memory_id: str
    companion_id: str
    text: str
    created_at: datetime
    metadata: dict = field(default_factory=dict)
    vector: list[float] = field(default_factory=list, repr=False)


@dataclass
class SearchResult:
    """一次语义检索的命中结果。"""

    record: MemoryRecord
    score: float = 0.0          # 组合分（相似度 × 时间衰减）
    raw_similarity: float = 0.0  # 纯余弦相似度（调试/对比用）


class WarmMemoryStore(ABC):
    """温层向量记忆存储抽象。

    add/search/delete 均以 companion_id 隔离命名空间；
    search 支持时间衰减重排参数（参照⑥），默认半衰期与衰减强度可调。
    """

    @abstractmethod
    def add(
        self,
        companion_id: str,
        text: str,
        *,
        metadata: dict | None = None,
        memory_id: str | None = None,
    ) -> str:
        """入库一条记忆（内部完成 embedding），返回 memory_id。"""

    @abstractmethod
    def search(
        self,
        companion_id: str,
        query: str,
        *,
        top_k: int = 5,
        half_life_days: float = 30.0,
        decay_exponent: float = 1.0,
        now: datetime | None = None,
    ) -> list[SearchResult]:
        """语义检索：query 编码后与集合内记忆算相似度，
        按「相似度 × 时间衰减」组合分排序返回 top_k。
        now 参数仅供测试注入时间。
        """

    @abstractmethod
    def delete(self, companion_id: str, memory_id: str) -> bool:
        """删除一条记忆，返回是否删除成功。"""

    @abstractmethod
    def count(self, companion_id: str) -> int:
        """某陪伴对象当前的记忆条数。"""
