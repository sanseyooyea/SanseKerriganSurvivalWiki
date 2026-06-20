// 流量打点：每次路由切换后上报当前路径到 /api/track。
// 仅客户端运行，失败静默（统计不应影响用户体验）。
export default defineNuxtPlugin((nuxtApp) => {
  if (typeof window === 'undefined') return

  const router = useRouter()

  const report = (path: string) => {
    // 用 sendBeacon 优先，页面卸载时也能发出；不可用则退回 fetch keepalive。
    const body = JSON.stringify({ path, ref: document.referrer || '' })
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/track', new Blob([body], { type: 'application/json' }))
        return
      }
    } catch {}
    fetch('/api/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    }).catch(() => {})
  }

  // 首屏（hydration 完成后）
  nuxtApp.hook('app:mounted', () => report(router.currentRoute.value.path))
  // 后续路由切换
  router.afterEach((to, from) => {
    if (to.path !== from.path) report(to.path)
  })
})
