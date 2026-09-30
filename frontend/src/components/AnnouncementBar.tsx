import { useTranslation } from 'react-i18next'
import './AnnouncementBar.css'

export default function AnnouncementBar() {
  const { i18n } = useTranslation()
  const text = i18n.language === 'it'
    ? 'Spedizione in tutta Italia · Qualità professionale garantita'
    : 'Shipping across Italy · Professional quality guaranteed'

  return (
    <div className="announcement-bar" role="region" aria-label="Announcement">
      <div className="container">{text}</div>
    </div>
  )
}
