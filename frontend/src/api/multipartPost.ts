import i18n from '../i18n'

type ApiErrorBody = {
  detail?: string
  errors?: unknown[]
}

/**
 * POST multipart/form-data and parse JSON — avoids axios forcing application/json on uploads.
 */
export function postMultipartJson<T>(apiPath: string, form: FormData): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const path = apiPath.startsWith('/') ? apiPath : `/${apiPath}`
    const qs = new URLSearchParams({ lang: i18n.language })
    xhr.open('POST', `/api${path}?${qs.toString()}`)
    xhr.withCredentials = true
    xhr.responseType = 'json'

    const token = localStorage.getItem('access_token')
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }
    xhr.setRequestHeader('Accept', 'application/json')

    xhr.onload = () => {
      const data = xhr.response as T | ApiErrorBody | null
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data as T)
        return
      }
      let detail = `HTTP ${xhr.status}`
      if (data && typeof data === 'object' && typeof (data as ApiErrorBody).detail === 'string') {
        detail = (data as ApiErrorBody).detail as string
      }
      reject(
        Object.assign(new Error(detail), {
          response: { status: xhr.status, data },
        }),
      )
    }

    xhr.onerror = () => reject(new Error('Network error during file upload.'))
    xhr.send(form)
  })
}
