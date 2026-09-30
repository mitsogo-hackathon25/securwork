import { Link } from 'react-router-dom'
import type { Category } from '../api/types'
import './CategoryCard.css'

interface Props {
  category: Category
  variant?: 'default' | 'compact' | 'hero'
}

export default function CategoryCard({ category, variant = 'default' }: Props) {
  const link = `/shop?category=${category.slug}`

  return (
    <Link to={link} className={`category-card category-card--${variant}`}>
      <div className="category-card-bg" aria-hidden="true" />
      {category.image ? (
        <img src={category.image} alt="" className="category-card-img" loading="lazy" />
      ) : null}
      <div className="category-card-content">
        <h3>{category.name}</h3>
        {category.description && variant === 'default' && (
          <p>{category.description}</p>
        )}
        <span className="category-card-cta">→</span>
      </div>
    </Link>
  )
}
