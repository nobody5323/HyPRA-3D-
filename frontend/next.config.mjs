/** @type {import('next').NextConfig} */
const nextConfig = {
  // 后端 API 地址（容器内可用 http://backend:8000）
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000",
  },
  eslint: {
    // 参赛演示优先保证构建可复现；lint 单独跑
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
