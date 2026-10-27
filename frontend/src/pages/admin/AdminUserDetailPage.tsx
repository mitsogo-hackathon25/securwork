import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { fetchAdminUser } from '../../api/admin'
import { formatPrice } from '../../utils/format'
import { formatOrderStatus, orderStatusBadgeClass, paymentStatusBadgeClass } from '../../utils/orderLabels'
import './Admin.css'

export default function AdminUserDetailPage() {
  const { id } = useParams()
  const userId = Number(id)
  const { t, i18n } = useTranslation()

  const { data: user, isLoading, isError } = useQuery({
    queryKey: ['admin-user', userId],
    queryFn: () => fetchAdminUser(userId),
    enabled: Number.isFinite(userId) && userId > 0,
  })

  const dateLocale = i18n.language.startsWith('it') ? 'it-IT' : 'en-GB'
  const formatDate = (value: string | null) => {
    if (!value) return '—'
    return new Date(value).toLocaleString(dateLocale, { dateStyle: 'medium', timeStyle: 'short' })
  }

  if (!Number.isFinite(userId) || userId <= 0) {
    return (
      <div className="admin-page">
        <p className="admin-alert admin-alert-error">{t('adminUsers.notFound')}</p>
        <Link to="/admin/users" className="admin-back">{t('adminUsers.back')}</Link>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="admin-page">
        <p>{t('adminUsers.loading')}</p>
      </div>
    )
  }

  if (isError || !user) {
    return (
      <div className="admin-page">
        <p className="admin-alert admin-alert-error">{t('adminUsers.notFound')}</p>
        <Link to="/admin/users" className="admin-back">{t('adminUsers.back')}</Link>
      </div>
    )
  }

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || '—'

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <Link to="/admin/users" className="admin-back">{t('adminUsers.back')}</Link>
          <h1>{fullName}</h1>
          <p>{user.email}</p>
        </div>
        <div className="admin-order-badges">
          <span className={`admin-badge ${user.is_active ? 'admin-badge-success' : 'admin-badge-muted'}`}>
            {user.is_active ? t('adminCommon.active') : t('adminCommon.inactive')}
          </span>
          {user.is_staff && (
            <span className="admin-badge admin-badge-muted">{t('adminUsers.staffBadge')}</span>
          )}
        </div>
      </div>

      <div className="admin-order-grid">
        <div className="admin-card">
          <h2>{t('adminUsers.accountSection')}</h2>
          <dl className="admin-detail-list">
            <dt>{t('adminUsers.fieldUsername')}</dt>
            <dd>{user.username}</dd>
            <dt>{t('adminUsers.fieldEmail')}</dt>
            <dd>{user.email}</dd>
            <dt>{t('adminUsers.fieldName')}</dt>
            <dd>{fullName}</dd>
            <dt>{t('adminUsers.columnJoined')}</dt>
            <dd>{formatDate(user.date_joined)}</dd>
            <dt>{t('adminUsers.columnLastLogin')}</dt>
            <dd>{formatDate(user.last_login)}</dd>
          </dl>
        </div>

        <div className="admin-card">
          <h2>{t('adminUsers.profileSection')}</h2>
          <dl className="admin-detail-list">
            <dt>{t('adminUsers.fieldPhone')}</dt>
            <dd>{user.profile.phone || '—'}</dd>
            <dt>{t('adminUsers.fieldCompany')}</dt>
            <dd>{user.profile.company || '—'}</dd>
            <dt>{t('adminUsers.fieldVat')}</dt>
            <dd>{user.profile.vat_number || '—'}</dd>
          </dl>
        </div>

        <div className="admin-card">
          <h2>{t('adminUsers.ordersSection')}</h2>
          <dl className="admin-detail-list">
            <dt>{t('adminUsers.fieldOrderCount')}</dt>
            <dd>{user.order_count}</dd>
            <dt>{t('adminUsers.fieldPaidOrders')}</dt>
            <dd>{user.paid_order_count}</dd>
            <dt>{t('adminUsers.fieldTotalSpent')}</dt>
            <dd>{formatPrice(user.total_spent)}</dd>
            <dt>{t('adminUsers.fieldLastOrder')}</dt>
            <dd>{formatDate(user.last_order_at)}</dd>
          </dl>
        </div>
      </div>

      <div className="admin-card">
        <h2>{t('adminUsers.recentOrders')}</h2>
        {user.recent_orders.length === 0 ? (
          <p className="admin-hint">{t('adminUsers.noOrders')}</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>{t('adminOrders.columnOrder')}</th>
                  <th>{t('adminOrders.columnTotal')}</th>
                  <th>{t('adminOrders.columnStatus')}</th>
                  <th>{t('adminOrders.columnPayment')}</th>
                  <th>{t('adminOrders.columnDate')}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {user.recent_orders.map((order) => (
                  <tr key={order.id}>
                    <td>{order.order_number}</td>
                    <td>{formatPrice(order.total)}</td>
                    <td>
                      <span className={`admin-badge ${orderStatusBadgeClass(order.status)}`}>
                        {formatOrderStatus(order.status)}
                      </span>
                    </td>
                    <td>
                      <span className={`admin-badge ${paymentStatusBadgeClass(order.payment_status)}`}>
                        {order.payment_status}
                      </span>
                    </td>
                    <td>{formatDate(order.created_at)}</td>
                    <td className="admin-actions">
                      <Link to={`/admin/orders/${order.id}`} className="admin-link">
                        {t('adminOrders.detail')}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
