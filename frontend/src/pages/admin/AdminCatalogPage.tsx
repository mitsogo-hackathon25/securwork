import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  bulkDeleteAdminCategories,
  createAdminBrand,
  createAdminCategory,
  createAdminColor,
  deleteAdminBrand,
  deleteAdminCategory,
  deleteAdminColor,
  fetchAdminBrands,
  fetchAdminCategories,
  fetchAdminCategoryList,
  fetchAdminColors,
  removeAdminCategoryImage,
  updateAdminBrand,
  updateAdminCategory,
  updateAdminColor,
  uploadAdminCategoryImage,
} from '../../api/admin'
import type { AdminBrand, AdminCategory, AdminCategoryOption, AdminColor } from '../../api/types'
import { formatApiError } from '../../utils/formatApiError'
import { CATEGORY_IMAGE_DIMENSIONS_HINT } from '../../constants/homeImages'
import './Admin.css'

const emptyCategory = (): AdminCategory => ({
  section: 'workwear',
  visible_in_workwear: true,
  visible_in_professional: false,
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
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [catalogTab, setCatalogTab] = useState<CatalogTab>('categories')
  const [categoryForm, setCategoryForm] = useState<AdminCategory | null>(null)
  const [brandForm, setBrandForm] = useState<AdminBrand | null>(null)
  const [colorForm, setColorForm] = useState<AdminColor | null>(null)
  const [error, setError] = useState('')
  const [categoryImageBusy, setCategoryImageBusy] = useState(false)
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<Set<number>>(new Set())
  const [categoryDeleteModal, setCategoryDeleteModal] = useState<
    | null
    | { mode: 'single' | 'bulk'; ids: number[]; productCount: number }
  >(null)
  const [reassignTargetId, setReassignTargetId] = useState<number | ''>('')

  const switchTab = (tab: CatalogTab) => {
    setCatalogTab(tab)
    setError('')
    setCategoryForm(null)
    setBrandForm(null)
    setColorForm(null)
    setSelectedCategoryIds(new Set())
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

  const { data: categoryOptions = [] } = useQuery({
    queryKey: ['admin-categories', 'options'],
    queryFn: fetchAdminCategories,
    enabled: categoryDeleteModal !== null,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin-category-list'] })
    queryClient.invalidateQueries({ queryKey: ['admin-categories'] })
    queryClient.invalidateQueries({ queryKey: ['admin-brands'] })
    queryClient.invalidateQueries({ queryKey: ['admin-colors'] })
    queryClient.invalidateQueries({ queryKey: ['product-brands'] })
    queryClient.invalidateQueries({ queryKey: ['product-colors'] })
    queryClient.invalidateQueries({ queryKey: ['categories'] })
    queryClient.invalidateQueries({ queryKey: ['siteConfig'] })
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
    mutationFn: (vars: { id: number; reassignTo?: number }) =>
      deleteAdminCategory(vars.id, vars.reassignTo),
    onSuccess: () => {
      setCategoryDeleteModal(null)
      setReassignTargetId('')
      setSelectedCategoryIds(new Set())
      invalidate()
    },
    onError: (err: unknown) => {
      setError(formatApiError(err, 'Impossibile eliminare la categoria.'))
    },
  })

  const bulkRemoveCategories = useMutation({
    mutationFn: (vars: { ids: number[]; reassignTo?: number }) =>
      bulkDeleteAdminCategories(vars.ids, vars.reassignTo),
    onSuccess: (res) => {
      setCategoryDeleteModal(null)
      setReassignTargetId('')
      setSelectedCategoryIds((prev) => {
        const next = new Set(prev)
        for (const id of res.deleted) {
          next.delete(id)
        }
        return next
      })
      invalidate()
      if (res.failed.length > 0) {
        const lines = res.failed.map((f) => `#${f.id}: ${f.detail}`).join('\n')
        setError(
          res.deleted.length > 0
            ? `Eliminate ${res.deleted.length} categorie. Non eliminate:\n${lines}`
            : `Nessuna categoria eliminata:\n${lines}`,
        )
      } else {
        setError('')
      }
    },
    onError: (err: unknown) => {
      setError(formatApiError(err, 'Eliminazione multipla non riuscita.'))
    },
  })

  const categoryRowsWithId = categories.filter((c): c is typeof c & { id: number } => typeof c.id === 'number')
  const selectableCategoryIds = categoryRowsWithId.map((c) => c.id)
  const allCategoriesSelected =
    selectableCategoryIds.length > 0
    && selectableCategoryIds.every((id) => selectedCategoryIds.has(id))
  const someCategoriesSelected = selectableCategoryIds.some((id) => selectedCategoryIds.has(id))

  const toggleSelectAllCategories = () => {
    if (allCategoriesSelected) {
      setSelectedCategoryIds(new Set())
    } else {
      setSelectedCategoryIds(new Set(selectableCategoryIds))
    }
  }

  const toggleCategoryRow = (id: number) => {
    setSelectedCategoryIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleBulkDeleteCategories = () => {
    const ids = [...selectedCategoryIds]
    if (ids.length === 0) return
    const labels = categoryRowsWithId
      .filter((c) => ids.includes(c.id))
      .map((c) => c.name_it)
      .slice(0, 5)
    const preview = labels.length < ids.length
      ? `${labels.join(', ')}… (+${ids.length - labels.length})`
      : labels.join(', ')
    const totalProducts = categoryRowsWithId
      .filter((c) => ids.includes(c.id))
      .reduce((sum, c) => sum + (c.product_count ?? 0), 0)
    const needsReassign = totalProducts > 0
    if (needsReassign) {
      setReassignTargetId('')
      setCategoryDeleteModal({
        mode: 'bulk',
        ids,
        productCount: totalProducts,
      })
      return
    }
    if (!window.confirm(`Eliminare ${ids.length} categorie selezionate?\n\n${preview}`)) return
    bulkRemoveCategories.mutate({ ids })
  }

  const categoryReassignOptions = categoryOptions.filter(
    (o: AdminCategoryOption) =>
      !categoryDeleteModal?.ids.includes(o.id),
  )

  const confirmCategoryDeleteWithReassign = () => {
    if (!categoryDeleteModal) return
    if (categoryDeleteModal.productCount === 0) {
      setError('')
      if (categoryDeleteModal.mode === 'single') {
        removeCategory.mutate({ id: categoryDeleteModal.ids[0] })
      } else {
        bulkRemoveCategories.mutate({ ids: categoryDeleteModal.ids })
      }
      return
    }
    if (reassignTargetId === '') {
      setError('Seleziona la categoria in cui spostare i prodotti.')
      return
    }
    const tid = Number(reassignTargetId)
    if (!Number.isFinite(tid)) {
      setError('Destinazione non valida.')
      return
    }
    setError('')
    if (categoryDeleteModal.mode === 'single') {
      removeCategory.mutate({ id: categoryDeleteModal.ids[0], reassignTo: tid })
    } else {
      bulkRemoveCategories.mutate({ ids: categoryDeleteModal.ids, reassignTo: tid })
    }
  }

  const handleSingleCategoryDelete = async (cat: AdminCategory & { id: number }) => {
    if (!window.confirm(`Eliminare la categoria "${cat.name_it}"?`)) return
    setError('')
    if ((cat.product_count ?? 0) > 0) {
      setReassignTargetId('')
      setCategoryDeleteModal({
        mode: 'single',
        ids: [cat.id],
        productCount: cat.product_count ?? 0,
      })
      return
    }
    try {
      await deleteAdminCategory(cat.id)
      setSelectedCategoryIds(new Set())
      invalidate()
    } catch (err: unknown) {
      const res = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { status?: number; data?: { code?: string; product_count?: number } } }).response
        : undefined
      if (res?.status === 400 && res.data?.code === 'category_has_products') {
        setReassignTargetId('')
        setCategoryDeleteModal({
          mode: 'single',
          ids: [cat.id],
          productCount: res.data.product_count ?? 0,
        })
        return
      }
      setError(formatApiError(err, 'Impossibile eliminare la categoria.'))
    }
  }

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

  const handleCategoryImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !categoryForm?.id) return
    setCategoryImageBusy(true)
    setError('')
    try {
      const updated = await uploadAdminCategoryImage(categoryForm.id, file)
      setCategoryForm(updated)
      invalidate()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Caricamento immagine non riuscito.')
    } finally {
      setCategoryImageBusy(false)
    }
  }

  const handleCategoryImageRemove = async () => {
    if (!categoryForm?.id) return
    if (!window.confirm('Rimuovere l\'immagine di questa categoria?')) return
    setCategoryImageBusy(true)
    setError('')
    try {
      const updated = await removeAdminCategoryImage(categoryForm.id)
      setCategoryForm(updated)
      invalidate()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Rimozione immagine non riuscita.')
    } finally {
      setCategoryImageBusy(false)
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>{t('adminCatalog.title')}</h1>
          <p>{t('adminCatalog.subtitle')}</p>
        </div>
      </div>

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      {categoryDeleteModal && (
        <div
          className="admin-import-brand-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="category-delete-modal-title"
        >
          <div className="admin-card admin-import-brand-dialog">
            <h3 id="category-delete-modal-title">
              {categoryDeleteModal.mode === 'single' ? 'Elimina categoria' : 'Elimina categorie selezionate'}
            </h3>
            <p className="admin-hint">
              {categoryDeleteModal.productCount > 0
                ? (
                  <>
                    {categoryDeleteModal.mode === 'single'
                      ? `Questa categoria ha ${categoryDeleteModal.productCount} prodott${categoryDeleteModal.productCount === 1 ? 'o' : 'i'}. `
                      : `${categoryDeleteModal.productCount} prodotti in totale nelle categorie selezionate (stima da conteggio). `}
                    Scegli una categoria di destinazione: i prodotti verranno collegati anche a quella, poi la categoria
                    verrà rimossa dall’assegnazione.
                  </>
                )
                : 'Conferma eliminazione.'}
            </p>
            <label className="full-width">
              Sposta prodotti verso *
              <select
                value={reassignTargetId === '' ? '' : String(reassignTargetId)}
                onChange={(e) => {
                  const v = e.target.value
                  setReassignTargetId(v === '' ? '' : Number(v))
                }}
                required={categoryDeleteModal.productCount > 0}
              >
                <option value="">— Seleziona categoria —</option>
                {categoryReassignOptions
                  .slice()
                  .sort((a, b) => a.name.localeCompare(b.name, 'it', { sensitivity: 'base' }))
                  .map((opt) => {
                    const sec =
                      opt.section === 'professional' ? 'Prof.' : 'Lavoro'
                    return (
                      <option key={opt.id} value={opt.id}>
                        {opt.name} ({opt.slug}) [{sec}]
                      </option>
                    )
                  })}
              </select>
            </label>
            <p className="admin-hint">
              Non è possibile eliminare categorie principali che contengono ancora sottocategorie; in quel caso spostale o
              eliminale prima.
            </p>
            <div className="admin-inline-form-actions" style={{ marginTop: '1rem' }}>
              <button
                type="button"
                className="btn btn-primary"
                disabled={removeCategory.isPending || bulkRemoveCategories.isPending}
                onClick={confirmCategoryDeleteWithReassign}
              >
                {categoryDeleteModal.productCount > 0 ? 'Sposta ed elimina' : 'Elimina'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={removeCategory.isPending || bulkRemoveCategories.isPending}
                onClick={() => {
                  setCategoryDeleteModal(null)
                  setReassignTargetId('')
                }}
              >
                Annulla
              </button>
            </div>
          </div>
        </div>
      )}

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
          <div className="admin-section-header-actions">
            {selectedCategoryIds.size > 0 && (
              <button
                type="button"
                className="btn btn-secondary admin-btn-danger-outline"
                disabled={bulkRemoveCategories.isPending}
                onClick={handleBulkDeleteCategories}
              >
                Elimina selezionate ({selectedCategoryIds.size})
              </button>
            )}
            <button type="button" className="btn btn-secondary" onClick={() => setCategoryForm(emptyCategory())}>
              Aggiungi categoria
            </button>
          </div>
        </div>

        <p className="admin-hint">
          Immagine categoria (home e schede shop): dimensioni consigliate{' '}
          <strong>{CATEGORY_IMAGE_DIMENSIONS_HINT}</strong>.
          Carica l&apos;immagine dopo aver creato la categoria (Modifica → Immagine).
          Le categorie principali Workwear e Professionale compaiono in evidenza in homepage.
        </p>

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
              <div className="admin-category-section-checks">
                <span className="admin-category-section-checks-label">Sezioni catalogo</span>
                <label className="admin-category-section-check">
                  <input
                    type="checkbox"
                    checked={categoryForm.visible_in_workwear}
                    onChange={(e) =>
                      setCategoryForm({
                        ...categoryForm,
                        visible_in_workwear: e.target.checked,
                      })
                    }
                  />
                  Abbigliamento da lavoro
                </label>
                <label className="admin-category-section-check">
                  <input
                    type="checkbox"
                    checked={categoryForm.visible_in_professional}
                    onChange={(e) =>
                      setCategoryForm({
                        ...categoryForm,
                        visible_in_professional: e.target.checked,
                      })
                    }
                  />
                  Abbigliamento professionale
                </label>
                <p className="admin-hint admin-category-section-hint">
                  Spunta entrambe se la stessa categoria deve comparare sotto lavoro e professionale (es. Pantaloni).
                  Per i filtri dello shop serve almeno una sezione.
                </p>
              </div>
            </div>
            {categoryForm.id ? (
              <div className="admin-category-image-block">
                <p className="admin-hint">
                  Dimensioni consigliate:{' '}
                  <strong>{categoryForm.image_dimensions_hint || CATEGORY_IMAGE_DIMENSIONS_HINT}</strong>
                </p>
                {categoryForm.image && (
                  <img
                    src={categoryForm.image}
                    alt=""
                    className="admin-category-image-preview"
                  />
                )}
                <div className="admin-inline-form-actions">
                  <label className="btn btn-secondary">
                    {categoryImageBusy ? 'Caricamento…' : 'Carica immagine'}
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      hidden
                      disabled={categoryImageBusy}
                      onChange={handleCategoryImageUpload}
                    />
                  </label>
                  {categoryForm.image && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={categoryImageBusy}
                      onClick={handleCategoryImageRemove}
                    >
                      Rimuovi immagine
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <p className="admin-hint">Salva la categoria, poi potrai caricare l&apos;immagine.</p>
            )}
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
                  <th className="admin-table-col-check" scope="col">
                    <input
                      type="checkbox"
                      className="admin-table-checkbox"
                      checked={allCategoriesSelected}
                      ref={(el) => {
                        if (el) el.indeterminate = someCategoriesSelected && !allCategoriesSelected
                      }}
                      onChange={toggleSelectAllCategories}
                      aria-label="Seleziona tutte le categorie"
                    />
                  </th>
                  <th>Immagine</th>
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
                    <td className="admin-table-col-check">
                      {typeof cat.id === 'number' && (
                        <input
                          type="checkbox"
                          className="admin-table-checkbox"
                          checked={selectedCategoryIds.has(cat.id)}
                          onChange={() => toggleCategoryRow(cat.id)}
                          aria-label={`Seleziona ${cat.name_it}`}
                        />
                      )}
                    </td>
                    <td>
                      {cat.image ? (
                        <img src={cat.image} alt="" className="admin-table-thumb" />
                      ) : (
                        <span className="admin-muted">—</span>
                      )}
                    </td>
                    <td><strong>{cat.name_it}</strong><br /><span className="admin-muted">{cat.slug}</span></td>
                    <td>
                      {[
                        cat.visible_in_workwear !== false && 'Lavoro',
                        cat.visible_in_professional && 'Professionale',
                      ]
                        .filter(Boolean)
                        .join(', ') || (cat.section === 'workwear' ? 'Abbigliamento da lavoro' : 'Professionale')}
                    </td>
                    <td>{cat.parent_name || '—'}</td>
                    <td>{cat.product_count ?? 0}</td>
                    <td className="admin-actions">
                      <button type="button" className="admin-link" onClick={() => setCategoryForm(cat)}>Modifica</button>
                      <button
                        type="button"
                        className="admin-link admin-link-danger"
                        onClick={() => cat.id && handleSingleCategoryDelete(cat)}
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
