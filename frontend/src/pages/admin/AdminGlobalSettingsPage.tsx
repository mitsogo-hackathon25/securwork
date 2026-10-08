import { useEffect, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {

  adjustAllProductPrices,

  fetchAdminGlobalSettings,

  updateAdminGlobalSettings,

} from '../../api/admin'

import { formatApiError } from '../../utils/formatApiError'

import './Admin.css'



export default function AdminGlobalSettingsPage() {

  const queryClient = useQueryClient()

  const [percent, setPercent] = useState('10')

  const [direction, setDirection] = useState<'increase' | 'decrease'>('increase')

  const [priceMessage, setPriceMessage] = useState('')

  const [priceError, setPriceError] = useState('')



  const [notificationEmails, setNotificationEmails] = useState('')

  const [mailMessage, setMailMessage] = useState('')

  const [mailError, setMailError] = useState('')



  const { data: globalSettings, isLoading: settingsLoading } = useQuery({

    queryKey: ['admin-global-settings'],

    queryFn: fetchAdminGlobalSettings,

  })



  useEffect(() => {

    if (globalSettings) {

      setNotificationEmails(globalSettings.order_notification_emails ?? '')

    }

  }, [globalSettings])



  const priceMutation = useMutation({

    mutationFn: adjustAllProductPrices,

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



  const handlePriceSubmit = (e: React.FormEvent) => {

    e.preventDefault()

    setPriceMessage('')

    setPriceError('')

    const value = parseFloat(percent.replace(',', '.'))

    if (!Number.isFinite(value) || value <= 0) {

      setPriceError('Inserisci una percentuale valida maggiore di zero.')

      return

    }

    const signed = direction === 'decrease' ? -value : value

    if (!window.confirm(

      `Applicare ${direction === 'decrease' ? 'una riduzione' : 'un aumento'} del ${value}% a tutte le varianti prodotto?`,

    )) {

      return

    }

    priceMutation.mutate(signed)

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

          <p>Prezzi in blocco e notifiche email per i nuovi ordini.</p>

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

        <h2>Aggiornamento massivo prezzi</h2>

        <p className="admin-hint">

          Modifica il prezzo base e il prezzo scontato di ogni variante. L&apos;operazione non può essere

          annullata automaticamente: esporta il catalogo prima se vuoi un backup.

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

            {direction === 'increase'

              ? `I prezzi di tutte le varianti aumenteranno del ${percent || '0'}%.`

              : `I prezzi di tutte le varianti diminuiranno del ${percent || '0'}%.`}

          </p>

          <div className="admin-inline-form-actions">

            <button type="submit" className="btn btn-primary" disabled={priceMutation.isPending}>

              {priceMutation.isPending

                ? 'Aggiornamento…'

                : direction === 'increase'

                  ? 'Aumenta tutti i prezzi'

                  : 'Riduci tutti i prezzi'}

            </button>

          </div>

        </form>

      </section>

    </div>

  )

}

