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

  if (isLoading) return <p>Caricamento ordine…</p>
  if (error || !order) {
    return (
      <div className="admin-page">
        <p className="admin-alert admin-alert-error">Ordine non trovato.</p>
        <Link to="/admin/orders" className="admin-back">← Torna agli ordini</Link>
      </div>
    )
  }

  const addressLine = (parts: string[]) => parts.filter(Boolean).join(', ')

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <Link to="/admin/orders" className="admin-back">← Torna agli ordini</Link>
          <h1>{order.order_number}</h1>
          <p>Effettuato il {formatDate(order.created_at)} · {order.language.toUpperCase()}</p>
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
          <h2>Aggiorna ordine</h2>
          <div className="admin-form-grid">
            <label>
              Stato ordine
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="pending">In attesa</option>
                <option value="processing">In elaborazione</option>
                <option value="shipped">Spedito</option>
                <option value="delivered">Consegnato</option>
                <option value="cancelled">Annullato</option>
                <option value="refunded">Rimborsato</option>
              </select>
            </label>
            <label>
              Stato pagamento
              <select value={paymentStatus} onChange={(e) => setPaymentStatus(e.target.value)}>
                <option value="pending">In attesa</option>
                <option value="paid">Pagato</option>
                <option value="failed">Fallito</option>
                <option value="refunded">Rimborsato</option>
              </select>
            </label>
            <label className="full-width">
              Note interne
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
              {saveMutation.isPending ? 'Salvataggio…' : 'Salva modifiche'}
            </button>
            {saveMutation.isSuccess && <span className="admin-hint">Salvato.</span>}
            {saveMutation.isError && <span className="admin-hint" style={{ color: '#b91c1c' }}>Salvataggio non riuscito.</span>}
          </div>
        </div>

        <div className="admin-card">
          <h2>Cliente</h2>
          <dl className="admin-detail-list">
            <dt>Email</dt><dd>{order.email}</dd>
            <dt>Telefono</dt><dd>{order.phone || '—'}</dd>
          </dl>
        </div>

        <div className="admin-card">
          <h2>Pagamento</h2>
          <dl className="admin-detail-list">
            <dt>Metodo</dt><dd>{formatPaymentMethod(order.payment_method)}</dd>
            <dt>Stato</dt><dd>{formatOrderStatus(order.payment_status)}</dd>
            <dt>Pagato il</dt><dd>{formatDate(order.paid_at)}</dd>
            {order.coupon_code && (
              <>
                <dt>Coupon</dt><dd>{order.coupon_code}</dd>
              </>
            )}
          </dl>
        </div>

        <div className="admin-card">
          <h2>Indirizzo di fatturazione</h2>
          <p className="admin-address">
            <strong>{order.billing_first_name} {order.billing_last_name}</strong>
            {order.billing_company && <><br />{order.billing_company}</>}
            <br />{order.billing_address}
            <br />{order.billing_postcode} {order.billing_city}, {order.billing_country}
            {order.billing_vat && <><br />P.IVA: {order.billing_vat}</>}
          </p>
        </div>

        <div className="admin-card">
          <h2>Indirizzo di spedizione</h2>
          <p className="admin-address">
            <strong>{order.shipping_first_name} {order.shipping_last_name}</strong>
            <br />{order.shipping_address}
            <br />{order.shipping_postcode} {order.shipping_city}, {order.shipping_country}
          </p>
        </div>
      </div>

      <div className="admin-card">
        <h2>Articoli</h2>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Prodotto</th>
                <th>SKU</th>
                <th>Taglia / Colore</th>
                <th>Qtà</th>
                <th>Unitario</th>
                <th>Totale</th>
                <th>Personalizzazione</th>
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
                        {item.customization.method && (
                          <strong>
                            {{
                              embroidery_chest: 'Ricamo — lato cuore/petto',
                              embroidery_large: 'Ricamo grande',
                              dtf_chest: 'DTF — lato cuore/petto',
                              dtf_large: 'DTF grande (formato A4)',
                            }[item.customization.method] || item.customization.method}
                          </strong>
                        )}
                        {item.customization.preview && (
                          <img src={item.customization.preview} alt="Anteprima design" />
                        )}
                        {item.customization.logo && (
                          <a href={item.customization.logo} target="_blank" rel="noreferrer">Scarica logo</a>
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
          <div><span>Subtotale</span><span>{formatPrice(order.subtotal)}</span></div>
          <div><span>Spedizione</span><span>{formatPrice(order.shipping_cost)}</span></div>
          {parseFloat(order.tax_amount) > 0 && (
            <div><span>Tasse</span><span>{formatPrice(order.tax_amount)}</span></div>
          )}
          {parseFloat(order.discount_amount) > 0 && (
            <div><span>Sconto</span><span>-{formatPrice(order.discount_amount)}</span></div>
          )}
          <div className="admin-order-total-row"><span>Totale</span><span>{formatPrice(order.total)}</span></div>
        </div>
      </div>
    </div>
  )
}
