import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { Category } from '../api/types'
import { getShopCategoryGroups } from '../utils/categoryNav'
import './MegaMenu.css'

interface Props {
  categories: Category[]
  open?: boolean
  onNavigate?: () => void
  onMouseEnter?: () => void
  onMouseLeave?: () => void
}

export default function MegaMenu({
  categories,
  open = false,
  onNavigate,
  onMouseEnter,
  onMouseLeave,
}: Props) {
  const { t, i18n } = useTranslation()
  const { workwear, professional } = getShopCategoryGroups(categories, i18n.language)

  const handleClick = () => onNavigate?.()

  return (
    <div
      className={`mega-menu ${open ? 'open' : ''}`}
      role="navigation"
      aria-label="Product categories"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="mega-menu-grid">
        <div className="mega-menu-col">
          <Link to="/shop?section=workwear" className="mega-menu-heading" onClick={handleClick}>
            {t('nav.workwear')}
          </Link>
          <ul>
            {workwear.map((child) => (
              <li key={child.id}>
                <Link
                  to={`/shop?section=workwear&category=${child.slug}`}
                  onClick={handleClick}
                >
                  {child.name || child.slug}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="mega-menu-col">
          <Link to="/shop?section=professional" className="mega-menu-heading" onClick={handleClick}>
            {t('nav.professional')}
          </Link>
          <ul>
            {professional.map((child) => (
              <li key={child.id}>
                <Link
                  to={`/shop?section=professional&category=${child.slug}`}
                  onClick={handleClick}
                >
                  {child.name || child.slug}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="mega-menu-col mega-menu-promo">
          <p className="mega-menu-promo-text">{t('home.heroSubtitle')}</p>
          <Link to="/shop" className="btn btn-primary btn-sm" onClick={handleClick}>
            {t('cta.shopNow')}
          </Link>
        </div>
      </div>
    </div>
  )
}
