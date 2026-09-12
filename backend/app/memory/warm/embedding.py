"""Embedding 提供者抽象 + 确定性本地实现。

- EmbeddingProvider：接口，供 store 编码文本。真实现（云 API）在配置
  就绪后接入，如 dashscope / siliconflow / openai-compatible，接口不变。
- DeterministicEmbeddingProvider：纯本地确定性编码（字符 n-gram 特征哈希），
  用于离线开发、测试与 CI——同文本必得同向量，共享字词的文本向量相近，
  足以驱动 warm 层全链路测试；不产生任何网络请求与费用。
"""

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections import Counter

_WS = re.compile(r"\s+")


class EmbeddingProvider(ABC):
    """文本编码抽象。"""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """把一段文本编码为向量。"""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度。"""


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """确定性本地 embedding（n-gram 特征哈希 + L2 归一化）。

    实现要点：
    - 字符 uni-gram + bi-gram 作为特征；
    - 过滤中文高频虚字（的了是很…）——这类字几乎出现在所有句子中，
      会污染相似度（导致无关文本也相近）；
    - md5 哈希到高维桶（默认 256），短文本区分度更好。
    仅用于离线开发/测试/CI，不产生网络请求；真实现接入时替换。
    """

    # 中文高频虚字 / 代词语助词（过滤后特征聚焦实义字词）
    _STOP_CHARS = set(
        "的了是很在我有和就不人都一这中上个也还那要会没她他它吗吧啊哦呀呢么与你"
    )

    def __init__(self, dim: int = 256) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def _features(self, text: str) -> list[str]:
        """字符 uni-gram + bi-gram 特征（去空白、去虚字后按字符切分）。"""
        chars = [ch for ch in _WS.sub("", text) if ch not in self._STOP_CHARS]
        grams = list(chars)
        grams += [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
        return grams

    @staticmethod
    def _hash_to_bucket(token: str, dim: int) -> int:
        """md5 哈希 → 桶下标（确定性、分布均匀）。"""
        digest = hashlib.md5(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % dim

    def embed(self, text: str) -> list[float]:
        counts = Counter(self._features(text))
        vec = [0.0] * self._dim
        for token, freq in counts.items():
            vec[self._hash_to_bucket(token, self._dim)] += freq
        # L2 归一化（空文本返回零向量）
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """两个向量的余弦相似度（均为 L2 归一化时可简化为点积）。"""
    if len(a) != len(b):
        raise ValueError(f"向量维度不一致：{len(a)} vs {len(b)}")
    return sum(x * y for x, y in zip(a, b))


def create_embedding_provider(provider: str) -> EmbeddingProvider:
    """按配置创建 embedding provider。

    当前仅 deterministic（本地假实现，零依赖默认）；
    接入真实实现（dashscope / siliconflow / openai-compatible）后在此注册，
    接口返回不变，store 无需改动。
    """
    name = (provider or "deterministic").strip().lower()
    if name in {"deterministic", "memory", "mock"} or not name:
        return DeterministicEmbeddingProvider()
    if name in {"dashscope", "siliconflow", "openai-compatible"}:
        raise NotImplementedError(
            f"provider「{name}」尚未接入：请在 .env 使用 "
            "EMBEDDING_PROVIDER=deterministic 零依赖运行。"
        )
    raise ValueError(f"未知 embedding provider：{provider!r}")
