import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { adminLogin, fetchMe } from '../../api/admin'
import './Admin.css'

export default function AdminLoginPage() {
  const navigate = useNavigate()
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
        setError('This account does not have admin access.')
        return
      }
      navigate('/admin/products')
    } catch {
      setError('Invalid username or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="admin-login-page">
      <form className="admin-login-card" onSubmit={handleSubmit}>
        <h1>SecurWork Admin</h1>
        <p>Sign in with your staff account to manage products.</p>
        {error && <div className="admin-alert admin-alert-error">{error}</div>}
        <label>
          Username
          <input name="username" required autoComplete="username" />
        </label>
        <label>
          Password
          <input name="password" type="password" required autoComplete="current-password" />
        </label>
        <button type="submit" className="btn btn-primary admin-login-btn" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
