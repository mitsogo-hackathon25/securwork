import { useTranslation } from 'react-i18next'
import type { Category } from '../api/types'
import './ShopFilters.css'

interface FilterState {
  section: string
  category: string
  inStock: string
  size: string
  color: string
  minPrice: string
  maxPrice: string
}

interface Props {
  categories: Category[]
  filters: FilterState
  onChange: (key: string, value: string) => void
  onClear: () => void
  mobileOpen?: boolean
  onCloseMobile?: () => void
}

export default function ShopFilters({
  categories,
  filters,
  onChange,
  onClear,
  mobileOpen,
  onCloseMobile,
}: Props) {
  const { t } = useTranslation()

  const content = (
    <>
      <div className="filters-header">
        <h2>{t('shop.filters')}</h2>
        <button type="button" className="filters-clear" onClick={onClear}>{t('shop.clearFilters')}</button>
      </div>

      <div className="filter-group">
        <label htmlFor="filter-section">{t('shop.section')}</label>
        <select id="filter-section" value={filters.section} onChange={(e) => onChange('section', e.target.value)}>
          <option value="">—</option>
          <option value="workwear">{t('nav.workwear')}</option>
          <option value="professional">{t('nav.professional')}</option>
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="filter-category">{t('shop.category')}</label>
        <select id="filter-category" value={filters.category} onChange={(e) => onChange('category', e.target.value)}>
          <option value="">—</option>
          {categories.flatMap((parent) =>
            parent.children?.map((child) => (
              <option key={child.id} value={child.slug}>{child.name}</option>
            )) ?? []
          )}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="filter-stock">{t('shop.availability')}</label>
        <select id="filter-stock" value={filters.inStock} onChange={(e) => onChange('in_stock', e.target.value)}>
          <option value="">—</option>
          <option value="true">{t('shop.inStock')}</option>
          <option value="false">{t('shop.outOfStock')}</option>
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="filter-size">{t('product.size')}</label>
        <select id="filter-size" value={filters.size} onChange={(e) => onChange('size', e.target.value)}>
          <option value="">—</option>
          {['S', 'M', 'L', 'XL', 'XXL'].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="filter-color">{t('product.color')}</label>
        <select id="filter-color" value={filters.color} onChange={(e) => onChange('color', e.target.value)}>
          <option value="">—</option>
          {['Nero', 'Blu', 'Grigio'].map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="filter-group filter-group--row">
        <div>
          <label htmlFor="filter-min">{t('shop.priceMin')}</label>
          <input id="filter-min" type="number" min="0" value={filters.minPrice} onChange={(e) => onChange('min_price', e.target.value)} />
        </div>
        <div>
          <label htmlFor="filter-max">{t('shop.priceMax')}</label>
          <input id="filter-max" type="number" min="0" value={filters.maxPrice} onChange={(e) => onChange('max_price', e.target.value)} />
        </div>
      </div>
    </>
  )

  return (
    <>
      <aside className="shop-filters desktop-filters" aria-label={t('shop.filters')}>
        {content}
      </aside>

      <div className={`shop-filters-mobile ${mobileOpen ? 'open' : ''}`}>
        <div className="shop-filters-mobile-backdrop" onClick={onCloseMobile} aria-hidden="true" />
        <div className="shop-filters-mobile-panel" role="dialog" aria-modal="true" aria-label={t('shop.filters')}>
          <button type="button" className="filters-close" onClick={onCloseMobile} aria-label="Close">×</button>
          {content}
          <button type="button" className="btn btn-primary filters-apply" onClick={onCloseMobile}>
            {t('shop.applyFilters')}
          </button>
        </div>
      </div>
    </>
  )
}
