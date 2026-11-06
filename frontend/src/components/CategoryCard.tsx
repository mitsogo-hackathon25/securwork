import { Link } from 'react-router-dom'
import type { Category } from '../api/types'
import './CategoryCard.css'

interface Props {
  category: Category
  variant?: 'default' | 'compact' | 'hero'
  imageUrl?: string | null
  /** When set, shop links use this section (e.g. same category visible in both workwear and professional). */
  shopSection?: 'workwear' | 'professional'
}

export default function CategoryCard({ category, variant = 'default', imageUrl, shopSection }: Props) {
  const isSectionRoot = category.parent == null
  const sectionForLink = shopSection ?? category.section
  const link = isSectionRoot && sectionForLink
    ? `/shop?section=${sectionForLink}`
    : sectionForLink
      ? `/shop?section=${sectionForLink}&category=${category.slug}`
      : `/shop?category=${category.slug}`

  const displayImage = imageUrl ?? category.image
  const hasImage = Boolean(displayImage)

  return (
    <Link
      to={link}
      className={`category-card category-card--${variant}${hasImage ? ' category-card--has-image' : ''}`}
    >
      <div className="category-card-bg" aria-hidden="true" />
      {hasImage ? (
        <img src={displayImage!} alt="" className="category-card-img" loading="lazy" />
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
