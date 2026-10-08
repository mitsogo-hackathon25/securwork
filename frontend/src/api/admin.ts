import api from './client'
import type {
  AdminBrand,
  AdminColor,
  AdminCategory,
  AdminCategoryOption,
  AdminCoupon,
  AdminOrder,
  AdminOrderListItem,
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
}

const downloadCsvBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob)
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
    .get('/admin/products/export_csv/', { responseType: 'blob' })
    .then((r) => downloadCsvBlob(r.data, 'securwork-products-export.csv'))

export const importProductsCsv = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api
    .post<CsvImportResult>('/admin/products/import_csv/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

export const fetchAdminCategories = () =>
  api.get<AdminCategoryOption[]>('/admin/categories/', { params: { options: 'true' } }).then((r) => r.data)

export const fetchAdminCategoryList = () =>
  api.get<AdminCategory[]>('/admin/categories/').then((r) => r.data)

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
  return api.post(`/admin/products/${productId}/upload_image/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const deleteProductImage = (productId: number, imageId: number) =>
  api.delete(`/admin/products/${productId}/images/${imageId}/`)

export const setPrimaryImage = (productId: number, imageId: number) =>
  api.patch(`/admin/products/${productId}/images/${imageId}/`, { is_primary: true })

export const uploadProductMockup = (productId: number, file: File) => {
  const form = new FormData()
  form.append('mockup_front', file)
  return api.post<AdminProduct>(`/admin/products/${productId}/upload_mockup/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const removeProductMockup = (productId: number) =>
  api.delete(`/admin/products/${productId}/remove_mockup/`)

export const fetchAdminOrders = (params?: Record<string, string | number | boolean>) =>
  api.get<PaginatedResponse<AdminOrderListItem>>('/admin/orders/', { params }).then((r) => r.data)

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
