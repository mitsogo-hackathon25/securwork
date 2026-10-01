import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { Product } from '../api/types'
import { formatPrice } from '../utils/format'
import './ProductCard.css'

interface Props {
  product: Product
}

export default function ProductCard({ product }: Props) {
  const { t } = useTranslation()

  return (
    <article className="product-card">
      <Link to={`/product/${product.slug}`} className="product-card-link">
        <div className="product-card-image">
          {product.primary_image ? (
            <img src={product.primary_image} alt={product.name} loading="lazy" />
          ) : (
            <div className="product-card-placeholder" aria-hidden="true">
              <span>{product.name.replace('[DEMO] ', '').charAt(0)}</span>
            </div>
          )}
          <div className="product-card-badges">
            {product.is_new_arrival && <span className="product-badge new">{t('home.newArrivals')}</span>}
            {product.is_bestseller && <span className="product-badge bestseller">{t('home.bestsellers')}</span>}
            {!product.in_stock && <span className="product-badge out-of-stock">{t('shop.outOfStock')}</span>}
          </div>
        </div>
        <div className="product-card-body">
          <h3 className="product-card-title">{product.name}</h3>
          {product.short_description && (
            <p className="product-card-desc">{product.short_description}</p>
          )}
          {product.min_price && (
            <p className="product-card-price">{formatPrice(product.min_price)}</p>
          )}
        </div>
      </Link>
    </article>
  )
}
