import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAdminProduct,
  deleteProductImage,
  fetchAdminBrands,
  fetchAdminCategories,
  fetchAdminColors,
  fetchAdminProduct,
  removeProductMockup,
  setPrimaryImage,
  updateAdminProduct,
  uploadProductImage,
  uploadProductMockup,
} from '../../api/admin'
import type { AdminProduct, AdminProductVariant } from '../../api/types'
import { CLOTHING_SIZES } from '../../constants/clothingSizes'
import { PRODUCT_COLORS } from '../../constants/productColors'
import { formatApiError } from '../../utils/formatApiError'
import './Admin.css'

type SizeGroup = {
  size: string
  indices: number[]
}

const suggestVariantSku = (productSku: string, size: string, color: string) => {
  const parts = [productSku.trim()]
  if (size) parts.push(size)
  if (color) parts.push(color.slice(0, 3).toUpperCase())
  return parts.filter(Boolean).join('-')
}

const getSizeGroups = (variants: AdminProductVariant[]): SizeGroup[] => {
  const groups: SizeGroup[] = []
  const seen = new Set<string>()

  variants.forEach((variant, index) => {
    const key = variant.size
    if (seen.has(key)) {
      groups.find((group) => group.size === key)?.indices.push(index)
      return
    }
    seen.add(key)
    groups.push({ size: key, indices: [index] })
  })

  return groups
}

const emptyVariant = (): AdminProductVariant => ({
  sku: '',
  size: '',
  color: '',
  price: '0.00',
  sale_price: null,
  stock_quantity: 0,
  is_active: true,
})

const emptyProduct = (): AdminProduct => ({
  slug: '',
  sku: '',
  brand: '',
  name_it: '',
  name_en: '',
  short_description_it: '',
  short_description_en: '',
  description_it: '',
  description_en: '',
  meta_title_it: '',
  meta_title_en: '',
  meta_description_it: '',
  meta_description_en: '',
  category_ids: [],
  variants: [emptyVariant()],
  is_active: true,
  is_featured: false,
  is_new_arrival: false,
  is_bestseller: false,
  allows_customization: false,
  customization_fee: '0.00',
  embroidery_chest_enabled: false,
  embroidery_chest_fee: '0.00',
  embroidery_large_enabled: false,
  embroidery_large_fee: '0.00',
  dtf_chest_enabled: false,
  dtf_chest_fee: '0.00',
  dtf_large_enabled: false,
  dtf_large_fee: '0.00',
})

