// 代理 194823.xyz 更新日志，按页缓存，避免每个访客都回源外站
export default defineCachedEventHandler(async (event) => {
  const q = getQuery(event)
  const page = Math.max(1, parseInt((q.page as string) || '1') || 1)
  const pageSize = Math.min(50, Math.max(1, parseInt((q.page_size as string) || '20') || 20))

  try {
    const data = await $fetch(
      `https://194823.xyz/api/patchnotes?page=${page}&page_size=${pageSize}`,
      { headers: { Accept: 'application/json' }, timeout: 8000 }
    )
    return data
  } catch (e: any) {
    throw createError({ statusCode: 502, message: '无法获取更新日志' })
  }
}, {
  maxAge: 300, // 更新日志变动不频繁，缓存 5 分钟
  name: 'patchnotes',
  getKey: (event) => {
    const q = getQuery(event)
    return `p${q.page || 1}-s${q.page_size || 20}`
  },
})
