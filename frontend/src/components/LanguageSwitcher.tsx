import { useTranslation } from 'react-i18next'

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const current = i18n.language

  const switchLang = (lang: string) => {
    i18n.changeLanguage(lang)
    localStorage.setItem('securwork_lang', lang)
    document.documentElement.lang = lang
  }

  return (
    <div className="lang-switcher" role="navigation" aria-label="Language">
      <button
        className={`lang-btn ${current === 'it' ? 'active' : ''}`}
        onClick={() => switchLang('it')}
        aria-current={current === 'it' ? 'true' : undefined}
      >
        IT
      </button>
      <span className="lang-divider">|</span>
      <button
        className={`lang-btn ${current === 'en' ? 'active' : ''}`}
        onClick={() => switchLang('en')}
        aria-current={current === 'en' ? 'true' : undefined}
      >
        EN
      </button>
    </div>
  )
}
