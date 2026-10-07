import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAdminProduct,
  deleteProductImage,
  fetchAdminCategories,
  fetchAdminProduct,
  removeProductMockup,
  setPrimaryImage,
  updateAdminProduct,
  uploadProductImage,
  uploadProductMockup,
} from '../../api/admin'
import type { AdminProduct, AdminProductVariant } from '../../api/types'
import './Admin.css'

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
})

export default function AdminProductFormPage() {
  const { id } = useParams()
  const isNew = id === 'new'
  const productId = isNew ? null : Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<AdminProduct>(emptyProduct())
  const [langTab, setLangTab] = useState<'it' | 'en'>('it')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const { data: categories = [] } = useQuery({
    queryKey: ['admin-categories'],
    queryFn: fetchAdminCategories,
  })

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
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
      if (isNew) navigate(`/admin/products/${saved.id}`)
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

  const addVariant = () => {
    setForm((prev) => ({ ...prev, variants: [...prev.variants, emptyVariant()] }))
  }

  const removeVariant = (index: number) => {
    setForm((prev) => ({
      ...prev,
      variants: prev.variants.filter((_, i) => i !== index),
    }))
  }

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
      await saveMutation.mutateAsync(payload)
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Could not save product.'
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !productId) return
    await uploadProductImage(productId, file, !form.images?.length)
    queryClient.invalidateQueries({ queryKey: ['admin-product', productId] })
    e.target.value = ''
  }

  const handleDeleteImage = async (imageId: number) => {
    if (!productId || !window.confirm('Delete this image?')) return
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
    if (!productId || !window.confirm('Remove mockup image?')) return
    await removeProductMockup(productId)
    setForm((prev) => ({ ...prev, mockup_front: null }))
    queryClient.invalidateQueries({ queryKey: ['admin-product', productId] })
  }

  if (!isNew && isLoading) return <p>Loading product…</p>

  const lang = langTab

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <Link to="/admin/products" className="admin-back">← Back to products</Link>
          <h1>{isNew ? 'Add product' : 'Edit product'}</h1>
        </div>
      </div>

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      <form className="admin-form" onSubmit={handleSubmit}>
        <section className="admin-card">
          <h2>Basic info</h2>
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
              Slug
              <input
                value={form.slug}
                onChange={(e) => updateField('slug', e.target.value)}
                placeholder="auto-generated if empty"
              />
            </label>
            <label>
              Brand
              <input
                value={form.brand || ''}
                onChange={(e) => updateField('brand', e.target.value)}
                placeholder="e.g. ISACCO, U-Power"
              />
            </label>
          </div>
          <div className="admin-checkbox-grid">
            <label><input type="checkbox" checked={form.is_active} onChange={(e) => updateField('is_active', e.target.checked)} /> Active</label>
            <label><input type="checkbox" checked={form.is_featured} onChange={(e) => updateField('is_featured', e.target.checked)} /> Featured</label>
            <label><input type="checkbox" checked={form.is_new_arrival} onChange={(e) => updateField('is_new_arrival', e.target.checked)} /> New arrival</label>
            <label><input type="checkbox" checked={form.is_bestseller} onChange={(e) => updateField('is_bestseller', e.target.checked)} /> Bestseller</label>
          </div>
        </section>

        <section className="admin-card">
          <h2>Categories</h2>
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
              Name ({lang}) *
              <input
                value={form[`name_${lang}`]}
                onChange={(e) => updateField(`name_${lang}` as keyof AdminProduct, e.target.value)}
                required={lang === 'it'}
              />
            </label>
            <label className="full-width">
              Short description ({lang})
              <textarea
                rows={2}
                value={form[`short_description_${lang}`]}
                onChange={(e) => updateField(`short_description_${lang}` as keyof AdminProduct, e.target.value)}
              />
            </label>
            <label className="full-width">
              Description ({lang})
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
            <h2>Variants — price &amp; stock</h2>
            <button type="button" className="btn btn-secondary" onClick={addVariant}>Add variant</button>
          </div>
          <div className="admin-table-wrap">
            <table className="admin-table admin-variant-table">
              <thead>
                <tr>
                  <th>SKU *</th>
                  <th>Size</th>
                  <th>Color</th>
                  <th>Price *</th>
                  <th>Sale price</th>
                  <th>Stock *</th>
                  <th>Active</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {form.variants.map((variant, index) => (
                  <tr key={variant.id ?? `new-${index}`}>
                    <td><input value={variant.sku} onChange={(e) => updateVariant(index, 'sku', e.target.value)} required /></td>
                    <td><input value={variant.size} onChange={(e) => updateVariant(index, 'size', e.target.value)} /></td>
                    <td><input value={variant.color} onChange={(e) => updateVariant(index, 'color', e.target.value)} /></td>
                    <td><input type="number" step="0.01" min="0" value={variant.price} onChange={(e) => updateVariant(index, 'price', e.target.value)} required /></td>
                    <td><input type="number" step="0.01" min="0" value={variant.sale_price ?? ''} onChange={(e) => updateVariant(index, 'sale_price', e.target.value || null)} /></td>
                    <td><input type="number" min="0" value={variant.stock_quantity} onChange={(e) => updateVariant(index, 'stock_quantity', Number(e.target.value))} required /></td>
                    <td><input type="checkbox" checked={variant.is_active} onChange={(e) => updateVariant(index, 'is_active', e.target.checked)} /></td>
                    <td>
                      {form.variants.length > 1 && (
                        <button type="button" className="admin-link admin-link-danger" onClick={() => removeVariant(index)}>Remove</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="admin-card">
          <h2>Logo customization</h2>
          <p className="admin-hint">
            Enable this to let customers upload a logo and position it on the product page.
            If no mockup image is set, the primary product photo is used.
          </p>
          <div className="admin-checkbox-grid">
            <label>
              <input
                type="checkbox"
                checked={form.allows_customization ?? false}
                onChange={(e) => updateField('allows_customization', e.target.checked)}
              />
              Allow logo customization
            </label>
          </div>
          <label>
            Customization fee (EUR)
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.customization_fee ?? '0.00'}
              onChange={(e) => updateField('customization_fee', e.target.value)}
              disabled={!form.allows_customization}
            />
          </label>
          {!isNew && form.allows_customization && (
            <div className="admin-mockup">
              {form.mockup_front ? (
                <div className="admin-image-card">
                  <img src={form.mockup_front} alt="Mockup front" />
                  <div className="admin-image-actions">
                    <button type="button" className="admin-link-danger" onClick={handleRemoveMockup}>
                      Remove mockup
                    </button>
                  </div>
                </div>
              ) : (
                <p className="admin-hint">No mockup uploaded — primary product image will be used.</p>
              )}
              <label className="admin-upload">
                <span className="btn btn-secondary">
                  {form.mockup_front ? 'Replace mockup' : 'Upload mockup image'}
                </span>
                <input type="file" accept="image/*" onChange={handleMockupUpload} />
              </label>
            </div>
          )}
        </section>

        {!isNew && (
          <section className="admin-card">
            <h2>Images</h2>
            <div className="admin-images">
              {(form.images ?? []).map((img) => (
                <div key={img.id} className="admin-image-card">
                  <img src={img.image} alt={img.alt_text || ''} />
                  {img.is_primary && <span className="admin-badge admin-badge-success">Primary</span>}
                  <div className="admin-image-actions">
                    {!img.is_primary && (
                      <button type="button" onClick={() => handleSetPrimary(img.id)}>Set primary</button>
                    )}
                    <button type="button" className="admin-link-danger" onClick={() => handleDeleteImage(img.id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
            <label className="admin-upload">
              <span className="btn btn-secondary">Upload image</span>
              <input type="file" accept="image/*" onChange={handleImageUpload} />
            </label>
          </section>
        )}

        <div className="admin-form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : isNew ? 'Create product' : 'Save changes'}
          </button>
          {isNew && <p className="admin-hint">You can upload images after creating the product.</p>}
        </div>
      </form>
    </div>
  )
}
