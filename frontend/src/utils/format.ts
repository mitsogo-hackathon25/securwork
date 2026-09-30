export function formatPrice(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return ''
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (Number.isNaN(num)) return ''
  return `€ ${num.toFixed(2).replace('.', ',')}`
}
