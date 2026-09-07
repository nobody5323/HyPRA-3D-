"""确定性 embedding 测试。"""

from app.memory.warm.embedding import (
    DeterministicEmbeddingProvider,
    cosine_similarity,
)


def test_deterministic_same_text_same_vector() -> None:
    provider = DeterministicEmbeddingProvider()
    a = provider.embed("小林喜欢下雨天")
    b = provider.embed("小林喜欢下雨天")
    assert a == b


def test_dimension() -> None:
    provider = DeterministicEmbeddingProvider(dim=128)
    assert provider.dimension == 128
    assert len(provider.embed("任意文本")) == 128


def test_unit_norm() -> None:
    provider = DeterministicEmbeddingProvider()
    vec = provider.embed("苏澄的咨询室在梧桐树下")
    norm2 = sum(v * v for v in vec)
    assert abs(norm2 - 1.0) < 1e-6


def test_similar_texts_close_vectors() -> None:
    """共享字词多的文本余弦相似度应明显高于无关文本。"""
    provider = DeterministicEmbeddingProvider()
    a = provider.embed("我最近总是失眠睡不着")
    b = provider.embed("晚上失眠很严重怎么办")   # 共享 失眠/晚 等
    c = provider.embed("今天天气晴朗适合郊游")   # 无关
    sim_ab = cosine_similarity(a, b)
    sim_ac = cosine_similarity(a, c)
    assert sim_ab > sim_ac
    assert sim_ac < 0.5  # 无关文本相似度应较低


def test_empty_text_zero_vector() -> None:
    provider = DeterministicEmbeddingProvider()
    vec = provider.embed("   ")
    assert all(v == 0.0 for v in vec)


def test_unknown_tokens_do_not_break() -> None:
    """各种字符（含符号）不应抛异常。"""
    provider = DeterministicEmbeddingProvider()
    vec = provider.embed("Emoji 🐱 测试 123 ABC！")
    assert len(vec) == provider.dimension
