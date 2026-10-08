const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

export function isLoggedIn(): boolean {
  return !!localStorage.getItem(ACCESS_KEY)
}

export function setAuthTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearAuthTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export function accountUrlWithNext(nextPath: string, mode: 'login' | 'register' = 'login'): string {
  const params = new URLSearchParams({ next: nextPath, mode })
  return `/account?${params.toString()}`
}
