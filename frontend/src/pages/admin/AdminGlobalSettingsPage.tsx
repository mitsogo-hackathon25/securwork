import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  adjustProductPricesByBrand,
  fetchAdminBrands,
  fetchAdminGlobalSettings,
  updateAdminGlobalSettings,
} from '../../api/admin'
import { formatApiError } from '../../utils/formatApiError'
import './Admin.css'

const NO_BRAND_VALUE = '__none__'

export default function AdminGlobalSettingsPage() {
  const queryClient = useQueryClient()
  const [percent, setPercent] = useState('10')
  const [direction, setDirection] = useState<'increase' | 'decrease'>('increase')
  const [brand, setBrand] = useState('')
  const [priceMessage, setPriceMessage] = useState('')
  const [priceError, setPriceError] = useState('')

  const [notificationEmails, setNotificationEmails] = useState('')
  const [mailMessage, setMailMessage] = useState('')
  const [mailError, setMailError] = useState('')

  const { data: globalSettings, isLoading: settingsLoading } = useQuery({
    queryKey: ['admin-global-settings'],
    queryFn: fetchAdminGlobalSettings,
  })

  const { data: brands = [], isLoading: brandsLoading } = useQuery({
    queryKey: ['admin-brands'],
    queryFn: fetchAdminBrands,
  })

  const brandOptions = useMemo(
    () => [...brands]
      .filter((b) => b.is_active)
      .sort((a, b) => a.name.localeCompare(b.name, 'it', { sensitivity: 'base' })),
    [brands],
  )

  useEffect(() => {
    if (globalSettings) {
      setNotificationEmails(globalSettings.order_notification_emails ?? '')
    }
  }, [globalSettings])

  const priceMutation = useMutation({
    mutationFn: adjustProductPricesByBrand,
    onSuccess: (result) => {
      setPriceMessage(result.detail)
      setPriceError('')
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    },
    onError: (err: unknown) => {
      setPriceMessage('')
      setPriceError(formatApiError(err, 'Impossibile aggiornare i prezzi.'))
    },
  })

  const mailMutation = useMutation({
    mutationFn: updateAdminGlobalSettings,
    onSuccess: () => {
      setMailMessage('Impostazioni email salvate.')
      setMailError('')
      queryClient.invalidateQueries({ queryKey: ['admin-global-settings'] })
    },
    onError: (err: unknown) => {
      setMailMessage('')
      setMailError(formatApiError(err, 'Impossibile salvare le impostazioni email.'))
    },
  })

  const selectedBrandLabel = brand === NO_BRAND_VALUE
    ? 'Senza marca'
    : brandOptions.find((b) => b.name === brand)?.name ?? brand

  const handlePriceSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setPriceMessage('')
    setPriceError('')

    if (!brand) {
      setPriceError('Seleziona una marca.')
      return
    }

    const value = parseFloat(percent.replace(',', '.'))
    if (!Number.isFinite(value) || value <= 0) {
      setPriceError('Inserisci una percentuale valida maggiore di zero.')
      return
    }

    const signed = direction === 'decrease' ? -value : value
    if (!window.confirm(
      `Applicare ${direction === 'decrease' ? 'una riduzione' : 'un aumento'} del ${value}% `
        + `ai prezzi della marca «${selectedBrandLabel}»?`,
    )) {
      return
    }

    priceMutation.mutate({ percent: signed, brand })
  }

  const handleMailSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setMailMessage('')
    setMailError('')
    mailMutation.mutate({ order_notification_emails: notificationEmails })
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>Impostazioni globali</h1>
          <p>Prezzi per marca e notifiche email per i nuovi ordini.</p>
        </div>
      </div>

      <section className="admin-card">
        <h2>Notifiche nuovo ordine</h2>
        <p className="admin-hint">
          Inserisci uno o più indirizzi email (uno per riga o separati da virgola). Riceveranno un messaggio
          solo quando arriva un nuovo ordine. L&apos;invio usa SMTP (es. Brevo): configura{' '}
          <code>EMAIL_HOST</code>, <code>EMAIL_HOST_USER</code> e <code>EMAIL_HOST_PASSWORD</code> nel file{' '}
          <code>.env</code> del server.
        </p>

        {settingsLoading ? (
          <p>Caricamento…</p>
        ) : (
          <>
            {mailMessage && <p className="admin-alert admin-alert-success">{mailMessage}</p>}
            {mailError && <p className="admin-alert admin-alert-error">{mailError}</p>}

            <form className="admin-form" onSubmit={handleMailSubmit}>
              <label>
                Email notifiche ordini
                <textarea
                  rows={5}
                  value={notificationEmails}
                  onChange={(e) => setNotificationEmails(e.target.value)}
                  placeholder="ordini@esempio.it&#10;magazzino@esempio.it"
                />
              </label>
              <p className="admin-hint">
                Se lasci vuoto, viene usato <code>ORDER_ADMIN_EMAIL</code> dal file <code>.env</code>.
              </p>
              <div className="admin-inline-form-actions">
                <button type="submit" className="btn btn-primary" disabled={mailMutation.isPending}>
                  {mailMutation.isPending ? 'Salvataggio…' : 'Salva email'}
                </button>
              </div>
            </form>
          </>
        )}
      </section>

      <section className="admin-card">
        <h2>Aggiornamento prezzi per marca</h2>
        <p className="admin-hint">
          Modifica il prezzo base e il prezzo scontato delle varianti dei prodotti con la marca selezionata
          (campo marca sul prodotto). L&apos;operazione non può essere annullata automaticamente: esporta il
          catalogo prima se vuoi un backup.
        </p>

        {priceMessage && <p className="admin-alert admin-alert-success">{priceMessage}</p>}
        {priceError && <p className="admin-alert admin-alert-error">{priceError}</p>}

        <form className="admin-inline-form" onSubmit={handlePriceSubmit}>
          <div className="admin-price-direction">
            <span className="admin-price-direction-label">Azione</span>
            <div className="admin-tabs">
              <button
                type="button"
                className={direction === 'increase' ? 'active' : ''}
                onClick={() => setDirection('increase')}
              >
                Aumenta (%)
              </button>
              <button
                type="button"
                className={direction === 'decrease' ? 'active' : ''}
                onClick={() => setDirection('decrease')}
              >
                Riduci (%)
              </button>
            </div>
          </div>

          <div className="admin-form-grid">
            <label>
              Marca *
              <select
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                required
                disabled={brandsLoading}
              >
                <option value="">— Seleziona marca —</option>
                {brandOptions.map((b) => (
                  <option key={b.id} value={b.name}>{b.name}</option>
                ))}
                <option value={NO_BRAND_VALUE}>Senza marca</option>
              </select>
            </label>
            <label>
              Percentuale
              <input
                type="number"
                min="0.01"
                max="99.99"
                step="0.01"
                value={percent}
                onChange={(e) => setPercent(e.target.value)}
                required
              />
            </label>
          </div>

          <p className="admin-hint">
            {brand
              ? direction === 'increase'
                ? `I prezzi delle varianti «${selectedBrandLabel}» aumenteranno del ${percent || '0'}%.`
                : `I prezzi delle varianti «${selectedBrandLabel}» diminuiranno del ${percent || '0'}%.`
              : 'Seleziona una marca per vedere l&apos;anteprima dell&apos;operazione.'}
          </p>

          <div className="admin-inline-form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={priceMutation.isPending || !brand}
            >
              {priceMutation.isPending
                ? 'Aggiornamento…'
                : direction === 'increase'
                  ? 'Aumenta prezzi marca'
                  : 'Riduci prezzi marca'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
