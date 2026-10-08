import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAdminCoupon,
  fetchAdminCoupon,
  updateAdminCoupon,
} from '../../api/admin'
import type { AdminCoupon } from '../../api/types'
import './Admin.css'

const emptyCoupon = (): AdminCoupon => ({
  code: '',
  discount_percent: '10.00',
  discount_amount: null,
  min_order_amount: '0.00',
  max_uses: 100,
  is_active: true,
  valid_from: null,
  valid_until: null,
})

const toLocalDatetime = (value: string | null) => {
  if (!value) return ''
  const date = new Date(value)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const fromLocalDatetime = (value: string) => (value ? new Date(value).toISOString() : null)

export default function AdminCouponFormPage() {
  const { id } = useParams()
  const isNew = !id || id === 'new'
  const couponId = isNew ? null : Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<AdminCoupon>(emptyCoupon())
  const [discountType, setDiscountType] = useState<'percent' | 'amount'>('percent')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const { data: coupon, isLoading } = useQuery({
    queryKey: ['admin-coupon', couponId],
    queryFn: () => fetchAdminCoupon(couponId!),
    enabled: !!couponId,
  })

  useEffect(() => {
    if (!coupon) return
    setForm(coupon)
    setDiscountType(coupon.discount_percent ? 'percent' : 'amount')
  }, [coupon])

  const saveMutation = useMutation({
    mutationFn: (payload: AdminCoupon) =>
      isNew ? createAdminCoupon(payload) : updateAdminCoupon(couponId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-coupons'] })
      navigate('/admin/coupons')
    },
  })

  const updateField = <K extends keyof AdminCoupon>(key: K, value: AdminCoupon[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const payload: AdminCoupon = {
        ...form,
        code: form.code.trim().toUpperCase(),
        discount_percent: discountType === 'percent' ? form.discount_percent : null,
        discount_amount: discountType === 'amount' ? form.discount_amount : null,
        max_uses: form.max_uses && form.max_uses > 0 ? form.max_uses : null,
      }
      await saveMutation.mutateAsync(payload)
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? JSON.stringify((err as { response?: { data?: unknown } }).response?.data)
        : 'Impossibile salvare il coupon.'
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  if (!isNew && isLoading) return <p>Caricamento coupon…</p>

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <Link to="/admin/coupons" className="admin-back">← Torna ai coupon</Link>
          <h1>{isNew ? 'Aggiungi coupon' : 'Modifica coupon'}</h1>
        </div>
      </div>

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      <form className="admin-form" onSubmit={handleSubmit}>
        <section className="admin-card">
          <h2>Dettagli coupon</h2>
          <div className="admin-form-grid">
            <label>
              Codice *
              <input
                value={form.code}
                onChange={(e) => updateField('code', e.target.value.toUpperCase())}
                placeholder="es. ESTATE20"
                required
              />
            </label>
            <label className="admin-checkbox-inline full-width">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => updateField('is_active', e.target.checked)}
              />
              <span>Attivo (i clienti possono usare questo codice)</span>
            </label>
          </div>
        </section>

        <section className="admin-card">
          <h2>Sconto</h2>
          <div className="admin-tabs">
            <button
              type="button"
              className={discountType === 'percent' ? 'active' : ''}
              onClick={() => setDiscountType('percent')}
            >
              Percentuale
            </button>
            <button
              type="button"
              className={discountType === 'amount' ? 'active' : ''}
              onClick={() => setDiscountType('amount')}
            >
              Importo fisso
            </button>
          </div>
          <div className="admin-form-grid">
            {discountType === 'percent' ? (
              <label>
                Sconto (%)
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="100"
                  value={form.discount_percent ?? ''}
                  onChange={(e) => updateField('discount_percent', e.target.value)}
                  required
                />
              </label>
            ) : (
              <label>
                Sconto (EUR)
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={form.discount_amount ?? ''}
                  onChange={(e) => updateField('discount_amount', e.target.value)}
                  required
                />
              </label>
            )}
            <label>
              Ordine minimo (EUR)
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.min_order_amount}
                onChange={(e) => updateField('min_order_amount', e.target.value)}
              />
            </label>
          </div>
        </section>

        <section className="admin-card">
          <h2>Limite utilizzi</h2>
          <p className="admin-hint">
            Imposta quante volte i clienti possono usare questo coupon su tutti gli ordini.
            Lascia vuoto per utilizzi illimitati.
          </p>
          <div className="admin-form-grid">
            <label>
              Utilizzi massimi
              <input
                type="number"
                min="1"
                value={form.max_uses ?? ''}
                onChange={(e) => updateField('max_uses', e.target.value ? Number(e.target.value) : null)}
                placeholder="Illimitati"
              />
            </label>
            {!isNew && (
              <label>
                Volte usato (sola lettura)
                <input value={form.used_count ?? 0} readOnly disabled />
              </label>
            )}
          </div>
        </section>

        <section className="admin-card">
          <h2>Periodo di validità</h2>
          <p className="admin-hint">Opzionale. Lascia vuoto per nessuna restrizione di data.</p>
          <div className="admin-form-grid">
            <label>
              Valido dal
              <input
                type="datetime-local"
                value={toLocalDatetime(form.valid_from)}
                onChange={(e) => updateField('valid_from', fromLocalDatetime(e.target.value))}
              />
            </label>
            <label>
              Valido fino al
              <input
                type="datetime-local"
                value={toLocalDatetime(form.valid_until)}
                onChange={(e) => updateField('valid_until', fromLocalDatetime(e.target.value))}
              />
            </label>
          </div>
        </section>

        <div className="admin-form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Salvataggio…' : isNew ? 'Crea coupon' : 'Salva modifiche'}
          </button>
        </div>
      </form>
    </div>
  )
}
