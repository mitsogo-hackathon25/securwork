import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import {
  confirmPasswordReset,
  fetchOrders,
  login,
  register,
  requestPasswordReset,
} from '../api/store'
import { clearAuthTokens, isLoggedIn, setAuthTokens } from '../utils/auth'
import { formatApiError } from '../utils/formatApiError'
import { formatPrice } from '../utils/format'
import './AccountPage.css'

type AuthMode = 'login' | 'register' | 'forgot' | 'reset'

function parseAuthMode(value: string | null): AuthMode {
  if (value === 'register' || value === 'forgot' || value === 'reset') return value
  return 'login'
}

export default function AccountPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = searchParams.get('next') || ''
  const initialMode = parseAuthMode(searchParams.get('mode'))
  const [mode, setMode] = useState<AuthMode>(initialMode)
  const [resetEmail, setResetEmail] = useState(searchParams.get('email') || '')
  const [loggedIn, setLoggedIn] = useState(isLoggedIn)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setMode(parseAuthMode(searchParams.get('mode')))
    const emailParam = searchParams.get('email')
    if (emailParam) setResetEmail(emailParam)
  }, [searchParams])

  const { data: orders = [] } = useQuery({
    queryKey: ['orders'],
    queryFn: fetchOrders,
    enabled: loggedIn,
  })

  const redirectAfterAuth = () => {
    if (nextPath.startsWith('/') && !nextPath.startsWith('//')) {
      navigate(nextPath)
      return
    }
    navigate('/account')
  }

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSubmitting(true)
    const form = new FormData(e.currentTarget)
    try {
      const res = await login(form.get('username') as string, form.get('password') as string)
      setAuthTokens(res.access, res.refresh)
      setLoggedIn(true)
      redirectAfterAuth()
    } catch (err: unknown) {
      setError(formatApiError(err, t('account.loginError')))
    } finally {
      setSubmitting(false)
    }
  }

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSubmitting(true)
    const form = new FormData(e.currentTarget)
    const data: Record<string, string> = {}
    form.forEach((v, k) => { data[k] = v.toString() })
    try {
      await register(data)
      const res = await login(data.username, data.password)
      setAuthTokens(res.access, res.refresh)
      setLoggedIn(true)
      setSuccess(t('account.registerSuccess'))
      redirectAfterAuth()
    } catch (err: unknown) {
      setError(formatApiError(err, t('account.registerError')))
    } finally {
      setSubmitting(false)
    }
  }

  const handleForgotRequest = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSubmitting(true)
    const form = new FormData(e.currentTarget)
    const email = (form.get('email') as string).trim()
    try {
      await requestPasswordReset(email)
      setResetEmail(email)
      setSuccess(t('account.resetRequestSuccess'))
      setMode('reset')
    } catch (err: unknown) {
      setError(formatApiError(err, t('account.resetEmailError')))
    } finally {
      setSubmitting(false)
    }
  }

  const handleResetConfirm = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSubmitting(true)
    const form = new FormData(e.currentTarget)
    const email = (form.get('email') as string).trim()
    const otp = (form.get('otp') as string).trim()
    const password = form.get('password') as string
    const password_confirm = form.get('password_confirm') as string
    try {
      await confirmPasswordReset({ email, otp, password, password_confirm })
      setSuccess(t('account.resetConfirmSuccess'))
      setMode('login')
    } catch (err: unknown) {
      setError(formatApiError(err, t('account.resetError')))
    } finally {
      setSubmitting(false)
    }
  }

  const handleLogout = () => {
    clearAuthTokens()
    setLoggedIn(false)
    setSuccess('')
    setError('')
  }

  const showAuthTabs = mode === 'login' || mode === 'register'

  return (
    <>
      <Helmet><title>{t('nav.account')} — SecurWork</title></Helmet>

      <div className={`container section account-page${loggedIn ? '' : ' account-page--auth'}`}>
        {loggedIn ? (
          <h1 className="section-title">{t('nav.account')}</h1>
        ) : null}

        {loggedIn ? (
          <div className="account-logged-in">
            <div className="account-toolbar">
              <p className="account-welcome">{t('account.welcome')}</p>
              <button type="button" className="btn btn-secondary" onClick={handleLogout}>
                {t('account.logout')}
              </button>
            </div>
            <h2>{t('account.orders')}</h2>
            {orders.length === 0 ? (
              <p className="account-empty">
                {t('account.noOrders')}{' '}
                <Link to="/shop">{t('nav.shop')}</Link>
              </p>
            ) : (
              <ul className="account-orders">
                {orders.map((o) => (
                  <li key={o.order_number}>
                    <Link to={`/order-confirmation/${o.order_number}`}>
                      <strong>{o.order_number}</strong>
                      <span>{o.status}</span>
                      <span>{formatPrice(o.total)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div className="account-auth">
            <div className="account-auth-shell">
            <div className="account-auth-card">
            {nextPath === '/checkout' && mode === 'login' && (
              <p className="account-notice">{t('account.loginRequiredCheckout')}</p>
            )}

            {showAuthTabs && (
              <>
                <h1 className="account-auth-heading">
                  {mode === 'register' ? t('account.register') : t('account.login')}
                </h1>
                <p className="account-auth-sub">
                  {mode === 'register' ? t('account.registerSubtitle') : t('account.loginSubtitle')}
                </p>
              </>
            )}

            {showAuthTabs && (
              <div className="account-tabs" role="tablist" aria-label={t('nav.account')}>
                <button
                  type="button"
                  className={`btn ${mode === 'login' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => { setMode('login'); setError(''); setSuccess('') }}
                >
                  {t('account.login')}
                </button>
                <button
                  type="button"
                  className={`btn ${mode === 'register' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => { setMode('register'); setError(''); setSuccess('') }}
                >
                  {t('account.register')}
                </button>
              </div>
            )}

            {error && <p className="account-error">{error}</p>}
            {success && <p className="account-success">{success}</p>}

            {mode === 'login' && (
              <form onSubmit={handleLogin} className="account-form">
                <div className="form-grid">
                  <label className="full-width">
                    {t('account.username')}
                    <input name="username" required autoComplete="username" />
                  </label>
                  <label className="full-width">
                    {t('account.password')}
                    <input name="password" type="password" required autoComplete="current-password" />
                  </label>
                </div>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? t('common.loading') : t('account.login')}
                </button>
                <p className="account-switch">
                  <button
                    type="button"
                    className="account-link-btn"
                    onClick={() => { setMode('forgot'); setError(''); setSuccess('') }}
                  >
                    {t('account.forgotPassword')}
                  </button>
                </p>
              </form>
            )}

            {mode === 'register' && (
              <form onSubmit={handleRegister} className="account-form">
                <div className="form-grid">
                  <label className="full-width">
                    {t('account.username')}
                    <input name="username" required autoComplete="username" />
                  </label>
                  <label className="full-width">
                    {t('contact.email')}
                    <input name="email" type="email" required autoComplete="email" />
                  </label>
                  <label>
                    {t('account.firstName')}
                    <input name="first_name" autoComplete="given-name" />
                  </label>
                  <label>
                    {t('account.lastName')}
                    <input name="last_name" autoComplete="family-name" />
                  </label>
                  <label className="full-width">
                    {t('account.password')}
                    <input name="password" type="password" required autoComplete="new-password" />
                  </label>
                  <label className="full-width">
                    {t('account.passwordConfirm')}
                    <input name="password_confirm" type="password" required autoComplete="new-password" />
                  </label>
                </div>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? t('common.loading') : t('account.register')}
                </button>
              </form>
            )}

            {mode === 'forgot' && (
              <>
                <h2 className="account-subtitle">{t('account.forgotTitle')}</h2>
                <p className="account-hint">{t('account.forgotHint')}</p>
                <form onSubmit={handleForgotRequest} className="account-form">
                  <div className="form-grid">
                    <label className="full-width">
                      {t('contact.email')}
                      <input
                        name="email"
                        type="email"
                        required
                        autoComplete="email"
                        defaultValue={resetEmail}
                      />
                    </label>
                  </div>
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    {submitting ? t('common.loading') : t('account.sendCode')}
                  </button>
                  <p className="account-switch">
                    <button type="button" className="account-link-btn" onClick={() => setMode('login')}>
                      {t('account.backToLogin')}
                    </button>
                  </p>
                </form>
              </>
            )}

            {mode === 'reset' && (
              <>
                <h2 className="account-subtitle">{t('account.resetTitle')}</h2>
                <p className="account-hint">{t('account.resetHint')}</p>
                <form onSubmit={handleResetConfirm} className="account-form">
                  <div className="form-grid">
                    <label className="full-width">
                      {t('contact.email')}
                      <input
                        name="email"
                        type="email"
                        required
                        autoComplete="email"
                        defaultValue={resetEmail}
                      />
                    </label>
                    <label className="full-width">
                      {t('account.otp')}
                      <input
                        name="otp"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength={6}
                        required
                        autoComplete="one-time-code"
                      />
                    </label>
                    <label className="full-width">
                      {t('account.password')}
                      <input name="password" type="password" required autoComplete="new-password" />
                    </label>
                    <label className="full-width">
                      {t('account.passwordConfirm')}
                      <input name="password_confirm" type="password" required autoComplete="new-password" />
                    </label>
                  </div>
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    {submitting ? t('common.loading') : t('account.resetPassword')}
                  </button>
                  <p className="account-switch">
                    <button type="button" className="account-link-btn" onClick={() => setMode('forgot')}>
                      {t('account.sendCode')}
                    </button>
                    {' · '}
                    <button type="button" className="account-link-btn" onClick={() => setMode('login')}>
                      {t('account.backToLogin')}
                    </button>
                  </p>
                </form>
              </>
            )}
            </div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
