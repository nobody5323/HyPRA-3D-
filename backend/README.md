# HyPRA 后端

分层提示词 + 混合记忆（热/温/冷）+ 情绪识别 + 数字人驱动的 FastAPI 服务。

## 目录

    app/
      api/           # FastAPI 路由（chat / memory / media，按需新增）
      config.py      # 配置（backend/.env 读取，密钥不入库）
      main.py        # 应用工厂 + /health
    tests/           # pytest

> 更多分层（prompts / worldbook / memory / rag / llm / tools / digital_human）
> 随里程碑逐步落位，详见项目根目录 AGENTS.md。

## 本地开发

```bash
# 在项目根目录创建虚拟环境并安装（示例，在 backend/ 内执行）
cd backend
python -m venv ../.venv
../.venv/Scripts/pip install -e ".[dev]"
```

运行：

```bash
uvicorn app.main:app --reload --port 8000
```

测试：

```bash
pytest
```
