import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import { fetchOrders, login, register } from '../api/store'

export default function AccountPage() {
  const { t } = useTranslation()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const isLoggedIn = !!localStorage.getItem('access_token')

  const { data: orders = [] } = useQuery({
    queryKey: ['orders'],
    queryFn: fetchOrders,
    enabled: isLoggedIn,
  })

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const res = await login(form.get('username') as string, form.get('password') as string)
    localStorage.setItem('access_token', res.access)
    localStorage.setItem('refresh_token', res.refresh)
    window.location.reload()
  }

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const data: Record<string, string> = {}
    form.forEach((v, k) => { data[k] = v.toString() })
    await register(data)
    setMode('login')
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.location.reload()
  }

  return (
    <>
      <Helmet><title>{t('nav.account')} — SecurWork</title></Helmet>

      <div className="container section">
        <h1 className="section-title">{t('nav.account')}</h1>

        {isLoggedIn ? (
          <div>
            <button className="btn btn-secondary" onClick={handleLogout}>{t('account.logout')}</button>
            <h2 style={{ marginTop: '2rem' }}>{t('account.orders')}</h2>
            {orders.length === 0 ? (
              <p>No orders yet.</p>
            ) : (
              <ul>
                {orders.map((o) => (
                  <li key={o.order_number}>
                    {o.order_number} — {o.status} — € {parseFloat(o.total).toFixed(2)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div>
            <div style={{ marginBottom: '1rem' }}>
              <button className={`btn ${mode === 'login' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setMode('login')}>{t('account.login')}</button>
              <button className={`btn ${mode === 'register' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setMode('register')} style={{ marginLeft: '0.5rem' }}>{t('account.register')}</button>
            </div>

            {mode === 'login' ? (
              <form onSubmit={handleLogin} className="checkout-form" style={{ maxWidth: 400 }}>
                <div className="form-grid">
                  <input name="username" required placeholder="Username" className="full-width" />
                  <input name="password" type="password" required placeholder="Password" className="full-width" />
                </div>
                <button type="submit" className="btn btn-primary">{t('account.login')}</button>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="checkout-form" style={{ maxWidth: 400 }}>
                <div className="form-grid">
                  <input name="username" required placeholder="Username" className="full-width" />
                  <input name="email" type="email" required placeholder="Email" className="full-width" />
                  <input name="first_name" placeholder="Nome" className="full-width" />
                  <input name="last_name" placeholder="Cognome" className="full-width" />
                  <input name="password" type="password" required placeholder="Password" className="full-width" />
                  <input name="password_confirm" type="password" required placeholder="Confirm password" className="full-width" />
                </div>
                <button type="submit" className="btn btn-primary">{t('account.register')}</button>
              </form>
            )}
          </div>
        )}
      </div>
    </>
  )
}
