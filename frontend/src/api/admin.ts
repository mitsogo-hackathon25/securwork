import api from './client'
import { buildCsvUploadForm } from './csvUpload'
import i18n from '../i18n'
import { postMultipartJson } from './multipartPost'
import { readBlobApiDetail } from '../utils/formatApiError'
import { sortByName } from '../utils/sortCategories'
import type {
  AdminBrand,
  AdminColor,
  AdminCategory,
  AdminCategoryOption,
  AdminCoupon,
  AdminMonthlySales,
  AdminOrder,
  AdminOrderListItem,
  AdminPickupLocation,
  AdminUserDetail,
  AdminUserListItem,
  AdminProduct,
  AdminProductListItem,
  PaginatedResponse,
} from './types'

export const fetchMe = () =>
  api.get<{ id: number; username: string; is_staff: boolean }>('/auth/me/').then((r) => r.data)

export const adminLogin = (username: string, password: string) =>
  api.post('/auth/login/', { username, password }).then((r) => r.data)

export const fetchAdminProducts = (params?: Record<string, string | number | boolean>) =>
  api.get<PaginatedResponse<AdminProductListItem>>('/admin/products/', { params }).then((r) => r.data)

export const fetchAdminProduct = (id: number) =>
  api.get<AdminProduct>(`/admin/products/${id}/`).then((r) => r.data)

export const createAdminProduct = (data: Partial<AdminProduct>) =>
  api.post<AdminProduct>('/admin/products/', data).then((r) => r.data)

export const updateAdminProduct = (id: number, data: Partial<AdminProduct>) =>
  api.patch<AdminProduct>(`/admin/products/${id}/`, data).then((r) => r.data)

export const deleteAdminProduct = (id: number) =>
  api.delete(`/admin/products/${id}/`)

export type BulkDeleteBlockedProduct = {
  id: number
  name: string
  detail: string
  code: string
}

export type BulkDeleteResult = {
  detail: string
  deleted: number[]
  blocked: BulkDeleteBlockedProduct[]
  not_found: number[]
}

export const bulkDeleteAdminProducts = (ids: number[]) =>
  api.post<BulkDeleteResult>('/admin/products/bulk_delete/', { ids }).then((r) => r.data)

export const deleteAllAdminProducts = () =>
  api
    .post<BulkDeleteResult>('/admin/products/delete_all/', { confirm: 'Stilpromo@2026' })
    .then((r) => r.data)

export type CsvImportError = {
  row: number
  field: string
  message: string
}

export type CsvImportResult = {
  detail: string
  errors: CsvImportError[]
  created_products: number
  created_variants: number
  skipped_products?: number
  batch_id?: string
  can_rollback?: boolean
  import_partial?: boolean
}

