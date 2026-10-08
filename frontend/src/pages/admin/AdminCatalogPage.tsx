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
        : 'Impossibile salvare la categoria.')
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
        : 'Impossibile salvare la marca.')
    },
  })

  const removeCategory = useMutation({
    mutationFn: deleteAdminCategory,
    onSuccess: invalidate,
    onError: (err: unknown) => {
      setError(err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Impossibile eliminare la categoria.')
    },
  })

  const removeBrand = useMutation({
    mutationFn: deleteAdminBrand,
    onSuccess: invalidate,
    onError: (err: unknown) => {
      setError(err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Impossibile eliminare la marca.')
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
        : 'Impossibile salvare il colore.')
    },
  })

  const removeColor = useMutation({
    mutationFn: deleteAdminColor,
    onSuccess: invalidate,
    onError: (err: unknown) => {
      setError(err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Impossibile eliminare il colore.')
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
          <h1>Catalogo</h1>
          <p>Gestisci categorie, marche e colori usati nei filtri del negozio e nelle varianti prodotto.</p>
        </div>
      </div>

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      <div className="admin-tabs admin-catalog-tabs">
        <button
          type="button"
          className={catalogTab === 'categories' ? 'active' : ''}
          onClick={() => switchTab('categories')}
        >
          Categorie
        </button>
        <button
          type="button"
          className={catalogTab === 'brands' ? 'active' : ''}
          onClick={() => switchTab('brands')}
        >
          Marche
        </button>
        <button
          type="button"
          className={catalogTab === 'colors' ? 'active' : ''}
          onClick={() => switchTab('colors')}
        >
          Colori
        </button>
      </div>

      {catalogTab === 'categories' && (
      <section className="admin-card admin-catalog-section">
        <div className="admin-section-header">
          <h2>Categorie</h2>
          <button type="button" className="btn btn-secondary" onClick={() => setCategoryForm(emptyCategory())}>
            Aggiungi categoria
          </button>
        </div>

        {categoryForm && (
          <form className="admin-inline-form" onSubmit={handleCategorySubmit}>
            <div className="admin-form-grid">
              <label>
                Nome (IT) *
                <input
                  value={categoryForm.name_it}
                  onChange={(e) => setCategoryForm({ ...categoryForm, name_it: e.target.value })}
                  required
                />
              </label>
              <label>
                Nome (EN)
                <input
                  value={categoryForm.name_en}
                  onChange={(e) => setCategoryForm({ ...categoryForm, name_en: e.target.value })}
                />
              </label>
              <label>
                Sezione
                <select
                  value={categoryForm.section}
                  onChange={(e) => setCategoryForm({
                    ...categoryForm,
                    section: e.target.value as AdminCategory['section'],
                  })}
                >
                  <option value="workwear">Abbigliamento da lavoro</option>
                  <option value="professional">Professionale</option>
                </select>
              </label>
            </div>
            <div className="admin-inline-form-actions">
              <button type="submit" className="btn btn-primary" disabled={saveCategory.isPending}>
                {categoryForm.id ? 'Salva categoria' : 'Crea categoria'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setCategoryForm(null)}>Annulla</button>
            </div>
          </form>
        )}

        {loadingCategories ? (
          <p>Caricamento categorie…</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Nome (IT)</th>
                  <th>Sezione</th>
                  <th>Genitore</th>
                  <th>Prodotti</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {categories.map((cat) => (
                  <tr key={cat.id}>
                    <td><strong>{cat.name_it}</strong><br /><span className="admin-muted">{cat.slug}</span></td>
                    <td>{cat.section === 'workwear' ? 'Abbigliamento da lavoro' : 'Professionale'}</td>
                    <td>{cat.parent_name || '—'}</td>
                    <td>{cat.product_count ?? 0}</td>
                    <td className="admin-actions">
                      <button type="button" className="admin-link" onClick={() => setCategoryForm(cat)}>Modifica</button>
                      <button
                        type="button"
                        className="admin-link admin-link-danger"
                        onClick={() => {
                          if (!cat.id || !window.confirm(`Eliminare la categoria "${cat.name_it}"?`)) return
                          removeCategory.mutate(cat.id)
                        }}
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
      </section>
      )}

      {catalogTab === 'brands' && (
      <section className="admin-card admin-catalog-section">
        <div className="admin-section-header">
          <h2>Marche</h2>
          <button type="button" className="btn btn-secondary" onClick={() => setBrandForm(emptyBrand())}>
            Aggiungi marca
          </button>
        </div>

        {brandForm && (
          <form className="admin-inline-form" onSubmit={handleBrandSubmit}>
            <div className="admin-form-grid">
              <label>
                Nome marca *
                <input
                  value={brandForm.name}
                  onChange={(e) => setBrandForm({ ...brandForm, name: e.target.value })}
                  required
                />
              </label>
            </div>
            <div className="admin-inline-form-actions">
              <button type="submit" className="btn btn-primary" disabled={saveBrand.isPending}>
                {brandForm.id ? 'Salva marca' : 'Crea marca'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setBrandForm(null)}>Annulla</button>
            </div>
          </form>
        )}

        {loadingBrands ? (
          <p>Caricamento marche…</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Prodotti</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {brands.length === 0 ? (
                  <tr><td colSpan={3} className="admin-empty">Nessuna marca ancora.</td></tr>
                ) : brands.map((brand) => (
                  <tr key={brand.id}>
                    <td><strong>{brand.name}</strong></td>
                    <td>{brand.product_count ?? 0}</td>
                    <td className="admin-actions">
                      <button type="button" className="admin-link" onClick={() => setBrandForm(brand)}>Modifica</button>
                      <button
                        type="button"
                        className="admin-link admin-link-danger"
                        onClick={() => {
                          if (!brand.id || !window.confirm(`Eliminare la marca "${brand.name}"?`)) return
                          removeBrand.mutate(brand.id)
                        }}
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
      </section>
      )}

      {catalogTab === 'colors' && (
      <section className="admin-card admin-catalog-section">
        <div className="admin-section-header">
          <h2>Colori</h2>
          <button type="button" className="btn btn-secondary" onClick={() => setColorForm(emptyColor())}>
            Aggiungi colore
          </button>
        </div>

        {colorForm && (
          <form className="admin-inline-form" onSubmit={handleColorSubmit}>
            <div className="admin-form-grid">
              <label>
                  Nome colore *
                <input
                  value={colorForm.name}
                  onChange={(e) => setColorForm({ ...colorForm, name: e.target.value })}
                  required
                />
              </label>
            </div>
            <div className="admin-inline-form-actions">
              <button type="submit" className="btn btn-primary" disabled={saveColor.isPending}>
                {colorForm.id ? 'Salva colore' : 'Crea colore'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setColorForm(null)}>Annulla</button>
            </div>
          </form>
        )}

        {loadingColors ? (
          <p>Caricamento colori…</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Varianti</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {colors.length === 0 ? (
                  <tr><td colSpan={3} className="admin-empty">Nessun colore ancora.</td></tr>
                ) : colors.map((color) => (
                  <tr key={color.id}>
                    <td><strong>{color.name}</strong></td>
                    <td>{color.variant_count ?? 0}</td>
                    <td className="admin-actions">
                      <button type="button" className="admin-link" onClick={() => setColorForm(color)}>Modifica</button>
                      <button
                        type="button"
                        className="admin-link admin-link-danger"
                        onClick={() => {
                          if (!color.id || !window.confirm(`Eliminare il colore "${color.name}"?`)) return
                          removeColor.mutate(color.id)
                        }}
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
      </section>
      )}
    </div>
  )
}
