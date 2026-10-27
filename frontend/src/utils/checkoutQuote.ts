import type { CheckoutQuote } from '../api/types'

/** Mirrors backend defaults (orders/services.py + payment_fees.py). */
const VAT_RATE = 0.22
const SHIPPING_FLAT = 5.99
const FREE_SHIPPING_THRESHOLD = 100
const PAYPAL_FEE_PERCENT = 0.034
const PAYPAL_FEE_FIXED = 0.35

function money(value: number): string {
  return value.toFixed(2)
}

function paypalCustomerFee(net: number): number {
  if (net <= 0) return 0
  const gross = (net + PAYPAL_FEE_FIXED) / (1 - PAYPAL_FEE_PERCENT)
  return Math.round((gross - net) * 100) / 100
}

/** Client-side estimate when /checkout/quote/ is unavailable (same rules as backend). */
export function estimateCheckoutQuote(
  subtotal: number,
  paymentMethod: string,
  discountAmount = 0,
  fulfillmentType: 'delivery' | 'pickup' = 'delivery',
): CheckoutQuote {
  const taxable = Math.max(0, subtotal - discountAmount)
  const tax = Math.round(taxable * VAT_RATE * 100) / 100
  const shipping = fulfillmentType === 'pickup'
    ? 0
    : (taxable >= FREE_SHIPPING_THRESHOLD ? 0 : SHIPPING_FLAT)
  const net = Math.round((taxable + tax + shipping) * 100) / 100
  const paymentFee = paymentMethod === 'paypal' ? paypalCustomerFee(net) : 0
  const total = Math.round((net + paymentFee) * 100) / 100
  return {
    subtotal: money(subtotal),
    discount_amount: money(discountAmount),
    shipping_cost: money(shipping),
    tax_amount: money(tax),
    payment_fee: money(paymentFee),
    total: money(total),
    payment_method: paymentMethod,
  }
}
