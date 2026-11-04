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

export type CsvImportPrepareResult = {
  upload_id: string
  batch_id: string
  total_products: number
  variant_rows: number
  chunk_size: number
  detail: string
  usage_right_stats?: Record<string, number>
}

export type CsvImportChunkResult = {
  upload_id: string
  batch_id: string
  offset: number
  next_offset: number
  done: boolean
  total_products: number
  chunk_created_products: number
  chunk_skipped_products: number
  chunk_created_variants: number
  created_products: number
  created_variants: number
  skipped_products: number
  errors: CsvImportError[]
  can_rollback?: boolean
  import_partial?: boolean
  detail: string
}

function buildCsvImportPostForm(
  uploadId: string,
  filename: string,
  columnFilter?: CsvImportColumnFilter,
  extra?: Record<string, string>,
) {
  const form = new FormData()
  form.append('upload_id', uploadId)
  form.append('filename', filename)
  form.append('skip_existing', '1')
  appendCsvImportFilters(form, columnFilter)
  if (extra) {
    for (const [key, value] of Object.entries(extra)) {
      form.append(key, value)
    }
  }
  return form
}

async function prepareCsvImport(
  uploadId: string,
  file: File,
  columnFilter?: CsvImportColumnFilter,
): Promise<CsvImportPrepareResult> {
  const form = buildCsvImportPostForm(uploadId, file.name, columnFilter)
  return postMultipartJson<CsvImportPrepareResult>('/admin/products/import_csv_prepare/', form)
}

async function prepareTopTexSync(): Promise<CsvImportPrepareResult> {
  const qs = new URLSearchParams({ lang: i18n.language })
  return api
    .post<CsvImportPrepareResult>(
      `/admin/products/toptex_sync_prepare/?${qs.toString()}`,
      {},
      { timeout: 0 },
    )
    .then((r) => r.data)
}

async function importCsvImportChunk(
  uploadId: string,
  batchId: string,
  offset: number,
  chunkSize: number,
  filename: string,
  columnFilter?: CsvImportColumnFilter,
): Promise<CsvImportChunkResult> {
  const form = buildCsvImportPostForm(uploadId, filename, columnFilter, {
    batch_id: batchId,
    offset: String(offset),
    chunk_size: String(chunkSize),
  })
  return postMultipartJson<CsvImportChunkResult>('/admin/products/import_csv_chunk/', form)
}

