import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteAdminPickupLocation, fetchAdminPickupLocations } from '../../api/admin'
import './Admin.css'

export default function AdminPickupLocationsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const params: Record<string, string | number> = { page, ordering: 'sort_order' }
  if (search) params.search = search

  const { data, isLoading } = useQuery({
    queryKey: ['admin-pickup-locations', params],
    queryFn: () => fetchAdminPickupLocations(params),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAdminPickupLocation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-pickup-locations'] }),
  })

  const locations = data?.results ?? []
  const totalPages = data ? Math.ceil(data.count / 12) : 1

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(t('adminPickup.confirmDelete', { name }))) return
    await deleteMutation.mutateAsync(id)
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>{t('adminPickup.title')}</h1>
          <p>{t('adminPickup.subtitle')}</p>
        </div>
        <Link to="/admin/pickup-locations/new" className="btn btn-primary">{t('adminPickup.add')}</Link>
      </div>

      <div className="admin-toolbar">
        <input
          type="search"
          placeholder={t('adminPickup.searchPlaceholder')}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
      </div>

      {isLoading ? (
        <p>{t('adminCommon.loading')}</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t('adminPickup.colName')}</th>
                <th>{t('adminPickup.colAddress')}</th>
                <th>{t('adminPickup.colStatus')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {locations.length === 0 ? (
                <tr>
                  <td colSpan={4} className="admin-empty">{t('adminPickup.empty')}</td>
                </tr>
              ) : locations.map((loc) => (
                <tr key={loc.id}>
                  <td>{loc.name}</td>
                  <td>{loc.address}, {loc.postcode} {loc.city}</td>
                  <td>
                    <span className={`admin-badge ${loc.is_active ? 'admin-badge-success' : 'admin-badge-muted'}`}>
                      {loc.is_active ? t('adminCommon.active') : t('adminCommon.inactive')}
                    </span>
                  </td>
                  <td className="admin-actions">
                    <Link to={`/admin/pickup-locations/${loc.id}`} className="admin-link">{t('adminCommon.edit')}</Link>
                    <button type="button" className="admin-link admin-link-danger" onClick={() => handleDelete(loc.id, loc.name)}>
                      {t('adminCommon.delete')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="admin-pagination">
          <button type="button" className="btn btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t('adminCommon.prev')}
          </button>
          <span>{t('adminCommon.pageOf', { page, total: totalPages })}</span>
          <button type="button" className="btn btn-secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            {t('adminCommon.next')}
          </button>
        </div>
      )}
    </div>
  )
}
