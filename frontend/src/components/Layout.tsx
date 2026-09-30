import { Outlet } from 'react-router-dom'
import Header from './Header'
import Footer from './Footer'
import AnnouncementBar from './AnnouncementBar'
import CookieBanner from './CookieBanner'

export default function Layout() {
  return (
    <>
      <AnnouncementBar />
      <Header />
      <main id="main-content">
        <Outlet />
      </main>
      <Footer />
      <CookieBanner />
    </>
  )
}
