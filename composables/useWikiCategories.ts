import rolesData from '~/data/roles.json'

function toKebab(name: string): string {
  return name.toLowerCase().replace(/\s+/g, '-')
}

const GENERAL_CATEGORIES = [
  { value: 'guide', label: '指南' },
  { value: 'system', label: '系统分析' },
  { value: 'governance', label: '治理' },
  { value: 'general', label: '通用' },
]

const heroCategories = (rolesData as Array<{ id: number; nameEn: string; nameZh?: string }>)
  .filter((r) => r.nameEn && r.nameEn !== 'Random')
  .map((r) => ({
    value: toKebab(r.nameEn),
    label: r.nameZh || r.nameEn,
  }))
  .sort((a, b) => a.value.localeCompare(b.value))

export function useWikiCategories() {
  const groups = [
    { label: '英雄教学', options: heroCategories },
    { label: '通用分类', options: GENERAL_CATEGORIES },
  ]

  const allCategories = [...heroCategories, ...GENERAL_CATEGORIES]
  const validSet = new Set(allCategories.map((c) => c.value))

  function isValidCategory(val: string): boolean {
    return validSet.has(val)
  }

  return { groups, allCategories, isValidCategory }
}

export const SLUG_REGEX = /^[a-z0-9]+(-[a-z0-9]+)*$/

export function isValidSlug(slug: string): boolean {
  return slug.length >= 2 && slug.length <= 80 && SLUG_REGEX.test(slug)
}

export function normalizeSlug(input: string): string {
  return input
    .toLowerCase()
    .replace(/[\s_]+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '')
}
