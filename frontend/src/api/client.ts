import axios, { AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'
import i18n from '../i18n'
import { SESSION_EXPIRED_EVENT, accountUrlWithNext, clearAuthTokens } from '../utils/auth'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

function isJsonRequestBody(data: unknown): boolean {
  if (data === undefined || data === null) return false
  if (typeof FormData !== 'undefined' && data instanceof FormData) return false
  if (typeof Blob !== 'undefined' && data instanceof Blob) return false
  if (data instanceof ArrayBuffer) return false
  return typeof data === 'object' || typeof data === 'string'
}

function applyRequestContentType(config: InternalAxiosRequestConfig) {
  const method = (config.method || 'get').toLowerCase()
  if (method === 'get' || method === 'head' || method === 'delete') return

  const headers = AxiosHeaders.from(config.headers)
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    headers.delete('Content-Type')
    headers.delete('content-type')
    config.headers = headers
    return
  }

  if (!isJsonRequestBody(config.data)) return

  if (!headers.has('Content-Type') && !headers.has('content-type')) {
    headers.set('Content-Type', 'application/json')
  }
  config.headers = headers
}

declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    _retryAuth?: boolean
  }
}

let refreshInFlight: Promise<string | null> | null = null
let sessionExpiryHandled = false

function isAuthRoute(url: string): boolean {
  return (
    url.includes('/auth/login')
    || url.includes('/auth/register')
    || url.includes('/auth/refresh')
    || url.includes('/auth/password-reset/')
  )
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return null
  if (refreshInFlight) return refreshInFlight

  refreshInFlight = (async () => {
    try {
      const { data } = await axios.post<{ access?: string }>(
        '/api/auth/refresh/',
        { refresh },
        { headers: { 'Content-Type': 'application/json' }, withCredentials: true },
      )
      const access = data?.access
      if (access) {
        localStorage.setItem('access_token', access)
        return access
      }
      return null
    } catch {
      return null
    } finally {
      refreshInFlight = null
    }
  })()

  return refreshInFlight
}

function redirectAfterSessionExpired() {
  const path = window.location.pathname + window.location.search
  if (path.startsWith('/admin')) {
    window.location.assign('/admin/login')
    return
  }
  if (!path.startsWith('/account')) {
    window.location.assign(accountUrlWithNext(path, 'login'))
  }
}

function handleSessionExpired() {
  clearAuthTokens()
  if (sessionExpiryHandled) return
  sessionExpiryHandled = true
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT))
  window.setTimeout(() => {
    redirectAfterSessionExpired()
    window.setTimeout(() => {
      sessionExpiryHandled = false
    }, 1000)
  }, 3200)
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (!config.params) config.params = {}
  config.params.lang = i18n.language
  applyRequestContentType(config)
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status
    const config = error.config
    if (!config || status !== 401) {
      return Promise.reject(error)
    }

    const url = String(config.url || '')
    if (isAuthRoute(url)) {
      return Promise.reject(error)
    }

    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      return Promise.reject(error)
    }

    if (!config._retryAuth) {
      config._retryAuth = true
      const access = await refreshAccessToken()
      if (access) {
        config.headers.Authorization = `Bearer ${access}`
        return api(config)
      }
    }

    handleSessionExpired()
    const message = i18n.t('common.sessionExpired')
    if (error.response?.data && typeof error.response.data === 'object') {
      error.response.data = { ...error.response.data, detail: message }
    } else if (error.response) {
      error.response.data = { detail: message }
    }

    return Promise.reject(error)
  },
)

export default api
