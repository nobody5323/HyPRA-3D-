"use client";

/**
 * HyPRA 主页面：左侧数字人舞台 + 右侧对话与情绪面板。
 *
 * F1（当前）：浏览器原生 TTS 播报 —— 对接后端 `/chat` 即可完整演示
 *（对话 + 记忆 + 情绪 + 工具调用 + 播报 + 字幕）。
 * F2：把 useBrowserAvatar 换成 useXmovAvatar（魔珐 SDK），其余不变。
 */

import { useEffect, useState } from "react";

import { AvatarStage } from "@/components/AvatarStage";
import { ChatPanel } from "@/components/ChatPanel";
import { MoodIndicator } from "@/components/MoodIndicator";
import { StyleSwitcher } from "@/components/StyleSwitcher";
import { SubtitleBar } from "@/components/SubtitleBar";
import { useBrowserAvatar } from "@/hooks/useAvatar";
import { useChatSession } from "@/hooks/useChatSession";
import { getHealth } from "@/lib/api";

export default function HomePage() {
  const avatar = useBrowserAvatar();
  const session = useChatSession(avatar);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    getHealth().then((health) => setBackendOnline(health?.status === "ok"));
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 p-4 lg:p-6">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">
            HyPRA · <span className="text-sky-300">苏澄</span>
          </h1>
          <p className="text-xs text-slate-500">
            情感陪伴 3D 交互系统 · 分层提示词 + 混合记忆 + 情绪链路 + Agent 行动层
          </p>
        </div>
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
      </header>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[1.05fr_1fr]">
        {/* 左：数字人 + 字幕 */}
        <div className="flex flex-col gap-3">
          <AvatarStage
            state={avatar.state}
            emotion={session.emotion}
            provider={avatar.provider}
          />
          <SubtitleBar text={session.subtitle} active={avatar.state === "speak"} />
          {!avatar.ready && (
            <p className="text-center text-[11px] text-slate-500">
              当前浏览器未启用语音合成，字幕与对话功能不受影响。
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
