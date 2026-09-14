import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "HyPRA · 苏澄",
  description: "打通提示词架构与混合记忆的情感陪伴 3D 交互系统",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">{children}</body>
    </html>
  );
}
