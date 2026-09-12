"""OpenAI 兼容 LLM provider（基于 openai 官方 SDK）。

覆盖国内主流托管 API（均提供 OpenAI 兼容端点）：
- dashscope     阿里百炼（Qwen 系列）
- siliconflow   硅基流动
- openai-compatible  任意兼容端点（评审自接其他模型）

设计要点：
- 依赖注入 http_client，便于用 httpx.MockTransport 做**无网络测试**；
- base_url 未显式提供时按 provider 名取默认值；
- 真实 key 一律从 backend/.env 读取，不入库。
"""

from openai import OpenAI

from app.llm.base import ChatMessage, LLMProvider, ToolCall

# 各提供商默认 base_url（可被 .env 的 LLM_BASE_URL 覆盖）
DEFAULT_BASE_URLS: dict[str, str] = {
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
}


class OpenAICompatibleProvider(LLMProvider):
    """通过 openai SDK 调用任意 OpenAI 兼容端点。"""

    def __init__(
        self,
        *,
        name: str = "openai-compatible",
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        http_client=None,
    ) -> None:
        """初始化。

        参数:
            name: 提供商名（dashscope / siliconflow / openai-compatible）；
            api_key: 云端 key（来自 .env）；
            model: 模型名，如 qwen2.5-7b-instruct；
            base_url: 端点地址，缺省按 name 取默认值；
            timeout / max_retries: 网络超时与重试（SDK 自带退避重试）；
            http_client: 自定义 httpx 客户端（测试注入用）。
        """
        resolved_base = base_url or DEFAULT_BASE_URLS.get(name, "")
        if not resolved_base:
            raise ValueError(
                f"provider「{name}」需要显式 base_url（请设置 LLM_BASE_URL）"
            )
        if not api_key:
            raise ValueError(f"provider「{name}」缺少 api_key（请设置 LLM_API_KEY）")

        self.name = name
        self.model = model
        self._client = OpenAI(
            api_key=api_key,
            base_url=resolved_base,
            timeout=timeout,
            max_retries=max_retries,
            http_client=http_client,
        )

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """调用 chat/completions，返回助手回复文本。"""
        kwargs: dict = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = self._client.chat.completions.create(**kwargs)
        if not response.choices:
            return ""
        return response.choices[0].message.content or ""

    def chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[dict],
        *,
        tool_choice: str | dict = "auto",
        temperature: float = 0.7,
    ) -> list[ToolCall] | None:
        """function calling（OpenAI tools 协议）。

        模型未触发工具调用（如老模型不支持）时返回 None，由调用方降级。
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
        )
        if not response.choices:
            return None
        message = response.choices[0].message
        if not message.tool_calls:
            return None
        return [
            ToolCall(
                name=call.function.name,
                arguments=call.function.arguments,
                call_id=getattr(call, "id", "") or "",
            )
            for call in message.tool_calls
        ]
