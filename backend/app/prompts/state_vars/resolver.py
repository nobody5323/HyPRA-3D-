"""状态变量宏替换器：把 {{variable}} 替换为运行时值。

规则：
- 命中运行时 context → 用其值；
- 未命中 context 但存在注册表定义 → 用默认值并记一条 warning（不静默失败）；
- 完全未知的变量名 → 保留原文并记 warning（避免误伤模板中的普通文本）。
"""

import re
from collections.abc import Mapping

from app.prompts.state_vars.definitions import get_state_var

# 匹配 {{ 变量名 }}，变量名限定为字母数字下划线
_VAR_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


def resolve_template(
    text: str,
    context: Mapping[str, str] | None = None,
) -> tuple[str, list[str]]:
    """替换文本中的 {{变量}}，返回 (替换后文本, 告警列表)。"""
    context = context or {}
    warnings: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in context:
            return context[name]
        definition = get_state_var(name)
        if definition is not None:
            warnings.append(f"状态变量 {{{{{name}}}}} 未提供，已用默认值「{definition.default}」")
            return definition.default
        warnings.append(f"未知状态变量 {{{{{name}}}}}，已保留原文")
        return match.group(0)

    resolved = _VAR_PATTERN.sub(_replace, text)
    return resolved, warnings
