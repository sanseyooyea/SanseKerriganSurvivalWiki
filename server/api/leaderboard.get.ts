export default defineCachedEventHandler(async () => {
  try {
    const data = await $fetch('https://194823.xyz/api/leaderboard', {
      headers: { Accept: 'application/json' },
      timeout: 8000,
    })
    return data
  } catch (e: any) {
    throw createError({ statusCode: 502, message: '无法获取排行榜数据' })
  }
}, {
  maxAge: 60, // 排行榜周期性生成，缓存 60s 即可，避免每个访客都回源
  name: 'leaderboard',
  getKey: () => 'global',
})
