import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { fetchMe } from '../../api/admin'

export default function AdminRoute() {
  const [status, setStatus] = useState<'loading' | 'allowed' | 'denied'>('loading')

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setStatus('denied')
      return
    }
    fetchMe()
      .then((user) => setStatus(user.is_staff ? 'allowed' : 'denied'))
      .catch(() => setStatus('denied'))
  }, [])

  if (status === 'loading') {
    return <div className="admin-loading">Loading admin panel…</div>
  }

  if (status === 'denied') {
    return <Navigate to="/admin/login" replace />
  }

  return <Outlet />
}
