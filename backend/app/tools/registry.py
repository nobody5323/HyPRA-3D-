"""工具注册表与执行框架（Agent 行动层）。

设计目标：让大模型能够**真正调用工具办事**（而非仅返回结构化字段）。

调用链（OpenAI tools 协议）：
    LLM(tools=[...]) → tool_calls → registry.execute() → 结果文本回传 → LLM 生成最终回复

关键设计：
- **异常隔离**：工具失败不中断对话——错误信息作为结果回传，模型可自然应对；
- **参数校验**：JSON 参数经 pydantic 校验后才进入 handler；
- **统一 schema**：ToolSpec 自动导出 OpenAI tools 格式，新增工具零胶水代码。
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError


@dataclass
class ToolContext:
    """工具执行时的运行时上下文。

    设计：具体依赖（记忆门面 / 情绪日记库 / SSML 等）统一放在 extras 里，
    使 registry 不依赖任何具体存储类型（保持解耦与可测）。
    """

    companion_id: str
    session_id: str = ""
    user_name: str = "用户"
    extras: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    """一次工具执行的结果。"""

    name: str
    success: bool
    content: str                       # 回传给模型的文本（成功为结果，失败为错误说明）
    data: dict = field(default_factory=dict)   # 结构化结果（供 API 暴露给前端）

    def to_message_content(self) -> str:
        """转成回传给 LLM 的工具消息内容。"""
        return self.content


@dataclass
class ToolSpec:
    """一个可被模型调用的工具。"""

    name: str
    description: str
    parameters: dict                                  # JSON Schema
    handler: Callable[[BaseModel, ToolContext], dict]  # (参数模型, 上下文) → 结构化结果
    args_model: type[BaseModel] | None = None         # 用于参数校验的 pydantic 模型
    requires_confirmation: bool = False               # 是否需要用户确认（预留）
    tags: list[str] = field(default_factory=list)     # 分类标签（供文档/筛选）

    def to_openai_schema(self) -> dict:
        """导出 OpenAI tools 格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """工具注册表：注册、查询、导出 schema、执行。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """注册一个工具（重名报错，避免静默覆盖）。"""
        if spec.name in self._tools:
            raise ValueError(f"工具名重复：{spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict]:
        """全部工具的 OpenAI tools 格式列表。"""
        return [spec.to_openai_schema() for spec in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def execute(
        self,
        name: str,
        arguments: str | dict | None,
        context: ToolContext | None = None,
    ) -> ToolResult:
        """执行工具：解析参数 → 校验 → 调用 handler，全程异常隔离。

        无论失败原因是什么，都返回 ToolResult（success=False）而非抛异常——
        这样模型能拿到错误说明并自然应对，对话不中断。
        """
        spec = self._tools.get(name)
        if spec is None:
            return ToolResult(
                name=name,
                success=False,
                content=f"工具 {name} 不存在，请改用其他方式回应。",
            )

        # ① 解析参数（模型返回的是 JSON 字符串）
        try:
            raw_args = arguments if isinstance(arguments, dict) else json.loads(arguments or "{}")
            if not isinstance(raw_args, dict):
                raise ValueError("参数必须是 JSON 对象")
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            return ToolResult(
                name=name,
                success=False,
                content=f"工具参数解析失败（{exc}）。请检查参数格式后重试。",
            )

        # ② 参数校验
        try:
            if spec.args_model is not None:
                args = spec.args_model.model_validate(raw_args)
            else:
                args = raw_args  # type: ignore[assignment]
        except ValidationError as exc:
            return ToolResult(
                name=name,
                success=False,
                content=f"工具参数不合法：{_format_validation_error(exc)}",
            )

        # ③ 执行（异常隔离）
        try:
            outcome = spec.handler(args, context or ToolContext(companion_id="")) or {}
        except Exception as exc:  # noqa: BLE001 - 工具失败必须被隔离
            return ToolResult(
                name=name,
                success=False,
                content=f"工具执行失败：{type(exc).__name__}: {exc}",
            )

        message = str(outcome.get("message") or "操作已完成。")
        data = {k: v for k, v in outcome.items() if k != "message"}
        return ToolResult(name=name, success=True, content=message, data=data)


def _format_validation_error(exc: ValidationError) -> str:
    """把 pydantic 校验错误压成一行可读说明。"""
    parts = []
    for err in exc.errors()[:3]:
        loc = ".".join(str(x) for x in err.get("loc", ())) or "参数"
        parts.append(f"{loc}: {err.get('msg', '不合法')}")
    return "；".join(parts)
