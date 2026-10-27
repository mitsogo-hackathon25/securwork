import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Trans, useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Helmet } from 'react-helmet-async'
import Breadcrumbs from '../components/Breadcrumbs'
import { checkout, fetchCart, fetchCheckoutQuote, fetchPaymentConfig, fetchPickupLocations } from '../api/store'
import { accountUrlWithNext, isLoggedIn } from '../utils/auth'
import { formatApiError } from '../utils/formatApiError'
import { formatPrice } from '../utils/format'
import { estimateCheckoutQuote } from '../utils/checkoutQuote'
import './CheckoutPage.css'

export default function CheckoutPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<'paypal' | 'stripe' | 'bank_transfer'>('paypal')
  const [sameAsBilling, setSameAsBilling] = useState(true)
  const [couponCode, setCouponCode] = useState('')
  const [fulfillmentType, setFulfillmentType] = useState<'delivery' | 'pickup'>('delivery')
  const [pickupLocationId, setPickupLocationId] = useState<number | null>(null)

  const cancelled = searchParams.get('cancelled')
  const loggedIn = isLoggedIn()

  useEffect(() => {
    if (!loggedIn) {
      navigate(accountUrlWithNext('/checkout', 'login'), { replace: true })
    }
  }, [loggedIn, navigate])

  const couponParam = couponCode.trim() || undefined

  const { data: pickupLocations } = useQuery({
    queryKey: ['pickup-locations'],
    queryFn: fetchPickupLocations,
    enabled: loggedIn,
  })

  const { data: cart, isLoading: cartLoading } = useQuery({
    queryKey: ['cart', paymentMethod, couponParam, fulfillmentType],
    queryFn: () => fetchCart({
      payment_method: paymentMethod,
      coupon_code: couponParam,
      fulfillment_type: fulfillmentType,
    }),
    enabled: loggedIn,
  })

  const { data: apiQuote } = useQuery({
    queryKey: ['checkout-quote', paymentMethod, couponParam, fulfillmentType, cart?.items.length],
    queryFn: () => fetchCheckoutQuote({
      payment_method: paymentMethod,
      coupon_code: couponParam,
      fulfillment_type: fulfillmentType,
    }),
    enabled: loggedIn && Boolean(cart?.items.length),
    retry: 1,
  })

  const quote = useMemo(() => {
    if (!cart?.items.length) return null
    if (apiQuote) return apiQuote
    if (cart.checkout_preview) return cart.checkout_preview
    const subtotal = parseFloat(cart.total)
    const discount = 0
    return estimateCheckoutQuote(subtotal, paymentMethod, discount, fulfillmentType)
  }, [apiQuote, cart, paymentMethod, fulfillmentType])

  useEffect(() => {
    if (fulfillmentType !== 'pickup' || !pickupLocations?.length) return
    if (pickupLocationId && pickupLocations.some((l) => l.id === pickupLocationId)) return
    setPickupLocationId(pickupLocations[0].id)
  }, [fulfillmentType, pickupLocations, pickupLocationId])
  const { data: paymentConfig } = useQuery({
    queryKey: ['paymentConfig'],
    queryFn: fetchPaymentConfig,
    enabled: loggedIn,
  })

  const stripeAvailable = paymentConfig?.stripe_enabled ?? false
  const paypalAvailable = paymentConfig?.paypal_enabled ?? false

  useEffect(() => {
    if (!paymentConfig) return
    if (paymentConfig.paypal_enabled) {
      setPaymentMethod('paypal')
    } else if (paymentConfig.stripe_enabled) {
      setPaymentMethod('stripe')
    } else {
      setPaymentMethod('bank_transfer')
    }
  }, [paymentConfig])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!isLoggedIn()) {
      navigate(accountUrlWithNext('/checkout', 'login'))
      return
    }
    setLoading(true)
    setError('')
    const form = new FormData(e.currentTarget)
    const data: Record<string, unknown> = {}
    form.forEach((value, key) => { data[key] = value })
    data.accept_terms = form.get('accept_terms') === 'on'
    data.language = i18n.language
    data.payment_method = paymentMethod
    data.fulfillment_type = fulfillmentType
    if (fulfillmentType === 'pickup') {
      if (!pickupLocationId) {
        setError(t('checkout.pickupRequired'))
        setLoading(false)
        return
      }
      data.pickup_location_id = pickupLocationId
    } else if (sameAsBilling) {
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
    } catch (err: unknown) {
      const status = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { status?: number } }).response?.status
        : undefined
      if (status === 401) {
        navigate(accountUrlWithNext('/checkout', 'login'))
        return
      }
      setError(formatApiError(err, t('common.error')))
    } finally {
      setLoading(false)
    }
  }

  if (!loggedIn) {
    return (
      <div className="container checkout-page">
        <p>{t('common.loading')}</p>
      </div>
    )
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
                <input type="hidden" name="billing_country" value="IT" />
                <input name="billing_vat" placeholder="P.IVA" />
              </div>
            </section>

            <section>
              <h2>{t('checkout.fulfillment')}</h2>
              <div className="fulfillment-methods">
                <label className={`payment-option ${fulfillmentType === 'delivery' ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="fulfillment_type_ui"
                    checked={fulfillmentType === 'delivery'}
                    onChange={() => setFulfillmentType('delivery')}
                  />
                  <span>{t('checkout.fulfillmentDelivery')}</span>
                </label>
                <label className={`payment-option ${fulfillmentType === 'pickup' ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="fulfillment_type_ui"
                    checked={fulfillmentType === 'pickup'}
                    onChange={() => setFulfillmentType('pickup')}
                  />
                  <span>{t('checkout.fulfillmentPickup')}</span>
                </label>
              </div>

              {fulfillmentType === 'pickup' && (
                <div className="pickup-locations">
                  {!pickupLocations?.length ? (
                    <p className="checkout-notice">{t('checkout.pickupNone')}</p>
                  ) : (
                    pickupLocations.map((loc) => (
                      <label
                        key={loc.id}
                        className={`pickup-location-option ${pickupLocationId === loc.id ? 'active' : ''}`}
                      >
                        <input
                          type="radio"
                          name="pickup_location"
                          checked={pickupLocationId === loc.id}
                          onChange={() => setPickupLocationId(loc.id)}
                        />
                        <div>
                          <strong>{loc.name}</strong>
                          <p>{loc.address}, {loc.postcode} {loc.city}</p>
                          {loc.phone && <p>{loc.phone}</p>}
                          {loc.notes && <p className="pickup-notes">{loc.notes}</p>}
                        </div>
                      </label>
                    ))
                  )}
                </div>
              )}
            </section>

            {fulfillmentType === 'delivery' && (
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
                  <input type="hidden" name="shipping_country" value="IT" />
                </div>
              )}
            </section>
            )}

            <section>
              <h2>{t('checkout.paymentMethod')}</h2>
              <div className="payment-methods">
                {paypalAvailable && (
                  <label className={`payment-option ${paymentMethod === 'paypal' ? 'active' : ''}`}>
                    <input
                      type="radio"
                      name="payment_method_ui"
                      value="paypal"
                      checked={paymentMethod === 'paypal'}
                      onChange={() => { setPaymentMethod('paypal') }}
                    />
                    <span>{t('checkout.payPayPal')}</span>
                  </label>
                )}
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
              <input
                name="coupon_code"
                placeholder={t('checkout.coupon')}
                className="full-width coupon-input"
                value={couponCode}
                onChange={(e) => setCouponCode(e.target.value)}
              />
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
              {loading ? t('common.loading') : (paymentMethod === 'stripe' && stripeAvailable)
                  || (paymentMethod === 'paypal' && paypalAvailable)
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
                {cartLoading && !quote ? (
                  <p className="checkout-note">{t('checkout.calculatingTotal')}</p>
                ) : quote ? (
                  <div className="checkout-quote">
                    <div className="checkout-quote-row">
                      <span>{t('cart.subtotal')}</span>
                      <span>{formatPrice(quote.subtotal)}</span>
                    </div>
                    {parseFloat(quote.discount_amount) > 0 && (
                      <div className="checkout-quote-row">
                        <span>{t('checkout.discount')}</span>
                        <span>−{formatPrice(quote.discount_amount)}</span>
                      </div>
                    )}
                    <div className="checkout-quote-row">
                      <span>
                        {fulfillmentType === 'pickup' ? t('checkout.pickupLine') : t('checkout.shipping')}
                      </span>
                      <span>
                        {parseFloat(quote.shipping_cost) > 0
                          ? formatPrice(quote.shipping_cost)
                          : t('checkout.shippingFree')}
                      </span>
                    </div>
                    <div className="checkout-quote-row">
                      <span>{t('checkout.vat')}</span>
                      <span>{formatPrice(quote.tax_amount)}</span>
                    </div>
                    {paymentMethod === 'paypal' && parseFloat(quote.payment_fee) > 0 && (
                      <div className="checkout-quote-row">
                        <span>{t('checkout.paypalFee')}</span>
                        <span>{formatPrice(quote.payment_fee)}</span>
                      </div>
                    )}
                    <p className="checkout-total">
                      <strong>{t('checkout.totalPayable')}</strong>
                      <strong>{formatPrice(quote.total)}</strong>
                    </p>
                  </div>
                ) : null}
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
