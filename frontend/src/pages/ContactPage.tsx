import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import { fetchSiteConfig, sendContact } from '../api/store'
import './ContactPage.css'

function buildMapUrl(lat: string, lng: string) {
  const latNum = parseFloat(lat)
  const lngNum = parseFloat(lng)
  const delta = 0.015
  const bbox = `${lngNum - delta},${latNum - delta},${lngNum + delta},${latNum + delta}`
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${latNum},${lngNum}`
}

export default function ContactPage() {
  const { t } = useTranslation()
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { data: site } = useQuery({
    queryKey: ['siteConfig'],
    queryFn: fetchSiteConfig,
  })

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    const form = new FormData(e.currentTarget)
    const data: Record<string, string> = {}
    form.forEach((v, k) => { data[k] = v.toString() })
    try {
      await sendContact(data)
      setSent(true)
    } catch {
      setError(t('contact.error'))
    } finally {
      setLoading(false)
    }
  }

  const mapUrl = site ? buildMapUrl(site.map_lat, site.map_lng) : null

  return (
    <>
      <Helmet><title>{t('contact.title')} — SecurWork</title></Helmet>

      <div className="container section contact-page">
        <h1 className="section-title">{t('contact.title')}</h1>

        <div className="contact-layout">
          <div className="contact-info">
            <h2>{t('contact.infoTitle')}</h2>
            {site && (
              <div className="contact-details">
                <p><strong>{site.company_name}</strong></p>
                <p>{site.company_address}</p>
                <p>{site.company_city}</p>
                <p>{site.company_vat}</p>
                <p>
                  <a href={`tel:${site.company_phone.replace(/\s/g, '')}`}>{site.company_phone}</a>
                </p>
                <p>
                  <a href={`mailto:${site.contact_email}`}>{site.contact_email}</a>
                </p>
              </div>
            )}

            {mapUrl && (
              <div className="contact-map" aria-label={t('contact.mapLabel')}>
                <iframe
                  title={t('contact.mapLabel')}
                  src={mapUrl}
                  loading="lazy"
                />
              </div>
            )}
          </div>

          <div className="contact-form-section">
            <h2>{t('contact.formTitle')}</h2>
            {sent ? (
              <p className="contact-success">{t('contact.success')}</p>
            ) : (
              <>
                {error && <p className="contact-error">{error}</p>}
                <form onSubmit={handleSubmit} className="checkout-form">
                  <div className="contact-honeypot" aria-hidden="true">
                    <input name="website" tabIndex={-1} autoComplete="off" />
                  </div>
                  <div className="form-grid">
                    <input name="name" required placeholder={`${t('contact.name')} *`} className="full-width" />
                    <input name="email" type="email" required placeholder={`${t('contact.email')} *`} className="full-width" />
                    <input name="phone" placeholder={t('contact.phone')} className="full-width" />
                    <input name="subject" required placeholder={`${t('contact.subject')} *`} className="full-width" />
                    <textarea
                      name="message"
                      required
                      placeholder={`${t('contact.message')} *`}
                      rows={5}
                      className="full-width"
                      style={{ padding: '0.75rem', border: '1px solid var(--color-border)', borderRadius: 'var(--radius)', fontFamily: 'inherit' }}
                    />
                  </div>
                  <button type="submit" className="btn btn-primary" disabled={loading}>
                    {loading ? t('common.loading') : t('contact.send')}
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