const downloadCsvBlob = async (blob: Blob, filename: string) => {
  if (blob.size === 0) {
    throw new Error('The CSV file is empty.')
  }

  const fullText = await blob.text()
  const trimmed = fullText.trimStart().replace(/^\ufeff/, '')

  if (trimmed.startsWith('{') || trimmed.startsWith('<!DOCTYPE') || trimmed.startsWith('<html')) {
    try {
      const payload = JSON.parse(trimmed) as { detail?: string }
      throw new Error(payload.detail || 'CSV download failed. Sign in to admin and try again.')
    } catch (err) {
      if (err instanceof Error && !err.message.includes('JSON')) {
        throw err
      }
      throw new Error('CSV download failed. Sign in to admin and try again.')
    }
  }

  const lines = trimmed.split(/\r?\n/).filter((line) => line.trim().length > 0)
  if (lines.length < 2) {
    throw new Error(
      'Export contains no product rows (header only). Add products with variants, then export again.',
    )
  }

  const outBlob = new Blob([fullText], { type: 'text/csv;charset=utf-8' })
  const url = window.URL.createObjectURL(outBlob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}

export const downloadProductCsvTemplate = () =>
  api
    .get('/admin/products/csv_template/', { responseType: 'blob' })
    .then((r) => downloadCsvBlob(r.data, 'securwork-products-template.csv'))

export const exportProductsCsv = () =>
  api
    .get('/admin/products/export_csv/', {
      responseType: 'blob',
      validateStatus: () => true,
    })
    .then(async (r) => {
      if (r.status !== 200) {
        const detail = await readBlobApiDetail(
          r.data as Blob,
          `CSV export failed (HTTP ${r.status}).`,
        )
        throw new Error(detail)
      }
      await downloadCsvBlob(r.data, 'securwork-products-export.csv')
    })

export const restoreDemoCatalog = () =>
  api
    .post<{ detail: string; product_count: number; variant_count: number }>(
      '/admin/products/restore_demo_catalog/',
    )
    .then((r) => r.data)

export const importProductsCsv = async (file: File) => {
  const form = await buildCsvUploadForm(file)
  return postMultipartJson<CsvImportResult>('/admin/products/import_csv/', form)
}

export type CsvImportProgressEvent = {
  phase: 'uploading' | 'validating' | 'validated' | 'importing' | 'skipped' | 'done' | 'failed'
  current?: number
  total?: number
  message?: string
  product_sku?: string
  detail?: string
  errors?: CsvImportError[]
  error_count?: number
  created_products?: number
  created_variants?: number
  skipped_products?: number
  batch_id?: string
  can_rollback?: boolean
  import_partial?: boolean
}

export type CsvImportBrandOption = {
  key: string
  name: string
  product_count: number
  row_count: number
}

export type CsvImportColumnOption = {
  key: string
  label: string
}

export type CsvImportValueOption = CsvImportBrandOption

export type CsvImportColumnFilter = {
  column: string
  values: string[]
}

export const fetchCsvImportBrands = async (file: File) => {
  const form = await buildCsvUploadForm(file)
  return postMultipartJson<{ brands: CsvImportBrandOption[] }>(
    '/admin/products/import_csv_brands/',
    form,
  )
}

export const fetchCsvImportColumns = async (file: File) => {
  const form = await buildCsvUploadForm(file)
  return postMultipartJson<{ columns: CsvImportColumnOption[] }>(
    '/admin/products/import_csv_columns/',
    form,
  )
}

export const fetchCsvImportColumnValues = async (file: File, column: string) => {
  const form = await buildCsvUploadForm(file, { column })
  return postMultipartJson<{ column: string; values: CsvImportValueOption[] }>(
    '/admin/products/import_csv_column_values/',
    form,
  )
}

function appendCsvImportFilters(form: FormData, columnFilter?: CsvImportColumnFilter) {
  if (columnFilter?.column && columnFilter.values.length > 0) {
    form.append('filter_column', columnFilter.column)
    form.append('filter_values', JSON.stringify(columnFilter.values))
  }
}

function applyCsvImportStreamXhr(
  form: FormData,
  onEvent: (event: CsvImportProgressEvent) => void,
): Promise<CsvImportResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const qs = new URLSearchParams({ lang: i18n.language })
    xhr.open('POST', `/api/admin/products/import_csv_stream/?${qs.toString()}`)
    xhr.withCredentials = true
    xhr.timeout = 0

    const token = localStorage.getItem('access_token')
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }
    xhr.setRequestHeader('Accept', 'application/json')

    let lastParsedIndex = 0
    let buffer = ''
    let settled = false
    let lastBatchId: string | undefined
    let lastCanRollback = false

    const failImport = (message: string) => {
      if (settled) return
      settled = true
      reject(new Error(message))
    }

    const consumeBuffer = () => {
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue
        try {
          const event = JSON.parse(trimmed) as CsvImportProgressEvent
          if (event.batch_id) lastBatchId = event.batch_id
          if (event.can_rollback) lastCanRollback = true
          onEvent(event)
          if (event.phase === 'done' && !settled) {
            settled = true
            resolve({
              detail: event.detail || 'Import completato.',
              errors: event.errors || [],
              created_products: event.created_products ?? 0,
              created_variants: event.created_variants ?? 0,
              skipped_products: event.skipped_products,
              batch_id: event.batch_id ?? lastBatchId,
              can_rollback: event.can_rollback ?? lastCanRollback,
              import_partial: event.import_partial,
            })
          } else if (event.phase === 'failed' && !settled) {
            settled = true
            const err = new Error(event.detail || 'Import non riuscito.') as Error & {
              response?: { data: CsvImportResult & { error_count?: number } }
            }
            err.response = {
              data: {
                detail: event.detail || 'Import non riuscito.',
                errors: event.errors || [],
                created_products: event.created_products ?? 0,
                created_variants: event.created_variants ?? 0,
                error_count: event.error_count,
                batch_id: event.batch_id ?? lastBatchId,
                can_rollback: event.can_rollback ?? lastCanRollback,
              },
            }
            reject(err)
          }
        } catch {
          /* partial chunk */
        }
      }
    }

    const drainResponse = () => {
      const chunk = xhr.responseText.slice(lastParsedIndex)
      if (!chunk) return
      lastParsedIndex = xhr.responseText.length
      buffer += chunk
      consumeBuffer()
    }

    xhr.onreadystatechange = () => {
      if (xhr.readyState >= 3) drainResponse()
    }
    xhr.onprogress = () => drainResponse()

    const pollId = window.setInterval(() => {
      if (xhr.readyState >= 4) {
        window.clearInterval(pollId)
        return
      }
      if (xhr.readyState >= 3) drainResponse()
    }, 400)
    const stopPoll = () => window.clearInterval(pollId)

    xhr.onload = () => {
      stopPoll()
      drainResponse()
      if (settled) return
      if (xhr.status === 0) {
        failImport(
          'Connessione interrotta durante l\'import. '
          + 'Se usi Cloudflare (proxy arancione), il limite è ~100 secondi: passa l\'API in DNS only '
          + 'oppure aumenta timeout nginx/gunicorn (600s). Prova anche un filtro colonna.',
        )
        return
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        failImport('Import terminato senza conferma dal server.')
        return
      }
      let detail = xhr.responseText || `HTTP ${xhr.status}`
      if (xhr.status === 524) {
        detail = 'Timeout Cloudflare (524). Disattiva il proxy per www.securwork.it o importa a batch con filtro colonna.'
      }
      try {
        const parsed = JSON.parse(xhr.responseText) as { detail?: string }
        if (parsed.detail) detail = parsed.detail
      } catch {
        /* plain text */
      }
      failImport(detail)
    }

    xhr.onerror = () => {
      stopPoll()
      failImport(
        'Connessione interrotta (import_csv_stream). '
        + 'Il file viene caricato in un passo separato; se fallisce qui, di solito è timeout proxy durante validazione/import. '
        + 'Controlla DevTools → Network (524 o failed).',
      )
    }
    xhr.ontimeout = () => {
      stopPoll()
      failImport('Timeout durante l\'import CSV.')
    }
    xhr.onabort = () => {
      stopPoll()
      failImport('Import CSV annullato.')
    }
    xhr.send(form)
  })
}

