import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { checkout } from '../api/store'
import type { CheckoutResponse } from '../api/types'
import { loadPayPalSdk, type PayPalCardFieldsHandle } from '../utils/paypalSdk'

export type PayPalCardFieldsController = {
  submit: (payload: Record<string, unknown>) => Promise<void>
  isEligible: () => boolean
}

type Props = {
  clientId: string
  currency: string
  enabled: boolean
  onReady: (controller: PayPalCardFieldsController | null) => void
  onSuccess: (result: CheckoutResponse, paypalOrderId: string) => void
  onError: (message: string) => void
}

export default function PayPalCardFields({
  clientId,
  currency,
  enabled,
  onReady,
  onSuccess,
  onError,
}: Props) {
  const { t } = useTranslation()
  const pendingPayloadRef = useRef<Record<string, unknown> | null>(null)
  const lastCheckoutRef = useRef<CheckoutResponse | null>(null)
  const cardFieldsRef = useRef<PayPalCardFieldsHandle | null>(null)
  const onReadyRef = useRef(onReady)
  const onSuccessRef = useRef(onSuccess)
  const onErrorRef = useRef(onError)
  onReadyRef.current = onReady
  onSuccessRef.current = onSuccess
  onErrorRef.current = onError
  const [eligible, setEligible] = useState(true)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    if (!enabled || !clientId) {
      cardFieldsRef.current = null
      setMounted(false)
      onReadyRef.current(null)
      return
    }

    let cancelled = false

    loadPayPalSdk(clientId, currency)
      .then(() => {
        if (cancelled || !window.paypal?.CardFields) return

        const cardField = window.paypal.CardFields({
          createOrder: async () => {
            const payload = pendingPayloadRef.current
            if (!payload) {
              throw new Error('Missing checkout data')
            }
            const result = await checkout(payload)
            if (!result.paypal_order_id) {
              throw new Error('PayPal order was not created')
            }
            lastCheckoutRef.current = result
            return result.paypal_order_id
          },
          onApprove: async (data) => {
            const result = lastCheckoutRef.current
            if (result) {
              onSuccessRef.current(result, data.orderID)
            }
          },
          onError: (err) => {
            const message = err && typeof err === 'object' && 'message' in err
              ? String((err as { message: unknown }).message)
              : t('checkout.cardPayError')
            onErrorRef.current(message)
          },
        })

        if (!cardField.isEligible()) {
          setEligible(false)
          onReadyRef.current(null)
          return
        }

        cardFieldsRef.current = cardField
        return Promise.all([
          cardField.NameField().render('#pp-card-name'),
          cardField.NumberField().render('#pp-card-number'),
          cardField.ExpiryField().render('#pp-card-expiry'),
          cardField.CVVField().render('#pp-card-cvv'),
        ]).then(() => {
          if (!cancelled) setMounted(true)
        })
      })
      .catch(() => {
        if (!cancelled) onErrorRef.current(t('checkout.cardSdkError'))
      })

    return () => {
      cancelled = true
      cardFieldsRef.current = null
      setMounted(false)
      onReadyRef.current(null)
    }
  }, [enabled, clientId, currency, t])

  useEffect(() => {
    if (!mounted || !eligible || !cardFieldsRef.current) {
      onReadyRef.current(null)
      return
    }
    const controller: PayPalCardFieldsController = {
      submit: async (payload) => {
        pendingPayloadRef.current = payload
        lastCheckoutRef.current = null
        if (!cardFieldsRef.current) {
          throw new Error('Card fields not ready')
        }
        await cardFieldsRef.current.submit({ contingencies: ['3D_SECURE'] })
      },
      isEligible: () => cardFieldsRef.current?.isEligible?.() ?? false,
    }
    onReadyRef.current(controller)
  }, [mounted, eligible])

  if (!enabled) return null

  if (!eligible) {
    return <p className="checkout-notice">{t('checkout.cardNotEligible')}</p>
  }

  return (
    <div className="paypal-card-fields" aria-busy={!mounted}>
      <p className="checkout-note">{t('checkout.cardFieldsHint')}</p>
      <label className="pp-field-label">{t('checkout.cardName')}</label>
      <div id="pp-card-name" className="pp-card-field" />
      <label className="pp-field-label">{t('checkout.cardNumber')}</label>
      <div id="pp-card-number" className="pp-card-field" />
      <div className="pp-card-field-row">
        <div>
          <label className="pp-field-label">{t('checkout.cardExpiry')}</label>
          <div id="pp-card-expiry" className="pp-card-field" />
        </div>
        <div>
          <label className="pp-field-label">{t('checkout.cardCvv')}</label>
          <div id="pp-card-cvv" className="pp-card-field" />
        </div>
      </div>
      {!mounted && <p className="checkout-note">{t('checkout.cardFieldsLoading')}</p>}
    </div>
  )
}
