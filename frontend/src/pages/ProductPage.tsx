import { useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import Breadcrumbs from '../components/Breadcrumbs'
import ProductCard from '../components/ProductCard'
import { BreadcrumbSchema, ProductSchema } from '../components/SeoSchema'
import ProductCustomizer, { type ProductCustomizerHandle } from '../components/ProductCustomizer'
import { addToCart, fetchProduct, fetchRelated } from '../api/store'
import type { ProductVariant } from '../api/types'
import { formatPrice } from '../utils/format'
import './ProductPage.css'

export default function ProductPage() {
  const { slug } = useParams<{ slug: string }>()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | null>(null)
  const [activeImage, setActiveImage] = useState(0)
  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const [added, setAdded] = useState(false)
  const [customize, setCustomize] = useState(false)
  const [hasLogo, setHasLogo] = useState(false)
  const customizerRef = useRef<ProductCustomizerHandle>(null)

  const { data: product, isLoading } = useQuery({
    queryKey: ['product', slug],
    queryFn: () => fetchProduct(slug!),
    enabled: !!slug,
  })

  const { data: related = [] } = useQuery({
    queryKey: ['related', slug],
    queryFn: () => fetchRelated(slug!),
    enabled: !!slug,
  })

  if (isLoading) return <div className="container section"><p>{t('common.loading')}</p></div>
  if (!product) return <div className="container section"><p>{t('common.error')}</p></div>

  const variants = product.variants || []
  const variant = selectedVariant || variants.find((v) => v.in_stock) || variants[0]
  const maxQty = variant?.stock_quantity ?? 1
  const images = product.images?.length ? product.images : []
  const mainImage = images[activeImage]?.image || product.primary_image

  const mockupUrl = product.mockup_front || product.primary_image

  const handleAddToCart = async () => {
    if (!variant) return
    if (customize && !hasLogo) return
    setAdding(true)
    try {
      let customizationId: number | undefined
      if (customize && customizerRef.current?.hasLogo()) {
        customizationId = await customizerRef.current.upload()
      }
      await addToCart(variant.id, quantity, customizationId)
      queryClient.invalidateQueries({ queryKey: ['cart'] })
      setAdded(true)
      setTimeout(() => setAdded(false), 2500)
    } finally {
      setAdding(false)
    }
  }

  const sizes = [...new Set(variants.map((v) => v.size).filter(Boolean))]
  const colors = [...new Set(variants.map((v) => v.color).filter(Boolean))]
  const productUrl = `${window.location.origin}/product/${product.slug}`

  const selectVariant = (size?: string, color?: string) => {
    const match = variants.find((v) =>
      (!size || v.size === size) && (!color || v.color === color)
    )
    if (match) setSelectedVariant(match)
  }

  return (
    <>
      <Helmet>
        <title>{product.meta_title || product.name} — SecurWork</title>
        {product.meta_description && <meta name="description" content={product.meta_description} />}
        <meta property="og:title" content={product.name} />
        <meta property="og:type" content="product" />
        {mainImage && <meta property="og:image" content={mainImage} />}
      </Helmet>
      <ProductSchema
        name={product.name}
        description={product.short_description}
        sku={variant?.sku || product.sku}
        image={mainImage}
        price={variant?.effective_price}
        inStock={product.in_stock}
        url={productUrl}
      />
      <BreadcrumbSchema items={[
        { name: 'Home', url: window.location.origin },
        { name: t('nav.shop'), url: `${window.location.origin}/shop` },
        { name: product.name, url: productUrl },
      ]} />

      <div className="product-page">
        <div className="container">
          <Breadcrumbs items={[
            { label: t('nav.shop'), to: '/shop' },
            { label: product.name },
          ]} />

          <div className="product-layout">
            <div className="product-gallery">
              <div className="product-gallery-main">
                {mainImage ? (
                  <img src={mainImage} alt={product.name} />
                ) : (
                  <div className="product-gallery-placeholder" />
                )}
              </div>
              {images.length > 1 && (
                <div className="product-gallery-thumbs">
                  {images.map((img, i) => (
                    <button
                      key={img.id}
                      type="button"
                      className={`thumb ${i === activeImage ? 'active' : ''}`}
                      onClick={() => setActiveImage(i)}
                      aria-label={`Image ${i + 1}`}
                    >
                      <img src={img.image} alt="" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="product-info">
              <h1>{product.name}</h1>

              {product.short_description && (
                <p className="product-short-desc">{product.short_description}</p>
              )}

              {variant && (
                <p className="product-price">
                  {variant.sale_price && parseFloat(variant.sale_price) < parseFloat(variant.price) ? (
                    <>
                      <span className="sale-price">{formatPrice(variant.effective_price)}</span>
                      <span className="original-price">{formatPrice(variant.price)}</span>
                    </>
                  ) : (
                    formatPrice(variant.effective_price)
                  )}
                </p>
              )}

              {product.brand && (
                <p className="product-brand">{t('product.brand')}: {product.brand}</p>
              )}
              <p className="product-sku">{t('product.sku')}: {variant?.sku || product.sku}</p>

              {sizes.length > 0 && (
                <div className="variant-select">
                  <label>{t('product.size')}</label>
                  <div className="variant-options">
                    {sizes.map((size) => (
                      <button
                        key={size}
                        type="button"
                        className={`variant-btn ${variant?.size === size ? 'active' : ''}`}
                        onClick={() => selectVariant(size, variant?.color)}
                      >
                        {size}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {colors.length > 0 && (
                <div className="variant-select">
                  <label>{t('product.color')}</label>
                  <div className="variant-options">
                    {colors.map((color) => (
                      <button
                        key={color}
                        type="button"
                        className={`variant-btn ${variant?.color === color ? 'active' : ''}`}
                        onClick={() => selectVariant(variant?.size, color)}
                      >
                        {color}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {product.allows_customization && mockupUrl && (
                <div className="customization-toggle">
                  <label>
                    <input
                      type="checkbox"
                      checked={customize}
                      onChange={(e) => setCustomize(e.target.checked)}
                    />
                    {t('customizer.enable')}
                  </label>
                </div>
              )}

              {product.allows_customization && customize && mockupUrl && variant && (
                <ProductCustomizer
                  ref={customizerRef}
                  mockupUrl={mockupUrl}
                  variantId={variant.id}
                  customizationFee={product.customization_fee}
                  onReadyChange={setHasLogo}
                />
              )}

              <div className="quantity-select">
                <label htmlFor="qty">{t('product.quantity')}</label>
                <input
                  id="qty"
                  type="number"
                  min={1}
                  max={maxQty}
                  value={quantity}
                  onChange={(e) => setQuantity(Math.min(maxQty, Math.max(1, parseInt(e.target.value) || 1)))}
                />
                {variant && (
                  <span className={`stock-info ${variant.in_stock ? 'in-stock' : 'out-of-stock'}`}>
                    {variant.in_stock
                      ? variant.is_low_stock ? t('shop.lowStock') : t('shop.inStock')
                      : t('shop.outOfStock')}
                  </span>
                )}
              </div>

              <button
                className="btn btn-primary add-to-cart-btn"
                onClick={handleAddToCart}
                disabled={!variant?.in_stock || adding || (customize && !hasLogo)}
              >
                {adding ? t('common.loading') : added ? t('product.addedToCart') : t('cta.addToCart')}
              </button>

              <div className="product-shipping-info">
                <h3>{t('product.shippingInfo')}</h3>
                <p>{t('product.shippingInfoText')}</p>
              </div>
            </div>
          </div>

          {product.description && (
            <div className="product-description-full">
              <h2>{t('product.description')}</h2>
              <div dangerouslySetInnerHTML={{ __html: product.description }} />
            </div>
          )}

          {related.length > 0 && (
            <section className="related-products">
              <h2 className="section-title">{t('product.related')}</h2>
              <div className="grid-products">
                {related.map((p) => <ProductCard key={p.id} product={p} />)}
              </div>
            </section>
          )}
        </div>
      </div>
    </>
  )
}
