'use client'
import { useEffect, useState } from 'react'
import AuthLayout from '@/components/AuthLayout'
import { monitorApi, blogsApi } from '@/lib/api'

interface DashboardStats {
  total: number
  online: number
  offline: number
  building: number
  error: number
}

interface Blog {
  id: string
  name: string
  custom_domain?: string
  pages_domain?: string
  theme: string
  status: string
  fail_count: number
  last_deployed_at?: string
  last_checked_at?: string
}

const StatusBadge = ({ status }: { status: string }) => {
  const map: Record<string, { color: string; label: string; dot: string }> = {
    online:    { color: 'bg-green-100 text-green-700',  label: '在线',  dot: 'bg-green-500' },
    offline:   { color: 'bg-red-100 text-red-700',     label: '离线',  dot: 'bg-red-500' },
    building:  { color: 'bg-yellow-100 text-yellow-700', label: '构建中', dot: 'bg-yellow-500' },
    deploying: { color: 'bg-blue-100 text-blue-700',   label: '部署中', dot: 'bg-blue-500' },
    error:     { color: 'bg-red-100 text-red-700',     label: '错误',  dot: 'bg-red-500' },
  }
  const s = map[status] || { color: 'bg-gray-100 text-gray-600', label: status, dot: 'bg-gray-400' }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${s.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot} ${['building','deploying'].includes(status) ? 'status-dot-pulse' : ''}`}></span>
      {s.label}
    </span>
  )
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [blogs, setBlogs] = useState<Blog[]>([])
  const [loading, setLoading] = useState(true)
  const [checkLoading, setCheckLoading] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

  const loadData = async () => {
    try {
      const [statsRes, blogsRes] = await Promise.all([
        monitorApi.dashboard(),
        blogsApi.list()
      ])
      setStats(statsRes.data)
      setBlogs(blogsRes.data)
      setLastRefresh(new Date())
    } catch (err) {
      console.error('加载数据失败', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const timer = setInterval(loadData, 30000) // 30s 自动刷新
    return () => clearInterval(timer)
  }, [])

  const triggerCheck = async () => {
    setCheckLoading(true)
    try {
      await monitorApi.triggerCheck()
      setTimeout(loadData, 2000)
    } catch {}
    setCheckLoading(false)
  }

  const statCards = stats ? [
    { label: '总站点', value: stats.total, color: 'text-gray-800', bg: 'bg-white', icon: '🌐' },
    { label: '在线', value: stats.online, color: 'text-green-600', bg: 'bg-green-50', icon: '✅' },
    { label: '离线', value: stats.offline, color: 'text-red-600', bg: 'bg-red-50', icon: '🔴' },
    { label: '构建中', value: stats.building, color: 'text-yellow-600', bg: 'bg-yellow-50', icon: '⚙️' },
    { label: '错误', value: stats.error, color: 'text-red-500', bg: 'bg-red-50', icon: '⚠️' },
  ] : []

  return (
    <AuthLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">监控大盘</h1>
            <p className="text-sm text-gray-500 mt-1">
              最后刷新：{lastRefresh.toLocaleTimeString('zh-CN')} · 每 30 秒自动更新
            </p>
          </div>
          <button
            onClick={triggerCheck}
            disabled={checkLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {checkLoading ? (
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
            ) : '🔍'}
            手动探活
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          {loading ? (
            Array(5).fill(0).map((_, i) => (
              <div key={i} className="bg-white rounded-xl p-4 animate-pulse">
                <div className="h-8 bg-gray-200 rounded mb-2"></div>
                <div className="h-4 bg-gray-100 rounded"></div>
              </div>
            ))
          ) : statCards.map(card => (
            <div key={card.label} className={`${card.bg} rounded-xl p-4 border border-gray-100 shadow-sm`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xl">{card.icon}</span>
              </div>
              <div className={`text-3xl font-bold ${card.color}`}>{card.value}</div>
              <div className="text-sm text-gray-500 mt-1">{card.label}</div>
            </div>
          ))}
        </div>

        {/* Blog Table */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">资产列表</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-500 font-medium">博客名称</th>
                  <th className="text-left px-6 py-3 text-gray-500 font-medium">域名</th>
                  <th className="text-left px-6 py-3 text-gray-500 font-medium">主题</th>
                  <th className="text-left px-6 py-3 text-gray-500 font-medium">状态</th>
                  <th className="text-left px-6 py-3 text-gray-500 font-medium">最后部署</th>
                  <th className="text-left px-6 py-3 text-gray-500 font-medium">探活时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {loading ? (
                  <tr><td colSpan={6} className="text-center py-12 text-gray-400">加载中...</td></tr>
                ) : blogs.length === 0 ? (
                  <tr><td colSpan={6} className="text-center py-12 text-gray-400">暂无博客，前往「博客管理」创建第一个站点</td></tr>
                ) : blogs.map(blog => (
                  <tr key={blog.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 font-medium text-gray-900">{blog.name}</td>
                    <td className="px-6 py-4 text-gray-600">
                      <div>{blog.custom_domain || '-'}</div>
                      {blog.pages_domain && (
                        <div className="text-xs text-gray-400">{blog.pages_domain}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-gray-500 capitalize">{blog.theme?.replace('-', ' ')}</td>
                    <td className="px-6 py-4"><StatusBadge status={blog.status} /></td>
                    <td className="px-6 py-4 text-gray-500 text-xs">
                      {blog.last_deployed_at ? new Date(blog.last_deployed_at).toLocaleString('zh-CN') : '-'}
                    </td>
                    <td className="px-6 py-4 text-gray-500 text-xs">
                      {blog.last_checked_at ? new Date(blog.last_checked_at).toLocaleString('zh-CN') : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AuthLayout>
  )
}
