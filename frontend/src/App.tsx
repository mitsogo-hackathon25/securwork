import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ScrollToTop from './components/ScrollToTop'
import AdminRoute from './components/admin/AdminRoute'
import HomePage from './pages/HomePage'
import ShopPage from './pages/ShopPage'
import ProductPage from './pages/ProductPage'
import CartPage from './pages/CartPage'
import CheckoutPage from './pages/CheckoutPage'
import OrderConfirmationPage from './pages/OrderConfirmationPage'
import CmsPage from './pages/CmsPage'
import ContactPage from './pages/ContactPage'
import FAQPage from './pages/FAQPage'
import AccountPage from './pages/AccountPage'
import TicketsPage from './pages/TicketsPage'
import NotFoundPage from './pages/NotFoundPage'
import AdminLayout from './pages/admin/AdminLayout'
import AdminLoginPage from './pages/admin/AdminLoginPage'
import AdminProductsPage from './pages/admin/AdminProductsPage'
import AdminProductFormPage from './pages/admin/AdminProductFormPage'
import AdminOrdersPage from './pages/admin/AdminOrdersPage'
import AdminOrderDetailPage from './pages/admin/AdminOrderDetailPage'
import AdminCouponsPage from './pages/admin/AdminCouponsPage'
import AdminCouponFormPage from './pages/admin/AdminCouponFormPage'
import AdminCatalogPage from './pages/admin/AdminCatalogPage'
import AdminGlobalSettingsPage from './pages/admin/AdminGlobalSettingsPage'
import AdminSupportPage from './pages/admin/AdminSupportPage'
import AdminUsersPage from './pages/admin/AdminUsersPage'
import AdminUserDetailPage from './pages/admin/AdminUserDetailPage'
import AdminPickupLocationsPage from './pages/admin/AdminPickupLocationsPage'
import AdminPickupLocationFormPage from './pages/admin/AdminPickupLocationFormPage'

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/admin" element={<AdminRoute />}>
          <Route element={<AdminLayout />}>
            <Route index element={<Navigate to="/admin/products" replace />} />
            <Route path="products" element={<AdminProductsPage />} />
            <Route path="products/new" element={<AdminProductFormPage />} />
            <Route path="products/:id" element={<AdminProductFormPage />} />
            <Route path="orders" element={<AdminOrdersPage />} />
            <Route path="orders/:id" element={<AdminOrderDetailPage />} />
            <Route path="users" element={<AdminUsersPage />} />
            <Route path="users/:id" element={<AdminUserDetailPage />} />
            <Route path="coupons" element={<AdminCouponsPage />} />
            <Route path="coupons/new" element={<AdminCouponFormPage />} />
            <Route path="coupons/:id" element={<AdminCouponFormPage />} />
            <Route path="catalog" element={<AdminCatalogPage />} />
            <Route path="pickup-locations" element={<AdminPickupLocationsPage />} />
            <Route path="pickup-locations/new" element={<AdminPickupLocationFormPage />} />
            <Route path="pickup-locations/:id" element={<AdminPickupLocationFormPage />} />
            <Route path="settings" element={<AdminGlobalSettingsPage />} />
            <Route path="tickets" element={<AdminSupportPage />} />
            <Route path="tickets/:id" element={<AdminSupportPage />} />
            <Route path="pricing" element={<Navigate to="/admin/settings" replace />} />
          </Route>
        </Route>

        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/shop" element={<ShopPage />} />
          <Route path="/product/:slug" element={<ProductPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/order-confirmation/:orderNumber" element={<OrderConfirmationPage />} />
          <Route path="/about" element={<CmsPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route path="/faq" element={<FAQPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/tickets" element={<TicketsPage />} />
          <Route path="/tickets/:id" element={<TicketsPage />} />
          <Route path="/pages/:pageType" element={<CmsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
