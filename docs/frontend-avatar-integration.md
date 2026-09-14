# 前端接入说明：魔珐星云数字人（M5）

> 面向前端（Next.js）开发者：如何把后端产出的**播报指令**交给魔珐 SDK，
> 让数字人「说人话、带情绪、有动作」。

## 一、整体架构

```
前端发一条用户消息
      ↓  POST /chat
后端（HyPRA）
  ├─ 对话链路：人设 + 世界书 + 记忆 + 文风 → LLM 生成回复
  ├─ 情绪链路：function calling → 情绪标签（label/intensity/facial_expression）
  └─ 播报指令：回复 + 情绪 → SSML（含 KA 动作）
      ↓  响应：{ reply, emotion, speak: { ssml, display_text, ka_action, tone, voice } }
前端
  └─ avatar.speak(speak.ssml, true, true)   ← SDK 内部完成 TTS + 口型 + 表情 + 动作 + 渲染
```

**职责边界**：后端只产出**文本与指令**，渲染与语音由魔珐 SDK 在前端完成。

---

## 二、准备工作：获取 appId / appSecret

1. 登录 [魔珐星云](https://xingyun3d.com/) 控制台
2. 进入**应用中心** → 创建**驱动应用**（选择角色、音色、表演风格）
3. 应用创建后 → **查看密钥** → 复制 **App ID** 与 **App Secret**

> ⚠️ 注意：`/media/speak` 等后端接口使用**同一对密钥**，但走的是服务端签名鉴权
> （X-APP-ID + X-TOKEN），密钥只放在 `backend/.env`，**不要写进前端代码**。

---

## 三、SDK 引入与初始化

```html
<!-- 1. 引入（注意关注版本，以获取最新特性） -->
<script src="https://media.xingyun3d.com/xingyun3d/general/litesdk/xmovAvatar@latest.js"></script>
```

```js
// 2. 创建实例
const avatar = new XmovAvatar({
  containerId: '#avatar-container',
  appId: '<由后端下发或构建时注入>',        // 或用后端签发的临时凭证
  appSecret: '<同上>',
  gatewayServer: 'https://nebula-agent.xingyun3d.com/user/v1/ttsa/session',
  hardwareAcceleration: 'prefer-hardware',
  onWidgetEvent(data) { console.log('Widget 事件:', data) },
});

// 3. 建立连接（进入待机）
await avatar.init();
```

> **安全提示**：`appSecret` 出现在前端属于官方 SDK 的设计；若部署到公网，
> 建议由后端签发**临时凭证/代理**，或限制域名来源。

---

## 四、完整对话流程（推荐写法）

```js
async function sendMessage(userText, sessionId) {
  // ① 调后端：拿到回复 + 情绪 + 播报指令
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: userText, session_id: sessionId, user_name: '小林' }),
  });
  const data = await res.json();

  // ② 渲染字幕 / 更新 UI
  renderSubtitle(data.speak.display_text);

  // ③ 驱动数字人说话（SDK 内部完成 TTS + 口型 + 表情 + KA 动作）
  avatar.speak(data.speak.ssml, /* is_start */ true, /* is_end */ true);

  // ④ 可选：用情绪驱动页面视觉（背景色、光效等）
  applyMoodTheme(data.emotion);   // { label, label_zh, intensity, facial_expression }

  return data;   // { reply, emotion, speak, memory_counts, style, ... }
}
```

### 播报指令字段说明（`/chat` 响应的 `speak` 字段）

| 字段 | 说明 |
|---|---|
| `ssml` | **SSML 播报文本**（含 KA 动作指令），直接传给 `avatar.speak()` |
| `display_text` | 字幕纯文本（已剥离 SSML 标签） |
| `ka_action` | 本次写入的动作标识（如 `comfort`；强度不足时为空） |
| `tone` | 语气描述（如「柔声、放缓」），用于 UI 提示，**不在 SSML 内** |
| `voice` | 音色 ID（`tts_vcn`） |

也可以单独调用：`POST /media/speak`（只生成播报指令，不跑对话链路）。

---

## 五、关键注意事项（官方文档要点）

| # | 注意点 | 说明 |
|---|---|---|
| 1 | **`speak` 不能连续调用** | 上一次 `is_end=true` 之后，需先用 `interactive_idle` 切换状态再播下一句 |
| 2 | **流式播报** | 对接大模型流式输出时：首句 `is_start=true`，末句 `is_end=true`，中间都为 `false`；建议首句积攒一小段内容再发 |
| 3 | **讲话状态** | `onVoiceStateChange` 会抛出 `voice_start` / `voice_end`，用它判断数字人是否在说话 |
| 4 | **资源释放** | 页面卸载前调用 `avatar.destroy()` |
| 5 | **状态** | 支持 `idle` / `interactive_idle` / `speak` 等状态切换 |

### 连续多轮对话的正确写法

```js
async function speakSafely(ssml) {
  // 若正在播报，先打断并回到交互待机，避免 speak 连续调用
  avatar.interrupt?.();
  avatar.setState?.('interactive_idle');
  await waitVoiceEnd(avatar);      // 监听 onVoiceStateChange → voice_end
  avatar.speak(ssml, true, true);
}
```

---

## 六、后端接口速查

| 接口 | 用途 | 说明 |
|---|---|---|
| `POST /chat` | 完整对话 | 返回 `reply` / `emotion` / `speak` / `memory_counts` / `style` |
| `POST /media/speak` | 仅生成播报指令 | 参数：`text` / `emotion` / `intensity` / `voice` / `streaming` |
| `POST /media/avatar` | **扩展路径**：口型/表情/动作**时间轴** | 供自研渲染使用（见下节） |
| `GET /media/audio/{file}` | 音频文件 | 仅扩展路径产生音频时有值 |

---

## 七、扩展路径：可接入任意 3D / 2D 模型

除魔珐 SDK 外，后端还提供**驱动时间轴**（`POST /media/avatar`），
让项目可以接入自研或其它渲染器（Three.js / Live2D / Unity WebGL 等）：

```json
{
  "duration_ms": 3200,
  "visemes": [{ "start_ms": 0, "end_ms": 180, "viseme": "A", "char": "我" }, ...],
  "face":    [{ "start_ms": 0, "end_ms": 300, "expression": "frowning_worry", "intensity": 0.8 }, ...],
  "body":    [{ "start_ms": 0, "end_ms": 1200, "gesture": "lean_in", "intensity": 0.8 }, ...]
}
```

- `visemes`：口型时间轴（10 种口型；若能拿到 TTS 字级时间戳则为**精确对齐**）
- `face`：表情时间轴（来自 M4 情绪链路的 `facial_expression` + `intensity`）
- `body`：动作时间轴（幅度随情绪强度变化）

这套接口是**渲染无关**的，因此同一份后端数据既可驱动魔珐 SDK，也可驱动任意模型。

---

## 八、常见问题

| 现象 | 排查 |
|---|---|
| 报「应用不存在或无法使用」 | 密钥来自**驱动应用**；确认应用已创建并完成配置（角色/音色/表演风格） |
| 数字人不说话 | 检查 `avatar.init()` 是否成功；确认 WebSocket 已连接（`ttsa/session`） |
| 说完一句后第二句没反应 | `speak` 不能连续调用，需先 `interactive_idle`（见第五节） |
| 字幕出现 `kacomfort` 之类乱码 | 前端应使用 `display_text` 字段渲染字幕，而不是自行去标签 |
