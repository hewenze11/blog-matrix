'use client'
import { useEffect, useState, useCallback } from 'react'
import AuthLayout from '@/components/AuthLayout'
import { blogsApi, accountsApi, statsApi } from '@/lib/api'
import CNAMEGuideModal from '@/components/CNAMEGuideModal'

interface Blog {
  id: string
  name: string
  slug: string
  custom_domain?: string
  pages_domain?: string
  theme: string
  status: string
  fail_count: number
  build_log?: string
  last_deployed_at?: string
  cf_account_id: string
  created_at: string
  content_markdown?: string
}

interface Account {
  id: string
  name: string
  account_id: string
  status: string
}

interface BlogStats {
  blog_id: string
  blog_name: string
  summary: {
    total_views: number
    today_views: number
    total_clicks: number
    today_clicks: number
    ctr_percent: number
  }
  top_countries: { country: string; count: number }[]
  device_breakdown: Record<string, number>
  daily_trend: { date: string; views: number; clicks: number }[]
}

const THEMES = [
  { value: 'minimal-white', label: '极简白色', desc: '干净、阅读向' },
  { value: 'dark-tech',     label: '科技暗黑', desc: '深色、代码感' },
  { value: 'magazine',      label: '杂志风格', desc: '多栏、图文混排' },
  { value: 'personal',      label: '个人博客', desc: '卡片式、动态感' },
  { value: 'enterprise',    label: '企业资讯', desc: '正式、SEO强化' },
]

