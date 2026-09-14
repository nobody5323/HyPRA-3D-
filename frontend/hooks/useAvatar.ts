"use client";

/**
 * 具身状态机 + 语音播报控制器。
 *
 * 本文件同时提供两种实现（同一接口，可切换）：
 * - useBrowserAvatar：浏览器原生 TTS（Web Speech API）——**零依赖**，F1 阶段即可演示；
 * - useXmovAvatar：魔珐具身驱动 SDK（F2 接入，见 docs/frontend-avatar-integration.md）。
 *
 * 状态机（赛题明确的评分点）：
 *   idle → listen（用户输入）→ think（等待后端）→ speak（播报）→ idle
 *                       ↑                                    │
 *                       └──────── interrupt（打断）──────────┘
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { AVATAR_STATE_LABELS, type AvatarState } from "@/lib/types";

export interface AvatarController {
  state: AvatarState;
  stateLabel: string;
  ready: boolean;
  provider: "browser" | "xmov";
  setState: (state: AvatarState) => void;
  /** 播报一段文本（F1 用浏览器 TTS；F2 用 SDK 播报 SSML） */
  speak: (text: string) => Promise<void>;
  /** 打断当前播报（客户端即时打断，不等服务端） */
  interrupt: () => void;
}

/** F1 实现：浏览器原生语音合成（零依赖）。 */
export function useBrowserAvatar(): AvatarController {
  const [state, setState] = useState<AvatarState>("idle");
  const [ready, setReady] = useState(false);
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const pickVoice = () => {
      const voices = window.speechSynthesis.getVoices();
      // 优先中文女声（更贴近「苏澄」人设）
      voiceRef.current =
        voices.find((v) => /zh/i.test(v.lang) && /female|Xiaoxiao|Huihui/i.test(v.name)) ??
        voices.find((v) => /zh/i.test(v.lang)) ??
        null;
      setReady(true);
    };
    pickVoice();
    window.speechSynthesis.onvoiceschanged = pickVoice;
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  const speak = useCallback(async (text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window) || !text.trim()) return;
    window.speechSynthesis.cancel();
    await new Promise<void>((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text);
      if (voiceRef.current) utterance.voice = voiceRef.current;
      utterance.rate = 0.95; // 略慢，贴近温柔基调
      utterance.onend = () => resolve();
      utterance.onerror = () => resolve();
      window.speechSynthesis.speak(utterance);
    });
  }, []);

  const interrupt = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setState("idle");
  }, []);

  return {
    state,
    stateLabel: AVATAR_STATE_LABELS[state],
    ready,
    provider: "browser",
    setState,
    speak,
    interrupt,
  };
}
