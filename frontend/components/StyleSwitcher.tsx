"use client";

/**
 * 文风切换器（A/B 对比演示用）。
 *
 * 四种预设与后端 `backend/app/prompts/style/presets/` 一一对应，
 * 切换后下一轮对话即生效（前端仅传 style_id）。
 */

import { useState } from "react";

const STYLES: { id: string; name: string; hint: string }[] = [
  { id: "modern-conversational", name: "现代口语", hint: "像熟人聊天，短句 + 语气词" },
  { id: "brief-direct", name: "简短利落", hint: "一两句，留白" },
  { id: "classical-elegant", name: "古典雅致", hint: "含蓄，带一点文气" },
  { id: "gentle-elaborate", name: "细腻长句", hint: "有动作神态描写" },
];

export function StyleSwitcher({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (id: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const current = STYLES.find((style) => style.id === value) ?? STYLES[0];

  return (
    <div className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-slate-900/40 px-4 py-2.5 text-left text-sm text-slate-200 transition-colors hover:border-sky-500/40 disabled:opacity-50"
      >
        <span>
          <span className="text-xs text-slate-500">文风 · </span>
          {current.name}
        </span>
        <span className="text-xs text-slate-500">{open ? "收起" : "切换"}</span>
      </button>

      {open && (
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-white/10 bg-slate-900 shadow-xl">
          {STYLES.map((style) => (
            <li key={style.id}>
              <button
                type="button"
                onClick={() => {
                  onChange(style.id);
                  setOpen(false);
                }}
                className={`w-full px-4 py-2.5 text-left text-sm transition-colors hover:bg-slate-800 ${
                  style.id === value ? "text-sky-300" : "text-slate-300"
                }`}
              >
                <span className="block">{style.name}</span>
                <span className="block text-[11px] text-slate-500">{style.hint}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
