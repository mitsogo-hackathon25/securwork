import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { fetchSiteConfig } from '../api/store'
import './Footer.css'

export default function Footer() {
  const { t } = useTranslation()
  const year = new Date().getFullYear()
  const { data: site } = useQuery({ queryKey: ['siteConfig'], queryFn: fetchSiteConfig })

  return (
    <footer className="site-footer" role="contentinfo">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-brand">
            <div className="footer-logo">
              <span className="logo-mark">SW</span>
              <span className="logo-text">SecurWork</span>
            </div>
            <p className="footer-tagline">{t('home.heroSubtitle')}</p>
            {site ? (
              <div className="footer-company">
                <p>{site.company_name}</p>
                <p>{site.company_vat}</p>
                <p>{site.company_address}, {site.company_city}</p>
                <p><a href={`mailto:${site.contact_email}`}>{site.contact_email}</a></p>
              </div>
            ) : (
              <p className="footer-placeholder">{t('footer.companyPlaceholder')}</p>
            )}
          </div>

          <nav className="footer-nav" aria-label="Shop">
            <h3>{t('nav.shop')}</h3>
            <Link to="/shop">{t('nav.shop')}</Link>
            <Link to="/shop?section=workwear">{t('nav.workwear')}</Link>
            <Link to="/shop?section=professional">{t('nav.professional')}</Link>
          </nav>

          <nav className="footer-nav" aria-label="Information">
            <h3>{t('footer.info')}</h3>
            <Link to="/about">{t('nav.about')}</Link>
            <Link to="/faq">{t('nav.faq')}</Link>
            <Link to="/contact">{t('nav.contact')}</Link>
            <Link to="/pages/shipping">{t('footer.shipping')}</Link>
            <Link to="/pages/returns">{t('footer.returns')}</Link>
          </nav>

          <nav className="footer-nav" aria-label="Legal">
            <h3>{t('footer.legal')}</h3>
            <Link to="/pages/privacy">{t('footer.privacy')}</Link>
            <Link to="/pages/cookies">{t('footer.cookies')}</Link>
            <Link to="/pages/terms">{t('footer.terms')}</Link>
          </nav>
        </div>

        <div className="footer-bottom">
          <p>&copy; {year} SecurWork. {t('footer.rights')}</p>
        </div>
      </div>
    </footer>
  )
}
