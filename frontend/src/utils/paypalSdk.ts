declare global {
  interface Window {
    paypal?: PayPalNamespace
  }
}

export type PayPalCardFieldsHandle = {
  submit: (options?: Record<string, unknown>) => Promise<void>
  isEligible: () => boolean
}

type PayPalNamespace = {
  CardFields: (config: {
    createOrder: () => Promise<string>
    onApprove?: (data: { orderID: string }) => void | Promise<void>
    onError?: (err: unknown) => void
  }) => PayPalCardFieldsHandle & {
    NameField: () => { render: (selector: string) => Promise<void> }
    NumberField: () => { render: (selector: string) => Promise<void> }
    ExpiryField: () => { render: (selector: string) => Promise<void> }
    CVVField: () => { render: (selector: string) => Promise<void> }
  }
}

let sdkPromise: Promise<void> | null = null

export function loadPayPalSdk(clientId: string, currency: string): Promise<void> {
  if (window.paypal?.CardFields) {
    return Promise.resolve()
  }
  if (sdkPromise) return sdkPromise

  sdkPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    const params = new URLSearchParams({
      'client-id': clientId,
      components: 'card-fields',
      currency,
      intent: 'capture',
    })
    script.src = `https://www.paypal.com/sdk/js?${params.toString()}`
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('PayPal SDK failed to load'))
    document.body.appendChild(script)
  })
  return sdkPromise
}
