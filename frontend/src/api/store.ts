import api from './client'
import type {
  Cart, Category, CheckoutResponse, CustomizationDesign, FAQ, LineItemCustomization,
  Order, Page, PaginatedResponse, PaymentConfig, Product, SiteConfig,
} from './types'
import { sortCategoryTree } from '../utils/sortCategories'

export const fetchCategories = (lang?: string) => {
  const stored = lang
    ?? (typeof localStorage !== 'undefined' ? localStorage.getItem('securwork_lang') : null)
    ?? 'it'
  const locale = stored.startsWith('en') ? 'en' : 'it'
  return api
    .get<PaginatedResponse<Category> | Category[]>('/categories/', { params: { lang: locale } })
    .then((r) => {
      const data = r.data
      const list = Array.isArray(data) ? data : data.results
      return sortCategoryTree(list, locale)
    })
}

export const fetchProducts = (params?: Record<string, string | number | boolean>) =>
  api.get<PaginatedResponse<Product>>('/products/', { params }).then((r) => r.data)

export const fetchProductBrands = (params?: Record<string, string>) =>
  api.get<string[]>('/products/brands/', { params }).then((r) => r.data)

export const fetchProductColors = (params?: Record<string, string>) =>
  api.get<string[]>('/products/colors/', { params }).then((r) => r.data)

export const fetchProduct = (slug: string) =>
  api.get<Product>(`/products/${slug}/`).then((r) => r.data)

export const fetchFeatured = () =>
  api.get<Product[]>('/products/featured/').then((r) => r.data)

export const fetchNewArrivals = () =>
  api.get<Product[]>('/products/new_arrivals/').then((r) => r.data)

export const fetchBestsellers = () =>
  api.get<Product[]>('/products/bestsellers/').then((r) => r.data)

export const fetchRelated = (slug: string) =>
  api.get<Product[]>(`/products/${slug}/related/`).then((r) => r.data)

export const fetchCart = () =>
  api.get<Cart>('/cart/').then((r) => r.data)

export const addToCart = (variantId: number, quantity = 1, customizationId?: number) =>
  api.post<Cart>('/cart/', {
    variant_id: variantId,
    quantity,
    ...(customizationId ? { customization_id: customizationId } : {}),
  }).then((r) => r.data)

export const uploadCustomization = (payload: {
  variantId: number
  logo: File
  preview: File
  designData: CustomizationDesign
  method: string
}) => {
  const form = new FormData()
  form.append('variant_id', String(payload.variantId))
  form.append('logo', payload.logo)
  form.append('preview', payload.preview)
  form.append('method', payload.method)
  form.append('design_data', JSON.stringify(payload.designData))
  return api.post<LineItemCustomization>('/customizations/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const updateCartItem = (itemId: number, quantity: number) =>
  api.patch<Cart>(`/cart/items/${itemId}/`, { quantity }).then((r) => r.data)

export const removeCartItem = (itemId: number) =>
  api.delete<Cart>(`/cart/items/${itemId}/`).then((r) => r.data)

export const fetchPaymentConfig = () =>
  api.get<PaymentConfig>('/payments/config/').then((r) => r.data)

export const checkout = (data: Record<string, unknown>) =>
  api.post<CheckoutResponse>('/checkout/', data).then((r) => r.data)

export const verifyOrder = (
  orderNumber: string,
  options?: { sessionId?: string; paypalToken?: string },
) =>
  api.get<Order>(`/orders/${orderNumber}/verify/`, {
    params: {
      ...(options?.sessionId ? { session_id: options.sessionId } : {}),
      ...(options?.paypalToken ? { token: options.paypalToken } : {}),
    },
  }).then((r) => r.data)

export const fetchSiteConfig = () =>
  api.get<SiteConfig>('/site-config/').then((r) => r.data)

export const fetchPage = (pageType: string) =>
  api.get<Page>(`/pages/${pageType}/`).then((r) => r.data)

export const fetchFAQ = () =>
  api.get<FAQ[]>('/faq/').then((r) => r.data)

export const sendContact = (data: Record<string, string>) =>
  api.post('/contact/', data).then((r) => r.data)

export const login = (email: string, password: string) =>
  api.post('/auth/login/', { email, password }).then((r) => r.data)

export const register = (data: Record<string, string>) =>
  api.post('/auth/register/', data).then((r) => r.data)

export const requestPasswordReset = (email: string) =>
  api.post<{ detail: string }>('/auth/password-reset/request/', { email }).then((r) => r.data)

export const confirmPasswordReset = (data: {
  email: string
  otp: string
  password: string
  password_confirm: string
}) =>
  api.post<{ detail: string }>('/auth/password-reset/confirm/', data).then((r) => r.data)

export const fetchOrders = () =>
  api.get<Order[]>('/orders/').then((r) => r.data)
