'use client'
import { useEffect, useState } from 'react'
import AuthLayout from '@/components/AuthLayout'
import { accountsApi } from '@/lib/api'

interface Account {
  id: string
  name: string
  account_id: string
  status: string
  site_count: string
  last_verified_at?: string
  created_at: string
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ name: '', account_id: '', api_token: '' })
  const [formError, setFormError] = useState('')
  const [adding, setAdding] = useState(false)
  const [verifyingId, setVerifyingId] = useState<string | null>(null)

  const loadAccounts = async () => {
    try {
      const res = await accountsApi.list()
      setAccounts(res.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { loadAccounts() }, [])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setAdding(true)
    try {
      await accountsApi.add(form)
      setShowAdd(false)
      setForm({ name: '', account_id: '', api_token: '' })
      loadAccounts()
    } catch (err: any) {
      setFormError(err.response?.data?.detail || '添加失败，请检查 Token 和 Account ID')
    } finally {
      setAdding(false)
    }
  }

  const handleVerify = async (id: string) => {
    setVerifyingId(id)
    try {
      const res = await accountsApi.verify(id)
      alert(`验证完成：${res.data.is_valid ? '✅ Token 有效' : '❌ Token 无效'} | 站点数：${res.data.site_count}`)
      loadAccounts()
    } catch (err: any) {
      alert('验证请求失败：' + (err.response?.data?.detail || err.message))
    } finally {
      setVerifyingId(null)
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确认删除账号「${name}」？`)) return
    await accountsApi.delete(id)
    loadAccounts()
  }

  return (
    <AuthLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">CF 账号池</h1>
            <p className="text-sm text-gray-500 mt-1">管理 Cloudflare 账号，平台自动负载均衡分配</p>
          </div>
          <button onClick={() => setShowAdd(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
            + 添加账号
          </button>
        </div>

        {/* Stats Banner */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6 flex items-center gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-700">{accounts.length}</div>
            <div className="text-xs text-blue-500">总账号数</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{accounts.filter(a => a.status === 'active').length}</div>
            <div className="text-xs text-gray-500">健康账号</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-700">{accounts.reduce((s, a) => s + parseInt(a.site_count || '0'), 0)}</div>
            <div className="text-xs text-gray-500">总站点数</div>
          </div>
          <div className="ml-auto text-xs text-blue-400">
            💡 负载均衡：新建博客时自动分配站点数最少的健康账号
          </div>
        </div>

        {/* Account List */}
        {loading ? (
          <div className="space-y-3">
            {[1,2].map(i => (
              <div key={i} className="bg-white rounded-xl p-5 animate-pulse">
                <div className="h-5 bg-gray-200 rounded w-1/3 mb-3"></div>
                <div className="h-4 bg-gray-100 rounded w-2/3"></div>
              </div>
            ))}
          </div>
        ) : accounts.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-xl border border-gray-100">
            <div className="text-4xl mb-4">☁️</div>
            <p className="text-gray-500 mb-4">还没有 CF 账号，先添加一个吧</p>
            <button onClick={() => setShowAdd(true)}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">
              添加账号
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {accounts.map(acc => (
              <div key={acc.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-3 h-3 rounded-full ${acc.status === 'active' ? 'bg-green-500' : 'bg-red-400'}`}></div>
                    <div>
                      <div className="font-semibold text-gray-900">{acc.name}</div>
                      <div className="text-sm text-gray-400 font-mono">{acc.account_id}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-center">
                      <div className="text-lg font-bold text-gray-800">{acc.site_count}</div>
                      <div className="text-xs text-gray-400">站点数</div>
                    </div>
                    <div className="text-center">
                      <div className={`text-sm font-medium ${acc.status === 'active' ? 'text-green-600' : 'text-red-500'}`}>
                        {acc.status === 'active' ? '✅ 正常' : '❌ 异常'}
                      </div>
                      <div className="text-xs text-gray-400">
                        {acc.last_verified_at ? new Date(acc.last_verified_at).toLocaleDateString('zh-CN') : '未验证'}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleVerify(acc.id)}
                        disabled={verifyingId === acc.id}
                        className="px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 disabled:opacity-50 transition-colors"
                      >
                        {verifyingId === acc.id ? '验证中...' : '🔍 验证'}
                      </button>
                      <button
                        onClick={() => handleDelete(acc.id, acc.name)}
                        className="px-3 py-1.5 text-xs font-medium text-red-500 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                      >
                        🗑️ 删除
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add Modal */}
        {showAdd && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
              <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">添加 CF 账号</h2>
                <button onClick={() => setShowAdd(false)} className="text-gray-400 hover:text-gray-600">✕</button>
              </div>
              <form onSubmit={handleAdd} className="p-6 space-y-4">
                {formError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">{formError}</div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">账号昵称 *</label>
                  <input type="text" required value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none text-gray-900"
                    placeholder="例如：主账号 / 备用账号01" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Account ID *</label>
                  <input type="text" required value={form.account_id}
                    onChange={e => setForm(f => ({ ...f, account_id: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none font-mono text-gray-900"
                    placeholder="f74a853cac5f8327..." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">API Token *</label>
                  <input type="password" required value={form.api_token}
                    onChange={e => setForm(f => ({ ...f, api_token: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none font-mono text-gray-900"
                    placeholder="cfut_xxxx..." />
                  <p className="text-xs text-gray-400 mt-1">平台会自动验证 Token 有效性后才保存</p>
                </div>
                <div className="flex gap-3 pt-2">
                  <button type="button" onClick={() => setShowAdd(false)}
                    className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50">
                    取消
                  </button>
                  <button type="submit" disabled={adding}
                    className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
                    {adding ? '验证中...' : '✅ 验证并保存'}
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
