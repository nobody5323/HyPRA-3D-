"use client";

/**
 * 订阅数字人凭证配置的 React Hook。
 *
 * 首屏使用构建时兜底值（避免 SSR/CSR 不一致导致的 hydration 警告），
 * 挂载后再读取 localStorage 并在凭证变化时同步更新。
 */

import { useEffect, useMemo, useState } from "react";

import {
  type AvatarCredentials,
  type CredentialSource,
  clearCredentials,
  getEffectiveCredentials,
  saveCredentials,
  subscribeCredentials,
} from "@/lib/avatar-config";

export interface AvatarCredentialsState {
  credentials: AvatarCredentials | null;
  source: CredentialSource;
  configured: boolean;
  save: (credentials: AvatarCredentials) => void;
  clear: () => void;
}

export function useAvatarCredentials(): AvatarCredentialsState {
  const [snapshot, setSnapshot] = useState(() => getEffectiveCredentials());

  useEffect(() => {
    setSnapshot(getEffectiveCredentials()); // 挂载后读取 localStorage
    return subscribeCredentials(() => setSnapshot(getEffectiveCredentials()));
  }, []);

  // 稳定引用：仅在凭证内容变化时更新（便于作为 effect 依赖）
  const credentials = useMemo(
    () => snapshot.credentials,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [snapshot.credentials?.appId, snapshot.credentials?.appSecret],
  );

  return {
    credentials,
    source: snapshot.source,
    configured: Boolean(credentials),
    save: saveCredentials,
    clear: clearCredentials,
  };
}
