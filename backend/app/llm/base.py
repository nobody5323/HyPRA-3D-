"""LLM 提供商抽象与消息模型。

provider 通过工厂按配置创建（factory.py）：
- mock                本地占位实现（无 key 可跑通链路，测试/演示用）
- dashscope           阿里百炼（Qwen）
- siliconflow         硅基流动
- openai-compatible   任何 OpenAI 兼容端点（评委自接任意模型）

接入真实 provider 只需实现 LLMProvider 接口并在工厂注册。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

# 消息角色（与渲染管道 to_messages 输出对齐）
Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    """一条对话消息。"""

    role: Role = Field(description="消息角色")
    content: str = Field(description="消息内容")


@dataclass
class ToolCall:
    """一次 function calling 的工具调用。"""

    name: str          # 工具名
    arguments: str     # 参数（JSON 字符串，由调用方解析）
    call_id: str = ""  # 工具调用 id（多轮工具对话时需要回传）


class LLMProvider(ABC):
    """LLM 对话生成抽象。"""

    #: 提供商名称（mock / dashscope / siliconflow / openai-compatible）
    name: str

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """给定消息列表生成 assistant 回复文本。

        参数:
            messages: system + 历史 + user 的完整消息列表；
            temperature: 采样温度；
            max_tokens: 回复长度上限（None 用模型默认）。
        """

    def chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[dict],
        *,
        tool_choice: str | dict = "auto",
        temperature: float = 0.7,
    ) -> list[ToolCall] | None:
        """function calling：请求模型以工具调用形式返回结构化结果。

        返回:
            工具调用列表；模型未触发工具调用或本 provider 不支持时返回 None
            （调用方据此降级到 chat() + 正则兜底）。

        默认实现返回 None（不支持）；支持 function calling 的 provider 覆盖本方法。
        """
        return None
