"use client";

/**
 * 数字人舞台。
 *
 * F1（当前）：占位形象 + 状态徽标 + 情绪光效 —— 不依赖魔珐 SDK 也能完整演示；
 * F2：把 SDK 挂载到本组件的容器上（见 docs/frontend-avatar-integration.md），
 *     届时替换占位形象为真实 3D 渲染，其余交互完全不变。
 */

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
}: {
  state: AvatarState;
  emotion: EmotionInfo | null;
  provider: string;
}) {
  const color = MOOD_COLOR[emotion?.label ?? "neutral"] ?? MOOD_COLOR.neutral;
  const intensity = emotion?.intensity ?? 0.5;

  return (
    <section className="relative flex flex-col items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-slate-900/60 p-6">
      {/* 情绪光晕 */}
      <div
        className="pointer-events-none absolute inset-0 opacity-40 transition-all duration-1000"
        style={{
          background: `radial-gradient(circle at 50% 45%, ${color}${Math.round(
            20 + intensity * 40,
          ).toString(16)} 0%, transparent 65%)`,
        }}
      />

      {/* 占位数字人形象（F2 由 SDK 渲染替换） */}
      <div className="relative z-10 flex flex-col items-center gap-5">
        <div
          className={`relative h-52 w-52 rounded-full bg-gradient-to-b from-slate-200/90 to-slate-400/70 shadow-xl transition-transform duration-700 ${
            state === "speak" ? "animate-breathe-in" : ""
          }`}
          style={{
            boxShadow: `0 0 ${20 + intensity * 50}px ${color}55`,
          }}
          aria-label="数字人形象占位"
        >
          {/* 简化的面部示意（口型随说话状态变化） */}
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

        <div className="flex flex-col items-center gap-2">
          <p className="text-lg font-medium text-slate-100">苏澄</p>
          <p className="text-xs text-slate-400">心理倾听师 · 温柔年长的知心姐姐</p>
          <StateBadge state={state} />
        </div>

        <p className="text-[11px] text-slate-500">
          {provider === "browser" ? "语音：浏览器原生 TTS（F1 占位）" : "语音：魔珐具身驱动 SDK"}
        </p>
      </div>
    </section>
  );
}
