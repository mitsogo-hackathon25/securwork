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

export interface Product {
  id: number
  slug: string
  name: string
  short_description: string
  description?: string
  sku: string
  primary_image: string | null
  min_price: string | null
  in_stock: boolean
  is_featured: boolean
  is_new_arrival: boolean
  is_bestseller: boolean
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
  line_total: string
  product_name: string
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
  items: { product_name: string; sku: string; quantity: number; line_total: string }[]
  created_at: string
  paid_at?: string | null
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
