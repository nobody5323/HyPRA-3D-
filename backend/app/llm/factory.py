"""LLM 提供商工厂：按配置创建 provider 实例。

新接入真实 provider（dashscope / siliconflow / openai-compatible）时：
1. 在 llm/ 下新增实现模块（实现 LLMProvider）；
2. 在本工厂注册 name → 构造逻辑。
上层（chat 流程）只依赖 LLMProvider 接口，不感知具体实现。
"""

from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider


def create_llm_provider(
    provider: str,
    *,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> LLMProvider:
    """按名称创建 LLM provider。

    参数:
        provider: mock | dashscope | siliconflow | openai-compatible；
        api_key / model / base_url: 真实 provider 的接入参数
            （mock 忽略；接入真实实现后使用）。
    """
    name = (provider or "mock").strip().lower()
    if name == "mock" or not name:
        return MockLLMProvider()
    if name in {"dashscope", "siliconflow", "openai-compatible"}:
        # TODO: 接入真实云端实现（需在 .env 配置 key / model / base_url）
        raise NotImplementedError(
            f"provider「{name}」尚未接入：请先实现 llm/ 下的云端实现，"
            "或在 .env 使用 LLM_PROVIDER=mock 无 key 运行。"
        )
    raise ValueError(f"未知 LLM provider：{provider!r}")
