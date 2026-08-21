import { Marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'

// 允许被 <iframe> 嵌入的可信视频域名白名单。
// 只有 src 落在这些域名下的 iframe 才会被保留，其余一律移除，
// 防止投稿者往正文里塞任意外站内容（钓鱼 / 追踪 / 恶意页）。
const ALLOWED_IFRAME_HOSTS = new Set([
  'player.bilibili.com',
  'www.youtube-nocookie.com',
  'www.youtube.com',
])

// —— 视频短代码扩展 ——
// 投稿者写 @bilibili(...) 或 @youtube(...)，括号内既可以是纯 BV 号 / 视频 ID，
// 也可以直接粘整条视频链接——由下面的 extract* 从中抠出 ID。src 模板由这里锁死，
// 投稿者碰不到，既不会写错也没有安全口子。抠不到合法 ID 时不渲染（回退成原文）。

// 从括号内容里抽 B 站 BV 号：纯 BV 号、含 query/尾斜杠的完整视频链接、b23.tv 带 BV 的短链
// 都能命中；小写 bv 前缀规范化为 BV（号本体大小写保持）。b23.tv 纯哈希短链无法离线解析 → null。
function extractBvid(raw: string): string | null {
  const s = raw.trim()
  const m = /(?:^|[^0-9A-Za-z])((?:BV|bv)[0-9A-Za-z]{10})(?:$|[^0-9A-Za-z])/.exec(s)
            || /((?:BV|bv)[0-9A-Za-z]{10})/.exec(s)
  if (!m) return null
  const id = m[1]
  return id.startsWith('bv') ? 'BV' + id.slice(2) : id
}

// 从括号内容里抽 YouTube 视频 ID：youtu.be/<id>、watch?v=<id>、/embed/<id>、/shorts/<id>
// 及裸 11 位 ID 都能命中。
function extractYoutubeId(raw: string): string | null {
  const s = raw.trim()
  const patterns = [
    /(?:youtu\.be\/)([A-Za-z0-9_-]{11})/,
    /(?:[?&]v=)([A-Za-z0-9_-]{11})/,
    /(?:\/embed\/)([A-Za-z0-9_-]{11})/,
    /(?:\/shorts\/)([A-Za-z0-9_-]{11})/,
  ]
  for (const re of patterns) {
    const m = re.exec(s)
    if (m) return m[1]
  }
  return /^[A-Za-z0-9_-]{11}$/.test(s) ? s : null
}

const bilibili = {
  name: 'bilibili',
  level: 'block' as const,
  start(src: string) {
    const i = src.indexOf('@bilibili(')
    return i < 0 ? undefined : i
  },
  tokenizer(src: string) {
    // 宽松捕获括号内除换行外的任意内容（含整条链接），再抽 BV 号；抽不到则不消费（回退原文）。
    const m = /^@bilibili\(\s*([^)\n]+?)\s*\)[^\S\n]*(?:\n|$)/.exec(src)
    if (!m) return
    const id = extractBvid(m[1])
    if (id) return { type: 'bilibili', raw: m[0], id }
  },
  renderer(token: any) {
    const url = `https://player.bilibili.com/player.html?bvid=${token.id}&page=1&autoplay=0&danmaku=0&high_quality=1`
    return `<div class="wk-video"><iframe src="${url}" scrolling="no" frameborder="0" allowfullscreen></iframe></div>\n`
  },
}

const youtube = {
  name: 'youtube',
  level: 'block' as const,
  start(src: string) {
    const i = src.indexOf('@youtube(')
    return i < 0 ? undefined : i
  },
  tokenizer(src: string) {
    const m = /^@youtube\(\s*([^)\n]+?)\s*\)[^\S\n]*(?:\n|$)/.exec(src)
    if (!m) return
    const id = extractYoutubeId(m[1])
    if (id) return { type: 'youtube', raw: m[0], id }
  },
  renderer(token: any) {
    const url = `https://www.youtube-nocookie.com/embed/${token.id}`
    return `<div class="wk-video"><iframe src="${url}" frameborder="0" allow="accelerometer; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>\n`
  },
}

const md = new Marked({ extensions: [bilibili, youtube] })

// 二次防线：即便有人手写 <iframe>，src 不在白名单就删掉整个节点。
let hookAdded = false
function ensureHook() {
  if (hookAdded) return
  hookAdded = true
  DOMPurify.addHook('uponSanitizeElement', (node: any, data: any) => {
    if (data.tagName !== 'iframe') return
    const src = node.getAttribute?.('src') || ''
    let ok = false
    try {
      const u = new URL(src, 'https://invalid.example/')
      ok = u.protocol === 'https:' && ALLOWED_IFRAME_HOSTS.has(u.host)
    } catch {
      ok = false
    }
    if (!ok) node.parentNode?.removeChild(node)
  })
}

/**
 * 把 Wiki 文章的 Markdown 渲染成经过净化的安全 HTML。
 * 支持视频短代码 @bilibili(...) / @youtube(...)，并对 iframe 做域名白名单。
 */
export function renderMarkdown(src: string): string {
  ensureHook()
  const html = md.parse(src) as string
  return DOMPurify.sanitize(html, {
    ADD_TAGS: ['iframe'],
    ADD_ATTR: ['id', 'allow', 'allowfullscreen', 'frameborder', 'scrolling', 'src'],
  })
}
