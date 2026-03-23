'use client'
import { useEffect, useState, useCallback } from 'react'
import AuthLayout from '@/components/AuthLayout'
import { blogsApi, accountsApi } from '@/lib/api'
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
}

interface Account {
  id: string
  name: string
  account_id: string
  status: string
}

const THEMES = [
  { value: 'minimal-white', label: '极简白色', desc: '干净、阅读向' },
  { value: 'dark-tech', label: '科技暗黑', desc: '深色、代码感' },
  { value: 'magazine', label: '杂志风格', desc: '多栏、图文混排' },
  { value: 'personal', label: '个人博客', desc: '卡片式、动态感' },
  { value: 'enterprise', label: '企业资讯', desc: '正式、SEO强化' },
]

const StatusBadge = ({ status }: { status: string }) => {
  const map: Record<string, { color: string; label: string }> = {
    online:    { color: 'bg-green-100 text-green-700', label: '在线' },
    offline:   { color: 'bg-red-100 text-red-700', label: '离线' },
    building:  { color: 'bg-yellow-100 text-yellow-700', label: '构建中' },
    deploying: { color: 'bg-blue-100 text-blue-700', label: '部署中' },
    error:     { color: 'bg-red-100 text-red-700', label: '错误' },
  }
  const s = map[status] || { color: 'bg-gray-100 text-gray-600', label: status }
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${s.color}`}>{s.label}</span>
}

export default function BlogsPage() {
  const [blogs, setBlogs] = useState<Blog[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [cnameInfo, setCnameInfo] = useState<any>(null)

  // 表单状态
  const [form, setForm] = useState({
    name: '',
    custom_domain: '',
    cf_account_id: '',
    theme: 'minimal-white',
    content_markdown: '',
  })
  const [formError, setFormError] = useState('')

  const loadData = useCallback(async () => {
    try {
      const [blogsRes, accountsRes] = await Promise.all([
        blogsApi.list(),
        accountsApi.list()
      ])
      setBlogs(blogsRes.data)
      setAccounts(accountsRes.data)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => {
    loadData()
    const timer = setInterval(loadData, 10000)
    return () => clearInterval(timer)
  }, [loadData])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!form.cf_account_id) {
      setFormError('请选择 CF 账号')
      return
    }
    setCreating(true)
    try {
      const res = await blogsApi.create(form)
      const newBlog = res.data
      setShowCreate(false)
      setForm({ name: '', custom_domain: '', cf_account_id: '', theme: 'minimal-white', content_markdown: '' })
      await loadData()

      // 轮询等待构建完成，然后弹出 CNAME 引导
      pollForCname(newBlog.id)
    } catch (err: any) {
      setFormError(err.response?.data?.detail || '创建失败')
    } finally {
      setCreating(false)
    }
  }

  const pollForCname = async (blogId: string) => {
    let attempts = 0
    const timer = setInterval(async () => {
      attempts++
      if (attempts > 30) {
        clearInterval(timer)
        return
      }
      try {
        const res = await blogsApi.get(blogId)
        const blog = res.data
        if (blog.pages_domain && ['online', 'deploying'].includes(blog.status)) {
          clearInterval(timer)
          const cnameRes = await blogsApi.getCnameInfo(blogId)
          setCnameInfo(cnameRes.data)
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
      alert('域名绑定请求已提交！DNS 生效通常需要 5-10 分钟，请耐心等待。')
      setCnameInfo(null)
    } catch (err: any) {
      alert(err.response?.data?.detail || '绑定失败，请确保 CNAME 已正确配置后重试')
    }
  }

  return (
    <AuthLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">博客管理</h1>
            <p className="text-sm text-gray-500 mt-1">管理所有博客站点，每 10 秒自动刷新</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <span>+</span> 新建博客
          </button>
        </div>

        {/* Blog Cards */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array(3).fill(0).map((_, i) => (
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
            <button
              onClick={() => setShowCreate(true)}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              立即创建
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {blogs.map(blog => (
              <div key={blog.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-gray-900 truncate flex-1 mr-2">{blog.name}</h3>
                  <StatusBadge status={blog.status} />
                </div>
                <div className="space-y-1.5 text-sm text-gray-500 mb-4">
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
                  {['building','deploying'].includes(blog.status) && blog.build_log && (
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
                <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                  {blog.pages_domain && blog.custom_domain && (
                    <button
                      onClick={async () => {
                        const res = await blogsApi.getCnameInfo(blog.id)
                        setCnameInfo(res.data)
                      }}
                      className="flex-1 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      📡 CNAME引导
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(blog.id, blog.name)}
                    className="flex-1 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    🗑️ 删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create Modal */}
        {showCreate && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">新建博客</h2>
                <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600">✕</button>
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">CF 账号 *</label>
                  <select required value={form.cf_account_id}
                    onChange={e => setForm(f => ({ ...f, cf_account_id: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none text-gray-900">
                    <option value="">-- 请选择（留空则自动分配负载最低账号）--</option>
                    {accounts.filter(a => a.status === 'active').map(a => (
                      <option key={a.id} value={a.id}>{a.name} ({a.account_id.slice(0, 8)}...)</option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-400 mt-1">不选则自动分配站点数最少的账号</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">主题风格</label>
                  <div className="grid grid-cols-1 gap-2">
                    {THEMES.map(theme => (
                      <label key={theme.value}
                        className={`flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer transition-colors ${
                          form.theme === theme.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                        }`}>
                        <input type="radio" name="theme" value={theme.value} checked={form.theme === theme.value}
                          onChange={e => setForm(f => ({ ...f, theme: e.target.value }))} className="hidden" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">{theme.label}</div>
                          <div className="text-xs text-gray-400">{theme.desc}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">首页内容（Markdown，可选）</label>
                  <textarea value={form.content_markdown}
                    onChange={e => setForm(f => ({ ...f, content_markdown: e.target.value }))}
                    rows={5}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none font-mono text-gray-900"
                    placeholder="# 欢迎来到我的博客&#10;&#10;填写您的首页内容..." />
                </div>
                <div className="flex gap-3 pt-2">
                  <button type="button" onClick={() => setShowCreate(false)}
                    className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50">
                    取消
                  </button>
                  <button type="submit" disabled={creating}
                    className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
                    {creating ? (
                      <><svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>构建发布中...</>
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
            onBind={() => handleBindDomain(cnameInfo.blog_id || blogs.find(b => b.pages_domain === cnameInfo.pages_domain)?.id || '')}
          />
        )}
      </div>
    </AuthLayout>
  )
}
