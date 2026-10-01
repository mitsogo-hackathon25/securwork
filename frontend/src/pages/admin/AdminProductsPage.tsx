import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteAdminProduct, fetchAdminProducts } from '../../api/admin'
import { formatPrice } from '../../utils/format'
import './Admin.css'

export default function AdminProductsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)

  const params: Record<string, string | number | boolean> = { page, ordering: '-updated_at' }
  if (search) params.search = search
  if (statusFilter === 'active') params.is_active = true
  if (statusFilter === 'inactive') params.is_active = false

  const { data, isLoading } = useQuery({
    queryKey: ['admin-products', params],
    queryFn: () => fetchAdminProducts(params),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAdminProduct,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-products'] }),
  })

  const products = data?.results ?? []
  const totalPages = data ? Math.ceil(data.count / 12) : 1

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return
    await deleteMutation.mutateAsync(id)
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>Products</h1>
          <p>Manage catalog, inventory, pricing, and descriptions.</p>
        </div>
        <Link to="/admin/products/new" className="btn btn-primary">Add product</Link>
      </div>

      <div className="admin-toolbar">
        <input
          type="search"
          placeholder="Search by name, SKU, or slug…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}>
          <option value="all">All statuses</option>
          <option value="active">Active only</option>
          <option value="inactive">Inactive only</option>
        </select>
      </div>

      {isLoading ? (
        <p>Loading products…</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Price</th>
                <th>Stock</th>
                <th>Status</th>
                <th>Flags</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {products.length === 0 ? (
                <tr>
                  <td colSpan={7} className="admin-empty">No products found.</td>
                </tr>
              ) : products.map((product) => (
                <tr key={product.id}>
                  <td>
                    <div className="admin-product-cell">
                      {product.primary_image ? (
                        <img src={product.primary_image} alt="" />
                      ) : (
                        <div className="admin-product-thumb-placeholder" />
                      )}
                      <div>
                        <strong>{product.name}</strong>
                        <span>{product.slug}</span>
                      </div>
                    </div>
                  </td>
                  <td>{product.sku}</td>
                  <td>{product.min_price ? formatPrice(product.min_price) : '—'}</td>
                  <td>
                    <span className={product.in_stock ? 'admin-stock-ok' : 'admin-stock-out'}>
                      {product.total_stock}
                    </span>
                  </td>
                  <td>
                    <span className={`admin-badge ${product.is_active ? 'admin-badge-success' : 'admin-badge-muted'}`}>
                      {product.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <div className="admin-flags">
                      {product.is_featured && <span className="admin-flag">Featured</span>}
                      {product.is_new_arrival && <span className="admin-flag">New</span>}
                      {product.is_bestseller && <span className="admin-flag">Best</span>}
                    </div>
                  </td>
                  <td className="admin-actions">
                    <Link to={`/admin/products/${product.id}`} className="admin-link">Edit</Link>
                    <button
                      type="button"
                      className="admin-link admin-link-danger"
                      onClick={() => handleDelete(product.id, product.name)}
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
