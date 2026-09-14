"use client";

/** 情绪指示器：情绪标签 + 强度条 + 语气（来自 M4 情绪链路 / M5 播报元数据）。 */

import type { EmotionInfo } from "@/lib/types";

const MOOD_BAR: Record<string, string> = {
  happy: "bg-amber-400",
  calm: "bg-sky-400",
  sad: "bg-slate-400",
  anxious: "bg-orange-400",
  tired: "bg-indigo-400",
  angry: "bg-rose-400",
  surprised: "bg-yellow-400",
  neutral: "bg-slate-500",
};

export function MoodIndicator({
  emotion,
  tone,
  memoryCounts,
}: {
  emotion: EmotionInfo | null;
  tone?: string;
  memoryCounts?: Record<string, number>;
}) {
  if (!emotion) return null;
  const barColor = MOOD_BAR[emotion.label] ?? MOOD_BAR.neutral;
  const percent = Math.round(Math.max(0, Math.min(1, emotion.intensity)) * 100);
  const memoryTotal = memoryCounts
    ? Object.values(memoryCounts).reduce((sum, value) => sum + value, 0)
    : 0;

  return (
    <div className="rounded-xl border border-white/10 bg-slate-900/40 px-4 py-3">
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>当前情绪</span>
        <span>{emotion.source === "llm" ? "模型识别" : "规则兜底"}</span>
      </div>

      <div className="mt-2 flex items-center gap-3">
        <span className="text-base text-slate-100">{emotion.label_zh}</span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-700/60">
          <div
            className={`h-full rounded-full transition-all duration-700 ${barColor}`}
            style={{ width: `${percent}%` }}
          />
        </div>
        <span className="text-xs text-slate-400">{percent}%</span>
      </div>

      <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-500">
        {tone && <span>语气：{tone}</span>}
        {memoryTotal > 0 && <span>召回记忆 {memoryTotal} 条</span>}
        <span>表情键：{emotion.facial_expression}</span>
      </div>
    </div>
  );
}
