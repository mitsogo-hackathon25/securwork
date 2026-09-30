import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import Breadcrumbs from '../components/Breadcrumbs'
import ProductCard from '../components/ProductCard'
import ShopFilters from '../components/ShopFilters'
import { fetchCategories, fetchProducts } from '../api/store'
import './ShopPage.css'

export default function ShopPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const [mobileFilters, setMobileFilters] = useState(false)

  const section = params.get('section') || ''
  const category = params.get('category') || ''
  const search = params.get('search') || ''
  const inStock = params.get('in_stock') || ''
  const size = params.get('size') || ''
  const color = params.get('color') || ''
  const minPrice = params.get('min_price') || ''
  const maxPrice = params.get('max_price') || ''
  const ordering = params.get('ordering') || '-created_at'

  const queryParams: Record<string, string> = { ordering }
  if (section) queryParams.section = section
  if (category) queryParams.category = category
  if (search) queryParams.search = search
  if (inStock) queryParams.in_stock = inStock
  if (size) queryParams.size = size
  if (color) queryParams.color = color
  if (minPrice) queryParams.min_price = minPrice
  if (maxPrice) queryParams.max_price = maxPrice

  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: fetchCategories })

  const { data, isLoading } = useQuery({
    queryKey: ['products', queryParams],
    queryFn: () => fetchProducts(queryParams),
  })

  const products = data?.results ?? []
  const total = data?.count ?? 0

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }

  const clearFilters = () => setParams({})

  const pageTitle = section === 'workwear'
    ? t('nav.workwear')
    : section === 'professional'
      ? t('nav.professional')
      : t('shop.title')

  return (
    <>
      <Helmet>
        <title>{pageTitle} — SecurWork</title>
        <meta name="description" content={t('shop.metaDescription')} />
      </Helmet>

      <div className="shop-page">
        <div className="container">
          <Breadcrumbs items={[{ label: pageTitle }]} />

          <div className="shop-layout">
            <ShopFilters
              categories={categories}
              filters={{ section, category, inStock, size, color, minPrice, maxPrice }}
              onChange={updateFilter}
              onClear={clearFilters}
              mobileOpen={mobileFilters}
              onCloseMobile={() => setMobileFilters(false)}
            />

            <div className="shop-main">
              <div className="shop-toolbar">
                <div>
                  <h1 className="shop-title">{pageTitle}</h1>
                  {!isLoading && <p className="shop-count">{t('shop.resultCount', { count: total })}</p>}
                </div>
                <div className="shop-toolbar-actions">
                  <button type="button" className="btn-filter-mobile" onClick={() => setMobileFilters(true)}>
                    {t('shop.filters')}
                  </button>
                  <select
                    className="shop-sort"
                    value={ordering}
                    onChange={(e) => updateFilter('ordering', e.target.value)}
                    aria-label={t('shop.sortBy')}
                  >
                    <option value="-created_at">{t('shop.sortNewest')}</option>
                    <option value="created_at">{t('shop.sortOldest')}</option>
                    <option value="translations__name">{t('shop.sortNameAsc')}</option>
                    <option value="-translations__name">{t('shop.sortNameDesc')}</option>
                  </select>
                </div>
              </div>

              {isLoading ? (
                <div className="shop-loading">{t('common.loading')}</div>
              ) : products.length === 0 ? (
                <div className="shop-empty">
                  <p>{t('shop.noResults')}</p>
                  <button type="button" className="btn btn-secondary" onClick={clearFilters}>{t('shop.clearFilters')}</button>
                </div>
              ) : (
                <div className="grid-products">
                  {products.map((p) => <ProductCard key={p.id} product={p} />)}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
