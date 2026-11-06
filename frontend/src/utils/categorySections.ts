import type { Category } from '../api/types'

/** Shop URL section query value */
export type ShopSection = 'workwear' | 'professional'

export function categoryVisibleInSection(
  cat: Pick<Category, 'visible_in_workwear' | 'visible_in_professional' | 'section'>,
  section: ShopSection,
): boolean {
  if (section === 'workwear') {
    if (typeof cat.visible_in_workwear === 'boolean') return cat.visible_in_workwear
    return cat.section === 'workwear'
  }
  if (typeof cat.visible_in_professional === 'boolean') return cat.visible_in_professional
  return cat.section === 'professional'
}

export function parentCategoriesForSection(categories: Category[], section: ShopSection): Category[] {
  return categories.filter(
    (c) => c.parent == null && categoryVisibleInSection(c, section),
  )
}
