"use client";

/**
 * 具身状态机 + 语音播报控制器（两种实现，同一接口，可自动降级）。
 *
 * - `useBrowserAvatar`：浏览器原生 TTS（Web Speech API）——零依赖，无密钥可用；
 * - `useXmovAvatar`：魔珐具身驱动 SDK（XmovAvatar）——真实 3D 数字人渲染。
 *
 * 状态机（赛题明确的评分点）：
 *   idle → listen（用户输入）→ think（等待后端）→ speak（播报）→ idle
 *                       ↑                                    │
 *                       └──────── interrupt（打断）──────────┘
 *
 * 降级策略（赛题「稳定性与容错」评分点）：
 *   未配置密钥 / SDK 脚本加载失败 / init 失败 → 自动回退浏览器 TTS，并**完整暴露原因**
 *   （stage/detail 会显示在数字人区域，便于现场排查）。
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { RefObject } from "react";

import type { AvatarCredentials } from "@/lib/avatar-config";
import { AVATAR_STATE_LABELS, type AvatarState } from "@/lib/types";

/** 数字人初始化阶段（用于向用户暴露诊断信息） */
export type AvatarInitStage =
  | "unconfigured" // 未配置凭证
  | "loading-sdk" // 正在加载 SDK 脚本
  | "initializing" // SDK 连接/渲染初始化中
  | "ready" // 就绪
  | "failed"; // 失败（见 detail）

export interface AvatarController {
  state: AvatarState;
  stateLabel: string;
  ready: boolean;
  provider: "browser" | "xmov";
  /** 初始化阶段（诊断用） */
  stage: AvatarInitStage;
  /** 阶段详情 / 失败原因（诊断用） */
  detail: string;
  setState: (state: AvatarState) => void;
  /**
   * 播报一段回复。
   * @param text 纯文本（字幕/浏览器 TTS 用）
   * @param ssml SSML（魔珐 SDK 用；含 KA 动作指令）
   */
  speak: (text: string, ssml?: string) => Promise<void>;
  /** 打断当前播报（客户端即时打断，不等服务端） */
  interrupt: () => void;
  /** SDK 挂载容器 id（仅 xmov 需要） */
  containerId?: string;
}

/** 魔珐 SDK 脚本地址（版本由官方 latest 维护） */
const XMOV_SDK_URL =
  "https://media.xingyun3d.com/xingyun3d/general/litesdk/xmovAvatar@latest.js";
const XMOV_GATEWAY = "https://nebula-agent.xingyun3d.com/user/v1/ttsa/session";

/** 初始化超时（毫秒）：资源下载或 socket.io 连接卡住时兜底，避免永久“初始化中” */
const INIT_TIMEOUT_MS = 90_000;

// =============================================================
// 实现一：浏览器原生 TTS（零依赖，默认）
// =============================================================

export function useBrowserAvatar(): AvatarController {
  const [state, setState] = useState<AvatarState>("idle");
  const [ready, setReady] = useState(false);
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const pickVoice = () => {
      const voices = window.speechSynthesis.getVoices();
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
      utterance.rate = 0.95;
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
    stage: "ready",
    detail: "",
    setState,
    speak,
    interrupt,
  };
}

// =============================================================
// 实现二：魔珐具身驱动 SDK（真实 3D 数字人）
// =============================================================

interface UseXmovOptions {
  /** 魔珐凭证（运行时配置：界面填写 > 构建时环境变量）；为空时不加载 SDK */
  credentials: AvatarCredentials | null;
  /** 是否启用（false 时不加载 SDK，用于自动降级） */
  enabled?: boolean;
  /** 配置修订号：变化即重建（支持「重新连接」，即使凭证内容未变） */
  revision?: number;
  /** 渲染容器 ref（优先使用，避免选择器解析问题） */
  containerRef?: RefObject<HTMLElement | null>;
  /** 不可用时回调（调用方据此回退浏览器实现） */
  onUnavailable?: (reason: string) => void;
}

