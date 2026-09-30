import { useTranslation } from 'react-i18next'
import { IconPayment, IconReturn, IconShield, IconSupport, IconTruck } from './Icons'
import './TrustBadges.css'

const badges = [
  { key: 'trustShipping', Icon: IconTruck },
  { key: 'trustReturns', Icon: IconReturn },
  { key: 'trustSecure', Icon: IconShield },
  { key: 'trustSupport', Icon: IconSupport },
  { key: 'trustPayment', Icon: IconPayment },
] as const

export default function TrustBadges() {
  const { t } = useTranslation()

  return (
    <div className="trust-badges" role="region" aria-label="Service benefits">
      <div className="container trust-badges-inner">
        {badges.map(({ key, Icon }) => (
          <div key={key} className="trust-badge">
            <Icon size={28} />
            <span>{t(`home.${key}`)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
