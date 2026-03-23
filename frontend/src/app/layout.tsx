import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '站点矩阵引擎',
  description: '企业级静态博客矩阵管理平台',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  )
}
