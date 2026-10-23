import type { Category } from '../api/types'
import { sortByName } from './sortCategories'

const WORKWEAR_PARENT_SLUGS = ['abbigliamento-da-lavoro']
const PROFESSIONAL_PARENT_SLUGS = ['abbigliamento-professionale']

function mergeSectionChildren(
  categories: Category[],
  section: 'workwear' | 'professional',
  preferredSlugs: string[],
  locale?: string,
): Category[] {
  const parents = categories.filter((c) => c.section === section)
  if (!parents.length) return []

  const preferred = parents.find((p) => preferredSlugs.includes(p.slug))
  if (preferred?.children?.length) {
    return sortByName(preferred.children, locale)
  }

  const bySlug = new Map<string, Category>()
  for (const parent of parents) {
    for (const child of parent.children ?? []) {
      if (child.slug && !bySlug.has(child.slug)) {
        bySlug.set(child.slug, child)
      }
    }
  }
  return sortByName([...bySlug.values()], locale)
}

export function getShopCategoryGroups(categories: Category[], locale?: string) {
  return {
    workwear: mergeSectionChildren(categories, 'workwear', WORKWEAR_PARENT_SLUGS, locale),
    professional: mergeSectionChildren(
      categories,
      'professional',
      PROFESSIONAL_PARENT_SLUGS,
      locale,
    ),
  }
}
