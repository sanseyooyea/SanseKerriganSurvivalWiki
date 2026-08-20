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
// 投稿者只需写 @bilibili(BV号) 或 @youtube(视频ID)，
// src 模板由这里锁死，投稿者碰不到，既不会写错也没有安全口子。

const bilibili = {
  name: 'bilibili',
  level: 'block' as const,
  start(src: string) {
    const i = src.indexOf('@bilibili(')
    return i < 0 ? undefined : i
  },
  tokenizer(src: string) {
    const m = /^@bilibili\(\s*([A-Za-z0-9]+)\s*\)[^\S\n]*(?:\n|$)/.exec(src)
    if (m) return { type: 'bilibili', raw: m[0], id: m[1] }
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
    const m = /^@youtube\(\s*([A-Za-z0-9_-]+)\s*\)[^\S\n]*(?:\n|$)/.exec(src)
    if (m) return { type: 'youtube', raw: m[0], id: m[1] }
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
