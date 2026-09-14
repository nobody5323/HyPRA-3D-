"use client";

/**
 * HyPRA 主页面：左侧数字人舞台 + 右侧对话与情绪面板。
 *
 * 数字人渲染 provider（自动选择 + 自动降级）：
 *   - 已配置凭证（**页面「数字人设置」填写** 或 构建时环境变量）→ **魔珐具身驱动 SDK**（真实 3D）
 *   - 未配置 / SDK 加载失败 / init 失败 → **浏览器原生 TTS + 占位形象**（演示不中断）
 *
 * 凭证可在页面上直接填写（存 localStorage，即时生效，无需重新构建）。
 */

import { useEffect, useRef, useState } from "react";

import { AvatarSettings } from "@/components/AvatarSettings";
import { AvatarStage } from "@/components/AvatarStage";
import { ChatPanel } from "@/components/ChatPanel";
import { MoodIndicator } from "@/components/MoodIndicator";
import { StyleSwitcher } from "@/components/StyleSwitcher";
import { SubtitleBar } from "@/components/SubtitleBar";
import { useBrowserAvatar, useXmovAvatar } from "@/hooks/useAvatar";
import { useAvatarCredentials } from "@/hooks/useAvatarCredentials";
import { useChatSession } from "@/hooks/useChatSession";
import { getHealth } from "@/lib/api";

const CONTAINER_ID = "avatar-container"; // 用于 DOM 元素的 id
const CONTAINER_SELECTOR = "#avatar-container"; // 传给 SDK 的 CSS 选择器（兜底）

export default function HomePage() {
  const { credentials, source, configured, revision } = useAvatarCredentials();
  const [provider, setProvider] = useState<"xmov" | "browser">("browser");
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  // 凭证可用性变化 → 切换渲染方式（配置好即启用真实数字人）
  useEffect(() => {
    setProvider(credentials ? "xmov" : "browser");
    if (credentials) setAvatarError(null); // 重新配置后清掉旧错误
  }, [credentials, revision]);

  const browserAvatar = useBrowserAvatar();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const xmovAvatar = useXmovAvatar(CONTAINER_SELECTOR, {
    credentials,
    enabled: provider === "xmov",
    revision,
    containerRef,
    onUnavailable: (reason) => {
      setAvatarError(reason); // 保留失败原因（降级后仍可见）
      setProvider("browser");
    },
  });
  const avatar = provider === "xmov" ? xmovAvatar : browserAvatar;

  const session = useChatSession(avatar);

  useEffect(() => {
    getHealth().then((health) => setBackendOnline(health?.status === "ok"));
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 p-4 lg:p-6">
      <header className="relative flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">
            HyPRA · <span className="text-sky-300">苏澄</span>
          </h1>
          <p className="text-xs text-slate-500">
            情感陪伴 3D 交互系统 · 分层提示词 + 混合记忆 + 情绪链路 + Agent 行动层
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-3 py-1 text-[11px] ring-1 ${
              provider === "xmov"
                ? "bg-violet-500/15 text-violet-300 ring-violet-400/30"
                : "bg-slate-800 text-slate-300 ring-white/10"
            }`}
          >
            {provider === "xmov" ? "魔珐 SDK" : "浏览器 TTS"}
          </span>
          <span
            className={`rounded-full px-3 py-1 text-[11px] ring-1 ${
              backendOnline === null
                ? "bg-slate-800 text-slate-400 ring-white/10"
                : backendOnline
                  ? "bg-emerald-500/15 text-emerald-300 ring-emerald-400/30"
                  : "bg-rose-500/15 text-rose-300 ring-rose-400/30"
            }`}
          >
            {backendOnline === null ? "检测后端…" : backendOnline ? "后端在线" : "后端未连接"}
          </span>
          <button
            type="button"
            onClick={() => setSettingsOpen((prev) => !prev)}
            className={`rounded-full px-3 py-1 text-[11px] ring-1 transition-colors ${
              configured
                ? "bg-slate-800 text-slate-300 ring-white/10 hover:bg-slate-700"
                : "bg-amber-500/10 text-amber-300 ring-amber-400/30 hover:bg-amber-500/20"
            }`}
          >
            {configured ? "数字人设置" : "配置数字人密钥"}
          </button>
        </div>

        <AvatarSettings open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      </header>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[1.05fr_1fr]">
        {/* 左：数字人 + 字幕 */}
        <div className="flex flex-col gap-3">
          <AvatarStage
            state={avatar.state}
            emotion={session.emotion}
            provider={avatar.provider}
            containerId={CONTAINER_ID}
            containerRef={containerRef}
            stage={avatar.provider === "xmov" ? xmovAvatar.stage : "ready"}
            detail={avatar.provider === "xmov" ? xmovAvatar.detail : ""}
          />
          <SubtitleBar text={session.subtitle} active={avatar.state === "speak"} />

          {/* 数字人失败原因（不因降级而丢失，便于现场排查） */}
          {avatarError && (
            <div className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-xs text-rose-200">
              <p className="font-medium">数字人未启用：{avatarError}</p>
              <p className="mt-1 leading-relaxed text-rose-200/70">
                已自动降级为浏览器语音（对话 / 字幕 / 情绪均不受影响）。常见原因：
                密钥不是「驱动应用」的、应用未完成配置、或网络无法访问魔珐服务。
                修正后点击右上角设置重新保存即可重连。
              </p>
            </div>
          )}

          {!configured && (
            <p className="text-center text-[11px] text-slate-500">
              当前使用浏览器语音演示。点击右上角「配置数字人密钥」可启用真实 3D 数字人。
            </p>
          )}
        </div>

        {/* 右：情绪 + 文风 + 对话 */}
        <div className="flex min-h-0 flex-col gap-3">
          <MoodIndicator
            emotion={session.emotion}
            tone={session.tone}
            memoryCounts={session.memoryCounts}
          />
          <StyleSwitcher
            value={session.styleId}
            onChange={session.setStyleId}
            disabled={session.busy}
          />
          <div className="min-h-0 flex-1">
            <ChatPanel
              messages={session.messages}
              toolsUsed={session.toolsUsed}
              busy={session.busy}
              error={session.error}
              onSend={session.send}
              onInterrupt={session.interrupt}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
