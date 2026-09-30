import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Trans, useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import Breadcrumbs from '../components/Breadcrumbs'
import { checkout, fetchCart, fetchPaymentConfig } from '../api/store'
import { formatPrice } from '../utils/format'
import './CheckoutPage.css'

export default function CheckoutPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<'stripe' | 'bank_transfer'>('stripe')
  const [sameAsBilling, setSameAsBilling] = useState(true)

  const cancelled = searchParams.get('cancelled')

  const { data: cart } = useQuery({ queryKey: ['cart'], queryFn: fetchCart })
  const { data: paymentConfig } = useQuery({ queryKey: ['paymentConfig'], queryFn: fetchPaymentConfig })

  const stripeAvailable = paymentConfig?.stripe_enabled ?? false

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    const form = new FormData(e.currentTarget)
    const data: Record<string, unknown> = {}
    form.forEach((value, key) => { data[key] = value })
    data.accept_terms = form.get('accept_terms') === 'on'
    data.language = i18n.language
    data.payment_method = paymentMethod

    if (sameAsBilling) {
      data.shipping_first_name = data.billing_first_name
      data.shipping_last_name = data.billing_last_name
      data.shipping_address = data.billing_address
      data.shipping_city = data.billing_city
      data.shipping_postcode = data.billing_postcode
      data.shipping_country = data.billing_country || 'IT'
    }

    try {
      const result = await checkout(data)
      if (result.checkout_url) {
        window.location.href = result.checkout_url
        return
      }
      navigate(`/order-confirmation/${result.order.order_number}`)
    } catch {
      setError(t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Helmet><title>{t('checkout.title')} — SecurWork</title></Helmet>

      <div className="container checkout-page">
        <Breadcrumbs items={[{ label: t('nav.cart'), to: '/cart' }, { label: t('checkout.title') }]} />

        <h1 className="section-title">{t('checkout.title')}</h1>

        {cancelled && <p className="checkout-notice">{t('checkout.cancelled')}</p>}
        {error && <p className="checkout-error">{error}</p>}

        <div className="checkout-layout">
          <form onSubmit={handleSubmit} className="checkout-form">
            <section>
              <h2>{t('checkout.billing')}</h2>
              <div className="form-grid">
                <input name="email" type="email" required placeholder={`${t('contact.email')} *`} className="full-width" />
                <input name="phone" type="tel" placeholder={t('contact.phone')} className="full-width" />
                <input name="billing_first_name" required placeholder="Nome *" />
                <input name="billing_last_name" required placeholder="Cognome *" />
                <input name="billing_company" placeholder="Azienda" className="full-width" />
                <input name="billing_address" required placeholder="Indirizzo *" className="full-width" />
                <input name="billing_city" required placeholder="Città *" />
                <input name="billing_postcode" required placeholder="CAP *" />
                <input name="billing_vat" placeholder="P.IVA" />
              </div>
            </section>

            <section>
              <label className="same-address-check">
                <input
                  type="checkbox"
                  checked={sameAsBilling}
                  onChange={(e) => setSameAsBilling(e.target.checked)}
                />
                {t('checkout.sameAsBilling')}
              </label>

              {!sameAsBilling && (
                <div className="form-grid">
                  <h2 className="full-width">{t('checkout.shipping')}</h2>
                  <input name="shipping_first_name" required placeholder="Nome *" />
                  <input name="shipping_last_name" required placeholder="Cognome *" />
                  <input name="shipping_address" required placeholder="Indirizzo *" className="full-width" />
                  <input name="shipping_city" required placeholder="Città *" />
                  <input name="shipping_postcode" required placeholder="CAP *" />
                </div>
              )}
            </section>

            <section>
              <h2>{t('checkout.paymentMethod')}</h2>
              <div className="payment-methods">
                {stripeAvailable && (
                  <label className={`payment-option ${paymentMethod === 'stripe' ? 'active' : ''}`}>
                    <input
                      type="radio"
                      name="payment_method_ui"
                      value="stripe"
                      checked={paymentMethod === 'stripe'}
                      onChange={() => setPaymentMethod('stripe')}
                    />
                    <span>{t('checkout.payCard')}</span>
                  </label>
                )}
                <label className={`payment-option ${paymentMethod === 'bank_transfer' ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="payment_method_ui"
                    value="bank_transfer"
                    checked={paymentMethod === 'bank_transfer'}
                    onChange={() => setPaymentMethod('bank_transfer')}
                  />
                  <span>{t('checkout.payBank')}</span>
                </label>
              </div>
              {paymentMethod === 'bank_transfer' && paymentConfig && (
                <div className="bank-details">
                  <p><strong>{paymentConfig.bank_details.account_name}</strong></p>
                  <p>IBAN: {paymentConfig.bank_details.iban}</p>
                  <p>BIC: {paymentConfig.bank_details.bic}</p>
                  <p className="bank-note">{t('checkout.bankNote')}</p>
                </div>
              )}
            </section>

            <section>
              <input name="coupon_code" placeholder={t('checkout.coupon')} className="full-width coupon-input" />
            </section>

            <label className="terms-check">
              <input name="accept_terms" type="checkbox" required />
              <Trans
                i18nKey="checkout.acceptTerms"
                components={{
                  1: <Link to="/pages/terms" target="_blank" rel="noopener noreferrer" />,
                  3: <Link to="/pages/privacy" target="_blank" rel="noopener noreferrer" />,
                }}
              />
            </label>

            <button type="submit" className="btn btn-primary checkout-submit" disabled={loading}>
              {loading ? t('common.loading') : paymentMethod === 'stripe' && stripeAvailable
                ? t('checkout.payNow')
                : t('checkout.placeOrder')}
            </button>
          </form>

          <aside className="checkout-summary">
            <h2>{t('checkout.summary')}</h2>
            {cart && cart.items.length > 0 ? (
              <>
                <ul className="checkout-items">
                  {cart.items.map((item) => (
                    <li key={item.id}>
                      <span>{item.product_name} × {item.quantity}</span>
                      <span>{formatPrice(item.line_total)}</span>
                    </li>
                  ))}
                </ul>
                <p className="checkout-total">
                  <strong>{t('cart.total')}</strong>
                  <strong>{formatPrice(cart.total)}</strong>
                </p>
                <p className="checkout-note">{t('checkout.taxNote')}</p>
              </>
            ) : (
              <p>{t('cart.empty')}</p>
            )}
          </aside>
        </div>
      </div>
    </>
  )
}
