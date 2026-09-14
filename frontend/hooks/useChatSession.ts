"use client";

/**
 * 对话会话编排：串起「具身状态机 + 后端请求 + 播报 + 情绪视觉」。
 *
 * 流程（与赛题要求的 Listen/Think/Speak/Interrupt 对齐）：
 *   listen（记录用户输入）→ think（等待后端）→ speak（播报 + 字幕）→ idle
 */

import { useCallback, useRef, useState } from "react";

import { postChat } from "@/lib/api";
import type { ChatMessage, EmotionInfo, ToolUsage } from "@/lib/types";
import type { AvatarController } from "./useAvatar";

export interface ChatSession {
  messages: ChatMessage[];
  emotion: EmotionInfo | null;
  toolsUsed: ToolUsage[];
  subtitle: string;
  tone: string;
  memoryCounts: Record<string, number>;
  sessionId: string | null;
  styleId: string;
  setStyleId: (id: string) => void;
  busy: boolean;
  error: string | null;
  send: (text: string) => Promise<void>;
  interrupt: () => void;
}

export function useChatSession(avatar: AvatarController, userName = "小林"): ChatSession {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [emotion, setEmotion] = useState<EmotionInfo | null>(null);
  const [toolsUsed, setToolsUsed] = useState<ToolUsage[]>([]);
  const [subtitle, setSubtitle] = useState("");
  const [tone, setTone] = useState("");
  const [memoryCounts, setMemoryCounts] = useState<Record<string, number>>({});
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [styleId, setStyleId] = useState("modern-conversational");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || busy) return;

      setError(null);
      setBusy(true);
      avatar.setState("listen"); // ① 聆听
      setMessages((prev) => [...prev, { role: "user", text: content }]);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        avatar.setState("think"); // ② 思考（等待后端）
        const res = await postChat(
          { text: content, session_id: sessionId, style_id: styleId, user_name: userName },
          { signal: controller.signal },
        );

        setSessionId(res.session_id);
        setMessages((prev) => [...prev, { role: "assistant", text: res.reply }]);
        setEmotion(res.emotion ?? null);
        setToolsUsed(res.tools_used ?? []);
        setSubtitle(res.speak?.display_text || res.reply);
        setTone(res.speak?.tone ?? "");
        setMemoryCounts(res.memory_counts ?? {});

        avatar.setState("speak"); // ③ 播报
        await avatar.speak(res.speak?.display_text || res.reply);
        avatar.setState("idle"); // ④ 回到待机
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setError("已打断本轮对话。");
        } else {
          setError((err as Error).message || "对话失败，请检查后端是否已启动。");
        }
        avatar.setState("idle");
      } finally {
        setBusy(false);
        abortRef.current = null;
      }
    },
    [avatar, busy, sessionId, styleId, userName],
  );

  /** 打断：立即停止播报并中止请求（客户端即时打断，不等服务端）。 */
  const interrupt = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    avatar.interrupt();
    setBusy(false);
  }, [avatar]);

  return {
    messages,
    emotion,
    toolsUsed,
    subtitle,
    tone,
    memoryCounts,
    sessionId,
    styleId,
    setStyleId,
    busy,
    error,
    send,
    interrupt,
  };
}
