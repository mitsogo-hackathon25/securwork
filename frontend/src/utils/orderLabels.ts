const ORDER_STATUS: Record<string, string> = {
  pending: 'In attesa',
  processing: 'In elaborazione',
  shipped: 'Spedito',
  delivered: 'Consegnato',
  cancelled: 'Annullato',
  refunded: 'Rimborsato',
}

const PAYMENT_STATUS: Record<string, string> = {
  pending: 'In attesa',
  paid: 'Pagato',
  failed: 'Fallito',
  refunded: 'Rimborsato',
}

const PAYMENT_METHOD: Record<string, string> = {
  stripe: 'Carta (Stripe)',
  bank_transfer: 'Bonifico bancario',
  manual: 'Manuale',
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
