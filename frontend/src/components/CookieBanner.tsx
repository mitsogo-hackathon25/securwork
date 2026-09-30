import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import './CookieBanner.css'

const CONSENT_KEY = 'securwork-cookie-consent'

export default function CookieBanner() {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem(CONSENT_KEY)) {
      setVisible(true)
    }
  }, [])

  const accept = () => {
    localStorage.setItem(CONSENT_KEY, 'accepted')
    setVisible(false)
  }

  const decline = () => {
    localStorage.setItem(CONSENT_KEY, 'declined')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div className="cookie-banner" role="dialog" aria-label={t('cookies.bannerTitle')}>
      <div className="container cookie-banner-inner">
        <p className="cookie-banner-text">
          {t('cookies.bannerText')}{' '}
          <Link to="/pages/cookies">{t('footer.cookies')}</Link>
        </p>
        <div className="cookie-banner-actions">
          <button type="button" className="btn btn-decline" onClick={decline}>
            {t('cookies.decline')}
          </button>
          <button type="button" className="btn btn-accept" onClick={accept}>
            {t('cookies.accept')}
          </button>
        </div>
      </div>
    </div>
  )
}
