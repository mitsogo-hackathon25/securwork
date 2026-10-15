import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import ProductCard from '../components/ProductCard'
import SectionHeader from '../components/SectionHeader'
import CategoryCard from '../components/CategoryCard'
import Newsletter from '../components/Newsletter'
import TrustBadges from '../components/TrustBadges'
import { OrganizationSchema } from '../components/SeoSchema'
import { IconQuality, IconService, IconShield, IconTruck } from '../components/Icons'
import { SITE_LOGO_URL } from '../constants/branding'
import {
  fetchBestsellers,
  fetchCategories,
  fetchFeatured,
  fetchNewArrivals,
} from '../api/store'
import './HomePage.css'

const whyIcons = [IconShield, IconQuality, IconService, IconTruck]
const whyKeys = ['whySafety', 'whyQuality', 'whyService', 'whyDelivery'] as const

const industryKeys = ['industryConstruction', 'industryManufacturing', 'industryHealthcare', 'industryFood', 'industryLogistics'] as const

const WORKWEAR_HOME_SLUGS = ['t-shirt', 'polo', 'pantaloni-da-lavoro', 'scarpe-da-lavoro']
const PROFESSIONAL_HOME_SLUGS = ['linea-chef', 'divise-professionali']

const heroHighlightKeys = ['heroHighlight1', 'heroHighlight2', 'heroHighlight3'] as const
const heroStatKeys = ['heroStat1', 'heroStat2', 'heroStat3'] as const