async function runPreparedImportChunks(
  prepared: CsvImportPrepareResult,
  filename: string,
  onEvent: (event: CsvImportProgressEvent) => void,
  columnFilter?: CsvImportColumnFilter,
): Promise<CsvImportResult> {
  let offset = 0
  const allErrors: CsvImportError[] = []
  let lastChunk: CsvImportChunkResult | null = null

  while (true) {
    onEvent({
      phase: 'importing',
      current: offset,
      total: prepared.total_products,
      message: `Import blocco (${offset + 1}–${Math.min(offset + prepared.chunk_size, prepared.total_products)} di ${prepared.total_products})…`,
      batch_id: prepared.batch_id,
    })

    const chunk = await importCsvImportChunk(
      prepared.upload_id,
      prepared.batch_id,
      offset,
      prepared.chunk_size,
      filename,
      columnFilter,
    )
    lastChunk = chunk
    if (chunk.errors?.length) {
      allErrors.push(...chunk.errors)
    }

    onEvent({
      phase: 'importing',
      current: chunk.next_offset,
      total: chunk.total_products,
      message: chunk.detail,
      batch_id: chunk.batch_id,
    })

    if (chunk.done) break
    offset = chunk.next_offset
  }

  const finalDetail = lastChunk?.detail || prepared.detail
  onEvent({
    phase: 'done',
    current: prepared.total_products,
    total: prepared.total_products,
    message: finalDetail,
    detail: finalDetail,
    batch_id: prepared.batch_id,
    created_products: lastChunk?.created_products ?? 0,
    created_variants: lastChunk?.created_variants ?? 0,
    skipped_products: lastChunk?.skipped_products,
    can_rollback: (lastChunk?.created_products ?? 0) > 0,
    import_partial: allErrors.length > 0,
    errors: allErrors.slice(0, 50),
  })

  return {
    detail: finalDetail,
    errors: allErrors.slice(0, 50),
    created_products: lastChunk?.created_products ?? 0,
    created_variants: lastChunk?.created_variants ?? 0,
    skipped_products: lastChunk?.skipped_products,
    batch_id: prepared.batch_id,
    can_rollback: (lastChunk?.created_products ?? 0) > 0,
    import_partial: allErrors.length > 0,
  }
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

    const failImport = (message: string, partial?: Partial<CsvImportResult>) => {
      if (settled) return
      settled = true
      if (partial?.batch_id && partial.can_rollback) {
        const err = new Error(message) as Error & {
          response?: { data: CsvImportResult & { error_count?: number } }
        }
        err.response = {
          data: {
            detail: message,
            errors: [],
            created_products: partial.created_products ?? 0,
            created_variants: partial.created_variants ?? 0,
            batch_id: partial.batch_id,
            can_rollback: true,
          },
        }
        reject(err)
        return
      }
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
          if (
            event.batch_id
            && (event.phase === 'importing' || event.phase === 'skipped')
            && (event.current ?? 0) > 0
          ) {
            lastCanRollback = true
          }
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
      drainResponse()
      const partialMsg =
        'Connessione interrotta (import_csv_stream). '
        + 'Di solito è Cloudflare (proxy arancione ~100s) o timeout nginx non aggiornato. '
        + 'In Cloudflare: DNS only (nuvola grigia) per www.securwork.it opure importa a blocchi con filtro colonna.'
      if (lastBatchId && lastCanRollback) {
        failImport(
          `${partialMsg} Alcuni prodotti potrebbero essere già stati importati: usa «Annulla questo import» o reimporta (i duplicati vengono saltati).`,
          {
            batch_id: lastBatchId,
            can_rollback: true,
            created_products: 0,
            created_variants: 0,
            detail: partialMsg,
            errors: [],
          },
        )
        return
      }
      failImport(partialMsg)
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
  const filterActive = Boolean(columnFilter?.column && columnFilter.values.length > 0)

  return stageCsvImportFile(file, onUploadProgress).then(async (staged) => {
    onEvent({
      phase: 'uploading',
      current: 100,
      total: 100,
      message: 'File caricato sul server, avvio validazione…',
    })
    onEvent({
      phase: 'validating',
      message: filterActive
        ? 'Validazione CSV (solo prodotti selezionati)…'
        : 'Validazione CSV…',
    })

    const prepared = await prepareCsvImport(staged.upload_id, file, columnFilter)
    onEvent({
      phase: 'validated',
      current: prepared.total_products,
      total: prepared.total_products,
      message: filterActive
        ? `Pronti ${prepared.total_products} prodotti selezionati (${prepared.variant_rows} righe varianti).`
        : prepared.detail,
      batch_id: prepared.batch_id,
    })

    return runPreparedImportChunks(prepared, file.name, onEvent, columnFilter)
  })
}

export function importProductsTopTexWithProgress(
  onEvent: (event: CsvImportProgressEvent) => void,
): Promise<CsvImportResult> {
  onEvent({
    phase: 'validating',
    message: 'TopTex: autenticazione e catalogo (b2b_b2c, b2b_uniquement, b2c_uniquement)…',
  })

  return prepareTopTexSync().then(async (prepared) => {
    onEvent({
      phase: 'validated',
      current: prepared.total_products,
      total: prepared.total_products,
      message: prepared.detail,
      batch_id: prepared.batch_id,
    })
    return runPreparedImportChunks(prepared, 'TopTex API', onEvent)
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