/** 动态加载 SDK 脚本（幂等）。 */
function loadXmovSdk(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") return reject(new Error("非浏览器环境"));
    if ((window as any).XmovAvatar) return resolve();

    const existing = document.querySelector<HTMLScriptElement>(`script[src="${XMOV_SDK_URL}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("SDK 脚本加载失败")));
      return;
    }

    const script = document.createElement("script");
    script.src = XMOV_SDK_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("SDK 脚本加载失败（网络或域名被拦截）"));
    document.head.appendChild(script);
  });
}

/** 把 SDK 抛出的任意错误转成可读文本（便于现场排查） */
function describeError(error: unknown): string {
  if (!error) return "未知错误";
  const err = error as any;
  const parts: string[] = [];
  if (err.name) parts.push(String(err.name));
  if (err.message) parts.push(String(err.message));
  if (typeof err === "string") parts.push(err);
  if (err.code) parts.push(`code=${err.code}`);
  return parts.length ? parts.join(": ") : JSON.stringify(err).slice(0, 200);
}

export function useXmovAvatar(
  containerId = "#avatar-container",
  options: UseXmovOptions,
): AvatarController {
  const { credentials, enabled = true, revision = 0, containerRef, onUnavailable } = options;
  const [state, setState] = useState<AvatarState>("idle");
  const [ready, setReady] = useState(false);
  const [stage, setStage] = useState<AvatarInitStage>("unconfigured");
  const [detail, setDetail] = useState("");
  const avatarRef = useRef<any>(null);
  /** 同步跟踪具身状态（供 speak 判断是否需要先切回待机） */
  const stateRef = useRef<AvatarState>("idle");

  const updateState = useCallback((next: AvatarState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  // 凭证内容变化 → 重建 SDK（用字符串做依赖，避免对象引用每次变化）
  const credentialKey = credentials
    ? `${credentials.appId}:${credentials.appSecret}`
    : "";

  useEffect(() => {
    if (!enabled) return;

    if (!credentials) {
      setStage("unconfigured");
      setDetail("未配置魔珐密钥（点击右上角「配置数字人密钥」填写）");
      onUnavailable?.("未配置魔珐密钥");
      return;
    }

    let disposed = false;

    (async () => {
      // 提到 try 外：失败时需销毁实例（超时/鉴权失败等）
      let avatar: any = null;
      try {
        setStage("loading-sdk");
        setDetail(`正在加载 SDK 脚本…（${XMOV_SDK_URL.split("/").pop()}）`);
        await loadXmovSdk();
        if (disposed) return;

        setStage("initializing");
        setDetail("SDK 已加载，正在建立数字人连接…");

        // 官方 SDK 要求 containerId 为 **CSS 选择器**（内部用 document.querySelector）；
        // 同时优先传 HTMLElement，避免选择器解析失败。
        const element = containerRef?.current ?? null;
        // SDK 失败时 init() 仍会 resolve（如容器不存在），因此用标志记录 onMessage 报错
        let initError: string | null = null;

        // 构造参数：
        // - containerId / container：容器定位（选择器兜底 + 元素优先）
        // - 回调：官方列为初始化参数，且 SDK 内部**无条件调用 onDownloadProgress**，
        //   缺失会抛 TypeError（实测错误：Cannot read properties of undefined 'onDownloadProgress'）
        const config: Record<string, unknown> = {
          containerId,
          appId: credentials.appId,
          appSecret: credentials.appSecret,
          gatewayServer: XMOV_GATEWAY,
          hardwareAcceleration: "prefer-hardware",

          /** 资源加载进度（必需参数）：达到 100% 即视为就绪，不阻塞在 init 的 Promise 上 */
          onDownloadProgress: (progress: number) => {
            const pct = Math.round(progress);
            console.log(`[HyPRA][avatar] 资源加载 ${pct}%`);
            if (pct >= 99) {
              setStage("ready");
              setReady(true);
              setDetail("魔珐数字人已就绪");
            } else {
              setStage("initializing");
              setDetail(`正在加载数字人资源… ${pct}%`);
            }
          },
          /** SDK 状态 → 具身状态机（speak / idle 等） */
          onStateChange: (sdkState: string) => {
            const value = String(sdkState ?? "").toLowerCase();
            if (value.includes("speak") || value.includes("play")) setState("speak");
            else if (value.includes("listen")) setState("listen");
            else if (value.includes("idle")) setState("idle");
          },
          /** SDK 消息 / 错误（错误通过 code 字段区分） */
          onMessage: (payload: any) => {
            if (payload && payload.code !== undefined) {
              const reason = `${payload.message ?? "SDK 报错"}（code=${payload.code}）`;
              initError = reason;
              setStage("failed");
              setDetail(reason);
              setReady(false);
              onUnavailable?.(reason);
            }
          },
          /** 以下回调官方示例均提供，这里仅占位避免 SDK 内部空引用 */
          onNetworkInfo: () => {},
          onStatusChange: () => {},
          onStateRenderChange: () => {},
          onWidgetEvent: () => {},
        };
        if (element) config.container = element;

        const avatarInstance = new (window as any).XmovAvatar(config);
        avatar = avatarInstance;
        // ⚠️ 提前挂载引用：init() 可能因会话握手较慢而长时间未 resolve，
        // 但渲染与播报已可用——否则 speak() 会因 avatarRef 为空而静默失效（没声音）。
        avatarRef.current = avatarInstance;

        // 语音状态 → 驱动具身状态机（voice_end 后回到交互待机）
        const handleVoiceState = (event: unknown) => {
          const name = typeof event === "string" ? event : (event as any)?.state;
          console.log("[HyPRA][avatar] 语音状态:", name);
          if (name === "voice_start") updateState("speak");
          if (name === "voice_end") {
            avatar?.interactiveidle?.(); // SDK 公开方法（小写无下划线）
            updateState("idle");
          }
        };
        avatar.onVoiceStateChange = handleVoiceState;

        // SDK 内部错误也暴露出来（否则只会静默失败）
        avatar.onError = (error: unknown) => {
          const reason = describeError(error);
          setStage("failed");
          setDetail(`SDK 运行错误：${reason}`);
          setReady(false);
          onUnavailable?.(reason);
        };

        // ⚠️ 官方文档「1.3 初始化连接房间」参数表明确：onDownloadProgress 为**必填**
        // （init 的参数，非构造参数）；源码中为无条件调用，缺失即抛 TypeError。
        //
        // 额外加超时保护：资源下载或 socket.io 连接卡住时，避免永久停在“初始化中”。
        let timeoutHandle: ReturnType<typeof setTimeout> | undefined;
        const timeoutPromise = new Promise<never>((_, reject) => {
          timeoutHandle = setTimeout(
            () =>
              reject(
                new Error(
                  `初始化超时（${INIT_TIMEOUT_MS / 1000}s）：资源加载或服务连接未完成`,
                ),
              ),
            INIT_TIMEOUT_MS,
          );
        });

        try {
          await Promise.race([
            avatar.init({
              onDownloadProgress: (progress: number) => {
                const pct = Math.round(progress);
                console.log(`[HyPRA][avatar] init 进度 ${pct}%`);
                if (pct >= 99) {
                  // 资源已就绪：即使 init Promise 仍在等待会话握手，界面也先转为可用
                  setStage("ready");
                  setReady(true);
                  setDetail("魔珐数字人已就绪");
                } else {
                  setStage("initializing");
                  setDetail(`正在加载数字人资源… ${pct}%`);
                }
              },
              initModel: "normal",
            }),
            timeoutPromise,
          ]);
        } finally {
          if (timeoutHandle) clearTimeout(timeoutHandle);
        }
        if (initError) return; // 初始化已失败并在 onMessage 中上报（init 仍会 resolve）
        if (disposed) {
          avatar.destroy?.();
          return;
        }

        avatarRef.current = avatar;
        setReady(true);
        setStage("ready");
        setDetail("魔珐数字人已就绪");
      } catch (error) {
        const reason = describeError(error);
        setStage("failed");
        setDetail(`数字人初始化失败：${reason}`);
        setReady(false);
        avatar?.destroy?.(); // 清理失败的实例（避免 WebGL 资源泄漏）
        onUnavailable?.(reason);
      }
    })();

    return () => {
      disposed = true;
      avatarRef.current?.destroy?.(); // 官方要求：卸载前销毁，释放 WebGL 资源
      avatarRef.current = null;
    };
    // containerId 或凭证变化时重建（其余依赖刻意不入列，避免重复初始化）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerId, enabled, credentialKey, revision]);

  /** 切换具身状态：同步更新 React 状态与 SDK 行为状态 */
  const setAvatarState = useCallback(
    (next: AvatarState) => {
      updateState(next);
      const avatar = avatarRef.current;
      if (!avatar) return;
      // 官方公开方法：idle() / listen() / interactiveidle()
      if (next === "idle") avatar.idle?.();
      else if (next === "listen") avatar.listen?.();
      else if (next === "think") avatar.interactiveidle?.();
    },
    [updateState],
  );

  const speak = useCallback(async (text: string, ssml?: string) => {
    const avatar = avatarRef.current;
    if (!avatar) return;

    // 官方约束：speak 不允许连续调用，需先用 interactive_idle 做状态切换；
    // 而状态切换是异步的（经 WebSocket 下发），立即 speak 会被忽略——
    // 因此仅在「正在播报」时打断并等待片刻，其余情况直接播报。
    if (stateRef.current === "speak") {
      console.log("[HyPRA][avatar] 正在播报，先打断并切回交互待机");
      avatar.interrupt?.();
      avatar.interactiveidle?.();
      await new Promise((resolve) => setTimeout(resolve, 400));
    }

    console.log("[HyPRA][avatar] speak 调用:", (ssml || text).slice(0, 60));
    avatar.speak(ssml || text, true, true);
  }, []);

  const interrupt = useCallback(() => {
    const avatar = avatarRef.current;
    avatar?.interrupt?.();
    avatar?.interactiveidle?.();
    updateState("idle");
  }, [updateState]);

  return {
    state,
    stateLabel: AVATAR_STATE_LABELS[state],
    ready,
    provider: "xmov",
    stage,
    detail,
    setState: setAvatarState,
    speak,
    interrupt,
    containerId,
  };
}