export default function HomePage() {
  const { t, i18n } = useTranslation()

  const { data: featured = [] } = useQuery({ queryKey: ['featured'], queryFn: fetchFeatured })
  const { data: newArrivals = [] } = useQuery({ queryKey: ['newArrivals'], queryFn: fetchNewArrivals })
  const { data: bestsellers = [] } = useQuery({ queryKey: ['bestsellers'], queryFn: fetchBestsellers })
  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: fetchCategories })

  const workwear = categories.find((c) => c.section === 'workwear')
  const professional = categories.find((c) => c.section === 'professional')

  const workwearHomeCards = workwear?.children?.filter((c) => WORKWEAR_HOME_SLUGS.includes(c.slug)) ?? []
  const professionalHomeCards = professional?.children?.filter((c) => PROFESSIONAL_HOME_SLUGS.includes(c.slug)) ?? []

  const hasProductShowcase = featured.length > 0 || newArrivals.length > 0 || bestsellers.length > 0

  return (
    <>
      <Helmet>
        <title>SecurWork — {t('home.heroTitle')}</title>
        <meta name="description" content={t('home.heroSubtitle')} />
        <meta property="og:title" content={`SecurWork — ${t('home.heroTitle')}`} />
        <meta property="og:description" content={t('home.heroSubtitle')} />
        <meta property="og:type" content="website" />
        <html lang={i18n.language} />
      </Helmet>
      <OrganizationSchema />

      <div className="home-page">
      <section className="hero">
        <div className="hero-backdrop" aria-hidden="true">
          <div className="hero-grid-lines" />
          <div className="hero-glow" />
        </div>
        <div className="container hero-layout">
          <div className="hero-copy animate-in">
            <span className="hero-eyebrow">{t('home.heroEyebrow')}</span>
            <h1>{t('home.heroTitle')}</h1>
            <p className="hero-lead">{t('home.heroSubtitle')}</p>
            <div className="hero-cta">
              <Link to="/shop" className="btn btn-primary btn-lg">{t('cta.shopNow')}</Link>
              <Link to="/contact" className="btn btn-hero-secondary">{t('home.heroContactCta')}</Link>
            </div>
          </div>
          <aside className="hero-panel animate-in" aria-label={t('home.heroPanelLabel')}>
            <div className="hero-panel-inner">
              <img src={SITE_LOGO_URL} alt="" className="hero-panel-logo" width={140} height={48} />
              <p className="hero-panel-tagline">{t('home.heroPanelTagline')}</p>
              <ul className="hero-panel-list">
                {heroHighlightKeys.map((key) => (
                  <li key={key}>{t(`home.${key}`)}</li>
                ))}
              </ul>
            </div>
          </aside>
        </div>
        <div className="hero-stats">
          <div className="container hero-stats-grid">
            {heroStatKeys.map((key) => (
              <div key={key} className="hero-stat">
                <span className="hero-stat-value">{t(`home.${key}Value`)}</span>
                <span className="hero-stat-label">{t(`home.${key}Label`)}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <TrustBadges />

      <section className="section home-why">
        <div className="container">
          <div className="home-section-intro">
            <span className="home-section-eyebrow">{t('home.whyEyebrow')}</span>
            <h2>{t('home.whyTitle')}</h2>
            <p>{t('home.whySubtitle')}</p>
          </div>
          <div className="why-grid">
            {whyKeys.map((key, i) => {
              const Icon = whyIcons[i]
              return (
                <article key={key} className="why-card">
                  <div className="why-icon"><Icon size={28} /></div>
                  <h3>{t(`home.${key}`)}</h3>
                  <p>{t(`home.${key}Desc`)}</p>
                </article>
              )
            })}
          </div>
        </div>
      </section>

      <section className="section section-alt home-categories">
        <div className="container">
          <SectionHeader
            title={t('home.categoriesTitle')}
            subtitle={t('home.categoriesSubtitle')}
            linkTo="/shop"
            linkLabel={t('cta.viewProducts')}
          />
          <div className="hero-categories">
            {workwear && <CategoryCard category={workwear} variant="hero" />}
            {professional && <CategoryCard category={professional} variant="hero" />}
          </div>
          {(workwearHomeCards.length > 0 || professionalHomeCards.length > 0) && (
            <div className="home-subcategories">
              {workwearHomeCards.length > 0 && (
                <div className="home-category-block">
                  <h3 className="home-category-block-title">{t('nav.workwear')}</h3>
                  <div className="subcategory-grid">
                    {workwearHomeCards.map((cat) => (
                      <CategoryCard key={cat.id} category={cat} variant="compact" />
                    ))}
                  </div>
                </div>
              )}
              {professionalHomeCards.length > 0 && (
                <div className="home-category-block">
                  <h3 className="home-category-block-title">{t('nav.professional')}</h3>
                  <div className="subcategory-grid">
                    {professionalHomeCards.map((cat) => (
                      <CategoryCard key={cat.id} category={cat} variant="compact" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {hasProductShowcase && (
        <section className="section home-catalog">
          <div className="container">
            <SectionHeader
              title={t('home.catalogTitle')}
              subtitle={t('home.catalogSubtitle')}
              linkTo="/shop"
              linkLabel={t('cta.viewProducts')}
            />

            {featured.length > 0 && (
              <div className="home-catalog-block">
                <SectionHeader title={t('home.featured')} linkTo="/shop" linkLabel={t('cta.viewProducts')} />
                <div className="grid-products grid-products--home">
                  {featured.slice(0, 4).map((p) => <ProductCard key={p.id} product={p} />)}
                </div>
              </div>
            )}

            {(newArrivals.length > 0 || bestsellers.length > 0) && (
              <div className="home-catalog-duo">
                {newArrivals.length > 0 && (
                  <div className="home-catalog-column">
                    <SectionHeader title={t('home.newArrivals')} linkTo="/shop" linkLabel={t('cta.viewProducts')} />
                    <div className="grid-products grid-products--stack">
                      {newArrivals.slice(0, 3).map((p) => <ProductCard key={p.id} product={p} />)}
                    </div>
                  </div>
                )}
                {bestsellers.length > 0 && (
                  <div className="home-catalog-column">
                    <SectionHeader title={t('home.bestsellers')} linkTo="/shop" linkLabel={t('cta.viewProducts')} />
                    <div className="grid-products grid-products--stack">
                      {bestsellers.slice(0, 3).map((p) => <ProductCard key={p.id} product={p} />)}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      )}

      <section className="home-custom-cta">
        <div className="container home-custom-cta-inner">
          <div>
            <span className="home-section-eyebrow home-section-eyebrow--light">{t('home.customEyebrow')}</span>
            <h2>{t('home.customCtaTitle')}</h2>
            <p>{t('home.customCtaSubtitle')}</p>
          </div>
          <Link to="/shop" className="btn btn-primary btn-lg">{t('home.customCtaButton')}</Link>
        </div>
      </section>

      <section className="section section-alt home-industries">
        <div className="container">
          <div className="home-section-intro">
            <span className="home-section-eyebrow">{t('home.industryEyebrow')}</span>
            <h2>{t('home.industryTitle')}</h2>
            <p>{t('home.industrySubtitle')}</p>
          </div>
          <div className="industry-grid">
            {industryKeys.map((key, index) => (
              <Link key={key} to="/shop" className="industry-card">
                <span className="industry-card-index">{String(index + 1).padStart(2, '0')}</span>
                <h3>{t(`home.${key}`)}</h3>
                <p>{t(`home.${key}Desc`)}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="promo-banner">
        <div className="container promo-banner-inner">
          <div>
            <h2>{t('home.promoTitle')}</h2>
            <p>{t('home.promoSubtitle')}</p>
          </div>
          <Link to="/shop?on_sale=true" className="btn btn-promo">{t('nav.promotions')}</Link>
        </div>
      </section>

      <Newsletter />
      </div>
    </>
  )
}
