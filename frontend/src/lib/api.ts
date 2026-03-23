import axios from 'axios'
import Cookies from 'js-cookie'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE !== undefined && process.env.NEXT_PUBLIC_API_BASE !== '') ? process.env.NEXT_PUBLIC_API_BASE : ''

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 30000,
})

// 请求拦截：自动带 token
api.interceptors.request.use((config) => {
  const token = Cookies.get('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：401 自动跳转登录
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      Cookies.remove('access_token')
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default api

// ── Auth ──────────────────────────────────────────────────────
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me'),
}

// ── CF Accounts ───────────────────────────────────────────────
export const accountsApi = {
  list: () => api.get('/accounts'),
  add: (data: { name: string; account_id: string; api_token: string }) =>
    api.post('/accounts', data),
  delete: (id: string) => api.delete(`/accounts/${id}`),
  verify: (id: string) => api.post(`/accounts/${id}/verify`),
  getSites: (id: string) => api.get(`/accounts/${id}/sites`),
}

// ── Blogs ─────────────────────────────────────────────────────
export const blogsApi = {
  list: () => api.get('/blogs'),
  get: (id: string) => api.get(`/blogs/${id}`),
  create: (data: {
    name: string
    custom_domain: string
    cf_account_id: string
    theme: string
    content_markdown?: string
  }) => api.post('/blogs', data),
  delete: (id: string) => api.delete(`/blogs/${id}`),
  getCnameInfo: (id: string) => api.get(`/blogs/${id}/cname-info`),
  bindDomain: (id: string) => api.post(`/blogs/${id}/bind-domain`, { blog_id: id, confirmed: true }),
}

// ── Monitor ───────────────────────────────────────────────────
export const monitorApi = {
  dashboard: () => api.get('/monitor/dashboard'),
  offlineSites: () => api.get('/monitor/offline-sites'),
  triggerCheck: () => api.post('/monitor/trigger-check'),
}

// ── Tasks ─────────────────────────────────────────────────────
export const tasksApi = {
  list: (limit?: number) => api.get('/tasks', { params: { limit } }),
  stats: () => api.get('/tasks/stats'),
}
