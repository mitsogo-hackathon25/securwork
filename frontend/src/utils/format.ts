/** Parse API money strings (dot or comma decimals) to a number. */
export function parseMoney(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === '') return NaN
  if (typeof value === 'number') return value
  const cleaned = String(value).trim().replace(/\s/g, '').replace(',', '.')
  return parseFloat(cleaned)
}

export function formatPrice(value: string | number | null | undefined): string {
  const num = typeof value === 'number' ? value : parseMoney(value)
  if (Number.isNaN(num)) return ''
  return `€ ${num.toFixed(2).replace('.', ',')}`
}

/** True when the customer pays less than the list price (matches backend effective_price). */
export function variantHasDiscount(variant: {
  price: string
  effective_price?: string | null
  sale_price?: string | null
}): boolean {
  const list = parseMoney(variant.price)
  const effective = parseMoney(variant.effective_price ?? variant.price)
  if (Number.isNaN(list) || Number.isNaN(effective)) return false
  return effective < list
}