function stageCsvImportFile(
  file: File,
  onUploadProgress?: (percent: number) => void,
): Promise<{ upload_id: string; estimated_rows: number }> {
  return buildCsvUploadForm(file).then(
    (form) =>
      new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        const qs = new URLSearchParams({ lang: i18n.language })
        xhr.open('POST', `/api/admin/products/import_csv_stage/?${qs.toString()}`)
        xhr.withCredentials = true
        xhr.responseType = 'json'
        xhr.timeout = 0

        const token = localStorage.getItem('access_token')
        if (token) {
          xhr.setRequestHeader('Authorization', `Bearer ${token}`)
        }

        xhr.upload.onprogress = (e) => {
          if (!onUploadProgress || !e.lengthComputable) return
          onUploadProgress(Math.min(100, Math.round((e.loaded / e.total) * 100)))
        }

        xhr.onload = () => {
          if (xhr.status === 413) {
            reject(new Error('File troppo grande (HTTP 413). Imposta nginx client_max_body_size 256M.'))
            return
          }
          if (xhr.status >= 200 && xhr.status < 300) {
            const data = xhr.response as { upload_id?: string; estimated_rows?: number }
            if (data?.upload_id) {
              resolve({
                upload_id: data.upload_id,
                estimated_rows: data.estimated_rows ?? 0,
              })
              return
            }
          }
          let detail = `HTTP ${xhr.status}`
          try {
            const parsed = xhr.response as { detail?: string }
            if (parsed?.detail) detail = parsed.detail
          } catch {
            /* ignore */
          }
          reject(new Error(detail || 'Caricamento CSV fallito.'))
        }

        xhr.onerror = () => {
          reject(
            new Error(
              'Caricamento CSV fallito (rete). Controlla import_csv_stage in DevTools (413, failed).',
            ),
          )
        }
        xhr.send(form)
      }),
  )
}

