import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { fetchAdminMonthlySales, fetchAdminOrders } from '../../api/admin'
import { formatPrice } from '../../utils/format'
import { formatOrderStatus, orderStatusBadgeClass, paymentStatusBadgeClass } from '../../utils/orderLabels'
import './Admin.css'

const currentYear = new Date().getFullYear()

export default function AdminOrdersPage() {
  const { t, i18n } = useTranslation()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [paymentFilter, setPaymentFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [salesYear, setSalesYear] = useState(currentYear)
  const [salesEnabled, setSalesEnabled] = useState(false)

  const params: Record<string, string | number> = { page, ordering: '-created_at' }
  if (search) params.search = search
  if (statusFilter !== 'all') params.status = statusFilter
  if (paymentFilter !== 'all') params.payment_status = paymentFilter

  const { data, isLoading } = useQuery({
    queryKey: ['admin-orders', params],
    queryFn: () => fetchAdminOrders(params),
  })

  const {
    data: monthlySales,
    isLoading: salesLoading,
    isError: salesError,
    refetch: refetchSales,
  } = useQuery({
    queryKey: ['admin-monthly-sales', salesYear],
    queryFn: () => fetchAdminMonthlySales(salesYear),
    enabled: salesEnabled,
  })

  const orders = data?.results ?? []
  const totalPages = data ? Math.ceil(data.count / 12) : 1

  const yearOptions = useMemo(() => {
    const years: number[] = []
    for (let y = currentYear; y >= currentYear - 6; y -= 1) {
      years.push(y)
    }
    return years
  }, [])

  const dateLocale = i18n.language.startsWith('it') ? 'it-IT' : 'en-GB'

  const formatDate = (value: string) =>
    new Date(value).toLocaleString(dateLocale, { dateStyle: 'short', timeStyle: 'short' })

  const formatMonth = (month: number) =>
    new Date(salesYear, month - 1, 1).toLocaleString(dateLocale, { month: 'long' })

  const loadMonthlySales = () => {
    setSalesEnabled(true)
    if (salesEnabled) {
      refetchSales()
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>{t('adminOrders.title')}</h1>
          <p>{t('adminOrders.subtitle')}</p>
        </div>
      </div>

      <section className="admin-sales-panel" aria-labelledby="admin-monthly-sales-title">
        <div className="admin-sales-panel-head">
          <div>
            <h2 id="admin-monthly-sales-title">{t('adminOrders.monthlySalesTitle')}</h2>
            <p className="admin-sales-hint">{t('adminOrders.monthlySalesHint')}</p>
          </div>
          <div className="admin-sales-controls">
            <label className="admin-sales-year">
              <span>{t('adminOrders.year')}</span>
              <select
                value={salesYear}
                onChange={(e) => {
                  setSalesYear(Number(e.target.value))
                  setSalesEnabled(false)
                }}
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="btn btn-primary admin-sales-load"
              onClick={loadMonthlySales}
              disabled={salesLoading}
            >
              {salesLoading ? t('adminOrders.loadingSales') : t('adminOrders.loadSales')}
            </button>
          </div>
        </div>

        {salesError && <p className="admin-sales-error">{t('adminOrders.salesError')}</p>}

        {monthlySales && salesEnabled && !salesLoading && (
          <>
            <div className="admin-sales-summary">
              <div>
                <strong>{t('adminOrders.yearTotal')}</strong>
                <span>{formatPrice(monthlySales.summary.revenue)}</span>
              </div>
              <div>
                <span>{t('adminOrders.ordersCount', { count: monthlySales.summary.order_count })}</span>
                <span>{t('adminOrders.paidCount', { count: monthlySales.summary.paid_order_count })}</span>
              </div>
            </div>
            <div className="admin-table-wrap admin-sales-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{t('adminOrders.columnMonth')}</th>
                    <th>{t('adminOrders.columnOrders')}</th>
                    <th>{t('adminOrders.columnPaidOrders')}</th>
                    <th>{t('adminOrders.columnRevenue')}</th>
                  </tr>
                </thead>
                <tbody>
                  {monthlySales.months.map((row) => (
                    <tr key={row.month}>
                      <td>{formatMonth(row.month)}</td>
                      <td>{row.order_count}</td>
                      <td>{row.paid_order_count}</td>
                      <td>{formatPrice(row.revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <div className="admin-toolbar">
        <input
          type="search"
          placeholder={t('adminOrders.searchPlaceholder')}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}>
          <option value="all">{t('adminOrders.allStatuses')}</option>
          <option value="pending">In attesa</option>
          <option value="processing">In elaborazione</option>
          <option value="shipped">Spedito</option>
          <option value="delivered">Consegnato</option>
          <option value="cancelled">Annullato</option>
          <option value="refunded">Rimborsato</option>
        </select>
        <select value={paymentFilter} onChange={(e) => { setPaymentFilter(e.target.value); setPage(1) }}>
          <option value="all">{t('adminOrders.allPayments')}</option>
          <option value="pending">Pagamento in attesa</option>
          <option value="paid">Pagato</option>
          <option value="failed">Fallito</option>
          <option value="refunded">Rimborsato</option>
        </select>
      </div>

      {isLoading ? (
        <p>{t('adminOrders.loading')}</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t('adminOrders.columnOrder')}</th>
                <th>{t('adminOrders.columnCustomer')}</th>
                <th>{t('adminOrders.columnItems')}</th>
                <th>{t('adminOrders.columnTotal')}</th>
                <th>{t('adminOrders.columnStatus')}</th>
                <th>{t('adminOrders.columnPayment')}</th>
                <th>{t('adminOrders.columnDate')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-empty">{t('adminOrders.empty')}</td>
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
                    <Link to={`/admin/orders/${order.id}`} className="admin-link">{t('adminOrders.detail')}</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="admin-pagination">
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t('adminOrders.prevPage')}
          </button>
          <span>{t('adminOrders.pageOf', { page, total: totalPages })}</span>
          <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            {t('adminOrders.nextPage')}
          </button>
        </div>
      )}
    </div>
  )
}
