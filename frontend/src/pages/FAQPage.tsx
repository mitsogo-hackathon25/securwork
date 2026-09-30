import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import { fetchFAQ } from '../api/store'

export default function FAQPage() {
  const { t } = useTranslation()
  const { data: faqs = [], isLoading } = useQuery({ queryKey: ['faq'], queryFn: fetchFAQ })

  return (
    <>
      <Helmet><title>{t('nav.faq')} — SecurWork</title></Helmet>

      <div className="container section">
        <h1 className="section-title">{t('nav.faq')}</h1>

        {isLoading ? (
          <p>{t('common.loading')}</p>
        ) : (
          <div className="faq-list">
            {faqs.map((faq) => (
              <details key={faq.id} className="faq-item">
                <summary>{faq.question}</summary>
                <p>{faq.answer}</p>
              </details>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