export function importProductsCsvWithProgress(
  file: File,
  onEvent: (event: CsvImportProgressEvent) => void,
  onUploadProgress?: (percent: number) => void,
  columnFilter?: CsvImportColumnFilter,
): Promise<CsvImportResult> {
  return stageCsvImportFile(file, onUploadProgress).then((staged) => {
    onEvent({
      phase: 'uploading',
      current: 100,
      total: 100,
      message: 'File caricato sul server, avvio validazione…',
    })
    const form = new FormData()
    form.append('upload_id', staged.upload_id)
    form.append('filename', file.name)
    form.append('skip_existing', '1')
    appendCsvImportFilters(form, columnFilter)
    return applyCsvImportStreamXhr(form, onEvent)
  })
}

export const rollbackCsvImportBatch = (batchId: string) =>
  api
    .post<BulkDeleteResult & { batch_id: string }>(
      '/admin/products/rollback_import_batch/',
      { batch_id: batchId },
    )
    .then((r) => r.data)

export type PriceAdjustResult = {
  detail: string
  updated_variants: number
  percent: string
  brand: string
}

export const adjustProductPricesByBrand = (payload: { percent: number; brand: string }) =>
  api
    .post<PriceAdjustResult>('/admin/products/adjust_prices/', payload)
    .then((r) => r.data)

export type AdminGlobalSettings = {
  order_notification_emails: string
  updated_at: string
}

export const fetchAdminGlobalSettings = () =>
  api.get<AdminGlobalSettings>('/admin/global-settings/').then((r) => r.data)

export const updateAdminGlobalSettings = (data: Pick<AdminGlobalSettings, 'order_notification_emails'>) =>
  api.patch<AdminGlobalSettings>('/admin/global-settings/', data).then((r) => r.data)

export const fetchAdminCategories = () =>
  api.get<AdminCategoryOption[]>('/admin/categories/', { params: { options: 'true' } })
    .then((r) => sortByName(r.data, 'it'))

export const fetchAdminCategoryList = () =>
  api.get<AdminCategory[]>('/admin/categories/').then((r) =>
    [...r.data].sort((a, b) =>
      (a.name_it || a.slug).localeCompare(b.name_it || b.slug, 'it', { sensitivity: 'base' }),
    ),
  )

export const createAdminCategory = (data: Partial<AdminCategory>) =>
  api.post<AdminCategory>('/admin/categories/', data).then((r) => r.data)

export const updateAdminCategory = (id: number, data: Partial<AdminCategory>) =>
  api.patch<AdminCategory>(`/admin/categories/${id}/`, data).then((r) => r.data)

export const deleteAdminCategory = (id: number) =>
  api.delete(`/admin/categories/${id}/`)

export const fetchAdminBrands = () =>
  api.get<AdminBrand[]>('/admin/brands/').then((r) => r.data)

export const createAdminBrand = (data: Partial<AdminBrand>) =>
  api.post<AdminBrand>('/admin/brands/', data).then((r) => r.data)

export const updateAdminBrand = (id: number, data: Partial<AdminBrand>) =>
  api.patch<AdminBrand>(`/admin/brands/${id}/`, data).then((r) => r.data)

export const deleteAdminBrand = (id: number) =>
  api.delete(`/admin/brands/${id}/`)

export const fetchAdminColors = () =>
  api.get<AdminColor[]>('/admin/colors/').then((r) => r.data)

export const createAdminColor = (data: Partial<AdminColor>) =>
  api.post<AdminColor>('/admin/colors/', data).then((r) => r.data)

export const updateAdminColor = (id: number, data: Partial<AdminColor>) =>
  api.patch<AdminColor>(`/admin/colors/${id}/`, data).then((r) => r.data)

