"""情绪识别工具：function calling 结构化输出（M4）。

统一情绪标签：识别「用户此刻的情绪」，一处产出、三处消费——
    ① 状态变量 {{current_mood}}（人设动态注入，下一轮生效）
    ② 记忆加权（冷层事实 emotion_tag + 温层召回加权，参照⑤）
    ③ 3D 数字人表情联动（M5 消费，做共情式回应表情）

主通道：LLM function calling（本模块提供工具 schema 与结果解析）；
兜底通道：关键词/正则提取（模型未返回结构化输出时启用，保证不空转）。
"""

import json
import re
from enum import Enum

from pydantic import BaseModel, Field


class EmotionLabel(str, Enum):
    """情绪标签（8 类，覆盖情感陪伴高频场景）。"""

    HAPPY = "happy"
    CALM = "calm"
    SAD = "sad"
    ANXIOUS = "anxious"
    TIRED = "tired"
    ANGRY = "angry"
    SURPRISED = "surprised"
    NEUTRAL = "neutral"


# 英文标签 → 中文（供 {{current_mood}} 状态变量与前端展示）
EMOTION_LABELS_ZH: dict[str, str] = {
    EmotionLabel.HAPPY.value: "开心",
    EmotionLabel.CALM.value: "平静",
    EmotionLabel.SAD.value: "难过",
    EmotionLabel.ANXIOUS.value: "焦虑",
    EmotionLabel.TIRED.value: "疲惫",
    EmotionLabel.ANGRY.value: "生气",
    EmotionLabel.SURPRISED.value: "惊讶",
    EmotionLabel.NEUTRAL.value: "平静",
}

# 情绪 → 3D 表情键（M5 数字人联动使用；M4 仅产出数据）
EMOTION_FACIAL_EXPRESSIONS: dict[str, str] = {
    EmotionLabel.HAPPY.value: "smile",
    EmotionLabel.CALM.value: "gentle",
    EmotionLabel.SAD.value: "downcast",
    EmotionLabel.ANXIOUS.value: "frowning_worry",
    EmotionLabel.TIRED.value: "droopy_eyes",
    EmotionLabel.ANGRY.value: "frown",
    EmotionLabel.SURPRISED.value: "wide_eyes",
    EmotionLabel.NEUTRAL.value: "default",
}

# function calling 工具名
EMOTION_TOOL_NAME = "report_reply_and_emotion"


class EmotionResult(BaseModel):
    """一次结构化输出：助手回复 + 用户情绪判定。"""

    reply: str = Field(description="给用户的回复正文")
    emotion: EmotionLabel = Field(default=EmotionLabel.NEUTRAL, description="用户此刻情绪")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="情绪强度 0-1")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="判定置信度 0-1")
    evidence: str = Field(default="", description="判定依据（简短，便于调试与展示）")
    source: str = Field(default="llm", description="来源：llm（结构化输出）| fallback（正则兜底）")

    @property
    def label_zh(self) -> str:
        """中文标签（写入 current_mood 状态变量用）。"""
        return EMOTION_LABELS_ZH.get(self.emotion.value, "平静")

    @property
    def facial_expression(self) -> str:
        """3D 表情键（M5 消费）。"""
        return EMOTION_FACIAL_EXPRESSIONS.get(self.emotion.value, "default")


def build_emotion_tool() -> dict:
    """OpenAI function calling 工具定义（tools 参数格式）。"""
    return {
        "type": "function",
        "function": {
            "name": EMOTION_TOOL_NAME,
            "description": (
                "在回复用户的同时，判定用户此刻的情绪。"
                "必须先给出回复，再根据用户最新发言判断情绪类别与强度。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reply": {
                        "type": "string",
                        "description": "给用户的回复正文（保持角色人设与语气）",
                    },
                    "emotion": {
                        "type": "string",
                        "enum": [label.value for label in EmotionLabel],
                        "description": "用户此刻的情绪标签",
                    },
                    "intensity": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "情绪强度（0 轻微，1 强烈）",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "情绪判定置信度",
                    },
                    "evidence": {
                        "type": "string",
                        "description": "判定依据（引用用户原话中的关键词，简短）",
                    },
                },
                "required": ["reply", "emotion"],
            },
        },
    }


