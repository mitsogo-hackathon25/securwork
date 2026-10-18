import type { Category } from '../api/types'

export function compareNames(a: string, b: string, locale?: string): number {
  return a.localeCompare(b, locale || undefined, { sensitivity: 'base' })
}

/** Sort categories and nested children A→Z by display name. */
export function sortCategoryTree(categories: Category[], locale?: string): Category[] {
  return [...categories]
    .sort((a, b) => compareNames(a.name, b.name, locale))
    .map((cat) => ({
      ...cat,
      children: cat.children?.length
        ? [...cat.children].sort((a, b) => compareNames(a.name, b.name, locale))
        : cat.children,
    }))
}

export function sortByName<T extends { name: string }>(items: T[], locale?: string): T[] {
  return [...items].sort((a, b) => compareNames(a.name, b.name, locale))
}
