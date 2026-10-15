import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Reset window scroll when the route path changes (e.g. product A → product B). */
export default function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [pathname])

  return null
}
