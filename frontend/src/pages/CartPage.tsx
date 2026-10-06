import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import { fetchCart, removeCartItem, updateCartItem } from '../api/store'
import './CartPage.css'

export default function CartPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: cart, isLoading } = useQuery({
    queryKey: ['cart'],
    queryFn: fetchCart,
  })

  const formatPrice = (p: string) => `€ ${parseFloat(p).toFixed(2).replace('.', ',')}`

  const handleUpdate = async (itemId: number, quantity: number) => {
    await updateCartItem(itemId, quantity)
    queryClient.invalidateQueries({ queryKey: ['cart'] })
  }

  const handleRemove = async (itemId: number) => {
    await removeCartItem(itemId)
    queryClient.invalidateQueries({ queryKey: ['cart'] })
  }

  return (
    <>
      <Helmet><title>{t('cart.title')} — SecurWork</title></Helmet>

      <div className="container section cart-page">
        <h1 className="section-title">{t('cart.title')}</h1>

        {isLoading ? (
          <p>{t('common.loading')}</p>
        ) : !cart?.items.length ? (
          <div className="cart-empty">
            <p>{t('cart.empty')}</p>
            <Link to="/shop" className="btn btn-primary">{t('cta.continueShopping')}</Link>
          </div>
        ) : (
          <>
            <table className="cart-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Price</th>
                  <th>{t('product.quantity')}</th>
                  <th>Total</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {cart.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="cart-product-cell">
                        {item.customization?.preview && (
                          <img src={item.customization.preview} alt="" className="cart-custom-preview" />
                        )}
                        <div>
                          <strong>{item.product_name}</strong>
                          {item.customization && (
                            <span className="cart-custom-badge">{t('customizer.customized')}</span>
                          )}
                          <br />
                          <small>{item.variant.sku} — {item.variant.size} {item.variant.color}</small>
                        </div>
                      </div>
                    </td>
                    <td>{formatPrice(item.unit_price || item.variant.effective_price)}</td>
                    <td>
                      <input
                        type="number"
                        min={1}
                        max={item.variant.stock_quantity}
                        value={item.quantity}
                        onChange={(e) => handleUpdate(item.id, parseInt(e.target.value) || 1)}
                        className="qty-input"
                      />
                    </td>
                    <td>{formatPrice(item.line_total)}</td>
                    <td>
                      <button className="remove-btn" onClick={() => handleRemove(item.id)}>
                        {t('cart.remove')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="cart-summary">
              <p className="cart-total">
                <strong>{t('cart.total')}:</strong> {formatPrice(cart.total)}
              </p>
              <Link to="/checkout" className="btn btn-primary">{t('cta.checkout')}</Link>
            </div>
          </>
        )}
      </div>
    </>
  )
}
