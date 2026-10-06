const ORDER_STATUS: Record<string, string> = {
  pending: 'Pending',
  processing: 'Processing',
  shipped: 'Shipped',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
  refunded: 'Refunded',
}

const PAYMENT_STATUS: Record<string, string> = {
  pending: 'Pending',
  paid: 'Paid',
  failed: 'Failed',
  refunded: 'Refunded',
}

const PAYMENT_METHOD: Record<string, string> = {
  stripe: 'Card (Stripe)',
  bank_transfer: 'Bank transfer',
  manual: 'Manual',
}

export function formatOrderStatus(value: string): string {
  return ORDER_STATUS[value] ?? PAYMENT_STATUS[value] ?? value
}

export function formatPaymentMethod(value: string): string {
  return PAYMENT_METHOD[value] ?? value
}

export function orderStatusBadgeClass(status: string): string {
  switch (status) {
    case 'processing':
    case 'shipped':
      return 'admin-badge-info'
    case 'delivered':
    case 'paid':
      return 'admin-badge-success'
    case 'cancelled':
    case 'failed':
      return 'admin-badge-danger'
    case 'refunded':
      return 'admin-badge-warning'
    default:
      return 'admin-badge-muted'
  }
}

export function paymentStatusBadgeClass(status: string): string {
  return orderStatusBadgeClass(status)
}
