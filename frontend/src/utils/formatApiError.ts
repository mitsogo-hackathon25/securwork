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
    if (!detail && Array.isArray(record.errors)) {
      const first = record.errors[0]
      if (first && typeof first === 'object' && first !== null && 'message' in first) {
        const msg = (first as { message?: unknown }).message
        if (typeof msg === 'string') detail = msg
      }
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

/** Prefer axios JSON `detail` / `errors`, then thrown Error.message (export helpers). */
export function formatClientError(err: unknown, fallback: string): string {
  const fromApi = formatApiError(err, fallback)
  if (fromApi !== fallback) return fromApi
  if (err instanceof Error && err.message.trim()) {
    const msg = err.message.trim()
    if (!/^Request failed with status code \d+$/.test(msg)) {
      return msg
    }
  }
  return fallback
}

export async function readBlobApiDetail(blob: Blob, fallback: string): Promise<string> {
  try {
    const text = await blob.text()
    const payload = JSON.parse(text) as { detail?: string }
    if (typeof payload.detail === 'string' && payload.detail.trim()) {
      return payload.detail.trim()
    }
  } catch {
    /* not JSON */
  }
  return fallback
}
