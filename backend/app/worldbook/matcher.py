"""世界书触发匹配器（关键词 + 正则）。

规则（对齐设计参照 1.2）：
- 仅 enabled 的条目参与匹配；
- 关键词：任一命中即触发；默认不区分大小写，条目可自行声明 case_sensitive；
- 正则：条目 regex 列表中任一模式 search 命中即触发（与关键词互为补充，
  任一通道命中都算条目命中）；
- 命中结果按 priority 降序排列，供后续 PromptManager 注入编排使用。
"""

import re
from collections.abc import Iterable

from app.worldbook.models import WorldBookEntry


def _keys_hit(entry: WorldBookEntry, text: str) -> bool:
    """关键词通道：任一关键词出现在文本中。"""
    if not entry.keys:
        return False
    if entry.case_sensitive:
        return any(key in text for key in entry.keys)
    lowered = text.lower()
    return any(key.lower() in lowered for key in entry.keys)


def _regex_hit(entry: WorldBookEntry, text: str) -> bool:
    """正则通道：任一模式 search 命中。"""
    return any(re.search(pattern, text) for pattern in entry.regex)


def match_entries(
    entries: Iterable[WorldBookEntry],
    text: str,
    *,
    include_disabled: bool = False,
) -> list[WorldBookEntry]:
    """对给定文本匹配世界书条目，返回按 priority 降序的命中列表。

    参数:
        include_disabled: 是否把 enabled=False 的条目也纳入匹配
            （默认 False：停用条目直接跳过）。
    """
    hits: list[WorldBookEntry] = []
    for entry in entries:
        if not include_disabled and not entry.enabled:
            continue
        if _keys_hit(entry, text) or _regex_hit(entry, text):
            hits.append(entry)
    # 稳定排序：priority 高者在前；同优先级保持加载顺序
    hits.sort(key=lambda e: e.priority, reverse=True)
    return hits
