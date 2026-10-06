import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { Category } from '../api/types'
import './MegaMenu.css'

interface Props {
  categories: Category[]
  open?: boolean
  onNavigate?: () => void
}

export default function MegaMenu({ categories, open = false, onNavigate }: Props) {
  const { t } = useTranslation()

  const workwear = categories.find((c) => c.section === 'workwear')
  const professional = categories.find((c) => c.section === 'professional')

  const handleClick = () => onNavigate?.()

  return (
    <div className={`mega-menu ${open ? 'open' : ''}`} role="navigation" aria-label="Product categories">
      <div className="mega-menu-grid">
        {workwear && (
          <div className="mega-menu-col">
            <Link to="/shop?section=workwear" className="mega-menu-heading" onClick={handleClick}>
              {t('nav.workwear')}
            </Link>
            <ul>
              {workwear.children?.map((child) => (
                <li key={child.id}>
                  <Link to={`/shop?section=workwear&category=${child.slug}`} onClick={handleClick}>{child.name}</Link>
                </li>
              ))}
            </ul>
          </div>
        )}

        {professional && (
          <div className="mega-menu-col">
            <Link to="/shop?section=professional" className="mega-menu-heading" onClick={handleClick}>
              {t('nav.professional')}
            </Link>
            <ul>
              {professional.children?.map((child) => (
                <li key={child.id}>
                  <Link to={`/shop?section=professional&category=${child.slug}`} onClick={handleClick}>{child.name}</Link>
                </li>
              ))}
            </ul>
          </div>
        )}

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
