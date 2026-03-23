'use client'
import { useEffect, useState, useCallback } from 'react'
import AuthLayout from '@/components/AuthLayout'
import api from '@/lib/api'

interface Task {
  id: string
  blog_id: string
  blog_name: string
  theme: string
  status: 'pending' | 'running' | 'success' | 'failed'
  queue_position: number
  log: string
  started_at?: string
  finished_at?: string
  created_at: string
  duration_seconds?: number
}

interface QueueData {
  semaphore_locked: boolean
  concurrency_limit: number
  pending_count: number
  running_count: number
  tasks: Task[]
}

const STATUS_CONFIG = {
  pending:  { label: '排队等待', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: '⏳', dot: 'bg-yellow-400' },
  running:  { label: '编译中',   color: 'bg-blue-100 text-blue-700 border-blue-200',   icon: '⚙️', dot: 'bg-blue-500 status-dot-pulse' },
  success:  { label: '成功',     color: 'bg-green-100 text-green-700 border-green-200', icon: '✅', dot: 'bg-green-500' },
  failed:   { label: '失败',     color: 'bg-red-100 text-red-700 border-red-200',     icon: '❌', dot: 'bg-red-500' },
}

function StatusBadge({ status }: { status: Task['status'] }) {
  const s = STATUS_CONFIG[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${s.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`}></span>
      {s.label}
    </span>
  )
}

function formatDuration(seconds?: number): string {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m${seconds % 60}s`
}

function TaskLogViewer({ log }: { log: string }) {
  return (
    <div className="mt-2 bg-gray-900 text-green-400 rounded-lg p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap max-h-24 overflow-y-auto">
      {log}
    </div>
  )
}

export default function TaskQueuePage() {
  const [data, setData] = useState<QueueData | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const loadTasks = useCallback(async () => {
    try {
      const res = await api.get('/tasks')
      setData(res.data)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => {
    loadTasks()
    // 有运行中任务时 3s 刷新，否则 10s 刷新
    const timer = setInterval(() => {
      loadTasks()
    }, data?.running_count || data?.pending_count ? 3000 : 10000)
    return () => clearInterval(timer)
  }, [loadTasks, data?.running_count, data?.pending_count])

  const activeCount = (data?.running_count || 0) + (data?.pending_count || 0)

  return (
    <AuthLayout>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">构建任务队列</h1>
            <p className="text-sm text-gray-500 mt-1">
              串行执行，防止并发编译导致 OOM · {activeCount > 0 ? `🔴 ${activeCount} 个任务活跃，每 3 秒自动刷新` : '✅ 队列空闲，每 10 秒刷新'}
            </p>
          </div>
          <button onClick={loadTasks} className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg text-sm hover:bg-gray-50 transition-colors">
            🔄 刷新
          </button>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">并发限制</span>
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">防OOM</span>
            </div>
            <div className="text-2xl font-bold text-gray-800">{data?.concurrency_limit ?? 1} 个</div>
            <div className="text-xs text-gray-400 mt-1">同时最多运行数</div>
          </div>
          <div className={`rounded-xl border p-4 shadow-sm ${data?.running_count ? 'bg-blue-50 border-blue-200' : 'bg-white border-gray-100'}`}>
            <div className="text-sm text-gray-500 mb-2">编译中</div>
            <div className={`text-2xl font-bold ${data?.running_count ? 'text-blue-600' : 'text-gray-400'}`}>
              {data?.running_count ?? 0}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {data?.semaphore_locked ? '🔒 构建槽已占用' : '🔓 构建槽空闲'}
            </div>
          </div>
          <div className={`rounded-xl border p-4 shadow-sm ${data?.pending_count ? 'bg-yellow-50 border-yellow-200' : 'bg-white border-gray-100'}`}>
            <div className="text-sm text-gray-500 mb-2">排队等待</div>
            <div className={`text-2xl font-bold ${data?.pending_count ? 'text-yellow-600' : 'text-gray-400'}`}>
              {data?.pending_count ?? 0}
            </div>
            <div className="text-xs text-gray-400 mt-1">等待构建槽</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
            <div className="text-sm text-gray-500 mb-2">历史任务</div>
            <div className="text-2xl font-bold text-gray-700">{data?.tasks.length ?? 0}</div>
            <div className="text-xs text-gray-400 mt-1">最近 50 条</div>
          </div>
        </div>

        {/* 队列可视化 */}
        {(data?.pending_count || 0) > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <span>⏳</span>
              <span className="font-semibold text-yellow-800">队列状态</span>
              <span className="text-yellow-600 text-sm">（排队中，依次执行）</span>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {/* 正在运行 */}
              {data?.tasks.filter(t => t.status === 'running').map(t => (
                <div key={t.id} className="flex items-center gap-1.5 bg-blue-100 text-blue-700 px-3 py-1.5 rounded-lg text-xs font-medium border border-blue-300">
                  <span className="animate-spin">⚙️</span>
                  <span>{t.blog_name}</span>
                  <span className="text-blue-400">[运行中]</span>
                </div>
              ))}
              {(data?.pending_count || 0) > 0 && (
                <div className="text-gray-400 text-sm">→</div>
              )}
              {/* 排队中 */}
              {data?.tasks
                .filter(t => t.status === 'pending')
                .sort((a, b) => a.queue_position - b.queue_position)
                .map((t, i) => (
                  <div key={t.id} className="flex items-center gap-1.5 bg-yellow-100 text-yellow-700 px-3 py-1.5 rounded-lg text-xs font-medium border border-yellow-300">
                    <span className="font-bold text-yellow-500">#{i + 1}</span>
                    <span>{t.blog_name}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Task Table */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">任务列表</h2>
            <span className="text-xs text-gray-400">点击任意任务展开构建日志</span>
          </div>

          {loading ? (
            <div className="p-8 text-center text-gray-400">加载中...</div>
          ) : !data?.tasks.length ? (
            <div className="p-12 text-center">
              <div className="text-4xl mb-3">🎯</div>
              <p className="text-gray-400">还没有构建任务，创建博客后这里会显示编译进度</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {data.tasks.map(task => (
                <div key={task.id}>
                  <div
                    className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => setExpandedId(expandedId === task.id ? null : task.id)}
                  >
                    <div className="flex items-center gap-4">
                      {/* Status */}
                      <StatusBadge status={task.status} />

                      {/* Queue position for pending */}
                      {task.status === 'pending' && task.queue_position > 0 && (
                        <span className="text-xs text-yellow-600 font-medium bg-yellow-50 px-2 py-0.5 rounded-full border border-yellow-200">
                          第 {task.queue_position} 位
                        </span>
                      )}

                      {/* Blog name */}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 truncate">{task.blog_name}</div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          主题: {task.theme} · task_id: {task.id.slice(0, 8)}...
                        </div>
                      </div>

                      {/* Duration */}
                      <div className="text-right text-sm text-gray-500">
                        <div>{formatDuration(task.duration_seconds)}</div>
                        <div className="text-xs text-gray-400">
                          {new Date(task.created_at).toLocaleString('zh-CN')}
                        </div>
                      </div>

                      {/* Expand icon */}
                      <span className={`text-gray-400 transition-transform ${expandedId === task.id ? 'rotate-180' : ''}`}>
                        ▾
                      </span>
                    </div>

                    {/* Running progress bar */}
                    {task.status === 'running' && (
                      <div className="mt-2 h-1 bg-blue-100 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                      </div>
                    )}
                  </div>

                  {/* Expanded log */}
                  {expandedId === task.id && (
                    <div className="px-6 pb-4 bg-gray-50">
                      <div className="text-xs font-medium text-gray-500 mb-1">构建日志</div>
                      <TaskLogViewer log={task.log || '暂无日志'} />
                      <div className="mt-2 flex gap-4 text-xs text-gray-400">
                        {task.started_at && (
                          <span>🏁 开始: {new Date(task.started_at).toLocaleString('zh-CN')}</span>
                        )}
                        {task.finished_at && (
                          <span>🏆 结束: {new Date(task.finished_at).toLocaleString('zh-CN')}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AuthLayout>
  )
}
