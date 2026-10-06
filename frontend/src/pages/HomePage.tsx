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
import {
  fetchBestsellers,
  fetchCategories,
  fetchFeatured,
  fetchNewArrivals,
  fetchProducts,
} from '../api/store'
import './HomePage.css'

const whyIcons = [IconShield, IconQuality, IconService, IconTruck]
const whyKeys = ['whySafety', 'whyQuality', 'whyService', 'whyDelivery'] as const

const industryKeys = ['industryConstruction', 'industryManufacturing', 'industryHealthcare', 'industryFood', 'industryLogistics'] as const

const WORKWEAR_HOME_SLUGS = ['t-shirt', 'polo', 'pantaloni-da-lavoro', 'scarpe-da-lavoro']
const PROFESSIONAL_HOME_SLUGS = ['linea-chef', 'divise-professionali']

export default function HomePage() {
  const { t, i18n } = useTranslation()

  const { data: featured = [] } = useQuery({ queryKey: ['featured'], queryFn: fetchFeatured })
  const { data: newArrivals = [] } = useQuery({ queryKey: ['newArrivals'], queryFn: fetchNewArrivals })
  const { data: bestsellers = [] } = useQuery({ queryKey: ['bestsellers'], queryFn: fetchBestsellers })
  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: fetchCategories })
  const { data: workwearProducts } = useQuery({
    queryKey: ['products', 'workwear'],
    queryFn: () => fetchProducts({ section: 'workwear' }),
  })
  const { data: professionalProducts } = useQuery({
    queryKey: ['products', 'professional'],
    queryFn: () => fetchProducts({ section: 'professional' }),
  })

  const workwear = categories.find((c) => c.section === 'workwear')
  const professional = categories.find((c) => c.section === 'professional')

  const workwearHomeCards = workwear?.children?.filter((c) => WORKWEAR_HOME_SLUGS.includes(c.slug)) ?? []
  const professionalHomeCards = professional?.children?.filter((c) => PROFESSIONAL_HOME_SLUGS.includes(c.slug)) ?? []

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

      {/* Hero */}
      <section className="hero animate-in">
        <div className="hero-pattern" aria-hidden="true" />
        <div className="container hero-content">
          <span className="hero-eyebrow">{t('home.heroEyebrow')}</span>
          <h1>{t('home.heroTitle')}</h1>
          <p>{t('home.heroSubtitle')}</p>
          <div className="hero-cta">
            <Link to="/shop" className="btn btn-primary">{t('cta.shopNow')}</Link>
            <Link to="/shop?section=workwear" className="btn btn-outline">{t('cta.discover')}</Link>
          </div>
        </div>
      </section>

      <TrustBadges />

      {/* Main categories */}
      <section className="section">
        <div className="container">
          <SectionHeader title={t('home.categoriesTitle')} subtitle={t('home.categoriesSubtitle')} linkTo="/shop" linkLabel={t('cta.viewProducts')} />
          <div className="hero-categories">
            {workwear && <CategoryCard category={workwear} variant="hero" />}
            {professional && <CategoryCard category={professional} variant="hero" />}
          </div>
          {workwearHomeCards.length > 0 && (
            <div className="home-category-block">
              <h3 className="home-category-block-title">{t('nav.workwear')}</h3>
              <div className="subcategory-grid subcategory-grid--workwear">
                {workwearHomeCards.map((cat) => (
                  <CategoryCard key={cat.id} category={cat} variant="compact" />
                ))}
              </div>
            </div>
          )}
          {professionalHomeCards.length > 0 && (
            <div className="home-category-block">
              <h3 className="home-category-block-title">{t('nav.professional')}</h3>
              <div className="subcategory-grid subcategory-grid--professional">
                {professionalHomeCards.map((cat) => (
                  <CategoryCard key={cat.id} category={cat} variant="compact" />
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Featured */}
      {featured.length > 0 && (
        <section className="section section-alt">
          <div className="container">
            <SectionHeader title={t('home.featured')} linkTo="/shop" linkLabel={t('cta.viewProducts')} />
            <div className="grid-products">
              {featured.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          </div>
        </section>
      )}

      {/* Workwear section */}
      {workwearProducts && workwearProducts.results.length > 0 && (
        <section className="section">
          <div className="container">
            <SectionHeader title={t('nav.workwear')} subtitle={t('home.workwearSubtitle')} linkTo="/shop?section=workwear" linkLabel={t('cta.discover')} />
            <div className="grid-products">
              {workwearProducts.results.slice(0, 4).map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          </div>
        </section>
      )}

      {/* Professional section */}
      {professionalProducts && professionalProducts.results.length > 0 && (
        <section className="section section-alt">
          <div className="container">
            <SectionHeader title={t('nav.professional')} subtitle={t('home.professionalSubtitle')} linkTo="/shop?section=professional" linkLabel={t('cta.discover')} />
            <div className="grid-products">
              {professionalProducts.results.slice(0, 2).map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          </div>
        </section>
      )}

      {/* New arrivals */}
      {newArrivals.length > 0 && (
        <section className="section">
          <div className="container">
            <SectionHeader title={t('home.newArrivals')} linkTo="/shop" linkLabel={t('cta.viewProducts')} />
            <div className="grid-products">
              {newArrivals.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          </div>
        </section>
      )}

      {/* Bestsellers */}
      {bestsellers.length > 0 && (
        <section className="section section-alt">
          <div className="container">
            <SectionHeader title={t('home.bestsellers')} linkTo="/shop" linkLabel={t('cta.viewProducts')} />
            <div className="grid-products">
              {bestsellers.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          </div>
        </section>
      )}

      {/* Why choose */}
      <section className="section why-section">
        <div className="container">
          <SectionHeader title={t('home.whyTitle')} subtitle={t('home.whySubtitle')} />
          <div className="why-grid">
            {whyKeys.map((key, i) => {
              const Icon = whyIcons[i]
              return (
                <div key={key} className="why-card">
                  <div className="why-icon"><Icon size={32} /></div>
                  <h3>{t(`home.${key}`)}</h3>
                  <p>{t(`home.${key}Desc`)}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Industry use cases */}
      <section className="section section-alt">
        <div className="container">
          <SectionHeader title={t('home.industryTitle')} subtitle={t('home.industrySubtitle')} />
          <div className="industry-grid">
            {industryKeys.map((key) => (
              <Link key={key} to="/shop" className="industry-card">
                <h3>{t(`home.${key}`)}</h3>
                <p>{t(`home.${key}Desc`)}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Promo banner */}
      <section className="promo-banner">
        <div className="container promo-banner-inner">
          <div>
            <h2>{t('home.promoTitle')}</h2>
            <p>{t('home.promoSubtitle')}</p>
          </div>
          <Link to="/shop?on_sale=true" className="btn btn-primary">{t('nav.promotions')}</Link>
        </div>
      </section>

      <Newsletter />
    </>
  )
}
