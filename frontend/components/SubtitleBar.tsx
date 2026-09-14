"use client";

/** 字幕条：显示当前播报文本（消费后端的 speak.display_text）。 */

export function SubtitleBar({ text, active }: { text: string; active: boolean }) {
  if (!text) return null;
  return (
    <div
      className={`rounded-xl border px-4 py-3 text-center text-sm leading-relaxed transition-colors ${
        active
          ? "border-emerald-400/30 bg-emerald-500/5 text-slate-100"
          : "border-white/10 bg-slate-900/40 text-slate-300"
      }`}
    >
      {text}
    </div>
  );
}
