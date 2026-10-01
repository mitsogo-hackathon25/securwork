import api from './client'
import type { AdminCategoryOption, AdminProduct, AdminProductListItem, PaginatedResponse } from './types'

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

export const fetchAdminCategories = () =>
  api.get<AdminCategoryOption[]>('/admin/categories/').then((r) => r.data)

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
