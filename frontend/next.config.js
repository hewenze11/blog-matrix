/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // NEXT_PUBLIC_API_BASE 为空时，axios 请求走相对路径（nginx 反代）
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || '',
  },
}

module.exports = nextConfig