def parse_emotion_result(raw_arguments: str) -> EmotionResult | None:
    """解析工具调用的 arguments（JSON 字符串）→ EmotionResult。

    解析失败（非法 JSON / 缺字段 / 取值越界）返回 None，由调用方降级。
    """
    try:
        payload = json.loads(raw_arguments)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or not payload.get("reply"):
        return None
    try:
        result = EmotionResult.model_validate({**payload, "source": "llm"})
    except Exception:
        return None
    return result


# ---------- 兜底通道：关键词 / 正则 ----------

# (情绪标签, 正则模式元组, 基础强度) —— 按顺序匹配，首个命中即返回
# 用正则而非子串：支持程度副词（「压力好大」「太累了」）与常见变体。
_FALLBACK_RULES: list[tuple[EmotionLabel, tuple[str, ...], float]] = [
    (
        EmotionLabel.ANXIOUS,
        (
            r"焦虑", r"紧张", r"担心", r"害怕", r"不安", r"心慌", r"慌",
            r"压力(?:好|很|特别|太|挺)?大", r"失眠", r"睡不着", r"睡不着", r"睡不好",
        ),
        0.7,
    ),
    (
        EmotionLabel.SAD,
        (r"难过", r"伤心", r"想哭", r"哭了?", r"委屈", r"失恋", r"失落", r"沮丧", r"低落"),
        0.7,
    ),
    (
        EmotionLabel.TIRED,
        (r"累", r"疲惫", r"好困", r"撑不住", r"没力气", r"精疲力尽", r"熬夜", r"没睡"),
        0.6,
    ),
    (
        EmotionLabel.ANGRY,
        (r"生气", r"愤怒", r"气死", r"火大", r"讨厌", r"烦死", r"烦躁"),
        0.7,
    ),
    (
        EmotionLabel.HAPPY,
        (r"开心", r"高兴", r"太好了", r"哈哈", r"兴奋", r"喜欢", r"谢谢", r"顺利"),
        0.6,
    ),
    (
        EmotionLabel.SURPRISED,
        (r"没想到", r"居然", r"竟然", r"惊讶", r"天啊"),
        0.6,
    ),
    (
        EmotionLabel.CALM,
        (r"平静", r"还好", r"挺好的", r"放松", r"踏实"),
        0.5,
    ),
]

# 兜底时用于生成的最小回复（模型不可用时保证不空转）
FALLBACK_REPLY = "我在这儿，听着呢。你愿意多说一点吗？"


def extract_emotion_fallback(text: str) -> EmotionResult:
    """关键词/正则兜底提取（模型未返回结构化输出时启用）。

    永不失败：未命中任何规则时返回 NEUTRAL 情绪 + 通用承接回复。
    """
    for label, patterns, intensity in _FALLBACK_RULES:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return EmotionResult(
                    reply=FALLBACK_REPLY,
                    emotion=label,
                    intensity=intensity,
                    confidence=0.4,  # 兜底通道置信度低，便于后续被 LLM 结果覆盖
                    evidence=f"关键词命中：{match.group(0)}",
                    source="fallback",
                )
    return EmotionResult(
        reply=FALLBACK_REPLY,
        emotion=EmotionLabel.NEUTRAL,
        intensity=0.5,
        confidence=0.3,
        evidence="未命中情绪关键词",
        source="fallback",
    )


def has_emotion_keyword(text: str) -> bool:
    """文本是否含任一情绪关键词（供调试/测试用）。"""
    return any(
        re.search(pattern, text)
        for _, patterns, _ in _FALLBACK_RULES
        for pattern in patterns
    )
