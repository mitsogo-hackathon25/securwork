/** Default home imagery when no upload exists in admin (replace via Catalog / Settings). */
export const HOME_HERO_IMAGE_FALLBACK =
  'https://images.unsplash.com/photo-1581094794329-c8112a89af12?auto=format&fit=crop&w=1832&h=858&q=80'

export const HOME_SECTION_CATEGORY_FALLBACKS: Record<string, string> = {
  workwear:
    'https://images.unsplash.com/photo-1581094794329-c8112a89af12?auto=format&fit=crop&w=1200&h=800&q=80',
  professional:
    'https://images.unsplash.com/photo-1556910103-1c02745aae4d?auto=format&fit=crop&w=1200&h=800&q=80',
}

export const CATEGORY_IMAGE_DIMENSIONS_HINT = '1200 × 800 px (rapporto 3:2, JPG/PNG/WebP)'
export const HERO_IMAGE_DIMENSIONS_HINT = '1832 × 858 px (banner home, JPG/PNG/WebP)'

export function resolveCategoryCardImage(category: {
  image: string | null
  section: string
  parent: number | null
}): string | null {
  if (category.image) return category.image
  if (category.parent == null) {
    return HOME_SECTION_CATEGORY_FALLBACKS[category.section] ?? null
  }
  return null
}
