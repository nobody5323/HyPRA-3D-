"""Mock LLM：无 key 的占位实现（开发/测试/演示兜底）。

不调用任何外部服务，根据最后一条 user 消息做**关键词共情**，生成确定性的、
符合「苏澄」温柔基调的占位回复。真实 key 接入后，chat 流程无需改动即可
切换 provider（见 factory.create_llm_provider）。

设计取舍：不把用户原文直接嵌进回复（读起来破碎），改用情绪/话题关键词
匹配 + 通用承接话术，输出更自然、更适合演示。
"""

from app.llm.base import ChatMessage, LLMProvider

# 关键词 → 共情话术（按序匹配，首个命中生效）
_KEYWORD_REPLIES: list[tuple[tuple[str, ...], str]] = [
    (
        ("失眠", "睡不着", "熬夜", "做梦"),
        "听起来你最近休息得不太好，睡不着的夜晚总是格外难熬。"
        "我在这儿陪着，你想说说今晚在想什么吗？",
    ),
    (
        ("压力", "焦虑", "崩溃", "累", "疲惫", "撑不住"),
        "能感觉到这段时间你扛了挺多，辛苦了。"
        "不用急着解决什么，先在这儿喘口气也行。",
    ),
    (
        ("难过", "伤心", "哭", "委屈", "失落"),
        "嗯，我在听着。难过的时候不必急着好起来，"
        "我陪你待一会儿，慢慢说。",
    ),
    (
        ("妈妈", "爸爸", "家人", "父母", "孩子"),
        "家里的事总是牵动人心，你愿意的话，"
        "可以多说一些——你现在的感受，比事情本身更重要。",
    ),
    (
        ("工作", "老板", "辞职", "同事", "加班"),
        "工作带来的疲惫常常藏在心里最深处。"
        "你最近是在为哪件事耗神？我听着呢。",
    ),
    (
        ("谢谢", "感谢"),
        "不用客气，能陪你说说话，我也很安心。",
    ),
]

# 未命中任何关键词时的通用承接话术
_DEFAULT_REPLY = (
    "我在这儿听着呢。不用急着把话说清楚，"
    "想到哪儿说到哪儿就好——你现在最想聊的是什么？"
)


class MockLLMProvider(LLMProvider):
    """确定性占位实现（关键词共情，无网络请求）。"""

    name = "mock"

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        for keywords, reply in _KEYWORD_REPLIES:
            if any(word in last_user for word in keywords):
                return reply
        return _DEFAULT_REPLY
