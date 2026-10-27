import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Helmet } from 'react-helmet-async'
import { verifyOrder } from '../api/store'
import type { Order } from '../api/types'
import { formatPrice } from '../utils/format'
import './OrderConfirmationPage.css'

export default function OrderConfirmationPage() {
  const { orderNumber } = useParams<{ orderNumber: string }>()
  const [searchParams] = useSearchParams()
  const { t } = useTranslation()
  const [order, setOrder] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!orderNumber) return
    const sessionId = searchParams.get('session_id') || undefined
    const paypalToken = searchParams.get('token') || undefined
    verifyOrder(orderNumber, { sessionId, paypalToken })
      .then(setOrder)
      .catch(() => setOrder(null))
      .finally(() => setLoading(false))
  }, [orderNumber, searchParams])

  if (loading) {
    return <div className="container section"><p>{t('common.loading')}</p></div>
  }

  if (!order) {
    return (
      <div className="container section">
        <p>{t('common.error')}</p>
        <Link to="/shop" className="btn btn-primary">{t('cta.continueShopping')}</Link>
      </div>
    )
  }

  const isPaid = order.payment_status === 'paid'
  const isBankPending = order.payment_method === 'bank_transfer' && !isPaid

  return (
    <>
      <Helmet><title>{t('checkout.success', { orderNumber: order.order_number })}</title></Helmet>

      <div className="container order-confirmation">
        <div className="confirmation-card">
          <div className="confirmation-icon" aria-hidden="true">✓</div>
          <h1>{t('checkout.confirmationTitle')}</h1>
          <p className="order-number">{order.order_number}</p>

          {isPaid ? (
            <p className="confirmation-message">{t('checkout.paidMessage')}</p>
          ) : isBankPending ? (
            <p className="confirmation-message">{t('checkout.bankPendingMessage')}</p>
          ) : (
            <p className="confirmation-message">{t('checkout.pendingMessage')}</p>
          )}

          <div className="confirmation-summary">
            <div className="summary-row">
              <span>{t('cart.subtotal')}</span>
              <span>{formatPrice(order.subtotal)}</span>
            </div>
            {order.fulfillment_type === 'pickup' && order.pickup_location_name && (
              <div className="summary-row">
                <span>{t('checkout.fulfillmentPickup')}</span>
                <span>{order.pickup_location_name}</span>
              </div>
            )}
            {order.fulfillment_type !== 'pickup' && parseFloat(order.shipping_cost) > 0 && (
              <div className="summary-row">
                <span>{t('checkout.shipping')}</span>
                <span>{formatPrice(order.shipping_cost)}</span>
              </div>
            )}
            {order.fulfillment_type === 'pickup' && (
              <div className="summary-row">
                <span>{t('checkout.pickupLine')}</span>
                <span>{t('checkout.shippingFree')}</span>
              </div>
            )}
            {parseFloat(order.tax_amount) > 0 && (
              <div className="summary-row">
                <span>{t('checkout.vat')}</span>
                <span>{formatPrice(order.tax_amount)}</span>
              </div>
            )}
            {order.payment_fee && parseFloat(order.payment_fee) > 0 && (
              <div className="summary-row">
                <span>{t('checkout.paypalFee')}</span>
                <span>{formatPrice(order.payment_fee)}</span>
              </div>
            )}
            <div className="summary-row total">
              <span>{t('checkout.totalPayable')}</span>
              <span>{formatPrice(order.total)}</span>
            </div>
          </div>

          <p className="confirmation-email">
            {t('checkout.emailSent', { email: order.email })}
          </p>

          <Link to="/shop" className="btn btn-primary">{t('cta.continueShopping')}</Link>
        </div>
      </div>
    </>
  )
}
