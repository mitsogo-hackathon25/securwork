import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAdminBrand,
  createAdminCategory,
  createAdminColor,
  deleteAdminBrand,
  deleteAdminCategory,
  deleteAdminColor,
  fetchAdminBrands,
  fetchAdminCategoryList,
  fetchAdminColors,
  updateAdminBrand,
  updateAdminCategory,
  updateAdminColor,
} from '../../api/admin'
import type { AdminBrand, AdminCategory, AdminColor } from '../../api/types'
import './Admin.css'

const emptyCategory = (): AdminCategory => ({
  section: 'workwear',
  parent_id: null,
  name_it: '',
  name_en: '',
  description_it: '',
  description_en: '',
  sort_order: 0,
  is_active: true,
})

const emptyBrand = (): AdminBrand => ({
  name: '',
  is_active: true,
  sort_order: 0,
})

const emptyColor = (): AdminColor => ({
  name: '',
  is_active: true,
  sort_order: 0,
})

type CatalogTab = 'categories' | 'brands' | 'colors'

export default function AdminCatalogPage() {
  const queryClient = useQueryClient()
  const [catalogTab, setCatalogTab] = useState<CatalogTab>('categories')
  const [categoryForm, setCategoryForm] = useState<AdminCategory | null>(null)
  const [brandForm, setBrandForm] = useState<AdminBrand | null>(null)
  const [colorForm, setColorForm] = useState<AdminColor | null>(null)
  const [error, setError] = useState('')

  const switchTab = (tab: CatalogTab) => {
    setCatalogTab(tab)
    setError('')
    setCategoryForm(null)
    setBrandForm(null)
    setColorForm(null)
  }

  const { data: categories = [], isLoading: loadingCategories } = useQuery({
    queryKey: ['admin-category-list'],
    queryFn: fetchAdminCategoryList,
  })

  const { data: brands = [], isLoading: loadingBrands } = useQuery({
    queryKey: ['admin-brands'],
    queryFn: fetchAdminBrands,
  })

  const { data: colors = [], isLoading: loadingColors } = useQuery({
    queryKey: ['admin-colors'],
    queryFn: fetchAdminColors,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin-category-list'] })
    queryClient.invalidateQueries({ queryKey: ['admin-categories'] })
    queryClient.invalidateQueries({ queryKey: ['admin-brands'] })
    queryClient.invalidateQueries({ queryKey: ['admin-colors'] })
    queryClient.invalidateQueries({ queryKey: ['product-brands'] })
    queryClient.invalidateQueries({ queryKey: ['product-colors'] })
    queryClient.invalidateQueries({ queryKey: ['categories'] })
  }

  const saveCategory = useMutation({
    mutationFn: (payload: AdminCategory) =>
      payload.id ? updateAdminCategory(payload.id, payload) : createAdminCategory(payload),
    onSuccess: () => {
      setCategoryForm(null)
      setError('')
      invalidate()
    },
    onError: (err: unknown) => {
      setError(err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Could not save category.')
    },
  })

  const saveBrand = useMutation({
    mutationFn: (payload: AdminBrand) =>
      payload.id ? updateAdminBrand(payload.id, payload) : createAdminBrand(payload),
    onSuccess: () => {
      setBrandForm(null)
      setError('')
      invalidate()
    },
    onError: (err: unknown) => {
      setError(err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Could not save brand.')
    },
  })

  const removeCategory = useMutation({
    mutationFn: deleteAdminCategory,
    onSuccess: invalidate,
    onError: (err: unknown) => {
      setError(err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Could not delete category.')
    },
  })

  const removeBrand = useMutation({
    mutationFn: deleteAdminBrand,
    onSuccess: invalidate,
    onError: (err: unknown) => {
      setError(err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Could not delete brand.')
    },
  })

  const saveColor = useMutation({
    mutationFn: (payload: AdminColor) =>
      payload.id ? updateAdminColor(payload.id, payload) : createAdminColor(payload),
    onSuccess: () => {
      setColorForm(null)
      setError('')
      invalidate()
    },
    onError: (err: unknown) => {
      setError(err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Could not save color.')
    },
  })

  const removeColor = useMutation({
    mutationFn: deleteAdminColor,
    onSuccess: invalidate,
    onError: (err: unknown) => {
      setError(err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Could not delete color.')
    },
  })

  const handleCategorySubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!categoryForm) return
    saveCategory.mutate({ ...categoryForm, is_active: true })
  }

  const handleBrandSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!brandForm) return
    saveBrand.mutate({ ...brandForm, is_active: true })
  }

  const handleColorSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!colorForm) return
    saveColor.mutate({ ...colorForm, is_active: true })
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>Catalog</h1>
          <p>Manage categories, brands, and colors used in shop filters and product variants.</p>
        </div>
      </div>

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      <div className="admin-tabs admin-catalog-tabs">
        <button
          type="button"
          className={catalogTab === 'categories' ? 'active' : ''}
          onClick={() => switchTab('categories')}
        >
          Categories
        </button>
        <button
          type="button"
          className={catalogTab === 'brands' ? 'active' : ''}
          onClick={() => switchTab('brands')}
        >
          Brands
        </button>
        <button
          type="button"
          className={catalogTab === 'colors' ? 'active' : ''}
          onClick={() => switchTab('colors')}
        >
          Colors
        </button>
      </div>

      {catalogTab === 'categories' && (
      <section className="admin-card admin-catalog-section">
        <div className="admin-section-header">
          <h2>Categories</h2>
          <button type="button" className="btn btn-secondary" onClick={() => setCategoryForm(emptyCategory())}>
            Add category
          </button>
        </div>

        {categoryForm && (
          <form className="admin-inline-form" onSubmit={handleCategorySubmit}>
            <div className="admin-form-grid">
              <label>
                Name (IT) *
                <input
                  value={categoryForm.name_it}
                  onChange={(e) => setCategoryForm({ ...categoryForm, name_it: e.target.value })}
                  required
                />
              </label>
              <label>
                Name (EN)
                <input
                  value={categoryForm.name_en}
                  onChange={(e) => setCategoryForm({ ...categoryForm, name_en: e.target.value })}
                />
              </label>
              <label>
                Section
                <select
                  value={categoryForm.section}
                  onChange={(e) => setCategoryForm({
                    ...categoryForm,
                    section: e.target.value as AdminCategory['section'],
                  })}
                >
                  <option value="workwear">Workwear</option>
                  <option value="professional">Professional</option>
                </select>
              </label>
            </div>
            <div className="admin-inline-form-actions">
              <button type="submit" className="btn btn-primary" disabled={saveCategory.isPending}>
                {categoryForm.id ? 'Save category' : 'Create category'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setCategoryForm(null)}>Cancel</button>
            </div>
          </form>
        )}

        {loadingCategories ? (
          <p>Loading categories…</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name (IT)</th>
                  <th>Section</th>
                  <th>Parent</th>
                  <th>Products</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {categories.map((cat) => (
                  <tr key={cat.id}>
                    <td><strong>{cat.name_it}</strong><br /><span className="admin-muted">{cat.slug}</span></td>
                    <td>{cat.section === 'workwear' ? 'Workwear' : 'Professional'}</td>
                    <td>{cat.parent_name || '—'}</td>
                    <td>{cat.product_count ?? 0}</td>
                    <td className="admin-actions">
                      <button type="button" className="admin-link" onClick={() => setCategoryForm(cat)}>Edit</button>
                      <button
                        type="button"
                        className="admin-link admin-link-danger"
                        onClick={() => {
                          if (!cat.id || !window.confirm(`Delete category "${cat.name_it}"?`)) return
                          removeCategory.mutate(cat.id)
                        }}
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
      </section>
      )}

      {catalogTab === 'brands' && (
      <section className="admin-card admin-catalog-section">
        <div className="admin-section-header">
          <h2>Brands</h2>
          <button type="button" className="btn btn-secondary" onClick={() => setBrandForm(emptyBrand())}>
            Add brand
          </button>
        </div>

        {brandForm && (
          <form className="admin-inline-form" onSubmit={handleBrandSubmit}>
            <div className="admin-form-grid">
              <label>
                Brand name *
                <input
                  value={brandForm.name}
                  onChange={(e) => setBrandForm({ ...brandForm, name: e.target.value })}
                  required
                />
              </label>
            </div>
            <div className="admin-inline-form-actions">
              <button type="submit" className="btn btn-primary" disabled={saveBrand.isPending}>
                {brandForm.id ? 'Save brand' : 'Create brand'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setBrandForm(null)}>Cancel</button>
            </div>
          </form>
        )}

        {loadingBrands ? (
          <p>Loading brands…</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Products</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {brands.length === 0 ? (
                  <tr><td colSpan={3} className="admin-empty">No brands yet.</td></tr>
                ) : brands.map((brand) => (
                  <tr key={brand.id}>
                    <td><strong>{brand.name}</strong></td>
                    <td>{brand.product_count ?? 0}</td>
                    <td className="admin-actions">
                      <button type="button" className="admin-link" onClick={() => setBrandForm(brand)}>Edit</button>
                      <button
                        type="button"
                        className="admin-link admin-link-danger"
                        onClick={() => {
                          if (!brand.id || !window.confirm(`Delete brand "${brand.name}"?`)) return
                          removeBrand.mutate(brand.id)
                        }}
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
      </section>
      )}

      {catalogTab === 'colors' && (
      <section className="admin-card admin-catalog-section">
        <div className="admin-section-header">
          <h2>Colors</h2>
          <button type="button" className="btn btn-secondary" onClick={() => setColorForm(emptyColor())}>
            Add color
          </button>
        </div>

        {colorForm && (
          <form className="admin-inline-form" onSubmit={handleColorSubmit}>
            <div className="admin-form-grid">
              <label>
                  Color name *
                <input
                  value={colorForm.name}
                  onChange={(e) => setColorForm({ ...colorForm, name: e.target.value })}
                  required
                />
              </label>
            </div>
            <div className="admin-inline-form-actions">
              <button type="submit" className="btn btn-primary" disabled={saveColor.isPending}>
                {colorForm.id ? 'Save color' : 'Create color'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setColorForm(null)}>Cancel</button>
            </div>
          </form>
        )}

        {loadingColors ? (
          <p>Loading colors…</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Variants</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {colors.length === 0 ? (
                  <tr><td colSpan={3} className="admin-empty">No colors yet.</td></tr>
                ) : colors.map((color) => (
                  <tr key={color.id}>
                    <td><strong>{color.name}</strong></td>
                    <td>{color.variant_count ?? 0}</td>
                    <td className="admin-actions">
                      <button type="button" className="admin-link" onClick={() => setColorForm(color)}>Edit</button>
                      <button
                        type="button"
                        className="admin-link admin-link-danger"
                        onClick={() => {
                          if (!color.id || !window.confirm(`Delete color "${color.name}"?`)) return
                          removeColor.mutate(color.id)
                        }}
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
      </section>
      )}
    </div>
  )
}
