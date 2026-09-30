import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import './Newsletter.css'

export default function Newsletter() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (email.trim()) {
      setSubmitted(true)
      setEmail('')
    }
  }

  return (
    <section className="newsletter-section" aria-labelledby="newsletter-title">
      <div className="container newsletter-inner">
        <div className="newsletter-copy">
          <h2 id="newsletter-title">{t('footer.newsletter')}</h2>
          <p>{t('home.newsletterSubtitle')}</p>
        </div>
        {submitted ? (
          <p className="newsletter-success">{t('home.newsletterSuccess')}</p>
        ) : (
          <form className="newsletter-form" onSubmit={handleSubmit}>
            <label htmlFor="newsletter-email" className="sr-only">{t('footer.newsletterPlaceholder')}</label>
            <input
              id="newsletter-email"
              type="email"
              required
              placeholder={t('footer.newsletterPlaceholder')}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <button type="submit" className="btn btn-primary">{t('home.newsletterCta')}</button>
          </form>
        )}
        <p className="newsletter-placeholder">{t('home.newsletterPlaceholderNote')}</p>
      </div>
    </section>
  )
}
