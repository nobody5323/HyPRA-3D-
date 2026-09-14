"""工具注册表测试：注册、schema 导出、参数校验、异常隔离。"""

import json

import pytest
from pydantic import BaseModel, Field

from app.tools.registry import ToolContext, ToolRegistry, ToolSpec


class _Args(BaseModel):
    text: str = Field(min_length=1)
    count: int = Field(default=1, ge=1, le=5)


def _registry() -> ToolRegistry:
    registry = ToolRegistry()

    def _echo(args: _Args, ctx: ToolContext) -> dict:
        return {"message": f"收到 {args.text}×{args.count}", "echo": args.text}

    registry.register(
        ToolSpec(
            name="echo",
            description="回显文本",
            parameters=_Args.model_json_schema(),
            args_model=_Args,
            handler=_echo,
            tags=["test"],
        )
    )
    return registry


def _ctx() -> ToolContext:
    return ToolContext(companion_id="c1", session_id="s1")


# ---------- 注册与查询 ----------


def test_register_and_get() -> None:
    registry = _registry()
    assert registry.get("echo") is not None
    assert registry.names() == ["echo"]
    assert len(registry) == 1


def test_duplicate_name_raises() -> None:
    registry = _registry()
    with pytest.raises(ValueError, match="重复"):
        registry.register(
            ToolSpec(
                name="echo", description="x", parameters={}, handler=lambda a, c: {}
            )
        )


def test_schemas_openai_format() -> None:
    schema = _registry().schemas()[0]
    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "echo"
    assert fn["description"] == "回显文本"
    assert "text" in fn["parameters"]["properties"]


# ---------- 执行 ----------


def test_execute_success_with_json_string() -> None:
    result = _registry().execute("echo", json.dumps({"text": "你好", "count": 2}), _ctx())
    assert result.success is True
    assert "你好" in result.content
    assert result.data["echo"] == "你好"


def test_execute_accepts_dict_arguments() -> None:
    result = _registry().execute("echo", {"text": "hi"}, _ctx())
    assert result.success is True


def test_execute_unknown_tool() -> None:
    result = _registry().execute("no-such-tool", "{}", _ctx())
    assert result.success is False
    assert "不存在" in result.content


def test_execute_invalid_json() -> None:
    result = _registry().execute("echo", "{不是 json", _ctx())
    assert result.success is False
    assert "解析失败" in result.content


def test_execute_validation_error() -> None:
    """缺必填字段 / 越界 → 返回可读的参数错误（不抛异常）。"""
    result = _registry().execute("echo", json.dumps({"count": 99}), _ctx())
    assert result.success is False
    assert "不合法" in result.content


def test_execute_handler_exception_isolated() -> None:
    """handler 抛异常必须被隔离（对话不能中断）。"""
    registry = ToolRegistry()

    def _boom(args, ctx) -> dict:
        raise RuntimeError("模拟外部服务不可用")

    registry.register(
        ToolSpec(name="boom", description="x", parameters={}, handler=_boom)
    )
    result = registry.execute("boom", "{}", _ctx())
    assert result.success is False
    assert "工具执行失败" in result.content
    assert "模拟外部服务不可用" in result.content


def test_execute_without_context_does_not_crash() -> None:
    """未传上下文时使用空上下文（工具内部自行处理缺依赖）。"""
    result = _registry().execute("echo", {"text": "x"})
    assert result.success is True


def test_empty_handler_outcome() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="noop", description="x", parameters={}, handler=lambda a, c: None)
    )
    result = registry.execute("noop", "{}", _ctx())
    assert result.success is True
    assert result.content                      # 有默认文案，不返回空串
