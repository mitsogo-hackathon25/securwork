import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { isLoggedIn, accountUrlWithNext } from '../utils/auth'
import './HelpWidget.css'

const QUESTION_KEYS = ['q1', 'q2', 'q3', 'q4', 'q5'] as const

export default function HelpWidget() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [activeAnswer, setActiveAnswer] = useState<string | null>(null)

  const ticketsHref = isLoggedIn() ? '/tickets' : accountUrlWithNext('/tickets')

  return (
    <div className="help-widget" aria-live="polite">
      {open && (
        <div className="help-widget-panel" role="dialog" aria-label={t('help.title')}>
          <header className="help-widget-header">
            <h2>{t('help.title')}</h2>
            <p>{t('help.subtitle')}</p>
            <button
              type="button"
              className="help-widget-close"
              onClick={() => setOpen(false)}
              aria-label={t('help.close')}
            >
              ×
            </button>
          </header>
          <div className="help-widget-body">
            {activeAnswer ? (
              <div className="help-widget-answer">
                <button type="button" className="help-widget-back" onClick={() => setActiveAnswer(null)}>
                  ← {t('help.back')}
                </button>
                <p>{activeAnswer}</p>
              </div>
            ) : (
              <>
                <p className="help-widget-hint">{t('help.suggested')}</p>
                <ul className="help-widget-questions">
                  {QUESTION_KEYS.map((key) => (
                    <li key={key}>
                      <button
                        type="button"
                        onClick={() => setActiveAnswer(t(`help.${key}Answer`))}
                      >
                        {t(`help.${key}Question`)}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <Link to={ticketsHref} className="btn btn-primary help-widget-ticket" onClick={() => setOpen(false)}>
              {t('help.openTicket')}
            </Link>
            <Link to="/faq" className="help-widget-faq" onClick={() => setOpen(false)}>
              {t('help.viewFaq')}
            </Link>
          </div>
        </div>
      )}
      <button
        type="button"
        className="help-widget-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={t('help.toggle')}
      >
        ?
      </button>
    </div>
  )
}
