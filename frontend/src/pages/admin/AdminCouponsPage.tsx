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
  if (!from && !until) return 'No expiry'
  const fmt = (value: string) =>
    new Date(value).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })
  if (from && until) return `${fmt(from)} → ${fmt(until)}`
  if (from) return `From ${fmt(from)}`
  return `Until ${fmt(until!)}`
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
    if (!window.confirm(`Delete coupon "${code}"?`)) return
    await deleteMutation.mutateAsync(id)
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>Coupons</h1>
          <p>Create discount codes for customers. Set a usage limit to control how many times each code can be used.</p>
        </div>
        <Link to="/admin/coupons/new" className="btn btn-primary">Add coupon</Link>
      </div>

      <div className="admin-toolbar">
        <input
          type="search"
          placeholder="Search by code…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={activeFilter} onChange={(e) => { setActiveFilter(e.target.value); setPage(1) }}>
          <option value="all">All coupons</option>
          <option value="active">Active only</option>
          <option value="inactive">Inactive only</option>
        </select>
      </div>

      {isLoading ? (
        <p>Loading coupons…</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Discount</th>
                <th>Min. order</th>
                <th>Uses</th>
                <th>Validity</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {coupons.length === 0 ? (
                <tr>
                  <td colSpan={7} className="admin-empty">No coupons found.</td>
                </tr>
              ) : coupons.map((coupon) => (
                <tr key={coupon.id}>
                  <td><strong>{coupon.code}</strong></td>
                  <td>{formatDiscount(coupon)}</td>
                  <td>{formatPrice(coupon.min_order_amount)}</td>
                  <td>
                    {formatUses(coupon)}
                    {coupon.max_uses != null && coupon.uses_remaining === 0 && (
                      <span className="admin-flag">Limit reached</span>
                    )}
                  </td>
                  <td>{formatDateRange(coupon.valid_from, coupon.valid_until)}</td>
                  <td>
                    <span className={`admin-badge ${coupon.is_active ? 'admin-badge-success' : 'admin-badge-muted'}`}>
                      {coupon.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="admin-actions">
                    <Link to={`/admin/coupons/${coupon.id}`} className="admin-link">Edit</Link>
                    <button
                      type="button"
                      className="admin-link admin-link-danger"
                      onClick={() => handleDelete(coupon.id!, coupon.code)}
                    >
                      Delete
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
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span>Page {page} of {totalPages}</span>
          <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      )}
    </div>
  )
}
