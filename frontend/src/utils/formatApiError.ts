export function formatApiError(err: unknown, fallback = 'Something went wrong.'): string {
  if (!err || typeof err !== 'object' || !('response' in err)) {
    return fallback
  }

  const data = (err as { response?: { data?: unknown } }).response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data

  if (typeof data === 'object' && data !== null) {
    const record = data as Record<string, unknown>
    if (typeof record.detail === 'string') return record.detail

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
