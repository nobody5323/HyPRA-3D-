"use client";

/** 对话面板：消息列表 + 输入框 + Agent 工具提示 + 打断按钮。 */

import { useEffect, useRef, useState } from "react";

import type { ChatMessage, ToolUsage } from "@/lib/types";

/** 工具调用 → 用户可读提示（体现「能办事」） */
const TOOL_LABELS: Record<string, string> = {
  record_mood_journal: "已记录这次心情",
  query_mood_trend: "已查看情绪趋势",
  start_breathing_exercise: "已准备好呼吸引导",
  recall_memory: "已检索长期记忆",
};

export function ChatPanel({
  messages,
  toolsUsed,
  busy,
  error,
  onSend,
  onInterrupt,
}: {
  messages: ChatMessage[];
  toolsUsed: ToolUsage[];
  busy: boolean;
  error: string | null;
  onSend: (text: string) => void;
  onInterrupt: () => void;
}) {
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  function submit() {
    const text = draft.trim();
    if (!text || busy) return;
    onSend(text);
    setDraft("");
  }

  const toolNotes = toolsUsed
    .map((tool) => TOOL_LABELS[tool.name])
    .filter((label): label is string => Boolean(label));

  return (
    <section className="flex h-full min-h-0 flex-col rounded-2xl border border-white/10 bg-slate-900/50">
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <h2 className="text-sm font-medium text-slate-200">对话</h2>
        <span className="text-[11px] text-slate-500">
          {messages.length > 0 ? `${messages.length} 条消息` : "开始聊聊吧"}
        </span>
      </header>

      <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <p className="mt-6 text-center text-sm text-slate-500">
            说点什么吧——比如「我最近总是失眠」。
          </p>
        )}
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                message.role === "user"
                  ? "bg-sky-600/80 text-white"
                  : "bg-slate-800/80 text-slate-100"
              }`}
            >
              {message.text}
            </div>
          </div>
        ))}

        {toolNotes.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {toolNotes.map((note, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-1 text-[11px] text-emerald-300 ring-1 ring-emerald-400/30"
              >
                ✓ {note}
              </span>
            ))}
          </div>
        )}

        {busy && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-slate-800/60 px-4 py-2.5 text-sm text-slate-400">
              苏澄正在回应…
            </div>
          </div>
        )}
      </div>

      {error && (
        <p className="mx-4 mb-2 rounded-lg bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
          {error}
        </p>
      )}

      <footer className="border-t border-white/10 px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            rows={2}
            placeholder="说说你今天怎么样…（Enter 发送，Shift+Enter 换行）"
            className="min-h-[44px] flex-1 resize-none rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-sky-500/50"
          />
          {busy ? (
            <button
              type="button"
              onClick={onInterrupt}
              className="h-11 shrink-0 rounded-xl bg-rose-600/80 px-4 text-sm font-medium text-white transition-colors hover:bg-rose-600"
            >
              打断
            </button>
          ) : (
            <button
              type="button"
              onClick={submit}
              disabled={!draft.trim()}
              className="h-11 shrink-0 rounded-xl bg-sky-600 px-4 text-sm font-medium text-white transition-colors hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-700"
            >
              发送
            </button>
          )}
        </div>
      </footer>
    </section>
  );
}
