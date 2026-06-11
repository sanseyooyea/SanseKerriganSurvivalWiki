import DOMPurify from 'isomorphic-dompurify'

const COLOR_MAP: Record<string, string> = {
  'FFFF00': 'var(--sc2-yellow)',
  'FFff00': 'var(--sc2-yellow)',
  '00FF00': 'var(--sc2-green)',
  '00ff00': 'var(--sc2-green)',
  'FF0000': 'var(--sc2-red)',
  'ff0000': 'var(--sc2-red)',
  '00FFFF': 'var(--sc2-cyan)',
  '00ffff': 'var(--sc2-cyan)',
  'FF8000': 'var(--sc2-orange)',
  'ff8000': 'var(--sc2-orange)',
  'FFFFFF': 'var(--sc2-white)',
  'ffffff': 'var(--sc2-white)',
}

function mapColor(hex: string): string {
  return COLOR_MAP[hex] || `var(--sc2-fallback, #${hex})`
}

// Matches: label: val|val|val (3+ values separated by |)
// Values can contain digits, dots, minus, Chinese units, spaces, or be empty
const LEVEL_LINE_RE = /^(.+?)[：:]\s*(.+\|.+\|.+)$/

function isLevelLine(raw: string): { label: string; values: string[] } | null {
  const m = raw.match(LEVEL_LINE_RE)
  if (!m) return null
  const values = m[2].split('|').map(v => v.trim())
  // Must have 3-8 values, and at least half should look like numbers (with optional unit)
  if (values.length < 3 || values.length > 8) return null
  const numericCount = values.filter(v => /^-?[\d.]+/.test(v) || v === '').length
  if (numericCount < values.length * 0.5) return null
  return { label: m[1].trim(), values }
}

function formatLevelLine(label: string, values: string[]): string {
  const cells = values.map((v, i) => {
    let display = v || '-'
    // Value is just a unit without a number (e.g. "秒") — treat as missing
    if (display && !/\d/.test(display)) display = '-'
    return `<td class="lvl-td"><div class="lvl-head">${i + 1}</div><div class="lvl-num">${display}</div></td>`
  }).join('')
  return `<table class="lvl-table"><caption class="lvl-cap">${label}</caption><tr>${cells}</tr></table>`
}

export function parseDescription(raw: string): string {
  if (!raw) return ''
  let text = raw
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/<n\/>/g, '\n')
    .replace(/<c val="([^"]+)">/g, (_m, hex) =>
      `<span style="color:${mapColor(hex)};font-weight:500">`)
    .replace(/<\/c>/g, '</span>')
    .replace(/<d ref="([^"]+)"[^/]*\/>/g, '<em class="sc2-ref">[$1]</em>')
    .replace(/<s val="[^"]*">/g, '')
    .replace(/<\/s>/g, '')

  const lines = text.split('\n')
  const result = lines.map(line => {
    const plain = line.replace(/<[^>]*>/g, '')
    const parsed = isLevelLine(plain)
    if (parsed) return formatLevelLine(parsed.label, parsed.values)
    return line
  })

  // 输出直接喂给 v-html，且 raw 可能来自 editor 可写的 class override，
  // 必须消毒掉任意 HTML（脚本/事件处理器），只保留我们生成的展示标签。
  return DOMPurify.sanitize(result.join('<br>'), {
    ALLOWED_TAGS: ['span', 'em', 'br', 'table', 'caption', 'tr', 'td', 'div'],
    ALLOWED_ATTR: ['class', 'style'],
  })
}

export function stripTags(raw: string): string {
  if (!raw) return ''
  return raw
    .replace(/<n\/>/g, '\n')
    .replace(/<c val="[^"]*">/g, '')
    .replace(/<\/c>/g, '')
    .replace(/<d ref="[^"]*"[^/]*\/>/g, '')
    .replace(/<s val="[^"]*">/g, '')
    .replace(/<\/s>/g, '')
}
