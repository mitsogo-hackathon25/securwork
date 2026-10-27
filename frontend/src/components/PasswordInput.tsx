import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import './PasswordInput.css'

type Props = {
  name: string
  autoComplete?: string
  required?: boolean
  defaultValue?: string
}

export default function PasswordInput({
  name,
  autoComplete,
  required = false,
  defaultValue,
}: Props) {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(false)

  return (
    <div className="password-input-wrap">
      <input
        name={name}
        type={visible ? 'text' : 'password'}
        required={required}
        autoComplete={autoComplete}
        defaultValue={defaultValue}
        className="password-input-field"
      />
      <button
        type="button"
        className="password-input-toggle"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? t('account.hidePassword') : t('account.showPassword')}
        aria-pressed={visible}
      >
        {visible ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
            <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
            <line x1="1" y1="1" x2="23" y2="23" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </div>
  )
}
