import { useParams, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import Breadcrumbs from '../components/Breadcrumbs'
import { fetchPage } from '../api/store'
import './CmsPage.css'

export default function CmsPage() {
  const { pageType: paramType } = useParams<{ pageType: string }>()
  const location = useLocation()
  const pageType = paramType || (location.pathname === '/about' ? 'about' : '')
  const { t } = useTranslation()

  const { data: page, isLoading, error } = useQuery({
    queryKey: ['page', pageType],
    queryFn: () => fetchPage(pageType!),
    enabled: !!pageType,
  })

  if (isLoading) return <div className="container section"><p>{t('common.loading')}</p></div>
  if (error || !page) return <div className="container section"><p>{t('common.error')}</p></div>

  return (
    <>
      <Helmet>
        <title>{page.meta_title || page.title} — SecurWork</title>
        {page.meta_description && <meta name="description" content={page.meta_description} />}
      </Helmet>

      <div className="container section cms-page">
        <Breadcrumbs items={[{ label: page.title }]} />
        <h1>{page.title}</h1>
        <article className="cms-content" dangerouslySetInnerHTML={{ __html: page.content }} />
      </div>
    </>
  )
}
