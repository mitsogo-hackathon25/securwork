import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { fetchAdminUsers } from '../../api/admin'
import './Admin.css'

export default function AdminUsersPage() {
  const { t, i18n } = useTranslation()
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('all')
  const [page, setPage] = useState(1)

  const params: Record<string, string | number> = { page, ordering: '-date_joined' }
  if (search) params.search = search
  if (activeFilter === 'active') params.is_active = 'true'
  if (activeFilter === 'inactive') params.is_active = 'false'

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', params],
    queryFn: () => fetchAdminUsers(params),
  })

  const users = data?.results ?? []
  const totalPages = data ? Math.ceil(data.count / 12) : 1
  const dateLocale = i18n.language.startsWith('it') ? 'it-IT' : 'en-GB'

  const formatDate = (value: string | null) => {
    if (!value) return '—'
    return new Date(value).toLocaleString(dateLocale, { dateStyle: 'short', timeStyle: 'short' })
  }

  const displayName = (user: { first_name: string; last_name: string; email: string }) => {
    const name = [user.first_name, user.last_name].filter(Boolean).join(' ')
    return name || user.email
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>{t('adminUsers.title')}</h1>
          <p>{t('adminUsers.subtitle')}</p>
        </div>
      </div>

      <div className="admin-toolbar">
        <input
          type="search"
          placeholder={t('adminUsers.searchPlaceholder')}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select
          value={activeFilter}
          onChange={(e) => { setActiveFilter(e.target.value); setPage(1) }}
        >
          <option value="all">{t('adminUsers.filterAll')}</option>
          <option value="active">{t('adminUsers.filterActive')}</option>
          <option value="inactive">{t('adminUsers.filterInactive')}</option>
        </select>
      </div>

      {isLoading ? (
        <p>{t('adminUsers.loading')}</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t('adminUsers.columnName')}</th>
                <th>{t('adminUsers.columnEmail')}</th>
                <th>{t('adminUsers.columnPhone')}</th>
                <th>{t('adminUsers.columnOrders')}</th>
                <th>{t('adminUsers.columnStatus')}</th>
                <th>{t('adminUsers.columnJoined')}</th>
                <th>{t('adminUsers.columnLastLogin')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-empty">{t('adminUsers.empty')}</td>
                </tr>
              ) : users.map((user) => (
                <tr key={user.id}>
                  <td>
                    {displayName(user)}
                    {user.is_staff && (
                      <span className="admin-badge admin-badge-muted" style={{ marginLeft: 8 }}>
                        {t('adminUsers.staffBadge')}
                      </span>
                    )}
                  </td>
                  <td>{user.email}</td>
                  <td>{user.phone || '—'}</td>
                  <td>{user.order_count}</td>
                  <td>
                    <span className={`admin-badge ${user.is_active ? 'admin-badge-success' : 'admin-badge-muted'}`}>
                      {user.is_active ? t('adminCommon.active') : t('adminCommon.inactive')}
                    </span>
                  </td>
                  <td>{formatDate(user.date_joined)}</td>
                  <td>{formatDate(user.last_login)}</td>
                  <td className="admin-actions">
                    <Link to={`/admin/users/${user.id}`} className="admin-link">{t('adminUsers.detail')}</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isLoading && totalPages > 1 && (
        <div className="admin-pagination">
          <button type="button" className="btn btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t('adminUsers.prevPage')}
          </button>
          <span>{t('adminUsers.pageOf', { page, total: totalPages })}</span>
          <button type="button" className="btn btn-secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            {t('adminUsers.nextPage')}
          </button>
        </div>
      )}
    </div>
  )
}
