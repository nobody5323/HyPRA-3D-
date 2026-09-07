"""worldbook 注入编排：把 matcher 命中结果拼成「场景补充」块。

消费 matcher 已按 priority 排序的命中列表，用 token 预算做贪心注入：
- 顺着 priority 降序逐条尝试放入；
- 累计估算 token 超出 budget 的条目跳过，记入 skipped（低优先者先被裁）；
- 预算不足时不硬塞，保证 prompt 不超限。
"""

from collections.abc import Iterable

from app.prompts.renderer import estimate_tokens
from app.worldbook.models import WorldBookEntry


def assemble_worldbook_section(
    hits: Iterable[WorldBookEntry],
    budget: int,
) -> tuple[str, list[WorldBookEntry]]:
    """把命中条目编排成注入文本。

    返回:
        (注入文本, 因预算被跳过的条目列表)。
        无命中或全部被跳过时，注入文本为空字符串。
    """
    # 防御性重排：即使调用方传入无序列表，也按 priority 降序消费
    ordered = sorted(hits, key=lambda e: e.priority, reverse=True)

    blocks: list[str] = []
    skipped: list[WorldBookEntry] = []
    used = 0
    for entry in ordered:
        block = f"[{entry.title}]\n{entry.content}"
        cost = estimate_tokens(block)
        if used + cost > budget:
            skipped.append(entry)
            continue
        blocks.append(block)
        used += cost

    return "\n\n".join(blocks), skipped
