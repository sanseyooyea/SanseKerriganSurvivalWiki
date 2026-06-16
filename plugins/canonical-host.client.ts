// 客户端规范化域名跳转：若用户通过 IP 或 http 访问（如 http://116.62.66.21:8080），
// 跳转到 https://wiki.ks2.top。非安全上下文下剪贴板 API 不可用，分享图/兑换码复制会失效，
// 统一收口到 HTTPS 域名可彻底解决，同时利于 SEO/备案。
export default defineNuxtPlugin(() => {
  if (typeof window === 'undefined') return

  const CANONICAL_HOST = 'wiki.ks2.top'
  const { hostname, protocol, pathname, search, hash } = window.location

  // localhost / 127.0.0.1 用于本地开发，不跳转
  const isLocal = hostname === 'localhost' || hostname === '127.0.0.1'
  if (isLocal) return

  const needsRedirect = hostname !== CANONICAL_HOST || protocol !== 'https:'
  if (needsRedirect) {
    window.location.replace(`https://${CANONICAL_HOST}${pathname}${search}${hash}`)
  }
})
