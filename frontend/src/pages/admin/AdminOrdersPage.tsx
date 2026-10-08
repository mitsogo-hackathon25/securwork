import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchAdminOrders } from '../../api/admin'
import { formatPrice } from '../../utils/format'
import { formatOrderStatus, orderStatusBadgeClass, paymentStatusBadgeClass } from '../../utils/orderLabels'
import './Admin.css'

export default function AdminOrdersPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [paymentFilter, setPaymentFilter] = useState('all')
  const [page, setPage] = useState(1)

  const params: Record<string, string | number> = { page, ordering: '-created_at' }
  if (search) params.search = search
  if (statusFilter !== 'all') params.status = statusFilter
  if (paymentFilter !== 'all') params.payment_status = paymentFilter

  const { data, isLoading } = useQuery({
    queryKey: ['admin-orders', params],
    queryFn: () => fetchAdminOrders(params),
  })

  const orders = data?.results ?? []
  const totalPages = data ? Math.ceil(data.count / 12) : 1

  const formatDate = (value: string) =>
    new Date(value).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>Ordini</h1>
          <p>Visualizza dettagli ordine, stato pagamento e evasione.</p>
        </div>
      </div>

      <div className="admin-toolbar">
        <input
          type="search"
          placeholder="Cerca per n. ordine, email o nome…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}>
          <option value="all">Tutti gli stati</option>
          <option value="pending">In attesa</option>
          <option value="processing">In elaborazione</option>
          <option value="shipped">Spedito</option>
          <option value="delivered">Consegnato</option>
          <option value="cancelled">Annullato</option>
          <option value="refunded">Rimborsato</option>
        </select>
        <select value={paymentFilter} onChange={(e) => { setPaymentFilter(e.target.value); setPage(1) }}>
          <option value="all">Tutti i pagamenti</option>
          <option value="pending">Pagamento in attesa</option>
          <option value="paid">Pagato</option>
          <option value="failed">Fallito</option>
          <option value="refunded">Rimborsato</option>
        </select>
      </div>

      {isLoading ? (
        <p>Caricamento ordini…</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Ordine</th>
                <th>Cliente</th>
                <th>Articoli</th>
                <th>Totale</th>
                <th>Stato</th>
                <th>Pagamento</th>
                <th>Data</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-empty">Nessun ordine trovato.</td>
                </tr>
              ) : orders.map((order) => (
                <tr key={order.id}>
                  <td><strong>{order.order_number}</strong></td>
                  <td>{order.email}</td>
                  <td>{order.item_count}</td>
                  <td>{formatPrice(order.total)}</td>
                  <td>
                    <span className={`admin-badge ${orderStatusBadgeClass(order.status)}`}>
                      {formatOrderStatus(order.status)}
                    </span>
                  </td>
                  <td>
                    <span className={`admin-badge ${paymentStatusBadgeClass(order.payment_status)}`}>
                      {formatOrderStatus(order.payment_status)}
                    </span>
                  </td>
                  <td>{formatDate(order.created_at)}</td>
                  <td className="admin-actions">
                    <Link to={`/admin/orders/${order.id}`} className="admin-link">Dettaglio</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="admin-pagination">
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Precedente</button>
          <span>Pagina {page} di {totalPages}</span>
          <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Successiva</button>
        </div>
      )}
    </div>
  )
}
