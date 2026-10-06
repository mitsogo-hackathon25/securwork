import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchAdminOrder, updateAdminOrder } from '../../api/admin'
import { formatPrice } from '../../utils/format'
import { formatOrderStatus, formatPaymentMethod, orderStatusBadgeClass, paymentStatusBadgeClass } from '../../utils/orderLabels'
import './Admin.css'

export default function AdminOrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const orderId = Number(id)
  const queryClient = useQueryClient()

  const { data: order, isLoading, error } = useQuery({
    queryKey: ['admin-order', orderId],
    queryFn: () => fetchAdminOrder(orderId),
    enabled: Number.isFinite(orderId),
  })

  const [status, setStatus] = useState('')
  const [paymentStatus, setPaymentStatus] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    if (!order) return
    setStatus(order.status)
    setPaymentStatus(order.payment_status)
    setNotes(order.notes || '')
  }, [order])

  const saveMutation = useMutation({
    mutationFn: () => updateAdminOrder(orderId, { status, payment_status: paymentStatus, notes }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['admin-order', orderId], updated)
      queryClient.invalidateQueries({ queryKey: ['admin-orders'] })
    },
  })

  const formatDate = (value: string | null | undefined) => {
    if (!value) return '—'
    return new Date(value).toLocaleString('it-IT', { dateStyle: 'medium', timeStyle: 'short' })
  }

  if (isLoading) return <p>Loading order…</p>
  if (error || !order) {
    return (
      <div className="admin-page">
        <p className="admin-alert admin-alert-error">Order not found.</p>
        <Link to="/admin/orders" className="admin-back">← Back to orders</Link>
      </div>
    )
  }

  const addressLine = (parts: string[]) => parts.filter(Boolean).join(', ')

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <Link to="/admin/orders" className="admin-back">← Back to orders</Link>
          <h1>{order.order_number}</h1>
          <p>Placed {formatDate(order.created_at)} · {order.language.toUpperCase()}</p>
        </div>
        <div className="admin-order-badges">
          <span className={`admin-badge ${orderStatusBadgeClass(order.status)}`}>
            {formatOrderStatus(order.status)}
          </span>
          <span className={`admin-badge ${paymentStatusBadgeClass(order.payment_status)}`}>
            {formatOrderStatus(order.payment_status)}
          </span>
        </div>
      </div>

      <div className="admin-order-grid">
        <div className="admin-card">
          <h2>Update order</h2>
          <div className="admin-form-grid">
            <label>
              Order status
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
                <option value="shipped">Shipped</option>
                <option value="delivered">Delivered</option>
                <option value="cancelled">Cancelled</option>
                <option value="refunded">Refunded</option>
              </select>
            </label>
            <label>
              Payment status
              <select value={paymentStatus} onChange={(e) => setPaymentStatus(e.target.value)}>
                <option value="pending">Pending</option>
                <option value="paid">Paid</option>
                <option value="failed">Failed</option>
                <option value="refunded">Refunded</option>
              </select>
            </label>
            <label className="full-width">
              Internal notes
              <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </label>
          </div>
          <div className="admin-form-actions">
            <button
              type="button"
              className="btn btn-primary"
              disabled={saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              {saveMutation.isPending ? 'Saving…' : 'Save changes'}
            </button>
            {saveMutation.isSuccess && <span className="admin-hint">Saved.</span>}
            {saveMutation.isError && <span className="admin-hint" style={{ color: '#b91c1c' }}>Save failed.</span>}
          </div>
        </div>

        <div className="admin-card">
          <h2>Customer</h2>
          <dl className="admin-detail-list">
            <dt>Email</dt><dd>{order.email}</dd>
            <dt>Phone</dt><dd>{order.phone || '—'}</dd>
          </dl>
        </div>

        <div className="admin-card">
          <h2>Payment</h2>
          <dl className="admin-detail-list">
            <dt>Method</dt><dd>{formatPaymentMethod(order.payment_method)}</dd>
            <dt>Status</dt><dd>{formatOrderStatus(order.payment_status)}</dd>
            <dt>Paid at</dt><dd>{formatDate(order.paid_at)}</dd>
            {order.coupon_code && (
              <>
                <dt>Coupon</dt><dd>{order.coupon_code}</dd>
              </>
            )}
          </dl>
        </div>

        <div className="admin-card">
          <h2>Billing address</h2>
          <p className="admin-address">
            <strong>{order.billing_first_name} {order.billing_last_name}</strong>
            {order.billing_company && <><br />{order.billing_company}</>}
            <br />{order.billing_address}
            <br />{order.billing_postcode} {order.billing_city}, {order.billing_country}
            {order.billing_vat && <><br />P.IVA: {order.billing_vat}</>}
          </p>
        </div>

        <div className="admin-card">
          <h2>Shipping address</h2>
          <p className="admin-address">
            <strong>{order.shipping_first_name} {order.shipping_last_name}</strong>
            <br />{order.shipping_address}
            <br />{order.shipping_postcode} {order.shipping_city}, {order.shipping_country}
          </p>
        </div>
      </div>

      <div className="admin-card">
        <h2>Line items</h2>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Size / Color</th>
                <th>Qty</th>
                <th>Unit</th>
                <th>Total</th>
                <th>Customization</th>
              </tr>
            </thead>
            <tbody>
              {order.items.map((item, index) => (
                <tr key={`${item.sku}-${index}`}>
                  <td>{item.product_name}</td>
                  <td>{item.sku}</td>
                  <td>{addressLine([item.size, item.color]) || '—'}</td>
                  <td>{item.quantity}</td>
                  <td>{formatPrice(item.unit_price)}</td>
                  <td>{formatPrice(item.line_total)}</td>
                  <td>
                    {item.customization ? (
                      <div className="admin-customization">
                        {item.customization.preview && (
                          <img src={item.customization.preview} alt="Design preview" />
                        )}
                        {item.customization.logo && (
                          <a href={item.customization.logo} target="_blank" rel="noreferrer">Download logo</a>
                        )}
                      </div>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="admin-order-totals">
          <div><span>Subtotal</span><span>{formatPrice(order.subtotal)}</span></div>
          <div><span>Shipping</span><span>{formatPrice(order.shipping_cost)}</span></div>
          {parseFloat(order.tax_amount) > 0 && (
            <div><span>Tax</span><span>{formatPrice(order.tax_amount)}</span></div>
          )}
          {parseFloat(order.discount_amount) > 0 && (
            <div><span>Discount</span><span>-{formatPrice(order.discount_amount)}</span></div>
          )}
          <div className="admin-order-total-row"><span>Total</span><span>{formatPrice(order.total)}</span></div>
        </div>
      </div>
    </div>
  )
}
