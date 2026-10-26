import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../../components/LanguageSwitcher'
import { adminLogin, fetchMe } from '../../api/admin'
import './Admin.css'

export default function AdminLoginPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    const form = new FormData(e.currentTarget)
    const username = form.get('username') as string
    const password = form.get('password') as string

    try {
      const tokens = await adminLogin(username, password)
      localStorage.setItem('access_token', tokens.access)
      localStorage.setItem('refresh_token', tokens.refresh)
      const user = await fetchMe()
      if (!user.is_staff) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setError(t('adminLogin.errorNotStaff'))
        return
      }
      navigate('/admin/products')
    } catch {
      setError(t('adminLogin.errorCredentials'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="admin-login-page notranslate" translate="no">
      <div className="admin-login-lang">
        <LanguageSwitcher />
      </div>
      <form className="admin-login-card" onSubmit={handleSubmit}>
        <h1>{t('adminLogin.title')}</h1>
        <p>{t('adminLogin.subtitle')}</p>
        {error && <div className="admin-alert admin-alert-error">{error}</div>}
        <label>
          {t('adminLogin.username')}
          <input name="username" required autoComplete="username" />
        </label>
        <label>
          {t('adminLogin.password')}
          <input name="password" type="password" required autoComplete="current-password" />
        </label>
        <button type="submit" className="btn btn-primary admin-login-btn" disabled={loading}>
          {loading ? t('adminLogin.submitting') : t('adminLogin.submit')}
        </button>
        <p className="admin-login-forgot">
          <Link to="/account?mode=forgot&next=/admin/login">{t('adminLogin.forgotPassword')}</Link>
        </p>
      </form>
    </div>
  )
}
