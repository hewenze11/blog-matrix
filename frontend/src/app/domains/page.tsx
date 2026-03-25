'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import AuthLayout from '@/components/AuthLayout'
import { domainsApi, registrarsApi, blogsApi } from '@/lib/api'

interface Domain {
  id: string
  domain_name: string
  status: string
  blog_id?: string
  blog_name?: string
  registrar_id?: string
  registrar_name?: string
  expires_at?: string
  registered_at?: string
  created_at: string
  error_message?: string
}

interface Registrar {
  id: string
  name: string
  provider: string
}

interface Blog {
  id: string
  name: string
}

interface CheckResult {
  domain: string
  available: boolean
  price?: number
  currency?: string
  message?: string
}

const STATUS_MAP: Record<string, { label: string; color: string; animate: boolean }> = {
  pending_registration: { label: '等待注册',    color: 'bg-yellow-100 text-yellow-700', animate: false },
  registering:          { label: '注册中...',   color: 'bg-blue-100 text-blue-700',    animate: true  },
  registered:           { label: '注册成功',    color: 'bg-cyan-100 text-cyan-700',    animate: false },
  dns_configuring:      { label: '配置DNS中...', color: 'bg-blue-100 text-blue-700',   animate: true  },
  dns_configured:       { label: 'DNS已配置',   color: 'bg-teal-100 text-teal-700',   animate: false },
  cf_binding:           { label: '绑定CF中...',  color: 'bg-indigo-100 text-indigo-700', animate: true },
  active:               { label: '已激活',       color: 'bg-green-100 text-green-700', animate: false },
  error:                { label: '错误',         color: 'bg-red-100 text-red-700',     animate: false },
}

