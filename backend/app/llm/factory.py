"""LLM 提供商工厂：按配置创建 provider 实例。

支持的 provider：
- mock                本地占位实现（无 key，默认）
- dashscope           阿里百炼（Qwen）
- siliconflow         硅基流动
- openai-compatible   任意 OpenAI 兼容端点（需 LLM_BASE_URL）

上层（LangGraph 节点 / chat 路由）只依赖 LLMProvider 接口。
"""

from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider

# 走 OpenAI 兼容实现（openai SDK）的 provider 名
_OPENAI_COMPATIBLE_NAMES = {"dashscope", "siliconflow", "openai-compatible"}


def create_llm_provider(
    provider: str,
    *,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
    timeout: float = 60.0,
    enable_thinking: bool | None = None,
    http_client=None,
) -> LLMProvider:
    """按名称创建 LLM provider。

    参数:
        provider: mock | dashscope | siliconflow | openai-compatible；
        api_key / model / base_url: 云端接入参数（mock 忽略）；
        timeout: 单次请求超时（秒）；prompt 长时需放宽；
        enable_thinking: 推理模型的思考开关（False 可显著提速；None 不传该参数）；
        http_client: 自定义 httpx 客户端（测试注入用）。
    """
    name = (provider or "mock").strip().lower()
    if name == "mock" or not name:
        return MockLLMProvider()
    if name in _OPENAI_COMPATIBLE_NAMES:
        return OpenAICompatibleProvider(
            name=name,
            api_key=api_key,
            model=model or "qwen2.5-7b-instruct",
            base_url=base_url or None,
            timeout=timeout,
            enable_thinking=enable_thinking,
            http_client=http_client,
        )
    raise ValueError(f"未知 LLM provider：{provider!r}")
