import { Link } from 'react-router-dom'
import './Breadcrumbs.css'

export interface Crumb {
  label: string
  to?: string
}

interface Props {
  items: Crumb[]
}

export default function Breadcrumbs({ items }: Props) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <ol>
        <li><Link to="/">Home</Link></li>
        {items.map((item, i) => (
          <li key={i}>
            {item.to ? <Link to={item.to}>{item.label}</Link> : <span aria-current="page">{item.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  )
}
