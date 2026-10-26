import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import LanguageSwitcher from './LanguageSwitcher'
import MegaMenu from './MegaMenu'
import { fetchCart, fetchCategories } from '../api/store'
import { fetchSupportUnreadCount } from '../api/support'
import { isLoggedIn } from '../utils/auth'
import { getShopCategoryGroups } from '../utils/categoryNav'
import { SITE_LOGO_URL } from '../constants/branding'
import './Header.css'

export default function Header() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [megaOpen, setMegaOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [search, setSearch] = useState('')

  const loggedIn = isLoggedIn()

  const { data: cart } = useQuery({
    queryKey: ['cart'],
    queryFn: fetchCart,
    refetchInterval: 30_000,
  })

  const { data: supportUnread } = useQuery({
    queryKey: ['support-unread'],
    queryFn: fetchSupportUnreadCount,
    enabled: loggedIn,
    refetchInterval: 30_000,
  })

  const { data: categories = [] } = useQuery({
    queryKey: ['categories', i18n.language],
    queryFn: () => fetchCategories(i18n.language),
  })

  const { workwear: workwearChildren, professional: professionalChildren } = getShopCategoryGroups(
    categories,
    i18n.language,
  )

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (search.trim()) {
      navigate(`/shop?search=${encodeURIComponent(search.trim())}`)
      setSearch('')
      setMobileOpen(false)
    }
  }

  const closeAll = () => {
    setMobileOpen(false)
    setMegaOpen(false)
  }

  return (
    <header className={`site-header ${scrolled ? 'scrolled' : ''}`} role="banner">
      <div className="header-wrapper">
        <div className="container header-inner">
          <Link to="/" className="logo" aria-label="SecurWork Home" onClick={closeAll}>
            <img src={SITE_LOGO_URL} alt="" className="site-logo-img" width={196} height={56} />
          </Link>

          <nav className={`main-nav ${mobileOpen ? 'open' : ''}`} aria-label="Main navigation">
            <Link to="/" onClick={closeAll} onMouseEnter={() => setMegaOpen(false)}>{t('nav.home')}</Link>

            <div className="nav-dropdown" onMouseEnter={() => setMegaOpen(true)}>
              <Link
                to="/shop"
                className={megaOpen ? 'active' : ''}
                onClick={closeAll}
                aria-haspopup="true"
                aria-expanded={megaOpen}
              >
                {t('nav.shop')} <span className="nav-chevron" aria-hidden="true">▾</span>
              </Link>
            </div>

            <Link to="/shop?on_sale=true" onClick={closeAll} onMouseEnter={() => setMegaOpen(false)}>{t('nav.promotions')}</Link>
            <Link to="/about" onClick={closeAll} onMouseEnter={() => setMegaOpen(false)}>{t('nav.about')}</Link>
            <Link to="/contact" onClick={closeAll} onMouseEnter={() => setMegaOpen(false)}>{t('nav.contact')}</Link>
            <Link to="/faq" onClick={closeAll} onMouseEnter={() => setMegaOpen(false)}>{t('nav.faq')}</Link>
            <Link to="/tickets" onClick={closeAll} onMouseEnter={() => setMegaOpen(false)} className="nav-link-with-dot">
              {t('nav.tickets')}
              {loggedIn && (supportUnread?.count ?? 0) > 0 && (
                <span className="nav-unread-dot" aria-label={t('tickets.unread')} />
              )}
            </Link>

            {mobileOpen && (workwearChildren.length > 0 || professionalChildren.length > 0) && (
              <div className="mobile-categories">
                {workwearChildren.length > 0 && (
                  <div className="mobile-categories-group">
                    <p className="mobile-categories-label">{t('nav.workwear')}</p>
                    {workwearChildren.map((child) => (
                      <Link
                        key={child.id}
                        to={`/shop?section=workwear&category=${child.slug}`}
                        onClick={closeAll}
                      >
                        {child.name || child.slug}
                      </Link>
                    ))}
                  </div>
                )}
                {professionalChildren.length > 0 && (
                  <div className="mobile-categories-group">
                    <p className="mobile-categories-label">{t('nav.professional')}</p>
                    {professionalChildren.map((child) => (
                      <Link
                        key={child.id}
                        to={`/shop?section=professional&category=${child.slug}`}
                        onClick={closeAll}
                      >
                        {child.name || child.slug}
                      </Link>
                    ))}
                  </div>
                )}
                <Link to="/shop" className="mobile-categories-all" onClick={closeAll}>
                  {t('nav.shop')} — {t('cta.shopNow')}
                </Link>
              </div>
            )}
          </nav>

          <div className="header-actions">
            <form className="search-form" onSubmit={handleSearch} role="search">
              <label htmlFor="header-search" className="sr-only">{t('nav.search')}</label>
              <input
                id="header-search"
                type="search"
                placeholder={t('nav.search')}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </form>

            <LanguageSwitcher />

            <Link to="/account" className="header-icon" aria-label={t('nav.account')}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
              </svg>
            </Link>

            <Link to="/cart" className="header-icon cart-link" aria-label={t('nav.cart')}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="9" cy="21" r="1" />
                <circle cx="20" cy="21" r="1" />
                <path d="M1 1h4l2.2 11.4a2 2 0 0 0 2 1.7h9.7a2 2 0 0 0 2-1.7L23 6H6" />
              </svg>
              {cart && cart.item_count > 0 && (
                <span className="cart-count" aria-hidden="true">
                  {cart.item_count > 99 ? '99+' : cart.item_count}
                </span>
              )}
            </Link>

            <button
              className={`mobile-toggle ${mobileOpen ? 'open' : ''}`}
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-expanded={mobileOpen}
              aria-label="Toggle menu"
            >
              <span /><span /><span />
            </button>
          </div>
        </div>

        <MegaMenu
          categories={categories}
          open={megaOpen}
          onNavigate={closeAll}
          onMouseEnter={() => setMegaOpen(true)}
          onMouseLeave={() => setMegaOpen(false)}
        />
      </div>
    </header>
  )
}
