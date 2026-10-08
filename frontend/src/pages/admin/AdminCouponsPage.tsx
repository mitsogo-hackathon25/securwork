import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteAdminCoupon, fetchAdminCoupons } from '../../api/admin'
import { formatPrice } from '../../utils/format'
import './Admin.css'

function formatDiscount(coupon: { discount_percent: string | null; discount_amount: string | null }) {
  if (coupon.discount_percent) return `${coupon.discount_percent}%`
  if (coupon.discount_amount) return formatPrice(coupon.discount_amount)
  return '—'
}

function formatUses(coupon: { used_count?: number; max_uses: number | null; uses_remaining?: number | null }) {
  const used = coupon.used_count ?? 0
  if (coupon.max_uses == null) return `${used} / ∞`
  return `${used} / ${coupon.max_uses}`
}

function formatDateRange(from: string | null, until: string | null) {
  if (!from && !until) return 'Nessuna scadenza'
  const fmt = (value: string) =>
    new Date(value).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })
  if (from && until) return `${fmt(from)} → ${fmt(until)}`
  if (from) return `Dal ${fmt(from)}`
  return `Fino al ${fmt(until!)}`
}

export default function AdminCouponsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('all')
  const [page, setPage] = useState(1)

  const params: Record<string, string | number> = { page, ordering: '-id' }
  if (search) params.search = search
  if (activeFilter === 'active') params.is_active = 'true'
  if (activeFilter === 'inactive') params.is_active = 'false'

  const { data, isLoading } = useQuery({
    queryKey: ['admin-coupons', params],
    queryFn: () => fetchAdminCoupons(params),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAdminCoupon,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-coupons'] }),
  })

  const coupons = data?.results ?? []
  const totalPages = data ? Math.ceil(data.count / 12) : 1

  const handleDelete = async (id: number, code: string) => {
    if (!window.confirm(`Eliminare il coupon "${code}"?`)) return
    await deleteMutation.mutateAsync(id)
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>Coupon</h1>
          <p>Crea codici sconto per i clienti. Imposta un limite di utilizzi per controllare quante volte ogni codice può essere usato.</p>
        </div>
        <Link to="/admin/coupons/new" className="btn btn-primary">Aggiungi coupon</Link>
      </div>

      <div className="admin-toolbar">
        <input
          type="search"
          placeholder="Cerca per codice…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={activeFilter} onChange={(e) => { setActiveFilter(e.target.value); setPage(1) }}>
          <option value="all">Tutti i coupon</option>
          <option value="active">Solo attivi</option>
          <option value="inactive">Solo inattivi</option>
        </select>
      </div>

      {isLoading ? (
        <p>Caricamento coupon…</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Codice</th>
                <th>Sconto</th>
                <th>Ordine min.</th>
                <th>Utilizzi</th>
                <th>Validità</th>
                <th>Stato</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {coupons.length === 0 ? (
                <tr>
                  <td colSpan={7} className="admin-empty">Nessun coupon trovato.</td>
                </tr>
              ) : coupons.map((coupon) => (
                <tr key={coupon.id}>
                  <td><strong>{coupon.code}</strong></td>
                  <td>{formatDiscount(coupon)}</td>
                  <td>{formatPrice(coupon.min_order_amount)}</td>
                  <td>
                    {formatUses(coupon)}
                    {coupon.max_uses != null && coupon.uses_remaining === 0 && (
                      <span className="admin-flag">Limite raggiunto</span>
                    )}
                  </td>
                  <td>{formatDateRange(coupon.valid_from, coupon.valid_until)}</td>
                  <td>
                    <span className={`admin-badge ${coupon.is_active ? 'admin-badge-success' : 'admin-badge-muted'}`}>
                      {coupon.is_active ? 'Attivo' : 'Inattivo'}
                    </span>
                  </td>
                  <td className="admin-actions">
                    <Link to={`/admin/coupons/${coupon.id}`} className="admin-link">Modifica</Link>
                    <button
                      type="button"
                      className="admin-link admin-link-danger"
                      onClick={() => handleDelete(coupon.id!, coupon.code)}
                    >
                      Elimina
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
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Precedente</button>
          <span>Pagina {page} di {totalPages}</span>
          <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Successiva</button>
        </div>
      )}
    </div>
  )
}