export default function AdminProductFormPage() {
  const { id } = useParams()
  const isNew = !id || id === 'new'
  const productId = isNew ? null : Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<AdminProduct>(emptyProduct())
  const [langTab, setLangTab] = useState<'it' | 'en'>('it')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [imageError, setImageError] = useState('')
  const [pendingImages, setPendingImages] = useState<{ file: File; preview: string }[]>([])

  const { data: categories = [] } = useQuery({
    queryKey: ['admin-categories'],
    queryFn: fetchAdminCategories,
  })

  const { data: brands = [] } = useQuery({
    queryKey: ['admin-brands'],
    queryFn: fetchAdminBrands,
  })

  const { data: adminColors = [] } = useQuery({
    queryKey: ['admin-colors'],
    queryFn: fetchAdminColors,
  })

  const colorOptions = useMemo(() => {
    const names = new Set(
      adminColors.filter((color) => color.is_active).map((color) => color.name),
    )
    if (names.size === 0) {
      PRODUCT_COLORS.forEach((color) => names.add(color))
    }
    form.variants.forEach((variant) => {
      if (variant.color) names.add(variant.color)
    })
    return [...names].sort((a, b) => a.localeCompare(b))
  }, [adminColors, form.variants])

  const { data: product, isLoading } = useQuery({
    queryKey: ['admin-product', productId],
    queryFn: () => fetchAdminProduct(productId!),
    enabled: !!productId,
  })

  useEffect(() => {
    if (product) setForm(product)
  }, [product])

  const saveMutation = useMutation({
    mutationFn: (payload: AdminProduct) =>
      isNew ? createAdminProduct(payload) : updateAdminProduct(productId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    },
  })

  const updateField = <K extends keyof AdminProduct>(key: K, value: AdminProduct[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const updateVariant = (index: number, field: keyof AdminProductVariant, value: string | number | boolean | null) => {
    setForm((prev) => {
      const variants = [...prev.variants]
      variants[index] = { ...variants[index], [field]: value }
      return { ...prev, variants }
    })
  }

  const addSizeGroup = () => {
    setForm((prev) => {
      const usedSizes = new Set(prev.variants.map((variant) => variant.size))
      const nextSize = CLOTHING_SIZES.find((size) => !usedSizes.has(size)) || ''
      const color = colorOptions[0] || ''
      const template = prev.variants[0]
      const variant: AdminProductVariant = {
        ...emptyVariant(),
        size: nextSize,
        color,
        price: template?.price ?? '0.00',
        sale_price: template?.sale_price ?? null,
        sku: suggestVariantSku(prev.sku, nextSize, color),
      }
      return { ...prev, variants: [...prev.variants, variant] }
    })
  }

  const addColorToSize = (size: string) => {
    setForm((prev) => {
      const siblings = prev.variants.filter((variant) => variant.size === size)
      const usedColors = new Set(siblings.map((variant) => variant.color))
      const nextColor = colorOptions.find((color) => !usedColors.has(color)) || ''
      const template = siblings[0]
      const variant: AdminProductVariant = {
        ...emptyVariant(),
        size,
        color: nextColor,
        price: template?.price ?? '0.00',
        sale_price: template?.sale_price ?? null,
        sku: suggestVariantSku(prev.sku, size, nextColor),
      }
      return { ...prev, variants: [...prev.variants, variant] }
    })
  }

  const updateSizeForGroup = (currentSize: string, nextSize: string) => {
    setForm((prev) => ({
      ...prev,
      variants: prev.variants.map((variant) => (
        variant.size === currentSize
          ? {
            ...variant,
            size: nextSize,
            sku: variant.sku || suggestVariantSku(prev.sku, nextSize, variant.color),
          }
          : variant
      )),
    }))
  }

  const removeVariant = (index: number) => {
    setForm((prev) => ({
      ...prev,
      variants: prev.variants.length > 1
        ? prev.variants.filter((_, i) => i !== index)
        : prev.variants,
    }))
  }

  const removeSizeGroup = (size: string) => {
    setForm((prev) => {
      const nextVariants = prev.variants.filter((variant) => variant.size !== size)
      return {
        ...prev,
        variants: nextVariants.length > 0 ? nextVariants : [emptyVariant()],
      }
    })
  }

  const sizeGroups = getSizeGroups(form.variants)

  const toggleCategory = (categoryId: number) => {
    setForm((prev) => {
      const ids = prev.category_ids.includes(categoryId)
        ? prev.category_ids.filter((id) => id !== categoryId)
        : [...prev.category_ids, categoryId]
      return { ...prev, category_ids: ids }
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setImageError('')
    setSaving(true)
    try {
      const payload = {
        ...form,
        variants: form.variants.map((v) => ({
          ...v,
          id: v.id ?? null,
          sale_price: v.sale_price || null,
        })),
      }
      const saved = await saveMutation.mutateAsync(payload)
      if (isNew && pendingImages.length > 0 && saved.id) {
        let hasImages = false
        for (const item of pendingImages) {
          await uploadProductImage(saved.id, item.file, !hasImages)
          hasImages = true
        }
        pendingImages.forEach((item) => URL.revokeObjectURL(item.preview))
        setPendingImages([])
      }
      if (isNew && saved.id) navigate(`/admin/products/${saved.id}`)
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Impossibile salvare il prodotto.'
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    e.target.value = ''
    if (!files.length) return
    setImageError('')

    if (!productId) {
      setPendingImages((prev) => [
        ...prev,
        ...files.map((file) => ({ file, preview: URL.createObjectURL(file) })),
      ])
      return
    }

    let hasImages = (form.images?.length ?? 0) > 0
    try {
      for (const file of files) {
        await uploadProductImage(productId, file, !hasImages)
        hasImages = true
      }
      queryClient.invalidateQueries({ queryKey: ['admin-product', productId] })
    } catch (err: unknown) {
      setImageError(formatApiError(err, 'Impossibile caricare l\'immagine.'))
    }
  }

  const removePendingImage = (index: number) => {
    setPendingImages((prev) => {
      const target = prev[index]
      if (target) URL.revokeObjectURL(target.preview)
      return prev.filter((_, i) => i !== index)
    })
  }

  const handleDeleteImage = async (imageId: number) => {
    if (!productId || !window.confirm('Eliminare questa immagine?')) return
    await deleteProductImage(productId, imageId)
    queryClient.invalidateQueries({ queryKey: ['admin-product', productId] })
  }

  const handleSetPrimary = async (imageId: number) => {
    if (!productId) return
    await setPrimaryImage(productId, imageId)
    queryClient.invalidateQueries({ queryKey: ['admin-product', productId] })
  }

  const handleMockupUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !productId) return
    const updated = await uploadProductMockup(productId, file)
    setForm((prev) => ({ ...prev, mockup_front: updated.mockup_front }))
    queryClient.invalidateQueries({ queryKey: ['admin-product', productId] })
    e.target.value = ''
  }

  const handleRemoveMockup = async () => {
    if (!productId || !window.confirm('Rimuovere l\'immagine mockup?')) return
    await removeProductMockup(productId)
    setForm((prev) => ({ ...prev, mockup_front: null }))
    queryClient.invalidateQueries({ queryKey: ['admin-product', productId] })
  }

  if (!isNew && isLoading) return <p>Caricamento prodotto…</p>

  const lang = langTab

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <Link to="/admin/products" className="admin-back">← Torna ai prodotti</Link>
          <h1>{isNew ? 'Aggiungi prodotto' : 'Modifica prodotto'}</h1>
        </div>
      </div>

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      <form className="admin-form" onSubmit={handleSubmit}>
        <section className="admin-card">
          <h2>Informazioni di base</h2>
          <div className="admin-form-grid">
            <label>
              SKU *
              <input
                value={form.sku}
                onChange={(e) => updateField('sku', e.target.value)}
                required
              />
            </label>
            <label>
              Marca
              <select
                value={form.brand || ''}
                onChange={(e) => updateField('brand', e.target.value)}
              >
                <option value="">— Nessuna marca —</option>
                {brands.filter((b) => b.is_active).map((brand) => (
                  <option key={brand.id} value={brand.name}>{brand.name}</option>
                ))}
                {form.brand && !brands.some((b) => b.name === form.brand) && (
                  <option value={form.brand}>{form.brand}</option>
                )}
              </select>
            </label>
          </div>
          <div className="admin-checkbox-grid">
            <label><input type="checkbox" checked={form.is_active} onChange={(e) => updateField('is_active', e.target.checked)} /> Attivo</label>
            <label><input type="checkbox" checked={form.is_featured} onChange={(e) => updateField('is_featured', e.target.checked)} /> In evidenza</label>
            <label><input type="checkbox" checked={form.is_new_arrival} onChange={(e) => updateField('is_new_arrival', e.target.checked)} /> Nuovo arrivo</label>
            <label><input type="checkbox" checked={form.is_bestseller} onChange={(e) => updateField('is_bestseller', e.target.checked)} /> Best seller</label>
          </div>
        </section>

        <section className="admin-card">
          <h2>Categorie</h2>
          <div className="admin-category-grid">
            {categories.map((cat) => (
              <label key={cat.id} className="admin-category-chip">
                <input
                  type="checkbox"
                  checked={form.category_ids.includes(cat.id)}
                  onChange={() => toggleCategory(cat.id)}
                />
                <span>{cat.name}</span>
              </label>
            ))}
          </div>
        </section>

        <section className="admin-card">
          <div className="admin-tabs">
            <button type="button" className={langTab === 'it' ? 'active' : ''} onClick={() => setLangTab('it')}>Italiano</button>
            <button type="button" className={langTab === 'en' ? 'active' : ''} onClick={() => setLangTab('en')}>English</button>
          </div>
          <div className="admin-form-grid">
            <label className="full-width">
              Nome ({lang}) *
              <input
                value={form[`name_${lang}`]}
                onChange={(e) => updateField(`name_${lang}` as keyof AdminProduct, e.target.value)}
                required={lang === 'it'}
              />
            </label>
            <label className="full-width">
              Descrizione breve ({lang})
              <textarea
                rows={2}
                value={form[`short_description_${lang}`]}
                onChange={(e) => updateField(`short_description_${lang}` as keyof AdminProduct, e.target.value)}
              />
            </label>
            <label className="full-width">
              Descrizione ({lang})
              <textarea
                rows={6}
                value={form[`description_${lang}`]}
                onChange={(e) => updateField(`description_${lang}` as keyof AdminProduct, e.target.value)}
              />
            </label>
            <label>
              Meta title ({lang})
              <input
                value={form[`meta_title_${lang}`]}
                onChange={(e) => updateField(`meta_title_${lang}` as keyof AdminProduct, e.target.value)}
              />
            </label>
            <label>
              Meta description ({lang})
              <textarea
                rows={2}
                value={form[`meta_description_${lang}`]}
                onChange={(e) => updateField(`meta_description_${lang}` as keyof AdminProduct, e.target.value)}
              />
            </label>
          </div>
        </section>

        <section className="admin-card">
          <div className="admin-section-header">
            <div>
              <h2>Varianti — taglie e colori</h2>
              <p className="admin-hint">Aggiungi una taglia, poi più colori per quella taglia (ogni colore ha SKU, prezzo e scorte propri).</p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={addSizeGroup}>Aggiungi taglia</button>
          </div>

          <div className="admin-variant-groups">
            {sizeGroups.map((group) => (
              <div key={`size-${group.size}-${group.indices[0]}`} className="admin-variant-group">
                <div className="admin-variant-group-header">
                  <label className="admin-variant-size-label">
                    Taglia
                    <select
                      value={group.size}
                      onChange={(e) => updateSizeForGroup(group.size, e.target.value)}
                    >
                      <option value="">— Nessuna taglia —</option>
                      {CLOTHING_SIZES.map((size) => (
                        <option key={size} value={size}>{size}</option>
                      ))}
                      {group.size && !CLOTHING_SIZES.includes(group.size as typeof CLOTHING_SIZES[number]) && (
                        <option value={group.size}>{group.size}</option>
                      )}
                    </select>
                  </label>
                  <div className="admin-variant-group-actions">
                    <button type="button" className="btn btn-secondary" onClick={() => addColorToSize(group.size)}>
                      Aggiungi colore
                    </button>
                    {sizeGroups.length > 1 && (
                      <button
                        type="button"
                        className="admin-link admin-link-danger"
                        onClick={() => removeSizeGroup(group.size)}
                      >
                        Rimuovi taglia
                      </button>
                    )}
                  </div>
                </div>

                <div className="admin-table-wrap">
                  <table className="admin-table admin-variant-table">
                    <thead>
                      <tr>
                        <th>Colore *</th>
                        <th>SKU *</th>
                        <th>Prezzo *</th>
                        <th>Prezzo scontato</th>
                        <th>Scorte *</th>
                        <th>Attivo</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {group.indices.map((index) => {
                        const variant = form.variants[index]
                        return (
                          <tr key={variant.id ?? `new-${index}`}>
                            <td>
                              <select
                                value={variant.color}
                                onChange={(e) => {
                                  const color = e.target.value
                                  setForm((prev) => {
                                    const variants = [...prev.variants]
                                    const current = variants[index]
                                    variants[index] = {
                                      ...current,
                                      color,
                                      sku: current.sku || suggestVariantSku(prev.sku, current.size, color),
                                    }
                                    return { ...prev, variants }
                                  })
                                }}
                                required
                              >
                                <option value="">— Seleziona —</option>
                                {colorOptions.map((color) => (
                                  <option key={color} value={color}>{color}</option>
                                ))}
                                {variant.color && !colorOptions.includes(variant.color) && (
                                  <option value={variant.color}>{variant.color}</option>
                                )}
                              </select>
                            </td>
                            <td>
                              <input
                                value={variant.sku}
                                onChange={(e) => updateVariant(index, 'sku', e.target.value)}
                                required
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                value={variant.price}
                                onChange={(e) => updateVariant(index, 'price', e.target.value)}
                                required
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                value={variant.sale_price ?? ''}
                                onChange={(e) => updateVariant(index, 'sale_price', e.target.value || null)}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                min="0"
                                value={variant.stock_quantity}
                                onChange={(e) => updateVariant(index, 'stock_quantity', Number(e.target.value))}
                                required
                              />
                            </td>
                            <td>
                              <input
                                type="checkbox"
                                checked={variant.is_active}
                                onChange={(e) => updateVariant(index, 'is_active', e.target.checked)}
                              />
                            </td>
                            <td>
                              {group.indices.length > 1 && (
                                <button
                                  type="button"
                                  className="admin-link admin-link-danger"
                                  onClick={() => removeVariant(index)}
                                >
                                  Rimuovi
                                </button>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="admin-card">
          <h2>Personalizzazione logo</h2>
          <p className="admin-hint">
            Abilita uno o più metodi di personalizzazione con il relativo costo.
            Se non è impostata un&apos;immagine mockup, viene usata la foto principale del prodotto.
          </p>
          <div className="admin-method-grid">
            {([
              ['embroidery_chest_enabled', 'embroidery_chest_fee', 'Ricamo — lato cuore/petto'],
              ['embroidery_large_enabled', 'embroidery_large_fee', 'Ricamo grande'],
              ['dtf_chest_enabled', 'dtf_chest_fee', 'DTF — lato cuore/petto'],
              ['dtf_large_enabled', 'dtf_large_fee', 'DTF grande (formato A4)'],
            ] as const).map(([enabledKey, feeKey, label]) => (
              <div key={enabledKey} className="admin-method-row">
                <label className="admin-checkbox-inline">
                  <input
                    type="checkbox"
                    checked={Boolean(form[enabledKey])}
                    onChange={(e) => updateField(enabledKey, e.target.checked)}
                  />
                  <span>{label}</span>
                </label>
                <label>
                  Costo (EUR)
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form[feeKey] ?? '0.00'}
                    onChange={(e) => updateField(feeKey, e.target.value)}
                    disabled={!form[enabledKey]}
                  />
                </label>
              </div>
            ))}
          </div>
          {!isNew && (
            form.embroidery_chest_enabled
            || form.embroidery_large_enabled
            || form.dtf_chest_enabled
            || form.dtf_large_enabled
          ) ? (
            <div className="admin-mockup">
              {form.mockup_front ? (
                <div className="admin-image-card">
                  <img src={form.mockup_front} alt="Mockup fronte" />
                  <div className="admin-image-actions">
                    <button type="button" className="admin-link-danger" onClick={handleRemoveMockup}>
                      Rimuovi mockup
                    </button>
                  </div>
                </div>
              ) : (
                <p className="admin-hint">Nessun mockup caricato — verrà usata l&apos;immagine principale del prodotto.</p>
              )}
              <label className="admin-upload">
                <span className="btn btn-secondary">
                  {form.mockup_front ? 'Sostituisci mockup' : 'Carica immagine mockup'}
                </span>
                <input type="file" accept="image/*" onChange={handleMockupUpload} />
              </label>
            </div>
          ) : null}
        </section>

        <section className="admin-card">
          <h2>Immagini</h2>
          <p className="admin-hint">
            {isNew
              ? 'Seleziona le immagini ora: verranno caricate dopo la creazione del prodotto. La prima diventa principale.'
              : 'Carica tutte le immagini necessarie. La prima diventa l\'immagine principale.'}
          </p>
          <div className="admin-images">
            {(form.images ?? []).map((img) => (
              <div key={img.id} className="admin-image-card">
                <img src={img.image} alt={img.alt_text || ''} />
                {img.is_primary && <span className="admin-badge admin-badge-success">Principale</span>}
                <div className="admin-image-actions">
                  {!img.is_primary && (
                    <button type="button" onClick={() => handleSetPrimary(img.id)}>Imposta principale</button>
                  )}
                  <button type="button" className="admin-link-danger" onClick={() => handleDeleteImage(img.id)}>Elimina</button>
                </div>
              </div>
            ))}
            {pendingImages.map((item, index) => (
              <div key={`${item.file.name}-${index}`} className="admin-image-card">
                <img src={item.preview} alt={item.file.name} />
                <span className="admin-badge admin-badge-muted">In attesa</span>
                <div className="admin-image-actions">
                  <button type="button" className="admin-link-danger" onClick={() => removePendingImage(index)}>
                    Rimuovi
                  </button>
                </div>
              </div>
            ))}
          </div>
          <label className="admin-upload">
            <span className="btn btn-secondary">Carica immagini</span>
            <input type="file" accept="image/*" multiple onChange={handleImageUpload} />
          </label>
          {imageError && <p className="admin-hint admin-hint-error">{imageError}</p>}
        </section>

        <div className="admin-form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Salvataggio…' : isNew ? 'Crea prodotto' : 'Salva modifiche'}
          </button>
        </div>
      </form>
    </div>
  )
}
