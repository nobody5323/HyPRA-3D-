"use client";

/**
 * 数字人设置面板：**在页面上直接填写魔珐密钥**（无需改 .env 重新构建）。
 *
 * 凭证保存到 localStorage 并即时生效（SDK 会自动重建）；
 * 未配置时自动降级为「浏览器原生 TTS + 占位形象」。
 */

import { useEffect, useState } from "react";

import { useAvatarCredentials } from "@/hooks/useAvatarCredentials";

const SOURCE_LABEL: Record<string, { text: string; className: string }> = {
  local: { text: "已填写（本机保存）", className: "bg-emerald-500/15 text-emerald-300" },
  env: { text: "来自部署配置", className: "bg-sky-500/15 text-sky-300" },
  none: { text: "未配置 → 使用浏览器语音", className: "bg-amber-500/15 text-amber-300" },
};

export function AvatarSettings({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { credentials, source, save, clear } = useAvatarCredentials();
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [revealSecret, setRevealSecret] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // 打开面板时同步当前值
  useEffect(() => {
    if (!open) return;
    setAppId(credentials?.appId ?? "");
    setAppSecret(credentials?.appSecret ?? "");
    setRevealSecret(false);
    setMessage(null);
  }, [open, credentials]);

  if (!open) return null;

  const canSave = appId.trim().length > 0 && appSecret.trim().length > 0;
  const badge = SOURCE_LABEL[source] ?? SOURCE_LABEL.none;

  function handleSave() {
    if (!canSave) return;
    save({ appId, appSecret });
    setMessage("已保存，数字人将自动重新初始化。");
  }

  function handleClear() {
    clear();
    setAppId("");
    setAppSecret("");
    setMessage("已清除本机配置。");
  }

  return (
    <div className="absolute right-0 top-full z-30 mt-2 w-[380px] rounded-2xl border border-white/10 bg-slate-900 p-4 shadow-2xl">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-medium text-slate-100">数字人设置</h3>
          <p className="mt-0.5 text-[11px] text-slate-500">
            填写后即时生效，无需重新构建前端
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg px-2 py-1 text-xs text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
        >
          关闭
        </button>
      </div>

      <div className="mt-3">
        <span className={`inline-block rounded-full px-2.5 py-1 text-[11px] ${badge.className}`}>
          {badge.text}
        </span>
      </div>

      <div className="mt-3 space-y-3">
        <label className="block">
          <span className="text-xs text-slate-400">App ID（AK）</span>
          <input
            value={appId}
            onChange={(event) => setAppId(event.target.value)}
            placeholder="例如 c8fc6578…"
            autoComplete="off"
            className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-sky-500/50"
          />
        </label>

        <label className="block">
          <span className="text-xs text-slate-400">App Secret</span>
          <div className="mt-1 flex gap-2">
            <input
              value={appSecret}
              onChange={(event) => setAppSecret(event.target.value)}
              type={revealSecret ? "text" : "password"}
              placeholder="••••••••"
              autoComplete="off"
              className="w-full rounded-lg border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-sky-500/50"
            />
            <button
              type="button"
              onClick={() => setRevealSecret((prev) => !prev)}
              className="shrink-0 rounded-lg border border-white/10 px-3 text-xs text-slate-400 transition-colors hover:bg-slate-800"
            >
              {revealSecret ? "隐藏" : "显示"}
            </button>
          </div>
        </label>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={!canSave}
          className="flex-1 rounded-lg bg-sky-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-700"
        >
          保存并启用
        </button>
        <button
          type="button"
          onClick={handleClear}
          className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800"
        >
          清除
        </button>
      </div>

      {message && <p className="mt-2 text-[11px] text-emerald-300">{message}</p>}

      <div className="mt-3 space-y-1 border-t border-white/5 pt-3 text-[11px] leading-relaxed text-slate-500">
        <p>
          获取方式：魔珐星云控制台 → <span className="text-slate-400">应用中心</span> → 创建
          <span className="text-slate-400">驱动应用</span> → 查看密钥 → 复制 App ID / App Secret。
        </p>
        <p>
          留空即使用浏览器原生语音（字幕与对话功能不受影响）。
          凭证仅保存在本机浏览器，不会上传到服务器。
        </p>
      </div>
    </div>
  );
}
