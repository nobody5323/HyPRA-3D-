# HyPRA 后端

分层提示词 + 混合记忆（热/温/冷）+ 情绪识别 + 数字人驱动的 FastAPI 服务。

## 目录

    app/
      api/           # FastAPI 路由（chat 已落地，memory/media 按需新增）
      session/       # 会话：上下文 + 内存存储（热层滚动窗口载体）
      prompts/       # 分层 System Prompt：人设预设 / 状态变量 / 世界书注入编排 / 渲染管道
      worldbook/     # 世界书：条目模型 / YAML 加载 / 关键词+正则触发匹配
      memory/
        cold/        # 冷层：SQLite 结构化事实表 + 滚动增量摘要
        warm/        # 温层：WarmMemoryStore 接口 + 时间衰减 + 确定性 embedding + 内存实现
      llm/           # LLM 抽象：接口 / mock（零依赖默认）/ 工厂（云 provider 待接入）
      config.py      # 配置（backend/.env 读取，双模式：本地 Docker 优先，云可切）
      main.py        # 应用工厂 + /health + 路由注册
    tests/           # pytest（91 项，全离线无外部依赖）
    data/            # 本地 SQLite 数据库（gitignore，不入库）

> 开发/评审双模式与一键部署见根目录 [docs/deployment.md](../docs/deployment.md)。

## 本地开发（零云端 key 可跑通链路）

```bash
# 在项目根目录创建虚拟环境并安装（在 backend/ 内执行）
cd backend
python -m venv ../.venv
../.venv/Scripts/pip install -e ".[dev]"
cp .env.example .env    # 默认 mock LLM + 本地 embedding，无需任何 key
```

运行：

```bash
../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

验证：

```bash
curl http://localhost:8000/health
```

测试：

```bash
../.venv/Scripts/python -m pytest
```
