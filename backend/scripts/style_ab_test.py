"""文风 A/B 对比脚本（真实模型，需 backend/.env 配好 key）。

用途：验证「风格系统」对模型表达的实际影响——同一句用户输入，
分别用「无风格（调前基线）」与各文风预设生成回复，直接对比效果。

用法（在 backend 目录下）：
    ../.venv/Scripts/python.exe scripts/style_ab_test.py
    ../.venv/Scripts/python.exe scripts/style_ab_test.py --text "我很累" --sleep 20
    ../.venv/Scripts/python.exe scripts/style_ab_test.py --styles brief-direct,classical-elegant --no-baseline

注意：
- 每次调用真实模型较慢（本机实测约 30 秒/次），脚本默认在两次请求间留出间隔；
- 云端端点可能限流（连续请求后挂起），遇超时请增大 --sleep 或稍后重试。
"""

import argparse
import sys
import tempfile
import time
from pathlib import Path

# 允许以 `python scripts/style_ab_test.py` 方式运行（把 backend 加入 sys.path）
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.graph.chat_graph import build_chat_graph  # noqa: E402
from app.graph.nodes import ChatNodes  # noqa: E402
from app.llm.factory import create_llm_provider  # noqa: E402
from app.memory.cold.sqlite_store import SqliteColdStore  # noqa: E402
from app.memory.store import MemoryStore  # noqa: E402
from app.memory.warm.inmemory_store import InMemoryWarmStore  # noqa: E402
from app.prompts.persona.loader import load_builtin_presets  # noqa: E402
from app.prompts.style.loader import load_builtin_styles  # noqa: E402
from app.worldbook.loader import load_builtin_entries  # noqa: E402

PERSONA_ID = "therapist-elder-sister"
DEFAULT_TEXT = "我最近总是失眠，压力好大，感觉快撑不住了"
DEFAULT_STYLES = "modern-conversational,brief-direct,classical-elegant,gentle-elaborate"


def generate(provider, presets, entries, styles, persona_id: str, text: str, style_id: str) -> str:
    """用指定文风生成一次回复（每次使用独立记忆，避免相互污染）。"""
    tmp_dir = Path(tempfile.mkdtemp())
    nodes = ChatNodes(
        presets=presets,
        entries=entries,
        memory_store=MemoryStore(SqliteColdStore(db_path=tmp_dir / "m.db"), InMemoryWarmStore()),
        llm_provider=provider,
        styles=styles if style_id else {},
        default_style_id=style_id or "",
        model_name=getattr(provider, "model", ""),
    )
    graph = build_chat_graph(nodes)
    state = {
        "session_id": "ab-test",
        "companion_id": persona_id,
        "persona_id": persona_id,
        "user_name": "小林",
        "user_input": text,
        "history": [],
        "turn_index": 1,
        "state_vars": {},
        "style_id": style_id or "",
        "warnings": [],
    }
    result = graph.invoke(state)
    meta = result.get("sampling")
    if meta is not None:
        print(f"  [采样] {meta.to_provider_kwargs()}  (档位: {meta.profile_id})")
    print(f"  [情绪] {(result.get('emotion').label_zh if result.get('emotion') else '-')}")
    return result.get("reply", "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="文风 A/B 对比（真实模型）")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="用户输入")
    parser.add_argument("--styles", default=DEFAULT_STYLES, help="逗号分隔的风格 id 列表")
    parser.add_argument("--no-baseline", action="store_true", help="跳过「无风格」基线")
    parser.add_argument("--sleep", type=float, default=10.0, help="两次请求间隔秒数（防空限流）")
    args = parser.parse_args()

    settings = get_settings()
    if settings.llm_provider == "mock":
        print("[!] 当前 LLM_PROVIDER=mock，请在 backend/.env 配置真实 provider 与 key。")
        return 1

    provider = create_llm_provider(
        settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout,
    )
    presets, entries, styles = (
        load_builtin_presets(),
        load_builtin_entries(),
        load_builtin_styles(),
    )

    print(f"模型: {settings.llm_model} | 输入: {args.text}")
    print("=" * 64)

    cases: list[tuple[str, str]] = []
    if not args.no_baseline:
        cases.append(("① 无风格（调前基线）", ""))
    for style_id in [s.strip() for s in args.styles.split(",") if s.strip()]:
        preset = styles.get(style_id)
        cases.append((f"◆ {preset.name if preset else style_id}", style_id))

    for index, (label, style_id) in enumerate(cases):
        if index > 0:
            time.sleep(args.sleep)  # 请求间隔，降低被限流概率
        print(f"\n===== {label} =====")
        try:
            reply = generate(provider, presets, entries, styles, PERSONA_ID, args.text, style_id)
            print(reply[:600])
        except Exception as exc:  # 单次失败不影响后续对比
            print(f"  [失败] {type(exc).__name__}: {str(exc)[:120]}")

    print("\n" + "=" * 64 + "\n对比完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
