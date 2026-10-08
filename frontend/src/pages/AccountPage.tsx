import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import { fetchOrders, login, register } from '../api/store'
import { clearAuthTokens, isLoggedIn, setAuthTokens } from '../utils/auth'
import { formatApiError } from '../utils/formatApiError'
import { formatPrice } from '../utils/format'
import './AccountPage.css'

export default function AccountPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = searchParams.get('next') || ''
  const initialMode = searchParams.get('mode') === 'register' ? 'register' : 'login'
  const [mode, setMode] = useState<'login' | 'register'>(initialMode)
  const [loggedIn, setLoggedIn] = useState(isLoggedIn)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setMode(initialMode)
  }, [initialMode])

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

  const handleLogout = () => {
    clearAuthTokens()
    setLoggedIn(false)
    setSuccess('')
    setError('')
  }

  return (
    <>
      <Helmet><title>{t('nav.account')} — SecurWork</title></Helmet>

      <div className="container section account-page">
        <h1 className="section-title">{t('nav.account')}</h1>

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
            {nextPath === '/checkout' && (
              <p className="account-notice">{t('account.loginRequiredCheckout')}</p>
            )}

            <div className="account-tabs">
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

            {error && <p className="account-error">{error}</p>}
            {success && <p className="account-success">{success}</p>}

            {mode === 'login' ? (
              <form onSubmit={handleLogin} className="checkout-form account-form">
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
                  {t('account.noAccount')}{' '}
                  <button type="button" className="account-link-btn" onClick={() => setMode('register')}>
                    {t('account.register')}
                  </button>
                </p>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="checkout-form account-form">
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
                <p className="account-switch">
                  {t('account.hasAccount')}{' '}
                  <button type="button" className="account-link-btn" onClick={() => setMode('login')}>
                    {t('account.login')}
                  </button>
                </p>
              </form>
            )}
          </div>
        )}
      </div>
    </>
  )
}
