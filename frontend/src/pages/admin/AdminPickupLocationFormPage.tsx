import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAdminPickupLocation,
  fetchAdminPickupLocation,
  updateAdminPickupLocation,
} from '../../api/admin'
import type { AdminPickupLocation } from '../../api/types'
import './Admin.css'

const emptyLocation = (): AdminPickupLocation => ({
  id: 0,
  name: '',
  address: '',
  city: '',
  postcode: '',
  country: 'IT',
  phone: '',
  notes: '',
  is_active: true,
  sort_order: 0,
})

export default function AdminPickupLocationFormPage() {
  const { id } = useParams()
  const { t } = useTranslation()
  const isNew = !id || id === 'new'
  const locationId = isNew ? null : Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<AdminPickupLocation>(emptyLocation())
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const { data: location, isLoading } = useQuery({
    queryKey: ['admin-pickup-location', locationId],
    queryFn: () => fetchAdminPickupLocation(locationId!),
    enabled: !!locationId,
  })

  useEffect(() => {
    if (location) setForm(location)
  }, [location])

  const saveMutation = useMutation({
    mutationFn: (payload: Partial<AdminPickupLocation>) =>
      isNew ? createAdminPickupLocation(payload) : updateAdminPickupLocation(locationId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-pickup-locations'] })
      navigate('/admin/pickup-locations')
    },
  })

  const updateField = <K extends keyof AdminPickupLocation>(key: K, value: AdminPickupLocation[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const { id: _id, created_at, updated_at, ...payload } = form
      await saveMutation.mutateAsync(payload)
    } catch {
      setError(t('adminPickup.saveError'))
    } finally {
      setSaving(false)
    }
  }

  if (!isNew && isLoading) return <p>{t('adminCommon.loading')}</p>

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <Link to="/admin/pickup-locations" className="admin-back">{t('adminPickup.back')}</Link>
          <h1>{isNew ? t('adminPickup.add') : t('adminPickup.edit')}</h1>
        </div>
      </div>

      {error && <p className="admin-alert admin-alert-error">{error}</p>}

      <form className="admin-card admin-form" onSubmit={handleSubmit}>
        <div className="admin-form-grid">
          <label className="full-width">
            {t('adminPickup.fieldName')}
            <input required value={form.name} onChange={(e) => updateField('name', e.target.value)} />
          </label>
          <label className="full-width">
            {t('adminPickup.fieldAddress')}
            <input required value={form.address} onChange={(e) => updateField('address', e.target.value)} />
          </label>
          <label>
            {t('adminPickup.fieldCity')}
            <input required value={form.city} onChange={(e) => updateField('city', e.target.value)} />
          </label>
          <label>
            {t('adminPickup.fieldPostcode')}
            <input required value={form.postcode} onChange={(e) => updateField('postcode', e.target.value)} />
          </label>
          <label>
            {t('adminPickup.fieldCountry')}
            <input required maxLength={2} value={form.country} onChange={(e) => updateField('country', e.target.value.toUpperCase())} />
          </label>
          <label>
            {t('adminPickup.fieldPhone')}
            <input value={form.phone} onChange={(e) => updateField('phone', e.target.value)} />
          </label>
          <label>
            {t('adminPickup.fieldSortOrder')}
            <input type="number" min={0} value={form.sort_order} onChange={(e) => updateField('sort_order', Number(e.target.value))} />
          </label>
          <label className="full-width">
            {t('adminPickup.fieldNotes')}
            <textarea rows={3} value={form.notes} onChange={(e) => updateField('notes', e.target.value)} />
          </label>
          <label className="same-address-check">
            <input type="checkbox" checked={form.is_active} onChange={(e) => updateField('is_active', e.target.checked)} />
            {t('adminCommon.active')}
          </label>
        </div>
        <div className="admin-form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? t('adminCommon.loading') : t('adminCommon.save')}
          </button>
        </div>
      </form>
    </div>
  )
}