const StatusBadge = ({ status }: { status: string }) => {
  const s = STATUS_MAP[status] || { label: status, color: 'bg-gray-100 text-gray-600', animate: false }
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${s.color}`}>
      {s.animate && (
        <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {s.label}
    </span>
  )
}

export default function DomainsPage() {
  const [domains, setDomains]       = useState<Domain[]>([])
  const [registrars, setRegistrars] = useState<Registrar[]>([])
  const [blogs, setBlogs]           = useState<Blog[]>([])
  const [loading, setLoading]       = useState(true)

  // Check availability form
  const [checkForm, setCheckForm]   = useState({ domain: '', registrar_id: '' })
  const [checking, setChecking]     = useState(false)
  const [checkResult, setCheckResult] = useState<CheckResult | null>(null)

  // Register form
  const [showRegister, setShowRegister] = useState(false)
  const [registerForm, setRegisterForm] = useState({
    domain_name: '', registrar_id: '', blog_id: '',
  })
  const [registering, setRegistering] = useState(false)
  const [registerError, setRegisterError] = useState('')

  // Polling refs for in-progress domains
  const pollingRef = useRef<Map<string, NodeJS.Timeout>>(new Map())

  const loadData = useCallback(async () => {
    try {
      const [dr, rr, br] = await Promise.all([
        domainsApi.list(),
        registrarsApi.list(),
        blogsApi.list(),
      ])
      setDomains(dr.data)
      setRegistrars(rr.data)
      setBlogs(br.data)
    } catch {}
    setLoading(false)
  }, [])

  const pollDomain = useCallback((id: string) => {
    if (pollingRef.current.has(id)) return
    const t = setInterval(async () => {
      try {
        const r = await domainsApi.get(id)
        const d: Domain = r.data
        setDomains(prev => prev.map(x => x.id === id ? { ...x, ...d } : x))
        if (d.status === 'active' || d.status === 'error') {
          clearInterval(t)
          pollingRef.current.delete(id)
        }
      } catch {
        clearInterval(t)
        pollingRef.current.delete(id)
      }
    }, 4000)
    pollingRef.current.set(id, t)
  }, [])

  useEffect(() => {
    loadData()
    return () => {
      pollingRef.current.forEach(t => clearInterval(t))
    }
  }, [loadData])

  // Start polling for non-terminal domains
  useEffect(() => {
    const inProgress = domains.filter(d =>
      !['active', 'error'].includes(d.status)
    )
    inProgress.forEach(d => pollDomain(d.id))
  }, [domains, pollDomain])

  const handleCheck = async (e: React.FormEvent) => {
    e.preventDefault()
    setChecking(true)
    setCheckResult(null)
    try {
      const res = await domainsApi.check(checkForm)
      setCheckResult(res.data)
    } catch (err: any) {
      setCheckResult({
        domain: checkForm.domain,
        available: false,
        message: err.response?.data?.detail || '查询失败，请稍后重试',
      })
    } finally {
      setChecking(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setRegisterError('')
    setRegistering(true)
    try {
      const res = await domainsApi.register(registerForm)
      setShowRegister(false)
      setRegisterForm({ domain_name: '', registrar_id: '', blog_id: '' })
      await loadData()
      // Start polling the new domain
      if (res.data?.id) pollDomain(res.data.id)
    } catch (err: any) {
      setRegisterError(err.response?.data?.detail || '注册失败，请重试')
    } finally {
      setRegistering(false)
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确认删除域名「${name}」？`)) return
    await domainsApi.delete(id)
    loadData()
  }

  const prefillRegister = (domain: string) => {
    setRegisterForm(f => ({ ...f, domain_name: domain }))
    setShowRegister(true)
  }

  return (
    <AuthLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">域名管理</h1>
            <p className="text-sm text-gray-500 mt-1">查询域名可用性、注册域名、查看状态流水线</p>
          </div>
          <div className="flex items-center gap-2">
            <a href="/registrars"
              className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-200">
              🏢 注册商账号
            </a>
            <a href="/blogs"
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">
              ← 返回博客
            </a>
            <button
              onClick={() => setShowRegister(true)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
            >
              + 注册域名
            </button>
          </div>
        </div>

        {/* Check availability */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">🔍 查询域名可用性</h2>
          <form onSubmit={handleCheck} className="flex items-end gap-3 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs text-gray-500 mb-1">域名</label>
              <input
                type="text" required value={checkForm.domain}
                onChange={e => setCheckForm(f => ({ ...f, domain: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                placeholder="例如：example.com"
              />
            </div>
            <div className="min-w-[180px]">
              <label className="block text-xs text-gray-500 mb-1">注册商账号</label>
              <select
                value={checkForm.registrar_id}
                onChange={e => setCheckForm(f => ({ ...f, registrar_id: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
              >
                <option value="">-- 选择账号 --</option>
                {registrars.map(r => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
            <button type="submit" disabled={checking}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
              {checking ? '查询中…' : '查询'}
            </button>
          </form>

          {checkResult && (
            <div className={`mt-3 p-3 rounded-lg text-sm ${
              checkResult.available
                ? 'bg-green-50 border border-green-200 text-green-800'
                : 'bg-gray-50 border border-gray-200 text-gray-700'
            }`}>
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium">{checkResult.domain}</span>
                  <span className="ml-2">{checkResult.available ? '✅ 可以注册' : '❌ 不可注册'}</span>
                  {checkResult.price && (
                    <span className="ml-2 text-gray-500">
                      首年价格：{checkResult.price} {checkResult.currency || 'CNY'}
                    </span>
                  )}
                  {checkResult.message && (
                    <span className="ml-2 text-gray-500">{checkResult.message}</span>
                  )}
                </div>
                {checkResult.available && (
                  <button
                    onClick={() => prefillRegister(checkResult.domain)}
                    className="px-3 py-1 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700"
                  >
                    立即注册
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Domain list */}
        {loading ? (
          <div className="bg-white rounded-xl p-8 text-center text-gray-400">加载中…</div>
        ) : domains.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl border border-gray-100">
            <div className="text-4xl mb-4">🌐</div>
            <p className="text-gray-500 mb-4">还没有域名，注册第一个吧！</p>
            <button onClick={() => setShowRegister(true)}
              className="px-6 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">
              注册域名
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">域名</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">状态</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">关联博客</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">注册商</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">到期时间</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {domains.map(d => (
                  <tr key={d.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      <a href={`https://${d.domain_name}`} target="_blank" rel="noopener noreferrer"
                        className="hover:text-blue-600 hover:underline">{d.domain_name}</a>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <StatusBadge status={d.status} />
                        {d.status === 'error' && d.error_message && (
                          <div className="text-xs text-red-500 mt-1 max-w-[160px] truncate" title={d.error_message}>
                            {d.error_message}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{d.blog_name || '—'}</td>
                    <td className="px-4 py-3 text-gray-500">{d.registrar_name || '—'}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {d.expires_at ? new Date(d.expires_at).toLocaleDateString('zh-CN') : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDelete(d.id, d.domain_name)}
                        className="px-3 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Status pipeline legend */}
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <h3 className="text-xs font-semibold text-gray-500 mb-2">域名状态流水线</h3>
          <div className="flex items-center gap-1 flex-wrap text-xs">
            {Object.entries(STATUS_MAP).map(([key, val], i, arr) => (
              <span key={key} className="flex items-center gap-1">
                <span className={`px-2 py-0.5 rounded-full ${val.color}`}>{val.label}</span>
                {i < arr.length - 1 && <span className="text-gray-300">→</span>}
              </span>
            ))}
          </div>
        </div>

        {/* Register Modal */}
        {showRegister && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
              <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">注册域名</h2>
                <button onClick={() => setShowRegister(false)}
                  className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
              </div>
              <form onSubmit={handleRegister} className="p-6 space-y-4">
                {registerError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">{registerError}</div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">域名 *</label>
                  <input
                    type="text" required value={registerForm.domain_name}
                    onChange={e => setRegisterForm(f => ({ ...f, domain_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none text-gray-900"
                    placeholder="例如：myblog.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">注册商账号 *</label>
                  <select
                    required value={registerForm.registrar_id}
                    onChange={e => setRegisterForm(f => ({ ...f, registrar_id: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none text-gray-900"
                  >
                    <option value="">-- 选择注册商账号 --</option>
                    {registrars.map(r => (
                      <option key={r.id} value={r.id}>{r.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">关联博客（可选）</label>
                  <select
                    value={registerForm.blog_id}
                    onChange={e => setRegisterForm(f => ({ ...f, blog_id: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none text-gray-900"
                  >
                    <option value="">-- 暂不关联 --</option>
                    {blogs.map(b => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-3 pt-2">
                  <button type="button" onClick={() => setShowRegister(false)}
                    className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50">
                    取消
                  </button>
                  <button type="submit" disabled={registering}
                    className="flex-1 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50">
                    {registering ? '注册中…' : '🚀 立即注册'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AuthLayout>
  )
}
