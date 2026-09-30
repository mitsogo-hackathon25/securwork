import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import LanguageSwitcher from './LanguageSwitcher'
import MegaMenu from './MegaMenu'
import { fetchCart, fetchCategories } from '../api/store'
import './Header.css'

export default function Header() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [megaOpen, setMegaOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [search, setSearch] = useState('')

  const { data: cart } = useQuery({
    queryKey: ['cart'],
    queryFn: fetchCart,
    refetchInterval: 30_000,
  })

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: fetchCategories,
  })

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
            <span className="logo-mark" aria-hidden="true">SW</span>
            <span className="logo-text">SecurWork</span>
          </Link>

          <nav className={`main-nav ${mobileOpen ? 'open' : ''}`} aria-label="Main navigation">
            <Link to="/" onClick={closeAll}>{t('nav.home')}</Link>

            <div
              className="nav-dropdown"
              onMouseEnter={() => setMegaOpen(true)}
              onMouseLeave={() => setMegaOpen(false)}
            >
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

            <Link to="/about" onClick={closeAll}>{t('nav.about')}</Link>
            <Link to="/contact" onClick={closeAll}>{t('nav.contact')}</Link>
            <Link to="/faq" onClick={closeAll}>{t('nav.faq')}</Link>

            {mobileOpen && categories.length > 0 && (
              <div className="mobile-categories">
                <p className="mobile-categories-label">{t('nav.shop')}</p>
                {categories.flatMap((parent) =>
                  parent.children?.map((child) => (
                    <Link key={child.id} to={`/shop?category=${child.slug}`} onClick={closeAll}>
                      {child.name}
                    </Link>
                  )) ?? []
                )}
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
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><line x1="3" y1="6" x2="21" y2="6" /><path d="M16 10a4 4 0 0 1-8 0" />
              </svg>
              {cart && cart.item_count > 0 && (
                <span className="cart-count">{cart.item_count}</span>
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

        <MegaMenu categories={categories} open={megaOpen} onNavigate={closeAll} />
      </div>
    </header>
  )
}
