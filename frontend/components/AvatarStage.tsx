"use client";

/**
 * 数字人舞台。
 *
 * 两种渲染模式（由 provider 决定）：
 * - `xmov`：把魔珐 SDK 挂载到 `#avatar-container`（真实 3D 数字人，F2）；
 * - `browser`：占位形象 + 情绪光效（零依赖降级，F1）。
 *
 * 两种模式共享同一套外部 UI（状态徽标、角色名、提示），便于演示时无缝切换。
 */

import type { RefObject } from "react";

import type { AvatarInitStage } from "@/hooks/useAvatar";
import type { AvatarState, EmotionInfo } from "@/lib/types";
import { StateBadge } from "./StateBadge";

const MOOD_COLOR: Record<string, string> = {
  happy: "var(--mood-happy, #f6c177)",
  calm: "var(--mood-calm, #8fb8c9)",
  sad: "var(--mood-sad, #7c8ba1)",
  anxious: "var(--mood-anxious, #e0a075)",
  tired: "var(--mood-tired, #6b7a99)",
  angry: "var(--mood-angry, #c97676)",
  surprised: "var(--mood-surprised, #d8b46a)",
  neutral: "var(--mood-neutral, #9aa5b1)",
};

export function AvatarStage({
  state,
  emotion,
  provider,
  containerId = "avatar-container",
  containerRef,
  stage = "ready",
  detail = "",
}: {
  state: AvatarState;
  emotion: EmotionInfo | null;
  provider: "browser" | "xmov";
  containerId?: string;
  containerRef?: RefObject<HTMLDivElement | null>;
  stage?: AvatarInitStage;
  detail?: string;
}) {
  const color = MOOD_COLOR[emotion?.label ?? "neutral"] ?? MOOD_COLOR.neutral;
  const intensity = emotion?.intensity ?? 0.5;
  const isXmov = provider === "xmov";
  const loading = isXmov && (stage === "loading-sdk" || stage === "initializing");

  return (
    <section className="relative flex flex-col items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-slate-900/60 p-6">
      {/* 情绪光晕（两种模式共用，SDK 画布浮在其上） */}
      <div
        className="pointer-events-none absolute inset-0 opacity-40 transition-all duration-1000"
        style={{
          background: `radial-gradient(circle at 50% 45%, ${color}${Math.round(
            20 + intensity * 40,
          ).toString(16)} 0%, transparent 65%)`,
        }}
      />

      <div className="relative z-10 flex w-full flex-col items-center gap-5">
        {isXmov ? (
          /* 魔珐 SDK 挂载容器（真实 3D 渲染） */
          <div
            id={containerId}
            ref={containerRef}
            className="h-[420px] w-full overflow-hidden rounded-xl bg-slate-950/40"
            aria-label="魔珐数字人渲染容器"
          >
            {loading && (
              <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-center">
                <span className="h-6 w-6 animate-spin rounded-full border-2 border-sky-400/40 border-t-sky-400" />
                <p className="text-sm text-slate-200">正在初始化数字人…</p>
                <p className="px-6 text-[11px] text-slate-500">{detail}</p>
              </div>
            )}
          </div>
        ) : (
          /* 占位形象（零依赖降级） */
          <div
            className={`relative h-52 w-52 rounded-full bg-gradient-to-b from-slate-200/90 to-slate-400/70 shadow-xl transition-transform duration-700 ${
              state === "speak" ? "animate-breathe-in" : ""
            }`}
            style={{ boxShadow: `0 0 ${20 + intensity * 50}px ${color}55` }}
            aria-label="数字人形象占位"
          >
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-4">
                <div className="flex gap-6">
                  <span className="h-2.5 w-2.5 rounded-full bg-slate-700/70" />
                  <span className="h-2.5 w-2.5 rounded-full bg-slate-700/70" />
                </div>
                <span
                  className={`bg-slate-700/60 transition-all duration-300 ${
                    state === "speak" ? "h-4 w-8 rounded-full" : "h-1 w-6 rounded-full"
                  }`}
                />
              </div>
            </div>
          </div>
        )}

        <div className="flex flex-col items-center gap-2">
          <p className="text-lg font-medium text-slate-100">苏澄</p>
          <p className="text-xs text-slate-400">心理倾听师 · 温柔年长的知心姐姐</p>
          <StateBadge state={state} />
        </div>

        <p className="text-[11px] text-slate-500">
          {isXmov ? "渲染：魔珐星云具身驱动 SDK" : "渲染：占位形象（配置密钥后自动切换真实数字人）"}
        </p>
      </div>
    </section>
  );
}
