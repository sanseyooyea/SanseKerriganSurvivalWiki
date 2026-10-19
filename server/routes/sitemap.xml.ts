import { readFileSync } from 'fs'
import { join } from 'path'

/**
 * 动态 sitemap：静态页面 + 51 个职业页 + 838 个单位页。
 * 数据直接读本地 JSON，不依赖外部接口。
 */
const BASE = 'https://wiki.ks2.top'

const STATIC_PAGES: { path: string; changefreq: string; priority: string }[] = [
  { path: '/', changefreq: 'daily', priority: '1.0' },
  { path: '/classes', changefreq: 'weekly', priority: '0.9' },
  { path: '/units', changefreq: 'weekly', priority: '0.9' },
  { path: '/skins', changefreq: 'weekly', priority: '0.9' },
  { path: '/economy', changefreq: 'weekly', priority: '0.8' },
  { path: '/terrain', changefreq: 'weekly', priority: '0.7' },
  { path: '/balance', changefreq: 'daily', priority: '0.8' },
  { path: '/balance/trends', changefreq: 'daily', priority: '0.7' },
  { path: '/leaderboard', changefreq: 'hourly', priority: '0.7' },
  { path: '/lookup', changefreq: 'monthly', priority: '0.6' },
  { path: '/changelog', changefreq: 'daily', priority: '0.6' },
  { path: '/council', changefreq: 'daily', priority: '0.5' },
  { path: '/wiki', changefreq: 'weekly', priority: '0.6' },
]

function readJson(name: string): any {
  try {
    return JSON.parse(readFileSync(join(process.cwd(), 'data', name), 'utf-8'))
  } catch {
    return null
  }
}

function esc(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

export default defineEventHandler((event) => {
  const roles = readJson('roles.json') as any[] | null
  const unitsDoc = readJson('units-v2.json')
  const units = unitsDoc?.units ? Object.keys(unitsDoc.units) : []

  const urls: string[] = []

  for (const p of STATIC_PAGES) {
    urls.push(
      `  <url><loc>${BASE}${p.path}</loc>` +
      `<changefreq>${p.changefreq}</changefreq>` +
      `<priority>${p.priority}</priority></url>`
    )
  }

  for (const r of roles ?? []) {
    if (r?.id === undefined || r?.id === null) continue
    urls.push(
      `  <url><loc>${BASE}/classes/${r.id}</loc>` +
      `<changefreq>weekly</changefreq><priority>0.8</priority></url>`
    )
  }

  for (const id of units) {
    urls.push(
      `  <url><loc>${BASE}/units/${encodeURIComponent(id)}</loc>` +
      `<changefreq>weekly</changefreq><priority>0.5</priority></url>`
    )
  }

  const xml =
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    urls.join('\n') +
    '\n</urlset>\n'

  setHeader(event, 'Content-Type', 'application/xml; charset=utf-8')
  setHeader(event, 'Cache-Control', 'public, max-age=3600')
  return xml
})
