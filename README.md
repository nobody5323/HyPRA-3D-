# HyPRA-3D：打通提示词架构与混合记忆的情感陪伴 3D 交互系统

> 在高速发展的网络情感、日益破碎化的日常生活中，给现代人一个完全符合其幻想的 AI 陪聊助手，
> 化解当代人各方面的压力。

HyPRA 借鉴 [SillyTavern](https://github.com/SillyTavern/SillyTavern) 的提示词工程与记忆体系**思想**，
将「分层提示词架构 + 混合记忆引擎 + 情绪识别 + 3D 数字人驱动」打通为一个完整的情感陪伴 Web 应用。

## ✨ 功能亮点

- **分层提示词（System Prompt）架构**：全局人设 / 动态状态变量（如 `{{current_mood}}`）/ 对话格式分层设计；
  预设内容与代码分离。
- **世界书（World Info）动态注入**：JSON/YAML 条目 + 关键词 / 正则 / 向量三重触发机制，按优先级拼入上下文。
- **混合记忆引擎（热 / 温 / 冷三层）**：
  - 热层：上下文滚动窗口，保留最近 N 轮；
  - 温层：Qdrant 向量库（本地 Docker / 云双模式），对话 Embedding 入库与语义检索（含时间衰减）；
  - 冷层：SQLite/JSON 结构化事实表，回复后由 LLM 自动抽取并更新关键事实（时间、地点、人物关系）+ 增量摘要。
- **RAG + 推理编排**：LangChain / LangGraph 组装——世界书触发 > 向量召回 > 结构化事实 > 摘要 > 滚动窗口。
- **情绪识别与工具调用**：function calling 结构化输出情绪标签，驱动 3D 表情联动与记忆加权。
- **3D 数字人联动**：文本 + 情绪标签 → 魔珐星云 SDK → MP4 / 语音 → 前端播放（可扩展 TTS 沉浸感）。

## 🧠 设计参照

记忆与提示词机制的详细参照说明见 [`docs/sillytavern-memory-design-reference.md`](docs/sillytavern-memory-design-reference.md)，
项目级开发约定见 [`AGENTS.md`](AGENTS.md)。

## 🚀 快速开始

开发模式（零云端依赖可跑通链路）：

```bash
# 后端
cd backend
python -m venv ../.venv && ../.venv/Scripts/pip install -e ".[dev]"
cp .env.example .env    # 默认 mock LLM + 本地 embedding，无需任何 key
../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
# 访问 http://localhost:8000/docs 调 POST /chat 即可对话
```

评审模式（docker compose 一键部署，见 [`docs/deployment.md`](docs/deployment.md)）。

## 🗂 目录结构

    backend/     Python 后端（FastAPI + LangChain/LangGraph + Qdrant + 魔珐星云）
    frontend/    Next.js 前端（对话 UI + 数字人视频播放）
    docs/        设计文档、部署说明、参赛说明、演示脚本
    AGENTS.md    项目开发约定
    LICENSE

## 📄 合规声明

> **本项目借鉴 SillyTavern 架构思想，但底层代码 100% 原创，不受 AGPL-3.0 协议传染。**
> 项目内测试语料 / 世界书 / RAG 语料仅使用自创或公有领域内容。

## 📌 路线图

- [ ] M1 提示词架构（分层 System Prompt + 世界书）
- [ ] M2 混合记忆引擎（热 / 温 / 冷三层）
- [ ] M3 RAG + LangGraph 推理编排
- [ ] M4 情绪识别 + 工具调用
- [ ] M5 魔珐星云 3D 数字人 + TTS
- [ ] M6 100+ 轮长对话压测与记忆调优
- [ ] M7 参赛文档与演示视频

## 📄 许可

本项目基于 [Apache License 2.0](LICENSE) 开源（Copyright 2026 nobody5323）。
**声明：本项目借鉴 SillyTavern 架构思想，底层代码 100% 原创，不受 AGPL-3.0 协议传染。**
