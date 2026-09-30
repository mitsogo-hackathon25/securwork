import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Helmet } from 'react-helmet-async'

export default function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <>
      <Helmet><title>{t('notFound.title')} — SecurWork</title></Helmet>
      <div className="container section" style={{ textAlign: 'center', padding: '4rem 1rem' }}>
        <h1>{t('notFound.title')}</h1>
        <p>{t('notFound.message')}</p>
        <Link to="/" className="btn btn-primary" style={{ marginTop: '1.5rem' }}>
          {t('notFound.backHome')}
        </Link>
      </div>
    </>
  )
}
