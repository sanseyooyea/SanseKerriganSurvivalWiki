export default defineCachedEventHandler(async (event) => {
  const handle = getQuery(event).handle as string
  if (!handle) {
    throw createError({ statusCode: 400, message: '缺少handle参数' })
  }

  try {
    const data = await $fetch(`https://194823.xyz/api/player?player_handle=${encodeURIComponent(handle)}`, {
      headers: { Accept: 'application/json' },
      timeout: 8000,
    })
    return data
  } catch (e: any) {
    if (e.status === 404 || e.statusCode === 404) {
      return null
    }
    throw createError({ statusCode: 502, message: '无法获取MMR数据' })
  }
}, {
  maxAge: 30,
  name: 'mmr',
  getKey: (event) => (getQuery(event).handle as string) || 'none',
})
