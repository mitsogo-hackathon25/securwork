/** Clothing sizes used in shop filters and product variants. */
export const CLOTHING_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '4XL'] as const

const SIZE_ORDER = new Map(CLOTHING_SIZES.map((size, index) => [size, index]))

/** Sort sizes small → large; known clothing sizes first, then any others alphabetically. */
export function sortClothingSizes(sizes: string[]): string[] {
  return [...sizes].sort((a, b) => {
    const aIndex = SIZE_ORDER.get(a as typeof CLOTHING_SIZES[number])
    const bIndex = SIZE_ORDER.get(b as typeof CLOTHING_SIZES[number])
    if (aIndex !== undefined && bIndex !== undefined) return aIndex - bIndex
    if (aIndex !== undefined) return -1
    if (bIndex !== undefined) return 1
    return a.localeCompare(b)
  })
}
