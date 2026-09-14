# HyPRA 前端

情感陪伴对话 UI + 具身数字人（Next.js App Router + TypeScript + Tailwind）。

## 快速开始

```bash
cd frontend
npm install                       # 国内可加 --registry=https://registry.npmmirror.com
cp .env.local.example .env.local  # 按需修改 NEXT_PUBLIC_API_BASE
npm run dev                       # http://localhost:3000
```

> 需要先启动后端（`cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload`），
> 页面顶部会显示「后端在线 / 未连接」。

## 已实现

### F1：对话产品化

| 能力 | 说明 |
|---|---|
| 对话 UI | 多轮对话、Enter 发送、打字中提示、错误提示 |
| **具身状态机** | 待机 / 聆听中 / 思考中 / 说话中（`hooks/useAvatar.ts`） |
| 字幕 | 消费后端 `speak.display_text`（已剥离 SSML 标签） |
| 情绪视觉 | 情绪标签 + 强度条 + 数字人光效随情绪变化 |
| 文风切换 | 4 种预设（A/B 对比演示用） |
| Agent 工具提示 | 展示「✓ 已记录这次心情」等办事结果 |
| 播报 | 浏览器原生 TTS（零依赖，F1 占位实现） |
| 打断 | 客户端即时打断（中止请求 + 停止播报） |

### F2：魔珐具身驱动 SDK 集成

| 能力 | 说明 |
|---|---|
| **真实 3D 数字人** | 动态加载 `xmovAvatar.js`，SDK 挂载到 `#avatar-container` |
| **SSML 播报** | 把后端 `speak.ssml`（含 KA 动作）交给 `avatar.speak(ssml, true, true)` |
| 语音状态联动 | 监听 `onVoiceStateChange`（voice_start/voice_end）驱动状态机 |
| **自动降级** | 未配置密钥 / 脚本加载失败 / init 失败 → 回退**浏览器 TTS + 占位形象**，演示不中断 |
| 资源释放 | 卸载时调用 `avatar.destroy()`（释放 WebGL 资源） |

**配置方式**：在 `frontend/.env.local` 填入魔珐**驱动应用**密钥（留空即使用浏览器 TTS）：

```ini
NEXT_PUBLIC_XMOV_APP_ID=你的AppID
NEXT_PUBLIC_XMOV_APP_SECRET=你的AppSecret
```

> 页面右上角显示当前渲染方式（「魔珐 SDK」/「浏览器 TTS」）。

## 待实现

- 断线重连（弱网演示）与更细的 SDK 错误提示
- 多模态 Widget 展示（图片 / 字幕组件）

## 目录

```
app/          页面（layout / page / globals.css）
components/   AvatarStage（数字人舞台）/ ChatPanel / SubtitleBar / MoodIndicator / StyleSwitcher
hooks/        useAvatar（具身状态机 + 播报）/ useChatSession（对话编排）
lib/          api.ts（后端接口）/ types.ts（类型定义）
```
