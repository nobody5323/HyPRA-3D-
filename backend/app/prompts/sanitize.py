"""模型输出清理（兜底）。

问题背景（实测）：
1. 模型（尤其推理模型）会把 markdown 格式与 emoji 写进回复；
2. 更严重的是**自我纠正泄漏**——例如「🌱（注：虽然不能加 emoji 但是语气可以很软）
   → actually no emoji allowed per instructions! Corrected below.」，
   即模型在正文里写下它对规则的检查与纠正过程。

风格预设已用**正向指令**要求纯文字表达（第一道防线），本模块做最后兜底：
剥离格式标记、emoji，并删除明显的元评论行——只保留对用户说的话。
"""

import re

# 元评论整行（模型对规则/指令的自述与自我纠正）——整行删除
_META_LINE = re.compile(
    r"^.*(?:"
    r"emoji|Emoji|EMOJI|instructions|Instruction|corrected|Corrected|"
    r"按指令|按要求|已按要求|已修正|虽然不能|不能加|规则检查|自我纠正"
    r").*$",
    re.MULTILINE,
)
# 行首列表符号：- / * / + / • / 1. / 1、 / 1)
_LIST_MARK = re.compile(r"^[ \t]*(?:[-*+•]|\d+[.、)])\s+", re.MULTILINE)
# 标题符号
_HEADING = re.compile(r"^[ \t]*#{1,6}\s+", re.MULTILINE)
# 分隔线
_DIVIDER = re.compile(r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$", re.MULTILINE)
# 行内代码
_INLINE_CODE = re.compile(r"`([^`]+)`")
# emoji / 符号表情（常见 Unicode 区间）
_EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff\u2b00-\u2bff\ufe0f]"
)


def sanitize_reply(text: str) -> str:
    """清理 assistant 回复：剥离格式标记、emoji 与元评论行。

    保守策略：只做「去标记」与「删元评论行」，不改写任何正常语句。
    """
    if not text:
        return text

    cleaned = _META_LINE.sub("", text)          # 先删元评论（避免干扰后续处理）
    cleaned = _DIVIDER.sub("", cleaned)
    cleaned = _HEADING.sub("", cleaned)
    cleaned = _LIST_MARK.sub("", cleaned)
    cleaned = _INLINE_CODE.sub(r"\1", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "")   # 强调标记
    cleaned = _EMOJI.sub("", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)            # 行尾空白
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)            # 多余空行
    return cleaned.strip()


def has_meta_comment(text: str) -> bool:
    """文本是否含元评论（供测试与调试）。"""
    return bool(_META_LINE.search(text or ""))
