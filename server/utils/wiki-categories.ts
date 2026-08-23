import { readFileSync } from 'fs'
import { resolve } from 'path'

function toKebab(name: string): string {
  return name.toLowerCase().replace(/\s+/g, '-')
}

const rolesPath = resolve(process.cwd(), 'data/roles.json')
const roles: Array<{ id: number; nameEn: string }> = JSON.parse(
  readFileSync(rolesPath, 'utf-8'),
)

const GENERAL_CATEGORIES = ['guide', 'system', 'governance', 'general'] as const

const heroCategories: string[] = roles
  .filter((r) => r.nameEn && r.nameEn !== 'Random')
  .map((r) => toKebab(r.nameEn))

export const VALID_CATEGORIES = new Set([
  ...heroCategories,
  ...GENERAL_CATEGORIES,
])

export const SLUG_REGEX = /^[a-z0-9]+(-[a-z0-9]+)*$/

export function isValidSlug(slug: string): boolean {
  return slug.length >= 2 && slug.length <= 80 && SLUG_REGEX.test(slug)
}

export function isValidCategory(category: string): boolean {
  return VALID_CATEGORIES.has(category)
}

export function getCategoryGroups() {
  return {
    hero: heroCategories.sort(),
    general: [...GENERAL_CATEGORIES],
  }
}
