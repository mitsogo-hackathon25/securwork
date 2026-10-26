import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../../components/LanguageSwitcher'
import { SITE_LOGO_URL } from '../../constants/branding'
import './Admin.css'

export default function AdminLayout() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/admin/login')
  }

  return (
    <div className="admin-shell notranslate" translate="no">
      <aside className="admin-sidebar">
        <Link to="/admin/products" className="admin-brand">
          <img src={SITE_LOGO_URL} alt="" className="site-logo-img site-logo-img--admin" width={120} height={36} />
          <span>{t('adminNav.label')}</span>
        </Link>
        <nav className="admin-nav">
          <NavLink to="/admin/products" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>
            {t('adminNav.products')}
          </NavLink>
          <NavLink to="/admin/orders" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>
            {t('adminNav.orders')}
          </NavLink>
          <NavLink to="/admin/coupons" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>
            {t('adminNav.coupons')}
          </NavLink>
          <NavLink to="/admin/catalog" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>
            {t('adminNav.catalog')}
          </NavLink>
          <NavLink to="/admin/settings" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>
            {t('adminNav.settings')}
          </NavLink>
          <a href="/" className="admin-nav-link admin-nav-link-muted" target="_blank" rel="noreferrer">
            {t('adminNav.store')}
          </a>
        </nav>
        <div className="admin-sidebar-footer">
          <LanguageSwitcher />
          <button type="button" className="admin-logout" onClick={handleLogout}>
            {t('adminNav.logout')}
          </button>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet key={i18n.resolvedLanguage || i18n.language} />
      </main>
    </div>
  )
}
