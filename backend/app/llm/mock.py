"""Mock LLM：无 key 的占位实现（开发/测试/演示兜底）。

不调用任何外部服务，仅根据最后一条 user 消息生成确定性的、符合
「苏澄」温柔基调的占位回复。真实 key 接入后，chat 流程无需改动即可
切换 provider（见 factory.create_llm_provider）。
"""

from app.llm.base import ChatMessage, LLMProvider

# 占位回复模板：温柔承接 + 引导（与苏澄人设一致的基调）
_REPLY_TPL = (
    "我听到了，{topic}。想先陪你把这份心情放一放——"
    "如果愿意，可以再多说一点，我在这儿听着。"
)


class MockLLMProvider(LLMProvider):
    """确定性占位实现。"""

    name = "mock"

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        if not messages:
            return _REPLY_TPL.format(topic="你现在")
        # 取最后一条 user 消息的前 12 字作为话题锚点（去空白）
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "你现在",
        )
        topic = "".join(last_user.split())[:12] or "你现在"
        return _REPLY_TPL.format(topic=topic)