const StatusBadge = ({ status }: { status: string }) => {
  const map: Record<string, { color: string; label: string }> = {
    online:    { color: 'bg-green-100 text-green-700',   label: '在线' },
    offline:   { color: 'bg-red-100 text-red-700',       label: '离线' },
    building:  { color: 'bg-yellow-100 text-yellow-700', label: '构建中' },
    deploying: { color: 'bg-blue-100 text-blue-700',     label: '部署中' },
    error:     { color: 'bg-red-100 text-red-700',       label: '错误' },
  }
  const s = map[status] || { color: 'bg-gray-100 text-gray-600', label: status }
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${s.color}`}>{s.label}</span>
}

export default function BlogsPage() {
  const [blogs, setBlogs]       = useState<Blog[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading]   = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating]     = useState(false)
  const [cnameInfo, setCnameInfo]   = useState<any>(null)

  // stats
  const [statsMap, setStatsMap]         = useState<Record<string, BlogStats>>({})
  const [expandedId, setExpandedId]     = useState<string | null>(null)
  const [loadingStats, setLoadingStats] = useState(false)

  // edit
  const [editingBlog, setEditingBlog] = useState<Blog | null>(null)
  const [editForm, setEditForm]       = useState({ name: '', theme: '', content_markdown: '' })
  const [editSaving, setEditSaving]   = useState(false)
  const [editError, setEditError]     = useState('')

  // create form
  const [form, setForm] = useState({
    name: '', custom_domain: '', cf_account_id: '', theme: 'minimal-white', content_markdown: '',
  })
  const [formError, setFormError] = useState('')

  const loadData = useCallback(async () => {
    try {
      const [br, ar] = await Promise.all([blogsApi.list(), accountsApi.list()])
      setBlogs(br.data)
      setAccounts(ar.data)
    } catch {}
    setLoading(false)
  }, [])

  const loadAllStats = useCallback(async (list: Blog[]) => {
    const online = list.filter(b => b.status === 'online')
    if (!online.length) return
    const results = await Promise.allSettled(online.map(b => statsApi.getBlogStats(b.id, '30d')))
    setStatsMap(prev => {
      const m = { ...prev }
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') m[online[i].id] = r.value.data
      })
      return m
    })
  }, [])

  useEffect(() => {
    loadData()
    const t = setInterval(loadData, 10000)
    return () => clearInterval(t)
  }, [loadData])

  useEffect(() => {
    if (blogs.length) loadAllStats(blogs)
  }, [blogs, loadAllStats])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setCreating(true)
    try {
      const res = await blogsApi.create(form)
      setShowCreate(false)
      setForm({ name: '', custom_domain: '', cf_account_id: '', theme: 'minimal-white', content_markdown: '' })
      await loadData()
      pollForCname(res.data.id)
    } catch (err: any) {
      setFormError(err.response?.data?.detail || '创建失败')
    } finally { setCreating(false) }
  }

  const pollForCname = (blogId: string) => {
    let n = 0
    const t = setInterval(async () => {
      if (++n > 30) { clearInterval(t); return }
      try {
        const r = await blogsApi.get(blogId)
        if (r.data.pages_domain && ['online', 'deploying'].includes(r.data.status)) {
          clearInterval(t)
          const c = await blogsApi.getCnameInfo(blogId)
          setCnameInfo(c.data)
        }
      } catch {}
    }, 3000)
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确认删除博客「${name}」？此操作不可撤销。`)) return
    await blogsApi.delete(id)
    loadData()
  }

  const handleBindDomain = async (blogId: string) => {
    try {
      await blogsApi.bindDomain(blogId)
      alert('域名绑定请求已提交！DNS 生效通常需要 5-10 分钟。')
      setCnameInfo(null)
    } catch (err: any) {
      alert(err.response?.data?.detail || '绑定失败，请确保 CNAME 已正确配置后重试')
    }
  }

  const openEdit = (blog: Blog) => {
    setEditingBlog(blog)
    setEditForm({ name: blog.name, theme: blog.theme, content_markdown: blog.content_markdown || '' })
    setEditError('')
  }

  const handleEditSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingBlog) return
    setEditSaving(true)
    setEditError('')
    try {
      await blogsApi.update(editingBlog.id, editForm)
      setEditingBlog(null)
      await loadData()
    } catch (err: any) {
      setEditError(err.response?.data?.detail || '保存失败，请重试')
    } finally { setEditSaving(false) }
  }

  const toggleExpand = async (blogId: string) => {
    if (expandedId === blogId) { setExpandedId(null); return }
    setExpandedId(blogId)
    setLoadingStats(true)
    try {
      const r = await statsApi.getBlogStats(blogId, '7d')
      setStatsMap(m => ({ ...m, [blogId]: r.data }))
    } catch {}
    setLoadingStats(false)
  }

  return (
    <AuthLayout>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">博客管理</h1>
            <p className="text-sm text-gray-500 mt-1">管理所有博客站点，每 10 秒自动刷新</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2"
          >
            <span>+</span> 新建博客
          </button>
        </div>

        {/* Blog list */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[0, 1, 2].map(i => (
              <div key={i} className="bg-white rounded-xl p-5 animate-pulse">
                <div className="h-5 bg-gray-200 rounded mb-3 w-3/4"></div>
                <div className="h-4 bg-gray-100 rounded mb-2"></div>
                <div className="h-4 bg-gray-100 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : blogs.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-xl border border-gray-100">
            <div className="text-4xl mb-4">📝</div>
            <p className="text-gray-500 mb-4">还没有博客，创建第一个站点吧！</p>
            <button onClick={() => setShowCreate(true)}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
              立即创建
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {blogs.map(blog => {
              const st = statsMap[blog.id]
              return (
                <div key={blog.id}
                  className="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow flex flex-col">
                  <div className="p-5 flex-1">
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="font-semibold text-gray-900 truncate flex-1 mr-2">{blog.name}</h3>
                      <StatusBadge status={blog.status} />
                    </div>
                    <div className="space-y-1.5 text-sm text-gray-500">
                      {blog.custom_domain && (
                        <div className="flex items-center gap-1.5">
                          <span>🔗</span>
                          <a href={`https://${blog.custom_domain}`} target="_blank" rel="noopener noreferrer"
                            className="text-blue-500 hover:underline truncate">{blog.custom_domain}</a>
                        </div>
                      )}
                      {blog.pages_domain && (
                        <div className="flex items-center gap-1.5">
                          <span>☁️</span>
                          <a href={`https://${blog.pages_domain}`} target="_blank" rel="noopener noreferrer"
                            className="text-gray-400 hover:text-blue-400 truncate text-xs">{blog.pages_domain}</a>
                        </div>
                      )}
                      <div className="flex items-center gap-1.5">
                        <span>🎨</span>
                        <span>{THEMES.find(t => t.value === blog.theme)?.label || blog.theme}</span>
                      </div>
                      {blog.last_deployed_at && (
                        <div className="flex items-center gap-1.5">
                          <span>🕐</span>
                          <span>{new Date(blog.last_deployed_at).toLocaleString('zh-CN')}</span>
                        </div>
                      )}
                      {['building', 'deploying'].includes(blog.status) && blog.build_log && (
                        <div className="mt-2 p-2 bg-yellow-50 rounded text-xs text-yellow-700 border border-yellow-200">
                          ⚙️ {blog.build_log}
                        </div>
                      )}
                      {blog.status === 'error' && blog.build_log && (
                        <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-700 border border-red-200">
                          ❌ {blog.build_log}
                        </div>
                      )}
                    </div>
                    {/* Stats summary */}
                    {blog.status === 'online' && st && (
                      <div className="mt-3 pt-3 border-t border-gray-50 flex items-center gap-3 text-xs text-gray-500">
                        <span title="总访问" className="flex items-center gap-1">
                          👁 <strong className="text-gray-700">{st.summary.total_views.toLocaleString()}</strong>
                          {st.summary.today_views > 0 && (
                            <span className="text-green-500">+{st.summary.today_views}</span>
                          )}
                        </span>
                        <span title="apimart点击" className="flex items-center gap-1">
                          🖱 <strong className="text-gray-700">{st.summary.total_clicks.toLocaleString()}</strong>
                        </span>
                        <span title="转化率" className="flex items-center gap-1">
                          📈 <strong className={
                            st.summary.ctr_percent >= 5 ? 'text-green-600'
                            : st.summary.ctr_percent >= 2 ? 'text-yellow-600'
                            : 'text-gray-600'
                          }>{st.summary.ctr_percent}%</strong>
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-1 px-3 pb-3 border-t border-gray-50 pt-2">
                    {blog.status === 'online' && (
                      <button
                        onClick={() => toggleExpand(blog.id)}
                        className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          expandedId === blog.id
                            ? 'bg-blue-100 text-blue-700'
                            : 'text-blue-600 hover:bg-blue-50'
                        }`}
                      >
                        📊 {expandedId === blog.id ? '收起' : '数据'}
                      </button>
                    )}
                    <button
                      onClick={() => openEdit(blog)}
                      className="flex-1 py-1.5 text-xs font-medium text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                    >
                      ✏️ 编辑
                    </button>
                    {blog.pages_domain && blog.custom_domain && (
                      <button
                        onClick={async () => {
                          const r = await blogsApi.getCnameInfo(blog.id)
                          setCnameInfo(r.data)
                        }}
                        className="flex-1 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                      >
                        📡 CNAME
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(blog.id, blog.name)}
                      className="flex-1 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      🗑️
                    </button>
                  </div>

                  {/* Expanded stats panel */}
                  {expandedId === blog.id && (
                    <div className="border-t border-gray-100 p-4 bg-gray-50 rounded-b-xl">
                      {loadingStats && !st ? (
                        <div className="text-center text-xs text-gray-400 py-4">加载中…</div>
                      ) : st ? (
                        <div className="space-y-3">
                          <div className="grid grid-cols-3 gap-2 text-center">
                            <div className="bg-white rounded-lg p-2 shadow-sm">
                              <div className="text-base font-bold text-blue-600">{st.summary.total_views.toLocaleString()}</div>
                              <div className="text-xs text-gray-400">总访问</div>
                            </div>
                            <div className="bg-white rounded-lg p-2 shadow-sm">
                              <div className="text-base font-bold text-green-600">{st.summary.total_clicks.toLocaleString()}</div>
                              <div className="text-xs text-gray-400">总点击</div>
                            </div>
                            <div className="bg-white rounded-lg p-2 shadow-sm">
                              <div className={`text-base font-bold ${st.summary.ctr_percent >= 5 ? 'text-green-600' : 'text-orange-500'}`}>
                                {st.summary.ctr_percent}%
                              </div>
                              <div className="text-xs text-gray-400">转化率</div>
                            </div>
                          </div>
                          {st.daily_trend && st.daily_trend.length > 0 && (
                            <div>
                              <div className="text-xs font-medium text-gray-400 mb-1">近7天趋势</div>
                              <div className="flex items-end gap-0.5 h-10">
                                {st.daily_trend.slice(-7).map(d => {
                                  const maxV = Math.max(...st.daily_trend.slice(-7).map(x => x.views), 1)
                                  const h = Math.max(2, Math.round(d.views / maxV * 36))
                                  return (
                                    <div key={d.date} className="flex-1 flex flex-col items-center gap-0.5"
                                      title={`${d.date}: ${d.views}访问`}>
                                      <div className="w-full bg-blue-300 rounded-sm" style={{ height: `${h}px` }}></div>
                                      <div className="text-gray-300" style={{ fontSize: '7px' }}>{d.date.slice(5)}</div>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          )}
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="bg-white rounded-lg p-2">
                              <div className="font-medium text-gray-500 mb-1">📱 设备</div>
                              {Object.entries(st.device_breakdown).map(([d, p]) => (
                                <div key={d} className="flex justify-between text-gray-400">
                                  <span>{d === 'mobile' ? '手机' : d === 'desktop' ? '电脑' : d}</span>
                                  <span>{p}%</span>
                                </div>
                              ))}
                              {Object.keys(st.device_breakdown).length === 0 && (
                                <div className="text-gray-300">暂无</div>
                              )}
                            </div>
                            <div className="bg-white rounded-lg p-2">
                              <div className="font-medium text-gray-500 mb-1">🌍 地区</div>
                              {st.top_countries.slice(0, 3).map(c => (
                                <div key={c.country} className="flex justify-between text-gray-400">
                                  <span>{c.country}</span><span>{c.count}</span>
                                </div>
                              ))}
                              {st.top_countries.length === 0 && (
                                <div className="text-gray-300">暂无</div>
                              )}
                            </div>
                          </div>
                          <div className="text-xs text-gray-400 bg-white rounded-lg p-2 flex gap-4">
                            <span>今日访问 <strong className="text-blue-600">{st.summary.today_views}</strong></span>
                            <span>今日点击 <strong className="text-green-600">{st.summary.today_clicks}</strong></span>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center text-xs text-gray-400 py-4">暂无统计数据</div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* ===== Edit Modal ===== */}
        {editingBlog && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">编辑博客</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    修改后点「重新发布」，平台将自动重新构建并推送到 CF Pages
                  </p>
                </div>
                <button onClick={() => setEditingBlog(null)}
                  className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
              </div>
              <form onSubmit={handleEditSave} className="p-6 space-y-5">
                {editError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">{editError}</div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">博客名称</label>
                  <input type="text" required value={editForm.name}
                    onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none text-gray-900" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">主题风格</label>
                  <div className="grid grid-cols-2 gap-2">
                    {THEMES.map(t => (
                      <label key={t.value}
                        className={`flex items-center gap-2 p-3 border-2 rounded-lg cursor-pointer transition-colors ${
                          editForm.theme === t.value
                            ? 'border-purple-500 bg-purple-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}>
                        <input type="radio" name="edit_theme" value={t.value}
                          checked={editForm.theme === t.value}
                          onChange={e => setEditForm(f => ({ ...f, theme: e.target.value }))}
                          className="hidden" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">{t.label}</div>
                          <div className="text-xs text-gray-400">{t.desc}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    首页 Markdown 内容
                    <span className="text-gray-400 font-normal ml-2 text-xs">
                      apimart.ai 软广会自动注入，无需手写
                    </span>
                  </label>
                  <textarea
                    value={editForm.content_markdown}
                    onChange={e => setEditForm(f => ({ ...f, content_markdown: e.target.value }))}
                    rows={12}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none font-mono text-gray-900 resize-y"
                    placeholder={'# 欢迎来到我的博客\n\n## 关于本站\n\n介绍内容...'}
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    支持 # 标题 / **加粗** / *斜体* / [链接](url) 语法
                  </p>
                </div>
                <div className="flex gap-3">
                  <button type="button" onClick={() => setEditingBlog(null)}
                    className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50">
                    取消
                  </button>
                  <button type="submit" disabled={editSaving}
                    className="flex-1 py-2.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2">
                    {editSaving ? (
                      <>
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        重新发布中…
                      </>
                    ) : '🚀 重新发布'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ===== Create Modal ===== */}
        {showCreate && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
                <h2 className="text-lg font-bold text-gray-900">新建博客</h2>
                <button onClick={() => setShowCreate(false)}
                  className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
              </div>
              <form onSubmit={handleCreate} className="p-6 space-y-4">
                {formError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">{formError}</div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">博客名称 *</label>
                  <input type="text" required value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none text-gray-900"
                    placeholder="例如：科技前沿资讯" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">主域名 *</label>
                  <input type="text" required value={form.custom_domain}
                    onChange={e => setForm(f => ({ ...f, custom_domain: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none text-gray-900"
                    placeholder="例如：myblog.com（不含 https://）" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">CF 账号</label>
                  <select value={form.cf_account_id}
                    onChange={e => setForm(f => ({ ...f, cf_account_id: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none text-gray-900">
                    <option value="">-- 自动分配负载最低账号 --</option>
                    {accounts.filter(a => a.status === 'active').map(a => (
                      <option key={a.id} value={a.id}>{a.name} ({a.account_id.slice(0, 8)}…)</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">主题风格</label>
                  <div className="grid grid-cols-1 gap-2">
                    {THEMES.map(t => (
                      <label key={t.value}
                        className={`flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer transition-colors ${
                          form.theme === t.value
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}>
                        <input type="radio" name="theme" value={t.value}
                          checked={form.theme === t.value}
                          onChange={e => setForm(f => ({ ...f, theme: e.target.value }))}
                          className="hidden" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">{t.label}</div>
                          <div className="text-xs text-gray-400">{t.desc}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    首页内容（Markdown，可选）
                  </label>
                  <textarea value={form.content_markdown}
                    onChange={e => setForm(f => ({ ...f, content_markdown: e.target.value }))}
                    rows={5}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none font-mono text-gray-900"
                    placeholder={'# 欢迎来到我的博客\n\n填写您的首页内容...'} />
                </div>
                <div className="flex gap-3 pt-2">
                  <button type="button" onClick={() => setShowCreate(false)}
                    className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50">
                    取消
                  </button>
                  <button type="submit" disabled={creating}
                    className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
                    {creating ? (
                      <>
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        构建发布中…
                      </>
                    ) : '🚀 立即创建'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* CNAME Guide Modal */}
        {cnameInfo && (
          <CNAMEGuideModal
            info={cnameInfo}
            onClose={() => setCnameInfo(null)}
            onBind={() => handleBindDomain(
              cnameInfo.blog_id || blogs.find(b => b.pages_domain === cnameInfo.pages_domain)?.id || ''
            )}
          />
        )}
      </div>
    </AuthLayout>
  )
}
