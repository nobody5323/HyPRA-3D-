"""情绪工具测试：标签体系、结构化解析、正则兜底。"""

import json

import pytest

from app.tools.emotion import (
    EMOTION_FACIAL_EXPRESSIONS,
    EMOTION_LABELS_ZH,
    EMOTION_TOOL_NAME,
    EmotionLabel,
    EmotionResult,
    build_emotion_tool,
    extract_emotion_fallback,
    has_emotion_keyword,
    parse_emotion_result,
)


# ---------- 标签体系 ----------


def test_eight_labels_defined() -> None:
    assert len(EmotionLabel) == 8
    assert {e.value for e in EmotionLabel} == {
        "happy", "calm", "sad", "anxious", "tired", "angry", "surprised", "neutral",
    }


def test_labels_have_zh_and_expression_mapping() -> None:
    for label in EmotionLabel:
        assert label.value in EMOTION_LABELS_ZH, f"{label.value} 缺中文映射"
        assert label.value in EMOTION_FACIAL_EXPRESSIONS, f"{label.value} 缺表情映射"


def test_result_derived_properties() -> None:
    result = EmotionResult(reply="我在", emotion=EmotionLabel.ANXIOUS)
    assert result.label_zh == "焦虑"
    assert result.facial_expression == "frowning_worry"


# ---------- 工具 schema ----------


def test_tool_schema_shape() -> None:
    tool = build_emotion_tool()
    assert tool["type"] == "function"
    fn = tool["function"]
    assert fn["name"] == EMOTION_TOOL_NAME
    props = fn["parameters"]["properties"]
    assert set(props) >= {"reply", "emotion", "intensity", "confidence", "evidence"}
    assert props["emotion"]["enum"] == [e.value for e in EmotionLabel]
    assert fn["parameters"]["required"] == ["reply", "emotion"]


# ---------- 解析 ----------


def test_parse_valid_arguments() -> None:
    raw = json.dumps(
        {"reply": "我在听着", "emotion": "anxious", "intensity": 0.8,
         "confidence": 0.9, "evidence": "提到失眠"},
        ensure_ascii=False,
    )
    result = parse_emotion_result(raw)
    assert result is not None
    assert result.reply == "我在听着"
    assert result.emotion == EmotionLabel.ANXIOUS
    assert result.intensity == 0.8
    assert result.source == "llm"
    assert result.label_zh == "焦虑"


def test_parse_invalid_json_returns_none() -> None:
    assert parse_emotion_result("{不是合法 json") is None
    assert parse_emotion_result("") is None


def test_parse_missing_reply_returns_none() -> None:
    assert parse_emotion_result(json.dumps({"emotion": "sad"})) is None


def test_parse_out_of_range_intensity_returns_none() -> None:
    raw = json.dumps({"reply": "x", "emotion": "sad", "intensity": 1.8})
    assert parse_emotion_result(raw) is None


def test_parse_unknown_label_returns_none() -> None:
    raw = json.dumps({"reply": "x", "emotion": "excited"})
    assert parse_emotion_result(raw) is None


def test_parse_minimal_arguments() -> None:
    """只有必填字段也应能解析（其余用默认值）。"""
    result = parse_emotion_result(json.dumps({"reply": "嗯", "emotion": "calm"}))
    assert result is not None
    assert result.emotion == EmotionLabel.CALM
    assert 0.0 <= result.intensity <= 1.0


# ---------- 兜底提取 ----------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("我最近总是失眠，压力好大", EmotionLabel.ANXIOUS),
        ("今天好累啊，撑不住了", EmotionLabel.TIRED),
        ("我妈身体不好我很担心", EmotionLabel.ANXIOUS),
        ("今天太开心了！", EmotionLabel.HAPPY),
        ("气死我了", EmotionLabel.ANGRY),
        ("没想到会这样", EmotionLabel.SURPRISED),
        ("今天挺平静的", EmotionLabel.CALM),
        ("嗯嗯好的", EmotionLabel.NEUTRAL),
    ],
)
def test_fallback_extraction(text: str, expected: EmotionLabel) -> None:
    result = extract_emotion_fallback(text)
    assert result.emotion == expected
    assert result.source == "fallback"
    assert result.confidence <= 0.5  # 兜底置信度低


def test_fallback_never_fails() -> None:
    """任意文本都应返回结果（永不抛异常、永不空）."""
    for text in ["", "?!", "12345", "……"]:
        result = extract_emotion_fallback(text)
        assert result.emotion is not None
        assert result.reply


def test_fallback_intensity_by_label() -> None:
    """焦虑/难过类强度应高于中性。"""
    assert extract_emotion_fallback("我很焦虑").intensity > extract_emotion_fallback("嗯").intensity


def test_has_emotion_keyword() -> None:
    assert has_emotion_keyword("我好累") is True
    assert has_emotion_keyword("今天周三") is False
