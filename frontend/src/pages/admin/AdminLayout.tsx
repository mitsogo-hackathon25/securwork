import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import './Admin.css'

export default function AdminLayout() {
  const navigate = useNavigate()

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/admin/login')
  }

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <Link to="/admin/products" className="admin-brand">
          <span className="admin-brand-mark">sw</span>
          <span>SecurWork Admin</span>
        </Link>
        <nav className="admin-nav">
          <NavLink to="/admin/products" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>Prodotti</NavLink>
          <NavLink to="/admin/orders" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>Ordini</NavLink>
          <NavLink to="/admin/coupons" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>Coupon</NavLink>
          <NavLink to="/admin/catalog" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>Catalogo</NavLink>
          <NavLink to="/admin/settings" className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>Impostazioni globali</NavLink>
          <a href="/" className="admin-nav-link admin-nav-link-muted" target="_blank" rel="noreferrer">
            Vai al negozio
          </a>
        </nav>
        <button type="button" className="admin-logout" onClick={handleLogout}>Esci</button>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  )
}
