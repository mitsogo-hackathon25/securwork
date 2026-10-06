import { Link } from 'react-router-dom'
import type { Category } from '../api/types'
import './CategoryCard.css'

interface Props {
  category: Category
  variant?: 'default' | 'compact' | 'hero'
}

export default function CategoryCard({ category, variant = 'default' }: Props) {
  const link = category.section
    ? `/shop?section=${category.section}&category=${category.slug}`
    : `/shop?category=${category.slug}`

  const hasImage = Boolean(category.image)

  return (
    <Link
      to={link}
      className={`category-card category-card--${variant}${hasImage ? ' category-card--has-image' : ''}`}
    >
      <div className="category-card-bg" aria-hidden="true" />
      {hasImage ? (
        <img src={category.image!} alt="" className="category-card-img" loading="lazy" />
      ) : (
        <div className="category-card-placeholder" aria-hidden="true">
          <span>{category.name.charAt(0)}</span>
        </div>
      )}
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
