"""记忆门面：聚合热 / 温 / 冷三层，按固定顺序产出记忆上下文。

设计参照①的固定顺序（本门面负责「世界书之后、滚动窗口之前」这一段）：
    世界书触发 > **向量召回 > 结构化事实 > 摘要** > 滚动窗口

三层职责（参照⑦）：
- 热层：会话滚动窗口 —— 由 session.ChatTurn 承载，不经本门面；
- 温层：语义回忆 —— warm store 按相似度 + 时间衰减召回；
- 冷层：长期事实（importance 优先）与滚动摘要 —— cold store。

容错：任一层不可用（如 Qdrant 未启动）时记 warning 并降级，不阻断对话。
"""

from dataclasses import dataclass, field

from app.memory.cold.extractor import RuleBasedExtractor, TurnExtractor
from app.memory.cold.models import Fact, Summary
from app.memory.cold.store import ColdMemoryStore
from app.memory.warm.base import SearchResult, WarmMemoryStore
from app.prompts.renderer import estimate_tokens

# 默认参数（可经 config 覆盖）
DEFAULT_FACT_LIMIT = 5        # 冷层事实召回条数
DEFAULT_MEMORY_TOP_K = 3      # 温层语义召回条数
DEFAULT_BLOCK_BUDGET = 300    # 记忆块 token 预算

MEMORY_SECTION = "记忆回忆"


@dataclass
class MemoryContext:
    """一次记忆召回的结果（三层聚合）。"""

    facts: list[Fact] = field(default_factory=list)
    memories: list[SearchResult] = field(default_factory=list)
    summary: Summary | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        """三层皆无有效内容。"""
        has_summary = bool(self.summary and self.summary.content.strip())
        return not (self.facts or self.memories or has_summary)

    def to_prompt_block(self, *, budget: int = DEFAULT_BLOCK_BUDGET) -> str:
        """拼成可注入 prompt 的记忆块（按 召回 > 事实 > 摘要 顺序）。

        budget 用尽时按上述顺序停止追加（保证高优先内容先入）。
        """
        if self.empty:
            return ""

        tokens_used = estimate_tokens(f"[{MEMORY_SECTION}]")
        lines: list[str] = [f"[{MEMORY_SECTION}]"]

        def _try_append(header: str, items: list[str]) -> None:
            nonlocal tokens_used
            if not items:
                return
            pending: list[str] = []
            for item in items:
                cost = estimate_tokens(item)
                if tokens_used + cost > budget:
                    break
                pending.append(item)
                tokens_used += cost
            if pending:
                lines.append(header)
                lines.extend(pending)

        # ① 向量召回（温层）
        _try_append("相关回忆：", [f"- {r.record.text}" for r in self.memories])
        # ② 结构化事实（冷层）
        _try_append("已知事实：", [f"- {f.summary_text}" for f in self.facts])
        # ③ 摘要（冷层）
        if self.summary and self.summary.content.strip():
            _try_append("会话摘要：", [f"- {self.summary.content}"])

        return "\n".join(lines) if len(lines) > 1 else ""


class MemoryStore:
    """三层记忆门面（召回 + 写入）。"""

    def __init__(
        self,
        cold: ColdMemoryStore,
        warm: WarmMemoryStore,
        *,
        fact_limit: int = DEFAULT_FACT_LIMIT,
        memory_top_k: int = DEFAULT_MEMORY_TOP_K,
        block_budget: int = DEFAULT_BLOCK_BUDGET,
        extractor: TurnExtractor | None = None,
    ) -> None:
        self.cold = cold
        self.warm = warm
        self.fact_limit = fact_limit
        self.memory_top_k = memory_top_k
        self.block_budget = block_budget
        self.extractor = extractor or RuleBasedExtractor()

    def recall(self, companion_id: str, query: str) -> MemoryContext:
        """按 query 召回三层记忆（任一层异常降级为 warning）。"""
        warnings: list[str] = []
        memories: list[SearchResult] = []
        facts: list[Fact] = []
        summary: Summary | None = None

        # ① 温层语义召回
        try:
            memories = self.warm.search(companion_id, query, top_k=self.memory_top_k)
        except Exception as exc:  # 存储不可用不应阻断对话
            warnings.append(f"温层召回失败（已降级）：{exc}")

        # ② 冷层事实 + ③ 摘要
        try:
            facts = self.cold.list_facts(companion_id, limit=self.fact_limit)
            # importance 优先，其次按时间新近
            facts.sort(key=lambda f: (f.importance, f.created_at), reverse=True)
        except Exception as exc:
            warnings.append(f"冷层事实读取失败（已降级）：{exc}")

        try:
            summary = self.cold.get_summary(companion_id)
        except Exception as exc:
            warnings.append(f"冷层摘要读取失败（已降级）：{exc}")

        return MemoryContext(
            facts=facts,
            memories=memories,
            summary=summary,
            warnings=warnings,
        )

    # ---------- 写入（回复后事件驱动，参照③④）----------

    def remember_turn(
        self,
        companion_id: str,
        user_text: str,
        assistant_text: str,
        *,
        turn_index: int = 0,
        source: str = "",
        subject: str = "用户",
    ) -> dict[str, int]:
        """回复完成后的一次写入：抽取事实 → 向量入库 → 摘要增量并入。

        返回写入统计（facts / memory / summary），异常降级为 warnings 不阻断。
        """
        stats = {"facts": 0, "memory": 0, "summary": 0}

        # ① 事件驱动抽取（结构化事实 + 摘要行）
        try:
            result = self.extractor.extract(
                user_text,
                assistant_text,
                companion_id=companion_id,
                source=source,
                subject=subject,
            )
        except Exception:  # 抽取失败不影响对话
            result = None

        # ② 冷层：事实入库（去重靠 store 主键）
        if result is not None:
            for fact in result.facts:
                try:
                    self.cold.save_fact(companion_id, fact)
                    stats["facts"] += 1
                except Exception:
                    break

        # ③ 温层：本轮用户话语向量化入库（供后续语义召回）
        try:
            self.warm.add(
                companion_id,
                user_text,
                metadata={"turn": turn_index, "source": source},
            )
            stats["memory"] = 1
        except Exception:
            pass

        # ④ 冷层：摘要滚动增量并入（设计参照④）
        if result is not None and result.summary_line:
            try:
                self.cold.append_summary(companion_id, turn_index, result.summary_line)
                stats["summary"] = 1
            except Exception:
                pass

        return stats
