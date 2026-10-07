export interface Category {
  id: number
  slug: string
  name: string
  description: string
  section: string
  parent: number | null
  image: string | null
  children: Category[]
}

export interface ProductVariant {
  id: number
  sku: string
  size: string
  color: string
  price: string
  sale_price: string | null
  effective_price: string
  stock_quantity: number
  in_stock: boolean
  is_low_stock: boolean
}

export interface CustomizationDesign {
  view: string
  x_pct: number
  y_pct: number
  width_pct: number
  height_pct: number
  rotation: number
}

export interface LineItemCustomization {
  id: number
  logo: string | null
  preview: string | null
  design_data: CustomizationDesign
  created_at?: string
}

export interface Product {
  id: number
  slug: string
  name: string
  short_description: string
  description?: string
  sku: string
  brand?: string
  primary_image: string | null
  min_price: string | null
  in_stock: boolean
  is_featured: boolean
  is_new_arrival: boolean
  is_bestseller: boolean
  allows_customization?: boolean
  mockup_front?: string | null
  customization_fee?: string | null
  images?: { id: number; image: string; alt_text: string; is_primary: boolean }[]
  variants?: ProductVariant[]
  categories?: Category[]
  is_variable?: boolean
  meta_title?: string
  meta_description?: string
}

export interface CartItem {
  id: number
  variant: ProductVariant
  quantity: number
  unit_price?: string
  line_total: string
  product_name: string
  customization?: LineItemCustomization | null
}

export interface Cart {
  id: number
  items: CartItem[]
  total: string
  item_count: number
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Page {
  slug: string
  page_type: string
  title: string
  content: string
  meta_title: string
  meta_description: string
}

export interface FAQ {
  id: number
  question: string
  answer: string
}

export interface OrderItem {
  product_name: string
  sku: string
  size: string
  color: string
  unit_price: string
  quantity: number
  line_total: string
  customization?: LineItemCustomization | null
}

export interface Order {
  order_number: string
  status: string
  payment_method: string
  payment_status: string
  total: string
  subtotal: string
  shipping_cost: string
  tax_amount: string
  discount_amount: string
  items: OrderItem[]
  created_at: string
  paid_at?: string | null
}

export interface AdminOrderListItem {
  id: number
  order_number: string
  email: string
  status: string
  payment_status: string
  payment_method: string
  total: string
  item_count: number
  created_at: string
}

export interface AdminCoupon {
  id?: number
  code: string
  discount_percent: string | null
  discount_amount: string | null
  min_order_amount: string
  max_uses: number | null
  used_count?: number
  uses_remaining?: number | null
  is_active: boolean
  valid_from: string | null
  valid_until: string | null
}

export interface AdminOrder extends Order {
  id: number
  email: string
  phone: string
  language: string
  billing_first_name: string
  billing_last_name: string
  billing_company: string
  billing_address: string
  billing_city: string
  billing_postcode: string
  billing_country: string
  billing_vat: string
  shipping_first_name: string
  shipping_last_name: string
  shipping_address: string
  shipping_city: string
  shipping_postcode: string
  shipping_country: string
  coupon_code: string
  notes: string
  updated_at: string
}

export interface PaymentConfig {
  stripe_enabled: boolean
  stripe_publishable_key: string
  currency: string
  bank_transfer_enabled: boolean
  bank_details: {
    iban: string
    bic: string
    account_name: string
  }
}

export interface CheckoutResponse {
  order: Order
  checkout_url: string | null
  payment_method: string
}

export interface SiteConfig {
  company_name: string
  company_vat: string
  company_address: string
  company_city: string
  company_phone: string
  contact_email: string
  map_lat: string
  map_lng: string
}

export interface AdminCategoryOption {
  id: number
  slug: string
  name: string
  section: string
  parent: number | null
}

export interface AdminCategory {
  id?: number
  slug: string
  section: 'workwear' | 'professional'
  parent_id: number | null
  parent_name?: string | null
  name_it: string
  name_en: string
  description_it?: string
  description_en?: string
  sort_order: number
  is_active: boolean
  product_count?: number
  created_at?: string
}

export interface AdminBrand {
  id?: number
  name: string
  slug?: string
  is_active: boolean
  sort_order: number
  product_count?: number
  created_at?: string
}

export interface AdminColor {
  id?: number
  name: string
  slug?: string
  is_active: boolean
  sort_order: number
  variant_count?: number
  created_at?: string
}

export interface AdminProductVariant {
  id?: number | null
  sku: string
  size: string
  color: string
  price: string
  sale_price: string | null
  stock_quantity: number
  is_active: boolean
  effective_price?: string
  in_stock?: boolean
}

export interface AdminProductImage {
  id: number
  image: string
  alt_text: string
  sort_order: number
  is_primary: boolean
}

export interface AdminProductListItem {
  id: number
  slug: string
  sku: string
  name: string
  primary_image: string | null
  min_price: string | null
  total_stock: number
  in_stock: boolean
  variant_count: number
  is_active: boolean
  is_featured: boolean
  is_new_arrival: boolean
  is_bestseller: boolean
  created_at: string
  updated_at: string
}

export interface AdminProduct {
  id?: number
  slug: string
  sku: string
  brand?: string
  name_it: string
  name_en: string
  short_description_it: string
  short_description_en: string
  description_it: string
  description_en: string
  meta_title_it: string
  meta_title_en: string
  meta_description_it: string
  meta_description_en: string
  category_ids: number[]
  variants: AdminProductVariant[]
  images?: AdminProductImage[]
  is_active: boolean
  is_featured: boolean
  is_new_arrival: boolean
  is_bestseller: boolean
  allows_customization?: boolean
  mockup_front?: string | null
  customization_fee?: string
  min_price?: string | null
  total_stock?: number
  in_stock?: boolean
  created_at?: string
  updated_at?: string
}
