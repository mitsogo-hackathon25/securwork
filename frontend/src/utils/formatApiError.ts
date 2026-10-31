import i18n from '../i18n'

function isAuthFailure(status: number | undefined, detail: string | undefined): boolean {
  if (status !== 401) return false
  if (!detail) return true
  const lower = detail.toLowerCase()
  if (lower.includes('authentication credentials were not provided')) return true
  if (lower.includes('token') || lower.includes('not valid') || lower.includes('expired')) return true
  return false
}

export function formatApiError(err: unknown, fallback = 'Something went wrong.'): string {
  if (!err || typeof err !== 'object' || !('response' in err)) {
    return fallback
  }

  const response = (err as { response?: { status?: number; data?: unknown } }).response
  const status = response?.status
  const data = response?.data

  let detail: string | undefined
  if (typeof data === 'string') {
    if (data.includes('<!DOCTYPE') || data.includes('<html')) return fallback
    detail = data
  } else if (typeof data === 'object' && data !== null) {
    const record = data as Record<string, unknown>
    if (typeof record.detail === 'string') detail = record.detail
    else if (Array.isArray(record.detail)) {
      const parts = record.detail.filter((item): item is string => typeof item === 'string')
      if (parts.length) detail = parts.join(' ')
    }
  }

  if (isAuthFailure(status, detail)) {
    return i18n.t('common.sessionExpired')
  }

  if (!data) return fallback
  if (typeof data === 'string') return data

  if (typeof data === 'object' && data !== null) {
    const record = data as Record<string, unknown>
    if (typeof record.detail === 'string') return record.detail
    if (Array.isArray(record.detail)) {
      const parts = record.detail.filter((item): item is string => typeof item === 'string')
      if (parts.length) return parts.join(' ')
    }

    const messages: string[] = []
    for (const value of Object.values(record)) {
      if (typeof value === 'string') {
        messages.push(value)
      } else if (Array.isArray(value)) {
        value.forEach((item) => {
          if (typeof item === 'string') messages.push(item)
        })
      }
    }
    if (messages.length) return messages.join(' ')
  }

  return fallback
}
