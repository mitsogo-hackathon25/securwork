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
          <h1>Orders</h1>
          <p>View order details, payment status, and fulfilment.</p>
        </div>
      </div>

      <div className="admin-toolbar">
        <input
          type="search"
          placeholder="Search by order #, email, or name…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}>
          <option value="all">All statuses</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="shipped">Shipped</option>
          <option value="delivered">Delivered</option>
          <option value="cancelled">Cancelled</option>
          <option value="refunded">Refunded</option>
        </select>
        <select value={paymentFilter} onChange={(e) => { setPaymentFilter(e.target.value); setPage(1) }}>
          <option value="all">All payments</option>
          <option value="pending">Payment pending</option>
          <option value="paid">Paid</option>
          <option value="failed">Failed</option>
          <option value="refunded">Refunded</option>
        </select>
      </div>

      {isLoading ? (
        <p>Loading orders…</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Customer</th>
                <th>Items</th>
                <th>Total</th>
                <th>Status</th>
                <th>Payment</th>
                <th>Date</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-empty">No orders found.</td>
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
                    <Link to={`/admin/orders/${order.id}`} className="admin-link">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="admin-pagination">
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span>Page {page} of {totalPages}</span>
          <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      )}
    </div>
  )
}
