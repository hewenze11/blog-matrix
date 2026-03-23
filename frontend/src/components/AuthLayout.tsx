'use client'
import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Cookies from 'js-cookie'
import Link from 'next/link'
import api from '@/lib/api'

const navItems = [
  { href: '/dashboard', label: '监控大盘', icon: '📊' },
  { href: '/blogs', label: '博客管理', icon: '📝' },
  { href: '/accounts', label: 'CF账号池', icon: '☁️' },
  { href: '/tasks', label: '任务队列', icon: '⚙️' },
]

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [username, setUsername] = useState('')
  const [queueBadge, setQueueBadge] = useState(0) // 活跃任务数

  useEffect(() => {
    const token = Cookies.get('access_token')
    if (!token) {
      router.replace('/login')
      return
    }
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      setUsername(payload.sub || 'admin')
    } catch {}
  }, [router])

  // 轮询任务队列统计（轻量）
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await api.get('/tasks/stats')
        setQueueBadge((res.data.pending || 0) + (res.data.running || 0))
      } catch {}
    }
    poll()
    const timer = setInterval(poll, 5000)
    return () => clearInterval(timer)
  }, [])

  const handleLogout = () => {
    Cookies.remove('access_token')
    router.replace('/login')
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-60 bg-gray-900 text-white flex flex-col">
        <div className="p-5 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-500 rounded-lg flex items-center justify-center text-lg">🌐</div>
            <div>
              <div className="font-bold text-sm">站点矩阵引擎</div>
              <div className="text-xs text-gray-400">SiteMatrix Engine</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                pathname === item.href
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <span>{item.icon}</span>
              <span className="flex-1">{item.label}</span>
              {/* 任务队列徽标 */}
              {item.href === '/tasks' && queueBadge > 0 && (
                <span className="bg-yellow-400 text-yellow-900 text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                  {queueBadge}
                </span>
              )}
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-sm font-bold">
              {username.charAt(0).toUpperCase()}
            </div>
            <span className="text-sm text-gray-300">{username}</span>
          </div>
          <button
            onClick={handleLogout}
            className="w-full text-left px-3 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            🚪 退出登录
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-gray-50">
        {children}
      </main>
    </div>
  )
}
