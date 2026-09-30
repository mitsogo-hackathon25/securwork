import { Link } from 'react-router-dom'
import './SectionHeader.css'

interface Props {
  title: string
  subtitle?: string
  linkTo?: string
  linkLabel?: string
}

export default function SectionHeader({ title, subtitle, linkTo, linkLabel }: Props) {
  return (
    <div className="section-header">
      <div>
        <h2 className="section-header-title">{title}</h2>
        {subtitle && <p className="section-header-subtitle">{subtitle}</p>}
      </div>
      {linkTo && linkLabel && (
        <Link to={linkTo} className="section-header-link">{linkLabel} →</Link>
      )}
    </div>
  )
}