export const deleteAdminColor = (id: number) =>
  api.delete(`/admin/colors/${id}/`)

export const uploadProductImage = (productId: number, file: File, isPrimary = false) => {
  const form = new FormData()
  form.append('image', file)
  form.append('is_primary', String(isPrimary))
  return api.post(`/admin/products/${productId}/upload_image/`, form).then((r) => r.data)
}

export const addProductImageUrl = (productId: number, imageUrl: string, isPrimary = false) =>
  api.post(`/admin/products/${productId}/add_image_url/`, {
    image_url: imageUrl,
    is_primary: isPrimary,
  }).then((r) => r.data)

export const deleteProductImage = (productId: number, imageId: number) =>
  api.delete(`/admin/products/${productId}/images/${imageId}/`)

export const setPrimaryImage = (productId: number, imageId: number) =>
  api.patch(`/admin/products/${productId}/images/${imageId}/`, { is_primary: true })

export const uploadProductMockup = (productId: number, file: File) => {
  const form = new FormData()
  form.append('mockup_front', file)
  return api.post<AdminProduct>(`/admin/products/${productId}/upload_mockup/`, form).then((r) => r.data)
}

export const removeProductMockup = (productId: number) =>
  api.delete(`/admin/products/${productId}/remove_mockup/`)

export const fetchAdminUsers = (params?: Record<string, string | number | boolean>) =>
  api.get<PaginatedResponse<AdminUserListItem>>('/admin/users/', { params }).then((r) => r.data)

export const fetchAdminUser = (id: number) =>
  api.get<AdminUserDetail>(`/admin/users/${id}/`).then((r) => r.data)

export const fetchAdminOrders = (params?: Record<string, string | number | boolean>) =>
  api.get<PaginatedResponse<AdminOrderListItem>>('/admin/orders/', { params }).then((r) => r.data)

export const fetchAdminMonthlySales = (year: number) =>
  api.get<AdminMonthlySales>('/admin/orders/monthly-sales/', { params: { year } }).then((r) => r.data)

export const fetchAdminOrder = (id: number) =>
  api.get<AdminOrder>(`/admin/orders/${id}/`).then((r) => r.data)

export const updateAdminOrder = (id: number, data: Partial<Pick<AdminOrder, 'status' | 'payment_status' | 'notes'>>) =>
  api.patch<AdminOrder>(`/admin/orders/${id}/`, data).then((r) => r.data)

export const fetchAdminCoupons = (params?: Record<string, string | number | boolean>) =>
  api.get<PaginatedResponse<AdminCoupon>>('/admin/coupons/', { params }).then((r) => r.data)

export const fetchAdminCoupon = (id: number) =>
  api.get<AdminCoupon>(`/admin/coupons/${id}/`).then((r) => r.data)

export const createAdminCoupon = (data: Partial<AdminCoupon>) =>
  api.post<AdminCoupon>('/admin/coupons/', data).then((r) => r.data)

export const updateAdminCoupon = (id: number, data: Partial<AdminCoupon>) =>
  api.patch<AdminCoupon>(`/admin/coupons/${id}/`, data).then((r) => r.data)

export const deleteAdminCoupon = (id: number) =>
  api.delete(`/admin/coupons/${id}/`)

export const fetchAdminPickupLocations = (params?: Record<string, string | number | boolean>) =>
  api.get<PaginatedResponse<AdminPickupLocation>>('/admin/pickup-locations/', { params }).then((r) => r.data)

export const fetchAdminPickupLocation = (id: number) =>
  api.get<AdminPickupLocation>(`/admin/pickup-locations/${id}/`).then((r) => r.data)

export const createAdminPickupLocation = (data: Partial<AdminPickupLocation>) =>
  api.post<AdminPickupLocation>('/admin/pickup-locations/', data).then((r) => r.data)

export const updateAdminPickupLocation = (id: number, data: Partial<AdminPickupLocation>) =>
  api.patch<AdminPickupLocation>(`/admin/pickup-locations/${id}/`, data).then((r) => r.data)

export const deleteAdminPickupLocation = (id: number) =>
  api.delete(`/admin/pickup-locations/${id}/`)
