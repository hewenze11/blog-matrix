'use client'
import { useEffect, useState } from 'react'
import AuthLayout from '@/components/AuthLayout'
import { registrarsApi } from '@/lib/api'

interface Registrar {
  id: string
  name: string
  provider: string
  secret_id: string
  status: string
  domain_count: number
  last_verified_at?: string
  created_at: string
}

const PROVIDERS = [
  { value: 'tencentcloud', label: '腾讯云' },
  { value: 'aliyun', label: '阿里云' },
]

const StatusBadge = ({ status }: { status: string }) => {
  const map: Record<string, { color: string; label: string }> = {
    active:   { color: 'bg-green-100 text-green-700',  label: '正常' },
    inactive: { color: 'bg-gray-100 text-gray-600',    label: '未验证' },
    error:    { color: 'bg-red-100 text-red-700',      label: '异常' },
  }
  const s = map[status] || { color: 'bg-gray-100 text-gray-600', label: status }
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${s.color}`}>{s.label}</span>
}

export default function RegistrarsPage() {
  const [registrars, setRegistrars] = useState<Registrar[]>([])
  const [loading, setLoading]       = useState(true)
  const [showAdd, setShowAdd]       = useState(false)
  const [form, setForm]             = useState({
    name: '', provider: 'tencentcloud', secret_id: '', secret_key: '',
  })
  const [formError, setFormError]   = useState('')
  const [adding, setAdding]         = useState(false)
  const [verifyingId, setVerifyingId] = useState<string | null>(null)

  const loadData = async () => {
    try {
      const res = await registrarsApi.list()
      setRegistrars(res.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { loadData() }, [])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setAdding(true)
    try {
      await registrarsApi.create(form)
      setShowAdd(false)
      setForm({ name: '', provider: 'tencentcloud', secret_id: '', secret_key: '' })
      loadData()
    } catch (err: any) {
      setFormError(err.response?.data?.detail || '添加失败，请检查凭证信息')
    } finally {
      setAdding(false)
    }
  }

  const handleVerify = async (id: string) => {
    setVerifyingId(id)
    try {
      const res = await registrarsApi.verify(id)
      alert(`验证完成：${res.data.is_valid ? '✅ 凭证有效' : '❌ 凭证无效'}\n域名数：${res.data.domain_count ?? 0}`)
      loadData()
    } catch (err: any) {
      alert('验证请求失败：' + (err.response?.data?.detail || err.message))
    } finally {
      setVerifyingId(null)
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确认删除注册商账号「${name}」？`)) return
    await registrarsApi.delete(id)
    loadData()
  }

  return (
    <AuthLayout>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">注册商账号管理</h1>
            <p className="text-sm text-gray-500 mt-1">管理腾讯云、阿里云等域名注册商账号</p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/blogs"
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200"
            >
              ← 返回博客
            </a>
            <button
              onClick={() => setShowAdd(true)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700"
            >
              + 添加账号
            </button>
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <div className="bg-white rounded-xl p-8 text-center text-gray-400">加载中…</div>
        ) : registrars.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-xl border border-gray-100">
            <div className="text-4xl mb-4">🏢</div>
            <p className="text-gray-500 mb-4">还没有注册商账号，添加第一个吧！</p>
            <button onClick={() => setShowAdd(true)}
              className="px-6 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700">
              立即添加
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">账号名称</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">平台</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">SecretId</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">状态</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">域名数</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {registrars.map(r => (
                  <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{r.name}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {PROVIDERS.find(p => p.value === r.provider)?.label || r.provider}
                    </td>
                    <td className="px-4 py-3 text-gray-400 font-mono text-xs">
                      {r.secret_id ? `${r.secret_id.slice(0, 8)}…` : '—'}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                    <td className="px-4 py-3 text-gray-600">{r.domain_count ?? 0}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleVerify(r.id)}
                          disabled={verifyingId === r.id}
                          className="px-3 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100 disabled:opacity-50"
                        >
                          {verifyingId === r.id ? '验证中…' : '验证凭证'}
                        </button>
                        <button
                          onClick={() => handleDelete(r.id, r.name)}
                          className="px-3 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Add Modal */}
        {showAdd && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
              <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">添加注册商账号</h2>
                <button onClick={() => setShowAdd(false)}
                  className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
              </div>
              <form onSubmit={handleAdd} className="p-6 space-y-4">
                {formError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">{formError}</div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">账号名称 *</label>
                  <input
                    type="text" required value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none text-gray-900"
                    placeholder="例如：腾讯云主账号"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">平台 *</label>
                  <select
                    value={form.provider}
                    onChange={e => setForm(f => ({ ...f, provider: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none text-gray-900"
                  >
                    {PROVIDERS.map(p => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SecretId *</label>
                  <input
                    type="text" required value={form.secret_id}
                    onChange={e => setForm(f => ({ ...f, secret_id: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none text-gray-900"
                    placeholder="API SecretId"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SecretKey *</label>
                  <input
                    type="password" required value={form.secret_key}
                    onChange={e => setForm(f => ({ ...f, secret_key: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none text-gray-900"
                    placeholder="API SecretKey（加密存储）"
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <button type="button" onClick={() => setShowAdd(false)}
                    className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50">
                    取消
                  </button>
                  <button type="submit" disabled={adding}
                    className="flex-1 py-2.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50">
                    {adding ? '添加中…' : '确认添加'}
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
